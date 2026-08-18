import os
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()

DEFAULT_RATE_LIMIT = os.environ.get("RATE_LIMIT_DEFAULT", "60/minute")
LOGIN_RATE_LIMIT = os.environ.get("RATE_LIMIT_LOGIN", "5/minute")
AI_RATE_LIMIT = os.environ.get("RATE_LIMIT_AI", "10/minute")

from starlette.requests import Request

def get_real_ip(request: Request) -> str:
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    # jesli zamiast cloudflare nginx
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    return get_remote_address(request)
limiter = Limiter(
    key_func=get_real_ip,
    default_limits=[DEFAULT_RATE_LIMIT]
)

