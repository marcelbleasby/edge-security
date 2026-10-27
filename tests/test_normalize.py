import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'backend'))
from app.collector import normalize, parse_ts

def test_alert():
    e = normalize({'event_type':'alert','timestamp':'2026-10-26T12:00:00Z','alert':{'signature_id':42,'severity':2}}, 'k')
    assert e['signature_id']==42
    assert e['severity']==2
    assert e['event_type']=='alert'

def test_dns():
    e = normalize({'event_type':'dns','dns':{'rrname':'example.org'}}, 'k')
    assert e['domain']=='example.org'

def test_bad_timestamp():
    assert parse_ts('not a date') is None
