from __future__ import annotations

import json
from typing import List

from .schemas import ResponseItem, ReviewBundle, FirstOpinion


def build_first_opinion_prompt(query: str, context: str | None) -> str:
    context_block = f"\nContext:\n{context}" if context else ""
    return (
        "You are a Council member. Provide a concise, accurate answer. "
        "If unsure, say so briefly.\n\n"
        f"Query:\n{query}{context_block}\n\nAnswer:"
    )


def build_review_prompt(query: str, responses: List[ResponseItem], rubric: str) -> str:
    response_lines = [f"{item.response_id}: {item.answer}" for item in responses]
    response_block = "\n".join(response_lines)
    return (
        "You are a strict evaluator. Rank the responses by accuracy and insight. "
        "Return ONLY valid JSON with a top-level key 'rankings'. "
        "Each ranking item must have response_id, rank (1 is best), and rationale. "
        "No extra keys, no prose.\n\n"
        f"Rubric:\n{rubric}\n\n"
        f"Query:\n{query}\n\n"
        f"Responses:\n{response_block}\n\n"
        "Return JSON now."
    )


def build_json_fix_prompt(bad_output: str) -> str:
    return (
        "The previous output was invalid JSON. "
        "Return ONLY corrected JSON matching: {\"rankings\": [{\"response_id\": str, "
        "\"rank\": int, \"rationale\": str}]}. "
        "No extra keys or text.\n\n"
        f"Bad output:\n{bad_output}\n\n"
        "Return corrected JSON only."
    )


def build_chairman_prompt(
    query: str, first_opinions: List[FirstOpinion], reviews: List[ReviewBundle]
) -> str:
    first_block = "\n".join(
        f"{item.model_id}: {item.answer}" for item in first_opinions
    )
    reviews_block = "\n".join(
        f"{bundle.reviewer_id}: {json.dumps([r.model_dump() for r in bundle.rankings])}"
        for bundle in reviews
    )
    return (
        "You are the Chairman. Synthesize a final answer using the first opinions and "
        "the reviews. Correct mistakes. Do not introduce unrelated new information. "
        "Write a clear, concise final response.\n\n"
        f"Query:\n{query}\n\n"
        f"First opinions:\n{first_block}\n\n"
        f"Reviews:\n{reviews_block}\n\n"
        "Final answer:"
    )
