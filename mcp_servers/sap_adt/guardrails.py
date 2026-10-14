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
# `\Z` (`$` DEĞİL): Python `$` sondaki TEK `\n`'in önünde de eşleşir ⇒ "ZFOO\n" kabul
# ediliyordu (Q363②, 2026-10-12). Kabul listesi tam-dize olmalı.
_CUSTOMER_PREFIX = re.compile(r"^[ZY][A-Z0-9_]*\Z", re.IGNORECASE)
# Lock objeleri (ENQU) ZORUNLU E-prefix alır (E + customer namespace, örn. EZSD000_X) —
# bu da MEŞRU customer-namespace'tir, standart obje DEĞİL (SAP konvansiyonu, ADR 0005-A istisnası).
_LOCK_TYPES = {"enqu", "lock", "lockobject", "lockobjects"}
_LOCK_PREFIX = re.compile(r"^E[ZY][A-Z0-9_]*\Z", re.IGNORECASE)


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

    ⚠ FAIL-CLOSED (2026-08-01 KAYIT-1): tier None/boş/UNKNOWN ise DEV VARSAYILMAZ —
    reddedilir. Eski `(tier or "DEV")` İKİNCİ bir fail-open katmanıydı: _conn
    fail-closed'a çevrilse bile buradaki varsayılan korumayı yeniden kapatırdı.
    """
    t = (tier or "").strip().upper() or "UNKNOWN"
    if t == "UNKNOWN":
        raise GuardrailViolation(
            "ADR_0010_TIER",
            f"{what} reddedildi — aktif sistemin tier'ı ÇÖZÜLEMEDİ (fail-closed). "
            f"Bilinmeyen tier DEV sayılmaz (PRD'de olup DEV sanma riski). Düzelt: "
            f".conn_adt'ye 'ADT_SAP_TIER=DEV|QA|PRD' satırını ekle (TAM anahtar — "
            f"'ADT_SAP_TIER_OLD=...' sayılmaz) ya da scripts/switch_tier.py ile geç. "
            f"Salt-okuma serbesttir.",
            tier=t,
        )
    if t not in _WRITABLE_TIERS:
        raise GuardrailViolation(
            "ADR_0010_TIER",
            f"{what} reddedildi — aktif sistem tier={t} (salt-okunur). "
            f"Mutasyon (create/push/activate/delete) yalnızca DEV'de serbest. "
            f"scripts/switch_tier.py DEV ile geçiş yap veya .conn_adt tier'ını doğrula.",
            tier=t,
        )


# ── Q369④ (2026-10-12): MCP araç SINIFLANDIRMASI — tamlık sözleşmesi ─────────────────────
# Her MCP aracı ya YAZMA-KORUMALIDIR (gövdesi `require_writable_tier` çağırır — AST ile
# ölçülür) ya da AŞAĞIDAKİ açık salt-okur listesindedir. İkisinde de olmayan araç
# SINIFLANDIRILMAMIŞTIR → `tests/fixtures/mcp_arac_sinifi` FAIL verir. Yeni araç ekleyen
# bu listeye (gerekçesiyle) ekler ya da tier kapısını koyar; ikisi birden de olabilir
# (ör. `adt_syntax_check`: bugün salt-okur checkrun, kapı bilinçli olarak korundu).
# ⛔ Bu liste `tools/list` gizlemesi YAPMAZ (tier'a göre gizleme bilinçli olarak YOK).
SALT_OKUR_ARACLAR = frozenset({
    "ping",                     # bağlantı yoklaması
    "adt_get",                  # GET (kaynak/metadata)
    "adt_msgclass_read",        # GET
    "adt_search_objects",       # GET arama
    "adt_transport_list",       # GET liste
    "adt_where_used",           # usageReferences sorgusu (araç docstring: SAP'ye YAZMAZ)
    "adt_atc_check",            # ATC koşusu: kaynak değişmez (sunucu yan kaydı ÖLÇÜLMEDİ)
    "adt_package_contents",     # GET
    "adt_table_read",           # datapreview (SELECT) — veri guard'ı ayrı
    "adt_sql_query",            # datapreview (SELECT) — veri guard'ı ayrı
    "adt_dump_list",            # GET
    "adt_dump_read",            # GET
    "adt_inactive_objects",     # GET worklist
    "adt_enhancements",         # GET
    "adt_enhancement_read",     # GET
    "adt_enhancement_options",  # GET
    "adt_feature_probe",        # GET
    "adt_grep_source",          # GET
    "adt_impact_analysis",      # GET
    "adt_lock_check",           # kilit DURUMU sorgusu (is_object_locked)
    "adt_get_method",           # Q363① GET + metinsel çıkarım
    "adt_revisions",            # Q363① GET versions feed
    "adt_pretty_print",         # Q363① biçimleme servisi (canlı ölçüm: obje değişmedi)
})


# =============================================================================
# Q369⑤ (2026-10-12) — YARATMA ANI ADLANDIRMA UYARISI (yalnız UYARI; GATE DEĞİL)
# Kaynak: `standards/01-naming.md` §4.4.5 Data Dictionary tablosu — nesne öneki adın
# BAŞ ve SON parçası dışında bir `_<ÖNEK>_` parçası olarak geçer (`ZSD001_T_DESC`,
# `ZFI001_CLC_V_SIZE`). Yalnız DDIC'in beş tipi kapsanır; diğer tiplerin adlandırması
# paket `.rules.md` regex'leriyle (`check_package_naming`) dosya düzeyinde ölçülür.
# FP ölçümü (2026-10-12, bir tüketici projenin kaynak korpusu, salt-okur; yeniden üretim:
# `tests/fixtures/adlandirma_uyarisi/run.py --korpus <SOURCE_ROOT>`): 184 mevcut DDIC adında
# (tablo 18 · yapı 15 · veri öğesi 93 · alan 58) uyarı 0. Sınırlar: korpus aynı standartla
# üretilmiştir (seçim yanlılığı) · tablo tipi korpusta dosya olarak YOK ⇒ TT ölçülmedi ·
# gerçek ihlal yakalama oranı (recall) korpusta ihlal olmadığı için ÖLÇÜLEMEDİ (fixture
# vektörleriyle sınanır).
# Kapsam dışı (None döner, uyarı YOK): ad alanlı (`/NS/`) adlar · `ZZ`/`YY` ile başlayan
# append yapıları · tanınmayan tip.
# =============================================================================
_ADLANDIRMA_ONEKLERI = {
    "table": ("T", "A"),
    "structure": ("S",),
    "dataelement": ("E",),
    "domain": ("D",),
    "tabletype": ("TT",),
}
_ADLANDIRMA_ESANLAM = {
    "tabl": "table", "dtel": "dataelement", "doma": "domain", "ttyp": "tabletype",
    "data_element": "dataelement", "table_type": "tabletype", "stru": "structure",
}
_ADLANDIRMA_ORNEK = {
    "table": "ZSD001_T_<AD>", "structure": "ZSD001_S_<AD>", "dataelement": "ZSD001_E_<AD>",
    "domain": "ZSD001_D_<AD>", "tabletype": "ZSD001_TT_<AD>",
}


def adlandirma_uyarisi(name: str, object_type: str) -> str | None:
    """DDIC yaratımında ad standarda uymuyorsa UYARI metni; uyuyorsa/kapsam dışıysa None.

    ⛔ Hiçbir durumda istisna atmaz ve yaratımı ENGELLEMEZ (Q369⑤: yalnız uyarı).
    """
    try:
        tip = (object_type or "").strip().lower()
        tip = _ADLANDIRMA_ESANLAM.get(tip, tip)
        izinli = _ADLANDIRMA_ONEKLERI.get(tip)
        ad = (name or "").strip().upper()
        if not izinli or not ad or "/" in ad or ad[:2] in ("ZZ", "YY") or ad[0] not in "ZY":
            return None
        parcalar = ad.split("_")
        if set(parcalar[1:-1]) & set(izinli):
            return None
        return ("ADLANDIRMA UYARISI (yalnız uyarı — yaratım ENGELLENMEDİ): '%s' (%s) "
                "standards/01-naming §4.4.5 nesne önekini taşımıyor: beklenen %s (örnek %s). "
                "Ad paket .rules.md'sinde bilinçli bir istisnaysa yok say."
                % (ad, tip, " ya da ".join("_%s_" % p for p in izinli), _ADLANDIRMA_ORNEK[tip]))
    except Exception:
        return None
