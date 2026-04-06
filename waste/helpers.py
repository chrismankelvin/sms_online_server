# app/utils/helpers.py
import sqlite3
import hashlib
import uuid
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
import logging
import os

logger = logging.getLogger(__name__)

# Database paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOCAL_DB_PATH = PROJECT_ROOT / "data" / "recovery_school.db"
RECOVERY_SECRET = os.getenv("RECOVERY_SECRET", "CHANGE_ME_IN_PRODUCTION")

def get_local_db_connection():
    """Get connection to local recovery SQLite database"""
    try:
        LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(LOCAL_DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Error connecting to local database: {e}")
        raise

def initialize_recovery_database():
    """Initialize the local recovery database with necessary tables"""
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        # Create tables (same as before)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recovered_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unique_id TEXT NOT NULL UNIQUE,
                username TEXT NOT NULL UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (
                    role IN ('admin', 'teacher', 'ta', 'accountant', 'student')
                ),
                status TEXT NOT NULL DEFAULT 'active' CHECK (
                    status IN ('active', 'suspended', 'disabled')
                ),
                last_login DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                recovered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                cloud_user_id INTEGER,
                original_cloud_data TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recovered_school_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                address TEXT,
                city TEXT,
                state TEXT,
                country TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                recovered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                cloud_school_id INTEGER,
                original_cloud_data TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recovery_activation_state (
                id INTEGER PRIMARY KEY DEFAULT 1,
                activated BOOLEAN NOT NULL DEFAULT FALSE,
                activation_code TEXT,
                machine_fingerprint TEXT,
                school_name TEXT,
                activated_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                recovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                CHECK (id = 1)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recovery_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                ip_address TEXT,
                timestamp DATETIME NOT NULL,
                success BOOLEAN NOT NULL,
                recovery_type TEXT NOT NULL,
                details TEXT,
                synced_to_cloud BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Ensure activation_state has the single row
        cursor.execute("SELECT id FROM recovery_activation_state WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO recovery_activation_state 
                (id, activated, created_at, updated_at)
                VALUES (1, FALSE, ?, ?)
            """, (datetime.now().isoformat(), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        logger.info("✅ Recovery database initialized")
        
    except Exception as e:
        logger.error(f"❌ Error initializing recovery database: {e}")
        raise

def hash_password(password: str) -> str:
    """Hash password for storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def log_recovery_attempt(email: str, recovery_type: str, status: str, 
                        details: str = None, ip_address: str = "0.0.0.0"):
    """Log recovery attempts to local database"""
    success = 1 if status.lower() == "success" else 0
    
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recovery_attempts 
            (email, ip_address, timestamp, success, recovery_type, details, synced_to_cloud)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            email, 
            ip_address, 
            datetime.now().isoformat(), 
            success, 
            recovery_type, 
            details,
            0
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging to local DB: {e}")

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

class RecoveryDatabaseManager:
    """Context manager for recovery database operations"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def __enter__(self):
        self.conn = get_local_db_connection()
        self.cursor = self.conn.cursor()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        if self.conn:
            self.conn.close()
    
    def execute(self, query: str, params: tuple = None):
        if params:
            return self.cursor.execute(query, params)
        return self.cursor.execute(query)
    
    def fetchone(self):
        return self.cursor.fetchone()
    
    def fetchall(self):
        return self.cursor.fetchall()
    
    @property
    def lastrowid(self):
        return self.cursor.lastrowid