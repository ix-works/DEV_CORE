---
name: feedback_sap-standart-kur-cevrimi-ters-yon-kaydina-sessizce-duser
description: SAP standart kur çevrimi (CL_EXCHANGE_RATES / CONVERT_TO_LOCAL_CURRENCY) istenen yönde kayıt yoksa TCURV-XINVR=X ile ters yön kaydının tersine SESSİZCE düşer — yön garantisi istiyorsan I_ExchangeRateRawData varlık ön denetimi
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: fa3047bd-a7ce-490e-a61f-6b3171d2ff98
  modified: 2026-10-14T20:10:07.947Z
---

SAP standart kur çevrimi (`CL_EXCHANGE_RATES=>convert_to_local_currency`, FM `CONVERT_TO_LOCAL_CURRENCY` sarmalı) istenen yönde (F→H) `geçerlilik ≤ tarih` satırı bulamazsa ve kur tipinde **TCURV-XINVR = X** ise **ters yöndeki (H→F) en son satırın tersini** döndürür — hata/uyarı yok. Dönüş değeri hangi satırdan geldiğini söylemez.

**Why:** Bir iş kuralı "kur daima yabancı→yerel yönünde okunur, ters yön kaydı dikkate alınmaz" diyorsa standart çağrı bu kuralı **sessizce** çiğner; iki yön kaydı birbirinin tam tersi olmadığında (ölçülen örnek: USD→EUR 0,85110 · EUR→USD 1,17500, çarpım 1,0000425) sonuç fark eder. Bir projede doküman (TS) kapısında yakalandı, kod yazılmadan.

**How to apply:** Yön garantisi gereken her çağrıdan önce `SELECT SINGLE` ile `I_ExchangeRateRawData` (RELEASED, `#NOT_REQUIRED`, genel tamponlu) üzerinde istenen yönde `ValidityStartDate <= d AND ExchangeRate <> 0` satırı var mı bak; yoksa standardı çağırma, "kur yok" say. Ön denetim kur **değerini** okumaz, yalnız varlığı — seçim kuralı standartta kalır. Eşdeğerlik ön koşulu: TCURV-BWAER boş ya da yerel PB, TCURF-ABWCT boş, TCURV-GKUZU/BKUZU boş (aksi hâlde standart başka satır okur). İki yabancı PB arasında da tek yön sabitle, ters 1 ÷ kur.

**Kanıt sınırı:** davranış kaynak okumasıyla (LSCUNF01 `daten_bereitstellen`, LSCUNU03) kuruldu; koşu ile ölçüm yazıldığı tarihte yoktu (build turuna bırakıldı). Fiyatlandırmadaki iz tutarlı: KKURS doğrudan yön satırını, daha yeni ters satırlara rağmen almış.

prior-art: yok (memory'de XINVR / ters yön aranıp bulunmadı, 2026-10-14).
Son-doğrulama: 2026-10-14 · Applies-to: s4_private / ecc — standart kur çevrimini çağıran her rapor/hesap
