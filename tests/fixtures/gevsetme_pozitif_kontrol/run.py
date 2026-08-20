#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PARTI-3: IKI GEVSETME — her biri POZITIF KONTROLLU (kullanici onayli, 2026-08-20).

Bu korpusun VAR OLMA SEBEBI: gevsetme onayi *"kapiyi korletmedigini KANITLA"* sartiyla
alindi. Asagidaki `⭐ POZITIF KONTROL` vektorleri o kanittir; **SILINEMEZLER** — onlar
olmadan iki gevsetme kanitsiz kalir ve bir sonraki bakimci sinirin nerede oldugunu
bilemez.

=== A) check_itg_signoff — BICIM toleransi (varlik/doluluk DEGIL) ===
OLCULEN FP: icerigi TAM ve canli-dogrulanmis bir artefakt BLOCKER aldi. Iki katman:
  ① baslik `## 3. ETKILENEN / ILGILI OBJELER — CANLI DOGRULANDI`; desen
     `etkilenen\\s+obje` araya giren `/ ILGILI` yuzunden ESLESMEDI -> "alan eksik".
  ② prior-art `- **Prior-art:** \\`ref_docs/RESEARCH-…\\`` (deger DOLU) ama kural
     literal `bulundu`/`yok` sozcugunu sart kosuyordu -> "alan bos/belirsiz".
  ⚠ UCUNCU katman kod okunurken bulundu: gercek artefaktlar alani `Alan: deger` satiri
     yerine MARKDOWN BASLIGI olarak yaziyor; o satirda `:` YOKTUR ⇒ deger cikarici hic
     eslesmez ve alan "degeri bos" sanilir. Tolerans her iki bicime kuruldu.
Maliyeti yuksekti: kapi BLOCKER, mesaj "alan eksik" diyordu ama alan VARDI ⇒ okuyan
belgeyi YENIDEN YAZMAYA girisiyordu.

⛔ NE GEVSEMEDI: 2026-08-01'de eklenen DEGER DOLULUGU zinciri (`_deger` + `_dolu_mu` +
`_YER_TUTUCULAR`). Bos sablon + `MUTABAKAT: [x]` bu kapiyi HALA GECEMEZ (A2/A3/A4).

=== B) worktree dislama — tarama kapsami ===
OLCULEN FP: worktree'de kosan pre-commit'te bu gate'in ozeti **87 satir / 22 dokuman ->
174 satir / 44 dokuman** oldu; her bulgu IKI KEZ listelendi. Worktree GECICI bir
checkout'tur: oradaki bulgu AYNI bulgudur. Ters yon daha kotu: worktree'de DUZELTILMIS
bir dosya varken ana agactaki bozuk surum de sayilir ⇒ "kac ihlal kaldi" YANILTICI.

⭐ SINIF DUZELTMESI: ilk denetimim "4 validator" demisti — cunku `rg _SKIP_SEGMENTS`
ile aramistim. Ad-bagimsiz tarama (`dirnames[:]`) sinifi **8 validator** gosterdi
(`_SKIP_SEGMENTS` ×4 · `_SKIP` ×1 · `_prune` ×3). Sekizine de eklendi.

  A1     OLCULEN FP artik GECIYOR
  A2-A4  ⭐ POZITIF KONTROLLER: bos sablon · tolere-edilen baslik ama BOS bolum ·
         prior-art duzyazi (referans izi yok) -> UCU DE HALA BLOCKER
  A5     FP capasi: kisa ama mesru `Prior-art: yok` gecmeye devam eder
  A6     teshis mesaji DENENEN DESENI yaziyor (eskiden gate kaynagi okunuyordu)
  A7     tolerans SINIRI: araya cok uzun metin / `:` asan eslesme SAYILMAZ
  B1     OLCULEN FP: worktree kopyasi bulgulari CIFTLEMIYOR
  B2     ⭐ POZITIF KONTROL: ana agactaki GERCEK ihlal HALA yakalanir
  B3     3. BAGLAM: worktree ICINDEN kosum kendi agacini TAM tarar
  B4     KABLOLAMA: 8 walk-pruner'in HEPSINDE `worktrees` (ad-bagimsiz tarama)
  M1-M5  fix'i sok -> korpus KIRMIZI olmali

Kosum: python tests/fixtures/gevsetme_pozitif_kontrol/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import re
import shutil
import subprocess
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
VALIDATORS = CORE / "scripts" / "validators"
ITG = VALIDATORS / "check_itg_signoff.py"
FSLOG = VALIDATORS / "check_fs_no_analysis_log.py"

TMP = Path(tempfile.mkdtemp(prefix="gevsetme_"))


def kos_itg(metin: str, validator: Path = ITG) -> tuple[int, str]:
    f = TMP / "artefakt.md"
    f.write_text(metin, encoding="utf-8")
    r = subprocess.run([sys.executable, str(validator), str(f)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr)


def _mod(yol: Path, src: str, ad: str):
    m = types.ModuleType(ad)
    m.__file__ = str(yol)
    exec(compile(src, str(yol), "exec"), m.__dict__)
    return m


# --- Artefakt sekilleri (gercek vakadan turetildi; adlar jenerik) ------------
FP_VAKASI = """# INTAKE ARTEFAKTI — S2

KAPSAM: SD / rapor / S2 (gerekce: yeni zincir, 9 tablo etkileniyor)

## 3. ETKILENEN / ILGILI OBJELER — CANLI DOGRULANDI
- ZSD001_T_ORDER -> degisir -> blast-radius: 3 CDS
- ZSD001_I_ITEM  -> yeni

- **Prior-art:** `ref_docs/RESEARCH-05-CANLI-TEYIT.md`

## KABUL KRITERLERI
- "Kullanici sevk emri girdiginde sistem lot tahsisi yapmali"

MUTABAKAT: [x] kullanici onayladi
"""
BOS_SABLON = """# INTAKE ARTEFAKTI — S2
KAPSAM:
## ETKILENEN OBJELER
Prior-art:
## KABUL KRITERLERI
MUTABAKAT: [x]
"""
TOLERE_AMA_BOS = """# INTAKE ARTEFAKTI — S2
KAPSAM: SD / rapor / S2 (gerekce: gercek gerekce)

## 3. ETKILENEN / ILGILI OBJELER — CANLI DOGRULANDI

## KABUL KRITERLERI
- "X olunca Y"

- **Prior-art:** `ref_docs/X.md`

MUTABAKAT: [x]
"""
PA_DUZYAZI = """# INTAKE ARTEFAKTI — S2
KAPSAM: SD / rapor / S2 (gerekce: gercek)
## ETKILENEN / ILGILI OBJELER
- ZSD001_T_X -> yeni
- **Prior-art:** benzer bir sey vardi galiba ama emin degilim
## KABUL KRITERLERI
- "X olunca Y"
MUTABAKAT: [x]
"""
PA_YOK = """# INTAKE ARTEFAKTI — S2
KAPSAM: SD / rapor / S2 (gerekce: gercek)
## ETKILENEN OBJELER
- ZSD001_T_X -> yeni
Prior-art: yok
## KABUL KRITERLERI
- "X olunca Y"
MUTABAKAT: [x]
"""
ALAN_YOK = """# INTAKE ARTEFAKTI — S2
KAPSAM: SD / rapor / S2 (gerekce: gercek)
## KABUL KRITERLERI
- "X olunca Y"
Prior-art: yok
MUTABAKAT: [x]
"""

# İhlalli FS gövdesi (fs gate'in yakaladığı sınıf: analiz-günlüğü izi)
IHLALLI_FS = """# FS-TEST — Fonksiyonel Sartname

## 2. Kapsam
Onceden `X` yaziyordu, simdi `Y` olacak.
Bu karar 2026-08-01'de olculdu ve v1.2'de degistirildi.
"""


def _fs_agaci(worktree_kopyasi: bool) -> Path:
    d = Path(tempfile.mkdtemp(prefix="fsagac_"))
    (d / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "docs").mkdir(parents=True)
    (d / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "docs" / "FS-TEST.md").write_text(
        IHLALLI_FS, encoding="utf-8")
    if worktree_kopyasi:
        wt = d / ".claude" / "worktrees" / "agent-x" / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "docs"
        wt.mkdir(parents=True)
        (wt / "FS-TEST.md").write_text(IHLALLI_FS, encoding="utf-8")
    return d


def senaryolar(itg_yolu: Path = ITG, fs_src: str | None = None) -> list[tuple[str, bool, str]]:
    out = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    # ================= A) check_itg_signoff ================================
    rc, o = kos_itg(FP_VAKASI, itg_yolu)
    ekle("A1 OLCULEN FP: '/ ILGILI' baslikli + backtick'li prior-art -> PASS",
         rc == 0, "rc=%s cikti=%r" % (rc, o[:130]))

    rc, o = kos_itg(BOS_SABLON, itg_yolu)
    ekle("A2 ⭐POZITIF KONTROL: bos sablon + [x] -> HALA BLOCKER",
         rc == 1, "rc=%s" % rc)

    rc, o = kos_itg(TOLERE_AMA_BOS, itg_yolu)
    ekle("A3 ⭐POZITIF KONTROL: tolere edilen baslik ama BOLUM BOS -> BLOCKER",
         rc == 1 and "DEĞERİ boş" in o, "rc=%s cikti=%r" % (rc, o[:130]))

    rc, o = kos_itg(PA_DUZYAZI, itg_yolu)
    ekle("A4 ⭐POZITIF KONTROL: prior-art DUZYAZI (referans izi yok) -> BLOCKER",
         rc == 1 and "Prior-art" in o, "rc=%s cikti=%r" % (rc, o[:130]))

    rc, o = kos_itg(PA_YOK, itg_yolu)
    ekle("A5 FP capasi: kisa ama mesru 'Prior-art: yok' -> PASS",
         rc == 0, "rc=%s cikti=%r" % (rc, o[:130]))

    rc, o = kos_itg(ALAN_YOK, itg_yolu)
    ekle("A6 teshis: alan HIC yoksa DENENEN DESEN mesajda yazili",
         rc == 1 and "denenen desen" in o, "rc=%s cikti=%r" % (rc, o[:160]))

    # A7: tolerans SINIRI — `:` asan / cok uzun ara eslesmemeli
    src = itg_yolu.read_text(encoding="utf-8")
    m = re.search(r"_ARA = r\"(.+?)\"", src)
    ekle("A7 tolerans SINIRLI: ara desen `\\n` ve `:` disliyor + uzunluk sinirli",
         bool(m) and "^\\n:" in m.group(1) and "{0,24}" in m.group(1),
         "_ARA=%r" % (m.group(1) if m else None))

    # ================= B) worktree dislama =================================
    fs_kaynak = fs_src if fs_src is not None else FSLOG.read_text(encoding="utf-8")
    fs = _mod(FSLOG, fs_kaynak, "fs_x")

    d_wt = _fs_agaci(worktree_kopyasi=True)
    d_yalin = _fs_agaci(worktree_kopyasi=False)
    try:
        n_wt = len(list(fs._iter_docs(d_wt)))
        n_yalin = len(list(fs._iter_docs(d_yalin)))
        ekle("B1 OLCULEN FP: worktree kopyasi dokumanlari CIFTLEMIYOR (%d == %d)"
             % (n_wt, n_yalin), n_wt == n_yalin == 1,
             "worktree'li=%d yalin=%d" % (n_wt, n_yalin))

        # B2: ⭐ ana agactaki GERCEK ihlal HALA yakalanir
        dosyalar = list(fs._iter_docs(d_wt))
        bulgu = 0
        if dosyalar:
            f, _lr, _bl = fs.scan_text(dosyalar[0].read_text(encoding="utf-8"))
            bulgu = sum(len(v) for v in f.values())
        ekle("B2 ⭐POZITIF KONTROL: ana agactaki GERCEK ihlal yakalanir (%d bulgu)" % bulgu,
             bulgu >= 1, "bulgu=%d dosya=%s" % (bulgu, dosyalar[:1]))

        # B3: 3. BAGLAM — worktree ICINDEN kosum kendi agacini tarar
        wt_koku = d_wt / ".claude" / "worktrees" / "agent-x"
        n_ic = len(list(fs._iter_docs(wt_koku)))
        ekle("B3 3.baglam: worktree ICINDEN kosumda kendi agaci TAM taranir",
             n_ic == 1, "worktree-icinden=%d" % n_ic)
    finally:
        shutil.rmtree(d_wt, ignore_errors=True)
        shutil.rmtree(d_yalin, ignore_errors=True)

    # B4: KABLOLAMA — 8 walk-pruner'in hepsinde `worktrees`
    eksik = []
    for p in sorted(VALIDATORS.glob("check_*.py")):
        s = p.read_text(encoding="utf-8")
        if "dirnames[:]" in s and "worktrees" not in s:
            eksik.append(p.name)
    toplam = sum(1 for p in VALIDATORS.glob("check_*.py")
                 if "dirnames[:]" in p.read_text(encoding="utf-8"))
    ekle("B4 KABLOLAMA: %d walk-pruner'in HEPSINDE `worktrees` (ad-bagimsiz tarama)" % toplam,
         not eksik and toplam >= 8, "eksik=%s toplam=%d" % (eksik, toplam))

    return out


MUTASYONLAR = [
    ("M1 itg baslik toleransini geri al (`etkilenen\\s+obje`)", "itg",
     lambda s: s.replace('_ARA = r"[^\\n:]{0,24}"', '_ARA = r"\\s+"')),
    ("M2 prior-art'i literal `bulundu` sartina dondur", "itg",
     lambda s: s.replace(
         "    return bool(_PA_OLUMSUZ.search(deger) or _PA_REFERANS.search(deger))",
         '    return bool(re.search(r"\\\\b(bulundu|found)\\\\b", deger, re.I))')),
    ("M3 ⭐SINIR: doluluk zincirini sok (`_dolu_mu` hep True)", "itg",
     lambda s: s.replace('    d = " ".join(deger.split()).strip().lower()\n'
                         "    if not d:\n        return False\n",
                         '    d = " ".join(deger.split()).strip().lower()\n'
                         "    return True\n    if not d:\n        return False\n")),
    ("M4 bir validator'dan `worktrees`i cikar (kablolama)", "fs",
     lambda s: s.replace('"archive", "worktrees"}', '"archive"}')),
    ("M5 fs gate'in prune'unu tumden sok", "fs",
     lambda s: s.replace("        dirnames[:] = [d for d in dirnames if d.lower() not in _SKIP]\n",
                         "")),
]


def main() -> int:
    print("=" * 78)
    print("gevsetme_pozitif_kontrol — IKI GEVSETME, her biri POZITIF KONTROLLU")
    print("=" * 78)

    ham_itg = ITG.read_text(encoding="utf-8")
    ham_fs = FSLOG.read_text(encoding="utf-8")

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
        ham = ham_itg if hedef == "itg" else ham_fs
        bozuk = mut(ham)
        if bozuk == ham:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        try:
            if hedef == "itg":
                # ⚠ Mutant GERCEK `validators/` dizininde yasar (B24 dersi): validator
                # kendi yolundan komsu modulleri cozer; tempdir'e kopyalanirsa import
                # OLUR ve HER mutasyon "yakalandi" gorunur (SAHTE-KIRMIZI).
                mutant = VALIDATORS / "_mutant_itg.py"
                try:
                    mutant.write_text(bozuk, encoding="utf-8")
                    m_res = senaryolar(itg_yolu=mutant)
                finally:
                    mutant.unlink(missing_ok=True)
            else:
                m_res = senaryolar(fs_src=bozuk)
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
