from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from core.database import db
from core.utils import to_objectid, to_string
from core.auth import get_current_user
import logging
import os
import json
from groq import Groq

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
if not os.getenv("GROQ_API_KEY"):
    logger.error("❌ GROQ_API_KEY not found in environment variables")
class ActivityRecommendationRequest(BaseModel):
    activity_id: str = Field(..., description="Activity ID, ID field, or name", example="studying")
    device_id: str = Field(..., description="Device to analyze", example="esp32-001")

class GeneralRecommendationRequest(BaseModel):
    device_id: str = Field(..., description="Device to analyze", example="esp32-001")

class SensorDataResponse(BaseModel):
    temperature: Optional[float] = Field(None, description="Current temperature (Celsius)")
    humidity: Optional[float] = Field(None, description="Current humidity (%)")
    air_quality: Optional[float] = Field(None, description="Air quality (0-100)")
    light: Optional[float] = Field(None, description="Light level (lux)")
    sound: Optional[float] = Field(None, description="Sound level (dB)")

class GeneralRecommendationResponse(BaseModel):
    recommendation_id: str = Field(..., description="Unique recommendation ID")
    recommendation_type: str = Field(..., description="Type of recommendation", example="general_environmental")
    device_id: str = Field(..., description="Device analyzed")
    environmental_score: float = Field(..., description="IEQ Score (0-100)")
    recommendations: List[str] = Field(..., description="List of actionable recommendations")
    sensor_data: SensorDataResponse = Field(..., description="Current sensor readings")
    generated_at: str = Field(..., description="ISO timestamp when generated")

class ActivityRecommendationResponse(BaseModel):
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
    activity_id: str = Field(..., description="Unique activity identifier")
    name: str = Field(..., description="Activity name")
    description: str = Field(..., description="Activity description")
    category: str = Field(..., description="Activity category")
    ideal_conditions: Dict = Field(..., description="Ideal environmental conditions")

class ActivitiesListResponse(BaseModel):
    count: int = Field(..., description="Number of activities")
    activities: List[ActivityInfo] = Field(..., description="Array of activity info")

class RecommendationItem(BaseModel):
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
    count: int = Field(..., description="Number of recommendations")
    recommendations: List[RecommendationItem] = Field(..., description="Array of recommendations")

def get_latest_device_data(device_id: str) -> Dict:
    """Get latest sensor data for a device"""
    latest_data = db.telemetry_collection.find_one({"device_id": device_id}, sort=[("processed_at", -1)])

    if not latest_data:
        raise HTTPException(status_code=404, detail="No data found for device")

    sensors = latest_data.get("sensors", {}) or {}
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

    if sensors and all(v is None for v in sensors.values()):
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

def call_groq_llm(prompt: str, max_tokens: int = 800) -> str:
    """Call Groq LLM with the given prompt"""
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",  
            temperature=0.7,
            max_tokens=max_tokens,
            top_p=1
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ Error calling Groq LLM: {e}")
        raise HTTPException(status_code=500, detail="AI service temporarily unavailable")

def generate_smart_general_recommendations(sensor_data: Dict) -> List[str]:
    """Generate smart general recommendations using LLM"""
    
    # Prepare sensor data for LLM
    sensor_info = {
        "temperature": f"{sensor_data.get('temperature', 'N/A')}°C" if sensor_data.get('temperature') is not None else "Not available",
        "humidity": f"{sensor_data.get('humidity', 'N/A')}%" if sensor_data.get('humidity') is not None else "Not available",
        "light": f"{sensor_data.get('light', 'N/A')} lux" if sensor_data.get('light') is not None else "Not available",
        "sound": f"{sensor_data.get('sound', 'N/A')} dB" if sensor_data.get('sound') is not None else "Not available",
        "air_quality": f"{sensor_data.get('air_quality', 'N/A')}/100" if sensor_data.get('air_quality') is not None else "Not available",
        "environmental_score": f"{sensor_data.get('ieq_score', 50)}/100"
    }
    
    prompt = f"""
    As an environmental optimization expert, analyze this sensor data and provide 3-5 specific, actionable recommendations to improve the indoor environment quality.

    CURRENT SENSOR READINGS:
    {json.dumps(sensor_info, indent=2)}

    IDEAL RANGES FOR REFERENCE:
    - Temperature: 20-24°C
    - Humidity: 40-60%
    - Light: 300-600 lux
    - Sound: 0-40 dB
    - Air Quality: 70-100/100

    Please provide:
    1. Specific, practical recommendations based on deviations from ideal ranges
    2. Prioritize health and comfort improvements
    3. Include both immediate actions and longer-term suggestions
    4. Consider energy efficiency where applicable
    5. Make recommendations clear and easy to implement

    Format your response as a JSON array of strings, each string being one recommendation. Example: ["Recommendation 1", "Recommendation 2"]

    Only return the JSON array, no additional text.
    """
    
    try:
        response = call_groq_llm(prompt)
        # Extract JSON array from response
        if response.startswith('[') and response.endswith(']'):
            recommendations = json.loads(response)
        else:
            # Fallback if LLM doesn't return pure JSON
            lines = [line.strip('- ').strip() for line in response.split('\n') if line.strip()]
            recommendations = [line for line in lines if line and not line.startswith('[') and not line.startswith('{')]
        
        return recommendations[:5] if recommendations else ["Environment conditions are generally acceptable. Maintain current settings."]
    
    except Exception as e:
        logger.error(f"❌ Error in smart general recommendations: {e}")
        return generate_fallback_recommendations(sensor_data)

def generate_smart_activity_recommendations(activity_id: str, sensor_data: Dict, user_preferences: Dict) -> List[str]:
    """Generate smart activity-specific recommendations using LLM"""
    
    # Get activity details
    activity = None
    try:
        activity_obj = to_objectid(activity_id)
        activity = db.activities.find_one({"_id": activity_obj})
    except Exception:
        activity = None

    if not activity:
        activity = db.activities.find_one({"activity_id": activity_id})

    if not activity:
        activity = db.activities.find_one({"name": {"$regex": f"^{activity_id}$", "$options": "i"}})

    if not activity:
        raise HTTPException(status_code=404, detail=f"Activity '{activity_id}' not found")
    
    activity_name = activity.get("name", activity_id)
    activity_description = activity.get("description", "")
    ideal_conditions = activity.get("ideal_conditions", {})
    
    # 🔍 COMPREHENSIVE DEBUGGING: Check preference lookup
    logger.info(f"🔍 ACTIVITY RECOMMENDATION DEBUG START")
    logger.info(f"🔍 Input activity_id: {activity_id}")
    logger.info(f"🔍 Found activity name: {activity_name}")
    logger.info(f"🔍 All user preferences keys: {list(user_preferences.keys())}")
    
    # Get ALL activity preferences
    all_activity_prefs = user_preferences.get("activity_preferences", {})
    logger.info(f"🔍 Available activity preferences: {list(all_activity_prefs.keys())}")
    
    # FLEXIBLE PREFERENCE LOOKUP: Try multiple matching strategies
    activity_prefs = {}
    
    # Strategy 1: Exact activity_id match
    if activity_id in all_activity_prefs:
        activity_prefs = all_activity_prefs[activity_id]
        logger.info(f"✅ Found preferences by exact activity_id: {activity_id}")
    
    # Strategy 2: Exact activity name match  
    elif activity_name in all_activity_prefs:
        activity_prefs = all_activity_prefs[activity_name]
        logger.info(f"✅ Found preferences by exact activity name: {activity_name}")
    
    # Strategy 3: Case-insensitive name match
    else:
        for pref_key in all_activity_prefs.keys():
            if pref_key.lower() == activity_name.lower():
                activity_prefs = all_activity_prefs[pref_key]
                logger.info(f"✅ Found preferences by case-insensitive match: {pref_key} -> {activity_name}")
                break
            # Also try matching activity_id with preference keys
            elif pref_key.lower() == activity_id.lower():
                activity_prefs = all_activity_prefs[pref_key]
                logger.info(f"✅ Found preferences by activity_id case-insensitive match: {pref_key} -> {activity_id}")
                break
    
    # Strategy 4: Partial name matching (for activities like "programming/coding" vs "coding")
    if not activity_prefs:
        for pref_key in all_activity_prefs.keys():
            if (activity_name.lower() in pref_key.lower()) or (pref_key.lower() in activity_name.lower()):
                activity_prefs = all_activity_prefs[pref_key]
                logger.info(f"✅ Found preferences by partial name match: {pref_key} -> {activity_name}")
                break
    
    # Final debug output
    if activity_prefs:
        logger.info(f"🎯 USING PREFERENCES: {json.dumps(activity_prefs, indent=2)}")
    else:
        logger.info("❌ NO MATCHING PREFERENCES FOUND")
        logger.info(f"💡 Tried to match: activity_id='{activity_id}', activity_name='{activity_name}'")
        logger.info(f"💡 Available preference keys: {list(all_activity_prefs.keys())}")
    
    # Also include sensitivity levels and health conditions
    sensitivity_levels = user_preferences.get("sensitivity_levels", {})
    health_conditions = user_preferences.get("health_conditions", [])
    
    logger.info(f"🔍 Sensitivity levels: {sensitivity_levels}")
    logger.info(f"🔍 Health conditions: {health_conditions}")
    logger.info(f"🔍 ACTIVITY RECOMMENDATION DEBUG END")
    
    # Prepare data for LLM
    sensor_info = {
        "temperature": f"{sensor_data.get('temperature', 'N/A')}°C" if sensor_data.get('temperature') is not None else "Not available",
        "humidity": f"{sensor_data.get('humidity', 'N/A')}%" if sensor_data.get('humidity') is not None else "Not available",
        "light": f"{sensor_data.get('light', 'N/A')} lux" if sensor_data.get('light') is not None else "Not available",
        "sound": f"{sensor_data.get('sound', 'N/A')} dB" if sensor_data.get('sound') is not None else "Not available",
        "air_quality": f"{sensor_data.get('air_quality', 'N/A')}/100" if sensor_data.get('air_quality') is not None else "Not available",
        "environmental_score": f"{sensor_data.get('ieq_score', 50)}/100"
    }
    
    # Prepare comprehensive user preferences context
    preferences_context_parts = []
    
    if activity_prefs:
        preferences_context_parts.append(f"USER PREFERENCES FOR THIS ACTIVITY: {json.dumps(activity_prefs, indent=2)}")
    
    if sensitivity_levels:
        preferences_context_parts.append(f"USER ENVIRONMENTAL SENSITIVITY LEVELS: {json.dumps(sensitivity_levels, indent=2)}")
    
    if health_conditions:
        preferences_context_parts.append(f"USER HEALTH CONDITIONS: {', '.join(health_conditions)}")
    
    preferences_context = "\n".join(preferences_context_parts)
    if preferences_context:
        preferences_context = "\n" + preferences_context
    
    # Enhanced prompt with all user context
    prompt = f"""
    As an environmental and productivity optimization expert, provide personalized recommendations for someone preparing to do this activity:

    ACTIVITY: {activity_name}
    DESCRIPTION: {activity_description}
    
    CURRENT ENVIRONMENTAL CONDITIONS:
    {json.dumps(sensor_info, indent=2)}
    
    IDEAL CONDITIONS FOR {activity_name.upper()}:
    {json.dumps(ideal_conditions, indent=2)}
    {preferences_context}

    Please provide 3-5 specific, actionable recommendations that:
    1. Optimize the environment specifically for {activity_name}
    2. Address any deviations from ideal conditions
    3. Consider the user's specific preferences, sensitivities, and health conditions
    4. Include activity-specific tips and best practices
    5. Are practical and easy to implement
    6. Prioritize recommendations based on user's sensitivity levels

    Format your response as a JSON array of strings, each string being one recommendation. Example: ["Recommendation 1", "Recommendation 2"]

    Only return the JSON array, no additional text.
    """
    
    # Log the final prompt (truncated for readability)
    logger.info(f"📝 LLM Prompt Summary - Activity: {activity_name}, Preferences used: {bool(activity_prefs)}")
    
    try:
        response = call_groq_llm(prompt)
        
        # Log the raw LLM response
        logger.info(f"🤖 LLM Raw Response: {response[:200]}...")
        
        # Extract JSON array from response
        if response.startswith('[') and response.endswith(']'):
            recommendations = json.loads(response)
        else:
            # Fallback if LLM doesn't return pure JSON
            lines = [line.strip('- ').strip() for line in response.split('\n') if line.strip()]
            recommendations = [line for line in lines if line and not line.startswith('[') and not line.startswith('{')]
        
        # Final success log
        if recommendations:
            logger.info(f"✅ Generated {len(recommendations)} recommendations for {activity_name}")
            for i, rec in enumerate(recommendations):
                logger.info(f"   {i+1}. {rec}")
        else:
            logger.warning(f"⚠️ No recommendations generated for {activity_name}")
        
        return recommendations[:5] if recommendations else [f"Environment is suitable for {activity_name}. You're good to start!"]
    
    except Exception as e:
        logger.error(f"❌ Error in smart activity recommendations: {e}")
        return generate_fallback_activity_recommendations(activity_name, sensor_data, ideal_conditions)

def generate_fallback_recommendations(sensor_data: Dict) -> List[str]:
    """Fallback recommendations when LLM fails"""
    recommendations = []
    
    temp = sensor_data.get("temperature")
    if temp is not None:
        if temp < 18:
            recommendations.append("Room is cold - Consider increasing temperature or wearing warmer clothes")
        elif temp > 26:
            recommendations.append("Room is warm - Consider decreasing temperature or wearing lighter clothes")
    
    humidity = sensor_data.get("humidity")
    if humidity is not None:
        if humidity < 35:
            recommendations.append("Air is dry - Use a humidifier to increase moisture")
        elif humidity > 65:
            recommendations.append("Air is humid - Use a dehumidifier to reduce moisture")
    
    light = sensor_data.get("light")
    if light is not None:
        if light < 200:
            recommendations.append("Lighting is insufficient - Increase lights in the room")
        elif light > 700:
            recommendations.append("Too much light - Reduce direct lighting")
    
    sound = sensor_data.get("sound")
    if sound is not None and sound > 50:
        recommendations.append("Noise level is high - Move to a quieter location if possible")
    
    air_quality = sensor_data.get("air_quality")
    if air_quality is not None and air_quality < 60:
        recommendations.append("Air quality is poor - Improve room ventilation immediately")
    
    return recommendations[:3] if recommendations else ["Environment conditions are acceptable"]

def generate_fallback_activity_recommendations(activity_name: str, sensor_data: Dict, ideal_conditions: Dict) -> List[str]:
    """Fallback activity recommendations when LLM fails"""
    recommendations = []
    
    current_temp = sensor_data.get("temperature")
    ideal_temp_range = ideal_conditions.get("temperature", [21, 23])
    if current_temp is not None and ideal_temp_range:
        ideal_temp_mid = sum(ideal_temp_range) / 2
        temp_diff = abs(current_temp - ideal_temp_mid)
        if temp_diff > 3:
            if current_temp < ideal_temp_mid:
                recommendations.append(f"For {activity_name}: Room is {temp_diff:.1f}°C cooler than ideal. Increase temperature for better comfort.")
            else:
                recommendations.append(f"For {activity_name}: Room is {temp_diff:.1f}°C warmer than ideal. Improve cooling for better focus.")
    
    current_light = sensor_data.get("light")
    ideal_light_range = ideal_conditions.get("light", [400, 600])
    if current_light is not None and ideal_light_range:
        ideal_light_mid = sum(ideal_light_range) / 2
        light_diff = abs(current_light - ideal_light_mid)
        if light_diff > 150:
            if current_light < ideal_light_mid:
                recommendations.append(f"For {activity_name}: Increase lighting to improve visibility.")
            else:
                recommendations.append(f"For {activity_name}: Reduce lighting to prevent eye strain.")
    
    # Activity-specific fallback tips
    activity_tips = {
        "studying": ["Take regular breaks using the Pomodoro technique", "Ensure proper desk and chair ergonomics"],
        "coding": ["Practice the 20-20-20 rule for eye care", "Maintain good posture while working"],
        "reading": ["Ensure adequate lighting from behind or side", "Take breaks to prevent eye strain"],
        "relaxing": ["Create a calm, clutter-free environment", "Use soft lighting for relaxation"],
        "exercising": ["Ensure good air circulation", "Stay hydrated during your workout"],
        "creative": ["Minimize interruptions for better flow", "Organize your materials for easy access"]
    }
    
    activity_name_key = activity_name.lower()
    if activity_name_key in activity_tips:
        recommendations.extend(activity_tips[activity_name_key])
    
    return recommendations[:4] if recommendations else [f"Environment is suitable for {activity_name}. You're good to start!"]

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
    """Generate smart general environmental recommendations using AI.
    
    Uses Groq's LLM to analyze current environmental data and provide intelligent,
    context-aware recommendations for optimizing the indoor environment.
    """
    try:
        user_id = current_user["user_id"]
        
        # Get latest device data
        sensor_data = get_latest_device_data(request.device_id)
        
        # Generate smart recommendations using LLM
        recommendations = generate_smart_general_recommendations(sensor_data)
        
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
    """Generate smart activity-specific recommendations using AI.
    
    Uses Groq's LLM to analyze environmental data and user preferences, providing
    personalized recommendations tailored to specific activities.
    """
    try:
        user_id = current_user["user_id"]
        
        # Get latest device data
        sensor_data = get_latest_device_data(request.device_id)
        
        # Get user preferences
        user_object_id = to_objectid(user_id)
        user_preferences = db.user_preferences.find_one({"user_id": user_object_id}) or {}
        
        # Generate smart activity recommendations using LLM
        recommendations = generate_smart_activity_recommendations(
            request.activity_id, 
            sensor_data, 
            user_preferences
        )
        
        # Resolve activity details
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
    """Get list of all predefined activities available for recommendations."""
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
    """Get all active recommendations for the current user."""
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        
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