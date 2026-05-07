"""
MedGenius - Favourites / Bookmarks Module  (Feature #5)

Lets each logged-in user save medicines to a personal favourites list.
Stored in memory (same pattern as SCAN_HISTORY / SEARCH_HISTORY).
Replace the in-memory dict with a database table in production.

API endpoints (all require JWT auth):
  POST   /api/favourites/add        { "medicine_id": 3 }
  DELETE /api/favourites/remove     { "medicine_id": 3 }
  GET    /api/favourites            → list of saved medicines
  GET    /api/favourites/check/<id> → { "is_favourite": true/false }
"""

import datetime
from flask import Blueprint, request, jsonify
from medicine_data import MEDICINES_DB, get_medicine_by_id

favourites_bp = Blueprint('favourites', __name__)

# ── In-memory store: user_id → set of medicine_ids ──────────────────────────
# Replace with DB in production:
#   CREATE TABLE favourites (user_id TEXT, medicine_id INTEGER,
#                            saved_at TIMESTAMP, PRIMARY KEY(user_id, medicine_id))
_FAVOURITES: dict = {}   # user_id -> list of { medicine_id, saved_at }

MAX_FAVOURITES = 50      # prevent unlimited bookmarking


def _get_user_favs(user_id: str) -> list:
    return _FAVOURITES.setdefault(user_id, [])


def _med_id_in_favs(user_id: str, medicine_id: int) -> bool:
    return any(f['medicine_id'] == medicine_id for f in _get_user_favs(user_id))


# ── Routes ────────────────────────────────────────────────────────────────────

@favourites_bp.route('/api/favourites', methods=['GET'])
def get_favourites():
    """Return full medicine details for all saved favourites"""
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'error': 'Authentication required'}), 401

    uid  = request.user['user_id']
    favs = _get_user_favs(uid)

    enriched = []
    for fav in favs:
        med = get_medicine_by_id(fav['medicine_id'])
        if med:
            enriched.append({
                'medicine_id': fav['medicine_id'],
                'saved_at':    fav['saved_at'],
                'medicine': {
                    'id':                med['id'],
                    'name':              med['name'],
                    'generic_name':      med['generic_name'],
                    'category':          med['category'],
                    'rating':            med['rating'],
                    'otc':               med['otc'],
                    'generic_available': med['generic_available'],
                    'price_range':       med['price_range'],
                    'savings':           med.get('savings', 'N/A'),
                }
            })

    return jsonify({
        'success': True,
        'count':   len(enriched),
        'favourites': enriched
    })


@favourites_bp.route('/api/favourites/add', methods=['POST'])
def add_favourite():
    """Add a medicine to the user's favourites list"""
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json(silent=True)
    if not data or 'medicine_id' not in data:
        return jsonify({'error': 'medicine_id is required'}), 400

    try:
        medicine_id = int(data['medicine_id'])
    except (TypeError, ValueError):
        return jsonify({'error': 'medicine_id must be an integer'}), 400

    # Validate medicine exists
    med = get_medicine_by_id(medicine_id)
    if not med:
        return jsonify({'error': f'Medicine with id {medicine_id} not found'}), 404

    uid  = request.user['user_id']
    favs = _get_user_favs(uid)

    if _med_id_in_favs(uid, medicine_id):
        return jsonify({'success': True, 'message': 'Already in favourites',
                        'medicine_name': med['name']}), 200

    if len(favs) >= MAX_FAVOURITES:
        return jsonify({'error': f'Maximum {MAX_FAVOURITES} favourites allowed. Remove some first.'}), 400

    favs.append({
        'medicine_id': medicine_id,
        'saved_at':    datetime.datetime.utcnow().isoformat()
    })

    return jsonify({
        'success':      True,
        'message':      f"{med['name']} added to favourites",
        'medicine_name': med['name'],
        'total_saved':  len(favs)
    }), 201


@favourites_bp.route('/api/favourites/remove', methods=['DELETE'])
def remove_favourite():
    """Remove a medicine from the user's favourites"""
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json(silent=True)
    if not data or 'medicine_id' not in data:
        return jsonify({'error': 'medicine_id is required'}), 400

    try:
        medicine_id = int(data['medicine_id'])
    except (TypeError, ValueError):
        return jsonify({'error': 'medicine_id must be an integer'}), 400

    uid  = request.user['user_id']
    favs = _get_user_favs(uid)

    before = len(favs)
    _FAVOURITES[uid] = [f for f in favs if f['medicine_id'] != medicine_id]

    if len(_FAVOURITES[uid]) == before:
        return jsonify({'error': 'Medicine not in favourites'}), 404

    med = get_medicine_by_id(medicine_id)
    name = med['name'] if med else str(medicine_id)

    return jsonify({
        'success':      True,
        'message':      f"{name} removed from favourites",
        'total_saved':  len(_FAVOURITES[uid])
    })


@favourites_bp.route('/api/favourites/check/<int:medicine_id>', methods=['GET'])
def check_favourite(medicine_id):
    """Check if a specific medicine is in the user's favourites"""
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'is_favourite': False}), 200

    uid          = request.user['user_id']
    is_favourite = _med_id_in_favs(uid, medicine_id)
    return jsonify({'is_favourite': is_favourite, 'medicine_id': medicine_id})


@favourites_bp.route('/api/favourites/clear', methods=['DELETE'])
def clear_favourites():
    """Remove all favourites for the logged-in user"""
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'error': 'Authentication required'}), 401

    uid = request.user['user_id']
    count = len(_get_user_favs(uid))
    _FAVOURITES[uid] = []

    return jsonify({
        'success': True,
        'message': f'Cleared {count} favourites'
    })


def init_favourites_for_user(user_id: str):
    """Call this when a new user registers to initialise their favourites list"""
    _FAVOURITES.setdefault(user_id, [])