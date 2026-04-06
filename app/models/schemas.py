# app/models/schemas.py
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class SchoolCheckRequest(BaseModel):
    email: EmailStr
    
    @validator('email')
    def normalize_email(cls, v):
        return v.strip().lower()

class SchoolRecoveryRequest(BaseModel):
    email: EmailStr
    school_name: str = Field(..., min_length=2)
    contact: str = Field(..., min_length=6)
    confirm_deactivation: bool = False
    
    @validator('school_name')
    def normalize_school_name(cls, v):
        return v.strip()
    
    @validator('contact')
    def normalize_contact(cls, v):
        return v.strip()

class RecoveryImportRequest(BaseModel):
    school_email: EmailStr
    encrypted_backup: str

class HealthComponent(BaseModel):
    cloud: str = "unknown"
    local_db: str = "unknown"

class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    components: HealthComponent = Field(default_factory=HealthComponent)

class SchoolInfo(BaseModel):
    id: int
    school_name: str
    school_email: str
    school_contact: str
    county: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    created_at: Optional[str] = None

class AdminInfo(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    contact: Optional[str] = None

class VerifyRecoveryResponse(BaseModel):
    success: bool
    verified: Optional[bool] = None
    message: str
    data: Optional[Dict[str, Any]] = None
    warning: Optional[str] = None