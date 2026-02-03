"""
PyWebView Launcher for DRC-ATEN
Starts Flask server and opens PyWebView window
Server stops automatically when window closes
"""

import webview
import threading
import time
import sys
import os
import requests

# Flag to track server status
server_running = False
shutdown_flag = False

def start_flask_server():
    """Start Flask-SocketIO server"""
    global server_running, shutdown_flag
    try:
        print("Starting Flask server...")
        # Import app after thread starts to ensure proper initialization
        from app import app, socketio, init_database
        
        # Initialize database connection
        print("Initializing database connection...")
        if init_database():
            print("✓ Database connected successfully")
        else:
            print("⚠ Warning: Database connection failed, continuing without DB")
        
        server_running = True
        print("Flask server ready on http://0.0.0.0:5000")
        
        # Run Flask-SocketIO server with debug=True to see errors
        socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        if not shutdown_flag:  # Only show error if not intentional shutdown
            print(f"Server error: {e}")
            import traceback
            traceback.print_exc()
    finally:
        server_running = False

def shutdown_server():
    """Shutdown Flask server gracefully"""
    global shutdown_flag
    shutdown_flag = True
    try:
        print("Sending shutdown signal to Flask server...")
        # Try to trigger shutdown via werkzeug
        requests.post('http://localhost:5000/shutdown', timeout=2)
    except:
        pass  # Server might already be down

def on_closing():
    """Called when PyWebView window closes"""
    print("\nWindow closed - Stopping server...")
    shutdown_server()
    time.sleep(1)  # Give server time to shutdown
    sys.exit(0)

if __name__ == '__main__':
    # Start Flask server in background thread (daemon=True to auto-stop)
    server_thread = threading.Thread(target=start_flask_server)
    server_thread.daemon = True  # Auto-stop when main thread exits
    server_thread.start()
    
    # Wait for server to start
    print("Waiting for server to start...")
    max_wait = 10  # seconds
    waited = 0
    while not server_running and waited < max_wait:
        time.sleep(0.5)
        waited += 0.5
    
    # Check if server started successfully
    if not server_running:
        print("ERROR: Server failed to start!")
        sys.exit(1)
    
    print("Server started successfully!")
    print("Opening PyWebView window...")
    print("\n" + "="*60)
    print("DRC-ATEN Production Server")
    print("="*60)
    print("Close the window to stop the server")
    print("="*60 + "\n")
    
    # Create and start PyWebView window
    try:
        window = webview.create_window(
            'DRC-ATEN - Production Server',
            'http://localhost:5000',
            width=1280,
            height=800,
            resizable=True,
            fullscreen=False,
            min_size=(800, 600)
        )
        
        # Start webview (blocks until window closes)
        webview.start()
        
    except Exception as e:
        print(f"PyWebView error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nShutting down...")
        on_closing()
