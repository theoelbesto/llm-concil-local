from __future__ import annotations

from typing import Dict, List, Tuple

from .schemas import Stage1Opinion, Stage2AnonResponse


def anonymize_responses(
    opinions: List[Stage1Opinion],
) -> Tuple[List[Stage2AnonResponse], Dict[str, str]]:
    mapping: Dict[str, str] = {}
    anon_list: List[Stage2AnonResponse] = []
    label_index = 0
    for opinion in opinions:
        if opinion.error:
            continue
        response_id = f"Response {chr(ord('A') + label_index)}"
        label_index += 1
        mapping[opinion.model_id] = response_id
        anon_list.append(Stage2AnonResponse(response_id=response_id, answer=opinion.answer))
    return anon_list, mapping
