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

Issue #430 (2026-11-15): Feedback basligi SATIR olarak bulunur (`## Feedback — konu`, sonda
bosluk, CRLF, EOF'ta yeni satirsiz; `## Feedbacks` baska basliktir) -> SAHNE 3 (8 varyant x 5
vektor; eski kodda `— konu`/bosluk/EOF/`Feedbacks` varyantlarinda ekleme NO-OP iken
"indekse eklendi" basiliyordu). "indekse eklendi" ve ozet `[OK]` satiri yalniz gercekten
yapilani soyler -> SAHNE 4 (ekleme ENJEKSIYONLA etkisiz kilinir; durust rapor yalniz gercek
basarisizlikta olculebilir). Eski surum `--seed-kaynak` ile koşulunca sahne 4 kurulamaz (exit 2).

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
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


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
    # --- Issue #430 (2026-11-15): baslik SATIR olarak bulunur + basari eylemden SONRA ---
    # ekleme eski tam-satir replace'e doner (baslik varyantlarinda NO-OP) -> H* kirmizi
    "--mutasyon-eski-ekleme": ("S",
        '            yeni = (metin[:son] + "\\n\\n" + blok + ("\\n" if son == len(metin) else "")\n'
        "                    + metin[son:])",
        '            yeni = metin.replace("## Feedback\\n", "## Feedback\\n\\n" + blok + "\\n", 1)'
        "  # MUTASYON"),
    # baslik tam satira daraltilir (`## Feedback — konu` taninmaz -> ikinci baslik acilir)
    "--mutasyon-tam-satir-baslik": ("S",
        'FEEDBACK_BASLIK_RE = re.compile(r"^## Feedback\\b[^\\n]*$", re.MULTILINE)',
        'FEEDBACK_BASLIK_RE = re.compile(r"^## Feedback$", re.MULTILINE)  # MUTASYON'),
    # "indekse eklendi" degisiklik olculmeden yazilir (Issue #430'un sahte basarisi)
    "--mutasyon-basari-once": ("S",
        '            islem.append(f"indekse eklendi: {ad}" if ad in sonra',
        '            islem.append(f"indekse eklendi: {ad}" if True  # MUTASYON\n'),
    # ozet eklenemeyen satiri gormez -> "[OK] tohumlandi/onarildi" basilir
    "--mutasyon-ozet-uyari-yok": ("S",
        "    elif elle or index_uyari:",
        "    elif elle:  # MUTASYON"),
    # ozet ne yapildigini saymaz (eski genel cumle)
    "--mutasyon-ozet-sayim-yok": ("S",
        '"\\n[OK] Feedback memory tohumlandı/onarıldı: " + " · ".join(yapilan)',
        '"\\n[OK] Feedback memory tohumlandı/onarıldı: " + ""  # MUTASYON\n'
        '                  '),
}

# #430 ENJEKSIYON (sahne 4): ekleme blogu BOSALTILIR -> satir gercekten eklenemez. Durust
# raporlama ancak gercek bir basarisizlikta gorulur; temiz kodda ekleme hic basarisiz olmaz.
ENJEKSIYON = ('        blok = "\\n".join(eklenecek)\n',
              '        blok = ""  # ENJEKSIYON: ekleme etkisiz\n')

# #430 baslik varyantlari: (ad, MEMORY.md baytlari). Hepsinde 7 seed eklenmeli ve satirlar
# ILK Feedback basliginin altina (bir sonraki `## ` basligindan once) dusmeli.
_GOVDE = "- [Kok](feedback_kok.md) — var\n"
BASLIK_VARYANTLARI = [
    ("H-tam (kontrol)", f"# M\n\n## Feedback\n\n{_GOVDE}\n## Diger\n\n- x\n".encode()),
    ("H-ek-metin", f"# M\n\n## Feedback — konu indeksleri\n\n{_GOVDE}\n## Diger\n\n- x\n".encode()),
    ("H-sonda-bosluk", f"# M\n\n## Feedback \n\n{_GOVDE}\n## Diger\n\n- x\n".encode()),
    ("H-crlf-ek-metin", f"# M\n\n## Feedback — x\n\n{_GOVDE}\n## Diger\n\n- x\n"
     .replace("\n", "\r\n").encode()),
    ("H-crlf-tam", f"# M\n\n## Feedback\n\n{_GOVDE}".replace("\n", "\r\n").encode()),
    ("H-eof-yeni-satirsiz", f"# M\n\n{_GOVDE}\n## Feedback".encode()),
    ("H-iki-baslik (ilk ek metinli)", f"# M\n\n## Feedback — a\n\n{_GOVDE}\n## Feedback\n\n- y\n"
     .encode()),
    ("H-feedbacks-baska-baslik", f"# M\n\n## Feedbacks\n\n{_GOVDE}".encode()),
]


class _SahneAtla(Exception):
    pass


def _ilk_feedback_bolumu(metin: str) -> tuple[int, int]:
    """(baslik satiri, bolum sonu) — test kendi tanimini kullanir (kod regex'ine BAKMAZ)."""
    satirlar = metin.splitlines()
    bas = next((i for i, s in enumerate(satirlar)
                if s == "## Feedback" or s.startswith("## Feedback ")), -1)
    if bas < 0:
        return -1, -1
    son = next((i for i in range(bas + 1, len(satirlar)) if satirlar[i].startswith("## ")),
               len(satirlar))
    return bas, son

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
    kurulamadi: list[str] = []
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

        # ================= SAHNE 3 (#430): Feedback BASLIK VARYANTLARI =================
        beklenen7 = set(SEED_ADLARI) - {"feedback_kok.md"}
        for i, (ad, bayt) in enumerate(BASLIK_VARYANTLARI):
            h = tmp / f"mem_h{i}"
            h.mkdir()
            (h / "MEMORY.md").write_bytes(bayt)
            rc_h, out_h, err_h = kos(h)
            ham = (h / "MEMORY.md").read_bytes()
            mm_h = ham.decode("utf-8").replace("\r\n", "\n")
            satirlar = mm_h.splitlines()
            bas, son = _ilk_feedback_bolumu(mm_h)
            dosyada = {a for a in beklenen7 if f"]({a})" in mm_h}
            yerinde = {a for a in beklenen7
                       if any(f"]({a})" in s for s in satirlar[bas + 1:son])} if bas >= 0 else set()
            soylenen = set(EKLENDI_RE.findall(out_h))
            son_s = [s for s in out_h.strip().splitlines() if s.strip()][-1:] or [""]
            ekle(f"{ad}: 7 seed satiri MEMORY.md'de GERCEKTEN var",
                 rc_h == 0 and dosyada == beklenen7,
                 f"rc={rc_h} eksik={sorted(beklenen7 - dosyada)} err={err_h[:160]!r}")
            ekle(f"{ad}: satirlar ILK Feedback basligi altinda (sonraki `## `ten once)",
                 yerinde == beklenen7, f"bas={bas} son={son} disarda={sorted(beklenen7 - yerinde)}")
            ekle(f"{ad}: 'indekse eklendi' = dosyada gercekten eklenen + uyari yok",
                 soylenen == dosyada and "EKLENEMEDİ" not in out_h,
                 f"soylenen-dosyada={sorted(soylenen - dosyada)}")
            ekle(f"{ad}: ozet yapilani sayar ('[OK] … indekse eklendi 7')",
                 son_s[0].startswith("[OK] Feedback memory tohumlandı/onarıldı:")
                 and "indekse eklendi 7" in son_s[0], f"son={son_s[0][:160]!r}")
            n_crlf, n_lf = ham.count(b"\r\n"), ham.count(b"\n")
            ekle(f"{ad}: satir sonu karismadi (ya hep CRLF ya hep LF)",
                 n_crlf in (0, n_lf), f"crlf={n_crlf} lf={n_lf}")

        # ================= SAHNE 4 (#430): ekleme ENJEKTE basarisiz -> DURUST rapor ======
        try:
            core_e = tmp / "core_enj"
            shutil.copytree(core, core_e, ignore=shutil.ignore_patterns("__pycache__"))
            sm_e = core_e / "scripts" / "seed_memory.py"
            k_e = sm_e.read_text(encoding="utf-8")
            if ENJEKSIYON[0] not in k_e:
                # ESKI surum (--seed-kaynak) bu capayi tasimaz: sahne 1-3 yine raporlanir, cikis 2.
                kurulamadi.append("sahne 4: enjeksiyon capasi bulunamadi (eski surum?)")
                raise _SahneAtla
            sm_e.write_text(k_e.replace(ENJEKSIYON[0], ENJEKSIYON[1], 1), encoding="utf-8")
            h = tmp / "mem_enj"
            h.mkdir()
            (h / "MEMORY.md").write_bytes(BASLIK_VARYANTLARI[1][1])
            env = dict(os.environ, PYTHONIOENCODING="utf-8", CLAUDE_PROJECT_DIR=str(tmp / "proje"))
            p = subprocess.run([sys.executable, str(sm_e), "--target", str(h)], env=env, cwd=str(tmp),
                               capture_output=True, timeout=120)
            out_e = p.stdout.decode("utf-8", "replace")
            mm_e = (h / "MEMORY.md").read_text(encoding="utf-8")
            son_e = [s for s in out_e.strip().splitlines() if s.strip()][-1:] or [""]
            dosyada_e = {a for a in beklenen7 if f"]({a})" in mm_e}
            ekle("ENJ0 kurulum: enjeksiyon gercekten etkili (dosyada 0 seed satiri)",
                 p.returncode == 0 and not dosyada_e, f"rc={p.returncode} dosyada={sorted(dosyada_e)}")
            ekle("ENJ1 eklenemeyen ad icin 'indekse eklendi' DENMEZ (eylemden once basari yok)",
                 not EKLENDI_RE.findall(out_e), f"soylenen={EKLENDI_RE.findall(out_e)}")
            ekle("ENJ2 ad basina '[UYARI] indekse EKLENEMEDİ' basilir (7 satir)",
                 out_e.count("indekse EKLENEMEDİ") == 7, f"sayi={out_e.count('indekse EKLENEMEDİ')}")
            ekle("ENJ3 son satir [UYARI], '[OK] … tohumlandı/onarıldı' YOK",
                 son_e[0].startswith("[UYARI]") and "tohumlandı/onarıldı" not in out_e,
                 f"son={son_e[0][:160]!r}")
        except _SahneAtla:
            pass
    finally:
        _sil(tmp)                                    # Q319: kopyalanan scripts/utils salt-okur

    gecen = sum(1 for _a, k, _c in sonuc if k)
    for ad, k, ac in sonuc:
        print(f"  [{'PASS' if k else 'FAIL'}] {ad}" + (f"  ({ac})" if ac and not k else ""))
    print(f"\nseed_memory_hub_indeks: {gecen}/{len(sonuc)}")
    if secili:
        print(f"  (MUTASYON {secili[0]} — dusmesi BEKLENEN vektorler var; "
              f"tam skor 'mutasyon KACTI' demektir)")
    for k in kurulamadi:
        print(f"  [DOGRULANAMADI] {k}")
    if kurulamadi:
        return 2
    return 0 if gecen == len(sonuc) and sonuc else 1


if __name__ == "__main__":
    raise SystemExit(main())
