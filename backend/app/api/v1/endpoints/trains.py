from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.trains import get_train_detail, get_train_route, list_train_stops, search_trains

router = APIRouter()


@router.get("/search")
def search(
    q: str = Query(min_length=1, max_length=64),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    return search_trains(db=db, query=q, limit=limit)


@router.get("/{train_id}")
def detail(train_id: UUID, db: Session = Depends(get_db)) -> dict:
    train = get_train_detail(db=db, train_id=train_id)
    if not train:
        raise HTTPException(status_code=404, detail="Train not found")
    return train


@router.get("/{train_id}/stops")
def stops(train_id: UUID, db: Session = Depends(get_db)) -> list[dict]:
    return list_train_stops(db=db, train_id=train_id)


@router.get("/{train_id}/route")
def route(train_id: UUID, db: Session = Depends(get_db)) -> dict:
    route_geojson = get_train_route(db=db, train_id=train_id)
    if not route_geojson:
        raise HTTPException(status_code=404, detail="Route not found")
    return route_geojson
