from fastapi import WebSocket
import logging

active_connections = []
logger = logging.getLogger(__name__)

async def connect(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    await websocket.send_json({"type": "connection", "message": "Connected"})
    logger.info(f"WebSocket connected ({len(active_connections)} active)")

async def disconnect(websocket: WebSocket):
    active_connections.remove(websocket)
    logger.info(f"WebSocket disconnected ({len(active_connections)} active)")

async def broadcast_to_websockets(message):
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_json(message)
        except:
            disconnected.append(ws)
    for ws in disconnected:
        await disconnect(ws)
