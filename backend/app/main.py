"""FastAPI app entry point: CORS, router wiring, startup table creation, health."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

load_dotenv()

from app.crypto import ensure_encryption_key  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402  (import after load_dotenv)
from app.pipeline.institution_seed import seed_institutions_from_fixture
from app.routers import decode, profile  # noqa: E402

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
        "profile_encryption": bool(os.getenv("PROFILE_ENCRYPTION_KEY")),
    }
