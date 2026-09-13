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
(ikisi hem `anlamli_imza`yı hem `d7_ciftleri`ni buradan okur — Q245②, 2026-09-13)
· `scripts/team_setup.py` (yalnız `D7_CIFTLERI`in pre-commit YOK onarım metni —
`hookspath_proje` uyarısı; eskiden `init_project --force` öneriyordu, Q303)
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

# ⭐ D7 ÇİFT LİSTESİ — TEK KAYNAK (2026-09-13, kayıt Q245②).
# Liste bugüne kadar İKİ kapıda AYRI literal olarak yaşıyordu (`session_start._drift_kontrol`
# + `ix_doctor._d7_drift`) — Q212'nin teşhis ettiği kopya-tanım sınıfının ikinci yüzü: yeni bir
# çift eklemek İKİ yere yazmayı gerektiriyordu ve biri unutulursa iki kapı yine ayrışırdı.
# Onarım metinleri de burada, çünkü çiftten çifte DEĞİŞİR (aşağıdaki pre-commit notu).
#
# `scripts/git-hooks/pre-commit` NEDEN BURADA (Q245②, ölçüldü 2026-09-13): `init_project.py`
# kopyayı doğumda BİR KEZ yazar (`uret`, var olanı ezmez), `team_setup.py` yalnız
# `core.hooksPath`i kablolar, içeriğe bakmaz ⇒ şablon sertleştikçe doğmuş projelerdeki kopya
# SESSİZCE geride kalıyordu (bir projede core-sızıntı kapısı bu yüzden fail-open kaldı).
# Şablonda yer tutucu YOK ⇒ davranışsal imza birebir eşit olmalıdır.
#
# ⛔ ONARIM METNİ KOPYALANMAZ — ölçülmüş üç tuzak (pre-commit için):
#   · `team_setup.dosya_tamamla` pre-commit ÜRETMEZ (yalnız settings.json + hook_shim.py)
#     ⇒ "team_setup ile üret" demek operatörü hiçbir şey üretmeyen bir komuta yollar.
#   · `init_project --force` CLAUDE.md · settings.json · project.yaml dahil HER üretilen
#     dosyayı ezer ⇒ tek dosya için önerilemez.
#   · pre-commit behavior-manifest yüzeyinde DEĞİL (`behavior_manifest.YUZEY_DOSYALAR`)
#     ⇒ "bilinçliyse manifest'e işle" bu çift için anlamsızdır.
_GENEL_YOK = "python core/scripts/team_setup.py ile uret"
_GENEL_SAPMA = "bilinçliyse manifest'e işle; değilse template'ten yenile"
_PRECOMMIT_YOK = ("sablondan KOPYALA (core/claude/git-hooks/pre-commit.template -> "
                  "scripts/git-hooks/pre-commit), sonra python core/scripts/team_setup.py "
                  "(core.hooksPath kablolar); init_project --force KULLANMA (tum dosyalari ezer)")
_PRECOMMIT_SAPMA = ("sablonda yer tutucu YOK, proje-ozel uyarlama beklenmez: sablondan yenile ve "
                    "projenin kendi deposunda PR ile commit'le (manifest yuzeyinde DEGIL)")

# (proje-göreli kopya, core-göreli şablon, görünen ad, YOK onarımı, SAPMA onarımı)
D7_CIFTLERI = (
    (".claude/settings.json", "claude/settings.template.json", "settings.json",
     _GENEL_YOK,
     _GENEL_SAPMA),
    ("scripts/hook_shim.py", "claude/hook_shim.template.py", "hook_shim.py",
     _GENEL_YOK,
     _GENEL_SAPMA),
    ("scripts/git-hooks/pre-commit", "claude/git-hooks/pre-commit.template", "pre-commit",
     _PRECOMMIT_YOK,
     _PRECOMMIT_SAPMA),
)


def d7_ciftleri(proj: Path, core: Path) -> list[tuple[Path, Path, str, str, str, str]]:
    """-> [(yerel, sablon, ad, yok_onarim, sapma_onarim, sablon_core_goreli)]

    `core` çağırana göre değişir: `session_start` → `PROJ/core` (junction), `ix_doctor` →
    kendi `CORE_ROOT`u. Şablon yolu mesajda core-GÖRELİ basılır (`tpl.name` DEĞİL:
    `git-hooks/` alt dizinini düşürür ve operatörü olmayan bir dosyaya yollar).
    """
    out = []
    for rel_y, rel_t, ad, yok, sapma in D7_CIFTLERI:
        out.append((proj / rel_y, core / rel_t, ad, yok, sapma, rel_t))
    return out


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
