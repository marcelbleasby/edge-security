import os
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import AdminSession
from app.session_auth import login, require_session, logout, hash_token
from app.reconciliation import fingerprint, plan, remote_match, OWNER
import pytest

@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv('ADMIN_USER','admin')
    monkeypatch.setenv('ADMIN_PASSWORD','very-strong-test-password')
    engine=create_engine('sqlite:///:memory:')
    AdminSession.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()

def test_session_lifecycle(db):
    token, ttl = login(db,'admin','very-strong-test-password')
    assert ttl == 8*3600
    assert db.get(AdminSession,hash_token(token)) is not None
    assert require_session(db,token)
    with pytest.raises(HTTPException) as e: require_session(db,'invalid')
    assert e.value.status_code == 401
    logout(db,token)
    with pytest.raises(HTTPException) as e: require_session(db,token)
    assert e.value.status_code == 401

def test_expiry_after_db_roundtrip(db):
    token,_=login(db,'admin','very-strong-test-password')
    record=db.get(AdminSession,hash_token(token))
    record.expires_at=datetime.now(timezone.utc)-timedelta(seconds=3)
    db.commit()
    db.expire_all()
    with pytest.raises(HTTPException) as e:require_session(db,token)
    assert e.value.status_code == 401

def test_wrong_credentials(db):
    with pytest.raises(HTTPException) as e:login(db,'admin','wrong')
    assert e.value.status_code==401

def test_reconciliation_conflict_cases():
    entry={'domain':'test.example','type':'deny','kind':'exact','comment':OWNER,'groups':[2,1],'enabled':True}
    assert fingerprint(entry)==fingerprint({**entry,'groups':[1,2]})
    assert fingerprint(entry)!=fingerprint({**entry,'groups':[1,3]})
    assert not plan(None,[1])['safe']
    assert not plan({**entry,'comment':'other owner'},[1])['safe']
    with pytest.raises(ValueError):remote_match([entry,entry],entry['domain'],entry['type'])
