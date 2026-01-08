from __future__ import annotations

from fastapi import FastAPI

from shared.prompts import build_chairman_prompt
from shared.schemas import FinalRequest, FinalResponse, HealthResponse
from shared.utils import post_ollama

from .config import MODEL_ID, OLLAMA_MODEL, OLLAMA_URL

app = FastAPI(title="Council Chairman")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True, model_id=MODEL_ID, detail="ready")


@app.post("/final", response_model=FinalResponse)
async def final_answer(payload: FinalRequest) -> FinalResponse:
    prompt = build_chairman_prompt(payload.query, payload.first_opinions, payload.reviews)
    answer, latency_ms = post_ollama(OLLAMA_URL, OLLAMA_MODEL, prompt, None)
    return FinalResponse(final_answer=answer.strip(), latency_ms=latency_ms)
