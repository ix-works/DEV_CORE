---
name: feedback_m-table-esnek-kolon-dar-ekranda-sifir-px
description: "sap.m.Table (fixedLayout) içinde genişliksiz 'esnek' kolon, sabit kolon toplamı tabloyu aşınca 0 px'e düşer — 'taşmayı esnek kolonla çöz' düzeltmesi dar ekranda kolonu yok eder; ayrıca width 100% + sapUiSmallMarginBeginEnd tabloyu 1rem taşırır"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 8865df6b-2e94-44e8-8952-84b42fc53742
  modified: 2026-10-16T06:40:42.608Z
---

Dialog içindeki `sap.m.Table`'da son kolon pencere dışına taşıyordu. İlk düzeltme bir kolonun `width`'ini kaldırıp
"esnek" yapmaktı; 1600 ve 1280 px'te iyi göründü. Bug-gate genişlik merdiveninde ölçtü: sabit kolon toplamı tablo
genişliğini aşınca (≤1180 px) esnek kolon **0 px**'e düştü — metin harf harf kırıldı, satır ~225 px uzadı.
Eski hâl (hepsi sabit) yalnız yatay kaydırıyordu, kolon kaybetmiyordu ⇒ düzeltme regresyondu.

İkinci gizli neden: `width` varsayılanı 100% olan tabloya `sapUiSmallMarginBeginEnd` verilince tablo kabından
**1rem taşar** (ölçüm: tablo 176–1456, pencere 160–1440). Çare `width="calc(100% - 2rem)"` (CSSSize calc kabul eder).

**Vaka (bir projede, 2026-10-16, iki diyalog penceresi):** kontrol grubu origin/main fragment'ı
Playwright route ile değiştirilerek ölçüldü; çözüm: bütün kolonlar sabit, toplam ≤ (contentWidth − 2rem), tablo
`calc(100% - 2rem)` ⇒ 1366+ px tam sığar, daha darda kaydırma, kırpılan hücre 0.

**Why:** fixed table layout, sabit genişlikleri korur; açığı yalnız genişliksiz kolondan keser.
**How to apply:** m.Table taşmasını esnek kolonla çözme; sabit toplamı küçült ya da `minScreenWidth`/`demandPopin`
kullan. Genişlik düzeltmesini tek ekranda değil **merdivenle** ölç (1600/1366/1280/1180/1093/1024; Windows %125
ölçekte 1366 ekran ≈ 1093 CSS px). Ölçüm: `th` getBoundingClientRect genişliği + dialog section scrollWidth/clientWidth.

Son-doğrulama: 2026-10-16
Applies-to: freestyle UI5 1.120 sap.m.Table (Dialog içinde, fixedLayout varsayılan)
prior-art: yok (memory rg "fixedLayout|esnek kolon|calc(100%" 2026-10-16 = 0)
İlgili: [[feedback_duzeltme-turu-kendi-regresyonunu-uretir]]
