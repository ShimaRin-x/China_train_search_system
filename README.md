# 中国铁路车次经路可视化平台

当前版本：V1.0.2

基于 Vue3 + TypeScript + Vite + MapLibre GL + Pinia + Element Plus，以及 FastAPI + PostgreSQL/PostGIS + SQLAlchemy + Redis 的中国铁路车次经路可视化平台。

V1 聚焦五件事：

- 铁路底图与线路/站点空间数据承载
- 车站图层展示
- 车次搜索与模糊匹配
- 经停站列表展示
- 车次经路高亮

## 快速启动

1. 如需覆盖默认配置，复制环境变量：

```bash
cp .env.example .env
```

2. 启动开发环境：

```bash
docker compose up --build
```

3. 打开服务：

- 前端：http://localhost:5173
- 后端 OpenAPI：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health

## 导入车次数据

V1 暂不抓取 12306 实时接口，车次搜索和经停站数据使用
[HerbertHe/cr-12306-train-info 的 data-20260617 release](https://github.com/HerbertHe/cr-12306-train-info/releases/tag/data-20260617)。

启动数据库和后端后执行：

```powershell
.\scripts\import_cr12306.ps1 -Date 20260617 -Download
```

也可以直接进入 backend 容器执行：

```bash
docker compose exec backend python -m app.cli.import_cr12306 --date 20260617 --download
```

如果已经手动下载了全量详情文件，例如仓库根目录的 `train_detail_20260617.json`，可以直接导入本地文件：

```powershell
.\scripts\import_cr12306.ps1 -Date 20260617 -DetailFile .\train_detail_20260617.json
```

导入后 `/api/v1/trains/search?q=G101` 会从数据库返回真实车次，`/stops` 会返回经停站和到发时刻。经路高亮仍依赖后续 OSM/OpenRailwayMap 空间匹配写入 `train_route_segments`；尚未匹配到线路时，接口返回空 GeoJSON，不再显示示例线路。

## 目录

- [项目目录结构](docs/PROJECT_STRUCTURE.md)
- [数据库 ER 图](docs/ERD.md)
- [API 设计文档](docs/API.md)
- [前后端开发计划](docs/DEVELOPMENT_PLAN.md)

## 数据源接入策略

- OpenStreetMap 铁路数据：用于 railway line、segment、station 的基础空间几何。
- OpenRailwayMap：用于补充铁路类型、电气化、速度、运营属性等专业铁路标签。
- cr-12306-train-info：用于车次、经停站、到发时刻、站序等客运运行信息。

V1 的核心数据链路是：先导入站点和铁路线网，再导入车次经停站，最后通过空间匹配或人工校验结果生成 `train_route_segments`，供前端高亮显示。

## 更新日志

### V1.0.2 - 2026-06-12

- 精简 README 更新日志内容，移除不面向使用者的仓库管理说明。

### V1.0.1 - 2026-06-12

- 完成 V1 MVP 项目骨架：Vue3 前端、FastAPI 后端、PostgreSQL/PostGIS、Redis、Docker Compose。
- 完成铁路地图前端基础体验：白底铁路地图、铁路类型配色、车站分级显示、搜索侧栏收放、地图图例。
- 接入 `cr-12306-train-info` 本地数据导入，支持车次搜索、模糊搜索、经停站展示。
- 增加 OSM/OpenRailwayMap 车站坐标导入与 12306 站名合并流程，目前已导入局部 OSM 车站坐标。
