import httpx
from app.pihole_client import PiHoleClient


def test_group_client_and_assignment_payloads():
    writes=[]
    def handler(req):
        if req.url.path == '/api/auth':
            return httpx.Response(200, json={'session': {'sid':'test'}}) if req.method=='POST' else httpx.Response(204)
        assert req.headers['X-FTL-SID'] == 'test'
        if req.method != 'GET':
            writes.append((req.method, req.url.path, req.content.decode()))
        return httpx.Response(200, json={'processed': {'success': []}})
    c=PiHoleClient(base='http://pihole',password='secret',transport=httpx.MockTransport(handler))
    c.add_group('Students','Managed group')
    c.add_client('192.0.2.5','Lab device',[0,2])
    c.update_client_groups('192.0.2.5',[2],'Lab device')
    assert [x[0] for x in writes]==['POST','POST','PUT']
    assert writes[0][1]=='/api/groups'
    assert writes[1][1]=='/api/clients'
    assert writes[2][1]=='/api/clients/192.0.2.5'
    assert '"groups":[2]' in writes[2][2]
