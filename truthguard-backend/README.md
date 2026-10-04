# TruthGuard AI — Backend (FastAPI)

Deepfake & misinformation detection API for civic education (UN SDG 4 & SDG 16).
Built for a 1-week college Software Engineering project: **no local model
weights, no GPU** — everything runs through free-tier hosted APIs.

## Features

| Endpoint | What it does | Upstream services |
|---|---|---|
| `POST /api/v1/detect-image` | Classifies an uploaded image as AI-generated/fake vs real, with a confidence % | Hugging Face Inference Providers (`hf-inference`), model `dima806/deepfake_vs_real_image_detection` |
| `POST /api/v1/fact-check` | Verifies a text claim → `True` / `False` / `Unverified` with explanation + real source URLs | Tavily (optional) or DuckDuckGo (`ddgs`) for retrieval + Groq (`openai/gpt-oss-20b`) for the judgement |
| `GET /health` | Uptime + which API keys are configured | — |

Interactive API docs (Swagger UI): **http://127.0.0.1:8000/docs**

## Project structure

```
truthguard-backend/
├── main.py                       # FastAPI app: CORS, endpoints, error handling, /health
├── config.py                     # Settings loaded from .env (pydantic-settings)
├── schemas.py                    # Pydantic request/response models (drive the /docs UI)
├── services/
│   ├── __init__.py
│   ├── errors.py                 # ServiceError -> clean JSON error responses
│   ├── deepfake_detector.py      # Part 1: image validation + HF inference + verdict logic
│   └── fact_checker.py           # Part 2: search -> prompt -> Groq -> validated JSON
├── requirements.txt
├── .env.example                  # copy to .env and fill in keys
└── README.md
```

## Setup (10 minutes)

```bash
# 1. Python 3.10+ required
cd truthguard-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure keys
cp .env.example .env            # Windows: copy .env.example .env
#    then edit .env:
#      HF_TOKEN     -> https://huggingface.co/settings/tokens  (Read scope)
#      GROQ_API_KEY -> https://console.groq.com/keys
#      TAVILY_API_KEY (optional) -> https://app.tavily.com

# 4. Run
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Important 2026 notes (things old tutorials get wrong)

1. **Groq retired `llama-3.1-8b-instant` on 2026-08-16** for free/developer
   accounts. The official replacement (used here by default) is
   `openai/gpt-oss-20b`. It's a *reasoning* model, so the code sends
   `include_reasoning=False` and `reasoning_effort="low"` for speed.
2. **Hugging Face's old Serverless Inference API
   (`api-inference.huggingface.co`) is decommissioned.** Use
   `InferenceClient(provider="hf-inference", token=...)` from
   `huggingface_hub>=1.0`. Free accounts get **$0.10/month of Inference
   Providers credit** — image classification is cheap, so this covers a demo,
   but don't load-test it.
3. **`duckduckgo-search` was renamed to `ddgs`** (mid-2025). The old package is
   frozen and breaks over time. This project uses `ddgs`.

## Testing with curl

```bash
# Health check
curl http://127.0.0.1:8000/health

# 1) Deepfake detection (multipart upload, field name = "file")
curl -X POST http://127.0.0.1:8000/api/v1/detect-image \
  -F "file=@/path/to/suspicious.jpg"

# 2) Fact-check
curl -X POST http://127.0.0.1:8000/api/v1/fact-check \
  -H "Content-Type: application/json" \
  -d '{"claim": "Drinking hot lemon water with salt cures the flu within 24 hours."}'
```

## Testing with Postman

- **detect-image**: `POST http://127.0.0.1:8000/api/v1/detect-image` →
  Body → *form-data* → key `file` (type **File**) → pick an image → Send.
- **fact-check**: `POST http://127.0.0.1:8000/api/v1/fact-check` →
  Body → *raw* → **JSON** → `{"claim": "..."}` → Send.
- Or just open **http://127.0.0.1:8000/docs** and use the "Try it out" buttons —
  no Postman needed at all.

## Error contract

Every failure returns JSON like:

```json
{ "detail": "Rate limited by Hugging Face (429). Wait a minute and retry.",
  "error_code": "hf_rate_limited" }
```

| HTTP | Meaning here |
|---|---|
| 400 | Invalid/corrupt image, empty file |
| 413 | Upload exceeds `MAX_IMAGE_MB` |
| 415 | Unsupported content type |
| 422 | Bad request JSON (claim missing/too short/too long) |
| 429 | Upstream rate limit (HF, Groq, or search) |
| 502/503/504 | Upstream failure / missing or invalid key / exhausted credits / cold start / timeout |

## How the fact-checker avoids hallucinations

- The LLM must judge **only** from the retrieved `<context>` snippets.
- Verdicts are whitelisted server-side (`True`/`False`/`Unverified`); anything
  ambiguous → `Unverified`.
- The LLM cites source **numbers**; the code maps numbers → the **real URLs it
  retrieved**, so fabricated sources are structurally impossible.
- Prompt injection: the claim is wrapped in `<claim>` tags and declared
  untrusted *data*; output schema is fixed; verdicts/citations re-validated in
  Python (defence in depth).

## Frontend integration notes

- CORS is preconfigured for `localhost:3000/5173/4200`; extend via
  `CORS_ORIGINS` in `.env`.
- Endpoints are auth-free by design so JWT middleware can be added on top
  (`Depends(get_current_user)` in `main.py` — services need no changes).
- Every response includes `X-Process-Time-Ms` and timing fields
  (`analyzed_in_ms` / `checked_in_ms`) for your UI spinners/metrics.
