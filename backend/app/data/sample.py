from __future__ import annotations

from uuid import UUID

SAMPLE_STATIONS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "name_zh": "北京南",
        "name_en": "Beijing South",
        "telecode": "VNP",
        "pinyin": "beijingnan",
        "city_name": "北京",
        "province_name": "北京",
        "coordinates": [116.3785, 39.8652],
        "display_rank": 1,
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "name_zh": "济南西",
        "name_en": "Jinan West",
        "telecode": "JGK",
        "pinyin": "jinanxi",
        "city_name": "济南",
        "province_name": "山东",
        "coordinates": [116.9019, 36.6684],
        "display_rank": 2,
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "name_zh": "南京南",
        "name_en": "Nanjing South",
        "telecode": "NKH",
        "pinyin": "nanjingnan",
        "city_name": "南京",
        "province_name": "江苏",
        "coordinates": [118.7921, 31.9707],
        "display_rank": 1,
    },
    {
        "id": "44444444-4444-4444-4444-444444444444",
        "name_zh": "上海虹桥",
        "name_en": "Shanghai Hongqiao",
        "telecode": "AOH",
        "pinyin": "shanghaihongqiao",
        "city_name": "上海",
        "province_name": "上海",
        "coordinates": [121.3181, 31.1949],
        "display_rank": 1,
    },
]

SAMPLE_TRAINS = [
    {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "train_no": "G101",
        "train_code": "G101",
        "train_type": "G",
        "service_date": None,
        "origin_station_name": "北京南",
        "destination_station_name": "上海虹桥",
        "data_source": "sample",
    }
]

SAMPLE_STOPS = [
    {
        "id": "90000000-0000-0000-0000-000000000001",
        "station_id": SAMPLE_STATIONS[0]["id"],
        "station_name": "北京南",
        "telecode": "VNP",
        "stop_order": 1,
        "arrive_time": None,
        "depart_time": "07:00:00",
        "day_offset": 0,
        "dwell_minutes": None,
        "mileage_km": 0,
        "longitude": 116.3785,
        "latitude": 39.8652,
    },
    {
        "id": "90000000-0000-0000-0000-000000000002",
        "station_id": SAMPLE_STATIONS[1]["id"],
        "station_name": "济南西",
        "telecode": "JGK",
        "stop_order": 2,
        "arrive_time": "08:22:00",
        "depart_time": "08:25:00",
        "day_offset": 0,
        "dwell_minutes": 3,
        "mileage_km": 406,
        "longitude": 116.9019,
        "latitude": 36.6684,
    },
    {
        "id": "90000000-0000-0000-0000-000000000003",
        "station_id": SAMPLE_STATIONS[2]["id"],
        "station_name": "南京南",
        "telecode": "NKH",
        "stop_order": 3,
        "arrive_time": "10:23:00",
        "depart_time": "10:25:00",
        "day_offset": 0,
        "dwell_minutes": 2,
        "mileage_km": 1023,
        "longitude": 118.7921,
        "latitude": 31.9707,
    },
    {
        "id": "90000000-0000-0000-0000-000000000004",
        "station_id": SAMPLE_STATIONS[3]["id"],
        "station_name": "上海虹桥",
        "telecode": "AOH",
        "stop_order": 4,
        "arrive_time": "11:38:00",
        "depart_time": None,
        "day_offset": 0,
        "dwell_minutes": None,
        "mileage_km": 1318,
        "longitude": 121.3181,
        "latitude": 31.1949,
    },
]


def sample_station_collection() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": item["coordinates"]},
                "properties": {key: value for key, value in item.items() if key != "coordinates"},
            }
            for item in SAMPLE_STATIONS
        ],
    }


def sample_railway_collection() -> dict:
    coordinates = [station["coordinates"] for station in SAMPLE_STATIONS]
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coordinates},
                "properties": {
                    "id": "sample-jinghu-hsr",
                    "name": "京沪高速铁路示例线",
                    "railway_type": "high_speed",
                    "source": "sample",
                },
            }
        ],
    }


def sample_train_route(train_id: UUID | str) -> dict | None:
    if str(train_id) != SAMPLE_TRAINS[0]["id"]:
        return None
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [station["coordinates"] for station in SAMPLE_STATIONS]},
                "properties": {
                    "train_id": SAMPLE_TRAINS[0]["id"],
                    "train_no": "G101",
                    "sequence": 1,
                    "confidence": 1,
                    "source": "sample",
                },
            }
        ],
    }
