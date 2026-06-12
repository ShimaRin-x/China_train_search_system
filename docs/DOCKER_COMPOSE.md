# Docker Compose 方案

## 服务组成

| 服务 | 镜像/构建 | 端口 | 职责 |
| --- | --- | --- | --- |
| `postgres` | `postgis/postgis:16-3.4` | `5432` | PostgreSQL + PostGIS，存储站点、线路、车次和空间几何 |
| `redis` | `redis:7-alpine` | `6379` | 缓存搜索结果、地图 GeoJSON 切片结果、导入任务状态 |
| `backend` | `./backend` | `8000` | FastAPI + SQLAlchemy API 服务 |
| `frontend` | `./frontend` | `5173` | Vue3 + Vite 开发服务 |

## 启动流程

```bash
cp .env.example .env # 可选：不复制时使用 docker-compose.yml 中的默认值
docker compose up --build
```

## 健康检查

- PostgreSQL 使用 `pg_isready`。
- Redis 使用 `redis-cli ping`。
- 后端可访问 `GET /api/v1/health`。

## 持久化

- `postgres-data`：数据库数据卷。
- `redis-data`：Redis 数据卷。
- `./data:/app/data`：后端导入命令的本地 JSON 缓存目录，例如 cr-12306 release 资产。

## 车次数据导入

V1 使用 `cr-12306-train-info` release JSON，不直接抓取 12306 接口。启动 `postgres` 和 `backend` 后可执行：

```bash
docker compose exec backend python -m app.cli.import_cr12306 --date 20260617 --download
```

或在 Windows PowerShell 下执行仓库脚本：

```powershell
.\scripts\import_cr12306.ps1 -Date 20260617 -Download
```

如果已下载本地详情文件：

```powershell
.\scripts\import_cr12306.ps1 -Date 20260617 -DetailFile .\train_detail_20260617.json
```

默认会下载 `train_list_20260617.json` 和 `train_detail_20260617.json` 到 `/app/data/cr12306`，并写入 `train_services`、`train_stops`、`stations`。重复执行会更新同一天同一计划车号的数据并重建经停站。

## 生产部署建议

- 前端通过 `npm run build` 生成静态资源，使用 Nginx 托管。
- 后端使用 `uvicorn app.main:app --workers 4` 或 Gunicorn + Uvicorn worker。
- PostgreSQL 独立部署并启用定期备份。
- Redis 独立部署，开启内存上限和淘汰策略。
- 大规模铁路图层建议预生成矢量瓦片或按 bbox + zoom 做缓存。
