from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from app.analytics import summarize_window, packet_loss, risk_label


def test_timeline_and_severity():
    begin = datetime(2026, 10, 26, 10, tzinfo=timezone.utc)
    events = [
        SimpleNamespace(timestamp=begin, event_type='alert', severity=1, dest_ip='203.0.113.10'),
        SimpleNamespace(timestamp=begin + timedelta(hours=1), event_type='dns', severity=None, dest_ip='203.0.113.10'),
        SimpleNamespace(timestamp=begin + timedelta(hours=3), event_type='flow', severity=None, dest_ip='203.0.113.11'),
    ]
    data = summarize_window(events, begin, 3)
    assert data['sample_size'] == 2
    assert data['alert_severity']['high'] == 1
    assert data['timeline'][0]['alerts'] == 1
    assert data['top_destinations'][0]['observations'] == 2


def test_loss_unknown_is_not_zero():
    assert packet_loss(None)['drop_percent'] is None
    assert packet_loss({'capture': {'kernel_packets': 1000, 'kernel_drops': 5}})['drop_percent'] == 0.5
    assert packet_loss({'capture': {'kernel_packets': 0, 'kernel_drops': 0}})['drop_percent'] is None


def test_priority():
    assert risk_label(1) == 'high'
    assert risk_label(4) == 'unknown'
