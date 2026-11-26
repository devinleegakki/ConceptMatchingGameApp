"""Google Sheets is authoritative. Device preferences hold the identity and unsent attempts."""
import asyncio
import json
import os
from pathlib import Path
import re
import secrets

import httpx


class ScoreServiceError(Exception):
    pass


def scores_endpoint(config):
    try:
        url = config.read_text(encoding="utf-8-sig").strip()
    except FileNotFoundError:
        url = ""
    except (OSError, UnicodeError) as exc:
        raise ScoreServiceError("Cannot read scores_endpoint.txt. Save the file as UTF-8 and retry.") from exc
    source = "scores_endpoint.txt"
    if not url:
        source = "SCORES_API_URL"
        url = os.environ.get(source, "").strip()
    if not url:
        raise ScoreServiceError("Google Sheets is not connected. Set the web app URL in scores_endpoint.txt and retry.")
    if not re.fullmatch(r"https://script\.google\.com/(?:macros|a/macros/[^/\s]+)/s/[A-Za-z0-9_-]+/exec", url):
        raise ScoreServiceError(f"Check {source}. Paste the deployed Google web app URL ending in /exec.")
    return url


def new_guest():
    animal = secrets.choice(("Robin", "Otter", "Falcon", "Lynx", "Panda", "Finch"))
    return {"key": secrets.token_hex(16), "name": f"Guest-{animal}-{secrets.token_hex(2)}"}


class SheetsScores:
    storage_key = "concept_match.scores.v1"

    def __init__(self, preferences):
        self.preferences = preferences
        self.config = Path(__file__).with_name("scores_endpoint.txt")
        self.lock = asyncio.Lock()
        self.identity = None
        self.pending = []
        self._client = None

    async def _load(self):
        if self.identity is not None:
            return
        saved = await self.preferences.get(self.storage_key)
        if saved:
            data = json.loads(saved)
            self.identity, self.pending = data["identity"], data["pending"]
        else:
            self.identity = new_guest()
            await self._save()

    async def _save(self):
        state = json.dumps({"identity": self.identity, "pending": self.pending})
        if not await self.preferences.set(self.storage_key, state):
            raise ScoreServiceError("Device storage is unavailable. Please retry.")

    async def _post(self, action, **payload):
        url = scores_endpoint(self.config)
        try:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=18)
            response = await self._client.post(url, json={"action": action, **payload}, follow_redirects=True)
        except httpx.TimeoutException as exc:
            raise ScoreServiceError(f"Connection to {exc.request.url.host} timed out. Check the network and retry.") from exc
        except httpx.RequestError as exc:
            raise ScoreServiceError(f"Connection to {exc.request.url.host} failed ({type(exc).__name__}). Check the network or proxy and retry.") from exc
        if response.url.host == "accounts.google.com" or response.status_code in (401, 403):
            raise ScoreServiceError("Access denied. Check that the web app deployment allows anyone to access it.")
        if not response.is_success:
            raise ScoreServiceError(f"The scores service returned HTTP {response.status_code}. Check the deployment URL and retry.")
        try:
            result = response.json()
        except ValueError as exc:
            raise ScoreServiceError("The web app returned a page instead of score data. Check the deployment URL and access settings.") from exc
        if not isinstance(result, dict):
            raise ScoreServiceError("Invalid scores service response.")
        if not result.get("ok") or "data" not in result:
            raise ScoreServiceError(result.get("error") or "Invalid scores service response.")
        return result["data"]

    async def enqueue(self, attempt):
        async with self.lock:
            await self._load()
            if not any(row["attempt_id"] == attempt["attempt_id"] for row in self.pending):
                self.pending.append(attempt)
            await self._save()

    async def _flush(self):
        while self.pending:
            await self._post("attempt", **self.identity, attempt=self.pending[0])
            self.pending.pop(0)
            await self._save()

    async def sync(self):
        async with self.lock:
            await self._load()
            await self._flush()

    async def view(self, action):
        async with self.lock:
            await self._load()
            return await self._post(action, **self.identity)

    async def sign_in(self, key):
        async with self.lock:
            await self._load()
            await self._flush()
            user = await self._post("login", key=key)
            self.identity = {"key": key, "name": user["name"]}
            await self._save()

    async def register(self, name):
        async with self.lock:
            await self._load()
            await self._flush()
            user = await self._post("register", key=self.identity["key"], name=name)
            self.identity["name"] = user["name"]
            await self._save()

    async def sign_out(self):
        async with self.lock:
            await self._load()
            await self._flush()
            self.identity = new_guest()
            await self._save()
