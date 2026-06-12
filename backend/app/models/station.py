from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Station(Base):
    __tablename__ = "stations"
    __table_args__ = (
        Index("ix_stations_location_gist", "location", postgresql_using="gist"),
        Index("ix_stations_name_zh_trgm", "name_zh", postgresql_using="gin", postgresql_ops={"name_zh": "gin_trgm_ops"}),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name_zh: Mapped[str] = mapped_column(String(128), index=True)
    name_en: Mapped[str | None] = mapped_column(String(128))
    telecode: Mapped[str | None] = mapped_column(String(16), unique=True, index=True)
    pinyin: Mapped[str | None] = mapped_column(String(128), index=True)
    city_name: Mapped[str | None] = mapped_column(String(64), index=True)
    province_name: Mapped[str | None] = mapped_column(String(64), index=True)
    osm_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    openrailwaymap_id: Mapped[str | None] = mapped_column(String(64), index=True)
    location: Mapped[str | None] = mapped_column(Geometry("POINT", srid=4326, spatial_index=False))
    properties: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    aliases: Mapped[list[StationSearchAlias]] = relationship(back_populates="station", cascade="all, delete-orphan")


class StationSearchAlias(Base):
    __tablename__ = "station_search_aliases"
    __table_args__ = (
        UniqueConstraint("station_id", "alias", name="uq_station_alias"),
        Index("ix_station_aliases_alias_trgm", "alias", postgresql_using="gin", postgresql_ops={"alias": "gin_trgm_ops"}),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stations.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str] = mapped_column(String(128), index=True)
    alias_type: Mapped[str] = mapped_column(String(32), default="keyword")
    weight: Mapped[int] = mapped_column(Integer, default=1)

    station: Mapped[Station] = relationship(back_populates="aliases")
