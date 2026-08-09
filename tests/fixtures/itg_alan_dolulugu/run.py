# -*- coding: utf-8 -*-
"""itg_alan_dolulugu — ITG S2 sign-off gate'i alanların DOLU olduğunu ölçüyor mu (KAYIT V3).

KÖK: `check_itg_signoff` docstring'i "Zorunlu alanlar dolu mu" diye BEYAN ediyordu, ama
kod yalnız BAŞLIĞIN geçtiğini arıyordu (`re.search(r"kapsam\\s*:")`). Sonuç: playbook'taki
S2 şablonunu kopyalayıp hiçbir alanı doldurmadan `MUTABAKAT: [x]` işaretlemek gate'i
GEÇİYORDU — ölçüldü: 8 satırlık boş şablon → `✓ intake-artefaktı TAM`, exit 0.

NEDEN ÖNEMLİ: bu bir BLOCKER gate'idir — `run_review.py` `itg_s2_signoff` task'ı üzerinden
SAP-YAZMA kapısında durur (ADR 0022 Faz-1). "Kapı var ama bakmıyor" hâli kapı olmamasından
tehlikelidir: koruma SANISI üretir (bkz. 2026-07-26, `frozen_readonly_paths` vakası —
kaldırılmış bir kural 10 dokümanda "aktif" ilan ediliyordu).

TUTARSIZLIK, EKSİKLİK DEĞİL: doğru teknik zaten AYNI DOSYADAYDI — `_PRIOR_ART_DOLU`
deseni prior-art için değerin dolu olmasını arıyordu. Kusur, o titizliğin diğer üç alana
uygulanmamasıydı. Fix deseni genelleştirir (aynı sınıf: V4'te `.gitignore` kilidi
alt-dizge ararken SIR kontrolü tam-satır kullanıyordu — tek dosyada iki titizlik seviyesi).

⚠ FP ÇAPALARI OMURGADIR: N1 (gerçekten doldurulmuş artefakt) ve N4 (`Prior-art: yok` —
kısa ama MEŞRU cevap) düşerse gate aşırı-sıkılaşmıştır ve meşru S2 işlerini bloklar.
`_dolu_mu` bilinçli olarak "N harften az" gibi sezgisel kullanmaz; tam da N4 yüzünden.

⚠ KONTROL GRUBU (K1/K2): eskiden de yakalanan iki varyant — alan başlığı hiç YOK, ve
MUTABAKAT işaretsiz. İki tarafta da FAIL vermeli; vermezse harness bozuktur (PATTERN#19).

Koşum:  python tests/fixtures/itg_alan_dolulugu/run.py
MUTASYON: `git show <taban-sha>:scripts/validators/check_itg_signoff.py` → P1/P2/P3 düşer,
          K1/K2/N* ayakta kalır.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
GATE = KOK / "scripts" / "validators" / "check_itg_signoff.py"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


def kos(icerik: str, dizin: Path, ad: str) -> tuple[int, str]:
    p = dizin / f"{ad}.md"
    p.write_text(icerik, encoding="utf-8")
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    try:
        r = subprocess.run([sys.executable, str(GATE), str(p)], env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
    except Exception as e:  # noqa: BLE001  (mutasyon-dostu)
        return (-1, f"KOŞULAMADI: {type(e).__name__}: {e}")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ── P1: playbook/intake-triage.md S2 şablonu, HİÇBİR alan doldurulmamış + [x] ────────
P1 = """# INTAKE — <kısa-ad>  (tarih)
- Modül / iş-tipi / KAPSAM:
- İstenen (özet):
- Çıkan domain-konuları:
- Etkilenen objeler (canlı-doğrulanmış):
- Prior-art: yok
- Kabul kriterleri (EARS):
- Açık kararlar / riskler:
- MUTABAKAT: [x] kullanıcı sign-off
"""

# ── P2: alanlar ŞABLON YER-TUTUCULARIYLA dolu (kopyala-yapıştır) + [x] ──────────────
P2 = """# INTAKE — <kısa-ad>  (tarih)
- Modül / iş-tipi / KAPSAM: SD / rapor / S2  (gerekçe: ...)
- İstenen (özet): yeni rapor
- Çıkan domain-konuları: [konu → araştırma özeti (a/b/c eksen)]
- Etkilenen objeler (canlı-doğrulanmış): [obje → reuse/yeni/değişir → blast-radius]
- Prior-art: yok
- Kabul kriterleri (EARS): "<olay> olduğunda sistem <sonuç> yapmalı" / "<durum> ise ..."
- MUTABAKAT: [x] kullanıcı sign-off
"""

# ── P3: tek alan boş (kısmi doldurma) — gate hepsini istemeli ───────────────────────
P3 = """# INTAKE — sevk raporu  (2026-08-01)
- Modül / iş-tipi / KAPSAM: SD / rapor / S2 (gerekçe: yeni ekran + 2 yeni CDS)
- Etkilenen objeler (canlı-doğrulanmış):
- Prior-art: bulundu: ZSD001_I_ORDER benzeri rapor (canlı doğrulandı)
- Kabul kriterleri (EARS): kullanıcı kaydettiğinde sistem sevk kalemini kilitlemeli
- MUTABAKAT: [x] kullanıcı sign-off
"""

# ── K1 (KONTROL): alan BAŞLIĞI hiç yok → eskiden de FAIL ───────────────────────────
K1 = """# INTAKE — sevk raporu  (2026-08-01)
- İstenen (özet): yeni sevk raporu
- Prior-art: yok
- MUTABAKAT: [x] kullanıcı sign-off
"""

# ── K2 (KONTROL): her şey dolu ama MUTABAKAT İŞARETSİZ → eskiden de FAIL ───────────
K2 = """# INTAKE — sevk raporu  (2026-08-01)
- Modül / iş-tipi / KAPSAM: SD / rapor / S2 (gerekçe: yeni ekran + 2 yeni CDS)
- Etkilenen objeler (canlı-doğrulanmış): ZSD001_I_ORDER (değişir, 3 tüketici), ZSD001_C_ORDER (yeni)
- Prior-art: bulundu: ZSD001 sipariş raporu (canlı doğrulandı)
- Kabul kriterleri (EARS): kullanıcı kaydettiğinde sistem sevk kalemini kilitlemeli
- MUTABAKAT: [ ] kullanıcı sign-off
"""

# ── N1 (FP ÇAPASI): gerçekten doldurulmuş artefakt → PASS ──────────────────────────
N1 = """# INTAKE — sevk emri kalem raporu  (2026-08-01)
- Modül / iş-tipi / KAPSAM: SD / rapor / S2  (gerekçe: yeni ekran + 2 yeni CDS + UI5 app)
- İstenen (özet): sevk emri kalemlerini filtreli grid'de göster
- Çıkan domain-konuları: sevk emri yaşam döngüsü → RAP projeksiyonu üzerinden okunur
- Etkilenen objeler (canlı-doğrulanmış): ZSD001_I_ORDER (reuse), ZSD001_C_ORDER (yeni), ZCL_SD001_RPT (yeni)
- Prior-art: bulundu: ZSD001 sipariş raporu (adt_get ile canlı doğrulandı)
- Kabul kriterleri (EARS): kullanıcı filtre uyguladığında sistem yalnız açık kalemleri listelemeli
- Açık kararlar / riskler: ortak value-help mi lokal mi (kullanıcıya soruldu)
- MUTABAKAT: [x] kullanıcı sign-off
"""

# ── N2 (FP ÇAPASI): ÇOK SATIRLI değer — devam satırları da değer sayılmalı ─────────
N2 = """# INTAKE — sevk emri kalem raporu  (2026-08-01)
- Modül / iş-tipi / KAPSAM: SD / rapor / S2 (gerekçe: yeni ekran)
- Etkilenen objeler (canlı-doğrulanmış):
    ZSD001_I_ORDER  → reuse → 3 tüketici (canlı where-used)
    ZSD001_C_ORDER  → yeni  → tüketici yok
- Prior-art: bulundu: ZSD001 sipariş raporu
- Kabul kriterleri (EARS):
    kullanıcı kaydettiğinde sistem sevk kalemini kilitlemeli
- MUTABAKAT: [x] kullanıcı sign-off
"""

# ── N3 (FP ÇAPASI): başlıklar farklı yazımla (esnek eşleşme korunuyor mu) ──────────
N3 = """# INTAKE — sevk emri  (2026-08-01)
* KAPSAM: S2 — yeni sprint
* Etkilenen objeler: ZSD001_I_ORDER (değişir)
* Prior-art: yok
* Kabul kriterleri (EARS): sipariş kaydedildiğinde sistem kalem üretmeli
* MUTABAKAT: [X] sign-off
"""

# ── N4 (FP ÇAPASI): `Prior-art: yok` — KISA ama meşru cevap bloklanmamalı ──────────
N4 = """# INTAKE — sevk emri  (2026-08-01)
- KAPSAM: S2 (gerekçe: yeni obje seti)
- Etkilenen objeler (canlı-doğrulanmış): ZSD001_T_ORDER (yeni tablo)
- Prior-art: yok
- Kabul kriterleri (EARS): kayıt sırasında sistem zorunlu alanları doğrulamalı
- MUTABAKAT: [x] kullanıcı sign-off
"""

SENARYOLAR: list[tuple[str, str, bool, str]] = [
    ("P1", P1, True, "P1 BOŞ şablon + [x] → BLOCKER (gate'in ta kendisi)"),
    ("P2", P2, True, "P2 ŞABLON YER-TUTUCULARI + [x] → BLOCKER"),
    ("P3", P3, True, "P3 tek alan boş (kısmi doldurma) → BLOCKER"),
    ("K1", K1, True, "K1 KONTROL alan başlığı hiç yok → BLOCKER"),
    ("K2", K2, True, "K2 KONTROL MUTABAKAT işaretsiz → BLOCKER"),
    ("N1", N1, False, "N1 FP gerçekten doldurulmuş artefakt → PASS"),
    ("N2", N2, False, "N2 FP çok satırlı değer → PASS"),
    ("N3", N3, False, "N3 FP farklı madde-işareti/yazım → PASS"),
    ("N4", N4, False, "N4 FP kısa ama meşru 'Prior-art: yok' → PASS"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="itg_dolu_"))
    try:
        for kod, icerik, fail_bekleniyor, ad in SENARYOLAR:
            rc, cikti = kos(icerik, tmp, kod)
            if rc < 0:
                kontrol(False, ad, cikti)
                continue
            oldu = rc != 0
            kontrol(oldu == fail_bekleniyor, ad,
                    f"exit={rc} (beklenen {'1' if fail_bekleniyor else '0'})"
                    + ("" if oldu == fail_bekleniyor else " :: " + cikti.strip()[:220]))

        # ── Yapısal çapa: doluluk kontrolü GERÇEKTEN alan-başına koşuyor mu ──
        #    (mesajın hangi alanları saydığı; "hepsi eksik" diye kaba bir mesaj değil)
        rc, cikti = kos(P3, tmp, "P3s")
        kontrol("etkilenen objeler" in cikti.lower(),
                "S1 boş alan ADIYLA raporlanıyor (P3 → 'etkilenen objeler')",
                cikti.strip()[:160])
        kontrol("kapsam" not in cikti.lower().split("boş/şablon:")[-1].split(".")[0],
                "S2 DOLU alanlar suçlanmıyor (P3'te 'kapsam' listede olmamalı)",
                cikti.strip()[:160])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\nitg_alan_dolulugu: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
