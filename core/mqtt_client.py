import json
import ssl
import asyncio
import logging
import paho.mqtt.client as mqtt
from datetime import datetime
from .database import db
from .websocket_manager import broadcast_to_websockets
from .config import MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD

logger = logging.getLogger(__name__)
mqtt_client = None

def compute_ieq_score(sensors_dict):
    """
    Calculate IEQ score from sensor data.
    Input sensors_dict should have: temperature, humidity, air_quality, light, sound
    """
    try:
        # Get sensor values with safe defaults
        temperature = sensors_dict.get("temperature", 22)
        humidity = sensors_dict.get("humidity", 50)
        air_quality = sensors_dict.get("air_quality", 70)
        light = sensors_dict.get("light", 400)
        sound = sensors_dict.get("sound", 40)
        
        # Calculate individual component scores (0-100)
        # Temperature: ideal 20-24°C
        temp_diff = abs(temperature - 22)
        temp_score = max(0, 100 - temp_diff * 5)
        
        # Humidity: ideal 40-60%
        humidity_diff = abs(humidity - 50)
        humidity_score = max(0, 100 - humidity_diff * 2)
        
        # Air quality: higher is better (0-100)
        aq_score = air_quality
        
        # Light: ideal 300-600 lux
        if 300 <= light <= 600:
            light_score = 100
        elif light < 300:
            light_score = (light / 300) * 100
        else:
            light_score = max(0, 100 - (light - 600) / 10)
        
        # Sound: ideal 0-40 dB
        sound_score = max(0, 100 - sound)
        
        # Weighted average: AQ=40%, Temp=30%, Light=20%, Sound=10%
        ieq_score = round(
            aq_score * 0.4 + temp_score * 0.3 + light_score * 0.2 + sound_score * 0.1,
            1
        )
        
        return max(0, min(100, ieq_score))  # Clamp between 0-100
    except Exception as e:
        logger.error(f"❌ Error calculating IEQ score: {e}")
        return 50  # Return neutral score on error

def process_telemetry_sync(payload):
    """
    Process telemetry data from MQTT payload.
    Expected payload format:
    {
        "device_id": "esp32-001",
        "site_id": "home",
        "ts": 4266,
        "sensors": {
            "mq135": 1115,           # Air quality sensor
            "dht": {"t": 24.2, "h": 54.3},  # Temperature and humidity
            "ldr": 901,              # Light sensor
            "sound_rms": 1050.008    # Sound sensor
        }
    }
    """
    try:
        device_id = payload.get("device_id")
        site_id = payload.get("site_id")
        ts = payload.get("ts", 0)  # Timestamp in milliseconds
        
        # Extract sensor values from raw MQTT data
        raw_sensors = payload.get("sensors", {})
        
        # Convert air quality (mq135 is raw value, convert to 0-100 scale)
        mq135_raw = raw_sensors.get("mq135", 0)
        # Assuming mq135 range is 0-2000, convert to air quality 0-100
        air_quality = max(0, min(100, 100 - (mq135_raw / 20)))
        
        # Extract temperature and humidity from DHT sensor
        dht_data = raw_sensors.get("dht", {})
        temperature = float(dht_data.get("t", 22))
        humidity = float(dht_data.get("h", 50))
        
        # Extract light value (ldr raw value, normalize to 0-100)
        ldr_raw = raw_sensors.get("ldr", 0)
        # Assuming ldr range is 0-4096, convert to 0-1000 lux equivalent
        light = max(0, min(1000, (ldr_raw / 4.096)))
        
        # Extract sound level (normalize to 0-100 dB equivalent)
        sound_rms = float(raw_sensors.get("sound_rms", 0))
        # Assuming sound_rms is already in useful units, clamp to 0-100
        sound = max(0, min(100, sound_rms / 10))
        
        # Calculate IEQ score with processed sensor values
        processed_sensors = {
            "temperature": temperature,
            "humidity": humidity,
            "air_quality": air_quality,
            "light": light,
            "sound": sound
        }
        
        ieq_score = compute_ieq_score(processed_sensors)
        
        # Determine timestamp - use ts if available, otherwise use current time
        if ts > 0:
            # ts is usually in milliseconds from device
            try:
                record_timestamp = datetime.fromtimestamp(ts / 1000)
            except (ValueError, OSError):
                # If conversion fails, use current time
                record_timestamp = datetime.utcnow()
        else:
            record_timestamp = datetime.utcnow()
        
        # Create telemetry document
        document = {
            "device_id": device_id,
            "site_id": site_id,
            "ts": ts,
            "sensors": processed_sensors,  # Processed sensor data
            "raw_sensors": raw_sensors,    # Keep raw data for debugging
            "ieq_score": ieq_score,
            "processed_at": datetime.utcnow(),
            "timestamp": record_timestamp
        }
        
        # Insert into database
        result = db.telemetry_collection.insert_one(document)
        logger.info(f"✅ Stored telemetry for {device_id}: IEQ={ieq_score}, ID={result.inserted_id}")
        
        # Broadcast to WebSocket clients
        asyncio.create_task(broadcast_to_websockets({
            "type": "telemetry",
            "data": {
                "device_id": device_id,
                "sensors": processed_sensors,
                "ieq_score": ieq_score,
                "timestamp": document["processed_at"].isoformat()
            }
        }))
        
    except Exception as e:
        logger.error(f"❌ Error processing telemetry: {e}", exc_info=True)

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
