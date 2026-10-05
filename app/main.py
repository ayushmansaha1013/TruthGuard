from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

supabase_url = os.getenv("SUPABASE_URL")

print("Supabase URL:", supabase_url)

@app.get("/")
def home():
    return {"message": "Backend Running"}