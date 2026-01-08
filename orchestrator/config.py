from __future__ import annotations

import os

COUNCIL_ENDPOINTS = [
    endpoint.strip()
    for endpoint in os.getenv("COUNCIL_ENDPOINTS", "").split(",")
    if endpoint.strip()
]
CHAIR_ENDPOINT = os.getenv("CHAIR_ENDPOINT", "")
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "60"))
MIN_AGENTS = int(os.getenv("MIN_AGENTS", "2"))
