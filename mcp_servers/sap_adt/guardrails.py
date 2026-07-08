"""ADR 0005 hardcoded guardrails — bypass-free.

Each guard raises GuardrailViolation with an ADR_0005_<cat> error code.
Tools call validate_* functions before issuing any HTTP request.

Reference: governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md
ADR:       governance/decisions/0007-sap-adt-mcp-server.md §Server-Side Guardrails

Implementation status:
- v1 (Task #4): Z/Y prefix check, transport non-empty, basic TR text presence
- v2 (Task #7): Full TR character validation, 4-label completeness, std object delete reject
"""
from __future__ import annotations

import re
from typing import Iterable


class GuardrailViolation(Exception):
    """Raised when an ADR 0005 rule is violated. Tool returns this to caller."""

    def __init__(self, code: str, message: str, **context):
        self.code = code
        self.context = context
        super().__init__(f"[{code}] {message}")

    def as_dict(self) -> dict:
        return {
            "ok": False,
            "error": "guardrail_violation",
            "code": self.code,
            "message": str(self),
            "context": self.context,
        }


# Customer namespace: Z or Y prefix
_CUSTOMER_PREFIX = re.compile(r"^[ZY][A-Z0-9_]*$", re.IGNORECASE)
# Lock objeleri (ENQU) ZORUNLU E-prefix alır (E + customer namespace, örn. EZSD000_X) —
# bu da MEŞRU customer-namespace'tir, standart obje DEĞİL (SAP konvansiyonu, ADR 0005-A istisnası).
_LOCK_TYPES = {"enqu", "lock", "lockobject", "lockobjects"}
_LOCK_PREFIX = re.compile(r"^E[ZY][A-Z0-9_]*$", re.IGNORECASE)


def _is_customer_namespace(name: str, object_type: str | None = None) -> bool:
    """Z/Y customer namespace mi? Lock objeleri (ENQU) için E+Z/Y de meşrudur."""
    if not name:
        return False
    if _CUSTOMER_PREFIX.match(name):
        return True
    if object_type and object_type.lower() in _LOCK_TYPES and _LOCK_PREFIX.match(name):
        return True  # lock objesi: E + Z/Y (örn. EZSD000_LOCK)
    return False


def require_customer_namespace(name: str, *, what: str = "object", object_type: str | None = None) -> None:
    """ADR 0005 §A: standart obje yaratma/değiştirme yasak.

    Customer namespace (Z/Y prefix; lock objeleri için E+Z/Y) zorunlu.
    """
    if not name:
        raise GuardrailViolation(
            "ADR_0005_A",
            f"{what} adı boş olamaz",
        )
    if not _is_customer_namespace(name, object_type):
        raise GuardrailViolation(
            "ADR_0005_A",
            f"Standart obje yaratma yasak — {what} '{name}' Z/Y (lock için E+Z/Y) ile başlamalı (customer namespace)",
            name=name,
        )


def require_transport(transport: str | None, *, what: str = "operation") -> None:
    """ADR 0005 §C: transport zorunlu, asla varsayma."""
    if not transport or not transport.strip():
        raise GuardrailViolation(
            "ADR_0005_C",
            f"{what} için transport zorunlu — list_user_transports ile aktif transportları sor ve kullanıcıya doğrulat",
        )


def require_tr_text(text: str | None, *, what: str = "label") -> None:
    """ADR 0005 §D: Z'li obje TR text zorunlu, boş bırakılamaz."""
    if not text or not text.strip():
        raise GuardrailViolation(
            "ADR_0005_D",
            f"TR text zorunlu — {what} boş bırakılamaz",
        )


def require_all_labels(labels: dict, expected: Iterable[str]) -> None:
    """ADR 0005 §D: DTEL 4 label (short/medium/long/heading) dolu zorunlu."""
    missing = [k for k in expected if not labels.get(k, "").strip()]
    if missing:
        raise GuardrailViolation(
            "ADR_0005_D",
            f"4 label zorunlu — eksik: {', '.join(missing)}",
            missing=missing,
        )


def reject_standard_delete(name: str, object_type: str | None = None) -> None:
    """ADR 0005 §A: standart obje delete yasak. Lock objeleri (ENQU) E+Z/Y meşru."""
    if not _is_customer_namespace(name or "", object_type):
        raise GuardrailViolation(
            "ADR_0005_A",
            f"Standart obje sil yasak — '{name}' Z/Y (lock için E+Z/Y) ile başlamıyor",
            name=name,
        )


# ADR 0010 — yalnızca DEV tier'da mutasyon serbest. QA/PRD salt-okunur.
_WRITABLE_TIERS = frozenset({"DEV"})


def require_writable_tier(tier: str | None, *, what: str = "mutasyon") -> None:
    """ADR 0010: create/push/activate/delete yalnızca DEV tier'da serbest.

    QA/PRD salt-okunur → yazma reddedilir. "Safety is not memory, it is code":
    tier .conn_adt'den okunur (mcp_servers.sap_adt._conn.get_active_tier), agent
    hatırlamasına bırakılmaz.
    """
    t = (tier or "DEV").strip().upper()
    if t not in _WRITABLE_TIERS:
        raise GuardrailViolation(
            "ADR_0010_TIER",
            f"{what} reddedildi — aktif sistem tier={t} (salt-okunur). "
            f"Mutasyon (create/push/activate/delete) yalnızca DEV'de serbest. "
            f"scripts/switch_tier.py DEV ile geçiş yap veya .conn_adt tier'ını doğrula.",
            tier=t,
        )
