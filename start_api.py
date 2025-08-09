#!/usr/bin/env python3
"""
PV-Hawk API Server Startup Script

This script starts the PV-Hawk REST API server with proper configuration.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="Start PV-Hawk API Server")
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=1, 
        help="Number of worker processes (default: 1)"
    )
    parser.add_argument(
        "--log-level", 
        choices=["debug", "info", "warning", "error", "critical"],
        default="info", 
        help="Log level (default: info)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true", 
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--ssl-keyfile",
        help="SSL key file path"
    )
    parser.add_argument(
        "--ssl-certfile",
        help="SSL certificate file path"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting PV-Hawk API Server on {args.host}:{args.port}")
    
    # Check if API dependencies are installed
    try:
        import fastapi
        import uvicorn
        import pydantic
    except ImportError as e:
        logger.error(f"Missing API dependencies: {e}")
        logger.error("Please install API dependencies: pip install -r api/requirements.txt")
        sys.exit(1)
    
    # Set environment variables
    os.environ.setdefault("API_SECRET_KEY", "pv-hawk-secret-key-change-in-production")
    
    # Prepare uvicorn configuration
    config = {
        "app": "api.server:app",
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "access_log": True
    }
    
    # Add SSL configuration if provided
    if args.ssl_keyfile and args.ssl_certfile:
        config["ssl_keyfile"] = args.ssl_keyfile
        config["ssl_certfile"] = args.ssl_certfile
        logger.info("SSL enabled")
    
    # Development vs production configuration
    if args.reload:
        config["reload"] = True
        logger.info("Development mode: auto-reload enabled")
    else:
        config["workers"] = args.workers
        logger.info(f"Production mode: {args.workers} workers")
    
    # Start the server
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()