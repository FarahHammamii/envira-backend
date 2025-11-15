from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel, EmailStr, Field
from core.database import db
from core.utils import to_objectid, to_string
from core.auth import hash_password, verify_password, create_access_token
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class UserRegister(BaseModel):
    """User registration request schema"""
    email: str = Field(..., description="User email address", example="john@example.com")
    password: str = Field(..., description="Password (min 6 characters recommended)", example="secure123")
    name: str = Field(..., description="User's full name", example="John Doe")

class UserLogin(BaseModel):
    """User login request schema"""
    email: str = Field(..., description="Registered email address", example="john@example.com")
    password: str = Field(..., description="User password", example="secure123")

class TokenResponse(BaseModel):
    """Successful login response with JWT token"""
    access_token: str = Field(..., description="JWT token to use in Authorization header")
    token_type: str = Field(..., description="Token type (always 'bearer')", example="bearer")
    user_id: str = Field(..., description="Unique user identifier")
    name: str = Field(..., description="User's full name")
    email: str = Field(..., description="User's email address")

class RegistrationResponse(BaseModel):
    """Successful registration response"""
    message: str = Field(..., example="User registered successfully")
    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="Registered email address")
    name: str = Field(..., description="User's name")

class TokenVerificationResponse(BaseModel):
    """Token verification response"""
    valid: bool = Field(..., description="Whether the token is valid")
    user_id: str = Field(..., description="User ID from token")
    email: str = Field(..., description="User email from token")

@router.post("/register", response_model=RegistrationResponse, responses={
    400: {"description": "Email already registered or missing required fields"},
    500: {"description": "Server error during registration"}
})
async def register(user_data: UserRegister = Body(..., example={
    "email": "john@example.com",
    "password": "secure123",
    "name": "John Doe"
})):
    """
    Register a new user account.
    
    **Request Body:**
    - `email`: Valid email address (must be unique)
    - `password`: Secure password (recommend at least 6 characters)
    - `name`: User's full name
    
    **Response:**
    Returns user_id, email, and name if successful.
    
    **Errors:**
    - 400: Email already registered or invalid input
    - 500: Server error
    
    **Note:** New users are automatically associated with the default device (esp32-001).
    """
    try:
        # Validate input
        if not user_data.email or not user_data.password or not user_data.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email, password, and name are required"
            )
        
        # Check if user already exists
        existing_user = db.users_collection.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user with hashed password
        user_doc = {
            "email": user_data.email,
            "password_hash": hash_password(user_data.password),
            "name": user_data.name,
            "preferences_set": False,
            # Ensure new users are associated with the default device
            "devices": ["esp32-001"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.users_collection.insert_one(user_doc)
        user_id = to_string(result.inserted_id)
        # Ensure default device exists in devices collection and set ownership
        default_device_id = "esp32-001"
        existing_device = db.devices_collection.find_one({"device_id": default_device_id})
        if not existing_device:
            device_doc = {
                "device_id": default_device_id,
                "name": "Default Device",
                "site_id": "home",
                "sensors": ["temperature", "humidity", "air_quality", "light", "sound"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "owner": user_id
            }
            db.devices_collection.insert_one(device_doc)
        else:
            # Add owner if missing
            db.devices_collection.update_one({"device_id": default_device_id}, {"$set": {"owner": user_id, "updated_at": datetime.utcnow()}})

        logger.info(f"✅ User registered: {user_data.email}")
        
        return {
            "message": "User registered successfully",
            "user_id": user_id,
            "email": user_data.email,
            "name": user_data.name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=TokenResponse, responses={
    401: {"description": "Invalid email or password"},
    500: {"description": "Server error during login"}
})
async def login(login_data: UserLogin = Body(..., example={
    "email": "admin@envira.com",
    "password": "admin123"
})):
    """
    Login user and receive JWT access token.
    
    **Request Body:**
    - `email`: Registered email address
    - `password`: Account password
    
    **Response:**
    Returns JWT token with 24-hour expiration and user information.
    
    **Usage:**
    1. Call this endpoint with credentials
    2. Copy the `access_token` from response
    3. Use it in all subsequent requests: `Authorization: Bearer <access_token>`
    
    **Token Type:** Bearer JWT (HS256 signed)
    **Expiration:** 24 hours
    
    **Errors:**
    - 401: Invalid credentials
    - 500: Server error
    """
    try:
        # Find user by email
        user = db.users_collection.find_one({"email": login_data.email})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(login_data.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create JWT token
        user_id = to_string(user["_id"])
        access_token = create_access_token(user_id=user_id, email=user["email"])
        
        logger.info(f"✅ User logged in: {user['email']}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "name": user["name"],
            "email": user["email"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/verify-token", response_model=TokenVerificationResponse, responses={
    401: {"description": "Invalid or expired token"},
    500: {"description": "Server error"}
})
async def verify_token_endpoint(token: str = Body(..., embed=True, example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")):
    """
    Verify if a JWT token is still valid.
    
    **Request Body:**
    - `token`: JWT token string to verify
    
    **Response:**
    Returns validity status and token claims (user_id, email) if valid.
    
    **Use Case:**
    - Frontend can call this to verify token before making API calls
    - Check if token needs refresh
    - Verify token hasn't expired (24 hours from issue)
    
    **Errors:**
    - 401: Token is invalid or expired
    - 500: Server error
    """
    from core.auth import verify_token
    try:
        payload = verify_token(token)
        return {
            "valid": True,
            "user_id": payload["user_id"],
            "email": payload["email"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )