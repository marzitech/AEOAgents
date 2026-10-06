"""Shared Gemini client.

Retries transient errors (429 rate limit, 5xx "high demand") with exponential
backoff so one overloaded minute doesn't fail the weekly run.
"""

from google import genai
from google.genai import types

from app.config import settings

_RETRY = types.HttpRetryOptions(
    attempts=6,
    initial_delay=2.0,
    max_delay=60.0,
    http_status_codes=[429, 500, 502, 503, 504],
)


def gemini_client() -> genai.Client:
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(retry_options=_RETRY),
    )
