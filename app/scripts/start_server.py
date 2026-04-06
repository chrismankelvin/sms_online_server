# app/scripts/start_server.py
#!/usr/bin/env python3
"""
Production start script for School Recovery Server
"""
import subprocess
import sys
import os
import socket
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_port_available(port: int, host: str = 'localhost') -> bool:
    """Check if a port is available"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        sock.close()
        return True
    except:
        return False

def start_server(host: str = '0.0.0.0', port: int = 8001, reload: bool = False):
    """Start the recovery server"""
    print("🔄 Starting School Recovery Server...")
    
    # Check if port is available
    if not check_port_available(port, host):
        print(f"❌ Port {port} is already in use on {host}!")
        print("   Please check if another instance is running")
        sys.exit(1)
    
    # Build command
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        f"--host={host}",
        f"--port={port}",
        "--log-level=info"
    ]
    
    if reload:
        cmd.append("--reload")
    
    print(f"📡 Server will be available at http://{host}:{port}")
    print("🔧 Press Ctrl+C to stop")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 Recovery server stopped")
    except Exception as e:
        print(f"❌ Error starting recovery server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start School Recovery Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development only)")
    
    args = parser.parse_args()
    
    # Warn if reload is enabled in production
    if args.reload and args.host != "localhost":
        print("⚠️  Warning: Auto-reload should not be used in production!")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    start_server(host=args.host, port=args.port, reload=args.reload)