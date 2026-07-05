"""FastAPI app entry point: CORS, router wiring, startup table creation, health."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.db import Base, engine  # noqa: E402  (import after load_dotenv)
from app.routers import decode  # noqa: E402

app = FastAPI(title="Standing API")

# Vite dev server origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(decode.router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health() -> dict:
    demo_mode = os.getenv("DEMO_MODE", "1") == "1"
    return {"status": "ok", "demo_mode": demo_mode}
