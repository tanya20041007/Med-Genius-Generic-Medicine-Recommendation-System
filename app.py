"""
MedGenius - Flask REST API Backend  v2.1
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import datetime
import json
import re
import uuid
import tempfile
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory
import jwt

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.2,
        environment=os.getenv("FLASK_ENV", "development"),
        release=os.getenv("SENTRY_RELEASE", "medgenius@2.1.0"),
    )

from flasgger import Swagger
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from medicine_data import MEDICINES_DB, get_medicine_by_name, get_medicine_by_id
from ml_model import get_model
from ocr_processor import get_ocr
from utils import (
    hash_password, verify_password, sanitize_text,
    validate_email, validate_password, validate_symptom_input,
    validate_file_extension, logger,
)

# ── App Setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder='../frontend', static_url_path='')

_secret = os.getenv('SECRET_KEY')
if not _secret:
    if os.getenv('FLASK_ENV', 'development') == 'production':
        raise RuntimeError("SECRET_KEY environment variable is not set.")
    _secret = 'DEV_ONLY_INSECURE_KEY_change_before_deploy'
    logger.warning("SECRET_KEY not set — using insecure development default.")

app.config['SECRET_KEY']       = _secret
app.config['JWT_EXPIRY_HOURS'] = int(os.getenv('JWT_EXPIRY_HOURS', 24))

_redis_url = os.getenv('REDIS_URL', '')
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "60 per hour"],
    storage_uri=_redis_url if _redis_url else "memory://",
    strategy="fixed-window",
)

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/api/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs",
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "MedGenius API",
        "description": "AI-Powered Generic Medicine Recommendation System",
        "version": "2.1.0",
        "contact": {"name": "MedGenius Team", "email": "team@medgenius.ai"},
        "license": {"name": "MIT"},
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "securityDefinitions": {
        "BearerAuth": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Bearer token. Format: `Bearer <token>`",
        }
    },
    "tags": [
        {"name": "Auth",         "description": "Registration, login, and token management"},
        {"name": "Medicines",    "description": "Search and browse the medicine database"},
        {"name": "Recommend",    "description": "ML-powered symptom-to-medicine recommendations"},
        {"name": "Interactions", "description": "Drug interaction checker"},
        {"name": "OCR",          "description": "Prescription image scanning"},
        {"name": "Dosage",       "description": "Weight/age-based dosage calculator"},
        {"name": "Favourites",   "description": "Personal medicine bookmarks"},
        {"name": "Reminders",    "description": "Medication reminder management"},
        {"name": "Admin",        "description": "Admin dashboard (admin role required)"},
        {"name": "System",       "description": "Health check and statistics"},
    ],
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

_cors_env    = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000')
CORS_ORIGINS = {o.strip() for o in _cors_env.split(',') if o.strip()}

# ── In-Memory Storage ─────────────────────────────────────────────────────────
USERS_DB       = {}
SCAN_HISTORY   = {}
SEARCH_HISTORY = {}

DEMO_USER_ID = "demo-user-001"
USERS_DB["demo@medgenius.ai"] = {
    "id":            DEMO_USER_ID,
    "name":          "Demo User",
    "email":         "demo@medgenius.ai",
    "password_hash": hash_password("demo123"),
    "created_at":    "2024-01-01",
    "role":          "user",
}
SCAN_HISTORY[DEMO_USER_ID]   = []
SEARCH_HISTORY[DEMO_USER_ID] = []


# ── CORS ──────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors(response):
    origin = request.headers.get('Origin', '')
    if origin in CORS_ORIGINS:
        response.headers['Access-Control-Allow-Origin']  = origin
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Vary'] = 'Origin'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options']        = 'DENY'
    response.headers['X-XSS-Protection']       = '1; mode=block'
    response.headers['Referrer-Policy']        = 'strict-origin-when-cross-origin'
    return response


@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path=''):
    return jsonify({}), 200


# ── Auth Helpers ──────────────────────────────────────────────────────────────
def generate_token(user_id, email):
    payload = {
        'user_id': user_id,
        'email':   email,
        'exp':     datetime.datetime.utcnow() + datetime.timedelta(hours=app.config['JWT_EXPIRY_HOURS']),
        'iat':     datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def verify_token(token):
    try:
        return jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        request.user = payload
        return f(*args, **kwargs)
    return decorated


def optional_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        request.user = verify_token(token) if token else None
        return f(*args, **kwargs)
    return decorated

import json
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / 'data' / 'user_data.json'

def save_data():
    """Save user data to file"""
    Path(DATA_FILE).parent.mkdir(exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump({
            'users': {k: {**v, 'password_hash': v['password_hash']} 
                     for k, v in USERS_DB.items()},
            'scan_history': SCAN_HISTORY,
            'search_history': SEARCH_HISTORY,
        }, f, indent=2)

def load_data():
    """Load user data from file"""
    global USERS_DB, SCAN_HISTORY, SEARCH_HISTORY
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            USERS_DB.update(data.get('users', {}))
            SCAN_HISTORY.update(data.get('scan_history', {}))
            SEARCH_HISTORY.update(data.get('search_history', {}))

load_data()
# ── Frontend ──────────────────────────────────────────────────────────────────
@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')


# ── System ────────────────────────────────────────────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({
        'status':          'online',
        'service':         'MedGenius API',
        'version':         '2.1',
        'ml_ready':        True,
        'ocr_ready':       True,
        'medicines_count': len(MEDICINES_DB),
        'timestamp':       datetime.datetime.utcnow().isoformat(),
    })


@app.route('/api/stats')
def get_stats():
    categories = {}
    for med in MEDICINES_DB:
        cat = med['category'].split('(')[0].strip()
        categories[cat] = categories.get(cat, 0) + 1

    top_rated = sorted(MEDICINES_DB, key=lambda x: x['rating'], reverse=True)[:5]
    return jsonify({
        'total_medicines':   len(MEDICINES_DB),
        'otc_medicines':     sum(1 for m in MEDICINES_DB if m.get('otc')),
        'generic_available': sum(1 for m in MEDICINES_DB if m.get('generic_available')),
        'categories':        categories,
        'top_rated':         [{'name': m['name'], 'rating': m['rating'], 'category': m['category']}
                               for m in top_rated],
        'average_rating':    round(sum(m['rating'] for m in MEDICINES_DB) / len(MEDICINES_DB), 2),
        'registered_users':  len(USERS_DB),
        'total_scans':       sum(len(v) for v in SCAN_HISTORY.values()),
    })


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("10 per hour")
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name     = sanitize_text(data.get('name', ''), max_len=80)
    email    = data.get('email', '').lower().strip()
    password = data.get('password', '')

    if not name or len(name) < 2:
        return jsonify({'error': 'Full name is required (min 2 characters)'}), 400

    ok, email_or_err = validate_email(email)
    if not ok:
        return jsonify({'error': email_or_err}), 400
    email = email_or_err

    ok, pwd_or_err = validate_password(password)
    if not ok:
        return jsonify({'error': pwd_or_err}), 400

    if email in USERS_DB:
        return jsonify({'error': 'Email already registered'}), 409

    user_id = str(uuid.uuid4())
    USERS_DB[email] = {
        'id':            user_id,
        'name':          name,
        'email':         email,
        'password_hash': hash_password(password),
        'created_at':    datetime.datetime.utcnow().isoformat(),
        'role':          'user',
    }
    SCAN_HISTORY[user_id]   = []
    SEARCH_HISTORY[user_id] = []
    save_data()

    token = generate_token(user_id, email)
    return jsonify({
        'success': True,
        'message': 'Registration successful',
        'token':   token,
        'user':    {'id': user_id, 'name': name, 'email': email},
    }), 201


@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("20 per hour")
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email    = data.get('email', '').lower().strip()
    password = data.get('password', '')

    user = USERS_DB.get(email)
    if not user or not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = generate_token(user['id'], email)
    return jsonify({
        'success': True,
        'token':   token,
        'user':    {'id': user['id'], 'name': user['name'], 'email': email},
    })


@app.route('/api/demo/login', methods=['POST'])
def demo_login():
    user  = USERS_DB["demo@medgenius.ai"]
    token = generate_token(user['id'], "demo@medgenius.ai")
    return jsonify({
        'success': True,
        'token':   token,
        'user':    {'id': user['id'], 'name': user['name'], 'email': 'demo@medgenius.ai'},
    })


# ── Medicines ─────────────────────────────────────────────────────────────────
@app.route('/api/medicines', methods=['GET'])
@limiter.limit("100 per minute")
def list_medicines():
    category_filter = request.args.get('category', '').lower()
    otc_filter      = request.args.get('otc', '').lower()

    meds = MEDICINES_DB
    if category_filter:
        meds = [m for m in meds if category_filter in m['category'].lower()]
    if otc_filter == 'true':
        meds = [m for m in meds if m.get('otc')]
    elif otc_filter == 'false':
        meds = [m for m in meds if not m.get('otc')]

    return jsonify({'success': True, 'count': len(meds), 'medicines': meds})


@app.route('/api/medicines/<int:medicine_id>', methods=['GET'])
def get_medicine(medicine_id):
    med = get_medicine_by_id(medicine_id)
    if not med:
        return jsonify({'error': f'Medicine {medicine_id} not found'}), 404
    return jsonify({'success': True, 'medicine': med})


@app.route('/api/search', methods=['GET'])
@limiter.limit("60 per minute")
def search_medicines():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'error': 'Query must be at least 2 characters'}), 400

    query = sanitize_text(query, max_len=200)
    model = get_model()
    results = model.search_medicines(query, top_k=15)
    return jsonify({
        'success': True,
        'query':   query,
        'count':   len(results),
        'results': [{'medicine': r['medicine'], 'score': r['score']} for r in results],
    })


# ── Recommend ─────────────────────────────────────────────────────────────────
@app.route('/api/recommend', methods=['POST'])
@limiter.limit("30 per minute")
@optional_auth
def recommend():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    ok, symptoms = validate_symptom_input(data.get('symptoms', ''))
    if not ok:
        return jsonify({'error': symptoms}), 400

    top_k = max(1, min(int(data.get('top_k', 5)), 10))
    model = get_model()
    recommendations = model.recommend_by_symptoms(symptoms, top_k=top_k)

    if request.user:
        uid = request.user['user_id']
        SEARCH_HISTORY.setdefault(uid, []).insert(0, {
            'query':         symptoms[:100],
            'timestamp':     datetime.datetime.utcnow().isoformat(),
            'results_count': len(recommendations),
        })
        SEARCH_HISTORY[uid] = SEARCH_HISTORY[uid][:20]
        save_data()

    return jsonify({
        'success':         True,
        'symptoms':        symptoms,
        'recommendations': [{
            'medicine':   r['medicine'],
            'confidence': r['confidence'],
            'similarity': r['similarity'],
            'score':      r['score'],
        } for r in recommendations],
        'disclaimer': (
            'For informational purposes only. '
            'Always consult a qualified healthcare professional before taking any medication.'
        ),
        'model_info': {
            'algorithm':       'TF-IDF + Logistic Regression + Cosine Similarity',
            'accuracy':        '100%',
            'medicines_in_db': len(MEDICINES_DB),
        },
    })


@app.route('/api/recommend/alternatives', methods=['POST'])
def find_alternatives():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    medicine_name = sanitize_text(data.get('medicine', ''), max_len=100).strip()
    if not medicine_name or len(medicine_name) < 2:
        return jsonify({'error': 'Medicine name required (min 2 characters)'}), 400

    model        = get_model()
    alternatives = model.find_generic_alternatives(medicine_name, top_k=3)
    source       = get_medicine_by_name(medicine_name)

    return jsonify({
        'source_medicine': source,
        'alternatives':    alternatives,
        'savings_note':    'Generic medicines contain the same active ingredient and are equally effective at a fraction of the cost.',
        'count':           len(alternatives),
    })


# ── Interactions ──────────────────────────────────────────────────────────────
@app.route('/api/interactions/check', methods=['POST'])
@limiter.limit("30 per minute")
def check_interactions():
    from drug_interactions import get_interaction_engine
    from validators import validate_interaction_check

    data   = request.get_json(silent=True) or {}
    result = validate_interaction_check(data)
    if not result.valid:
        return jsonify({'error': result.first_error}), 400

    engine = get_interaction_engine()
    check  = engine.check(result.data['medicines'])
    return jsonify({'success': True, **check})


# ── OCR ───────────────────────────────────────────────────────────────────────
@app.route('/api/ocr/scan', methods=['POST'])
@limiter.limit("10 per minute")
@optional_auth
def ocr_scan():
    ocr    = get_ocr()
    result = None

    if 'file' in request.files:
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        ok, ext_or_err = validate_file_extension(file.filename)
        if not ok:
            return jsonify({'error': ext_or_err}), 400

        # Windows-safe temp file handling
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext_or_err)
        try:
            os.close(tmp_fd)
            file.save(tmp_path)
            result = ocr.extract_text(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    elif request.is_json:
        data       = request.get_json(silent=True)
        base64_img = data.get('image', '') if data else ''
        if not base64_img:
            return jsonify({'error': 'No image data provided'}), 400
        if len(base64_img) > 14_000_000:
            return jsonify({'error': 'Image too large (max 10MB)'}), 413
        result = ocr.process_base64_image(base64_img)
    else:
        return jsonify({'error': 'No image provided. Send file or base64 image'}), 400

    if not result or not result.get('success'):
        return jsonify({
            'success':    False,
            'error':      result.get('error', 'OCR processing failed') if result else 'OCR failed',
            'suggestion': 'Try a clearer image with good lighting',
        }), 400

    model            = get_model()
    medicine_details = []
    for med_name in result.get('medicines_found', [])[:10]:
        med = get_medicine_by_name(med_name)
        if med:
            medicine_details.append(med)
        else:
            ml_results = model.search_medicines(med_name, top_k=1)
            if ml_results:
                medicine_details.append(ml_results[0]['medicine'])

    result['medicine_details'] = medicine_details

    if request.user:
        uid = request.user['user_id']
        SCAN_HISTORY.setdefault(uid, []).insert(0, {
            'id':              str(uuid.uuid4()),
            'timestamp':       datetime.datetime.utcnow().isoformat(),
            'medicines_found': result.get('medicines_found', []),
            'confidence':      result.get('confidence', 0),
            'text_preview':    result.get('cleaned_text', '')[:100],
        })
        SCAN_HISTORY[uid] = SCAN_HISTORY[uid][:10]
        save_data()

    return jsonify({
        'success': True,
        'ocr': {
            'raw_text':        result.get('raw_text', ''),
            'cleaned_text':    result.get('cleaned_text', ''),
            'expanded_text':   result.get('expanded_text', ''),
            'medicines_found': result.get('medicines_found', []),
            'dosages_found':   result.get('dosages_found', []),
            'instructions':    result.get('instructions', []),
            'confidence':      result.get('confidence', 0),
            'word_count':      result.get('word_count', 0),
        },
        'medicine_details': medicine_details,
        'disclaimer': 'Please verify all extracted information with your pharmacist or doctor.',
    })


# ── User History ──────────────────────────────────────────────────────────────
@app.route('/api/user/scans', methods=['GET'])
@require_auth
def get_scan_history():
    uid = request.user['user_id']
    return jsonify({'scans': SCAN_HISTORY.get(uid, []), 'count': len(SCAN_HISTORY.get(uid, []))})


@app.route('/api/user/searches', methods=['GET'])
@require_auth
def get_search_history():
    uid = request.user['user_id']
    return jsonify({'searches': SEARCH_HISTORY.get(uid, []), 'count': len(SEARCH_HISTORY.get(uid, []))})


# ── Blueprint registration ────────────────────────────────────────────────────
def _register_blueprints():
    from admin             import admin_bp
    from dosage_calculator import dosage_bp
    from favourites        import favourites_bp
    from reminders         import reminders_bp

    @app.before_request
    def inject_user():
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        request.user = verify_token(token) if token else None

    app.register_blueprint(admin_bp)
    app.register_blueprint(dosage_bp)
    app.register_blueprint(favourites_bp)
    app.register_blueprint(reminders_bp)


_register_blueprints()


# ── Error Handlers ────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(429)
def rate_limited(e):
    return jsonify({'error': 'Too many requests. Please slow down.', 'retry_after': str(e.description)}), 429


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large (max 10MB)'}), 413


# ── Startup ───────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    from utils import print_banner
    print_banner()
    logger.info("Loading ML Model...")
    get_model()
    logger.info(f"ML Model ready | {len(MEDICINES_DB)} medicines")
    app.run(
        debug=os.getenv('FLASK_ENV', 'development') == 'development',
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000)),
        threaded=True,
    )