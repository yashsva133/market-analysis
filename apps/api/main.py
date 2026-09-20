"""Main FastAPI application for India Market AI Research Terminal."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.common.config import settings
from packages.common.logging import get_logger
from packages.common.database import engine, Base

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown handler."""
    logger.info("Starting India Market AI Research Terminal API...")
    # Ensure database schema is created if database is reachable
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema validated.")
    except Exception as e:
        logger.warning(f"Database connection unavailable during startup ({e}). Continuing in standalone/offline mode.")
    yield
    logger.info("Shutting down API server...")
    try:
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title="India Market AI Research Terminal API",
    description="Local-first Indian equity event-monitoring and deep research intelligence system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID Middleware for distributed tracing across logs, collectors, and API
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from packages.common.logging import correlation_id_var

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        token = correlation_id_var.set(corr_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            return response
        finally:
            correlation_id_var.reset(token)

app.add_middleware(CorrelationIdMiddleware)


from apps.api.routers import (
    health,
    companies,
    events,
    research,
    ingest,
    market,
    screener,
    watchlist,
    portfolio,
    explorer,
    documents,
    calendar,
    compare,
    search,
    simulator,
    macro,
    lab,
    scenario,
    models,
    catalysts,
    alerts,
    news,
)

# Register Routers
app.include_router(health.router)
app.include_router(companies.router)
app.include_router(events.router)
app.include_router(research.router)
app.include_router(ingest.router)
app.include_router(market.router)
app.include_router(catalysts.router)
app.include_router(alerts.router)
app.include_router(news.router)
app.include_router(screener.router)
app.include_router(watchlist.router)
app.include_router(portfolio.router)
app.include_router(explorer.router)
app.include_router(documents.router)
app.include_router(calendar.router)
app.include_router(compare.router)
app.include_router(search.router)
app.include_router(simulator.router)
app.include_router(macro.router)
app.include_router(lab.router)
app.include_router(scenario.router)
app.include_router(models.router)





@app.get("/")
async def root():
    return {
        "terminal": "India Market AI Research Terminal",
        "status": "online",
        "docs_url": "/docs",
    }
