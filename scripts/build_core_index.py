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
ALANLAR = ["playbook", "standards", "profiles", "governance/decisions"]

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


def uret() -> str:
    satirlar = [BASLIK]
    toplam = 0
    for alan in ALANLAR:
        d = CORE / alan
        if not d.is_dir():
            continue
        dosyalar = sorted(d.rglob("*.md"))
        if not dosyalar:
            continue
        satirlar.append(f"\n## `core/{alan}/` ({len(dosyalar)} dosya)\n")
        for f in dosyalar:
            rel = f.relative_to(CORE).as_posix()
            ozet = _ozet(f)
            satirlar.append(f"- [`core/{rel}`](../core/{rel})" + (f" — {ozet}" if ozet else ""))
            toplam += 1
    satirlar.append(f"\n---\n\n**Toplam {toplam} dokuman.** Bu dosya uretilmistir; "
                    f"icerik degistiginde `build_core_index.py` yeniden kosulur.\n")
    return "\n".join(satirlar)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="yazma; mevcutla karşılaştır")
    a = ap.parse_args()

    yeni = uret()
    if a.check:
        if not HEDEF.is_file():
            print(f"  [FAIL] {HEDEF.relative_to(PROJ)} YOK — üret: python core/scripts/build_core_index.py")
            return 1
        mevcut = HEDEF.read_text(encoding="utf-8", errors="replace")
        if mevcut.replace("\r\n", "\n") != yeni.replace("\r\n", "\n"):
            print(f"  [FAIL] {HEDEF.relative_to(PROJ)} BAYAT — core dokümanları değişmiş.")
            print("         Bayat indeks = ajana YANLIŞ yol verir (sessiz hata).")
            print("         Onarım: python core/scripts/build_core_index.py")
            return 1
        print(f"  [OK] CORE-INDEX güncel ({yeni.count(chr(10) + '- [`core/')} doküman)")
        return 0

    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    HEDEF.write_text(yeni, encoding="utf-8", newline="\n")
    print(f"[ OK ] yazıldı: {HEDEF}  ({yeni.count(chr(10) + '- [`core/')} doküman)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
