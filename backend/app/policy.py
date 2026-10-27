"""Pure domain validation and matching for observation-only policy decisions."""
import ipaddress
import re

DOMAIN_LABEL = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')

def canonical_domain(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError('domain must be a string')
    value = value.strip().rstrip('.').lower()
    try:
        value = value.encode('idna').decode('ascii')
    except UnicodeError as exc:
        raise ValueError('invalid domain') from exc
    if not value or len(value) > 253 or any(not DOMAIN_LABEL.fullmatch(x) for x in value.split('.')):
        raise ValueError('invalid domain')
    return value

def match_policy(domain: str | None, policies):
    if not domain:
        return None
    try:
        domain = canonical_domain(domain)
    except ValueError:
        return None
    matching = []
    for policy in policies:
        if not policy.enabled:
            continue
        pattern = policy.domain
        if domain == pattern or (policy.include_subdomains and domain.endswith('.' + pattern)):
            matching.append(policy)
    if not matching:
        return None
    # Most-specific matching rule wins; allow wins ties, then stable ID.
    return sorted(matching, key=lambda p: (-len(p.domain), p.action != 'allow', p.id))[0]

def canonical_ip(value: str):
    return str(ipaddress.ip_address(value))
