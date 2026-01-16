# # Cloud_backend.py
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from typing import Optional
# from datetime import datetime
# import sqlite3
# from pathlib import Path
# import hashlib
# import uuid
# import os
# import json  # add at the top
# # Import the existing cloud client
# try:
#     from database.cloud_db import SQLiteCloudClient
# except ImportError:
#     # Fallback if cloud_db is in a different location
#     import sys
#     sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#     from database.cloud_db import SQLiteCloudClient

# app = FastAPI(title="School Recovery Server", description="Separate backend for school account recovery")

# # CORS configuration
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:5173",
#         "http://127.0.0.1:5173",
#         "http://localhost:3000"
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize cloud client
# cloud_client = SQLiteCloudClient()

# # Request Models
# class SchoolCheckRequest(BaseModel):
#     email: str

# class SchoolRecoveryRequest(BaseModel):
#     email: str
#     school_name: str
#     contact: str
#     confirm_deactivation: bool = False

# class AdminRecoveryRequest(BaseModel):
#     school_email: str
#     admin_email: str

# # Database paths
# PROJECT_ROOT = Path(__file__).parent.parent
# LOCAL_DB_PATH = PROJECT_ROOT / "database" / "recovery_school.db"  # Separate recovery database

# def get_recovery_db_connection():
#     """Get connection to recovery SQLite database"""
#     try:
#         LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
#         conn = sqlite3.connect(str(LOCAL_DB_PATH))
#         return conn
#     except Exception as e:
#         print(f"Error connecting to recovery database: {e}")
#         raise

# def initialize_recovery_database():
#     """Initialize the recovery database with necessary tables"""
#     try:
#         conn = get_recovery_db_connection()
#         cursor = conn.cursor()
        
#         # Create users table (similar to main database but for recovery)
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS recovered_users (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 unique_id TEXT NOT NULL UNIQUE,
#                 username TEXT NOT NULL UNIQUE,
#                 email TEXT UNIQUE,
#                 password_hash TEXT NOT NULL,
#                 role TEXT NOT NULL CHECK (
#                     role IN ('admin', 'teacher', 'ta', 'accountant', 'student')
#                 ),
#                 status TEXT NOT NULL DEFAULT 'active' CHECK (
#                     status IN ('active', 'suspended', 'disabled')
#                 ),
#                 last_login DATETIME,
#                 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
#                 recovered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
#                 cloud_user_id INTEGER,
#                 original_cloud_data TEXT
#             )
#         """)
        
#         # Create school_info table for recovery
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS recovered_school_info (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 school_name TEXT NOT NULL,
#                 email TEXT UNIQUE NOT NULL,
#                 phone TEXT,
#                 address TEXT,
#                 city TEXT,
#                 state TEXT,
#                 country TEXT,
#                 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
#                 updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
#                 recovered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
#                 cloud_school_id INTEGER,
#                 original_cloud_data TEXT
#             )
#         """)
        
#         # Create activation_state table (will be set to NOT activated)
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS recovery_activation_state (
#                 id INTEGER PRIMARY KEY DEFAULT 1,
#                 activated BOOLEAN NOT NULL DEFAULT FALSE,
#                 activation_code TEXT,
#                 machine_fingerprint TEXT,
#                 school_name TEXT,
#                 activated_at DATETIME,
#                 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
#                 updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
#                 recovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
#                 CHECK (id = 1)
#             )
#         """)
        
#         # Ensure activation_state has the single row
#         cursor.execute("SELECT id FROM recovery_activation_state WHERE id = 1")
#         if not cursor.fetchone():
#             cursor.execute("""
#                 INSERT INTO recovery_activation_state 
#                 (id, activated, created_at, updated_at)
#                 VALUES (1, FALSE, ?, ?)
#             """, (datetime.now().isoformat(), datetime.now().isoformat()))
        
#         # Create recovery logs table
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS recovery_logs (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 school_email TEXT NOT NULL,
#                 recovery_type TEXT NOT NULL,
#                 status TEXT NOT NULL,
#                 details TEXT,
#                 recovered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
#             )
#         """)
        
#         conn.commit()
#         conn.close()
#         print("✅ Recovery database initialized")
        
#     except Exception as e:
#         print(f"❌ Error initializing recovery database: {e}")
#         raise

# # Initialize database on startup
# initialize_recovery_database()

# def hash_password(password: str) -> str:
#     """Hash password for storage"""
#     return hashlib.sha256(password.encode()).hexdigest()

# def log_recovery_attempt(school_email: str, recovery_type: str, status: str, details: str = None):
#     """Log recovery attempts for audit purposes"""
#     try:
#         conn = get_recovery_db_connection()
#         cursor = conn.cursor()
        
#         cursor.execute("""
#             INSERT INTO recovery_logs 
#             (school_email, recovery_type, status, details)
#             VALUES (?, ?, ?, ?)
#         """, (school_email, recovery_type, status, details))
        
#         conn.commit()
#         conn.close()
#     except Exception as e:
#         print(f"Error logging recovery attempt: {e}")

# # ============================================
# # RECOVERY ENDPOINTS
# # ============================================

# @app.get("/")
# async def root():
#     """Root endpoint - server status"""
#     return {
#         "service": "school-recovery-server",
#         "status": "online",
#         "version": "1.0.0",
#         "timestamp": datetime.now().isoformat()
#     }

# @app.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     try:
#         # Test cloud connection
#         cloud_online = cloud_client.check_connection()
        
#         # Test local database
#         conn = get_recovery_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT 1")
#         db_online = cursor.fetchone() is not None
#         conn.close()
        
#         return {
#             "status": "healthy" if cloud_online and db_online else "degraded",
#             "cloud_connected": cloud_online,
#             "database_connected": db_online,
#             "timestamp": datetime.now().isoformat()
#         }
        
#     except Exception as e:
#         return {
#             "status": "unhealthy",
#             "error": str(e),
#             "timestamp": datetime.now().isoformat()
#         }

# @app.post("/check-school")
# async def check_school_exists(req: SchoolCheckRequest):
#     """Check if school exists in cloud database"""
#     try:
#         if not cloud_client.check_connection():
#             log_recovery_attempt(req.email, "check_school", "failed", "Cloud not connected")
#             raise HTTPException(
#                 status_code=503, 
#                 detail="Cannot connect to cloud database. Please check your internet connection."
#             )
        
#         # Query cloud database for school
#         query = """
#             SELECT id, school_name, school_email, school_contact, 
#                    county, region, city, town, gps_address, 
#                    manufacture_code, created_at
#             FROM school_installations 
#             WHERE school_email = ? 
#             LIMIT 1
#         """
        
#         result = cloud_client.execute_query(query, (req.email,))
        
#         if result.get("rows"):
#             school = result["rows"][0]
            
#             # Don't return sensitive information
#             sanitized_school = {
#                 "id": school.get("id"),
#                 "school_name": school.get("school_name"),
#                 "school_email": school.get("school_email"),
#                 "school_contact": school.get("school_contact"),
#                 "county": school.get("county"),
#                 "region": school.get("region"),
#                 "city": school.get("city"),
#                 "created_at": school.get("created_at")
#             }
            
#             log_recovery_attempt(req.email, "check_school", "success", f"School found: {school.get('school_name')}")
            
#             return {
#                 "success": True,
#                 "exists": True,
#                 "school": sanitized_school,
#                 "message": f"School found: {school.get('school_name')}"
#             }
#         else:
#             log_recovery_attempt(req.email, "check_school", "failed", "School not found")
#             return {
#                 "success": True,
#                 "exists": False,
#                 "message": "No school found with this email address."
#             }
            
#     except HTTPException:
#         raise
#     except Exception as e:
#         log_recovery_attempt(req.email, "check_school", "error", str(e))
#         raise HTTPException(status_code=500, detail=f"Failed to check school: {str(e)}")

# @app.post("/verify-recovery")
# async def verify_school_recovery(req: SchoolRecoveryRequest):
#     """Verify school recovery details and get admin information"""
#     try:
#         if not cloud_client.check_connection():
#             raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
#         # First, verify school exists
#         check_result = await check_school_exists(SchoolCheckRequest(email=req.email))
        
#         if not check_result.get("exists"):
#             return {
#                 "success": False,
#                 "message": "School not found. Please check the email address."
#             }
        
#         school_data = check_result["school"]
        
#         # Verify school name and contact match
#         if (school_data.get("school_name", "").strip().lower() != req.school_name.strip().lower()):
#             return {
#                 "success": False,
#                 "message": "School name does not match our records."
#             }
        
#         if (school_data.get("school_contact", "").strip() != req.contact.strip()):
#             return {
#                 "success": False,
#                 "message": "Contact number does not match our records."
#             }
        
#         # Get admin information from cloud
#         query = """
#             SELECT id, first_name, middle_name, last_name, 
#                    contact, email, password_hash, created_at
#             FROM admin_table 
#             WHERE school_id = ? 
#             ORDER BY created_at DESC
#         """
        
#         result = cloud_client.execute_query(query, (school_data["id"],))
#         admins = result.get("rows", [])
        
#         if not admins:
#             return {
#                 "success": False,
#                 "message": "No admin accounts found for this school."
#             }
        
#         # Return verification success with admin count (not password hashes)
#         log_recovery_attempt(req.email, "verify_recovery", "success", f"Verified: {school_data['school_name']}")
        
#         return {
#             "success": True,
#             "verified": True,
#             "message": "School verification successful",
#             "data": {
#                 "school": school_data,
#                 "admin_count": len(admins),
#                 "admins": [
#                     {
#                         "first_name": admin.get("first_name"),
#                         "last_name": admin.get("last_name"),
#                         "email": admin.get("email"),
#                         "contact": admin.get("contact")
#                     }
#                     for admin in admins
#                 ]
#             },
#             "warning": "Recovery will deactivate any existing device and require reactivation."
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         log_recovery_attempt(req.email, "verify_recovery", "error", str(e))
#         raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

# @app.post("/perform-recovery")
# async def perform_school_recovery(req: SchoolRecoveryRequest):
#     """Perform the complete school recovery process"""
#     try:
#         if not req.confirm_deactivation:
#             raise HTTPException(
#                 status_code=400, 
#                 detail="You must confirm device deactivation to proceed with recovery."
#             )
        
#         if not cloud_client.check_connection():
#             raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
#         # Step 1: Verify school details
#         verify_result = await verify_school_recovery(req)
        
#         if not verify_result.get("verified"):
#             return {
#                 "success": False,
#                 "message": verify_result.get("message", "Verification failed")
#             }
        
#         school_data = verify_result["data"]["school"]
#         school_id = school_data["id"]
        
#         # Step 2: Get full admin data (including password hashes)
#         query = """
#             SELECT id, first_name, middle_name, last_name, 
#                    contact, email, password_hash, created_at
#             FROM admin_table 
#             WHERE school_id = ? 
#             ORDER BY created_at DESC
#         """
        
#         result = cloud_client.execute_query(query, (school_id,))
#         admins = result.get("rows", [])
        
#         if not admins:
#             raise HTTPException(status_code=404, detail="No admin accounts found")
        
#         conn = None
#         try:
#             conn = get_recovery_db_connection()
#             cursor = conn.cursor()
            
#             # Step 3: Clear any existing recovery data for this school
#             cursor.execute("DELETE FROM recovered_school_info WHERE email = ?", (req.email,))
#             cursor.execute("DELETE FROM recovered_users WHERE email IN (SELECT email FROM (SELECT email FROM recovered_users WHERE email IS NOT NULL))")
            
#             # Step 4: Save school info to recovery database
#             cursor.execute("""
#                 INSERT INTO recovered_school_info 
#                 (school_name, email, phone, address, city, state, country, 
#                  created_at, updated_at, recovered_at, cloud_school_id, original_cloud_data)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """, (
#                 school_data.get("school_name"),
#                 school_data.get("school_email"),
#                 school_data.get("school_contact"),
#                 f"{school_data.get('town', '')}, {school_data.get('city', '')}",
#                 school_data.get("city"),
#                 school_data.get("region"),
#                 school_data.get("county"),
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat(),
#                 school_id,
#                 str(school_data)  # Store original data for reference
#             ))
            
#             # Step 5: Save each admin to recovery database
#             saved_admin_ids = []
#             for admin in admins:
#                 unique_id = str(uuid.uuid4())
#                 username = admin.get("email") or admin.get("contact") or unique_id
                
#                 cursor.execute("""
#                     INSERT INTO recovered_users 
#                     (unique_id, username, email, password_hash, role, status, 
#                      created_at, recovered_at, cloud_user_id, original_cloud_data)
#                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                 """, (
#                     unique_id,
#                     username,
#                     admin.get("email"),
#                     admin.get("password_hash"),
#                     "admin",
#                     "active",
#                     datetime.now().isoformat(),
#                     datetime.now().isoformat(),
#                     admin.get("id"),
#                     str({k: v for k, v in admin.items() if k != 'password_hash'})  # Store without password hash
#                 ))
                
#                 saved_admin_ids.append(cursor.lastrowid)
            
#             # Step 6: Ensure activation state is NOT activated
#             cursor.execute("""
#                 UPDATE recovery_activation_state 
#                 SET activated = FALSE,
#                     activation_code = NULL,
#                     machine_fingerprint = NULL,
#                     school_name = ?,
#                     activated_at = NULL,
#                     updated_at = ?,
#                     recovered_at = ?
#                 WHERE id = 1
#             """, (
#                 school_data.get("school_name"),
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat()
#             ))
            
#             conn.commit()
            
#             log_recovery_attempt(req.email, "perform_recovery", "success", 
#                                f"Recovered {len(saved_admin_ids)} admins")
            
#             return {
#                 "success": True,
#                 "message": "School recovery completed successfully!",
#                 "data": {
#                     "school_name": school_data.get("school_name"),
#                     "admins_recovered": len(saved_admin_ids),
#                     "recovery_timestamp": datetime.now().isoformat(),
#                     "next_step": "activation",
#                     "note": "System has been deactivated. You need to activate it with a new activation code."
#                 }
#             }
            
#         except Exception as e:
#             if conn:
#                 conn.rollback()
#             raise e
#         finally:
#             if conn:
#                 conn.close()
                
#     except HTTPException:
#         raise
#     except Exception as e:
#         log_recovery_attempt(req.email, "perform_recovery", "error", str(e))
#         raise HTTPException(status_code=500, detail=f"Recovery failed: {str(e)}")




# @app.get("/recovery-status")
# async def get_recovery_status():
#     """Get the current recovery status from local recovery database"""
#     try:
#         conn = get_recovery_db_connection()
#         cursor = conn.cursor()
        
#         # Check recovered school info
#         cursor.execute("SELECT COUNT(*) FROM recovered_school_info")
#         school_count = cursor.fetchone()[0]
        
#         # Check recovered admins
#         cursor.execute("SELECT COUNT(*) FROM recovered_users WHERE role = 'admin'")
#         admin_count = cursor.fetchone()[0]
        
#         # Check activation state
#         cursor.execute("SELECT activated FROM recovery_activation_state WHERE id = 1")
#         activation_state = cursor.fetchone()
        
#         # Get latest recovery log
#         cursor.execute("""
#             SELECT school_email, recovery_type, status, recovered_at 
#             FROM recovery_logs 
#             ORDER BY recovered_at DESC 
#             LIMIT 1
#         """)
#         latest_log = cursor.fetchone()
        
#         conn.close()
        
#         status = {
#             "recovery_database": "online",
#             "school_recovered": school_count > 0,
#             "admins_recovered": admin_count > 0,
#             "system_activated": bool(activation_state[0]) if activation_state else False,
#             "school_count": school_count,
#             "admin_count": admin_count,
#             "last_recovery_attempt": None
#         }
        
#         if latest_log:
#             status["last_recovery_attempt"] = {
#                 "school_email": latest_log[0],
#                 "type": latest_log[1],
#                 "status": latest_log[2],
#                 "timestamp": latest_log[3]
#             }
        
#         return status
        
#     except Exception as e:
#         return {
#             "recovery_database": "offline",
#             "error": str(e),
#             "school_recovered": False,
#             "admins_recovered": False,
#             "system_activated": False
#         }

# @app.post("/transfer-to-main")
# async def transfer_to_main_database():
#     """Transfer recovered data to the main school database"""
#     try:
#         # This endpoint would transfer data from recovery database to main database
#         # For security, this might require additional authentication
        
#         # For now, just return success - in production, implement proper transfer logic
#         return {
#             "success": True,
#             "message": "Recovery data is ready. Please restart the main application to use recovered data.",
#             "note": "The recovery server stores data separately. To use it, copy the recovery_school.db file to your main database location."
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     print("🚀 Starting School Recovery Server on http://localhost:8001")
#     print("📊 Endpoints:")
#     print("  - GET  /                 Server status")
#     print("  - GET  /health           Health check")
#     print("  - POST /check-school     Check if school exists")
#     print("  - POST /verify-recovery  Verify recovery details")
#     print("  - POST /perform-recovery Complete recovery")
#     print("  - GET  /recovery-status  Get recovery status")
#     print("  - POST /transfer-to-main Transfer to main DB")
    
#     uvicorn.run(
#         app, 
#         host="0.0.0.0", 
#         port=8001,
#         log_level="info"
#     )




# Cloud_backend.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sqlite3
from pathlib import Path
import hashlib
import uuid
import os
import json
import base64
import requests
from cryptography.fernet import Fernet

# Import the existing cloud client
try:
    from database.cloud_db import SQLiteCloudClient
except ImportError:
    # Fallback if cloud_db is in a different location
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database.cloud_db import SQLiteCloudClient

app = FastAPI(title="School Recovery Server", description="Separate backend for school account recovery")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000"  # Allow main app
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize cloud client
cloud_client = SQLiteCloudClient()

# Request Models
class SchoolCheckRequest(BaseModel):
    email: str

class SchoolRecoveryRequest(BaseModel):
    email: str
    school_name: str
    contact: str
    confirm_deactivation: bool = False

class RecoveryImportRequest(BaseModel):
    school_email: str
    encrypted_backup: str

# Database paths
PROJECT_ROOT = Path(__file__).parent.parent
LOCAL_DB_PATH = PROJECT_ROOT / "database" / "recovery_school.db"  # Separate recovery database

# MUST match main.py's RECOVERY_SECRET
RECOVERY_SECRET = "CHANGE_ME_IN_PRODUCTION"

def get_recovery_db_connection():
    """Get connection to recovery SQLite database"""
    try:
        LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(LOCAL_DB_PATH))
        return conn
    except Exception as e:
        print(f"Error connecting to recovery database: {e}")
        raise

def initialize_recovery_database():
    """Initialize the recovery database with necessary tables"""
    try:
        conn = get_recovery_db_connection()
        cursor = conn.cursor()
        
        # Create users table (similar to main database but for recovery)
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
        
        # Create school_info table for recovery
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
        
        # Create activation_state table (will be set to NOT activated)
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
        
        # Ensure activation_state has the single row
        cursor.execute("SELECT id FROM recovery_activation_state WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO recovery_activation_state 
                (id, activated, created_at, updated_at)
                VALUES (1, FALSE, ?, ?)
            """, (datetime.now().isoformat(), datetime.now().isoformat()))
        
        # Create recovery logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recovery_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_email TEXT NOT NULL,
                recovery_type TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                recovered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Recovery database initialized")
        
    except Exception as e:
        print(f"❌ Error initializing recovery database: {e}")
        raise

# Initialize database on startup
initialize_recovery_database()

def hash_password(password: str) -> str:
    """Hash password for storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def log_recovery_attempt(school_email: str, recovery_type: str, status: str, details: str = None):
    """Log recovery attempts for audit purposes"""
    try:
        conn = get_recovery_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO recovery_logs 
            (school_email, recovery_type, status, details)
            VALUES (?, ?, ?, ?)
        """, (school_email, recovery_type, status, details))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging recovery attempt: {e}")

# ============================================
# ENCRYPTION FUNCTIONS (For compatibility with main app)
# ============================================

def derive_recovery_key(school_email: str) -> bytes:
    """Derive encryption key from school email and secret"""
    raw = f"{school_email}:{RECOVERY_SECRET}".encode()
    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest[:32])  # Fernet needs 32 bytes

def create_recovery_blob(school_data: dict, admins: list) -> str:
    """Create encrypted recovery blob matching main app's format"""
    # Create payload matching expected schema
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
    
    # Encrypt with Fernet
    key = derive_recovery_key(school_data["school_email"])
    fernet = Fernet(key)
    
    # Encrypt JSON string
    json_str = json.dumps(payload, default=str)
    encrypted = fernet.encrypt(json_str.encode())
    
    return encrypted.decode()

def validate_recovery_payload(payload: dict):
    """Validate recovery payload structure"""
    required = ["schema_version", "school", "admins", "issued_at"]
    for key in required:
        if key not in payload:
            raise Exception(f"Invalid recovery payload: missing {key}")

    if payload["schema_version"] != 1:
        raise Exception("Unsupported recovery schema version")

    if not payload["admins"]:
        raise Exception("Recovery payload contains no admins")

# ============================================
# RECOVERY ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint - server status"""
    return {
        "service": "school-recovery-server",
        "status": "online",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "cloud_recovery",
            "encrypted_blobs",
            "direct_import"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test cloud connection
        cloud_online = cloud_client.check_connection()
        
        # Test local database
        conn = get_recovery_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        db_online = cursor.fetchone() is not None
        conn.close()
        
        # Test main app connection
        main_app_online = False
        try:
            response = requests.get("http://localhost:8000/health/test", timeout=5)
            main_app_online = response.status_code == 200
        except:
            pass
        
        return {
            "status": "healthy" if cloud_online and db_online else "degraded",
            "cloud_connected": cloud_online,
            "database_connected": db_online,
            "main_app_connected": main_app_online,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/check-school")
async def check_school_exists(req: SchoolCheckRequest):
    """Check if school exists in cloud database"""
    try:
        if not cloud_client.check_connection():
            log_recovery_attempt(req.email, "check_school", "failed", "Cloud not connected")
            raise HTTPException(
                status_code=503, 
                detail="Cannot connect to cloud database. Please check your internet connection."
            )
        
        # Query cloud database for school
        query = """
            SELECT id, school_name, school_email, school_contact, 
                   county, region, city, town, gps_address, 
                   manufacture_code, created_at
            FROM school_installations 
            WHERE school_email = ? 
            LIMIT 1
        """
        
        result = cloud_client.execute_query(query, (req.email,))
        
        if result.get("rows"):
            school = result["rows"][0]
            
            # Don't return sensitive information
            sanitized_school = {
                "id": school.get("id"),
                "school_name": school.get("school_name"),
                "school_email": school.get("school_email"),
                "school_contact": school.get("school_contact"),
                "county": school.get("county"),
                "region": school.get("region"),
                "city": school.get("city"),
                "created_at": school.get("created_at")
            }
            
            log_recovery_attempt(req.email, "check_school", "success", f"School found: {school.get('school_name')}")
            
            return {
                "success": True,
                "exists": True,
                "school": sanitized_school,
                "message": f"School found: {school.get('school_name')}"
            }
        else:
            log_recovery_attempt(req.email, "check_school", "failed", "School not found")
            return {
                "success": True,
                "exists": False,
                "message": "No school found with this email address."
            }
            
    except HTTPException:
        raise
    except Exception as e:
        log_recovery_attempt(req.email, "check_school", "error", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to check school: {str(e)}")

@app.post("/verify-recovery")
async def verify_school_recovery(req: SchoolRecoveryRequest):
    """Verify school recovery details and get admin information"""
    try:
        if not cloud_client.check_connection():
            raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
        # First, verify school exists
        check_result = await check_school_exists(SchoolCheckRequest(email=req.email))
        
        if not check_result.get("exists"):
            return {
                "success": False,
                "message": "School not found. Please check the email address."
            }
        
        school_data = check_result["school"]
        
        # Verify school name and contact match
        if (school_data.get("school_name", "").strip().lower() != req.school_name.strip().lower()):
            return {
                "success": False,
                "message": "School name does not match our records."
            }
        
        if (school_data.get("school_contact", "").strip() != req.contact.strip()):
            return {
                "success": False,
                "message": "Contact number does not match our records."
            }
        
        # Get admin information from cloud
        query = """
            SELECT id, first_name, middle_name, last_name, 
                   contact, email, password_hash, created_at
            FROM admin_table 
            WHERE school_id = ? 
            ORDER BY created_at DESC
        """
        
        result = cloud_client.execute_query(query, (school_data["id"],))
        admins = result.get("rows", [])
        
        if not admins:
            return {
                "success": False,
                "message": "No admin accounts found for this school."
            }
        
        # Return verification success with admin count (not password hashes)
        log_recovery_attempt(req.email, "verify_recovery", "success", f"Verified: {school_data['school_name']}")
        
        return {
            "success": True,
            "verified": True,
            "message": "School verification successful",
            "data": {
                "school": school_data,
                "admin_count": len(admins),
                "admins": [
                    {
                        "first_name": admin.get("first_name"),
                        "last_name": admin.get("last_name"),
                        "email": admin.get("email"),
                        "contact": admin.get("contact")
                    }
                    for admin in admins
                ]
            },
            "warning": "Recovery will deactivate any existing device and require reactivation."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_recovery_attempt(req.email, "verify_recovery", "error", str(e))
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@app.post("/perform-recovery")
async def perform_school_recovery(req: SchoolRecoveryRequest):
    """Perform the complete school recovery process"""
    print(f"🔍 DEBUG: /perform-recovery called for email: {req.email}")
    
    try:
        # Input validation
        if not req.email or "@" not in req.email:
            raise HTTPException(status_code=400, detail="Invalid email address")
        
        if not req.school_name or len(req.school_name.strip()) < 2:
            raise HTTPException(status_code=400, detail="School name is required")
        
        if not req.contact or len(req.contact.strip()) < 6:
            raise HTTPException(status_code=400, detail="Valid contact number is required")
        
        if not req.confirm_deactivation:
            raise HTTPException(
                status_code=400, 
                detail="You must confirm device deactivation to proceed with recovery."
            )
        
        print(f"🔍 DEBUG: Input validation passed")
        
        # Check cloud connection
        if not cloud_client.check_connection():
            print("❌ DEBUG: Cloud client connection failed")
            raise HTTPException(
                status_code=503, 
                detail="Cannot connect to cloud database. Please check your internet connection."
            )
        
        print("✅ DEBUG: Cloud connection successful")
        
        # Step 1: Verify school details
        print(f"🔍 DEBUG: Calling verify_school_recovery for {req.email}")
        verify_result = await verify_school_recovery(req)
        
        if not verify_result.get("verified"):
            error_msg = verify_result.get("message", "Verification failed")
            print(f"❌ DEBUG: Verification failed: {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
        
        print("✅ DEBUG: School verification successful")
        
        school_data = verify_result["data"]["school"]
        school_id = school_data.get("id")
        
        if not school_id:
            print("❌ DEBUG: No school_id in verification result")
            raise HTTPException(status_code=500, detail="School ID not found in verification data")
        
        print(f"✅ DEBUG: School ID: {school_id}, Name: {school_data.get('school_name')}")
        
        # Step 2: Get full admin data (including password hashes)
        query = """
            SELECT id, first_name, middle_name, last_name, 
                   contact, email, password_hash, created_at
            FROM admin_table 
            WHERE school_id = ? 
            ORDER BY created_at DESC
        """
        
        print(f"🔍 DEBUG: Executing admin query for school_id: {school_id}")
        result = cloud_client.execute_query(query, (school_id,))
        
        if not result.get("success", True):
            print(f"❌ DEBUG: Cloud query failed: {result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to query admin data: {result.get('error', 'Unknown error')}"
            )
        
        admins = result.get("rows", [])
        print(f"✅ DEBUG: Found {len(admins)} admins")
        
        if not admins:
            raise HTTPException(
                status_code=404, 
                detail="No admin accounts found for this school."
            )
        
        # Step 3: Get full school data for blob creation
        print(f"🔍 DEBUG: Getting full school data for ID: {school_id}")
        full_school_query = """
            SELECT * FROM school_installations WHERE id = ?
        """
        full_school_result = cloud_client.execute_query(full_school_query, (school_id,))
        
        if not full_school_result.get("success", True):
            print(f"⚠️ DEBUG: Failed to get full school data, using basic data")
            full_school_data = school_data
        elif not full_school_result.get("rows"):
            print(f"⚠️ DEBUG: No rows in full school data, using basic data")
            full_school_data = school_data
        else:
            full_school_data = full_school_result["rows"][0]
            print(f"✅ DEBUG: Got full school data with {len(full_school_data)} fields")
        
        # Step 4: Create encrypted recovery blob
        print(f"🔍 DEBUG: Creating encrypted recovery blob...")
        try:
            encrypted_blob = create_recovery_blob(full_school_data, admins)
            print(f"✅ DEBUG: Created blob of length {len(encrypted_blob)}")
        except Exception as blob_error:
            print(f"❌ DEBUG: Failed to create blob: {blob_error}")
            # Continue without blob for now
            encrypted_blob = None
        
        # Database operations
        conn = None
        try:
            conn = get_recovery_db_connection()
            cursor = conn.cursor()
            print("✅ DEBUG: Connected to recovery database")
            
            # Step 5: Clear any existing recovery data for this school
            print(f"🔍 DEBUG: Clearing existing recovery data for {req.email}")
            
            # FIXED: Removed extra parenthesis
            cursor.execute("DELETE FROM recovered_school_info WHERE email = ?", (req.email,))
            cursor.execute("DELETE FROM recovered_users WHERE email IN (SELECT email FROM recovered_users WHERE email IS NOT NULL)")
            
            deleted_schools = cursor.rowcount
            print(f"✅ DEBUG: Deleted {deleted_schools} existing school records")
            
            # Step 6: Save school info to recovery database
            print(f"🔍 DEBUG: Saving school info to recovery DB")
            
            # Prepare school data
            school_name = school_data.get("school_name", "").strip()
            school_email = school_data.get("school_email", "").strip()
            school_contact = school_data.get("school_contact", "").strip()
            town = full_school_data.get("town", "")
            city = full_school_data.get("city", "")
            region = full_school_data.get("region", "")
            county = full_school_data.get("county", "")
            
            # Validate required fields
            if not school_name:
                raise ValueError("School name is required")
            if not school_email:
                raise ValueError("School email is required")
            
            address = f"{town}, {city}".strip(", ")
            if not address or address == ", ":
                address = city if city else "Unknown"
            
            cursor.execute("""
                INSERT INTO recovered_school_info 
                (school_name, email, phone, address, city, state, country, 
                 created_at, updated_at, recovered_at, cloud_school_id, original_cloud_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                school_name,
                school_email,
                school_contact,
                address,
                city,
                region,
                county,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                school_id,
                json.dumps(full_school_data, default=str)  # Use json.dumps instead of str()
            ))
            
            school_db_id = cursor.lastrowid
            print(f"✅ DEBUG: Saved school with ID: {school_db_id}")
            
            # Step 7: Save each admin to recovery database
            saved_admin_ids = []
            print(f"🔍 DEBUG: Saving {len(admins)} admins to recovery DB")
            
            for i, admin in enumerate(admins):
                unique_id = str(uuid.uuid4())
                email = admin.get("email", "").strip()
                contact = admin.get("contact", "").strip()
                
                # Determine username
                if email:
                    username = email
                elif contact:
                    username = contact
                else:
                    username = f"admin_{unique_id[:8]}"
                
                password_hash = admin.get("password_hash")
                if not password_hash:
                    print(f"⚠️ DEBUG: Admin {i+1} has no password hash, using dummy")
                    password_hash = hash_password("temporary_password")
                
                # Prepare original data (without password hash)
                original_data = {}
                for k, v in admin.items():
                    if k != 'password_hash':
                        original_data[k] = v
                
                try:
                    cursor.execute("""
                        INSERT INTO recovered_users 
                        (unique_id, username, email, password_hash, role, status, 
                         created_at, recovered_at, cloud_user_id, original_cloud_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        unique_id,
                        username,
                        email if email else None,
                        password_hash,
                        "admin",
                        "active",
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        admin.get("id"),
                        json.dumps(original_data, default=str)  # Use json.dumps
                    ))
                    
                    saved_admin_ids.append(cursor.lastrowid)
                    print(f"  ✅ Admin {i+1}: {email or contact} saved")
                    
                except sqlite3.IntegrityError as e:
                    print(f"⚠️ DEBUG: Admin {i+1} integrity error: {e}")
                    # Try with different username
                    username = f"admin_{uuid.uuid4().hex[:8]}"
                    cursor.execute("""
                        INSERT INTO recovered_users 
                        (unique_id, username, email, password_hash, role, status, 
                         created_at, recovered_at, cloud_user_id, original_cloud_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        unique_id,
                        username,
                        email if email else None,
                        password_hash,
                        "admin",
                        "active",
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        admin.get("id"),
                        json.dumps(original_data, default=str)
                    ))
                    saved_admin_ids.append(cursor.lastrowid)
            
            print(f"✅ DEBUG: Saved {len(saved_admin_ids)} admins")
            
            # Step 8: Ensure activation state is NOT activated
            print(f"🔍 DEBUG: Updating activation state")
            cursor.execute("""
                UPDATE recovery_activation_state 
                SET activated = FALSE,
                    activation_code = NULL,
                    machine_fingerprint = NULL,
                    school_name = ?,
                    activated_at = NULL,
                    updated_at = ?,
                    recovered_at = ?
                WHERE id = 1
            """, (
                school_name,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            print("✅ DEBUG: Database transaction committed")
            
            log_recovery_attempt(req.email, "perform_recovery", "success", 
                               f"Recovered {len(saved_admin_ids)} admins")
            
            # Prepare response
            response_data = {
                "success": True,
                "message": "School recovery completed successfully!",
                "data": {
                    "school_name": school_name,
                    "school_email": school_email,
                    "admins_recovered": len(saved_admin_ids),
                    "recovery_timestamp": datetime.now().isoformat(),
                    "encrypted_blob_available": encrypted_blob is not None,
                    "database_updated": True,
                    "recovery_db_path": str(LOCAL_DB_PATH)
                }
            }
            
            # Add blob info if available
            if encrypted_blob:
                response_data["data"]["encrypted_blob_length"] = len(encrypted_blob)
                response_data["data"]["next_steps"] = [
                    "Option 1: Use /recovery/import-blob to send to main app",
                    "Option 2: Use /recovery/auto-import for automatic transfer",
                    "Option 3: Manually copy recovery_school.db to school.db"
                ]
                response_data["encrypted_blob"] = encrypted_blob
            
            print(f"✅ DEBUG: Recovery completed successfully for {school_name}")
            return response_data
            
        except sqlite3.Error as db_error:
            print(f"❌ DEBUG: Database error: {db_error}")
            if conn:
                conn.rollback()
                print("✅ DEBUG: Transaction rolled back")
            raise HTTPException(
                status_code=500, 
                detail=f"Database error during recovery: {str(db_error)}"
            )
        except Exception as e:
            print(f"❌ DEBUG: Unexpected error in DB operations: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
                print("✅ DEBUG: Database connection closed")
                
    except HTTPException as he:
        print(f"❌ DEBUG: HTTPException raised: {he.detail}")
        log_recovery_attempt(req.email, "perform_recovery", "error", f"HTTP: {he.detail}")
        raise
    except Exception as e:
        print(f"❌ DEBUG: Unhandled exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        log_recovery_attempt(req.email, "perform_recovery", "error", f"Unhandled: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Recovery failed: {str(e)}"
        )

@app.post("/recovery/import-blob")
async def import_recovery_blob(req: RecoveryImportRequest):
    """Import an encrypted recovery blob directly to main app"""
    try:
        # Test main app connection
        try:
            response = requests.get("http://localhost:8000/health/test", timeout=5)
            if response.status_code != 200:
                raise HTTPException(status_code=503, detail="Main app is not responding")
        except requests.exceptions.ConnectionError:
            raise HTTPException(status_code=503, detail="Cannot connect to main app. Make sure it's running on port 8000")
        
        # Send to main app's /recovery/import endpoint
        main_app_url = "http://localhost:8000/recovery/import"
        
        response = requests.post(
            main_app_url,
            json={
                "school_email": req.school_email,
                "encrypted_backup": req.encrypted_backup
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            log_recovery_attempt(
                req.school_email, 
                "import_blob", 
                "success", 
                f"Imported to main app: {result.get('admins_imported', 0)} admins"
            )
            
            return {
                "success": True,
                "message": "Recovery blob successfully imported to main app",
                "main_app_response": result
            }
        else:
            error_msg = f"Main app returned {response.status_code}: {response.text}"
            log_recovery_attempt(req.school_email, "import_blob", "failed", error_msg)
            
            return {
                "success": False,
                "message": "Failed to import to main app",
                "status_code": response.status_code,
                "error": response.text
            }
            
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Request to main app timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@app.post("/recovery/auto-import/{school_email}")
async def auto_import_recovery(school_email: str):
    """Automatically recover and import to main app in one step"""
    try:
        # First, get school data to recover
        check_result = await check_school_exists(SchoolCheckRequest(email=school_email))
        
        if not check_result.get("exists"):
            raise HTTPException(status_code=404, detail="School not found")
        
        school_data = check_result["school"]
        
        # We need school name and contact for recovery
        # In a real app, you'd get these from user input
        # For now, we'll use a simplified approach
        
        # Get full school data
        query = """
            SELECT * FROM school_installations WHERE school_email = ? LIMIT 1
        """
        result = cloud_client.execute_query(query, (school_email,))
        
        if not result.get("rows"):
            raise HTTPException(status_code=404, detail="School data not found")
        
        full_school = result["rows"][0]
        
        # Get admins
        admin_query = """
            SELECT * FROM admin_table WHERE school_id = ?
        """
        admin_result = cloud_client.execute_query(admin_query, (full_school["id"],))
        admins = admin_result.get("rows", [])
        
        if not admins:
            raise HTTPException(status_code=404, detail="No admin accounts found")
        
        # Create encrypted blob
        encrypted_blob = create_recovery_blob(full_school, admins)
        
        # Import to main app
        import_result = await import_recovery_blob(RecoveryImportRequest(
            school_email=school_email,
            encrypted_backup=encrypted_blob
        ))
        
        # Also save to recovery database
        conn = get_recovery_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO recovered_school_info 
            (school_name, email, phone, address, city, state, country, 
             created_at, updated_at, recovered_at, cloud_school_id, original_cloud_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            full_school.get("school_name"),
            full_school.get("school_email"),
            full_school.get("school_contact"),
            f"{full_school.get('town', '')}, {full_school.get('city', '')}",
            full_school.get("city"),
            full_school.get("region"),
            full_school.get("county"),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            full_school["id"],
            str(full_school)
        ))
        
        conn.commit()
        conn.close()
        
        log_recovery_attempt(school_email, "auto_import", "success", 
                           f"Auto-imported {len(admins)} admins")
        
        return {
            "success": True,
            "message": "Auto-import completed successfully",
            "data": {
                "school_name": full_school.get("school_name"),
                "admins_recovered": len(admins),
                "main_app_imported": import_result.get("success", False),
                "recovery_timestamp": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_recovery_attempt(school_email, "auto_import", "error", str(e))
        raise HTTPException(status_code=500, detail=f"Auto-import failed: {str(e)}")

@app.get("/recovery-status")
async def get_recovery_status():
    """Get the current recovery status from local recovery database"""
    try:
        conn = get_recovery_db_connection()
        cursor = conn.cursor()
        
        # Check recovered school info
        cursor.execute("SELECT COUNT(*) FROM recovered_school_info")
        school_count = cursor.fetchone()[0]
        
        # Check recovered admins
        cursor.execute("SELECT COUNT(*) FROM recovered_users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        # Check activation state
        cursor.execute("SELECT activated FROM recovery_activation_state WHERE id = 1")
        activation_state = cursor.fetchone()
        
        # Get latest recovery log
        cursor.execute("""
            SELECT school_email, recovery_type, status, recovered_at 
            FROM recovery_logs 
            ORDER BY recovered_at DESC 
            LIMIT 1
        """)
        latest_log = cursor.fetchone()
        
        conn.close()
        
        status = {
            "recovery_database": "online",
            "school_recovered": school_count > 0,
            "admins_recovered": admin_count > 0,
            "system_activated": bool(activation_state[0]) if activation_state else False,
            "school_count": school_count,
            "admin_count": admin_count,
            "last_recovery_attempt": None
        }
        
        if latest_log:
            status["last_recovery_attempt"] = {
                "school_email": latest_log[0],
                "type": latest_log[1],
                "status": latest_log[2],
                "timestamp": latest_log[3]
            }
        
        return status
        
    except Exception as e:
        return {
            "recovery_database": "offline",
            "error": str(e),
            "school_recovered": False,
            "admins_recovered": False,
            "system_activated": False
        }

@app.get("/recovery/blob/{school_email}")
async def get_recovery_blob(school_email: str):
    """Get encrypted recovery blob for a specific school"""
    try:
        if not cloud_client.check_connection():
            raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
        # Get school data
        query = """
            SELECT * FROM school_installations WHERE school_email = ? LIMIT 1
        """
        result = cloud_client.execute_query(query, (school_email,))
        
        if not result.get("rows"):
            raise HTTPException(status_code=404, detail="School not found")
        
        school_data = result["rows"][0]
        
        # Get admins
        admin_query = """
            SELECT * FROM admin_table WHERE school_id = ?
        """
        admin_result = cloud_client.execute_query(admin_query, (school_data["id"],))
        admins = admin_result.get("rows", [])
        
        if not admins:
            raise HTTPException(status_code=404, detail="No admin accounts found")
        
        # Create encrypted blob
        encrypted_blob = create_recovery_blob(school_data, admins)
        
        return {
            "success": True,
            "school_email": school_email,
            "school_name": school_data.get("school_name"),
            "encrypted_backup": encrypted_blob,
            "admins_count": len(admins),
            "blob_length": len(encrypted_blob),
            "issued_at": datetime.now().isoformat(),
            "usage": "Use this with POST /recovery/import-blob or main app's /recovery/import"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create recovery blob: {str(e)}")

@app.post("/transfer-to-main")
async def transfer_to_main_database():
    """Transfer recovered data to the main school database (legacy method)"""
    try:
        # Check if main app is running
        try:
            response = requests.get("http://localhost:8000/health/test", timeout=5)
            if response.status_code != 200:
                return {
                    "success": False,
                    "message": "Main app is not running. Start it on port 8000 first.",
                    "alternative": "Use /recovery/auto-import instead"
                }
        except:
            return {
                "success": False,
                "message": "Cannot connect to main app",
                "alternative": "Start main app on port 8000 or use manual database copy"
            }
        
        # Get recovered school data
        conn = get_recovery_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM recovered_school_info LIMIT 1")
        school_row = cursor.fetchone()
        
        if not school_row:
            conn.close()
            return {
                "success": False,
                "message": "No recovered school data found. Perform recovery first."
            }
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        school_data = dict(zip(column_names, school_row))
        
        # Get admins
        cursor.execute("SELECT * FROM recovered_users WHERE role = 'admin'")
        admin_rows = cursor.fetchall()
        
        if not admin_rows:
            conn.close()
            return {
                "success": False,
                "message": "No recovered admin data found"
            }
        
        admin_columns = [description[0] for description in cursor.description]
        admins = [dict(zip(admin_columns, row)) for row in admin_rows]
        
        conn.close()
        
        # Create encrypted blob for transfer
        formatted_school_data = {
            "school_name": school_data.get("school_name"),
            "school_email": school_data.get("email"),
            "school_contact": school_data.get("phone"),
            "county": school_data.get("country", ""),  # Note: mapping might differ
            "region": school_data.get("state", ""),
            "city": school_data.get("city", ""),
            "town": school_data.get("address", "").split(",")[0] if school_data.get("address") else "",
            "gps_address": "",
            "manufacture_code": "",
            "created_at": school_data.get("created_at")
        }
        
        formatted_admins = []
        for admin in admins:
            # Extract original cloud data if available
            original_data = {}
            if admin.get("original_cloud_data"):
                try:
                    original_data = eval(admin.get("original_cloud_data"))
                except:
                    pass
            
            formatted_admins.append({
                "first_name": original_data.get("first_name", "Recovered"),
                "middle_name": original_data.get("middle_name", ""),
                "last_name": original_data.get("last_name", "Admin"),
                "contact": admin.get("email", ""),  # Fallback
                "email": admin.get("email"),
                "password_hash": admin.get("password_hash"),
                "created_at": admin.get("created_at")
            })
        
        encrypted_blob = create_recovery_blob(formatted_school_data, formatted_admins)
        
        # Import to main app
        import_result = await import_recovery_blob(RecoveryImportRequest(
            school_email=school_data.get("email"),
            encrypted_backup=encrypted_blob
        ))
        
        return {
            "success": import_result.get("success", False),
            "message": "Transfer attempted using encrypted blob",
            "details": {
                "school": school_data.get("school_name"),
                "admins_transferred": len(formatted_admins),
                "method": "encrypted_blob",
                "main_app_response": import_result
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting School Recovery Server on http://localhost:8001")
    print("📊 Version 2.0 - With Encrypted Blob Support")
    print("📋 Endpoints:")
    print("  - GET  /                          Server status")
    print("  - GET  /health                    Health check")
    print("  - POST /check-school              Check if school exists")
    print("  - POST /verify-recovery           Verify recovery details")
    print("  - POST /perform-recovery          Complete recovery (returns blob)")
    print("  - GET  /recovery-status           Get recovery status")
    print("  - GET  /recovery/blob/{email}     Get recovery blob")
    print("  - POST /recovery/import-blob      Import blob to main app")
    print("  - POST /recovery/auto-import/{email}  Auto recover & import")
    print("  - POST /transfer-to-main          Legacy transfer method")
    print("")
    print("🔗 Main app should be running on http://localhost:8000")
    print("🔐 Using encryption key derived from: school_email + RECOVERY_SECRET")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        log_level="info"
    )