#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K1 — validator ailesi taradigi DOSYA SAYISINI raporlamiyordu: SESSIZ KAPSAM KAYBI.

=== OLCULMUS KUSUR (kayit satir 48 + 30) ===
BOS bir sandbox projede (`CLAUDE_PROJECT_DIR`=hicbir kaynak dosyasi olmayan dizin)
agac tarayan validator'lar kosuldu. **12'si** soyle dedi:

    bdef ters-tirnak: temiz.
    [OK] liste view grid (sap.ui.table) ihlali yok.
    RAP commit yasagi (BE-26): temiz (class'ta explicit DB-commit yok).
    ...

Bunlarin **6'si HARD gate**. Hicbiri "0 dosya taradim" demedi ⇒ okuyan icin

    "ihlal bulamadim"   ile   "bakacak dosya bulamadim"   AYIRT EDILEMEZ.

⭐ KONTROL GRUBU (dedektorun saglam oldugunu kanitlar): ayni validator'lar DOLU
sandbox'ta ihlalleri DOGRU yakaliyor. Yani bozuk olan dedektor degil, GORUNURLUK:
`IX_SOURCE_ROOT`/kok yanlissa arac yesil ekran verir. Bu, bozuk bir dedektorden
daha tehlikelidir — yesil ekrana kimse bakmaz.

=== SINIF, VAKA DEGIL ===
Fix tek tek 12 dosyaya yazilmis metin degil, ORTAK bir cikti sozlesmesidir
(`scripts/utils/kapsam.py` → `Kapsam.say()` + `Kapsam.ek()`). W1 vektoru bunu AST
ile civiler: 12 validator'in HEPSI sayaci hem SARMALAMALI hem PAYDAYI basmali.
(Metin capasi kullanilmadi — `"KAPSAM" in src` docstring'e de takilirdi.)

=== ⛔ BU BIR GATE SERTLESTIRMESI DEGILDIR (ADR 0019 / gate-moratoryumu) ===
`n == 0` FAIL URETMEZ; 12 validator'in cikis kodu AYNEN korunur. Sifir kapsam MESRU
olabilir (`.bdef`i olmayan proje 0 `.bdef` tarar). Kapatilan sey SESSIZLIKTIR.
X1 vektoru + M3 mutasyonu bu siniri civiler: biri "0 dosya -> yine exit 0" der,
digeri "birileri bunu FAIL'e cevirirse korpus KIRMIZI yanar" der. **X1/M3 SILINEMEZ** —
onlar olmadan bu degisiklik bir gun sessizce sertlestirilir.

  P1..P12 ⭐ AYIRT EDICI  BOS sandbox -> 12'sinin HEPSI `KAPSAM SIFIR` basar (once: sessiz)
  N1..N12 FP capasi      DOLU+TEMIZ sandbox -> payda `(N ... tarandi)`, N>0, SIFIR uyarisi YOK
  C1..C3  ⭐ POZ.KONTROL  DOLU+IHLALLI sandbox -> gercek ihlal HALA yakalanir (dedektor korlesmedi)
  W1      KABLOLAMA      12 validator'in hepsi AST'de `KAPSAM.say(` + `KAPSAM.ek()` cagirir
  X1      ⭐ SINIR        BOS sandbox'ta 12'sinin de cikis kodu 0 (sertlestirme YOK)
  H1/H2   yardimci       `kapsam_eki(0,..)` isaretci + kok izi · `kapsam_eki(5,..)` payda
  M1..M4                 fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/validator_kapsam_paydasi/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import ast
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
V = KOK / "scripts" / "validators"
KAPSAM_PY = KOK / "scripts" / "utils" / "kapsam.py"

# Sinifin TAM uyeligi (2026-08-20 bos-sandbox olcumu). Bir uye eksilirse W1 duser.
AILE = [
    "check_amdp_comment_apostrophe", "check_audit_fields_autofill", "check_bdef_backtick",
    "check_cds_srvd_comment_syntax", "check_decimal_write_to", "check_filter_search_pattern",
    "check_kd_no_raw_mermaid", "check_list_view_grid", "check_method_param_type_c",
    "check_no_rap_commit", "check_rap_byassoc_keys_only", "check_ui5_freestyle_traps",
]
# Bunlarin 6'si HARD (run_all_validators etiketleri): list_view_grid ·
# filter_search_pattern · no_rap_commit · amdp_comment_apostrophe ·
# cds_srvd_comment_syntax · bdef_backtick.

PROJE_YAML = ("sap_profile: s4_private\nrelease: '2025'\nmaster_language: TR\n"
              "source_root: SOURCE_CODES\ncleancore_policy: balanced\n")

# DOLU + TEMIZ: her uyenin >=1 dosya GORMESI icin gereken asgari agac (olculdu).
TEMIZ_AGAC = {
    "project.yaml": PROJE_YAML,
    "SOURCE_CODES/SD/ZTEST/ZTEST.bdef":
        "managed implementation in class zbp_test unique;\n"
        "define behavior for ZTEST_I alias T\n{\n  field ( readonly ) Mandt;\n}\n",
    "SOURCE_CODES/SD/ZTEST/ZCL_TEST.clas.abap":
        "CLASS zcl_test DEFINITION PUBLIC.\n  PUBLIC SECTION.\n"
        "    METHODS run IMPORTING iv_x TYPE string.\nENDCLASS.\n"
        "CLASS zcl_test IMPLEMENTATION.\n  METHOD run.\n  ENDMETHOD.\nENDCLASS.\n",
    "SOURCE_CODES/SD/ZTEST/ZIF_TEST.intf.abap":
        "INTERFACE zif_test PUBLIC.\nENDINTERFACE.\n",
    "SOURCE_CODES/SD/ZTEST/ZTEST_I.cds":
        "define view entity ZTEST_I as select from ztest_t\n{\n  key mandt as Mandt\n}\n",
    "SOURCE_CODES/SD/ZTEST/ZTEST_UI.srvd":
        "define service ZTEST_UI {\n  expose ZTEST_I;\n}\n",
    "SOURCE_CODES/SD/ZTEST/ui/webapp/view/List.view.xml":
        '<mvc:View xmlns:mvc="sap.ui.core.mvc" xmlns:t="sap.ui.table">\n'
        '  <t:Table id="tbl"/>\n</mvc:View>\n',
    "SOURCE_CODES/SD/ZTEST/ui/webapp/view/Filter.view.xml":
        '<mvc:View xmlns:mvc="sap.ui.core.mvc" xmlns="sap.m">\n'
        '  <MultiInput id="f1"/>\n</mvc:View>\n',
    "SOURCE_CODES/SD/ZTEST/ui/webapp/controller/List.controller.js":
        'sap.ui.define([], function () {\n  "use strict";\n  return {};\n});\n',
    "docs/KD-ZTEST.html": "<html><body><img src='d.png'/></body></html>\n",
}

# DOLU + IHLALLI: ⭐ POZITIF KONTROL — payda eklenmesi dedektoru KORLESTIRMEDI.
IHLALLI_AGAC = dict(TEMIZ_AGAC)
IHLALLI_AGAC["SOURCE_CODES/SD/ZTEST/ZTEST.bdef"] = (
    "managed implementation in class zbp_test unique;\n"
    "define behavior for ZTEST_I alias T\n{\n"
    "  field ( readonly ) CreatedBy;   // audit alani VAR, setAdmin YOK -> ihlal\n"
    "  // ters-tirnak ihlali: `ZTEST_I`\n}\n")
IHLALLI_AGAC["SOURCE_CODES/SD/ZTEST/ui/webapp/view/List.view.xml"] = (
    '<mvc:View xmlns:mvc="sap.ui.core.mvc" xmlns="sap.m">\n'
    '  <Table id="tbl"/>   <!-- sap.m.Table = liste-grid ihlali -->\n</mvc:View>\n')


def _izole_agac() -> Path:
    """Mutasyon icin `scripts/` AGAC KOPYASI.

    ⛔ 2026-08-20 DERSI: ilk surum mutasyonu GERCEK `kapsam.py` /
    `check_bdef_backtick.py` uzerine yaziyordu. Art arda kosumlarda kalinti birikti;
    bir noktada gercek kaynaklar MUTANT halde diskte kaldi ve KOMSU korpuslar
    (fs_docstd) kirlendi. Kalici cozum: mutasyon izole kopyada yasar; gercek agac
    korpus boyunca SALT-OKUNURDUR (F1 vektoru bunu civiler).

    `scripts/` TUMDEN kopyalanir: validator'lar `parents[1]`den `utils.*` cozer;
    yalniz iki dosya kopyalanirsa import OLUR ve her mutasyon "yakalandi" gorunur
    (SAHTE-KIRMIZI).
    """
    kok = Path(tempfile.mkdtemp(prefix="k1izo_"))
    shutil.copytree(KOK / "scripts", kok / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
    return kok


def _kur(agac: dict[str, str]) -> Path:
    d = Path(tempfile.mkdtemp(prefix="k1_"))
    for rel, icerik in agac.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(icerik, encoding="utf-8")
    (d / "SOURCE_CODES").mkdir(exist_ok=True)
    return d


def _bos() -> Path:
    return _kur({"project.yaml": PROJE_YAML})


def _kos(ad: str, kum: Path, agac_kok: Path = KOK) -> tuple[int, str]:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(kum)
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("IX_SOURCE_ROOT", None)
    v = agac_kok / "scripts" / "validators"
    p = subprocess.run([sys.executable, str(v / f"{ad}.py")], cwd=str(kum), env=env,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def senaryolar(agac_kok: Path = KOK) -> list[tuple[str, bool, str]]:
    r: list[tuple[str, bool, str]] = []

    def ekle(ad: str, ok: bool, detay: str = "") -> None:
        r.append((ad, ok, detay))

    # --- P + X1: BOS sandbox --------------------------------------------------
    bos = _bos()
    try:
        rc_hepsi = []
        for i, ad in enumerate(AILE, 1):
            rc, out = _kos(ad, bos, agac_kok)
            rc_hepsi.append((ad, rc))
            ekle(f"P{i} ⭐ BOS kapsam GORUNUR: {ad}",
                 "KAPSAM SIFIR" in out,
                 f"rc={rc} · cikti={out.strip()[:160]!r}")
        ekle("X1 ⭐ SINIR: BOS sandbox'ta 12'sinin de cikis kodu 0 "
             "(bu bir gate SERTLESTIRMESI degil)",
             all(rc == 0 for _, rc in rc_hepsi),
             f"sifir-olmayan={[(a, c) for a, c in rc_hepsi if c != 0]}")
    finally:
        shutil.rmtree(bos, ignore_errors=True)

    # --- N: DOLU + TEMIZ ------------------------------------------------------
    temiz = _kur(TEMIZ_AGAC)
    try:
        for i, ad in enumerate(AILE, 1):
            rc, out = _kos(ad, temiz, agac_kok)
            payda = [l for l in out.splitlines() if "tarandı)" in l]
            sayi = 0
            if payda:
                try:
                    parca = payda[0].rsplit("(", 1)[1]
                    sayi = int(parca.split()[0])
                except (IndexError, ValueError):
                    sayi = 0
            ekle(f"N{i} FP capasi: DOLU agacta payda N>0 ve SIFIR uyarisi YOK: {ad}",
                 sayi > 0 and "KAPSAM SIFIR" not in out,
                 f"rc={rc} · N={sayi} · payda={payda[:1]}")
    finally:
        shutil.rmtree(temiz, ignore_errors=True)

    # --- C: ⭐ POZITIF KONTROL — gercek ihlal HALA yakalaniyor ------------------
    ihlalli = _kur(IHLALLI_AGAC)
    try:
        rc, out = _kos("check_bdef_backtick", ihlalli, agac_kok)
        ekle("C1 ⭐ POZITIF KONTROL: bdef ters-tirnak ihlali HALA yakalaniyor "
             "(payda eklemek dedektoru korlestirmedi)",
             rc != 0 and "İHLAL" in out, f"rc={rc} · {out.strip()[:200]!r}")
        rc, out = _kos("check_audit_fields_autofill", ihlalli, agac_kok)
        ekle("C2 ⭐ POZITIF KONTROL: audit/setAdmin ihlali HALA yakalaniyor",
             "İHLAL" in out, f"rc={rc} · {out.strip()[:200]!r}")
        rc, out = _kos("check_list_view_grid", ihlalli, agac_kok)
        ekle("C3 ⭐ POZITIF KONTROL: liste-grid ihlali HALA yakalaniyor",
             rc != 0 or "İHLAL" in out, f"rc={rc} · {out.strip()[:200]!r}")
    finally:
        shutil.rmtree(ihlalli, ignore_errors=True)

    # --- W1: KABLOLAMA (AST — metin capasi degil) -----------------------------
    eksik = []
    for ad in AILE:
        src = (agac_kok / "scripts" / "validators" / f"{ad}.py").read_text(encoding="utf-8")
        try:
            agac = ast.parse(src)
        except SyntaxError as e:
            eksik.append(f"{ad}(SyntaxError:{e.lineno})")
            continue
        say_var = ek_var = False
        for n in ast.walk(agac):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                hedef = n.func.value
                if isinstance(hedef, ast.Name) and hedef.id == "KAPSAM":
                    if n.func.attr == "say":
                        say_var = True
                    elif n.func.attr == "ek":
                        ek_var = True
        if not (say_var and ek_var):
            eksik.append(f"{ad}(say={say_var},ek={ek_var})")
    ekle("W1 KABLOLAMA: 12 validator'in HEPSI `KAPSAM.say(` + `KAPSAM.ek()` cagiriyor (AST)",
         not eksik, f"eksik={eksik}")

    # --- H: yardimcinin kendi sozlesmesi --------------------------------------
    sys.path.insert(0, str(agac_kok / "scripts"))
    for m in [k for k in list(sys.modules) if k.startswith("utils.kapsam")]:
        del sys.modules[m]          # mutasyon turlari arasinda BAYAT modul kalmasin
    from utils.kapsam import kapsam_eki  # noqa: E402
    s0 = kapsam_eki(0, ".bdef")
    ekle("H1 `kapsam_eki(0,..)`: SIFIR isaretcisi + KOK izi (eyleme donusur tani)",
         "KAPSAM SIFIR" in s0 and "kök=" in s0, repr(s0[:160]))
    s5 = kapsam_eki(5, ".bdef")
    ekle("H2 `kapsam_eki(5,..)`: payda basiliyor, SIFIR uyarisi YOK",
         "(5 .bdef tarandı)" in s5 and "KAPSAM SIFIR" not in s5, repr(s5))
    return r


# --- MUTASYONLAR ------------------------------------------------------------
# ⚠ IKI DEGISMEZ -> IKI MUTASYON SINIFI: (a) gorunurlugu sok (M1/M2/M4),
#    (b) SINIRI sok = 0 dosyayi FAIL yap (M3). Yalniz (a) yazilsaydi bu degisiklik
#    bir gun sessizce gate sertlestirmesine terfi ederdi ve korpus fark etmezdi.
MUTASYONLAR = [
    ("M1 `ek()` SIFIR dalini sok (hep payda bicimi dondur)", "kapsam",
     lambda s: s.replace(
         '    if n > 0:\n        return f"  ({n} {birim} tarandı)"\n',
         '    if True:\n        return f"  ({n} {birim} tarandı)"\n')),
    ("M2 `say()` SAYMAYI biraksin (sayac hep 0 kalir)", "kapsam",
     lambda s: s.replace(
         "        for x in it:\n            self.n += 1\n            yield x\n",
         "        for x in it:\n            yield x\n")),
    ("M3 ⭐SINIR: 0 dosyayi FAIL yap (gate SERTLESTIRMESI — X1 kirmizi yanmali)", "bdef",
     lambda s: s.replace(
         '    print("bdef ters-tırnak: temiz." + KAPSAM.ek())\n    return 0\n',
         '    print("bdef ters-tırnak: temiz." + KAPSAM.ek())\n'
         '    return 1 if KAPSAM.n == 0 else 0\n')),
    ("M4 bir validator'dan PAYDAYI sok (kablolama)", "bdef",
     lambda s: s.replace('    print("bdef ters-tırnak: temiz." + KAPSAM.ek())',
                         '    print("bdef ters-tırnak: temiz.")')),
]


def main() -> int:
    print("=" * 78)
    print("validator_kapsam_paydasi — K1: 'temiz' mi, 'bakilmadi' mi?")
    print("=" * 78)
    for eksik in (KAPSAM_PY,):
        if not eksik.is_file():
            print(f"FAIL — ortak yardimci yok: {eksik}")
            return 1

    BDEF = V / "check_bdef_backtick.py"
    ham = {"kapsam": KAPSAM_PY.read_text(encoding="utf-8"),
           "bdef": BDEF.read_text(encoding="utf-8")}
    yol = {"kapsam": KAPSAM_PY, "bdef": BDEF}

    sonuc = senaryolar()
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
        izole = None
        try:
            izole = _izole_agac()
            (izole / yol[hedef].relative_to(KOK)).write_text(bozuk, encoding="utf-8")
            m_res = senaryolar(izole)
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:  # noqa: BLE001
            yakalandi, kacan = False, []
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
        finally:
            if izole is not None:
                shutil.rmtree(izole, ignore_errors=True)
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    # F1 ⭐ IZOLASYON KANITI: korpus GERCEK agaci degistirmemis olmali.
    for k, p in yol.items():
        if p.read_text(encoding="utf-8") != ham[k]:
            print(f"FAIL — F1: {p} korpus tarafindan DEGISTIRILDI (izolasyon kirik)")
            return 1
    print("  [PASS] F1 ⭐ izolasyon: gercek kapsam.py/validator korpus boyunca DEGISMEDI")

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
