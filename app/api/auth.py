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

if not API_KEY:
    _logger.warning(
        "PAPER_MAKER_API_KEY set nahi hai — /api endpoints UNPROTECTED hain. "
        "Production deploy se pehle .env mein PAPER_MAKER_API_KEY zaroor set karo."
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
