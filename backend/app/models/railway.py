from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RailwayLine(Base):
    __tablename__ = "railway_lines"
    __table_args__ = (
        Index("ix_railway_lines_geom_gist", "geom", postgresql_using="gist"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128), index=True)
    ref: Mapped[str | None] = mapped_column(String(64), index=True)
    operator: Mapped[str | None] = mapped_column(String(128), index=True)
    railway_type: Mapped[str | None] = mapped_column(String(64), index=True)
    osm_relation_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    geom: Mapped[str | None] = mapped_column(Geometry("MULTILINESTRING", srid=4326, spatial_index=False))
    properties: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    segments: Mapped[list[RailSegment]] = relationship(back_populates="line", cascade="all, delete-orphan")


class RailSegment(Base):
    __tablename__ = "rail_segments"
    __table_args__ = (
        Index("ix_rail_segments_geom_gist", "geom", postgresql_using="gist"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    line_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("railway_lines.id", ondelete="SET NULL"), index=True)
    from_station_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stations.id", ondelete="SET NULL"), index=True)
    to_station_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stations.id", ondelete="SET NULL"), index=True)
    name: Mapped[str | None] = mapped_column(String(128), index=True)
    distance_km: Mapped[float | None] = mapped_column(Float)
    geom: Mapped[str | None] = mapped_column(Geometry("LINESTRING", srid=4326, spatial_index=False))
    properties: Mapped[dict | None] = mapped_column(JSONB)

    line: Mapped[RailwayLine | None] = relationship(back_populates="segments")
