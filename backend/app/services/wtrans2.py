from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any

import httpx

EMPTY_FEATURE_COLLECTION = {"type": "FeatureCollection", "features": []}
CNRAIL_API_BASE = "http://cnrail.geogv.org/api"
CNRAIL_LOCALE = "zhcn"
MAX_STATION_NAMES = 100
MAX_STATION_LOOKUP_WORKERS = 12


def clean_station_name(name: str) -> str:
    return re.sub(r"\s+", "", name).removesuffix("站")


def decode_cnrail_payload(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str) or not payload:
        return None

    key_length = ord(payload[0])
    key = payload[1 : 1 + key_length]
    body = payload[1 + key_length :]
    if not key:
        return None

    decoded = "".join(chr(ord(char) - ord(key[index % len(key)])) for index, char in enumerate(body))
    try:
        data = json.loads(decoded)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def station_query_variants(name: str) -> list[str]:
    compact = re.sub(r"\s+", "", name)
    base = clean_station_name(compact)
    variants = [compact]
    if base and base != compact:
        variants.append(base)
    if base:
        variants.append(f"{base}站")

    seen: set[str] = set()
    return [value for value in variants if value and not (value in seen or seen.add(value))]


def result_score(result: dict[str, Any], target_name: str) -> tuple[int, str]:
    name = str(result.get("name") or "")
    query = str(result.get("query") or "")
    clean_name = clean_station_name(name)
    clean_target = clean_station_name(target_name)

    if clean_name == clean_target and query.startswith("geo/"):
        return (0, name)
    if clean_name == clean_target:
        return (1, name)
    if query.startswith("geo/") and clean_target in clean_name:
        return (2, name)
    if clean_target in clean_name:
        return (3, name)
    return (9, name)


def search_station_candidates(client: httpx.Client, query: str) -> list[dict[str, Any]]:
    response = client.get(
        f"{CNRAIL_API_BASE}/search/",
        params={"keyword": query, "region": "", "locale": CNRAIL_LOCALE},
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def fetch_poi(client: httpx.Client, kid: str) -> dict[str, Any] | None:
    response = client.get(f"{CNRAIL_API_BASE}/poi/{kid}", params={"locale": CNRAIL_LOCALE})
    response.raise_for_status()
    return decode_cnrail_payload(response.json())


@lru_cache(maxsize=4096)
def wtrans2_station_geometry(name: str) -> dict[str, Any] | None:
    target_name = clean_station_name(name)
    if not target_name:
        return None

    try:
        with httpx.Client(timeout=httpx.Timeout(6.0, connect=3.0)) as client:
            for query in station_query_variants(name):
                candidates = search_station_candidates(client, query)
                station_candidates = [candidate for candidate in candidates if str(candidate.get("query") or "").startswith("geo/")]
                if not station_candidates:
                    continue

                best = sorted(station_candidates, key=lambda item: result_score(item, target_name))[0]
                kid = str(best.get("query", "")).split("/", 1)[1]
                poi = fetch_poi(client, kid)
                if not poi:
                    continue

                geometry = poi.get("geom")
                if not isinstance(geometry, dict) or geometry.get("type") != "Point":
                    continue

                return {
                    "kid": kid,
                    "matched_name": re.sub(r"<[^>]+>", "", str(poi.get("name") or best.get("name") or "")),
                    "geometry": geometry,
                    "minzoom": poi.get("minzoom"),
                    "location": poi.get("location"),
                }
    except httpx.HTTPError:
        return None

    return None


def station_geometries_feature_collection(names: list[str]) -> dict[str, Any]:
    limited_names = names[:MAX_STATION_NAMES]

    def build_feature(item: tuple[int, str]) -> dict[str, Any] | None:
        index, name = item
        station = wtrans2_station_geometry(name)
        if not station:
            return None

        return {
            "type": "Feature",
            "geometry": station["geometry"],
            "properties": {
                "order": index,
                "input_name": name,
                "matched_name": station["matched_name"],
                "kid": station["kid"],
                "minzoom": station["minzoom"],
                "location": station["location"],
            },
        }

    features = []
    with ThreadPoolExecutor(max_workers=min(MAX_STATION_LOOKUP_WORKERS, max(len(limited_names), 1))) as executor:
        for feature in executor.map(build_feature, enumerate(limited_names)):
            if feature:
                features.append(feature)

    return {"type": "FeatureCollection", "features": features} if features else EMPTY_FEATURE_COLLECTION
