"""
main.py — TruthGuard AI backend (FastAPI).

TruthGuard is a deepfake & misinformation detection platform for civic
education (UN SDG 4 & SDG 16). This service exposes two AI endpoints:

    POST /api/v1/detect-image  -> deepfake / AI-generated image detection
    POST /api/v1/fact-check    -> claim verification grounded in live web sources
    GET  /health               -> uptime + configuration readiness check

Run locally:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Interactive docs (share these with your frontend teammate!):
    http://127.0.0.1:8000/docs

NOTE FOR THE SECURITY TEAMMATE: these endpoints are intentionally
auth-free so you can wrap them with your JWT middleware. The two service
functions (`detect_deepfake`, `fact_check`) are plain async calls — add your
`Depends(get_current_user)` on the endpoints in this file without touching
the services.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from schemas import (
    ErrorResponse,
    FactCheckRequest,
    FactCheckResponse,
    HealthResponse,
    ImageDetectionResponse,
)
from services.deepfake_detector import detect_deepfake
from services.errors import ServiceError
from services.fact_checker import fact_check

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("truthguard")

APP_VERSION = "1.0.0"
settings = get_settings()

CHUNK_SIZE = 1024 * 1024  # read uploads in 1 MB chunks

# Standard error responses documented in the OpenAPI schema (visible at /docs).
COMMON_ERROR_RESPONSES = {
    429: {"model": ErrorResponse, "description": "Upstream rate limit (Hugging Face / Groq / search)."},
    502: {"model": ErrorResponse, "description": "Upstream service failed or returned bad data."},
    503: {"model": ErrorResponse, "description": "Missing/invalid API key, exhausted credits, or model cold start."},
    504: {"model": ErrorResponse, "description": "Upstream timeout."},
}


# ---------------------------------------------------------------------------
# Startup: validate configuration and warn loudly about missing keys
# (we do NOT crash — teammates can run the app with partial config)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting TruthGuard AI backend v%s", APP_VERSION)
    if not settings.hf_token:
        logger.warning("HF_TOKEN missing -> /api/v1/detect-image will return 503 until it is set in .env")
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY missing -> /api/v1/fact-check will return 503 until it is set in .env")
    if not settings.tavily_api_key:
        logger.info("TAVILY_API_KEY not set -> using keyless DuckDuckGo search (can be rate-limited; Tavily is more reliable)")
    logger.info(
        "Config | deepfake model: %s (provider: %s) | groq model: %s | search: %s | CORS origins: %s",
        settings.deepfake_model_id, settings.hf_provider,
        settings.groq_model, settings.search_provider, settings.cors_origins_list,
    )
    yield
    logger.info("TruthGuard AI backend shutting down.")


app = FastAPI(
    title="TruthGuard AI API",
    version=APP_VERSION,
    description=(
        "Deepfake & misinformation detection backend for civic education (UN SDG 4 & 16).\n\n"
        "**Endpoints**\n"
        "- `POST /api/v1/detect-image` — upload an image (multipart form field `file`), get a fake/real verdict.\n"
        "- `POST /api/v1/fact-check` — submit a text claim, get True/False/Unverified grounded in live web sources.\n"
        "- `GET /health` — uptime and configuration readiness.\n\n"
        "All errors return `{\"detail\": \"...\", \"error_code\": \"...\"}` JSON."
    ),
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — lets the React frontend (running on a different localhost port)
# call this API from the browser. Origins are configurable via CORS_ORIGINS.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,      # needed once JWT auth sends cookies/headers
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time-Ms"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Tiny observability helper: every response gets its server time in ms."""
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = str(int((time.perf_counter() - start) * 1000))
    return response


# ---------------------------------------------------------------------------
# Exception handling — convert ServiceError into clean JSON responses
# ---------------------------------------------------------------------------
@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    logger.warning("ServiceError %d [%s] on %s: %s",
                   exc.status_code, exc.error_code, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """Last-resort net: log the full traceback server-side, send a vague 500
    to the client (never leak internals — your cybersecurity teammate approves)."""
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. The team has been notified via logs.",
                 "error_code": "internal_error"},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _read_upload_with_limit(file: UploadFile) -> bytes:
    """
    Stream the upload in chunks and enforce MAX_IMAGE_MB *while reading* —
    we never hold a multi-gigabyte file in memory just to reject it.
    """
    max_bytes = settings.max_image_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ServiceError(
                413,
                f"Image is larger than the {settings.max_image_mb} MB limit. Please upload a smaller file.",
                error_code="file_too_large",
            )
        chunks.append(chunk)
    if total == 0:
        raise ServiceError(400, "Uploaded file is empty.", error_code="empty_file")
    return b"".join(chunks)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["Meta"])
async def root():
    return {
        "service": "TruthGuard AI API",
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "endpoints": ["POST /api/v1/detect-image", "POST /api/v1/fact-check"],
    }


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"],
         summary="Uptime + configuration readiness check")
async def health():
    """
    Returns 200 as long as the process is alive, plus flags telling you which
    API keys are configured — the fastest way to debug "why is my endpoint
    returning 503?" during a demo.
    """
    all_keys_ready = bool(settings.hf_token and settings.groq_api_key)
    return {
        "status": "ok" if all_keys_ready else "degraded",
        "service": "truthguard-ai-backend",
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "hf_token_configured": bool(settings.hf_token),
            "groq_key_configured": bool(settings.groq_api_key),
            "search_provider": settings.search_provider,
            "deepfake_model": settings.deepfake_model_id,
            "groq_model": settings.groq_model,
        },
    }


@app.post(
    "/api/v1/detect-image",
    response_model=ImageDetectionResponse,
    tags=["Deepfake Detection"],
    summary="Detect whether an image is AI-generated / manipulated",
    responses={
        400: {"model": ErrorResponse, "description": "File is not a valid image."},
        413: {"model": ErrorResponse, "description": "File exceeds the size limit."},
        415: {"model": ErrorResponse, "description": "Unsupported content type."},
        **COMMON_ERROR_RESPONSES,
    },
)
async def detect_image_endpoint(
    file: UploadFile = File(..., description="Image to analyze (JPEG, PNG or WebP, max 8 MB)."),
):
    """
    Upload an image as `multipart/form-data` with the field name **file**.

    The image is validated locally, then classified by a pre-trained Vision
    Transformer on Hugging Face (`dima806/deepfake_vs_real_image_detection`
    by default) — no model weights are downloaded to this server.
    """
    image_bytes = await _read_upload_with_limit(file)
    result = await detect_deepfake(
        image_bytes,
        content_type=file.content_type,
        filename=file.filename,
    )
    return result


@app.post(
    "/api/v1/fact-check",
    response_model=FactCheckResponse,
    tags=["Fact Checking"],
    summary="Verify a text claim against live web sources",
    responses={
        422: {"description": "Claim missing, too short (<10) or too long (>1000 chars)."},
        **COMMON_ERROR_RESPONSES,
    },
)
async def fact_check_endpoint(payload: FactCheckRequest):
    """
    Submit a JSON body: `{"claim": "..."}`.

    Pipeline ("Search-Augmented Generation", a lightweight RAG):
    1. Search the live web for the claim (Tavily API if configured, else DuckDuckGo).
    2. Feed the top results to a Groq-hosted LLM with a strict system prompt:
       judge ONLY from that context, answer "Unverified" when unsure, and treat
       the claim text as untrusted data (prompt-injection defence).
    3. Validate the LLM's JSON server-side and map its cited source numbers
       back to the real URLs we retrieved — fabricated sources are impossible.
    """
    result = await fact_check(payload.claim)
    return result


if __name__ == "__main__":
    # Convenience: `python main.py` works too (same as the uvicorn command).
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
