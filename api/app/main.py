from fastapi import FastAPI

from api.main import api_router
from app.mcp.server import mcp_app

app = FastAPI(title="Dispatch", lifespan=mcp_app.lifespan)

app.include_router(api_router)

app.mount("/agent", mcp_app)