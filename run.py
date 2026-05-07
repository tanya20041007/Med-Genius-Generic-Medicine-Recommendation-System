"""
MedGenius - Project Entry Point
Run this file to start the complete application
"""

import sys
import os

# Load .env FIRST before anything else
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))


def train_model():
    """Pre-train the ML model before starting the server"""
    print("\n" + "="*60)
    print("  MedGenius ML Training Phase")
    print("="*60)
    from backend.ml_model import get_model
    model = get_model()
    print("  Model ready!")


def start_server():
    """Start the Flask development server"""
    from backend.app import app
    print("\n" + "="*60)
    print("  MedGenius: AI Medicine Recommendation System")
    print("="*60)
    print("  Backend API : http://localhost:5000/api")
    print("  Frontend UI : http://localhost:5000")
    print("  Health Check: http://localhost:5000/api/health")
    print("\n  Demo Login  : demo@medgenius.ai / demo123")
    print("="*60)
    print("\n  Press Ctrl+C to stop the server\n")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    train_model()
    start_server()