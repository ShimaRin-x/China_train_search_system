# API 设计文档

基础路径：`/api/v1`

V1 返回 GeoJSON 的接口可直接被 MapLibre GL 作为 `geojson` source 使用。

## 健康检查

### `GET /health`

响应：

```json
{
  "status": "ok"
}
```

## 地图图层

### `GET /map/railways`

查询铁路线路 GeoJSON。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `bbox` | string | 否 | `west,south,east,north` |
| `limit` | number | 否 | 默认 `5000`，最大 `20000` |

响应：

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [[116.3785, 39.8652], [121.3181, 31.1949]]
      },
      "properties": {
        "id": "uuid",
        "name": "京沪高速铁路",
        "distance_km": 1318
      }
    }
  ]
}
```

### `GET /map/stations`

查询车站 GeoJSON。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `bbox` | string | 否 | `west,south,east,north` |
| `limit` | number | 否 | 默认 `2000`，最大 `10000` |

## 车站

### `GET /stations/search`

车站模糊搜索。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `q` | string | 是 | 中文站名、拼音、电报码或别名 |
| `limit` | number | 否 | 默认 `20`，最大 `100` |

响应：

```json
[
  {
    "id": "uuid",
    "name_zh": "北京南",
    "name_en": "Beijing South",
    "telecode": "VNP",
    "pinyin": "beijingnan",
    "city_name": "北京",
    "province_name": "北京"
  }
]
```

## 车次

### `GET /trains/search`

车次模糊搜索。

参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `q` | string | 是 | 车次号，如 `G101`、`D701` |
| `limit` | number | 否 | 默认 `20`，最大 `100` |

响应：

```json
[
  {
    "id": "uuid",
    "train_no": "G101",
    "train_code": "G101",
    "train_type": "G",
    "service_date": null,
    "origin_station_name": "北京南",
    "destination_station_name": "上海虹桥"
  }
]
```

### `GET /trains/{train_id}`

获取车次详情。

响应：

```json
{
  "id": "uuid",
  "train_no": "G101",
  "train_code": "G101",
  "train_type": "G",
  "service_date": null,
  "origin_station_name": "北京南",
  "destination_station_name": "上海虹桥",
  "data_source": "cr-12306-train-info"
}
```

### `GET /trains/{train_id}/stops`

获取经停站列表。

响应：

```json
[
  {
    "id": "uuid",
    "station_id": "uuid",
    "station_name": "北京南",
    "telecode": "VNP",
    "stop_order": 1,
    "arrive_time": null,
    "depart_time": "07:00:00",
    "day_offset": 0,
    "dwell_minutes": null,
    "mileage_km": 0,
    "longitude": 116.3785,
    "latitude": 39.8652
  }
]
```

### `GET /trains/{train_id}/route`

获取车次经路高亮 GeoJSON。

如果该车次已导入但尚未完成铁路网络空间匹配，返回空 `FeatureCollection`，前端保持经停站列表可用且不显示示例线路。

响应：

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [[116.3785, 39.8652], [121.3181, 31.1949]]
      },
      "properties": {
        "train_id": "uuid",
        "train_no": "G101",
        "sequence": 1,
        "confidence": 0.93
      }
    }
  ]
}
```

## 错误格式

FastAPI 默认错误格式：

```json
{
  "detail": "Train not found"
}
```

## 缓存建议

- `/map/railways`：按 `bbox` 和 zoom 级别缓存。
- `/map/stations`：按 `bbox` 和 zoom 级别缓存。
- `/trains/search`：按搜索词缓存短 TTL。
- `/trains/{id}/route`：经路数据稳定，适合长 TTL。
