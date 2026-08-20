#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_fixture_tests KENDI OLCTUGU ORTAMI KIRLETIYORDU (suit idempotent degildi).

KOK (bugun bisect ile izole edildi): `populate_tables_unit_kind` korpusu
`populate_tables.py`yi exec eder -> o da `sap_adt_lib`i import eder -> kutuphane repo
KOKUNE yer-tutucu bir `.conn_adt` YAZAR (1087 B). Dosya gitignored oldugu icin
`git status` TEMIZ gosterir. IKINCI ardisik kosumda `conn_cift_anahtar`in
*"tier YOK -> UNKNOWN"* vektoru o dosyadan `tier=DEV` okuyup FAIL verir.

OLCUM (2026-08-20, ayni agac): 1. kosum **130/130** · 2. ardisik kosum **129/130**
(`conn_cift_anahtar` SAPMA) · kalinti silinince yine 130/130 ⇒ nedensellik kanitli,
sebep KOD DEGIL suitin KENDI URETTIGI ARTIK.

⚠ NEDEN ONEMSIZ DEGIL: yanilan test bir fail-closed TIER korumasinin testidir
(ADR 0010). Bugunku yon "sahte FAIL" (gurultulu, fark edilir) — ama ayni kirlenme
TERS yonde de calisabilir: kalinti BEKLENEN degeri saglarsa, gercekte kirik bir
koruma YESIL gorunur ve kimse fark etmez.

⛔ GEVSETME DEGIL: vektor kaldirilmadi, beklenen deger degistirilmedi. Kirlilik
giderildi, olcut AYNEN duruyor. (Kayit bu iki yolu ACIKCA yasaklamisti.)

  S1-S2  baslangic sondasi: kalinti VARSA gorunur uyari · YOKSA sessiz
  S3     temizlik: suitin KENDI urettigi kalinti silinir (idempotans)
  S4     ⭐ FP CAPASI: kosumdan ONCE var olan dosya KULLANICININDIR -> DOKUNULMAZ
  S5     KABLOLAMA (AST): main() ikisini de try/finally icinde cagirir
  M1-M3  fix'i sok -> korpus KIRMIZI olmali

⚠ GERCEK IDEMPOTANS KANITI bu korpusta DEGIL (suiti iki kez kosmak ~6 dk):
  recete B26'da elle adim olarak durur ve bugun olculdu (131/131 + 131/131).

Kosum: python tests/fixtures/suite_ortam_hijyeni/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import ast
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SUITE_PATH = CORE / "tests" / "run_fixture_tests.py"
sys.path.insert(0, str(CORE / "tests"))

try:
    import run_fixture_tests as S
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] suit yuklenemedi (sessiz gecme YOK): {exc}")


def _kablolu_mu(src: str) -> tuple[bool, str]:
    """main() ikisini de cagiriyor mu ve BITIR bir `finally` blogunda mi (AST)?

    ⚠ Metin aramasi kullanilmaz: cagri ile TANIM metinde birbirine benzer ve
    `def _ortam_hijyeni_bitir` satiri `"_ortam_hijyeni_bitir(" in src` kontrolunu
    cagri sokulmus olsa bile True yapar (Parti-1'de bu tuzak bir mutasyonu kacirdi).
    """
    try:
        agac = ast.parse(src)
    except SyntaxError as e:
        return False, "ayristirilamadi: %s" % e
    for fn in agac.body:
        if not (isinstance(fn, ast.FunctionDef) and fn.name == "main"):
            continue
        basla = any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_ortam_hijyeni_basla"
                    for n in ast.walk(fn))
        bitir_finally = False
        for n in ast.walk(fn):
            if isinstance(n, ast.Try):
                for f in n.finalbody:
                    if any(isinstance(c, ast.Call)
                           and getattr(c.func, "id", "") == "_ortam_hijyeni_bitir"
                           for c in ast.walk(f)):
                        bitir_finally = True
        if not basla:
            return False, "main() `_ortam_hijyeni_basla` CAGIRMIYOR"
        if not bitir_finally:
            return False, "`_ortam_hijyeni_bitir` bir `finally` blogunda DEGIL (cokmede temizlenmez)"
        return True, ""
    return False, "main() bulunamadi"


def senaryolar(modul=S) -> list[tuple[str, bool, str]]:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    tmp = Path(tempfile.mkdtemp(prefix="hijyen_"))
    sahte = tmp / ".conn_adt"
    eski = modul._CONN
    try:
        modul._CONN = sahte

        # --- S1: kalinti VAR -> True + GORUNUR uyari -----------------------
        sahte.write_text("ADT_SAP_TIER=DEV\n", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            vardi = modul._ortam_hijyeni_basla()
        c = buf.getvalue()
        # K4 (2026-08-20): donus (var_mi, bayt, sha1) demetidir — [0] eski `bool`un yerini
        # alir. Olcut DEGISMEDI: "kalinti VARSA True + gorunur uyari".
        ekle("S1 kalinti VAR -> True + 'KİRLİ ORTAM' uyarisi",
             vardi[0] is True and "KİRLİ ORTAM" in c and "tier" in c.lower(),
             "vardi=%r cikti=%r" % (vardi, c[:90]))

        # --- S2: kalinti YOK -> False + SESSIZ (FP capasi) -----------------
        sahte.unlink()
        buf = io.StringIO()
        with redirect_stdout(buf):
            yok = modul._ortam_hijyeni_basla()
        ekle("S2 kalinti YOK -> False + hicbir sey basilmaz",
             yok[0] is False and buf.getvalue() == "",
             "yok=%r cikti=%r" % (yok, buf.getvalue()[:60]))

        # --- S3: temizlik — suitin KENDI urettigi silinir ------------------
        sahte.write_text("x" * 40, encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            modul._ortam_hijyeni_bitir((False, 0, ""))   # kosum basinda YOKTU
        ekle("S3 suitin urettigi kalinti SILINIR (idempotans)",
             not sahte.exists() and "SİLİNDİ" in buf.getvalue(),
             "var_mi=%s cikti=%r" % (sahte.exists(), buf.getvalue()[:80]))

        # --- S4: ⭐ FP CAPASI — kullanicinin dosyasina DOKUNULMAZ ----------
        # Kosumdan ONCE var olan bir `.conn_adt` KULLANICININDIR (gercek baglanti
        # bilgisi olabilir). Onu silmek, kapatmaya calistigimiz "sessiz veri kaybi"
        # sinifini URETMEK olurdu.
        sahte.write_text("GERCEK_BAGLANTI=1\n", encoding="utf-8")
        # Imza dosyanin O ANKI halinden alinir: "vardi ve DEGISMEDI" durumu.
        # (Degisseydi K4'un ezilme-tespiti devreye girerdi — o dal `conn_kum_sizintisi`
        # korpusunda L1/L2 ile olculur, burada FP capasi olarak SESSIZLIK beklenir.)
        onceki_imza = modul._conn_imza()
        buf = io.StringIO()
        with redirect_stdout(buf):
            modul._ortam_hijyeni_bitir(onceki_imza)   # kosum basinda VARDI
        ekle("S4 FP capasi: kosum oncesi var olan dosya SILINMEZ (kullanicinin)",
             sahte.exists() and sahte.read_text(encoding="utf-8") == "GERCEK_BAGLANTI=1\n"
             and buf.getvalue() == "",
             "var_mi=%s cikti=%r" % (sahte.exists(), buf.getvalue()[:60]))

        # --- S5: KABLOLAMA (AST) -------------------------------------------
        ok, detay = _kablolu_mu(SUITE_PATH.read_text(encoding="utf-8"))
        ekle("S5 kablolama: main() ikisini de cagirir, BITIR `finally`de", ok, detay)
    finally:
        modul._CONN = eski

    return out


MUTASYONLAR = [
    ("M1 `vardi` korumasini sok (kullanicinin dosyasi da silinsin)",
     lambda s: s.replace("    if onceki[0]:\n", "    if False:\n")),
    ("M2 kirli-ortam uyarisini sok (sessizce oku)",
     lambda s: s.replace('    if imza[0]:\n        print(f"⚠ KİRLİ ORTAM:',
                         '    if False:\n        print(f"⚠ KİRLİ ORTAM:')),
    ("M3 temizligi `finally`den cikar (cokmede kalinti kalsin)",
     lambda s: s.replace(
         "    try:\n        return _main(argv)\n    finally:\n"
         "        # try/finally: çökmede de temizlenir (yarım koşum kalıntı bırakmasın).\n"
         "        _ortam_hijyeni_bitir(onceki_conn)",
         "    return _main(argv)")),
]


def _yukle(src: str):
    import types
    m = types.ModuleType("suite_mut")
    m.__file__ = str(SUITE_PATH)
    exec(compile(src, str(SUITE_PATH), "exec"), m.__dict__)
    return m


def main() -> int:
    print("=" * 78)
    print("suite_ortam_hijyeni — suit kendi olctugu ortami kirletmez")
    print("=" * 78)

    sonuc = senaryolar()
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    ham = SUITE_PATH.read_text(encoding="utf-8")
    mut_kirik, yama_kirik = [], []
    for ad, mut in MUTASYONLAR:
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        if "finally" in ad or "M3" in ad:
            # Kablolama mutasyonu: AST ile KAYNAK metninden olculur (import gerekmez).
            ok, detay = _kablolu_mu(bozuk)
            m_res = [("S5 kablolama (mutasyonlu kaynak)", ok, detay)]
        else:
            try:
                m_res = senaryolar(_yukle(bozuk))
            except BaseException as e:
                m_res = []
                print("  [KURULAMADI] %s -> %s" % (ad, type(e).__name__))
        yakalandi = bool(m_res) and any(not ok for _, ok, _ in m_res)
        kacan = [a for a, ok, _ in m_res if not ok]
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
