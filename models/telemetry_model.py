from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional

class Sensors(BaseModel):
    """Processed sensor values"""
    temperature: Optional[float] = None  # Celsius
    humidity: Optional[float] = None  # Percentage (0-100)
    air_quality: Optional[float] = None  # Air quality index (0-100)
    light: Optional[float] = None  # Lux (0-1000)
    sound: Optional[float] = None  # dB equivalent (0-100)

class RawSensors(BaseModel):
    """Raw MQTT sensor values"""
    mq135: Optional[int] = None  # Air quality raw value
    dht: Optional[Dict[str, float]] = None  # {t: temperature, h: humidity}
    ldr: Optional[int] = None  # Light raw value
    sound_rms: Optional[float] = None  # Sound raw value

class Telemetry(BaseModel):
    """Complete telemetry data model"""
    device_id: str
    site_id: str
    ts: int = 0  # Timestamp in milliseconds from device
    sensors: Sensors
    raw_sensors: Optional[RawSensors] = None
    ieq_score: float = Field(default=50.0, ge=0, le=100)  # Indoor Environmental Quality Score
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class TelemetryResponse(BaseModel):
    """Response model for telemetry queries"""
    device_id: str
    site_id: str
    sensors: Sensors
    ieq_score: float
    timestamp: datetime
    environmental_score: float = Field(alias="ieq_score")

