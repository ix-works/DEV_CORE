#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SABLON KUSURLARI: her yeni paket/brif yanlisi MIRAS ALIYORDU.

A) `templates/new-package/.rules.md.tmpl` — DTEL/Domain oneki YANLISTI
   Sablon `{PKG}_DE_*`/`{PKG}_DTEL_*` ve `{PKG}_DOM_*` yaziyordu. Kurumsal standart
   (`standards/01-naming.md` §4.4.5) ise Data Element = **E** (`ZMM001_E_AMOUNT`),
   Domain = **D** (`ZSD001_D_AMOUNT`) diyor; canli sistemde `_DOM_`/`_DE_` onekli
   TEK BIR OBJE YOK (olculdu 2026-08-17).
   ⭐ SINIF KANITI: ayni duzeltme UC AYRI pakette ELLE yapildi (2026-05-15 · 2026-08-05 ·
   2026-08-17). Uc turda uc kez elle duzeltmek, duzeltmenin YANLIS KATMANDA yapildiginin
   kanitidir — kok sablondaydi ve her yeni paket onu miras aliyordu.
   ⚠ Kural dosyasi validator'un GIRDISIDIR: yanlis oldugunda standarda uygun ad yazan
   gelistirici VALIDATOR HATASI alir; ya kural bukulur ya ad bozulur.

B) `claude/templates/spawn-brief.md` §9 + `brifing-lint` — "ENGELLENIRSEN" maddesi YOKTU
   VAKA: `isolation:"worktree"` ile acilan infra ajaninin worktree'si YANLIS repoda
   olustu; charter'i canli agaca yazmayi yasakladigi icin YAZACAK YERI YOKTU. Yasaga
   uydu, bekledi, HABER VERMEDI -> **26 dk olculebilir cikti SIFIR**. Watchdog
   "heartbeat taze" diyordu (canlilik olcer, ILERLEME olcmez). Kusur ajanda degil BRIFTEYDI.

   ⭐ LINT EKSENI OLCULEREK DARALTILDI (587 gercek brif, transcript korpusu):
     · ham "madde var mi?"                -> **%86,7** atesler ⇒ KULLANILAMAZ (uyari korlugu)
     · DAR (baska-agac + yazma isi)       -> **%18,4** kapsam / **%16,0** atesleme
       ⇒ KB-01'in olculmus gurultu tabaniyla (%13,9) ayni bant; mevcut GOREV ekseni %25,0.

C) `Class` satirinin 2. bicimi (Q193②, KAPANDI 2026-09-13; kullanici karari 2026-08-29)
   Sablon `ZCL_{PKG}_*` (-> `ZCL_ZSD001_*`, canlida 0 kullanim) yaziyordu; standart
   (`01-naming.md` §4.4.3 notu + `05-coding-rap.md` §4) ve canli artefakt `ZCL_<PKG#>_*`
   (`ZCL_SD001_*`). Yer tutucu yoktu -> `bootstrap_package.py`ye `PKG_NOZ` eklendi.
   ⓘ 2026-09-13 REPOINT (ikinci kez): A4/A5 + M4/M5 bu eksenin "AÇIK KARAR" notuna
   capaliydi; not kapaninca M4 [YAMA TUTMADI] olurdu (ayni sinif 2026-08-29'da Message
   Class ekseninde yasandi). Capalar artik KAPANISI ve URETICIYI (bootstrap) olcer.

  A1-A2  sablon <-> STANDART esligi (E/D) + eski onekler geri gelmemis
  A3     3. BAGLAM: sablonun diger DDIC satirlari standartla tutarli
  A4     `Class` satiri HIZALI: `ZCL_{PKG_NOZ}_` VAR, eski `ZCL_{PKG}_` YOK (satir kapsamli)
  A5     acik not KAPANDI (bayat "AÇIK KARAR" basligi geri gelmemis, kapanis kaydi var)
  A6     ⭐ GERCEK GIRIS: bootstrap uretilen paket dosyalarinda cozulmemis `{YER_TUTUCU}` YOK
  A7     ⭐ GERCEK GIRIS: uretilen .rules.md + GERCEK validator: `ZCL_SD001_X` KABUL,
         `ZSD001_CL_X` KABUL (legacy), `ZCL_ZSD001_X` RED
  A8     3. BAGLAM: Z'siz ad (`YSD001`/`SD001`) -> PKG_NOZ DEGISMEZ + [BİLGİ] notu
  B1-B2  lint DAR eksen: baska-agac+yazma & madde YOK -> atesler / madde VAR -> susar
  B3-B4  ⭐ FP CAPALARI: yalniz-okuma isi ateslemez · kisa brif muaf
  B5     sablon §9 zorunlu maddeyi TASIYOR
  B6     mevcut GOREV/KANIT-KURAL ekseni BOZULMADI (regresyon)
  M1-M7  fix'i sok -> korpus KIRMIZI olmali (M5/M6 bootstrap kaynagini BELLEKTE bozar)

Kosum: python tests/fixtures/sablon_zorunlu_maddeler/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import shutil
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
TPL_DIR = CORE / "templates" / "new-package"
TMPL = TPL_DIR / ".rules.md.tmpl"
STD = CORE / "standards" / "01-naming.md"
BRIEF = CORE / "claude" / "templates" / "spawn-brief.md"
LINT = CORE / "scripts" / "hooks" / "watchdog_launch.py"
BOOT = CORE / "scripts" / "bootstrap_package.py"
VALIDATOR = CORE / "scripts" / "validators" / "check_package_naming.py"

_YER_TUTUCU = re.compile(r"\{[A-Z][A-Z_]*\}")


def _std_ddic_onekleri() -> dict[str, str]:
    """`standards/01-naming.md` §4.4.5 tablosundan {obje: onek} — TEK OTORITE.

    ⚠ Onekler burada KOPYALANMAZ, standarttan OKUNUR: ikinci kopya bayatlar ve
    korpus standardi degil kendi ezberini dogrular hale gelir.
    """
    metin = STD.read_text(encoding="utf-8")
    i = metin.find("#### 4.4.5")
    if i < 0:
        return {}
    blok = metin[i:i + 2500]
    out = {}
    for satir in blok.splitlines():
        m = re.match(r"\|\s*([^|]+?)\s*\|\s*Z or Y\s*\|\s*`([A-Z]+)`\s*\|", satir)
        if m:
            out[m.group(1).strip()] = m.group(2)
    return out


def _tmpl_regex(obje: str, src: str) -> str | None:
    for satir in src.splitlines():
        m = re.match(r"\|\s*" + re.escape(obje) + r"\s*\|\s*`([^`]+)`", satir)
        if m:
            return m.group(1)
    return None


def _tmpl_satir(obje: str, src: str) -> str | None:
    """Sablondaki naming tablosunun `| <obje> | ... |` satirini AYNEN dondurur.

    ⚠ `_tmpl_regex` yalnizca 2. hucredeki ILK backtick grubunu verir; bir hucre
    iki bicim tasiyorsa ikincisini GORMEZ. Capa dosyanin TAMAMINDA aranirsa da
    olmaz: ayni dize aciklama notunun tarihsel alintilarinda da gecer (kapanis
    notu `ZCL_{PKG}_*`yi tarihce olarak anar) ⇒ kapsam SATIRDIR.
    """
    for satir in src.splitlines():
        if re.match(r"\|\s*" + re.escape(obje) + r"\s*\|", satir):
            return satir
    return None


def _lint_yukle(src: str):
    """watchdog_launch'i TAZE namespace'e yukler (mutasyon icin)."""
    mod = types.ModuleType("watchdog_launch_x")
    mod.__file__ = str(LINT)
    exec(compile(src, str(LINT), "exec"), mod.__dict__)
    return mod


def _boot_yukle(src: str):
    """bootstrap_package'i TAZE namespace'e yukler.

    ⚠ `__file__` DAIMA gercek yol: modul `parents[0]`dan `utils` import eder ve
    `--templates-root` varsayilanini `__file__`dan turetir. Kaynak metni ayri gelir
    (mutasyon / eski-kod karsitligi icin) — kopya yol verilseydi import kokunu kaybederdi.
    """
    mod = types.ModuleType("bootstrap_package_x")
    mod.__file__ = str(BOOT)
    exec(compile(src, str(BOOT), "exec"), mod.__dict__)
    return mod


def _validator_yukle():
    spec = importlib.util.spec_from_file_location("check_package_naming_x", VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _bootstrap_kos(boot, tmpl_text: str, paket: str, siniflar=()) -> dict:
    """GERCEK `main()` + argparse, gecici agacta (gercek projeye YAZMAZ).

    Sablon dizini gecici agaca kopyalanir ve `.rules.md.tmpl` verilen metinle ezilir.
    `siniflar` verilirse uretilen paketin `classes/` altina bos dosya olarak konur ve
    GERCEK validator (`validate_package`) kosulur.
    """
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        tdir = td / "tpl"
        shutil.copytree(TPL_DIR, tdir)
        (tdir / ".rules.md.tmpl").write_text(tmpl_text, encoding="utf-8")
        kaynak = td / "SRC"
        (kaynak / "SD").mkdir(parents=True)
        argv = ["bootstrap_package.py", paket, "--title", "Fixture", "--module", "SD",
                "--templates-root", str(tdir), "--source-root", str(kaynak)]
        eski, sys.argv = sys.argv, argv
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = boot.main()
        finally:
            sys.argv = eski
        pkg_dir = kaynak / "SD" / paket
        cozulmemis = {}
        for f in sorted(pkg_dir.rglob("*")) if pkg_dir.exists() else []:
            if f.is_file():
                bulunan = sorted(set(_YER_TUTUCU.findall(f.read_text(encoding="utf-8"))))
                if bulunan:
                    cozulmemis[f.name] = bulunan
        ihlal = None
        if siniflar and pkg_dir.exists():
            (pkg_dir / "classes").mkdir(exist_ok=True)
            for ad in siniflar:
                (pkg_dir / "classes" / (ad + ".clas.abap")).write_text("", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                ihlal = _validator_yukle().validate_package(pkg_dir)
        return {"rc": rc, "cozulmemis": cozulmemis, "ihlal": ihlal,
                "stderr": err.getvalue(), "var": pkg_dir.exists()}


def _payload(prompt: str) -> dict:
    return {"tool_input": {"prompt": prompt}}


# --- Gercek sekilden turetilmis brifingler (adlar jenerik) -------------------
_DOLGU = ("GOREV: bilesen uzerinde calis. KANIT KURAL: tahmin yasak, olcerek ilerle. "
          "Cikti formati: rapor. Arac kilavuzu: repo araclari. " * 6)
BRIF_YAZMA_ENGELSIZ = ("GOREV: worktree C:/IX/_wt/ornek icinde fix uygula ve commit et. "
                       "KANIT KURAL: olc. " + _DOLGU)
BRIF_YAZMA_ENGELLI = (BRIF_YAZMA_ENGELSIZ +
                      " ENGELLENIRSEN: yazacak yerin yoksa TAHMIN ETME, DERHAL "
                      "SendMessage(to:'main') ile bildir.")
BRIF_SALT_OKUMA = ("GOREV: worktree icindeki kodu OKU ve bulgulari rapor et. "
                   "KANIT KURAL: olc. Hicbir sey degistirme. " + _DOLGU)
BRIF_KISA = "GOREV: test echo. worktree fix uygula."

# A7 vektorleri: (sinif adi, validator KABUL etmeli mi)
SINIF_VEKTORLERI = (("ZCL_SD001_X", True), ("ZSD001_CL_X", True), ("ZCL_ZSD001_X", False))


def senaryolar(mod, boot_src: str | None = None) -> list[tuple[str, bool, str]]:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    tmpl = TMPL.read_text(encoding="utf-8")
    std = _std_ddic_onekleri()

    # --- A1: sablon <-> STANDART esligi (E/D) ------------------------------
    beklenen = {"Data Element": std.get("Data Element"), "Domain": std.get("Domain")}
    gercek = {o: _tmpl_regex(o, tmpl) for o in beklenen}
    uyum = all(
        beklenen[o] and gercek[o] and re.search(r"_" + beklenen[o] + r"_", gercek[o])
        for o in beklenen)
    ekle("A1 sablon DTEL/Domain oneki STANDARTLA (§4.4.5) esit: E / D",
         uyum, "standart=%s sablon=%s" % (beklenen, gercek))

    # --- A2: eski YANLIS onekler geri gelmemis -----------------------------
    kotu = [k for k in ("_DE_", "_DTEL_", "_DOM_")
            if re.search(r"\|\s*(Data Element|Domain)\s*\|[^|]*" + k, tmpl)]
    ekle("A2 eski yanlis onekler (_DE_/_DTEL_/_DOM_) naming satirinda YOK",
         not kotu, "bulunan=%s" % kotu)

    # --- A3: 3. BAGLAM — diger DDIC satirlari da standartla tutarli --------
    # (Sablon degistirilirken komsu satirin bozulmadiginin capasi.)
    komsu = {"Structure": "S", "Table": "T", "Table Type": "TT"}
    sapan = [o for o, p in komsu.items()
             if not (_tmpl_regex(o, tmpl) or "").count("_" + p + "_")]
    ekle("A3 3.baglam: Structure/Table/TableType onekleri bozulmadi",
         not sapan, "sapan=%s" % sapan)

    # --- A4: `Class` satiri HIZALI (Q193②, 2026-09-13) ---------------------
    # ⚠ Kapsam SATIR: kapanis notu eski bicimi TARIHCE olarak anar (bkz. _tmpl_satir).
    cls_satir = _tmpl_satir("Class", tmpl) or ""
    ekle("A4 ⭐`Class` satiri hizali: ZCL_{PKG_NOZ}_ VAR, eski ZCL_{PKG}_ YOK",
         "ZCL_{PKG_NOZ}_" in cls_satir and "ZCL_{PKG}_" not in cls_satir,
         "satir=%r" % cls_satir[:100])

    # --- A5: acik not KAPANDI, bayat baslik geri gelmemis ------------------
    # Karar kapandiktan sonra "AÇIK KARAR" basligi okuyana ACIK bir soru varmis gibi
    # gorunur (bayat durum). Kapanis kaydi da SILINMEMELI: gerekce/olcum orada yasar.
    ekle("A5 `Class` acik notu KAPANDI (bayat AÇIK KARAR yok, kapanis kaydi var)",
         "AÇIK KARAR — `Class`" not in tmpl and "KAPANDI — `Class`" in tmpl,
         "acik=%s kapanis=%s" % ("AÇIK KARAR — `Class`" in tmpl, "KAPANDI — `Class`" in tmpl))

    # --- A6/A7: ⭐ GERCEK GIRIS — uretici + validator ----------------------
    # Sablon bir YER TUTUCU kullanir; ureticinin haritasinda yoksa `{PKG_NOZ}` uretilen
    # .rules.md'ye HARFIYEN yazilir ve validator `ZCL_{PKG_NOZ}_` regex'iyle HICBIR sinifi
    # kabul etmez. Metin capasi (A4) bunu goremez — uretici kosulmadan olculemez.
    boot = _boot_yukle(boot_src if boot_src is not None else BOOT.read_text(encoding="utf-8"))
    r = _bootstrap_kos(boot, tmpl, "ZSD001_CLC", [a for a, _ in SINIF_VEKTORLERI])
    ekle("A6 ⭐bootstrap uretti + cozulmemis yer tutucu YOK",
         r["rc"] == 0 and r["var"] and not r["cozulmemis"],
         "rc=%r cozulmemis=%s" % (r["rc"], r["cozulmemis"]))
    ihlal = r["ihlal"] or []
    reddedilen = sorted(a for a, _ in SINIF_VEKTORLERI if any(a + ".clas" in v for v in ihlal))
    beklenen_red = sorted(a for a, kabul in SINIF_VEKTORLERI if not kabul)
    ekle("A7 ⭐GERCEK validator: ZCL_SD001_X + ZSD001_CL_X KABUL · ZCL_ZSD001_X RED",
         r["ihlal"] is not None and reddedilen == beklenen_red,
         "reddedilen=%s beklenen=%s" % (reddedilen, beklenen_red))

    # --- A8: 3. BAGLAM — Z ile baslamayan ad -------------------------------
    # `Y` ATILMAZ: `YSD001` -> `SD001` olsaydi sinif deseni `ZSD001` paketinin ad
    # alanina duserdi. Oneksiz ad da degismez. Arac bu durumda SESSIZ kalmaz.
    turet = getattr(boot, "pkg_noz_turet", None)
    degerler = {a: (turet(a) if turet else None) for a in ("ZSD001", "YSD001", "SD001")}
    ry = _bootstrap_kos(boot, tmpl, "YSD001_CLC")
    ekle("A8 3.baglam: ZSD001->SD001 · YSD001/SD001 DEGISMEZ + [BİLGİ] notu",
         degerler == {"ZSD001": "SD001", "YSD001": "YSD001", "SD001": "SD001"}
         and ry["rc"] == 0 and "[BİLGİ] PKG_NOZ = PKG" in ry["stderr"],
         "degerler=%s bilgi=%s" % (degerler, "[BİLGİ] PKG_NOZ = PKG" in ry["stderr"]))

    # --- B1: DAR eksen atesler --------------------------------------------
    n = mod._brifing_lint(_payload(BRIF_YAZMA_ENGELSIZ)) or ""
    ekle("B1 baska-agac + yazma + madde YOK -> lint UYARIR",
         "ENGELLENIRSEN" in n, "not=%r" % n[:110])

    # --- B2: madde VARSA susar (ayirt edici ikiz) -------------------------
    n2 = mod._brifing_lint(_payload(BRIF_YAZMA_ENGELLI)) or ""
    ekle("B2 ayni brif + madde VAR -> bu eksen SUSAR",
         "ENGELLENIRSEN" not in n2, "not=%r" % n2[:110])

    # --- B3: ⭐ FP CAPASI — salt-okuma isi ateslemez ----------------------
    n3 = mod._brifing_lint(_payload(BRIF_SALT_OKUMA)) or ""
    ekle("B3 FP capasi: yalniz-OKUMA isi bu ekseni atesleMEZ",
         "ENGELLENIRSEN" not in n3, "not=%r" % n3[:110])

    # --- B4: FP CAPASI — kisa/mekanik brif muaf ---------------------------
    n4 = mod._brifing_lint(_payload(BRIF_KISA))
    ekle("B4 FP capasi: <400 karakter brif MUAF (hicbir not yok)",
         n4 is None, "not=%r" % (n4 or "")[:80])

    # --- B5: sablon zorunlu maddeyi tasiyor -------------------------------
    b = BRIEF.read_text(encoding="utf-8")
    ekle("B5 spawn-brief.md §9 zorunlu maddeyi TASIYOR",
         "ENGELLENİRSEN" in b and "SendMessage" in b and "26 dakika" in b,
         "uzunluk=%d" % len(b))

    # --- B6: REGRESYON — mevcut GOREV/KANIT-KURAL ekseni bozulmadi --------
    n5 = mod._brifing_lint(_payload("x" * 500)) or ""
    ekle("B6 regresyon: sablonsuz brifte GOREV/KANIT KURAL ekseni HALA uyarir",
         "R2 sablon izleri eksik" in n5, "not=%r" % n5[:110])

    return out


MUTASYONLAR = [
    ("M1 sablonda eski oneki geri getir (_DOM_)",
     "tmpl",
     lambda s: s.replace("| Domain | `{PKG}_D_*` | `^{PKG}_D_[A-Z0-9_]+$` |",
                         "| Domain | `{PKG}_DOM_*` | `^{PKG}_DOM_[A-Z0-9_]+$` |")),
    ("M2 lint'in ENGELLENIRSEN eksenini sok",
     "lint",
     lambda s: s.replace("        if yer and yazma and not engel:",
                         "        if False:")),
    ("M3 ekseni GENISLET (yazma sarti kalksin -> salt-okumada da atesler)",
     "lint",
     lambda s: s.replace("        if yer and yazma and not engel:",
                         "        if yer and not engel:")),
    # A4/A7'nin degismezi: Class satiri eski `ZCL_{PKG}_` bicimine donerse KIRMIZI.
    ("M4 Class satirini eski ZCL_{PKG}_ bicimine dondur",
     "tmpl",
     lambda s: s.replace("ZCL_{PKG_NOZ}_", "ZCL_{PKG}_")),
    # A6'nin AYRI degismezi: sablon dogru ama URETICI yer tutucuyu doldurmuyor.
    # (A4 bunu GORMEZ — yalniz metne bakar; uretici kosulmadan yakalanamaz.)
    ("M5 bootstrap haritasindan PKG_NOZ'u sok (sablon satiri dogru kalir)",
     "boot",
     lambda s: s.replace('        "PKG_NOZ": pkg_noz,\n', "")),
    # A8'in degismezi: Y onekini de atan turetim ad alani carpismasi uretir.
    ("M6 turetim Y'yi de atsin (YSD001 -> SD001)",
     "boot",
     lambda s: s.replace('pkg[0] == "Z"', 'pkg[0] in "ZY"')),
    # A5'in degismezi: kapanmis kararin bayat "acik" basligi geri gelirse KIRMIZI.
    ("M7 kapanis kaydini bayat AÇIK KARAR basligina geri cevir",
     "tmpl",
     lambda s: s.replace("KAPANDI — `Class`", "AÇIK KARAR — `Class`")),
]


def main() -> int:
    print("=" * 78)
    print("sablon_zorunlu_maddeler — sablon kusuru = her yeni paket/brif miras alir")
    print("=" * 78)

    ham = {"lint": LINT.read_text(encoding="utf-8"),
           "tmpl": TMPL.read_text(encoding="utf-8"),
           "boot": BOOT.read_text(encoding="utf-8")}

    mod = _lint_yukle(ham["lint"])
    sonuc = senaryolar(mod)
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
        try:
            if hedef == "tmpl":
                TMPL.write_text(bozuk, encoding="utf-8")
                try:
                    m_res = senaryolar(mod)
                finally:
                    TMPL.write_text(ham["tmpl"], encoding="utf-8")   # HER halukarda geri al
            elif hedef == "boot":
                m_res = senaryolar(mod, boot_src=bozuk)             # BELLEKTE; diske yazilmaz
            else:
                m_res = senaryolar(_lint_yukle(bozuk))
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:
            yakalandi, kacan = False, []
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    # Sablon dosyasi geri alindi mi (mutasyon kalintisi = SESSIZ BOZULMA)
    print("\n--- kalinti kontrolu ---")
    geri = TMPL.read_text(encoding="utf-8") == ham["tmpl"]
    print("  [%s] sablon dosyasi mutasyondan SONRA geri alindi" % ("OK" if geri else "KALINTI"))

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik or not geri:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        if not geri:
            print("FAIL — sablon dosyasinda MUTASYON KALINTISI kaldi")
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
