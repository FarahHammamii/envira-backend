from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "🌿 Envira Cloud API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "latest_data": "/latest/esp32-001",
            "telemetry": "/telemetry/esp32-001",
            "devices": "/devices",
            "websocket": "/ws",
            "debug": "/debug"
        }
    }
