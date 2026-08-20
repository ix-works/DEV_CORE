#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K4 — conn fixture'i KUM DISINA yaziyordu: KALINTI degil, VERI KAYBI.

=== OLCULMUS MEKANIZMA (2026-08-20, repro edildi) ===
`conn_yazici_encoding` fixture'i izolasyon icin `CLAUDE_PROJECT_DIR`+`chdir` kullaniyordu.
IKISI DE YETMEZ. `sap_adt_lib.find_conn_file()` adaylari *"dosyanin VAR OLDUGU ilk yer"*
diye secer — env yalnizca ORADA dosya VARSA kazanir. Git-bash `PWD`yi repo koküne kurar;
repo kokunde bir `.conn_adt` VARSA (suitin `populate_tables_unit_kind` korpusu import
yan-etkisiyle bir sablon yazar) hedef ORAYA kayar ve fixture'in V4 vektoru

    create_conn_file("https://ornek.gecerli:44300", "TEST_USER", "pÄrola-üğş", ...)

**KULLANICININ GERCEK `.conn_adt` DOSYASINI EZER.** Olculdu: 78 B gercek -> 522 B sentetik.
(Kayit 522 B'lik artigi bulmus ama olusum anini kanitlayamamisti; bu tur kanitladi.)

⚠ SUITIN HIJYENI BUNU KURTARMIYORDU: `_ortam_hijyeni_bitir` "kosumdan once vardi"
   gordugu icin dosyaya DOKUNMUYOR — yani ezilmis dosya oldugu gibi kaliyor. Dosya
   gitignored oldugu icin `git status` da sessiz. Kayip GORUNMEZDI.

=== IKI KATMAN -> IKI MUTASYON ===
① ONLEME (fixture): `set_explicit_working_dir(KUM)` + kacak env'leri temizle +
  **yazmadan ONCE** hedefin kumda oldugunu KANITLA (degilse yazmadan `sys.exit(1)`).
② TESPIT (suit): kosum oncesi/sonrasi `.conn_adt` IMZASI kiyaslanir; degistiyse
  `⛔ VERİ KAYBI` basar. ① bir gun bozulursa ② sessiz birakmaz.
Tek katmanli mutasyon ISKALAR (savunma derinligi) — M1 ikisini BIRDEN soker.

  P1 ⭐ AYIRT EDICI  sahte repo kokunde `.conn_adt` VARKEN fixture kosar -> dosya DEGISMEZ
  P2               fixture yine 7/7 PASS (izolasyon olcumu bozmadi)
  W1 KABLOLAMA     fixture: `set_explicit_working_dir` + PWD temizligi + KUM-DISI capasi (AST)
  L1 ⭐ 2.KATMAN    suit, EZILEN bir `.conn_adt`yi `⛔ VERİ KAYBI` diye bildirir
  L2 FP capasi     dosya DEGISMEDIYSE uyari YOK (alarm yorgunlugu)
  L3 FP capasi     kosum oncesi dosya YOKKEN suitin URETTIGI kalinti yine SILINIR
  M1-M4            fix'i sok -> korpus KIRMIZI olmali (M4: UC katmani birden)

⛔ GERCEK repo koküne DOKUNULMAZ: P1 sahte bir kok kurar ve `PWD`yi ona yoneltir
   (kacisin gercek tetikleyicisi buydu). Korpus kendi olctugu agaci kirletmez.

Kosum: python tests/fixtures/conn_kum_sizintisi/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
FIXTURE = KOK / "tests" / "fixtures" / "conn_yazici_encoding" / "run.py"
KOSUCU = KOK / "tests" / "run_fixture_tests.py"

GERCEK_CONN = ("ADT_SAP_URL=https://kullanicininki:44300\n"
               "ADT_SAP_USER=GERCEK\nADT_SAP_TIER=DEV\n")


def _sha(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


def _kosucu_modulu(src: str | None = None):
    """run_fixture_tests'i MODUL olarak yukle (main() calismaz — hijyen fonksiyonlarini olceriz).

    ⛔ 2026-08-20 DERSI: mutasyon KOSUCUNUN KENDI DOSYASINA yazilmaz. Bu korpus
    SUIT tarafindan kosulur; kosmakta olan kosucuyu diskte degistirmek, art arda
    kosumlarda kalinti birakip KOMSU korpuslari kirletir (yasandi). Mutasyonlu
    surum BELLEKTE exec edilir; disk DOKUNULMADAN kalir.
    """
    import types
    if src is None:
        src = KOSUCU.read_text(encoding="utf-8")
    mod = types.ModuleType("_k4_kosucu")
    mod.__file__ = str(KOSUCU)
    sys.modules["_k4_kosucu"] = mod
    exec(compile(src, str(KOSUCU), "exec"), mod.__dict__)
    return mod


def senaryolar(fixture: Path, kosucu_src: str | None = None) -> list[tuple[str, bool, str]]:
    r: list[tuple[str, bool, str]] = []

    def ekle(ad: str, ok: bool, detay: str = "") -> None:
        r.append((ad, ok, detay))

    # --- P1/P2: SAHTE repo koku + PWD kacisi ---------------------------------
    sahte = Path(tempfile.mkdtemp(prefix="k4kok_"))
    try:
        conn = sahte / ".conn_adt"
        conn.write_text(GERCEK_CONN, encoding="utf-8")
        once_sha, once_boy = _sha(conn), conn.stat().st_size

        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PWD"] = str(sahte)            # ⭐ kacisin GERCEK tetikleyicisi
        env.pop("CLAUDE_PROJECT_DIR", None)
        env.pop("IX_CORE_ROOT", None)
        p = subprocess.run([sys.executable, str(fixture)], cwd=str(sahte), env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
        out = (p.stdout or "") + (p.stderr or "")
        sonra_sha = _sha(conn) if conn.exists() else "<SILINDI>"
        ekle("P1 ⭐ sahte repo kokundeki `.conn_adt` DEGISMEDI (fix oncesi 522 B ile EZILIRDI)",
             sonra_sha == once_sha,
             f"once={once_boy}B/{once_sha[:12]} sonra={conn.stat().st_size if conn.exists() else 0}B/"
             f"{sonra_sha[:12]} · fixture rc={p.returncode}")
        ekle("P2 fixture yine 7/7 PASS (izolasyon olcumu bozmadi)",
             p.returncode == 0 and "7/7 OK" in out, f"rc={p.returncode} · {out.strip()[-200:]!r}")
    finally:
        shutil.rmtree(sahte, ignore_errors=True)

    # --- W1: KABLOLAMA (AST + hedefli metin) ---------------------------------
    src = fixture.read_text(encoding="utf-8")
    agac = ast.parse(src)
    explicit = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr == "set_explicit_working_dir"
                   for n in ast.walk(agac))
    capa = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "is_relative_to"
               for n in ast.walk(agac))
    pwd_temiz = any(isinstance(n, ast.Constant) and n.value == "PWD" for n in ast.walk(agac))
    ekle("W1 KABLOLAMA: fixture `set_explicit_working_dir` + KUM-DISI capasi "
         "(`is_relative_to`) + PWD temizligi tasiyor (AST)",
         explicit and capa and pwd_temiz,
         f"explicit={explicit} capa={capa} pwd={pwd_temiz}")

    # --- L1/L2/L3: IKINCI KATMAN (suit hijyeni) ------------------------------
    import contextlib
    import io

    mod = _kosucu_modulu(kosucu_src)
    kum = Path(tempfile.mkdtemp(prefix="k4h_"))
    try:
        sahte_conn = kum / ".conn_adt"
        eski_conn = mod._CONN
        mod._CONN = sahte_conn            # gercek repo koküne DOKUNMA
        try:
            # L1: kosum ONCESI vardi, SONRA degisti -> VERI KAYBI bildirilir
            sahte_conn.write_text(GERCEK_CONN, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                onceki = mod._ortam_hijyeni_basla()
            sahte_conn.write_text("EZILDI=1\n", encoding="utf-8")
            tampon = io.StringIO()
            with contextlib.redirect_stdout(tampon):
                mod._ortam_hijyeni_bitir(onceki)
            cikti = tampon.getvalue()
            ekle("L1 ⭐ 2.KATMAN: EZILEN `.conn_adt` `⛔ VERİ KAYBI` diye bildiriliyor",
                 "VERİ KAYBI" in cikti, repr(cikti[:220]))
            ekle("L1b ezilen dosya SILINMIYOR (kullanicinin verisi — karar ONUN)",
                 sahte_conn.exists(), f"var={sahte_conn.exists()}")

            # L2 FP capasi: degismediyse uyari YOK
            sahte_conn.write_text(GERCEK_CONN, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                onceki = mod._ortam_hijyeni_basla()
            tampon = io.StringIO()
            with contextlib.redirect_stdout(tampon):
                mod._ortam_hijyeni_bitir(onceki)
            ekle("L2 FP capasi: dosya DEGISMEDIYSE `VERİ KAYBI` uyarisi YOK",
                 "VERİ KAYBI" not in tampon.getvalue(), repr(tampon.getvalue()[:220]))

            # L3 FP capasi: once YOKTU, suit uretti -> yine SILINIR (eski davranis korundu)
            sahte_conn.unlink(missing_ok=True)
            with contextlib.redirect_stdout(io.StringIO()):
                onceki = mod._ortam_hijyeni_basla()
            sahte_conn.write_text("SUIT-URETTI=1\n", encoding="utf-8")
            tampon = io.StringIO()
            with contextlib.redirect_stdout(tampon):
                mod._ortam_hijyeni_bitir(onceki)
            ekle("L3 FP capasi: once YOKKEN suitin URETTIGI kalinti yine SILINIR",
                 not sahte_conn.exists(), f"var={sahte_conn.exists()} · {tampon.getvalue()[:160]!r}")
        finally:
            mod._CONN = eski_conn
    finally:
        shutil.rmtree(kum, ignore_errors=True)
        sys.modules.pop("_k4_kosucu", None)
    return r


MUTASYONLAR = [
    # ⚠ TEK KATMANLI mutasyon ISKALAR: `set_explicit_working_dir` kaldirilsa bile
    #    PWD temizligi kacisi engeller. Fix'i SOKMEK ikisini BIRDEN kaldirmaktir.
    ("M1 ONLEMEYI TUMDEN sok (explicit-dir + PWD temizligi) -> kacis geri gelir", "fixture",
     lambda s: s.replace(
         'for _kacak in ("PWD", "CLAUDE_CWD", "INIT_CWD", "COPILOT_CWD"):\n'
         '    os.environ.pop(_kacak, None)\n', ""
     ).replace(
         "L.set_explicit_working_dir(KUM)     # kütüphanenin belgelenmiş izolasyon kancası\n",
         "")),
    ("M2 KUM-DISI capasini sok (yazmadan durma korumasi)", "fixture",
     lambda s: s.replace(
         "if not HEDEF.resolve().is_relative_to(KUM.resolve()):",
         "if False:")),
    ("M3 ⭐2.KATMAN: suit imza kiyasini sok (ezilme SESSIZ kalir)", "kosucu",
     lambda s: s.replace(
         "        if simdiki[0] and simdiki[2] != onceki[2]:",
         "        if False:")),
    # ⚠ M4 OLMADAN P1 OLU BIR VEKTORDU: M1/M2 tek baslarina veri kaybi URETMEZ —
    #   onleme dusse bile KUM-DISI capasi fixture'i YAZMADAN durdurur (gurultulu
    #   basarisizlik, sessiz kayip degil). P1'in gercekten FALSIFIYE EDILEBILIR
    #   oldugunu ancak UC KATMANI BIRDEN soken bu mutasyon gosterir; yoksa P1
    #   "hicbir zaman kirilmayan yesil" olurdu (erisilemez yesil = olu capa).
    ("M4 ⭐UC KATMANI BIRDEN sok -> GERCEK veri kaybi geri gelir (P1 kirmizi yanmali)",
     "fixture",
     lambda s: s.replace(
         'for _kacak in ("PWD", "CLAUDE_CWD", "INIT_CWD", "COPILOT_CWD"):\n'
         '    os.environ.pop(_kacak, None)\n', ""
     ).replace(
         "L.set_explicit_working_dir(KUM)     # kütüphanenin belgelenmiş izolasyon kancası\n",
         ""
     ).replace(
         "if not HEDEF.resolve().is_relative_to(KUM.resolve()):",
         "if False:")),
]


def main() -> int:
    print("=" * 78)
    print("conn_kum_sizintisi — K4: fixture KUM DISINA kimlik yaziyordu")
    print("=" * 78)
    for eksik in (FIXTURE, KOSUCU):
        if not eksik.is_file():
            print(f"FAIL — dosya yok: {eksik}")
            return 1

    ham = {"fixture": FIXTURE.read_text(encoding="utf-8"),
           "kosucu": KOSUCU.read_text(encoding="utf-8")}
    yol = {"fixture": FIXTURE, "kosucu": KOSUCU}

    sonuc = senaryolar(FIXTURE)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik, yama_kirik = [], []
    for ad, hedef, mut in MUTASYONLAR:
        bozuk = mut(ham[hedef])
        if bozuk == ham[hedef]:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        mutant = FIXTURE.with_name("_mutant_conn_yazici.py")
        try:
            if hedef == "fixture":
                # Kardes dosya AYNI dizinde: `parents[3]` derinligi ayni kalir,
                # yani KOK cozumlemesi ve import zinciri degismez.
                mutant.write_text(bozuk, encoding="utf-8")
                m_res = senaryolar(mutant)
            else:
                m_res = senaryolar(FIXTURE, bozuk)   # kosucu BELLEKTE mutasyonlu
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:  # noqa: BLE001
            yakalandi, kacan = False, []
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
        finally:
            mutant.unlink(missing_ok=True)
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    # F1 ⭐ IZOLASYON KANITI: korpus GERCEK dosyalari degistirmemis olmali.
    for k, p in yol.items():
        if p.read_text(encoding="utf-8") != ham[k]:
            print(f"FAIL — F1: {p} korpus tarafindan DEGISTIRILDI (izolasyon kirik)")
            return 1
    if FIXTURE.with_name("_mutant_conn_yazici.py").exists():
        print("FAIL — F1: mutant kardes dosya kaldi")
        return 1
    print("  [PASS] F1 ⭐ izolasyon: gercek fixture/kosucu DEGISMEDI, mutant KALMADI")

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
