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
# import json
# import base64
# import requests
# from cryptography.fernet import Fernet

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
#         "http://localhost:3000",
#         "http://localhost:8000"  # Allow main app
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

# class RecoveryImportRequest(BaseModel):
#     school_email: str
#     encrypted_backup: str

# # Database paths
# PROJECT_ROOT = Path(__file__).parent.parent
# LOCAL_DB_PATH = PROJECT_ROOT / "database" / "recovery_school.db"  # Separate recovery database

# # MUST match main.py's RECOVERY_SECRET
# RECOVERY_SECRET = "CHANGE_ME_IN_PRODUCTION"

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
# # ENCRYPTION FUNCTIONS (For compatibility with main app)
# # ============================================

# def derive_recovery_key(school_email: str) -> bytes:
#     """Derive encryption key from school email and secret"""
#     raw = f"{school_email}:{RECOVERY_SECRET}".encode()
#     digest = hashlib.sha256(raw).digest()
#     return base64.urlsafe_b64encode(digest[:32])  # Fernet needs 32 bytes

# def create_recovery_blob(school_data: dict, admins: list) -> str:
#     """Create encrypted recovery blob matching main app's format"""
#     # Create payload matching expected schema
#     payload = {
#         "schema_version": 1,
#         "school": {
#             "school_name": school_data.get("school_name"),
#             "school_email": school_data.get("school_email"),
#             "school_contact": school_data.get("school_contact"),
#             "county": school_data.get("county"),
#             "region": school_data.get("region"),
#             "city": school_data.get("city"),
#             "town": school_data.get("town", ""),
#             "gps_address": school_data.get("gps_address", ""),
#             "manufacture_code": school_data.get("manufacture_code", ""),
#             "created_at": school_data.get("created_at")
#         },
#         "admins": [
#             {
#                 "first_name": admin.get("first_name"),
#                 "middle_name": admin.get("middle_name", ""),
#                 "last_name": admin.get("last_name"),
#                 "contact": admin.get("contact"),
#                 "email": admin.get("email"),
#                 "password_hash": admin.get("password_hash"),
#                 "created_at": admin.get("created_at")
#             }
#             for admin in admins
#         ],
#         "issued_at": datetime.now().isoformat()
#     }
    
#     # Encrypt with Fernet
#     key = derive_recovery_key(school_data["school_email"])
#     fernet = Fernet(key)
    
#     # Encrypt JSON string
#     json_str = json.dumps(payload, default=str)
#     encrypted = fernet.encrypt(json_str.encode())
    
#     return encrypted.decode()

# def validate_recovery_payload(payload: dict):
#     """Validate recovery payload structure"""
#     required = ["schema_version", "school", "admins", "issued_at"]
#     for key in required:
#         if key not in payload:
#             raise Exception(f"Invalid recovery payload: missing {key}")

#     if payload["schema_version"] != 1:
#         raise Exception("Unsupported recovery schema version")

#     if not payload["admins"]:
#         raise Exception("Recovery payload contains no admins")

# # ============================================
# # RECOVERY ENDPOINTS
# # ============================================

# @app.get("/")
# async def root():
#     """Root endpoint - server status"""
#     return {
#         "service": "school-recovery-server",
#         "status": "online",
#         "version": "2.0.0",
#         "timestamp": datetime.now().isoformat(),
#         "features": [
#             "cloud_recovery",
#             "encrypted_blobs",
#             "direct_import"
#         ]
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
        
#         # Test main app connection
#         main_app_online = False
#         try:
#             response = requests.get("http://localhost:8000/health/test", timeout=5)
#             main_app_online = response.status_code == 200
#         except:
#             pass
        
#         return {
#             "status": "healthy" if cloud_online and db_online else "degraded",
#             "cloud_connected": cloud_online,
#             "database_connected": db_online,
#             "main_app_connected": main_app_online,
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
#     print(f"🔍 DEBUG: /perform-recovery called for email: {req.email}")
    
#     try:
#         # Input validation
#         if not req.email or "@" not in req.email:
#             raise HTTPException(status_code=400, detail="Invalid email address")
        
#         if not req.school_name or len(req.school_name.strip()) < 2:
#             raise HTTPException(status_code=400, detail="School name is required")
        
#         if not req.contact or len(req.contact.strip()) < 6:
#             raise HTTPException(status_code=400, detail="Valid contact number is required")
        
#         if not req.confirm_deactivation:
#             raise HTTPException(
#                 status_code=400, 
#                 detail="You must confirm device deactivation to proceed with recovery."
#             )
        
#         print(f"🔍 DEBUG: Input validation passed")
        
#         # Check cloud connection
#         if not cloud_client.check_connection():
#             print("❌ DEBUG: Cloud client connection failed")
#             raise HTTPException(
#                 status_code=503, 
#                 detail="Cannot connect to cloud database. Please check your internet connection."
#             )
        
#         print("✅ DEBUG: Cloud connection successful")
        
#         # Step 1: Verify school details
#         print(f"🔍 DEBUG: Calling verify_school_recovery for {req.email}")
#         verify_result = await verify_school_recovery(req)
        
#         if not verify_result.get("verified"):
#             error_msg = verify_result.get("message", "Verification failed")
#             print(f"❌ DEBUG: Verification failed: {error_msg}")
#             return {
#                 "success": False,
#                 "message": error_msg
#             }
        
#         print("✅ DEBUG: School verification successful")
        
#         school_data = verify_result["data"]["school"]
#         school_id = school_data.get("id")
        
#         if not school_id:
#             print("❌ DEBUG: No school_id in verification result")
#             raise HTTPException(status_code=500, detail="School ID not found in verification data")
        
#         print(f"✅ DEBUG: School ID: {school_id}, Name: {school_data.get('school_name')}")
        
#         # Step 2: Get full admin data (including password hashes)
#         query = """
#             SELECT id, first_name, middle_name, last_name, 
#                    contact, email, password_hash, created_at
#             FROM admin_table 
#             WHERE school_id = ? 
#             ORDER BY created_at DESC
#         """
        
#         print(f"🔍 DEBUG: Executing admin query for school_id: {school_id}")
#         result = cloud_client.execute_query(query, (school_id,))
        
#         if not result.get("success", True):
#             print(f"❌ DEBUG: Cloud query failed: {result.get('error', 'Unknown error')}")
#             raise HTTPException(
#                 status_code=500, 
#                 detail=f"Failed to query admin data: {result.get('error', 'Unknown error')}"
#             )
        
#         admins = result.get("rows", [])
#         print(f"✅ DEBUG: Found {len(admins)} admins")
        
#         if not admins:
#             raise HTTPException(
#                 status_code=404, 
#                 detail="No admin accounts found for this school."
#             )
        
#         # Step 3: Get full school data for blob creation
#         print(f"🔍 DEBUG: Getting full school data for ID: {school_id}")
#         full_school_query = """
#             SELECT * FROM school_installations WHERE id = ?
#         """
#         full_school_result = cloud_client.execute_query(full_school_query, (school_id,))
        
#         if not full_school_result.get("success", True):
#             print(f"⚠️ DEBUG: Failed to get full school data, using basic data")
#             full_school_data = school_data
#         elif not full_school_result.get("rows"):
#             print(f"⚠️ DEBUG: No rows in full school data, using basic data")
#             full_school_data = school_data
#         else:
#             full_school_data = full_school_result["rows"][0]
#             print(f"✅ DEBUG: Got full school data with {len(full_school_data)} fields")
        
#         # Step 4: Create encrypted recovery blob
#         print(f"🔍 DEBUG: Creating encrypted recovery blob...")
#         try:
#             encrypted_blob = create_recovery_blob(full_school_data, admins)
#             print(f"✅ DEBUG: Created blob of length {len(encrypted_blob)}")
#         except Exception as blob_error:
#             print(f"❌ DEBUG: Failed to create blob: {blob_error}")
#             # Continue without blob for now
#             encrypted_blob = None
        
#         # Database operations
#         conn = None
#         try:
#             conn = get_recovery_db_connection()
#             cursor = conn.cursor()
#             print("✅ DEBUG: Connected to recovery database")
            
#             # Step 5: Clear any existing recovery data for this school
#             print(f"🔍 DEBUG: Clearing existing recovery data for {req.email}")
            
#             # FIXED: Removed extra parenthesis
#             cursor.execute("DELETE FROM recovered_school_info WHERE email = ?", (req.email,))
#             cursor.execute("DELETE FROM recovered_users WHERE email IN (SELECT email FROM recovered_users WHERE email IS NOT NULL)")
            
#             deleted_schools = cursor.rowcount
#             print(f"✅ DEBUG: Deleted {deleted_schools} existing school records")
            
#             # Step 6: Save school info to recovery database
#             print(f"🔍 DEBUG: Saving school info to recovery DB")
            
#             # Prepare school data
#             school_name = school_data.get("school_name", "").strip()
#             school_email = school_data.get("school_email", "").strip()
#             school_contact = school_data.get("school_contact", "").strip()
#             town = full_school_data.get("town", "")
#             city = full_school_data.get("city", "")
#             region = full_school_data.get("region", "")
#             county = full_school_data.get("county", "")
            
#             # Validate required fields
#             if not school_name:
#                 raise ValueError("School name is required")
#             if not school_email:
#                 raise ValueError("School email is required")
            
#             address = f"{town}, {city}".strip(", ")
#             if not address or address == ", ":
#                 address = city if city else "Unknown"
            
#             cursor.execute("""
#                 INSERT INTO recovered_school_info 
#                 (school_name, email, phone, address, city, state, country, 
#                  created_at, updated_at, recovered_at, cloud_school_id, original_cloud_data)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """, (
#                 school_name,
#                 school_email,
#                 school_contact,
#                 address,
#                 city,
#                 region,
#                 county,
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat(),
#                 school_id,
#                 json.dumps(full_school_data, default=str)  # Use json.dumps instead of str()
#             ))
            
#             school_db_id = cursor.lastrowid
#             print(f"✅ DEBUG: Saved school with ID: {school_db_id}")
            
#             # Step 7: Save each admin to recovery database
#             saved_admin_ids = []
#             print(f"🔍 DEBUG: Saving {len(admins)} admins to recovery DB")
            
#             for i, admin in enumerate(admins):
#                 unique_id = str(uuid.uuid4())
#                 email = admin.get("email", "").strip()
#                 contact = admin.get("contact", "").strip()
                
#                 # Determine username
#                 if email:
#                     username = email
#                 elif contact:
#                     username = contact
#                 else:
#                     username = f"admin_{unique_id[:8]}"
                
#                 password_hash = admin.get("password_hash")
#                 if not password_hash:
#                     print(f"⚠️ DEBUG: Admin {i+1} has no password hash, using dummy")
#                     password_hash = hash_password("temporary_password")
                
#                 # Prepare original data (without password hash)
#                 original_data = {}
#                 for k, v in admin.items():
#                     if k != 'password_hash':
#                         original_data[k] = v
                
#                 try:
#                     cursor.execute("""
#                         INSERT INTO recovered_users 
#                         (unique_id, username, email, password_hash, role, status, 
#                          created_at, recovered_at, cloud_user_id, original_cloud_data)
#                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                     """, (
#                         unique_id,
#                         username,
#                         email if email else None,
#                         password_hash,
#                         "admin",
#                         "active",
#                         datetime.now().isoformat(),
#                         datetime.now().isoformat(),
#                         admin.get("id"),
#                         json.dumps(original_data, default=str)  # Use json.dumps
#                     ))
                    
#                     saved_admin_ids.append(cursor.lastrowid)
#                     print(f"  ✅ Admin {i+1}: {email or contact} saved")
                    
#                 except sqlite3.IntegrityError as e:
#                     print(f"⚠️ DEBUG: Admin {i+1} integrity error: {e}")
#                     # Try with different username
#                     username = f"admin_{uuid.uuid4().hex[:8]}"
#                     cursor.execute("""
#                         INSERT INTO recovered_users 
#                         (unique_id, username, email, password_hash, role, status, 
#                          created_at, recovered_at, cloud_user_id, original_cloud_data)
#                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                     """, (
#                         unique_id,
#                         username,
#                         email if email else None,
#                         password_hash,
#                         "admin",
#                         "active",
#                         datetime.now().isoformat(),
#                         datetime.now().isoformat(),
#                         admin.get("id"),
#                         json.dumps(original_data, default=str)
#                     ))
#                     saved_admin_ids.append(cursor.lastrowid)
            
#             print(f"✅ DEBUG: Saved {len(saved_admin_ids)} admins")
            
#             # Step 8: Ensure activation state is NOT activated
#             print(f"🔍 DEBUG: Updating activation state")
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
#                 school_name,
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat()
#             ))
            
#             conn.commit()
#             print("✅ DEBUG: Database transaction committed")
            
#             log_recovery_attempt(req.email, "perform_recovery", "success", 
#                                f"Recovered {len(saved_admin_ids)} admins")
            
#             # Prepare response
#             response_data = {
#                 "success": True,
#                 "message": "School recovery completed successfully!",
#                 "data": {
#                     "school_name": school_name,
#                     "school_email": school_email,
#                     "admins_recovered": len(saved_admin_ids),
#                     "recovery_timestamp": datetime.now().isoformat(),
#                     "encrypted_blob_available": encrypted_blob is not None,
#                     "database_updated": True,
#                     "recovery_db_path": str(LOCAL_DB_PATH)
#                 }
#             }
            
#             # Add blob info if available
#             if encrypted_blob:
#                 response_data["data"]["encrypted_blob_length"] = len(encrypted_blob)
#                 response_data["data"]["next_steps"] = [
#                     "Option 1: Use /recovery/import-blob to send to main app",
#                     "Option 2: Use /recovery/auto-import for automatic transfer",
#                     "Option 3: Manually copy recovery_school.db to school.db"
#                 ]
#                 response_data["encrypted_blob"] = encrypted_blob
            
#             print(f"✅ DEBUG: Recovery completed successfully for {school_name}")
#             return response_data
            
#         except sqlite3.Error as db_error:
#             print(f"❌ DEBUG: Database error: {db_error}")
#             if conn:
#                 conn.rollback()
#                 print("✅ DEBUG: Transaction rolled back")
#             raise HTTPException(
#                 status_code=500, 
#                 detail=f"Database error during recovery: {str(db_error)}"
#             )
#         except Exception as e:
#             print(f"❌ DEBUG: Unexpected error in DB operations: {e}")
#             if conn:
#                 conn.rollback()
#             raise e
#         finally:
#             if conn:
#                 conn.close()
#                 print("✅ DEBUG: Database connection closed")
                
#     except HTTPException as he:
#         print(f"❌ DEBUG: HTTPException raised: {he.detail}")
#         log_recovery_attempt(req.email, "perform_recovery", "error", f"HTTP: {he.detail}")
#         raise
#     except Exception as e:
#         print(f"❌ DEBUG: Unhandled exception: {type(e).__name__}: {e}")
#         import traceback
#         traceback.print_exc()
#         log_recovery_attempt(req.email, "perform_recovery", "error", f"Unhandled: {str(e)}")
#         raise HTTPException(
#             status_code=500, 
#             detail=f"Recovery failed: {str(e)}"
#         )

# @app.post("/recovery/import-blob")
# async def import_recovery_blob(req: RecoveryImportRequest):
#     """Import an encrypted recovery blob directly to main app"""
#     try:
#         # Test main app connection
#         try:
#             response = requests.get("http://localhost:8000/health/test", timeout=5)
#             if response.status_code != 200:
#                 raise HTTPException(status_code=503, detail="Main app is not responding")
#         except requests.exceptions.ConnectionError:
#             raise HTTPException(status_code=503, detail="Cannot connect to main app. Make sure it's running on port 8000")
        
#         # Send to main app's /recovery/import endpoint
#         main_app_url = "http://localhost:8000/recovery/import"
        
#         response = requests.post(
#             main_app_url,
#             json={
#                 "school_email": req.school_email,
#                 "encrypted_backup": req.encrypted_backup
#             },
#             timeout=30
#         )
        
#         if response.status_code == 200:
#             result = response.json()
            
#             log_recovery_attempt(
#                 req.school_email, 
#                 "import_blob", 
#                 "success", 
#                 f"Imported to main app: {result.get('admins_imported', 0)} admins"
#             )
            
#             return {
#                 "success": True,
#                 "message": "Recovery blob successfully imported to main app",
#                 "main_app_response": result
#             }
#         else:
#             error_msg = f"Main app returned {response.status_code}: {response.text}"
#             log_recovery_attempt(req.school_email, "import_blob", "failed", error_msg)
            
#             return {
#                 "success": False,
#                 "message": "Failed to import to main app",
#                 "status_code": response.status_code,
#                 "error": response.text
#             }
            
#     except HTTPException:
#         raise
#     except requests.exceptions.Timeout:
#         raise HTTPException(status_code=504, detail="Request to main app timed out")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

# @app.post("/recovery/auto-import/{school_email}")
# async def auto_import_recovery(school_email: str):
#     """Automatically recover and import to main app in one step"""
#     try:
#         # First, get school data to recover
#         check_result = await check_school_exists(SchoolCheckRequest(email=school_email))
        
#         if not check_result.get("exists"):
#             raise HTTPException(status_code=404, detail="School not found")
        
#         school_data = check_result["school"]
        
#         # We need school name and contact for recovery
#         # In a real app, you'd get these from user input
#         # For now, we'll use a simplified approach
        
#         # Get full school data
#         query = """
#             SELECT * FROM school_installations WHERE school_email = ? LIMIT 1
#         """
#         result = cloud_client.execute_query(query, (school_email,))
        
#         if not result.get("rows"):
#             raise HTTPException(status_code=404, detail="School data not found")
        
#         full_school = result["rows"][0]
        
#         # Get admins
#         admin_query = """
#             SELECT * FROM admin_table WHERE school_id = ?
#         """
#         admin_result = cloud_client.execute_query(admin_query, (full_school["id"],))
#         admins = admin_result.get("rows", [])
        
#         if not admins:
#             raise HTTPException(status_code=404, detail="No admin accounts found")
        
#         # Create encrypted blob
#         encrypted_blob = create_recovery_blob(full_school, admins)
        
#         # Import to main app
#         import_result = await import_recovery_blob(RecoveryImportRequest(
#             school_email=school_email,
#             encrypted_backup=encrypted_blob
#         ))
        
#         # Also save to recovery database
#         conn = get_recovery_db_connection()
#         cursor = conn.cursor()
        
#         cursor.execute("""
#             INSERT OR REPLACE INTO recovered_school_info 
#             (school_name, email, phone, address, city, state, country, 
#              created_at, updated_at, recovered_at, cloud_school_id, original_cloud_data)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """, (
#             full_school.get("school_name"),
#             full_school.get("school_email"),
#             full_school.get("school_contact"),
#             f"{full_school.get('town', '')}, {full_school.get('city', '')}",
#             full_school.get("city"),
#             full_school.get("region"),
#             full_school.get("county"),
#             datetime.now().isoformat(),
#             datetime.now().isoformat(),
#             datetime.now().isoformat(),
#             full_school["id"],
#             str(full_school)
#         ))
        
#         conn.commit()
#         conn.close()
        
#         log_recovery_attempt(school_email, "auto_import", "success", 
#                            f"Auto-imported {len(admins)} admins")
        
#         return {
#             "success": True,
#             "message": "Auto-import completed successfully",
#             "data": {
#                 "school_name": full_school.get("school_name"),
#                 "admins_recovered": len(admins),
#                 "main_app_imported": import_result.get("success", False),
#                 "recovery_timestamp": datetime.now().isoformat()
#             }
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         log_recovery_attempt(school_email, "auto_import", "error", str(e))
#         raise HTTPException(status_code=500, detail=f"Auto-import failed: {str(e)}")

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

# @app.get("/recovery/blob/{school_email}")
# async def get_recovery_blob(school_email: str):
#     """Get encrypted recovery blob for a specific school"""
#     try:
#         if not cloud_client.check_connection():
#             raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
#         # Get school data
#         query = """
#             SELECT * FROM school_installations WHERE school_email = ? LIMIT 1
#         """
#         result = cloud_client.execute_query(query, (school_email,))
        
#         if not result.get("rows"):
#             raise HTTPException(status_code=404, detail="School not found")
        
#         school_data = result["rows"][0]
        
#         # Get admins
#         admin_query = """
#             SELECT * FROM admin_table WHERE school_id = ?
#         """
#         admin_result = cloud_client.execute_query(admin_query, (school_data["id"],))
#         admins = admin_result.get("rows", [])
        
#         if not admins:
#             raise HTTPException(status_code=404, detail="No admin accounts found")
        
#         # Create encrypted blob
#         encrypted_blob = create_recovery_blob(school_data, admins)
        
#         return {
#             "success": True,
#             "school_email": school_email,
#             "school_name": school_data.get("school_name"),
#             "encrypted_backup": encrypted_blob,
#             "admins_count": len(admins),
#             "blob_length": len(encrypted_blob),
#             "issued_at": datetime.now().isoformat(),
#             "usage": "Use this with POST /recovery/import-blob or main app's /recovery/import"
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to create recovery blob: {str(e)}")

# @app.post("/transfer-to-main")
# async def transfer_to_main_database():
#     """Transfer recovered data to the main school database (legacy method)"""
#     try:
#         # Check if main app is running
#         try:
#             response = requests.get("http://localhost:8000/health/test", timeout=5)
#             if response.status_code != 200:
#                 return {
#                     "success": False,
#                     "message": "Main app is not running. Start it on port 8000 first.",
#                     "alternative": "Use /recovery/auto-import instead"
#                 }
#         except:
#             return {
#                 "success": False,
#                 "message": "Cannot connect to main app",
#                 "alternative": "Start main app on port 8000 or use manual database copy"
#             }
        
#         # Get recovered school data
#         conn = get_recovery_db_connection()
#         cursor = conn.cursor()
        
#         cursor.execute("SELECT * FROM recovered_school_info LIMIT 1")
#         school_row = cursor.fetchone()
        
#         if not school_row:
#             conn.close()
#             return {
#                 "success": False,
#                 "message": "No recovered school data found. Perform recovery first."
#             }
        
#         # Get column names
#         column_names = [description[0] for description in cursor.description]
#         school_data = dict(zip(column_names, school_row))
        
#         # Get admins
#         cursor.execute("SELECT * FROM recovered_users WHERE role = 'admin'")
#         admin_rows = cursor.fetchall()
        
#         if not admin_rows:
#             conn.close()
#             return {
#                 "success": False,
#                 "message": "No recovered admin data found"
#             }
        
#         admin_columns = [description[0] for description in cursor.description]
#         admins = [dict(zip(admin_columns, row)) for row in admin_rows]
        
#         conn.close()
        
#         # Create encrypted blob for transfer
#         formatted_school_data = {
#             "school_name": school_data.get("school_name"),
#             "school_email": school_data.get("email"),
#             "school_contact": school_data.get("phone"),
#             "county": school_data.get("country", ""),  # Note: mapping might differ
#             "region": school_data.get("state", ""),
#             "city": school_data.get("city", ""),
#             "town": school_data.get("address", "").split(",")[0] if school_data.get("address") else "",
#             "gps_address": "",
#             "manufacture_code": "",
#             "created_at": school_data.get("created_at")
#         }
        
#         formatted_admins = []
#         for admin in admins:
#             # Extract original cloud data if available
#             original_data = {}
#             if admin.get("original_cloud_data"):
#                 try:
#                     original_data = eval(admin.get("original_cloud_data"))
#                 except:
#                     pass
            
#             formatted_admins.append({
#                 "first_name": original_data.get("first_name", "Recovered"),
#                 "middle_name": original_data.get("middle_name", ""),
#                 "last_name": original_data.get("last_name", "Admin"),
#                 "contact": admin.get("email", ""),  # Fallback
#                 "email": admin.get("email"),
#                 "password_hash": admin.get("password_hash"),
#                 "created_at": admin.get("created_at")
#             })
        
#         encrypted_blob = create_recovery_blob(formatted_school_data, formatted_admins)
        
#         # Import to main app
#         import_result = await import_recovery_blob(RecoveryImportRequest(
#             school_email=school_data.get("email"),
#             encrypted_backup=encrypted_blob
#         ))
        
#         return {
#             "success": import_result.get("success", False),
#             "message": "Transfer attempted using encrypted blob",
#             "details": {
#                 "school": school_data.get("school_name"),
#                 "admins_transferred": len(formatted_admins),
#                 "method": "encrypted_blob",
#                 "main_app_response": import_result
#             }
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     print("🚀 Starting School Recovery Server on http://localhost:8001")
#     print("📊 Version 2.0 - With Encrypted Blob Support")
#     print("📋 Endpoints:")
#     print("  - GET  /                          Server status")
#     print("  - GET  /health                    Health check")
#     print("  - POST /check-school              Check if school exists")
#     print("  - POST /verify-recovery           Verify recovery details")
#     print("  - POST /perform-recovery          Complete recovery (returns blob)")
#     print("  - GET  /recovery-status           Get recovery status")
#     print("  - GET  /recovery/blob/{email}     Get recovery blob")
#     print("  - POST /recovery/import-blob      Import blob to main app")
#     print("  - POST /recovery/auto-import/{email}  Auto recover & import")
#     print("  - POST /transfer-to-main          Legacy transfer method")
#     print("")
#     print("🔗 Main app should be running on http://localhost:8000")
#     print("🔐 Using encryption key derived from: school_email + RECOVERY_SECRET")
    
#     uvicorn.run(
#         app, 
#         host="0.0.0.0", 
#         port=8001,
#         log_level="info"
#     )





















# ======================================================================================================
# // UPDATAED, VERIFICATION OF ENDPOINT AND PRIME TO MATCH ONLINE SERVER 
# // =====================================================================================================
# Cloud_backend.py
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
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
import logging
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the existing cloud client
try:
    from database.cloud_db import SQLiteCloudClient
except ImportError:
    try:
        from app.database.cloud_db import SQLiteCloudClient
    except ImportError:
        # Fallback
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from database.cloud_db import SQLiteCloudClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="School Recovery Server", 
    description="Separate backend for school account recovery",
    version="2.1.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# CONFIGURATION
# ============================================

class Config:
    # MUST match main.py's RECOVERY_SECRET
    RECOVERY_SECRET = os.getenv("RECOVERY_SECRET", "CHANGE_ME_IN_PRODUCTION")
    
    # Database paths
    PROJECT_ROOT = Path(__file__).parent.parent
    LOCAL_DB_PATH = PROJECT_ROOT / "database" / "recovery_school.db"
    
    # Connection settings
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

config = Config()

# Initialize cloud client
cloud_client = SQLiteCloudClient()

# ============================================
# REQUEST MODELS
# ============================================

class SchoolCheckRequest(BaseModel):
    email: str
    
    @validator('email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Invalid email address')
        return v.strip().lower()

class SchoolRecoveryRequest(BaseModel):
    email: str
    school_name: str
    contact: str
    confirm_deactivation: bool = False
    
    @validator('email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Invalid email address')
        return v.strip().lower()
    
    @validator('school_name')
    def validate_school_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('School name must be at least 2 characters')
        return v.strip()
    
    @validator('contact')
    def validate_contact(cls, v):
        if not v or len(v.strip()) < 6:
            raise ValueError('Contact number must be at least 6 characters')
        return v.strip()

class RecoveryImportRequest(BaseModel):
    school_email: str
    encrypted_backup: str
    
    @validator('school_email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Invalid email address')
        return v.strip().lower()

# ============================================
# LOCAL DATABASE FUNCTIONS
# ============================================

def get_local_db_connection():
    """Get connection to local recovery SQLite database"""
    try:
        config.LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(config.LOCAL_DB_PATH))
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
        
        # Create users table
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
        
        # Create school_info table
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
        
        # Create activation_state table
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
        
        # Create recovery_attempts table (replacing recovery_logs)
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
        
        conn.commit()
        conn.close()
        logger.info("✅ Recovery database initialized")
        
        # Try to create recovery_attempts table in cloud
        create_cloud_recovery_table()
        
    except Exception as e:
        logger.error(f"❌ Error initializing recovery database: {e}")
        raise

def create_cloud_recovery_table():
    """Create recovery_attempts table in cloud database"""
    try:
        if cloud_client.check_connection():
            # Check if table exists
            result = cloud_client.execute_query("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='recovery_attempts'
            """)
            
            if not result.get("rows"):
                logger.info("Creating recovery_attempts table in cloud...")
                cloud_client.execute_query("""
                    CREATE TABLE IF NOT EXISTS recovery_attempts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        ip_address TEXT,
                        timestamp DATETIME NOT NULL,
                        success BOOLEAN NOT NULL,
                        recovery_type TEXT NOT NULL,
                        details TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                logger.info("✅ Cloud recovery table initialized")
    except Exception as e:
        logger.error(f"⚠️ Could not create cloud recovery table: {e}")

# Initialize database on startup
initialize_recovery_database()

# ============================================
# UTILITY FUNCTIONS
# ============================================

def hash_password(password: str) -> str:
    """Hash password for storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def log_recovery_attempt(email: str, recovery_type: str, status: str, 
                        details: str = None, ip_address: str = "0.0.0.0"):
    """Log recovery attempts to both local and cloud databases"""
    
    success = 1 if status.lower() == "success" else 0
    
    # Log to local database
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
            0  # not synced yet
        ))
        conn.commit()
        conn.close()
        logger.debug(f"Logged to local DB: {email} - {recovery_type} - {status}")
    except Exception as e:
        logger.error(f"Error logging to local DB: {e}")
    
    # Try to log to cloud
    try:
        if cloud_client.check_connection():
            cloud_client.execute_query("""
                INSERT INTO recovery_attempts
                (email, ip_address, timestamp, success, recovery_type, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                email, 
                ip_address, 
                datetime.now().isoformat(), 
                success, 
                recovery_type, 
                details
            ))
            logger.debug(f"Logged to cloud DB: {email}")
    except Exception as e:
        logger.error(f"Could not log to cloud: {e}")

def derive_recovery_key(school_email: str) -> bytes:
    """Derive encryption key from school email and secret"""
    raw = f"{school_email}:{config.RECOVERY_SECRET}".encode()
    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest[:32])

def create_recovery_blob(school_data: dict, admins: list) -> str:
    """Create encrypted recovery blob matching main app's format"""
    # Create payload
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
    
    json_str = json.dumps(payload, default=str)
    encrypted = fernet.encrypt(json_str.encode())
    
    return encrypted.decode()

def execute_cloud_query(query: str, params: tuple = None) -> Dict[str, Any]:
    """Execute a query on SQLiteCloud using the cloud client"""
    try:
        if not cloud_client.check_connection():
            cloud_client.connect()
        
        return cloud_client.execute_query(query, params)
    except Exception as e:
        logger.error(f"Cloud query error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# ============================================
# RECOVERY ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint - server status"""
    return {
        "service": "school-recovery-server",
        "status": "online",
        "version": "2.1.0",
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
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Check cloud connection
    try:
        cloud_online = cloud_client.check_connection()
        health_status["components"]["cloud"] = "connected" if cloud_online else "disconnected"
        if not cloud_online:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["cloud"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check local database
    try:
        conn = get_local_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        health_status["components"]["local_db"] = "connected"
    except Exception as e:
        health_status["components"]["local_db"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

@app.post("/check-school")
async def check_school_exists(req: SchoolCheckRequest, request: Request):
    """Check if school exists in cloud database"""
    client_ip = request.client.host
    print(f"🔍 [CHECK-SCHOOL] Request received for email: {req.email} from IP: {client_ip}")
    print(f"🔍 [CHECK-SCHOOL] Request data: {req.dict()}")
    
    try:
        # Check cloud connection
        print(f"🔍 [CHECK-SCHOOL] Testing cloud connection...")
        cloud_connected = cloud_client.check_connection()
        print(f"🔍 [CHECK-SCHOOL] Cloud connection result: {cloud_connected}")
        
        if not cloud_connected:
            print(f"❌ [CHECK-SCHOOL] Cloud connection failed")
            log_recovery_attempt(req.email, "check_school", "failed", "Cloud not connected", client_ip)
            raise HTTPException(
                status_code=503, 
                detail="Cannot connect to cloud database. Please check your internet connection."
            )
        
        print(f"✅ [CHECK-SCHOOL] Cloud connection successful")
        
        # Query cloud database for school
        print(f"🔍 [CHECK-SCHOOL] Executing query for email: {req.email}")
        query = """
            SELECT id, school_name, school_email, school_contact, 
                   county, region, city, town, gps_address, 
                   manufacture_code, created_at
            FROM school_installations 
            WHERE school_email = ? 
            LIMIT 1
        """
        
        result = execute_cloud_query(query, (req.email,))
        print(f"🔍 [CHECK-SCHOOL] Query result: {result}")
        
        if result.get("success") and result.get("rows"):
            school = result["rows"][0]
            print(f"✅ [CHECK-SCHOOL] School found in database: {school}")
            
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
            print(f"✅ [CHECK-SCHOOL] Sanitized school data: {sanitized_school}")
            
            log_recovery_attempt(req.email, "check_school", "success", f"School found: {school.get('school_name')}", client_ip)
            
            response_data = {
                "success": True,
                "exists": True,
                "school": sanitized_school,
                "message": f"School found: {school.get('school_name')}"
            }
            print(f"✅ [CHECK-SCHOOL] Returning success response: {response_data}")
            return response_data
        else:
            print(f"⚠️ [CHECK-SCHOOL] No school found for email: {req.email}")
            log_recovery_attempt(req.email, "check_school", "failed", "School not found", client_ip)
            
            response_data = {
                "success": True,
                "exists": False,
                "message": "No school found with this email address."
            }
            print(f"⚠️ [CHECK-SCHOOL] Returning not found response: {response_data}")
            return response_data
            
    except HTTPException as he:
        print(f"❌ [CHECK-SCHOOL] HTTP Exception: {he.detail}")
        raise
    except Exception as e:
        print(f"❌ [CHECK-SCHOOL] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        log_recovery_attempt(req.email, "check_school", "error", str(e), client_ip)
        raise HTTPException(status_code=500, detail=f"Failed to check school: {str(e)}")
@app.post("/verify-recovery")
async def verify_school_recovery(req: SchoolRecoveryRequest, request: Request):
    """Verify school recovery details and get admin information"""
    client_ip = request.client.host
    
    try:
        if not cloud_client.check_connection():
            raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
        # First, verify school exists
        check_result = await check_school_exists(SchoolCheckRequest(email=req.email), request)
        
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
        
        result = execute_cloud_query(query, (school_data["id"],))
        
        if not result.get("success"):
            raise HTTPException(status_code=503, detail="Failed to query admin data")
        
        admins = result.get("rows", [])
        
        if not admins:
            return {
                "success": False,
                "message": "No admin accounts found for this school."
            }
        
        # Format admins for response
        formatted_admins = []
        for admin in admins:
            formatted_admins.append({
                "first_name": admin.get("first_name"),
                "last_name": admin.get("last_name"),
                "email": admin.get("email"),
                "contact": admin.get("contact")
            })
        
        log_recovery_attempt(req.email, "verify_recovery", "success", f"Verified: {school_data['school_name']}", client_ip)
        
        return {
            "success": True,
            "verified": True,
            "message": "School verification successful",
            "data": {
                "school": school_data,
                "admin_count": len(admins),
                "admins": formatted_admins
            },
            "warning": "Recovery will deactivate any existing device and require reactivation."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_recovery_attempt(req.email, "verify_recovery", "error", str(e), client_ip)
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

# @app.post("/perform-recovery")
# async def perform_school_recovery(req: SchoolRecoveryRequest, request: Request):
#     """Perform the complete school recovery process"""
#     client_ip = request.client.host
#     logger.info(f"🔍 /perform-recovery called for email: {req.email} from IP: {client_ip}")
    
#     try:
#         # Input validation
#         if not req.confirm_deactivation:
#             raise HTTPException(
#                 status_code=400, 
#                 detail="You must confirm device deactivation to proceed with recovery."
#             )
        
#         if not cloud_client.check_connection():
#             raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
#         # Step 1: Verify school details
#         verify_result = await verify_school_recovery(req, request)
        
#         if not verify_result.get("verified"):
#             return {
#                 "success": False,
#                 "message": verify_result.get("message", "Verification failed")
#             }
        
#         school_data = verify_result["data"]["school"]
#         school_id = school_data.get("id")
        
#         if not school_id:
#             raise HTTPException(status_code=500, detail="School ID not found in verification data")
        
#         # Step 2: Get full admin data (including password hashes)
#         admin_query = """
#             SELECT id, first_name, middle_name, last_name, 
#                    contact, email, password_hash, created_at
#             FROM admin_table 
#             WHERE school_id = ? 
#             ORDER BY created_at DESC
#         """
        
#         admin_result = execute_cloud_query(admin_query, (school_id,))
        
#         if not admin_result.get("success"):
#             raise HTTPException(status_code=503, detail="Failed to query admin data")
        
#         admins = admin_result.get("rows", [])
        
#         if not admins:
#             raise HTTPException(status_code=404, detail="No admin accounts found for this school.")
        
#         # Step 3: Get full school data for blob creation
#         full_school_query = """
#             SELECT * FROM school_installations WHERE id = ?
#         """
#         full_school_result = execute_cloud_query(full_school_query, (school_id,))
        
#         if full_school_result.get("success") and full_school_result.get("rows"):
#             full_school_data = full_school_result["rows"][0]
#         else:
#             full_school_data = school_data
        
#         # Step 4: Create encrypted recovery blob
#         try:
#             encrypted_blob = create_recovery_blob(full_school_data, admins)
#             logger.info(f"✅ Created blob of lengtllh {len(encrypted_blob)}")
#         except Exception as blob_error:
#             logger.error(f"Failed to create blob: {blob_error}")
#             encrypted_blob = None
        
#         # Step 5: Save to local database
#         conn = None
#         try:
#             conn = get_local_db_connection()
#             cursor = conn.cursor()
            
#             # Clear existing recovery data for this school
#             cursor.execute("DELETE FROM recovered_school_info WHERE email = ?", (req.email,))
#             cursor.execute("DELETE FROM recovered_users WHERE email = ?", (req.email,))
            
#             # Save school info
#             school_name = school_data.get("school_name", "").strip()
#             school_email = school_data.get("school_email", "").strip()
#             school_contact = school_data.get("school_contact", "").strip()
            
#             # Prepare address
#             town = full_school_data.get("town", "") if isinstance(full_school_data, dict) else ""
#             city = full_school_data.get("city", "") if isinstance(full_school_data, dict) else school_data.get("city", "")
#             region = full_school_data.get("region", "") if isinstance(full_school_data, dict) else school_data.get("region", "")
#             county = full_school_data.get("county", "") if isinstance(full_school_data, dict) else school_data.get("county", "")
            
#             address = f"{town}, {city}".strip(", ")
#             if not address or address == ", ":
#                 address = city if city else "Unknown"
            
#             cursor.execute("""
#                 INSERT INTO recovered_school_info 
#                 (school_name, email, phone, address, city, state, country, 
#                  created_at, updated_at, recovered_at, cloud_school_id, original_cloud_data)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """, (
#                 school_name,
#                 school_email,
#                 school_contact,
#                 address,
#                 city,
#                 region,
#                 county,
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat(),
#                 school_id,
#                 json.dumps(full_school_data if isinstance(full_school_data, dict) else {}, default=str)
#             ))
            
#             # Save admins
#             saved_admin_ids = []
#             for admin in admins:
#                 unique_id = str(uuid.uuid4())
#                 email = admin.get("email", "").strip()
#                 contact = admin.get("contact", "").strip()
                
#                 username = email or contact or f"admin_{unique_id[:8]}"
#                 password_hash = admin.get("password_hash") or hash_password("temporary_password")
                
#                 # Prepare original data (without password hash)
#                 original_data = {k: v for k, v in admin.items() if k != 'password_hash'}
                
#                 try:
#                     cursor.execute("""
#                         INSERT INTO recovered_users 
#                         (unique_id, username, email, password_hash, role, status, 
#                          created_at, recovered_at, cloud_user_id, original_cloud_data)
#                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                     """, (
#                         unique_id,
#                         username,
#                         email if email else None,
#                         password_hash,
#                         "admin",
#                         "active",
#                         datetime.now().isoformat(),
#                         datetime.now().isoformat(),
#                         admin.get("id"),
#                         json.dumps(original_data, default=str)
#                     ))
#                     saved_admin_ids.append(cursor.lastrowid)
#                 except sqlite3.IntegrityError:
#                     # Try with different username
#                     username = f"admin_{uuid.uuid4().hex[:8]}"
#                     cursor.execute("""
#                         INSERT INTO recovered_users 
#                         (unique_id, username, email, password_hash, role, status, 
#                          created_at, recovered_at, cloud_user_id, original_cloud_data)
#                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                     """, (
#                         unique_id,
#                         username,
#                         email if email else None,
#                         password_hash,
#                         "admin",
#                         "active",
#                         datetime.now().isoformat(),
#                         datetime.now().isoformat(),
#                         admin.get("id"),
#                         json.dumps(original_data, default=str)
#                     ))
#                     saved_admin_ids.append(cursor.lastrowid)
            
#             # Update activation state
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
#                 school_name,
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat()
#             ))
            
#             conn.commit()
            
#         except Exception as db_error:
#             if conn:
#                 conn.rollback()
#             logger.error(f"Database error: {db_error}")
#             raise HTTPException(status_code=500, detail=f"Database error during recovery: {str(db_error)}")
#         finally:
#             if conn:
#                 conn.close()
        
#         # Log success
#         log_recovery_attempt(req.email, "perform_recovery", "success", 
#                            f"Recovered {len(saved_admin_ids)} admins", client_ip)
        
#         # Prepare response
#         response_data = {
#             "success": True,
#             "message": "School recovery completed successfully!",
#             "data": {
#                 "school_name": school_name,
#                 "school_email": school_email,
#                 "admins_recovered": len(saved_admin_ids),
#                 "recovery_timestamp": datetime.now().isoformat(),
#                 "encrypted_blob_available": encrypted_blob is not None
#             }
#         }
        
#         if encrypted_blob:
#             response_data["data"]["encrypted_blob_length"] = len(encrypted_blob)
#             response_data["data"]["next_steps"] = [
#                 "Use /recovery/import-blob to send to main app",
#                 "Use /recovery/auto-import for automatic transfer"
#             ]
#             response_data["encrypted_blob"] = encrypted_blob
        
#         logger.info(f"✅ Recovery completed for {school_name}")
#         return response_data
                
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Unhandled exception: {e}")
#         import traceback
#         traceback.print_exc()
#         log_recovery_attempt(req.email, "perform_recovery", "error", f"Unhandled: {str(e)}", client_ip)
#         raise HTTPException(status_code=500, detail=f"Recovery failed: {str(e)}")

# @app.post("/recovery/import-blob")
# async def import_recovery_blob(req: RecoveryImportRequest, request: Request):
#     """Import an encrypted recovery blob directly to main app"""
#     client_ip = request.client.host
    
#     try:
#         # Test main app connection
#         try:
#             response = requests.get("http://localhost:8000/health/test", timeout=5)
#             if response.status_code != 200:
#                 raise HTTPException(status_code=503, detail="Main app is not responding")
#         except requests.exceptions.ConnectionError:
#             raise HTTPException(status_code=503, detail="Cannot connect to main app")
        
#         # Send to main app's import endpoint
#         main_app_url = "http://localhost:8000/recovery/import"
        
#         response = requests.post(
#             main_app_url,
#             json={
#                 "school_email": req.school_email,
#                 "encrypted_backup": req.encrypted_backup
#             },
#             timeout=30
#         )
        
#         if response.status_code == 200:
#             result = response.json()
            
#             log_recovery_attempt(
#                 req.school_email, "import_blob", "success", 
#                 f"Imported to main app: {result.get('admins_imported', 0)} admins",
#                 client_ip
#             )
            
#             return {
#                 "success": True,
#                 "message": "Recovery blob successfully imported to main app",
#                 "main_app_response": result
#             }
#         else:
#             error_msg = f"Main app returned {response.status_code}: {response.text}"
#             log_recovery_attempt(req.school_email, "import_blob", "failed", error_msg, client_ip)
            
#             return {
#                 "success": False,
#                 "message": "Failed to import to main app",
#                 "status_code": response.status_code,
#                 "error": response.text
#             }
            
#     except HTTPException:
#         raise
#     except requests.exceptions.Timeout:
#         raise HTTPException(status_code=504, detail="Request to main app timed out")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@app.post("/recovery/import-blob")
async def import_recovery_blob(req: RecoveryImportRequest, request: Request):
    """Import an encrypted recovery blob directly to main app"""
    client_ip = request.client.host
    logger.info(f"🔍 ===== IMPORT BLOB STARTED =====")
    logger.info(f"🔍 Request from IP: {client_ip}")
    logger.info(f"🔍 School email: {req.school_email}")
    logger.info(f"🔍 Encrypted blob length: {len(req.encrypted_backup) if req.encrypted_backup else 0}")
    logger.info(f"🔍 Blob preview: {req.encrypted_backup[:100] if req.encrypted_backup else 'None'}...")
    
    try:
        # Step 1: Test main app connection
        logger.info(f"🔍 Step 1: Testing main app connection to http://localhost:8000/health/test...")
        try:
            response = requests.get("http://localhost:8000/health/test", timeout=5)
            logger.info(f"🔍 Main app health check response status: {response.status_code}")
            logger.info(f"🔍 Main app health check response body: {response.text[:200]}")
            
            if response.status_code != 200:
                logger.error(f"❌ Main app returned status {response.status_code}, expected 200")
                raise HTTPException(
                    status_code=503, 
                    detail=f"Main app is not responding (status: {response.status_code})"
                )
            else:
                logger.info(f"✅ Main app is responding normally")
                
        except requests.exceptions.ConnectionError as ce:
            logger.error(f"❌ Connection error to main app: {ce}")
            logger.error(f"❌ Make sure main app is running on http://localhost:8000")
            raise HTTPException(
                status_code=503, 
                detail="Cannot connect to main app. Please ensure it's running on port 8000."
            )
        except requests.exceptions.Timeout as te:
            logger.error(f"❌ Timeout connecting to main app: {te}")
            raise HTTPException(status_code=504, detail="Connection to main app timed out")
        except Exception as e:
            logger.error(f"❌ Unexpected error checking main app: {e}")
            raise HTTPException(status_code=503, detail=f"Failed to check main app: {str(e)}")
        
        # Step 2: Send to main app's import endpoint
        main_app_url = "http://localhost:8000/recovery/import"
        logger.info(f"🔍 Step 2: Sending blob to main app at {main_app_url}")
        logger.info(f"🔍 Request payload: school_email={req.school_email}, blob_length={len(req.encrypted_backup)}")
        
        try:
            response = requests.post(
                main_app_url,
                json={
                    "school_email": req.school_email,
                    "encrypted_backup": req.encrypted_backup
                },
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"🔍 Main app import response status: {response.status_code}")
            logger.info(f"🔍 Main app import response headers: {dict(response.headers)}")
            logger.info(f"🔍 Main app import response body: {response.text[:500]}")  # Log first 500 chars
            
        except requests.exceptions.ConnectionError as ce:
            logger.error(f"❌ Connection error to main app import endpoint: {ce}")
            raise HTTPException(
                status_code=503, 
                detail="Cannot connect to main app import endpoint"
            )
        except requests.exceptions.Timeout as te:
            logger.error(f"❌ Timeout sending to main app: {te}")
            raise HTTPException(status_code=504, detail="Request to main app timed out")
        except Exception as e:
            logger.error(f"❌ Error sending to main app: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error sending to main app: {str(e)}")
        
        # Step 3: Process response
        if response.status_code == 200:
            try:
                result = response.json()
                logger.info(f"✅ Successfully parsed main app response JSON")
                logger.info(f"✅ Main app response: {result}")
                
                log_recovery_attempt(
                    req.school_email, "import_blob", "success", 
                    f"Imported to main app: {result.get('admins_imported', 0)} admins",
                    client_ip
                )
                
                return {
                    "success": True,
                    "message": "Recovery blob successfully imported to main app",
                    "main_app_response": result
                }
                
            except ValueError as json_error:
                logger.error(f"❌ Failed to parse main app response as JSON: {json_error}")
                logger.error(f"❌ Raw response: {response.text[:500]}")
                return {
                    "success": False,
                    "message": "Invalid JSON response from main app",
                    "status_code": response.status_code,
                    "error": str(json_error),
                    "raw_response": response.text[:500]
                }
        else:
            error_msg = f"Main app returned {response.status_code}: {response.text[:500]}"
            logger.error(f"❌ {error_msg}")
            
            log_recovery_attempt(
                req.school_email, "import_blob", "failed", 
                error_msg, 
                client_ip
            )
            
            return {
                "success": False,
                "message": "Failed to import to main app",
                "status_code": response.status_code,
                "error": response.text[:500]
            }
            
    except HTTPException as he:
        logger.error(f"❌ HTTPException: {he.detail}")
        raise
    except requests.exceptions.Timeout:
        logger.error("❌ Request to main app timed out")
        raise HTTPException(status_code=504, detail="Request to main app timed out")
    except Exception as e:
        logger.error(f"❌ Unhandled exception in import_blob: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        logger.info(f"🔍 ===== IMPORT BLOB COMPLETED =====\n")



# @app.post("/perform-recovery")
# async def perform_school_recovery(req: SchoolRecoveryRequest, request: Request):
#     """Perform the complete school recovery process"""
#     client_ip = request.client.host
#     logger.info(f"🔍 /perform-recovery called for email: {req.email} from IP: {client_ip}")
    
#     try:
#         # Input validation
#         if not req.confirm_deactivation:
#             raise HTTPException(
#                 status_code=400, 
#                 detail="You must confirm device deactivation to proceed with recovery."
#             )
        
#         if not cloud_client.check_connection():
#             raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
#         # Step 1: Verify school details
#         verify_result = await verify_school_recovery(req, request)
        
#         if not verify_result.get("verified"):
#             return {
#                 "success": False,
#                 "message": verify_result.get("message", "Verification failed")
#             }
        
#         school_data = verify_result["data"]["school"]
#         school_id = school_data.get("id")
        
#         if not school_id:
#             raise HTTPException(status_code=500, detail="School ID not found in verification data")
        
#         # Step 2: Get full admin data (including password hashes)
#         admin_query = """
#             SELECT id, first_name, middle_name, last_name, 
#                    contact, email, password_hash, created_at
#             FROM admin_table 
#             WHERE school_id = ? 
#             ORDER BY created_at DESC
#         """
        
#         admin_result = execute_cloud_query(admin_query, (school_id,))
        
#         if not admin_result.get("success"):
#             raise HTTPException(status_code=503, detail="Failed to query admin data")
        
#         admins = admin_result.get("rows", [])
        
#         if not admins:
#             raise HTTPException(status_code=404, detail="No admin accounts found for this school.")
        
#         logger.info(f"Found {len(admins)} admins to recover")
        
#         # Step 3: Get full school data for blob creation
#         full_school_query = """
#             SELECT * FROM school_installations WHERE id = ?
#         """
#         full_school_result = execute_cloud_query(full_school_query, (school_id,))
        
#         if full_school_result.get("success") and full_school_result.get("rows"):
#             full_school_data = full_school_result["rows"][0]
#         else:
#             full_school_data = school_data
        
#         # Step 4: Create encrypted recovery blob
#         try:
#             encrypted_blob = create_recovery_blob(full_school_data, admins)
#             logger.info(f"✅ Created blob of length {len(encrypted_blob)}")
#         except Exception as blob_error:
#             logger.error(f"Failed to create blob: {blob_error}")
#             encrypted_blob = None
        
#         # Step 5: Save to local database with SIMPLE approach
#         conn = None
#         try:
#             conn = get_local_db_connection()
#             cursor = conn.cursor()
            
#             # Start transaction
#             cursor.execute("BEGIN TRANSACTION")
            
#             # SIMPLE FIX: First, delete ONLY the conflicting records
#             admin_emails = []
#             for admin in admins:
#                 email = admin.get("email", "").strip()
#                 if email:
#                     admin_emails.append(email)
#                     # Delete any existing record with this email
#                     cursor.execute("DELETE FROM recovered_users WHERE email = ?", (email,))
#                     logger.info(f"Deleted existing record for email: {email}")
            
#             logger.info(f"Cleared {len(admin_emails)} potential conflicts")
            
#             # Save school info (use INSERT OR REPLACE)
#             school_name = school_data.get("school_name", "").strip()
#             school_email = school_data.get("school_email", "").strip()
#             school_contact = school_data.get("school_contact", "").strip()
            
#             # Prepare address
#             town = full_school_data.get("town", "") if isinstance(full_school_data, dict) else ""
#             city = full_school_data.get("city", "") if isinstance(full_school_data, dict) else school_data.get("city", "")
#             region = full_school_data.get("region", "") if isinstance(full_school_data, dict) else school_data.get("region", "")
#             county = full_school_data.get("county", "") if isinstance(full_school_data, dict) else school_data.get("county", "")
            
#             address = f"{town}, {city}".strip(", ")
#             if not address or address == ", ":
#                 address = city if city else "Unknown"
            
#             # Use INSERT OR REPLACE for school
#             cursor.execute("""
#                 INSERT OR REPLACE INTO recovered_school_info 
#                 (id, school_name, email, phone, address, city, state, country, 
#                  created_at, updated_at, recovered_at, cloud_school_id, original_cloud_data)
#                 VALUES (
#                     COALESCE((SELECT id FROM recovered_school_info WHERE email = ?), NULL),
#                     ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
#                 )
#             """, (
#                 school_email,  # for subquery
#                 school_name,
#                 school_email,
#                 school_contact,
#                 address,
#                 city,
#                 region,
#                 county,
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat(),
#                 school_id,
#                 json.dumps(full_school_data if isinstance(full_school_data, dict) else {}, default=str)
#             ))
            
#             logger.info(f"Saved school info")
            
#             # Save admins - NOW with clean slate
#             saved_admin_ids = []
#             failed_admins = []
            
#             for i, admin in enumerate(admins):
#                 try:
#                     unique_id = str(uuid.uuid4())
#                     email = admin.get("email", "").strip()
#                     contact = admin.get("contact", "").strip()
                    
#                     logger.info(f"Processing admin {i+1}: email='{email}'")
                    
#                     password_hash = admin.get("password_hash")
#                     if not password_hash:
#                         password_hash = hash_password("temporary_password")
                    
#                     # Prepare original data
#                     original_data = {k: v for k, v in admin.items() if k != 'password_hash'}
                    
#                     if email:
#                         # Simple insert - we already deleted conflicts
#                         cursor.execute("""
#                             INSERT INTO recovered_users 
#                             (unique_id, username, email, password_hash, role, status, 
#                              created_at, recovered_at, cloud_user_id, original_cloud_data)
#                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                         """, (
#                             unique_id,
#                             email,
#                             email,
#                             password_hash,
#                             "admin",
#                             "active",
#                             datetime.now().isoformat(),
#                             datetime.now().isoformat(),
#                             admin.get("id"),
#                             json.dumps(original_data, default=str)
#                         ))
#                     else:
#                         # Admin without email
#                         username = f"admin_{contact}_{unique_id[:8]}" if contact else f"admin_{unique_id[:8]}"
#                         cursor.execute("""
#                             INSERT INTO recovered_users 
#                             (unique_id, username, email, password_hash, role, status, 
#                              created_at, recovered_at, cloud_user_id, original_cloud_data)
#                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                         """, (
#                             unique_id,
#                             username,
#                             None,
#                             password_hash,
#                             "admin",
#                             "active",
#                             datetime.now().isoformat(),
#                             datetime.now().isoformat(),
#                             admin.get("id"),
#                             json.dumps(original_data, default=str)
#                         ))
                    
#                     saved_admin_ids.append(cursor.lastrowid)
#                     logger.info(f"✅ Admin {i+1} saved successfully")
                    
#                 except Exception as admin_error:
#                     logger.error(f"❌ Error for admin {i+1}: {admin_error}")
#                     failed_admins.append({
#                         "admin": {
#                             "id": admin.get("id"),
#                             "email": admin.get("email", ""),
#                             "contact": admin.get("contact", "")
#                         }, 
#                         "error": str(admin_error)
#                     })
            
#             # Update activation state
#             cursor.execute("""
#                 INSERT OR REPLACE INTO recovery_activation_state 
#                 (id, activated, school_name, updated_at, recovered_at)
#                 VALUES (1, FALSE, ?, ?, ?)
#             """, (
#                 school_name,
#                 datetime.now().isoformat(),
#                 datetime.now().isoformat()
#             ))
            
#             # Commit transaction
#             conn.commit()
#             logger.info(f"✅ Transaction committed. Saved {len(saved_admin_ids)} admins, Failed: {len(failed_admins)}")
            
#         except Exception as db_error:
#             if conn:
#                 conn.rollback()
#                 logger.error(f"Database error, rolled back: {db_error}")
#             raise HTTPException(status_code=500, detail=f"Database error during recovery: {str(db_error)}")
#         finally:
#             if conn:
#                 conn.close()
        
#         # Log success/failure
#         log_recovery_attempt(
#             req.email, "perform_recovery", 
#             "success" if saved_admin_ids else "failed", 
#             f"Recovered {len(saved_admin_ids)} admins, Failed: {len(failed_admins)}", 
#             client_ip
#         )
        
#         # Prepare response
#         response_data = {
#             "success": True if saved_admin_ids else False,
#             "message": f"Recovery completed. Recovered {len(saved_admin_ids)} out of {len(admins)} admins.",
#             "data": {
#                 "school_name": school_name,
#                 "school_email": school_email,
#                 "admins_recovered": len(saved_admin_ids),
#                 "admins_failed": len(failed_admins),
#                 "total_admins": len(admins),
#                 "recovery_timestamp": datetime.now().isoformat(),
#                 "encrypted_blob_available": encrypted_blob is not None
#             }
#         }
        
#         if failed_admins:
#             response_data["warning"] = f"Failed to recover {len(failed_admins)} admin(s)."
        
#         if encrypted_blob:
#             response_data["encrypted_blob"] = encrypted_blob
        
#         return response_data
                
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Unhandled exception: {e}")
#         log_recovery_attempt(req.email, "perform_recovery", "error", str(e), client_ip)
#         raise HTTPException(status_code=500, detail=f"Recovery failed: {str(e)}")




@app.post("/perform-recovery")
async def perform_school_recovery(req: SchoolRecoveryRequest, request: Request):
    """Perform the complete school recovery process"""
    client_ip = request.client.host
    logger.info(f"🔍 ===== PERFORM RECOVERY STARTED =====")
    logger.info(f"🔍 Request: email={req.email}, school_name={req.school_name}, contact={req.contact}, confirm_deactivation={req.confirm_deactivation}")
    logger.info(f"🔍 Client IP: {client_ip}")
    
    try:
        # Input validation
        logger.info(f"🔍 Step 1: Validating input...")
        if not req.confirm_deactivation:
            logger.error(f"❌ Validation failed: confirm_deactivation is false")
            raise HTTPException(
                status_code=400, 
                detail="You must confirm device deactivation to proceed with recovery."
            )
        logger.info(f"✅ Input validation passed")
        
        # Check cloud connection
        logger.info(f"🔍 Step 2: Checking cloud connection...")
        cloud_connected = cloud_client.check_connection()
        logger.info(f"🔍 Cloud connection result: {cloud_connected}")
        
        if not cloud_connected:
            logger.error(f"❌ Cloud connection failed")
            raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        logger.info(f"✅ Cloud connection successful")
        
        # Step 1: Verify school details
        logger.info(f"🔍 Step 3: Verifying school details for {req.email}...")
        verify_result = await verify_school_recovery(req, request)
        logger.info(f"🔍 Verify result: {verify_result}")
        
        if not verify_result.get("verified"):
            logger.warning(f"⚠️ Verification failed: {verify_result.get('message')}")
            return {
                "success": False,
                "message": verify_result.get("message", "Verification failed")
            }
        logger.info(f"✅ School verification successful")
        
        school_data = verify_result["data"]["school"]
        school_id = school_data.get("id")
        logger.info(f"🔍 School data: ID={school_id}, Name={school_data.get('school_name')}, Email={school_data.get('school_email')}")
        
        if not school_id:
            logger.error(f"❌ School ID not found in verification data")
            raise HTTPException(status_code=500, detail="School ID not found in verification data")
        
        # Step 2: Get full admin data
        logger.info(f"🔍 Step 4: Querying admin data for school_id={school_id}...")
        admin_query = """
            SELECT id, first_name, middle_name, last_name, 
                   contact, email, password_hash, created_at
            FROM admin_table 
            WHERE school_id = ? 
            ORDER BY created_at DESC
        """
        
        admin_result = execute_cloud_query(admin_query, (school_id,))
        logger.info(f"🔍 Admin query result success: {admin_result.get('success')}")
        logger.info(f"🔍 Admin rows count: {len(admin_result.get('rows', []))}")
        
        if not admin_result.get("success"):
            logger.error(f"❌ Admin query failed: {admin_result.get('error', 'Unknown error')}")
            raise HTTPException(status_code=503, detail="Failed to query admin data")
        
        admins = admin_result.get("rows", [])
        
        if not admins:
            logger.warning(f"⚠️ No admin accounts found for school_id={school_id}")
            raise HTTPException(status_code=404, detail="No admin accounts found for this school.")
        
        logger.info(f"✅ Found {len(admins)} admins to recover")
        for i, admin in enumerate(admins):
            logger.info(f"  Admin {i+1}: ID={admin.get('id')}, Email={admin.get('email')}, Contact={admin.get('contact')}")
        
        # Step 3: Get full school data
        logger.info(f"🔍 Step 5: Getting full school data for school_id={school_id}...")
        full_school_query = """
            SELECT * FROM school_installations WHERE id = ?
        """
        full_school_result = execute_cloud_query(full_school_query, (school_id,))
        logger.info(f"🔍 Full school query success: {full_school_result.get('success')}")
        
        if full_school_result.get("success") and full_school_result.get("rows"):
            full_school_data = full_school_result["rows"][0]
            logger.info(f"✅ Retrieved full school data with {len(full_school_data)} fields")
            logger.info(f"🔍 Full school data preview: {dict(list(full_school_data.items())[:5])}")  # First 5 fields
        else:
            full_school_data = school_data
            logger.info(f"⚠️ Using basic school data as fallback")
        
        # Step 4: Create encrypted recovery blob
        logger.info(f"🔍 Step 6: Creating encrypted recovery blob...")
        encrypted_blob = None
        try:
            encrypted_blob = create_recovery_blob(full_school_data, admins)
            logger.info(f"✅ Created blob of length {len(encrypted_blob)}")
            logger.info(f"✅ Blob preview: {encrypted_blob[:100]}...")
        except Exception as blob_error:
            logger.error(f"❌ Failed to create blob: {blob_error}")
            import traceback
            traceback.print_exc()
            # Continue without blob - don't fail the whole recovery
        
        # Step 5: Save to local database
        logger.info(f"🔍 Step 7: Saving to local database...")
        conn = None
        saved_admin_ids = []
        failed_admins = []
        school_name = school_data.get("school_name", "").strip()
        school_email = school_data.get("school_email", "").strip()
        
        try:
            logger.info(f"🔍 Connecting to local database at LOCAL_DB_PATH...")
            conn = get_local_db_connection()
            cursor = conn.cursor()
            logger.info(f"✅ Connected to local database")
            
            # Start transaction
            logger.info(f"🔍 Starting transaction...")
            cursor.execute("BEGIN TRANSACTION")
            logger.info(f"✅ Transaction started")
            
            # Delete existing records
            logger.info(f"🔍 Clearing existing records...")
            admin_emails = []
            for admin in admins:
                email = admin.get("email", "").strip()
                if email:
                    admin_emails.append(email)
                    cursor.execute("DELETE FROM recovered_users WHERE email = ?", (email,))
                    logger.info(f"  Deleted {cursor.rowcount} existing record(s) for email: {email}")
            
            logger.info(f"✅ Cleared {len(admin_emails)} potential conflicts")
            
            # Prepare school data
            school_contact = school_data.get("school_contact", "").strip()
            
            # Prepare address
            town = full_school_data.get("town", "") if isinstance(full_school_data, dict) else ""
            city = full_school_data.get("city", "") if isinstance(full_school_data, dict) else school_data.get("city", "")
            region = full_school_data.get("region", "") if isinstance(full_school_data, dict) else school_data.get("region", "")
            county = full_school_data.get("county", "") if isinstance(full_school_data, dict) else school_data.get("county", "")
            
            address = f"{town}, {city}".strip(", ")
            if not address or address == ", ":
                address = city if city else "Unknown"
            
            logger.info(f"🔍 School data to save: name={school_name}, email={school_email}, contact={school_contact}, address={address}")
            
            # Save school info
            logger.info(f"🔍 Saving school info...")
            cursor.execute("""
                INSERT OR REPLACE INTO recovered_school_info 
                (id, school_name, email, phone, address, city, state, country, 
                 created_at, updated_at, recovered_at, cloud_school_id, original_cloud_data)
                VALUES (
                    COALESCE((SELECT id FROM recovered_school_info WHERE email = ?), NULL),
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                school_email,  # for subquery
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
                json.dumps(full_school_data if isinstance(full_school_data, dict) else {}, default=str)
            ))
            logger.info(f"✅ Saved school info, rowid: {cursor.lastrowid}")
            
            # Save admins
            logger.info(f"🔍 Saving {len(admins)} admins...")
            for i, admin in enumerate(admins):
                try:
                    unique_id = str(uuid.uuid4())
                    email = admin.get("email", "").strip()
                    contact = admin.get("contact", "").strip()
                    
                    logger.info(f"  Processing admin {i+1}/{len(admins)}: ID={admin.get('id')}, email='{email}', contact='{contact}'")
                    
                    password_hash = admin.get("password_hash")
                    if not password_hash:
                        logger.warning(f"  ⚠️ Admin {i+1} has no password hash, using temporary")
                        password_hash = hash_password("temporary_password")
                    
                    # Prepare original data (without password hash)
                    original_data = {k: v for k, v in admin.items() if k != 'password_hash'}
                    
                    if email:
                        # Admin with email
                        cursor.execute("""
                            INSERT INTO recovered_users 
                            (unique_id, username, email, password_hash, role, status, 
                             created_at, recovered_at, cloud_user_id, original_cloud_data)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            unique_id,
                            email,
                            email,
                            password_hash,
                            "admin",
                            "active",
                            datetime.now().isoformat(),
                            datetime.now().isoformat(),
                            admin.get("id"),
                            json.dumps(original_data, default=str)
                        ))
                        logger.info(f"  ✅ Admin {i+1} saved with email as username")
                    else:
                        # Admin without email
                        username = f"admin_{contact}_{unique_id[:8]}" if contact else f"admin_{unique_id[:8]}"
                        logger.info(f"  🔍 Admin {i+1} has no email, using generated username: {username}")
                        cursor.execute("""
                            INSERT INTO recovered_users 
                            (unique_id, username, email, password_hash, role, status, 
                             created_at, recovered_at, cloud_user_id, original_cloud_data)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            unique_id,
                            username,
                            None,
                            password_hash,
                            "admin",
                            "active",
                            datetime.now().isoformat(),
                            datetime.now().isoformat(),
                            admin.get("id"),
                            json.dumps(original_data, default=str)
                        ))
                        logger.info(f"  ✅ Admin {i+1} saved with generated username")
                    
                    saved_admin_ids.append(cursor.lastrowid)
                    
                except Exception as admin_error:
                    logger.error(f"  ❌ Error for admin {i+1}: {admin_error}")
                    import traceback
                    traceback.print_exc()
                    failed_admins.append({
                        "admin": {
                            "id": admin.get("id"),
                            "email": admin.get("email", ""),
                            "contact": admin.get("contact", "")
                        }, 
                        "error": str(admin_error)
                    })
            
            logger.info(f"✅ Successfully saved {len(saved_admin_ids)} admins, Failed: {len(failed_admins)}")
            
            # Update activation state
            logger.info(f"🔍 Updating activation state...")
            cursor.execute("""
                INSERT OR REPLACE INTO recovery_activation_state 
                (id, activated, school_name, updated_at, recovered_at)
                VALUES (1, FALSE, ?, ?, ?)
            """, (
                school_name,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            logger.info(f"✅ Activation state updated")
            
            # Commit transaction
            logger.info(f"🔍 Committing transaction...")
            conn.commit()
            logger.info(f"✅ Transaction committed successfully")
            
        except Exception as db_error:
            if conn:
                logger.error(f"❌ Database error, rolling back: {db_error}")
                conn.rollback()
                logger.info(f"✅ Transaction rolled back")
            logger.error(f"❌ Database error details: {db_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Database error during recovery: {str(db_error)}")
        finally:
            if conn:
                conn.close()
                logger.info(f"✅ Database connection closed")
        
        # Log success/failure
        log_recovery_attempt(
            req.email, "perform_recovery", 
            "success" if saved_admin_ids else "failed", 
            f"Recovered {len(saved_admin_ids)} admins, Failed: {len(failed_admins)}", 
            client_ip
        )
        
        # Prepare response
        logger.info(f"🔍 Step 8: Preparing response...")
        response_data = {
            "success": True if saved_admin_ids else False,
            "message": f"Recovery completed. Recovered {len(saved_admin_ids)} out of {len(admins)} admins.",
            "data": {
                "school_name": school_name,
                "school_email": school_email,
                "admins_recovered": len(saved_admin_ids),
                "admins_failed": len(failed_admins),
                "total_admins": len(admins),
                "recovery_timestamp": datetime.now().isoformat(),
                "encrypted_blob_available": encrypted_blob is not None
            }
        }
        
        if failed_admins:
            response_data["warning"] = f"Failed to recover {len(failed_admins)} admin(s)."
            logger.info(f"⚠️ Warning: {len(failed_admins)} admins failed")
        
        if encrypted_blob:
            response_data["encrypted_blob"] = encrypted_blob
            logger.info(f"✅ Including encrypted blob in response (length: {len(encrypted_blob)})")
        else:
            logger.info(f"⚠️ No encrypted blob available to include in response")
        
        logger.info(f"✅ Response prepared: success={response_data['success']}, message={response_data['message']}")
        logger.info(f"✅ ===== PERFORM RECOVERY COMPLETED SUCCESSFULLY ===== for {school_name}")
        return response_data
                
    except HTTPException as he:
        logger.error(f"❌ HTTPException: {he.detail}")
        log_recovery_attempt(req.email, "perform_recovery", "error", f"HTTP: {he.detail}", client_ip)
        raise
    except Exception as e:
        logger.error(f"❌ Unhandled exception: {e}")
        import traceback
        traceback.print_exc()
        log_recovery_attempt(req.email, "perform_recovery", "error", str(e), client_ip)
        raise HTTPException(status_code=500, detail=f"Recovery failed: {str(e)}")


@app.post("/recovery/auto-import/{school_email}")
async def auto_import_recovery(school_email: str, request: Request):
    """Automatically recover and import to main app in one step"""
    client_ip = request.client.host
    
    try:
        # First, get school data
        check_result = await check_school_exists(SchoolCheckRequest(email=school_email), request)
        
        if not check_result.get("exists"):
            raise HTTPException(status_code=404, detail="School not found")
        
        school_data = check_result["school"]
        
        # Get full school data
        query = """
            SELECT * FROM school_installations WHERE school_email = ? LIMIT 1
        """
        result = execute_cloud_query(query, (school_email,))
        
        if not result.get("success") or not result.get("rows"):
            raise HTTPException(status_code=404, detail="School data not found")
        
        full_school = result["rows"][0]
        
        # Get admins
        admin_query = """
            SELECT * FROM admin_table WHERE school_id = ?
        """
        admin_result = execute_cloud_query(admin_query, (school_data["id"],))
        
        if not admin_result.get("success") or not admin_result.get("rows"):
            raise HTTPException(status_code=404, detail="No admin accounts found")
        
        admins = admin_result["rows"]
        
        # Create encrypted blob
        encrypted_blob = create_recovery_blob(full_school, admins)
        
        # Import to main app
        import_result = await import_recovery_blob(
            RecoveryImportRequest(
                school_email=school_email,
                encrypted_backup=encrypted_blob
            ), 
            request
        )
        
        # Also save to local database
        conn = get_local_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO recovered_school_info 
            (school_name, email, phone, address, city, state, country, 
             created_at, updated_at, recovered_at, cloud_school_id, original_cloud_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            full_school.get("school_name"),
            school_email,
            full_school.get("school_contact"),
            f"{full_school.get('town', '')}, {full_school.get('city', '')}",
            full_school.get("city"),
            full_school.get("region"),
            full_school.get("county"),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            school_data["id"],
            json.dumps(full_school, default=str)
        ))
        conn.commit()
        conn.close()
        
        log_recovery_attempt(school_email, "auto_import", "success", 
                           f"Auto-imported {len(admins)} admins", client_ip)
        
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
        log_recovery_attempt(school_email, "auto_import", "error", str(e), client_ip)
        raise HTTPException(status_code=500, detail=f"Auto-import failed: {str(e)}")


@app.get("/recovery-status")
async def get_recovery_status():
    """Get the current recovery status from local recovery database"""
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        # Check recovered school info
        cursor.execute("SELECT COUNT(*) FROM recovered_school_info")
        school_count = cursor.fetchone()[0]
        
        # Get school details
        school_details = None
        if school_count > 0:
            cursor.execute("""
                SELECT school_name, email, recovered_at 
                FROM recovered_school_info 
                ORDER BY recovered_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                school_details = {
                    "name": row[0],
                    "email": row[1],
                    "recovered_at": row[2]
                }
        
        # Check recovered admins
        cursor.execute("SELECT COUNT(*) FROM recovered_users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        # Check activation state
        cursor.execute("SELECT activated, school_name FROM recovery_activation_state WHERE id = 1")
        activation_row = cursor.fetchone()
        activation_state = bool(activation_row[0]) if activation_row else False
        activated_school = activation_row[1] if activation_row else None
        
        # Get latest recovery attempt
        cursor.execute("""
            SELECT email, recovery_type, success, timestamp 
            FROM recovery_attempts 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        latest_log = cursor.fetchone()
        
        conn.close()
        
        status = {
            "recovery_database": "online",
            "school_recovered": school_count > 0,
            "admins_recovered": admin_count > 0,
            "system_activated": activation_state,
            "school_count": school_count,
            "admin_count": admin_count,
            "activated_school": activated_school,
            "last_recovery_attempt": None
        }
        
        if school_details:
            status["recovered_school"] = school_details
        
        if latest_log:
            status["last_recovery_attempt"] = {
                "email": latest_log[0],
                "type": latest_log[1],
                "success": bool(latest_log[2]),
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
async def get_recovery_blob(school_email: str, request: Request):
    """Get encrypted recovery blob for a specific school"""
    client_ip = request.client.host
    
    try:
        if not cloud_client.check_connection():
            raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
        # Get school data
        query = """
            SELECT * FROM school_installations WHERE school_email = ? LIMIT 1
        """
        result = execute_cloud_query(query, (school_email,))
        
        if not result.get("success") or not result.get("rows"):
            raise HTTPException(status_code=404, detail="School not found")
        
        school_data = result["rows"][0]
        
        # Get admins
        admin_query = """
            SELECT * FROM admin_table WHERE school_id = ?
        """
        admin_result = execute_cloud_query(admin_query, (school_data.get("id"),))
        
        if not admin_result.get("success") or not admin_result.get("rows"):
            raise HTTPException(status_code=404, detail="No admin accounts found")
        
        admins = admin_result["rows"]
        
        # Create encrypted blob
        encrypted_blob = create_recovery_blob(school_data, admins)
        
        log_recovery_attempt(school_email, "get_blob", "success", 
                           f"Generated blob for {school_data.get('school_name')}", client_ip)
        
        return {
            "success": True,
            "school_email": school_email,
            "school_name": school_data.get("school_name"),
            "encrypted_backup": encrypted_blob,
            "admins_count": len(admins),
            "blob_length": len(encrypted_blob),
            "issued_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create recovery blob: {str(e)}")

@app.post("/transfer-to-main")
async def transfer_to_main_database(request: Request):
    """Transfer recovered data to the main school database"""
    client_ip = request.client.host
    
    try:
        # Check if main app is running
        try:
            response = requests.get("http://localhost:8000/health/test", timeout=5)
            if response.status_code != 200:
                return {
                    "success": False,
                    "message": "Main app is not running",
                    "alternative": "Use /recovery/auto-import instead"
                }
        except:
            return {
                "success": False,
                "message": "Cannot connect to main app",
                "alternative": "Start main app on port 8000"
            }
        
        # Get recovered school data
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM recovered_school_info LIMIT 1")
        school_row = cursor.fetchone()
        
        if not school_row:
            conn.close()
            return {
                "success": False,
                "message": "No recovered school data found. Perform recovery first."
            }
        
        # Convert row to dict
        school_data = dict(school_row)
        
        # Get admins
        cursor.execute("SELECT * FROM recovered_users WHERE role = 'admin'")
        admin_rows = cursor.fetchall()
        
        if not admin_rows:
            conn.close()
            return {
                "success": False,
                "message": "No recovered admin data found"
            }
        
        admins = [dict(row) for row in admin_rows]
        conn.close()
        
        # Create encrypted blob for transfer
        formatted_school_data = {
            "school_name": school_data.get("school_name"),
            "school_email": school_data.get("email"),
            "school_contact": school_data.get("phone"),
            "county": school_data.get("country", ""),
            "region": school_data.get("state", ""),
            "city": school_data.get("city", ""),
            "town": school_data.get("address", "").split(",")[0] if school_data.get("address") else "",
            "gps_address": "",
            "manufacture_code": "",
            "created_at": school_data.get("created_at")
        }
        
        formatted_admins = []
        for admin in admins:
            original_data = {}
            if admin.get("original_cloud_data"):
                try:
                    original_data = json.loads(admin.get("original_cloud_data"))
                except:
                    pass
            
            formatted_admins.append({
                "first_name": original_data.get("first_name", "Recovered"),
                "middle_name": original_data.get("middle_name", ""),
                "last_name": original_data.get("last_name", "Admin"),
                "contact": admin.get("email", ""),
                "email": admin.get("email"),
                "password_hash": admin.get("password_hash"),
                "created_at": admin.get("created_at")
            })
        
        encrypted_blob = create_recovery_blob(formatted_school_data, formatted_admins)
        
        # Import to main app
        import_result = await import_recovery_blob(
            RecoveryImportRequest(
                school_email=school_data.get("email"),
                encrypted_backup=encrypted_blob
            ), 
            request
        )
        
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
    print("📊 Version 2.1.0 - Using SQLiteCloud Client")
    print("📋 Endpoints:")
    print("  - GET  /                          Server status")
    print("  - GET  /health                    Health check")
    print("  - POST /check-school              Check if school exists")
    print("  - POST /verify-recovery           Verify recovery details")
    print("  - POST /perform-recovery          Complete recovery")
    print("  - GET  /recovery-status           Get recovery status")
    print("  - GET  /recovery/blob/{email}     Get recovery blob")
    print("  - POST /recovery/import-blob      Import blob to main app")
    print("  - POST /recovery/auto-import/{email}  Auto recover & import")
    print("  - POST /transfer-to-main          Legacy transfer method")
    
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "cloud_backend:app",
        host=host, 
        port=port,
        log_level="info",
        reload=False
    )