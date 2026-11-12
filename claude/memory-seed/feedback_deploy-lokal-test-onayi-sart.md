---
name: feedback_deploy-lokal-test-onayi-sart
description: "SAP'e (BSP/UI) deploy ETME — kullanıcı lokal testi \"OK\" demeden; deploy kullanıcı-kapılı"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cbd3c1b7-21b6-433c-9916-4307c1ea6587
---

Kullanıcı kuralı (2026-06-19): **Lokal test bitmeden SAP'e deploy etme.** Build → bug-gate → **lokal sun** → kullanıcı test eder → "OK" der → SADECE O ZAMAN gateway deploy. Otomatik/proaktif deploy YASAK (lider Wave-1'i kullanıcı onayı almadan deploy etti → uyarı geldi).

**Why:** Freestyle UI5 lokal sunucu (8101) zaten CANLI backend'i tüketir → kullanıcı FE değişikliğini lokalde gerçek veriyle test edebilir; deploy gereksiz ve erken (yanlışsa canlı BSP'yi kirletir). Test sahibi kullanıcı; deploy onayı onun.

**How to apply:**
- FE build (pas) bitince: bug-gate → **lokalde sun** (npm start / 8101) → kullanıcıya "lokal hazır, test et" de → BEKLE. "OK/deploy et" gelene kadar gateway'e UI deploy görevi VERME.
- **BE-bağımlı FE özelliği** (yeni CDS alanı: KDMAT/ağırlık vb.) lokal testte ancak BE CDS canlıda AKTİF ise görünür ($metadata canlıdan gelir). Bu durumda BE-aktivasyonu lokal-testin ÖN-KOŞULU → kullanıcıya AÇIKLA + onay iste (BE-aktivasyon da SAP-yazımı; ayrı karar). Salt-FE değişikliği (BE-bağımsız) için BE-aktivasyon gerekmez.
- "done/deploy" demeden runtime-doğrula prensibiyle ([[feedback_done-tam-kapsam-dogrula]], [[feedback_ui5-v2-plumbing-reuse-traps]]) tutarlı: fark = doğrulamayı KULLANICI lokalde yapar, deploy onun onayına bağlı.
- İlgili: [[feedback_ui-deploy-noninteractive]] (deploy NASIL yapılır — ama NE ZAMAN = kullanıcı OK'i), [[feedback_lider-bloke-olmama-background-dispatch]].

## ⭐⭐ 2026-09-10 — KURALIN AÇIĞI ÖLÇÜLDÜ: `deploy_ui.py` ONAY BAŞINA DEĞİL, ÇALIŞMA AĞACI BAŞINA ÇALIŞIR

Kullanıcı **bir iş** için deploy onayı verdi (*"kapı bitince deploy et"*). `deploy_ui.py --apps …`
çalıştırıldı ve **aynı app'lerdeki BAŞKA bir işin FE'si de canlıya çıktı** — o iş çapada *"kod hazır,
DEPLOY YOK — tek blokaj kullanıcının lokal testi"* diye duruyordu.

**Mekanizma:** `deploy_ui.py` `ui5 build --clean-dest`'i gömer ve **`webapp/`'in o anki hâlini**
paketler. Onay bir *işe* verilir, deploy bir *app'e* yapılır — ikisi aynı şey değildir. Aynı
app'te paralel yürüyen her iş, ilk deploy'da **birlikte** gider.

**Ölçüm (varsayım değil):** deploy edilen `dist/Component-preload.js`'te öbür işin yardımcı
fonksiyonları ve i18n anahtarları (9 anahtar) iki app'te de bulundu.

**How to apply:**
- Deploy onayı almadan önce **çalışma ağacında o app'e dokunan BAŞKA iş var mı** diye bak
  (`git status -- <app yolu>`). Varsa kullanıcıya **deploy'un fiili kapsamını** söyle:
  *"bu deploy şu işi de canlıya taşır"* — onay o kapsam bilinerek verilsin.
- Deploy'dan sonra **çapayı aynı turda güncelle**: *"deploy edilmedi"* diyen her satır bayatlar
  ([[feedback_karar-degisince-kaydi-ayni-turda-guncelle]]).
- ⛔ Bunu *"kural ihlal edildi"* diye okuma: deploy doğru ve gerekliydi (bayat `dist` canlıda
  artık var olmayan bir entity set'i çağırıyordu). Kusur icrada değil, **kapsamın önceden
  beyan edilmemesinde**.
- Tersi de geçerli: `--apps` listesinde **olmayan** app deploy edilmez; o app canlıda **eski**
  kalır — bu da açıkça söylenmelidir.

İlgili: [[feedback_deploy-ui-statik-varlik-korlugu]] · [[feedback_kapsam-niteleyicisini-dusurme]]

## ⭐ 2026-11-06 — TEKRAR: deploy, BE yazım brifine ADIM olarak gömüldü

Gateway'e verilen tek "DEV yazımı" brifinde 11 adım vardı; 1–10 BE (FUGR/FM/class/CDS/SRVB/include),
**11. adım BSP `deploy_ui`**. BE yazımı onaylıydı, UI deploy'u değildi — kullanıcı lokal testi henüz
yapmamıştı. Gateway sırayla hepsini koştu; BSP kullanıcı "deploy et" demeden canlıya çıktı. Lider
kullanıcıya açıkça bildirdi; kullanıcı sonradan "deploy et" dedi (zarar yok, ama sıra yanlıştı).

**Mekanizma:** onay *işe* verilmişti ("yaz"), brif ise yazma ile deploy'u **aynı listede** taşıdı —
ajan listedeki her adımı onaylı sayar. Kural lider bilincindeydi ama brifin yapısında değildi.

**How to apply:** BE yazım brifine UI deploy adımı **koyma**. Deploy ayrı bir brif/çağrıdır ve ancak
kullanıcının "OK/deploy et"i GELDİKTEN sonra yazılır. BE-bağımlı FE için akış: BE yaz → lokal sun
(`npx fiori run`, kimlikli) → kullanıcı test → "deploy et" → ayrı deploy çağrısı.

Son-doğrulama: 2026-11-06; tohum geri akışı 2026-11-12 · Applies-to: freestyle UI5 + BSP deploy,
gateway'e çok adımlı yazım brifi
