from fastapi import APIRouter

from api.routes import topology, chat, devices

api_router = APIRouter(prefix="/v1")

api_router.include_router(topology.router)
api_router.include_router(chat.router)
api_router.include_router(devices.router)