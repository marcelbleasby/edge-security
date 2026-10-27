"""Aggregate observed source IPs; SPAN cannot reliably reveal device MAC/hostname."""
from sqlalchemy.dialects.postgresql import insert
from app.models import NetworkDevice
from app.policy import canonical_ip

def upsert_observed_devices(db, records):
    seen = {}
    for e in records:
        ip = e.get('src_ip')
        if not ip or not e.get('timestamp'):
            continue
        try:
            ip = canonical_ip(ip)
        except ValueError:
            continue
        key = (e['sensor_id'], ip)
        ts = e['timestamp']
        if key not in seen:
            seen[key] = [ts, ts]
        else:
            seen[key][0] = min(seen[key][0], ts)
            seen[key][1] = max(seen[key][1], ts)
    for (sensor, ip), (first, last) in seen.items():
        stmt = insert(NetworkDevice).values(sensor_id=sensor, ip=ip, first_seen=first, last_seen=last)
        db.execute(stmt.on_conflict_do_update(
            constraint='uq_device_sensor_ip',
            set_={'first_seen': __import__('sqlalchemy').func.least(NetworkDevice.first_seen, first),
                  'last_seen': __import__('sqlalchemy').func.greatest(NetworkDevice.last_seen, last)}))
