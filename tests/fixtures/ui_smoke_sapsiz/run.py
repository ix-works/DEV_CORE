#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K7 — `ui-smoke` CI'da HIC kosmuyordu: SAP'siz sahte-sunucu korpusu.

=== KOK (kayit satir 18) ===
`helpers.selftest` disindaki her sey CANLI SAP + AYAKTA app istiyordu. Sonuc: aracin
en kritik davranisi — **LOCKOUT-SAFE on-dogrulama** — hic otomatik olculmuyordu.
Bu davranisin bozulmasi sessiz DEGIL, PAHALIdir: SAP'de 2 yanlis giris hesabi KILITLER.
"401'de DUR" korumasi kaybolursa playwright onlarca istek atar ve hesap kilitlenir
(olculmus vaka: "israrli popup + lrep 401 = hesap kilidi").

=== SEAM (SAP'siz olculebilen yuzey) ===
`read_creds()` + `verify_auth_once()` + `main()`in karar mantigi saf HTTP'dir. Sahte bir
`http.server` istenen durum kodunu doner; boylece 401/403/ulasilamaz dallari SAP'siz
kosulur. "playwright KOSTU MU" sorusu ise PATH'e konan sahte bir `npx` kabuguyla
olculur: kabuk bir IZ DOSYASI yazar ⇒ "kostu/kosmadi" TAHMIN degil OLCUM olur.
(⚠ `[DUR]` metnini gormek YETMEZ — mesaj basilip playwright yine de kosabilirdi.)

⚠ NE OLCULMEZ (durustluk): gercek UI5 etkilesimi, gercek SAP $metadata'si ve
   playwright'in KENDI dogrulugu. Onlar `B15` recetesindeki canli kosumun isidir.
   Bu korpus SARMALAYICININ karar mantigini civiler.

  P1 ⭐ AYIRT EDICI  401 -> `[DUR]` VE playwright KOSTURULMAZ (iz dosyasi YOK)
  P2 ⭐ POZ.KONTROL  200 -> `[ok] auth` VE playwright KOSAR (iz dosyasi VAR)
                    — P1 tek basina "hep reddeden" bir aracla da gecerdi
  P3               sunucu ulasilamaz -> `[DUR]` + playwright KOSTURULMAZ
  P4               403 -> 401 DEGIL -> devam eder (401 TEK kilit sinyalidir)
  N1 FP capasi     `.conn_adt` yok -> gurultulu hata + DENENEN KOK yazilir + npx YOK
  N2 FP capasi     `.conn_adt` var ama USER/PASSWORD eksik -> ayrik hata + npx YOK
  N3               gonderilen Basic-auth kimligi `.conn_adt`teki DEGERLERDIR
  N4 ⭐ SINIR       on-dogrulama TAM 1 istek atar (lockout-safe'in sayisal degismezi)
  M1..M3           fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/ui_smoke_sapsiz/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import base64
import http.server
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
ARAC = KOK / "scripts" / "ui-smoke" / "run_ui_smoke.py"

# Jenerik yer-tutucular (core PUBLIC repodur — gercek kimlik deseni YASAK).
KULLANICI, PAROLA = "TEST_USER", "gizli-Pärola-1"
CONN = (f"ADT_SAP_URL=https://ornek.gecerli:44300\nADT_SAP_USER={KULLANICI}\n"
        f"ADT_SAP_PASSWORD={PAROLA}\nADT_SAP_CLIENT=100\nADT_SAP_TIER=DEV\n")


class _Sunucu(http.server.BaseHTTPRequestHandler):
    durum = 200
    kayit: list = []

    def do_GET(self):  # noqa: N802
        # Govdeyi TUKET (okunmazsa istemci tekrar dener -> "1 istek" capasi sahte-KIRMIZI)
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            self.rfile.read(n)
        type(self).kayit.append((self.path, self.headers.get("Authorization")))
        self.send_response(type(self).durum)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *a):  # sessiz
        return


def _sunucu_baslat(durum: int):
    _Sunucu.durum = durum
    _Sunucu.kayit = []
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Sunucu)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def _bos_port() -> int:
    """Kapali bir port bul (ulasilamaz dali icin)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _npx_kabugu(dizin: Path) -> Path:
    """PATH'e konacak sahte `npx`: KOSTUGUNDA bir IZ dosyasi yazar.

    "playwright kostu mu" sorusunun tek durust cevabi budur; cikti metnine bakmak
    (`[ok] auth` gordum -> demek kostu) CIKARIMDIR, olcum degil.
    """
    iz = dizin / "npx_kostu.iz"
    (dizin / "npx.cmd").write_text(
        f'@echo off\r\necho KOSTU %*> "{iz}"\r\nexit /b 0\r\n', encoding="utf-8")
    kabuk = dizin / "npx"          # POSIX CI'da da anlamli kalsin
    kabuk.write_text(f'#!/bin/sh\necho KOSTU "$@" > "{iz}"\nexit 0\n', encoding="utf-8")
    try:
        kabuk.chmod(0o755)
    except OSError:
        pass
    return iz


def _kos(arac: Path, kum: Path, base_url: str) -> tuple[int, str, bool]:
    """(rc, cikti, playwright_kostu_mu)"""
    kabuk_dizin = Path(tempfile.mkdtemp(prefix="k7npx_"))
    try:
        iz = _npx_kabugu(kabuk_dizin)
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["CLAUDE_PROJECT_DIR"] = str(kum)
        env["PATH"] = str(kabuk_dizin) + os.pathsep + env.get("PATH", "")
        p = subprocess.run([sys.executable, str(arac), "--base-url", base_url],
                           cwd=str(kum), env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        return p.returncode, (p.stdout or "") + (p.stderr or ""), iz.exists()
    finally:
        shutil.rmtree(kabuk_dizin, ignore_errors=True)


def _kum(conn: str | None) -> Path:
    d = Path(tempfile.mkdtemp(prefix="k7_"))
    (d / "project.yaml").write_text(
        "sap_profile: s4_private\nsource_root: SOURCE_CODES\nmaster_language: TR\n",
        encoding="utf-8")
    if conn is not None:
        (d / ".conn_adt").write_text(conn, encoding="utf-8")
    return d


def senaryolar(arac: Path) -> list[tuple[str, bool, str]]:
    r: list[tuple[str, bool, str]] = []

    def ekle(ad: str, ok: bool, detay: str = "") -> None:
        r.append((ad, ok, detay))

    # P1 ⭐ 401 -> DUR, playwright KOSMAZ
    srv, port = _sunucu_baslat(401)
    kum = _kum(CONN)
    try:
        rc, out, kostu = _kos(arac, kum, f"http://127.0.0.1:{port}")
        ekle("P1 ⭐ 401 -> `[DUR]` VE playwright KOSTURULMAZ (hesap kilidi onlemi)",
             rc != 0 and "[DUR]" in out and not kostu,
             f"rc={rc} · npx_kostu={kostu} · {out.strip()[:200]!r}")
        ekle("N4 ⭐ SINIR: on-dogrulama TAM 1 istek atti (lockout-safe sayisal degismez)",
             len(_Sunucu.kayit) == 1, f"istek sayisi={len(_Sunucu.kayit)}")
    finally:
        srv.shutdown()
        shutil.rmtree(kum, ignore_errors=True)

    # P2 ⭐ POZITIF KONTROL: 200 -> playwright KOSAR + N3 kimlik dogru
    srv, port = _sunucu_baslat(200)
    kum = _kum(CONN)
    try:
        rc, out, kostu = _kos(arac, kum, f"http://127.0.0.1:{port}")
        ekle("P2 ⭐ POZ.KONTROL: 200 -> `[ok] auth` VE playwright KOSAR "
             "(arac 'hep reddeden' degil)",
             "[ok] auth" in out and kostu,
             f"rc={rc} · npx_kostu={kostu} · {out.strip()[:200]!r}")
        beklenen = "Basic " + base64.b64encode(f"{KULLANICI}:{PAROLA}".encode()).decode()
        gonderilen = [a for _, a in _Sunucu.kayit]
        ekle("N3 gonderilen Basic-auth kimligi `.conn_adt`teki DEGERLERDIR",
             beklenen in gonderilen, f"gonderilen adet={len(gonderilen)}")
    finally:
        srv.shutdown()
        shutil.rmtree(kum, ignore_errors=True)

    # P3 ulasilamaz
    kapali = _bos_port()
    kum = _kum(CONN)
    try:
        rc, out, kostu = _kos(arac, kum, f"http://127.0.0.1:{kapali}")
        ekle("P3 sunucu ulasilamaz -> `[DUR]` + playwright KOSTURULMAZ",
             rc != 0 and "[DUR]" in out and not kostu,
             f"rc={rc} · npx_kostu={kostu} · {out.strip()[:200]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)

    # P4 403 -> 401 DEGIL -> devam
    srv, port = _sunucu_baslat(403)
    kum = _kum(CONN)
    try:
        rc, out, kostu = _kos(arac, kum, f"http://127.0.0.1:{port}")
        ekle("P4 403 -> 401 DEGIL -> devam eder (401 TEK kilit sinyalidir)",
             "[ok] auth" in out and kostu,
             f"rc={rc} · npx_kostu={kostu} · {out.strip()[:200]!r}")
    finally:
        srv.shutdown()
        shutil.rmtree(kum, ignore_errors=True)

    # N1 .conn_adt YOK
    srv, port = _sunucu_baslat(200)
    kum = _kum(None)
    try:
        rc, out, kostu = _kos(arac, kum, f"http://127.0.0.1:{port}")
        ekle("N1 FP capasi: `.conn_adt` yok -> gurultulu hata + DENENEN KOK yazilir + npx YOK",
             rc != 0 and ".conn_adt yok" in out and not kostu,
             f"rc={rc} · npx_kostu={kostu} · {out.strip()[:220]!r}")
    finally:
        srv.shutdown()
        shutil.rmtree(kum, ignore_errors=True)

    # N2 alan eksik
    srv, port = _sunucu_baslat(200)
    kum = _kum("ADT_SAP_URL=https://ornek.gecerli:44300\nADT_SAP_CLIENT=100\n")
    try:
        rc, out, kostu = _kos(arac, kum, f"http://127.0.0.1:{port}")
        ekle("N2 FP capasi: USER/PASSWORD eksik -> AYRIK hata (kok hatasi maskelemez) + npx YOK",
             rc != 0 and "ADT_SAP_USER" in out and ".conn_adt yok" not in out and not kostu,
             f"rc={rc} · npx_kostu={kostu} · {out.strip()[:220]!r}")
    finally:
        srv.shutdown()
        shutil.rmtree(kum, ignore_errors=True)
    return r


MUTASYONLAR = [
    ("M1 ⭐ 401'i kilit sinyali SAYMA (lockout korumasini sok)",
     lambda s: s.replace("    if status == 401:", "    if False:")),
    ("M2 ⭐SINIR: on-dogrulamayi IKI KEZ yap (tek-istek degismezini sok)",
     lambda s: s.replace("    status = verify_auth_once(base, u, p)\n",
                         "    verify_auth_once(base, u, p)\n"
                         "    status = verify_auth_once(base, u, p)\n")),
    ("M3 ulasilamaz (None) dalini sok -> app ayakta degilken de playwright kosar",
     lambda s: s.replace("    if status is None:", "    if False:")),
]


def main() -> int:
    print("=" * 78)
    print("ui_smoke_sapsiz — K7: lockout-safe on-dogrulama SAP'siz olculur")
    print("=" * 78)
    if not ARAC.is_file():
        print(f"FAIL — arac yok: {ARAC}")
        return 1

    ham = ARAC.read_text(encoding="utf-8")
    sonuc = senaryolar(ARAC)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik, yama_kirik, kurulamadi = [], [], []
    # ⚠ Mutant GERCEK `ui-smoke/` dizininde yasar: arac `HERE`den playwright.config'i
    # ve komsu `utils.` modullerini kendi konumundan cozer (B24 dersi).
    mutant = ARAC.with_name("_mutant_run_ui_smoke.py")
    for ad, mut in MUTASYONLAR:
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        try:
            mutant.write_text(bozuk, encoding="utf-8")
            m_res = senaryolar(mutant)
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:  # noqa: BLE001
            # ⛔ KURULAMADI != KACTI (cokme != FAIL): mutasyon KURULAMADIYSA korpusun
            #    zayif oldugu SONUCU CIKARILAMAZ — olcum hic yapilamamistir. Ucuncu
            #    deger olarak ayri raporlanir ve korpusu KIRMIZI yapar.
            kurulamadi.append("%s -> %s: %s" % (ad, type(e).__name__, e))
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
            continue
        finally:
            mutant.unlink(missing_ok=True)
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik or kurulamadi:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        if kurulamadi:
            print("FAIL — mutasyon KURULAMADI (olcum yapilamadi; korpus zayif DEMEK DEGIL): %s"
                  % "; ".join(kurulamadi))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
