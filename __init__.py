"""
MedGenius Backend Package
Exposes the Flask app factory and core utilities
"""
from .app import app
from .ml_model import get_model
from .ocr_processor import get_ocr

__version__ = "2.0.0"
__author__  = "Tarun Sharma, Tanya Chauhan, Tanu Chauhan, Mouna Biswas"
__all__     = ["app", "get_model", "get_ocr"]