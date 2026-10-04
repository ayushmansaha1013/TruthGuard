"""
services/deepfake_detector.py — PART 1: Deepfake / AI-generated image detection.

HOW IT WORKS (beginner explanation):
    We do NOT run any model locally (no GPU, no giant downloads). Instead:

      1. The user uploads an image to our FastAPI endpoint.
      2. We validate it with Pillow (is it really an image? is it too big?).
      3. We send the bytes to Hugging Face's "Inference Providers" API using
         the official `huggingface_hub.InferenceClient`. The model
         `dima806/deepfake_vs_real_image_detection` is a Vision Transformer
         fine-tuned on ~140k real vs AI-generated face images. It runs on
         Hugging Face's servers (provider "hf-inference") and returns a list
         like:  [{"label": "Fake", "score": 0.94}, {"label": "Real", "score": 0.06}]
      4. We translate that into a clean verdict JSON for the frontend.

    NOTE (Oct 2026): the old endpoint `api-inference.huggingface.co` was shut
    down. The modern way is `InferenceClient(provider="hf-inference", token=...)`
    which is exactly what we use here. Free HF accounts get a small monthly
    credit ($0.10) for Inference Providers — image classification on
    hf-inference is cheap, which is plenty for a college demo, but don't run
    load tests against it.

    This model is an EDUCATIONAL heuristic, not forensic proof — it looks at
    visual artifacts typical of GAN/diffusion-generated faces. We say so in
    every response ("note" field) so nobody mistakes it for ground truth.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
from typing import Any

from PIL import Image, UnidentifiedImageError

from config import get_settings
from services.errors import ServiceError

logger = logging.getLogger("truthguard.deepfake")

# Content types we accept. Browsers/curl sometimes send "application/octet-stream"
# for drag-and-dropped files, so we allow it and let Pillow sniff the real bytes.
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/octet-stream",
}

# We downscale huge images before uploading them to HF. The model itself only
# looks at 224x224 pixels internally, so 1024px max side loses nothing useful
# and keeps us far below HF's payload limits.
MAX_SIDE_PX = 1024
JPEG_QUALITY = 85

# Confidence tiers (percent) used to phrase the verdict for humans.
HIGH_CONFIDENCE = 85.0
MEDIUM_CONFIDENCE = 60.0

EDUCATIONAL_NOTE = (
    "This is an AI-based heuristic for civic education, not forensic proof. "
    "Detection of AI-generated media is an arms race — treat the result as a signal, not a verdict of law."
)


# ---------------------------------------------------------------------------
# Step 1: Validate + normalize the uploaded image (pure CPU, no network)
# ---------------------------------------------------------------------------
def _validate_and_prepare(image_bytes: bytes, content_type: str | None) -> bytes:
    """
    Make sure the upload is a real image, then re-encode it as a reasonably
    sized JPEG so the Hugging Face call is fast and within payload limits.

    Raises ServiceError(400/415) for anything the user did wrong.
    """
    if content_type and content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise ServiceError(
            415,
            f"Unsupported file type '{content_type}'. Please upload a JPEG, PNG or WebP image.",
            error_code="unsupported_media_type",
        )

    if not image_bytes:
        raise ServiceError(400, "Uploaded file is empty.", error_code="empty_file")

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # .load() forces Pillow to decode the ENTIRE file now. Without it,
            # a truncated/corrupt image would only explode later mid-request.
            img.load()

            # convert("RGB") drops alpha channels (PNG transparency) and CMYK,
            # giving the API a plain, predictable pixel format.
            rgb = img.convert("RGB")

            # thumbnail() shrinks in place while preserving aspect ratio and
            # does nothing if the image is already smaller than the box.
            rgb.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))

            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=JPEG_QUALITY)
            return buffer.getvalue()

    except UnidentifiedImageError:
        raise ServiceError(
            400,
            "The uploaded file could not be decoded as an image. Please upload a valid JPEG/PNG/WebP file.",
            error_code="invalid_image",
        )
    except Image.DecompressionBombError:
        # Pillow's built-in protection against tiny files that expand to
        # gigantic pixel counts (a classic DoS trick — your cybersecurity
        # teammate will appreciate this one).
        raise ServiceError(
            400,
            "Image rejected: suspiciously large pixel dimensions (possible decompression bomb).",
            error_code="image_too_many_pixels",
        )
    except OSError as exc:
        raise ServiceError(
            400,
            f"Invalid or corrupt image file: {exc}",
            error_code="invalid_image",
        )


# ---------------------------------------------------------------------------
# Step 2: Call Hugging Face (blocking network call — runs in a worker thread)
# ---------------------------------------------------------------------------
def _call_huggingface(prepared_jpeg: bytes) -> list[dict[str, Any]]:
    """
    Synchronous function that talks to Hugging Face and returns the raw
    classification results as plain dicts: [{"label": "Fake", "score": 0.94}, ...]
    """
    settings = get_settings()

    if not settings.hf_token:
        raise ServiceError(
            503,
            "HF_TOKEN is not configured. Create a free token at "
            "https://huggingface.co/settings/tokens (Read permission is enough) "
            "and put it in your .env file, then restart the server.",
            error_code="hf_token_missing",
        )

    try:
        from huggingface_hub import InferenceClient
        from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError
    except ImportError as exc:  # pragma: no cover
        raise ServiceError(
            500,
            "huggingface_hub is not installed. Run: pip install -r requirements.txt",
            error_code="dependency_missing",
        ) from exc

    # The client is cheap to build; no model weights are downloaded here.
    client = InferenceClient(
        provider=settings.hf_provider,     # "hf-inference" (HF's own serverless provider)
        token=settings.hf_token,
        timeout=settings.hf_timeout_seconds,
    )

    try:
        raw = client.image_classification(
            prepared_jpeg,
            model=settings.deepfake_model_id,
            top_k=5,
        )
    except HfHubHTTPError as exc:
        raise _map_hf_http_error(exc) from exc
    except InferenceTimeoutError as exc:
        raise ServiceError(
            504,
            "Hugging Face took too long to respond. The model may be cold-starting; retry in ~30 seconds.",
            error_code="upstream_timeout",
        ) from exc
    except Exception as exc:  # network down, DNS failure, anything unexpected
        logger.exception("Unexpected error calling Hugging Face")
        raise ServiceError(
            502,
            f"Unexpected error while calling Hugging Face: {type(exc).__name__}: {str(exc)[:200]}",
            error_code="upstream_error",
        ) from exc

    # Normalize whatever the SDK returned (dataclass objects or dicts) into
    # plain dicts so the rest of our code stays simple.
    results: list[dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, dict):
            label, score = item.get("label"), item.get("score")
        else:
            label, score = getattr(item, "label", None), getattr(item, "score", None)
        if label is not None and score is not None:
            results.append({"label": str(label), "score": float(score)})

    if not results:
        raise ServiceError(
            502,
            "Hugging Face returned an empty or unreadable response. Please retry.",
            error_code="empty_upstream_response",
        )
    return results


def _map_hf_http_error(exc: Exception) -> ServiceError:
    """
    Translate Hugging Face HTTP errors into friendly, actionable messages.
    Each branch is a failure mode you WILL hit during demos — knowing the
    difference saves debugging time.
    """
    settings = get_settings()

    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    body_excerpt = str(exc)[:300]

    if status in (401, 403):
        return ServiceError(
            503,
            "Hugging Face rejected the API token (401/403). Check that HF_TOKEN in your .env "
            "is valid and has at least 'Read' permission.",
            error_code="hf_token_invalid",
        )
    if status == 402:
        return ServiceError(
            503,
            "Your monthly free Hugging Face Inference Providers credit is exhausted (402). "
            "Free accounts get $0.10/month of credit; wait for next month or top up at "
            "https://huggingface.co/settings/billing.",
            error_code="hf_credits_exhausted",
        )
    if status == 404:
        return ServiceError(
            503,
            f"Model '{settings.deepfake_model_id}' was not found on provider '{settings.hf_provider}' (404). "
            "Check the model page on huggingface.co — the 'Inference Providers' widget must list a provider.",
            error_code="hf_model_not_found",
        )
    if status == 429:
        return ServiceError(
            429,
            "Rate limited by Hugging Face (429). You sent too many requests too quickly — wait a minute and retry.",
            error_code="hf_rate_limited",
        )
    if status == 503:
        return ServiceError(
            503,
            "The model is loading on Hugging Face's servers (cold start). Wait ~30-60 seconds and retry.",
            error_code="hf_model_loading",
        )
    return ServiceError(
        502,
        f"Hugging Face request failed (status {status}): {body_excerpt}",
        error_code="hf_upstream_error",
    )


# ---------------------------------------------------------------------------
# Step 3: Turn model output into a clean verdict
# ---------------------------------------------------------------------------
def _build_verdict(raw_label: str, confidence: float) -> str:
    """Map (predicted label, confidence %) to a human-friendly verdict string."""
    if raw_label == "fake":
        if confidence >= HIGH_CONFIDENCE:
            return "Likely Fake"
        if confidence >= MEDIUM_CONFIDENCE:
            return "Possibly Fake"
        return "Uncertain"
    # raw_label == "real"
    if confidence >= HIGH_CONFIDENCE:
        return "Likely Real"
    if confidence >= MEDIUM_CONFIDENCE:
        return "Possibly Real"
    return "Uncertain"


def _build_response(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the fake/real entries, compute confidence and assemble the JSON."""
    settings = get_settings()

    fake = next((r for r in results if "fake" in r["label"].lower()), None)
    real = next((r for r in results if "real" in r["label"].lower()), None)

    if fake is None and real is None:
        labels = ", ".join(r["label"] for r in results)
        raise ServiceError(
            500,
            f"Model '{settings.deepfake_model_id}' did not return the expected 'fake'/'real' "
            f"labels (got: {labels}). Set DEEPFAKE_MODEL_ID to a binary fake-vs-real classifier.",
            error_code="unexpected_model_output",
        )

    # fake_probability is the model's direct estimate that the image is AI-generated.
    if fake is not None:
        fake_probability = fake["score"] * 100.0
    else:
        fake_probability = (1.0 - real["score"]) * 100.0  # complement of "real" score

    # The predicted label is whichever of the two scored higher.
    if fake is not None and real is not None:
        top = fake if fake["score"] >= real["score"] else real
    else:
        top = fake or real

    raw_label = "fake" if "fake" in top["label"].lower() else "real"
    confidence = round(top["score"] * 100.0, 1)

    return {
        "verdict": _build_verdict(raw_label, confidence),
        "confidence": confidence,               # % confidence in the predicted label
        "raw_label": raw_label,                 # exactly what the model predicted
        "fake_probability": round(fake_probability, 1),  # handy for a frontend gauge
        "is_fake": raw_label == "fake",         # boolean convenience flag
        "model": settings.deepfake_model_id,
        "note": EDUCATIONAL_NOTE,
    }


# ---------------------------------------------------------------------------
# Public entry point (async — this is what main.py calls)
# ---------------------------------------------------------------------------
async def detect_deepfake(
    image_bytes: bytes,
    content_type: str | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """
    Full pipeline: validate -> call Hugging Face -> build verdict JSON.

    WHY asyncio.to_thread?
        FastAPI endpoints are `async`. The Hugging Face client is synchronous
        (it blocks until the HTTP response arrives, which can take seconds).
        Calling it directly inside an async endpoint would freeze the whole
        server for everyone during that time. `asyncio.to_thread` hands the
        blocking work to a background thread so the event loop stays free.
    """
    started = time.perf_counter()
    logger.info("Analyzing image upload (filename=%s, content_type=%s, bytes=%d)",
                filename, content_type, len(image_bytes))

    prepared = _validate_and_prepare(image_bytes, content_type)
    results = await asyncio.to_thread(_call_huggingface, prepared)
    response = _build_response(results)

    response["analyzed_in_ms"] = int((time.perf_counter() - started) * 1000)
    logger.info("Verdict: %s (%.1f%% %s)", response["verdict"],
                response["confidence"], response["raw_label"])
    return response
