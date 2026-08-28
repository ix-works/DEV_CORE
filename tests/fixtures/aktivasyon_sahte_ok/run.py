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
    from create_rap_service import (_activation_failures, _zorunlu_desc,
                                    activate_and_verify, step_bactivate,
                                    step_cdsactivate, step_pbactivate)
    from sap_adt_lib import SAPADTError
except Exception as exc:                                    # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] modul yuklenemedi (sessiz gecme YOK): {exc}")

BASARI = ('<?xml version="1.0"?><chkl:messages xmlns:chkl="http://www.sap.com/abapxml/checklist" '
          'activationExecuted="true"/>')
HATA_E = ('<?xml version="1.0"?><chkl:messages activationExecuted="false">'
          '<msg type="E"><txt>Syntax error in ZCL_X</txt></msg></chkl:messages>')
# activationExecuted="false" ama HIC hata mesaji YOK — 2026-06-11 dersinin saf hali:
# "POST 200 dondu, SAP aktive etmedi, gerekce de yazmadi".
EXEC_FALSE = ('<?xml version="1.0"?><chkl:messages xmlns:chkl="http://www.sap.com/abapxml/checklist" '
              'activationExecuted="false"/>')
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

    # C) #73 (2026-08-29) — `step_*activate` CAGRI YERLERI.
    # Bu uc fonksiyon ana yoldan (activate/activate_and_verify) BAGIMSIZ, kendi
    # ad-hoc kontrolunu tasiyordu: `severity="E"/"A"` + `status>=400`. UC KUSUR:
    #   1. `severity=` ADT aktivasyon semasinda YOKTUR (gercek sema
    #      `<chkl:message ... type="E">`) -> kosul ASLA eslesmez.
    #      playbook/adt-rap.md:827: "`severity="E"` aramak YETMEZ".
    #   2. `activationExecuted` HIC okunmuyordu (2026-06-11 dersi).
    #   3. Taninmayan govdede fail-OPEN (2026-08-01 W2-MCPT-02); `status>=400`
    #      yalniz tasima katmanini kapatir, "200 + cop govde" acikti.
    for fn_ad, fn in (("step_cdsactivate", step_cdsactivate),
                      ("step_pbactivate", step_pbactivate),
                      ("step_bactivate", step_bactivate)):
        for ad, kod, govde, bekl in [
            ("KONTROL 200+basari -> gecer", 200, BASARI, True),   # FP CAPASI (omurga)
            ("200 + type=E -> reddeder", 200, HATA_E, False),
            ("200 + executed=false -> reddeder", 200, EXEC_FALSE, False),
            ("200 + BOS govde -> reddeder", 200, "", False),
            ("HTTP 500 -> reddeder", 500, HTTP500, False),
        ]:
            try:
                oldu = bool(fn(_Client(_Yanit(kod, govde)), "tok"))
                detay = f"dondu={oldu}"
            except Exception as e:                              # pragma: no cover
                oldu, detay = None, f"ISTISNA {type(e).__name__}: {str(e)[:40]}"
            sonuc.append((f"C) {fn_ad}: {ad}", oldu is bekl, detay))

    # D) SINIF CAPASI (AST) — ornek degil SINIF kapanmali.
    # Sozlesme: `/sap/bc/adt/activation`a POST eden (= `ACTIVATION` sabitini kullanan)
    # HICBIR fonksiyon hukmunu `severity=` dizgesine dayandirmaz; karar tek noktadan
    # (`_activation_failures`) gelir. Yarin 4. bir cagri yeri eklenirse bu vektor duser.
    # NOT: `_activation_failures`in KENDISI muaftir (ACTIVATION sabitini kullanmaz) —
    # oradaki `severity=` ADT-checklist fallback'idir ve A) bolumu onu ayrica olcer.
    import ast
    kaynak_yolu = REPO / "scripts" / "create_rap_service.py"
    kaynak = kaynak_yolu.read_text(encoding="utf-8")
    agac = ast.parse(kaynak)
    kirli, aktivasyon_fn = [], []
    for dugum in ast.walk(agac):
        if not isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(isinstance(x, ast.Name) and x.id == "ACTIVATION"
                   for x in ast.walk(dugum)):
            continue
        aktivasyon_fn.append(dugum.name)
        if 'severity="' in (ast.get_source_segment(kaynak, dugum) or ""):
            kirli.append(dugum.name)
    # Capa kendini de dogrular: hic aktivasyon fonksiyonu bulamadiysak olcum BOZUK.
    sonuc.append(("D) SINIF: ACTIVATION POST eden fonksiyon sayisi > 0 (olcum canli)",
                  len(aktivasyon_fn) > 0, f"bulunan={aktivasyon_fn}"))
    sonuc.append(("D) SINIF: ACTIVATION POST edenler `severity=` dizgesine dayanmiyor",
                  not kirli, f"kirli={kirli or 'yok'}"))

    # E) #71 (2026-08-29) — obje ACIKLAMASI artik GOMULU DEGIL.
    # ⚠ IKINCI EKSEN: bu bolum bu dosyanin (create_rap_service.py) aktivasyondan FARKLI
    # bir kusurunu olcer; burada yasamasinin sebebi run_fixture_tests HARITA'sinin bu
    # dosyayi YALNIZ bu fixture'a baglamasidir. Ayri fixture + HARITA satiri daha temiz
    # olurdu (kosucu dosyasi bu turda baska bir partin sahipliginde — rapora yazildi).
    # Kusur: `"Sefer Baslik davranisi"` / `"Sefer Baslik davranis uygulamasi"` ZSD001'e
    # ozgu metinlerdi ve HER yeni serviste kopyalaniyordu. ADR 0005-D: Z obje metnini
    # AI ONERMEZ -> varsayilan uretilmez, BOS ise akis DURUR.
    for ad, deger, patlamali in [
        ("BOS -> DURDURUR", "", True),
        ("yalniz bosluk -> DURDURUR", "   ", True),
        ("mesru TR metin -> GECER", "Siparis Baslik davranisi", False),   # FP CAPASI
    ]:
        try:
            donen = _zorunlu_desc(deger, "--bdef-desc", "BDEF ZX")
            patladi, detay = False, f"dondu={donen!r}"
        except SAPADTError as e:
            patladi, detay = True, f"SAPADTError: {str(e)[:38]}"
        except Exception as e:                                  # pragma: no cover
            patladi, detay = None, f"YANLIS ISTISNA {type(e).__name__}"
        sonuc.append((f"E) _zorunlu_desc: {ad}", patladi is patlamali, detay))
    # trim davranisi (mesru degeri BOZMADIGININ capasi)
    try:
        kirpildi = _zorunlu_desc("  Siparis  ", "--bdef-desc", "BDEF ZX")
    except Exception as e:                                      # pragma: no cover
        kirpildi = f"ISTISNA {type(e).__name__}"
    sonuc.append(("E) _zorunlu_desc: bastaki/sondaki bosluk kirpilir",
                  kirpildi == "Siparis", f"dondu={kirpildi!r}"))

    # E-SINIF (AST): shell uretecine gecen `desc` argumani STRING LITERAL OLAMAZ.
    # Yarin biri "gecici olsun" diye yeniden gomerse bu vektor duser.
    gomulu = []
    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.Call):
            continue
        fn = dugum.func
        if not (isinstance(fn, ast.Name)
                and fn.id in ("bdef_shell_xml", "bclass_shell_xml")):
            continue
        if len(dugum.args) >= 2 and isinstance(dugum.args[1], ast.Constant):
            gomulu.append(f"{fn.id}(...,{dugum.args[1].value!r})")
    sonuc.append(("E) SINIF: shell ureteclerine GOMULU aciklama gecilmiyor",
                  not gomulu, f"gomulu={gomulu or 'yok'}"))

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
