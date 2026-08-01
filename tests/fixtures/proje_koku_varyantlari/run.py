# -*- coding: utf-8 -*-
"""proje_koku_varyantlari — `__file__`-kökü dedektörünün YAZIM VARYANTLARI (KAYIT V5).

KÖK: `check_project_root_resolution` bir SINIFI (proje kökünü `__file__`'dan türetme,
ADR 0020) yasaklamak için var, ama yalnız BİR yazım biçimini görüyordu: `KÖK / "SOURCE_CODES"`
(Path bölme operatörü) ve `KÖK.rglob(...)`. Aynı hasarı veren dört yazım kaçıyordu:
    1. `KÖK.glob("*/*.cds")`                 → `rglob` yasak, `glob` serbest (keyfi ayrım)
    2. `KÖK.joinpath("SOURCE_CODES")`        → `/` operatörünün metot ikizi
    3. `f"{KÖK}/SOURCE_CODES"` · `str(KÖK) + "/.claude"`  → Path aritmetiği yok, hasar aynı
    4. `KÖK2 = KÖK.parent` → `KÖK2 / "SOURCE_CODES"`      → ara değişken kusuru bir adım
       öteye taşıyıp dedektörü kör ediyordu

NEDEN ÖNEMLİ: bu gate'in DOĞUŞ sebebi (2026-07-09, d2d326d) tam bu sınıfın canlı hasarıdır —
`check_method_param_type_c` junction'da `DEV_CORE/SOURCE_CODES`e bakıyor, dizin YOK, 0 dosya
tarıyor ve bilerek konan ihlale `[OK] ihlal yok` diyordu. Yani kaçış, gate'in kendisini
sessizce boşaltır. Aynı tuzağa 3 kez düşülmüştü.

⚠ DURUM: LATENT. Canlı core'da (193 script) bu dört varyantı kullanan GERÇEK bir satır
ÖLÇÜLDÜ ve BULUNAMADI (`.glob` 0, `.joinpath` 0; 8 f-string + 6 `+` var ama hepsi meşru:
`print(f"core: {CORE_ROOT}")`, `str(X) + os.pathsep`). Fix bugünkü bir ihlali düzeltmez,
yarınki yazımı yakalar — bu yüzden fixture'ın kendisi TEK kanıttır.

⚠ FP ÇAPALARI OMURGADIR — asıl risk aşırı-genişlemedir:
  - N1/N7: `PLAYBOOK = CORE / "playbook"` ardından `PLAYBOOK.rglob(...)` / `.glob(...)`
    MEŞRUDUR (core kendi ağacını tarar; canlı ölçüm: 26 türetilmiş ad). Bu yüzden
    geçişlilik YALNIZ segment-filtreli yol dedektörlerine verildi, TARAMA dedektörlerine
    DEĞİL. Bu iki satır o kararın bekçisidir; düşerlerse core'un kendi taramaları
    yanlış-pozitif olur ve gate alarm-yorgunluğundan ölür.
  - N2/N3: yol YAZDIRAN f-string ve `os.pathsep` birleştirmesi → sessiz kalmalı.
  - N6: `CORE / ".claude" / "memory-seed"` KAYITLI istisnadır (core'un kendi tohum dizini).

⚠ KONTROL GRUBU (K1/K2): kanonik `KÖK / "SOURCE_CODES"` ve `def repo_root()` sarmalayıcısı —
eskiden de yakalanan varyantlar. İki tarafta da yakalanmalı; yakalanmazsa bulgu değil
HARNESS bozuktur (PATTERN#19).

Koşum:  python tests/fixtures/proje_koku_varyantlari/run.py
MUTASYON: `git show <taban-sha>:scripts/validators/check_project_root_resolution.py`
          → P1..P5 düşer, K1/K2 ve N* ayakta kalır.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK / "scripts" / "validators"))

import check_project_root_resolution as R  # noqa: E402

SONUC: list[tuple[bool, str]] = []
TMP: Path | None = None


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


def bulgular(kaynak: str, ad: str):
    """`_ihlaller`i sentetik dosya üzerinde koştur — MUTASYON-DOSTU.

    Eski sürümde imza/ad değişikse çökmek yerine ölçülen sonuca çevirir
    ("çökme ≠ FAIL"; howto-infra-fix SAHA DERSLERİ D2).
    """
    assert TMP is not None
    p = TMP / f"{ad}.py"
    p.write_text(kaynak, encoding="utf-8")
    fn = getattr(R, "_ihlaller", None)
    if fn is None:
        return None
    try:
        return list(fn(p))
    except Exception as e:  # noqa: BLE001
        return f"HATA {type(e).__name__}: {e}"


BAS = "from pathlib import Path\nimport os, sys\nKOK = Path(__file__).resolve().parents[2]\n"

# ── POZİTİF: dört kaçış varyantı ───────────────────────────────────────────────────
P1 = BAS + 'for f in KOK.glob("*/*/*.cds"):\n    print(f)\n'
P2 = BAS + 'hedef = KOK.joinpath("SOURCE_CODES", "SD")\n'
P3 = BAS + 'hedef = f"{KOK}/SOURCE_CODES"\n'
P4 = BAS + 'hedef = str(KOK) + "/.claude/state.json"\n'
P5 = BAS + 'KOK2 = KOK.parent\nhedef = KOK2 / "SOURCE_CODES"\n'

# ── KONTROL GRUBU: eskiden de yakalanan varyantlar ─────────────────────────────────
K1 = BAS + 'hedef = KOK / "SOURCE_CODES"\n'
K2 = ("from pathlib import Path\n"
      "def repo_root():\n"
      "    return Path(__file__).resolve().parent.parent\n")

# ── FP ÇAPALARI ────────────────────────────────────────────────────────────────────
N1 = BAS + 'PLAYBOOK = KOK / "playbook"\nfor f in PLAYBOOK.rglob("*.md"):\n    print(f)\n'
N2 = BAS + 'print(f"core: {KOK}")\n'
N3 = BAS + 'yol = str(KOK) + os.pathsep + os.environ.get("PYTHONPATH", "")\n'
N4 = BAS + 'hedef = KOK / "governance" / "decisions"\n'
N5 = 'from pathlib import Path\nimport sys\nsys.path.insert(0, str(Path(__file__).parent))\n'
N6 = BAS + 'TOHUM = KOK / ".claude" / "memory-seed"\n'
N7 = BAS + 'ALT = KOK / "standards"\nfor f in ALT.glob("*.md"):\n    print(f)\n'

POZITIF = [
    ("P1", P1, "glob", "P1 `.glob(...)` → proje geneli tarama"),
    ("P2", P2, "joinpath", "P2 `.joinpath(\"SOURCE_CODES\")`"),
    ("P3", P3, "SOURCE_CODES", "P3 f-string `f\"{KÖK}/SOURCE_CODES\"`"),
    ("P4", P4, ".claude", "P4 str-concat `str(KÖK) + \"/.claude/...\"`"),
    ("P5", P5, "SOURCE_CODES", "P5 transitive `KÖK2 = KÖK.parent` → `KÖK2 / \"SOURCE_CODES\"`"),
]
KONTROL = [
    ("K1", K1, "K1 KONTROL kanonik `KÖK / \"SOURCE_CODES\"`"),
    ("K2", K2, "K2 KONTROL `def repo_root()` sarmalayıcısı"),
]
NEGATIF = [
    ("N1", N1, "N1 FP core-içi türetilmiş dizinde `.rglob` (geçişlilik TARAMAYA sızmamalı)"),
    ("N2", N2, "N2 FP yolu YAZDIRAN f-string"),
    ("N3", N3, "N3 FP `str(KÖK) + os.pathsep` (PYTHONPATH kurulumu)"),
    ("N4", N4, "N4 FP core-içi yol `KÖK / \"governance\"`"),
    ("N5", N5, "N5 FP `sys.path.insert(0, str(Path(__file__).parent))` (atama değil)"),
    ("N6", N6, "N6 FP kayıtlı istisna `.claude/memory-seed` (core tohum dizini)"),
    ("N7", N7, "N7 FP core-içi türetilmiş dizinde `.glob` (yeni eklenen attr sızmamalı)"),
]


def main() -> int:
    global TMP
    TMP = Path(tempfile.mkdtemp(prefix="proje_kok_"))
    try:
        for kod, kaynak, parca, ad in POZITIF:
            b = bulgular(kaynak, kod)
            if b is None or isinstance(b, str):
                kontrol(False, ad, f"ölçülemedi: {b}")
                continue
            metin = " ".join(m for _s, m in b)
            kontrol(len(b) >= 1 and parca in metin, ad,
                    f"bulgu={len(b)} (>=1 ve '{parca}' bekleniyor) :: {metin[:150]}")

        for kod, kaynak, ad in KONTROL:
            b = bulgular(kaynak, kod)
            kontrol(isinstance(b, list) and len(b) >= 1, ad,
                    f"bulgu={len(b) if isinstance(b, list) else b} (>=1 bekleniyor)")

        for kod, kaynak, ad in NEGATIF:
            b = bulgular(kaynak, kod)
            kontrol(isinstance(b, list) and len(b) == 0, ad,
                    f"bulgu={b if not isinstance(b, list) else len(b)} (0 bekleniyor)"
                    + ("" if isinstance(b, list) and not b else
                       " :: " + str(b)[:180]))

        # ── Yapısal çapa: tarama attr kümesi + geçişlilik ayrımı ──
        kontrol("glob" in getattr(R, "TARAMA_ATTR", set())
                and "rglob" in getattr(R, "TARAMA_ATTR", set()),
                "S1 TARAMA_ATTR hem `glob` hem `rglob` içeriyor",
                str(sorted(getattr(R, "TARAMA_ATTR", set()))))
        kontrol(getattr(R, "_gecisli_koklar", None) is not None,
                "S2 geçişli kök çözümlemesi (`_gecisli_koklar`) var")
    finally:
        shutil.rmtree(TMP, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\nproje_koku_varyantlari: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
