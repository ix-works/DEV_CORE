"""Aktif bağlantı tier'ını okuma — ADR 0010 (tier-bazlı readonly guard).

`.conn_adt` içindeki `ADT_SAP_TIER` satırı sistemin tier'ını belirler:
  DEV → tüm mutasyon serbest
  QA  → salt-okunur (mutasyon reddedilir)
  PRD → salt-okunur (mutasyon reddedilir)

Kaynak önceliği: .conn_adt dosyası (otoriter) → os.environ (fallback) → DEV (fail-safe + uyarı).
Tier her çağrıda taze okunur (switch_tier.py ile değişim aynı oturumda görülebilir).

Referans: governance/decisions/0010-tier-bazli-readonly-guard.md
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger("sap-adt-mcp")

# Müşteri landscape'lerindeki standart-olmayan tier adları → kanonik eşleme (sc4sap deseni).
_TIER_ALIASES = {
    "DEVELOPMENT": "DEV", "DEV": "DEV", "SANDBOX": "DEV", "SBX": "DEV",
    "QUALITY": "QA", "QA": "QA", "QAS": "QA", "TEST": "QA",
    "INTEGRATION": "QA", "STAGING": "QA", "TRAINING": "QA",
    "PRODUCTION": "PRD", "PRD": "PRD", "PROD": "PRD", "P": "PRD",
}


def _normalize_tier(raw: str | None) -> str | None:
    if not raw:
        return None
    return _TIER_ALIASES.get(raw.strip().upper(), raw.strip().upper())


def get_active_tier() -> str:
    """Aktif sistemin tier'ını döndür (DEV/QA/PRD). Bulunamazsa DEV (uyarı loglar).

    Otoriter kaynak .conn_adt dosyasıdır; env değişkeni stale olabilir (dotenv override).
    """
    # 1) .conn_adt dosyası (otoriter)
    try:
        from sap_adt_lib import get_conn_path  # type: ignore
        p = get_conn_path()
        if p and p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s.startswith("ADT_SAP_TIER") and "=" in s:
                    t = _normalize_tier(s.split("=", 1)[1])
                    if t:
                        return t
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("tier: .conn_adt okunamadı (%s), env'e düşülüyor", exc)

    # 2) Ortam değişkeni (fallback)
    env_t = _normalize_tier(os.getenv("ADT_SAP_TIER"))
    if env_t:
        return env_t

    # 3) Fail-safe: DEV + görünür uyarı (mevcut/eski .conn_adt'ler kırılmasın diye)
    log.warning(
        "ADT_SAP_TIER tanımlı değil → DEV varsayıldı. "
        ".conn_adt'ye 'ADT_SAP_TIER=DEV' ekle veya scripts/switch_tier.py kullan."
    )
    return "DEV"


def _conn_value(key: str, default: str) -> str:
    """`.conn_adt`'den bir değeri oku (env fallback, sonra default)."""
    try:
        from sap_adt_lib import get_conn_path  # type: ignore
        p = get_conn_path()
        if p and p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s.startswith(key) and "=" in s:
                    v = s.split("=", 1)[1].strip()
                    if v:
                        return v
    except Exception:
        pass
    return os.getenv(key) or default


def get_atc_variant() -> str:
    """Sistemin ATC (Code Inspector) check variant'ı — .conn_adt ADT_ATC_VARIANT.

    Sisteme özgü standart variant (ör. ZZNDBS_ATC). Tanımlı değilse 'DEFAULT'.
    Hardcode YOK — her sistem kendi variant'ını .conn_adt'de belirler.
    """
    return _conn_value("ADT_ATC_VARIANT", "DEFAULT")


def write_mcp_binding_state(url: str | None = None, client: str | None = None) -> None:
    """MCP'nin bağlı/bağlanacağı sistemi `.claude/.mcp_active_system`'e yaz.

    statusline bunu `.conn_adt` ile kıyaslar: ayrışırsa (switch_tier yapıldı ama /mcp
    restart edilmedi) "MCP farklı sisteme bakıyor → /mcp" uyarısı gösterir.

    - Açılışta (server.main) parametresiz çağrılır → `.conn_adt`'den "intended binding"
      (taze server her zaman `.conn_adt`'ye bağlanır) → /mcp biter bitmez statusline güncel.
    - Canlı bağlanışta (ilk client) gerçek url/client geçilir → fiili host doğrulanır.

    best-effort: asla server açılışını/bağlanmayı kırmaz.
    """
    try:
        import json
        import os

        from sap_adt_lib import get_conn_path  # type: ignore

        conn = get_conn_path()
        if not conn:
            return
        root = conn.parent
        state = {
            "system": _conn_value("ADT_SAP_SYSTEM_NAME", "") or None,
            "url": url or _conn_value("ADT_SAP_URL", "") or None,
            "client": client or _conn_value("ADT_SAP_CLIENT", "") or None,
            "tier": get_active_tier(),
            "pid": os.getpid(),
        }
        out = root / ".claude" / ".mcp_active_system"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(state), encoding="utf-8")
    except Exception:  # pragma: no cover - state yazımı asla akışı kırmaz
        pass
