
import sqlitecloud
from datetime import datetime
from typing import Optional, Dict, Any, List
import os

class SQLiteCloudClient:
    def __init__(self):
        # SQLiteCloud connection string from your example
        self.connection_string = os.getenv(
            "SQLITECLOUD_CONNECTION_STRING",
            "sqlitecloud://crp6lwxvnz.g2.sqlite.cloud:8860/sms_cloud?apikey=CWwoReVnb5JGoUcHzuZgVuaLpIVt2Vyag7iHbW1ixMU"
        )
        self.conn = None
        
    def connect(self):
        """Establish connection to SQLiteCloud"""
        try:
            self.conn = sqlitecloud.connect(self.connection_string)
            return True
        except Exception as e:
            print(f"Failed to connect to SQLiteCloud: {str(e)}")
            return False
    
    def close(self):
        """Close the connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def execute_query(self, query: str, params: tuple = None) -> Dict[str, Any]:
        """Execute a query on SQLiteCloud"""
        if not self.conn and not self.connect():
            raise Exception("Failed to connect to SQLiteCloud")
        
        try:
            cursor = self.conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Try to fetch results if it's a SELECT query
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # Convert to list of dictionaries
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
            # Rollback in case of error
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            raise Exception(f"SQLiteCloud query error: {str(e)}")
    
    def insert_school(self, data: Dict) -> Optional[str]:
        """Insert school into cloud database and return school_id"""
        # First, check if school already exists with this email
        check_query = "SELECT id FROM school_installations WHERE school_email = ?"
        existing = self.execute_query(check_query, (data["school_email"],))
        
        if existing.get("rows"):
            # School already exists
            return existing["rows"][0]["id"]
        
        # Generate a manufacture code (simple example)
        import hashlib
        import time
        manufacture_code = hashlib.md5(
            f"{data['school_name']}{time.time()}".encode()
        ).hexdigest()[:12].upper()
        
        # Insert new school
        query = """
        INSERT INTO school_installations 
        (manufacture_code, school_name, school_email, school_contact, 
         county, region, city, town, gps_address, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            manufacture_code,
            data["school_name"],
            data["school_email"],
            data["school_contact"],
            data["county"],
            data["region"],
            data["city"],
            data["town"],
            data["gps_address"],
            datetime.now().isoformat()
        )
        
        result = self.execute_query(query, params)
        if result.get("lastrowid"):
            return result["lastrowid"]
        return None
    
    def insert_admin(self, school_id: int, data: Dict) -> Optional[str]:
        """Insert admin into cloud database"""
        # First, check if admin already exists with this email
        check_query = "SELECT id FROM admin_table WHERE contact = ? OR email = ?"
        existing = self.execute_query(check_query, (data["contact"], data.get("email", "")))
        
        if existing.get("rows"):
            # Admin already exists
            return existing["rows"][0]["id"]
        
        # Insert new admin
        query = """
        INSERT INTO admin_table 
        (school_id, first_name, middle_name, last_name, contact, 
         password_hash, role, created_at, email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            school_id,
            data["first_name"],
            data.get("middle_name", ""),
            data["last_name"],
            data["contact"],
            data["password_hash"],
            data.get("role", "SUPER_ADMIN"),
            datetime.now().isoformat(),
            data.get("email", "")
        )
        
        result = self.execute_query(query, params)
        if result.get("lastrowid"):
            return result["lastrowid"]
        return None
    
    def update_activation(self, school_id: int, activation_code: str) -> bool:
        """Update activation code in cloud database"""
        query = """
        UPDATE school_installations 
        SET activation_code = ?
        WHERE id = ?
        """
        
        params = (activation_code, school_id)
        result = self.execute_query(query, params)
        return result.get("rowcount", 0) > 0
    
    # NEW DEVICE SYNC METHODS
    def get_school_by_name_or_email(self, school_name: str = None, school_email: str = None) -> Optional[Dict]:
        """Get school by name or email"""
        try:
            if school_name:
                query = "SELECT * FROM school_installations WHERE school_name = ? LIMIT 1"
                result = self.execute_query(query, (school_name,))
            elif school_email:
                query = "SELECT * FROM school_installations WHERE school_email = ? LIMIT 1"
                result = self.execute_query(query, (school_email,))
            else:
                return None
                
            if result.get("rows"):
                return result["rows"][0]
            return None
        except:
            return None
    
    def get_device_by_id(self, device_id: str) -> Optional[Dict]:
        """Get device by device_id"""
        try:
            query = "SELECT * FROM devices WHERE device_id = ? LIMIT 1"
            result = self.execute_query(query, (device_id,))
            
            if result.get("rows"):
                return result["rows"][0]
            return None
        except:
            return None
    
    def insert_device(self, device_data: Dict) -> Optional[int]:
        """Insert a device into cloud database"""
        try:
            # Prepare columns and values
            columns = []
            values = []
            placeholders = []
            
            for key, value in device_data.items():
                columns.append(key)
                values.append(value)
                placeholders.append("?")
            
            query = f"""
            INSERT INTO devices ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            """
            
            result = self.execute_query(query, tuple(values))
            return result.get("lastrowid")
        except Exception as e:
            print(f"Error inserting device: {e}")
            return None
    
    def update_device(self, device_id: str, device_data: Dict) -> bool:
        """Update device in cloud database"""
        try:
            set_clause = ", ".join([f"{key} = ?" for key in device_data.keys()])
            values = list(device_data.values())
            values.append(device_id)
            
            query = f"""
            UPDATE devices 
            SET {set_clause}
            WHERE device_id = ?
            """
            
            result = self.execute_query(query, tuple(values))
            return result.get("rowcount", 0) > 0
        except Exception as e:
            print(f"Error updating device: {e}")
            return False
    
    def upsert_device(self, device_data: Dict) -> Dict:
        """Insert or update device in cloud"""
        try:
            device_id = device_data.get("device_id")
            if not device_id:
                return {"success": False, "message": "device_id required"}
            
            # Check if device exists
            existing = self.get_device_by_id(device_id)
            
            if existing:
                # Update existing
                success = self.update_device(device_id, device_data)
                if success:
                    return {
                        "success": True,
                        "action": "updated",
                        "message": f"Device {device_id} updated in cloud"
                    }
                else:
                    return {
                        "success": False,
                        "action": "update_failed",
                        "message": f"Failed to update device {device_id}"
                    }
            else:
                # Insert new
                device_id = self.insert_device(device_data)
                if device_id:
                    return {
                        "success": True,
                        "action": "inserted",
                        "message": f"Device {device_data.get('device_id')} inserted to cloud",
                        "cloud_device_id": device_id
                    }
                else:
                    return {
                        "success": False,
                        "action": "insert_failed",
                        "message": f"Failed to insert device {device_data.get('device_id')}"
                    }
        except Exception as e:
            return {
                "success": False,
                "action": "error",
                "message": str(e)
            }
    
    def get_devices_by_school(self, school_id: int, limit: int = 100) -> List[Dict]:
        """Get devices for a specific school"""
        try:
            query = """
            SELECT d.*, s.school_name, s.school_email
            FROM devices d
            LEFT JOIN school_installations s ON d.school_installation_id = s.id
            WHERE d.school_installation_id = ?
            ORDER BY d.created_at DESC
            LIMIT ?
            """
            
            result = self.execute_query(query, (school_id, limit))
            return result.get("rows", [])
        except:
            return []
    
    def check_connection(self) -> bool:
        """Check if we can connect to SQLiteCloud"""
        try:
            if not self.conn and not self.connect():
                return False
            
            # Try a simple query
            result = self.execute_query("SELECT 1 as test")
            return result.get("success", False)
        except:
            return False
    
    def create_devices_table(self):
        """Create devices table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL UNIQUE,
            
            -- Link to school_installation instead of users
            school_installation_id INTEGER,
            admin_id INTEGER,
            
            device_name TEXT,
            device_type TEXT,
            os_name TEXT,
            os_version TEXT,
            activation_key TEXT UNIQUE,
            activation_status TEXT DEFAULT 'pending',
            
            -- Activation info
            activation_token_hash TEXT,
            license_type TEXT DEFAULT 'STANDARD',
            activated_at DATETIME,
            license_valid_until DATE,
            last_license_check DATETIME,
            
            last_activated_at DATETIME,
            registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            -- Additional fields for sync
            local_user_id INTEGER,
            local_user_email TEXT,
            local_user_unique_id TEXT,
            cloud_sync_status TEXT DEFAULT 'pending',
            last_sync_at DATETIME,
            sync_attempts INTEGER DEFAULT 0,
            
            -- Foreign keys to link with existing cloud tables
            FOREIGN KEY (school_installation_id) REFERENCES school_installations(id),
            FOREIGN KEY (admin_id) REFERENCES admin_table(id)
        )
        """
        
        try:
            self.execute_query(create_table_sql)
            print("✅ Devices table created or already exists")
            
            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_devices_school ON devices(school_installation_id)",
                "CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id)",
                "CREATE INDEX IF NOT EXISTS idx_devices_sync_status ON devices(cloud_sync_status)",
                "CREATE INDEX IF NOT EXISTS idx_devices_activation ON devices(activation_status, activation_key)"
            ]
            
            for index_sql in indexes:
                try:
                    self.execute_query(index_sql)
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ Error creating devices table: {e}")