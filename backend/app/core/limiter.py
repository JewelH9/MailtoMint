from slowapi import Limiter
from slowapi.util import get_remote_address

# get_remote_address extracts the real client IP
# In production behind a proxy, set FORWARDED_ALLOW_IPS env var
limiter = Limiter(key_func=get_remote_address)