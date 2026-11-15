---
name: feedback_ui-testi-dom-varligi-gorunurluk-ve-olay-parametresi
description: "UI5 testinde DOM'da VAR olmak GÖRÜNÜR olmak değildir (rect + elementFromPoint ölç); olay parametre adı UI5 kaynağından doğrulanır; üretim kodunu kopyalayan test düzeneği aynı hatayı taşır, gerçek tıklama ister"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

UI5 davranış testinde üç ayrı kör nokta vardır ve üçü de "yeşil test, bozuk ekran" sonucu üretir:

1. **DOM'da var olmak görünür olmak demek değildir.** `querySelectorAll(...)` ile öğeyi bulmak ya da Playwright `click()` ile tıklamak, öğenin kullanıcıya görünür olduğunu kanıtlamaz. Playwright tıklamadan önce otomatik kaydırır ve öğe kırpılmış bir kabın içinde olsa bile tıklar. Görünürlüğü ölçmek için iki şeye bak: öğenin `getBoundingClientRect()` kutusu kabın kutusunun içinde mi, ve `document.elementFromPoint(merkezX, merkezY)` öğenin kendisini (ya da bir torununu) mu döndürüyor.
2. **Olay parametresinin adı tahmin edilmez.** `oEvent.getParameter("<ad>")` için kullanılan ad, kontrolün `-dbg.js` kaynağındaki `fire<Olay>({...})` çağrısından okunur. Var olmayan bir ad hata vermez, sessizce `undefined` döner.
3. **Üretim mantığını kopyalayan test düzeneği aynı hatayı taşır.** Düzenekteki stub handler üretim kodunun kopyasıysa, yanlış parametre adı iki yerde de aynıdır. Test kontrolü olay üzerinden değil de doğrudan çağırırsa (`controller.onX()` ya da modeli elle yazmak) hata görünmez. Olay yolu **gerçek tıklamayla** test edilir.

**Why:** Vaka 2026-11-14 (bir SD fiyat onayı uygulaması):
- ① `SegmentedButton` `selectionChange` handler'ı `getParameter("key")` okuyordu. UI5 1.120'de `SegmentedButton-dbg.js` bu olayda yalnız `item` parametresini taşır, bu yüzden "Yalnız uyarılı" filtresi onay kipinde hiç uygulanmıyordu. Regresyon süiti yeşildi, çünkü test düzeneğindeki stub da aynı `key` okumasını kopyalamıştı. Bulguyu taze bir bug-gate yakaladı. Gerçek tıklama senaryosu eklenince eski kod KIRMIZI verdi (kontrol grubu), düzeltilmiş kod 3/0 geçti.
- ② Aynı partide bir buton 4 satırlık bir tabloda kırpılıyordu ve DOM varlık testi bunu göremedi. rect + elementFromPoint ölçümü eklenince kırpılma ölçülebilir hâle geldi.

**How to apply:**
- Görünürlük iddiası taşıyan her UI testi rect + `elementFromPoint` kontrolünü içerir. "Öğe var" kontrolü bunun yerine geçmez.
- Yeni ya da değişen bir olay handler'ında parametre adı kontrolün kaynağından doğrulanır ve kaynak satırı yorumda ya da raporda belirtilir.
- Olay yolunu test eden senaryo, kontrolü gerçek tıklamayla tetikler. Kontrol grubu olarak eski kod da koşulur: eski kod KIRMIZI vermiyorsa test hatayı yakalayamıyor demektir.

İlgili: [[feedback_playwright-ui5-firepress-model-api]] (tetikleme yöntemi; bu ders ise neyin kanıt sayılacağı) · [[feedback_m-table-esnek-kolon-dar-ekranda-sifir-px]] · [[feedback_done-tam-kapsam-dogrula]]
Son-doğrulama: 2026-11-14 · Applies-to: freestyle UI5 testleri (Playwright/mock), tüm profiller
prior-art: kısmi — `feedback_playwright-ui5-firepress-model-api` (click ile firePress farkı, rect ile genişlik) · `feedback_m-table-esnek-kolon-dar-ekranda-sifir-px` (th rect). "Varlık ≠ görünürlük" ve "olay parametresi kaynaktan okunur" yoktu.
