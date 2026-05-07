"""
MedGenius - Request Validation Layer
Validates and sanitizes all incoming API request payloads.
Returns structured errors with field-level details.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Any, Dict


# ── Base Validator ────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    valid:   bool
    errors:  Dict[str, str] = field(default_factory=dict)
    data:    Dict[str, Any] = field(default_factory=dict)

    def add_error(self, field_name: str, message: str):
        self.valid  = False
        self.errors[field_name] = message

    @property
    def first_error(self) -> Optional[str]:
        return next(iter(self.errors.values()), None)

    def to_response(self) -> Tuple[dict, int]:
        if self.valid:
            return {"success": True, **self.data}, 200
        return {
            "success": False,
            "error":   self.first_error,
            "details": self.errors
        }, 422


# ── Field-level validators ────────────────────────────────────────────────────

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$')

def _v_email(value: Any) -> Tuple[bool, str, str]:
    """Returns (ok, cleaned_value, error_message)"""
    if not value:
        return False, "", "Email is required"
    v = str(value).strip().lower()
    if len(v) > 254:
        return False, "", "Email too long"
    if not EMAIL_RE.match(v):
        return False, "", "Invalid email format"
    return True, v, ""


def _v_password(value: Any) -> Tuple[bool, str, str]:
    if not value:
        return False, "", "Password is required"
    v = str(value)
    if len(v) < 6:
        return False, "", "Password must be at least 6 characters"
    if len(v) > 128:
        return False, "", "Password too long (max 128 chars)"
    return True, v, ""


def _v_name(value: Any, label: str = "Name") -> Tuple[bool, str, str]:
    if not value:
        return False, "", f"{label} is required"
    v = str(value).strip()
    if len(v) < 2:
        return False, "", f"{label} too short (min 2 chars)"
    if len(v) > 80:
        return False, "", f"{label} too long (max 80 chars)"
    if re.search(r'[<>"\';\\]', v):
        return False, "", f"{label} contains invalid characters"
    return True, v, ""


def _v_symptoms(value: Any) -> Tuple[bool, str, str]:
    if not value:
        return False, "", "Symptoms description is required"
    v = str(value).strip()
    if len(v) < 3:
        return False, "", "Please describe your symptoms in more detail (min 3 chars)"
    if len(v) > 1000:
        return False, "", "Description too long (max 1000 chars)"
    # Strip dangerous chars
    v = re.sub(r'[<>"\';\\]', '', v)
    return True, v, ""


def _v_medicine_name(value: Any) -> Tuple[bool, str, str]:
    if not value:
        return False, "", "Medicine name is required"
    v = str(value).strip()
    if len(v) < 2:
        return False, "", "Medicine name too short"
    if len(v) > 100:
        return False, "", "Medicine name too long"
    return True, v, ""


def _v_search_query(value: Any) -> Tuple[bool, str, str]:
    if not value:
        return False, "", "Search query is required"
    v = str(value).strip()
    if len(v) < 2:
        return False, "", "Search query too short (min 2 chars)"
    if len(v) > 200:
        return False, "", "Search query too long"
    v = re.sub(r'[<>"\';\\]', '', v)
    return True, v, ""


def _v_top_k(value: Any, default: int = 5) -> Tuple[bool, int, str]:
    try:
        k = int(value) if value is not None else default
        if k < 1 or k > 15:
            return False, default, "top_k must be between 1 and 15"
        return True, k, ""
    except (TypeError, ValueError):
        return True, default, ""


def _v_medicines_list(value: Any) -> Tuple[bool, list, str]:
    if not value or not isinstance(value, list):
        return False, [], "medicines must be a non-empty list"
    cleaned = [str(m).strip() for m in value if str(m).strip()]
    if len(cleaned) < 2:
        return False, [], "Provide at least 2 medicine names"
    if len(cleaned) > 10:
        return False, [], "Maximum 10 medicines at a time"
    return True, cleaned, ""


# ── Schema validators (called from Flask routes) ──────────────────────────────

def validate_register(data: dict) -> ValidationResult:
    result = ValidationResult(valid=True)
    if not data:
        result.add_error("body", "Request body is required")
        return result

    ok, name, err = _v_name(data.get("name"), "Name")
    if not ok: result.add_error("name", err)
    else:      result.data["name"] = name

    ok, email, err = _v_email(data.get("email"))
    if not ok: result.add_error("email", err)
    else:      result.data["email"] = email

    ok, pwd, err = _v_password(data.get("password"))
    if not ok: result.add_error("password", err)
    else:      result.data["password"] = pwd

    return result


def validate_login(data: dict) -> ValidationResult:
    result = ValidationResult(valid=True)
    if not data:
        result.add_error("body", "Request body is required")
        return result

    ok, email, err = _v_email(data.get("email"))
    if not ok: result.add_error("email", err)
    else:      result.data["email"] = email

    if not data.get("password"):
        result.add_error("password", "Password is required")
    else:
        result.data["password"] = str(data["password"])

    return result


def validate_symptom_request(data: dict) -> ValidationResult:
    result = ValidationResult(valid=True)
    if not data:
        result.add_error("body", "Request body is required")
        return result

    ok, symptoms, err = _v_symptoms(data.get("symptoms"))
    if not ok: result.add_error("symptoms", err)
    else:      result.data["symptoms"] = symptoms

    ok, k, err = _v_top_k(data.get("top_k", 5))
    if not ok: result.add_error("top_k", err)
    result.data["top_k"] = k

    return result


def validate_alternative_request(data: dict) -> ValidationResult:
    result = ValidationResult(valid=True)
    if not data:
        result.add_error("body", "Request body is required")
        return result

    ok, med, err = _v_medicine_name(data.get("medicine"))
    if not ok: result.add_error("medicine", err)
    else:      result.data["medicine"] = med

    return result


def validate_search_query(query: str) -> ValidationResult:
    result = ValidationResult(valid=True)
    ok, q, err = _v_search_query(query)
    if not ok: result.add_error("q", err)
    else:      result.data["q"] = q
    return result


def validate_interaction_check(data: dict) -> ValidationResult:
    result = ValidationResult(valid=True)
    if not data:
        result.add_error("body", "Request body is required")
        return result

    ok, meds, err = _v_medicines_list(data.get("medicines"))
    if not ok: result.add_error("medicines", err)
    else:      result.data["medicines"] = meds

    return result


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        ("validate_register",
         validate_register({"name": "Tarun", "email": "t@g.com", "password": "pass123"})),
        ("validate_register (bad email)",
         validate_register({"name": "X", "email": "not-an-email", "password": "abc"})),
        ("validate_symptom_request",
         validate_symptom_request({"symptoms": "fever and headache", "top_k": 3})),
        ("validate_symptom_request (empty)",
         validate_symptom_request({"symptoms": ""})),
        ("validate_interaction_check",
         validate_interaction_check({"medicines": ["Aspirin", "Warfarin"]})),
        ("validate_interaction_check (too few)",
         validate_interaction_check({"medicines": ["Aspirin"]})),
    ]
    for name, result in tests:
        status = "✅ VALID" if result.valid else f"❌ INVALID: {result.first_error}"
        print(f"{name:45s} → {status}")