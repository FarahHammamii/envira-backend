from bson import ObjectId
from fastapi import HTTPException
from typing import Union

def to_objectid(id_value: Union[str, ObjectId]) -> ObjectId:
    """Convert string to ObjectId, handle errors"""
    if isinstance(id_value, ObjectId):
        return id_value
    try:
        return ObjectId(id_value)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

def to_string(id_value: Union[str, ObjectId]) -> str:
    """Convert ObjectId to string"""
    if isinstance(id_value, str):
        return id_value
    return str(id_value)


def normalize_sensors(sensors: dict) -> dict:
    """Normalize stored sensor payloads to a consistent processed format.

    Accepts either already-processed sensors (temperature, humidity, air_quality, light, sound)
    or legacy/raw formats coming from devices (mq135, dht, ldr, sound_rms).
    Returns a dict with keys: temperature, humidity, air_quality, light, sound
    """
    if not sensors:
        return {
            "temperature": None,
            "humidity": None,
            "air_quality": None,
            "light": None,
            "sound": None
        }

    # If already processed
    if any(k in sensors for k in ("temperature", "humidity", "air_quality", "light", "sound")):
        return {
            "temperature": sensors.get("temperature"),
            "humidity": sensors.get("humidity"),
            "air_quality": sensors.get("air_quality"),
            "light": sensors.get("light"),
            "sound": sensors.get("sound")
        }

    # Legacy/raw keys
    mq135 = sensors.get("mq135")
    dht = sensors.get("dht", {}) or {}
    ldr = sensors.get("ldr")
    sound_rms = sensors.get("sound_rms")

    # Convert mq135 -> air_quality (0-100)
    try:
        mq135_val = float(mq135) if mq135 is not None else None
    except Exception:
        mq135_val = None

    air_quality = None
    if mq135_val is not None:
        air_quality = max(0, min(100, 100 - (mq135_val / 20)))

    # DHT
    try:
        temperature = float(dht.get("t")) if dht.get("t") is not None else None
    except Exception:
        temperature = None
    try:
        humidity = float(dht.get("h")) if dht.get("h") is not None else None
    except Exception:
        humidity = None

    # LDR -> lux approximation
    try:
        ldr_val = float(ldr) if ldr is not None else None
    except Exception:
        ldr_val = None

    light = None
    if ldr_val is not None:
        light = max(0, min(1000, (ldr_val / 4.096)))

    # sound_rms -> approximate dB (clamped)
    try:
        sound_val = float(sound_rms) if sound_rms is not None else None
    except Exception:
        sound_val = None

    sound = None
    if sound_val is not None:
        sound = max(0, min(100, sound_val / 10))

    return {
        "temperature": temperature,
        "humidity": humidity,
        "air_quality": air_quality,
        "light": light,
        "sound": sound
    }