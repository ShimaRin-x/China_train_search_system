import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.railway import RailSegment

EMPTY_FEATURE_COLLECTION = {"type": "FeatureCollection", "features": []}


def list_railway_features(db: Session, bbox: str | None = None, limit: int = 5000) -> dict:
    statement = select(
        RailSegment.id,
        RailSegment.name,
        RailSegment.distance_km,
        RailSegment.properties,
        func.ST_AsGeoJSON(RailSegment.geom).label("geometry"),
    ).where(RailSegment.geom.is_not(None))

    if bbox:
        west, south, east, north = [float(value) for value in bbox.split(",")]
        envelope = func.ST_MakeEnvelope(west, south, east, north, 4326)
        statement = statement.where(func.ST_Intersects(RailSegment.geom, envelope))

    rows = db.execute(statement.limit(limit)).all()
    if not rows:
        return EMPTY_FEATURE_COLLECTION

    features = []
    for row in rows:
        properties = row.properties or {}
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(row.geometry),
                "properties": {
                    "id": row.id,
                    "name": row.name,
                    "distance_km": row.distance_km,
                    "railway_type": properties.get("railway_type")
                    or properties.get("service_type")
                    or properties.get("category")
                    or properties.get("traffic_type")
                    or "passenger",
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }
