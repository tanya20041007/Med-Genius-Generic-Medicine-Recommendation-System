"""
MedGenius - Utility Functions
Shared helpers used across the backend

SECURITY FIX #1: Replaced SHA-256 with bcrypt for password hashing.
SHA-256 is a fast hash — attackers can try billions of guesses per second.
bcrypt is deliberately slow (cost factor 12) and includes a salt automatically,
making brute-force and rainbow-table attacks infeasible.
"""

import re
import os
import logging
import datetime
from pathlib import Path
from functools import wraps
from typing import Optional, List, Tuple

import bcrypt  # pip install bcrypt


# ── Logger setup ─────────────────────────────────────────────────────────────
def setup_logger(name: str = "medgenius", level: str = "INFO") -> logging.Logger:
    """Create and configure a logger with file + console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s %(name)s — %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler (optional)
    try:
        log_dir = Path(__file__).parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_dir / 'medgenius.log', encoding='utf-8')
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass

    return logger


logger = setup_logger()


# ── Input Validators ─────────────────────────────────────────────────────────

EMAIL_RE  = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
SAFE_TEXT = re.compile(r'[<>"\';\\]')  # characters to strip

def validate_email(email: str) -> Tuple[bool, str]:
    email = email.strip().lower()
    if not email:
        return False, "Email is required"
    if not EMAIL_RE.match(email):
        return False, "Invalid email format"
    if len(email) > 254:
        return False, "Email too long"
    return True, email


def validate_password(pwd: str) -> Tuple[bool, str]:
    if not pwd:
        return False, "Password is required"
    if len(pwd) < 6:
        return False, "Password must be at least 6 characters"
    if len(pwd) > 128:
        return False, "Password too long"
    return True, pwd


def sanitize_text(text: str, max_len: int = 2000) -> str:
    """Strip dangerous characters and truncate"""
    text = SAFE_TEXT.sub('', str(text))
    return text[:max_len].strip()


def validate_symptom_input(text: str) -> Tuple[bool, str]:
    text = sanitize_text(text, max_len=1000)
    if len(text) < 3:
        return False, "Symptom description too short (min 3 chars)"
    if len(text) > 1000:
        return False, "Symptom description too long (max 1000 chars)"
    return True, text


def validate_file_extension(filename: str,
                             allowed: set = None) -> Tuple[bool, str]:
    allowed = allowed or {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp'}
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        return False, f"File type '{ext}' not allowed. Use: {', '.join(sorted(allowed))}"
    return True, ext


# ── Hashing (SECURITY FIX #1) ────────────────────────────────────────────────
# OLD (insecure): hashlib.sha256(password.encode()).hexdigest()
#   - No salt → same password always produces same hash → rainbow table attacks work
#   - Too fast → billions of guesses per second on a GPU
#
# NEW (secure): bcrypt with cost factor 12
#   - Automatically generates a unique random salt per password
#   - Deliberately slow — cost factor 12 = ~250ms per hash, making brute-force impractical
#   - Industry standard: used by Django, Spring Security, Node bcrypt

def hash_password(password: str) -> str:
    """
    Hash a plaintext password with bcrypt (cost factor 12).
    Returns a string that includes the salt, so only the hash needs to be stored.
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')  # store as string in DB


def verify_password(plain: str, hashed: str) -> bool:
    """
    Safely compare a plaintext password against a stored bcrypt hash.
    Uses constant-time comparison to prevent timing attacks.
    """
    try:
        return bcrypt.checkpw(
            plain.encode('utf-8'),
            hashed.encode('utf-8')
        )
    except Exception:
        return False


# ── Response Builders ────────────────────────────────────────────────────────

def success_response(data: dict, message: str = "Success",
                     code: int = 200) -> Tuple[dict, int]:
    return {
        "success": True,
        "message": message,
        **data,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }, code


def error_response(message: str, code: int = 400,
                   details: Optional[str] = None) -> Tuple[dict, int]:
    body = {
        "success": False,
        "error": message,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
    if details:
        body["details"] = details
    return body, code


# ── Pagination ───────────────────────────────────────────────────────────────

def paginate(items: list, page: int = 1, per_page: int = 10) -> dict:
    page     = max(1, int(page))
    per_page = max(1, min(int(per_page), 100))
    total    = len(items)
    start    = (page - 1) * per_page
    end      = start + per_page
    return {
        "items":    items[start:end],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    (total + per_page - 1) // per_page,
        "has_next": end < total,
        "has_prev": page > 1
    }


# ── Text Utilities ───────────────────────────────────────────────────────────

def truncate(text: str, max_len: int = 100, suffix: str = "…") -> str:
    return (text[:max_len] + suffix) if len(text) > max_len else text


def normalize_medicine_name(name: str) -> str:
    """Normalize a medicine name for comparison"""
    return re.sub(r'\s+', ' ', name.strip().lower())


def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from a text string"""
    return [float(n) for n in re.findall(r'\d+(?:\.\d+)?', text)]


def format_price(amount_inr: float) -> str:
    """Format Indian Rupee price"""
    return f"₹{amount_inr:,.0f}"


# ── Rate Limiting (simple in-memory) ─────────────────────────────────────────

_rate_store: dict = {}  # ip -> (count, reset_time)

def is_rate_limited(identifier: str,
                    max_requests: int = 60,
                    window_seconds: int = 60) -> bool:
    now = datetime.datetime.utcnow()
    if identifier in _rate_store:
        count, reset = _rate_store[identifier]
        if now < reset:
            if count >= max_requests:
                return True
            _rate_store[identifier] = (count + 1, reset)
        else:
            _rate_store[identifier] = (1, now + datetime.timedelta(seconds=window_seconds))
    else:
        _rate_store[identifier] = (1, now + datetime.timedelta(seconds=window_seconds))
    return False


# ── Decorators ───────────────────────────────────────────────────────────────

def rate_limit(max_per_minute: int = 30):
    """Flask route decorator for simple rate limiting"""
    from flask import request, jsonify
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr or 'unknown'
            if is_rate_limited(ip, max_requests=max_per_minute):
                return jsonify({'error': 'Too many requests. Please slow down.'}), 429
            return f(*args, **kwargs)
        return wrapped
    return decorator


def log_request(f):
    """Decorator that logs incoming API requests"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        from flask import request
        logger.info(f"{request.method} {request.path} — {request.remote_addr}")
        return f(*args, **kwargs)
    return wrapped


# ── File Utilities ───────────────────────────────────────────────────────────

def safe_filename(filename: str) -> str:
    """Return a filesystem-safe filename"""
    name = re.sub(r'[^\w\-_.]', '_', Path(filename).stem)
    ext  = Path(filename).suffix.lower()
    ts   = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return f"{ts}_{name}{ext}"


def file_size_mb(filepath: str) -> float:
    return os.path.getsize(filepath) / (1024 * 1024)


# ── Startup banner ───────────────────────────────────────────────────────────

def print_banner():
    banner = r"""
  ╔══════════════════════════════════════════════════════╗
  ║   __  __          _  _____           _               ║
  ║  |  \/  | ___  __| |/ ____|___ _ __ (_)_   _ ___    ║
  ║  | |\/| |/ _ \/ _` | |  _ / _ \ '_ \| | | | / __|   ║
  ║  | |  | |  __/ (_| | |_| |  __/ | | | | |_| \__ \   ║
  ║  |_|  |_|\___|\__,_|\_____|\___|_| |_|_|\__,_|___/   ║
  ║                                                       ║
  ║  AI-Powered Generic Medicine Recommendation System   ║
  ║  Version 2.0  •  Graphic Era Hill University         ║
  ╚══════════════════════════════════════════════════════╝
    """
    print(banner)