"""Pure analytics helpers for bounded sets of Suricata EVE events."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address


def risk_label(priority):
    # Suricata signature priority: lower number = higher urgency.
    return {1: 'high', 2: 'medium', 3: 'low'}.get(priority, 'unknown')


def summarize_window(events, start, hours=24):
    points = [start + timedelta(hours=i) for i in range(hours)]
    buckets = {p.strftime('%Y-%m-%dT%H:00:00Z'): {'total': 0, 'alerts': 0, 'dns': 0, 'flows': 0} for p in points}
    destinations = Counter()
    severities = Counter()
    for event in events:
        when = event.timestamp
        if when is None:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        when = when.astimezone(timezone.utc)
        key = when.strftime('%Y-%m-%dT%H:00:00Z')
        if key not in buckets:
            continue
        b = buckets[key]
        b['total'] += 1
        if event.event_type == 'alert':
            b['alerts'] += 1
            severities[risk_label(event.severity)] += 1
        elif event.event_type == 'dns':
            b['dns'] += 1
        elif event.event_type == 'flow':
            b['flows'] += 1
        if event.dest_ip:
            destinations[event.dest_ip] += 1
    return {'timeline': [{'hour': k, **v} for k, v in buckets.items()],
            'top_destinations': [{'ip': ip, 'observations': count} for ip, count in destinations.most_common(10)],
            'alert_severity': {level: severities[level] for level in ('high', 'medium', 'low', 'unknown')},
            'sample_size': sum(v['total'] for v in buckets.values())}


def packet_loss(stats):
    """Best-effort: Suricata counters are cumulative and may reset after restart."""
    if not isinstance(stats, dict):
        return {'capture_drops': None, 'capture_packets': None, 'drop_percent': None}
    capture = stats.get('capture') or {}
    if not isinstance(capture, dict):
        return {'capture_drops': None, 'capture_packets': None, 'drop_percent': None}
    def number(*keys):
        for key in keys:
            value = capture.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return value
        return None
    packets = number('kernel_packets', 'kernel_packets_total')
    drops = number('kernel_drops', 'kernel_drops_total')
    percentage = round(100 * drops / packets, 3) if packets and drops is not None else None
    return {'capture_drops': drops, 'capture_packets': packets, 'drop_percent': percentage}
