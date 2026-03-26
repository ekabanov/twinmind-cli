"""Twinmind API client."""

import logging
import time
from typing import Any

import requests

from . import auth
from .models import Memory, MemoryTitle

logger = logging.getLogger(__name__)

API_BASE = "https://api.thirdear.live"
REQUEST_DELAY = 0.5
MAX_RETRIES = 3
BACKOFF_BASE = 2


class TwinmindAPI:
    def __init__(self):
        self._token: str | None = None
        self._session = requests.Session()

    def _get_token(self) -> str:
        if self._token is None:
            self._token = auth.get_id_token()
        return self._token

    def _refresh_token(self) -> str:
        self._token = None
        self._token = auth.get_id_token()
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def _request(
        self, method: str, path: str, params: dict | None = None, **kwargs
    ) -> Any:
        url = f"{API_BASE}{path}"
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                resp = self._session.request(
                    method, url, headers=self._headers(),
                    params=params, timeout=60, **kwargs,
                )

                if resp.status_code == 401:
                    logger.info("Got 401, refreshing token...")
                    self._refresh_token()
                    resp = self._session.request(
                        method, url, headers=self._headers(),
                        params=params, timeout=60, **kwargs,
                    )

                if resp.status_code == 429:
                    wait = BACKOFF_BASE ** (attempt + 1)
                    logger.warning("Rate limited, waiting %ds...", wait)
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                time.sleep(REQUEST_DELAY)
                return resp.json()

            except requests.exceptions.ConnectionError as e:
                last_error = e
                wait = BACKOFF_BASE**attempt
                logger.warning("Connection error, retrying in %ds: %s", wait, e)
                time.sleep(wait)
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code >= 500:
                    last_error = e
                    wait = BACKOFF_BASE**attempt
                    logger.warning("Server error %s, retrying in %ds", e.response.status_code, wait)
                    time.sleep(wait)
                else:
                    raise

        raise RuntimeError(f"Request failed after {MAX_RETRIES} retries: {last_error}")

    def get_memory_titles(self) -> list[MemoryTitle]:
        """Fetch all memory titles via POST, paginating with limit/offset."""
        all_titles = []
        offset = 0
        page_size = 100

        while True:
            data = self._request(
                "POST", "/api/v1/get_memory_titles",
                json={"limit": page_size, "offset": offset},
            )
            items = data.get("memories", []) if isinstance(data, dict) else data if isinstance(data, list) else []

            if not items:
                break

            all_titles.extend(MemoryTitle.from_api(item) for item in items)
            logger.info("Fetched %d memory titles (total: %d)", len(items), len(all_titles))

            if len(items) < page_size:
                break

            offset += len(items)

        return all_titles

    def get_memory(self, meeting_id: str) -> Memory:
        """Fetch full memory details including transcript and summary."""
        data = self._request("POST", "/api/v1/get_memory", json={"meeting_id": meeting_id})
        if isinstance(data, dict) and "memories" in data:
            memories = data["memories"]
            if memories:
                inner = memories[0]
                if "summary" in inner and isinstance(inner["summary"], dict):
                    return Memory.from_api(inner["summary"])
        return Memory.from_api(data)

    def get_summary_view(self, meeting_id: str) -> dict:
        """Fetch the V2 summary view for richer summary data."""
        try:
            return self._request("POST", "/api/v2/summary/view", json={"meeting_id": meeting_id})
        except Exception as e:
            logger.warning("Failed to fetch V2 summary for %s: %s", meeting_id, e)
            return {}

    def get_audio_url(self, meeting_id: str) -> str | None:
        """Get a signed URL for downloading the audio file."""
        try:
            data = self._request("POST", "/api/v2/transcriber-proxy/get-audio-url", json={"meeting_id": meeting_id})
            if isinstance(data, dict):
                return data.get("url") or data.get("audio_url") or data.get("signed_url")
            return None
        except Exception as e:
            logger.warning("Failed to get audio URL for %s: %s", meeting_id, e)
            return None

    def download_audio(self, url: str, dest_path: str) -> bool:
        """Download audio from a signed URL to a local file."""
        try:
            resp = self._session.get(url, stream=True, timeout=300)
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            logger.warning("Failed to download audio: %s", e)
            return False
