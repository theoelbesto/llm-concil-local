from __future__ import annotations

import os

MODEL_ID = os.getenv("MODEL_ID", "council-agent")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
DEFAULT_REVIEW_RUBRIC = os.getenv(
    "DEFAULT_REVIEW_RUBRIC",
    "Accuracy to the query, depth of insight, clarity, and correctness.",
)
