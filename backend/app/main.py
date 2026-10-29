"""Main FastAPI application entry point, lifespan, CORS, error handling, and WebSocket hub."""

import logging
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.v1 import api_v1_router
from backend.certs.keys import get_or_create_active_signing_key
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.core.init_db import init_database
from backend.core.security import decode_token
from backend.models import User
from backend.wipe.worker import wipe_worker
from backend.ws.manager import ws_manager

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("securewipe.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager verifying simulation mode and starting background services."""
    # 1. Hard check: enforce WIPE_MODE strictly equals simulation
    if settings.WIPE_MODE != "simulation":
        logger.critical(f"FATAL: WIPE_MODE is '{settings.WIPE_MODE}'. Refusing to start.")
        sys.exit(1)

    logger.info("Initializing database tables and PL/pgSQL triggers...")
    await init_database()

    # Fresh database (e.g. a new cloud host): load the demo users and devices
    if settings.AUTO_SEED:
        from sqlalchemy import func, select
        from backend.seed import seed_database

        async with AsyncSessionLocal() as session:
            user_count = (await session.execute(select(func.count(User.id)))).scalar() or 0
        if user_count == 0:
            logger.info("Empty database detected, seeding demo users and devices...")
            await seed_database()

    # 2. Ensure active Ed25519 signing key exists
    async with AsyncSessionLocal() as session:
        active_key = await get_or_create_active_signing_key(session)
        logger.info(f"Active Ed25519 signing key ready: {active_key.key_id}")

    # 3. Start background asyncio worker
    wipe_worker.start()
    logger.info("FastAPI application started in SIMULATION MODE.")

    yield

    # Shutdown
    wipe_worker.stop()
    logger.info("FastAPI application shut down gracefully.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Certified IT asset recycling and NIST SP 800-88 Rev. 1 data wiping platform (Strict Simulation Mode).",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/docs/openapi.json",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Formats all HTTP errors into consistent {code, message, details} schema."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "details": getattr(exc, "details", None),
        },
    )


@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint confirming simulation mode status."""
    return {
        "status": "healthy",
        "mode": "simulation",
        "version": settings.VERSION,
    }


from backend.api.v1.public import router as public_router

# Include API v1 router and root public routes
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
app.include_router(public_router)


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    channel: str = Query("global"),
):
    """Real-time WebSocket endpoint streaming live progress and approval alerts."""
    # Validate token if provided
    user_name = "Anonymous"
    if token:
        try:
            payload = decode_token(token)
            user_id = uuid.UUID(payload.get("sub"))
            async with AsyncSessionLocal() as session:
                user = await session.get(User, user_id)
                if user:
                    user_name = user.name
        except Exception:
            pass

    await ws_manager.connect(websocket, channel=channel)
    try:
        # Send initial connection acknowledgment
        await websocket.send_json({
            "type": "connection.established",
            "channel": channel,
            "user": user_name,
            "mode": "simulation",
        })

        while True:
            # Client can send channel subscriptions or ping messages
            data = await websocket.receive_text()
            try:
                import json
                msg = json.loads(data)
                if msg.get("action") == "subscribe" and "channel" in msg:
                    await ws_manager.connect(websocket, channel=msg["channel"])
                    await websocket.send_json({"type": "subscribed", "channel": msg["channel"]})
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel=channel)
