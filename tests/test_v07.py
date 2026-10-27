import os
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
from types import SimpleNamespace
from unittest.mock import Mock
from fastapi import HTTPException
import pytest
from app.main import desired_groups, set_policy_groups, PolicyGroupsUpdate, dns_drift
from app.models import DNSPolicyGroups, DomainPolicy


def test_default_policy_group_is_zero():
    db=Mock()
    db.get.return_value=None
    assert desired_groups(db, 5)==[0]


def test_existing_group_scope():
    db=Mock()
    db.get.return_value=DNSPolicyGroups(policy_id=5,group_ids=[2, 3])
    assert desired_groups(db, 5)==[2, 3]


def test_scope_cannot_change_live_deployment(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, 'PiHoleClient', lambda: SimpleNamespace(groups=lambda: [{'id':0},{'id':2}]))
    db=Mock()
    db.get.return_value=DomainPolicy(id=1,domain='example.org',action='deny',enabled=True,include_subdomains=False)
    db.scalar.return_value=SimpleNamespace(status='deployed')
    with pytest.raises(HTTPException) as exc:
        set_policy_groups(1, PolicyGroupsUpdate(groups=[2]),db)
    assert exc.value.status_code==409
    db.commit.assert_not_called()


def test_scope_rejects_unknown_group(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, 'PiHoleClient', lambda: SimpleNamespace(groups=lambda: [{'id':0}]))
    db=Mock()
    db.get.return_value=DomainPolicy(id=1,domain='example.org',action='deny',enabled=True,include_subdomains=False)
    with pytest.raises(HTTPException) as exc:
        set_policy_groups(1, PolicyGroupsUpdate(groups=[99]), db)
    assert exc.value.status_code==422
