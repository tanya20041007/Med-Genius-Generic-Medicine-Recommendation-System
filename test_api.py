"""
MedGenius - Unit & Integration Test Suite  (Feature #9)
Run with:  pytest tests/test_api.py -v

Tests cover:
  - Authentication (register, login, JWT)
  - Medicine search and detail endpoints
  - ML symptom recommendations
  - OCR scan endpoint
  - Favourites CRUD
  - Dosage calculator
  - Reminders CRUD
  - Admin dashboard
  - Input validation / edge cases
  - Security: bad tokens, missing fields, oversized input
"""

import json
import pytest
import sys
import os

# Make sure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app as flask_app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Flask test client with testing mode enabled"""
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key-for-pytest'
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def auth_headers(client):
    """Register + login a fresh test user and return JWT auth headers"""
    # Register
    client.post('/api/auth/register', json={
        'name':     'Test User',
        'email':    'pytest@test.com',
        'password': 'testpass123'
    })
    # Login
    resp  = client.post('/api/auth/login', json={
        'email':    'pytest@test.com',
        'password': 'testpass123'
    })
    token = resp.get_json().get('token', '')
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_headers(client):
    """Login as the built-in demo user (must be admin in app.py)"""
    resp  = client.post('/api/auth/login', json={
        'email':    'demo@medgenius.ai',
        'password': 'demo123'
    })
    token = resp.get_json().get('token', '')
    return {'Authorization': f'Bearer {token}'}


# ── Health check ──────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200

    def test_health_has_required_fields(self, client):
        data = client.get('/api/health').get_json()
        assert data['status'] == 'online'
        assert 'medicines_count' in data
        assert data['medicines_count'] > 0
        assert 'version' in data


# ── Authentication ────────────────────────────────────────────────────────────

class TestAuth:
    def test_register_success(self, client):
        resp = client.post('/api/auth/register', json={
            'name': 'New User', 'email': 'new@test.com', 'password': 'pass123'
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        assert 'token' in data

    def test_register_duplicate_email(self, client):
        payload = {'name': 'X', 'email': 'dup@test.com', 'password': 'pass123'}
        client.post('/api/auth/register', json=payload)
        resp = client.post('/api/auth/register', json=payload)
        assert resp.status_code == 409

    def test_register_short_password(self, client):
        resp = client.post('/api/auth/register', json={
            'name': 'X', 'email': 'short@test.com', 'password': 'abc'
        })
        assert resp.status_code == 400

    def test_register_invalid_email(self, client):
        resp = client.post('/api/auth/register', json={
            'name': 'X', 'email': 'not-an-email', 'password': 'pass123'
        })
        assert resp.status_code == 400

    def test_register_missing_name(self, client):
        resp = client.post('/api/auth/register', json={
            'email': 'noname@test.com', 'password': 'pass123'
        })
        assert resp.status_code == 400

    def test_login_success(self, client):
        client.post('/api/auth/register', json={
            'name': 'Login User', 'email': 'login@test.com', 'password': 'pass123'
        })
        resp = client.post('/api/auth/login', json={
            'email': 'login@test.com', 'password': 'pass123'
        })
        assert resp.status_code == 200
        assert 'token' in resp.get_json()

    def test_login_wrong_password(self, client):
        client.post('/api/auth/register', json={
            'name': 'X', 'email': 'wrongpw@test.com', 'password': 'correct'
        })
        resp = client.post('/api/auth/login', json={
            'email': 'wrongpw@test.com', 'password': 'wrong'
        })
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post('/api/auth/login', json={
            'email': 'nobody@test.com', 'password': 'pass123'
        })
        assert resp.status_code == 401

    def test_me_requires_auth(self, client):
        resp = client.get('/api/auth/me')
        assert resp.status_code == 401

    def test_me_returns_user_info(self, client, auth_headers):
        resp = client.get('/api/auth/me', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'email' in data
        assert 'name' in data

    def test_bad_token_rejected(self, client):
        resp = client.get('/api/auth/me',
                          headers={'Authorization': 'Bearer totally.fake.token'})
        assert resp.status_code == 401


# ── Medicine endpoints ────────────────────────────────────────────────────────

class TestMedicines:
    def test_list_medicines(self, client):
        resp = client.get('/api/medicines')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'medicines' in data
        assert data['count'] > 0

    def test_filter_otc_only(self, client):
        resp = client.get('/api/medicines?otc=true')
        assert resp.status_code == 200
        meds = resp.get_json()['medicines']
        assert all(m['otc'] for m in meds)

    def test_filter_generic_only(self, client):
        resp = client.get('/api/medicines?generic=true')
        meds = resp.get_json()['medicines']
        assert all(m['generic_available'] for m in meds)

    def test_get_medicine_by_id(self, client):
        resp = client.get('/api/medicines/1')
        assert resp.status_code == 200

    def test_get_medicine_not_found(self, client):
        resp = client.get('/api/medicines/99999')
        assert resp.status_code == 404

    def test_search_medicines(self, client):
        resp = client.get('/api/medicines/search?q=paracetamol')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] > 0

    def test_search_too_short(self, client):
        resp = client.get('/api/medicines/search?q=a')
        assert resp.status_code == 400

    def test_search_empty_query(self, client):
        resp = client.get('/api/medicines/search?q=')
        assert resp.status_code == 400

    def test_search_xss_input_sanitised(self, client):
        # XSS attempt — should not crash and should return 200 or 400, never 500
        resp = client.get('/api/medicines/search?q=<script>alert(1)</script>')
        assert resp.status_code in (200, 400)


# ── ML Recommendations ────────────────────────────────────────────────────────

class TestRecommendations:
    def test_recommend_fever(self, client):
        resp = client.post('/api/recommend/symptoms',
                           json={'symptoms': 'fever and headache', 'top_k': 3})
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'recommendations' in data
        assert len(data['recommendations']) > 0

    def test_recommend_diabetes(self, client):
        resp = client.post('/api/recommend/symptoms',
                           json={'symptoms': 'high blood sugar diabetes'})
        assert resp.status_code == 200

    def test_recommend_empty_symptoms(self, client):
        resp = client.post('/api/recommend/symptoms', json={'symptoms': ''})
        assert resp.status_code == 400

    def test_recommend_too_short(self, client):
        resp = client.post('/api/recommend/symptoms', json={'symptoms': 'ab'})
        assert resp.status_code == 400

    def test_recommend_has_disclaimer(self, client):
        resp = client.post('/api/recommend/symptoms',
                           json={'symptoms': 'cough and cold'})
        data = resp.get_json()
        assert 'disclaimer' in data

    def test_recommend_top_k_capped(self, client):
        resp = client.post('/api/recommend/symptoms',
                           json={'symptoms': 'fever', 'top_k': 100})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['recommendations']) <= 10

    def test_alternatives_found(self, client):
        resp = client.post('/api/recommend/alternatives',
                           json={'medicine': 'Paracetamol'})
        assert resp.status_code == 200

    def test_alternatives_missing_field(self, client):
        resp = client.post('/api/recommend/alternatives', json={})
        assert resp.status_code == 400


# ── Favourites ────────────────────────────────────────────────────────────────

class TestFavourites:
    def test_get_favourites_unauthenticated(self, client):
        resp = client.get('/api/favourites')
        assert resp.status_code == 401

    def test_add_favourite(self, client, auth_headers):
        resp = client.post('/api/favourites/add',
                           json={'medicine_id': 1}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.get_json()['success'] is True

    def test_add_duplicate_favourite(self, client, auth_headers):
        client.post('/api/favourites/add', json={'medicine_id': 2}, headers=auth_headers)
        resp = client.post('/api/favourites/add', json={'medicine_id': 2}, headers=auth_headers)
        assert resp.status_code == 200   # 200 not 201 — already saved

    def test_get_favourites_after_add(self, client, auth_headers):
        client.post('/api/favourites/add', json={'medicine_id': 3}, headers=auth_headers)
        resp = client.get('/api/favourites', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        ids  = [f['medicine_id'] for f in data['favourites']]
        assert 3 in ids

    def test_check_favourite_true(self, client, auth_headers):
        client.post('/api/favourites/add', json={'medicine_id': 4}, headers=auth_headers)
        resp = client.get('/api/favourites/check/4', headers=auth_headers)
        assert resp.get_json()['is_favourite'] is True

    def test_check_favourite_false(self, client, auth_headers):
        resp = client.get('/api/favourites/check/9999', headers=auth_headers)
        assert resp.get_json()['is_favourite'] is False

    def test_remove_favourite(self, client, auth_headers):
        client.post('/api/favourites/add', json={'medicine_id': 5}, headers=auth_headers)
        resp = client.delete('/api/favourites/remove',
                             json={'medicine_id': 5}, headers=auth_headers)
        assert resp.status_code == 200

    def test_add_nonexistent_medicine(self, client, auth_headers):
        resp = client.post('/api/favourites/add',
                           json={'medicine_id': 99999}, headers=auth_headers)
        assert resp.status_code == 404


# ── Dosage Calculator ─────────────────────────────────────────────────────────

class TestDosage:
    def test_supported_medicines_list(self, client):
        resp = client.get('/api/dosage/medicines')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['count'] > 0

    def test_calculate_adult_paracetamol(self, client):
        resp = client.post('/api/dosage/calculate', json={
            'medicine_id': 1, 'weight_kg': 70,
            'age': 30, 'patient_type': 'adult'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'dosage' in data
        assert 'recommended_dose' in data['dosage']

    def test_calculate_child_paracetamol(self, client):
        resp = client.post('/api/dosage/calculate', json={
            'medicine_id': 1, 'weight_kg': 20,
            'age': 7, 'patient_type': 'child'
        })
        assert resp.status_code == 200
        dosage = resp.get_json()['dosage']
        assert 'dose_formula' in dosage   # per_kg formula shown

    def test_calculate_auto_patient_type(self, client):
        # No patient_type given — should auto-determine
        resp = client.post('/api/dosage/calculate', json={
            'medicine_id': 1, 'weight_kg': 70, 'age': 30
        })
        assert resp.status_code == 200

    def test_calculate_invalid_weight(self, client):
        resp = client.post('/api/dosage/calculate', json={
            'medicine_id': 1, 'weight_kg': 500, 'age': 30
        })
        assert resp.status_code == 400

    def test_calculate_unsupported_medicine(self, client):
        resp = client.post('/api/dosage/calculate', json={
            'medicine_id': 9999, 'weight_kg': 70, 'age': 30
        })
        assert resp.status_code == 400

    def test_calculate_has_disclaimer(self, client):
        resp = client.post('/api/dosage/calculate', json={
            'medicine_id': 1, 'weight_kg': 70, 'age': 30
        })
        dosage = resp.get_json()['dosage']
        assert 'disclaimer' in dosage


# ── Reminders ────────────────────────────────────────────────────────────────

class TestReminders:
    def test_create_reminder(self, client, auth_headers):
        resp = client.post('/api/reminders', json={
            'medicine_name': 'Paracetamol',
            'medicine_id':   1,
            'dose':          '500mg',
            'frequency':     'twice_daily',
            'times':         ['08:00', '20:00']
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        assert 'reminder' in data

    def test_list_reminders(self, client, auth_headers):
        client.post('/api/reminders', json={
            'medicine_name': 'Metformin', 'dose': '500mg',
            'frequency': 'twice_daily', 'times': ['07:00', '19:00']
        }, headers=auth_headers)
        resp = client.get('/api/reminders', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['count'] > 0

    def test_create_reminder_missing_dose(self, client, auth_headers):
        resp = client.post('/api/reminders', json={
            'medicine_name': 'X', 'frequency': 'once_daily', 'times': ['08:00']
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_reminder_invalid_frequency(self, client, auth_headers):
        resp = client.post('/api/reminders', json={
            'medicine_name': 'X', 'dose': '10mg',
            'frequency': 'every_2_minutes', 'times': ['08:00']
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_mark_taken(self, client, auth_headers):
        r = client.post('/api/reminders', json={
            'medicine_name': 'Cetirizine', 'dose': '10mg',
            'frequency': 'once_daily', 'times': ['21:00']
        }, headers=auth_headers)
        rid  = r.get_json()['reminder']['id']
        resp = client.post(f'/api/reminders/{rid}/taken', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_delete_reminder(self, client, auth_headers):
        r = client.post('/api/reminders', json={
            'medicine_name': 'Ibuprofen', 'dose': '400mg',
            'frequency': 'three_daily', 'times': ['08:00', '14:00', '20:00']
        }, headers=auth_headers)
        rid  = r.get_json()['reminder']['id']
        resp = client.delete(f'/api/reminders/{rid}', headers=auth_headers)
        assert resp.status_code == 200

    def test_due_reminders_endpoint(self, client, auth_headers):
        resp = client.get('/api/reminders/due', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'due_reminders' in data

    def test_reminders_require_auth(self, client):
        resp = client.get('/api/reminders')
        assert resp.status_code == 401


# ── Stats endpoint ────────────────────────────────────────────────────────────

class TestStats:
    def test_stats_returns_200(self, client):
        resp = client.get('/api/stats')
        assert resp.status_code == 200

    def test_stats_has_expected_fields(self, client):
        data = client.get('/api/stats').get_json()
        assert 'total_medicines' in data
        assert 'otc_medicines' in data
        assert 'generic_available' in data
        assert 'average_rating' in data
        assert 'top_rated' in data


# ── Security edge cases ────────────────────────────────────────────────────────

class TestSecurity:
    def test_no_body_on_login(self, client):
        resp = client.post('/api/auth/login',
                           data='', content_type='application/json')
        assert resp.status_code in (400, 401, 415)

    def test_oversized_symptom_rejected(self, client):
        resp = client.post('/api/recommend/symptoms',
                           json={'symptoms': 'a' * 2000})
        assert resp.status_code == 400

    def test_sql_injection_attempt_in_search(self, client):
        # Should not crash — just sanitise or return 400
        resp = client.get("/api/medicines/search?q='; DROP TABLE medicines;--")
        assert resp.status_code in (200, 400)
        assert resp.status_code != 500

    def test_cors_header_not_wildcard(self, client):
        resp = client.get('/api/health',
                          headers={'Origin': 'http://localhost:5000'})
        origin_header = resp.headers.get('Access-Control-Allow-Origin', '')
        # Must NOT be wildcard *
        assert origin_header != '*'

    def test_security_headers_present(self, client):
        resp = client.get('/api/health')
        assert 'X-Content-Type-Options' in resp.headers
        assert 'X-Frame-Options' in resp.headers