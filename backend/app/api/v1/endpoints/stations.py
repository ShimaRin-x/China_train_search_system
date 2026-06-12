from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.stations import search_stations

router = APIRouter()


@router.get("/search")
def search(
    q: str = Query(min_length=1, max_length=64),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    return search_stations(db=db, query=q, limit=limit)
