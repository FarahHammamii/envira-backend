from pymongo import MongoClient
from datetime import datetime
import os
import logging

from .config import MONGODB_URL
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.MONGODB_URL = MONGODB_URL
        self.client = MongoClient(MONGODB_URL)
        self.db = self.client.envira

        
        # Existing collections (keep for backward compatibility)
        self.telemetry_collection = self.db.telemetry
        self.devices_collection = self.db.devices
        self.users_collection = self.db.users
        
        # New collections for enhanced features
        self.user_preferences = self.db.user_preferences
        self.activities = self.db.activities
        self.user_activities = self.db.user_activities
        self.sentiment_logs = self.db.sentiment_logs
        self.recommendations = self.db.recommendations
        
        # Exercise collections
        self.exercises = self.db.exercises
        self.exercise_sessions = self.db.exercise_sessions
        self.exercise_history = self.db.exercise_history
        
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize database with default data"""
        try:
            # Initialize default device (existing functionality)
            self.devices_collection.update_one(
                {"device_id": "esp32-001"},
                {"$set": {
                    "device_id": "esp32-001",
                    "site_id": "home",
                    "name": "Main Sensor",
                    "created_at": datetime.utcnow(),
                    "sensors": ["temperature", "humidity", "air_quality", "light", "sound"]
                }},
                upsert=True
            )
            self.initialize_default_user()

            
            # Initialize default activities (new functionality)
            self.initialize_default_activities()
            
            logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
    def initialize_default_user(self):
        """Create a default admin user if no users exist"""
        import hashlib
        
        def hash_password(password: str) -> str:
            return hashlib.sha256(password.encode()).hexdigest()
        
        # Check if any users exist
        existing_users = self.users_collection.count_documents({})
        
        if existing_users == 0:
            default_user = {
                "email": "admin@envira.com",
                "password_hash": hash_password("admin123"),
                "name": "Envira Admin",
                "preferences_set": False,
                "devices": ["esp32-001"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            user_id = self.users_collection.insert_one(default_user).inserted_id
            logger.info(f"✅ Created default admin user: admin@envira.com")
            
            # Also create default preferences for this user
            default_preferences = {
                "user_id": user_id,
                "activity_preferences": {
                    "studying": {
                        "ideal_temperature": 22,
                        "ideal_humidity": 45,
                        "ideal_light": 600,
                        "ideal_noise": 30,
                        "priority": "high"
                    },
                    "sleeping": {
                        "ideal_temperature": 20,
                        "ideal_humidity": 50,
                        "ideal_light": 10,
                        "ideal_noise": 20,
                        "priority": "high"
                    },
                    "exercising": {
                        "ideal_temperature": 18,
                        "ideal_humidity": 40,
                        "ideal_light": 300,
                        "ideal_noise": 50,
                        "priority": "medium"
                    }
                },
                "sensitivity_levels": {
                    "temperature": "medium",
                    "noise": "high",
                    "light": "medium",
                    "air_quality": "high"
                },
                "health_conditions": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            self.user_preferences.insert_one(default_preferences)
            logger.info("✅ Created default user preferences")
    def initialize_default_activities(self):
        """Initialize default activities in the database"""
        default_activities = [
            {
                "activity_id": "studying",
                "name": "Studying/Learning",
                "description": "Focus-intensive learning, reading, or academic work",
                "category": "focus",
                "ideal_conditions": {
                    "temperature": [20, 23],
                    "humidity": [40, 50],
                    "light": [300, 600],
                    "sound": [0, 35],
                    "air_quality": [70, 100]
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "activity_id": "coding",
                "name": "Programming/Coding",
                "description": "Software development, debugging, or technical work",
                "category": "focus",
                "ideal_conditions": {
                    "temperature": [21, 24],
                    "humidity": [40, 55],
                    "light": [400, 700],
                    "sound": [20, 45],
                    "air_quality": [70, 100]
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "activity_id": "reading",
                "name": "Reading",
                "description": "Leisure reading or research",
                "category": "relaxation",
                "ideal_conditions": {
                    "temperature": [21, 24],
                    "humidity": [40, 55],
                    "light": [500, 800],
                    "sound": [0, 30],
                    "air_quality": [70, 100]
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "activity_id": "relaxing",
                "name": "Relaxing/Meditation",
                "description": "Meditation, rest, or casual activities",
                "category": "relaxation",
                "ideal_conditions": {
                    "temperature": [21, 24],
                    "humidity": [45, 55],
                    "light": [100, 300],
                    "sound": [0, 25],
                    "air_quality": [75, 100]
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "activity_id": "exercising",
                "name": "Exercising",
                "description": "Physical workout or stretching",
                "category": "physical",
                "ideal_conditions": {
                    "temperature": [18, 21],
                    "humidity": [40, 50],
                    "light": [200, 500],
                    "sound": [30, 60],
                    "air_quality": [65, 100]
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "activity_id": "creative",
                "name": "Creative Work",
                "description": "Writing, designing, or artistic activities",
                "category": "creative",
                "ideal_conditions": {
                    "temperature": [21, 24],
                    "humidity": [40, 55],
                    "light": [400, 700],
                    "sound": [20, 45],
                    "air_quality": [70, 100]
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        # Only insert if activities don't exist
        existing_count = self.activities.count_documents({})
        if existing_count == 0:
            self.activities.insert_many(default_activities)
            logger.info(f"✅ Inserted {len(default_activities)} default activities")
        else:
            # Update existing activities to new structure
            for activity in default_activities:
                self.activities.update_one(
                    {"activity_id": activity["activity_id"]},
                    {"$set": activity},
                    upsert=True
                )
            logger.info(f"✅ Updated activities to new structure")

# Global database instance
db = Database()