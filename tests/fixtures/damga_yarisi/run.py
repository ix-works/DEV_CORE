#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E-02 — `sap_sync_pull._stamp()` KILITSIZ oku-degistir-yaz: damga SESSIZCE kayboluyordu.

=== KOK ===
`_stamp` seans-tazelik store'unu (`.claude/.session_fresh.json`) OKUR, kendi objesini
EKLER, geri YAZAR. Bu dizi kilitsizdi. Iki kosum (paralel ajan · hook + elle pull ·
arka-plan tur) cakisirsa ikisi de AYNI store'u okur ve son yazan digerinin damgasini
SILER. Ustune `write_text` ATOMIK DEGILDIR: truncate ile yazma arasinda okuyan surec
YARIM JSON gorur -> tuketici `except: return False` dalina duser ve store'un TAMAMI
degersizlesir.

Kayip damga = "bu dosya canlidan cekildi" bilgisinin yok olmasi. `pull_before_edit`
(ADR 0016) tam da o bilgiye bakarak karar verir.

=== YON ANALIZI (fix'in tasarim gerekcesi) ===
Kayip damganin YONU guvenlidir: hook "taze degil" der, kullanici tekrar ceker.
TEHLIKELI yon SAHTE-TAZE damgadir (cekilmemis objeyi cekilmis sanmak). Bu yuzden
fix hicbir dalda sahte-taze uretmez; kilit alinamazsa bile GORUNUR uyari basar
(sessiz dusus dali YOK) ve bayat kilit KIRILIR (kalici kilitlenme = araci olduren
"erisilemez yesil"in kilit hali).

  D1 ⭐ AYIRT EDICI  determinist ic-ice damga: A'yi damgalarken B damgalanir -> IKISI DE durur
  S1 ⭐SINIR         bayat kilit (cokmus surec) KIRILIR -> arac kilitlenmez
  S4 ⭐SINIR         kilitte `PermissionError` (Windows delete-pending ikizi) = MESGUL, cokme DEGIL
  S2 ⭐SINIR         taze kilit alinamaz -> damga YINE yazilir + GORUNUR uyari (sessiz DEGIL)
  S3                yuk: 8 surec x 12 obje = 96 damga -> 96/96 (istatistiksel destek)
  A1                atomik yazim yapisal capasi (AST): `os.replace` VAR, `write_text` YOK
  A2                gurultu olcumu: 400 esz. okumada YARIM/bozuk JSON = 0
  N1 FP capasi      tek damga -> store SEKLI ayni (session_id/objects/UPPER anahtar/ISO)
  N2 FP capasi      farkli seans -> store SIFIRLANIR (mevcut semantik korunur)
  N3 FP capasi      bozuk store -> sifirdan yazilir (mevcut davranis korunur)
  N4 3.BAGLAM       TUKETICI `pull_before_edit._is_fresh` iki damgayi da TAZE goruyor
  N5 FP capasi      hijyen: `.tmp` ve `.lock` kalintisi YOK
  M1-M6             fix'i sok -> korpus KIRMIZI olmali

🔴 DOGRULANAMADI (durustluk siniri): "yazim atomiktir" iddiasi satir-ici yarista
DETERMINIST olarak olculemez (yazma tek `os.replace` cagrisidir; araya girecek seam
yok). A1 YAPISAL capadir, A2 ise gurultu olcumu — ikisi birlikte "atomik" iddiasinin
kanit tabanidir, tek baslarina degil.

Kosum: python tests/fixtures/damga_yarisi/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
SCRIPTS = REPO / "scripts"
HEDEF = SCRIPTS / "sap_sync_pull.py"
SID = "seans-E02"

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


# --- yardimcilar -------------------------------------------------------------
def _yukle(yol: Path, ad: str):
    """Modulu ADI DEGISTIRILMIS olarak yukle (mutant ile taban ayni surecte yasar).

    ⚠ STDOUT GASPI: hedef modul import ANINDA `sys.stdout`u `io.TextIOWrapper` ile
    SARAR (win32 UTF-8 zorlamasi). Ayni surecte IKINCI kez yuklenince ikinci sarmalayici
    kurulur; birincisi GC edilince ALTTAKI buffer'i KAPATIR -> kosucu "lost sys.stderr"
    ile coker ve MUTASYON HIC OLCULEMEZ. Sarmalayici `detach()` ile buffer'dan
    ayrilir (kapatmadan) ve orijinal akislar geri konur.
    """
    sys.modules.pop(ad, None)
    o_out, o_err = sys.stdout, sys.stderr
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
    sys.modules[ad] = mod
    try:
        spec.loader.exec_module(mod)                      # type: ignore[union-attr]
    finally:
        for yeni, eski in ((sys.stdout, o_out), (sys.stderr, o_err)):
            if yeni is not eski:
                try:
                    yeni.detach()
                except Exception:
                    pass
        sys.stdout, sys.stderr = o_out, o_err
    return mod


def _kum() -> Path:
    d = Path(tempfile.mkdtemp(prefix="e02_"))
    (d / ".claude").mkdir(parents=True, exist_ok=True)
    return d


def _bagla(mod, kum: Path):
    """Modul-duzeyi yollari KUMA cevir (uretim kodu env'den cozer; burada dogrudan)."""
    mod.ROOT = kum
    mod.FRESH_STORE = kum / ".claude" / ".session_fresh.json"
    return mod.FRESH_STORE


def _store(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _cocuk(kum: Path, modul_yolu: Path, kod: str, ek_env: dict | None = None):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(kum)
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(ek_env or {})
    on = (
        "import sys, importlib.util\n"
        f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
        f"_spec = importlib.util.spec_from_file_location('hedef_mod', {str(modul_yolu)!r})\n"
        "m = importlib.util.module_from_spec(_spec)\n"
        "sys.modules['hedef_mod'] = m\n"
        "_spec.loader.exec_module(m)\n"
    )
    return subprocess.Popen([sys.executable, "-c", on + kod], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


# =============================================================================
# D1 ⭐ AYIRT EDICI — determinist ic-ice damga
# =============================================================================
def d1_ic_ice(mod, modul_yolu: Path) -> None:
    """`_now_iso` seam'i: A damgalanirken B'yi damgalayan bir surec KOSAR ve BITER.

    Kilitsiz kodda A'nin okumasi B'nin yazimindan ONCEdir -> A'nin yazimi B'yi EZER.
    Kilitli kodda B, A kilidi birakana kadar bekler -> IKISI DE store'da olur.
    """
    kum = _kum()
    try:
        store = _bagla(mod, kum)
        hazir = kum / "cocuk_hazir"
        proc = {}

        gercek_now = mod._now_iso

        def _seam():
            if not proc:
                proc["p"] = _cocuk(kum, modul_yolu,
                                   "import pathlib\n"
                                   f"pathlib.Path({str(hazir)!r}).write_text('1')\n"
                                   f"m._stamp({SID!r}, 'ZOBJE_B')\n")
                bitis = time.monotonic() + 20
                while not hazir.exists() and time.monotonic() < bitis:
                    time.sleep(0.01)
                # Cocuk damgasini TAMAMLAYABILSIN diye pay birak: kilitsiz kodda
                # cocuk yazimi BITER ve ardindan ebeveynin yazimi onu EZER (determinist).
                time.sleep(0.6)
            return gercek_now()

        mod._now_iso = _seam
        try:
            mod._stamp(SID, "ZOBJE_A")
        finally:
            mod._now_iso = gercek_now
        p = proc.get("p")
        cocuk_cikti = ""
        if p is not None:
            cocuk_cikti = (p.communicate(timeout=60)[0] or "").strip()

        objeler = _store(store).get("objects", {})
        kontrol("D1 ⭐ ic ice damga: A ve B'nin IKISI de store'da (kayip guncelleme YOK)",
                "ZOBJE_A" in objeler and "ZOBJE_B" in objeler,
                f"objeler={sorted(objeler)} cocuk_cikti={cocuk_cikti[:200]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)


# =============================================================================
# S1/S2 ⭐SINIR — kilit kose durumlari (in-process, kisaltilmis sabitlerle)
# =============================================================================
def s1_bayat_kilit(mod) -> None:
    kum = _kum()
    try:
        store = _bagla(mod, kum)
        kilit = store.with_name(store.name + ".lock")
        kilit.write_text("999999", encoding="utf-8")
        eski = time.time() - 600
        os.utime(kilit, (eski, eski))          # cokmus surecten kalmis gibi
        z_eski, b_eski = mod._KILIT_ZAMAN_ASIMI_S, mod._KILIT_BAYAT_S
        mod._KILIT_ZAMAN_ASIMI_S, mod._KILIT_BAYAT_S = 3.0, 30.0
        t0 = time.monotonic()
        try:
            mod._stamp(SID, "ZOBJE_BAYAT")
        finally:
            mod._KILIT_ZAMAN_ASIMI_S, mod._KILIT_BAYAT_S = z_eski, b_eski
        gecen = time.monotonic() - t0
        kontrol("S1 ⭐SINIR bayat kilit KIRILIR (arac kalici kilitlenmez)",
                "ZOBJE_BAYAT" in _store(store).get("objects", {}) and gecen < 3.0,
                f"gecen={gecen:.2f}s objeler={sorted(_store(store).get('objects', {}))}")
        kontrol("S1b bayat kilit dosyasi ARDINDA BIRAKILMAZ", not kilit.exists(),
                f"kilit_var={kilit.exists()}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)


def s4_windows_ikizi(mod) -> None:
    """⭐SINIR — "kilit MESGUL" iki isimle gelir: Windows'ta `PermissionError`.

    Silinmesi BEKLEYEN (delete-pending) bir kilide `O_EXCL` ile acilinca Windows
    ERROR_ACCESS_DENIED verir -> Python `PermissionError` yapar, `FileExistsError`
    DEGIL. Yalniz `FileExistsError` yakalayan kilit yuksek eszamanlilikta `_stamp`i
    COKERTIR (olculdu 2026-08-28: 12 surec x 30 damga -> 14 cocuk cokmesi, 66 damga
    hic yazilamadi). Burada o dal DETERMINIST enjekte edilir.
    """
    kum = _kum()
    gercek_open = os.open
    try:
        store = _bagla(mod, kum)
        sayac = {"n": 0}

        def sahte_open(yol, bayrak, *a, **k):
            if str(yol).endswith(".lock") and sayac["n"] == 0:
                sayac["n"] = 1
                raise PermissionError(13, "delete pending (Windows ikizi)")
            return gercek_open(yol, bayrak, *a, **k)

        os.open = sahte_open                     # `mod.os` sureç-genelidir → finally'de geri
        try:
            mod._stamp(SID, "ZOBJE_IKIZ")
            coktu = ""
        except BaseException as exc:             # noqa: BLE001
            coktu = f"{type(exc).__name__}: {exc}"
        finally:
            os.open = gercek_open
        kontrol("S4 ⭐SINIR Windows ikizi: kilitte `PermissionError` MESGUL sayilir "
                "(cokme DEGIL)",
                not coktu and "ZOBJE_IKIZ" in _store(store).get("objects", {})
                and sayac["n"] == 1,
                f"coktu={coktu!r} enjekte={sayac['n']} "
                f"objeler={sorted(_store(store).get('objects', {}))}")
    finally:
        os.open = gercek_open
        shutil.rmtree(kum, ignore_errors=True)


def s2_taze_kilit(mod) -> None:
    kum = _kum()
    try:
        store = _bagla(mod, kum)
        kilit = store.with_name(store.name + ".lock")
        kilit.write_text("1234", encoding="utf-8")      # TAZE (bayat degil)
        z_eski = mod._KILIT_ZAMAN_ASIMI_S
        mod._KILIT_ZAMAN_ASIMI_S = 0.3
        import contextlib
        import io as _io
        tampon = _io.StringIO()
        try:
            with contextlib.redirect_stdout(tampon):
                mod._stamp(SID, "ZOBJE_KILITLI")
        finally:
            mod._KILIT_ZAMAN_ASIMI_S = z_eski
        cikti = tampon.getvalue()
        yazildi = "ZOBJE_KILITLI" in _store(store).get("objects", {})
        kontrol("S2 ⭐SINIR kilit alinamadi -> damga YAZILDI *ve* GORUNUR uyari basildi "
                "(sessiz dusus YOK)",
                yazildi and "DAMGA KİLİDİ ALINAMADI" in cikti,
                f"yazildi={yazildi} cikti={cikti.strip()[:160]!r}")
        kontrol("S2b baskasinin kilidi SILINMEDI (kilit sahipligi ihlal edilmiyor)",
                kilit.exists(), f"kilit_var={kilit.exists()}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)


# =============================================================================
# S3 — yuk testi (8 surec x 12 obje)
# =============================================================================
def s3_yuk(kum_modul_yolu: Path) -> None:
    kum = _kum()
    try:
        store = kum / ".claude" / ".session_fresh.json"
        surecler = [
            _cocuk(kum, kum_modul_yolu,
                   f"for i in range(12): m._stamp({SID!r}, 'ZP{w}_%03d' % i)\n")
            for w in range(8)
        ]
        ciktilar = [(p.communicate(timeout=180)[0] or "") for p in surecler]
        objeler = _store(store).get("objects", {})
        kontrol("S3 yuk: 8 surec x 12 obje -> 96/96 damga korundu (cocuk cokmesi YOK)",
                len(objeler) == 96 and not any(c.strip() for c in ciktilar),
                f"korunan={len(objeler)}/96 eksik_ornek="
                f"{sorted({f'ZP{w}_%03d' % i for w in range(8) for i in range(12)} - set(objeler))[:6]} "
                f"cocuk_cikti={''.join(ciktilar)[:200]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)


# =============================================================================
# A1/A2 — atomik yazim (yapisal capa + gurultu olcumu)
# =============================================================================
def a1_yapisal(modul_yolu: Path) -> None:
    import ast
    agac = ast.parse(modul_yolu.read_text(encoding="utf-8"))
    yazicilar = [f for f in ast.walk(agac)
                 if isinstance(f, ast.FunctionDef) and f.name in ("_store_yaz", "_stamp")]
    kaynak = "\n".join(ast.dump(f) for f in yazicilar)
    replace_var = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "replace" and getattr(n.func.value, "id", "") == "os"
        for f in yazicilar for n in ast.walk(f))
    write_text_var = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "write_text"
        for f in yazicilar for n in ast.walk(f))
    kontrol("A1 yapisal: damga yazimi `os.replace` ile ATOMIK, `write_text` YOK",
            replace_var and not write_text_var and bool(yazicilar),
            f"os.replace={replace_var} write_text={write_text_var} "
            f"fonksiyon={[f.name for f in yazicilar]} ({len(kaynak)} bayt AST)")


def a2_gurultu(modul_yolu: Path) -> None:
    kum = _kum()
    try:
        store = kum / ".claude" / ".session_fresh.json"
        p = _cocuk(kum, modul_yolu,
                   f"for i in range(200): m._stamp({SID!r}, 'ZG_%03d' % i)\n")
        bozuk, okuma = 0, 0
        while p.poll() is None and okuma < 400:
            okuma += 1
            try:
                ham = store.read_text(encoding="utf-8")
            except OSError:
                continue
            if not ham:
                continue
            try:
                json.loads(ham)
            except Exception:
                bozuk += 1
        p.communicate(timeout=180)
        kontrol("A2 gurultu: esz. okumalarda YARIM/bozuk JSON = 0",
                bozuk == 0, f"bozuk={bozuk}/{okuma} okuma")
    finally:
        shutil.rmtree(kum, ignore_errors=True)


# =============================================================================
# N1-N5 — FP capalari + 3. BAGLAM (tuketici)
# =============================================================================
def n_fp(mod, modul_yolu: Path) -> None:
    kum = _kum()
    try:
        store = _bagla(mod, kum)
        mod._stamp(SID, "zobje_kucuk")
        s = _store(store)
        kontrol("N1 FP capasi: store SEKLI degismedi (session_id + objects + UPPER + ISO)",
                s.get("session_id") == SID and list(s.get("objects", {})) == ["ZOBJE_KUCUK"]
                and str(s["objects"]["ZOBJE_KUCUK"]).endswith("Z"),
                f"store={s}")

        mod._stamp("BASKA-SEANS", "ZOBJE_YENI")
        s = _store(store)
        kontrol("N2 FP capasi: farkli seans -> store SIFIRLANIR (mevcut semantik)",
                s.get("session_id") == "BASKA-SEANS"
                and list(s.get("objects", {})) == ["ZOBJE_YENI"],
                f"store={s}")

        store.write_text("{bozuk json", encoding="utf-8")
        mod._stamp(SID, "ZOBJE_SIFIRDAN")
        s = _store(store)
        kontrol("N3 FP capasi: bozuk store -> sifirdan yazilir (mevcut davranis)",
                s.get("session_id") == SID and "ZOBJE_SIFIRDAN" in s.get("objects", {}),
                f"store={s}")

        kalinti = [p.name for p in (kum / ".claude").iterdir()
                   if p.name != ".session_fresh.json"]
        kontrol("N5 FP capasi: hijyen — `.tmp`/`.lock` kalintisi YOK", not kalinti,
                f"kalinti={kalinti}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)


def n4_tuketici(modul_yolu: Path) -> None:
    """3. BAGLAM (gorev-DISI): damgayi YAZAN degil OKUYAN modul — `pull_before_edit`."""
    kum = _kum()
    try:
        p1 = _cocuk(kum, modul_yolu, f"m._stamp({SID!r}, 'ZTUK_BIR')\n")
        p2 = _cocuk(kum, modul_yolu, f"m._stamp({SID!r}, 'ZTUK_IKI')\n")
        p1.communicate(timeout=120)
        p2.communicate(timeout=120)
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(kum)
        env["PYTHONIOENCODING"] = "utf-8"
        kod = (
            "import sys, importlib.util\n"
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            f"_s = importlib.util.spec_from_file_location('pbe', {str(SCRIPTS / 'hooks' / 'pull_before_edit.py')!r})\n"
            "h = importlib.util.module_from_spec(_s)\n"
            "sys.modules['pbe'] = h\n"
            "_s.loader.exec_module(h)\n"
            f"print(h._is_fresh({SID!r}, 'ZTUK_BIR'), h._is_fresh({SID!r}, 'ZTUK_IKI'))\n"
        )
        r = subprocess.run([sys.executable, "-c", kod], env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=120)
        cikti = (r.stdout or "").strip().splitlines()[-1:] or [""]
        kontrol("N4 3.BAGLAM tuketici `pull_before_edit._is_fresh` IKI damgayi da TAZE goruyor",
                cikti[0].strip() == "True True",
                f"cikti={cikti[0]!r} stderr={(r.stderr or '').strip()[:200]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)


def korpus(modul_yolu: Path, ad: str) -> list[tuple[str, bool, str]]:
    global SONUC
    SONUC = []
    mod = _yukle(modul_yolu, ad)
    for bolum in ((lambda: d1_ic_ice(mod, modul_yolu)),
                  (lambda: s1_bayat_kilit(mod)),
                  (lambda: s2_taze_kilit(mod)),
                  (lambda: s4_windows_ikizi(mod)),
                  (lambda: s3_yuk(modul_yolu)),
                  (lambda: a1_yapisal(modul_yolu)),
                  (lambda: a2_gurultu(modul_yolu)),
                  (lambda: n_fp(mod, modul_yolu)),
                  (lambda: n4_tuketici(modul_yolu))):
        try:
            bolum()
        except BaseException as exc:                          # noqa: BLE001
            # ⛔ COKME != FAIL: patlayan bolum ADIYLA FAIL yazilir (kanit uretilemedi).
            kontrol(f"[BOLUM COKTU] {getattr(bolum, '__name__', 'bolum')}", False,
                    f"{type(exc).__name__}: {str(exc)[:200]}")
    return SONUC


# --- MUTASYONLAR: her biri korpusu KIRMIZI yapmali --------------------------
_KILITLI_STAMP = '''    with _store_kilidi() as kilit_uyarisi:
        try:
            store = json.loads(FRESH_STORE.read_text(encoding="utf-8"))
        except Exception:
            store = {}
        if not isinstance(store, dict):   # bozuk/yabancı şekil (liste, dize) → sıfırdan
            store = {}
        if store.get("session_id") != session_id:
            store = {"session_id": session_id, "objects": {}}
        store.setdefault("objects", {})[obj.upper()] = _now_iso()
        _store_yaz(store)
    if kilit_uyarisi:
        print(kilit_uyarisi)'''

_KUSURUN_ESKI_HALI = '''    try:
        store = json.loads(FRESH_STORE.read_text(encoding="utf-8"))
    except Exception:
        store = {}
    if store.get("session_id") != session_id:
        store = {"session_id": session_id, "objects": {}}
    store.setdefault("objects", {})[obj.upper()] = _now_iso()
    FRESH_STORE.parent.mkdir(parents=True, exist_ok=True)
    FRESH_STORE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")'''

_OKUMA_KILIT_DISINDA = '''    try:
        store = json.loads(FRESH_STORE.read_text(encoding="utf-8"))
    except Exception:
        store = {}
    if not isinstance(store, dict):
        store = {}
    with _store_kilidi() as kilit_uyarisi:
        if store.get("session_id") != session_id:
            store = {"session_id": session_id, "objects": {}}
        store.setdefault("objects", {})[obj.upper()] = _now_iso()
        _store_yaz(store)
    if kilit_uyarisi:
        print(kilit_uyarisi)'''

MUTASYONLAR = [
    ("M1 kusurun BIREBIR eski hali: kilitsiz oku-degistir-yaz + write_text",
     lambda s: s.replace(_KILITLI_STAMP, _KUSURUN_ESKI_HALI)),
    ("M2 ⭐SINIR yarim-fix: kilit VAR ama OKUMA kilidin DISINDA (kayip guncelleme geri gelir)",
     lambda s: s.replace(_KILITLI_STAMP, _OKUMA_KILIT_DISINDA)),
    ("M3 ⭐SINIR bayat-kilit kirma dalini kaldir (arac kalici kilitlenir)",
     lambda s: s.replace(
         "        if bayat:\n"
         "            # Çökmüş/öldürülmüş süreçten kalan kilit ARACI KALICI OLARAK\n"
         "            # kilitlerdi (erişilemez-yeşil sınıfının kilit hâli) → kır.\n"
         "            with contextlib.suppress(OSError):\n"
         "                kilit.unlink()\n"
         "            continue\n",
         "        if bayat:\n"
         "            pass\n")),
    ("M4 ⭐SINIR kilit-zaman-asimi uyarisini SESSIZCE yut (sessiz dusus)",
     lambda s: s.replace(
         '            uyari = ("[!] DAMGA KİLİDİ ALINAMADI (%.0fs) — başka bir pull koşuyor "',
         '            uyari = None or ("" and "[!] DAMGA KİLİDİ ALINAMADI (%.0fs) — başka bir pull koşuyor "')),
    ("M5 atomik yazimi `write_text`e dondur (yarim JSON yeniden mumkun)",
     lambda s: s.replace(
         '    FRESH_STORE.parent.mkdir(parents=True, exist_ok=True)\n'
         '    fd, gecici = tempfile.mkstemp(dir=str(FRESH_STORE.parent),\n',
         '    FRESH_STORE.parent.mkdir(parents=True, exist_ok=True)\n'
         '    FRESH_STORE.write_text(json.dumps(store, ensure_ascii=False, indent=2),\n'
         '                           encoding="utf-8")\n'
         '    return\n'
         '    fd, gecici = tempfile.mkstemp(dir=str(FRESH_STORE.parent),\n')),
    ("M6 ⭐SINIR kilit `PermissionError`i MESGUL saymaz (Windows ikizi geri gelir)",
     lambda s: s.replace(
         "        except (FileExistsError, PermissionError):\n",
         "        except FileExistsError:\n")),
]


def main() -> int:
    print("=" * 78)
    print("damga_yarisi — E-02: seans-tazelik damgasi eszamanli yazimda KAYBOLUYORDU")
    print("=" * 78)
    if not HEDEF.is_file():
        print(f"FAIL — hedef yok: {HEDEF}")
        return 1
    ham = HEDEF.read_text(encoding="utf-8")

    sonuc = korpus(HEDEF, "hedef_taban")
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok or os.environ.get("IX_FIXTURE_VERBOSE"):
            print("         -> %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    # ⚠ Mutant GERCEK `scripts/` dizininde yasar: modul komsu yollari (utils/) kendi
    # konumundan cozer; tempdir'e kopyalanirsa import patlar ve her mutasyon
    # "yakalandi" gorunur (SAHTE-KIRMIZI). Kum yalniz VERI icindir.
    mutant = SCRIPTS / "_mutant_sap_sync_pull.py"
    mut_kirik, yama_kirik, kurulamadi = [], [], []
    for i, (ad, mut) in enumerate(MUTASYONLAR):
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        try:
            mutant.write_text(bozuk, encoding="utf-8", newline="\n")
            m_res = korpus(mutant, "hedef_mutant_%d" % i)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:                            # noqa: BLE001
            # ⛔ KURULAMADI != KACTI: olcum HIC yapilamamistir; korpusun zayifligi
            #    SONUCU CIKARILAMAZ. Ucuncu deger olarak ayri raporlanir.
            kurulamadi.append("%s -> %s: %s" % (ad, type(e).__name__, e))
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
            continue
        finally:
            mutant.unlink(missing_ok=True)
        print("  [%s] %s" % ("YAKALANDI" if kacan else "KACTI", ad))
        if kacan:
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
