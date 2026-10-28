import hashlib
import secrets
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from app.config import COOKIE_NAME, SESSION_DURATION_HOURS
from app.database import get_connection

def hash_password(password: str, salt: str = None) -> str:
    """PBKDF2-HMAC-SHA256 password hashing with salt."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        200_000
    )
    return f"{salt}:{key.hex()}"

def verify_password(stored_hash: str, password_attempt: str) -> bool:
    try:
        salt, key_hex = stored_hash.split(':')
        test_key = hashlib.pbkdf2_hmac(
            'sha256',
            password_attempt.encode('utf-8'),
            salt.encode('utf-8'),
            200_000
        )
        return secrets.compare_digest(test_key.hex(), key_hex)
    except Exception:
        return False

def is_admin_configured() -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM auth_config WHERE key = 'admin_password_hash'")
    row = cursor.fetchone()
    conn.close()
    return bool(row and row["value"])

def set_admin_password(password: str):
    hashed = hash_password(password)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO auth_config (key, value, updated_at)
    VALUES ('admin_password_hash', ?, CURRENT_TIMESTAMP)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (hashed,))
    conn.commit()
    conn.close()

def check_admin_password(password: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM auth_config WHERE key = 'admin_password_hash'")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    return verify_password(row["value"], password)

def create_session() -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_sessions (session_token, expires_at) VALUES (?, ?)", (token, expires))
    conn.commit()
    conn.close()
    return token

def validate_session(token: str) -> bool:
    if not token:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT expires_at FROM user_sessions WHERE session_token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    expires_at = datetime.fromisoformat(row["expires_at"])
    return datetime.utcnow() < expires_at

def destroy_session(token: str):
    if not token:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_sessions WHERE session_token = ?", (token,))
    conn.commit()
    conn.close()

def get_current_user_or_none(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    return validate_session(token)

def require_auth(request: Request):
    """Dependency that ensures the user is securely logged into PHAMOUXE."""
    if not is_admin_configured():
        raise HTTPException(status_code=307, detail="Setup required", headers={"Location": "/setup"})
    if not get_current_user_or_none(request):
        raise HTTPException(status_code=307, detail="Authentication required", headers={"Location": "/login"})
    return True
