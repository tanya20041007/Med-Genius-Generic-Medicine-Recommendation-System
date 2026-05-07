"""
MedGenius - Admin Dashboard Module  (Feature #8)

Protected by role='admin' check on the JWT token.
Gives a full view of the system: users, usage, top searches, OCR stats.

To make the demo user an admin, change their role in app.py:
    USERS_DB["demo@medgenius.ai"]["role"] = "admin"

API endpoints (all require admin JWT):
  GET  /api/admin/dashboard     — full system overview
  GET  /api/admin/users         — all registered users (paginated)
  GET  /api/admin/users/<id>    — single user detail + activity
  PUT  /api/admin/users/<id>    — update user role or status
  GET  /api/admin/search-stats  — top search queries
  GET  /api/admin/ocr-stats     — OCR scan statistics
  GET  /api/admin/medicines     — medicine popularity by search + view count
  POST /api/admin/clear-logs    — wipe usage logs (admin only)
"""

import datetime
import collections
from flask import Blueprint, request, jsonify
from medicine_data import MEDICINES_DB

admin_bp = Blueprint('admin', __name__)

# ── In-memory analytics store (populated by app.py routes) ───────────────────
# These dicts are filled by the app when users do things.
# In production, these would be DB queries.
_SEARCH_LOG:  list = []   # { query, user_id, timestamp, results_count }
_OCR_LOG:     list = []   # { user_id, timestamp, confidence, medicines_found }
_VIEW_LOG:    list = []   # { medicine_id, medicine_name, user_id, timestamp }
_SYMPTOM_LOG: list = []   # { symptoms, top_result, user_id, timestamp }

MAX_LOG_SIZE = 5_000


def log_search(query: str, user_id: str, results_count: int):
    """Call this from the search endpoint in app.py"""
    _SEARCH_LOG.append({
        'query':         query,
        'user_id':       user_id or 'anonymous',
        'results_count': results_count,
        'timestamp':     datetime.datetime.utcnow().isoformat()
    })
    if len(_SEARCH_LOG) > MAX_LOG_SIZE:
        _SEARCH_LOG.pop(0)


def log_ocr(user_id: str, confidence: int, medicines_found: int):
    """Call this from the OCR endpoint in app.py"""
    _OCR_LOG.append({
        'user_id':        user_id or 'anonymous',
        'confidence':     confidence,
        'medicines_found':medicines_found,
        'timestamp':      datetime.datetime.utcnow().isoformat()
    })
    if len(_OCR_LOG) > MAX_LOG_SIZE:
        _OCR_LOG.pop(0)


def log_symptom(symptoms: str, top_result: str, user_id: str):
    """Call this from the recommend endpoint in app.py"""
    _SYMPTOM_LOG.append({
        'symptoms':   symptoms[:100],
        'top_result': top_result,
        'user_id':    user_id or 'anonymous',
        'timestamp':  datetime.datetime.utcnow().isoformat()
    })
    if len(_SYMPTOM_LOG) > MAX_LOG_SIZE:
        _SYMPTOM_LOG.pop(0)


def log_medicine_view(medicine_id: int, medicine_name: str, user_id: str):
    """Call this from the medicine detail endpoint in app.py"""
    _VIEW_LOG.append({
        'medicine_id':   medicine_id,
        'medicine_name': medicine_name,
        'user_id':       user_id or 'anonymous',
        'timestamp':     datetime.datetime.utcnow().isoformat()
    })
    if len(_VIEW_LOG) > MAX_LOG_SIZE:
        _VIEW_LOG.pop(0)


# ── Admin auth decorator ──────────────────────────────────────────────────────

def require_admin(f):
    """
    Decorator — rejects the request unless the JWT user has role='admin'.
    Apply AFTER the require_auth decorator from app.py.
    """
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'user') or not request.user:
            return jsonify({'error': 'Authentication required'}), 401

        # Look up current role from USERS_DB (import lazily to avoid circular import)
        try:
            from app import USERS_DB
            email = request.user.get('email', '')
            user  = USERS_DB.get(email, {})
            role  = user.get('role', 'user')
        except ImportError:
            role = 'user'

        if role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


# ── Helper: date range filter ─────────────────────────────────────────────────

def _filter_last_days(log: list, days: int = 7) -> list:
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
    return [e for e in log if e.get('timestamp', '') >= cutoff]


def _daily_counts(log: list, days: int = 7) -> dict:
    """Return dict of date → count for the last N days"""
    counts: dict = {}
    for e in _filter_last_days(log, days):
        day = e['timestamp'][:10]
        counts[day] = counts.get(day, 0) + 1
    return dict(sorted(counts.items()))


# ── Routes ────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/dashboard', methods=['GET'])
@require_admin
def dashboard():
    """Master overview for the admin panel"""
    try:
        from app import USERS_DB, SCAN_HISTORY
    except ImportError:
        USERS_DB, SCAN_HISTORY = {}, {}

    # User stats
    total_users    = len(USERS_DB)
    admin_users    = sum(1 for u in USERS_DB.values() if u.get('role') == 'admin')
    new_users_7d   = sum(
        1 for u in USERS_DB.values()
        if u.get('created_at', '') >= (
            datetime.datetime.utcnow() - datetime.timedelta(days=7)
        ).isoformat()
    )

    # Activity stats
    total_searches  = len(_SEARCH_LOG)
    total_ocr       = len(_OCR_LOG)
    total_symptoms  = len(_SYMPTOM_LOG)
    searches_today  = len(_filter_last_days(_SEARCH_LOG, 1))
    ocr_today       = len(_filter_last_days(_OCR_LOG, 1))

    # OCR confidence average
    avg_confidence = 0
    if _OCR_LOG:
        avg_confidence = round(
            sum(e.get('confidence', 0) for e in _OCR_LOG) / len(_OCR_LOG), 1
        )

    # Top search queries (last 7 days)
    search_7d     = _filter_last_days(_SEARCH_LOG, 7)
    query_counter = collections.Counter(e['query'].lower() for e in search_7d)
    top_searches  = [{'query': q, 'count': c} for q, c in query_counter.most_common(10)]

    # Top symptom queries
    symptom_7d      = _filter_last_days(_SYMPTOM_LOG, 7)
    symptom_counter = collections.Counter(e['symptoms'][:60] for e in symptom_7d)
    top_symptoms    = [{'symptoms': s, 'count': c} for s, c in symptom_counter.most_common(5)]

    # Daily activity (last 7 days)
    daily_searches = _daily_counts(_SEARCH_LOG, 7)
    daily_ocr      = _daily_counts(_OCR_LOG, 7)

    # Medicine DB summary
    otc_count     = sum(1 for m in MEDICINES_DB if m.get('otc'))
    generic_count = sum(1 for m in MEDICINES_DB if m.get('generic_available'))

    return jsonify({
        'success':    True,
        'generated':  datetime.datetime.utcnow().isoformat(),
        'users': {
            'total':     total_users,
            'admins':    admin_users,
            'new_7_days': new_users_7d,
        },
        'activity': {
            'total_searches':  total_searches,
            'searches_today':  searches_today,
            'total_ocr_scans': total_ocr,
            'ocr_today':       ocr_today,
            'total_symptom_queries': total_symptoms,
            'avg_ocr_confidence':    avg_confidence,
        },
        'top_searches': top_searches,
        'top_symptoms': top_symptoms,
        'daily_activity': {
            'searches': daily_searches,
            'ocr_scans': daily_ocr,
        },
        'medicine_db': {
            'total':     len(MEDICINES_DB),
            'otc':       otc_count,
            'rx_only':   len(MEDICINES_DB) - otc_count,
            'generic_available': generic_count,
        }
    })


@admin_bp.route('/api/admin/users', methods=['GET'])
@require_admin
def list_users():
    """Return all registered users (paginated)"""
    try:
        from app import USERS_DB, SCAN_HISTORY, SEARCH_HISTORY
    except ImportError:
        return jsonify({'error': 'Could not load user data'}), 500

    page     = max(1, int(request.args.get('page', 1)))
    per_page = min(50, max(1, int(request.args.get('per_page', 20))))

    users = []
    for email, u in USERS_DB.items():
        uid = u.get('id', '')
        users.append({
            'id':           uid,
            'name':         u.get('name', ''),
            'email':        email,
            'role':         u.get('role', 'user'),
            'created_at':   u.get('created_at', ''),
            'scan_count':   len(SCAN_HISTORY.get(uid, [])),
            'search_count': len(SEARCH_HISTORY.get(uid, [])),
        })

    # Sort newest first
    users.sort(key=lambda x: x['created_at'], reverse=True)

    total  = len(users)
    start  = (page - 1) * per_page
    end    = start + per_page

    return jsonify({
        'success':  True,
        'total':    total,
        'page':     page,
        'per_page': per_page,
        'pages':    (total + per_page - 1) // per_page,
        'users':    users[start:end]
    })


@admin_bp.route('/api/admin/users/<user_id>', methods=['GET'])
@require_admin
def user_detail(user_id):
    """Return detailed info for a single user"""
    try:
        from app import USERS_DB, SCAN_HISTORY, SEARCH_HISTORY
    except ImportError:
        return jsonify({'error': 'Could not load user data'}), 500

    user = next((u for u in USERS_DB.values() if u.get('id') == user_id), None)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    uid = user['id']
    return jsonify({
        'success': True,
        'user': {
            'id':          uid,
            'name':        user.get('name'),
            'email':       user.get('email'),
            'role':        user.get('role', 'user'),
            'created_at':  user.get('created_at'),
            'recent_scans':    SCAN_HISTORY.get(uid, [])[:5],
            'recent_searches': SEARCH_HISTORY.get(uid, [])[:10],
        }
    })


@admin_bp.route('/api/admin/users/<user_id>', methods=['PUT'])
@require_admin
def update_user(user_id):
    """Update a user's role (promote to admin / demote to user)"""
    try:
        from app import USERS_DB
    except ImportError:
        return jsonify({'error': 'Could not load user data'}), 500

    user = next((u for u in USERS_DB.values() if u.get('id') == user_id), None)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Prevent self-demotion
    requesting_email = request.user.get('email')
    if user.get('email') == requesting_email:
        return jsonify({'error': 'You cannot change your own role'}), 400

    data = request.get_json(silent=True) or {}

    if 'role' in data:
        new_role = str(data['role']).lower()
        if new_role not in ('admin', 'user'):
            return jsonify({'error': "role must be 'admin' or 'user'"}), 400
        user['role'] = new_role

    return jsonify({
        'success': True,
        'message': f"User {user.get('name')} updated",
        'user':    {'id': user_id, 'role': user.get('role')}
    })


@admin_bp.route('/api/admin/search-stats', methods=['GET'])
@require_admin
def search_stats():
    """Detailed search query analytics"""
    days          = min(30, max(1, int(request.args.get('days', 7))))
    recent        = _filter_last_days(_SEARCH_LOG, days)
    query_counter = collections.Counter(e['query'].lower() for e in recent)

    return jsonify({
        'success':        True,
        'period_days':    days,
        'total_searches': len(recent),
        'unique_queries': len(query_counter),
        'top_queries':    [{'query': q, 'count': c} for q, c in query_counter.most_common(20)],
        'daily':          _daily_counts(_SEARCH_LOG, days),
        'zero_results':   sum(1 for e in recent if e.get('results_count', 1) == 0)
    })


@admin_bp.route('/api/admin/ocr-stats', methods=['GET'])
@require_admin
def ocr_stats():
    """OCR scan performance analytics"""
    days   = min(30, max(1, int(request.args.get('days', 7))))
    recent = _filter_last_days(_OCR_LOG, days)

    if not recent:
        return jsonify({'success': True, 'period_days': days, 'total_scans': 0})

    confidences     = [e.get('confidence', 0) for e in recent]
    medicines_found = [e.get('medicines_found', 0) for e in recent]

    return jsonify({
        'success':          True,
        'period_days':      days,
        'total_scans':      len(recent),
        'avg_confidence':   round(sum(confidences) / len(confidences), 1),
        'high_confidence':  sum(1 for c in confidences if c >= 80),
        'low_confidence':   sum(1 for c in confidences if c < 50),
        'avg_medicines_per_scan': round(sum(medicines_found) / len(medicines_found), 1),
        'daily':            _daily_counts(_OCR_LOG, days),
    })


@admin_bp.route('/api/admin/medicines', methods=['GET'])
@require_admin
def medicine_popularity():
    """Most viewed medicines"""
    view_counter = collections.Counter(
        e['medicine_name'] for e in _VIEW_LOG
    )
    search_counter = collections.Counter(
        e['query'].lower() for e in _SEARCH_LOG
        if len(e.get('query', '')) > 2
    )

    top_viewed = [
        {'medicine': name, 'views': count}
        for name, count in view_counter.most_common(15)
    ]

    return jsonify({
        'success':     True,
        'top_viewed':  top_viewed,
        'total_views': len(_VIEW_LOG),
    })


@admin_bp.route('/api/admin/clear-logs', methods=['POST'])
@require_admin
def clear_logs():
    """Wipe all analytics logs (irreversible)"""
    data    = request.get_json(silent=True) or {}
    confirm = data.get('confirm', '')
    if confirm != 'CLEAR_ALL_LOGS':
        return jsonify({
            'error': 'Send { "confirm": "CLEAR_ALL_LOGS" } to proceed'
        }), 400

    counts = {
        'searches':  len(_SEARCH_LOG),
        'ocr_scans': len(_OCR_LOG),
        'symptoms':  len(_SYMPTOM_LOG),
        'views':     len(_VIEW_LOG),
    }
    _SEARCH_LOG.clear()
    _OCR_LOG.clear()
    _SYMPTOM_LOG.clear()
    _VIEW_LOG.clear()

    return jsonify({
        'success': True,
        'message': 'All logs cleared',
        'cleared': counts
    })