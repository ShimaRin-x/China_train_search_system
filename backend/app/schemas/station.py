from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class StationProperties(BaseModel):
    id: UUID
    name_zh: str
    name_en: str | None = None
    telecode: str | None = None
    pinyin: str | None = None
    city_name: str | None = None
    province_name: str | None = None


class StationFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any]
    properties: StationProperties


class StationDetail(StationProperties):
    osm_id: int | None = None
    openrailwaymap_id: str | None = None
    properties: dict[str, Any] | None = None
