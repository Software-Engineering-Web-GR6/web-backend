import logging
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import bootstrap_database
from app.db.seed import seed_data
from app.services.mqtt_service import mqtt_service
from app.websocket.manager import ws_manager
from fastapi.responses import RedirectResponse, Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application bootstrap")
    await bootstrap_database(seed_data)
    mqtt_service.start(asyncio.get_running_loop())
    logger.info("Application bootstrap completed successfully")
    yield
    mqtt_service.stop()


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"message": f"{settings.APP_NAME} is running"}


@app.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)
        raise

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")
