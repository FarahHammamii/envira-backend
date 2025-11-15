from datetime import datetime
from bson import ObjectId
from typing import List, Dict, Optional

class SentimentLogs:
    def __init__(self, db):
        self.collection = db.sentiment_logs
    
    def create_sentiment_log(self, user_id: str, sentiment_data: Dict) -> str:
        log_entry = {
            "user_id": ObjectId(user_id),
            "mood_rating": sentiment_data["mood_rating"],
            "mood_tags": sentiment_data.get("mood_tags", []),
            "physical_symptoms": sentiment_data.get("physical_symptoms", []),
            "current_activity": sentiment_data.get("current_activity"),
            "environmental_context": sentiment_data.get("environmental_context", {}),
            "notes": sentiment_data.get("notes", ""),
            "timestamp": datetime.utcnow(),
            "llm_analysis": sentiment_data.get("llm_analysis", "")
        }
        result = self.collection.insert_one(log_entry)
        return str(result.inserted_id)
    
    def get_user_sentiment_history(self, user_id: str, days: int = 30) -> List[Dict]:
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        
        return list(self.collection.find({
            "user_id": ObjectId(user_id),
            "timestamp": {"$gte": start_date}
        }, sort=[("timestamp", -1)]))
    
    def update_llm_analysis(self, log_id: str, analysis: str):
        self.collection.update_one(
            {"_id": ObjectId(log_id)},
            {"$set": {"llm_analysis": analysis}}
        )
    
    def get_recent_sentiment(self, user_id: str, limit: int = 10) -> List[Dict]:
        return list(self.collection.find(
            {"user_id": ObjectId(user_id)},
            sort=[("timestamp", -1)]
        ).limit(limit))