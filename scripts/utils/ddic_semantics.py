#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DDIC semantik sınıflandırma — CURR/QUAN/CUKY/UNIT DTEL sözlüğü (TEK KAYNAK).

NEDEN AYRI MODÜL (B-13, 2026-08-19): bu sözlük iki tarafça kullanılır ve ikisinin
AYNI cevabı vermesi zorunludur:

  - ÜRETİCİ  `scripts/populate_tables.py`  → DDL'e @Semantics annotation'ını YAZAR
  - DENETÇİ  `scripts/validators/check_cds_currency_reference.py` → aynı annotation'ı
             BLOCKER seviyesinde DOĞRULAR (C-TBL-CUR-02/03/04, C-TBL-QUAN-01/02,
             C-STR-CUR-*, C-STR-UNIT-*, C-CDS-CUR-*, C-RAP-VE-07 — ADR 0019)

Sözlük iki yerde yaşarsa biri bayatlar ve üretici, denetçinin BLOCKER diyeceği DDL'i
üretir (B-13'ün ta kendisi: `netwr` alanına unitOfMeasure yazılıyordu, denetçi ise
`netwr`'ı CURR sayıp amount.currencyCode bekliyordu). Bu yüzden sözlük TEK yerdedir.

⚠ Sözlük genişletilebilir ama KISALTILAMAZ: bir DTEL'i çıkarmak denetçinin o alanı
görmezden gelmesine yol açar (sessiz gevşetme).
"""

# ---------------------------------------------------------------------------
# DTEL sözlükleri — kaynak: check_cds_currency_reference.py (B-13'te buraya taşındı)
# ---------------------------------------------------------------------------

# Built-in CURR DTEL'leri (genişletilebilir)
# ⚠ GEVŞETME (DEV_CORE #402 EK-3, 2026-11-08, sahip onaylı): `curr` ÇIKARILDI — yukarıdaki
# "kısaltılamaz" kuralının bilinçli istisnası. Ölçüm: DD04L (S/4 private DEV, salt-okuma)
# `ROLLNAME='CURR'` → 0 satır ⇒ DTEL yolunda hiçbir alanla eşleşemezdi; tek etkisi CDS kolon-adı
# sezgisindeydi (`_eleman_tipi`): `curr as Curr` (para BİRİMİ, CUKY) elemanı tutar sayılıp
# "ölçülen CURR" paydasını şişiriyordu. Aynı ölçümde PRICE = CURR(15) (kalır), RATE = DEC(9)
# (eklenmez). BİLİNEN SINIR: `amount` DD04L'de NUMC(9) (tutar DEĞİL) ve QUAN_DTELS'teki `quan`
# DD04L'de 0 satır — ikisi de sözlükte DURUYOR (gözlenmiş hata yok; çıkarmak ad sezgisini gevşetir).
CURR_DTELS = {
    'netwr', 'mwsbp', 'kbetr', 'dmbtr', 'wrbtr', 'kzwi1', 'kzwi2',
    'kzwi3', 'kzwi4', 'kzwi5', 'kzwi6', 'sklfr', 'klfre', 'lfrec',
    'price', 'amount',
}

# Built-in QUAN DTEL'leri
QUAN_DTELS = {
    'menge_d', 'kwmeng', 'kwmen', 'lfimg', 'lfime', 'wmeng', 'bmeng',
    'menge', 'volum', 'ntgew', 'brgew', 'quan',
}

# Built-in CUKY/UNIT DTEL'leri
# 2026-11-08 (DEV_CORE Issue #399): koşul kaydı DTEL'leri eklendi — `konwa`/`konws`
# (CUKY) · `kmein`/`konms` (UNIT). Kaynak: Issue #399 ölçümü (S/4 DEV, 2026-11-08,
# DD04L 9 adlık sorgu → 8 aktif DTEL; standart KONP `KBETR` → `RV13A-KONWA`).
# Eksiklikleri `konwa` tipli para birimi alanına başvuran tutarı "referans tabloda
# yok" BLOCKER'ına düşürüyordu (yanlış pozitif).
# `lager`: aynı ölçümde aktif DTEL olarak DÖNMEDİ; bu turda bağımsız ölçülemediği ve
# başka sürümde var olup olmadığı bilinmediği için DOKUNULMADI (yukarıdaki kural:
# sözlük kısaltılamaz). Var olmayan bir DTEL'le hiçbir alan aktive olamaz, yani
# üyeliği bugün hiçbir kararı değiştirmez.
CUKY_DTELS = {'waers', 'waerk', 'hwaer', 'konwa', 'konws'}
UNIT_DTELS = {'meins', 'vrkme', 'gewei', 'voleh', 'lager', 'unit', 'kmein', 'konms'}


# ---------------------------------------------------------------------------
# unit_kind sözleşmesi (populate_tables.py CSV 10. kolonu)
# ---------------------------------------------------------------------------

UNIT_KIND_QUANTITY = 'quantity'
UNIT_KIND_CURRENCY = 'currency'
VALID_UNIT_KINDS = (UNIT_KIND_CURRENCY, UNIT_KIND_QUANTITY)


class UnitKindError(ValueError):
    """CSV'de geçersiz unit_kind değeri — SESSİZ varsayılana düşmek YASAK."""


def normalize_unit_kind(raw):
    """CSV'den gelen ham `unit_kind` değerini normalize eder.

    Dönüş:
        None                 — hücre boş (→ çağıran otomatik çıkarıma düşer)
        'quantity'/'currency'— açık değer

    Hata:
        UnitKindError — tanınmayan değer. FAIL-CLOSED: yazım hatası ('curency',
        'CURR', 'para') sessizce quantity'ye düşerse B-13 aynen geri gelir; bu
        yüzden hata YÜKSELTİLİR, varsayılana düşülmez.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = s.casefold()
    # Tam eşitlik — 'curr' ya da 'cur' gibi kısaltmalar KABUL EDİLMEZ (belirsiz).
    if s in VALID_UNIT_KINDS:
        return s
    raise UnitKindError(
        "gecersiz unit_kind: %r (gecerli: %s veya bos birak)"
        % (raw, '/'.join(VALID_UNIT_KINDS))
    )


def classify_unit_kind(value_dtel, ref_dtel=None):
    """DTEL adlarından unit_kind çıkarır — AÇIK unit_kind YOKSA kullanılır.

    İki bağımsız sinyal, sırayla:
      1) Tutar/miktar alanının DTEL'i   (netwr → currency, menge_d → quantity)
      2) Referans alanın DTEL'i         (waers → currency, vrkme → quantity)

    (2) gereklidir çünkü tutar/miktar alanı Z'li özel DTEL olabilir
    (örn. ZSD001_E_ORDQTY) ama referans alan neredeyse daima standart bir
    CUKY/UNIT DTEL'idir.

    Dönüş: 'currency' | 'quantity' | None (ikisi de tanımıyorsa → çağıran karar verir)

    ⚠ Alan ADINA bakılmaz, yalnız DTEL'e bakılır. 'WAERS adlı alan para birimidir'
    tarzı ad tahmini YASAK (ad serbesttir, DTEL değildir).
    """
    v = (value_dtel or '').strip().casefold()
    if v in CURR_DTELS:
        return UNIT_KIND_CURRENCY
    if v in QUAN_DTELS:
        return UNIT_KIND_QUANTITY

    r = (ref_dtel or '').strip().casefold()
    if r in CUKY_DTELS:
        return UNIT_KIND_CURRENCY
    if r in UNIT_DTELS:
        return UNIT_KIND_QUANTITY

    return None
