from __future__ import annotations

import json
import re
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.station import Station
from app.models.train import TrainRouteSegment, TrainService, TrainStop


EMPTY_FEATURE_COLLECTION = {"type": "FeatureCollection", "features": []}


def train_search_conditions(query: str):
    if query == "0":
        return or_(
            TrainService.train_type == "0",
            TrainService.train_code.op("~")(r"(^|/)[0-9]"),
            TrainService.train_no.op("~")(r"(^|/)[0-9]"),
        )

    if re.fullmatch(r"[A-Z]", query):
        return or_(
            TrainService.train_type == query,
            TrainService.train_code.ilike(f"{query}%"),
            TrainService.train_code.ilike(f"%/{query}%"),
            TrainService.train_code.ilike(f"%{query}%"),
            TrainService.train_no.ilike(f"{query}%"),
            TrainService.train_no.ilike(f"%{query}%"),
        )

    normalized = f"%{query}%"
    return or_(TrainService.train_no.ilike(normalized), TrainService.train_code.ilike(normalized))


def search_trains(db: Session, query: str, limit: int = 20) -> list[dict]:
    stripped_query = query.strip().upper()
    if not stripped_query:
        return []

    prefix_match = f"{stripped_query}%"
    slash_prefix_match = f"%/{stripped_query}%"
    origin = Station.__table__.alias("origin")
    destination = Station.__table__.alias("destination")

    statement = (
        select(
            TrainService.id,
            TrainService.train_no,
            TrainService.train_code,
            TrainService.train_type,
            TrainService.service_date,
            origin.c.name_zh.label("origin_station_name"),
            destination.c.name_zh.label("destination_station_name"),
        )
        .outerjoin(origin, TrainService.origin_station_id == origin.c.id)
        .outerjoin(destination, TrainService.destination_station_id == destination.c.id)
        .where(train_search_conditions(stripped_query))
        .order_by(
            case(
                (TrainService.train_type == stripped_query, 0),
                (TrainService.train_code.ilike(prefix_match), 0),
                (TrainService.train_code.ilike(slash_prefix_match), 1),
                (TrainService.train_no.ilike(prefix_match), 2),
                else_=3,
            ),
            TrainService.train_code,
        )
        .limit(limit)
    )
    rows = db.execute(statement).all()

    return [dict(row._mapping) for row in rows]


def get_train_detail(db: Session, train_id: UUID) -> dict | None:
    origin = Station.__table__.alias("origin")
    destination = Station.__table__.alias("destination")
    statement = (
        select(
            TrainService.id,
            TrainService.train_no,
            TrainService.train_code,
            TrainService.train_type,
            TrainService.service_date,
            TrainService.data_source,
            origin.c.name_zh.label("origin_station_name"),
            destination.c.name_zh.label("destination_station_name"),
        )
        .outerjoin(origin, TrainService.origin_station_id == origin.c.id)
        .outerjoin(destination, TrainService.destination_station_id == destination.c.id)
        .where(TrainService.id == train_id)
    )
    row = db.execute(statement).first()
    if row:
        return dict(row._mapping)
    return None


def list_train_stops(db: Session, train_id: UUID) -> list[dict]:
    statement = (
        select(
            TrainStop.id,
            TrainStop.station_id,
            Station.name_zh.label("station_name"),
            Station.telecode,
            TrainStop.stop_order,
            TrainStop.arrive_time,
            TrainStop.depart_time,
            TrainStop.day_offset,
            TrainStop.dwell_minutes,
            TrainStop.mileage_km,
            func.ST_X(Station.location).label("longitude"),
            func.ST_Y(Station.location).label("latitude"),
        )
        .join(Station, TrainStop.station_id == Station.id)
        .where(TrainStop.train_id == train_id)
        .order_by(TrainStop.stop_order)
    )
    rows = db.execute(statement).all()
    return [dict(row._mapping) for row in rows]


def get_train_route(db: Session, train_id: UUID) -> dict | None:
    statement = (
        select(
            TrainRouteSegment.id,
            TrainRouteSegment.sequence,
            TrainRouteSegment.confidence,
            func.ST_AsGeoJSON(TrainRouteSegment.route_geom).label("geometry"),
        )
        .where(TrainRouteSegment.train_id == train_id)
        .order_by(TrainRouteSegment.sequence)
    )
    rows = db.execute(statement).all()
    if not rows:
        train_exists = db.scalar(select(TrainService.id).where(TrainService.id == train_id))
        return EMPTY_FEATURE_COLLECTION if train_exists else None

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(row.geometry),
                "properties": {
                    "id": row.id,
                    "train_id": train_id,
                    "sequence": row.sequence,
                    "confidence": row.confidence,
                },
            }
            for row in rows
        ],
    }
