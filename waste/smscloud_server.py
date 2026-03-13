# start_recovery_server.py
import subprocess
import sys
import os


def start_recovery_server():
    """Start the recovery server"""
    print("🔄 Starting School Recovery Server...")
    
    # Check if port 8001 is available
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 8001))
        sock.close()
    except:
        print(f"❌ Port 8001 is already in use!")
        print("   Please close any application using port 8001")
        sys.exit(1)
    
    # Start the server
    try:
        subprocess.run([sys.executable, "cloud_backend.py"])
    except KeyboardInterrupt:
        print("\n🛑 Recovery server stopped")
    except Exception as e:
        print(f"❌ Error starting recovery server: {e}")

if __name__ == "__main__":
    start_recovery_server()