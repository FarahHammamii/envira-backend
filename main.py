from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.mqtt_client import connect_mqtt
from core.database import db
from routes.root_route import router as root_router
from dotenv import load_dotenv
load_dotenv()
from routes.device_routes import router as device_router
from routes.health_routes import router as health_router
from routes.websocket_route import router as ws_router
import asyncio
import logging
from routes.auth_routes import router as auth_router
from routes.user_routes import router as user_router

from routes.recommendation_routes import router as recommendation_router
from routes.exercises_routes import router as exercises_router

from routes.latest_routes import router as latest_router

app = FastAPI(title="Envira Cloud API", version="2.0")

# Add explicit OpenAPI security schema so Swagger UI shows the Authorize button
from fastapi.openapi.utils import get_openapi


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    # Define a Bearer (JWT) security scheme
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    # Apply globally so protected endpoints will present the Authorize control
    openapi_schema.setdefault("security", [])
    openapi_schema["security"].append({"BearerAuth": []})

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

@app.on_event("startup")
async def startup():
    # Seed exercises if not already in database
    from models.exercise_seed import seed_exercises
    seed_exercises(db)
    
    asyncio.create_task(connect_mqtt())

@app.on_event("shutdown")
async def shutdown():
    db.client.close()

# Routers
app.include_router(root_router)
app.include_router(health_router)
# telemetry router not included to avoid redundancy
app.include_router(device_router)
app.include_router(ws_router)
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(latest_router, tags=["latest-data"])
app.include_router(recommendation_router, prefix="/recommendations", tags=["recommendations"])
app.include_router(exercises_router, tags=["exercises"])
# Sentiment routes removed per configuration

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
