"""Router API key LLM — banyak key, SATU base URL, SATU model.

Masalah yang dipecahkan: satu API key gampang kena limit (HTTP 429) karena
dipakai bersama untuk **AI chat** (AI Search) dan **block chat** (moderasi AI).

Desainnya sengaja dibuat sesederhana mungkin supaya gampang di-set:

* **Base URL cuma satu** (``LLM_BASE_URL``) — mencegah error salah endpoint.
* **Model cuma satu** (``LLM_MODEL``) — hemat token & perilaku konsisten.
* **API key boleh banyak** (``LLM_API_KEYS`` dipisah koma, atau
  ``LLM_API_KEY_1..N``, atau ``LLM_API_KEY`` lama). Semua digabung & de-dupe.

Cara kerja:
* Request dibagi **round-robin** ke key yang sehat — beban tersebar rata.
* Key yang kena **429** (limit) atau **5xx** masuk **cooldown sementara** dan
  dilewati; request otomatis dicoba ke key berikutnya dalam satu permintaan
  yang sama, jadi pemakai tidak melihat error limit selama masih ada key hidup.
* Key yang **401/403** (invalid / tidak punya akses model) diistirahatkan lebih
  lama, bukan dibuang, supaya pulih sendiri kalau diperbaiki.
* Statistik per key bisa dipantau lewat panel admin: ``GET /admin/ai/keys``.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from src.config import config
from src.logging_config import create_logger

logger = create_logger("llm_router", __name__)


class LLMError(RuntimeError):
    """Semua key gagal / tidak ada key yang bisa dipakai."""


def mask_key(key: str) -> str:
    k = (key or "").strip()
    if not k:
        return ""
    if len(k) <= 8:
        return f"{k[:1]}***({len(k)})"
    return f"{k[:4]}...{k[-4:]}"


@dataclass
class KeyState:
    """Status kesehatan satu API key (in-memory, hilang saat restart)."""

    label: str
    key: str
    ok: int = 0
    errors: int = 0
    cooldown_until: float = 0.0
    last_error: Optional[str] = None
    last_used_at: Optional[float] = None

    @property
    def cooling_down(self) -> bool:
        return self.cooldown_until > time.monotonic()

    def cooldown_remaining(self) -> float:
        return round(max(0.0, self.cooldown_until - time.monotonic()), 1)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "key": mask_key(self.key),
            "ok": self.ok,
            "errors": self.errors,
            "coolingDown": self.cooling_down,
            "cooldownSeconds": self.cooldown_remaining(),
            "lastError": self.last_error,
            "lastUsedAgo": (
                round(time.monotonic() - self.last_used_at) if self.last_used_at else None
            ),
        }


class _KeyFailure(Exception):
    def __init__(self, status: int, message: str, cooldown: float):
        super().__init__(message)
        self.status = status
        self.message = message
        self.cooldown = cooldown


class LLMRouter:
    """Round-robin + cooldown + failover untuk sekumpulan API key."""

    def __init__(
        self,
        keys: list[str],
        base_url: str,
        model: str,
        temperature: float = 0.3,
        timeout: float = 30.0,
        cooldown: float = 60.0,
        invalid_cooldown: float = 900.0,
        max_attempts: int = 0,
        max_cooldown: float = 3600.0,
    ):
        self._keys: list[KeyState] = [
            KeyState(label=f"key-{i + 1}", key=k.strip())
            for i, k in enumerate(keys or [])
            if (k or "").strip()
        ]
        self.base_url = (base_url or "").rstrip("/")           # hanya SATU base url
        self.model = model                                     # hanya SATU model
        self.temperature = temperature
        self.timeout = timeout
        self.cooldown = cooldown
        self.invalid_cooldown = invalid_cooldown
        self.max_cooldown = max_cooldown
        self.max_attempts = max_attempts or 0
        self._cursor = 0
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------- factory
    @classmethod
    def from_config(cls) -> "LLMRouter":
        return cls(
            keys=config.llm_api_keys,
            base_url=config.llm_base_url,
            model=config.llm_model,
            temperature=config.llm_temperature,
            timeout=config.llm_timeout_seconds,
            cooldown=config.llm_key_cooldown_seconds,
            invalid_cooldown=config.llm_key_invalid_cooldown_seconds,
            max_attempts=config.llm_max_attempts,
        )

    # ---------------------------------------------------------------- props
    @property
    def configured(self) -> bool:
        return bool(self._keys)

    @property
    def key_count(self) -> int:
        return len(self._keys)

    @property
    def url(self) -> str:
        return f"{self.base_url}/chat/completions"

    # -------------------------------------------------------------- picking
    def _pick(self) -> KeyState:
        """Round-robin: ambil key sehat berikutnya; semua sibuk ⇒ yang paling
        cepat bebas (akan tetap dicoba, siapa tahu limitnya sudah reset)."""
        total = len(self._keys)
        for i in range(total):
            idx = (self._cursor + i) % total
            state = self._keys[idx]
            if not state.cooling_down:
                self._cursor = (idx + 1) % total
                return state
        return min(self._keys, key=lambda s: s.cooldown_until)

    def _penalize(self, state: KeyState, failure: _KeyFailure) -> None:
        state.errors += 1
        state.last_error = failure.message
        state.cooldown_until = time.monotonic() + min(failure.cooldown, self.max_cooldown)
        logger.warning(
            f"[llm-router] {state.label} gagal ({failure.message}) — "
            f"istirahat {min(failure.cooldown, self.max_cooldown):.0f}s"
        )

    # ----------------------------------------------------------------- call
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Kirim chat completion. Rotasi key otomatis bila ada yang limit/error.

        Return: teks jawaban model. Raise ``LLMError`` bila semua key gagal.
        """
        if not self._keys:
            raise LLMError("Belum ada API key LLM yang dikonfigurasi.")

        attempts = self.max_attempts or len(self._keys)
        attempts = max(1, min(attempts, len(self._keys)))
        last_error = "tidak diketahui"

        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature if temperature is None else temperature,
            "messages": messages,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with self._lock:
            for _ in range(attempts):
                state = self._pick()
                state.last_used_at = time.monotonic()
                try:
                    async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
                        res = await client.post(
                            self.url,
                            headers={
                                "content-type": "application/json",
                                "authorization": f"Bearer {state.key}",
                            },
                            json=payload,
                        )

                    if res.status_code != 200:
                        raise self._as_failure(res)

                    try:
                        data = res.json()
                    except Exception as exc:  # body bukan JSON
                        raise _KeyFailure(res.status_code, f"Respon bukan JSON ({exc})", self.cooldown)

                    text = (
                        (data.get("choices") or [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        or ""
                    ).strip()
                    if not text:
                        err = (data.get("error") or {}).get("message") if isinstance(data, dict) else None
                        raise _KeyFailure(200, err or "Respon model kosong", self.cooldown)

                    state.ok += 1
                    state.last_error = None
                    state.cooldown_until = 0.0
                    return text

                except _KeyFailure as failure:
                    last_error = failure.message
                    self._penalize(state, failure)
                except Exception as exc:  # jaringan / timeout, dsb
                    last_error = f"{type(exc).__name__}: {exc}"
                    self._penalize(
                        state,
                        _KeyFailure(0, last_error, max(5.0, self.cooldown / 2)),
                    )

        raise LLMError(last_error)

    def _as_failure(self, res) -> _KeyFailure:
        status = res.status_code
        message = ""
        try:
            data = res.json()
            if isinstance(data, dict):
                message = (data.get("error") or {}).get("message") or data.get("message") or ""
        except Exception:
            data = None
        message = f"HTTP {status}: {(message or (res.text or '')[:120]).strip() or '-'}"

        if status in (401, 403):
            # key invalid / tidak punya akses ke model — istirahatkan lebih lama
            return _KeyFailure(status, message, self.invalid_cooldown)
        if status == 429:
            retry_after = res.headers.get("retry-after") if hasattr(res, "headers") else None
            cooldown = self.cooldown
            if retry_after:
                try:
                    cooldown = min(float(retry_after), self.max_cooldown)
                except (TypeError, ValueError):
                    pass
            return _KeyFailure(status, message, cooldown)
        if status >= 500 or status in (408, 409):
            return _KeyFailure(status, message, self.cooldown)
        return _KeyFailure(status, message, max(5.0, self.cooldown / 2))

    # ---------------------------------------------------------------- stats
    def stats(self) -> dict:
        return {
            "configured": bool(self._keys),
            "baseUrl": self.base_url,
            "model": self.model,
            "totalKeys": len(self._keys),
            "ready": sum(1 for k in self._keys if not k.cooling_down),
            "coolingDown": sum(1 for k in self._keys if k.cooling_down),
            "keys": [k.to_dict() for k in self._keys],
        }


_ROUTER: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Singleton router (dibuat saat pertama dipakai)."""
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = LLMRouter.from_config()
    return _ROUTER


def reset_router() -> None:
    """Buang singleton — dipakai test & saat env berubah."""
    global _ROUTER
    _ROUTER = None


def llm_configured() -> bool:
    return get_router().configured
