"""
Automatic Server Starter for VSB Feedback System
This script automatically detects the local IP and starts the server.
"""

import os
import sys
import socket
import logging
import webbrowser
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        return "127.0.0.1"


def check_port_available(host, port):
    """Check if a port is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        sock.close()
        return True
    except socket.error:
        return False


def start_server():
    """Start the Flask server with automatic configuration."""
    logger.info("=" * 60)
    logger.info("VSB Feedback System - Starting Server")
    logger.info("=" * 60)
    
    # Get local IP
    host_ip = get_local_ip()
    logger.info(f"Detected Local IP: {host_ip}")
    
    # Determine the best port to use
    ports_to_try = [5000, 8080, 8000, 3000, 5001]
    selected_port = None
    
    for port in ports_to_try:
        if check_port_available(host_ip, port):
            selected_port = port
            logger.info(f"Port {port} is available")
            break
        else:
            logger.warning(f"Port {port} is already in use")
    
    if not selected_port:
        logger.error("No available ports found. Please close other applications.")
        sys.exit(1)
    
    logger.info(f"Selected Port: {selected_port}")
    logger.info("=" * 60)
    logger.info(f"Server will be accessible at:")
    logger.info(f"  Local:   http://localhost:{selected_port}")
    logger.info(f"  Network: http://{host_ip}:{selected_port}")
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 60)
    
    # Import and run the application
    try:
        # Add current directory to path to ensure imports work
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import the Flask app
        import importlib.util
        spec = importlib.util.spec_from_file_location("main_app", "app.py")
        main_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_app)
        asgi_app = main_app.asgi_app
        
        import uvicorn
        
        # Open browser after a short delay
        import threading
        def open_browser():
            import time
            time.sleep(2)
            webbrowser.open(f"http://localhost:{selected_port}")
        
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # Start the server
        uvicorn.run(
            asgi_app,
            host=host_ip,
            port=selected_port,
            log_config=None
        )
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    start_server()
