from pymongo import MongoClient
from datetime import datetime
from typing import List, Dict, Optional
from bson import ObjectId

class User:
    def __init__(self, db):
        self.collection = db.users
    
    def create_user(self, email: str, password_hash: str, name: str) -> str:
        user_data = {
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "preferences_set": False,
            "devices": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.collection.insert_one(user_data)
        return str(result.inserted_id)
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        return self.collection.find_one({"email": email})
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        return self.collection.find_one({"_id": ObjectId(user_id)})
    
    def update_user_devices(self, user_id: str, device_id: str):
        self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$addToSet": {"devices": device_id}, "$set": {"updated_at": datetime.utcnow()}}
        )
    
    def mark_preferences_set(self, user_id: str):
        self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"preferences_set": True, "updated_at": datetime.utcnow()}}
        )

class UserPreferences:
    def __init__(self, db):
        self.collection = db.user_preferences
    
    def create_preferences(self, user_id: str, preferences_data: Dict) -> str:
        preferences = {
            "user_id": ObjectId(user_id),
            "activity_preferences": preferences_data.get("activity_preferences", {}),
            "sensitivity_levels": preferences_data.get("sensitivity_levels", {}),
            "health_conditions": preferences_data.get("health_conditions", []),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.collection.insert_one(preferences)
        return str(result.inserted_id)
    
    def get_preferences_by_user_id(self, user_id: str) -> Optional[Dict]:
        return self.collection.find_one({"user_id": ObjectId(user_id)})
    
    def update_preferences(self, user_id: str, updates: Dict):
        updates["updated_at"] = datetime.utcnow()
        self.collection.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": updates}
        )
    
    def delete_preferences(self, user_id: str):
        self.collection.delete_one({"user_id": ObjectId(user_id)})