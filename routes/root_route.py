from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/")
async def root():
    """Root endpoint with complete API documentation"""
    return {
        "message": "🌿 Envira Cloud API",
        "version": "1.0.0",
        "status": "running",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "authentication": {
            "required_for": "All endpoints except /health and POST /auth/register and POST /auth/login",
            "token_type": "Bearer JWT",
            "how_to_authenticate": {
                "step_1": "POST /auth/register with email and password",
                "step_2": "POST /auth/login with email and password to get token",
                "step_3": "Include in all requests: Authorization: Bearer <your_token>",
                "step_4": "Token expires in 24 hours"
            },
            "test_in_swagger": "Click 'Authorize' button at top of /docs page"
        },
        "endpoints": {
            "authentication": {
                "POST /auth/register": "Create new user account",
                "POST /auth/login": "Get JWT token (required for other endpoints)",
                "POST /auth/verify-token": "Check if token is valid"
            },
            "user_profile": {
                "GET /users/me": "Get current user profile",
                "GET /users/profile": "Alias for /users/me",
                "GET /users/devices": "List user's associated devices",
                "PUT /users/preferences": "Update activity preferences and sensitivity levels"
            },
            "devices": {
                "GET /devices": "List all registered devices",
                "GET /devices/{device_id}": "Get device metadata",
                "POST /devices/register": "Register a new device",
                "PUT /devices/{device_id}": "Update device information",
                "DELETE /devices/{device_id}": "Delete a device",
                "POST /devices/associate-default": "Bulk associate esp32-001 to all users",
                "GET /devices/{device_id}/data": "Get historical telemetry data (limit=50, hours=24)"
            },
            "telemetry": {
                "GET /latest/{device_id}": "Get most recent sensor readings",
                "GET /latest/device/{device_id}/summary": "Get latest data with trend analysis"
            },
            "recommendations": {
                "POST /recommendations/general": "Generate environmental recommendations",
                "POST /recommendations/activity": "Generate activity-specific recommendations",
                "GET /recommendations/activities": "List all available activities",
                "GET /recommendations/user": "Get user's active recommendations (4-hour expiry)"
            },
            "exercises": {
                "GET /exercises": "List exercises (filters: category, difficulty)",
                "GET /exercises/{exercise_id}": "Get exercise with all steps",
                "POST /exercises/{exercise_id}/start": "Begin exercise session",
                "GET /exercises/session/{session_id}": "Check session progress",
                "PUT /exercises/session/{session_id}/step": "Update current step",
                "POST /exercises/session/{session_id}/complete": "Mark exercise as completed",
                "GET /exercises/history/user": "Get past exercises (30-day window)",
                "GET /exercises/stats/user": "Get streaks and favorite exercises"
            },
            "health": {
                "GET /health": "Health check (no authentication required)"
            },
            "websocket": {
                "WS /ws": "Real-time data updates"
            }
        },
        "quick_start": {
            "1_create_account": "POST to /auth/register with {\"email\": \"your@email.com\", \"password\": \"secure_password\", \"name\": \"Your Name\"}",
            "2_get_token": "POST to /auth/login with {\"email\": \"your@email.com\", \"password\": \"secure_password\"}",
            "3_test_endpoints": "Use the token in Authorization header: Authorization: Bearer <token>",
            "4_interactive_docs": "Visit /docs for interactive Swagger UI to test all endpoints"
        },
        "sensor_ranges": {
            "temperature": "-40 to 85°C",
            "humidity": "0-100%",
            "air_quality": "0-100 (0=clean, 100=poor)",
            "light": "0-1000 lux",
            "sound": "30-100 dB",
            "ieq_score": "0-100 (40% AQ + 30% Temp + 20% Light + 10% Sound)"
        },
        "default_device": {
            "device_id": "esp32-001",
            "description": "All users are automatically associated with this device on registration",
            "note": "You can register additional devices with POST /devices/register"
        }
    }
