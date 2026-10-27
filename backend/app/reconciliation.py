"""Pure conflict detection for DNS changes; remote mutations are explicitly requested."""
import hashlib
import json

OWNER = 'managed by Edge Security'

def fingerprint(entry):
    if entry is None:
        return 'absent'
    value = {k: entry.get(k) for k in ('domain','type','kind','comment','groups','enabled')}
    value['groups'] = sorted(value['groups'] or [])
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def remote_match(entries, domain, action):
    matches=[r for r in entries if r.get('domain')==domain and r.get('type')==action and r.get('kind')=='exact']
    if len(matches)>1:
        raise ValueError('Ambiguous remote entries')
    return matches[0] if matches else None

def plan(entry, groups):
    if entry is None:
        return {'status':'missing','safe':False,'reason':'Remote policy absent; manual review required'}
    if entry.get('comment') != OWNER:
        return {'status':'ownership_changed','safe':False,'reason':'Policy is no longer owned by Edge Security'}
    if entry.get('enabled') is not True:
        return {'status':'changed','safe':False,'reason':'Remote enabled flag differs; manual review required'}
    if set(entry.get('groups') or []) == set(groups):
        return {'status':'in_sync','safe':True,'reason':'No change required'}
    return {'status':'groups_mismatch','safe':True,'reason':'Managed groups can be updated after confirmation'}
