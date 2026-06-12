from __future__ import annotations

import json

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.station import Station, StationSearchAlias

EMPTY_FEATURE_COLLECTION = {"type": "FeatureCollection", "features": []}

MAJOR_STATION_CITIES = {
    "北京",
    "上海",
    "广州",
    "深圳",
    "香港",
    "澳门",
    "台北",
    "天津",
    "重庆",
    "武汉",
    "郑州",
    "西安",
    "成都",
    "南京",
    "杭州",
    "沈阳",
    "哈尔滨",
    "乌鲁木齐",
    "拉萨",
    "昆明",
    "南宁",
}

REGIONAL_STATION_CITIES = {
    "石家庄",
    "济南",
    "青岛",
    "合肥",
    "南昌",
    "长沙",
    "福州",
    "厦门",
    "贵阳",
    "兰州",
    "西宁",
    "呼和浩特",
    "太原",
    "长春",
    "大连",
    "海口",
    "三亚",
    "珠海",
    "台中",
    "高雄",
}


def station_display_rank(name_zh: str | None, city_name: str | None, properties: dict | None) -> int:
    if properties and isinstance(properties.get("display_rank"), int):
        return properties["display_rank"]
    station_name = name_zh or ""
    city = city_name or ""
    if city in MAJOR_STATION_CITIES or any(token in station_name for token in MAJOR_STATION_CITIES):
        return 1
    if city in REGIONAL_STATION_CITIES:
        return 2
    return 3


def list_station_features(db: Session, bbox: str | None = None, limit: int = 2000) -> dict:
    statement = select(
        Station.id,
        Station.name_zh,
        Station.name_en,
        Station.telecode,
        Station.pinyin,
        Station.city_name,
        Station.province_name,
        Station.properties,
        func.ST_AsGeoJSON(Station.location).label("geometry"),
    ).where(Station.location.is_not(None))

    if bbox:
        west, south, east, north = [float(value) for value in bbox.split(",")]
        envelope = func.ST_MakeEnvelope(west, south, east, north, 4326)
        statement = statement.where(func.ST_Intersects(Station.location, envelope))

    rows = db.execute(statement.limit(limit)).all()
    if not rows:
        return EMPTY_FEATURE_COLLECTION

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(row.geometry),
                "properties": {
                    "id": row.id,
                    "name_zh": row.name_zh,
                    "name_en": row.name_en,
                    "telecode": row.telecode,
                    "pinyin": row.pinyin,
                    "city_name": row.city_name,
                    "province_name": row.province_name,
                    "display_rank": station_display_rank(row.name_zh, row.city_name, row.properties),
                },
            }
            for row in rows
        ],
    }


def search_stations(db: Session, query: str, limit: int = 20) -> list[dict]:
    stripped_query = query.strip()
    normalized = f"%{stripped_query}%"
    statement = (
        select(
            Station.id,
            Station.name_zh,
            Station.name_en,
            Station.telecode,
            Station.pinyin,
            Station.city_name,
            Station.province_name,
            Station.properties,
            func.ST_X(Station.location).label("longitude"),
            func.ST_Y(Station.location).label("latitude"),
        )
        .outerjoin(StationSearchAlias)
        .where(
            or_(
                Station.name_zh.ilike(normalized),
                Station.name_en.ilike(normalized),
                Station.pinyin.ilike(normalized),
                Station.telecode.ilike(normalized),
                StationSearchAlias.alias.ilike(normalized),
            )
        )
        .order_by(
            Station.location.is_(None),
            case(
                (Station.name_zh == stripped_query, 0),
                (StationSearchAlias.alias == stripped_query, 1),
                else_=2,
            ),
            Station.name_zh,
            Station.telecode,
        )
        .limit(limit * 3)
    )
    rows = db.execute(statement).all()

    seen_station_ids = set()
    results = []
    for row in rows:
        if row.id in seen_station_ids:
            continue
        seen_station_ids.add(row.id)
        results.append(
            {
                "id": row.id,
                "name_zh": row.name_zh,
                "name_en": row.name_en,
                "telecode": row.telecode,
                "pinyin": row.pinyin,
                "city_name": row.city_name,
                "province_name": row.province_name,
                "display_rank": station_display_rank(row.name_zh, row.city_name, row.properties),
                "longitude": row.longitude,
                "latitude": row.latitude,
            }
        )
        if len(results) >= limit:
            break

    return results
