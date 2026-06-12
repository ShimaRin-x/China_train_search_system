from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TrainService(Base):
    __tablename__ = "train_services"
    __table_args__ = (
        UniqueConstraint("train_no", "service_date", name="uq_train_service_no_date"),
        Index("ix_train_services_no_trgm", "train_no", postgresql_using="gin", postgresql_ops={"train_no": "gin_trgm_ops"}),
        Index("ix_train_services_code_trgm", "train_code", postgresql_using="gin", postgresql_ops={"train_code": "gin_trgm_ops"}),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    train_no: Mapped[str] = mapped_column(String(32), index=True)
    train_code: Mapped[str | None] = mapped_column(String(32), index=True)
    train_type: Mapped[str | None] = mapped_column(String(32), index=True)
    service_date: Mapped[date | None] = mapped_column(Date, index=True)
    origin_station_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stations.id", ondelete="SET NULL"), index=True)
    destination_station_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stations.id", ondelete="SET NULL"), index=True)
    data_source: Mapped[str] = mapped_column(String(64), default="cr-12306-train-info")
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    origin_station: Mapped["Station | None"] = relationship(foreign_keys=[origin_station_id])
    destination_station: Mapped["Station | None"] = relationship(foreign_keys=[destination_station_id])
    stops: Mapped[list[TrainStop]] = relationship(back_populates="train", cascade="all, delete-orphan", order_by="TrainStop.stop_order")
    route_segments: Mapped[list[TrainRouteSegment]] = relationship(back_populates="train", cascade="all, delete-orphan", order_by="TrainRouteSegment.sequence")


class TrainStop(Base):
    __tablename__ = "train_stops"
    __table_args__ = (
        UniqueConstraint("train_id", "stop_order", name="uq_train_stop_order"),
        UniqueConstraint("train_id", "station_id", "stop_order", name="uq_train_stop_station_order"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    train_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("train_services.id", ondelete="CASCADE"), index=True)
    station_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stations.id", ondelete="RESTRICT"), index=True)
    stop_order: Mapped[int] = mapped_column(Integer, index=True)
    arrive_time: Mapped[time | None] = mapped_column(Time)
    depart_time: Mapped[time | None] = mapped_column(Time)
    day_offset: Mapped[int] = mapped_column(Integer, default=0)
    dwell_minutes: Mapped[int | None] = mapped_column(Integer)
    mileage_km: Mapped[float | None] = mapped_column(Float)

    train: Mapped[TrainService] = relationship(back_populates="stops")
    station: Mapped["Station"] = relationship()


class TrainRouteSegment(Base):
    __tablename__ = "train_route_segments"
    __table_args__ = (
        UniqueConstraint("train_id", "sequence", name="uq_train_route_sequence"),
        Index("ix_train_route_geom_gist", "route_geom", postgresql_using="gist"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    train_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("train_services.id", ondelete="CASCADE"), index=True)
    segment_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("rail_segments.id", ondelete="SET NULL"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, index=True)
    from_stop_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("train_stops.id", ondelete="SET NULL"))
    to_stop_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("train_stops.id", ondelete="SET NULL"))
    route_geom: Mapped[str | None] = mapped_column(Geometry("LINESTRING", srid=4326, spatial_index=False))
    confidence: Mapped[float | None] = mapped_column(Float)
    properties: Mapped[dict | None] = mapped_column(JSONB)

    train: Mapped[TrainService] = relationship(back_populates="route_segments")
    segment: Mapped["RailSegment | None"] = relationship()
