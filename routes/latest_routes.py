from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from core.database import db
from core.auth import get_current_user
from core.utils import to_string, normalize_sensors
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/latest", tags=["latest-data"])

class SensorReading(BaseModel):
    """Current sensor values from device."""
    temperature: Optional[float] = Field(None, description="Temperature in Celsius (-40 to 85)")
    humidity: Optional[float] = Field(None, description="Humidity percentage (0-100)")
    air_quality: Optional[float] = Field(None, description="Air quality score (0-100, 0=clean)")
    light: Optional[float] = Field(None, description="Light level in lux (0-1000)")
    sound: Optional[float] = Field(None, description="Sound level in dB (30-100)")

class LatestDataResponse(BaseModel):
    """Latest telemetry reading from a device."""
    device_id: str = Field(..., description="Device identifier")
    site_id: str = Field(..., description="Physical location")
    timestamp: datetime = Field(..., description="When data was processed")
    ts: Optional[datetime] = Field(None, description="Alternate timestamp field")
    sensors: SensorReading = Field(..., description="Current sensor readings")
    ieq_score: float = Field(..., description="Indoor Environmental Quality Score (0-100)")
    environmental_score: float = Field(..., description="Alias for ieq_score (compatibility)")

class TrendData(BaseModel):
    """Trend information for a sensor."""
    value: float = Field(..., description="Current sensor value")
    trend: str = Field(..., description="Direction: rising/falling/stable")
    change: float = Field(..., description="Change from previous reading")

class DeviceSummaryResponse(BaseModel):
    """Summary of device status with trend analysis."""
    device_id: str = Field(..., description="Device identifier")
    site_id: str = Field(..., description="Physical location")
    current_time: datetime = Field(..., description="Current server time")
    last_update: datetime = Field(..., description="When device last reported data")
    ieq_score: float = Field(..., description="Current Indoor Environmental Quality Score")
    current_sensors: SensorReading = Field(..., description="Current sensor readings")
    trends: Dict[str, TrendData] = Field(..., description="Trends for monitored sensors")
    reading_count: int = Field(..., description="Number of recent readings analyzed")

@router.get("/{device_id}", response_model=LatestDataResponse)
async def get_latest_data(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the most recent telemetry data for a device.
    
    Returns the latest sensor readings and Indoor Environmental Quality (IEQ) score.
    Sensor data is automatically normalized from raw MQTT format to processed values.
    
    **Required:** Bearer token in Authorization header
    
    **Parameters:**
    - device_id: The device to query (e.g., esp32-001)
    
    **Returns:**
    - device_id: Device identifier
    - site_id: Physical location of device
    - timestamp: When data was processed (processed_at)
    - ts: Optional alternate timestamp
    - sensors: Current sensor readings:
      - temperature: -40 to 85°C
      - humidity: 0-100%
      - air_quality: 0-100 (0=clean, 100=poor)
      - light: 0-1000 lux
      - sound: 30-100 dB
    - ieq_score: IEQ Score (0-100)
      - Formula: 40% air_quality + 30% temperature + 20% light + 10% sound
      - 75+: Excellent | 50-74: Good | 25-49: Fair | <25: Poor
    - environmental_score: Alias for ieq_score
    
    **Sensor Data Format:**
    Internally, devices may report data in different formats (raw MQTT or processed).
    This endpoint automatically normalizes both formats to ensure consistent output.
    
    **Example Usage:**
    ```
    GET /latest/esp32-001
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Expected Response:**
    ```json
    {
      "device_id": "esp32-001",
      "site_id": "office_main",
      "timestamp": "2024-01-15T14:30:00",
      "ts": "2024-01-15T14:29:55",
      "sensors": {
        "temperature": 22.5,
        "humidity": 45.2,
        "air_quality": 35,
        "light": 450,
        "sound": 62
      },
      "ieq_score": 62.5,
      "environmental_score": 62.5
    }
    ```
    
    **Status Codes:**
    - 200: Latest data retrieved successfully
    - 401: Invalid or missing authentication token
    - 404: No data found for device
    - 500: Server error
    """
    try:
        # Get the most recent telemetry data
        latest_data = db.telemetry_collection.find_one(
            {"device_id": device_id},
            sort=[("processed_at", -1)]
        )
        
        if not latest_data:
            raise HTTPException(status_code=404, detail="No data found for device")
        
        # Extract and format sensor data, support both processed and raw formats
        raw_sensors = latest_data.get("sensors", {})
        processed = normalize_sensors(raw_sensors)
        ieq_score = latest_data.get("ieq_score", 0)

        return {
            "device_id": device_id,
            "site_id": latest_data.get("site_id"),
            "timestamp": latest_data.get("processed_at"),
            "ts": latest_data.get("ts"),
            "sensors": processed,
            "ieq_score": ieq_score,
            "environmental_score": ieq_score  # Alias for compatibility
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching latest data: {e}")
        raise HTTPException(status_code=500, detail="Error fetching latest data")

@router.get("/device/{device_id}/summary", response_model=DeviceSummaryResponse)
async def get_device_summary(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get device summary with trend analysis.
    
    Returns current device status along with trend analysis for key sensors.
    Trends are calculated by comparing latest reading with previous readings.
    
    **Required:** Bearer token in Authorization header
    
    **Parameters:**
    - device_id: The device to query (e.g., esp32-001)
    
    **Returns:**
    - device_id: Device identifier
    - site_id: Physical location
    - current_time: Current server time
    - last_update: When device last reported data
    - ieq_score: Current IEQ Score (0-100)
    - current_sensors: Latest sensor readings
    - trends: Trend data for monitored sensors:
      - value: Current sensor reading
      - trend: Direction (rising/falling/stable)
      - change: Numerical change from previous reading
    - reading_count: Number of recent readings used for trend calculation (typically 10)
    
    **Trend Analysis:**
    Trends compare the latest reading with the previous reading to identify patterns.
    - rising: Sensor value increased
    - falling: Sensor value decreased
    - stable: Sensor value unchanged
    
    **Example Usage:**
    ```
    GET /latest/device/esp32-001/summary
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Expected Response:**
    ```json
    {
      "device_id": "esp32-001",
      "site_id": "office_main",
      "current_time": "2024-01-15T14:35:00",
      "last_update": "2024-01-15T14:30:00",
      "ieq_score": 62.5,
      "current_sensors": {
        "temperature": 22.5,
        "humidity": 45.2,
        "air_quality": 35,
        "light": 450,
        "sound": 62
      },
      "trends": {
        "temperature": {
          "value": 22.5,
          "trend": "rising",
          "change": 0.3
        }
      },
      "reading_count": 10
    }
    ```
    
    **Status Codes:**
    - 200: Summary retrieved successfully
    - 401: Invalid or missing authentication token
    - 404: No data found for device
    - 500: Server error
    """
    try:
        # Get latest data
        latest_data = db.telemetry_collection.find_one(
            {"device_id": device_id},
            sort=[("processed_at", -1)]
        )
        
        if not latest_data:
            raise HTTPException(status_code=404, detail="No data found for device")
        
        # Get previous readings for trend analysis
        previous_readings = list(db.telemetry_collection.find(
            {"device_id": device_id},
            sort=[("processed_at", -1)],
            limit=10
        ))
        
        sensor_data = latest_data.get("sensors", {})
        ieq_score = latest_data.get("ieq_score", 0)
        
        # Calculate trends
        trends = {}
        if len(previous_readings) > 1:
            latest_temp = sensor_data.get("temperature")
            prev_temp = previous_readings[1].get("sensors", {}).get("temperature")
            
            if latest_temp is not None and prev_temp is not None:
                temp_trend = "rising" if latest_temp > prev_temp else "falling" if latest_temp < prev_temp else "stable"
                trends["temperature"] = {
                    "value": latest_temp,
                    "trend": temp_trend,
                    "change": round(latest_temp - prev_temp, 2)
                }
        
        return {
            "device_id": device_id,
            "site_id": latest_data.get("site_id"),
            "current_time": datetime.utcnow(),
            "last_update": latest_data.get("processed_at"),
            "ieq_score": ieq_score,
            "current_sensors": {
                "temperature": sensor_data.get("temperature"),
                "humidity": sensor_data.get("humidity"),
                "air_quality": sensor_data.get("air_quality"),
                "light": sensor_data.get("light"),
                "sound": sensor_data.get("sound")
            },
            "trends": trends,
            "reading_count": len(previous_readings)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching device summary: {e}")
        raise HTTPException(status_code=500, detail="Error fetching device summary")