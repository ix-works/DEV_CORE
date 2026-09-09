#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drift_imzasi.py — D7 template-drift ölçümünün TEK KAYNAĞI (iki kapı ortak kullanır).

NEDEN VAR (ölçüldü 2026-09-09, kayıt Q212): AYNI olgu — *"projenin `.claude/settings.json`'u
şablondan sapmış mı"* — İKİ kapıda İKİ AYRI tanımla ölçülüyordu ve tanımlar AYRIŞTI:
  · `scripts/hooks/session_start.py::_anlamli_imza()` → DAVRANIŞSAL imza
    (JSON'da `_comment*` anahtarları atılır, metinde CRLF/son-boşluk sayılmaz)  → SAPMA YOK
  · `scripts/ix_doctor.py::katman4()` 4a kolu       → HAM `sha256(read_bytes())`  → SAPMIŞ
Ölçülen canlı sonuç (bir tüketici projede, aynı dosya, aynı an): `session_start` **eş**
(`33522a6e2f10dcc5 == 33522a6e2f10dcc5`), `ix_doctor` **`[WARN] settings.json template'ten
SAPMIŞ`**. Tek fark `_comment*` anahtarlarıydı — davranış TAŞIMAZLAR. ⇒ `ix_doctor`in her
koşumu bir YANLIŞ-POZİTİF basıyordu ve yanlış-pozitif üreten uyarı **uyarı körlüğü** yaratır:
gerçek drift geldiğinde aynı satır görünür ve aynı şekilde göz ardı edilir.

⭐ NORMALİZASYON BURADA **ZORUNLUDUR** — ve bu, bu evde ZATEN KARARLANMIŞ bir ayrımdır
(`governance/infra-changelog.md`, `behavior_manifest` kaydının *"TASARIM KARARI — taban neden
NORMALİZE edilmedi"* bloğu):
  · **D7 = iki BAĞIMSIZ ÜRETİLMİŞ artefaktın kıyası** (proje `settings.json` ↔ `settings.template.json`).
    İkisini ayrı ayrı biz/araç üretiriz; insan notu (`_comment*`) ve satır-sonu farkı
    *beklenen gürültüdür* ⇒ normalize edilir.
  · **`behavior_manifest.uretilen_hash` = dosyanın KENDİ kayıtlı geçmişiyle kıyası.** O baytları
    biz yazdık ⇒ her sapma dışarıdan dokunuşun kanıtıdır ⇒ **bayt-bayt** kalır.
İki eksen DİKTİR. Bu modül YALNIZ birinci ekseni (D7) temsil eder; `behavior_manifest`
tabanını normalize etmek için KULLANILMAZ (bu ölçülmemiş bir gevşetme olurdu).

⛔ NEDEN AYRI MODÜL (ve neden kapı-başına kopya DEĞİL): kopya-tanım tam da bu turun teşhisidir.
`hook_shim` hook'u `runpy` ile AYNI SÜREÇTE koşturur, `sys.path[0]` boş olur ve DÜZ
kardeş-import ÖLÜR ⇒ tüketiciler yolu `__file__`ten türetir
(`sys.path.insert(0, parents[1])` → `scripts/`), tıpkı `utils.infra_yuzeyi` (Q209) ve
`utils.inject_paths` gibi. ⛔ BAŞARISIZLIK SESSİZ DEĞİL: modül okunamazsa D7 kolu **PASS
DEMEZ**, "ÖLÇÜLEMEDİ" der (ölçüm-yokluğu sözleşmesi — bu evde `ix_doctor._kablolama_kontrol`
S4 vektörüyle ZATEN çivili bir sınıf).

Tüketiciler: `scripts/hooks/session_start.py` · `scripts/ix_doctor.py`
Korpus: tests/fixtures/d7_drift_imzasi/run.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# İmza çıkarılamadığında dönen DEĞER. ⛔ Boş dize DEĞİL ve rastgele DEĞİL: tüketici bunu
# görürse "eş/eş değil" diye karar VERMEZ, ölçüm yapılamadığını İLAN eder. (İki taraf da
# okunamazsa `"?" == "?"` sahte-PASS üretirdi — çağıran bu sabiti AYRICA kontrol eder.)
OKUNAMADI = "?"


def yorumsuz(nesne):
    """`_comment*` anahtarlarını özyinelemeli at — JSON'da yorum yoktur, bunlar insan notudur."""
    if isinstance(nesne, dict):
        return {k: yorumsuz(v) for k, v in nesne.items() if not k.startswith("_comment")}
    if isinstance(nesne, list):
        return [yorumsuz(x) for x in nesne]
    return nesne


def anlamli_imza(p: Path) -> str:
    """DAVRANIŞSAL imza: JSON'da yorum anahtarları, metinde CRLF/son-boşluk sayılmaz.

    2026-07-10 (kökeni): bu fonksiyon `session_start` içinde ham `_sha16` idi. Bir tüketici
    projenin settings.json'u template'le kablolama olarak BİREBİR aynıyken, tek bir
    `_comment_yorumlar` anahtarı yüzünden her oturum "SAPMIS (D7)" diye bağırıyordu.
    Yanlış-pozitif üreten uyarı, uyarıya karşı bağışıklık yaratır — gerçek drift
    geldiğinde görülmez. Kapsam kaybı yok: atılan alanların ikisi de (yorum, satır-sonu)
    davranış taşımaz.

    2026-09-09 (Q212): fonksiyon `session_start`tan BURAYA taşındı; `ix_doctor` D7 kolu
    kendi ham-sha kopyasını bırakıp bunu okuyor. Kopya kalsaydı ikisi yine ayrışırdı.

    ⚠ JSON'da anahtar SIRASI sayılmaz (`sort_keys=True`) — sıra davranış taşımaz.
    ⚠ Bir hook girdisinin/matcher'ın DÜŞMESİ imzayı DEĞİŞTİRİR (kapsam kaybı yok).
    """
    try:
        ham = p.read_bytes()
        if p.suffix == ".json":
            veri = yorumsuz(json.loads(ham.decode("utf-8")))
            norm = json.dumps(veri, sort_keys=True, ensure_ascii=False).encode("utf-8")
        else:
            norm = ham.replace(b"\r\n", b"\n").strip()
        return hashlib.sha256(norm).hexdigest()[:16]
    except Exception:
        return OKUNAMADI


if __name__ == "__main__":  # elle duman testi
    for _y in sys.argv[1:]:
        print(f"{anlamli_imza(Path(_y))}  {_y}")
