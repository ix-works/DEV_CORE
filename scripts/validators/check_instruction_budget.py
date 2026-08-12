#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATOR — talimat-dosyası bütçesi + blok-tekrarı (C-BUD-01, warn-first).

# ENFORCES: C-BUD-01

NEDEN (2026-08-12 talimat-hijyeni ölçümü):
  Her oturum context'e yüklenen talimat dosyaları SESSİZCE şişer — kimse dosyayı bütün
  olarak görmez, ayrı oturumların eklemeleri üst üste biner. Ölçülen vaka: bir rules
  dosyasında %55 blok-tekrarı (aynı bölüm 3 kopya, biri sapmış); çekirdek loader resmî
  <200-satır hedefinin 2 katı. Şişkin talimat = düşük uyum (resmî: "bloated CLAUDE.md
  causes Claude to ignore your actual instructions").

NE ÖLÇER (kapsam: her oturum KOŞULSUZ yüklenenler):
  <proje>/CLAUDE.md · <core>/CLAUDE.core.md · <core>/claude/rules/*.md
  1) SATIR BÜTÇESİ: soyulmuş içerik (frontmatter + blok-HTML-yorum hariç — üst harness
     ≥2.1.211 semantiği) > 200 satır → WARN. Resmî referans: code.claude.com docs/memory.
  2) BLOK-TEKRARI: ≥5 ardışık dolu satırlık bir blok dosya içinde 2+ kez → WARN (satır no'larıyla).
  3) TOPLAM YÜK: bilgi satırı (trend radar turunda okunur).

GATE DEĞİL: varsayılan çıkış DAİMA 0 (warn-first — emsal: check_list_view_grid doğuşu).
`--strict` → bulgu varsa exit 1. HARD terfisi tarihli karara bağlı (proje deferred-triggers,
≈2026-09-09 radar: taban temiz + nüks şartı). Eşik İCAT DEĞİL: 200 = resmî sayı.

Test: tests/fixtures/instruction_budget/run.py (P: temiz sentetik → 0 bulgu · N: şişkin+tekrarlı
sentetik → WARN + --strict exit 1). `--root` yalnız fixture içindir.
"""
from __future__ import annotations

import argparse
import os

import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

SATIR_TAVAN = 200          # resmî hedef (code.claude.com/docs/en/memory) — icat değil
BLOK_BOYU = 5              # ≥5 ardışık dolu satır = anlamlı blok (tek-satır gürültüsü elenir)

# TEK-KAYNAK (2026-08-12, infra-pilot bulgusu): soyma semantiği check_memory_index'teki
# `_yukleme_govdesi`'nden import edilir — aynı harness davranışının İKİ ayrı uygulaması
# sessizce ayrışır (claude_paths/S4 sınıfı). O uygulama blok-seviyeli + kod-fence-duyarlı +
# kapanmamış-yorumda fail-safe'tir; buradaki eski regex satır-içi yorumu da siliyordu (yanlış).
from check_memory_index import _yukleme_govdesi  # noqa: E402


def _soy(metin: str) -> list[str]:
    """Üst-harness yükleme semantiği: frontmatter + blok-HTML-yorumları bütçeye SAYILMAZ."""
    return _yukleme_govdesi(metin).splitlines()


def _blok_tekrarlari(satirlar: list[str]) -> list[tuple[int, int]]:
    """(ilk-görüldüğü-satır, tekrar-satırı) çiftleri — ≥BLOK_BOYU ardışık dolu satır."""
    gorulen: dict[tuple[str, ...], int] = {}
    bulgular = []
    i = 0
    while i <= len(satirlar) - BLOK_BOYU:
        pencere = tuple(s.strip() for s in satirlar[i:i + BLOK_BOYU])
        if all(pencere):
            if pencere in gorulen and (not bulgular or i >= bulgular[-1][1] + BLOK_BOYU):
                bulgular.append((gorulen[pencere], i + 1))
                i += BLOK_BOYU          # aynı kümenin ardışık pencerelerini tek bulgu say
                continue
            gorulen.setdefault(pencere, i + 1)
        i += 1
    return bulgular


def _hedefler(kok: Path) -> list[Path]:
    adaylar = [kok / "CLAUDE.md", kok / "CLAUDE.core.md", kok / "core" / "CLAUDE.core.md"]
    for rd in (kok / "claude" / "rules", kok / "core" / "claude" / "rules"):
        if rd.is_dir():
            adaylar += sorted(rd.glob("*.md"))
    gor, out = set(), []
    for a in adaylar:
        if a.is_file() and a.resolve() not in gor:
            gor.add(a.resolve())
            out.append(a)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Talimat-dosyası bütçesi (C-BUD-01, warn-first)")
    ap.add_argument("--strict", action="store_true", help="bulgu varsa exit 1")
    ap.add_argument("--root", default=None, help="yalnız fixture testi için kök override")
    a = ap.parse_args()

    kok = Path(a.root) if a.root else Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    hedefler = _hedefler(kok)
    if not hedefler:
        print("[SKIP] talimat dosyası bulunamadı (kök doğru mu?)")
        return 0

    bulgu, toplam_bayt = 0, 0
    for f in hedefler:
        metin = f.read_text(encoding="utf-8", errors="replace")
        satirlar = _soy(metin)
        n = len(satirlar)
        toplam_bayt += len(metin.encode("utf-8"))
        rel = f.as_posix().replace(kok.as_posix() + "/", "")
        if n > SATIR_TAVAN:
            print(f"[WARN] {rel}: {n} soyulmuş-satır > {SATIR_TAVAN} (resmî hedef) — böl/incelt")
            bulgu += 1
        for ilk, tekrar in _blok_tekrarlari(satirlar):
            print(f"[WARN] {rel}: satır {tekrar} civarı ≥{BLOK_BOYU}-satırlık blok, satır {ilk}'in "
                  f"TEKRARI — birleşim-koruyan dedup gerek (howto-talimat-dosyasi-bakimi)")
            bulgu += 1
    print(f"[BİLGİ] oturum-başı talimat yükü: {len(hedefler)} dosya · {toplam_bayt} bayt "
          f"(~{toplam_bayt // 4000}k token) · bulgu: {bulgu}")
    if bulgu:
        print("  (warn-first: bloklamaz; HARD terfisi tarihli karara bağlı — deferred-triggers)")
        if a.strict:
            return 1
    else:
        print("[OK] talimat-dosyası bütçesi: tavan aşımı ve blok-tekrarı yok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
