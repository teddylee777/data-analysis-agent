#!/usr/bin/env python3
"""Simple HTTP server to serve plot images for agent-chat-ui."""

import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import threading
import time

# Configuration
PLOTS_DIR = "/tmp/dataanalysis_plots"
PORT = 8001
HOST = "localhost"

class PlotServerHandler(SimpleHTTPRequestHandler):
    """Custom handler to serve plot images."""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        os.chdir(PLOTS_DIR)
        super().__init__(*args, **kwargs)
    
    def end_headers(self):
        """Add CORS headers to allow access from agent-chat-ui."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle preflight requests."""
        self.send_response(200)
        self.end_headers()

def ensure_plots_directory():
    """Create plots directory if it doesn't exist."""
    Path(PLOTS_DIR).mkdir(parents=True, exist_ok=True)

def cleanup_old_plots():
    """Remove plots older than 1 hour."""
    while True:
        try:
            current_time = time.time()
            for file in Path(PLOTS_DIR).glob("plot_*.png"):
                if current_time - file.stat().st_mtime > 3600:  # 1 hour
                    file.unlink()
                    print(f"Removed old plot: {file.name}")
        except Exception as e:
            print(f"Error during cleanup: {e}")
        time.sleep(300)  # Run every 5 minutes

def main():
    """Start the plot server."""
    ensure_plots_directory()
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_old_plots, daemon=True)
    cleanup_thread.start()
    
    # Start HTTP server
    with HTTPServer((HOST, PORT), PlotServerHandler) as httpd:
        print(f"Plot server running at http://{HOST}:{PORT}")
        print(f"Serving files from: {PLOTS_DIR}")
        print("Press Ctrl+C to stop")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down plot server...")
            sys.exit(0)

if __name__ == "__main__":
    main()