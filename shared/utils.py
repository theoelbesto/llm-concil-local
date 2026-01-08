from __future__ import annotations

import time
from typing import Any, Dict, Tuple

import requests


def now_ms() -> int:
    return int(time.time() * 1000)


def post_ollama(
    ollama_url: str,
    model: str,
    prompt: str,
    temperature: float | None = None,
    timeout: int = 120,
) -> Tuple[str, int]:
    start = now_ms()
    payload: Dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
    if temperature is not None:
        payload["options"] = {"temperature": temperature}
    response = requests.post(
        f"{ollama_url.rstrip('/')}/api/generate",
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    latency_ms = now_ms() - start
    return data.get("response", ""), latency_ms
