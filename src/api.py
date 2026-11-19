"""FastAPI application for the Sentinel AI Gateway."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.engine import SecurityViolationError, SentinelEngine
from core.schema import AgentAction

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="Sentinel AI Gateway",
    description="Enterprise security gateway for validating agent actions against MITRE ATLAS / NIST CSF",
    version="1.0.0",
)

engine = SentinelEngine()


@app.get("/")
async def root():
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return FileResponse(index)


@app.post("/api/v1/validate")
async def validate(action: AgentAction):
    """Validate an AgentAction. Returns 200 if safe, 403 with threat intel if blocked."""
    try:
        result = engine.validate_action(action)
        return result
    except SecurityViolationError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "BLOCKED",
                "message": exc.message,
                "threat_intel": exc.threat_intel,
            },
        ) from exc


@app.get("/api/v1/metrics")
async def metrics():
    """Return aggregate counters and recent audit log entries."""
    return engine.get_metrics(recent_limit=10)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
