# 数据库 ER 图

```mermaid
erDiagram
  STATIONS {
    uuid id PK
    varchar name_zh
    varchar name_en
    varchar telecode UK
    varchar pinyin
    varchar city_name
    varchar province_name
    bigint osm_id
    varchar openrailwaymap_id
    geometry_point location
    jsonb properties
    timestamptz created_at
    timestamptz updated_at
  }

  STATION_SEARCH_ALIASES {
    int id PK
    uuid station_id FK
    varchar alias
    varchar alias_type
    int weight
  }

  RAILWAY_LINES {
    uuid id PK
    varchar name
    varchar ref
    varchar operator
    varchar railway_type
    bigint osm_relation_id
    geometry_multilinestring geom
    jsonb properties
    timestamptz created_at
    timestamptz updated_at
  }

  RAIL_SEGMENTS {
    uuid id PK
    uuid line_id FK
    uuid from_station_id FK
    uuid to_station_id FK
    varchar name
    float distance_km
    geometry_linestring geom
    jsonb properties
  }

  TRAIN_SERVICES {
    uuid id PK
    varchar train_no
    varchar train_code
    varchar train_type
    date service_date
    uuid origin_station_id FK
    uuid destination_station_id FK
    varchar data_source
    jsonb raw_payload
    timestamptz created_at
    timestamptz updated_at
  }

  TRAIN_STOPS {
    uuid id PK
    uuid train_id FK
    uuid station_id FK
    int stop_order
    time arrive_time
    time depart_time
    int day_offset
    int dwell_minutes
    float mileage_km
  }

  TRAIN_ROUTE_SEGMENTS {
    uuid id PK
    uuid train_id FK
    uuid segment_id FK
    int sequence
    uuid from_stop_id FK
    uuid to_stop_id FK
    geometry_linestring route_geom
    float confidence
    jsonb properties
  }

  INGEST_JOBS {
    uuid id PK
    varchar source
    varchar status
    timestamptz started_at
    timestamptz finished_at
    jsonb stats
    text error_message
    timestamptz created_at
  }

  STATIONS ||--o{ STATION_SEARCH_ALIASES : has
  STATIONS ||--o{ TRAIN_STOPS : stops_at
  STATIONS ||--o{ TRAIN_SERVICES : origin
  STATIONS ||--o{ TRAIN_SERVICES : destination
  RAILWAY_LINES ||--o{ RAIL_SEGMENTS : contains
  STATIONS ||--o{ RAIL_SEGMENTS : from_station
  STATIONS ||--o{ RAIL_SEGMENTS : to_station
  TRAIN_SERVICES ||--o{ TRAIN_STOPS : has
  TRAIN_SERVICES ||--o{ TRAIN_ROUTE_SEGMENTS : highlights
  RAIL_SEGMENTS ||--o{ TRAIN_ROUTE_SEGMENTS : matched_by
  TRAIN_STOPS ||--o{ TRAIN_ROUTE_SEGMENTS : from_stop
  TRAIN_STOPS ||--o{ TRAIN_ROUTE_SEGMENTS : to_stop
```

## 关键索引

- `stations.location`：GiST 空间索引，用于地图视野内车站查询。
- `rail_segments.geom`：GiST 空间索引，用于铁路地图图层和经路匹配。
- `train_route_segments.route_geom`：GiST 空间索引，用于高亮线路空间查询。
- `stations.name_zh`、`station_search_aliases.alias`、`train_services.train_no`、`train_services.train_code`：GIN + `pg_trgm`，用于模糊搜索。

## 数据来源映射

- OpenStreetMap：`stations.osm_id`、`railway_lines.osm_relation_id`、`rail_segments.geom`。
- OpenRailwayMap：`openrailwaymap_id`、`railway_type`、`properties` 中的电气化、轨距、限速、运营状态等标签。
- cr-12306-train-info：`train_services`、`train_stops`、`raw_payload`。
