#!/usr/bin/env python3
"""
Patient Risk Classifier Backend Demo
Startup script for development and demonstration
"""

import uvicorn
from pathlib import Path
import sys

# Add src to Python path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Start the FastAPI development server"""
    print("🏥 Starting Patient Risk Classifier Backend Demo...")
    print("📊 Real-time patient deterioration risk assessment system")
    print()
    print("🚀 Server will be available at:")
    print("   • API Server: http://localhost:8000")
    print("   • Interactive Docs: http://localhost:8000/docs")
    print("   • Health Check: http://localhost:8000/health")
    print()
    
    # Start the server
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()