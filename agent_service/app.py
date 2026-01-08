from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from shared.prompts import (
    build_first_opinion_prompt,
    build_json_fix_prompt,
    build_review_prompt,
)
from shared.schemas import (
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    ReviewRequest,
    ReviewResponse,
)
from shared.utils import now_ms, post_ollama

from .config import DEFAULT_REVIEW_RUBRIC, MODEL_ID, OLLAMA_MODEL, OLLAMA_URL

app = FastAPI(title="Council Agent")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True, model_id=MODEL_ID, detail="ready")


@app.post("/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest) -> GenerateResponse:
    prompt = build_first_opinion_prompt(payload.query, payload.context)
    answer, latency_ms = post_ollama(
        OLLAMA_URL, OLLAMA_MODEL, prompt, payload.temperature
    )
    return GenerateResponse(model_id=MODEL_ID, answer=answer.strip(), latency_ms=latency_ms)


def _parse_rankings(model_output: str) -> Dict[str, Any]:
    try:
        data = json.loads(model_output)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    if "rankings" not in data or not isinstance(data["rankings"], list):
        raise ValueError("JSON missing 'rankings' list")
    return data


@app.post("/review", response_model=ReviewResponse)
async def review(payload: ReviewRequest) -> ReviewResponse:
    rubric = payload.rubric or DEFAULT_REVIEW_RUBRIC
    prompt = build_review_prompt(payload.query, payload.responses, rubric)
    start = now_ms()
    output, _ = post_ollama(OLLAMA_URL, OLLAMA_MODEL, prompt, None)
    try:
        data = _parse_rankings(output)
    except ValueError:
        fix_prompt = build_json_fix_prompt(output)
        output, _ = post_ollama(OLLAMA_URL, OLLAMA_MODEL, fix_prompt, None)
        try:
            data = _parse_rankings(output)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    latency_ms = now_ms() - start
    return ReviewResponse(
        model_id=MODEL_ID, rankings=data["rankings"], latency_ms=latency_ms
    )
