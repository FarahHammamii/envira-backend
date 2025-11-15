"""
Exercise models for guided wellness exercises
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class ExerciseStep(BaseModel):
    """A single step in an exercise with duration and instructions"""
    step_number: int
    title: str
    description: str
    duration_seconds: int  # How long to spend on this step
    guidance: Optional[str] = None  # Detailed guidance text
    cues: Optional[List[str]] = None  # Tips/cues for the step


class Exercise(BaseModel):
    """Predefined wellness exercise"""
    exercise_id: str = Field(..., description="Unique exercise identifier (e.g., 'breathing-4-7-8')")
    name: str = Field(..., description="Exercise name (e.g., 'Box Breathing')")
    category: str = Field(..., description="Category: breathing, meditation, stretching, focus, movement")
    description: str = Field(..., description="Short description of the exercise")
    total_duration_seconds: int = Field(..., description="Total duration in seconds")
    difficulty: str = Field(default="beginner", description="Difficulty level: beginner, intermediate, advanced")
    steps: List[ExerciseStep] = Field(..., description="Ordered list of exercise steps")
    benefits: List[str] = Field(default_factory=list, description="List of benefits (e.g., 'stress relief')")
    prerequisites: Optional[List[str]] = None  # Requirements (e.g., 'quiet space', 'mat')
    ideal_environment: Optional[Dict[str, str]] = None  # Environmental conditions (e.g., {'light': 'dim', 'sound': 'quiet'})
    frequency_recommendation: Optional[str] = None  # E.g., '2-3 times per day'
    best_time: Optional[str] = None  # E.g., 'morning', 'before bed', 'any time'


class UserExerciseSession(BaseModel):
    """Track user's exercise session"""
    user_id: str = Optional[str]
    exercise_id: str
    status: str = Field(default="in_progress", description="Status: in_progress, completed, paused, abandoned")
    started_at: datetime
    completed_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    current_step: int = 0  # Which step the user is on
    notes: Optional[str] = None
    completion_percentage: int = 0  # 0-100


class ExerciseHistory(BaseModel):
    """User's exercise activity log"""
    user_id: str
    exercise_id: str
    exercise_name: str
    completed_at: datetime
    duration_seconds: int
    steps_completed: int
    total_steps: int
    notes: Optional[str] = None
