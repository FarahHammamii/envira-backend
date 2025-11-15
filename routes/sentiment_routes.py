from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from core.database import db
from core.utils import to_objectid, to_string
from core.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sentiment"])

class SentimentAnalysisRequest(BaseModel):
    text: str
    mood_rating: Optional[int] = None  # 1-10 scale
    physical_symptoms: Optional[List[str]] = []
    current_activity: Optional[str] = None

# Simple rule-based sentiment analysis
SENTIMENT_RULES = {
    "positive": [
        "good", "great", "excellent", "happy", "joy", "love", "amazing", "wonderful",
        "fantastic", "perfect", "nice", "better", "best", "awesome", "pleased",
        "comfortable", "relaxed", "peaceful", "calm", "focused", "productive",
        "energetic", "confident", "motivated"
    ],
    "negative": [
        "bad", "terrible", "awful", "sad", "angry", "mad", "hate", "worst",
        "horrible", "uncomfortable", "stressed", "anxious", "nervous", "tired",
        "exhausted", "frustrated", "annoyed", "upset", "depressed", "sick",
        "overwhelmed", "confused", "lost"
    ],
    "neutral": [
        "okay", "fine", "normal", "average", "regular", "usual", "meh", "alright", "so-so"
    ]
}

def analyze_sentiment_simple(text: str) -> dict:
    """Simple rule-based sentiment analysis"""
    text_lower = text.lower()
    
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    
    # Count occurrences of sentiment words
    for word in SENTIMENT_RULES["positive"]:
        if word in text_lower:
            positive_count += 1
    
    for word in SENTIMENT_RULES["negative"]:
        if word in text_lower:
            negative_count += 1
    
    for word in SENTIMENT_RULES["neutral"]:
        if word in text_lower:
            neutral_count += 1
    
    # Determine sentiment
    total_keywords = positive_count + negative_count + neutral_count
    
    if total_keywords == 0:
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "score": 5,
            "keywords_found": []
        }
    
    if positive_count > negative_count and positive_count > neutral_count:
        sentiment = "positive"
        score = min(10, 5 + (positive_count * 2))
        confidence = positive_count / total_keywords
    elif negative_count > positive_count and negative_count > neutral_count:
        sentiment = "negative"
        score = max(1, 5 - (negative_count * 2))
        confidence = negative_count / total_keywords
    else:
        sentiment = "neutral"
        score = 5
        confidence = neutral_count / total_keywords
    
    # Get found keywords
    found_keywords = []
    for category, words in SENTIMENT_RULES.items():
        for word in words:
            if word in text_lower:
                found_keywords.append({"word": word, "category": category})
    
    return {
        "sentiment": sentiment,
        "score": score,
        "confidence": round(confidence, 2),
        "keywords_found": found_keywords,
        "analysis": {
            "positive_words": positive_count,
            "negative_words": negative_count,
            "neutral_words": neutral_count,
            "total_keywords": total_keywords
        }
    }

@router.post("/analyze")
async def analyze_sentiment(
    request: SentimentAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze sentiment from user text input"""
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        
        # Perform simple sentiment analysis
        analysis_result = analyze_sentiment_simple(request.text)
        
        # Store analysis in database
        sentiment_log = {
            "user_id": user_object_id,
            "text_input": request.text,
            "sentiment": analysis_result["sentiment"],
            "sentiment_score": analysis_result["score"],
            "mood_rating": request.mood_rating,
            "confidence": analysis_result["confidence"],
            "physical_symptoms": request.physical_symptoms or [],
            "current_activity": request.current_activity,
            "analysis_details": analysis_result,
            "timestamp": datetime.utcnow()
        }
        
        result = db.sentiment_logs.insert_one(sentiment_log)
        
        logger.info(f"✅ Sentiment logged for user {user_id}")
        
        return {
            "analysis_id": to_string(result.inserted_id),
            "analysis": analysis_result,
            "mood_rating": request.mood_rating,
            "timestamp": sentiment_log["timestamp"].isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error analyzing sentiment: {e}")
        raise HTTPException(status_code=500, detail="Error analyzing sentiment")

@router.get("/history")
async def get_sentiment_history(
    days: int = 7,
    current_user: dict = Depends(get_current_user)
):
    """Get sentiment analysis history for current user"""
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = list(db.sentiment_logs.find({
            "user_id": user_object_id,
            "timestamp": {"$gte": start_date}
        }).sort("timestamp", -1).limit(100))
        
        return {
            "count": len(logs),
            "days": days,
            "sentiment_history": [
                {
                    "id": to_string(log["_id"]),
                    "text_input": (log.get("text_input", "")[:80] + "...") if len(log.get("text_input", "")) > 80 else log.get("text_input", ""),
                    "sentiment": log.get("sentiment", "neutral"),
                    "sentiment_score": log.get("sentiment_score", 5),
                    "mood_rating": log.get("mood_rating"),
                    "confidence": log.get("confidence", 0.5),
                    "current_activity": log.get("current_activity"),
                    "physical_symptoms": log.get("physical_symptoms", []),
                    "timestamp": log["timestamp"].isoformat()
                }
                for log in logs
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching sentiment history: {e}")
        raise HTTPException(status_code=500, detail="Error fetching sentiment history")

@router.get("/summary")
async def get_sentiment_summary(
    days: int = 7,
    current_user: dict = Depends(get_current_user)
):
    """Get sentiment summary/statistics"""
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = list(db.sentiment_logs.find({
            "user_id": user_object_id,
            "timestamp": {"$gte": start_date}
        }))
        
        if not logs:
            return {
                "period_days": days,
                "total_entries": 0,
                "sentiment_distribution": {},
                "average_mood": None,
                "message": "No sentiment data available for this period"
            }
        
        # Calculate statistics
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        mood_ratings = []
        
        for log in logs:
            sentiment = log.get("sentiment", "neutral")
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            if log.get("mood_rating"):
                mood_ratings.append(log["mood_rating"])
        
        avg_mood = sum(mood_ratings) / len(mood_ratings) if mood_ratings else None
        
        return {
            "period_days": days,
            "total_entries": len(logs),
            "sentiment_distribution": sentiment_counts,
            "sentiment_percentages": {
                k: round(v / len(logs) * 100, 1) for k, v in sentiment_counts.items()
            },
            "average_mood_rating": round(avg_mood, 1) if avg_mood else None,
            "mood_entries_count": len(mood_ratings)
        }
    
    except Exception as e:
        logger.error(f"❌ Error calculating sentiment summary: {e}")
        raise HTTPException(status_code=500, detail="Error calculating sentiment summary")