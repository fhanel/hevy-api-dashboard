import os
from typing import Any, Dict
import httpx

BASE: str = os.getenv("HEVY_API_BASE", "https://api.hevyapp.com/v1").rstrip("/")
# Ensure /v1 is always in the base URL
if not BASE.endswith("/v1"):
    BASE = f"{BASE.rstrip('/')}/v1" 
API_KEY: str = (os.getenv("HEVY_API_KEY") or "").strip()

if not API_KEY:
    raise RuntimeError(
        "HEVY_API_KEY is not set inside the container. "
        "Add it to .env and pass it via docker-compose.yml -> api.environment."
    )

def _headers() -> Dict[str, str]:
    return {
        "api-key": API_KEY,
        "accept": "application/json",
    }

def list_workouts(page: int = 1, page_size: int = 25) -> Any:
    url = f"{BASE}/workouts"
    params = {"page": page, "pageSize": page_size}
    with httpx.Client(timeout=30.0) as client:
        r = client.get(url, headers=_headers(), params=params)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            # Log useful context once during setup
            raise
        return r.json()

def get_workout(workout_id: str) -> Any:
    url = f"{BASE}/workouts/{workout_id}"
    with httpx.Client(timeout=30.0) as client:
        r = client.get(url, headers=_headers())
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            raise
        return r.json()

def list_exercise_templates(page: int = 1, page_size: int = 100) -> Any:
    """Fetch exercise templates from Hevy API"""
    url = f"{BASE}/exercise_templates"
    params = {"page": page, "pageSize": page_size}
    with httpx.Client(timeout=30.0) as client:
        r = client.get(url, headers=_headers(), params=params)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            raise
        return r.json()