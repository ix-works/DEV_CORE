#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_id_uniqueness — core dokümanlarındaki KİMLİK TANIMLARI tekil mi? (HARD)

NEDEN (ölçülmüş, tekrar eden sınıf): core'da elle verilen kimlikler aynı numarayla
İKİ KEZ tanımlandı ve her seferinde atıf belirsizleşti:
  · BE-58 (core #49) · FE-36 / FE-37 / BE-63 (Q270, 2026-09-13 — tüketici projede yanlış
    atıf üç dokümanda yaşadı, iki bağımsız kapı belirsizliği raporladı)
  · B51-B53 son anda önlendi; B-no dersi 2026-09-13'te yazıldı, 2026-09-26'da yine
    çakıştı: `infra-test-recipes.md` `## B18d` ve `## B18e` ikişer kez tanımlıydı.
Ders vardı, hatırlatma vardı; çakışma yine oldu ⇒ ADR 0019 beş şart (kullanıcı onayı
2026-10-03, HARD).

NE SAYAR — yalnız TANIM, atıf DEĞİL (aile tablosu `AILELER`; kapsam beyanı ondan türetilir):
  · B-no      : `governance/infra-test-recipes.md` başlıkları `#… B<n>[a-z]` (her düzey).
                `### B0-SEÇİM` gibi TİRELE BİTİŞİK alt-etiket ayrı kimlik DEĞİLDİR (B0'ın
                alt bölümüdür) → sayılmaz.
  · checklist : `playbook/checklists/*.md` tablo satırının İLK hücresi `<ÖNEK>-<n>[a-z]`
                (`**BE-58**` = `BE-58`). Tekillik TÜM checklist'ler arasında aranır
                (dosyalar arası çift de çifttir).
  · PATTERN   : `playbook/lessons-learned.md` başlıkları `PATTERN #<n>`.
  · ADR       : `governance/decisions/NNNN-*.md` dosya adının 4 haneli numarası.
Kod bloğu (``` / ~~~) içi taranmaz: örnek metindir, tanım değildir.

ÇIKIŞ: 0 çift yok · 1 en az bir kimlik birden çok kez tanımlı · 2 ÖLÇÜLEMEDİ (bir ailenin
kaynağı YOK ya da 0 tanım verdi — dedektör sessizce kör kalmasın; "0 tanım" ≠ "çift yok").

KÖK: `--kok <yol>` → env `IX_CORE_ROOT` → `Path(__file__).parents[2]` (CORE-03: core'un
KENDİ dokümanlarını ölçer; `project_root()`'a ÇEVRİLMEZ — çevrilirse proje kökünde boş
tarar). Kök enjeksiyonu fixture'ın sentetik ağaç kurabilmesi içindir (C-ENC-01 emsali).
"""
# ENFORCES: CORE-08  (ADR 0019 coverage binding)
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

# ── Aile tanımları ─────────────────────────────────────────────────────────────
# B-no: başlık metni kimlikle başlar; kimlikten sonra harf/rakam/TİRE gelmez
# (`B0-SEÇİM` alt-etiketi, `B18dx` başka bir şey).
_B_BASLIK = re.compile(r"^#{1,6}[ \t]+(B\d+[a-z]?)(?![\w-])")
_PATTERN_BASLIK = re.compile(r"^#{1,6}[ \t]+PATTERN[ \t]*#(\d+[a-z]?)(?![\w-])")
_CHECKLIST_ID = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+[a-z]?$")
_ADR_DOSYA = re.compile(r"^(\d{4})-.+\.md$")
_FENCE = re.compile(r"^[ \t]*(```|~~~)")


def core_kok(argv: list[str] | None = None) -> Path:
    """Taranacak CORE kökü — `--kok <yol>` → env `IX_CORE_ROOT` → `__file__` türevi."""
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    if "--kok" in argv:
        i = argv.index("--kok")
        if i + 1 < len(argv):
            return Path(argv[i + 1]).resolve()
    env = os.environ.get("IX_CORE_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


def _satirlar(p: Path):
    """(satır_no, satır) — kod bloğu İÇİ atlanır."""
    fence = False
    # `split("\n")` — `splitlines()` DEĞİL: o, U+2028/U+0085 gibi Unicode sınırlarında da
    # böler ve satır numaralarını kaydırır (bu evde ölçülmüş tuzak, JSONL vakası).
    metin = p.read_text(encoding="utf-8", errors="replace")
    for i, satir in enumerate(metin.split("\n"), 1):
        satir = satir.rstrip("\r")
        if _FENCE.match(satir):
            fence = not fence
            continue
        if not fence:
            yield i, satir


def _baslik_tara(desen: re.Pattern, onek: str):
    def tara(dosyalar: list[Path], kok: Path) -> list[tuple[str, str]]:
        out = []
        for p in dosyalar:
            rel = p.relative_to(kok).as_posix()
            for i, satir in _satirlar(p):
                m = desen.match(satir)
                if m:
                    out.append((onek + m.group(1), f"{rel}:{i}"))
        return out
    return tara


def _checklist_tara(dosyalar: list[Path], kok: Path) -> list[tuple[str, str]]:
    out = []
    for p in dosyalar:
        rel = p.relative_to(kok).as_posix()
        for i, satir in _satirlar(p):
            s = satir.strip()
            if not s.startswith("|"):
                continue
            ilk = s.strip("|").split("|", 1)[0].strip().strip("*`").strip()
            if _CHECKLIST_ID.match(ilk):
                out.append((ilk, f"{rel}:{i}"))
    return out


def _adr_tara(dosyalar: list[Path], kok: Path) -> list[tuple[str, str]]:
    out = []
    for p in dosyalar:
        m = _ADR_DOSYA.match(p.name)
        if m:
            out.append(("ADR " + m.group(1), p.relative_to(kok).as_posix()))
    return out


# (ad, dizin, glob, tanım biçimi açıklaması, tarayıcı) — KAPSAM BEYANI bu tablodan basılır.
AILELER = [
    ("B-no", "governance", "infra-test-recipes.md", "başlık `#… B<n>[a-z]` (alt-etiket `B0-X` hariç)",
     _baslik_tara(_B_BASLIK, "")),
    ("checklist", "playbook/checklists", "*.md", "tablo ilk hücresi `<ÖNEK>-<n>[a-z]` (dosyalar arası)",
     _checklist_tara),
    ("PATTERN", "playbook", "lessons-learned.md", "başlık `PATTERN #<n>`",
     _baslik_tara(_PATTERN_BASLIK, "PATTERN #")),
    ("ADR", "governance/decisions", "*.md", "dosya adı `NNNN-*.md`", _adr_tara),
]

BAKILMAYAN = ("metin içi atıflar · kod bloğu (```/~~~) içi · standards/** tablo kimlikleri "
              "(FR-/PC-/TC-…: şablon örnekleri meşru tekrar eder) · infra-changelog kayıt "
              "başlıkları (Q-no tanım değil kayıttır) · test/fixture vektör kimlikleri · "
              "proje repoları (governance/decisions dahil)")


def main(argv: list[str] | None = None) -> int:
    kok = core_kok(argv)
    print(f"check_id_uniqueness — kimlik tekilliği (HARD, CORE-08) · kök: {kok}")
    print("KAPSAM BEYANI:")
    olculemedi: list[str] = []
    tum: dict[str, list[str]] = {}
    for ad, dizin, glob, bicim, tara in AILELER:
        d = kok / dizin
        dosyalar = sorted(d.glob(glob)) if d.is_dir() else []
        dosyalar = [p for p in dosyalar if p.is_file()]
        tanimlar = tara(dosyalar, kok) if dosyalar else []
        tekil = {k for k, _ in tanimlar}
        print(f"  [{ad}] {dizin}/{glob} · {bicim} · {len(dosyalar)} dosya · "
              f"{len(tanimlar)} tanım · {len(tekil)} tekil kimlik")
        if not dosyalar or not tanimlar:
            neden = "kaynak dosya YOK" if not dosyalar else "0 tanım (biçim değişti mi?)"
            olculemedi.append(f"{ad}: {neden} — {dizin}/{glob}")
            continue
        for k, yer in tanimlar:
            tum.setdefault(f"{ad}\x00{k}", []).append(yer)
    print(f"  BAKILMAYAN: {BAKILMAYAN}")

    ciftler = {k: v for k, v in tum.items() if len(v) > 1}
    rc = 0
    if ciftler:
        print(f"[FAIL] {len(ciftler)} kimlik birden çok kez tanımlı (atıf belirsizleşir):")
        for k in sorted(ciftler):
            ad, kimlik = k.split("\x00", 1)
            print(f"  - [{ad}] {kimlik}: {' · '.join(ciftler[k])}")
        print("  Onarım: SONRAKİ tanıma ailenin bir sonraki BOŞ kimliğini ver; o tanıma "
              "yapılan atıfları (core + tüketici projeler) bağlamdan ayırıp güncelle.")
        rc = 1
    if olculemedi:
        print(f"[ÖLÇÜLEMEDİ] {len(olculemedi)} aile ölçülemedi — '0 tanım' ≠ 'çift yok':")
        for s in olculemedi:
            print(f"  - {s}")
        rc = rc or 2
    if rc == 0:
        print(f"[OK] {len(tum)} kimlik tanımı ({len(AILELER)} aile) — çift yok")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
