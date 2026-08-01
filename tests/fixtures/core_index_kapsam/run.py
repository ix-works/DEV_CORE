# -*- coding: utf-8 -*-
"""core_index_kapsam — CORE-INDEX hangi core dokümanlarını GÖRÜYOR (KAYIT S3).

KÖK: `build_core_index.ALANLAR` yalnız `governance/decisions`'ı taşıyordu; `core/governance/`
DÜZ dosyaları indekse HİÇ girmiyordu. Görünmeyenlerin arasında `infra-changelog.md` ve
`infra-test-recipes.md` de vardı — yani infra-expert'in F0'da okumak ZORUNDA olduğu iki
dosya, tam da junction-körlüğünü kapatmak için var olan artefaktın kendisinde yoktu
(D29: kökten arama core'u görmez; sıfır sonuç "böyle bir kural yok" diye okunur).

FP ÇAPASI (bu fixture'ın omurgası): indeks ŞİŞMEMELİ. `governance`'ı `rglob` ile eklemek
`decisions/`i ÇİFTLERDİ; `CORE-INDEX.md`'nin kendisi de üretilmiş bir dosyadır ve indekse
girerse ajanı kendi indeksine yönlendirir. İkisi de burada ölçülür — "eksik dosya kalmasın"
kadar "fazla dosya girmesin" de test altındadır.

Koşum:  python tests/fixtures/core_index_kapsam/run.py
MUTASYON: DUZ_ALANLAR'ı boşalt → V1/V2 FAIL · HARIC'i boşalt → V4 FAIL ·
          DUZ_ALANLAR yerine ALANLAR'a "governance" ekle (rglob) → V3 FAIL.
"""
from __future__ import annotations

import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK / "scripts"))
import build_core_index as B  # noqa: E402

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


metin = B.uret()
satirlar = [s for s in metin.splitlines() if s.startswith("- [`core/")]
yollar = [s.split("`")[1] for s in satirlar]        # "core/<rel>"

# ── V1 — F0'ın ZORUNLU iki dosyası indekste ─────────────────────────────────────
F0 = ["core/governance/infra-changelog.md", "core/governance/infra-test-recipes.md"]
eksik = [y for y in F0 if y not in yollar]
kontrol("V1 F0 zorunlu dosyaları (infra-changelog + infra-test-recipes) indekste",
        not eksik, f"eksik={eksik}")

# ── V2 — diğer governance düz dokümanları da görünür ────────────────────────────
BEKLENEN = ["core/governance/agent-teams-operating-model.md",
            "core/governance/tooling-plugins.md",
            "core/governance/removed-controls.md"]
eksik2 = [y for y in BEKLENEN if y not in yollar]
kontrol("V2 governance düz dokümanları (operating-model/tooling-plugins/removed-controls)",
        not eksik2, f"eksik={eksik2}")

# ── V3 — FP ÇAPASI: hiçbir dosya İKİ KEZ listelenmiyor (rglob-çiftleme tuzağı) ──
tekrar = sorted({y for y in yollar if yollar.count(y) > 1})
kontrol("V3 FP ÇAPASI: mükerrer satır YOK (governance rglob decisions'ı çiftlemiyor)",
        not tekrar, f"mükerrer={tekrar}")

# ── V4 — FP ÇAPASI: üretilmiş CORE-INDEX.md kendini listelemiyor ────────────────
kontrol("V4 FP ÇAPASI: `governance/CORE-INDEX.md` indekste YOK (özyineli referans)",
        "core/governance/CORE-INDEX.md" not in yollar,
        f"bulunan={[y for y in yollar if 'CORE-INDEX' in y]}")

# ── V5 — FP ÇAPASI: kod dizinleri hâlâ DIŞARIDA (kapsam kaymadı) ───────────────
sizinti = [y for y in yollar
           if y.startswith(("core/scripts/", "core/mcp_servers/", "core/tests/",
                            "core/claude/", "core/intake/", "core/attic/"))]
kontrol("V5 FP ÇAPASI: scripts/mcp_servers/tests/claude indekse SIZMADI (kod ≠ doküman)",
        not sizinti, f"sızan={sizinti[:5]}")

# ── V6 — REGRESYON ÇAPASI: eski kapsam AYNEN duruyor (playbook/standards/decisions) ─
for alan, en_az in (("core/playbook/", 40), ("core/standards/", 8),
                    ("core/governance/decisions/", 20)):
    n = sum(1 for y in yollar if y.startswith(alan))
    kontrol(f"V6 eski kapsam korunuyor: {alan} ≥ {en_az} doküman", n >= en_az, f"bulunan={n}")

# ── V7 — 3. BAĞLAM (görev-dışı): --check karşılaştırması damgayı YOK SAYIYOR ────
#   `_damga()` her koşumda değişen bir zaman damgası basar; tazelik kıyası onu ayıklamazsa
#   `check_core_index_fresh` HER koşumda FAIL eder (gürültü → gate'e güven kaybı).
damgali = B._damga() + metin
kontrol("V7 3.BAĞLAM: damga --check kıyasında ayıklanıyor (her koşumda sahte-BAYAT yok)",
        B._DAMGA_RE.sub("", damgali, count=1) == metin,
        f"ayıklanan={B._DAMGA_RE.sub('', damgali, count=1)[:60]!r}")

# ── V8 — indeks GERÇEKTEN diskteki dosyaları gösteriyor (yol doğruluğu) ─────────
kirik = [y for y in yollar if not (KOK / y[len("core/"):]).is_file()][:5]
kontrol("V8 indeksteki her yol diskte GERÇEKTEN var (kırık yol = sessiz yanlış yönlendirme)",
        not kirik, f"kırık={kirik}")

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK  (indekslenen toplam: {len(yollar)} doküman)")
sys.exit(0 if gecen == len(SONUC) else 1)
