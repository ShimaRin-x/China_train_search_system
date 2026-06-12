from fastapi import APIRouter

from app.api.v1.endpoints import health, map_layers, stations, trains

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(map_layers.router, prefix="/map", tags=["map"])
api_router.include_router(stations.router, prefix="/stations", tags=["stations"])
api_router.include_router(trains.router, prefix="/trains", tags=["trains"])
