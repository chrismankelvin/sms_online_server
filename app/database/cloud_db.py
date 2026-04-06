# # app/database/cloud_db.py
# import sqlitecloud
# from datetime import datetime
# from typing import Optional, Dict, Any, List
# import os
# import logging
# from functools import wraps

# logger = logging.getLogger(__name__)

# def handle_connection(func):
#     """Decorator to handle database connections"""
#     @wraps(func)
#     def wrapper(self, *args, **kwargs):
#         try:
#             if not self.conn and not self.connect():
#                 raise Exception("Failed to connect to SQLiteCloud")
#             return func(self, *args, **kwargs)
#         except Exception as e:
#             logger.error(f"Database error in {func.__name__}: {str(e)}")
#             raise
#     return wrapper

# class SQLiteCloudClient:
#     def __init__(self, connection_string: str = None):
#         self.connection_string = connection_string or os.getenv(
#             "SQLITECLOUD_CONNECTION_STRING"
#         )
#         if not self.connection_string:
#             raise ValueError("SQLITECLOUD_CONNECTION_STRING environment variable is required")
        
#         self.conn = None
#         self.max_retries = 3
#         self.retry_delay = 1  # seconds
        
#     def connect(self) -> bool:
#         """Establish connection to SQLiteCloud"""
#         for attempt in range(self.max_retries):
#             try:
#                 self.conn = sqlitecloud.connect(self.connection_string)
#                 logger.info("Successfully connected to SQLiteCloud")
#                 return True
#             except Exception as e:
#                 logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
#                 if attempt < self.max_retries - 1:
#                     import time
#                     time.sleep(self.retry_delay)
#                 else:
#                     logger.error(f"Failed to connect after {self.max_retries} attempts")
#                     return False
#         return False
    
#     def close(self):
#         """Close the connection"""
#         if self.conn:
#             try:
#                 self.conn.close()
#                 logger.debug("Database connection closed")
#             except Exception as e:
#                 logger.error(f"Error closing connection: {e}")
#             finally:
#                 self.conn = None
    
#     @handle_connection
#     def execute_query(self, query: str, params: tuple = None) -> Dict[str, Any]:
#         """Execute a query on SQLiteCloud"""
#         cursor = None
#         try:
#             cursor = self.conn.cursor()
            
#             if params:
#                 cursor.execute(query, params)
#             else:
#                 cursor.execute(query)
            
#             # Try to fetch results if it's a SELECT query
#             if query.strip().upper().startswith('SELECT'):
#                 results = cursor.fetchall()
#                 columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
#                 # Convert to list of dictionaries
#                 rows = []
#                 for row in results:
#                     rows.append(dict(zip(columns, row)))
                
#                 return {
#                     "success": True,
#                     "rows": rows,
#                     "rowcount": len(rows)
#                 }
#             else:
#                 # For INSERT, UPDATE, DELETE
#                 self.conn.commit()
#                 return {
#                     "success": True,
#                     "rowcount": cursor.rowcount,
#                     "lastrowid": cursor.lastrowid
#                 }
                
#         except Exception as e:
#             # Rollback in case of error
#             if self.conn:
#                 try:
#                     self.conn.rollback()
#                 except:
#                     pass
#             logger.error(f"Query error: {str(e)}")
#             raise Exception(f"SQLiteCloud query error: {str(e)}")
#         finally:
#             if cursor:
#                 cursor.close()
    
#     def check_connection(self) -> bool:
#         """Check if we can connect to SQLiteCloud"""
#         try:
#             if not self.conn and not self.connect():
#                 return False
            
#             # Try a simple query
#             result = self.execute_query("SELECT 1 as test")
#             return result.get("success", False)
#         except Exception as e:
#             logger.error(f"Connection check failed: {e}")
#             return False
    
#     def __enter__(self):
#         """Context manager entry"""
#         self.connect()
#         return self
    
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         """Context manager exit"""
#         self.close()






import sqlitecloud
from datetime import datetime
from typing import Optional, Dict, Any, List
import os
import logging

logger = logging.getLogger(__name__)

class SQLiteCloudClient:
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or os.getenv(
            "SQLITECLOUD_CONNECTION_STRING"
        )
        if not self.connection_string:
            raise ValueError("SQLITECLOUD_CONNECTION_STRING environment variable is required")
        
        self.conn = None
        self.max_retries = 3
        self.retry_delay = 1
        
    def connect(self) -> bool:
        """Establish connection to SQLiteCloud"""
        for attempt in range(self.max_retries):
            try:
                self.conn = sqlitecloud.connect(self.connection_string)
                logger.info("Successfully connected to SQLiteCloud")
                return True
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to connect after {self.max_retries} attempts")
                    return False
        return False
    
    def close(self):
        """Close the connection"""
        if self.conn:
            try:
                self.conn.close()
                logger.debug("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self.conn = None
    
    def execute_query(self, query: str, params: tuple = None) -> Dict[str, Any]:
        """Execute a query on SQLiteCloud"""
        # Ensure connection exists
        if not self.conn and not self.connect():
            raise Exception("Failed to connect to SQLiteCloud")
        
        cursor = None
        try:
            cursor = self.conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Check if it's a SELECT query
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                rows = []
                for row in results:
                    rows.append(dict(zip(columns, row)))
                
                return {
                    "success": True,
                    "rows": rows,
                    "rowcount": len(rows)
                }
            else:
                # For INSERT, UPDATE, DELETE
                self.conn.commit()
                return {
                    "success": True,
                    "rowcount": cursor.rowcount,
                    "lastrowid": cursor.lastrowid
                }
                
        except Exception as e:
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            logger.error(f"Query error: {str(e)}")
            raise Exception(f"SQLiteCloud query error: {str(e)}")
        finally:
            if cursor:
                cursor.close()
    
    def check_connection(self) -> bool:
        """Check if we can connect to SQLiteCloud"""
        try:
            if not self.conn and not self.connect():
                return False
            
            result = self.execute_query("SELECT 1 as test")
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()