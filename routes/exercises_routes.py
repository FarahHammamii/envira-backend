from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from core.database import db
from core.auth import get_current_user
from core.utils import to_objectid, to_string
from pydantic import BaseModel
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/exercises", tags=["exercises"])


class ExerciseSelectionRequest(BaseModel):
    """Request to start an exercise session"""
    exercise_id: str


class ExerciseStepUpdateRequest(BaseModel):
    """Update progress in current exercise step"""
    current_step: int
    notes: Optional[str] = None


class ExerciseCompletionRequest(BaseModel):
    """Mark exercise as completed"""
    notes: Optional[str] = None


@router.get("")
async def list_exercises(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of all available exercises.
    
    Optional filters:
    - category: breathing, meditation, stretching, focus, movement, relaxation
    - difficulty: beginner, intermediate, advanced
    """
    try:
        query = {}
        if category:
            query["category"] = category
        if difficulty:
            query["difficulty"] = difficulty
        
        exercises = list(db.exercises.find(query, {
            "_id": 0,
            "exercise_id": 1,
            "name": 1,
            "category": 1,
            "description": 1,
            "total_duration_seconds": 1,
            "difficulty": 1,
            "benefits": 1
        }).sort("category", 1))
        
        return {
            "count": len(exercises),
            "exercises": exercises
        }
    
    except Exception as e:
        logger.error(f"❌ Error listing exercises: {e}")
        raise HTTPException(status_code=500, detail="Error fetching exercises")


@router.get("/{exercise_id}")
async def get_exercise_detail(
    exercise_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific exercise.
    Includes all steps, guidance, cues, and environmental recommendations.
    """
    try:
        exercise = db.exercises.find_one(
            {"exercise_id": exercise_id},
            {"_id": 0}
        )
        
        if not exercise:
            raise HTTPException(status_code=404, detail=f"Exercise '{exercise_id}' not found")
        
        return exercise
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching exercise: {e}")
        raise HTTPException(status_code=500, detail="Error fetching exercise")


@router.post("/{exercise_id}/start")
async def start_exercise(
    exercise_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Start a new exercise session.
    
    This creates a record of the user starting an exercise for tracking progress
    and history.
    """
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        
        # Verify exercise exists
        exercise = db.exercises.find_one({"exercise_id": exercise_id})
        if not exercise:
            raise HTTPException(status_code=404, detail=f"Exercise '{exercise_id}' not found")
        
        # Create session record
        session = {
            "user_id": user_object_id,
            "exercise_id": exercise_id,
            "exercise_name": exercise.get("name"),
            "status": "in_progress",
            "current_step": 0,
            "started_at": datetime.utcnow(),
            "completed_at": None,
            "paused_at": None,
            "completion_percentage": 0,
            "notes": None
        }
        
        result = db.exercise_sessions.insert_one(session)
        session_id = to_string(result.inserted_id)
        
        logger.info(f"✅ User {user_id} started exercise: {exercise_id}")
        
        return {
            "session_id": session_id,
            "exercise_id": exercise_id,
            "exercise_name": exercise.get("name"),
            "total_duration_seconds": exercise.get("total_duration_seconds"),
            "total_steps": len(exercise.get("steps", [])),
            "status": "in_progress",
            "current_step": 0,
            "started_at": session["started_at"].isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error starting exercise: {e}")
        raise HTTPException(status_code=500, detail="Error starting exercise")


@router.put("/session/{session_id}/step")
async def update_exercise_step(
    session_id: str,
    request: ExerciseStepUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the current step in an ongoing exercise session.
    """
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        session_object_id = to_objectid(session_id)
        
        # Find and verify session belongs to user
        session = db.exercise_sessions.find_one({
            "_id": session_object_id,
            "user_id": user_object_id
        })
        
        if not session:
            raise HTTPException(status_code=404, detail="Exercise session not found")
        
        # Get exercise to calculate completion percentage
        exercise = db.exercises.find_one({"exercise_id": session["exercise_id"]})
        total_steps = len(exercise.get("steps", [])) if exercise else 1
        completion_percentage = int((request.current_step / total_steps) * 100)
        
        # Update session
        db.exercise_sessions.update_one(
            {"_id": session_object_id},
            {
                "$set": {
                    "current_step": request.current_step,
                    "completion_percentage": min(completion_percentage, 100),
                    "notes": request.notes
                }
            }
        )
        
        logger.info(f"✅ Updated step for session {session_id}: step {request.current_step}")
        
        return {
            "session_id": session_id,
            "current_step": request.current_step,
            "completion_percentage": completion_percentage
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating exercise step: {e}")
        raise HTTPException(status_code=500, detail="Error updating exercise step")


@router.post("/session/{session_id}/complete")
async def complete_exercise(
    session_id: str,
    request: ExerciseCompletionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark an exercise session as completed.
    
    This moves the session to "completed" status and records it in the user's
    exercise history.
    """
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        session_object_id = to_objectid(session_id)
        
        # Find session
        session = db.exercise_sessions.find_one({
            "_id": session_object_id,
            "user_id": user_object_id
        })
        
        if not session:
            raise HTTPException(status_code=404, detail="Exercise session not found")
        
        # Get exercise for total info
        exercise = db.exercises.find_one({"exercise_id": session["exercise_id"]})
        
        # Calculate actual duration
        duration = (datetime.utcnow() - session["started_at"]).total_seconds()
        
        # Update session status
        completed_at = datetime.utcnow()
        db.exercise_sessions.update_one(
            {"_id": session_object_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": completed_at,
                    "completion_percentage": 100,
                    "notes": request.notes
                }
            }
        )
        
        # Record in history
        history_record = {
            "user_id": user_object_id,
            "exercise_id": session["exercise_id"],
            "exercise_name": session["exercise_name"],
            "completed_at": completed_at,
            "duration_seconds": int(duration),
            "steps_completed": session.get("current_step", 0),
            "total_steps": len(exercise.get("steps", [])) if exercise else 0,
            "notes": request.notes
        }
        
        db.exercise_history.insert_one(history_record)
        
        logger.info(f"✅ User {user_id} completed exercise: {session['exercise_id']}")
        
        return {
            "session_id": session_id,
            "status": "completed",
            "exercise_id": session["exercise_id"],
            "exercise_name": session["exercise_name"],
            "duration_seconds": int(duration),
            "completed_at": completed_at.isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error completing exercise: {e}")
        raise HTTPException(status_code=500, detail="Error completing exercise")


@router.get("/history/user")
async def get_user_exercise_history(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the user's completed exercise history.
    
    Parameters:
    - days: Look back window (default 30 days)
    """
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        history = list(db.exercise_history.find({
            "user_id": user_object_id,
            "completed_at": {"$gte": start_date}
        }).sort("completed_at", -1))
        
        # Convert ObjectIds and calculate stats
        history_list = []
        total_minutes = 0
        
        for record in history:
            duration_minutes = record.get("duration_seconds", 0) / 60
            total_minutes += duration_minutes
            
            history_list.append({
                "exercise_id": record["exercise_id"],
                "exercise_name": record["exercise_name"],
                "completed_at": record["completed_at"].isoformat(),
                "duration_minutes": round(duration_minutes, 1),
                "steps_completed": record.get("steps_completed", 0),
                "total_steps": record.get("total_steps", 0),
                "notes": record.get("notes")
            })
        
        # Category breakdown
        category_counts = {}
        for record in history:
            exercise = db.exercises.find_one({"exercise_id": record["exercise_id"]})
            if exercise:
                category = exercise.get("category")
                category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            "period_days": days,
            "total_completed": len(history_list),
            "total_minutes": round(total_minutes, 1),
            "category_breakdown": category_counts,
            "history": history_list
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching exercise history: {e}")
        raise HTTPException(status_code=500, detail="Error fetching exercise history")


@router.get("/stats/user")
async def get_user_exercise_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get the user's exercise statistics and streaks.
    """
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        
        # Get all completed exercises
        history = list(db.exercise_history.find({
            "user_id": user_object_id
        }).sort("completed_at", -1))
        
        if not history:
            return {
                "total_exercises_completed": 0,
                "total_minutes": 0,
                "favorite_category": None,
                "current_streak": 0,
                "exercises_by_category": {}
            }
        
        # Calculate stats
        total_minutes = sum(r.get("duration_seconds", 0) for r in history) / 60
        
        # Category stats
        exercises_by_category = {}
        for record in history:
            exercise = db.exercises.find_one({"exercise_id": record["exercise_id"]})
            if exercise:
                category = exercise.get("category")
                if category not in exercises_by_category:
                    exercises_by_category[category] = 0
                exercises_by_category[category] += 1
        
        favorite_category = max(exercises_by_category, key=exercises_by_category.get) if exercises_by_category else None
        
        # Calculate streak (consecutive days)
        streak = 0
        if history:
            today = datetime.utcnow().date()
            last_date = None
            
            for record in sorted(history, key=lambda x: x["completed_at"], reverse=True):
                record_date = record["completed_at"].date()
                
                if last_date is None:
                    if record_date == today or record_date == today - timedelta(days=1):
                        streak = 1
                        last_date = record_date
                    else:
                        break
                elif record_date == last_date - timedelta(days=1):
                    streak += 1
                    last_date = record_date
                else:
                    break
        
        return {
            "total_exercises_completed": len(history),
            "total_minutes": round(total_minutes, 1),
            "favorite_category": favorite_category,
            "current_streak": streak,
            "exercises_by_category": exercises_by_category
        }
    
    except Exception as e:
        logger.error(f"❌ Error calculating exercise stats: {e}")
        raise HTTPException(status_code=500, detail="Error calculating exercise stats")


@router.get("/session/{session_id}")
async def get_session_status(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the status of an ongoing or completed exercise session.
    """
    try:
        user_id = current_user["user_id"]
        user_object_id = to_objectid(user_id)
        session_object_id = to_objectid(session_id)
        
        session = db.exercise_sessions.find_one({
            "_id": session_object_id,
            "user_id": user_object_id
        })
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get exercise details
        exercise = db.exercises.find_one({"exercise_id": session["exercise_id"]})
        current_step_details = None
        
        if exercise and session.get("current_step") > 0:
            steps = exercise.get("steps", [])
            if session["current_step"] <= len(steps):
                current_step_details = steps[session["current_step"] - 1]
        
        return {
            "session_id": session_id,
            "exercise_id": session["exercise_id"],
            "exercise_name": session["exercise_name"],
            "status": session["status"],
            "current_step": session.get("current_step", 0),
            "total_steps": len(exercise.get("steps", [])) if exercise else 0,
            "completion_percentage": session.get("completion_percentage", 0),
            "current_step_details": current_step_details,
            "elapsed_seconds": int((datetime.utcnow() - session["started_at"]).total_seconds()),
            "started_at": session["started_at"].isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching session: {e}")
        raise HTTPException(status_code=500, detail="Error fetching session")
