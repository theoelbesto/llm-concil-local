from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    query: str
    context: Optional[str] = None
    temperature: Optional[float] = None


class GenerateResponse(BaseModel):
    model_id: str
    answer: str
    latency_ms: int


class ResponseItem(BaseModel):
    response_id: str
    answer: str


class ReviewRequest(BaseModel):
    query: str
    responses: List[ResponseItem]
    rubric: str


class RankingItem(BaseModel):
    response_id: str
    rank: int = Field(ge=1)
    rationale: str


class ReviewResponse(BaseModel):
    model_id: str
    rankings: List[RankingItem]
    latency_ms: int


class FirstOpinion(BaseModel):
    model_id: str
    answer: str


class ReviewBundle(BaseModel):
    reviewer_id: str
    rankings: List[RankingItem]


class FinalRequest(BaseModel):
    query: str
    first_opinions: List[FirstOpinion]
    reviews: List[ReviewBundle]


class FinalResponse(BaseModel):
    final_answer: str
    latency_ms: int


class HealthResponse(BaseModel):
    ok: bool
    model_id: str
    detail: str


class OrchestratorRunRequest(BaseModel):
    query: str
    context: Optional[str] = None
    temperature: Optional[float] = None


class Stage1Opinion(BaseModel):
    model_id: str
    answer: str
    latency_ms: int
    error: Optional[str] = None


class Stage2AnonResponse(BaseModel):
    response_id: str
    answer: str


class Stage2Review(BaseModel):
    model_id: str
    rankings: List[RankingItem]
    latency_ms: int
    error: Optional[str] = None


class Stage3Final(BaseModel):
    final_answer: str
    latency_ms: int
    error: Optional[str] = None


class OrchestratorRunResponse(BaseModel):
    stage1_first_opinions: List[Stage1Opinion]
    stage2_anonymized_responses: List[Stage2AnonResponse]
    stage2_reviews: List[Stage2Review]
    stage3_final: Stage3Final
