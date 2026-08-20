#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""populate_* ucusu AKTIVE ETMIYOR ama sessizce `exit 0` doner ("exit 0 != kanit").

KOK (olculdu 2026-08-19): `populate_domains` · `populate_dataelements` ·
`populate_tables` icinde `activate` cagrisi **0 eslesme**. Uculu de sonunda
`=== Sonuc: N basarili, 0 hatali ===` yazip 0 doner; objeler INAKTIF kalir ve
bosluk ancak SONRAKI katman *"tip yok"* ile dustugunde gorunur. Kardesi
`populate_lock_objects` ise AKTIVE EDER -> aile kendi icinde tutarsiz ve bu
hicbir yerde yazili degildi.

FIX (bilincli olarak DAVRANIS DEGISTIRMEZ): aktivasyon EKLENMEDI, cunku
tuketiciler "aktive etmiyor" varsayimina gore kendi `activate_object.py`
adimlarini kurmus durumda -> eklemek CIFT AKTIVASYON yaratirdi. Degisen tek sey
CIKTININ DURUSTLUGU: kosum sonunda GORUNUR bir kapanis notu + kosulacak tam komut.
Metin TEK KAYNAKTA (`utils/ddic_aktivasyon.py`) yasar, uc script oradan cagirir.

Bu korpus S(enaryo) + M(utasyon) tasir:
  S1-S2  notun kendisi: dolu liste -> tam komut · bos liste -> SESSIZ (gurultu yok)
  S3     ⭐ URETICI<->TUKETICI: basilan `--type` degeri activate_object.py'nin
         GERCEK argparse choices'inda mi (metin kiyasi DEGIL, canli cozum)
  S4     3. BAGLAM: bilinmeyen tip -> SESSIZ KALMAZ (kapatmaya calistigimiz kusur
         tam da sessizlik; tipi cozemedigini soyleyip yine uyarmali)
  S5-S7  KABLOLAMA (kod != kablolama): uc script'in main()'inde cagri VAR mi ve
         `if not args.dry_run` altinda mi -- AST ile, metin aramasiyla degil
  S8     --cwd verilince komutta aynen gorunur
  M1-M3  fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/ddic_aktivasyon_notu/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import ast
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
HELPER_PATH = SCRIPTS / "utils" / "ddic_aktivasyon.py"

TUKETICILER = {
    "domain": SCRIPTS / "populate_domains.py",
    "dataelement": SCRIPTS / "populate_dataelements.py",
    "table": SCRIPTS / "populate_tables.py",
}

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_helper(mut=None):
    """Yardimciyi TAZE namespace'e yukler; mutasyon KAYNAK METNINE uygulanir.

    Yardimci saf metin uretir (SAP yok, stdout gaspi yok) -> kardes fixture'lardaki
    TextIOWrapper korumasi burada GEREKMEZ; gereksiz karmasa eklemiyoruz.
    """
    src = HELPER_PATH.read_text(encoding="utf-8")
    if mut:
        src = mut(src)
    mod = types.ModuleType("utils.ddic_aktivasyon")
    mod.__file__ = str(HELPER_PATH)
    exec(compile(src, str(HELPER_PATH), "exec"), mod.__dict__)
    return mod


def kablolu_mu(src: str) -> tuple[bool, str]:
    """main() icinde `aktivasyon_notu(...)` cagrisi `if not args.dry_run` ALTINDA mi?

    AST ile bakilir; metin aramasi (`grep "aktivasyon_notu"`) yorum satirinda da
    eslesir ve "kod != kablolama" tuzagina duser. Ayrica dry-run dalinin ICINDE
    olmasi ONEMLI: dry-run'da nota gerek yok (hicbir sey yazilmadi), orada basmak
    uyari korlugu uretir.
    """
    try:
        agac = ast.parse(src)
    except SyntaxError as e:
        return False, "kaynak ayristirilamadi: %s" % e

    def cagri_var(dugum) -> bool:
        return any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "aktivasyon_notu"
            for n in ast.walk(dugum)
        )

    def dry_run_negatifi(test) -> bool:
        # `not args.dry_run`
        return (
            isinstance(test, ast.UnaryOp)
            and isinstance(test.op, ast.Not)
            and isinstance(test.operand, ast.Attribute)
            and test.operand.attr == "dry_run"
        )

    for fn in ast.walk(agac):
        if not (isinstance(fn, ast.FunctionDef) and fn.name == "main"):
            continue
        if not cagri_var(fn):
            return False, "main() icinde aktivasyon_notu cagrisi YOK"
        for dugum in ast.walk(fn):
            if isinstance(dugum, ast.If) and dry_run_negatifi(dugum.test):
                if any(cagri_var(g) for g in dugum.body):
                    return True, ""
        return False, "cagri VAR ama `if not args.dry_run` dalinda DEGIL"
    return False, "main() bulunamadi"


def gercek_choices() -> set[str]:
    """activate_object.py'nin `--type` choices'ini AYNI KAYNAKTAN cozer.

    activate_object.py:34 -> `list_supported_types() + list(OBJECT_TYPE_ALIASES)`.
    Metin kopyalamak yerine modulu import ediyoruz: tuketici sozlesmesi degisirse
    bu vektor kirilir (istenen davranis).
    """
    from object_types import list_supported_types, OBJECT_TYPE_ALIASES  # type: ignore
    return set(list_supported_types()) | set(OBJECT_TYPE_ALIASES.keys())


def senaryolar(mod) -> list[tuple[str, bool, str]]:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    # --- S1: dolu liste -> her obje icin tam komut --------------------------
    n = mod.aktivasyon_notu("domain", ["ZSD001_D_AAA", "ZSD001_D_BBB"])
    kosullar = [
        "AKTIVASYON YAPILMADI" in n,
        "activate_object.py" in n,
        "--type doma" in n,
        "ZSD001_D_AAA" in n and "ZSD001_D_BBB" in n,
        n.count("activate_object.py") == 2,   # obje BASINA bir komut
    ]
    ekle("S1 dolu liste: 2 obje icin 2 tam komut + uyari basligi",
         all(kosullar), "kosullar=%s" % kosullar)

    # --- S2: bos liste -> SESSIZ (FP capasi, S1'den AYRI) -------------------
    ekle("S2 bos liste: hicbir sey basilmaz (gurultu yok)",
         mod.aktivasyon_notu("domain", []) == "",
         "gorulen=%r" % mod.aktivasyon_notu("domain", [])[:40])

    # --- S3: ⭐ URETICI <-> TUKETICI sozlesmesi ------------------------------
    try:
        gercek = gercek_choices()
        basilan = set(mod.AKTIVASYON_TIPI.values())
        eksik = sorted(basilan - gercek)
        ekle("S3 basilan --type degerleri activate_object choices'inda (%d tip)"
             % len(basilan),
             not eksik,
             "activate_object'in TANIMADIGI tip(ler)=%s" % eksik)
    except Exception as e:
        ekle("S3 basilan --type degerleri activate_object choices'inda",
             False, "cozulemedi: %s: %s" % (type(e).__name__, e))

    # --- S4: 3. BAGLAM — bilinmeyen tip SESSIZ KALMAZ ----------------------
    n = mod.aktivasyon_notu("bilinmeyen_tip", ["ZSD001_X_AAA"])
    ekle("S4 3.baglam: bilinmeyen tip -> yine de UYARIR (sessiz kalmaz)",
         n != "" and "AKTIVASYON YAPILMADI" in n and "ZSD001_X_AAA" in n,
         "gorulen=%r" % n[:60])

    # --- S5-S7: KABLOLAMA (kod != kablolama), AST ile ----------------------
    for tip, yol in TUKETICILER.items():
        ok, detay = kablolu_mu(yol.read_text(encoding="utf-8"))
        ekle("S%d kablolama: %s main()'inde cagri var + dry-run disinda"
             % (5 + list(TUKETICILER).index(tip), yol.name), ok, detay)

    # --- S8: --cwd komuta aynen gecer --------------------------------------
    n = mod.aktivasyon_notu("table", ["ZSD001_T_AAA"], cwd="/tmp/proje")
    ekle("S8 --cwd verilince komutta gorunur",
         "--cwd /tmp/proje" in n and "--type tabl" in n,
         "gorulen=%r" % n[-90:])

    # --- S9: C-ENC-01 — URETILEN METIN SAF ASCII ---------------------------
    # Windows konsolu cp1252'dir; non-ASCII bir UYARI metni, cagiranin stdout'u
    # UTF-8'e sabitlenmemisse kosumu UnicodeEncodeError ile COKERTIR (olculdu:
    # `python -c "...aktivasyon_notu(...)"` tam bunu yapti). Uyarinin kendisi
    # cokme sebebi olamaz.
    ascii_disi = {}
    for tip in ("domain", "dataelement", "table", "bilinmeyen"):
        metin = mod.aktivasyon_notu(tip, ["ZSD001_X_AAA"], cwd="/tmp/p")
        if not metin.isascii():
            ascii_disi[tip] = sorted({c for c in metin if not c.isascii()})
    ekle("S9 C-ENC-01: uretilen metin saf ASCII (cp1252 konsolda cokmez)",
         not ascii_disi, "ascii-disi karakterler=%s" % ascii_disi)

    return out


# ---------------------------------------------------------------------------
# MUTASYONLAR — uc ayri degismez, uc ayri mutasyon.
# ---------------------------------------------------------------------------
MUTASYONLAR = [
    ("M1 bos listede de metin uret (gurultu/uyari-korlugu degismezi)",
     "helper",
     lambda s: s.replace('    if not adlar:\n        return ""\n', "")),
    ("M2 gecersiz --type degeri yaz (uretici<->tuketici degismezi)",
     "helper",
     lambda s: s.replace('"table": "tabl",', '"table": "tablo",')),
    ("M3 populate_domains'ten cagriyi sok (KABLOLAMA degismezi)",
     "domain",
     lambda s: s.replace(
         "    if not args.dry_run:\n"
         "        print(aktivasyon_notu('domain', yaratilanlar, args.cwd))\n", "")),
    ("M4 uyari basligina non-ASCII geri koy (C-ENC-01 degismezi)",
     "helper",
     lambda s: s.replace('f"  [!] {len(adlar)} obje ISLENDI',
                         'f"  \\u26a0 {len(adlar)} obje ISLENDI')),
]


def main() -> int:
    print("=" * 78)
    print("ddic_aktivasyon_notu — 'yaratildi != aktif' kapanis notu korpusu")
    print("=" * 78)

    mod = load_helper()
    sonuc = senaryolar(mod)
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
            if hedef == "helper":
                m_mod = load_helper(mut=mut)
                m_res = senaryolar(m_mod)
            else:
                # Kablolama mutasyonu: tuketici KAYNAGINI yamalayip AST kontrolunu
                # o metne karsi kosuyoruz (diske YAZMADAN).
                bozuk = mut(TUKETICILER[hedef].read_text(encoding="utf-8"))
                ok, detay = kablolu_mu(bozuk)
                m_res = [("S5 kablolama (mutasyonlu kaynak)", ok, detay)]
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:   # cokme != FAIL: ayirt edilebilir kalsin
            yakalandi, kacan = True, ["yukleme hatasi: %s" % type(e).__name__]
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    # Mutasyonun GERCEKTEN uygulandigini kanitla (yama tutmazsa sahte-YESIL olur)
    print("\n--- yama-tuttu kanidi ---")
    yama_kirik = []
    for ad, hedef, mut in MUTASYONLAR:
        yol = HELPER_PATH if hedef == "helper" else TUKETICILER[hedef]
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
            print("FAIL — mutasyon KACTI (korpus bu degismezi olcmuyor): %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI (sahte-yesil riski): %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
