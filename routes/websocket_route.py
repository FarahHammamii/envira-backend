from fastapi import APIRouter, WebSocket

import logging

logger = logging.getLogger(__name__)
active_connections: list[WebSocket] = []

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"🔌 New WebSocket connection. Total: {len(active_connections)}")

    try:
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to Envira Real-time API",
            "connected_devices": len(active_connections)
        })
        while True:
            await websocket.receive_text()

    except Exception as e:
        logger.warning(f"WebSocket disconnected: {e}")
    finally:
        active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket disconnected. Remaining: {len(active_connections)}")
