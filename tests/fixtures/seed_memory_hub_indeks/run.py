#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEED-MEMORY HUB INDEKSI korpusu (Q289, 2026-09-12).

NEDEN BU KORPUS VAR
-------------------
`seed_memory.py::_index_onar` bir seed dersini "indekste VAR" saymak icin YALNIZ hedef
`MEMORY.md`'deki `](x.md)` linklerine bakiyordu. Memory butce diyetiyle kayitlarin cogu
`_indeks-*.md` HUB'larina `- [[slug]] — oz` biciminde tasindi. Olculdu (canli memory'nin
.tmp kopyasi, `--dry-run`): 85 seed · 30'u MEMORY.md'de · 54'u YALNIZ hub'larda ·
eski kod **45 x "indekse eklendi"** (her kurulum turu hub'a tasinmis satirlari MEMORY.md'ye
GERI yazar, butce diyetini sessizce geri alir).

FIX: "indekste var" kumesi = `MEMORY.md` + ayni dizindeki `_indeks-*.md`, iki link bicimi.
Tanim Q287'nin `build_recall_index.py`'sinden IMPORT edilir (kopya DEGIL) — V-KABLO
vektoru bunu davranisla olcer: builder'daki wiki kolu bozulunca seed de bozulur.

⚠ SEMANTIK FARK (bilincli): builder'in YETIM geri-dususu (hicbir indekste olmayan dosya
description'dan kayit olur) seed icin "var" DEGILDIR — N2 bunu civiller. Hub-DISI bir ders
dosyasindaki `[[wiki]]` de "indeks" sayilmaz (C-MEM-01 onu erisilebilir sayar; seed yine
satir ekler = zararsiz fazlalik) — N3 bu siniri belgeler.

Sandbox: gercek `scripts/seed_memory.py` + `build_recall_index.py` + `utils/` bir gecici
core kopyasina alinir; seed dizini sentetiktir. Mutasyonlar YALNIZ sandbox kopyasina yazilir
(gercek kaynak kirlenmez).

KOSUM:  python tests/fixtures/seed_memory_hub_indeks/run.py [--mutasyon-<kip>]
        [--seed-kaynak <dosya>]   (eski surumu olcmek icin: `git show <sha>:scripts/seed_memory.py`)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (capa tutmadi / mutant derlenmedi)
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
SCRIPTS = REPO / "scripts"

# kip -> (hedef "S"=seed_memory | "B"=build_recall_index, eski, yeni)
MUTLAR = {
    # hub'lar okunmaz -> yalniz MEMORY.md (eski kapsam)
    "--mutasyon-hub-yok": ("S",
        "    for hub in _recall.indeks_hublari(dst):",
        "    for hub in []:  # MUTASYON: hub okunmaz"),
    # yerel link tanimina geri donus (eski LINK_RE: yalniz `](x.md)`)
    "--mutasyon-yerel-tanim": ("S",
        "    var_olan = _recall.metin_linkleri(metin)",
        "    var_olan = set(LINK_RE.findall(metin))  # MUTASYON: yerel kopya tanim"),
    # KABLOLAMA: paylasilan tanimin wiki kolu builder'da bozulur -> seed de gormemeli
    "--mutasyon-builder-wiki-yok": ("B",
        "        if m.group(1) is not None:\n"
        "            out.append((_slug_basligi(m.group(1)), _wiki_dosya(m.group(1))))",
        "        if m.group(1) is not None:\n"
        "            continue  # MUTASYON: [[slug]] linki taninmaz"),
    # GEVSETME yonu: builder'in yetim semantigi seed'e sizar (diskteki her dosya "var")
    "--mutasyon-yetim-var": ("S",
        "    var_olan = _recall.metin_linkleri(metin)",
        "    var_olan = _recall.metin_linkleri(metin) | {p.name for p in target.glob('*.md')}"
        "  # MUTASYON"),
}

SEED_ADLARI = ["feedback_kok.md", "feedback_hub-md.md", "feedback_hub-wiki.md",
               "feedback_hub-duzyazi.md", "feedback_mm-wiki.md", "feedback_yok.md",
               "feedback_yetim-diskte.md", "feedback_hubdisi-wiki.md"]
SEED_INDEX = "# Seed\n\n## Feedback\n\n" + "".join(
    f"- [{a[9:-3]}]({a}) — seed satiri {a[9:-3]}\n" for a in SEED_ADLARI)

HEDEF_MEMORY = """# Hafiza

## Feedback

- [Kok ders](feedback_kok.md) — MEMORY.md'de md-link
- MEMORY.md'de wiki bicimi: [[feedback_mm-wiki]]
- [Silinmis seed](feedback_silindi.md) — diskte yok, seed'de yok -> duser
- **Alt indeks:** [tam indeks](_indeks-a.md)
- [Ordinary](feedback_ordinary.md) — hub olmayan ders dosyasi
"""
HEDEF_HUB = """---
name: _indeks-a
description: hub
metadata:
  type: reference
---

- ⭐ [Hub md dersi](feedback_hub-md.md)
- [[feedback_hub-wiki]] — hub wiki satiri
Duzyazi alt kayitlar: [[feedback_baska-bir-sey]] · [[feedback_hub-duzyazi]]
"""
HEDEF_ORDINARY = "---\nname: ordinary\n---\n\nIlgili: [[feedback_hubdisi-wiki]]\n"

# Eski kodda da GECERLI olmasi gereken beklenen ekleme kumesi (negatif kontroller)
BEKLENEN_EKLENEN = {"feedback_yok.md", "feedback_yetim-diskte.md", "feedback_hubdisi-wiki.md"}

EKLENDI_RE = re.compile(r"indekse eklendi: (\S+)")
DUSTU_RE = re.compile(r"indeksten düştü: (\S+)")


def _md5_agaci(d: Path) -> dict:
    return {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(d.iterdir()) if p.is_file()}


def main() -> int:
    arg = sys.argv[1:]
    for a in arg:
        if a.startswith("--mutasyon") and a not in MUTLAR:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + ", ".join(sorted(MUTLAR)))
    secili = [a for a in arg if a in MUTLAR]
    seed_kaynak = SCRIPTS / "seed_memory.py"
    if "--seed-kaynak" in arg:
        seed_kaynak = Path(arg[arg.index("--seed-kaynak") + 1])

    tmp = Path(tempfile.mkdtemp(prefix="seed_hub_"))
    sonuc: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, aciklama=""):
        sonuc.append((ad, bool(kosul), aciklama))

    try:
        core = tmp / "core"
        (core / "scripts").mkdir(parents=True)
        shutil.copy2(seed_kaynak, core / "scripts" / "seed_memory.py")
        shutil.copy2(SCRIPTS / "build_recall_index.py", core / "scripts" / "build_recall_index.py")
        shutil.copytree(SCRIPTS / "utils", core / "scripts" / "utils",
                        ignore=shutil.ignore_patterns("__pycache__"))
        seed_dir = core / "claude" / "memory-seed"
        seed_dir.mkdir(parents=True)
        for a in SEED_ADLARI:
            (seed_dir / a).write_text(f"---\nname: {a[:-3]}\n---\n\nseed govdesi\n", encoding="utf-8")
        (seed_dir / "MEMORY.md").write_text(SEED_INDEX, encoding="utf-8")

        if secili:
            tur, eski, yeni = MUTLAR[secili[0]]
            hedef_dosya = core / "scripts" / ("seed_memory.py" if tur == "S" else "build_recall_index.py")
            kaynak = hedef_dosya.read_text(encoding="utf-8")
            if eski not in kaynak:
                print(f"[DOGRULANAMADI] mutasyon capasi bulunamadi ({secili[0]}) -> "
                      "mutasyon uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
                return 2
            hedef_dosya.write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8")
            try:
                compile(hedef_dosya.read_text(encoding="utf-8"), str(hedef_dosya), "exec")
            except SyntaxError as e:
                print(f"[DOGRULANAMADI] mutant SOZDIZIMI BOZUK ({secili[0]}): {e}")
                return 2

        def kos(target: Path, *ek):
            env = dict(os.environ)
            env["PYTHONIOENCODING"] = "utf-8"
            env["CLAUDE_PROJECT_DIR"] = str(tmp / "proje")
            p = subprocess.run([sys.executable, str(core / "scripts" / "seed_memory.py"),
                                "--target", str(target), *ek], env=env, cwd=str(tmp),
                               capture_output=True, timeout=120)
            out = p.stdout.decode("utf-8", "replace")
            return p.returncode, out, p.stderr.decode("utf-8", "replace")

        # ================= SAHNE 1: hub'li hedef ===============================
        hedef = tmp / "mem1"
        hedef.mkdir()
        for a in SEED_ADLARI:                       # hepsi diskte (tipik kurulmus proje)
            (hedef / a).write_text(f"---\nname: {a[:-3]}\n---\n\nyerel\n", encoding="utf-8")
        (hedef / "MEMORY.md").write_text(HEDEF_MEMORY, encoding="utf-8")
        (hedef / "_indeks-a.md").write_text(HEDEF_HUB, encoding="utf-8")
        (hedef / "feedback_ordinary.md").write_text(HEDEF_ORDINARY, encoding="utf-8")

        once = _md5_agaci(hedef)
        rc, out, err = kos(hedef, "--dry-run")
        sonra = _md5_agaci(hedef)
        eklenen = set(EKLENDI_RE.findall(out))
        dusen = set(DUSTU_RE.findall(out))
        ekle("E1 dry-run exit 0, Traceback yok", rc == 0 and "Traceback" not in err,
             f"rc={rc} err={err[:300]!r}")
        ekle("D1 dry-run HICBIR dosyayi degistirmez (md5 once==sonra)", once == sonra,
             f"fark={sorted(k for k in once if once.get(k) != sonra.get(k))}")
        ekle("P1 hub'daki `[Baslik](x.md)` seed'i -> EKLENMEZ",
             "feedback_hub-md.md" not in eklenen, f"eklenen={sorted(eklenen)}")
        ekle("P2 hub'daki `- [[slug]] — oz` seed'i -> EKLENMEZ",
             "feedback_hub-wiki.md" not in eklenen, f"eklenen={sorted(eklenen)}")
        ekle("P3 hub DUZYAZI satirindaki `[[slug]]` seed'i -> EKLENMEZ",
             "feedback_hub-duzyazi.md" not in eklenen, f"eklenen={sorted(eklenen)}")
        ekle("P4 MEMORY.md'deki `[[slug]]` seed'i -> EKLENMEZ",
             "feedback_mm-wiki.md" not in eklenen, f"eklenen={sorted(eklenen)}")
        ekle("C1 MEMORY.md md-link seed'i -> EKLENMEZ (mevcut davranis)",
             "feedback_kok.md" not in eklenen)
        ekle("N1 hicbir indekste OLMAYAN seed -> EKLENIR (negatif kontrol)",
             "feedback_yok.md" in eklenen, f"eklenen={sorted(eklenen)}")
        ekle("N2 diskte olan ama hicbir indekste olmayan seed -> EKLENIR (yetim 'var' DEGIL)",
             "feedback_yetim-diskte.md" in eklenen, f"eklenen={sorted(eklenen)}")
        ekle("N3 yalniz hub-DISI ders dosyasindaki `[[wiki]]` -> EKLENIR (sinir, belgelenmis)",
             "feedback_hubdisi-wiki.md" in eklenen, f"eklenen={sorted(eklenen)}")
        ekle("C2 eklenen kume TAM beklenen", eklenen == BEKLENEN_EKLENEN,
             f"fazla={sorted(eklenen - BEKLENEN_EKLENEN)} eksik={sorted(BEKLENEN_EKLENEN - eklenen)}")
        ekle("C3 olu link temizligi aynen: `feedback_silindi.md` duser, baska sey dusmez",
             dusen == {"feedback_silindi.md"}, f"dusen={sorted(dusen)}")

        # gercek kosum: yazar, hub'a dokunmaz, ikinci kosum idempotent
        hub_md5 = hashlib.md5((hedef / "_indeks-a.md").read_bytes()).hexdigest()
        rc2, out2, err2 = kos(hedef)
        mm = (hedef / "MEMORY.md").read_text(encoding="utf-8")
        ekle("W1 gercek kosum exit 0 + MEMORY.md'ye yalniz beklenen 3 seed satiri",
             rc2 == 0 and all(f"]({a})" in mm for a in BEKLENEN_EKLENEN)
             and "](feedback_hub-wiki.md)" not in mm and "](feedback_hub-md.md)" not in mm,
             f"rc={rc2} err={err2[:200]!r}")
        ekle("W2 hub dosyasi seed tarafindan DEGISTIRILMEZ",
             hashlib.md5((hedef / "_indeks-a.md").read_bytes()).hexdigest() == hub_md5)
        rc3, out3, _ = kos(hedef, "--dry-run")
        ekle("W3 ikinci kosum idempotent: 0 x 'indekse eklendi'",
             rc3 == 0 and not EKLENDI_RE.findall(out3), f"eklenen={EKLENDI_RE.findall(out3)}")

        # ================= SAHNE 2 (3. baglam): hub'SIZ, `## Feedback`siz eski proje sekli ===
        hedef2 = tmp / "mem2"
        hedef2.mkdir()
        (hedef2 / "MEMORY.md").write_text("# Eski bicim\n\n- [Kok](feedback_kok.md) — var\n",
                                          encoding="utf-8")
        rc4, out4, err4 = kos(hedef2)
        mm2 = (hedef2 / "MEMORY.md").read_text(encoding="utf-8")
        eklenen2 = set(EKLENDI_RE.findall(out4))
        ekle("B1 hub'siz hedef: MEMORY.md disindaki 7 seed eklenir, `## Feedback` acilir",
             rc4 == 0 and eklenen2 == set(SEED_ADLARI) - {"feedback_kok.md"}
             and "\n## Feedback\n" in mm2, f"rc={rc4} eklenen={sorted(eklenen2)} err={err4[:200]!r}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for _a, k, _c in sonuc if k)
    for ad, k, ac in sonuc:
        print(f"  [{'PASS' if k else 'FAIL'}] {ad}" + (f"  ({ac})" if ac and not k else ""))
    print(f"\nseed_memory_hub_indeks: {gecen}/{len(sonuc)}")
    if secili:
        print(f"  (MUTASYON {secili[0]} — dusmesi BEKLENEN vektorler var; "
              f"tam skor 'mutasyon KACTI' demektir)")
    return 0 if gecen == len(sonuc) and sonuc else 1


if __name__ == "__main__":
    raise SystemExit(main())
