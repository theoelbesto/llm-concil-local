from __future__ import annotations

import asyncio
from typing import List, Optional, Tuple

import httpx
from fastapi import FastAPI, HTTPException

from shared.anonymize import anonymize_responses
from shared.schemas import (
    FinalRequest,
    OrchestratorRunRequest,
    OrchestratorRunResponse,
    ReviewRequest,
    Stage1Opinion,
    Stage2Review,
    Stage3Final,
)

from .config import CHAIR_ENDPOINT, COUNCIL_ENDPOINTS, MIN_AGENTS, REQUEST_TIMEOUT_S

app = FastAPI(title="LLM Council Orchestrator")


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "detail": "ready"}


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict) -> httpx.Response:
    return await client.post(url, json=payload, timeout=REQUEST_TIMEOUT_S)


async def _call_generate(
    client: httpx.AsyncClient, endpoint: str, request: OrchestratorRunRequest
) -> Stage1Opinion:
    try:
        response = await _post_json(
            client,
            f"{endpoint.rstrip('/')}/generate",
            request.model_dump(exclude_none=True),
        )
        response.raise_for_status()
        data = response.json()
        return Stage1Opinion(
            model_id=data.get("model_id", endpoint),
            answer=data.get("answer", ""),
            latency_ms=data.get("latency_ms", 0),
        )
    except Exception as exc:  # noqa: BLE001
        return Stage1Opinion(
            model_id=endpoint,
            answer="",
            latency_ms=0,
            error=str(exc),
        )


async def _call_review(
    client: httpx.AsyncClient,
    endpoint: str,
    review_request: ReviewRequest,
) -> Stage2Review:
    try:
        response = await _post_json(
            client,
            f"{endpoint.rstrip('/')}/review",
            review_request.model_dump(exclude_none=True),
        )
        response.raise_for_status()
        data = response.json()
        return Stage2Review(
            model_id=data.get("model_id", endpoint),
            rankings=data.get("rankings", []),
            latency_ms=data.get("latency_ms", 0),
        )
    except Exception as exc:  # noqa: BLE001
        return Stage2Review(
            model_id=endpoint,
            rankings=[],
            latency_ms=0,
            error=str(exc),
        )


async def _call_chairman(
    client: httpx.AsyncClient, request: FinalRequest
) -> Stage3Final:
    try:
        response = await _post_json(
            client,
            f"{CHAIR_ENDPOINT.rstrip('/')}/final",
            request.model_dump(exclude_none=True),
        )
        response.raise_for_status()
        data = response.json()
        return Stage3Final(
            final_answer=data.get("final_answer", ""),
            latency_ms=data.get("latency_ms", 0),
        )
    except Exception as exc:  # noqa: BLE001
        return Stage3Final(final_answer="", latency_ms=0, error=str(exc))


@app.post("/run", response_model=OrchestratorRunResponse)
async def run(payload: OrchestratorRunRequest) -> OrchestratorRunResponse:
    if not COUNCIL_ENDPOINTS:
        raise HTTPException(status_code=500, detail="COUNCIL_ENDPOINTS not set")
    if not CHAIR_ENDPOINT:
        raise HTTPException(status_code=500, detail="CHAIR_ENDPOINT not set")

    async with httpx.AsyncClient() as client:
        stage1_results = await asyncio.gather(
            *[
                _call_generate(client, endpoint, payload)
                for endpoint in COUNCIL_ENDPOINTS
            ]
        )

        ok_opinions = [op for op in stage1_results if not op.error]
        if len(ok_opinions) < MIN_AGENTS:
            raise HTTPException(
                status_code=503,
                detail="Not enough healthy agents to proceed",
            )

        anon_responses, _ = anonymize_responses(stage1_results)

        review_request = ReviewRequest(
            query=payload.query,
            responses=[
                {"response_id": item.response_id, "answer": item.answer}
                for item in anon_responses
            ],
            rubric="Accuracy and insight based on the query.",
        )

        stage2_results = await asyncio.gather(
            *[
                _call_review(client, endpoint, review_request)
                for endpoint in COUNCIL_ENDPOINTS
            ]
        )

        first_opinions = [
            {"model_id": op.model_id, "answer": op.answer} for op in ok_opinions
        ]
        reviews = [
            {"reviewer_id": rv.model_id, "rankings": rv.rankings}
            for rv in stage2_results
            if not rv.error
        ]

        chair_request = FinalRequest(
            query=payload.query, first_opinions=first_opinions, reviews=reviews
        )
        stage3_final = await _call_chairman(client, chair_request)

    return OrchestratorRunResponse(
        stage1_first_opinions=stage1_results,
        stage2_anonymized_responses=anon_responses,
        stage2_reviews=stage2_results,
        stage3_final=stage3_final,
    )
