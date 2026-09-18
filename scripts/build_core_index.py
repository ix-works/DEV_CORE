#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`<proje>/governance/CORE-INDEX.md` üretir — metodolojiyi KÖKTEN ARANABİLİR yapar.

NEDEN (2026-07-09 denetimi, ölçümle):
`core/` bir junction'dır. `Grep` ve `Glob` junction'ı **takip etmez** — ignore'lu olsun
olmasın. Kontrollü deney: ignore'suz bir junction'ın arkasındaki dosya iki araçla da
BULUNAMADI; aynı dosya gerçek dizindeyken BULUNDU. Yani sorun `.gitignore` DEĞİL:
`/core/` satırını silmek ya da `respectGitignore:false` yapmak **hiçbir şeyi değiştirmez.**

Sonuç: core'daki 199 doküman, lider ve TÜM alt-ajanların varsayılan arama yüzeyinde
**sessizce görünmez**. Sıfır sonuç "böyle bir kural yok" diye okunur.

ÇÖZÜM: junction'ı kaldıramayız (tek-kaynak mimarisi ona dayanıyor), ama **gerçek bir
indeks dosyası** üretebiliriz. `governance/CORE-INDEX.md` proje reposunda GERÇEK dosyadır
→ kökten `Grep`/`Glob` onu bulur → doğru `core/...` yolunu verir → `Read` çalışır.

Yani arama körlüğü bir KURAL'la (D29) değil, bir ARTEFAKT'la kapatılır.
Tazelik `check_core_index_fresh.py` ile gate'lenir; bayat indeks = sessiz yanlış yol.

Kullanım:  python core/scripts/build_core_index.py [--check]
  --check : yazmadan, mevcut indeksle karşılaştır (validator kullanır); fark → exit 1
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE / "scripts"))
from utils.project_config import project_root  # type: ignore  # noqa: E402

PROJ = project_root()
HEDEF = PROJ / "governance" / "CORE-INDEX.md"

# Taranan core alanları (metodoloji). scripts/ ve mcp_servers/ dışarıda: kod, doküman değil.
# ÖZYİNELİ alanlar (alt dizinler dahil):
# 2026-09-18 (Q331): `claude/templates` eklendi. Ölçüldü (bir tüketici projenin indeksinde):
# `claude/`=0 · `spawn-brief`=0 eşleşme; 24 ajanlık bir turda spawn şablonu BULUNAMADI ve
# sıfırdan yeniden icat edildi — oysa `spawn-brief.md` kendi başında "Kanonik ev BURASI"
# diyor. ⛔ `claude/` BÜTÜNÜYLE eklenmez: `claude/rules` ve `claude/agents` projeye FİZİKSEL
# kopya olarak iner (kökten zaten aranır → indekste ÇİFT olurdu), `memory-seed` ders
# deposudur, kalanı ayar/şablon dosyasıdır.
ALANLAR = ["playbook", "standards", "profiles", "governance/decisions", "claude/templates"]

# DÜZ alanlar (YALNIZ o dizinin kendi *.md'si; alt dizinleri AYRI bölümde listelenir).
# 2026-08-01 (KAYIT S3): `core/governance/` düz dosyaları indekse HİÇ girmiyordu — yalnız
# `governance/decisions` taranıyordu. Görünmeyenler arasında `infra-changelog.md` ve
# `infra-test-recipes.md` de vardı: yani infra-expert'in F0'da okumak ZORUNDA olduğu iki
# dosya, junction-körlüğünü kapatmak için var olan artefaktın kendisinde YOKTU
# (agent-teams-operating-model / tooling-plugins / tooling-radar / removed-controls da öyle).
# `rglob` ile "governance" eklemek decisions'ı ÇİFTLERDİ → düz tarama.
DUZ_ALANLAR = ["governance"]

# İndekse ALINMAYAN üretilmiş dosyalar (CORE-göreli posix yol).
# CORE-INDEX.md'nin kendisi üretilmiş bir indekstir: DEV_CORE kendi kendisinin projesi
# olduğunda (PROJ == CORE) indeks KENDİNİ listeler; projeden bakınca da ajanı core'un
# kendi indeksine yönlendirir = gürültü + özyineli referans.
HARIC = {"governance/CORE-INDEX.md"}

# KOD İŞARETÇİLERİ (Q331, 2026-09-18) — doküman DEĞİL, AYRI bölüm + AYRI satır öneki.
# Ölçüldü (aynı tüketici indeksi): `tests/`=0 · `run_battery`=0 · `mutasyon`=0 eşleşme ⇒
# mutasyon altyapısı (tek-komut batarya + fixture-içi mutasyon kipleri) kökten aramada
# görünmüyordu ve yeniden icat edildi. Kapsam bilinçli DAR: yalnız bu dizinlerin KENDİ
# `*.py`'si (DÜZ — alt dizin yok). `tests/fixtures/` altı TEK TEK listelenmez: her infra
# PR'ı fixture ekler; liste ya da sayı basılsaydı her PR, tüketen TÜM projelerde C-IDX-01'i
# "bayat"a düşürürdü. Bölüm başlığı bunun yerine SABİT metinle yönteme ve bulma komutuna
# yönlendirir (`ISARETCI_NOTU`).
ISARETCI_ALANLAR = ["tests"]
# Doküman satırı `- [`core/` ile başlar ve üç sayaç (`--check`, `--ci-check`, yazma) onu
# SAYAR; işaretçi satırı bu önekle BAŞLAMAMALI, yoksa doküman sayısı sessizce şişer.
ISARETCI_ONEK = "- (kod) "
ISARETCI_NOTU = """> **Bu bolum dokuman DEGILDIR — kod isaretcisidir.** Yalniz `core/tests/*.py` (duz; alt
> dizin yok) listelenir; ozet = modul docstring'inin ILK satiri.
> **Mutasyon yontemi** (fixture-ici `--mutasyon-<kip>`, sandbox, capa `count != 1` ise
> `[DOGRULANAMADI]` + exit 2): `core/playbook/howto-infra-fix-proseduru.md` §D2.
> **Fixture korpuslari:** `core/tests/fixtures/<ad>/run.py` — burada TEK TEK LISTELENMEZ
> (her infra PR'i fixture ekler; liste basilsaydi indeks her PR'da bayatlardi). Bul:
> `find -L core/tests/fixtures -name run.py` · mutasyon kipli olanlar:
> `rg -l -g run.py -- --mutasyon core/tests/fixtures` · taban + tum kipler tek komut:
> `python core/tests/run_battery.py <fixture-adi>`."""

BASLIK = """<!-- URETILMIS DOSYA — elle duzenleme. Uretici: core/scripts/build_core_index.py
     Tazelik gate'i: core/scripts/validators/check_core_index_fresh.py -->

# CORE-INDEX — metodoloji dokumanlarinin aranabilir dizini

> **Neden var:** `core/` bir junction'dir; `Grep` ve `Glob` junction'i TAKIP ETMEZ
> (gitignore'dan bagimsiz — olculdu). Kokten arama core'u GORMEZ ve sifir sonuc
> "boyle bir kural yok" diye okunur. Bu dosya GERCEK bir dosyadir: kokten aranir,
> bulunur ve dogru `core/...` yolunu verir. `Read("core/...")` calisir.
>
> **Arama receti (D29):** `Grep(path="core")` · `Glob(path="core/playbook", "*.md")`
> · `rg -L --no-ignore <p>` · `find -L core`. Kokten path'siz arama = sessiz sifir.
"""


def _ozet(p: Path) -> str:
    """Frontmatter `purpose:` → yoksa ilk H1 → yoksa ''."""
    try:
        metin = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = re.search(r"^purpose:\s*(.+)$", metin, re.MULTILINE)
    if m:
        return m.group(1).strip().strip('"')
    m = re.search(r"^#\s+(.+)$", metin, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _siralama_anahtari(f: Path) -> str:
    """Q214 (2026-09-02) — sıralama anahtarı PLATFORMDAN BAĞIMSIZ olmalı.

    KUSUR: burada eskiden anahtarsız `sorted(f for f in ham ...)` vardı, yani `Path`
    nesneleri KENDİ `__lt__`'leriyle kıyaslanıyordu. O kıyas platformun flavour'ına
    bağlıdır: `WindowsPath` parçaları `str.lower()` ile katlar, `PosixPath` katlamaz
    (Py 3.11 `_cparts`; Py 3.12+ `_str_normcase` — orada ayırıcı karakteri de kıyasa
    girer). Sonuç: AYNI doküman ağacı Windows'ta ve Linux'ta FARKLI sıralanır.
    Ölçüldü (2026-09-02, bu repo, 89 doküman): tek fark `playbook/README.md` —
    Linux'ta bölümün başında, Windows'ta `r`'lerin arasında; diff **2 satır**.
    Bu, C-IDX-01'i platforma çeviriyordu: Windows'ta üretilip commit'lenen indeks
    Linux CI'da `--ci-check` → `[FAIL] CORE-INDEX BAYAT` (template_project PR #15,
    2026-08-30); aynı komut aynı core-commit'te Windows'ta `[OK]`.

    ANAHTAR SEÇİMİ (ölçülmüş, alternatifler REDDEDİLDİ — geri çevirmeden önce oku):
    • `rel.as_posix()` (SEÇİLEN): yalnız kod-noktası sırasına dayanır; ne büyük/küçük
      harf tablolarına ne de yol ayırıcısına bağlıdır. Ayrıca **basılan metnin ta
      kendisidir** (satırlar `core/<rel>` yazar) ⇒ sıra artefaktın üzerinden gözle
      doğrulanabilir.
    • `rel.parts` (REDDEDİLDİ): bugünkü ağaçta as_posix ile AYNI çıktıyı verir
      (ölçüldü: 89/89 özdeş), ama `alt/` dizini ile `alt-ek.md` gibi ÖN-EK çakışması
      olduğunda ayrışır; iki anahtarı ayrı tutmak yerine tek ve basit olanı seçtik.
    • `rel.as_posix().lower()` (REDDEDİLDİ): bugünkü Windows çıktısını birebir korur
      (ölçüldü: 89/89 özdeş ⇒ mevcut indeksler hiç değişmezdi, cazip), AMA sırayı
      Unicode büyük/küçük-harf tablolarına bağlar — yani düzeltmeye çalıştığımız
      sınıfın (ortama bağlı kıyas) daha sessiz bir biçimini geri getirir; üstelik
      tek başına TOTAL değildir (yalnız harf-durumuyla ayrışan iki ad berabere kalır
      ve sıra `glob` sırasına düşer).
    """
    return f.relative_to(CORE).as_posix()


def _dosyalar(alan: str, ozyineli: bool, desen: str = "*.md") -> list[Path]:
    d = CORE / alan
    if not d.is_dir():
        return []
    ham = d.rglob(desen) if ozyineli else d.glob(desen)
    return sorted((f for f in ham if _siralama_anahtari(f) not in HARIC),
                  key=_siralama_anahtari)


def _kod_ozeti(p: Path) -> str:
    """Modül docstring'inin İLK dolu satırı (AST — regex değil); okunamazsa ''.

    ⛔ Sessiz atlama YOK: çağıran satırı özet boş olsa da BASAR (dosya indekste
    görünür kalır). `str.splitlines()` KULLANILMAZ — Unicode satır sınırlarında da
    böler; yalnız `\\n` ayırıcıdır.

    PLATFORM DETERMİNİZMİ (tüketici CI'ı Windows'ta üretilen indeksi Linux'ta aynı
    core-commit'te yeniden üretip kıyaslar — `_ci_check`): açık `utf-8` (locale'e
    bağlı değil) · `read_text` evrensel satır sonu çevirir ⇒ autocrlf'li Windows
    checkout'ta da özet `\\r` taşımaz · `clean=True` girintiyi normalize eder ·
    kenar boşluğu kırpılır.
    ÇÖKMEZLİK: bu üretici tüketicinin session/CI zincirindedir; tek bir bozuk
    `tests/*.py` (sözdizimi · null bayt · UTF-8 olmayan bayt · okunamaz) üretimi
    düşürmemeli — çökme C-IDX-01 kırmızısı olurdu. Bu yüzden istisna GENİŞ yakalanır.
    """
    try:
        kaynak = p.read_text(encoding="utf-8").lstrip("﻿")
        doc = ast.get_docstring(ast.parse(kaynak, filename=str(p)), clean=True)
    except Exception:  # noqa: BLE001 — bilinçli: yukarıdaki ÇÖKMEZLİK notu
        return ""
    for satir in (doc or "").split("\n"):
        if satir.strip():
            return satir.strip()
    return ""


def uret() -> str:
    satirlar = [BASLIK]
    toplam = 0
    for alan, ozyineli in ([(a, True) for a in ALANLAR] + [(a, False) for a in DUZ_ALANLAR]):
        dosyalar = _dosyalar(alan, ozyineli)
        if not dosyalar:
            continue
        satirlar.append(f"\n## `core/{alan}/` ({len(dosyalar)} dosya)\n")
        for f in dosyalar:
            rel = f.relative_to(CORE).as_posix()
            ozet = _ozet(f)
            satirlar.append(f"- [`core/{rel}`](../core/{rel})" + (f" — {ozet}" if ozet else ""))
            toplam += 1
    isaretci = 0
    for alan in ISARETCI_ALANLAR:
        dosyalar = _dosyalar(alan, False, "*.py")
        if not dosyalar:
            continue
        satirlar.append(f"\n## Kod isaretcileri — `core/{alan}/` ({len(dosyalar)} dosya; "
                        f"KOD, dokuman degil)\n")
        satirlar.append(ISARETCI_NOTU + "\n")
        for f in dosyalar:
            rel = f.relative_to(CORE).as_posix()
            ozet = _kod_ozeti(f)
            satirlar.append(f"{ISARETCI_ONEK}[`core/{rel}`](../core/{rel})"
                            + (f" — {ozet}" if ozet else ""))
            isaretci += 1
    satirlar.append(f"\n---\n\n**Toplam {toplam} dokuman · {isaretci} kod isaretcisi.** "
                    f"Bu dosya uretilmistir; "
                    f"icerik degistiginde `build_core_index.py` yeniden kosulur.\n")
    return "\n".join(satirlar)


def _damga() -> str:
    """Üretim tarihi + core-commit satırı (T0.10, 2026-07-31): okuyan bayatlığı GÖREBİLSİN.
    --check karşılaştırmasında YOK SAYILIR (yoksa her koşum timestamp farkıyla FAIL olurdu)."""
    import subprocess
    from datetime import datetime, timezone
    try:
        sha = subprocess.run(["git", "-C", str(CORE), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip() or "?"
    except Exception:
        sha = "?"
    z = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    return f"<!-- uretim: {z} · core-commit: {sha} — bilgi satiri; tazelik kiyasinda yok sayilir -->\n"


_DAMGA_RE = re.compile(r"^<!-- uretim: .*?-->\n", re.MULTILINE)
_DAMGA_SHA_RE = re.compile(r"core-commit:\s*(\S+)")


def _kayitli_core_commit() -> str | None:
    """Commit'li indeksin damgasındaki `core-commit` kısa-SHA'sı (yoksa None)."""
    if not HEDEF.is_file():
        return None
    ilk = HEDEF.read_text(encoding="utf-8", errors="replace")[:400]
    m = _DAMGA_SHA_RE.search(ilk)
    sha = m.group(1) if m else None
    return sha if sha and sha != "?" else None


def _simdiki_core_commit() -> str | None:
    import subprocess
    try:
        r = subprocess.run(["git", "-C", str(CORE), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or None if r.returncode == 0 else None
    except Exception:
        return None


def _ci_check() -> int:
    """CI ÖN-KONTROLÜ (DG-03, 2026-08-28) — TAUTOLOJİYİ kırar.

    KUSUR: `.github/workflows/project-guard.yml` `build_core_index.py`'yi (REGENERATE)
    `run_all_validators` içindeki `check_core_index_fresh` (--check) adımından ÖNCE
    koşuyordu ⇒ kontrol DAİMA kendi az önce ürettiği dosyaya bakıyordu: **her zaman
    yeşil**, C-IDX-01 CI'da hiçbir şey ölçmüyordu (kendi kendini doğrulama).

    ⛔ SIRAYI DÜZ ÇEVİRMEK YETMEZ — regenerate adımının GEREKÇESİ gerçek (workflow'da
    yazılı): CI'daki `core/` bir FRESH CLONE'dur (`--depth 1`, `main`), commit'li indeks
    ise geliştiricinin junction'ındaki core'a göre üretilmiştir. İkisi farklı commit'te
    ise `--check` GERÇEK bir bayatlık değil, **doküman-kümesi farkı** raporlar (FP).

    ÇÖZÜM: soruyu ancak CEVAPLANABİLİR olduğunda sor. Damgadaki `core-commit` ile
    fiilen klonlanmış core HEAD'i AYNI ise tazelik sorusu anlamlıdır → gerçek kıyas.
    Farklı ise ölçüm YAPILAMAZ → `SKIPPED measured=false` (sahte-yeşil DEĞİL, dürüst
    "ölçemedim"). Böylece yeşil ERİŞİLEBİLİR kalır ama BEDAVA değildir.
    """
    sys.path.insert(0, str(CORE / "scripts" / "validators"))
    from _gate_status import gate_status  # type: ignore  # noqa: E402

    if not HEDEF.is_file():
        print(f"  [FAIL] {HEDEF} YOK — üret: python core/scripts/build_core_index.py")
        gate_status("build_core_index", "FINDING", True, "indeks-dosyasi-yok")
        return 1

    kayitli, simdiki = _kayitli_core_commit(), _simdiki_core_commit()
    if kayitli is None or simdiki is None or kayitli != simdiki:
        print(f"  [ÖLÇÜLEMEDİ] CORE-INDEX tazeliği CI'da doğrulanamaz: damgadaki "
              f"core-commit={kayitli or '?'} ↔ klonlanan core HEAD={simdiki or '?'}.")
        print("               Farklı core commit'i = doküman-kümesi farkı; `--check` "
              "burada BAYATLIK değil FARK ölçerdi (yanlış-pozitif).")
        print("               ⚠ Bu 'temiz' DEĞİLDİR — C-IDX-01 bu koşumda ÖLÇÜLMEDİ.")
        gate_status("build_core_index", "SKIPPED", False, "core-commit-uyusmuyor")
        return 0

    yeni = uret()
    mevcut = _DAMGA_RE.sub("", HEDEF.read_text(encoding="utf-8", errors="replace"), count=1)
    if mevcut.replace("\r\n", "\n") != yeni.replace("\r\n", "\n"):
        print(f"  [FAIL] CORE-INDEX BAYAT (core-commit={kayitli} ile ÖLÇÜLDÜ) — "
              f"core dokümanları değişmiş, indeks yeniden üretilmemiş.")
        print("         Onarım: python core/scripts/build_core_index.py && git add governance/CORE-INDEX.md")
        gate_status("build_core_index", "FINDING", True, "indeks-bayat")
        return 1
    print(f"  [OK] CORE-INDEX güncel ve ÖLÇÜLDÜ (core-commit={kayitli}, "
          f"{yeni.count(chr(10) + '- [`core/')} doküman)")
    gate_status("build_core_index", "OK", True, "guncel")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="yazma; mevcutla karşılaştır")
    ap.add_argument("--ci-check", action="store_true",
                    help="CI ön-kontrolü: YALNIZ damgadaki core-commit klonlanan core "
                         "HEAD'iyle aynıysa ölçer, değilse SKIPPED measured=false (DG-03)")
    a = ap.parse_args()

    if a.ci_check:
        return _ci_check()

    yeni = uret()
    if a.check:
        if not HEDEF.is_file():
            print(f"  [FAIL] {HEDEF.relative_to(PROJ)} YOK — üret: python core/scripts/build_core_index.py")
            return 1
        mevcut = _DAMGA_RE.sub("", HEDEF.read_text(encoding="utf-8", errors="replace"), count=1)
        if mevcut.replace("\r\n", "\n") != yeni.replace("\r\n", "\n"):
            print(f"  [FAIL] {HEDEF.relative_to(PROJ)} BAYAT — core dokümanları değişmiş.")
            print("         Bayat indeks = ajana YANLIŞ yol verir (sessiz hata).")
            print("         Onarım: python core/scripts/build_core_index.py")
            return 1
        print(f"  [OK] CORE-INDEX güncel ({yeni.count(chr(10) + '- [`core/')} doküman)")
        return 0

    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    HEDEF.write_text(_damga() + yeni, encoding="utf-8", newline="\n")
    print(f"[ OK ] yazıldı: {HEDEF}  ({yeni.count(chr(10) + '- [`core/')} doküman)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
