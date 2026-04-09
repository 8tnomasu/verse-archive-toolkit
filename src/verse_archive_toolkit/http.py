from __future__ import annotations

import time
from typing import Any

import requests


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "verse-archive-toolkit/0.1.0"})
    return session


def safe_get_json(
    session: requests.Session,
    url: str,
    timeout: int,
    max_retries: int,
) -> Any:
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=timeout)

            if response.status_code in {429, 500, 502, 503, 504}:
                wait_seconds = min(2**attempt, 30)
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            last_error = error
            wait_seconds = min(2**attempt, 30)
            time.sleep(wait_seconds)

    if last_error is not None:
        raise last_error

    raise RuntimeError(f"Unable to fetch JSON from {url}.")
