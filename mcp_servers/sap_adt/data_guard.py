"""Veri-çıkarma / PII guard — ADR 0011 (KVKK / hassas veri koruması).

YALNIZCA QA/PRD tier'larında aktiftir (kullanıcı kararı 2026-06-02). DEV muaftır.

Amaç: canlı (QA/PRD) sistemlerden kişisel/hassas veri (müşteri, çalışan, banka, vergi no)
okumayı açık onay (acknowledge_risk + affirmative kelime) olmadan engellemek.

Çağıranlar (2026-08-01 itibarıyla CANLI — "guard hazır bekliyor" DEĞİL):
`adt_table_read` ve `adt_sql_query` (mcp_servers/sap_adt/tools/query.py).

⚠ Bu modülün eski docstring'i "şu an MCP'de doğrudan tablo-verisi çekme aracı yok;
guard hazır bekler" diyordu — araçlar 2026-07-12'de eklendiği hâlde metin güncellenmedi.
Bakımcı, guard'ı ÖLÜ kod sanarak inceler; oysa üretimde koşuyordu (bkz. F0 dersi).

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


# ── Released CDS / view katmanı (2026-08-01 KAYIT-K1c) ───────────────────────────
# Tablo-adı tabanlı desen released CDS'i GÖRMÜYORDU: `I_Customer`, `I_BusinessPartner`,
# `V_KNA1` aynı kişisel veriyi taşır ama hiçbiri `KNA1` gibi görünmez. Üstelik projenin
# KENDİ standardı ("released CDS kullan", clean-core) kullanıcıyı tam oraya yönlendirir →
# guard'ın kör noktası, tavsiye edilen yolun ta kendisiydi.
# İki ek yol:
#   (1) semantik CDS adları: ayraçsız-birleştirilmiş adda kavram kelimesi aranır
#       ("I_BusinessPartner" -> "IBUSINESSPARTNER" içinde "BUSINESSPARTNER").
#   (2) sarmalayıcı görünümler: ad `_`/`/` ile parçalanır, HER parça tablo desenine
#       sokulur ("V_KNA1" -> ["V","KNA1"] -> KNA1 hassas).
_SENSITIVE_CDS = re.compile(
    r"(BUSINESSPARTNER|BUSPARTNER|CUSTOMER|SUPPLIER|VENDOR|EMPLOYEE|"
    r"WORKAGREEMENT|PAYROLL|BANKDETAIL|BANKACCOUNT|TAXNUMBER|PERSONALDATA|"
    r"CONTACTPERSON|ADDRESS)",
    re.IGNORECASE,
)

# ── Tablo-ifadesi NORMALİZASYONU (2026-08-01 KAYIT-K1a) ──────────────────────────
# Guard eskiden ÇIPLAK tablo adı bekliyordu: `_SENSITIVE_TABLE.match("KNA1 AS K")` False
# döner (regex `^...$` çapalı) → takma ad yazan çağrı guard'ı ATLIYORDU. Vaka-yaması
# (" AS " ayır) yetmez: `JOIN`, virgüllü liste, şema öneki ve alt-sorgu yine kaçar.
# Bu yüzden hassaslık kontrolü ARTIK ham metne değil, NORMALİZE EDİLMİŞ ADAY KÜMESİNE
# uygulanır. Kardeş `adt_sql_query` zaten FROM/JOIN çıkarımı yapıyordu — o çözüm buraya
# TAŞINDI (tek kaynak); iki tool'un ayrışması bu sınıfın kökeniydi.
_IDENT = re.compile(r"^[A-Za-z_/][A-Za-z0-9_/]*$")
_LITERAL = re.compile(r"'[^']*'")
_FROM_JOIN = re.compile(r"\b(?:FROM|JOIN)\s+([^\s,()]+)", re.IGNORECASE)
# Tablo-ifadesinin BİTTİĞİ yer: ilk SQL anahtar kelimesi.
_CLAUSE = re.compile(
    r"\b(?:SELECT|WITH|FROM|JOIN|INNER|LEFT|RIGHT|OUTER|CROSS|ON|WHERE|GROUP|ORDER|"
    r"HAVING|UNION|INTO|UP|FIELDS|CLIENT)\b",
    re.IGNORECASE,
)
_SELECT_LIST = re.compile(r"\bSELECT\b(.*?)\bFROM\b", re.IGNORECASE | re.DOTALL)
_NOISE = {"SELECT", "WITH", "DISTINCT", "SINGLE", "ALL"}


def _norm_name(token: str) -> str:
    """Tek bir tablo-token'ını normalize et: şema öneki, CTE '+', parantez, kasa."""
    t = (token or "").strip().strip("()").strip()
    t = t.split(".")[-1]          # şema/DB öneki: SAPABAP1.KNA1 -> KNA1
    t = t.lstrip("+")             # OpenSQL CTE: +cte -> cte
    return t.upper() if _IDENT.match(t) else ""


def table_candidates(expr: str | None) -> set[str]:
    """Tablo İFADESİNDEN veya tam SELECT'ten normalize edilmiş tablo adları.

    Hem `"KNA1 AS K"` (adt_table_read'in `table` parametresi) hem
    `"SELECT ... FROM a JOIN b"` (adt_sql_query'nin sorgusu) desteklenir; ikisi de
    AYNI kümeyi üretir → iki tool'un guard'ı ayrışamaz.
    """
    if not expr:
        return set()
    text = _LITERAL.sub("''", expr).replace('"', " ").replace("`", " ")
    adaylar: set[str] = set()
    # (1) SQL bağlamı — FROM/JOIN hedefleri (alt-sorgu ve UNION dahil).
    for ham in _FROM_JOIN.findall(text):
        n = _norm_name(ham)
        if n and n not in _NOISE:
            adaylar.add(n)
    # (2) Tablo-ifadesi bağlamı — ilk SQL anahtar kelimesine kadarki kısım, virgülle
    #     ayrılmış her parçanın İLK token'ı ("KNA1 AS K", "kna1 k", "T000 AS T").
    bas = _CLAUSE.split(text)[0]
    for parca in bas.split(","):
        tok = parca.strip().split()
        if tok:
            n = _norm_name(tok[0])
            if n and n not in _NOISE:
                adaylar.add(n)
    return adaylar


def select_fields(sql: str | None) -> list[str]:
    """Tam SELECT'in alan listesini çıkar (alan-seviyesi guard'ı besler).

    `*` / aggregate → alan iddiası YOK (boş liste); tablo-seviyesi kontrol devrededir.
    """
    out: list[str] = []
    for blok in _SELECT_LIST.findall(_LITERAL.sub("''", sql or "")):
        for parca in blok.split(","):
            p = parca.strip()
            if not p or "*" in p:
                continue
            p = re.sub(r"^\s*(?:DISTINCT|ALL|SINGLE)\s+", "", p, flags=re.IGNORECASE)
            p = re.sub(r"^\w+\s*\(", "", p).rstrip(")")          # COUNT( x ) -> x
            p = re.split(r"\s+", p.strip())[0]                    # "x AS y" -> x
            p = p.split("~")[-1].split(".")[-1]                   # k~stcd1 -> stcd1
            if _IDENT.match(p) and p.upper() not in _NOISE:
                out.append(p.upper())
    return out


def _ad_hassas_mi(ad: str) -> bool:
    """Tek bir normalize ad hassas mı? (tablo · released CDS · sarmalayıcı görünüm)"""
    n = ad.upper()
    if _SENSITIVE_TABLE.match(n):
        return True
    if _SENSITIVE_CDS.search(n.replace("_", "")):
        return True
    for seg in re.split(r"[_/]", n):                              # V_KNA1 / ZV_LFA1_COPY
        if seg and _SENSITIVE_TABLE.match(seg):
            return True
    return False


def _is_affirmative(text: str | None) -> bool:
    if not text:
        return False
    return text.strip().lower() in _AFFIRMATIVE


def sensitive_matches(table: str | None, fields: list[str] | None = None) -> list[str]:
    """Hangi hedefler hassas? (boş liste = serbest) — hata mesajı bunu gösterir."""
    hit = sorted(ad for ad in table_candidates(table) if _ad_hassas_mi(ad))
    hit += sorted({str(f).upper() for f in (fields or [])
                   if f and _SENSITIVE_FIELD.search(str(f))})
    return hit


def is_sensitive_target(table: str | None, fields: list[str] | None = None) -> bool:
    """Hedef tablo/görünüm veya alanlar hassas mı? (normalize edilmiş ifadeye bakar)"""
    return bool(sensitive_matches(table, fields))


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

    ⚠ FAIL-CLOSED (2026-08-01 KAYIT-1): tier None/boş/UNKNOWN ise DEV muafiyeti
    UYGULANMAZ. Bilinmeyen tier PRD olabilir; PII muafiyeti "belki DEV'dir"e
    dayandırılamaz. Hassas-OLMAYAN okuma UNKNOWN'da da serbest kalır (salt-okuma
    gereksiz kısıtlanmaz) — yalnız hassas hedef açık onay ister.

    ⚠ NORMALİZE HEDEF (2026-08-01 KAYIT-K1a): `table` çıplak ad OLMAK ZORUNDA DEĞİL —
    takma adlı ifade ("KNA1 AS K"), JOIN'li ifade, virgüllü liste, şema öneki ve tam
    SELECT metni de kabul edilir; hepsinden aday tablo kümesi çıkarılır. Eskiden
    "KNA1 AS K" guard'ı sessizce ATLIYORDU (kontrol grubu: düz "KNA1" bloklanıyordu).
    """
    t = (tier or "").strip().upper() or "UNKNOWN"
    if t == "DEV":
        return  # DEV muaf (kullanıcı kararı)

    eslesme = sensitive_matches(table, fields)
    if not eslesme:
        return  # hassas değilse serbest (QA/PRD'de bile)

    if acknowledge_risk and _is_affirmative(approval_text):
        return  # açık onay verildi

    raise GuardrailViolation(
        "ADR_0011_PII",
        f"Hassas veri okuma reddedildi (tier={t}, hedef={table}). "
        f"Hassas bulunan: {', '.join(eslesme)}. "
        f"KVKK: DEV-DIŞI (QA/PRD ya da ÇÖZÜLEMEYEN tier) hassas tablo/görünüm/alan okumak "
        f"için acknowledge_risk=True + "
        f"açık onay kelimesi ('onay'/'approve'/'proceed') gerekir. "
        f"Muğlak ifade ('dene', 'çek') yetmez.",
        tier=t, table=table, matched=eslesme,
    )
