from types import SimpleNamespace
from app.policy import canonical_domain, match_policy

def rule(i, domain, action, sub=True, enabled=True):
    return SimpleNamespace(id=i, domain=domain, action=action, include_subdomains=sub, enabled=enabled)

def test_canonical():
    assert canonical_domain(' ExAmPle.Org. ') == 'example.org'
    assert canonical_domain('bücher.de') == 'xn--bcher-kva.de'

def test_invalid():
    for value in ('', 'not valid.org', 'a..com', '-abc.com'):
        try:
            canonical_domain(value)
            assert False, value
        except ValueError:
            pass

def test_specificity_and_boundaries():
    policies = [rule(1,'example.com','deny'), rule(2,'safe.example.com','allow')]
    assert match_policy('safe.example.com', policies).action == 'allow'
    assert match_policy('other.example.com', policies).action == 'deny'
    assert match_policy('badexample.com', policies) is None
    assert match_policy('example.com.evil', policies) is None

def test_exact_and_disabled():
    assert match_policy('sub.example.com',[rule(1,'example.com','deny',False)]) is None
    assert match_policy('example.com',[rule(1,'example.com','deny',True,False)]) is None
