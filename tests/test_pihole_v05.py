import httpx
from app.pihole_client import PiHoleClient


def test_v05_groups_clients_and_summary():
    seen=[]
    def handler(req):
        seen.append((req.method,req.url.path))
        if req.url.path == '/api/auth':
            if req.method == 'POST':
                return httpx.Response(200,json={'session':{'sid':'sid'}})
            return httpx.Response(204)
        assert req.headers['X-FTL-SID']=='sid'
        mapping={'/api/groups':{'groups':[{'name':'Default'}]},'/api/clients':{'clients':[{'client':'192.0.2.2'}]},'/api/stats/summary':{'queries':{'total':1}}}
        return httpx.Response(200,json=mapping[req.url.path])
    client=PiHoleClient(base='http://pihole',password='pass',transport=httpx.MockTransport(handler))
    assert client.groups()[0]['name']=='Default'
    assert client.clients()[0]['client']=='192.0.2.2'
    assert client.summary()['queries']['total']==1
    assert seen.count(('POST','/api/auth'))==3
    assert seen.count(('DELETE','/api/auth'))==3
