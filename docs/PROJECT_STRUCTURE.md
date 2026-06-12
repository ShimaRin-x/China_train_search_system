# 完整项目目录结构

```text
China_train_search_system/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── health.py
│   │   │       │   ├── map_layers.py
│   │   │       │   ├── stations.py
│   │   │       │   └── trains.py
│   │   │       └── router.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── cli/
│   │   │   └── import_cr12306.py
│   │   ├── data/
│   │   │   └── sample.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   │   ├── ingest.py
│   │   │   ├── railway.py
│   │   │   ├── station.py
│   │   │   └── train.py
│   │   ├── schemas/
│   │   │   ├── geojson.py
│   │   │   ├── station.py
│   │   │   └── train.py
│   │   ├── services/
│   │   │   ├── cache.py
│   │   │   ├── cr12306_importer.py
│   │   │   ├── importers.py
│   │   │   ├── railways.py
│   │   │   ├── stations.py
│   │   │   └── trains.py
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   │   ├── http.ts
│   │   │   ├── map.ts
│   │   │   └── trains.ts
│   │   ├── assets/
│   │   │   └── main.css
│   │   ├── components/
│   │   │   ├── RailwayMap.vue
│   │   │   └── TrainSearchPanel.vue
│   │   ├── router/
│   │   │   └── index.ts
│   │   ├── stores/
│   │   │   └── train.ts
│   │   ├── types/
│   │   │   ├── geojson.ts
│   │   │   └── train.ts
│   │   ├── views/
│   │   │   └── MapWorkspace.vue
│   │   ├── App.vue
│   │   └── main.ts
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── infra/
│   ├── nginx/
│   │   └── default.conf
│   └── postgres/
│       └── init.sql
├── docs/
│   ├── API.md
│   ├── DEVELOPMENT_PLAN.md
│   ├── DOCKER_COMPOSE.md
│   ├── ERD.md
│   └── PROJECT_STRUCTURE.md
├── scripts/
│   └── import_cr12306.ps1
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## 模块职责

- `backend/app/api/v1`：V1 REST API 路由。
- `backend/app/cli`：离线导入和维护命令。
- `backend/app/models`：SQLAlchemy ORM 与 PostGIS 空间字段。
- `backend/app/services`：查询、模糊搜索、GeoJSON 组装与数据导入服务。
- `frontend/src/components/RailwayMap.vue`：MapLibre GL 地图、车站图层、铁路图层、经路高亮。
- `frontend/src/components/TrainSearchPanel.vue`：车次模糊搜索和经停站展示。
- `docs`：ER 图、API、Compose、开发计划等交付文档。
