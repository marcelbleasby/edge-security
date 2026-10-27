"""Generate clearly labeled synthetic EVE events for local integration testing."""
import json
from datetime import datetime, timezone
from pathlib import Path
p = Path(__file__).resolve().parents[1] / 'logs' / 'eve.json'
p.parent.mkdir(exist_ok=True, parents=True)
now = datetime.now(timezone.utc).isoformat()
events = [
 {'timestamp': now, 'event_type': 'dns', 'src_ip':'192.0.2.10', 'dest_ip':'192.0.2.53', 'proto':'UDP', 'dns':{'rrname':'example.org'}},
 {'timestamp': now, 'event_type': 'flow', 'src_ip':'192.0.2.10', 'dest_ip':'198.51.100.20', 'proto':'TCP','dest_port':443},
 {'timestamp': now, 'event_type': 'alert', 'src_ip':'192.0.2.10', 'dest_ip':'198.51.100.20', 'proto':'TCP','alert':{'signature_id':1000001,'severity':2,'signature':'SYNTHETIC test alert - not a real detection'}}
]
with p.open('a', encoding='utf-8') as f:
    for e in events:
        f.write(json.dumps(e) + '\n')
print(f'Added {len(events)} SYNTHETIC events to {p}')
