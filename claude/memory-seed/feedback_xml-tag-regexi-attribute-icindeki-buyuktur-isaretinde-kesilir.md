---
name: feedback_xml-tag-regexi-attribute-icindeki-buyuktur-isaretinde-kesilir
description: "Toplu XML/HTML düzenlemede `<tag[^>]*>` deseni attribute DEĞERİ içindeki `>` karakterinde erken keser ve dosyayı bozar; tırnak-duyarlı desen + parser doğrulaması şart"
metadata:
  type: feedback
---

`<tag\s+id="x"[^>]*?>` gibi *"etiketin sonuna kadar"* desenleri, attribute **değerinin
içinde** `>` geçen her dosyada **erken kapanır** ve sessizce bozuk çıktı üretir.

**Ölçülmüş vaka (2026-09-10, UI5 `OrderPicker.fragment.xml` ×5):** UI5 binding sözdizimi
`rows="{se>/pickItems}"` bir `>` içerir. Desen orada kapandı; script yeni attribute'u
**değerin ortasına** yazdı:
`fixedColumnCount="6">/pickItems}" selectionMode=...` ⇒ **4 dosya bozuldu**.
Düzeltme: `git checkout --` ile geri al → tırnak-duyarlı desen
`<table:Table\s+id="pickTable"(?:[^>"]|"[^"]*")*>` → sonra **beş dosyayı da**
`xml.etree.ElementTree.parse` ile doğrula.
⚠ Aynı turda ikinci ölçüm hatası: kolon gövdesini **400 karakterle sınırlayan** bir sayım
regex'i `sip_se`'de bir ikon kolonunu atladı (7 dedi, gerçek **8**) ⇒ blok-bazlı, **sınırsız**
parse ile yeniden ölçüldü.

**Why:** Bozulma **derlemede patlamaz** — XML dosyası diskte durur, git diff küçük görünür,
hata ancak **tarayıcıda render** anında çıkar. Yani hızlı bir "değişiklik uygulandı" sinyali
alırsın ama teslim ettiğin şey kırık ([[feedback_kapi-zinciri-derlemeyi-gormez]]).
Bu, [[feedback_kopya-sayimi-tek-sozdizimi-desenine-dayanma]] ile aynı aile: tek desen,
tek dilin gerçek gramerini temsil etmiyor.

**How to apply:**
- Yapılandırılmış dosyada (XML/HTML/JSON) **toplu düzenleme regex'i yazacaksan** ya
  tırnak-duyarlı desen kullan `(?:[^>"]|"[^"]*")*` ya da doğrudan **parser** ile düzenle.
- Düzenlemeden sonra **her dosyayı ayrıştır** (`ET.parse` / `json.load`) — exit 0 değil,
  ayrıştırma başarısı kanıttır ([[feedback_exit0-degil-cikti-kaniti]]).
- **N dosyaya uygulamadan önce 1 dosyada koş ve çıktıyı GÖZLE**; toplu koşumda bozulma
  N kat büyür.
- Sayım/ölçüm regex'lerine **karakter sınırı koyma** (`.{0,400}` gibi) — sessizce eksik sayar.
- Bozulma olursa **`git checkout --` ile geri al**, düzeltmeyi bozuk metin üstünde deneme.

İlgili: [[feedback_duzeltme-turu-kendi-regresyonunu-uretir]] · [[feedback_create-cds-view-xml-escape]]
