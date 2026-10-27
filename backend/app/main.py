import os
from datetime import datetime
from typing import Literal
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import SecurityEvent, NetworkDevice, DomainPolicy
from app.policy import canonical_domain, match_policy

app = FastAPI(title='Edge Security API', version='0.7.0')

def auth(x_api_key: str | None = Header(default=None)):
    import secrets
    expected = os.environ.get('API_KEY', '')
    if not expected or not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail='Invalid API key')

def get_db():
    with SessionLocal() as db:
        yield db

def serialize(e, policies):
    policy = match_policy(e.domain, policies)
    return {'id': e.id, 'sensor_id': e.sensor_id, 'timestamp': e.timestamp, 'event_type': e.event_type,
            'src_ip': e.src_ip, 'dest_ip': e.dest_ip, 'src_port': e.src_port, 'dest_port': e.dest_port,
            'proto': e.proto, 'severity': e.severity, 'signature_id': e.signature_id,
            'signature': e.signature, 'domain': e.domain,
            'classification': policy.action if policy else 'unclassified',
            'policy_id': policy.id if policy else None, 'enforcement': 'observe_only'}

def policies_in(db):
    return db.scalars(select(DomainPolicy)).all()

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/api/v1/events', dependencies=[Depends(auth)])
def events(sensor_id: str | None = None, event_type: str | None = None,
           src_ip: str | None = None, since: datetime | None = None,
           limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
           db: Session = Depends(get_db)):
    q = select(SecurityEvent)
    if sensor_id: q = q.where(SecurityEvent.sensor_id == sensor_id)
    if event_type: q = q.where(SecurityEvent.event_type == event_type)
    if src_ip: q = q.where(SecurityEvent.src_ip == src_ip)
    if since: q = q.where(SecurityEvent.timestamp >= since)
    records = db.scalars(q.order_by(desc(SecurityEvent.id)).limit(limit).offset(offset)).all()
    rules = policies_in(db)
    return {'items': [serialize(e, rules) for e in records], 'limit': limit, 'offset': offset}

@app.get('/api/v1/alerts', dependencies=[Depends(auth)])
def alerts(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    records = db.scalars(select(SecurityEvent).where(SecurityEvent.event_type == 'alert').order_by(desc(SecurityEvent.id)).limit(limit)).all()
    rules = policies_in(db)
    return {'items': [serialize(e, rules) for e in records]}

@app.get('/api/v1/traffic/summary', dependencies=[Depends(auth)])
def summary(db: Session = Depends(get_db)):
    counts = db.execute(select(SecurityEvent.event_type, func.count()).group_by(SecurityEvent.event_type)).all()
    return {'by_event_type': {kind: count for kind, count in counts},
            'device_count': db.scalar(select(func.count()).select_from(NetworkDevice)) or 0,
            'policy_count': db.scalar(select(func.count()).select_from(DomainPolicy)) or 0}

@app.get('/api/v1/devices', dependencies=[Depends(auth)])
def devices(sensor_id: str | None = None, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    q = select(NetworkDevice)
    if sensor_id: q = q.where(NetworkDevice.sensor_id == sensor_id)
    records = db.scalars(q.order_by(desc(NetworkDevice.last_seen)).limit(limit)).all()
    return {'items': [{'id': d.id, 'sensor_id': d.sensor_id, 'ip': d.ip,
                        'name': d.name, 'first_seen': d.first_seen, 'last_seen': d.last_seen}
                       for d in records]}

class PolicyIn(BaseModel):
    domain: str = Field(min_length=1, max_length=253)
    action: Literal['allow', 'watch', 'deny']
    include_subdomains: bool = True
    enabled: bool = True
    description: str | None = Field(default=None, max_length=500)

def policy_out(p):
    return {'id': p.id, 'domain': p.domain, 'action': p.action, 'enabled': p.enabled,
            'include_subdomains': p.include_subdomains, 'description': p.description,
            'enforcement': 'observe_only'}

@app.get('/api/v1/policies/domains', dependencies=[Depends(auth)])
def list_policies(db: Session = Depends(get_db)):
    return {'items': [policy_out(p) for p in db.scalars(select(DomainPolicy).order_by(DomainPolicy.domain)).all()]}

@app.post('/api/v1/policies/domains', dependencies=[Depends(auth)], status_code=201)
def add_policy(body: PolicyIn, db: Session = Depends(get_db)):
    try:
        domain = canonical_domain(body.domain)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    rule = DomainPolicy(domain=domain, action=body.action, include_subdomains=body.include_subdomains,
                        enabled=body.enabled, description=body.description)
    db.add(rule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Policy for domain already exists')
    db.refresh(rule)
    return policy_out(rule)

@app.delete('/api/v1/policies/domains/{policy_id}', dependencies=[Depends(auth)], status_code=204)
def remove_policy(policy_id: int, db: Session = Depends(get_db)):
    p = db.get(DomainPolicy, policy_id)
    if p is None:
        raise HTTPException(status_code=404, detail='Policy not found')
    db.delete(p)
    db.commit()

# MVP v0.3: bounded observational analytics, not byte-accurate wire throughput.
from datetime import timedelta, timezone
from app.analytics import packet_loss, summarize_window

@app.get('/api/v1/analytics/overview', dependencies=[Depends(auth)])
def analytics_overview(sensor_id: str | None = None,
                       hours: int = Query(24, ge=1, le=168),
                       max_events: int = Query(10000, ge=100, le=50000),
                       db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=hours - 1)
    q = select(SecurityEvent).where(SecurityEvent.timestamp >= start, SecurityEvent.timestamp <= now)
    if sensor_id:
        q = q.where(SecurityEvent.sensor_id == sensor_id)
    # Bounded load for small deployments: samples newest events only.
    rows = db.scalars(q.order_by(desc(SecurityEvent.timestamp)).limit(max_events + 1)).all()
    truncated = len(rows) > max_events
    result = summarize_window(rows[:max_events], start, hours)
    result.update({'sensor_id': sensor_id, 'window_hours': hours, 'truncated': truncated,
                   'sample_limit': max_events, 'as_of': now})
    return result

@app.get('/api/v1/sensors/health', dependencies=[Depends(auth)])
def sensor_health(db: Session = Depends(get_db)):
    from app.models import CollectorCheckpoint
    last_by_sensor = db.execute(select(SecurityEvent.sensor_id, func.max(SecurityEvent.timestamp)).group_by(SecurityEvent.sensor_id)).all()
    checkpoints = {c.sensor_id: c for c in db.scalars(select(CollectorCheckpoint)).all()}
    result = []
    for sensor_id in sorted(set(checkpoints) | {s for s, _ in last_by_sensor}):
        ts = next((t for s, t in last_by_sensor if s == sensor_id), None)
        stats_row = db.scalar(select(SecurityEvent).where(SecurityEvent.sensor_id == sensor_id, SecurityEvent.event_type == 'stats').order_by(desc(SecurityEvent.timestamp)).limit(1))
        stats_data = (stats_row.raw or {}).get('stats', {}) if stats_row else None
        cp = checkpoints.get(sensor_id)
        result.append({'sensor_id': sensor_id, 'last_event_at': ts,
                       'checkpoint_updated_at': cp.updated_at if cp else None,
                       'checkpoint_offset': cp.byte_offset if cp else None,
                       'packet_loss': packet_loss(stats_data),
                       'stats_at': stats_row.timestamp if stats_row else None,
                       'status': 'unverified'})
    return {'items': result, 'note': 'Events and capture counters only; no sensor heartbeat. Missing stats are null, not zero.'}

# Pi-hole v6 is the enforcement engine; no automatic syncing from IDS observations.
from app.pihole_client import PiHoleClient, PiHoleError

@app.get('/api/v1/dns/status', dependencies=[Depends(auth)])
def dns_status():
    try:
        return {'available': True, 'summary': PiHoleClient().summary()}
    except PiHoleError:
        return {'available': False, 'summary': None}

@app.get('/api/v1/dns/preview', dependencies=[Depends(auth)])
def dns_preview(db: Session = Depends(get_db)):
    desired = [{'id':p.id,'domain':p.domain,'action':p.action,
                'eligible':p.enabled and p.action in ('allow','deny') and not p.include_subdomains,
                'reason': 'Only enabled exact allow/deny policies are deployable' if p.include_subdomains or p.action == 'watch' or not p.enabled else None}
               for p in policies_in(db)]
    return {'items':desired, 'mode':'manual-per-policy', 'automatic_sync':False}

from app.models import DNSDeployment, DNSAuditLog, DNSPolicyGroups

@app.get('/api/v1/dns/overview', dependencies=[Depends(auth)])
def dns_overview(db: Session = Depends(get_db)):
    try:
        client = PiHoleClient()
        domains, groups, clients, summary = client.domains(), client.groups(), client.clients(), client.summary()
    except PiHoleError:
        raise HTTPException(status_code=502, detail='Pi-hole API unavailable')
    entries = {(x.get('domain'),x.get('type'),x.get('kind')) for x in domains}
    deployments = db.scalars(select(DNSDeployment).order_by(desc(DNSDeployment.id))).all()
    managed = [{'id':d.id, 'domain':d.domain, 'action':d.action, 'policy_id':d.policy_id,
                'present':(d.domain,d.action,'exact') in entries, 'status':d.status,
                'groups':next((x.get('groups',[]) for x in domains if (x.get('domain'),x.get('type'),x.get('kind'))==(d.domain,d.action,'exact')),[]),
                'desired_groups':desired_groups(db,d.policy_id) if d.policy_id else None}
               for d in deployments]
    return {'summary':summary, 'groups':groups, 'clients':clients,
            'managed':managed, 'managed_present':sum(1 for d in managed if d['present']),
            'managed_missing':sum(1 for d in managed if not d['present']),
            'other_domain_rules':max(0,len(domains)-sum(1 for d in managed if d['present'])),
            'note':'Only Edge-created exact rules are tracked; external Pi-hole changes are never overwritten.'}

@app.get('/api/v1/dns/audit', dependencies=[Depends(auth)])
def dns_audit(limit:int=Query(50,ge=1,le=200), db:Session=Depends(get_db)):
    rows = db.scalars(select(DNSAuditLog).order_by(desc(DNSAuditLog.id)).limit(limit)).all()
    return {'items':[{'id':x.id,'event':x.event,'domain':x.domain,'detail':x.detail,'created_at':x.created_at} for x in rows]}

@app.post('/api/v1/dns/rollback/{deployment_id}', dependencies=[Depends(auth)])
def rollback_dns(deployment_id:int, db:Session=Depends(get_db)):
    d = db.get(DNSDeployment,deployment_id)
    if d is None or d.status!='deployed':
        raise HTTPException(status_code=404,detail='Managed deployment not found')
    client=PiHoleClient()
    try:
        current=client.domains()
        matches=[x for x in current if x.get('domain')==d.domain and x.get('type')==d.action and x.get('kind')=='exact']
        if not matches:
            raise HTTPException(status_code=409,detail='Rule missing in Pi-hole; reconciliation required')
        if len(matches)!=1 or matches[0].get('comment')!='managed by Edge Security':
            raise HTTPException(status_code=409,detail='Remote rule ownership changed; refusing removal')
        client.delete_exact(d.domain,d.action)
    except PiHoleError:
        raise HTTPException(status_code=502,detail='Pi-hole API rejected rollback')
    d.status='rolled_back'
    db.add(DNSAuditLog(event='rollback',domain=d.domain,detail=d.action))
    db.commit()
    return {'status':'rolled_back','domain':d.domain}

@app.post('/api/v1/dns/deploy/{policy_id}', dependencies=[Depends(auth)])
def deploy_dns_policy(policy_id: int, db: Session = Depends(get_db)):
    p = db.get(DomainPolicy, policy_id)
    if p is None:
        raise HTTPException(status_code=404, detail='Policy not found')
    if not p.enabled or p.action not in ('allow','deny') or p.include_subdomains:
        raise HTTPException(status_code=422, detail='Only enabled exact allow/deny policies can be deployed')
    existing_deployment = db.scalar(select(DNSDeployment).where(DNSDeployment.domain==p.domain, DNSDeployment.action==p.action))
    try:
        client=PiHoleClient()
        existing=client.domains()
        matches=[x for x in existing if x.get('domain')==p.domain and x.get('type')==p.action and x.get('kind')=='exact']
        if matches:
            if existing_deployment and existing_deployment.status=='deployed':
                return {'status':'already_present', 'domain':p.domain}
            raise HTTPException(status_code=409, detail='Existing Pi-hole rule is not owned by this deployment')
        if existing_deployment and existing_deployment.status=='deployed':
            raise HTTPException(status_code=409,detail='Tracked deployment missing remotely; review drift before redeploy')
        client.add_exact(p.domain,p.action,desired_groups(db,p.id))
    except PiHoleError:
        raise HTTPException(status_code=502, detail='Pi-hole API unavailable or rejected change')
    if existing_deployment:
        existing_deployment.status='deployed'
        existing_deployment.policy_id=p.id
    else:
        db.add(DNSDeployment(policy_id=p.id,domain=p.domain,action=p.action,status='deployed'))
    db.add(DNSAuditLog(event='deploy',domain=p.domain,detail=p.action))
    db.commit()
    return {'status':'deployed', 'domain':p.domain, 'type':p.action, 'kind':'exact'}


# MVP 0.6: explicit administrative writes; no automatic IDS->DNS enforcement.
import ipaddress
import re

class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    comment: str = Field(default='', max_length=250)

class ClientCreate(BaseModel):
    client: str = Field(min_length=1, max_length=64)
    comment: str = Field(default='', max_length=250)
    groups: list[int] = Field(default_factory=lambda: [0], max_length=32)

class ClientGroupsUpdate(BaseModel):
    groups: list[int] = Field(min_length=1, max_length=32)


def validated_client(value):
    # MVP deliberately supports only IP/CIDR. Hostname/MAC association is deferred.
    try:
        if '/' in value:
            return str(ipaddress.ip_network(value, strict=False))
        return str(ipaddress.ip_address(value))
    except ValueError:
        raise HTTPException(status_code=422, detail='Use an IPv4/IPv6 address or CIDR subnet')


def validated_groups(groups, available):
    if len(set(groups)) != len(groups) or any(g < 0 for g in groups):
        raise HTTPException(status_code=422, detail='Group IDs must be unique nonnegative integers')
    valid = {g['id'] for g in available if isinstance(g.get('id'), int)}
    if not set(groups).issubset(valid):
        raise HTTPException(status_code=422, detail='Unknown group ID')
    return groups


def write_audit(db, event, subject, detail):
    db.add(DNSAuditLog(event=event, domain=subject, detail=detail))
    db.commit()

@app.get('/api/v1/dns/groups', dependencies=[Depends(auth)])
def dns_groups():
    try:
        return {'items': PiHoleClient().groups()}
    except PiHoleError:
        raise HTTPException(status_code=502, detail='Pi-hole unavailable')

@app.post('/api/v1/dns/groups', dependencies=[Depends(auth)], status_code=201)
def dns_group_create(body:GroupCreate, db:Session=Depends(get_db)):
    name=body.name.strip()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9 _.-]{0,59}',name):
        raise HTTPException(status_code=422, detail='Invalid group name')
    try:
        client=PiHoleClient()
        if any(g.get('name','').lower()==name.lower() for g in client.groups()):
            raise HTTPException(status_code=409, detail='Group already exists')
        result=client.add_group(name,body.comment)
    except PiHoleError:
        raise HTTPException(status_code=502, detail='Pi-hole rejected group creation')
    write_audit(db,'group_created',name,body.comment)
    return {'result':result}

@app.get('/api/v1/dns/clients', dependencies=[Depends(auth)])
def dns_clients():
    try:
        return {'items': PiHoleClient().clients()}
    except PiHoleError:
        raise HTTPException(status_code=502, detail='Pi-hole unavailable')

@app.post('/api/v1/dns/clients', dependencies=[Depends(auth)], status_code=201)
def dns_client_create(body:ClientCreate, db:Session=Depends(get_db)):
    address=validated_client(body.client)
    try:
        client=PiHoleClient()
        validated_groups(body.groups,client.groups())
        if any(c.get('client')==address for c in client.clients()):
            raise HTTPException(status_code=409, detail='Client already exists')
        result=client.add_client(address,body.comment,body.groups)
    except PiHoleError:
        raise HTTPException(status_code=502, detail='Pi-hole rejected client creation')
    write_audit(db,'client_created',address,'groups='+str(body.groups))
    return {'result':result}

@app.put('/api/v1/dns/clients/{identifier:path}/groups', dependencies=[Depends(auth)])
def dns_client_groups(identifier:str, body:ClientGroupsUpdate, db:Session=Depends(get_db)):
    address=validated_client(identifier)
    try:
        client=PiHoleClient()
        validated_groups(body.groups,client.groups())
        existing=next((c for c in client.clients() if c.get('client')==address),None)
        if existing is None:
            raise HTTPException(status_code=404,detail='Client not found')
        old=existing.get('groups',[])
        result=client.update_client_groups(address,body.groups,existing.get('comment') or '')
    except PiHoleError:
        raise HTTPException(status_code=502,detail='Pi-hole rejected group assignment')
    write_audit(db,'client_groups_updated',address,'from='+str(old)+' to='+str(body.groups))
    return {'result':result}


# v0.7: desired group scope is explicit and is NEVER applied by an IDS alert.
class PolicyGroupsUpdate(BaseModel):
    groups: list[int] = Field(min_length=1, max_length=32)


def desired_groups(db, policy_id):
    assignment = db.get(DNSPolicyGroups, policy_id) if policy_id else None
    return assignment.group_ids if assignment else [0]


@app.get('/api/v1/dns/policy-groups', dependencies=[Depends(auth)])
def dns_policy_groups(db: Session = Depends(get_db)):
    return {'items': [{'policy_id': p.id, 'groups': desired_groups(db, p.id)}
                      for p in db.scalars(select(DomainPolicy)).all()]}


@app.put('/api/v1/dns/policies/{policy_id}/groups', dependencies=[Depends(auth)])
def set_policy_groups(policy_id: int, body: PolicyGroupsUpdate, db: Session = Depends(get_db)):
    policy = db.get(DomainPolicy, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail='Policy not found')
    try:
        available = PiHoleClient().groups()
    except PiHoleError:
        raise HTTPException(status_code=502, detail='Pi-hole unavailable')
    validated_groups(body.groups, available)
    deployment = db.scalar(select(DNSDeployment).where(
        DNSDeployment.domain == policy.domain, DNSDeployment.action == policy.action,
        DNSDeployment.status == 'deployed'))
    if deployment:
        raise HTTPException(status_code=409, detail='Revert active deployment before changing policy group scope')
    row = db.get(DNSPolicyGroups, policy_id)
    previous = row.group_ids if row else [0]
    if row:
        row.group_ids = body.groups
    else:
        db.add(DNSPolicyGroups(policy_id=policy_id, group_ids=body.groups))
    db.add(DNSAuditLog(event='policy_groups_set', domain=policy.domain,
                       detail=f'from={previous}; to={body.groups}'))
    db.commit()
    return {'policy_id': policy_id, 'groups': body.groups, 'publication': 'pending'}


@app.get('/api/v1/dns/drift', dependencies=[Depends(auth)])
def dns_drift(db: Session = Depends(get_db)):
    try:
        domains = PiHoleClient().domains()
    except PiHoleError:
        raise HTTPException(status_code=502, detail='Pi-hole unavailable')
    items=[]
    for d in db.scalars(select(DNSDeployment).where(DNSDeployment.status=='deployed')).all():
        match = next((x for x in domains if x.get('domain')==d.domain and
                      x.get('type')==d.action and x.get('kind')=='exact'), None)
        actual = match.get('groups',[]) if match else None
        desired = desired_groups(db, d.policy_id) if d.policy_id else None
        status = ('missing' if match is None else 'ownership_changed' if
                  match.get('comment')!='managed by Edge Security' else
                  'policy_missing' if desired is None else
                  'groups_mismatch' if set(actual)!=set(desired) else 'in_sync')
        items.append({'deployment_id': d.id, 'domain':d.domain, 'status':status,
                      'desired_groups':desired, 'actual_groups':actual})
    return {'items':items, 'automatic_repair':False}

# MVP 0.8: one administrator, revocable sessions and conflict-checked DNS changes.
from fastapi import Request
from datetime import timezone
from app.session_auth import login as create_admin_session, logout as revoke_admin_session, require_session
from app.models import DNSChange
from app.reconciliation import fingerprint, remote_match, plan, OWNER

class AdminLoginIn(BaseModel):
    username: str
    password: str

@app.post('/api/v1/auth/login', dependencies=[Depends(auth)])
def admin_login(body: AdminLoginIn, db: Session = Depends(get_db)):
    token, ttl = create_admin_session(db, body.username, body.password)
    return {'session': token, 'expires_in': ttl}

@app.get('/api/v1/auth/session', dependencies=[Depends(auth)])
def admin_validate_session(request: Request, db: Session = Depends(get_db)):
    require_session(db, request.headers.get('X-Admin-Session'))
    return {'authenticated': True, 'role':'admin'}

@app.post('/api/v1/auth/logout', dependencies=[Depends(auth)], status_code=204)
def admin_logout(request: Request, db: Session = Depends(get_db)):
    revoke_admin_session(db, request.headers.get('X-Admin-Session'))

class ReconcileApplyIn(BaseModel):
    deployment_id: int
    expected_fingerprint: str = Field(min_length=6, max_length=64)

@app.get('/api/v1/dns/reconcile/preview', dependencies=[Depends(auth)])
def reconcile_preview(db: Session = Depends(get_db)):
    try:
        client = PiHoleClient()
        entries, groups = client.domains(), client.groups()
    except PiHoleError:
        raise HTTPException(502, 'Pi-hole unavailable')
    result=[]
    active=db.scalars(select(DNSDeployment).where(DNSDeployment.status == 'deployed')).all()
    for d in active:
        try:
            remote=remote_match(entries,d.domain,d.action)
        except ValueError:
            result.append({'deployment_id':d.id,'domain':d.domain,'status':'ambiguous','safe':False})
            continue
        desired=desired_groups(db,d.policy_id)
        diff=plan(remote,desired)
        if not set(desired).issubset({g['id'] for g in groups}):
            diff={'status':'group_missing','safe':False,'reason':'A target group does not exist'}
        result.append({'deployment_id':d.id,'domain':d.domain,'action':d.action,'desired_groups':desired,
                       'actual_groups':remote.get('groups') if remote else None,
                       'expected_fingerprint':fingerprint(remote),**diff})
    return {'items':result,'automatic_apply':False}

@app.post('/api/v1/dns/reconcile/apply', dependencies=[Depends(auth)])
def reconcile_apply(body: ReconcileApplyIn, db: Session = Depends(get_db)):
    d=db.get(DNSDeployment,body.deployment_id)
    if d is None or d.status!='deployed' or d.policy_id is None:
        raise HTTPException(409,'Managed deployment not available')
    try:
        client=PiHoleClient()
        entries=client.domains()
        remote=remote_match(entries,d.domain,d.action)
        if fingerprint(remote)!=body.expected_fingerprint:
            raise HTTPException(409,'Remote policy changed; refresh preview')
        desired=desired_groups(db,d.policy_id)
        validated_groups(desired,client.groups())
        diff=plan(remote,desired)
        if not diff['safe']:
            raise HTTPException(409,diff['reason'])
        if diff['status']=='in_sync':
            return {'status':'in_sync'}
        before={k:remote.get(k) for k in ('domain','type','kind','comment','groups','enabled')}
        after={**before,'groups':desired}
        client.update_exact_groups(d.domain,d.action,desired)
        # Read-back required; commit history only if Pi-hole confirms the target state.
        confirmed=remote_match(client.domains(),d.domain,d.action)
        if fingerprint(confirmed)!=fingerprint(after):
            raise HTTPException(502,'Post-write verification failed; inspect remote state')
    except (PiHoleError,ValueError) as exc:
        raise HTTPException(502,'Pi-hole update failed') from exc
    change=DNSChange(deployment_id=d.id,operation='reconcile_groups',before_state=before,after_state=after)
    db.add(change)
    db.commit()
    db.refresh(change)
    return {'status':'applied','change_id':change.id}

@app.get('/api/v1/dns/changes', dependencies=[Depends(auth)])
def changes(limit:int=Query(50,ge=1,le=200), db:Session=Depends(get_db)):
    rows=db.scalars(select(DNSChange).order_by(desc(DNSChange.id)).limit(limit)).all()
    return {'items':[{'id':r.id,'deployment_id':r.deployment_id,'operation':r.operation,
                      'before':r.before_state,'after':r.after_state,'created_at':r.created_at,
                      'reverted_by':r.reverted_by} for r in rows]}

@app.post('/api/v1/dns/changes/{change_id}/rollback', dependencies=[Depends(auth)])
def rollback_change(change_id:int, db:Session=Depends(get_db)):
    original=db.get(DNSChange,change_id)
    if original is None or original.reverted_by is not None or original.operation!='reconcile_groups':
        raise HTTPException(409,'Change not eligible for rollback')
    d=db.get(DNSDeployment,original.deployment_id)
    if d is None or d.status!='deployed':
        raise HTTPException(409,'Deployment no longer active')
    # Do not overwrite another newer operation on the same deployment.
    newer=db.scalar(select(DNSChange).where(DNSChange.deployment_id==d.id,DNSChange.id>change_id).limit(1))
    if newer:
        raise HTTPException(409,'A newer change exists; rollback the latest change first')
    try:
        client=PiHoleClient()
        remote=remote_match(client.domains(),d.domain,d.action)
        if fingerprint(remote)!=fingerprint(original.after_state):
            raise HTTPException(409,'Remote policy differs from saved snapshot')
        old=original.before_state
        validated_groups(old['groups'],client.groups())
        client.update_exact_groups(d.domain,d.action,old['groups'])
        confirmed=remote_match(client.domains(),d.domain,d.action)
        if fingerprint(confirmed)!=fingerprint(old):
            raise HTTPException(502,'Rollback verification failed')
    except (PiHoleError,ValueError) as exc:
        raise HTTPException(502,'Pi-hole rollback failed') from exc
    inverse=DNSChange(deployment_id=d.id,operation='rollback_groups',before_state=original.after_state,after_state=original.before_state)
    db.add(inverse)
    db.flush()
    original.reverted_by=inverse.id
    db.commit()
    return {'status':'rolled_back','change_id':inverse.id}
