from typing import Literal, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from query import answer_question

app = FastAPI(title="DarkRag API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_MODELS = Literal["openai/gpt-oss-20b"]


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="User question")
    model: ALLOWED_MODELS = "openai/gpt-oss-20b"


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
