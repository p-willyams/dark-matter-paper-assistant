from typing import Literal, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sys
import os
import dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

dotenv_path = os.path.join(PROJECT_ROOT, ".env")
dotenv.load_dotenv(dotenv_path)

LLM_MODEL = os.getenv("LLM_MODEL")
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

from src.backend.query import answer_question

app = FastAPI(title="DarkRag API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_MODELS = Literal[LLM_MODEL]


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="User question")
    model: ALLOWED_MODELS = LLM_MODEL


class QueryResponse(BaseModel):
    answer: Optional[str]
    suspicious_citations: list[str]
    context: Optional[str]
    status: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=QueryResponse)
def ask_question(request: QueryRequest):
    result = answer_question(request.query, model=request.model)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result
