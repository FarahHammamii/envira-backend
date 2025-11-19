from fastapi import APIRouter, HTTPException, Depends, Body, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from core.database import db
from core.auth import get_current_user
from core.utils import to_objectid, to_string
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["devices"])

class RegisterDeviceRequest(BaseModel):
    """Request schema for registering a new device.
    
    **device_id:** Unique identifier for the device (e.g., esp32-001, sensor-office)
    - Must be unique across all registered devices
    - Typical format: [device-type]-[location]-[number]
    
    **name:** Human-readable display name for the device
    - Example: "Office Monitor", "Lobby Sensor", "Server Room"
    
    **site_id:** Physical location or deployment site
    - Default: "home"
    - Used for filtering and organizing devices by location
    
    **sensors:** List of sensor types available on device
    - Default: [temperature, humidity, air_quality, light, sound]
    - Custom sensors can be added for specialized devices
    """
    device_id: str = Field(..., description="Unique device identifier", example="esp32-001")
    name: str = Field(..., description="Human-readable device name", example="Office Monitor")
    site_id: str = Field(default="home", description="Physical location", example="office_main")
    sensors: Optional[List[str]] = Field(
        default=None,
        description="Sensor types on device",
        example=["temperature", "humidity", "air_quality", "light", "sound"]
    )

class UpdateDeviceRequest(BaseModel):
    """Request schema for updating device information.
    
    Any field can be omitted - only provided fields will be updated.
    """
    name: Optional[str] = Field(None, description="New device name", example="Updated Office Monitor")
    site_id: Optional[str] = Field(None, description="New location", example="office_secondary")
    sensors: Optional[List[str]] = Field(None, description="Updated sensor list")

class DeviceResponse(BaseModel):
    """Device metadata response."""
    device_id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Human-readable name")
    site_id: str = Field(..., description="Deployment location")
    sensors: List[str] = Field(..., description="Available sensors on device")
    created_at: Optional[datetime] = Field(None, description="Registration timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

class DeviceListResponse(BaseModel):
    """Response containing list of devices."""
    count: int = Field(..., description="Number of devices returned")
    devices: List[Dict] = Field(..., description="Array of device objects")

class RegisterDeviceResponse(BaseModel):
    """Response after successfully registering device."""
    message: str = Field(..., description="Confirmation message")
    device_id: str = Field(..., description="Registered device ID")
    name: str = Field(..., description="Device name")
    site_id: str = Field(..., description="Device location")
    sensors: List[str] = Field(..., description="Sensors on device")

class AssociateDeviceResponse(BaseModel):
    """Response after bulk device association."""
    message: str = Field(..., description="Confirmation message")
    modified_count: int = Field(..., description="Number of users updated")

class UpdateDeviceResponse(BaseModel):
    """Response after updating device."""
    message: str = Field(..., description="Confirmation message")
    device_id: str = Field(..., description="Updated device ID")
    name: Optional[str] = Field(None, description="Updated name if changed")
    site_id: Optional[str] = Field(None, description="Updated location if changed")

class DeleteDeviceResponse(BaseModel):
    """Response after deleting device."""
    message: str = Field(..., description="Confirmation message")
    device_id: str = Field(..., description="Deleted device ID")

class TelemetryRecord(BaseModel):
    """Single telemetry data point from device."""
    id: str = Field(..., description="Unique record identifier")
    device_id: str = Field(..., description="Device that recorded this data")
    site_id: str = Field(..., description="Physical location")
    sensors: Dict = Field(..., description="Sensor readings: temperature, humidity, air_quality, light, sound")
    ieq_score: Optional[float] = Field(None, description="Indoor Environmental Quality Score (0-100)")
    processed_at: datetime = Field(..., description="When data was processed")
    timestamp: Optional[datetime] = Field(None, description="When data was recorded")

class DeviceDataResponse(BaseModel):
    """Response containing historical telemetry data."""
    device_id: str = Field(..., description="Device ID")
    count: int = Field(..., description="Number of records returned")
    time_window_hours: int = Field(..., description="Time window queried (hours)")
    data: List[TelemetryRecord] = Field(..., description="Array of telemetry records")

@router.get("", response_model=DeviceListResponse)
async def get_devices(current_user: dict = Depends(get_current_user)):
    """Get all registered devices.
    
    Returns a list of all devices in the system. This endpoint provides minimal device information
    for quick lookups and filtering. Use GET /devices/{device_id} for full device metadata.
    
    **Required:** Bearer token in Authorization header
    
    **Returns:**
    - count: Total number of devices
    - devices: Array of device objects with device_id and name
    
    **Example Usage:**
    ```
    GET /devices
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Expected Response:**
    ```json
    {
      "count": 2,
      "devices": [
        {"device_id": "esp32-001", "name": "Office Monitor"},
        {"device_id": "esp32-002", "name": "Lobby Sensor"}
      ]
    }
    ```
    
    **Status Codes:**
    - 200: Devices retrieved successfully
    - 401: Invalid or missing authentication token
    - 500: Server error
    """
    try:
        # Return only minimal device list (device_id and name)
        devices = list(db.devices_collection.find({}, {"_id": 0, "device_id": 1, "name": 1}))
        return {
            "count": len(devices),
            "devices": [{"device_id": d.get("device_id"), "name": d.get("name")} for d in devices]
        }
    except Exception as e:
        logger.error(f"❌ Error fetching devices: {e}")
        raise HTTPException(status_code=500, detail="Error fetching devices")

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device_by_id(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed metadata for a specific device.
    
    Returns complete device information including registration timestamp and sensor list.
    To retrieve telemetry/sensor readings, use GET /devices/{device_id}/data or GET /latest/{device_id}.
    
    **Required:** Bearer token in Authorization header
    
    **Parameters:**
    - device_id: The device identifier (e.g., esp32-001)
    
    **Returns:**
    - device_id: Unique device identifier
    - name: Device display name
    - site_id: Physical location
    - sensors: List of sensors on device
    - created_at: When device was registered
    - updated_at: Last modification time
    
    **Example Usage:**
    ```
    GET /devices/esp32-001
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Expected Response:**
    ```json
    {
      "device_id": "esp32-001",
      "name": "Office Monitor",
      "site_id": "office_main",
      "sensors": ["temperature", "humidity", "air_quality", "light", "sound"],
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:00"
    }
    ```
    
    **Status Codes:**
    - 200: Device metadata retrieved
    - 401: Invalid or missing authentication token
    - 404: Device not found
    - 500: Server error
    """
    try:
        device = db.devices_collection.find_one({"device_id": device_id}, {"_id": 0})

        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        # Return device metadata only - latest data is available via /latest or /devices/{id}/data
        return device

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching device: {e}")
        raise HTTPException(status_code=500, detail="Error fetching device")

@router.post("/register", response_model=RegisterDeviceResponse)
async def register_device(
    request: RegisterDeviceRequest = Body(..., example={
        "device_id": "esp32-office-01",
        "name": "Office Air Quality Monitor",
        "site_id": "office_main",
        "sensors": ["temperature", "humidity", "air_quality", "light", "sound"]
    }),
    current_user: dict = Depends(get_current_user)
):
    """Register a new device.
    
    Creates a new device record in the system. The registering user becomes the device owner
    and is automatically associated with the device. Each device_id must be globally unique.
    
    **Required:** Bearer token in Authorization header
    
    **Request Body:**
    - device_id: Unique identifier (alphanumeric, hyphens allowed)
      - Examples: esp32-001, sensor-office-01, lobby-monitor
      - Must not already exist in system
    - name: Human-readable display name
    - site_id: Physical location (optional, defaults to "home")
    - sensors: Sensor types available (optional, defaults to standard 5)
    
    **Example Usage:**
    ```
    POST /devices/register
    Authorization: Bearer <JWT_TOKEN>
    Content-Type: application/json
    
    {
      "device_id": "esp32-office-01",
      "name": "Office Air Quality Monitor",
      "site_id": "office_main",
      "sensors": ["temperature", "humidity", "air_quality", "light", "sound"]
    }
    ```
    
    **Status Codes:**
    - 200: Device registered successfully
    - 400: Device ID already exists
    - 401: Invalid or missing authentication token
    - 500: Server error
    """
    try:
        # Check if device already exists
        existing_device = db.devices_collection.find_one({"device_id": request.device_id})
        if existing_device:
            raise HTTPException(
                status_code=400,
                detail=f"Device '{request.device_id}' is already registered"
            )
        
        # Create device document
        device_doc = {
            "device_id": request.device_id,
            "name": request.name,
            "site_id": request.site_id,
            "sensors": request.sensors or [
                "temperature",
                "humidity",
                "air_quality",
                "light",
                "sound"
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "owner": current_user["user_id"]
        }
        
        db.devices_collection.insert_one(device_doc)
        
        # Add device to user's device list
        user_object_id = to_objectid(current_user["user_id"])
        db.users_collection.update_one(
            {"_id": user_object_id},
            {
                "$addToSet": {"devices": request.device_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        logger.info(f"✅ Device registered: {request.device_id}")
        
        return {
            "message": "Device registered successfully",
            "device_id": request.device_id,
            "name": request.name,
            "site_id": request.site_id,
            "sensors": device_doc["sensors"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error registering device: {e}")
        raise HTTPException(status_code=500, detail="Error registering device")


@router.post("/associate-default", response_model=AssociateDeviceResponse)
async def associate_default_device_to_all(current_user: dict = Depends(get_current_user)):
    """Associate the default device (esp32-001) to all users missing it.

    This is an administrative endpoint that ensures every user account has the default device
    (esp32-001) in their device list. Useful for system setup or after device pool changes.
    
    **Required:** Bearer token in Authorization header (any authenticated user can call this)
    
    **Purpose:**
    - On user registration, users are auto-associated with esp32-001
    - This endpoint catches any users created before that feature or without association
    - Ensures all users can access default device data and recommendations
    - Creates the device if it doesn't exist yet
    
    **Returns:**
    - message: Confirmation of operation
    - modified_count: Number of user accounts updated
    
    **Example Usage:**
    ```
    POST /devices/associate-default
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Expected Response:**
    ```json
    {
      "message": "Associated default device to users",
      "modified_count": 5
    }
    ```
    
    **Status Codes:**
    - 200: Default device association completed
    - 401: Invalid or missing authentication token
    - 500: Server error
    """
    try:
        default_device_id = "esp32-001"
        users_updated = db.users_collection.update_many(
            {"devices": {"$ne": default_device_id}},
            {"$addToSet": {"devices": default_device_id}, "$set": {"updated_at": datetime.utcnow()}}
        )

        # Ensure the default device exists
        existing_device = db.devices_collection.find_one({"device_id": default_device_id})
        if not existing_device:
            device_doc = {
                "device_id": default_device_id,
                "name": "Default Device",
                "site_id": "home",
                "sensors": ["temperature", "humidity", "air_quality", "light", "sound"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "owner": current_user.get("user_id")
            }
            db.devices_collection.insert_one(device_doc)

        return {"message": "Associated default device to users", "modified_count": users_updated.modified_count}

    except Exception as e:
        logger.error(f"❌ Error associating default device: {e}")
        raise HTTPException(status_code=500, detail="Error associating default device")

@router.put("/{device_id}", response_model=UpdateDeviceResponse)
async def update_device(
    device_id: str,
    request: UpdateDeviceRequest = Body(..., example={
        "name": "Updated Office Monitor",
        "site_id": "office_secondary"
    }),
    current_user: dict = Depends(get_current_user)
):
    """Update device information.
    
    Modifies existing device metadata. Provide only the fields you want to change;
    omitted fields are left unchanged.
    
    **Required:** Bearer token in Authorization header
    
    **Parameters:**
    - device_id: The device to update (e.g., esp32-001)
    
    **Request Body (all optional):**
    - name: New display name
    - site_id: New location/site identifier
    - sensors: Updated sensor list
    
    **Example Usage:**
    ```
    PUT /devices/esp32-001
    Authorization: Bearer <JWT_TOKEN>
    Content-Type: application/json
    
    {
      "name": "Updated Office Monitor",
      "site_id": "office_secondary"
    }
    ```
    
    **Status Codes:**
    - 200: Device updated successfully
    - 401: Invalid or missing authentication token
    - 404: Device not found
    - 500: Server error
    """
    try:
        device = db.devices_collection.find_one({"device_id": device_id})
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Prepare update data
        update_data = {"updated_at": datetime.utcnow()}
        if request.name is not None:
            update_data["name"] = request.name
        if request.site_id is not None:
            update_data["site_id"] = request.site_id
        if request.sensors is not None:
            update_data["sensors"] = request.sensors
        
        db.devices_collection.update_one(
            {"device_id": device_id},
            {"$set": update_data}
        )
        
        logger.info(f"✅ Device updated: {device_id}")
        
        return {
            "message": "Device updated successfully",
            "device_id": device_id,
            **update_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating device: {e}")
        raise HTTPException(status_code=500, detail="Error updating device")

@router.delete("/{device_id}", response_model=DeleteDeviceResponse)
async def delete_device(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a device.
    
    Removes a device from the system and disassociates it from all user accounts.
    Deleting the default device (esp32-001) is not recommended as users rely on it.
    
    **Required:** Bearer token in Authorization header
    
    **Parameters:**
    - device_id: The device to delete (e.g., esp32-001)
    
    **Effects:**
    - Device record is removed from database
    - Device is removed from all users' device lists
    - Associated telemetry data remains (for historical records)
    
    **Example Usage:**
    ```
    DELETE /devices/esp32-002
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Status Codes:**
    - 200: Device deleted successfully
    - 401: Invalid or missing authentication token
    - 404: Device not found
    - 500: Server error
    """
    try:
        device = db.devices_collection.find_one({"device_id": device_id})
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Remove device from database
        db.devices_collection.delete_one({"device_id": device_id})
        
        # Remove device from all users' device lists
        user_object_id = to_objectid(current_user["user_id"])
        db.users_collection.update_one(
            {"_id": user_object_id},
            {
                "$pull": {"devices": device_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        logger.info(f"✅ Device deleted: {device_id}")
        
        return {"message": "Device deleted successfully", "device_id": device_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting device: {e}")
        raise HTTPException(status_code=500, detail="Error deleting device")

@router.get("/{device_id}/data", response_model=DeviceDataResponse)
async def get_device_data(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=500, description="Max records to return (1-500)"),
    hours: Optional[int] = Query(default=None, ge=1, le=8760, description="Time window in hours (optional)"),
    current_user: dict = Depends(get_current_user)
):
    """Get historical telemetry data for a device.
    
    Returns recent sensor readings from a device within a specified time window.
    Data is sorted by timestamp (newest first) and limited to prevent large responses.
    
    **Required:** Bearer token in Authorization header
    
    **Parameters:**
    - device_id: The device to query (e.g., esp32-001)
    - limit: Maximum records to return (default: 50, max: 500)
    - hours: Time window to query (default: 24 hours, max: 720 hours/30 days)
    
    **Returns:**
    - device_id: Device queried
    - count: Number of records returned
    - time_window_hours: Time window that was queried
    - data: Array of telemetry records with:
      - _id: Unique record identifier
      - device_id: Source device
      - site_id: Physical location
      - sensors: Object with {temperature, humidity, air_quality, light, sound}
      - ieq_score: Indoor Environmental Quality Score (0-100)
      - processed_at: When data was processed
      - timestamp: When data was recorded
    
    **Sensor Value Ranges:**
    - temperature: -40 to 85°C
    - humidity: 0-100%
    - air_quality: 0-100 (0=clean, 100=poor)
    - light: 0-1000 lux
    - sound: 30-100 dB
    - ieq_score: 0-100 (50% air quality + 30% temperature + 20% light + 10% sound)
    
    **Example Usage:**
    ```
    GET /devices/esp32-001/data?limit=50&hours=24
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Expected Response:**
    ```json
    {
      "device_id": "esp32-001",
      "count": 50,
      "time_window_hours": 24,
      "data": [
        {
          "_id": "507f1f77bcf86cd799439011",
          "device_id": "esp32-001",
          "site_id": "office_main",
          "sensors": {
            "temperature": 22.5,
            "humidity": 45.2,
            "air_quality": 35,
            "light": 450,
            "sound": 62
          },
          "ieq_score": 62.5,
          "processed_at": "2024-01-15T14:30:00",
          "timestamp": "2024-01-15T14:29:55"
        }
      ]
    }
    ```
    
    **Status Codes:**
    - 200: Data retrieved successfully
    - 401: Invalid or missing authentication token
    - 404: Device not found or no data in time window
    - 500: Server error
    """
    try:
        from datetime import timedelta

        time_threshold = datetime.utcnow() - timedelta(hours=hours)

        telemetry_data = list(db.telemetry_collection.find(
            {
                "device_id": device_id,
                "processed_at": {"$gte": time_threshold}
            },
            {
                "_id": 1,
                "device_id": 1,
                "site_id": 1,
                "sensors": 1,
                "ieq_score": 1,
                "processed_at": 1,
                "timestamp": 1
            }
        ).sort("processed_at", -1).limit(limit))

        # Convert ObjectId to string in response
        for record in telemetry_data:
            record["id"] = to_string(record["_id"])

        return {
            "device_id": device_id,
            "count": len(telemetry_data),
            "time_window_hours": hours,
            "data": telemetry_data
        }

    except Exception as e:
        logger.error(f"❌ Error fetching device telemetry: {e}")
        raise HTTPException(status_code=500, detail="Error fetching telemetry")
