"""Pi-hole v6 API adapter, explicit writes only. Never overwrite unmanaged entries."""
import os
from urllib.parse import quote
import httpx

class PiHoleError(RuntimeError):
    pass

class PiHoleClient:
    def __init__(self, base=None, password=None, transport=None):
        self.base = (base or os.getenv('PIHOLE_URL','http://pihole:80')).rstrip('/')
        self.password = password if password is not None else os.getenv('PIHOLE_PASSWORD','')
        self.transport = transport

    def request(self, method, path, payload=None):
        if not self.password:
            raise PiHoleError('PIHOLE_PASSWORD is not configured')
        with httpx.Client(base_url=self.base, timeout=8.0, transport=self.transport) as c:
            try:
                login = c.post('/api/auth', json={'password': self.password})
                login.raise_for_status()
                sid = login.json()['session']['sid']
                resp = c.request(method, path, json=payload, headers={'X-FTL-SID':sid})
                resp.raise_for_status()
                result = resp.json() if resp.content else {}
                try:
                    c.delete('/api/auth', headers={'X-FTL-SID':sid})
                except httpx.HTTPError:
                    pass
                return result
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                raise PiHoleError('Pi-hole API request failed') from exc

    def summary(self):
        return self.request('GET','/api/stats/summary')

    def domains(self):
        return self.request('GET','/api/domains').get('domains', [])

    def add_exact(self, domain, action, groups=None):
        if action not in ('allow','deny'):
            raise ValueError('Only allow and deny can be deployed')
        return self.request('POST', f'/api/domains/{action}/exact',
                            {'domain':domain, 'comment':'managed by Edge Security', 'groups':groups if groups is not None else [0]})

    def delete_exact(self, domain, action):
        if action not in ('allow','deny'):
            raise ValueError('Only allow and deny can be deployed')
        return self.request('DELETE',f'/api/domains/{action}/exact/{quote(domain, safe="")}')

    def groups(self):
        return self.request('GET', '/api/groups').get('groups', [])

    def clients(self):
        return self.request('GET', '/api/clients').get('clients', [])

    def queries(self, length=30):
        return self.request('GET', f'/api/queries?length={int(length)}')

    def add_group(self, name, comment=''):
        return self.request('POST', '/api/groups', {'name': name, 'comment': comment})

    def add_client(self, client, comment='', groups=None):
        return self.request('POST', '/api/clients', {'client': client, 'comment': comment, 'groups': groups or [0]})

    def update_client_groups(self, client, groups, comment=''):
        # PUT replaces the complete client configuration; retain its existing comment.
        return self.request('PUT', '/api/clients/' + quote(client, safe=''),
                            {'comment': comment, 'groups': groups})

    def update_exact_groups(self, domain, action, groups, comment='managed by Edge Security'):
        if action not in ('allow', 'deny'):
            raise ValueError('Invalid action')
        return self.request('PUT', f'/api/domains/{action}/exact/{quote(domain, safe="")}',
                            {'comment': comment, 'groups': groups, 'enabled': True})
