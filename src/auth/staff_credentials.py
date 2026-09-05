"""Kredensial staff (Admin & Moderator) yang dibaca dari environment.

Aturan main mengikuti permintaan owner — ALL-OR-NOTHING:

* Admin     : 3 slot  -> ``ADMIN_1_*`` .. ``ADMIN_3_*``
* Moderator : 10 slot -> ``MOD_1_*``  .. ``MOD_10_*``
* Setiap slot butuh **4 nilai sekaligus**: ``_USERNAME``, ``_EMAIL``,
  ``_PASSWORD``, ``_ACCESS_CODE``.
* Kalau **satu saja** kosong ⇒ slot bernilai ``False`` (nonaktif) dan akun
  tersebut **tidak bisa login** sampai keempat nilai lengkap.
* Pencocokan **100% persis**: besar/kecil huruf, spasi, dan karakter apa pun
  dihitung. Tidak ada lowercasing, trimming, maupun normalisasi.
* Tidak wajib mengisi semua user. Yang tidak mau ditambahkan cukup dibiarkan
  kosong (``= false``); yang diisi **harus lengkap**.

Contoh .env yang valid untuk satu admin::

    ADMIN_1_USERNAME=Neldah
    ADMIN_1_EMAIL=neldah@jkt48verse.local
    ADMIN_1_PASSWORD=Ra#hasia123
    ADMIN_1_ACCESS_CODE=JKT48-Admin-01

Nilai dibaca mentah dari ``os.environ`` (bukan lewat pydantic) supaya tidak
ada satu karakter pun yang berubah di tengah jalan.
"""

from __future__ import annotations

import hmac
import os
from dataclasses import dataclass, field
from typing import Optional

from src.logging_config import create_logger

logger = create_logger("staff_credentials", __name__)

ADMIN_ROLE = "ADMIN"
MODERATOR_ROLE = "MODERATOR"

#: prefix env per role
ROLE_PREFIX = {ADMIN_ROLE: "ADMIN", MODERATOR_ROLE: "MOD"}

#: jumlah slot yang disediakan
ADMIN_SLOT_COUNT = 3
MODERATOR_SLOT_COUNT = 10

#: urutan tetap — dipakai juga untuk laporan/seed
ROLE_SLOTS: tuple[tuple[str, int], ...] = (
    (ADMIN_ROLE, ADMIN_SLOT_COUNT),
    (MODERATOR_ROLE, MODERATOR_SLOT_COUNT),
)

#: field yang WAJIB lengkap supaya slot aktif
REQUIRED_FIELDS: tuple[str, ...] = ("USERNAME", "EMAIL", "PASSWORD", "ACCESS_CODE")

#: penanda di kolom users.provider untuk akun yang lahir dari slot ini
PROVIDER = "credential"


# --------------------------------------------------------------------- utils
def equals(a: str, b: str) -> bool:
    """Perbandingan persis (case-sensitive, karakter apa pun) + constant-time."""
    if a is None or b is None:
        return False
    if len(a) != len(b):
        return False
    try:
        return hmac.compare_digest(a, b)
    except TypeError:
        # compare_digest hanya menerima ASCII — fallback tetap persis
        return a == b


def _raw(role: str, slot: int, name: str) -> str:
    """Ambil nilai env **mentah** (tanpa strip/lower)."""
    return os.environ.get(f"{ROLE_PREFIX[role]}_{slot}_{name}", "")


def mask_secret(value: str) -> str:
    v = value or ""
    if not v:
        return ""
    if len(v) <= 8:
        return f"{v[0]}***({len(v)})"
    return f"{v[:3]}***{v[-2:]} ({len(v)} chars)"


def mask_email(email: str) -> str:
    e = email or ""
    if "@" not in e:
        return mask_secret(e)
    local, _, domain = e.partition("@")
    head = local[:2] if len(local) > 2 else local[:1]
    return f"{head}***@{domain}"


# ------------------------------------------------------------------- models
@dataclass(frozen=True)
class StaffCredential:
    """Satu slot kredensial yang **lengkap** (sudah lolos validasi)."""

    role: str
    slot: int
    username: str
    email: str
    password: str
    access_code: str

    @property
    def label(self) -> str:
        return f"{ROLE_PREFIX[self.role]}_{self.slot}"

    @property
    def env_keys(self) -> list[str]:
        return [f"{self.label}_{name}" for name in REQUIRED_FIELDS]

    def matches(self, username: str = "", email: str = "") -> bool:
        """Cocokkan username/email user database secara **persis**."""
        for candidate in (username, email):
            if not candidate:
                continue
            if equals(candidate, self.username) or equals(candidate, self.email):
                return True
        return False

    def verify_access_code(self, code: Optional[str]) -> bool:
        if not code:
            return False
        return equals(code, self.access_code)

    def to_dict(self, reveal: bool = False) -> dict:
        return {
            "role": self.role,
            "slot": self.slot,
            "label": self.label,
            "username": self.username if reveal else mask_secret(self.username),
            "email": self.email if reveal else mask_email(self.email),
            "password": "***" if self.password else "",
            "accessCode": mask_secret(self.access_code),
        }


@dataclass
class SlotStatus:
    """Status satu slot: aktif atau ``False`` berikut alasannya."""

    role: str
    slot: int
    active: bool = False
    defined: bool = False
    username: str = ""
    email: str = ""
    missing: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def label(self) -> str:
        return f"{ROLE_PREFIX[self.role]}_{self.slot}"

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "slot": self.slot,
            "label": self.label,
            "active": self.active,
            "defined": self.defined,
            "username": mask_secret(self.username),
            "email": mask_email(self.email),
            "missing": [f"{self.label}_{m}" for m in self.missing],
            "reason": self.reason,
        }


@dataclass
class GateResult:
    """Hasil pengecekan code akses saat login."""

    code: str  # SLOT_INCOMPLETE | CODE_REQUIRED | CODE_INVALID
    message: str


# ------------------------------------------------------------------ registry
@dataclass
class _Registry:
    credentials: list[StaffCredential] = field(default_factory=list)
    slots: list[SlotStatus] = field(default_factory=list)
    defined_slots: list[SlotStatus] = field(default_factory=list)

    def find(self, username: str = "", email: str = "") -> Optional[StaffCredential]:
        """Slot **aktif** yang cocok dengan user (persis)."""
        for cred in self.credentials:
            if cred.matches(username, email):
                return cred
        return None

    def find_slot(self, username: str = "", email: str = "") -> Optional[SlotStatus]:
        """Slot yang **pernah diisi** (aktif atau tidak) yang cocok dengan user."""
        for slot in self.defined_slots:
            for candidate in (username, email):
                if not candidate:
                    continue
                if equals(candidate, slot.username) or equals(candidate, slot.email):
                    return slot
        return None

    def by_role(self, role: str) -> list[StaffCredential]:
        return [c for c in self.credentials if c.role == role]


_REGISTRY: Optional[_Registry] = None


def _build() -> _Registry:
    creds: list[StaffCredential] = []
    slots: list[SlotStatus] = []
    defined: list[SlotStatus] = []
    seen_username: dict[str, str] = {}
    seen_email: dict[str, str] = {}

    for role, count in ROLE_SLOTS:
        for slot in range(1, count + 1):
            values = {name: _raw(role, slot, name) for name in REQUIRED_FIELDS}

            if not any(values.values()):
                # tidak dipakai sama sekali = false, tanpa peringatan
                slots.append(
                    SlotStatus(role, slot, active=False, defined=False, reason="kosong (tidak dipakai)")
                )
                continue

            for name, value in values.items():
                if value and value != value.strip():
                    logger.warning(
                        f"{ROLE_PREFIX[role]}_{slot}_{name} punya spasi di awal/akhir. "
                        "Nilai dipakai persis apa adanya (spasi ikut terhitung) — "
                        "pastikan saat login diketik sama persis."
                    )

            missing = [name for name in REQUIRED_FIELDS if values[name] == ""]
            if missing:
                status = SlotStatus(
                    role,
                    slot,
                    active=False,
                    defined=True,
                    username=values["USERNAME"],
                    email=values["EMAIL"],
                    missing=missing,
                    reason="tidak lengkap: " + ", ".join(missing),
                )
                slots.append(status)
                defined.append(status)
                logger.warning(
                    f"[staff] {status.label} NONAKTIF (false) — {status.reason}. "
                    "Akun ini tidak bisa login sampai keempat nilai diisi."
                )
                continue

            username, email = values["USERNAME"], values["EMAIL"]
            dup_of = seen_username.get(username) or seen_email.get(email.lower())
            if dup_of:
                status = SlotStatus(
                    role,
                    slot,
                    active=False,
                    defined=True,
                    username=username,
                    email=email,
                    reason=f"username/email duplikat dengan {dup_of}",
                )
                slots.append(status)
                defined.append(status)
                logger.warning(f"[staff] {status.label} NONAKTIF (false) — {status.reason}.")
                continue

            seen_username[username] = f"{ROLE_PREFIX[role]}_{slot}"
            seen_email[email.lower()] = f"{ROLE_PREFIX[role]}_{slot}"

            cred = StaffCredential(
                role=role,
                slot=slot,
                username=username,
                email=email,
                password=values["PASSWORD"],
                access_code=values["ACCESS_CODE"],
            )
            creds.append(cred)
            status = SlotStatus(
                role, slot, active=True, defined=True, username=username, email=email, reason="lengkap"
            )
            slots.append(status)
            defined.append(status)

    return _Registry(credentials=creds, slots=slots, defined_slots=defined)


def reload() -> _Registry:
    """Baca ulang environment (dipakai seeder & test)."""
    global _REGISTRY
    _REGISTRY = _build()
    return _REGISTRY


def registry() -> _Registry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build()
    return _REGISTRY


# --------------------------------------------------------------------- API
def staff_credentials() -> list[StaffCredential]:
    """Semua slot **aktif** (lengkap 4/4), admin + moderator."""
    return list(registry().credentials)


def admin_credentials() -> list[StaffCredential]:
    return registry().by_role(ADMIN_ROLE)


def moderator_credentials() -> list[StaffCredential]:
    return registry().by_role(MODERATOR_ROLE)


def find_credential(username: str = "", email: str = "") -> Optional[StaffCredential]:
    return registry().find(username, email)


def find_slot(username: str = "", email: str = "") -> Optional[SlotStatus]:
    return registry().find_slot(username, email)


def report() -> list[dict]:
    """Status semua slot (nilai rahasia disensor) — untuk panel admin."""
    return [s.to_dict() for s in registry().slots]


def summary() -> dict:
    reg = registry()
    out = {}
    for role, count in ROLE_SLOTS:
        active = len(reg.by_role(role))
        out[ROLE_PREFIX[role].lower()] = {
            "active": active,
            "slots": count,
            "inactive": count - active,
        }
    return out


def slot_count(role: str) -> int:
    return ADMIN_SLOT_COUNT if role == ADMIN_ROLE else MODERATOR_SLOT_COUNT


def gate_login(username: str, email: str, access_code: Optional[str]) -> Optional[GateResult]:
    """Gerbang login untuk akun staff.

    Dipanggil **setelah** password benar, dengan username/email yang tersimpan
    di database (bukan yang diketik) supaya tidak bisa dilewat dengan mengubah
    besar/kecil huruf. Return ``None`` bila boleh login.
    """
    reg = registry()

    cred = reg.find(username, email)
    if cred is not None:
        if not access_code:
            return GateResult(
                "CODE_REQUIRED",
                f"Akun {cred.label} butuh code akses. "
                "Lengkapi username, email, password, dan code akses untuk masuk.",
            )
        if not cred.verify_access_code(access_code):
            return GateResult(
                "CODE_INVALID",
                "Code akses tidak sesuai. Nilai harus sama persis (besar/kecil huruf, "
                "spasi, dan karakter dihitung).",
            )
        return None

    slot = reg.find_slot(username, email)
    if slot is not None:
        return GateResult(
            "SLOT_INCOMPLETE",
            f"Kredensial {slot.label} belum lengkap ({slot.reason}). "
            "Akun ini tidak bisa login sampai username, email, password, dan code akses diisi semua.",
        )

    return None
