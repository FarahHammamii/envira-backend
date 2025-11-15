from fastapi import APIRouter
from datetime import datetime
from core.mqtt_client import mqtt_client, MQTT_BROKER, MQTT_PORT
from core.database import db
from core.websocket_manager import active_connections
router = APIRouter(prefix="/health")

@router.get("")
async def health_check():
    """Health check endpoint"""
    mqtt_status = "connected" if mqtt_client and mqtt_client.is_connected() else "disconnected"
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "mqtt_broker": mqtt_status,
        "database": "connected" if db.client else "disconnected",
        "active_websockets": len(active_connections),
        "mqtt_broker_url": f"{MQTT_BROKER}:{MQTT_PORT}"
    }

@router.get("/debug")
async def debug():
    """Debug endpoint to check environment variables"""
    return {
        "mqtt_broker": MQTT_BROKER,
        "mqtt_port": MQTT_PORT,
        "mongodb_connected": db.client is not None,
        "active_mqtt_connection": mqtt_client.is_connected() if mqtt_client else False
    }
