"""
MedGenius - Medication Reminders Module  (Feature #7)

Lets logged-in users create, manage, and query medicine reminders.
Reminders are stored in memory (replace with DB in production).

The frontend can poll GET /api/reminders/due to check for reminders
that are due now, and use the browser Notification API to show alerts.

API endpoints (all require JWT auth):
  POST   /api/reminders            — create a reminder
  GET    /api/reminders            — list all my reminders
  GET    /api/reminders/due        — list reminders due in the next 15 minutes
  PUT    /api/reminders/<id>       — update a reminder
  DELETE /api/reminders/<id>       — delete a reminder
  POST   /api/reminders/<id>/taken — mark today's dose as taken
"""

import datetime
import uuid
from flask import Blueprint, request, jsonify
from medicine_data import get_medicine_by_id

reminders_bp = Blueprint('reminders', __name__)

# ── In-memory store ───────────────────────────────────────────────────────────
# user_id → list of reminder dicts
_REMINDERS: dict = {}

# Dose-taken log: user_id → list of { reminder_id, taken_at }
_TAKEN_LOG: dict = {}

MAX_REMINDERS = 20   # per user


# ── Frequency definitions ──────────────────────────────────────────────────────
VALID_FREQUENCIES = {
    'once_daily':    {'label': 'Once daily',       'times_per_day': 1},
    'twice_daily':   {'label': 'Twice daily',      'times_per_day': 2},
    'three_daily':   {'label': 'Three times daily','times_per_day': 3},
    'every_4_hours': {'label': 'Every 4 hours',    'times_per_day': 6},
    'every_6_hours': {'label': 'Every 6 hours',    'times_per_day': 4},
    'every_8_hours': {'label': 'Every 8 hours',    'times_per_day': 3},
    'weekly':        {'label': 'Once a week',       'times_per_day': 0},
    'as_needed':     {'label': 'As needed (PRN)',   'times_per_day': 0},
}


def _get_reminders(user_id: str) -> list:
    return _REMINDERS.setdefault(user_id, [])


def _get_taken_log(user_id: str) -> list:
    return _TAKEN_LOG.setdefault(user_id, [])


def _is_due(reminder: dict, window_minutes: int = 15) -> bool:
    """Check if a reminder is due within the next `window_minutes` minutes."""
    if not reminder.get('active', True):
        return False
    if reminder.get('frequency') == 'as_needed':
        return False

    now        = datetime.datetime.utcnow()
    today_str  = now.strftime('%Y-%m-%d')

    # Check if reminder is within its date range
    start = reminder.get('start_date', today_str)
    end   = reminder.get('end_date')
    if today_str < start:
        return False
    if end and today_str > end:
        return False

    # Check each scheduled time
    for time_str in reminder.get('times', []):
        try:
            h, m    = map(int, time_str.split(':'))
            due_dt  = now.replace(hour=h, minute=m, second=0, microsecond=0)
            delta   = (due_dt - now).total_seconds()
            if 0 <= delta <= window_minutes * 60:
                return True
        except (ValueError, AttributeError):
            continue
    return False


def _taken_today(user_id: str, reminder_id: str) -> bool:
    """Returns True if the user already marked this reminder taken today."""
    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    return any(
        t['reminder_id'] == reminder_id and t['taken_at'].startswith(today)
        for t in _get_taken_log(user_id)
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@reminders_bp.route('/api/reminders', methods=['POST'])
def create_reminder():
    """
    Create a new medication reminder.

    Body: {
      "medicine_id":  1,                   (int, required)
      "medicine_name": "Paracetamol",      (string, fallback if id not found)
      "dose":         "500mg",             (string, required)
      "frequency":    "twice_daily",       (string, from VALID_FREQUENCIES)
      "times":        ["08:00", "20:00"],  (list of HH:MM strings)
      "start_date":   "2024-12-01",        (YYYY-MM-DD, optional — defaults today)
      "end_date":     "2024-12-07",        (YYYY-MM-DD, optional)
      "notes":        "Take with food"     (string, optional)
    }
    """
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    uid = request.user['user_id']

    # ── Validate medicine ──
    medicine_id   = data.get('medicine_id')
    medicine_name = str(data.get('medicine_name', '')).strip()[:100]

    if medicine_id:
        try:
            medicine_id = int(medicine_id)
            med = get_medicine_by_id(medicine_id)
            if med:
                medicine_name = med['name']
        except (TypeError, ValueError):
            medicine_id = None

    if not medicine_name:
        return jsonify({'error': 'medicine_name is required'}), 400

    # ── Validate dose ──
    dose = str(data.get('dose', '')).strip()[:50]
    if not dose:
        return jsonify({'error': 'dose is required (e.g. "500mg", "1 tablet")'}), 400

    # ── Validate frequency ──
    frequency = str(data.get('frequency', 'once_daily')).lower().strip()
    if frequency not in VALID_FREQUENCIES:
        return jsonify({
            'error':   f"Invalid frequency. Choose from: {', '.join(VALID_FREQUENCIES.keys())}"
        }), 400

    # ── Validate times ──
    raw_times = data.get('times', [])
    if not isinstance(raw_times, list):
        raw_times = [raw_times]

    times = []
    for t in raw_times[:6]:   # max 6 per day
        t = str(t).strip()
        try:
            h, m = map(int, t.split(':'))
            if 0 <= h <= 23 and 0 <= m <= 59:
                times.append(f"{h:02d}:{m:02d}")
        except (ValueError, AttributeError):
            pass

    if not times and frequency not in ('as_needed', 'weekly'):
        return jsonify({'error': 'At least one time is required (format: HH:MM)'}), 400

    # ── Validate dates ──
    today      = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    start_date = str(data.get('start_date', today)).strip()
    end_date   = data.get('end_date')
    if end_date:
        end_date = str(end_date).strip()
        if end_date < start_date:
            return jsonify({'error': 'end_date cannot be before start_date'}), 400

    # ── Limit ──
    reminders = _get_reminders(uid)
    if len(reminders) >= MAX_REMINDERS:
        return jsonify({'error': f'Maximum {MAX_REMINDERS} reminders allowed. Delete some first.'}), 400

    # ── Create ──
    reminder = {
        'id':            str(uuid.uuid4()),
        'medicine_id':   medicine_id,
        'medicine_name': medicine_name,
        'dose':          dose,
        'frequency':     frequency,
        'frequency_label': VALID_FREQUENCIES[frequency]['label'],
        'times':         times,
        'start_date':    start_date,
        'end_date':      end_date,
        'notes':         str(data.get('notes', '')).strip()[:300],
        'active':        True,
        'created_at':    datetime.datetime.utcnow().isoformat(),
    }
    reminders.append(reminder)

    return jsonify({
        'success':  True,
        'message':  f"Reminder created for {medicine_name}",
        'reminder': reminder
    }), 201


@reminders_bp.route('/api/reminders', methods=['GET'])
def list_reminders():
    """Return all reminders for the logged-in user"""
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'error': 'Authentication required'}), 401

    uid       = request.user['user_id']
    reminders = _get_reminders(uid)
    today     = datetime.datetime.utcnow().strftime('%Y-%m-%d')

    # Attach taken-today flag to each reminder
    enriched = []
    for r in reminders:
        r_copy = dict(r)
        r_copy['taken_today'] = _taken_today(uid, r['id'])
        # Auto-mark inactive if past end_date
        if r.get('end_date') and today > r['end_date']:
            r_copy['active']  = False
            r_copy['expired'] = True
        enriched.append(r_copy)

    active   = [r for r in enriched if r.get('active')]
    inactive = [r for r in enriched if not r.get('active')]

    return jsonify({
        'success':        True,
        'count':          len(enriched),
        'active_count':   len(active),
        'reminders':      active + inactive   # active first
    })


@reminders_bp.route('/api/reminders/due', methods=['GET'])
def due_reminders():
    """
    Return reminders due in the next 15 minutes.
    Frontend polls this endpoint to trigger browser notifications.
    """
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'error': 'Authentication required'}), 401

    uid      = request.user['user_id']
    due_list = []

    for r in _get_reminders(uid):
        if _is_due(r) and not _taken_today(uid, r['id']):
            due_list.append({
                'id':            r['id'],
                'medicine_name': r['medicine_name'],
                'dose':          r['dose'],
                'times':         r['times'],
                'notes':         r.get('notes', '')
            })

    return jsonify({
        'success':       True,
        'due_count':     len(due_list),
        'due_reminders': due_list
    })


@reminders_bp.route('/api/reminders/<reminder_id>', methods=['PUT'])
def update_reminder(reminder_id):
    """Update an existing reminder (toggle active, change time, etc.)"""
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'error': 'Authentication required'}), 401

    uid       = request.user['user_id']
    reminders = _get_reminders(uid)
    data      = request.get_json(silent=True) or {}

    target = next((r for r in reminders if r['id'] == reminder_id), None)
    if not target:
        return jsonify({'error': 'Reminder not found'}), 404

    # Update allowed fields
    if 'active' in data:
        target['active'] = bool(data['active'])
    if 'dose' in data:
        target['dose'] = str(data['dose']).strip()[:50]
    if 'notes' in data:
        target['notes'] = str(data['notes']).strip()[:300]
    if 'times' in data and isinstance(data['times'], list):
        times = []
        for t in data['times'][:6]:
            try:
                h, m = map(int, str(t).split(':'))
                if 0 <= h <= 23 and 0 <= m <= 59:
                    times.append(f"{h:02d}:{m:02d}")
            except (ValueError, AttributeError):
                pass
        if times:
            target['times'] = times
    if 'end_date' in data:
        target['end_date'] = data['end_date']

    target['updated_at'] = datetime.datetime.utcnow().isoformat()

    return jsonify({'success': True, 'message': 'Reminder updated', 'reminder': target})


@reminders_bp.route('/api/reminders/<reminder_id>', methods=['DELETE'])
def delete_reminder(reminder_id):
    """Delete a reminder"""
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'error': 'Authentication required'}), 401

    uid       = request.user['user_id']
    reminders = _get_reminders(uid)
    before    = len(reminders)

    _REMINDERS[uid] = [r for r in reminders if r['id'] != reminder_id]

    if len(_REMINDERS[uid]) == before:
        return jsonify({'error': 'Reminder not found'}), 404

    return jsonify({'success': True, 'message': 'Reminder deleted'})


@reminders_bp.route('/api/reminders/<reminder_id>/taken', methods=['POST'])
def mark_taken(reminder_id):
    """Mark a dose as taken for today"""
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'error': 'Authentication required'}), 401

    uid       = request.user['user_id']
    reminders = _get_reminders(uid)

    reminder = next((r for r in reminders if r['id'] == reminder_id), None)
    if not reminder:
        return jsonify({'error': 'Reminder not found'}), 404

    if _taken_today(uid, reminder_id):
        return jsonify({'success': True, 'message': 'Already marked as taken today'})

    log = _get_taken_log(uid)
    log.append({
        'reminder_id':    reminder_id,
        'medicine_name':  reminder['medicine_name'],
        'dose':           reminder['dose'],
        'taken_at':       datetime.datetime.utcnow().isoformat()
    })
    # Keep last 200 entries
    _TAKEN_LOG[uid] = log[-200:]

    return jsonify({
        'success':      True,
        'message':      f"✅ {reminder['medicine_name']} marked as taken",
        'taken_at':     datetime.datetime.utcnow().isoformat()
    })


@reminders_bp.route('/api/reminders/history', methods=['GET'])
def dose_history():
    """Return the last 30 dose-taken records for the user"""
    if not hasattr(request, 'user') or not request.user:
        return jsonify({'error': 'Authentication required'}), 401

    uid = request.user['user_id']
    log = _get_taken_log(uid)

    return jsonify({
        'success': True,
        'count':   len(log[-30:]),
        'history': list(reversed(log[-30:]))   # most recent first
    })


def init_reminders_for_user(user_id: str):
    """Call when a new user registers"""
    _REMINDERS.setdefault(user_id, [])
    _TAKEN_LOG.setdefault(user_id, [])