#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sap_doctor.py — çok-katmanlı SAP bağlantı/ortam tanısı. (#5, ADR 0010)

Session protokolü adım-1/2'yi tek komuta indirir. Her katman izole; biri kırılsa
diğerleri çalışır. "Bağlantı bozuk mu, VPN mi, auth mı, TR-login mi?" sorusunu
tek bakışta yanıtlar.

Katmanlar:
  1. .conn_adt var + zorunlu alanlar dolu
  2. Aktif tier (DEV/QA/PRD) — ADR 0010
  3. Master language TR mi (ADR 0005-D — Z obje TR zorunlu)
  4. MCP server modülleri import edilebiliyor mu
  5. SAP bağlantı + auth (canlı probe — VPN/kimlik)
  6. Aktif paket erişilebilir mi (probe obje)

Kullanım:
    python scripts/sap_doctor.py
    python scripts/sap_doctor.py --probe ZSD015_I_VOYAGE --type ddls --package ZSD015_CLC
"""
from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Hem scripts/ (sap_client, sap_adt_lib) hem repo kökü (mcp_servers paketi) path'te olsun.
_REPO = Path(__file__).resolve().parents[1]
for _p in (str(_REPO), str(_REPO / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OK, FAIL, WARN, INFO = "[OK]  ", "[FAIL]", "[WARN]", "[bilgi]"
_REQUIRED = ("ADT_SAP_URL", "ADT_SAP_USER", "ADT_SAP_PASSWORD", "ADT_SAP_CLIENT")


def _conn_path() -> Path | None:
    try:
        from sap_adt_lib import get_conn_path  # type: ignore
        p = get_conn_path()
        return p if p and p.exists() else None
    except Exception:
        p = Path.cwd() / ".conn_adt"
        return p if p.exists() else None


def _parse_conn(p: Path) -> dict:
    d = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if "=" in s and not s.startswith("#"):
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def run(probe: str, ptype: str, package: str) -> int:
    results: list[tuple[str, str]] = []

    # 1. .conn_adt + alanlar
    cp = _conn_path()
    conn = {}
    if not cp:
        results.append((FAIL, ".conn_adt bulunamadı"))
    else:
        conn = _parse_conn(cp)
        missing = [k for k in _REQUIRED if not conn.get(k)]
        if missing:
            results.append((FAIL, f".conn_adt eksik alan: {', '.join(missing)}"))
        else:
            results.append((OK, f".conn_adt tamam ({cp})  URL={conn.get('ADT_SAP_URL','?')} client={conn.get('ADT_SAP_CLIENT','?')} user={conn.get('ADT_SAP_USER','?')}"))

    # 2. Tier
    try:
        from mcp_servers.sap_adt._conn import get_active_tier  # type: ignore
        tier = get_active_tier()
    except Exception:
        tier = (conn.get("ADT_SAP_TIER") or "DEV").upper()
    tag = OK if tier == "DEV" else WARN
    note = "mutasyon serbest" if tier == "DEV" else "SALT-OKUNUR (mutasyon reddedilir)"
    results.append((tag, f"Aktif tier = {tier} — {note}"))

    # 3. Master language TR
    lang = (conn.get("ADT_SAP_LANGUAGE") or "").upper()
    if lang == "TR":
        results.append((OK, "Master language = TR (ADR 0005-D ✓)"))
    else:
        results.append((WARN, f"Master language = {lang or '?'} — Z obje yaratımı TR olmalı (ADR 0005-D)"))

    # 4. MCP server import
    try:
        import mcp_servers.sap_adt.server  # noqa: F401
        from mcp_servers.sap_adt.tools import atom, composite, query  # noqa: F401
        results.append((OK, "MCP server modülleri import edildi (server + atom/composite/query)"))
    except Exception as exc:
        results.append((FAIL, f"MCP import hatası: {exc}"))

    # 5+6. Canlı SAP probe (VPN/auth/paket)
    try:
        from sap_client import SAPClient  # type: ignore
        from sap_adt_lib import SAPObjectNotFoundError  # type: ignore
        client = SAPClient()
        try:
            with contextlib.redirect_stdout(io.StringIO()):  # SAPClient chatter'ını yut
                md = client.get_object_metadata(probe, object_type=ptype)
            md_text = md if isinstance(md, str) else str(md or "")
        except SAPObjectNotFoundError:
            md_text = ""  # bağlantı/auth OK, sadece obje yok
        results.append((OK, f"SAP bağlantı + auth OK (VPN ✓, kimlik ✓)"))

        # 6. Paket erişimi (probe metadata paketi içeriyor mu)
        if md_text and package and package.lower() in md_text.lower():
            results.append((OK, f"Aktif paket erişilebilir: {package} (probe {probe} bu pakette)"))
        elif md_text:
            results.append((WARN, f"Probe {probe} erişildi ama paket {package} metadata'da görünmedi (yine de bağlantı OK)"))
        else:
            results.append((WARN, f"Probe obje {probe} ({ptype}) bulunamadı — bağlantı OK ama obje yok/paket teyit edilemedi"))
    except Exception as exc:
        name = type(exc).__name__
        if "Auth" in name:
            results.append((FAIL, f"SAP auth başarısız: {exc}  → kullanıcı/şifre/client kontrol"))
        elif "Connection" in name:
            results.append((FAIL, f"SAP bağlantı başarısız: {exc}  → VPN açık mı?"))
        else:
            results.append((FAIL, f"SAP probe hatası ({name}): {exc}"))

    # Rapor
    print("=" * 64)
    print("SAP DOCTOR — bağlantı/ortam tanısı")
    print("=" * 64)
    for tag, msg in results:
        print(f"  {tag} {msg}")
    print("-" * 64)
    n_fail = sum(1 for t, _ in results if t == FAIL)
    n_warn = sum(1 for t, _ in results if t == WARN)
    if n_fail:
        print(f"SONUÇ: {n_fail} KRİTİK sorun, {n_warn} uyarı — SAP işlemine başlamadan düzelt (CLAUDE.md §6 STOP).")
        return 1
    if n_warn:
        print(f"SONUÇ: OK ({n_warn} uyarı) — devam edilebilir.")
        return 0
    print("SONUÇ: Tüm katmanlar OK — SAP işlemine hazır.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="SAP bağlantı/ortam tanısı")
    ap.add_argument("--probe", default="ZSD015_I_VOYAGE", help="Canlı test için obje adı")
    ap.add_argument("--type", default="ddls", help="Probe obje tipi (ddls/class/tabl...)")
    ap.add_argument("--package", default="ZSD015_CLC", help="Erişim teyidi için paket")
    args = ap.parse_args()
    return run(args.probe, args.type, args.package)


if __name__ == "__main__":
    raise SystemExit(main())
