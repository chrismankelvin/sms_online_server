from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
from dotenv import load_dotenv
import json  # Add this with your other imports
import uuid
import requests  # Add this at the top of your file if not already there
# Load environment variables
load_dotenv()

from app.database.cloud_db import SQLiteCloudClient
from app.models.schemas import (
    SchoolCheckRequest, SchoolRecoveryRequest,
    RecoveryImportRequest, HealthResponse
)
from app.utils.helpers import (
    get_local_db_connection, initialize_recovery_database,
    log_recovery_attempt, create_recovery_blob,
       LOCAL_DB_PATH ,
    RecoveryDatabaseManager,
    hash_password
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.getenv("DEBUG", "false").lower() != "true" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
class Settings:
    RECOVERY_SECRET = os.getenv("RECOVERY_SECRET", "CHANGE_ME_IN_PRODUCTION")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "[]")
    
    @property
    def cors_origins_list(self) -> list:
        import json
        try:
            return json.loads(self.CORS_ORIGINS)
        except:
            return ["http://localhost:5173", "http://localhost:3000"]

settings = Settings()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up School Recovery Server...")
    
    # Initialize cloud client
    app.state.cloud_client = SQLiteCloudClient()
    
    # Test connection
    if app.state.cloud_client.check_connection():
        logger.info("✅ Connected to SQLiteCloud")
    else:
        logger.warning("⚠️ Could not connect to SQLiteCloud")
    
    # Initialize local database
    initialize_recovery_database()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if hasattr(app.state, 'cloud_client'):
        app.state.cloud_client.close()

# Create FastAPI app
app = FastAPI(
    title="School Recovery Server",
    description="Separate backend for school account recovery",
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get cloud client
def get_cloud_client(request: Request) -> SQLiteCloudClient:
    return request.app.state.cloud_client

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"}
    )

# ============================================
# HEALTH ENDPOINTS
# ============================================

@app.get("/", response_model=dict)
async def root():
    """Root endpoint - server status"""
    return {
        "service": "school-recovery-server",
        "status": "online",
        "version": app.version,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(cloud_client: SQLiteCloudClient = Depends(get_cloud_client)):
    """Health check endpoint"""
    health = HealthResponse()
    
    # Check cloud connection
    try:
        health.components.cloud = "connected" if cloud_client.check_connection() else "disconnected"
        health.status = "healthy" if health.components.cloud == "connected" else "degraded"
    except Exception as e:
        health.components.cloud = f"error: {str(e)}"
        health.status = "degraded"
    
    # Check local database
    try:
        conn = get_local_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        health.components.local_db = "connected"
    except Exception as e:
        health.components.local_db = f"error: {str(e)}"
        health.status = "degraded"
    
    return health

# ============================================
# RECOVERY ENDPOINTS
# ============================================

@app.post("/check-school")
async def check_school_exists(
    req: SchoolCheckRequest, 
    request: Request,
    cloud_client: SQLiteCloudClient = Depends(get_cloud_client)
):
    """Check if school exists in cloud database"""
    client_ip = request.client.host
    logger.info(f"Check school request for {req.email} from {client_ip}")
    
    try:
        if not cloud_client.check_connection():
            log_recovery_attempt(req.email, "check_school", "failed", "Cloud not connected", client_ip)
            raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
        query = """
            SELECT id, school_name, school_email, school_contact, 
                   county, region, city, town, gps_address, 
                   manufacture_code, created_at
            FROM school_installations 
            WHERE school_email = ? 
            LIMIT 1
        """
        
        result = cloud_client.execute_query(query, (req.email,))
        
        if result.get("success") and result.get("rows"):
            school = result["rows"][0]
            
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
            
            log_recovery_attempt(req.email, "check_school", "success", 
                               f"School found: {school.get('school_name')}", client_ip)
            
            return {
                "success": True,
                "exists": True,
                "school": sanitized_school,
                "message": f"School found: {school.get('school_name')}"
            }
        else:
            log_recovery_attempt(req.email, "check_school", "failed", "School not found", client_ip)
            return {
                "success": True,
                "exists": False,
                "message": "No school found with this email address."
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Check school error: {e}")
        log_recovery_attempt(req.email, "check_school", "error", str(e), client_ip)
        raise HTTPException(status_code=500, detail=f"Failed to check school: {str(e)}")


from datetime import datetime
# [Include other endpoint implementations here - verify-recovery, perform-recovery, etc.]

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
async def health_check(cloud_client: SQLiteCloudClient = Depends(get_cloud_client)):
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

# @app.post("/check-school")
# async def check_school_exists(req: SchoolCheckRequest, request: Request):
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
async def verify_school_recovery(
    req: SchoolRecoveryRequest, 
    request: Request,
    cloud_client: SQLiteCloudClient = Depends(get_cloud_client)  # Add this dependency
):
    """Verify school recovery details and get admin information"""
    client_ip = request.client.host
    
    try:
        if not cloud_client.check_connection():
            raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
        # First, verify school exists - make sure to pass cloud_client
        check_result = await check_school_exists(
            SchoolCheckRequest(email=req.email), 
            request,
            cloud_client  # Pass the cloud_client here
        )
        
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
        
        # Get admin information from cloud - USE cloud_client, not execute_cloud_query
        query = """
            SELECT id, first_name, middle_name, last_name, 
                   contact, email, password_hash, created_at
            FROM admin_table 
            WHERE school_id = ? 
            ORDER BY created_at DESC
        """
        
        result = cloud_client.execute_query(query, (school_data["id"],))  # Use cloud_client here
        
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




@app.post("/recovery/import-blob")
async def import_recovery_blob(req: RecoveryImportRequest, request: Request):
    """Import an encrypted recovery blob directly to main app"""
    client_ip = request.client.host
    
    try:
        # Test main app connection
        try:
            response = requests.get("http://localhost:8000/health/test", timeout=5)
            if response.status_code != 200:
                raise HTTPException(status_code=503, detail="Main app is not responding")
        except requests.exceptions.ConnectionError:
            raise HTTPException(status_code=503, detail="Cannot connect to main app")
        
        # Send to main app's import endpoint
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
                req.school_email, "import_blob", "success", 
                f"Imported to main app: {result.get('admins_imported', 0)} admins",
                client_ip
            )
            
            return {
                "success": True,
                "message": "Recovery blob successfully imported to main app",
                "main_app_response": result
            }
        else:
            error_msg = f"Main app returned {response.status_code}: {response.text}"
            log_recovery_attempt(req.school_email, "import_blob", "failed", error_msg, client_ip)
            
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





@app.post("/perform-recovery")
async def perform_school_recovery(
    req: SchoolRecoveryRequest, 
    request: Request,
    cloud_client: SQLiteCloudClient = Depends(get_cloud_client)
):
    """Perform the complete school recovery process"""
    client_ip = request.client.host
    logger.info(f"🔍 ===== STARTING PERFORM RECOVERY =====")
    logger.info(f"🔍 Request: email={req.email}, school_name={req.school_name}, contact={req.contact}, confirm={req.confirm_deactivation}")
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
        try:
            verify_result = await verify_school_recovery(req, request, cloud_client)
            logger.info(f"🔍 Verify result: {verify_result}")
        except Exception as verify_error:
            logger.error(f"❌ Error in verify_school_recovery: {verify_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Verification failed: {str(verify_error)}")
        
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
        
        try:
            admin_result = cloud_client.execute_query(admin_query, (school_id,))
            logger.info(f"🔍 Admin query result success: {admin_result.get('success')}")
            logger.info(f"🔍 Admin rows count: {len(admin_result.get('rows', []))}")
        except Exception as admin_query_error:
            logger.error(f"❌ Error executing admin query: {admin_query_error}")
            raise HTTPException(status_code=503, detail=f"Failed to query admin data: {str(admin_query_error)}")
        
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
        
        try:
            full_school_result = cloud_client.execute_query(full_school_query, (school_id,))
            logger.info(f"🔍 Full school query success: {full_school_result.get('success')}")
        except Exception as school_query_error:
            logger.error(f"❌ Error executing school query: {school_query_error}")
            full_school_data = school_data
            logger.info(f"⚠️ Using basic school data as fallback")
        else:
            if full_school_result.get("success") and full_school_result.get("rows"):
                full_school_data = full_school_result["rows"][0]
                logger.info(f"✅ Retrieved full school data with {len(full_school_data)} fields")
            else:
                full_school_data = school_data
                logger.info(f"⚠️ Using basic school data as fallback")
        
        # Step 4: Create encrypted recovery blob
        logger.info(f"🔍 Step 6: Creating encrypted recovery blob...")
        encrypted_blob = None
        blob_created = False
        try:
            encrypted_blob = create_recovery_blob(full_school_data, admins)
            blob_created = True
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
            logger.info(f"🔍 Connecting to local database at {LOCAL_DB_PATH}...")
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
                    delete_result = cursor.execute("DELETE FROM recovered_users WHERE email = ?", (email,))
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
                        logger.info(f"  ✅ Admin {i+1} saved with generated username: {username}")
                    
                    saved_admin_ids.append(cursor.lastrowid)
                    
                except Exception as admin_error:
                    logger.error(f"  ❌ Error for admin {i+1}: {admin_error}")
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
                "encrypted_blob_available": blob_created
            }
        }
        
        # Add warning if some admins failed
        if failed_admins:
            response_data["warning"] = f"Failed to recover {len(failed_admins)} admin(s)."
            logger.info(f"⚠️ Warning: {len(failed_admins)} admins failed")
        
        # Only include encrypted_blob if it was successfully created
        if blob_created and encrypted_blob:
            response_data["encrypted_blob"] = encrypted_blob
            response_data["data"]["encrypted_blob_length"] = len(encrypted_blob)
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
async def auto_import_recovery(
    school_email: str, 
    request: Request,
    cloud_client: SQLiteCloudClient = Depends(get_cloud_client)  # Add dependency
):
    """Automatically recover and import to main app in one step"""
    client_ip = request.client.host
    logger.info(f"🔍 Auto-import requested for {school_email} from {client_ip}")
    
    try:
        # First, get school data
        check_result = await check_school_exists(
            SchoolCheckRequest(email=school_email), 
            request,
            cloud_client  # Pass cloud_client
        )
        
        if not check_result.get("exists"):
            raise HTTPException(status_code=404, detail="School not found")
        
        school_data = check_result["school"]
        
        # Get full school data
        query = """
            SELECT * FROM school_installations WHERE school_email = ? LIMIT 1
        """
        result = cloud_client.execute_query(query, (school_email,))  # Use cloud_client
        
        if not result.get("success") or not result.get("rows"):
            raise HTTPException(status_code=404, detail="School data not found")
        
        full_school = result["rows"][0]
        
        # Get admins
        admin_query = """
            SELECT * FROM admin_table WHERE school_id = ?
        """
        admin_result = cloud_client.execute_query(admin_query, (school_data["id"],))  # Use cloud_client
        
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
        
        # Prepare address
        town = full_school.get("town", "")
        city = full_school.get("city", "")
        address = f"{town}, {city}".strip(", ")
        if not address or address == ", ":
            address = city if city else "Unknown"
        
        cursor.execute("""
            INSERT OR REPLACE INTO recovered_school_info 
            (school_name, email, phone, address, city, state, country, 
             created_at, updated_at, recovered_at, cloud_school_id, original_cloud_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            full_school.get("school_name"),
            school_email,
            full_school.get("school_contact"),
            address,
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
        logger.error(f"Auto-import error: {e}")
        log_recovery_attempt(school_email, "auto_import", "error", str(e), client_ip)
        raise HTTPException(status_code=500, detail=f"Auto-import failed: {str(e)}")

@app.get("/recovery-status")
async def get_recovery_status():
    """Get the current recovery status from local recovery database"""
    logger.info("🔍 Recovery status requested")
    
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        # Check recovered school info
        cursor.execute("SELECT COUNT(*) FROM recovered_school_info")
        school_count = cursor.fetchone()[0]
        logger.info(f"School count: {school_count}")
        
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
        logger.info(f"Admin count: {admin_count}")
        
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
        
        logger.info(f"✅ Recovery status: {status}")
        return status
        
    except Exception as e:
        logger.error(f"Error getting recovery status: {e}")
        return {
            "recovery_database": "offline",
            "error": str(e),
            "school_recovered": False,
            "admins_recovered": False,
            "system_activated": False
        }

@app.get("/recovery/blob/{school_email}")
async def get_recovery_blob(
    school_email: str, 
    request: Request,
    cloud_client: SQLiteCloudClient = Depends(get_cloud_client)  # Add dependency
):
    """Get encrypted recovery blob for a specific school"""
    client_ip = request.client.host
    logger.info(f"🔍 Recovery blob requested for {school_email} from {client_ip}")
    
    try:
        if not cloud_client.check_connection():
            raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
        # Get school data
        query = """
            SELECT * FROM school_installations WHERE school_email = ? LIMIT 1
        """
        result = cloud_client.execute_query(query, (school_email,))  # Use cloud_client
        
        if not result.get("success") or not result.get("rows"):
            raise HTTPException(status_code=404, detail="School not found")
        
        school_data = result["rows"][0]
        
        # Get admins
        admin_query = """
            SELECT * FROM admin_table WHERE school_id = ?
        """
        admin_result = cloud_client.execute_query(admin_query, (school_data.get("id"),))  # Use cloud_client
        
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
        logger.error(f"Error creating recovery blob: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create recovery blob: {str(e)}")

@app.post("/transfer-to-main")
async def transfer_to_main_database(
    request: Request,
    cloud_client: SQLiteCloudClient = Depends(get_cloud_client)  # Add dependency
):
    """Transfer recovered data to the main school database"""
    client_ip = request.client.host
    logger.info(f"🔍 Transfer to main requested from {client_ip}")
    
    try:
        # Check if main app is running
        try:
            response = request.get("http://localhost:8000/health/test", timeout=5)
            if response.status_code != 200:
                logger.warning("Main app is not responding")
                return {
                    "success": False,
                    "message": "Main app is not running",
                    "alternative": "Use /recovery/auto-import instead"
                }
        except requests.exceptions.ConnectionError:
            logger.warning("Cannot connect to main app")
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
            logger.warning("No recovered school data found")
            return {
                "success": False,
                "message": "No recovered school data found. Perform recovery first."
            }
        
        # Get column names and convert row to dict
        columns = [description[0] for description in cursor.description]
        school_data = dict(zip(columns, school_row))
        
        # Get admins
        cursor.execute("SELECT * FROM recovered_users WHERE role = 'admin'")
        admin_rows = cursor.fetchall()
        
        if not admin_rows:
            conn.close()
            logger.warning("No recovered admin data found")
            return {
                "success": False,
                "message": "No recovered admin data found"
            }
        
        admin_columns = [description[0] for description in cursor.description]
        admins = [dict(zip(admin_columns, row)) for row in admin_rows]
        conn.close()
        
        logger.info(f"Found {len(admins)} recovered admins for school {school_data.get('school_name')}")
        
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
        
        logger.info(f"Transfer completed: {import_result.get('success', False)}")
        
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
        logger.error(f"Transfer error: {e}")
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "app.main:app",
        host=host, 
        port=port,
        log_level="info",
        reload=settings.DEBUG
    )



# Import datetime at the top
