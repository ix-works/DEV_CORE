#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATOR — auto-memory bütçesi + indeks bütünlüğü (C-MEM-01).

NEDEN (2026-07-10 memory/recall denetimi):

1) **SESSİZ KESİLME.** Claude Code `MEMORY.md`'nin yalnız **ilk 200 satırını VEYA ilk
   25 KB'ını** (hangisi önce gelirse) oturum başında yükler; gerisi **yüklenmez, uyarı
   verilmez** (code.claude.com/docs/en/memory). Türkçe metinde bağlayıcı kısıt satır
   değil **BAYT**tır (çoğu harf 2 bayt). Denetimde MEMORY.md 20.192/25.600 bayt = %79
   doluydu ve kimse ölçmüyordu. Tavan aşılınca dosyanın SONU düşer — yani en alttaki
   davranış kuralları sessizce hafızadan silinir. Tam da "AI hatırlamıyor" şikâyeti.

2) **ÖLÜ İNDEKS LİNKİ.** `MEMORY.md` var olmayan bir dosyayı gösteriyordu; o hatıranın
   gövdesi erişilemez hâldeydi (yalnız tek satırlık özeti kalmış).

3) **ERİŞİLEMEZ HATIRA.** İndeksten (doğrudan ya da tek hop `[[wiki-link]]` ile)
   ulaşılamayan memory dosyası, model için YOK hükmündedir.

ENFORCES: C-MEM-01
Kapsam:
  * proje auto-memory dizini  → bütçe + bütünlük  (bulunamazsa sessizce atlanır)
  * `core/claude/memory-seed/` → bütünlük (seed'in bütçesi yok; yeni projeye tohumlanır)

Eşikler: bayt/satır doluluğu %85 → WARNING, %95 → FAIL. Ölü link / erişilemez dosya /
frontmatter şema ihlali → FAIL.
Onarım: MEMORY.md'yi sıkıştır (gövdeyi konu dosyasına taşı, indekste tek satır bırak).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Resmî limitler — code.claude.com/docs/en/memory ("first 200 lines or 25KB")
BAYT_TAVAN = 25 * 1024
SATIR_TAVAN = 200
UYARI_ORAN, FAIL_ORAN = 0.85, 0.95

LINK_RE = re.compile(r"\]\(([^)]+\.md)\)")
WIKI_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _memory_dizini(proj: Path) -> tuple[Path | None, str]:
    """Auto-memory dizini: `~/.claude/projects/<slug>/memory/`.

    Slug DETERMİNİSTİK türetilir: proje yolundaki alfanümerik olmayan her karakter '-'.
    (`C:\\IX\\Proje` → `C--IX-Proje`.)

    ⚠ Önceki sürüm "adı içeren tek dizin" sezgisiyle arıyordu; donmuş eski dünyanın
    aynı-adlı dizini de eşleşince İKİ aday çıkıyor ve validator **sessizce atlıyordu**
    — yani asıl bütçe kontrolü hiç koşmadan "[OK]" basıyordu. Bulunamadı ≠ sorun yok.
    """
    ozel = os.environ.get("CLAUDE_AUTO_MEMORY_DIR")
    if ozel:
        p = Path(os.path.expanduser(ozel))
        return (p if p.is_dir() else None), str(p)
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(proj))
    p = Path(os.path.expanduser("~")) / ".claude" / "projects" / slug / "memory"
    return (p if p.is_dir() else None), str(p)


def _butce(idx: Path, hatalar: list[str], uyarilar: list[str]) -> None:
    ham = idx.read_bytes()
    satir = len(ham.decode("utf-8", errors="replace").splitlines())
    for ad, deger, tavan in (("bayt", len(ham), BAYT_TAVAN), ("satır", satir, SATIR_TAVAN)):
        oran = deger / tavan
        mesaj = (f"MEMORY.md {ad} doluluğu %{oran*100:.0f} ({deger}/{tavan}). "
                 f"Tavan aşılınca dosyanın SONU sessizce yüklenmez.")
        if oran >= FAIL_ORAN:
            hatalar.append("[FAIL] " + mesaj)
        elif oran >= UYARI_ORAN:
            uyarilar.append("[WARN] " + mesaj)


def _butunluk(dizin: Path, etiket: str, hatalar: list[str]) -> None:
    idx = dizin / "MEMORY.md"
    if not idx.is_file():
        hatalar.append(f"[FAIL] {etiket}: MEMORY.md yok")
        return
    metin = idx.read_text(encoding="utf-8", errors="replace")
    dosyalar = {p.name for p in dizin.glob("*.md") if p.name != "MEMORY.md"}

    # 1) ölü indeks linki
    linkli = set(LINK_RE.findall(metin))
    for l in sorted(linkli - dosyalar):
        hatalar.append(f"[FAIL] {etiket}: MEMORY.md ölü link → '{l}' diskte yok")

    # 2) erişilebilirlik: indeksten doğrudan VEYA tek-hop wiki-link ile
    erisilir = set(linkli) & dosyalar
    for ad in list(erisilir):
        govde = (dizin / ad).read_text(encoding="utf-8", errors="replace")
        for w in WIKI_RE.findall(govde):
            aday = w if w.endswith(".md") else w + ".md"
            if aday in dosyalar:
                erisilir.add(aday)
    for ad in sorted(dosyalar - erisilir):
        hatalar.append(f"[FAIL] {etiket}: '{ad}' indeksten erişilemez "
                       f"(MEMORY.md'ye satır ekle ya da bir hatıradan [[link]] ver)")

    # 3) frontmatter şeması
    for ad in sorted(dosyalar):
        bas = (dizin / ad).read_text(encoding="utf-8", errors="replace")[:600]
        if not bas.startswith("---"):
            hatalar.append(f"[FAIL] {etiket}: '{ad}' frontmatter yok")
            continue
        for alan in ("name:", "description:"):
            if alan not in bas:
                hatalar.append(f"[FAIL] {etiket}: '{ad}' frontmatter'ında '{alan}' yok")
        if not re.search(r"type:\s*(user|feedback|project|reference)", bas):
            hatalar.append(f"[FAIL] {etiket}: '{ad}' metadata.type yok/geçersiz")


def main() -> int:
    core = Path(__file__).resolve().parents[2]
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()

    hatalar: list[str] = []
    uyarilar: list[str] = []

    mem, beklenen_yol = _memory_dizini(proj)
    if mem is not None:
        if (mem / "MEMORY.md").is_file():
            _butce(mem / "MEMORY.md", hatalar, uyarilar)
        _butunluk(mem, "auto-memory", hatalar)
    else:
        # SESSİZ ATLAMA YASAK: nerede aradığımızı yaz, yoksa "[OK]" yalan olur.
        print(f"  [SKIP] auto-memory dizini yok: {beklenen_yol}")

    seed = core / "claude" / "memory-seed"
    if seed.is_dir():
        _butunluk(seed, "memory-seed", hatalar)

    for u in uyarilar:
        print("  " + u)
    for h in hatalar:
        print("  " + h)
    if hatalar:
        print(f"\n  Toplam {len(hatalar)} ihlal (C-MEM-01).")
        return 1
    print("  [OK] auto-memory bütçesi + indeks bütünlüğü")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
