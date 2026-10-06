from fastapi import FastAPI, Request
from app.security.sanitize import sanitize

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Backend Running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/sanitize-test")
async def sanitize_test(request: Request):

    data = await request.json()

    user_text = data["text"]

    clean_text = sanitize(user_text)

    return {
        "original": user_text,
        "cleaned": clean_text
    }