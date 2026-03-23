from fastapi import APIRouter
from app.api.v1.endpoints import auth, sensors, devices, rules, alerts, dashboard, rooms

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["Rooms"])
api_router.include_router(sensors.router, prefix="/sensors", tags=["Sensors"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(rules.router, prefix="/rules", tags=["Rules"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
