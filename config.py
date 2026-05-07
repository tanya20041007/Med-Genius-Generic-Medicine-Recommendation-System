"""
MedGenius - Configuration Module
Centralizes all app settings; reads from environment / .env file
"""

import os
from pathlib import Path

# Try to load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass  # python-dotenv optional

BASE_DIR = Path(__file__).parent.parent


class Config:
    """Base configuration"""

    # ── Flask ─────────────────────────────────────────────
    SECRET_KEY        = os.getenv('SECRET_KEY', 'medgenius_dev_secret_2024')
    DEBUG             = False
    TESTING           = False

    # ── Server ────────────────────────────────────────────
    HOST              = os.getenv('HOST', '0.0.0.0')
    PORT              = int(os.getenv('PORT', 5000))

    # ── JWT ───────────────────────────────────────────────
    JWT_EXPIRY_HOURS  = int(os.getenv('JWT_EXPIRY_HOURS', 24))

    # ── File Upload ───────────────────────────────────────
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_UPLOAD_SIZE_MB', 10)) * 1024 * 1024
    UPLOAD_FOLDER      = os.getenv('UPLOAD_FOLDER', str(BASE_DIR / 'uploads'))
    ALLOWED_EXTENSIONS = set(
        os.getenv('ALLOWED_EXTENSIONS', 'jpg,jpeg,png,bmp,tiff,gif,webp').split(',')
    )

    # ── ML Model ──────────────────────────────────────────
    MODEL_PATH         = os.getenv('MODEL_PATH', str(BASE_DIR / 'models' / 'medgenius_model.pkl'))
    RETRAIN_ON_START   = os.getenv('RETRAIN_ON_START', 'False').lower() == 'true'

    # ── OCR / Tesseract ───────────────────────────────────
    TESSERACT_CMD      = os.getenv('TESSERACT_CMD', None)   # None = auto-detect

    # ── Logging ───────────────────────────────────────────
    LOG_LEVEL          = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE           = os.getenv('LOG_FILE', str(BASE_DIR / 'logs' / 'medgenius.log'))

    # ── Medicine DB ───────────────────────────────────────
    MAX_RECOMMENDATIONS = 10
    MAX_SEARCH_RESULTS  = 15
    MAX_SCAN_HISTORY    = 10
    MAX_SEARCH_HISTORY  = 20

    # ── CORS ──────────────────────────────────────────────
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5000',
                    'http://127.0.0.1:5000']

    @classmethod
    def ensure_dirs(cls):
        """Create necessary directories if they don't exist"""
        for d in [cls.UPLOAD_FOLDER,
                  Path(cls.MODEL_PATH).parent,
                  Path(cls.LOG_FILE).parent]:
            Path(d).mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG   = False
    TESTING = False
    # In production: SECRET_KEY must come from environment variable


class TestingConfig(Config):
    TESTING            = True
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    MODEL_PATH         = str(BASE_DIR / 'models' / 'test_model.pkl')


# ── Active config ─────────────────────────────────────────
_env = os.getenv('FLASK_ENV', 'development').lower()
config_map = {
    'development' : DevelopmentConfig,
    'production'  : ProductionConfig,
    'testing'     : TestingConfig,
}
ActiveConfig = config_map.get(_env, DevelopmentConfig)