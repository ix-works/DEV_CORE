#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""aktivasyon_sahte_ok fixture — "HTTP 200 KANIT DEGIL"in ikinci yuzu: HTTP HATASI da kanit degil.

NEDEN VAR (2026-08-01 adversarial bug-avi, W2-MCPT-02):
`activate_and_verify` yanit GOVDESINI ayristiriyordu ama `r.status_code`'a HIC bakmiyordu;
`_activation_failures` fallback'i de "hata isareti YOKSA basarili" diyordu. Sonuc: aktivasyon
yaniti OLMAYAN govdeler basari sayiliyordu. Olculdu (kontrol grubuyla):
    200 + basari govdesi -> aktive edildi   (dogru)
    200 + type=E         -> RuntimeError    (dogru)
    HTTP 500 hata sayfasi-> AKTIVE EDILDI   (YANLIS)
    HTTP 403 logon formu -> AKTIVE EDILDI   (YANLIS)
    200 + BOS govde      -> AKTIVE EDILDI   (YANLIS)
Ustelik fonksiyonun kendi docstring'i "sahte 'OK' imkansiz" diyordu — DOKUMAN DAVRANISI
YALANLIYORDU. Aktivasyon geri-alinamaz bir isin son adimidir; "aktive edildi" yanilgisi
zincirin geri kalanini (readback, publish, bir sonraki obje) yanlis temele oturtur.

POLITIKA (iki katman):
  1. TASIMA: HTTP 2xx disi -> aktivasyon yaniti DEGIL -> RuntimeError (govde ayristirilmadan).
  2. GOVDE: `activationExecuted` yoksa fallback YALNIZ govde gercekten bir ADT checklist
     yanitina benziyorsa uygulanir (chkl:/<msg/adtcore:/<messages). Taninmayan govde =
     kanit yok = BASARISIZ (fail-closed).

⚠ KONTROL GRUBU OMURGADIR: "200+basari -> aktive edildi" satiri korunmali; kaldirilirsa
test asiri-siki olur ve GERCEK aktivasyonu da reddeder.
"""
from __future__ import annotations

import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
for p in (REPO, REPO / "scripts"):
    sys.path.insert(0, str(p))

try:
    from create_rap_service import _activation_failures, activate_and_verify
except Exception as exc:                                    # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] modul yuklenemedi (sessiz gecme YOK): {exc}")

BASARI = ('<?xml version="1.0"?><chkl:messages xmlns:chkl="http://www.sap.com/abapxml/checklist" '
          'activationExecuted="true"/>')
HATA_E = ('<?xml version="1.0"?><chkl:messages activationExecuted="false">'
          '<msg type="E"><txt>Syntax error in ZCL_X</txt></msg></chkl:messages>')
ESKI_STIL = '<?xml version="1.0"?><chkl:messages><msg severity="I"><txt>ok</txt></msg></chkl:messages>'
HTTP500 = "<html><head><title>500 Internal Server Error</title></head><body>SAP Web AS</body></html>"
HTTP403 = "<html><body><form name='sapLogonForm'>Logon failed</form></body></html>"


class _Yanit:
    def __init__(self, kod, metin):
        self.status_code = kod
        self.text = metin


class _Client:
    def __init__(self, yanit):
        self.url = "https://ornek.test"
        self.session = type("S", (), {"post": lambda _s, *a, **k: yanit})()


def main() -> int:
    sonuc = []

    # A) saf ayristirici — (ad, govde, beklenen_executed)
    for ad, govde, bekl in [
        ("KONTROL basari govdesi -> executed", BASARI, True),
        ("KONTROL type=E -> executed degil", HATA_E, False),
        ("ESKI STIL (chkl, severity yok) -> executed", ESKI_STIL, True),
        ("HTTP 500 govdesi -> KANIT YOK", HTTP500, False),
        ("HTTP 403 logon -> KANIT YOK", HTTP403, False),
        ("BOS govde -> KANIT YOK", "", False),
    ]:
        ex, _errs = _activation_failures(govde)
        sonuc.append((f"A) {ad}", ex is bekl, f"executed={ex}"))

    # B) uctan uca — (ad, http, govde, basarili_olmali)
    for ad, kod, govde, basarili in [
        ("KONTROL 200 + basari -> gecer", 200, BASARI, True),
        ("KONTROL 200 + type=E -> reddeder", 200, HATA_E, False),
        ("HTTP 500 -> reddeder", 500, HTTP500, False),
        ("HTTP 403 -> reddeder", 403, HTTP403, False),
        ("200 + BOS govde -> reddeder", 200, "", False),
    ]:
        try:
            activate_and_verify(_Client(_Yanit(kod, govde)), "tok", [("/u/x", "ZX")])
            oldu = True
            detay = "TRUE dondu"
        except RuntimeError as e:
            oldu = False
            detay = f"RuntimeError: {str(e)[:40]}"
        sonuc.append((f"B) {ad}", oldu is basarili, detay))

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
