from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import paho.mqtt.client as mqtt
import os
import json
import asyncio
from datetime import datetime
import logging
import ssl

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Envira Cloud API", version="1.0.0")

# CORS - allow all origins for mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://farahhammami8_db_user:2003@envira-cluster.fuobdmy.mongodb.net/envira?retryWrites=true&w=majority")
client = MongoClient(MONGODB_URL)
db = client.envira

# Collections
telemetry_collection = db.telemetry
devices_collection = db.devices

# Initialize devices collection with your ESP32
devices_collection.update_one(
    {"device_id": "esp32-001"},
    {"$set": {
        "device_id": "esp32-001",
        "site_id": "home",
        "name": "Main Sensor",
        "created_at": datetime.utcnow(),
        "sensors": ["temperature", "humidity", "air_quality", "light", "sound"]
    }},
    upsert=True
)

# MQTT Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "y2b6df88.ala.eu-central-1.emqxsl.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))  # Changed to 8883 for TLS
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "farah")  # Add default
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "2003")   # Add default

# WebSocket connections for real-time updates
active_connections = []
mqtt_client = None

@app.on_event("startup")
async def startup_event():
    """Initialize MQTT connection when app starts"""
    logger.info("Starting Envira Backend...")
    logger.info(f"🔧 MQTT Configuration - Broker: {MQTT_BROKER}:{MQTT_PORT}, Username: '{MQTT_USERNAME}'")
    asyncio.create_task(connect_mqtt())

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown"""
    if mqtt_client:
        mqtt_client.disconnect()
    logger.info("Envira Backend stopped")

async def connect_mqtt():
    """Connect to MQTT broker and subscribe to topics"""
    global mqtt_client
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info("✅ Connected to MQTT Broker")
            client.subscribe("envira/+/+/telemetry")
            logger.info("📡 Subscribed to topic: envira/+/+/telemetry")
        else:
            logger.error(f"❌ Failed to connect to MQTT, return code: {rc}")
            # Add specific error messages
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier", 
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            logger.error(f"❌ MQTT Error: {error_messages.get(rc, 'Unknown error')}")
            logger.error(f"🔧 Debug - Username used: '{MQTT_USERNAME}', Broker: {MQTT_BROKER}:{MQTT_PORT}")

    def on_message(client, userdata, msg):
        try:
            logger.info(f"📨 Received MQTT message from topic: {msg.topic}")
            payload = json.loads(msg.payload.decode())
            
            # Process synchronously instead of using asyncio
            process_telemetry_sync(payload)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
        except Exception as e:
            logger.error(f"❌ MQTT processing error: {e}")

    # Create MQTT client
    mqtt_client = mqtt.Client()
    
    # Enable TLS with better configuration
    try:
        mqtt_client.tls_set(cert_reqs=ssl.CERT_NONE)  # Don't verify certificate
        mqtt_client.tls_insecure_set(True)  # Allow insecure TLS
        logger.info("🔒 TLS configured (insecure mode - no certificate verification)")
    except Exception as e:
        logger.error(f"❌ TLS configuration error: {e}")
        return
    
    # Debug credentials
    logger.info(f"🔑 Using MQTT credentials - Username: '{MQTT_USERNAME}', Broker: {MQTT_BROKER}:{MQTT_PORT}")
    
    if MQTT_USERNAME and MQTT_PASSWORD:
        mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        logger.info("🔑 MQTT credentials set successfully")
    else:
        logger.error("❌ No MQTT credentials provided in environment variables!")
        logger.error(f"   Username: '{MQTT_USERNAME}', Password: {'***' if MQTT_PASSWORD else 'None'}")
        return
    
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    try:
        logger.info(f"🔗 Attempting MQTT connection to {MQTT_BROKER}:{MQTT_PORT}")
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        logger.info("🔗 MQTT connection attempt completed")
    except Exception as e:
        logger.error(f"❌ MQTT connection exception: {e}")

def process_telemetry_sync(data):
    """Process incoming sensor data synchronously"""
    try:
        logger.info(f"🔧 Processing telemetry from device: {data.get('device_id')}")
        
        # Calculate IEQ score
        ieq_score = compute_ieq_score(data)
        
        # Create document for MongoDB
        document = {
            **data,
            "processed_at": datetime.utcnow(),
            "ieq_score": ieq_score,
            "timestamp": datetime.fromtimestamp(data["ts"] / 1000) if data.get("ts") else datetime.utcnow()
        }
        
        # Store in MongoDB
        result = telemetry_collection.insert_one(document)
        logger.info(f"💾 Stored in MongoDB with ID: {result.inserted_id}")
        
        # Broadcast to WebSocket clients
        asyncio.create_task(broadcast_to_websockets({
            "type": "telemetry",
            "data": document
        }))
        
    except Exception as e:
        logger.error(f"❌ Error processing telemetry: {e}")

def compute_ieq_score(data):
    """Calculate Indoor Environmental Quality score"""
    try:
        sensors = data["sensors"]
        
        # Air Quality Score (MQ135 - lower is better)
        mq135_value = sensors.get("mq135", 0)
        aq_score = max(0, 100 - (mq135_value / 10))
        
        # Thermal Comfort Score (DHT22)
        temperature = sensors.get("dht", {}).get("t", 22)
        thermal_score = 100 - abs(22 - temperature) * 5  # Optimal 22°C
        
        # Light Quality Score (LDR - higher is better)
        light_value = sensors.get("ldr", 0)
        light_score = min(100, light_value / 10)
        
        # Acoustic Comfort Score (Sound - lower is better)
        sound_value = sensors.get("sound_rms", 0)
        sound_score = max(0, 100 - sound_value * 5)
        
        # Composite IEQ Score (weighted average)
        ieq_score = (
            aq_score * 0.4 +      # Air quality 40%
            thermal_score * 0.3 + # Thermal 30%
            light_score * 0.2 +   # Light 20%
            sound_score * 0.1     # Sound 10%
        )
        
        logger.info(f"📊 IEQ Score calculated: {ieq_score:.1f}")
        return round(ieq_score, 1)
        
    except Exception as e:
        logger.error(f"❌ Error calculating IEQ score: {e}")
        return 0

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"🔌 New WebSocket connection. Total: {len(active_connections)}")
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to Envira Real-time API",
            "connected_devices": len(active_connections)
        })
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # You can handle incoming messages here if needed
            
    except Exception as e:
        logger.info(f"🔌 WebSocket disconnected: {e}")
    finally:
        active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket disconnected. Remaining: {len(active_connections)}")

async def broadcast_to_websockets(message):
    """Broadcast message to all connected WebSocket clients"""
    if not active_connections:
        return
        
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            disconnected.append(connection)
    
    # Remove disconnected clients
    for connection in disconnected:
        active_connections.remove(connection)

# REST API Endpoints
@app.get("/")
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    mqtt_status = "connected" if mqtt_client and mqtt_client.is_connected() else "disconnected"
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "mqtt_broker": mqtt_status,
        "database": "connected",
        "active_websockets": len(active_connections),
        "mqtt_broker_url": f"{MQTT_BROKER}:{MQTT_PORT}"
    }

@app.get("/debug")
async def debug():
    """Debug endpoint to check environment variables"""
    return {
        "mqtt_broker": MQTT_BROKER,
        "mqtt_port": MQTT_PORT,
        "mqtt_username": MQTT_USERNAME,
        "mqtt_password_length": len(MQTT_PASSWORD) if MQTT_PASSWORD else 0,
        "mongodb_connected": client is not None,
        "active_mqtt_connection": mqtt_client.is_connected() if mqtt_client else False
    }

@app.get("/telemetry/{device_id}")
async def get_telemetry(device_id: str, limit: int = 100, hours: int = 24):
    """Get historical telemetry data for a device"""
    try:
        # Calculate time filter
        time_threshold = datetime.utcnow().timestamp() - (hours * 3600)
        
        telemetry = list(telemetry_collection.find(
            {
                "device_id": device_id,
                "ts": {"$gte": time_threshold * 1000}  # Convert to milliseconds
            },
            {"_id": 0}
        ).sort("ts", -1).limit(limit))
        
        return {
            "device_id": device_id,
            "count": len(telemetry),
            "data": telemetry
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching telemetry: {e}")
        raise HTTPException(status_code=500, detail="Error fetching data")

@app.get("/latest/{device_id}")
async def get_latest_reading(device_id: str):
    """Get the latest reading from a device"""
    try:
        latest = telemetry_collection.find_one(
            {"device_id": device_id},
            {"_id": 0},
            sort=[("ts", -1)]
        )
        
        if not latest:
            raise HTTPException(status_code=404, detail="No data found for device")
        
        return latest
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching latest data: {e}")
        raise HTTPException(status_code=500, detail="Error fetching data")

@app.get("/devices")
async def get_devices():
    """Get all registered devices"""
    try:
        devices = list(devices_collection.find({}, {"_id": 0}))
        return {
            "count": len(devices),
            "devices": devices
        }
    except Exception as e:
        logger.error(f"❌ Error fetching devices: {e}")
        raise HTTPException(status_code=500, detail="Error fetching devices")

@app.get("/stats/{device_id}")
async def get_device_stats(device_id: str, hours: int = 24):
    """Get statistics for a device"""
    try:
        time_threshold = datetime.utcnow().timestamp() - (hours * 3600)
        
        pipeline = [
            {"$match": {"device_id": device_id, "ts": {"$gte": time_threshold * 1000}}},
            {"$group": {
                "_id": "$device_id",
                "avg_ieq": {"$avg": "$ieq_score"},
                "max_ieq": {"$max": "$ieq_score"},
                "min_ieq": {"$min": "$ieq_score"},
                "readings_count": {"$sum": 1},
                "latest_reading": {"$last": "$$ROOT"}
            }}
        ]
        
        stats = list(telemetry_collection.aggregate(pipeline))
        
        if not stats:
            raise HTTPException(status_code=404, detail="No statistics available")
        
        return stats[0]
        
    except Exception as e:
        logger.error(f"❌ Error calculating stats: {e}")
        raise HTTPException(status_code=500, detail="Error calculating statistics")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")