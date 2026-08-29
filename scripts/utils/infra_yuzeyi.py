#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""infra_yuzeyi.py — "fixture KOŞUCUSU" yüzeyinin TEK KAYNAĞI (iki hook ortak kullanır).

NEDEN VAR (ölçüldü 2026-08-29, kayıt Q209): aynı yüzey tanımı İKİ kopyada yaşıyordu ve
kopyalar AYRIŞTI —
  · `scripts/hooks/infra_write_guard.py` koşucuları KORUMAYA aldı (`_KOSUCU`),
  · `scripts/hooks/post_validate.py` infra-EXPRESS nudge kolu aynı yola hâlâ
    "fixture = infra kararı DEĞİL" diyordu (`_INFRA_HARIC`).
⇒ Bir koşucu düzenlendiğinde BLOK kolu "bu infra" derken NUDGE kolu susuyordu: aynı dosya
hakkında iki hook iki farklı cevap veriyordu. Bu, gate'in kendisinden daha sinsi bir
kusurdur — hangi cevabın doğru olduğu KULLANICIYA görünmez.

SINIF TANIMI — bir fixture İKİ AYRI ŞEYDEN oluşur:
  · KORPUS  (`bad/`, `good/`, sahte ağaçlar, `.md`/`.cds`/`.json` örnekleri) = VERİ.
    İnfra kararı TAŞIMAZ; serbesttir (fixture eklemek teşvik edilir).
  · KOŞUCU  (`run.py` / `tests/run_*.py`) = KANIT ARACININ KENDİSİ. Mantığı, mutasyon
    kümesini ve TABAN STRATEJİSİNİ taşır; CI'ın yeşil/kırmızı kararını o belirler.
    Bir gate'in doğruluğu koşucusunun doğruluğu kadardır ⇒ koşucu bir İNFRA KARARIDIR.

AD-BAĞIMLILIĞI BİLİNÇLİ ve SINIRI ÖLÇÜLDÜ (2026-08-29): core deposunda 92 koşucunun 92'si
`run.py` (×90) + `tests/run_*.py` (×2) adlandırmasını kullanır (precision 92/92, recall
92/92). Tüketici projede aynı sınıf BAŞKA adlarla yaşar (`kur_ve_kos.py`,
`mutasyon_kosumu.py`, `fp_ve_mutasyon.py`) ⇒ orada ad değil KONUM esas alınır
(`validators-local/fixtures/**.py`; korpus dosyaları `.md`/`.yaml` olduğu için FP yok).

⛔ NEDEN AYRI MODÜL (ve neden hook-başına kopya DEĞİL): 2026-08-13 ölçümü "hook'a ortak
yardımcı bağlama" konusunda haklı bir uyarı bırakmıştı — `hook_shim` hook'u `runpy` ile
AYNI SÜREÇTE koşturur, `sys.path[0]` boş olur ve DÜZ kardeş-import ÖLÜR. Bu modül o
tuzağa girmez çünkü tüketiciler yolu `__file__`ten türetir
(`sys.path.insert(0, parents[1])` → `scripts/`), tıpkı bugün üretimde koşan
`utils.inject_paths` gibi. Tüketici tarafında import DAİMA `try/except` içindedir ve
başarısızlık SESSİZ DEĞİLDİR (guard stderr'e NOT basar) — çünkü "yardımcı yok" ile
"yol korunmuyor" aynı şeye benzemez ama sonucu aynıdır.

Tüketiciler: `scripts/hooks/infra_write_guard.py` · `scripts/hooks/post_validate.py`
Korpus: tests/fixtures/infra_write_guard/run.py · tests/fixtures/fs_docstd/run.py
"""
from __future__ import annotations

import re
import sys

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# CORE deposu köküne GÖRELİ (posix) koşucu deseni — `^` ile birlikte kullanılır.
KOSUCU_REL = r"tests/(?:fixtures/[^/]+/run\.py|run_[^/]+\.py)$"

# PROJE deposundaki koşucu: ad değil KONUM (overlay gate'lerinin kanıt araçları).
KOSUCU_PROJE = r"/scripts/validators-local/fixtures/.+\.py$"

# TAM YOL üzerinde arama yapan birleşik desen (her iki yazımı da yakalar).
KOSUCU = re.compile(r"/" + KOSUCU_REL + r"|" + KOSUCU_PROJE, re.IGNORECASE)


def kosucu_mu(yol: str) -> bool:
    """Verilen (ham ya da normalize) yol bir fixture KOŞUCUSU mu?"""
    return bool(KOSUCU.search(str(yol).replace("\\", "/")))


if __name__ == "__main__":  # hızlı kendi-kendini sınama (koşucu DEĞİL: sayı raporlamaz)
    ORNEKLER = [
        # (yol, koşucu mu)
        ("C:/x/core/tests/fixtures/ornek/run.py", True),
        ("/home/u/core/tests/run_fixture_tests.py", True),
        ("/home/u/core/tests/fixtures/ornek/bad/veri.py", False),   # KORPUS = veri
        ("/home/u/core/tests/fixtures/ornek/agac/run_yardimci.py", False),
        ("/home/u/proje/scripts/validators-local/fixtures/kur_ve_kos.py", True),
        ("/home/u/proje/scripts/validators-local/check_x.py", False),  # validator, koşucu değil
        ("/home/u/core/scripts/hooks/post_validate.py", False),
    ]
    hata = 0
    for yol, bekleniyor in ORNEKLER:
        if kosucu_mu(yol) is not bekleniyor:
            hata += 1
            print(f"FAIL {yol} -> {kosucu_mu(yol)} (beklenen {bekleniyor})")
    print("infra_yuzeyi: OK" if not hata else f"infra_yuzeyi: {hata} HATA")
    raise SystemExit(1 if hata else 0)
