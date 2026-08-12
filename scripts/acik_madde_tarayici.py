#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Açık-madde tarayıcı — iş-takip yüzeylerinde "açık" görünen satırları listeler (RAPOR-ONLY).

NEDEN: 2026-08-12 denetiminde `governance/` altında **22 dosya** açık iş taşıyor görünüyordu ve
**hepsinin işi bitmişti** — biri 52 işaretsiz onay kutusu olan, aylar önce tamamlanmış bir geçiş
planıydı. Kapanış konuşmada olmuş, artefaktta olmamıştı (CLAUDE.core §1.1 "kapanış disiplini").
Bu araç o birikimi **görünür** kılar; karar vermez, bloklamaz, hiçbir dosyayı değiştirmez.

KULLANIM (içerik-sağlık radarı turu, madde 9):
    python core/scripts/acik_madde_tarayici.py                 # özet
    python core/scripts/acik_madde_tarayici.py --detay         # satır satır
    python core/scripts/acik_madde_tarayici.py --cikti r.txt   # dosyaya

ÇIKIŞ KODU DAİMA 0 — bu bir gate DEĞİLDİR (gate-moratoryumu ADR 0019).

⚠ SINIR (bilerek): metin-deseni tarar, anlam çıkarmaz. "AÇIK" kelimesi düz yazıda da geçer ⇒
çıktı **aday listesidir**, bulgu listesi değil. Her aday kanıtla doğrulanmadan kapatılmaz.
Aynı satırda kapanış işareti (✅ · ~~üstü çizili~~ · KAPANDI · TAMAM · ÇÖZÜLDÜ · İPTAL) varsa
satır aday sayılmaz — "kapatılmış ama işareti duran" gürültüsü böyle elenir.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

ACIK = re.compile(r"⬜|🔴|⏳|⛔ AÇIK|AÇIK KALEM|BEKLİYOR|BEKLIYOR|- \[ \]|\bAÇIK\b|TODO|KARAR BEKL")
KAPALI = re.compile(r"✅|~~|KAPANDI|KAPATILDI|TAMAM\b|TAMAMLANDI|ÇÖZÜLDÜ|COZULDU|İPTAL|ARŞİV|ARSIV")

# Arşiv KAPSAM DIŞI: oraya taşınmış olması zaten "kapandı" demektir (kural D1).
ATLA = ("archive", "node_modules", "dist", ".tmp", "ref_docs")


def _proje_koku() -> Path:
    """CORE-01: proje kökü env'den ya da cwd'den — `__file__` türevinden ASLA (junction tuzağı)."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _hedefler(proj: Path) -> list[Path]:
    d: list[Path] = []
    gov = proj / "governance"
    if gov.is_dir():
        d += sorted(gov.glob("*.md"))
    for desen in ("*/*/SESSION_NOTES.md", "*/*/docs/*RESUME*.md",
                  "*/*/docs/*PLAN*.md", "*/*/SPRINT_PLAN.md"):
        for kok in ("SOURCE_CODES", "ERP"):          # K12 öncesi ad da desteklenir
            if (proj / kok).is_dir():
                d += sorted((proj / kok).glob(desen))
    return [p for p in d if not any(s in p.parts for s in ATLA)]


def tara(proj: Path) -> list[tuple[Path, list[tuple[int, str]]]]:
    sonuc = []
    for f in _hedefler(proj):
        try:
            satirlar = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        bulunan = [(i, re.sub(r"\s+", " ", s.strip())[:150])
                   for i, s in enumerate(satirlar, 1)
                   if ACIK.search(s) and not KAPALI.search(s)]
        if bulunan:
            sonuc.append((f, bulunan))
    return sonuc


def main() -> int:
    ap = argparse.ArgumentParser(description="Açık-madde tarayıcı (rapor-only; gate DEĞİL)")
    ap.add_argument("--detay", action="store_true", help="satır satır dök")
    ap.add_argument("--cikti", metavar="DOSYA", help="raporu dosyaya yaz")
    a = ap.parse_args()

    proj = _proje_koku()
    sonuc = tara(proj)
    if not sonuc:
        print("[OK] açık-madde adayı yok (taranan yüzeylerde).")
        return 0

    satirlar = [f"Açık-madde ADAYLARI — {len(sonuc)} dosya "
                f"({sum(len(b) for _, b in sonuc)} satır) · proje: {proj}",
                "⚠ Bunlar aday; kanıtla doğrulanmadan kapatılmaz. Arşiv klasörleri kapsam dışı.", ""]
    for f, bulunan in sorted(sonuc, key=lambda x: -len(x[1])):
        satirlar.append(f"{len(bulunan):>4} aday  {f.relative_to(proj).as_posix()}")
        if a.detay:
            satirlar += [f"        {i:>5}  {s}" for i, s in bulunan[:25]]
            if len(bulunan) > 25:
                satirlar.append(f"        ... +{len(bulunan) - 25} satır daha")

    rapor = "\n".join(satirlar)
    if a.cikti:
        Path(a.cikti).write_text(rapor + "\n", encoding="utf-8")
        print(f"rapor yazıldı: {a.cikti} ({len(sonuc)} dosya)")
    else:
        print(rapor)
    return 0  # DAİMA 0 — gate değil


if __name__ == "__main__":
    raise SystemExit(main())
