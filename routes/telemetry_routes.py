from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from core.database import db
from core.auth import get_current_user
from core.utils import to_string
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["telemetry"])

@router.get("/{device_id}")
async def get_telemetry(
    device_id: str,
    limit: int = 100,
    hours: int = 24,
    current_user: dict = Depends(get_current_user)
):
    """
    Get historical telemetry data for a device
    - limit: Maximum number of records to return (default: 100)
    - hours: Look back window in hours (default: 24)
    """
    try:
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        
        telemetry_data = list(db.telemetry_collection.find(
            {
                "device_id": device_id,
                "processed_at": {"$gte": time_threshold}
            },
            {
                "_id": 1,
                "device_id": 1,
                "site_id": 1,
                "sensors": 1,
                "ieq_score": 1,
                "processed_at": 1,
                "timestamp": 1
            }
        ).sort("processed_at", -1).limit(limit))
        
        # Convert ObjectId to string in response
        for record in telemetry_data:
            record["_id"] = to_string(record["_id"])
        
        return {
            "device_id": device_id,
            "count": len(telemetry_data),
            "time_window_hours": hours,
            "data": telemetry_data
        }

    except Exception as e:
        logger.error(f"❌ Error fetching telemetry: {e}")
        raise HTTPException(status_code=500, detail="Error fetching telemetry")

