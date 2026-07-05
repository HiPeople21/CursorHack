"""FastAPI app entry point: CORS, router wiring, startup table creation, health."""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

load_dotenv()

from app.crypto import ensure_encryption_key, has_durable_encryption_key  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402  (import after load_dotenv)
from app.pipeline.institution_seed import seed_institutions_from_fixture
from app.routers import decode, lawyers, profile  # noqa: E402

app = FastAPI(title="Standing API")

_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,https://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add transport-security headers when TLS is enabled."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if os.getenv("FORCE_HTTPS", "0") == "1":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.include_router(decode.router)
app.include_router(lawyers.router)
app.include_router(profile.router)


@app.on_event("startup")
def on_startup() -> None:
    ensure_encryption_key()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_institutions_from_fixture(db)
    finally:
        db.close()


@app.get("/api/health")
def health() -> dict:
    demo_mode = os.getenv("DEMO_MODE", "1") == "1"
    tls_enabled = bool(os.getenv("SSL_KEYFILE") and os.getenv("SSL_CERTFILE"))
    return {
        "status": "ok",
        "demo_mode": demo_mode,
        "tls_enabled": tls_enabled,
        # Only report durable encryption — not the ephemeral dev key that the
        # demo bootstrap injects when no PROFILE_ENCRYPTION_KEY is configured.
        "profile_encryption": has_durable_encryption_key(),
    }


# --- Static frontend ---------------------------------------------------------
# In production the compiled Vite bundle is served by this same app, so the
# frontend's relative `/api/...` calls hit the same origin (no proxy, no CORS).
# The dist directory is optional: when it's absent (e.g. local `./dev.sh`, where
# Vite serves the frontend on :5173 and proxies /api here) these routes simply
# aren't registered. Registered last so the /api routes above always win.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_dist_candidates = []
if os.getenv("FRONTEND_DIST"):
    _dist_candidates.append(Path(os.environ["FRONTEND_DIST"]))
_dist_candidates += [
    _BACKEND_DIR / "static",  # baked into the Docker image
    _BACKEND_DIR.parent / "frontend" / "dist",  # local `npm run build`
]
_FRONTEND_DIST = next(
    (p for p in _dist_candidates if (p / "index.html").is_file()), None
)

if _FRONTEND_DIST is not None:
    _assets_dir = _FRONTEND_DIST / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        """Serve a static file when it exists, else fall back to index.html."""
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
