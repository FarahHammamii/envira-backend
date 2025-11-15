from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from core.database import db
from core.utils import to_objectid, to_string
from core.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ActivityRecommendationRequest(BaseModel):
    """Request for activity-specific recommendations.
    
    **activity_id:** Identifier for the activity
    - Can be activity ObjectId (string format), activity_id field, or activity name
    - Get valid IDs from GET /recommendations/activities
    
    **device_id:** Device to base recommendations on
    - Example: esp32-001
    """
    activity_id: str = Field(..., description="Activity ID, ID field, or name", example="studying")
    device_id: str = Field(..., description="Device to analyze", example="esp32-001")

class GeneralRecommendationRequest(BaseModel):
    """Request for general environmental recommendations.
    
    **device_id:** Device to analyze current environmental conditions
    - Example: esp32-001
    """
    device_id: str = Field(..., description="Device to analyze", example="esp32-001")

class SensorDataResponse(BaseModel):
    """Current sensor readings."""
    temperature: Optional[float] = Field(None, description="Current temperature (Celsius)")
    humidity: Optional[float] = Field(None, description="Current humidity (%)")
    air_quality: Optional[float] = Field(None, description="Air quality (0-100)")
    light: Optional[float] = Field(None, description="Light level (lux)")
    sound: Optional[float] = Field(None, description="Sound level (dB)")

class GeneralRecommendationResponse(BaseModel):
    """Response with general environmental recommendations."""
    recommendation_id: str = Field(..., description="Unique recommendation ID")
    recommendation_type: str = Field(..., description="Type of recommendation", example="general_environmental")
    device_id: str = Field(..., description="Device analyzed")
    environmental_score: float = Field(..., description="IEQ Score (0-100)")
    recommendations: List[str] = Field(..., description="List of actionable recommendations")
    sensor_data: SensorDataResponse = Field(..., description="Current sensor readings")
    generated_at: str = Field(..., description="ISO timestamp when generated")

class ActivityRecommendationResponse(BaseModel):
    """Response with activity-specific recommendations."""
    recommendation_id: str = Field(..., description="Unique recommendation ID")
    recommendation_type: str = Field(..., description="Type of recommendation", example="activity_specific")
    activity_id: str = Field(..., description="Activity ID used")
    activity_name: str = Field(..., description="Human-readable activity name")
    device_id: str = Field(..., description="Device analyzed")
    environmental_score: float = Field(..., description="IEQ Score (0-100)")
    recommendations: List[str] = Field(..., description="Activity-specific recommendations")
    sensor_data: SensorDataResponse = Field(..., description="Current sensor readings")
    generated_at: str = Field(..., description="ISO timestamp when generated")

class ActivityInfo(BaseModel):
    """Information about an activity."""
    activity_id: str = Field(..., description="Unique activity identifier")
    name: str = Field(..., description="Activity name")
    description: str = Field(..., description="Activity description")
    category: str = Field(..., description="Activity category")
    ideal_conditions: Dict = Field(..., description="Ideal environmental conditions")

class ActivitiesListResponse(BaseModel):
    """List of all available activities."""
    count: int = Field(..., description="Number of activities")
    activities: List[ActivityInfo] = Field(..., description="Array of activity info")

class RecommendationItem(BaseModel):
    """Single recommendation record."""
    id: str = Field(..., description="Recommendation ID")
    type: str = Field(..., description="Type (general or activity)")
    category: str = Field(..., description="Category/activity name")
    message: str = Field(..., description="Human-readable message")
    actionable_steps: List[str] = Field(..., description="Steps to implement recommendation")
    environmental_score: Optional[float] = Field(None, description="IEQ Score at time of generation")
    activity_id: Optional[str] = Field(None, description="Activity ID if activity-specific")
    priority: str = Field(..., description="Priority level (high/medium/low)")
    generated_at: str = Field(..., description="ISO timestamp")
    expires_at: Optional[str] = Field(None, description="When recommendation expires")

class UserRecommendationsResponse(BaseModel):
    """List of active recommendations for user."""
    count: int = Field(..., description="Number of recommendations")
    recommendations: List[RecommendationItem] = Field(..., description="Array of recommendations")

# Recommendation rules based on sensor data
RECOMMENDATION_RULES = {
    "temperature": {
        "low": [
            "Room is cold - Consider increasing temperature or wearing warmer clothes",
            "Use a space heater or move to a warmer area",
            "Close windows to prevent heat loss",
            "Adjust thermostat upward if available"
        ],
        "high": [
            "Room is warm - Consider decreasing temperature or wearing lighter clothes",
            "Use a fan or air conditioning if available",
            "Open windows for ventilation",
            "Reduce heat-generating activities"
        ]
    },
    "humidity": {
        "low": [
            "Air is dry - Use a humidifier to increase moisture",
            "Place water bowls in the room to increase humidity naturally",
            "Add indoor plants to increase humidity levels",
            "Keep doors open to allow moisture circulation"
        ],
        "high": [
            "Air is humid - Use a dehumidifier to reduce moisture",
            "Improve ventilation by opening windows",
            "Use exhaust fans in humid areas",
            "Reduce moisture-generating activities"
        ]
    },
    "light": {
        "low": [
            "Lighting is insufficient - Increase lights in the room",
            "Move closer to natural light sources or windows",
            "Use task lighting for better visibility",
            "Use brighter light bulbs"
        ],
        "high": [
            "Too much light - Reduce direct lighting",
            "Use curtains or blinds to filter sunlight",
            "Adjust screen brightness settings",
            "Position workspace to avoid glare"
        ]
    },
    "sound": {
        "high": [
            "Noise level is high - Move to a quieter location if possible",
            "Use noise-cancelling headphones or earplugs",
            "Close windows to reduce external noise",
            "Use white noise to mask distracting sounds"
        ]
    },
    "air_quality": {
        "low": [
            "Air quality is poor - Improve room ventilation immediately",
            "Open windows to bring in fresh air",
            "Use an air purifier if available",
            "Add air-purifying plants to the room"
        ]
    }
}

def get_latest_device_data(device_id: str) -> Dict:
    """Get latest sensor data for a device"""
    # Try to get the most recent telemetry
    latest_data = db.telemetry_collection.find_one({"device_id": device_id}, sort=[("processed_at", -1)])

    if not latest_data:
        raise HTTPException(status_code=404, detail="No data found for device")

    sensors = latest_data.get("sensors", {}) or {}
    # Normalize sensors to processed shape if raw values are stored
    try:
        from core.utils import normalize_sensors
        sensors_processed = normalize_sensors(sensors)
    except Exception:
        sensors_processed = {
            "temperature": sensors.get("temperature"),
            "humidity": sensors.get("humidity"),
            "light": sensors.get("light"),
            "sound": sensors.get("sound"),
            "air_quality": sensors.get("air_quality")
        }

    # If sensors are present but all None, try to find the most recent document with at least one non-null sensor
    if sensors and all(v is None for v in sensors.values()):
        # Build $or conditions for common sensor fields
        or_conditions = [
            {"sensors.temperature": {"$ne": None}},
            {"sensors.humidity": {"$ne": None}},
            {"sensors.air_quality": {"$ne": None}},
            {"sensors.light": {"$ne": None}},
            {"sensors.sound": {"$ne": None}}
        ]
        fallback = db.telemetry_collection.find_one(
            {"device_id": device_id, "$or": or_conditions},
            sort=[("processed_at", -1)]
        )
        if fallback:
            latest_data = fallback
            sensors = latest_data.get("sensors", {}) or {}

    return {
        "temperature": sensors_processed.get("temperature"),
        "humidity": sensors_processed.get("humidity"),
        "light": sensors_processed.get("light"),
        "sound": sensors_processed.get("sound"),
        "air_quality": sensors_processed.get("air_quality"),
        "ieq_score": latest_data.get("ieq_score", 50)
    }

def generate_general_recommendations(sensor_data: Dict) -> List[str]:
    """Generate general environmental recommendations based on sensor data"""
    recommendations = []
    
    # Temperature recommendations (ideal: 20-24°C)
    temp = sensor_data.get("temperature")
    if temp is not None:
        if temp < 18:
            recommendations.extend(RECOMMENDATION_RULES["temperature"]["low"])
        elif temp > 26:
            recommendations.extend(RECOMMENDATION_RULES["temperature"]["high"])
    
    # Humidity recommendations (ideal: 40-60%)
    humidity = sensor_data.get("humidity")
    if humidity is not None:
        if humidity < 35:
            recommendations.extend(RECOMMENDATION_RULES["humidity"]["low"])
        elif humidity > 65:
            recommendations.extend(RECOMMENDATION_RULES["humidity"]["high"])
    
    # Light recommendations (ideal: 300-600 lux)
    light = sensor_data.get("light")
    if light is not None:
        if light < 200:
            recommendations.extend(RECOMMENDATION_RULES["light"]["low"])
        elif light > 700:
            recommendations.extend(RECOMMENDATION_RULES["light"]["high"])
    
    # Sound recommendations (ideal: 0-40 dB)
    sound = sensor_data.get("sound")
    if sound is not None and sound > 50:
        recommendations.extend(RECOMMENDATION_RULES["sound"]["high"])
    
    # Air quality recommendations (ideal: 70-100)
    air_quality = sensor_data.get("air_quality")
    if air_quality is not None and air_quality < 60:
        recommendations.extend(RECOMMENDATION_RULES["air_quality"]["low"])
    
    # Remove duplicates and return unique recommendations
    unique_recommendations = list(dict.fromkeys(recommendations))
    return unique_recommendations[:5] if unique_recommendations else ["Environment conditions are acceptable"]

def generate_activity_recommendations(activity_id: str, sensor_data: Dict, user_preferences: Dict) -> List[str]:
    """Generate activity-specific recommendations"""
    recommendations = []
    
    # Find activity by multiple strategies: treat as ObjectId, then activity_id field, then by name
    activity = None
    try:
        activity_obj = to_objectid(activity_id)
        activity = db.activities.find_one({"_id": activity_obj})
    except Exception:
        activity = None

    if not activity:
        activity = db.activities.find_one({"activity_id": activity_id})

    if not activity:
        # try by name (case-insensitive)
        activity = db.activities.find_one({"name": {"$regex": f"^{activity_id}$", "$options": "i"}})

    if not activity:
        raise HTTPException(status_code=404, detail=f"Activity '{activity_id}' not found")
    
    ideal_conditions = activity.get("ideal_conditions", {})
    activity_prefs = user_preferences.get("activity_preferences", {}).get(activity_id, {})
    
    # Get ideal values from preferences or activity defaults
    ideal_temp_range = ideal_conditions.get("temperature", [21, 23])
    ideal_light_range = ideal_conditions.get("light", [400, 600])
    ideal_sound_range = ideal_conditions.get("sound", [0, 35])
    ideal_humidity_range = ideal_conditions.get("humidity", [40, 55])
    
    activity_name = activity.get("name", activity_id)
    
    # Temperature recommendations
    current_temp = sensor_data.get("temperature")
    if current_temp is not None:
        ideal_temp_mid = sum(ideal_temp_range) / 2
        temp_diff = abs(current_temp - ideal_temp_mid)
        if temp_diff > 3:
            if current_temp < ideal_temp_mid:
                recommendations.append(f"For {activity_name}: Room is {temp_diff:.1f}°C cooler than ideal. Increase temperature for better focus.")
            else:
                recommendations.append(f"For {activity_name}: Room is {temp_diff:.1f}°C warmer than ideal. Improve cooling for better comfort.")
    
    # Light recommendations
    current_light = sensor_data.get("light")
    if current_light is not None:
        ideal_light_mid = sum(ideal_light_range) / 2
        light_diff = abs(current_light - ideal_light_mid)
        if light_diff > 150:
            if current_light < ideal_light_mid:
                recommendations.append(f"For {activity_name}: Increase lighting to {ideal_light_mid:.0f} lux for optimal visibility.")
            else:
                recommendations.append(f"For {activity_name}: Reduce lighting to prevent eye strain and glare.")
    
    # Sound recommendations
    current_sound = sensor_data.get("sound")
    if current_sound is not None:
        ideal_sound_max = ideal_sound_range[1] if ideal_sound_range else 35
        if current_sound > ideal_sound_max + 10:
            recommendations.append(f"For {activity_name}: Noise level is high. Use noise-cancelling headphones or move to a quieter space.")
    
    # Activity-specific tips
    activity_tips = {
        "studying": [
            "Take a 5-minute break every 25 minutes (Pomodoro Technique)",
            "Ensure your desk and chair are ergonomically positioned",
            "Keep study materials organized for quick access",
            "Minimize notifications and digital distractions"
        ],
        "coding": [
            "Practice the 20-20-20 eye care rule (every 20 min, look 20 ft away for 20 sec)",
            "Maintain proper typing posture to prevent RSI",
            "Use dual monitors if possible to reduce neck strain",
            "Take regular movement breaks to maintain circulation"
        ],
        "reading": [
            "Position the book 10-12 inches from your eyes at a 45° angle",
            "Ensure lighting comes from behind or to the side",
            "Take a 2-minute break for every 20-30 minutes of reading",
            "Blink frequently to prevent eye dryness"
        ],
        "relaxing": [
            "Create a clutter-free, calm environment",
            "Use soft, warm lighting to promote relaxation",
            "Keep the space quiet or use calming ambient sounds",
            "Practice deep breathing: inhale for 4, hold for 4, exhale for 4"
        ],
        "exercising": [
            "Ensure good air circulation and ventilation",
            "Stay hydrated - keep water nearby",
            "Warm up for 5-10 minutes before exercising",
            "Cool down and stretch for 5-10 minutes after exercising"
        ],
        "creative": [
            "Organize materials and tools within arm's reach",
            "Position workspace near natural light if possible",
            "Minimize interruptions to maintain flow state",
            "Take 10-15 minute breaks every 60-90 minutes"
        ]
    }
    
    # Add activity-specific tips (match by activity name lowercased)
    activity_name_key = activity_name.lower()
    recommendations.extend(activity_tips.get(activity_name_key, []))
    
    return recommendations[:5]

def save_recommendation_to_db(user_id: str, rec_type: str, category: str, 
                            recommendations: List[str], sensor_data: Dict, 
                            activity_id: str = None):
    """Save recommendation to database"""
    try:
        rec_data = {
            "user_id": to_objectid(user_id),
            "type": rec_type,
            "category": category,
            "priority": "high" if rec_type == "general" else "medium",
            "message": f"{rec_type.title()} recommendations for optimal environment",
            "actionable_steps": recommendations,
            "sensor_data": sensor_data,
            "activity_id": activity_id,
            "environmental_score": sensor_data.get("ieq_score", 50),
            "generated_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=4)
        }
        
        result = db.recommendations.insert_one(rec_data)
        logger.info(f"✅ Saved {rec_type} recommendation for user {user_id}")
        return to_string(result.inserted_id)
    
    except Exception as e:
        logger.error(f"❌ Error saving recommendation: {e}")
        raise

@router.post("/general", response_model=GeneralRecommendationResponse)
async def generate_general_recommendation(
    request: GeneralRecommendationRequest = Body(..., example={"device_id": "esp32-001"}),
    current_user: dict = Depends(get_current_user)
):
    """Generate general environmental recommendations based on current sensor conditions.
    
    Analyzes current environmental data from the device and provides actionable recommendations
    to optimize the physical environment. Recommendations are based on standard ideal ranges.
    
    **Required:** Bearer token in Authorization header
    
    **Request Body:**
    - device_id: The device to analyze (e.g., esp32-001)
    
    **Recommendation Logic:**
    Recommendations are generated based on deviations from ideal ranges:
    - **Temperature**: Ideal 20-24°C
    - **Humidity**: Ideal 40-60%
    - **Light**: Ideal 300-600 lux
    - **Sound**: Ideal 0-40 dB
    - **Air Quality**: Ideal 70-100 score
    
    **Returns:**
    - recommendation_id: Unique identifier for this recommendation
    - recommendation_type: "general_environmental"
    - device_id: Device analyzed
    - environmental_score: IEQ Score (0-100)
    - recommendations: Array of 1-5 actionable suggestions
    - sensor_data: Current sensor readings
    - generated_at: ISO timestamp
    
    **Example Usage:**
    ```
    POST /recommendations/general
    Authorization: Bearer <JWT_TOKEN>
    Content-Type: application/json
    
    {
      "device_id": "esp32-001"
    }
    ```
    
    **Expected Response:**
    ```json
    {
      "recommendation_id": "507f1f77bcf86cd799439011",
      "recommendation_type": "general_environmental",
      "device_id": "esp32-001",
      "environmental_score": 62.5,
      "recommendations": [
        "Room is cold - Consider increasing temperature or wearing warmer clothes",
        "Noise level is high. Use noise-cancelling headphones or move to a quieter space."
      ],
      "sensor_data": {
        "temperature": 18.5,
        "humidity": 45.2,
        "air_quality": 35,
        "light": 450,
        "sound": 62
      },
      "generated_at": "2024-01-15T14:30:00"
    }
    ```
    
    **Status Codes:**
    - 200: Recommendations generated successfully
    - 401: Invalid or missing authentication token
    - 404: Device not found or has no data
    - 500: Server error
    """
    try:
        user_id = current_user["user_id"]
        
        # Get latest device data
        sensor_data = get_latest_device_data(request.device_id)
        
        # Generate recommendations
        recommendations = generate_general_recommendations(sensor_data)
        
        # Save to database
        rec_id = save_recommendation_to_db(
            user_id=user_id,
            rec_type="general",
            category="environmental",
            recommendations=recommendations,
            sensor_data=sensor_data
        )
        
        return {
            "recommendation_id": rec_id,
            "recommendation_type": "general_environmental",
            "device_id": request.device_id,
            "environmental_score": sensor_data.get("ieq_score", 50),
            "recommendations": recommendations,
            "sensor_data": {
                "temperature": sensor_data.get("temperature"),
                "humidity": sensor_data.get("humidity"),
                "air_quality": sensor_data.get("air_quality"),
                "light": sensor_data.get("light"),
                "sound": sensor_data.get("sound")
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating general recommendations: {e}")
        raise HTTPException(status_code=500, detail="Error generating recommendations")

@router.post("/activity", response_model=ActivityRecommendationResponse)
async def generate_activity_recommendation(
    request: ActivityRecommendationRequest = Body(..., example={"activity_id": "studying", "device_id": "esp32-001"}),
    current_user: dict = Depends(get_current_user)
):
    """Generate activity-specific recommendations based on environmental conditions.
    
    Analyzes environmental data and generates recommendations tailored to a specific activity.
    Compares current conditions against the activity's ideal environmental parameters
    and includes activity-specific tips for optimal performance.
    
    **Required:** Bearer token in Authorization header
    
    **Request Body:**
    - activity_id: The activity to optimize for
      - Can be: activity name (e.g., "studying"), ObjectId, or activity_id field value
      - Get valid activities from GET /recommendations/activities
    - device_id: Device to analyze (e.g., esp32-001)
    
    **Activity Categories:**
    - studying: Focus-based learning activity
    - coding: Programming and technical work
    - reading: Reading activity
    - relaxing: Stress reduction and relaxation
    - exercising: Physical exercise and fitness
    - creative: Creative work (art, music, writing)
    
    **Recommendation Types:**
    1. **Environmental Adjustments**: Temperature, humidity, light, sound modifications
    2. **Activity-Specific Tips**: Best practices for the activity
    
    **Returns:**
    - recommendation_id: Unique identifier
    - recommendation_type: "activity_specific"
    - activity_id: Activity identifier used
    - activity_name: Human-readable activity name
    - device_id: Device analyzed
    - environmental_score: IEQ Score (0-100)
    - recommendations: Array of activity-specific suggestions
    - sensor_data: Current sensor readings
    - generated_at: ISO timestamp
    
    **Example Usage:**
    ```
    POST /recommendations/activity
    Authorization: Bearer <JWT_TOKEN>
    Content-Type: application/json
    
    {
      "activity_id": "studying",
      "device_id": "esp32-001"
    }
    ```
    
    **Expected Response:**
    ```json
    {
      "recommendation_id": "507f1f77bcf86cd799439012",
      "recommendation_type": "activity_specific",
      "activity_id": "studying",
      "activity_name": "Studying",
      "device_id": "esp32-001",
      "environmental_score": 62.5,
      "recommendations": [
        "For studying: Room is 2.5°C cooler than ideal. Increase temperature for better focus.",
        "Practice the 20-20-20 eye care rule (every 20 min, look 20 ft away for 20 sec)",
        "Ensure your desk and chair are ergonomically positioned"
      ],
      "sensor_data": {
        "temperature": 18.5,
        "humidity": 45.2,
        "air_quality": 35,
        "light": 450,
        "sound": 62
      },
      "generated_at": "2024-01-15T14:30:00"
    }
    ```
    
    **Status Codes:**
    - 200: Recommendations generated successfully
    - 401: Invalid or missing authentication token
    - 404: Device not found or activity not found
    - 500: Server error
    """
    try:
        user_id = current_user["user_id"]
        
        # Get latest device data
        sensor_data = get_latest_device_data(request.device_id)
        
        # Get user preferences
        user_object_id = to_objectid(user_id)
        user_preferences = db.user_preferences.find_one({"user_id": user_object_id}) or {}
        
        # Generate activity recommendations
        recommendations = generate_activity_recommendations(
            request.activity_id, 
            sensor_data, 
            user_preferences
        )
        
        # Resolve activity similar to generation helper: try ObjectId, activity_id, then name
        activity = None
        try:
            activity_obj = to_objectid(request.activity_id)
            activity = db.activities.find_one({"_id": activity_obj})
        except Exception:
            activity = None

        if not activity:
            activity = db.activities.find_one({"activity_id": request.activity_id})

        if not activity:
            activity = db.activities.find_one({"name": {"$regex": f"^{request.activity_id}$", "$options": "i"}})

        if not activity:
            raise HTTPException(status_code=404, detail=f"Activity '{request.activity_id}' not found")

        activity_name = activity.get("name", request.activity_id)
        
        # Save to database
        rec_id = save_recommendation_to_db(
            user_id=user_id,
            rec_type="activity",
            category=activity_name,
            recommendations=recommendations,
            sensor_data=sensor_data,
            activity_id=request.activity_id
        )
        
        return {
            "recommendation_id": rec_id,
            "recommendation_type": "activity_specific",
            "activity_id": request.activity_id,
            "activity_name": activity_name,
            "device_id": request.device_id,
            "environmental_score": sensor_data.get("ieq_score", 50),
            "recommendations": recommendations,
            "sensor_data": {
                "temperature": sensor_data.get("temperature"),
                "humidity": sensor_data.get("humidity"),
                "air_quality": sensor_data.get("air_quality"),
                "light": sensor_data.get("light"),
                "sound": sensor_data.get("sound")
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating activity recommendations: {e}")
        raise HTTPException(status_code=500, detail="Error generating activity recommendations")

@router.get("/activities", response_model=ActivitiesListResponse)
async def get_predefined_activities(current_user: dict = Depends(get_current_user)):
    """Get list of all predefined activities available for recommendations.
    
    Returns all activities that can be used with POST /recommendations/activity endpoint.
    Activities contain ideal environmental conditions for optimal performance.
    
    **Required:** Bearer token in Authorization header
    
    **Use Cases:**
    1. Frontend can display available activities to user
    2. Get activity_id values to use in activity recommendation requests
    3. Show ideal environmental conditions for each activity
    
    **Returns:**
    - count: Total number of activities
    - activities: Array of activity objects containing:
      - activity_id: Unique identifier (use in POST /recommendations/activity)
      - name: Human-readable activity name
      - description: What the activity entails
      - category: Activity category
      - ideal_conditions: Object with optimal environmental parameters
        - temperature: Ideal temperature range [min, max] in Celsius
        - humidity: Ideal humidity range [min, max] in percentage
        - light: Ideal light range [min, max] in lux
        - sound: Ideal sound range [min, max] in dB
    
    **Example Usage:**
    ```
    GET /recommendations/activities
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Expected Response:**
    ```json
    {
      "count": 6,
      "activities": [
        {
          "activity_id": "507f1f77bcf86cd799439001",
          "name": "studying",
          "description": "Focus-intensive learning activities",
          "category": "work",
          "ideal_conditions": {
            "temperature": [21, 23],
            "humidity": [40, 55],
            "light": [400, 600],
            "sound": [0, 30]
          }
        },
        {
          "activity_id": "507f1f77bcf86cd799439002",
          "name": "coding",
          "description": "Programming and technical development",
          "category": "work",
          "ideal_conditions": {
            "temperature": [20, 24],
            "humidity": [40, 50],
            "light": [500, 700],
            "sound": [0, 35]
          }
        }
      ]
    }
    ```
    
    **Frontend Integration:**
    ```javascript
    // Get available activities
    const response = await fetch('/recommendations/activities', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const { activities } = await response.json();
    
    // Use activity_id in recommendation request
    const rec = await fetch('/recommendations/activity', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({
        activity_id: activities[0].activity_id,
        device_id: 'esp32-001'
      })
    });
    ```
    
    **Status Codes:**
    - 200: Activities retrieved successfully
    - 401: Invalid or missing authentication token
    - 500: Server error
    """
    try:
        activities = list(db.activities.find({}))

        return {
            "count": len(activities),
            "activities": [
                {
                    "activity_id": to_string(activity.get("_id")),
                    "name": activity.get("name"),
                    "description": activity.get("description"),
                    "category": activity.get("category"),
                    "ideal_conditions": activity.get("ideal_conditions", {})
                }
                for activity in activities
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching activities: {e}")
        raise HTTPException(status_code=500, detail="Error fetching activities")

@router.get("/user", response_model=UserRecommendationsResponse)
async def get_user_recommendations(current_user: dict = Depends(get_current_user)):
    """Get all active recommendations for the current user.
    
    Returns recommendations that were previously generated via POST /recommendations/general
    or POST /recommendations/activity endpoints. Only active (non-expired) recommendations
    are returned, sorted by most recently generated first.
    
    **Required:** Bearer token in Authorization header
    
    **Recommendation Lifecycle:**
    1. User calls POST /recommendations/general or /activity
    2. Recommendation is generated and stored in database
    3. GET /recommendations/user returns it (valid for 4 hours)
    4. After 4 hours, recommendation expires and is no longer returned
    5. User can generate new recommendations on demand
    
    **Returns:**
    - count: Number of active recommendations
    - recommendations: Array of recommendation objects (max 20 most recent)
      - id: Unique recommendation identifier
      - type: "general" or "activity"
      - category: Category name or activity name
      - message: Human-readable summary
      - actionable_steps: Array of specific action items
      - environmental_score: IEQ Score at time of generation
      - activity_id: Activity ID (if activity-specific)
      - priority: "high" (for general) or "medium" (for activity)
      - generated_at: ISO timestamp of generation
      - expires_at: When this recommendation stops being active
    
    **Use Cases:**
    1. Display recommendation history to user
    2. Allow user to review past suggestions
    3. Show recommendations from different devices/activities
    4. Implement recommendation dismissal features
    
    **Example Usage:**
    ```
    GET /recommendations/user
    Authorization: Bearer <JWT_TOKEN>
    ```
    
    **Expected Response:**
    ```json
    {
      "count": 2,
      "recommendations": [
        {
          "id": "507f1f77bcf86cd799439011",
          "type": "activity",
          "category": "studying",
          "message": "Activity recommendations for optimal environment",
          "actionable_steps": [
            "For studying: Room is 2.5°C cooler than ideal. Increase temperature for better focus.",
            "Practice the 20-20-20 eye care rule"
          ],
          "environmental_score": 62.5,
          "activity_id": "507f1f77bcf86cd799439001",
          "priority": "medium",
          "generated_at": "2024-01-15T14:30:00",
          "expires_at": "2024-01-15T18:30:00"
        },
        {
          "id": "507f1f77bcf86cd799439010",
          "type": "general",
          "category": "environmental",
          "message": "General recommendations for optimal environment",
          "actionable_steps": [
            "Room is cold - Consider increasing temperature",
            "Noise level is high - Use noise-cancelling headphones"
          ],
          "environmental_score": 62.5,
          "activity_id": null,
          "priority": "high",
          "generated_at": "2024-01-15T14:00:00",
          "expires_at": "2024-01-15T18:00:00"
        }
      ]
    }
    ```
    
    **Status Codes:**
    - 200: Recommendations retrieved successfully
    - 401: Invalid or missing authentication token
    - 500: Server error
    """
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        
        # Get active recommendations (not expired)
        recommendations = list(db.recommendations.find({
            "user_id": user_object_id,
            "expires_at": {"$gt": datetime.utcnow()}
        }).sort([("generated_at", -1)]).limit(20))
        
        return {
            "count": len(recommendations),
            "recommendations": [
                {
                    "id": to_string(rec["_id"]),
                    "type": rec["type"],
                    "category": rec["category"],
                    "message": rec["message"],
                    "actionable_steps": rec.get("actionable_steps", []),
                    "environmental_score": rec.get("environmental_score"),
                    "activity_id": rec.get("activity_id"),
                    "priority": rec.get("priority", "medium"),
                    "generated_at": rec["generated_at"].isoformat(),
                    "expires_at": rec.get("expires_at", "").isoformat() if rec.get("expires_at") else None
                }
                for rec in recommendations
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching user recommendations: {e}")
        raise HTTPException(status_code=500, detail="Error fetching recommendations")