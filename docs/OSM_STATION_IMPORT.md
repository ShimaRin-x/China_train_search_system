# OSM/OpenRailwayMap 车站坐标导入说明

当前地图底图能显示站名，是因为外部铁路地图瓦片自带了站点 POI。项目自己的后端数据库仍需要把 OSM/OpenRailwayMap 车站坐标导入到 `stations.location`，并和 `cr-12306-train-info` 导入的站名合并，才能支持车站搜索定位、经停站 Marker 和后续车次经路匹配。

## 导入目标

导入器会完成三件事：

1. 读取 OSM/OpenRailwayMap 车站点位。
2. 用站名归一化规则匹配已有 12306 车站，例如 `北京南站` 匹配 `北京南`。
3. 匹配成功后补齐 `stations.location`；匹配失败时默认新建 OSM 车站记录。

## 支持的数据格式

支持两类文件：

- Overpass JSON，包含 `elements`。
- GeoJSON，包含铁路车站 `FeatureCollection`。

要求记录中至少有：

- `railway=station|halt` 或 `public_transport=station + station=train`
- `name` 或 `name:zh`
- 点坐标，或 way/relation 的 `center`

## 方式一：导入本地文件

先启动数据库和后端：

```powershell
docker compose up -d postgres redis backend
```

导入本地 Overpass JSON 或 GeoJSON：

```powershell
.\scripts\import_osm_stations.ps1 -File .\data\osm\osm_railway_stations.json
```

如果只想给已有 12306 车站补坐标，不想新建额外 OSM 站点：

```powershell
.\scripts\import_osm_stations.ps1 -File .\data\osm\osm_railway_stations.json -MatchOnly
```

如果要覆盖已有坐标：

```powershell
.\scripts\import_osm_stations.ps1 -File .\data\osm\osm_railway_stations.json -OverwriteExistingLocation
```

## 方式二：从 Overpass 下载并导入

默认 bbox 约覆盖中国大陆、中国台湾、中国香港、中国澳门：

```powershell
.\scripts\import_osm_stations.ps1 -Download
```

更推荐使用行政区查询，只下载 `CN/TW/HK/MO` 范围内的站点：

```powershell
.\scripts\import_osm_stations.ps1 -Download -AreaQuery -Output "data/osm/greater_china_stations.json"
```

也可以指定 bbox，格式是 `south,west,north,east`：

```powershell
.\scripts\import_osm_stations.ps1 -Download -Bbox "29,115,32.8,122.5" -Output "data/osm/east_china_stations.json"
```

全国范围一次下载可能被 Overpass 限流或超时。实际生产建议按省份或区域分批下载，再多次导入。

## Docker 容器内命令

也可以直接进入 Docker 命令：

```bash
docker compose exec backend python -m app.cli.import_osm_stations --file /app/data/osm/osm_railway_stations.json
```

下载并导入：

```bash
docker compose exec backend python -m app.cli.import_osm_stations --download --bbox 17,73,54.5,136.5
```

## 建议导入顺序

推荐顺序：

1. 导入 OSM/OpenRailwayMap 车站坐标。
2. 导入 `cr-12306-train-info` 车次详情。
3. 再次导入 OSM/OpenRailwayMap 车站坐标，补齐 12306 新增站名的坐标。

也可以先导入 12306，再导入 OSM/OpenRailwayMap。导入器会用站名和别名候选合并。

## 验证

导入后检查接口：

```text
GET http://localhost:8000/api/v1/stations/search?q=北京南
GET http://localhost:8000/api/v1/map/stations?limit=10
```

预期：

- `stations/search` 返回的 `longitude`、`latitude` 不再是 `null`。
- `/map/stations` 返回有坐标的 GeoJSON 点。
- 前端搜索车站后可以定位到地图。
- 选择有坐标的车次经停站后，地图能显示经停站 Marker。
