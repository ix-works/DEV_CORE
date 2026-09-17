---
name: feedback_ddls-obje-aciklamasi-annotation-degisiminde-tazelenmez
description: "DDLS obje aciklamasi (adtcore:description) @EndUserText.label degisince TAZELENMEZ — kaynak readback'i 'etiket canliya gitti' kanitlamaz"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f07a9d9a-ccde-437b-818a-48086e4c73a7
---

Bir CDS DDLS'in **obje açıklaması** (`adtcore:description` — SE11 / ADT obje ağacı /
`TADIR` yüzeylerinde görünen metin) yalnızca objenin **ilk yaratılışında** kaynaktaki
`@EndUserText.label`'dan alınır. Sonradan annotation değiştirilip **yeniden push + aktive
edilse bile obje açıklaması ESKİ metinde kalır.**

**Ölçüm (2026-09-12, <SISTEM>/100, `ZSD001_I_DLV_SPLIT_SUM`):** aynı `adt_get … ddls
include_source=true` çağrısının iki parçası çelişiyordu —
- kaynak satır 2: `@EndUserText.label: 'Teslimat Parti Bölünmüş Kalem Toplamı'` (37, YENİ)
- metadata: `adtcore:description="Teslimat Parti Bölünmüş Alt Kalem Toplamı"` (41, ESKİ)
- `adtcore:changedAt="2026-09-11T16:33:09Z"` = kısaltma push'unun kendisi ⇒ obje o anda
  değişti ama açıklama tazelenmedi.

**Why:** "Canlı md5 == yerel" ve "canlı satır 2 kısaltılmış" kanıtları **yalnız kaynağı**
ölçer; obje metni ayrı bir yüzeydir ve o readback'in kör noktasındadır. Bu ayrımı
yapmadan *"etiket canlıya gitti"* demek, kanıtın kapsamını sessizce genişletmektir —
sonraki turda SE11'e bakan biri çelişki bulur.

**How to apply:** Z bir DDIC/CDS objesinin **etiketi değiştiyse** iki yüzeyi AYRI
doğrula: (1) kaynak annotation → `include_source=true`, (2) obje metni →
aynı yanıtın `adtcore:description`'ı. Raporda hangisinin ölçüldüğünü YAZ. Etki genelde
kozmetiktir (son kullanıcı etiketi ve OData `$metadata` kaynaktan gelir), ama "gitti"
hükmünü ikisi de eşleşmeden verme. Obje metninin de düzelmesi isteniyorsa bunu ayrı bir
gateway işi olarak planla; kendiliğinden olmasını bekleme.
İlgili: [[feedback_push-ok-mesaji-sahte-readback-esitligi]],
[[feedback_push-ara-kopyasi-bayatlar-readback-bunu-goremez]],
[[feedback_zli-obje-text-tahmin-yasak]],
[[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]].
