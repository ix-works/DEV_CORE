---
name: feedback_v2-date-only-filtre-utc-gece-yarisi
description: "OData V2 Edm.DateTime + display-format=Date (DATS) alana tarih gönderirken YEREL gece-yarısı değil UTC gece-yarısı gönder — SAP UTC değerin GÜN kısmını alır; 'gün-sonu 23:59:59' reçetesi ALT sınırı bir gün geriye kaydırır"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 92dff1a1-6efa-49c3-ae86-56b21b391799
  modified: 2026-09-23T12:20:13.994Z
---

`sap:display-format="Date"` taşıyan `Edm.DateTime` alan (arkada DATS) — `$filter` ya da function import parametresi — için UI5 V2 değeri **UTC** serialize eder; SAP gateway gelen UTC değerin **gün kısmını** alır. TR'de (UTC+3) yerel `00:00` → `...T21:00:00` = **bir önceki gün**. Yaygın "alt sınır gün-başı, üst sınır gün-sonu (23:59:59)" reçetesi yalnız üst sınırı kurtarır; **alt sınır bir gün geriye kayar**, seçilen aralığa önceki günün kayıtları sessizce girer.

Doğrusu: iki sınır da seçilen takvim gününün UTC gece-yarısı — `new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))`.

Kanıt (bir projede, 2026-09-23, proxy `$count` kontrol grubu): kullanıcı 23.09 seçince giden `Erdat ge datetime'2026-09-22T21:00:00'` 22.09'un 7 kaydını getirdi; `ge/le '2026-09-22T00:00:00'` → 7, 23.09 UTC → 0. İkinci bir listede eski 02.09 seçimi 01.09'un 12 lotunu getirdi. Bir mutabakat function import'u da aynı kaymayla yanlış pencere okuyordu.

⛔ **Filtreden daha kötüsü — yazan function import:** aynı dönüşüm `callFunction` `urlParameters`'ta `DatePicker.getDateValue()` ham verilince olur; bu kez yanlış gün **kalıcı YAZILIR** (vaka projesinde iki yazan function import — bug-gate 6. tur; gateway'in function-import parametresinde de UTC gün kısmını aldığı bir GET kontrol grubuyla ölçüldü: `21T21:00` ≡ `21T00`). Kardeş taramasında `getDateValue()` + `urlParameters`/create payload'ı da ara, yalnız `new Filter` değil (ilk turda bir rapor ve iki function import kaçtı).

**Why:** Hata sessizdir — fazla kayıt gelir, hata mesajı yok; yalnız kayıt tarihi seçilen günden farklı olunca görülür (DEV'de çoğu gün boş olduğu için gözden kaçar).
**How to apply:** date-only alana tarih gönderen her FE kodunda `setHours(0/23…)` görürsen `$metadata`'da `display-format` bak; Date ise UTC gece-yarısına çevir. Kontrol: kaydı OLAN bir günün **ertesi gününü** seç — 0 dönmeli. İstemci-tarafı JSON süzgeci (OData'ya gitmeyen) bu tuzağa tabi değildir.

Son-doğrulama: 2026-09-23 · Applies-to: UI5 OData V2 freestyle (tüm profiller), UTC dışı saat dilimi
Kanonik: core `playbook/checklists/bug-checklist-frontend.md` **FE-45** (DEV_CORE PR #288, kullanıcı onayı 2026-09-23).
prior-art: yok (memory grep `display-format|Date.UTC|23:59:59` 0; core playbook'ta reçete yok).
