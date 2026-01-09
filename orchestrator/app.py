from __future__ import annotations

import asyncio
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

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

from .config import (
    CHAIR_ENDPOINT,
    COUNCIL_ENDPOINTS,
    ALLOW_CHAIR_SAME_HOST,
    MIN_AGENTS,
    MIN_COUNCIL_HOSTS,
    REQUEST_TIMEOUT_S,
)

app = FastAPI(title="LLM Council Orchestrator")


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "detail": "ready"}


@app.get("/", response_class=HTMLResponse)
async def ui() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>LLM Council</title>
    <style>
      body { font-family: "Georgia", serif; margin: 24px; background: #f7f1e8; color: #1a1a1a; }
      h1 { margin: 0 0 8px; }
      .panel { background: #fff; border: 1px solid #d6cfc4; padding: 16px; border-radius: 8px; }
      .tabs { display: flex; gap: 8px; margin: 16px 0; flex-wrap: wrap; }
      .tab { border: 1px solid #b3a99a; background: #efe7da; padding: 8px 12px; border-radius: 6px; cursor: pointer; }
      .tab.active { background: #1a1a1a; color: #fff; border-color: #1a1a1a; }
      .content { display: none; white-space: pre-wrap; }
      .content.active { display: block; }
      textarea { width: 100%; min-height: 120px; }
      button { padding: 8px 14px; border-radius: 6px; border: none; background: #1a1a1a; color: #fff; cursor: pointer; }
      small { color: #5e5a52; }
    </style>
  </head>
  <body>
    <h1>LLM Council</h1>
    <p><small>Inspect Stage 1/2/3 outputs after running the council.</small></p>
    <div class="panel">
      <label for="query">Query</label>
      <textarea id="query" placeholder="Ask the council..."></textarea>
      <div style="margin-top: 12px;">
        <button id="runBtn">Run Council</button>
      </div>
    </div>

    <div class="tabs">
      <div class="tab active" data-tab="stage1">Stage 1</div>
      <div class="tab" data-tab="stage2">Stage 2</div>
      <div class="tab" data-tab="stage3">Stage 3</div>
      <div class="tab" data-tab="raw">Raw JSON</div>
    </div>
    <div class="panel" id="status">Status: idle</div>
    <div class="panel content active" id="stage1"></div>
    <div class="panel content" id="stage2"></div>
    <div class="panel content" id="stage3"></div>
    <div class="panel content" id="raw"></div>

    <script>
      const tabs = document.querySelectorAll(".tab");
      const contents = document.querySelectorAll(".content");
      tabs.forEach(tab => {
        tab.addEventListener("click", () => {
          tabs.forEach(t => t.classList.remove("active"));
          contents.forEach(c => c.classList.remove("active"));
          tab.classList.add("active");
          document.getElementById(tab.dataset.tab).classList.add("active");
        });
      });

      function formatStage1(data) {
        return data.stage1_first_opinions.map(item => {
          const label = item.model_id || "unknown";
          const answer = item.answer || "";
          return `Model: ${label}\\n${answer}`;
        }).join("\\n\\n---\\n\\n");
      }

      function formatStage2(data) {
        const anon = data.stage2_anonymized_responses.map(r => `${r.response_id}: ${r.answer}`);
        const reviews = data.stage2_reviews.map(r => `${r.model_id}: ${JSON.stringify(r.rankings)}`);
        return `Anonymized Responses\\n${anon.join("\\n")}\\n\\nReviews\\n${reviews.join("\\n")}`;
      }

      function formatStage3(data) {
        return data.stage3_final.final_answer || "";
      }

      document.getElementById("runBtn").addEventListener("click", async () => {
        const query = document.getElementById("query").value.trim();
        const status = document.getElementById("status");
        if (!query) {
          status.textContent = "Status: please enter a query.";
          return;
        }
        status.textContent = "Status: running...";
        try {
          const res = await fetch("/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query })
          });
          const data = await res.json();
          if (!res.ok) {
            status.textContent = `Status: error ${res.status} - ${data.detail || "unknown error"}`;
            document.getElementById("raw").textContent = JSON.stringify(data, null, 2);
            return;
          }
          document.getElementById("stage1").textContent = formatStage1(data);
          document.getElementById("stage2").textContent = formatStage2(data);
          document.getElementById("stage3").textContent = formatStage3(data);
          document.getElementById("raw").textContent = JSON.stringify(data, null, 2);
          status.textContent = "Status: completed.";
        } catch (err) {
          status.textContent = `Status: failed to reach orchestrator - ${err}`;
        }
      });
    </script>
  </body>
</html>
        """
    )


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


def _host_from_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.hostname:
        return parsed.hostname
    return endpoint


def _validate_deployment() -> None:
    if not COUNCIL_ENDPOINTS:
        raise HTTPException(status_code=500, detail="COUNCIL_ENDPOINTS not set")
    if not CHAIR_ENDPOINT:
        raise HTTPException(status_code=500, detail="CHAIR_ENDPOINT not set")

    council_hosts = {_host_from_endpoint(ep) for ep in COUNCIL_ENDPOINTS}
    chair_host = _host_from_endpoint(CHAIR_ENDPOINT)

    if len(COUNCIL_ENDPOINTS) < MIN_AGENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least {MIN_AGENTS} council endpoints",
        )
    if len(council_hosts) < MIN_COUNCIL_HOSTS:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least {MIN_COUNCIL_HOSTS} distinct council hosts",
        )
    if not ALLOW_CHAIR_SAME_HOST and chair_host in council_hosts:
        raise HTTPException(
            status_code=400,
            detail="Chairman must run on a separate host",
        )


@app.post("/run", response_model=OrchestratorRunResponse)
async def run(payload: OrchestratorRunRequest) -> OrchestratorRunResponse:
    _validate_deployment()

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
