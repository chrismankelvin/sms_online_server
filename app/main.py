# from fastapi import FastAPI, HTTPException, Request, Depends
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# from contextlib import asynccontextmanager
# import logging
# import os
# from dotenv import load_dotenv
# from datetime import datetime
# from typing import Optional

# load_dotenv()

# from app.database.cloud_db import SQLiteCloudClient
# from app.models.schemas import (
#     SchoolCheckRequest, SchoolRecoveryRequest,
#     HealthResponse, VerifyRecoveryResponse
# )
# from app.utils.crypto import create_recovery_blob, verify_school_credentials

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO if os.getenv("DEBUG", "false").lower() != "true" else logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)

# # Configuration
# class Settings:
#     ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
#     DEBUG = os.getenv("DEBUG", "false").lower() == "true"
#     CORS_ORIGINS = os.getenv("CORS_ORIGINS", '["http://localhost:5173", "http://localhost:3000"]')
    
#     @property
#     def cors_origins_list(self) -> list:
#         import json
#         try:
#             return json.loads(self.CORS_ORIGINS)
#         except:
#             return ["http://localhost:5173", "http://localhost:3000"]

# settings = Settings()

# # Lifespan context manager
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     logger.info("Starting up Stateless School Recovery Server...")
    
#     # Initialize cloud client
#     app.state.cloud_client = SQLiteCloudClient()
    
#     # Test connection
#     if app.state.cloud_client.check_connection():
#         logger.info("✅ Connected to SQLiteCloud")
#     else:
#         logger.warning("⚠️ Could not connect to SQLiteCloud - server will start but recovery may fail")
    
#     yield
    
#     # Shutdown
#     logger.info("Shutting down...")
#     if hasattr(app.state, 'cloud_client'):
#         app.state.cloud_client.close()

# # Create FastAPI app
# app = FastAPI(
#     title="School Recovery Server (Stateless)",
#     description="Stateless proxy for school account recovery - no local database",
#     version="3.0.0",
#     lifespan=lifespan,
#     docs_url="/docs" if settings.DEBUG else None,
#     redoc_url="/redoc" if settings.DEBUG else None
# )

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.cors_origins_list,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Dependency to get cloud client
# def get_cloud_client(request: Request) -> SQLiteCloudClient:
#     return request.app.state.cloud_client

# # Exception handler
# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     logger.error(f"Unhandled exception: {exc}", exc_info=True)
#     return JSONResponse(
#         status_code=500,
#         content={"detail": "An internal server error occurred"}
#     )

# # ============================================
# # HEALTH ENDPOINTS
# # ============================================

# @app.get("/", response_model=dict)
# async def root():
#     """Root endpoint - server status"""
#     return {
#         "service": "school-recovery-server",
#         "status": "online",
#         "version": app.version,
#         "environment": settings.ENVIRONMENT,
#         "type": "stateless",
#         "timestamp": datetime.now().isoformat()
#     }

# @app.get("/health", response_model=HealthResponse)
# async def health_check(cloud_client: SQLiteCloudClient = Depends(get_cloud_client)):
#     """Health check endpoint - checks cloud connectivity only"""
#     health = HealthResponse()
    
#     # Check cloud connection
#     try:
#         health.components.cloud = "connected" if cloud_client.check_connection() else "disconnected"
#         health.status = "healthy" if health.components.cloud == "connected" else "degraded"
#     except Exception as e:
#         health.components.cloud = f"error: {str(e)}"
#         health.status = "degraded"
    
#     # No local DB check - we're stateless!
#     health.components.local_db = "not_applicable"
    
#     return health

# # ============================================
# # RECOVERY ENDPOINTS (STATELESS)
# # ============================================

# @app.post("/check-school")
# async def check_school_exists(
#     req: SchoolCheckRequest, 
#     request: Request,
#     cloud_client: SQLiteCloudClient = Depends(get_cloud_client)
# ):
#     """
#     Check if school exists in cloud database.
#     Returns school info if found (no sensitive data).
#     """
#     client_ip = request.client.host
#     logger.info(f"Check school request for {req.email} from {client_ip}")
    
#     try:
#         if not cloud_client.check_connection():
#             raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
#         query = """
#             SELECT id, school_name, school_email, school_contact, 
#                    county, region, city, town, created_at
#             FROM school_installations 
#             WHERE school_email = ? 
#             LIMIT 1
#         """
        
#         result = cloud_client.execute_query(query, (req.email,))
        
#         if result.get("success") and result.get("rows"):
#             school = result["rows"][0]
            
#             # Return only non-sensitive info
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
            
#             return {
#                 "success": True,
#                 "exists": True,
#                 "school": sanitized_school,
#                 "message": f"School found: {school.get('school_name')}"
#             }
#         else:
#             return {
#                 "success": True,
#                 "exists": False,
#                 "message": "No school found with this email address."
#             }
            
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Check school error: {e}")
#         raise HTTPException(status_code=500, detail=f"Failed to check school: {str(e)}")

# @app.post("/verify-recovery")
# async def verify_school_recovery(
#     req: SchoolRecoveryRequest, 
#     request: Request,
#     cloud_client: SQLiteCloudClient = Depends(get_cloud_client)
# ):
#     """
#     Verify school recovery details and get admin information.
#     NO data is stored - just verification.
#     """
#     client_ip = request.client.host
#     logger.info(f"Verify recovery request for {req.email} from {client_ip}")
    
#     try:
#         if not cloud_client.check_connection():
#             raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
#         # Get school from cloud
#         school_query = """
#             SELECT id, school_name, school_email, school_contact, 
#                    county, region, city, town, created_at
#             FROM school_installations 
#             WHERE school_email = ? 
#             LIMIT 1
#         """
        
#         school_result = cloud_client.execute_query(school_query, (req.email,))
        
#         if not school_result.get("success") or not school_result.get("rows"):
#             return {
#                 "success": False,
#                 "verified": False,
#                 "message": "School not found. Please check the email address."
#             }
        
#         school_data = school_result["rows"][0]
        
#         # Verify credentials
#         if not verify_school_credentials(school_data, req.school_name, req.contact):
#             return {
#                 "success": False,
#                 "verified": False,
#                 "message": "School name or contact number does not match our records."
#             }
        
#         # Get admin information from cloud
#         admin_query = """
#             SELECT id, first_name, last_name, contact, email, created_at
#             FROM admin_table 
#             WHERE school_id = ? 
#             ORDER BY created_at DESC
#         """
        
#         admin_result = cloud_client.execute_query(admin_query, (school_data["id"],))
        
#         if not admin_result.get("success") or not admin_result.get("rows"):
#             return {
#                 "success": False,
#                 "verified": False,
#                 "message": "No admin accounts found for this school."
#             }
        
#         admins = admin_result["rows"]
        
#         # Format admins for response (no password hashes)
#         formatted_admins = []
#         for admin in admins:
#             formatted_admins.append({
#                 "first_name": admin.get("first_name"),
#                 "last_name": admin.get("last_name"),
#                 "email": admin.get("email"),
#                 "contact": admin.get("contact")
#             })
        
#         return {
#             "success": True,
#             "verified": True,
#             "message": "School verification successful",
#             "data": {
#                 "school": {
#                     "id": school_data.get("id"),
#                     "school_name": school_data.get("school_name"),
#                     "school_email": school_data.get("school_email"),
#                     "county": school_data.get("county"),
#                     "region": school_data.get("region"),
#                     "city": school_data.get("city")
#                 },
#                 "admin_count": len(admins),
#                 "admins": formatted_admins
#             },
#             "warning": "Recovery will deactivate any existing device and require reactivation."
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Verification error: {e}")
#         raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

# @app.post("/perform-recovery")
# async def perform_school_recovery(
#     req: SchoolRecoveryRequest, 
#     request: Request,
#     cloud_client: SQLiteCloudClient = Depends(get_cloud_client)
# ):
#     """
#     Perform complete school recovery - returns encrypted blob directly.
#     NO data is stored on this server.
#     Main app should handle the import.
#     """
#     client_ip = request.client.host
#     logger.info(f"Perform recovery request for {req.email} from {client_ip}")
    
#     try:
#         # Validate confirmation
#         if not req.confirm_deactivation:
#             raise HTTPException(
#                 status_code=400, 
#                 detail="You must confirm device deactivation to proceed with recovery."
#             )
        
#         if not cloud_client.check_connection():
#             raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
#         # Get full school data
#         school_query = """
#             SELECT * FROM school_installations WHERE school_email = ? LIMIT 1
#         """
#         school_result = cloud_client.execute_query(school_query, (req.email,))
        
#         if not school_result.get("success") or not school_result.get("rows"):
#             raise HTTPException(status_code=404, detail="School not found")
        
#         school_data = school_result["rows"][0]
        
#         # Verify credentials
#         if not verify_school_credentials(school_data, req.school_name, req.contact):
#             raise HTTPException(status_code=401, detail="Invalid school credentials")
        
#         # Get all admins
#         admin_query = """
#             SELECT * FROM admin_table WHERE school_id = ?
#         """
#         admin_result = cloud_client.execute_query(admin_query, (school_data["id"],))
        
#         if not admin_result.get("success") or not admin_result.get("rows"):
#             raise HTTPException(status_code=404, detail="No admin accounts found for this school")
        
#         admins = admin_result["rows"]
        
#         # Create encrypted recovery blob
#         try:
#             encrypted_blob = create_recovery_blob(school_data, admins)
#         except Exception as e:
#             logger.error(f"Failed to create recovery blob: {e}")
#             raise HTTPException(status_code=500, detail=f"Failed to create recovery blob: {str(e)}")
        
#         # Return blob directly - NO STORAGE
#         return {
#             "success": True,
#             "message": f"Recovery blob created successfully for {school_data['school_name']}",
#             "data": {
#                 "school_name": school_data["school_name"],
#                 "school_email": school_data["school_email"],
#                 "admins_count": len(admins),
#                 "recovery_timestamp": datetime.now().isoformat()
#             },
#             "encrypted_blob": encrypted_blob,
#             "blob_length": len(encrypted_blob)
#         }
                
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Recovery error: {e}")
#         raise HTTPException(status_code=500, detail=f"Recovery failed: {str(e)}")

# # ============================================
# # SIMPLE TEST ENDPOINT (for debugging)
# # ============================================

# @app.get("/ping")
# async def ping():
#     """Simple ping endpoint to test if server is alive"""
#     return {"pong": True, "timestamp": datetime.now().isoformat()}

# # Run with: uvicorn app.main:app --host 0.0.0.0 --port 8001
# if __name__ == "__main__":
#     import uvicorn
#     port = int(os.getenv("PORT", 8001))
#     host = os.getenv("HOST", "0.0.0.0")
    
#     uvicorn.run(
#         "app.main:app",
#         host=host, 
#         port=port,
#         log_level="info",
#         reload=settings.DEBUG
#     )





from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional

load_dotenv()

from app.database.cloud_db import SQLiteCloudClient
from app.models.schemas import (
    SchoolCheckRequest, SchoolRecoveryRequest,
    HealthResponse
)
from app.utils.crypto import create_recovery_blob, verify_school_credentials
from app.config.settings import settings
from app.middleware.auth import verify_api_key, rate_limiter

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting School Recovery Server (Production Mode)")
    logger.info(f"📡 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔑 Loaded {len(settings.api_keys_list)} API keys")
    logger.info(f"⏱️  Rate limits: {settings.RATE_LIMIT_PER_MINUTE}/min, {settings.RATE_LIMIT_PER_HOUR}/hour, {settings.RATE_LIMIT_PER_DAY}/day")
    
    # Initialize cloud client
    app.state.cloud_client = SQLiteCloudClient()
    
    # Test connection
    if app.state.cloud_client.check_connection():
        logger.info("✅ Connected to SQLiteCloud")
    else:
        logger.warning("⚠️ Could not connect to SQLiteCloud")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if hasattr(app.state, 'cloud_client'):
        app.state.cloud_client.close()

# Create FastAPI app
app = FastAPI(
    title="School Recovery Server",
    description="Secure stateless recovery server with API authentication and rate limiting",
    version="3.0.0",
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
# PUBLIC ENDPOINTS (no auth required)
# ============================================

@app.get("/", response_model=dict)
async def root():
    """Root endpoint - server status"""
    return {
        "service": "school-recovery-server",
        "status": "online",
        "version": app.version,
        "environment": settings.ENVIRONMENT,
        "type": "stateless",
        "authentication": "required",
        "rate_limits": {
            "per_minute": settings.RATE_LIMIT_PER_MINUTE,
            "per_hour": settings.RATE_LIMIT_PER_HOUR,
            "per_day": settings.RATE_LIMIT_PER_DAY
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(cloud_client: SQLiteCloudClient = Depends(get_cloud_client)):
    """Health check endpoint - no auth required"""
    health = HealthResponse()
    
    # Check cloud connection
    try:
        health.components.cloud = "connected" if cloud_client.check_connection() else "disconnected"
        health.status = "healthy" if health.components.cloud == "connected" else "degraded"
    except Exception as e:
        health.components.cloud = f"error: {str(e)}"
        health.status = "degraded"
    
    health.components.local_db = "not_applicable"
    
    return health

# ============================================
# PROTECTED ENDPOINTS (auth + rate limiting)
# ============================================

@app.post("/check-school")
async def check_school_exists(
    req: SchoolCheckRequest, 
    request: Request,
    cloud_client: SQLiteCloudClient = Depends(get_cloud_client),
    api_key: str = Depends(verify_api_key)  # REQUIRED
):
    """
    Check if school exists in cloud database.
    Requires: Authorization: Bearer <api_key>
    Rate limits: 10/min, 60/hour, 100/day
    """
    client_ip = request.client.host
    
    # Rate limiting check
    if not rate_limiter.is_allowed(api_key, settings.RATE_LIMIT_PER_MINUTE, 60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    
    logger.info(f"Check school request for {req.email} from {client_ip} (API Key: {api_key[:8]}...)")
    
    try:
        if not cloud_client.check_connection():
            raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
        query = """
            SELECT id, school_name, school_email, school_contact, 
                   county, region, city, town, created_at
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
            
            return {
                "success": True,
                "exists": True,
                "school": sanitized_school,
                "message": f"School found: {school.get('school_name')}"
            }
        else:
            return {
                "success": True,
                "exists": False,
                "message": "No school found with this email address."
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Check school error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check school: {str(e)}")

@app.post("/verify-recovery")
async def verify_school_recovery(
    req: SchoolRecoveryRequest, 
    request: Request,
    cloud_client: SQLiteCloudClient = Depends(get_cloud_client),
    api_key: str = Depends(verify_api_key)  # REQUIRED
):
    """
    Verify school recovery details and get admin information.
    Requires: Authorization: Bearer <api_key>
    """
    client_ip = request.client.host
    
    # Rate limiting check
    if not rate_limiter.is_allowed(api_key, settings.RATE_LIMIT_PER_MINUTE, 60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    
    logger.info(f"Verify recovery request for {req.email} from {client_ip}")
    
    try:
        if not cloud_client.check_connection():
            raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
        # Get school from cloud
        school_query = """
            SELECT id, school_name, school_email, school_contact, 
                   county, region, city, town, created_at
            FROM school_installations 
            WHERE school_email = ? 
            LIMIT 1
        """
        
        school_result = cloud_client.execute_query(school_query, (req.email,))
        
        if not school_result.get("success") or not school_result.get("rows"):
            return {
                "success": False,
                "verified": False,
                "message": "School not found. Please check the email address."
            }
        
        school_data = school_result["rows"][0]
        
        # Verify credentials
        if not verify_school_credentials(school_data, req.school_name, req.contact):
            return {
                "success": False,
                "verified": False,
                "message": "School name or contact number does not match our records."
            }
        
        # Get admin information from cloud
        admin_query = """
            SELECT id, first_name, last_name, contact, email, created_at
            FROM admin_table 
            WHERE school_id = ? 
            ORDER BY created_at DESC
        """
        
        admin_result = cloud_client.execute_query(admin_query, (school_data["id"],))
        
        if not admin_result.get("success") or not admin_result.get("rows"):
            return {
                "success": False,
                "verified": False,
                "message": "No admin accounts found for this school."
            }
        
        admins = admin_result["rows"]
        
        # Format admins for response (no password hashes)
        formatted_admins = []
        for admin in admins:
            formatted_admins.append({
                "first_name": admin.get("first_name"),
                "last_name": admin.get("last_name"),
                "email": admin.get("email"),
                "contact": admin.get("contact")
            })
        
        return {
            "success": True,
            "verified": True,
            "message": "School verification successful",
            "data": {
                "school": {
                    "id": school_data.get("id"),
                    "school_name": school_data.get("school_name"),
                    "school_email": school_data.get("school_email"),
                    "county": school_data.get("county"),
                    "region": school_data.get("region"),
                    "city": school_data.get("city")
                },
                "admin_count": len(admins),
                "admins": formatted_admins
            },
            "warning": "Recovery will deactivate any existing device and require reactivation."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verification error: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@app.post("/perform-recovery")
async def perform_school_recovery(
    req: SchoolRecoveryRequest, 
    request: Request,
    cloud_client: SQLiteCloudClient = Depends(get_cloud_client),
    api_key: str = Depends(verify_api_key)  # REQUIRED
):
    """
    Perform complete school recovery - returns encrypted blob.
    Requires: Authorization: Bearer <api_key>
    Stricter rate limit: 3 per hour per API key
    """
    client_ip = request.client.host
    
    # Stricter rate limit for recovery (3 per hour)
    if not rate_limiter.is_allowed(api_key, 3, 3600):
        raise HTTPException(status_code=429, detail="Recovery rate limit exceeded. Max 3 recoveries per hour.")
    
    logger.info(f"Perform recovery request for {req.email} from {client_ip}")
    
    try:
        # Validate confirmation
        if not req.confirm_deactivation:
            raise HTTPException(
                status_code=400, 
                detail="You must confirm device deactivation to proceed with recovery."
            )
        
        if not cloud_client.check_connection():
            raise HTTPException(status_code=503, detail="Cannot connect to cloud database")
        
        # Get full school data
        school_query = """
            SELECT * FROM school_installations WHERE school_email = ? LIMIT 1
        """
        school_result = cloud_client.execute_query(school_query, (req.email,))
        
        if not school_result.get("success") or not school_result.get("rows"):
            raise HTTPException(status_code=404, detail="School not found")
        
        school_data = school_result["rows"][0]
        
        # Verify credentials
        if not verify_school_credentials(school_data, req.school_name, req.contact):
            raise HTTPException(status_code=401, detail="Invalid school credentials")
        
        # Get all admins
        admin_query = """
            SELECT * FROM admin_table WHERE school_id = ?
        """
        admin_result = cloud_client.execute_query(admin_query, (school_data["id"],))
        
        if not admin_result.get("success") or not admin_result.get("rows"):
            raise HTTPException(status_code=404, detail="No admin accounts found for this school")
        
        admins = admin_result["rows"]
        
        # Create encrypted recovery blob
        try:
            encrypted_blob = create_recovery_blob(school_data, admins)
        except Exception as e:
            logger.error(f"Failed to create recovery blob: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create recovery blob: {str(e)}")
        
        # Return blob directly - NO STORAGE
        return {
            "success": True,
            "message": f"Recovery blob created successfully for {school_data['school_name']}",
            "data": {
                "school_name": school_data["school_name"],
                "school_email": school_data["school_email"],
                "admins_count": len(admins),
                "recovery_timestamp": datetime.now().isoformat()
            },
            "encrypted_blob": encrypted_blob,
            "blob_length": len(encrypted_blob)
        }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recovery error: {e}")
        raise HTTPException(status_code=500, detail=f"Recovery failed: {str(e)}")

# ============================================
# TEST ENDPOINT (for debugging)
# ============================================

@app.get("/ping")
async def ping():
    """Simple ping endpoint to test if server is alive"""
    return {"pong": True, "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    
    if settings.ENVIRONMENT == "production":
        logger.warning("=" * 50)
        logger.warning("RUNNING IN PRODUCTION MODE")
        logger.warning(f"API Keys configured: {len(settings.api_keys_list)}")
        logger.warning(f"Rate limits: {settings.RATE_LIMIT_PER_MINUTE}/min")
        logger.warning("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST, 
        port=settings.PORT,
        log_level="info" if not settings.DEBUG else "debug",
        reload=settings.DEBUG
    )