"""Check whether a legal-document URL is still reachable."""

import httpx

from app.clients.config import is_demo_mode


def is_url_reachable(url: str, timeout: float = 10.0) -> bool:
    """Return True if the URL responds with a success redirect or 2xx/3xx status."""
    if is_demo_mode():
        return True
    if not url or not url.startswith(("http://", "https://")):
        return False

    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Standing/1.0 (legal-doc link checker)"},
        ) as client:
            resp = client.head(url)
            if resp.status_code == 405:
                resp = client.get(url)
            return resp.status_code < 400
    except Exception:
        return False
