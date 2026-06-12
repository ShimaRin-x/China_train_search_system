from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_DATE_TOKEN = "20260617"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import cr-12306-train-info release JSON into the database.")
    parser.add_argument("--date", default=DEFAULT_DATE_TOKEN, help="Release data date, for example 20260617.")
    parser.add_argument("--tag", default=None, help="GitHub release tag. Defaults to data-<date>.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/cr12306"), help="Local cache directory for release assets.")
    parser.add_argument("--detail-file", type=Path, action="append", default=None, help="Local train_detail JSON file. Can be passed more than once.")
    parser.add_argument("--list-file", type=Path, default=None, help="Local train_list JSON file.")
    parser.add_argument("--class", dest="train_classes", action="append", default=None, help="Import split detail file by train class, such as G, D, C, Z, T, K, S or Y.")
    parser.add_argument("--download", action="store_true", help="Download missing release JSON files from GitHub.")
    parser.add_argument("--limit", type=int, default=None, help="Import only the first N detail records, useful for smoke tests.")
    parser.add_argument("--keep-route-segments", action="store_true", help="Do not clear existing route segments for reimported trains.")
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
    from app.services.cr12306_importer import import_cr12306_release

    with SessionLocal() as db:
        stats = import_cr12306_release(
            db,
            date_token=args.date,
            data_dir=args.data_dir,
            detail_files=args.detail_file,
            list_file=args.list_file,
            train_classes=args.train_classes,
            tag=args.tag,
            download=args.download,
            limit=args.limit,
            clear_route_segments=not args.keep_route_segments,
        )
        db.commit()

    print(json.dumps(stats.as_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
