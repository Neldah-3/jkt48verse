"""Router multi API key LLM: 1 base URL + 1 model, banyak key anti-limit."""

import pytest

from src.verse import llm_router
from src.verse.llm_router import LLMRouter, LLMError

BASE = "https://openrouter.ai/api/v1"
MODEL = "meta-llama/llama-3.1-8b-instruct"


class FakeResponse:
    def __init__(self, status_code: int, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


def _ok(content="Halo dari model"):
    return FakeResponse(200, {"choices": [{"message": {"content": content}}]})


class FakeClient:
    """Menggantikan httpx.AsyncClient — menjawab sesuai antrian yang diset."""

    queue: list = []

    def __init__(self, *args, **kwargs):
        self.calls: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers=None, json=None):
        FakeClient.calls.append({"url": url, "headers": headers, "json": json})
        item = FakeClient.queue.pop(0) if FakeClient.queue else _ok()
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def _fake_httpx(monkeypatch):
    FakeClient.queue = []
    FakeClient.calls = []
    monkeypatch.setattr(llm_router.httpx, "AsyncClient", FakeClient)
    yield
    FakeClient.queue = []
    FakeClient.calls = []


def _router(keys=("sk-a", "sk-b", "sk-c"), **kw):
    return LLMRouter(
        keys=list(keys),
        base_url=BASE,
        model=MODEL,
        cooldown=60,
        invalid_cooldown=900,
        **kw,
    )


@pytest.mark.asyncio
async def test_rotasi_round_robin():
    router = _router()
    FakeClient.queue = [_ok("satu"), _ok("dua"), _ok("tiga")]
    assert await router.chat([{"role": "user", "content": "a"}]) == "satu"
    assert await router.chat([{"role": "user", "content": "b"}]) == "dua"
    assert await router.chat([{"role": "user", "content": "c"}]) == "tiga"
    # setiap panggilan memakai key yang berbeda (beban tersebar)
    used = [c["headers"]["authorization"] for c in FakeClient.calls]
    assert used == ["Bearer sk-a", "Bearer sk-b", "Bearer sk-c"]


@pytest.mark.asyncio
async def test_key_kena_limit_pindah_ke_key_berikutnya():
    """Satu permintaan tetap berhasil walau key pertama kena 429."""
    router = _router()
    FakeClient.queue = [FakeResponse(429, {"error": {"message": "rate limited"}}), _ok("aman")]
    text = await router.chat([{"role": "user", "content": "hai"}])
    assert text == "aman"
    assert len(FakeClient.calls) == 2
    assert FakeClient.calls[0]["headers"]["authorization"] == "Bearer sk-a"
    assert FakeClient.calls[1]["headers"]["authorization"] == "Bearer sk-b"

    stats = router.stats()
    assert stats["coolingDown"] == 1
    assert stats["ready"] == 2
    assert stats["keys"][0]["errors"] == 1
    assert stats["keys"][0]["coolingDown"] is True


@pytest.mark.asyncio
async def test_retry_after_dipakai_untuk_cooldown():
    router = _router()
    FakeClient.queue = [
        FakeResponse(429, {"error": {"message": "limit"}}, headers={"retry-after": "45"}),
        _ok("ok"),
    ]
    await router.chat([{"role": "user", "content": "x"}])
    remaining = router.stats()["keys"][0]["cooldownSeconds"]
    assert 40 < remaining <= 45


@pytest.mark.asyncio
async def test_semua_key_limit_menghasilkan_error():
    router = _router(keys=("sk-a", "sk-b"))
    FakeClient.queue = [
        FakeResponse(429, {"error": {"message": "limit"}}),
        FakeResponse(429, {"error": {"message": "limit"}}),
    ]
    with pytest.raises(LLMError):
        await router.chat([{"role": "user", "content": "x"}])
    assert router.stats()["ready"] == 0


@pytest.mark.asyncio
async def test_key_invalid_diistirahatkan_lebih_lama():
    router = _router(keys=("sk-a", "sk-b"))
    FakeClient.queue = [FakeResponse(401, {"error": {"message": "bad key"}}), _ok("ok")]
    await router.chat([{"role": "user", "content": "x"}])
    assert router.stats()["keys"][0]["cooldownSeconds"] > 800


@pytest.mark.asyncio
async def test_error_jaringan_tidak_menghentikan_permintaan():
    router = _router(keys=("sk-a", "sk-b"))
    FakeClient.queue = [RuntimeError("timeout"), _ok("selamat")]
    assert await router.chat([{"role": "user", "content": "x"}]) == "selamat"


@pytest.mark.asyncio
async def test_respon_kosong_dianggap_gagal_lalu_coba_key_lain():
    router = _router(keys=("sk-a", "sk-b"))
    FakeClient.queue = [_ok("   "), _ok("isi")]
    assert await router.chat([{"role": "user", "content": "x"}]) == "isi"


@pytest.mark.asyncio
async def test_base_url_dan_model_tetap_satu():
    router = _router()
    FakeClient.queue = [_ok()]
    await router.chat([{"role": "user", "content": "x"}])
    call = FakeClient.calls[0]
    assert call["url"] == f"{BASE}/chat/completions"
    assert call["json"]["model"] == MODEL
    assert router.stats()["model"] == MODEL
    assert router.stats()["baseUrl"] == BASE


def test_tanpa_key_tidak_dikonfigurasi():
    router = LLMRouter(keys=[], base_url=BASE, model=MODEL)
    assert router.configured is False
    assert router.key_count == 0


@pytest.mark.asyncio
async def test_tanpa_key_chat_error():
    router = LLMRouter(keys=[], base_url=BASE, model=MODEL)
    with pytest.raises(LLMError):
        await router.chat([{"role": "user", "content": "x"}])


def test_statistik_menyensor_api_key():
    router = _router(keys=("sk-or-v1-rahasia-banget",))
    blob = str(router.stats())
    assert "sk-or-v1-rahasia-banget" not in blob
    assert router.stats()["keys"][0]["key"].startswith("sk-o")


def test_config_menggabungkan_semua_format_key(monkeypatch):
    from src.config import Settings

    monkeypatch.setenv("LLM_API_KEY", "sk-legacy")
    monkeypatch.setenv("LLM_API_KEYS", "sk-a, sk-b,sk-a")
    monkeypatch.setenv("LLM_API_KEY_1", "sk-n1")
    monkeypatch.setenv("LLM_API_KEY_2", "sk-n2")
    monkeypatch.setenv("LLM_API_KEY_3", "")
    s = Settings(
        ENV="dev",
        SECRET_KEY="dummy_secret_key_for_testing_12345",
        DATABASE_URL="postgresql://u:p@localhost/db",
    )
    assert s.llm_api_keys == ["sk-legacy", "sk-a", "sk-b", "sk-n1", "sk-n2"]
    assert s.llm_api_key == "sk-legacy"
    # base url & model tetap tunggal
    assert isinstance(s.llm_base_url, str) and isinstance(s.llm_model, str)


@pytest.mark.asyncio
async def test_moderation_block_chat_fail_open():
    """Moderasi memakai router yang sama; kalau LLM error → pesan diizinkan."""
    from src.verse import ai

    keys = ("sk-a", "sk-b")
    router = _router(keys=keys)
    monkeypatch_router = router

    import src.verse.ai as ai_mod

    original = ai_mod.get_router
    ai_mod.get_router = lambda: monkeypatch_router
    try:
        FakeClient.queue = [FakeResponse(200, {"choices": [{"message": {"content": "BLOCK|hinaan"}}]})]
        blocked, reason = await ai.moderate_text("dasar bego")
        assert blocked is True and reason == "hinaan"

        FakeClient.queue = [FakeResponse(200, {"choices": [{"message": {"content": "ALLOW"}}]})]
        blocked, reason = await ai.moderate_text("halo semua 😊")
        assert blocked is False and reason is None

        # fail-open: semua key error ⇒ tidak memblokir
        FakeClient.queue = [RuntimeError("down"), RuntimeError("down")]
        blocked, _ = await ai.moderate_text("pesan biasa")
        assert blocked is False
    finally:
        ai_mod.get_router = original


@pytest.mark.asyncio
async def test_parse_verdict():
    from src.verse import ai

    assert ai._parse_verdict("ALLOW") == (False, None)
    assert ai._parse_verdict("block") == (True, None)
    assert ai._parse_verdict("BLOCK|kata kasar") == (True, "kata kasar")
    assert ai._parse_verdict("") == (False, None)


class FakeDbResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeDbSession:
    async def execute(self, *args, **kwargs):
        return FakeDbResult([])


@pytest.mark.asyncio
async def test_ai_search_memakai_router(monkeypatch):
    """Jalur AI chat (AI Search) harus lewat router, bukan key tunggal."""
    from src.verse import ai

    router = _router(keys=("sk-a", "sk-b"))
    monkeypatch.setattr(ai, "get_router", lambda: router)

    FakeClient.queue = [_ok("JKT48 gen 3 antara lain ...")]
    result = await ai.llm_search(FakeDbSession(), "siapa member gen 3?")
    assert result["answer"] == "JKT48 gen 3 antara lain ..."
    assert result["mode"] == "llm"
    assert result["model"] == MODEL
    assert FakeClient.calls[0]["url"] == f"{BASE}/chat/completions"

    # key pertama error → otomatis lanjut ke key berikutnya, bukan fallback DB
    FakeClient.queue = [FakeResponse(429, {"error": {"message": "limit"}}), _ok("masuk")]
    result = await ai.llm_search(FakeDbSession(), "siapa member gen 3?")
    assert result["answer"] == "masuk"
    assert result.get("fallback") is None
