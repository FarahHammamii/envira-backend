from datetime import datetime, timedelta
from bson import ObjectId
from typing import List, Dict, Optional

class Recommendations:
    def __init__(self, db):
        self.collection = db.recommendations
    
    def create_recommendation(self, recommendation_data: Dict) -> str:
        recommendation = {
            "user_id": ObjectId(recommendation_data["user_id"]),
            "type": recommendation_data["type"],
            "category": recommendation_data["category"],
            "priority": recommendation_data["priority"],
            "message": recommendation_data["message"],
            "actionable_steps": recommendation_data.get("actionable_steps", []),
            "trigger_conditions": recommendation_data.get("trigger_conditions", {}),
            "related_activity": recommendation_data.get("related_activity"),
            "sentiment_context": recommendation_data.get("sentiment_context", []),
            "generated_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=24),  # Default 24h expiry
            "user_feedback": {
                "helpful": None,
                "implemented": None,
                "feedback_notes": ""
            }
        }
        result = self.collection.insert_one(recommendation)
        return str(result.inserted_id)
    
    def get_user_recommendations(self, user_id: str, active_only: bool = True) -> List[Dict]:
        query = {"user_id": ObjectId(user_id)}
        if active_only:
            query["expires_at"] = {"$gt": datetime.utcnow()}
        
        return list(self.collection.find(
            query,
            sort=[("priority", -1), ("generated_at", -1)]
        ))
    
    def update_feedback(self, recommendation_id: str, feedback_data: Dict):
        update_data = {
            "user_feedback.helpful": feedback_data.get("helpful"),
            "user_feedback.implemented": feedback_data.get("implemented"),
            "user_feedback.feedback_notes": feedback_data.get("feedback_notes", "")
        }
        
        self.collection.update_one(
            {"_id": ObjectId(recommendation_id)},
            {"$set": update_data}
        )
    
    def mark_as_read(self, recommendation_id: str):
        self.collection.update_one(
            {"_id": ObjectId(recommendation_id)},
            {"$set": {"read_at": datetime.utcnow()}}
        )
    
    def delete_expired_recommendations(self):
        self.collection.delete_many({"expires_at": {"$lt": datetime.utcnow()}})