"""Security utilities: password hashing + signed auth tokens.

Uses stdlib only (hashlib + hmac) so no bcrypt/pyjwt build issues in the slim
Docker image. PBKDF2-HMAC-SHA256 for passwords, HMAC-signed tokens for sessions.
"""
import base64
import hashlib
import hmac
import os
import secrets
import time

_PBKDF2_ITERATIONS = 200_000

# Server secret for token signing. Override in production via SECRET_KEY env.
SECRET_KEY = os.environ.get("SECRET_KEY", "tasks-tracker-dev-secret-change-me")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _algo, iterations, salt_hex, hash_hex = encoded.split("$")
        iterations = int(iterations)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(dk, expected)


def create_token(user_id: str, ttl_seconds: int = 30 * 24 * 3600) -> str:
    """Return an HMAC-signed token of the form payload.signature."""
    exp = int(time.time()) + ttl_seconds
    payload = f"{user_id}:{exp}"
    payload_b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8").rstrip("=")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_token(token: str) -> str | None:
    """Return user_id if the token is valid and not expired, else None."""
    try:
        payload_b64, sig = token.split(".")
    except ValueError:
        return None
    expected = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        payload = base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)).decode("utf-8")
        user_id, exp = payload.rsplit(":", 1)
        if int(exp) < time.time():
            return None
        return user_id
    except Exception:
        return None
