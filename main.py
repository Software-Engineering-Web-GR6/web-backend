from fastapi import FastAPI, WebSocket
from fastapi.responses import RedirectResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import init_db, AsyncSessionLocal
from app.db.seed import seed_data
from app.websocket.manager import ws_manager

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event() -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_data(session)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        await ws_manager.disconnect(websocket)