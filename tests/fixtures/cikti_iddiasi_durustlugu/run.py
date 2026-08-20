#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SINIF: arac CIKTISI, kodunun YAPTIGINDAN FAZLASINI iddia ediyor.

Iki bilesende ayni kusur olculdu (2026-08-20):

A) `run_pretty_printer.py` + `sap_client.pretty_print()`
   Arac SAP'nin DURUMSUZ bicimleme servisini cagirir: GET + POST(prettyprinter) +
   return. `lock` YOK · `PUT source/main` YOK · `activate` YOK. Buna ragmen
   basarida "Pretty printer applied to: X", hatada "X was NOT formatted in SAP",
   kutuphanede "Applying pretty printer to: X" yaziyordu -- UCU DE olmayan bir
   sunucu yazmasi iddia ediyor. Lider bu metinlere bakip "bu arac SAP'de kaynagi
   degistirir" varsaydi ve gateway brifingini ona gore kurdu; varsayim curudu.
   O turda kayip olmadi (bicim zaten ayniydi) ama FARK CIKSAYDI sessizce kaybolurdu.

B) `sap_sync_pull.py --type class`
   Yalniz `/source/main` (ana `.clas.abap`) cekilir; `.ccimp/.ccau/.ccdef/.ccmac`
   AYRI ADT uclarindadir ve HIC okunmaz. Ama `_stamp` obje ADINA yazildigi icin
   pull-before-edit kapisi alt-include'u da TAZE sayar ve cikti
   "artik duzenleyebilirsin" der ⇒ BAYAT bir `.ccimp.abap` taze sanilip duzenlenir.
   ⚠ Cekme yolu bu turda BILEREK kurulmadi: `object_types.CLASS_INCLUDE_TYPES`
   segment adlarinin 4'unden 3'u `'olculdu': False` (bu evde canli dogrulanmamis).
   Dogrulanmamis uctan okuyup repo dosyasinin ustune yazmak, kapatmaya calistigimiz
   sinifi URETMEK olurdu. Bugun yapilan: boslugu GORUNUR kilmak.

DEGISMEZ (ikisinde de ayni): cikti, kodun yapabildiginden fazlasini SOYLEMEZ;
yapamadigini da SESSIZ GECMEZ.

  A1-A4  pretty printer: basari/hata metni + docstring + YAZMA-YOK yapisal capasi
  B1-B4  sync_pull: alt-include varsa UYARIR · yoksa SESSIZ · marker TEK KAYNAK · ASCII
  M1-M3  fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/cikti_iddiasi_durustlugu/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import io
import sys
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SCRIPTS = CORE / "scripts"
RPP_PATH = SCRIPTS / "run_pretty_printer.py"
SYNC_PATH = SCRIPTS / "sap_sync_pull.py"
CLIENT_PATH = SCRIPTS / "sap_client.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_mod_refs: list = []


def _yukle(yol: Path, ad: str, mut=None):
    """Modulu TAZE namespace'e yukler; mutasyon KAYNAK METNINE uygulanir.

    ⚠ Her iki modul de import aninda `io.TextIOWrapper(sys.stdout.buffer)` kurar
    (win32 dali). Sadece sys.stdout'u geri koymak YETMEZ: wrapper GC'ye girince
    sardigi GERCEK buffer'i KAPATIR -> sonraki print "I/O operation on closed file"
    ile patlar. Import sirasinda stdout ATILABILIR bir BytesIO'ya baglanir.
    """
    src = yol.read_text(encoding="utf-8")
    if mut:
        src = mut(src)
    saved_out, saved_err = sys.stdout, sys.stderr
    cop_out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    cop_err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    sys.stdout, sys.stderr = cop_out, cop_err
    try:
        mod = types.ModuleType(ad)
        mod.__file__ = str(yol)
        exec(compile(src, str(yol), "exec"), mod.__dict__)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
        _mod_refs.append((cop_out, cop_err))
    return mod


def _rpp_calistir(mod, donen):
    """run_pretty_printer.main()'i sahte client ile kosar -> (rc, cikti)."""
    class _C:
        def pretty_print(self, object_name, object_type):
            if isinstance(donen, Exception):
                raise donen
            return donen

    argv = sys.argv[:]
    saved = sys.stdout
    tut = io.StringIO()
    sys.argv = ["run_pretty_printer.py", "--object-name", "ZCL_TEST",
                "--object-type", "class"]
    mod.SAPClient = lambda *a, **k: _C()
    mod.set_explicit_working_dir = lambda *a, **k: None
    sys.stdout = tut
    try:
        rc = mod.main()
    finally:
        sys.stdout = saved
        sys.argv = argv
    return rc, tut.getvalue()


# YAZMA yapan cagri ADLARI — bunlar YOKSA "sunucu degismedi" iddiasi DOGRUDUR.
# ⚠ AST ile aranir, METINLE DEGIL: docstring'imiz "kalici olsun istiyorsan
# push_object.py ile yaz" DIYOR ve duz metin aramasi bunu YAZMA CAGRISI sandi
# (ilk kosumda A4 sahte-KIRMIZI verdi). Yorum/docstring bir cagri degildir.
_YAZMA_CAGRILARI = {"set_object_source", "lock_object", "activate_object",
                    "push_object", "push_class_include", "put"}


def _cagrilan_adlar(src: str) -> set[str]:
    """Kaynaktaki GERCEK cagri adlari (ast) — yorum/docstring/dize HARIC."""
    import ast
    try:
        agac = ast.parse(src)
    except SyntaxError:
        return set()
    adlar = set()
    for n in ast.walk(agac):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                adlar.add(f.id)
            elif isinstance(f, ast.Attribute):
                adlar.add(f.attr)
    return adlar


def _kablolu_mu(src: str, fn_adi: str, cagri_adi: str) -> bool:
    """`fn_adi` fonksiyonunun GOVDESINDE `cagri_adi` cagrisi var mi (ast).

    ⚠ Metin aramasi BURADA DA yanildi: `"_alt_include_uyar(" in src` fonksiyonun
    KENDI `def` satiriyla eslesti ve cagri sokulmus olsa bile True dondu ->
    M2 mutasyonu KACTI. Cagri ile TANIM ayni metne benzer; AST ayirir.
    """
    import ast
    try:
        agac = ast.parse(src)
    except SyntaxError:
        return False
    for fn in ast.walk(agac):
        if isinstance(fn, ast.FunctionDef) and fn.name == fn_adi:
            return any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == cagri_adi
                for n in ast.walk(fn)
            )
    return False


def senaryolar(rpp, sync) -> list[tuple[str, bool, str]]:
    import tempfile

    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    # ================= A) run_pretty_printer =================================
    rc, cikti = _rpp_calistir(rpp, "CLASS zcl_test.\nENDCLASS.")
    ekle("A1 basari: 'SUNUCU DEGISMEDI' der ve 'applied to' DEMEZ",
         rc == 0 and "SUNUCU DEGISMEDI" in cikti and "applied to" not in cikti,
         "rc=%s | sunucu_degismedi=%s | applied_to_var=%s"
         % (rc, "SUNUCU DEGISMEDI" in cikti, "applied to" in cikti))

    rc, cikti = _rpp_calistir(rpp, None)
    ekle("A2 hata: 'was NOT formatted in SAP' DEMEZ (hic yazilmayacakti)",
         rc == 1 and "was NOT formatted in SAP" not in cikti
         and "ALINAMADI" in cikti,
         "rc=%s | eski_yalan=%s" % (rc, "was NOT formatted in SAP" in cikti))

    ekle("A3 docstring 'KAYDETMEZ' der",
         "KAYDETMEZ" in (rpp.__doc__ or ""),
         "docstring=%r" % (rpp.__doc__ or "")[:60])

    # A4: YAPISAL capa — iddia ile kod ortusuyor mu? Bir gun `--write` eklenirse
    # bu vektor kirilir ve yazan kisi cikti metnini de gozden gecirmek ZORUNDA kalir.
    rpp_src = RPP_PATH.read_text(encoding="utf-8")
    cl_src = CLIENT_PATH.read_text(encoding="utf-8")
    i = cl_src.find("def pretty_print(")
    govde = cl_src[i:i + 1400] if i >= 0 else ""
    izler = sorted(
        (_cagrilan_adlar(rpp_src) | _cagrilan_adlar("class _X:\n" + govde))
        & _YAZMA_CAGRILARI
    )
    ekle("A4 yapisal: pretty-print yolunda YAZMA cagrisi yok (iddia<->kod)",
         i >= 0 and not izler, "bulunan yazma cagrilari=%s" % izler)

    # ================= B) sap_sync_pull alt-include ==========================
    tmp = Path(tempfile.mkdtemp(prefix="sync_alt_"))

    # B1: alt-include VAR -> uyarir + hepsini adlandirir
    (tmp / "ZCL_TEST.clas.abap").write_text("CLASS zcl_test.\n", encoding="utf-8")
    (tmp / "ZCL_TEST.ccimp.abap").write_text("* impl\n", encoding="utf-8")
    (tmp / "ZCL_TEST.ccau.abap").write_text("* test\n", encoding="utf-8")
    (tmp / "ZCL_BASKA.ccimp.abap").write_text("* baska sinif\n", encoding="utf-8")  # FP capasi
    tut = io.StringIO()
    saved = sys.stdout
    sys.stdout = tut
    try:
        sync._alt_include_uyar("ZCL_TEST", str(tmp / "ZCL_TEST.clas.abap"))
    finally:
        sys.stdout = saved
    c = tut.getvalue()
    ekle("B1 alt-include VAR: uyarir + 2 dosyayi adlandirir + KOMSU sinifi karistirmaz",
         "CEKILMEDI" in c and "ZCL_TEST.ccimp.abap" in c
         and "ZCL_TEST.ccau.abap" in c and "ZCL_BASKA" not in c,
         "cikti=%r" % c[:120])

    # B2: alt-include YOK -> SESSIZ (FP capasi, B1'den AYRI)
    tmp2 = Path(tempfile.mkdtemp(prefix="sync_yalin_"))
    (tmp2 / "ZCL_YALIN.clas.abap").write_text("CLASS zcl_yalin.\n", encoding="utf-8")
    tut = io.StringIO()
    saved = sys.stdout
    sys.stdout = tut
    try:
        sync._alt_include_uyar("ZCL_YALIN", str(tmp2 / "ZCL_YALIN.clas.abap"))
    finally:
        sys.stdout = saved
    ekle("B2 alt-include YOK: hicbir sey basilmaz (gurultu yok)",
         tut.getvalue() == "", "gorulen=%r" % tut.getvalue()[:80])

    # B3: marker listesi TEK KAYNAK (source_drift) — yerel kopya ACILMAMIS
    sync_src = SYNC_PATH.read_text(encoding="utf-8")
    ekle("B3 marker listesi source_drift'ten import edilir (ikinci kopya yok)",
         "from source_drift import _CLASS_SUBSOURCE_MARKERS" in sync_src
         and ".ccimp.abap\"" not in sync_src and ".ccimp.abap'" not in sync_src,
         "import_var=%s"
         % ("from source_drift import _CLASS_SUBSOURCE_MARKERS" in sync_src))

    # B4: C-ENC-01 — uyari blogu saf ASCII (cp1252 konsolda cokmez)
    ekle("B4 C-ENC-01: uyari blogu saf ASCII",
         c.isascii(), "ascii-disi=%s" % sorted({x for x in c if not x.isascii()}))

    # B5: KABLOLAMA (kod != kablolama) — uyari main()'den GERCEKTEN cagriliyor mu
    ekle("B5 kablolama: main() icinde _alt_include_uyar cagrisi var (AST)",
         _kablolu_mu(sync_src, "main", "_alt_include_uyar"),
         "main() govdesinde cagri bulunamadi")

    return out


MUTASYONLAR = [
    ("M1 basari metnini 'applied to'ya geri dondur (A: iddia degismezi)",
     "rpp",
     lambda s: s.replace('f"[OK] Bicimlenmis kaynak DONDU: {args.object_name} '
                         '({len(result)} karakter)"',
                         'f"[OK] Pretty printer applied to: {args.object_name}"')),
    ("M2 alt-include uyarisini sok (B: sessizlik degismezi)",
     "sync",
     lambda s: s.replace("    _alt_include_uyar(obj, res.get(\"repo_path\"))\n", "")),
    ("M3 marker'i YEREL KOPYAYA cevir (B: tek-kaynak degismezi)",
     "sync",
     lambda s: s.replace("        from source_drift import _CLASS_SUBSOURCE_MARKERS",
                         "        _CLASS_SUBSOURCE_MARKERS = (\".ccimp.abap\",)")),
]


def main() -> int:
    print("=" * 78)
    print("cikti_iddiasi_durustlugu — 'arac yaptigindan fazlasini iddia etmez'")
    print("=" * 78)

    rpp = _yukle(RPP_PATH, "run_pretty_printer")
    sync = _yukle(SYNC_PATH, "sap_sync_pull")
    sonuc = senaryolar(rpp, sync)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik = []
    for ad, hedef, mut in MUTASYONLAR:
        try:
            if hedef == "rpp":
                m_res = senaryolar(_yukle(RPP_PATH, "run_pretty_printer", mut), sync)
            else:
                # M2 main() govdesini, M3 yardimciyi bozar; ikisi de KAYNAK metninde.
                if "uyarisini sok" in ad:
                    # KABLOLAMA mutasyonu: cagri main()'den sokuldu mu (AST).
                    bozuk = mut(SYNC_PATH.read_text(encoding="utf-8"))
                    m_res = [("B0 kablolama: main() icinde _alt_include_uyar cagrisi",
                              _kablolu_mu(bozuk, "main", "_alt_include_uyar"),
                              "cagri main()'de YOK")]
                else:
                    m_res = senaryolar(rpp, _yukle(SYNC_PATH, "sap_sync_pull", mut))
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:   # cokme != FAIL
            yakalandi, kacan = True, ["yukleme hatasi: %s" % type(e).__name__]
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    print("\n--- yama-tuttu kanidi ---")
    yama_kirik = []
    for ad, hedef, mut in MUTASYONLAR:
        yol = RPP_PATH if hedef == "rpp" else SYNC_PATH
        ham = yol.read_text(encoding="utf-8")
        degisti = mut(ham) != ham
        print("  [%s] %s" % ("degisti" if degisti else "YAMA TUTMADI", ad))
        if not degisti:
            yama_kirik.append(ad)

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI (sahte-yesil riski): %s"
                  % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
