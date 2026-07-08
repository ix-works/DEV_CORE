"""Veri-çıkarma / PII guard — ADR 0011 (KVKK / hassas veri koruması).

YALNIZCA QA/PRD tier'larında aktiftir (kullanıcı kararı 2026-06-02). DEV muaftır.

Amaç: canlı (QA/PRD) sistemlerden kişisel/hassas veri (müşteri, çalışan, banka, vergi no)
okumayı açık onay (acknowledge_risk + affirmative kelime) olmadan engellemek.

Bu guard bir veri-okuma aracı (örn. ileride eklenecek adt_table_read) tarafından çağrılır.
Şu an MCP'de doğrudan tablo-verisi çekme aracı yok; guard hazır bekler (ADR 0011).

Referans: governance/decisions/0011-veri-cikarma-pii-guard.md
"""
from __future__ import annotations

import re

from mcp_servers.sap_adt.guardrails import GuardrailViolation

# Açık yetki için kabul edilen kelimeler (muğlak "dene/çek" YETMEZ — sc4sap deseni).
_AFFIRMATIVE = {"yes", "approve", "approved", "proceed", "confirm", "confirmed",
                "onay", "onaylıyorum", "evet", "kabul"}

# Hassas tablo/alan desenleri (kademe: minimal). Genişletilebilir.
_SENSITIVE_TABLE = re.compile(
    r"^(KNA1|KNB1|KNVK|LFA1|LFB1|ADRC|ADR6|ADCP|"          # iş ortağı / adres
    r"BUT0\w*|BUT1\w*|BP\w*|"                              # business partner
    r"PA\d{4}|HRP\d+|PB\w*|T5\w*|"                          # HR / bordro
    r"PAYR|REGUH|REGUP|BNKA|TIBAN|"                         # ödeme / banka
    r"BSEG|BKPF|ACDOCA|VBAK|VBAP|LIKP|LIPS|VBRK|VBRP|"      # korumalı iş verisi (standard kademesi)
    r"DFKKBPTAXNUM|.*TAXNUM.*|.*STCD\d*.*|.*TCKN.*|.*VKN.*"  # vergi no / TCKN / IBAN
    r")$",
    re.IGNORECASE,
)
_SENSITIVE_FIELD = re.compile(
    r"(STCD\d*|TAXNUM|TCKN|VKN|IBAN|BANKN|KTOKD|SMTP_ADDR|TELF\d*|"
    r"GBDAT|GESCH|NACHN|VORNA|NAME[12]?|STRAS|PSTLZ)",
    re.IGNORECASE,
)


def _is_affirmative(text: str | None) -> bool:
    if not text:
        return False
    return text.strip().lower() in _AFFIRMATIVE


def is_sensitive_target(table: str | None, fields: list[str] | None = None) -> bool:
    """Hedef tablo veya alanlar hassas mı?"""
    if table and _SENSITIVE_TABLE.match(table.strip()):
        return True
    for f in (fields or []):
        if f and _SENSITIVE_FIELD.search(f):
            return True
    return False


def require_data_access(
    tier: str,
    table: str | None,
    *,
    fields: list[str] | None = None,
    acknowledge_risk: bool = False,
    approval_text: str | None = None,
) -> None:
    """ADR 0011: QA/PRD'de hassas veri okuma açık onay ister; DEV muaf.

    Args:
        tier: Aktif tier (DEV/QA/PRD) — mcp_servers.sap_adt._conn.get_active_tier().
        table: Okunacak tablo adı.
        fields: Okunacak alanlar (opsiyonel — alan-seviyesi hassasiyet için).
        acknowledge_risk: Çağıran açık risk-kabulü bayrağı.
        approval_text: Kullanıcının onay metni — affirmative kelime içermeli.

    Raises:
        GuardrailViolation: QA/PRD'de hassas hedef + yetersiz onay.
    """
    t = (tier or "DEV").strip().upper()
    if t == "DEV":
        return  # DEV muaf (kullanıcı kararı)

    if not is_sensitive_target(table, fields):
        return  # hassas değilse serbest (QA/PRD'de bile)

    if acknowledge_risk and _is_affirmative(approval_text):
        return  # açık onay verildi

    raise GuardrailViolation(
        "ADR_0011_PII",
        f"Hassas veri okuma reddedildi (tier={t}, tablo={table}). "
        f"KVKK: QA/PRD'de hassas tablo/alan okumak için acknowledge_risk=True + "
        f"açık onay kelimesi ('onay'/'approve'/'proceed') gerekir. "
        f"Muğlak ifade ('dene', 'çek') yetmez.",
        tier=t, table=table,
    )
