#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""switch_tier.py — aktif SAP sistemini değiştir. ADR 0010.

Slot dosyaları SİSTEM ADI ile anahtarlanır: conn/<SISTEM_ADI>.env
(ör. conn/TD_S4HANA_DEV.env). Bu sayede aynı tier'ı paylaşan birden çok
sistem (TD_S4HANA_QA + TD_ECC_QA gibi) yan yana durabilir. Seçilen slot
proje kökündeki .conn_adt üzerine kopyalanır; readonly-guard için tier
her zaman slot dosyasının ADT_SAP_TIER alanından okunur.

Kullanım — sistem adı VEYA (tek ise) tier ile:
    python scripts/switch_tier.py TD_S4HANA_DEV
    python scripts/switch_tier.py TD_S4HANA_QA
    python scripts/switch_tier.py TD_ECC_QA
    python scripts/switch_tier.py DEV     # tier o tier'da tek sistem varsa çözülür
    python scripts/switch_tier.py QA      # >1 QA sistemi varsa: belirsiz → sistem adı iste

QA/PRD tier'a geçişte yüksek-sesli uyarı verir (salt-okunur, mutasyon reddedilir).
Geçişten sonra MCP server'ı yeniden başlat.
"""
from __future__ import annotations

import io
import shutil
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[1]
CONN_DIR = REPO / "conn"
ACTIVE = REPO / ".conn_adt"

_TIER_ALIASES = {
    "DEV": "DEV", "DEVELOPMENT": "DEV", "SANDBOX": "DEV",
    "QA": "QA", "QAS": "QA", "QUALITY": "QA", "TEST": "QA",
    "PRD": "PRD", "PROD": "PRD", "PRODUCTION": "PRD",
}


def _field_of_file(p: Path, key: str) -> str | None:
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith(key) and "=" in s:
            return s.split("=", 1)[1].strip()
    return None


def _tier_of_file(p: Path) -> str | None:
    v = _field_of_file(p, "ADT_SAP_TIER")
    return v.upper() if v else None


def _name_of_file(p: Path) -> str:
    """Slot'un sistem adı: ADT_SAP_SYSTEM_NAME, yoksa dosya adı (stem)."""
    return (_field_of_file(p, "ADT_SAP_SYSTEM_NAME") or p.stem).strip()


def _registry() -> list[tuple[str, Path, str | None]]:
    """conn/*.env slotlarını listele → [(SISTEM_ADI_UPPER, path, tier), ...]."""
    out = []
    for env in sorted(CONN_DIR.glob("*.env")):
        out.append((_name_of_file(env).upper(), env, _tier_of_file(env)))
    return out


def _resolve(raw: str) -> tuple[Path, str] | None:
    """Argümanı (slot_path, tier)'a çöz. Belirsiz/eksikse None döner (çağıran raporlar)."""
    key = raw.strip().upper()
    reg = _registry()
    # 1) Birebir sistem adı eşleşmesi
    for name, path, tier in reg:
        if name == key:
            return (path, tier or "DEV")
    # 2) Tier kısaltması → o tier'daki sistemler
    tier_key = _TIER_ALIASES.get(key)
    if tier_key:
        hits = [(name, path, tier) for name, path, tier in reg if tier == tier_key]
        if len(hits) == 1:
            return (hits[0][1], tier_key)
        if len(hits) > 1:
            names = ", ".join(h[0] for h in hits)
            print(f"[HATA] tier={tier_key} altında birden çok sistem var: {names}")
            print("       Lütfen tier yerine SİSTEM ADI ile geç.")
            return None
    return None


def _has_placeholder(p: Path) -> bool:
    """Yorum-dışı değer satırlarında doldurulmamış <...> kalıbı var mı?"""
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        if "<" in s.split("=", 1)[1]:
            return True
    return False


def _masked(p: Path) -> str:
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        k = line.split("=", 1)[0]
        if any(s in k.lower() for s in ("pass", "pwd", "secret", "token")):
            out.append(k + "=***")
        elif line.strip():
            out.append(line)
    return "\n".join(out)


def _print_available() -> None:
    reg = _registry()
    if not reg:
        print("       (conn/ altında slot yok — conn/<SISTEM_ADI>.env oluştur.)")
        return
    print("       Mevcut sistemler:")
    for name, _path, tier in reg:
        print(f"         - {name}  (tier={tier})")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 1
    CONN_DIR.mkdir(exist_ok=True)

    resolved = _resolve(argv[1])
    if not resolved:
        print(f"[HATA] '{argv[1]}' bir sisteme çözülemedi.")
        _print_available()
        return 2
    src, tier = resolved

    # Placeholder güvenliği: doldurulmamış değer alanı varsa geçme.
    if _has_placeholder(src):
        print(f"[HATA] {src.relative_to(REPO)} hâlâ <...> placeholder değeri içeriyor. Önce bağlantı bilgilerini doldur.")
        return 3

    # Yedekle + kopyala
    if ACTIVE.exists():
        shutil.copy2(ACTIVE, CONN_DIR / ".conn_adt.bak")
    shutil.copy2(src, ACTIVE)

    sys_name = _name_of_file(ACTIVE)
    print(f"[OK] Aktif sistem → {sys_name}  tier={tier}  ({src.relative_to(REPO)} → .conn_adt)")
    print("-" * 60)
    print(_masked(ACTIVE))
    print("-" * 60)
    if tier in ("QA", "PRD"):
        print(f"⛔ DİKKAT: tier={tier} SALT-OKUNUR. MCP guard mutasyonu reddeder")
        print("   (create/push/activate/delete). Sadece okuma/analiz/teşhis.")
    print("ℹ MCP server'ı yeniden başlat (bağlantı cache'i yeni sisteme bağlansın).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
