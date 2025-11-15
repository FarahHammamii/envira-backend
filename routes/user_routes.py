from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from core.database import db
from core.utils import to_objectid, to_string
from core.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class UserPreferences(BaseModel):
    """User preference schema for activities and environment sensitivity.

    **activity_preferences:** Maps activity names to user preferences for that activity
    - Must use activity names from GET /recommendations/activities
    - Example: { "studying": { "lighting": "bright", "quiet": true } }
    
    **sensitivity_levels:** Environmental sensitivity (low/medium/high)
    - Keys: temperature, humidity, light, sound, air_quality
    - Example: { "sound": "high", "light": "medium" }
    
    **health_conditions:** Health conditions for personalized recommendations
    """
    activity_preferences: Dict = Field(..., example={"studying": {"lighting": "bright", "quiet": True}})
    sensitivity_levels: Dict = Field(..., example={"sound": "high", "light": "medium"})
    health_conditions: Optional[List[str]] = Field(default=[], example=["asthma"])


class UserDeviceResponse(BaseModel):
    """Device associated with user."""
    device_id: str = Field(..., description="Unique device identifier (e.g., esp32-001)")
    name: str = Field(..., description="Human-readable device name")
    site_id: str = Field(..., description="Site/location ID where device is deployed")
    sensors: List[str] = Field(default=[], description="List of sensors on this device")
    created_at: Optional[datetime] = Field(None, description="When device was registered")


class UserProfileResponse(BaseModel):
    """User profile with account and preference information."""
    user_id: str = Field(..., description="Unique user ID (ObjectId as string)")
    email: str = Field(..., description="User email address (must be unique)")
    name: str = Field(..., description="User full name")
    preferences_set: bool = Field(..., description="Whether user has configured preferences yet")
    devices: List[str] = Field(default=[], description="List of device_ids associated with user")
    preferences: Optional[Dict] = Field(None, description="User preferences object (only included if set)")


class PreferencesUpdateResponse(BaseModel):
    """Response after updating user preferences."""
    message: str = Field(..., description="Confirmation message", example="Preferences updated successfully")
    preferences_set: bool = Field(..., description="Whether preferences are now configured", example=True)


class UserDevicesResponse(BaseModel):
    """List of devices associated with user."""
    devices: List[UserDeviceResponse] = Field(..., description="Array of devices owned by user")

@router.get("/me", response_model=UserProfileResponse, tags=["users"])
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user's profile information.
    
    Returns the authenticated user's profile including email, name, device associations, and preferences.
    
    **Required:** Bearer token in Authorization header
    
    **Returns:**
    - user_id: Unique identifier for this user
    - email: User's email address (unique)
    - name: User's full name
    - preferences_set: Boolean indicating if user has configured preferences
    - devices: List of device_ids currently associated with this user
    - preferences: User's stored preferences (if configured)
    
    **Example Usage:**
    ```
    GET /users/me
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Status Codes:**
    - 200: User profile retrieved successfully
    - 401: Invalid or missing authentication token
    - 404: User account not found
    - 500: Server error
    """
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        
        user = db.users_collection.find_one({"_id": user_object_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        preferences = db.user_preferences.find_one({"user_id": user_object_id})
        
        response_data = {
            "user_id": to_string(user["_id"]),
            "email": user["email"],
            "name": user["name"],
            "preferences_set": user.get("preferences_set", False),
            "devices": user.get("devices", [])
        }
        
        if preferences:
            response_data["preferences"] = {
                "activity_preferences": preferences.get("activity_preferences", {}),
                "sensitivity_levels": preferences.get("sensitivity_levels", {}),
                "health_conditions": preferences.get("health_conditions", [])
            }
        
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting user info: {e}")
        raise HTTPException(status_code=500, detail="Error fetching user information")

@router.put("/preferences", response_model=PreferencesUpdateResponse, tags=["users"])
async def update_user_preferences(
    preferences_data: UserPreferences = Body(..., example={
        "activity_preferences": {"studying": {"lighting": "bright", "quiet": True}, "exercise": {"music": "upbeat"}},
        "sensitivity_levels": {"sound": "high", "light": "medium", "temperature": "low"},
        "health_conditions": ["asthma"]
    }),
    current_user: dict = Depends(get_current_user)
):
    """Update user's environmental preferences and activity settings.
    
    Stores user's activity preferences, environmental sensitivity levels, and health conditions for personalized recommendations.
    
    **Required:** Bearer token in Authorization header
    
    **Request Body:**
    - activity_preferences: Dict mapping activity names to their preferences
      - Activity names must match those from GET /recommendations/activities
      - Example: `{ "studying": { "lighting": "bright", "quiet": true } }`
    - sensitivity_levels: How sensitive user is to environmental factors (low/medium/high)
      - Keys can include: temperature, humidity, light, sound, air_quality
    - health_conditions: List of health conditions for recommendations
    
    **Valid Activity Names:** Retrieved from GET /recommendations/activities endpoint
    - Examples: studying, exercise, meditation, work, sleep
    
    **Valid Sensitivity Levels:** low, medium, high
    
    **Returns:**
    - message: Confirmation of successful update
    - preferences_set: Boolean confirming preferences are now stored
    
    **Example Usage:**
    ```
    PUT /users/preferences
    Authorization: Bearer <JWT_TOKEN>
    Content-Type: application/json
    
    {
      "activity_preferences": {
        "studying": {"lighting": "bright", "quiet": true},
        "exercise": {"music": "upbeat", "temperature": "cool"}
      },
      "sensitivity_levels": {
        "sound": "high",
        "light": "medium",
        "temperature": "low"
      },
      "health_conditions": ["asthma", "allergies"]
    }
    ```
    
    **Status Codes:**
    - 200: Preferences updated successfully
    - 400: Invalid activity names or missing required fields
      - Response includes list of valid activities
    - 401: Invalid or missing authentication token
    - 404: User account not found
    - 500: Server error
    """
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        
        # Verify user exists
        user = db.users_collection.find_one({"_id": user_object_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate activity keys against existing activities to help the frontend
        allowed_activities = list(db.activities.find({}, {"_id": 1, "name": 1}))
        allowed_names = {str(a["_id"]): a["name"] for a in allowed_activities}
        allowed_name_set = {a["name"].lower() for a in allowed_activities}

        invalid_keys = []
        for key in preferences_data.activity_preferences.keys():
            # Accept either activity _id (string) or activity name
            if key in allowed_name_set:
                continue
            if key in allowed_names:
                continue
            # try case-insensitive name match
            if any(key.lower() == n for n in allowed_name_set):
                continue
            invalid_keys.append(key)

        if invalid_keys:
            raise HTTPException(status_code=400, detail=f"Invalid activity keys in preferences: {invalid_keys}. Available activities: {list(allowed_name_set)}")

        preferences_doc = {
            "user_id": user_object_id,
            "activity_preferences": preferences_data.activity_preferences,
            "sensitivity_levels": preferences_data.sensitivity_levels,
            "health_conditions": preferences_data.health_conditions,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Update or insert preferences
        result = db.user_preferences.update_one(
            {"user_id": user_object_id},
            {"$set": preferences_doc},
            upsert=True
        )
        
        # Mark user as having preferences
        db.users_collection.update_one(
            {"_id": user_object_id},
            {"$set": {"preferences_set": True, "updated_at": datetime.utcnow()}}
        )
        
        logger.info(f"✅ Preferences updated for user: {user['email']}")
        
        return {
            "message": "Preferences updated successfully",
            "preferences_set": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating preferences: {e}")
        raise HTTPException(status_code=500, detail="Error updating preferences")

@router.get("/devices", response_model=UserDevicesResponse, tags=["users"])
async def get_user_devices(current_user: dict = Depends(get_current_user)):
    """Get user's registered devices.
    
    Returns list of all devices currently associated with this user's account.
    By default, users are automatically associated with the primary device (esp32-001) upon registration.
    
    **Required:** Bearer token in Authorization header
    
    **Returns:**
    - devices: Array of device objects containing:
      - device_id: Unique device identifier (e.g., esp32-001)
      - name: Human-readable device name
      - site_id: Physical location or deployment site
      - sensors: List of sensor types available on device
      - created_at: Registration timestamp
    
    **Example Usage:**
    ```
    GET /users/devices
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Expected Response:**
    ```json
    {
      "devices": [
        {
          "device_id": "esp32-001",
          "name": "Office Monitor",
          "site_id": "office_main",
          "sensors": ["temperature", "humidity", "air_quality", "light", "sound"],
          "created_at": "2024-01-15T10:30:00"
        }
      ]
    }
    ```
    
    **Status Codes:**
    - 200: Devices retrieved successfully
    - 401: Invalid or missing authentication token
    - 404: User account not found
    - 500: Server error
    """
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        
        user = db.users_collection.find_one({"_id": user_object_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        device_ids = user.get("devices", [])
        
        if not device_ids:
            return {"devices": []}
        
        devices = list(db.devices_collection.find({"device_id": {"$in": device_ids}}))
        
        return {
            "devices": [
                {
                    "device_id": device["device_id"],
                    "name": device.get("name", "Unknown"),
                    "site_id": device.get("site_id", "unknown"),
                    "sensors": device.get("sensors", []),
                    "created_at": device.get("created_at")
                }
                for device in devices
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting user devices: {e}")
        raise HTTPException(status_code=500, detail="Error fetching user devices")

@router.get("/profile", response_model=UserProfileResponse, tags=["users"])
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get full user profile (alias for /users/me).
    
    Returns complete user profile information including account details, device associations, and preferences.
    This endpoint is functionally identical to GET /users/me.
    
    **Required:** Bearer token in Authorization header
    
    **Returns:**
    - user_id: Unique identifier for this user
    - email: User's email address
    - name: User's full name
    - preferences_set: Whether user has configured preferences
    - devices: List of device_ids associated with user
    - preferences: User's stored preferences (if configured)
    
    **Example Usage:**
    ```
    GET /users/profile
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Status Codes:**
    - 200: User profile retrieved successfully
    - 401: Invalid or missing authentication token
    - 404: User account not found
    - 500: Server error
    """
    try:
        user_id = current_user["user_id"]
        return await get_current_user_info(current_user)
    
    except Exception as e:
        logger.error(f"❌ Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail="Error fetching user profile")