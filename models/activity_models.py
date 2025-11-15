from datetime import datetime
from bson import ObjectId
from typing import List, Dict, Optional

class Activities:
    def __init__(self, db):
        self.collection = db.activities
    
    def create_activity(self, activity_data: Dict) -> str:
        activity = {
            "name": activity_data["name"],
            "category": activity_data["category"],
            "description": activity_data["description"],
            "duration_minutes": activity_data["duration_minutes"],
            "ideal_conditions": activity_data["ideal_conditions"],
            "recommendations": activity_data.get("recommendations", []),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.collection.insert_one(activity)
        return str(result.inserted_id)
    
    def get_all_activities(self) -> List[Dict]:
        return list(self.collection.find({}))
    
    def get_activities_by_category(self, category: str) -> List[Dict]:
        return list(self.collection.find({"category": category}))
    
    def get_activity_by_id(self, activity_id: str) -> Optional[Dict]:
        return self.collection.find_one({"_id": ObjectId(activity_id)})
    
    def update_activity(self, activity_id: str, updates: Dict):
        updates["updated_at"] = datetime.utcnow()
        self.collection.update_one(
            {"_id": ObjectId(activity_id)},
            {"$set": updates}
        )
    
    def delete_activity(self, activity_id: str):
        self.collection.delete_one({"_id": ObjectId(activity_id)})

class UserActivities:
    def __init__(self, db):
        self.collection = db.user_activities
    
    def log_activity(self, user_id: str, activity_id: str, environmental_data: Dict) -> str:
        log_entry = {
            "user_id": ObjectId(user_id),
            "activity_id": ObjectId(activity_id),
            "environmental_context": environmental_data,
            "started_at": datetime.utcnow(),
            "completed": False
        }
        result = self.collection.insert_one(log_entry)
        return str(result.inserted_id)
    
    def complete_activity(self, log_id: str, sentiment_data: Dict = None):
        update_data = {
            "completed": True,
            "completed_at": datetime.utcnow()
        }
        if sentiment_data:
            update_data["sentiment_data"] = sentiment_data
        
        self.collection.update_one(
            {"_id": ObjectId(log_id)},
            {"$set": update_data}
        )
    
    def get_user_activity_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        return list(self.collection.find(
            {"user_id": ObjectId(user_id)},
            sort=[("started_at", -1)]
        ).limit(limit))