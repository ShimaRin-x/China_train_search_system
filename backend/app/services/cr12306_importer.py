from __future__ import annotations

import json
import re
import urllib.request
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, time
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.station import Station, StationSearchAlias
from app.models.train import TrainRouteSegment, TrainService, TrainStop


RELEASE_BASE_URL = "https://github.com/HerbertHe/cr-12306-train-info/releases/download"
DATA_SOURCE = "cr-12306-train-info"
DEFAULT_DATE_TOKEN = "20260617"


@dataclass
class Cr12306ImportStats:
    detail_files: list[str] = field(default_factory=list)
    list_file: str | None = None
    downloaded_files: list[str] = field(default_factory=list)
    services_seen: int = 0
    services_created: int = 0
    services_updated: int = 0
    services_skipped: int = 0
    stations_created: int = 0
    stops_created: int = 0
    stops_skipped: int = 0
    route_segments_cleared: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_date_token(value: str) -> str:
    token = re.sub(r"\D", "", value)
    if len(token) != 8:
        raise ValueError("date must be YYYYMMDD or YYYY-MM-DD")
    return token


def service_date_from_token(value: str) -> date:
    token = normalize_date_token(value)
    return date(int(token[:4]), int(token[4:6]), int(token[6:8]))


def release_tag_for_date(date_token: str) -> str:
    return f"data-{normalize_date_token(date_token)}"


def detail_asset_name(date_token: str, train_class: str | None = None) -> str:
    token = normalize_date_token(date_token)
    if train_class:
        return f"train_detail_{train_class.upper()}_{token}.json"
    return f"train_detail_{token}.json"


def train_list_asset_name(date_token: str) -> str:
    return f"train_list_{normalize_date_token(date_token)}.json"


def asset_url(date_token: str, asset_name: str, tag: str | None = None) -> str:
    release_tag = tag or release_tag_for_date(date_token)
    return f"{RELEASE_BASE_URL}/{release_tag}/{asset_name}"


def download_asset(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "ChinaTrainSearchSystem/1.0"})
    with urllib.request.urlopen(request) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
    return destination


def ensure_release_files(
    *,
    date_token: str,
    data_dir: Path,
    train_classes: list[str] | None = None,
    tag: str | None = None,
    download: bool = False,
) -> tuple[list[Path], Path | None, list[Path]]:
    token = normalize_date_token(date_token)
    data_dir.mkdir(parents=True, exist_ok=True)
    detail_names = [detail_asset_name(token, item) for item in train_classes] if train_classes else [detail_asset_name(token)]
    list_name = train_list_asset_name(token)
    paths = [data_dir / name for name in detail_names]
    list_path = data_dir / list_name
    downloaded: list[Path] = []

    required = [*paths, list_path]
    for path in required:
        if path.exists():
            continue
        if not download:
            raise FileNotFoundError(f"{path} does not exist; rerun with --download or pass an explicit file path")
        download_asset(asset_url(token, path.name, tag), path)
        downloaded.append(path)

    return paths, list_path, downloaded


def load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_train_list(path: Path | None) -> dict[str, list[dict[str, Any]]]:
    if not path or not path.exists():
        return {}
    rows = load_json_file(path)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        train_no = str(row.get("train_no") or "").strip()
        if train_no:
            grouped[train_no].append(row)
    return grouped


def load_detail_records(paths: list[Path], limit: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        rows = load_json_file(path)
        if not isinstance(rows, list):
            raise ValueError(f"{path} must contain a JSON array")
        records.extend(row for row in rows if isinstance(row, dict))
        if limit and len(records) >= limit:
            return records[:limit]
    return records


STATION_NAME_SUFFIXES = ("火车站", "铁路车站", "车站", "站")


def station_lookup_key(name: str | None) -> str:
    value = (name or "").strip()
    value = re.sub(r"[（(].*?[）)]", "", value)
    for suffix in STATION_NAME_SUFFIXES:
        if value.endswith(suffix) and len(value) > len(suffix):
            value = value[: -len(suffix)]
            break
    return re.sub(r"\s+", "", value)


def station_lookup_candidates(name: str | None) -> list[str]:
    key = station_lookup_key(name)
    if not key:
        return []
    return [key, station_lookup_key(f"{key}站")]


def station_name_from_stop(stop: dict[str, Any]) -> str | None:
    value = stop.get("station_name")
    if value is None:
        return None
    name = str(value).strip()
    return name or None


def collect_station_names(records: list[dict[str, Any]], train_list: dict[str, list[dict[str, Any]]]) -> set[str]:
    names: set[str] = set()
    for record in records:
        stops = record.get("data") or []
        for stop in stops:
            name = station_name_from_stop(stop)
            if name:
                names.add(name)
        start_name, end_name = service_endpoint_names(record, train_list.get(str(record.get("train_no") or "").strip(), []))
        if start_name:
            names.add(start_name)
        if end_name:
            names.add(end_name)
    return names


def load_station_cache(db: Session) -> dict[str, Any]:
    cache: dict[str, Any] = {}
    for station_id, name in db.execute(select(Station.id, Station.name_zh)).all():
        for key in station_lookup_candidates(name):
            cache.setdefault(key, station_id)
    for station_id, alias in db.execute(select(StationSearchAlias.station_id, StationSearchAlias.alias)).all():
        for key in station_lookup_candidates(alias):
            cache.setdefault(key, station_id)
    return cache


def ensure_stations(db: Session, names: set[str], stats: Cr12306ImportStats) -> dict[str, Any]:
    cache = load_station_cache(db)
    missing: list[str] = []
    for name in sorted(names):
        if not any(key in cache for key in station_lookup_candidates(name)):
            missing.append(name)

    created: list[tuple[str, Station]] = []
    for name in missing:
        station = Station(
            name_zh=name,
            properties={
                "source": DATA_SOURCE,
                "coordinate_status": "missing",
            },
        )
        db.add(station)
        created.append((name, station))

    if created:
        db.flush()

    for name, station in created:
        db.add(StationSearchAlias(station_id=station.id, alias=name, alias_type="cr12306_station_name", weight=5))
        for key in station_lookup_candidates(name):
            cache.setdefault(key, station.id)
        stats.stations_created += 1

    return cache


def station_id_for_name(station_cache: dict[str, Any], name: str | None) -> Any | None:
    for key in station_lookup_candidates(name):
        station_id = station_cache.get(key)
        if station_id:
            return station_id
    return None


def unique_codes(values: list[str]) -> list[str]:
    seen: set[str] = set()
    codes: list[str] = []
    for value in values:
        for part in str(value or "").split("/"):
            code = part.strip().upper()
            if code and code not in seen:
                seen.add(code)
                codes.append(code)
    return codes


def service_codes(record: dict[str, Any], list_entries: list[dict[str, Any]]) -> str | None:
    values: list[str] = []
    if record.get("station_train_codes"):
        values.append(str(record["station_train_codes"]))
    for stop in record.get("data") or []:
        if stop.get("station_train_code"):
            values.append(str(stop["station_train_code"]))
    for entry in list_entries:
        if entry.get("station_train_code"):
            values.append(str(entry["station_train_code"]))
    codes = unique_codes(values)
    return "/".join(codes) if codes else None


def infer_train_type(train_code: str | None) -> str | None:
    if not train_code:
        return None
    match = re.search(r"[A-Z]", train_code.upper())
    return match.group(0) if match else "0"


def parse_time_value(value: Any) -> time | None:
    if value in (None, "", "--", "----"):
        return None
    text = str(value).strip()
    if not text or text in {"--", "----"}:
        return None
    try:
        hour, minute = text.split(":", 1)
        return time(int(hour), int(minute))
    except (TypeError, ValueError):
        return None


def minutes_after_midnight(value: time) -> int:
    return value.hour * 60 + value.minute


def dwell_minutes(arrive_time: time | None, depart_time: time | None) -> int | None:
    if not arrive_time or not depart_time:
        return None
    arrive = minutes_after_midnight(arrive_time)
    depart = minutes_after_midnight(depart_time)
    if depart < arrive:
        depart += 24 * 60
    minutes = depart - arrive
    return minutes if 0 <= minutes <= 12 * 60 else None


def parse_day_offset(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def service_endpoint_names(record: dict[str, Any], list_entries: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    stops = record.get("data") or []
    first_stop = stops[0] if stops else {}
    last_stop = stops[-1] if stops else {}

    origin = first_stop.get("start_station_name") or first_stop.get("station_name")
    destination = first_stop.get("end_station_name") or last_stop.get("station_name")

    if (not origin or not destination) and list_entries:
        origin = origin or list_entries[0].get("from_station")
        destination = destination or list_entries[0].get("to_station")

    return (str(origin).strip() if origin else None, str(destination).strip() if destination else None)


def import_cr12306_records(
    db: Session,
    *,
    detail_records: list[dict[str, Any]],
    train_list: dict[str, list[dict[str, Any]]],
    service_date: date,
    release_tag: str,
    clear_route_segments: bool = True,
) -> Cr12306ImportStats:
    stats = Cr12306ImportStats()
    station_cache = ensure_stations(db, collect_station_names(detail_records, train_list), stats)

    for record in detail_records:
        stats.services_seen += 1
        train_no = str(record.get("train_no") or "").strip()
        stops = record.get("data") or []
        if not train_no or not stops:
            stats.services_skipped += 1
            continue

        list_entries = train_list.get(train_no, [])
        train_code = service_codes(record, list_entries)
        origin_name, destination_name = service_endpoint_names(record, list_entries)
        origin_id = station_id_for_name(station_cache, origin_name)
        destination_id = station_id_for_name(station_cache, destination_name)

        train = db.scalar(
            select(TrainService).where(
                TrainService.train_no == train_no,
                TrainService.service_date == service_date,
            )
        )
        if train is None:
            train = TrainService(train_no=train_no, service_date=service_date)
            db.add(train)
            stats.services_created += 1
        else:
            stats.services_updated += 1

        train.train_code = train_code
        train.train_type = infer_train_type(train_code)
        train.origin_station_id = origin_id
        train.destination_station_id = destination_id
        train.data_source = DATA_SOURCE
        train.raw_payload = {
            "release_tag": release_tag,
            "source": DATA_SOURCE,
            "train_list_entries": list_entries,
            "detail": record,
        }
        db.flush()

        if clear_route_segments:
            deleted = db.query(TrainRouteSegment).filter(TrainRouteSegment.train_id == train.id).delete(synchronize_session=False)
            stats.route_segments_cleared += deleted

        db.query(TrainStop).filter(TrainStop.train_id == train.id).delete(synchronize_session=False)

        for index, stop in enumerate(stops, start=1):
            station_name = station_name_from_stop(stop)
            station_id = station_id_for_name(station_cache, station_name)
            if not station_id:
                stats.stops_skipped += 1
                continue

            arrive_time = parse_time_value(stop.get("arrive_time"))
            depart_time = parse_time_value(stop.get("start_time"))
            if index == len(stops):
                depart_time = None

            db.add(
                TrainStop(
                    train_id=train.id,
                    station_id=station_id,
                    stop_order=index,
                    arrive_time=arrive_time,
                    depart_time=depart_time,
                    day_offset=parse_day_offset(stop.get("arrive_day_diff")),
                    dwell_minutes=dwell_minutes(arrive_time, depart_time),
                    mileage_km=None,
                )
            )
            stats.stops_created += 1

    return stats


def import_cr12306_release(
    db: Session,
    *,
    date_token: str = DEFAULT_DATE_TOKEN,
    data_dir: Path,
    detail_files: list[Path] | None = None,
    list_file: Path | None = None,
    train_classes: list[str] | None = None,
    tag: str | None = None,
    download: bool = False,
    limit: int | None = None,
    clear_route_segments: bool = True,
) -> Cr12306ImportStats:
    token = normalize_date_token(date_token)
    release_tag = tag or release_tag_for_date(token)

    downloaded: list[Path] = []
    if not detail_files:
        detail_files, default_list_file, downloaded = ensure_release_files(
            date_token=token,
            data_dir=data_dir,
            train_classes=train_classes,
            tag=release_tag,
            download=download,
        )
        list_file = list_file or default_list_file
    elif download:
        raise ValueError("--download can only be used when detail files are inferred from --date/--classes")

    detail_paths = [Path(path) for path in detail_files]
    list_path = Path(list_file) if list_file else None
    detail_records = load_detail_records(detail_paths, limit=limit)
    train_list = parse_train_list(list_path)

    stats = import_cr12306_records(
        db,
        detail_records=detail_records,
        train_list=train_list,
        service_date=service_date_from_token(token),
        release_tag=release_tag,
        clear_route_segments=clear_route_segments,
    )
    stats.detail_files = [str(path) for path in detail_paths]
    stats.list_file = str(list_path) if list_path else None
    stats.downloaded_files = [str(path) for path in downloaded]
    return stats
