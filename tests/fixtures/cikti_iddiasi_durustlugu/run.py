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
   (2026-08-20) Yalniz `/source/main` cekiliyordu; `.ccimp/.ccau/.ccdef/.ccmac` AYRI ADT
   uclarindadir ve HIC okunmuyordu. Damga obje ADINA yazildigi icin kapi alt-include'u
   da TAZE sayiyordu => BAYAT `.ccimp` taze sanilip duzenlenebiliyordu. O gun cekme yolu
   BILEREK kurulmadi (segmentler olculmemisti) ve bosluk "CEKILMEDI" uyarisiyla GORUNUR
   kilindi. Q283 (2026-09-13) segmentleri olctu; Q352 (2026-09-26) yeniden olcup cekme
   yolunu kurdu: her alt-include KENDI ucundan cekilir ve DOSYA anahtariyla AYRI damgalanir.
   Iddia AYNI kaldi, vektorler yeni koda gore yeniden yazildi (vektor silinmedi):
   cekilen -> [OK] + damga · cekilemeyen (404/istisna/KORUMA) -> "CEKILMEDI" + damga YOK
   + rc=1 · alt-include yoksa SESSIZ.

DEGISMEZ (ikisinde de ayni): cikti, kodun yapabildiginden fazlasini SOYLEMEZ;
yapamadigini da SESSIZ GECMEZ.

  A1-A4  pretty printer: basari/hata metni + docstring + YAZMA-YOK yapisal capasi
  B1-B6  sync_pull: cekilen [OK]+damga · cekilemeyen CEKILMEDI+damga yok+rc1 · yoksa
         SESSIZ · anahtar/marker TEK KAYNAK · istisna ve KORUMA dali · kablolama
  M1-M4  fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/cikti_iddiasi_durustlugu/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import io
import os
import shutil
import stat
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


def _sil(d: Path) -> None:
    """Q319: Windows'ta salt-okur girdi `rmtree(ignore_errors=True)` ile SESSİZCE kalır."""
    def _ac(func, path, _exc):                       # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)                       # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


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
        mod.__kaynak__ = src   # AST vektorleri MUTANT metni okur (diskteki degil)
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
    # `_sinif_includelari` GERCEK kodla kosar; yalniz AG (sap_adt_lib.sync_repo_from_live)
    # ve STORE yazimi (_stamp -> kaydedici) sahtedir. Repo taramasi GERCEK
    # `find_repo_class_includes` (kok = kum) -> komsu sinif eslemesi de olculur.
    import source_drift as _sd

    def _kos(obj, kum, davranis):
        """davranis: dosya-adi -> 'yaz' | '404' | 'istisna' | 'dirty'. -> (rc, cikti, damgalar)."""
        damgalar = []
        sahte = types.ModuleType("sap_adt_lib")

        def _sync(object_url, object_name, object_type, client=None, force=False, repo_file=None):
            d = davranis.get(Path(repo_file).name, "404")
            if d == "yaz":
                return {"written": True, "repo_path": str(repo_file), "url": object_url}
            if d == "istisna":
                raise ConnectionError("ag yok")
            if d == "dirty":
                return {"written": False, "blocked_dirty": True, "repo_path": str(repo_file),
                        "reason": "commit'siz yerel degisiklik"}
            return {"written": False, "repo_path": str(repo_file), "reason": "404 obje yok"}

        sahte.sync_repo_from_live = _sync
        eski_mod = sys.modules.get("sap_adt_lib")
        eski_bul = _sd.find_repo_class_includes
        eski_stamp = _sd._stamp        # store YAZIMI source_drift'te (Q352 arayuz)
        sys.modules["sap_adt_lib"] = sahte
        _sd.find_repo_class_includes = lambda ad, erp_root=None: eski_bul(ad, kum)
        _sd._stamp = lambda sid, anahtar: damgalar.append(anahtar)
        tut, saved = io.StringIO(), sys.stdout
        sys.stdout = tut
        try:
            rc = sync._sinif_includelari(obj, "fx-sid", object(), False)
        finally:
            sys.stdout = saved
            _sd._stamp = eski_stamp
            _sd.find_repo_class_includes = eski_bul
            if eski_mod is None:
                sys.modules.pop("sap_adt_lib", None)
            else:
                sys.modules["sap_adt_lib"] = eski_mod
        return rc, tut.getvalue(), damgalar

    def _anahtar(f):
        return _sd.tazelik_anahtari(f, sync.ROOT)

    # Q319: senaryolar() kosum basina birden cok kez cagrilir; kum finally'de silinir.
    tmp = Path(tempfile.mkdtemp(prefix="sync_alt_"))
    try:
        (tmp / "ZCL_TEST.clas.abap").write_text("CLASS zcl_test.\n", encoding="utf-8")
        imp = tmp / "ZCL_TEST.ccimp.abap"
        tst = tmp / "ZCL_TEST.ccau.abap"
        imp.write_text("* impl\n", encoding="utf-8")
        tst.write_text("* test\n", encoding="utf-8")
        (tmp / "ZCL_BASKA.ccimp.abap").write_text("* baska sinif\n", encoding="utf-8")  # FP capasi

        # B1: biri cekildi, biri 404 -> cekilen [OK]+damga; cekilemeyen CEKILMEDI+damga YOK+rc1
        rc, c, dm = _kos("ZCL_TEST", tmp, {imp.name: "yaz", tst.name: "404"})
        ekle("B1 cekilen [OK]+DAMGA · 404 alan 'CEKILMEDI'+damga YOK · rc=1 · komsu sinif yok",
             rc == 1 and "[OK] ZCL_TEST (implementations)" in c
             and "ALT-INCLUDE ÇEKİLMEDİ: ZCL_TEST.ccau.abap" in c
             and "ALT-INCLUDE ÇEKİLMEDİ: ZCL_TEST.ccimp.abap" not in c
             and dm == [_anahtar(imp)] and "ZCL_BASKA" not in c,
             "rc=%s damgalar=%s cikti=%r" % (rc, dm, c[-200:]))

        # B4: ag istisnasi -> cokmez, 'CEKILMEDI' der, damga YOK, rc1 (yapilmayan iddia edilmez)
        rc, c, dm = _kos("ZCL_TEST", tmp, {imp.name: "istisna", tst.name: "istisna"})
        ekle("B4 ag istisnasi: iki include da 'CEKILMEDI' · damga YOK · rc=1",
             rc == 1 and c.count("ALT-INCLUDE ÇEKİLMEDİ") == 2 and dm == [] and "[OK]" not in c,
             "rc=%s damgalar=%s" % (rc, dm))

        # B6: KORUMA (commit'siz yerel is) -> EZILMEDI, damga YOK, 'CEKILMEDI'
        rc, c, dm = _kos("ZCL_TEST", tmp, {imp.name: "dirty", tst.name: "yaz"})
        ekle("B6 KORUMA dali: dirty include damgalanmaz + adlandirilir; kardesi cekilir",
             rc == 1 and "[KORUMA]" in c and "ALT-INCLUDE ÇEKİLMEDİ: ZCL_TEST.ccimp.abap" in c
             and dm == [_anahtar(tst)],
             "rc=%s damgalar=%s" % (rc, dm))
    finally:
        _sil(tmp)

    # B2: alt-include YOK -> SESSIZ, rc0, damga yok (FP capasi, B1'den AYRI)
    tmp2 = Path(tempfile.mkdtemp(prefix="sync_yalin_"))
    try:
        (tmp2 / "ZCL_YALIN.clas.abap").write_text("CLASS zcl_yalin.\n", encoding="utf-8")
        rc, c, dm = _kos("ZCL_YALIN", tmp2, {})
        ekle("B2 alt-include YOK: hicbir sey basilmaz, rc=0, damga yok (gurultu yok)",
             rc == 0 and c == "" and dm == [], "rc=%s gorulen=%r" % (rc, c[:80]))
    finally:
        _sil(tmp2)

    # B3: TEK KAYNAK — sap_sync_pull'da alt-include son-eki LITERALI yok; damga anahtari
    # kapinin okudugu fonksiyondan (source_drift.tazelik_anahtari) gelir (AST).
    sync_src = getattr(sync, "__kaynak__", None) or SYNC_PATH.read_text(encoding="utf-8")
    literal = [m for m in ('.ccimp.abap"', ".ccimp.abap'", '.ccau.abap"', ".ccau.abap'")
               if m in sync_src]
    kablolu = _kablolu_mu(sync_src, "_damgala", "tazelik_damgala")
    ekle("B3 tek kaynak: marker literali YOK + _damgala source_drift.tazelik_damgala'yi cagirir (AST)",
         not literal and kablolu, "literal=%s kablolu=%s" % (literal, kablolu))

    # B5: KABLOLAMA (kod != kablolama) — main() alt-include cekmesini GERCEKTEN cagiriyor mu
    ekle("B5 kablolama: main() icinde _sinif_includelari cagrisi var (AST)",
         _kablolu_mu(sync_src, "main", "_sinif_includelari"),
         "main() govdesinde cagri bulunamadi")

    return out


MUTASYONLAR = [
    ("M1 basari metnini 'applied to'ya geri dondur (A: iddia degismezi)",
     "rpp",
     lambda s: s.replace('f"[OK] Bicimlenmis kaynak DONDU: {args.object_name} '
                         '({len(result)} karakter)"',
                         'f"[OK] Pretty printer applied to: {args.object_name}"')),
    ("M2 alt-include cekmesini main()'den sok (B: kablolama degismezi)",
     "sync-ast",
     # main()'deki HER çağrı sökülür (ana dal + `--type auto` sınıf dalı). Eski düz-metin çapası
     # iki satırı ortak son-ek sayesinde birlikte vuruyordu; takip turu 1 (2026-09-26) çağrıya
     # `kardes_koku` ekleyince girinti farkı ortak son-eki bozdu → tek satır sökülüp M2 KAÇTI.
     # Desen girintiden bağımsız: `rc = max(rc, _sinif_includelari(...))` → `pass`.
     lambda s: __import__("re").sub(
         r"rc = max\(rc, _sinif_includelari\([^()]*\)\)", "pass", s)),
    ("M3 damga anahtarini YEREL kurala cevir (B: tek-kaynak degismezi)",
     "sync",
     lambda s: s.replace("    return tazelik_damgala(session, repo_path, ROOT)\n",
                         "    from source_drift import _stamp\n"
                         "    anahtar = Path(repo_path).name.split('.', 1)[0].upper()\n"
                         "    _stamp(session, anahtar)\n"
                         "    return anahtar\n")),
    ("M4 yazilmayani da damgala (B: 'cekilmeyen cekildi denmez' degismezi)",
     "sync",
     lambda s: s.replace('    if not res.get("written"):\n', "    if False:\n")),
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
                # M2 main() govdesini bozar (AST), M3/M4 yardimcilari (davranis).
                if hedef == "sync-ast":
                    # KABLOLAMA mutasyonu: cagri main()'den sokuldu mu (AST).
                    bozuk = mut(SYNC_PATH.read_text(encoding="utf-8"))
                    m_res = [("B5 kablolama: main() icinde _sinif_includelari cagrisi",
                              _kablolu_mu(bozuk, "main", "_sinif_includelari"),
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
