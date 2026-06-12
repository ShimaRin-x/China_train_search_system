from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.station import Station, StationSearchAlias
from app.services.cr12306_importer import station_lookup_candidates, station_lookup_key


DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_CHINA_BBOX = (17.0, 73.0, 54.5, 136.5)
DEFAULT_AREA_CODES = ("CN", "TW", "HK", "MO")
RAILWAY_STATION_VALUES = {"station", "halt"}
PUBLIC_TRANSPORT_VALUES = {"station", "stop_position"}
URBAN_STATION_VALUES = {"subway", "light_rail", "monorail", "tram"}


@dataclass
class OsmStationImportStats:
    input_files: list[str] = field(default_factory=list)
    downloaded_file: str | None = None
    features_seen: int = 0
    features_skipped: int = 0
    stations_created: int = 0
    stations_matched: int = 0
    stations_updated: int = 0
    aliases_created: int = 0
    duplicate_names: int = 0
    features_outside_bbox: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImportedStationFeature:
    name_zh: str
    longitude: float
    latitude: float
    osm_id: int | None
    openrailwaymap_id: str | None
    source: str
    aliases: tuple[str, ...]
    properties: dict[str, Any]


def normalize_name(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return re.sub(r"\s+", "", text)


def candidate_names(tags: dict[str, Any]) -> list[str]:
    names = [
        tags.get("name:zh"),
        tags.get("name:zh-Hans"),
        tags.get("name:zh_pinyin"),
        tags.get("name"),
        tags.get("official_name"),
        tags.get("alt_name"),
        tags.get("old_name"),
    ]
    results: list[str] = []
    seen: set[str] = set()
    for value in names:
        if not value:
            continue
        for part in re.split(r"[;/；、]", str(value)):
            name = normalize_name(part)
            if name and name not in seen:
                seen.add(name)
                results.append(name)
    return results


def best_station_name(tags: dict[str, Any]) -> str | None:
    for key in ("name:zh", "name:zh-Hans", "name", "official_name"):
        name = normalize_name(tags.get(key))
        if name:
            return name
    names = candidate_names(tags)
    return names[0] if names else None


def is_rail_station(tags: dict[str, Any]) -> bool:
    railway = str(tags.get("railway") or "").lower()
    public_transport = str(tags.get("public_transport") or "").lower()
    station = str(tags.get("station") or "").lower()
    train = str(tags.get("train") or "").lower()
    usage = str(tags.get("usage") or "").lower()
    if station in URBAN_STATION_VALUES and train != "yes":
        return False
    if railway in RAILWAY_STATION_VALUES:
        return True
    if public_transport in PUBLIC_TRANSPORT_VALUES and station in {"train", "railway"}:
        return True
    if usage in {"main", "branch", "industrial", "freight", "tourism"} and railway:
        return True
    return False


def point_from_geometry(geometry: dict[str, Any] | None) -> tuple[float, float] | None:
    if not geometry:
        return None

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point" and isinstance(coordinates, list) and len(coordinates) >= 2:
        return float(coordinates[0]), float(coordinates[1])

    if geometry_type == "Polygon" and isinstance(coordinates, list) and coordinates and coordinates[0]:
        ring = coordinates[0]
        longitude = sum(float(coord[0]) for coord in ring) / len(ring)
        latitude = sum(float(coord[1]) for coord in ring) / len(ring)
        return longitude, latitude

    if geometry_type == "MultiPolygon" and isinstance(coordinates, list):
        points: list[list[float]] = []
        for polygon in coordinates:
            if polygon and polygon[0]:
                points.extend(polygon[0])
        if points:
            longitude = sum(float(coord[0]) for coord in points) / len(points)
            latitude = sum(float(coord[1]) for coord in points) / len(points)
            return longitude, latitude

    return None


def station_feature_from_geojson(feature: dict[str, Any], source: str) -> ImportedStationFeature | None:
    properties = feature.get("properties") or {}
    if not isinstance(properties, dict) or not is_rail_station(properties):
        return None

    coordinates = point_from_geometry(feature.get("geometry"))
    if not coordinates:
        return None

    name = best_station_name(properties)
    if not name:
        return None

    aliases = tuple(item for item in candidate_names(properties) if station_lookup_key(item) != station_lookup_key(name))
    osm_id = parse_osm_id(properties.get("osm_id") or properties.get("@id") or feature.get("id"))
    openrailwaymap_id = normalize_name(properties.get("openrailwaymap_id") or properties.get("orm_id"))
    return ImportedStationFeature(
        name_zh=name,
        longitude=coordinates[0],
        latitude=coordinates[1],
        osm_id=osm_id,
        openrailwaymap_id=openrailwaymap_id,
        source=source,
        aliases=aliases,
        properties=properties,
    )


def parse_osm_id(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value)
    match = re.search(r"(\d+)$", text)
    return int(match.group(1)) if match else None


def load_geojson_station_features(path: Path, source: str) -> list[ImportedStationFeature]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if data.get("type") == "FeatureCollection":
        raw_features = data.get("features") or []
    elif data.get("type") == "Feature":
        raw_features = [data]
    else:
        raise ValueError(f"{path} is not a GeoJSON FeatureCollection or Feature")

    features: list[ImportedStationFeature] = []
    for raw_feature in raw_features:
        if not isinstance(raw_feature, dict):
            continue
        feature = station_feature_from_geojson(raw_feature, source)
        if feature:
            features.append(feature)
    return features


def station_feature_from_overpass_element(element: dict[str, Any], source: str) -> ImportedStationFeature | None:
    tags = element.get("tags") or {}
    if not isinstance(tags, dict) or not is_rail_station(tags):
        return None

    longitude = element.get("lon")
    latitude = element.get("lat")
    center = element.get("center") or {}
    if longitude is None or latitude is None:
        longitude = center.get("lon")
        latitude = center.get("lat")
    if longitude is None or latitude is None:
        return None

    name = best_station_name(tags)
    if not name:
        return None

    aliases = tuple(item for item in candidate_names(tags) if station_lookup_key(item) != station_lookup_key(name))
    osm_type = element.get("type")
    osm_id = parse_osm_id(element.get("id"))
    tags_with_ids = {
        **tags,
        "osm_type": osm_type,
        "osm_id": osm_id,
    }
    return ImportedStationFeature(
        name_zh=name,
        longitude=float(longitude),
        latitude=float(latitude),
        osm_id=osm_id,
        openrailwaymap_id=normalize_name(tags.get("openrailwaymap_id") or tags.get("orm_id")),
        source=source,
        aliases=aliases,
        properties=tags_with_ids,
    )


def load_overpass_station_features(path: Path, source: str) -> list[ImportedStationFeature]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    elements = data.get("elements") or []
    features: list[ImportedStationFeature] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        feature = station_feature_from_overpass_element(element, source)
        if feature:
            features.append(feature)
    return features


def load_station_features(path: Path, source: str) -> list[ImportedStationFeature]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if "elements" in data:
        return load_overpass_station_features_from_data(data, source)
    return load_geojson_station_features_from_data(data, path, source)


def load_geojson_station_features_from_data(data: dict[str, Any], path: Path, source: str) -> list[ImportedStationFeature]:
    if data.get("type") == "FeatureCollection":
        raw_features = data.get("features") or []
    elif data.get("type") == "Feature":
        raw_features = [data]
    else:
        raise ValueError(f"{path} is not a GeoJSON FeatureCollection or Feature")

    features: list[ImportedStationFeature] = []
    for raw_feature in raw_features:
        if not isinstance(raw_feature, dict):
            continue
        feature = station_feature_from_geojson(raw_feature, source)
        if feature:
            features.append(feature)
    return features


def load_overpass_station_features_from_data(data: dict[str, Any], source: str) -> list[ImportedStationFeature]:
    elements = data.get("elements") or []
    features: list[ImportedStationFeature] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        feature = station_feature_from_overpass_element(element, source)
        if feature:
            features.append(feature)
    return features


def load_station_cache(db: Session) -> dict[str, list[Station]]:
    cache: dict[str, list[Station]] = {}
    for station in db.scalars(select(Station)).all():
        for key in station_lookup_candidates(station.name_zh):
            cache.setdefault(key, []).append(station)
    for station_id, alias in db.execute(select(StationSearchAlias.station_id, StationSearchAlias.alias)).all():
        station = db.get(Station, station_id)
        if not station:
            continue
        for key in station_lookup_candidates(alias):
            cache.setdefault(key, []).append(station)
    return cache


def load_alias_cache(db: Session) -> set[tuple[Any, str]]:
    return {
        (station_id, alias)
        for station_id, alias in db.execute(select(StationSearchAlias.station_id, StationSearchAlias.alias)).all()
    }


def find_station_match(feature: ImportedStationFeature, cache: dict[str, list[Station]], stats: OsmStationImportStats) -> Station | None:
    candidates: list[Station] = []
    for name in (feature.name_zh, *feature.aliases):
        for key in station_lookup_candidates(name):
            candidates.extend(cache.get(key, []))

    unique_candidates: dict[Any, Station] = {candidate.id: candidate for candidate in candidates}
    if not unique_candidates:
        return None

    with_missing_location = [candidate for candidate in unique_candidates.values() if candidate.location is None]
    if len(unique_candidates) > 1:
        stats.duplicate_names += 1
    return with_missing_location[0] if with_missing_location else next(iter(unique_candidates.values()))


def make_location(longitude: float, latitude: float):
    return from_shape(Point(longitude, latitude), srid=4326)


def merge_properties(existing: dict[str, Any] | None, feature: ImportedStationFeature) -> dict[str, Any]:
    properties = dict(existing or {})
    properties["coordinate_status"] = "matched"
    properties["coordinate_source"] = feature.source
    properties["osm_station_tags"] = feature.properties
    return properties


def add_aliases(
    db: Session,
    station: Station,
    aliases: Iterable[str],
    alias_type: str,
    stats: OsmStationImportStats,
    alias_cache: set[tuple[Any, str]],
) -> None:
    for alias in aliases:
        normalized = normalize_name(alias)
        if not normalized or normalized == station.name_zh:
            continue
        cache_key = (station.id, normalized)
        if cache_key in alias_cache:
            continue
        db.add(StationSearchAlias(station_id=station.id, alias=normalized, alias_type=alias_type, weight=3))
        alias_cache.add(cache_key)
        stats.aliases_created += 1


def upsert_station_feature(
    db: Session,
    feature: ImportedStationFeature,
    cache: dict[str, list[Station]],
    alias_cache: set[tuple[Any, str]],
    stats: OsmStationImportStats,
    *,
    create_missing: bool,
    overwrite_existing_location: bool,
) -> None:
    station = find_station_match(feature, cache, stats)
    if station:
        stats.stations_matched += 1
        changed = False
        if overwrite_existing_location or station.location is None:
            station.location = make_location(feature.longitude, feature.latitude)
            changed = True
        if feature.osm_id and station.osm_id is None:
            station.osm_id = feature.osm_id
            changed = True
        if feature.openrailwaymap_id and station.openrailwaymap_id is None:
            station.openrailwaymap_id = feature.openrailwaymap_id
            changed = True
        station.properties = merge_properties(station.properties, feature)
        add_aliases(db, station, (feature.name_zh, *feature.aliases), "osm_station_name", stats, alias_cache)
        if changed:
            stats.stations_updated += 1
        return

    if not create_missing:
        stats.features_skipped += 1
        return

    station = Station(
        name_zh=feature.name_zh,
        osm_id=feature.osm_id,
        openrailwaymap_id=feature.openrailwaymap_id,
        location=make_location(feature.longitude, feature.latitude),
        properties=merge_properties({"source": feature.source}, feature),
    )
    db.add(station)
    db.flush()
    add_aliases(db, station, feature.aliases, "osm_station_name", stats, alias_cache)
    for key in station_lookup_candidates(station.name_zh):
        cache.setdefault(key, []).append(station)
    for alias in feature.aliases:
        for key in station_lookup_candidates(alias):
            cache.setdefault(key, []).append(station)
    stats.stations_created += 1


def import_station_files(
    db: Session,
    *,
    paths: list[Path],
    source: str = "openstreetmap",
    create_missing: bool = True,
    overwrite_existing_location: bool = False,
    bbox: tuple[float, float, float, float] | None = DEFAULT_CHINA_BBOX,
) -> OsmStationImportStats:
    stats = OsmStationImportStats(input_files=[str(path) for path in paths])
    cache = load_station_cache(db)
    alias_cache = load_alias_cache(db)

    seen_keys: set[tuple[str, int | None]] = set()
    for path in paths:
        features = load_station_features(path, source)
        for feature in features:
            stats.features_seen += 1
            if bbox and not is_inside_bbox(feature.longitude, feature.latitude, bbox):
                stats.features_outside_bbox += 1
                continue
            dedupe_key = (
                station_lookup_key(feature.name_zh),
                feature.osm_id,
                round(feature.longitude, 6) if feature.osm_id is None else None,
                round(feature.latitude, 6) if feature.osm_id is None else None,
            )
            if dedupe_key in seen_keys:
                stats.features_skipped += 1
                continue
            seen_keys.add(dedupe_key)
            upsert_station_feature(
                db,
                feature,
                cache,
                alias_cache,
                stats,
                create_missing=create_missing,
                overwrite_existing_location=overwrite_existing_location,
            )

    return stats


def build_overpass_query(bbox: tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox
    return f"""
[out:json][timeout:180];
(
  node["railway"~"^(station|halt)$"]({south},{west},{north},{east});
  way["railway"~"^(station|halt)$"]({south},{west},{north},{east});
  relation["railway"~"^(station|halt)$"]({south},{west},{north},{east});
  node["public_transport"="station"]["station"="train"]({south},{west},{north},{east});
  way["public_transport"="station"]["station"="train"]({south},{west},{north},{east});
  relation["public_transport"="station"]["station"="train"]({south},{west},{north},{east});
);
out center tags;
""".strip()


def build_overpass_area_query(area_codes: tuple[str, ...] = DEFAULT_AREA_CODES) -> str:
    area_lines = "\n".join(
        f'area["ISO3166-1"="{code}"]->.area_{index};'
        for index, code in enumerate(area_codes)
    )
    union_lines = "".join(f".area_{index};" for index, _code in enumerate(area_codes))
    return f"""
[out:json][timeout:240];
{area_lines}
({union_lines})->.searchArea;
(
  node["railway"~"^(station|halt)$"](area.searchArea);
  way["railway"~"^(station|halt)$"](area.searchArea);
  relation["railway"~"^(station|halt)$"](area.searchArea);
  node["public_transport"="station"]["station"="train"](area.searchArea);
  way["public_transport"="station"]["station"="train"](area.searchArea);
  relation["public_transport"="station"]["station"="train"](area.searchArea);
);
out center tags;
""".strip()


def download_overpass_stations(
    *,
    destination: Path,
    bbox: tuple[float, float, float, float] = DEFAULT_CHINA_BBOX,
    overpass_url: str = DEFAULT_OVERPASS_URL,
    area_query: bool = False,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    query = build_overpass_area_query() if area_query else build_overpass_query(bbox)
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        overpass_url,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "ChinaTrainSearchSystem/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=240) as response, destination.open("wb") as file:
        file.write(response.read())
    return destination


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    parts = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be south,west,north,east")
    south, west, north, east = parts
    if south >= north or west >= east:
        raise ValueError("bbox must be south,west,north,east")
    return south, west, north, east


def is_inside_bbox(longitude: float, latitude: float, bbox: tuple[float, float, float, float]) -> bool:
    south, west, north, east = bbox
    return west <= longitude <= east and south <= latitude <= north
