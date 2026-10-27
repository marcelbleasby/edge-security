import httpx
import pytest
from app.pihole_client import PiHoleClient

def test_pihole_session_and_exact_deploy():
    calls=[]
    def handler(req):
        calls.append((req.method, req.url.path))
        if req.url.path=='/api/auth' and req.method=='POST':
            return httpx.Response(200,json={'session':{'sid':'testsid'}})
        assert req.headers.get('X-FTL-SID')=='testsid'
        if req.url.path=='/api/domains/deny/exact':
            assert req.method=='POST'
            assert req.read().decode().find('example.com')!=-1
            return httpx.Response(201,json={'domains':[]})
        if req.url.path=='/api/auth' and req.method=='DELETE':
            return httpx.Response(204)
        return httpx.Response(404)
    c=PiHoleClient(base='http://pihole',password='test',transport=httpx.MockTransport(handler))
    c.add_exact('example.com','deny')
    assert calls==[('POST','/api/auth'),('POST','/api/domains/deny/exact'),('DELETE','/api/auth')]

def test_prevent_watch_deployment():
    with pytest.raises(ValueError):
        PiHoleClient(password='test').add_exact('example.com','watch')
