"""API-key auth for the /api surface.

Ek shared key per deployment (`PAPER_MAKER_API_KEY`), jo har /api request ke
`x-api-key` header mein aati hai. Yeh auth-secret ka owning boundary hai — key
sirf yahin, ek dafa read hoti hai (jaise ai_service apni provider keys ke liye
karti hai).

Behaviour deliberately do-modes hai:
  - PAPER_MAKER_API_KEY set    -> har /api call par sahi key zaroori (warna 401).
  - PAPER_MAKER_API_KEY unset  -> auth OFF + startup par loud warning. Local dev
    frictionless rehta hai; production mein .env mein key set karte hi poora
    /api surface lock ho jata hai. (Static frontend `/` par hamesha khula rehta
    hai — HTML/JS bina key ke load hona chahiye.)
"""

import logging
import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = "x-api-key"

# Secret yahin, module load par, ek baar read hoti hai. Empty = auth disabled.
API_KEY = os.environ.get("PAPER_MAKER_API_KEY") or ""

# auto_error=False: header missing hone par FastAPI khud 403 na de — hum
# apna 401 + Hinglish detail dena chahte hain (aur dev-mode mein pass karna hai).
_api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)

_logger = logging.getLogger("uvicorn.error")

# Environment variables jinki maujoodgi batati hai ke hum ek real (public)
# deployment par hain, local dev par nahi. Railway (hamara deploy target) inhe
# production par khud inject karta hai. Kisi bhi doosre host par
# PAPER_MAKER_REQUIRE_API_KEY=1 set karke bhi auth ko mandatory banaya ja sakta hai.
_DEPLOY_ENV_MARKERS = (
    "RAILWAY_ENVIRONMENT",
    "RAILWAY_ENVIRONMENT_NAME",
    "RAILWAY_SERVICE_ID",
)

_AUTH_MISSING_IN_DEPLOY_MSG = (
    "PAPER_MAKER_API_KEY set nahi hai lekin ye ek deployment environment lagta "
    "hai — /api ko bina key ke public karna matlab koi bhi tumhare AI tokens "
    "(paisa) aur DB use kar sakta hai. Deploy ke environment variables mein "
    "PAPER_MAKER_API_KEY (koi lambi random string) set karo. Local dev ke liye "
    "ise unset chhodo — wahan auth off rehti hai."
)


def _is_deployment(env) -> bool:
    """True jab environment ek real deployment lage: ya explicit
    PAPER_MAKER_REQUIRE_API_KEY flag, ya koi known deploy-host marker."""
    if str(env.get("PAPER_MAKER_REQUIRE_API_KEY", "")).strip().lower() in ("1", "true", "yes"):
        return True
    return any(env.get(marker) for marker in _DEPLOY_ENV_MARKERS)


def auth_config_error(api_key: str, env) -> str | None:
    """Misconfiguration detect karta hai aur error message deta hai (warna None).
    Pure + testable. Rule: deployment par key missing = fail-closed. Local dev
    (koi deploy signal nahi, key bhi missing) safe hai."""
    if api_key:
        return None
    if _is_deployment(env):
        return _AUTH_MISSING_IN_DEPLOY_MSG
    return None


# Fail-closed: deploy par key missing ho to app start hi na ho. Silently
# UNPROTECTED chalne se behtar hai loud crash — deploy fix ho jayega.
_config_error = auth_config_error(API_KEY, os.environ)
if _config_error:
    raise RuntimeError(_config_error)

if not API_KEY:
    _logger.warning(
        "PAPER_MAKER_API_KEY set nahi hai — /api endpoints UNPROTECTED hain. "
        "Ye sirf local dev ke liye theek hai. Production deploy se pehle host ke "
        "environment variables mein PAPER_MAKER_API_KEY zaroor set karo."
    )


def require_api_key(provided_key: str = Security(_api_key_header)) -> None:
    """FastAPI dependency: /api routers par lagti hai. Key configure na ho to
    dev-mode (pass). Warna `x-api-key` header ka exact match zaroori."""
    if not API_KEY:
        return
    if provided_key == API_KEY:
        return
    raise HTTPException(
        status_code=401,
        detail="API key ghalat ya missing hai — x-api-key header mein sahi key bhejein.",
    )
