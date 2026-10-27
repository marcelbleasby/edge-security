"""Tail one EVE JSON file; commit records and cursor atomically.

Design assumption: one collector process per SENSOR_ID. A single current EVE
file is tracked; archived/rotated files are not scanned (see README caveat).
"""
import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from sqlalchemy.dialects.postgresql import insert

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
LOG = logging.getLogger(__name__)
SENSOR_ID = os.environ.get('SENSOR_ID', 'docker-lab-01')
EVE_PATH = Path(os.environ.get('EVE_PATH', '/var/log/suricata/eve.json'))
INTERVAL = float(os.environ.get('POLL_INTERVAL', '1'))
BATCH_SIZE = 200

def parse_ts(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None

def normalize(raw, key):
    alert = raw.get('alert') or {}
    dns = raw.get('dns') or {}
    # Suricata 7/8 EVE DNS layouts vary. Missing fields stay NULL.
    queries = dns.get('queries') or []
    q = queries[0] if queries and isinstance(queries[0], dict) else {}
    domain = dns.get('rrname') or dns.get('query') or q.get('rrname')
    def integer(v):
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None
    return {'event_key': key, 'sensor_id': SENSOR_ID,
        'timestamp': parse_ts(raw.get('timestamp')),
        'event_type': str(raw.get('event_type') or 'unknown')[:50],
        'src_ip': raw.get('src_ip'), 'dest_ip': raw.get('dest_ip'),
        'src_port': integer(raw.get('src_port')), 'dest_port': integer(raw.get('dest_port')),
        'proto': raw.get('proto'), 'signature_id': integer(alert.get('signature_id')),
        'severity': integer(alert.get('severity')), 'signature': alert.get('signature'),
        'domain': domain if isinstance(domain, str) else None, 'raw': raw}

def ingest_once():
    from app.database import SessionLocal
    from app.models import CollectorCheckpoint, SecurityEvent
    from app.inventory import upsert_observed_devices
    if not EVE_PATH.exists():
        return 0
    with EVE_PATH.open('rb') as stream:
        stat = os.fstat(stream.fileno())
        identity = f'{stat.st_dev}:{stat.st_ino}'
        with SessionLocal.begin() as db:
            cp = db.get(CollectorCheckpoint, SENSOR_ID)
            offset = cp.byte_offset if cp and cp.file_identity == identity and stat.st_size >= cp.byte_offset else 0
            stream.seek(offset)
            records = []
            new_offset = offset
            while len(records) < BATCH_SIZE:
                start = stream.tell()
                line = stream.readline()
                if not line or not line.endswith(b'\n'):
                    break
                new_offset = stream.tell()
                try:
                    payload = json.loads(line)
                    if not isinstance(payload, dict):
                        raise ValueError('event must be object')
                except (json.JSONDecodeError, ValueError):
                    LOG.warning('Skipping invalid complete JSON line at offset %d', start)
                    continue
                key = hashlib.sha256(f'{SENSOR_ID}|{identity}|{start}|'.encode() + line).hexdigest()
                records.append(normalize(payload, key))
            if records:
                stmt = insert(SecurityEvent).values(records).on_conflict_do_nothing(index_elements=['event_key'])
                db.execute(stmt)
                upsert_observed_devices(db, records)
            if cp is None:
                db.add(CollectorCheckpoint(sensor_id=SENSOR_ID, file_identity=identity, byte_offset=new_offset))
            else:
                cp.file_identity = identity
                cp.byte_offset = new_offset
            return len(records)

def main():
    LOG.info('Collector started: sensor=%s file=%s', SENSOR_ID, EVE_PATH)
    while True:
        try:
            n = ingest_once()
            if n:
                LOG.info('Processed %d events', n)
            if n >= BATCH_SIZE:
                continue
        except Exception:
            LOG.exception('Collector iteration failed; retrying')
        time.sleep(INTERVAL)

if __name__ == '__main__':
    main()
