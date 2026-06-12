from datetime import date, time
from uuid import UUID

from pydantic import BaseModel


class TrainSearchResult(BaseModel):
    id: UUID
    train_no: str
    train_code: str | None = None
    train_type: str | None = None
    service_date: date | None = None
    origin_station_name: str | None = None
    destination_station_name: str | None = None


class TrainDetail(TrainSearchResult):
    data_source: str


class TrainStopOut(BaseModel):
    id: UUID
    station_id: UUID
    station_name: str
    telecode: str | None = None
    stop_order: int
    arrive_time: time | None = None
    depart_time: time | None = None
    day_offset: int = 0
    dwell_minutes: int | None = None
    mileage_km: float | None = None
    longitude: float | None = None
    latitude: float | None = None
