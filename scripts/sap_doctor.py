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
    python scripts/sap_doctor.py --probe ZSD001_I_VOYAGE --type ddls --package ZSD001_CLC
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
        # KAYIT-1: tier yoksa "DEV" varsayma — UNKNOWN (guard fail-closed reddeder).
        tier = (conn.get("ADT_SAP_TIER") or "UNKNOWN").upper()
    if tier == "DEV":
        tag, note = OK, "mutasyon serbest"
    elif tier in ("QA", "PRD"):
        tag, note = WARN, "SALT-OKUNUR (mutasyon reddedilir)"
    else:
        tag, note = FAIL, ("ÇÖZÜLEMEDİ → MUTASYON REDDEDİLİR (fail-closed). "
                           ".conn_adt'ye ADT_SAP_TIER=DEV|QA|PRD ekle")
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
    #
    # ⛔ 2026-09-03 — "DOĞRULAMA KOŞAMADI = DOĞRULANDI" sınıfının BU dosyadaki üyesi.
    #    Eski kod probe'u `redirect_stdout(StringIO())` ile çağırıp çıktıyı ATIYOR, dönen
    #    `None`'ı ise KOŞULSUZ "bağlantı + auth OK (VPN ✓, kimlik ✓)" sayıyordu.
    #    `sap_client.get_object_metadata` HER istisnayı yutup `None` döndürür (KASITLI
    #    sözleşme — sınıflandırma çağıranın işidir, bkz. `atom._bos_sonuc_sinifi`), bu yüzden
    #    aşağıdaki `except Connection*` dalı ÖLÜ KODdu: DNS'te çözülmeyen host'ta bile
    #    SONUÇ=OK basılıyordu. Ölçüldü 2026-09-03: İKİ ayrı projede — <PROJECT_A> (probe'suz) VE <PROJECT_B>
    #    (probe+paket dolu) — İKİSİ de sahte-OK verdi ⇒ proje kurulumuyla ilgisi yok.
    #    Bu, 2026-08-01 (atom/push/where_used/ATC/inactive/csrf/package_contents) ve
    #    2026-08-19 (`run_sql_query`) süpürgelerinin ATLADIĞI üye: her ikisi de MCP tool
    #    katmanını + `sap_adt_lib`'i taradı, `scripts/` altındaki bu CLI tanı aracını DEĞİL.
    #    FIX: alt katmanın log'u YUTULMAZ, kanonik üç-değerli sınıflandırıcıya verilir.
    #    ⚠ `sap_client.get_object_metadata` BİLEREK DEĞİŞTİRİLMEDİ — istisna-yutması iki
    #    fixture korpusunda (`dogrulama_kosamadi`, `veri_yetki_guardlari`) ÇİVİLİ.
    try:
        from sap_client import SAPClient  # type: ignore
        from sap_adt_lib import SAPObjectNotFoundError  # type: ignore
        # BAĞIMLILIKSIZ modül — `tools.atom` MCP SDK'sını cekiyor; SDK'sız ortamda
        # (CI) import patlar ve arac 'ag mi yetki mi' sorusuna 'probe hatasi' derdi.
        from mcp_servers.sap_adt._bos_sonuc import _bos_sonuc_sinifi  # type: ignore
        client = SAPClient()
        log_buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(log_buf):  # chatter YUTULMAZ — kanıt olarak tutulur
                md = client.get_object_metadata(probe, object_type=ptype)
            md_text = md if isinstance(md, str) else ""
        except SAPObjectNotFoundError:
            md_text = ""  # sunucuya ULAŞILDI, obje yok
        client_log = log_buf.getvalue()
        iz = " ".join(client_log.split())[:200]

        if md_text:
            # POZİTİF KANIT: canlı gövde okundu ⇒ ağ + kimlik ikisi de kanıtlı.
            results.append((OK, "SAP bağlantı + auth OK (VPN ✓, kimlik ✓) — canlı metadata okundu"))
        else:
            sinif = _bos_sonuc_sinifi(client_log)
            if sinif == "ulasilamadi":
                results.append((FAIL, f"SAP'ye ULAŞILAMADI (ağ/DNS/VPN) — bağlantı KANITLANMADI. "
                                      f"Bu 'OK' DEĞİLDİR; VPN açık mı? İz: {iz or '(log boş)'}"))
            elif sinif == "belirsiz":
                results.append((WARN, f"Sunucuya ulaşıldı ama probe 404-DIŞI hata döndü — kimlik/yetki "
                                      f"TEYİT EDİLMEDİ (401/403/500 olabilir). İz: {iz}"))
            else:  # "yok" → 404 alındı: TCP+TLS+HTTP+kimlik yolu çalıştı
                results.append((OK, "SAP bağlantı + auth OK (VPN ✓, kimlik ✓) — probe 404 (sunucuya ulaşıldı)"))

        # 6. Paket erişimi (probe metadata paketi içeriyor mu)
        if md_text and package and package.lower() in md_text.lower():
            results.append((OK, f"Aktif paket erişilebilir: {package} (probe {probe} bu pakette)"))
        elif md_text:
            results.append((WARN, f"Probe {probe} erişildi ama paket {package} metadata'da görünmedi (yine de bağlantı OK)"))
        elif sinif == "yok":
            results.append((WARN, f"Probe obje {probe} ({ptype}) bulunamadı — bağlantı OK ama obje yok/paket teyit edilemedi"))
        else:
            results.append((WARN, f"Paket erişimi ÖLÇÜLEMEDİ — probe okunamadı (yukarıdaki satır)"))
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
    ap.add_argument("--probe", default=None, help="Canlı test objesi (default: project.yaml doctor_probe_object)")
    ap.add_argument("--type", default="ddls", help="Probe obje tipi (ddls/class/tabl...)")
    ap.add_argument("--package", default=None, help="Erişim paketi (default: project.yaml active_package)")
    args = ap.parse_args()
    from utils.project_config import cfg as _cfg
    probe = args.probe or _cfg("doctor_probe_object")
    pkg = args.package or _cfg("active_package")
    if not probe or not pkg:
        print("UYARI: probe/paket config yok (project.yaml doctor_probe_object + active_package) — canli-probe adimi SINIRLI kosacak")
    return run(probe or "", args.type, pkg or "")


if __name__ == "__main__":
    raise SystemExit(main())
