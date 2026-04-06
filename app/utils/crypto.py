import hashlib
import json
import base64
from datetime import datetime
from typing import Dict, Any, List
from cryptography.fernet import Fernet
import os
import logging

logger = logging.getLogger(__name__)

# No default value - MUST be set in environment
RECOVERY_SECRET = os.getenv("RECOVERY_SECRET")
if not RECOVERY_SECRET:
    raise ValueError("RECOVERY_SECRET environment variable is required")

def derive_recovery_key(school_email: str) -> bytes:
    """Derive encryption key from school email and secret"""
    raw = f"{school_email}:{RECOVERY_SECRET}".encode()
    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest[:32])

def create_recovery_blob(school_data: dict, admins: list) -> str:
    """Create encrypted recovery blob matching main app's format"""
    payload = {
        "schema_version": 1,
        "school": {
            "school_name": school_data.get("school_name"),
            "school_email": school_data.get("school_email"),
            "school_contact": school_data.get("school_contact"),
            "county": school_data.get("county"),
            "region": school_data.get("region"),
            "city": school_data.get("city"),
            "town": school_data.get("town", ""),
            "gps_address": school_data.get("gps_address", ""),
            "manufacture_code": school_data.get("manufacture_code", ""),
            "created_at": school_data.get("created_at")
        },
        "admins": [
            {
                "first_name": admin.get("first_name"),
                "middle_name": admin.get("middle_name", ""),
                "last_name": admin.get("last_name"),
                "contact": admin.get("contact"),
                "email": admin.get("email"),
                "password_hash": admin.get("password_hash"),
                "created_at": admin.get("created_at")
            }
            for admin in admins
        ],
        "issued_at": datetime.now().isoformat()
    }
    
    key = derive_recovery_key(school_data["school_email"])
    fernet = Fernet(key)
    
    json_str = json.dumps(payload, default=str)
    encrypted = fernet.encrypt(json_str.encode())
    
    return encrypted.decode()

def verify_school_credentials(school_data: dict, school_name: str, contact: str) -> bool:
    """Verify school name and contact match cloud data"""
    if not school_data:
        return False
    
    cloud_name = school_data.get("school_name", "").strip().lower()
    cloud_contact = school_data.get("school_contact", "").strip()
    
    return (cloud_name == school_name.strip().lower() and 
            cloud_contact == contact.strip())