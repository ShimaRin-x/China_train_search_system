from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.railways import list_railway_features
from app.services.stations import list_station_features
from app.services.wtrans2 import station_geometries_feature_collection

router = APIRouter()


class Wtrans2StationGeometryRequest(BaseModel):
    names: list[str] = Field(min_length=1, max_length=100)


@router.get("/railways")
def railways(
    bbox: str | None = Query(default=None, description="west,south,east,north"),
    limit: int = Query(default=5000, ge=1, le=20000),
    db: Session = Depends(get_db),
) -> dict:
    return list_railway_features(db=db, bbox=bbox, limit=limit)


@router.get("/stations")
def stations(
    bbox: str | None = Query(default=None, description="west,south,east,north"),
    limit: int = Query(default=2000, ge=1, le=10000),
    db: Session = Depends(get_db),
) -> dict:
    return list_station_features(db=db, bbox=bbox, limit=limit)


@router.post("/wtrans2/stations")
def wtrans2_stations(payload: Wtrans2StationGeometryRequest) -> dict:
    return station_geometries_feature_collection(payload.names)
