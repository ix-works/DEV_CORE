#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cds_curr_referans_tipi — C-TBL-CUR referans alanı: YANLIŞ BLOCKER sınıfı (DEV_CORE Issue #399).

VAKA (2026-11-08, tüketici bildirimi, sahip onaylı): `check_table` CURR alanının başvurduğu
para birimi alanını `cuky_fields` içinde arıyordu; o küme YALNIZ paylaşılan sözlükteki
(`utils/ddic_semantics.CUKY_DTELS`) DTEL'leri taşıdığı için üç ayrı durum AYNI BLOCKER'ı
alıyordu ("CUKY '<alan>' tabloda yok"):
  ① alan VAR, DTEL'i standart ama sözlükte yok (`konwa` — koşul kaydı para birimi)
  ② alan VAR, DTEL'i Z'li CUKY DTEL'i (sözlük onu bilemez)
  ③ qualified başvuru BAŞKA tabloyu gösteriyor (`'t001.waers'`; `split('.')[-1]` tablo
     kısmını atıyordu). Standart KONP: `KBETR` → `RV13A-KONWA`, `PKWRT` → `T001-WAERS`.
Yalnız "alan HİÇ yok" gerçek BLOCKER'dı.

DÜZELTME: ① sözlüğe `konwa`/`konws` (CUKY) + `kmein`/`konms` (UNIT) · ② WARNING
("tip sözlükten doğrulanamadı") · ③ aynı-tablo denetimi atlanır + INFO notu (stdout, rc 0).
Tablo adı karşılaştırması büyük/küçük harf duyarsız. KARDEŞ (aynı sınıf, R7): yerleşik tipli
`curr : abap.cuky;` alanı tablo alan desenine uymadığı için hiç kaydedilmiyordu ⇒ ona başvuran
tutar da "tabloda yok" alıyordu; artık referans sorusu için tanınır (marker denetimi değişmedi).

BUG-GATE TURU (PR #400, 2026-11-08) — ilk düzeltmenin kendi gerilemeleri:
  F1 başvurulan YEREL alanın marker'ı denetlenmiyordu (Z'li DTEL / `abap.cuky` marker'sız →
     "temiz"; taban BLOCKER veriyordu) → R2b R7b R7c R7d S3 · F3 boş tablo kısmı (`'.waers'`)
     "başka tablo" sayılıyordu → Q1 · F4 blok yorumdaki `define table` adı kimliği ele
     geçiriyordu → B1 · F5 ID'ler checklist'e hizalandı (tablo C-TBL-CUR-02/-04, yapı
     C-STR-CUR-04/-05) → K1 R2 R4b S2 S3 S4.

KORUNAN BLOCKER'LAR (K vektörleri — düzeltme turu kendi regresyonunu üretmesin):
alan yok · annotation eksik · qualified değil · CUKY marker eksik · QUAN annotation eksik.

AĞAÇ BAĞIMSIZ: her vektör bir `scripts/` köküne karşı ALT SÜREÇLE koşar (sys.modules
önbelleği iki ağacı karıştırmasın). Varsayılan kök = bu repo. `--kok <scripts_dizini>`
başka bir ağacı (ör. taban sürümün `git show` kopyası) ölçer. Mutasyon kipleri gerçek
ağacı DEĞİŞTİRMEZ: `scripts/validators` + `scripts/utils` geçici dizine kopyalanır,
yama orada uygulanır.

GERÇEK GİRİŞ NOKTASI (RR vektörleri): `run_review.py --task table_creation|struct_creation
--json` geçici kopyada, SAHTE `sap_adt_lib` ile (AĞ YOK) koşar; yalnız
`check_cds_currency_reference.py` kaydının durumu okunur.

Kullanım:
    python tests/fixtures/cds_curr_referans_tipi/run.py                  → exit 0 = hepsi PASS
    python tests/fixtures/cds_curr_referans_tipi/run.py --kok <scripts>  → başka ağaç
    python tests/fixtures/cds_curr_referans_tipi/run.py --mutasyon-<ad>  → tek mutasyon
Mutasyon exit sözleşmesi (run_battery karar tablosu): ilan edilen küme düştü → 1 ·
sapma → 2 · çapa bulunamadı / birden çok geçiyor → 3.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "scripts"
VAL_REL = Path("validators") / "check_cds_currency_reference.py"
DS_REL = Path("utils") / "ddic_semantics.py"

SAHTE_LIB = '''# -*- coding: utf-8 -*-
"""SAHTE sap_adt_lib — cds_curr_referans_tipi izolasyonu. AG ERISIMI YOK."""


class SAPADTClient:
    def __init__(self, *a, **kw):
        raise ConnectionError("sahte: baglanti yok (fixture izolasyonu)")
'''


def tablo(govde: str, ad: str = "zsd001_t_test", tur: str = "table") -> str:
    return (f"@EndUserText.label : 'Test'\n"
            f"@AbapCatalog.tableCategory : #TRANSPARENT\n"
            f"define {tur} {ad} {{\n  key mandt : mandt not null;\n{govde}}}\n")


# ─────────────────────────── ARTEFAKTLAR ───────────────────────────
ART = {
    # R1 — Issue #399 yeniden üretimi: `konwa` tipli para birimi alanı
    "R1": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                "  rate : kbetr;\n"
                "  @Semantics.currencyCode : true\n"
                "  curr : konwa;\n"),
    # R2 — Z'li CUKY DTEL'i (marker'lı): sözlük tipi bilemez ⇒ WARNING
    "R2": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                "  rate : kbetr;\n"
                "  @Semantics.currencyCode : true\n"
                "  curr : zsd001_de_cuky;\n"),
    # R2b — bug-gate F1: aynı, marker'SIZ ⇒ marker eksik BLOCKER (+ tip WARNING)
    "R2b": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                 "  rate : kbetr;\n"
                 "  curr : zsd001_de_cuky;\n"),
    # R3 — başka tabloya qualified başvuru
    "R3": tablo("  @Semantics.amount.currencyCode : 't001.waers'\n"
                "  rate : kbetr;\n"),
    # R4 — kendi adı BÜYÜK harfle tanımlı, başvuru karışık harfle ⇒ aynı tablo
    "R4": tablo("  @Semantics.amount.currencyCode : 'Zsd001_T_Test.curr'\n"
                "  rate : kbetr;\n"
                "  @Semantics.currencyCode : true\n"
                "  curr : konwa;\n", ad="ZSD001_T_TEST"),
    # R4b — aynı harf durumu, alan YOK ⇒ aynı tablo sayılır, BLOCKER korunur
    "R4b": tablo("  @Semantics.amount.currencyCode : 'Zsd001_T_Test.yok'\n"
                 "  rate : kbetr;\n", ad="ZSD001_T_TEST"),
    # R5 — `konwa` artık CUKY ⇒ marker denetimi onu da kapsar (madde 4)
    "R5": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                "  rate : kbetr;\n"
                "  curr : konwa;\n"),
    # R5b — sözlük üyeliğini TEK BAŞINA ölçen ikiz: `konwa` alanına HİÇBİR CURR başvurmaz,
    # marker yok ⇒ BLOCKER'ı yalnız sözlük verir (R5'te bug-gate F1 sonrası yerel başvuru
    # yolu da BLOCKER verdiği için R5 sözlük mutasyonunu artık ayırt etmez)
    "R5b": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                 "  rate : kbetr;\n"
                 "  @Semantics.currencyCode : true\n"
                 "  curr : waers;\n"
                 "  ikinci : konwa;\n"),
    # R6 — `konws` (ikinci yeni CUKY üyesi)
    "R6": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                "  rate : kbetr;\n"
                "  @Semantics.currencyCode : true\n"
                "  curr : konws;\n"),
    # R7 — kardeş (aynı sınıf): yerleşik tip `abap.cuky` alan desenine uymuyordu ⇒
    # alan hiç kaydedilmez, ona başvuran sözlük CURR'u "tabloda yok" BLOCKER'ı alırdı
    "R7": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                "  rate : netwr;\n"
                "  @Semantics.currencyCode : true\n"
                "  curr : abap.cuky;\n"),
    # R7b — bug-gate F1: R7'nin marker'SIZ eşi ⇒ BLOCKER (ilk tur "temiz" diyordu)
    "R7b": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                 "  rate : netwr;\n"
                 "  curr : abap.cuky;\n"),
    # R7c — uzunluklu yerleşik tip, marker'lı ⇒ temiz
    "R7c": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                 "  rate : netwr;\n"
                 "  @Semantics.currencyCode : true\n"
                 "  curr : abap.cuky(5);\n"),
    # R7d — uzunluklu yerleşik tip, marker'SIZ (aradaki boş satır bloğu bölmez) ⇒ BLOCKER
    "R7d": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                 "  rate : netwr;\n"
                 "\n"
                 "  curr : abap.cuky( 5 );\n"),
    # Q1 — bug-gate F3: boş tablo kısmı ⇒ qualified DEĞİL BLOCKER (ilk tur "başka tablo")
    "Q1": tablo("  @Semantics.amount.currencyCode : '.waers'\n"
                "  rate : netwr;\n"
                "  @Semantics.currencyCode : true\n"
                "  waers : waers;\n"),
    # B1 — bug-gate F4: blok yorumdaki eski `define table` başlığı adı ELE GEÇİRMEZ
    "B1": ("/* eski tanim:\ndefine table zsd001_t_eski {\n*/\n"
           + tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.yok'\n"
                   "  rate : netwr;\n")),
    # K1 — alan HİÇ yok ⇒ BLOCKER korunur
    "K1": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.yok'\n"
                "  rate : kbetr;\n"
                "  @Semantics.currencyCode : true\n"
                "  waers : waers;\n"),
    # K2 — CURR annotation eksik
    "K2": tablo("  rate : netwr;\n"
                "  @Semantics.currencyCode : true\n"
                "  waers : waers;\n"),
    # K3 — qualified değil
    "K3": tablo("  @Semantics.amount.currencyCode : 'waers'\n"
                "  rate : netwr;\n"
                "  @Semantics.currencyCode : true\n"
                "  waers : waers;\n"),
    # K4 — CUKY marker eksik (sözlükteki eski üye)
    "K4": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.waers'\n"
                "  rate : netwr;\n"
                "  waers : waers;\n"),
    # K5 — QUAN annotation eksik
    "K5": tablo("  kwmeng : kwmeng;\n"
                "  @Semantics.unitOfMeasure : true\n"
                "  meins : meins;\n"),
    # K6 — tam doğru, aynı tablo ⇒ temiz, INFO YOK
    "K6": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.waers'\n"
                "  rate : netwr;\n"
                "  @Semantics.currencyCode : true\n"
                "  waers : waers;\n"),
    # S1 — 3. BAĞLAM: yapı (`define type`, struct_creation yolu) + `konwa`
    "S1": tablo("  @Semantics.amount.currencyCode : 'zsd001_s_test.curr'\n"
                "  rate : kbetr;\n"
                "  @Semantics.currencyCode : true\n"
                "  curr : konwa;\n", ad="zsd001_s_test", tur="type"),
    # S2 — yapı + alan yok ⇒ BLOCKER korunur
    "S2": tablo("  @Semantics.amount.currencyCode : 'zsd001_s_test.yok'\n"
                "  rate : kbetr;\n", ad="zsd001_s_test", tur="type"),
    # S3 — yapı + Z'li CUKY marker'SIZ ⇒ C-STR-CUR-05 BLOCKER
    "S3": tablo("  @Semantics.amount.currencyCode : 'zsd001_s_test.curr'\n"
                "  rate : kbetr;\n"
                "  curr : zsd001_de_cuky;\n", ad="zsd001_s_test", tur="type"),
    # S4 — yapı + Z'li CUKY marker'lı ⇒ C-STR-CUR-04 WARNING
    "S4": tablo("  @Semantics.amount.currencyCode : 'zsd001_s_test.curr'\n"
                "  rate : kbetr;\n"
                "  @Semantics.currencyCode : true\n"
                "  curr : zsd001_de_cuky;\n", ad="zsd001_s_test", tur="type"),
    # ── DEV_CORE #402 (PR #400 bug-gate LOW bulguları Y1-Y3 + EK-3) ──
    # Y1a — marker blok YORUMUN içinde (kapanış annotation satırında), sözlük CUKY alanı
    # ⇒ marker YOK sayılmalı ⇒ C-TBL-CUR-04 BLOCKER (taban: "temiz")
    "Y1a": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                 "  rate : kbetr;\n"
                 "  /* eski:\n  @Semantics.currencyCode : true */\n"
                 "  curr : waers;\n"),
    # Y1b — aynı, Z'li CUKY DTEL'i ⇒ marker BLOCKER + tip WARNING (taban: yalnız WARNING)
    "Y1b": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                 "  rate : kbetr;\n"
                 "  /* eski:\n  @Semantics.currencyCode : true */\n"
                 "  curr : zsd001_de_cuky;\n"),
    # Y1k — KONTROL (FP çapası): blok yorum ARADA, gerçek marker alanın hemen üstünde ⇒ temiz
    "Y1k": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                 "  rate : kbetr;\n"
                 "  /* not */\n"
                 "  @Semantics.currencyCode : true\n"
                 "  curr : waers;\n"),
    # Y2 — çift nokta: tablo kısmı 'zsd001_t_test.' ⇒ qualified değil (taban: INFO "başka tablo")
    "Y2": tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test..curr'\n"
                "  rate : kbetr;\n"),
    # Y3 — `--` satırındaki `/*` blok maskeyi AÇMAMALI (taban: dosya sonuna kadar maskeli ⇒
    # yerleşik `abap.cuky` alanı görünmez ⇒ sahte "tabloda yok" BLOCKER)
    "Y3": ("-- not: /* eski bicim\n"
           + tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                   "  rate : netwr;\n"
                   "  @Semantics.currencyCode : true\n"
                   "  curr : abap.cuky;\n")),
    # Y3k — KONTROL: aynı satır `//` ile ⇒ temiz (tabanda da temiz)
    "Y3k": ("// not: /* eski bicim\n"
            + tablo("  @Semantics.amount.currencyCode : 'zsd001_t_test.curr'\n"
                    "  rate : netwr;\n"
                    "  @Semantics.currencyCode : true\n"
                    "  curr : abap.cuky;\n")),
    # Y3c — ÇAPA (Y3'ün tek başına koruyamadığı yön): `--` satırındaki `/*` maskeyi açarsa
    # dosyanın GERİ KALANI görünmez ⇒ gerçek ihlal (annotation'sız CURR) "temiz" olur.
    # Ölçüldü: `--mutasyon-y3-maske` altında Y3 YEŞİL kaldı (Y1 ile parse_source da maskeli
    # okuduğundan hiç alan kalmıyor ⇒ boş-temiz); Y3 tabanın kırmızısını, Y3c bugünün
    # korumasını taşır.
    "Y3c": ("-- not: /* eski bicim\n"
            + tablo("  rate : netwr;\n")),
    # Y3b — KARDEŞ: satır SONU `--` yorumu alan desenini (`;$`) bozmamalı ⇒ annotation eksik
    # BLOCKER (taban: alan kaydedilmiyor ⇒ "temiz"; aynı satır `//` ile BLOCKER veriyordu)
    "Y3b": tablo("  rate : netwr; -- tutar\n"),
}

# EK-3 (K5) — CDS kolon-adı sezgisi: `curr` (para BİRİMİ) elemanı CURR tutar SAYILMAZ.
# Taban: "CURR tipli 'Curr' elemanında annotation YOK" WARNING'i (sahte payda). DD04L'de
# `CURR` adlı DTEL 0 satır (sahip ölçümü 2026-11-08).
CDS_Y5 = ("@AccessControl.authorizationCheck: #NOT_REQUIRED\n"
          "define view entity ZSD001_I_X as select from zsd001_t_test as t\n{\n"
          "  key t.mandt as Mandt,\n      t.curr  as Curr\n}\n")


def _kos(cmd: list[str], cwd: Path, env_ek: dict | None = None) -> tuple[int, str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if env_ek:
        env.update(env_ek)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(cwd), env=env, timeout=180)
    return r.returncode, (r.stdout or "") + "\n" + (r.stderr or "")


def _var(cikti: str, *parcalar: str) -> bool:
    """Parçaların HEPSİNİ taşıyan TEK bir çıktı satırı var mı (sayıya değil kimliğe bakar)."""
    return any(all(p in satir for p in parcalar) for satir in cikti.splitlines())


def vektorler(kok: Path, tmp: Path) -> list[tuple[str, bool, str]]:
    out: list[tuple[str, bool, str]] = []
    val = kok / VAL_REL

    def ekle(ad, ok, detay):
        out.append((ad, bool(ok), detay))

    def dogrula(kod, *ek):
        p = tmp / f"{kod}.ddl"
        p.write_text(ART[kod], encoding="utf-8")
        return _kos([sys.executable, str(val), str(p), *ek], tmp)

    def blok_yok(o):
        return "[BLOCKER]" not in o

    def uyari_yok(o):
        return "[WARNING]" not in o

    # ── R: Issue #399 yanlış BLOCKER'ları (taban kodda KIRMIZI olmalı) ──
    for tip_arg in ([], ["--type", "table"]):
        e = " (--type table)" if tip_arg else " (auto)"
        rc, o = dogrula("R1", *tip_arg)
        ekle("R1 konwa referansı temiz" + e,
             rc == 0 and blok_yok(o) and uyari_yok(o) and "temiz" in o, f"rc={rc} :: {o[-220:]!r}")
    rc, o = dogrula("R2")
    ekle("R2 Z'li CUKY DTEL'i → WARNING (BLOCKER değil), rc 0",
         rc == 0 and blok_yok(o) and _var(o, "[WARNING]", "C-TBL-CUR-02", "'curr'", "tabloda var ama"),
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("R3")
    ekle("R3 başka tablo ('t001.waers') → aynı-tablo denetimi atlandı + INFO, temiz",
         rc == 0 and blok_yok(o) and uyari_yok(o) and "temiz" in o
         and _var(o, "[INFO]", "C-TBL-CUR-02", "t001.waers"), f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("R4")
    ekle("R4 kendi tablo adı harf-duyarsız (BÜYÜK tanım, karışık başvuru) → temiz, INFO YOK",
         rc == 0 and blok_yok(o) and "[INFO]" not in o and "temiz" in o, f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("R4b")
    ekle("R4b harf-duyarsız aynı tablo + alan yok → BLOCKER korunur",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-02", "'yok' tabloda yok"), f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("R5")
    ekle("R5 yeni CUKY üyesi (konwa) marker denetimine girer → marker eksik BLOCKER",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-04", "'curr'", "marker eksik"),
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("R5b")
    ekle("R5b başvurulmayan sözlük CUKY alanı (konwa) marker'sız → BLOCKER (yalnız sözlük)",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-04", "'ikinci'", "marker eksik"),
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("R6")
    ekle("R6 konws referansı temiz", rc == 0 and blok_yok(o) and uyari_yok(o), f"rc={rc} :: {o[-220:]!r}")
    rc, o = dogrula("R7")
    ekle("R7 kardeş: yerleşik `abap.cuky` alanına başvuru temiz (alan tanınır)",
         rc == 0 and blok_yok(o) and uyari_yok(o) and "temiz" in o, f"rc={rc} :: {o[-220:]!r}")
    rc, o = dogrula("R2b")
    ekle("R2b F1: Z'li CUKY marker'sız → marker eksik BLOCKER",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-04", "'curr'", "marker eksik"),
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("R7b")
    ekle("R7b F1: yerleşik `abap.cuky` marker'sız → marker eksik BLOCKER",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-04", "'curr'", "marker eksik"),
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("R7c")
    ekle("R7c F1: `abap.cuky(5)` marker'lı → temiz",
         rc == 0 and blok_yok(o) and uyari_yok(o) and "temiz" in o, f"rc={rc} :: {o[-220:]!r}")
    rc, o = dogrula("R7d")
    ekle("R7d F1: `abap.cuky( 5 )` marker'sız (boş satır arada) → marker eksik BLOCKER",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-04", "'curr'", "marker eksik"),
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("Q1")
    ekle("Q1 F3: boş tablo kısmı ('.waers') → qualified değil BLOCKER (başka tablo DEĞİL)",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-03", "qualified") and "[INFO]" not in o,
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("B1")
    ekle("B1 F4: blok yorumdaki eski `define table` adı kimliği ele geçirmez → alan yok BLOCKER",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-02", "'yok' tabloda yok") and "[INFO]" not in o,
         f"rc={rc} :: {o[-260:]!r}")

    # ── Y: DEV_CORE #402 — PR #400 bug-gate LOW bulguları (taban f15becb'de KIRMIZI) ──
    rc, o = dogrula("Y1a")
    ekle("Y1a yorumdaki marker SAYILMAZ (waers) → C-TBL-CUR-04 marker BLOCKER",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-04", "'curr'", "marker eksik"),
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("Y1b")
    ekle("Y1b yorumdaki marker SAYILMAZ (Z CUKY) → marker BLOCKER",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-04", "'curr'", "marker eksik"),
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("Y1k")
    ekle("Y1k KONTROL blok yorum arada + gerçek marker → temiz",
         rc == 0 and blok_yok(o) and uyari_yok(o) and "temiz" in o, f"rc={rc} :: {o[-220:]!r}")
    rc, o = dogrula("Y2")
    ekle("Y2 çift nokta ('tablo..curr') → qualified değil BLOCKER, INFO YOK",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-03", "qualified") and "[INFO]" not in o,
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("Y3")
    ekle("Y3 `--` satırındaki `/*` maskeyi açmaz → abap.cuky görünür, temiz",
         rc == 0 and blok_yok(o) and "temiz" in o, f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("Y3k")
    ekle("Y3k KONTROL aynı satır `//` ile → temiz",
         rc == 0 and blok_yok(o) and "temiz" in o, f"rc={rc} :: {o[-220:]!r}")
    rc, o = dogrula("Y3c")
    ekle("Y3c `--` satırındaki `/*` sonrası ihlali GİZLEMEZ → annotation eksik BLOCKER",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-03", "'rate'", "eksik"),
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("Y3b")
    ekle("Y3b satır sonu `--` yorumu alanı düşürmez → annotation eksik BLOCKER",
         rc == 1 and _var(o, "[BLOCKER]", "C-TBL-CUR-03", "'rate'", "eksik"),
         f"rc={rc} :: {o[-260:]!r}")
    p5 = tmp / "Y5.ddls"
    p5.write_text(CDS_Y5, encoding="utf-8")
    rc, o = _kos([sys.executable, str(val), str(p5)], tmp)
    ekle("Y5 EK-3: CDS `t.curr as Curr` (CUKY) CURR tutar SAYILMAZ → uyarı yok, payda 0",
         rc == 0 and uyari_yok(o) and blok_yok(o) and "ÇÖZÜLEBİLEN CURR/QUAN elemanı YOK" in o,
         f"rc={rc} :: {o[-260:]!r}")

    # ── K: korunan BLOCKER'lar ──
    for kod, parcalar, ad in [
        ("K1", ("[BLOCKER]", "C-TBL-CUR-02", "'yok' tabloda yok"), "K1 alan HİÇ yok → BLOCKER"),
        ("K2", ("[BLOCKER]", "C-TBL-CUR-03", "'rate'", "eksik"), "K2 CURR annotation eksik → BLOCKER"),
        ("K3", ("[BLOCKER]", "C-TBL-CUR-03", "qualified"), "K3 qualified değil → BLOCKER"),
        ("K4", ("[BLOCKER]", "C-TBL-CUR-04", "'waers'", "marker eksik"), "K4 CUKY marker eksik → BLOCKER"),
        ("K5", ("[BLOCKER]", "C-TBL-QUAN-02", "'kwmeng'"), "K5 QUAN annotation eksik → BLOCKER"),
    ]:
        rc, o = dogrula(kod)
        ekle(ad, rc == 1 and _var(o, *parcalar), f"rc={rc} :: {o[-220:]!r}")
    rc, o = dogrula("K6")
    ekle("K6 KONTROL tam doğru aynı tablo → temiz, INFO/WARNING YOK",
         rc == 0 and blok_yok(o) and uyari_yok(o) and "[INFO]" not in o and "temiz" in o,
         f"rc={rc} :: {o[-220:]!r}")

    # ── S: 3. BAĞLAM — yapı (define type) ──
    rc, o = dogrula("S1")
    ekle("S1 3.BAĞLAM yapı + konwa → temiz", rc == 0 and blok_yok(o) and uyari_yok(o),
         f"rc={rc} :: {o[-220:]!r}")
    rc, o = dogrula("S2")
    ekle("S2 3.BAĞLAM yapı + alan yok → BLOCKER korunur",
         rc == 1 and _var(o, "[BLOCKER]", "C-STR-CUR-04", "'yok' tabloda yok"), f"rc={rc} :: {o[-220:]!r}")
    rc, o = dogrula("S3")
    ekle("S3 3.BAĞLAM yapı + Z CUKY marker'sız → C-STR-CUR-05 marker BLOCKER",
         rc == 1 and _var(o, "[BLOCKER]", "C-STR-CUR-05", "'curr'", "marker eksik"),
         f"rc={rc} :: {o[-260:]!r}")
    rc, o = dogrula("S4")
    ekle("S4 3.BAĞLAM yapı + Z CUKY marker'lı → C-STR-CUR-04 WARNING, rc 0",
         rc == 0 and blok_yok(o) and _var(o, "[WARNING]", "C-STR-CUR-04", "tabloda var ama"),
         f"rc={rc} :: {o[-260:]!r}")

    # ── P: kardeş tüketici — üretici `classify_unit_kind` ──
    kod_py = ("import sys; sys.path.insert(0, sys.argv[1]); "
              "from utils.ddic_semantics import classify_unit_kind as c; "
              "print('SONUC', c('zsd001_de_amt','konwa'), c('zsd001_de_qty','kmein'), "
              "c('zsd001_de_amt','waers'), c('zsd001_de_qty','konms'))")
    rc, o = _kos([sys.executable, "-I", "-c", kod_py, str(kok)], tmp)
    son = next((s.split()[1:] for s in o.splitlines() if s.startswith("SONUC")), [])
    ekle("P1 üretici: Z tutar + konwa referans → currency",
         son[:1] == ["currency"], f"rc={rc} sonuc={son} :: {o[-160:]!r}")
    ekle("P2 üretici: Z miktar + kmein referans → quantity (sözlükten; uyarısız)",
         son[1:2] == ["quantity"], f"sonuc={son}")
    ekle("P3 KONTROL üretici: Z tutar + waers → currency (eski üye)",
         son[2:3] == ["currency"], f"sonuc={son}")
    ekle("P4 üretici: Z miktar + konms referans → quantity", son[3:4] == ["quantity"], f"sonuc={son}")

    # ── RR: GERÇEK giriş noktası — run_review, geçici kopya + sahte SAP ──
    izole = tmp / "izole"
    if izole.exists():
        shutil.rmtree(izole)
    (izole / "scripts").mkdir(parents=True)
    shutil.copytree(kok / "validators", izole / "scripts" / "validators",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(kok / "utils", izole / "scripts" / "utils",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (izole / "scripts" / "sap_adt_lib.py").write_text(SAHTE_LIB, encoding="utf-8")
    rr = izole / "scripts" / "validators" / "run_review.py"

    def review(gorev, kod):
        p = izole / f"{kod}.ddl"
        p.write_text(ART[kod], encoding="utf-8")
        rc, o = _kos([sys.executable, str(rr), "--task", gorev, "--artifact", str(p), "--json"],
                     izole, {"CLAUDE_PROJECT_DIR": str(izole), "IX_FAKE_SAP": "yok"})
        try:
            veri = json.loads(o[:o.rindex("}") + 1][o.index("{"):])
        except Exception:
            return None, o
        for r in veri.get("results", []):
            if str(r.get("validator", r.get("script", ""))).startswith("check_cds_currency_reference"):
                return r, o
        return None, o

    for kod, gorev, beklenen, ad in [
        ("R1", "table_creation", "PASS", "RR1 run_review table_creation + konwa → currency kapısı PASS"),
        ("S1", "struct_creation", "PASS", "RR2 run_review struct_creation + konwa → currency kapısı PASS"),
        ("R2", "table_creation", "PASS", "RR3 run_review table_creation + Z CUKY → PASS (uyarı stderr'de)"),
        ("K1", "table_creation", "FAIL", "RR4 KONTROL run_review table_creation + alan yok → FAIL"),
    ]:
        r, o = review(gorev, kod)
        durum = (r or {}).get("status")
        ok = durum == beklenen
        hata = str((r or {}).get("stderr", ""))
        if ok and kod == "R2":
            ok = "tabloda var ama" in hata
        elif ok and kod in ("R1", "S1"):
            # PASS tek başına yetmez: sözlük boşluğu da artık WARNING'le PASS verir
            # (ölçüldü: `--mutasyon-sozluk-cuky` altında RR1/RR2 PASS kalıyordu).
            ok = "[WARNING]" not in hata and "[BLOCKER]" not in hata
        ekle(ad, ok, f"status={durum} :: {o[-200:]!r}" if not ok else f"status={durum}")
    return out


# ─────────────────────────── MUTASYONLAR ───────────────────────────
# kip → (dosya, eski, yeni, düşmesi İLAN edilen vektörler — KOŞUMDAN türetildi)
MUTASYONLAR: dict[str, tuple[Path, str, str, tuple[str, ...]]] = {
    "--mutasyon-tip-blocker": (
        VAL_REL,
        "                            # ③ Alan var, tipi sözlükten doğrulanamıyor\n"
        "                            violations.append({\n"
        "                                'severity': 'WARNING',",
        "                            # ③ Alan var, tipi sözlükten doğrulanamıyor\n"
        "                            violations.append({\n"
        "                                'severity': 'BLOCKER',",
        ("R2", "S4", "RR3")),
    "--mutasyon-alan-yok": (
        VAL_REL,
        "                        # ② Alan bu kaynakta hiç yok\n"
        "                        violations.append({\n"
        "                            'severity': 'BLOCKER',",
        "                        # ② Alan bu kaynakta hiç yok\n"
        "                        violations.append({\n"
        "                            'severity': 'WARNING',",
        ("R4b", "B1", "K1", "S2", "RR4")),
    "--mutasyon-baska-tablo": (
        VAL_REL,
        "                    elif tablo_adi and ref_tablo != tablo_adi:\n",
        "                    elif False:\n",
        ("R3",)),
    "--mutasyon-harf": (
        VAL_REL,
        "                    ref_tablo = ref_tablo.strip().lower()\n",
        "                    ref_tablo = ref_tablo.strip()\n",
        ("R4", "R4b")),
    "--mutasyon-ad-harf": (
        VAL_REL,
        "            return tur, m.group(2).lower()\n",
        "            return tur, m.group(2)\n",
        ("R4", "R4b")),
    "--mutasyon-info": (
        VAL_REL,
        "        print(f\"  [INFO] line {v['line']} ({v['check_id']}): {v['message']}\")\n",
        "        pass\n",
        ("R3",)),
    "--mutasyon-info-ihlal": (
        VAL_REL,
        "    violations = [v for v in violations if v['severity'] != 'INFO']\n",
        "    pass\n",
        ("R3",)),
    "--mutasyon-yerlesik": (
        VAL_REL,
        "            tum_alanlar.setdefault(ad, kayit)\n"
        "            cuky_fields.setdefault(ad, kayit)\n",
        "            pass\n",
        ("R7", "R7b", "R7c", "R7d", "Y3", "Y3k")),
    "--mutasyon-marker-yerel": (
        VAL_REL,
        "            denetlenecek.append(tum_alanlar[ad])\n",
        "            pass\n",
        ("R2b", "R7b", "R7d", "Y1b", "S3")),
    "--mutasyon-yerlesik-marker": (
        VAL_REL,
        "                     'annotations': _ustteki_annotasyonlar(satirlar, i)}\n",
        "                     'annotations': []}\n",
        ("R7", "R7c", "Y3", "Y3k")),
    "--mutasyon-bos-parca": (
        VAL_REL,
        "                    if not ad_gecerli_mi(ref_tablo) or not ad_gecerli_mi(ref_field):\n",
        "                    if False:\n",
        ("Q1", "Y2")),
    "--mutasyon-blok-yorum": (
        VAL_REL,
        "    for raw_line in blok_yorumu_maskele(text).splitlines():\n"
        "        m = _KAYNAK_ADI_RE.match(yorumu_kirp(raw_line))\n",
        "    for raw_line in text.splitlines():\n"
        "        m = _KAYNAK_ADI_RE.match(yorumu_kirp(raw_line))\n",
        ("B1",)),
    "--mutasyon-id-yapi": (
        VAL_REL,
        "    id_referans = 'C-STR-CUR-04' if yapi_mi else 'C-TBL-CUR-02'\n",
        "    id_referans = 'C-TBL-CUR-02'\n",
        ("S2", "S4")),
    "--mutasyon-id-marker": (
        VAL_REL,
        "    id_marker = 'C-STR-CUR-05' if yapi_mi else 'C-TBL-CUR-04'\n",
        "    id_marker = 'C-TBL-CUR-04'\n",
        ("S3",)),
    "--mutasyon-sozluk-cuky": (
        DS_REL,
        "CUKY_DTELS = {'waers', 'waerk', 'hwaer', 'konwa', 'konws'}\n",
        "CUKY_DTELS = {'waers', 'waerk', 'hwaer'}\n",
        ("R1 konwa referansı temiz (auto)", "R1 konwa referansı temiz (--type table)",
         "R4", "R5b", "R6", "S1", "P1", "RR1", "RR2")),
    "--mutasyon-sozluk-unit": (
        DS_REL,
        "'unit', 'kmein', 'konms'}\n",
        "'unit'}\n",
        ("P2", "P4")),
    # ── DEV_CORE #402 ──
    "--mutasyon-y1-maske": (
        VAL_REL,
        "    lines = (blok_yorumu_maskele(text) if src_type == 'table' else text).splitlines()\n",
        "    lines = text.splitlines()\n",
        ("Y1a", "Y1b")),
    "--mutasyon-y3-maske": (
        VAL_REL,
        "        elif (c == '/' and i + 1 < n and text[i + 1] == '/') or (\n"
        "                c == '-' and i + 1 < n and text[i + 1] == '-'):\n",
        "        elif (c == '/' and i + 1 < n and text[i + 1] == '/') or (\n"
        "                False):\n",
        ("Y3c",)),
    "--mutasyon-y3-kirp": (
        VAL_REL,
        "        elif c == '-' and i + 1 < n and line[i + 1] == '-':\n",
        "        elif False:\n",
        ("Y3b",)),
    "--mutasyon-sozluk-curr": (
        DS_REL,
        "    'price', 'amount',\n",
        "    'price', 'curr', 'amount',\n",
        ("Y5",)),
}


def _kod(ad: str) -> str:
    return ad.split(" ")[0]


def _dusmus_mu(beklenen: str, dusen_adlar: list[str]) -> bool:
    if " " in beklenen:
        return beklenen in dusen_adlar
    return beklenen in {_kod(a) for a in dusen_adlar}


def mutasyon_kos(kip: str) -> int:
    dosya, eski, yeni, beklenen = MUTASYONLAR[kip]
    kaynak = (SCRIPTS / dosya).read_text(encoding="utf-8")
    n = kaynak.count(eski)
    if n != 1:
        print(f"[KURULAMADI] {kip}: çapa {n} kez geçiyor (1 bekleniyor) — {dosya}")
        return 3
    tmp = Path(tempfile.mkdtemp(prefix="cdsref_mut_"))
    try:
        kok = tmp / "scripts"
        kok.mkdir()
        shutil.copytree(SCRIPTS / "validators", kok / "validators",
                        ignore=shutil.ignore_patterns("__pycache__", "_mutant_*"))
        shutil.copytree(SCRIPTS / "utils", kok / "utils",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (kok / dosya).write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8", newline="")
        is_tmp = tmp / "is"
        is_tmp.mkdir()
        sonuc = vektorler(kok, is_tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    dusen = [ad for ad, ok, _ in sonuc if not ok]
    gecen = len(sonuc) - len(dusen)
    eksik = [b for b in beklenen if not _dusmus_mu(b, dusen)]
    # DEV_CORE #402 Y4: FAZLA düşen de SAPMA'dır — yalnız eksik bakılınca ilan kümeleri
    # koşumdan sapmıştı (ölçüldü: alan-yok B1'i, tip-blocker S4'ü, yerlesik 5 vektörü
    # ilan etmeden düşürüyordu) ve B96 reçetesi bu sapmayı taşıyordu.
    ilan_kodlari = {_kod(b) for b in beklenen}
    fazla = sorted({_kod(a) for a in dusen} - ilan_kodlari)
    print(f"cds_curr_referans_tipi {kip}: {gecen}/{len(sonuc)}")
    print(f"  düşen: {[_kod(a) for a in dusen]}")
    print(f"  ilan edilen: {list(beklenen)}")
    if eksik:
        print(f"[SAPMA] ilan edilip düşmeyen: {eksik}")
    if fazla:
        print(f"[SAPMA] ilan edilmeden düşen: {fazla}")
    if eksik or fazla:
        return 2
    return 1


def main() -> int:
    kipler = [a for a in sys.argv[1:] if a.startswith("--mutasyon")]
    if kipler:
        if len(kipler) != 1 or kipler[0] not in MUTASYONLAR:
            print(f"[KULLANIM] bilinmeyen/çoklu kip: {kipler}; geçerli: {sorted(MUTASYONLAR)}")
            return 3
        return mutasyon_kos(kipler[0])
    kok = SCRIPTS
    if "--kok" in sys.argv:
        kok = Path(sys.argv[sys.argv.index("--kok") + 1]).resolve()
    tmp = Path(tempfile.mkdtemp(prefix="cdsref_"))
    try:
        sonuc = vektorler(kok, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         {detay}"))
    print(f"\ncds_curr_referans_tipi: {gecen}/{len(sonuc)}")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    raise SystemExit(main())
