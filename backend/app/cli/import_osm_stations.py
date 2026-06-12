from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import OSM/OpenRailwayMap railway station coordinates into the database.")
    parser.add_argument("--file", type=Path, action="append", default=[], help="Local Overpass JSON or GeoJSON station file. Can be passed more than once.")
    parser.add_argument("--source", default="openstreetmap", choices=["openstreetmap", "openrailwaymap"], help="Coordinate source label.")
    parser.add_argument("--download", action="store_true", help="Download station data from Overpass before importing.")
    parser.add_argument("--area-query", action="store_true", help="Use ISO areas CN/TW/HK/MO instead of bbox when downloading from Overpass.")
    parser.add_argument("--bbox", default="17,73,54.5,136.5", help="Overpass bbox as south,west,north,east. Default covers China/Taiwan/HK/Macau roughly.")
    parser.add_argument("--no-bbox-filter", action="store_true", help="Do not filter imported local files by bbox.")
    parser.add_argument("--overpass-url", default=None, help="Custom Overpass interpreter URL.")
    parser.add_argument("--output", type=Path, default=Path("data/osm/osm_railway_stations.json"), help="Downloaded Overpass JSON path.")
    parser.add_argument("--match-only", action="store_true", help="Only update existing stations, do not create new OSM stations.")
    parser.add_argument("--overwrite-existing-location", action="store_true", help="Overwrite coordinates for stations that already have a location.")
    parser.add_argument("--skip-create-schema", action="store_true", help="Skip Base.metadata.create_all before import.")
    return parser


def ensure_database_schema() -> None:
    from sqlalchemy import text

    from app import models as _models
    from app.db.base import Base
    from app.db.session import engine

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    Base.metadata.create_all(bind=engine)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.skip_create_schema:
        ensure_database_schema()

    from app.db.session import SessionLocal
    from app.services.osm_station_importer import (
        download_overpass_stations,
        import_station_files,
        parse_bbox,
    )

    paths: list[Path] = list(args.file)
    bbox = parse_bbox(args.bbox)
    downloaded_file = None
    if args.download:
        overpass_url = args.overpass_url
        kwargs = {
            "destination": args.output,
            "bbox": bbox,
            "area_query": args.area_query,
        }
        if overpass_url:
            kwargs["overpass_url"] = overpass_url
        downloaded_file = download_overpass_stations(**kwargs)
        paths.append(downloaded_file)

    if not paths:
        parser.error("pass at least one --file or use --download")

    with SessionLocal() as db:
        stats = import_station_files(
            db,
            paths=paths,
            source=args.source,
            create_missing=not args.match_only,
            overwrite_existing_location=args.overwrite_existing_location,
            bbox=None if args.no_bbox_filter else bbox,
        )
        if downloaded_file:
            stats.downloaded_file = str(downloaded_file)
        db.commit()

    print(json.dumps(stats.as_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
