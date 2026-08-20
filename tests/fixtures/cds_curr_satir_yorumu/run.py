#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cds_curr_satir_yorumu — check_cds_currency_reference satır-sonu `//` yorumu (V1).

VAKA (2026-08-01 bug-avı kuyruk-kaydı V1): tablo alan deseni `^...;\\s*$` ile ANCHOR'lı.
Gerçek DDL'de yaygın olan `netwr : netwr;  // tutar` satırı desene UYMAZ → alan hiç
kaydedilmez → eksik CURR-annotation ihlali SESSİZCE kaybolur. Gate yeşil yanar; "0 alan
gördüm" ile "0 ihlal var" ayırt edilemez. Bu, run_all'ın tarihsel "dizin-yok → 0 dosya →
GATE YEŞİL" sınıfının (2026-07-09, d2d326d) satır-içi ikizidir.

İKİNCİ YÜZ (aynı kök): annotation DEĞERİ de yorumla kirleniyordu —
`@Semantics.amount.currencyCode : 'ztab.waers'  // para` → değer `ztab.waers' // para` →
`split('.')[-1]` = `waers' // para` → "referans CUKY tabloda yok" YANLIŞ-POZİTİF'i.
Yani aynı kusur bir yönde SESSİZ-KAÇIRMA, diğer yönde SAHTE-BLOCKER üretiyordu.

TASARIM (howto-infra-fix D2): bu fixture MUTASYON-DOSTUDUR — fix'ten ÖNCEKİ sürüme karşı
koşulduğunda ÇÖKMEZ, kaç vektörün düştüğünü ÖLÇER (`_cagir` sarmalayıcısı + `yorumu_kirp`
yokluğunda vektörü FAIL sayar, AttributeError ile koşucuyu öldürmez).

⚠ KONTROL GRUBU + FP ÇAPALARI OMURGADIR:
  - K1/K2 = yorumSUZ ihlaller: harness'ın gerçekten ölçtüğünün kanıtı (bunlar eski kodda
    da FAIL verir; kaldırılırsa "hepsi kaçıyordu" iddiası ölçülemez hâle gelir).
  - N1..N5 = temiz vektörler: kırpma AŞIRI-SIKI olursa (ör. tırnak-içi `http://`)
    bunlar düşer. Özellikle N4 (`'http://...'`) kaba `split("//")` çözümünün mezar taşıdır.

Kullanım: python tests/fixtures/cds_curr_satir_yorumu/run.py   → exit 0 = tüm vektörler OK
"""
from __future__ import annotations

import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "validators"))

import check_cds_currency_reference as V  # noqa: E402

SONUC: list[tuple[bool, str]] = []


def kaydet(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


def _cagir(fn_adi: str, *a):
    """Mutasyon-dostu çağrı: eski sürümde fonksiyon/imza değişikse ÖLÇÜLEN sonuca çevir.

    Çökme ≠ FAIL: eski koda karşı koşulduğunda traceback yerine `("HATA", mesaj)` döner,
    çağıran vektörü FAIL sayar ve hangi vektörün ayırt edici olduğu görünür kalır.
    """
    fn = getattr(V, fn_adi, None)
    if fn is None:
        return ("YOK", fn_adi)
    try:
        return ("OK", fn(*a))
    except Exception as e:  # noqa: BLE001
        return ("HATA", f"{type(e).__name__}: {e}")


def ihlaller(text: str, tip: str) -> tuple[str, object]:
    return _cagir("check_table" if tip == "table" else "check_cds", text)


def blocker_sayisi(sonuc: tuple[str, object]) -> int | None:
    """BLOCKER sayısı; ölçülemezse None (çökme/eksik fonksiyon)."""
    if sonuc[0] != "OK" or not isinstance(sonuc[1], list):
        return None
    return sum(1 for v in sonuc[1] if v.get("severity") == "BLOCKER")


def uyari_sayisi(sonuc: tuple[str, object], check_id: str | None = None) -> int | None:
    """WARNING sayısı; `check_id` verilirse YALNIZ o kontrolünkiler.

    ⚠ 2026-08-20: filtre EKLENDİ çünkü sayaç iki AYRI kontrolü aynı torbaya atıyordu.
    E1'in ölçtüğü değişmez *"yorumlanmış annotation'ın DEĞERİ üzerinden BİÇİM uyarısı
    üretilmesin"* (C-CDS-CUR-02) idi — kardeş yorumu bunu söylüyor: *"aynı geçersiz
    değer YORUMSUZ → WARNING üretilMELİ"*. Aynı gün eklenen EKSİKLİK denetimi
    (C-CDS-CUR-05) ise yorumlanmış girdide **haklı olarak** uyarı üretir: annotation
    yorumdaysa alan GERÇEKTEN annotation'sızdır. Filtresiz sayaç bu ikisini ayırt
    edemediği için E1 sahte-KIRMIZI verdi. Ölçüt GEVŞETİLMEDİ — KESKİNLEŞTİRİLDİ;
    E3 aynı girdide eksiklik uyarısının VARLIĞINI ayrıca çivilliyor.
    """
    if sonuc[0] != "OK" or not isinstance(sonuc[1], list):
        return None
    return sum(1 for v in sonuc[1]
               if v.get("severity") == "WARNING"
               and (check_id is None or v.get("check_id") == check_id))


def bulgu_var(sonuc: tuple[str, object], *parcalar: str) -> bool | None:
    """Mesajı verilen parçaların HEPSİNİ içeren bir BLOCKER var mı?

    ⚠ NEDEN "BLOCKER>=1" YETMİYOR (bu fixture'ın ilk sürümünde yaşandı): P1/P2 vektörleri
    eski koda karşı da "BLOCKER=1" veriyordu — ama BAŞKA bir alandan, başka gerekçeyle
    (kaçan `netwr` yerine `waers`'in marker'ı). Sayıya bakan bir iddia "yakalandı" der ve
    mutasyon ayırt ediciliğini kaybeder. **PASS ≠ baktı**: hangi ihlalin basıldığı sorulur.
    """
    if sonuc[0] != "OK" or not isinstance(sonuc[1], list):
        return None
    for v in sonuc[1]:
        if v.get("severity") != "BLOCKER":
            continue
        blob = f"{v.get('check_id', '')} {v.get('message', '')}"
        if all(p in blob for p in parcalar):
            return True
    return False


# ─────────────────────────── TABLO GÖVDELERİ ───────────────────────────
# Gerçek şekil bir canlı `*.tabl.ddl` tablo kaynağından örneklendi (alan sırası, `key
# mandt`, hizalı `:` ve annotation-üstte konvansiyonu).

BASLIK = """@EndUserText.label : 'Test Tablosu'
@AbapCatalog.tableCategory : #TRANSPARENT
define table zsd001_t_test {
"""
KUYRUK = "\n}\n"


def tablo(govde: str) -> str:
    return BASLIK + govde + KUYRUK


# P1 — CURR alanı satır-sonu yorumlu, annotation YOK → BLOCKER olmalı (eski kod: SESSİZ)
P1 = tablo("""  key mandt : mandt not null;
  netwr : netwr;  // toplam tutar
  waers : waers;
""")

# P2 — CUKY alanı satır-sonu yorumlu, `currencyCode : true` marker YOK → BLOCKER
P2 = tablo("""  key mandt : mandt not null;
  @Semantics.amount.currencyCode : 'zsd001_t_test.waers'
  netwr : netwr;
  waers : waers;  // para birimi
""")

# P3 — QUAN alanı satır-sonu yorumlu, unitOfMeasure YOK → BLOCKER
P3 = tablo("""  key mandt : mandt not null;
  kwmeng : kwmeng;   // siparis miktari
  meins : meins;
""")

# K1 (KONTROL GRUBU) — AYNI ihlal, YORUMSUZ → eski kodda da BLOCKER (harness ölçüyor mu?)
K1 = tablo("""  key mandt : mandt not null;
  netwr : netwr;
  waers : waers;
""")

# K2 (KONTROL GRUBU) — yorumsuz QUAN ihlali
K2 = tablo("""  key mandt : mandt not null;
  kwmeng : kwmeng;
  meins : meins;
""")

# N1 (FP ÇAPASI) — yorumsuz ve TAM DOĞRU → 0 BLOCKER
N1 = tablo("""  key mandt : mandt not null;
  @Semantics.amount.currencyCode : 'zsd001_t_test.waers'
  netwr : netwr;
  @Semantics.currencyCode : true
  waers : waers;
""")

# N2 (FP ÇAPASI) — HER SATIRI yorumlu ama TAM DOĞRU → 0 BLOCKER
#   Eski kod burada da 0 verir (hiçbir alanı görmediği için) — ayırt edici DEĞİL,
#   fakat yeni kodun aşırı-sıkılaşmadığının kanıtı: alanları GÖRÜP temiz demeli.
N2 = tablo("""  key mandt : mandt not null;   // istemci
  @Semantics.amount.currencyCode : 'zsd001_t_test.waers'
  netwr : netwr;  // tutar
  @Semantics.currencyCode : true
  waers : waers;  // para birimi
""")

# N3 (FP ÇAPASI — SAHTE-BLOCKER yönü) — annotation DEĞERİ satır-sonu yorumlu.
#   Eski kod: değer `zsd001_t_test.waers' // ...` olarak okunur → CUKY "tabloda yok" FP.
N3 = tablo("""  key mandt : mandt not null;
  @Semantics.amount.currencyCode : 'zsd001_t_test.waers'  // referans para birimi
  netwr : netwr;
  @Semantics.currencyCode : true
  waers : waers;
""")

# N4 (FP ÇAPASI — kaba `split("//")` mezar taşı) — TIRNAK İÇİ `//`.
#   Kırpma tırnak-duyarlı değilse label bozulur; daha kötüsü değer kırpılırsa
#   qualified referans parçalanıp SAHTE-BLOCKER doğar.
N4 = """@EndUserText.label : 'Bkz: http://intranet/doc//spec'
@AbapCatalog.tableCategory : #TRANSPARENT
define table zsd001_t_test {
  key mandt : mandt not null;
  @Semantics.amount.currencyCode : 'zsd001_t_test.waers'
  netwr : netwr;
  @Semantics.currencyCode : true
  waers : waers;
}
"""

# N5 (FP ÇAPASI) — yorum-SATIRI (tam satır `//`) pending annotation'ı DÜŞÜRMEMELİ.
N5 = tablo("""  key mandt : mandt not null;
  @Semantics.amount.currencyCode : 'zsd001_t_test.waers'
  // asagidaki alan toplam tutari tutar
  netwr : netwr;
  @Semantics.currencyCode : true
  waers : waers;
""")

# ─────────── 3. BAĞLAM (görev-DIŞI): CDS dalı + yorumlanmış annotation ───────────
# Görev V1'i "tablo alan regex'i" olarak tarifliyordu; kök sınıf (yorum kırpılmıyor)
# CDS dalını da vurur: YORUMLANMIŞ (ölü) bir annotation canlı kural sanılıp WARNING üretir.
C_OLU = """define view entity ZSD001_I_TEST as select from zsd001_t_test {
  // @Semantics.amount.currencyCode : '1_gecersiz'
  netwr as Netwr,
  waers as Waerk
}
"""
# C_CANLI (KONTROL GRUBU) — aynı geçersiz değer YORUMSUZ → WARNING üretilMELİ.
C_CANLI = """define view entity ZSD001_I_TEST as select from zsd001_t_test {
  @Semantics.amount.currencyCode : '1_gecersiz'
  netwr as Netwr,
  waers as Waerk
}
"""


def main() -> int:
    # ── A. Yapısal çapa: yorumu_kirp davranışı (birim) ──
    for girdi, beklenen, ad in [
        ("  netwr : netwr;  // tutar", "  netwr : netwr;  ", "A1 kod+yorum"),
        ("  netwr : netwr;", "  netwr : netwr;", "A2 yorumsuz DEĞİŞMEZ"),
        ("@X : 'http://a//b'", "@X : 'http://a//b'", "A3 TIRNAK İÇİ // korunur"),
        ("  // tamamen yorum", "  ", "A4 yorum-satırı boşalır"),
        ('@X : "http://a" // not', '@X : "http://a" ', "A5 çift tırnak + yorum"),
    ]:
        r = _cagir("yorumu_kirp", girdi)
        ok = r[0] == "OK" and r[1] == beklenen
        kaydet(ok, ad, "" if ok else f"beklenen {beklenen!r}, gelen {r!r}")

    # ── B. POZİTİF: yorumlu satırdaki ihlaller YAKALANMALI ──
    #    İddia SAYIYA değil BULGUNUN KİMLİĞİNE bakar (bkz. `bulgu_var` gerekçesi).
    for text, parcalar, ad in [
        (P1, ("C-TBL-CUR-03", "'netwr'", "eksik"),
         "P1 CURR 'netwr' annotation eksik (satır yorumlu)"),
        (P2, ("C-TBL-CUR-04", "'waers'", "marker eksik"),
         "P2 CUKY 'waers' marker eksik (satır yorumlu)"),
        (P3, ("C-TBL-QUAN-02", "'kwmeng'", "eksik"),
         "P3 QUAN 'kwmeng' annotation eksik (satır yorumlu)"),
    ]:
        s = ihlaller(text, "table")
        r = bulgu_var(s, *parcalar)
        kaydet(r is True, ad, f"bulgu={r} (parçalar: {', '.join(parcalar)})")

    # ── C. KONTROL GRUBU: aynı ihlaller yorumsuz da yakalanıyor mu (harness sağlam mı) ──
    for text, parcalar, ad in [
        (K1, ("C-TBL-CUR-03", "'netwr'"), "K1 KONTROL yorumsuz CURR ihlali"),
        (K2, ("C-TBL-QUAN-02", "'kwmeng'"), "K2 KONTROL yorumsuz QUAN ihlali"),
    ]:
        r = bulgu_var(ihlaller(text, "table"), *parcalar)
        kaydet(r is True, ad, f"bulgu={r}")

    # ── D. FP ÇAPALARI: temiz girdi BLOCKER üretmemeli ──
    for text, ad in [(N1, "N1 FP temiz+yorumsuz"),
                     (N2, "N2 FP temiz+her satır yorumlu"),
                     (N3, "N3 FP annotation DEĞERİ yorumlu (sahte-BLOCKER yönü)"),
                     (N4, "N4 FP tırnak-içi // (kaba split mezar taşı)"),
                     (N5, "N5 FP yorum-satırı pending annotation'ı düşürmez")]:
        s = ihlaller(text, "table")
        n = blocker_sayisi(s)
        ok = n == 0
        kaydet(ok, ad, f"BLOCKER={n} (0 bekleniyor)"
               + ("" if n == 0 or n is None else f" :: {s[1]}"))

    # ── E. 3. BAĞLAM (görev-dışı): CDS dalı ──
    # ⚠ İkisi de C-CDS-CUR-02 (BİÇİM) ile ölçülür — bu vektör çiftinin değişmezi
    # *"ölü (yorumlanmış) annotation'ın DEĞERİ üzerinden biçim uyarısı üretme"*dir.
    w_olu = uyari_sayisi(ihlaller(C_OLU, "cds"), "C-CDS-CUR-02")
    kaydet(w_olu == 0, "E1 3.BAĞLAM CDS: YORUMLANMIŞ annotation BİÇİM uyarısı üretmez",
           f"C-CDS-CUR-02 WARNING={w_olu} (0 bekleniyor)")
    w_canli = uyari_sayisi(ihlaller(C_CANLI, "cds"), "C-CDS-CUR-02")
    kaydet(w_canli is not None and w_canli >= 1,
           "E2 3.BAĞLAM KONTROL: canlı geçersiz annotation BİÇİM uyarısı üretir",
           f"C-CDS-CUR-02 WARNING={w_canli} (>=1 bekleniyor)")
    # E3 (2026-08-20, DERİNLİK): annotation YORUMDAYSA alan gerçekten annotation'sızdır
    # ⇒ EKSİKLİK uyarısı ÜRETİLMELİ. E1 ile aynı girdi, KARŞIT soru — ikisi birlikte
    # "hangi kontrol ne zaman konuşur"u çivilliyor (E1 tek başına kalırsa, eksiklik
    # denetimini tümden söken bir mutasyon bu dosyada YEŞİL kalırdı).
    w_eksik = uyari_sayisi(ihlaller(C_OLU, "cds"), "C-CDS-CUR-05")
    kaydet(w_eksik is not None and w_eksik >= 1,
           "E3 3.BAĞLAM DERİNLİK: yorumlanmış annotation = EKSİK annotation (C-CDS-CUR-05)",
           f"C-CDS-CUR-05 WARNING={w_eksik} (>=1 bekleniyor)")
    # E4 FP çapası: annotation CANLI ve doğru yerdeyse eksiklik uyarısı ÇIKMAMALI
    w_fp = uyari_sayisi(ihlaller(C_CANLI, "cds"), "C-CDS-CUR-05")
    kaydet(w_fp == 0,
           "E4 FP çapası: canlı annotation varken EKSİKLİK uyarısı YOK",
           f"C-CDS-CUR-05 WARNING={w_fp} (0 bekleniyor)")

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\ncds_curr_satir_yorumu: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
