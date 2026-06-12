# 前后端开发计划

## V1 范围

- 铁路地图：展示铁路线路和基础底图。
- 车站图层：展示站点点位和弹窗。
- 车次搜索：按车次号搜索。
- 经停站展示：按站序展示到发时刻、停站时长、里程。
- 车次经路高亮：在地图上显示选中车次线路。
- 模糊搜索：支持车次号、站名、拼音、电报码和别名。

## 后端计划

### 1. 数据库与模型

- 建立 PostGIS 数据库和扩展：`postgis`、`pg_trgm`、`unaccent`。
- 建立主表：`stations`、`station_search_aliases`、`railway_lines`、`rail_segments`、`train_services`、`train_stops`、`train_route_segments`。
- 为几何字段建立 GiST 索引。
- 为搜索字段建立 GIN trigram 索引。

### 2. 数据导入

- OpenStreetMap：
  - 使用 `osm2pgsql`、`osmium` 或 `pyrosm` 提取中国铁路站点和线路。
  - 将 station、halt、railway=rail、route=train 等对象标准化到站点和线路表。
- OpenRailwayMap：
  - 补充 railway 类型、电气化、轨距、限速、运营状态等标签。
  - 与 OSM 对象通过 OSM id、名称、空间邻近关系合并。
- cr-12306-train-info：
  - 使用 release JSON 离线导入车次、车站序列、到发时刻。
  - 站名与站点表通过中文名、电报码、拼音和人工别名匹配。
  - 当前命令：`python -m app.cli.import_cr12306 --date 20260617 --download`。

### 3. 经路匹配

- 根据车次经停站序列构建相邻 OD。
- 对每个 OD 在铁路网络上寻找候选路径。
- 使用站点距离、线路名、方向、路径长度偏差给候选路径打分。
- 将结果写入 `train_route_segments`，保留 `confidence` 和 `properties` 以便人工校验。

### 4. API

- 地图图层接口按 bbox 返回 GeoJSON。
- 搜索接口支持模糊匹配和 Redis 缓存。
- 车次详情、经停站、经路高亮分别独立接口，方便前端并发加载。
- 后续数据规模变大后，将 GeoJSON 图层升级为矢量瓦片。

## 前端计划

### 1. 地图工作台

- 使用 MapLibre GL 初始化地图。
- 使用 OSM 标准地图作为基础底图，默认叠加 OpenRailwayMap 铁路路网瓦片。
- 添加铁路线路、车站、选中车次经路、经停站四类图层。
- 点击车站显示名称和基础信息。

### 2. 搜索与展示

- 使用 Element Plus 输入框和按钮做车次搜索。
- 使用 Pinia 保存搜索词、候选车次、选中车次、经停站和经路 GeoJSON。
- 选择车次后并发加载详情、经停站、经路。
- 经路加载后自动 `fitBounds`。

### 3. 交互增强

- 搜索结果支持键盘选择。
- 经停站点击后地图定位到车站。
- 线路高亮支持 hover 显示线路片段属性。
- 车站图层按 zoom 调整可见密度。

### 4. 性能

- 地图图层按 bbox 请求。
- 搜索输入使用 debounce。
- 站点多时使用聚合或矢量瓦片。
- 路线 GeoJSON 做前端缓存，避免重复加载。

## 里程碑

| 阶段 | 内容 | 验收标准 |
| --- | --- | --- |
| V1.0 骨架 | 项目结构、Compose、基础 API、地图页面 | `docker compose up --build` 后可访问前后端 |
| V1.1 数据导入 | OSM/OpenRailwayMap/12306 数据导入脚本 | 可导入指定区域和样例车次 |
| V1.2 经路匹配 | 站序到铁路网络的路径匹配 | 样例车次路线可稳定高亮 |
| V1.3 搜索优化 | Redis 缓存、trigram 排序、别名库 | 车次和站点模糊搜索可用 |
| V1.4 地图优化 | bbox 查询、图层样式、交互细节 | 地图操作流畅，站点/线路清晰 |

## 测试计划

- 后端：
  - API 单元测试：健康检查、搜索、详情、经停站、经路。
  - 数据导入测试：重复导入幂等、站名匹配、异常数据处理。
  - 空间查询测试：bbox、路线 GeoJSON、站点坐标。
- 前端：
  - TypeScript 类型检查。
  - 组件测试：搜索面板、地图图层更新。
  - E2E：搜索车次、选择结果、经停站展示、地图高亮。
