"""One administrator, opaque revocable sessions persisted as SHA256 hashes."""
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import delete
from app.models import AdminSession

SESSION_TTL_HOURS = 8

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def login(db, username: str, password: str) -> tuple[str,int]:
    expected_user = os.environ.get('ADMIN_USER', 'admin')
    expected_pass = os.environ.get('ADMIN_PASSWORD', '')
    if not expected_pass or len(expected_pass) < 16:
        raise HTTPException(503, 'Administrator credentials not configured')
    good_user = secrets.compare_digest(username.encode(), expected_user.encode())
    good_pass = secrets.compare_digest(password.encode(), expected_pass.encode())
    if not (good_user and good_pass):
        raise HTTPException(401, 'Invalid credentials')
    token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    db.execute(delete(AdminSession).where(AdminSession.expires_at <= now))
    db.add(AdminSession(token_hash=hash_token(token), expires_at=now+timedelta(hours=SESSION_TTL_HOURS)))
    db.commit()
    return token, SESSION_TTL_HOURS*3600

def as_utc(value: datetime) -> datetime:
    """Normalize DB-returned timestamps (which may be timezone-naive) to UTC."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

def require_session(db, token: str | None):
    if not token:
        raise HTTPException(401, 'Login required')
    record = db.get(AdminSession, hash_token(token))
    if not record or as_utc(record.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(401, 'Session expired or invalid')
    return True

def logout(db, token: str | None):
    if token:
        db.execute(delete(AdminSession).where(AdminSession.token_hash == hash_token(token)))
        db.commit()
