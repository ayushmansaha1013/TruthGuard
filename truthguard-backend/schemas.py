"""
schemas.py — Pydantic request/response models.

These do three jobs:
  1. VALIDATE incoming JSON (wrong types / missing fields -> automatic 422).
  2. SHAPE outgoing JSON (extra internal fields never leak to clients).
  3. Generate the interactive API docs at http://127.0.0.1:8000/docs, which
     your frontend teammate can use to integrate without asking you anything.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Part 1 — Deepfake image detection
# ---------------------------------------------------------------------------
class ImageDetectionResponse(BaseModel):
    verdict: str = Field(
        ...,
        description="Human-friendly verdict.",
        examples=["Likely Fake", "Possibly Fake", "Likely Real", "Possibly Real", "Uncertain"],
    )
    confidence: float = Field(
        ..., ge=0, le=100,
        description="Model confidence in the predicted label, as a percentage (0-100).",
        examples=[94.2],
    )
    raw_label: Literal["fake", "real"] = Field(
        ..., description="Exactly what the underlying model predicted."
    )
    fake_probability: float = Field(
        ..., ge=0, le=100,
        description="The model's probability that the image is AI-generated (0-100). Great for UI gauges.",
    )
    is_fake: bool = Field(..., description="Convenience boolean: raw_label == 'fake'.")
    model: str = Field(..., description="Hugging Face model id used.")
    note: str = Field(..., description="Educational disclaimer shown to end users.")
    analyzed_in_ms: int = Field(..., description="Server-side processing time in milliseconds.")


# ---------------------------------------------------------------------------
# Part 2 — Text fact-checking
# ---------------------------------------------------------------------------
class FactCheckRequest(BaseModel):
    claim: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description=(
            "The claim to verify, e.g. a viral WhatsApp forward or a news headline. "
            "Between 10 and 1000 characters."
        ),
        examples=["Drinking hot lemon water with salt cures the flu within 24 hours."],
    )


class RetrievedContextItem(BaseModel):
    title: str
    url: str
    snippet: str = Field(..., description="First 200 chars of the snippet the LLM saw.")


class FactCheckResponse(BaseModel):
    verdict: Literal["True", "False", "Unverified"] = Field(
        ...,
        description=(
            "'True' = clearly supported by sources, 'False' = clearly contradicted, "
            "'Unverified' = insufficient or weak evidence (the safe default)."
        ),
    )
    explanation: str = Field(..., description="2-3 plain-English sentences referencing the sources.")
    sources: list[str] = Field(
        ..., description="Real URLs the verdict is grounded in. Taken from OUR search results — the LLM cannot fabricate these."
    )
    claim: str = Field(..., description="The claim, echoed back.")
    context_found: bool = Field(..., description="False when the web search returned nothing (verdict is then always 'Unverified').")
    model: str = Field(..., description="Groq model id used for the judgement.")
    search_provider: Literal["tavily", "duckduckgo", "none"]
    retrieved_context: list[RetrievedContextItem] = Field(
        default_factory=list, description="Transparency: the exact search results fed to the LLM."
    )
    checked_in_ms: int = Field(..., description="Server-side processing time in milliseconds.")


# ---------------------------------------------------------------------------
# Health + errors
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    timestamp: str
    checks: dict[str, Any] = Field(
        ..., description="Per-dependency readiness flags (keys configured, providers chosen)."
    )


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Human-readable message, safe to show end users.")
    error_code: str = Field(..., description="Machine-readable tag for programmatic handling.")
