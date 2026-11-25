"""Google Sheets is authoritative. Device preferences hold the identity and unsent attempts."""
import asyncio
import json
import os
from pathlib import Path
import secrets

import httpx


class ScoreServiceError(Exception):
    pass


def new_guest():
    animal = secrets.choice(("Robin", "Otter", "Falcon", "Lynx", "Panda", "Finch"))
    return {"key": secrets.token_hex(16), "name": f"Guest-{animal}-{secrets.token_hex(2)}"}


class SheetsScores:
    storage_key = "concept_match.scores.v1"

    def __init__(self, preferences):
        self.preferences = preferences
        config = Path(__file__).with_name("scores_endpoint.txt")
        self.url = os.environ.get("SCORES_API_URL") or (config.read_text("utf-8").strip() if config.exists() else "")
        self.lock = asyncio.Lock()
        self.identity = None
        self.pending = []

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
        if not self.url:
            raise ScoreServiceError("Google Sheets is not connected. Configure the scores web app and retry.")
        try:
            async with httpx.AsyncClient(timeout=18) as client:
                response = await client.post(self.url, json={"action": action, **payload}, follow_redirects=True)
                response.raise_for_status()
            result = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ScoreServiceError("Could not reach the scores sheet. Check the connection and web app access.") from exc
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
            await self._flush()
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
