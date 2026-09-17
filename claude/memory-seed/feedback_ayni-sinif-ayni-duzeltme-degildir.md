---
name: feedback_ayni-sinif-ayni-duzeltme-degildir
description: Kusur SINIFI nereye bakılacağını söyler, ne yapılacağını SÖYLEMEZ — kardeş vakanın düzeltmesini taşımadan önce mekanizmayı yeniden ölç
metadata:
  node_type: memory
  type: feedback
---

Bir kusur sınıfı (T-trigger, pattern, "aynı hatanın kardeşi") **arama uzayını** daraltır. Düzeltmeyi
vermez. Kardeş vakada işe yarayan yamayı ikinci vakaya taşımak, çoğu zaman **hiçbir şeyi düzeltmez
ama düzeldi sanılmasına** yol açar — çünkü sınıf aynıyken **mekanizma** farklı olabilir.

**2026-09-08, T-CDS-AGGKEY'in iki vakası** (ikisi de `key A,B` ilan edip `GROUP BY A,B,C` yapıyor):

| | ZSD001_I_CONTAINER_GROSS | ZSD000_I_DELIVERY_QTY |
|---|---|---|
| Fazladan kova | birimsiz teslimat, `btgew=0` | gelen teslimat, **gerçek miktar** |
| Sebep | veri boşluğu (SAP sıfır miktarda birimi boş bırakır) | **kapsam hatası** — `ReferenceSDDocument` satış değil **satınalma** siparişi taşıyor |
| Düzeltme | `gewei <> ''` | `SDDocumentCategory <> '7'` |

`gewei <> ''` mantığı ZSD000'e taşınsaydı hiçbir satırı elemezdi (orada boş birim yok): view yine
136/128 kalırdı, ama "kardeşiyle aynı yöntemle düzeltildi" diye kapatılırdı.

**Why:** Sınıf tanımı **belirtiyi** (anahtar tekilliği kırık) tarif eder, **nedeni** değil. Aynı
belirtinin arkasında veri boşluğu da olabilir, yanlış kapsam da, gerçek çok-birimlilik de — ve
üçünün düzeltmesi farklıdır. Kardeş vakanın çözümünü taşımak, ölçüm yerine **analoji** ile hareket
etmektir ([[feedback_kardes-artefakt-benzerligi-kip-semantigini-kanitlamaz]] ile aynı kök hata).

**How to apply:** Kardeş vakaya "aynı yöntemle düzelt" dendiğinde, taşınan şey **düzeltme değil
YÖNTEM** olmalı: (1) çakışan anahtarları listele, (2) çakışmayı üreten satırların **nereden geldiğini**
ölç — hangi belge, hangi tip, hangi tablo, (3) o kaynağın view'ın anlamına ait olup olmadığına karar
ver, (4) satır kaybı / ters yön / pozitif kontrol merdivenini kur. Düzeltme (2)'nin cevabından çıkar.
⚠ Kardeş vakanın şerhinde yazılı "sınırı" oku — ZSD001'in şerhi *"ikinci GERÇEK birim girerse bu
filtre YETMEZ"* diyordu ve ZSD000 tam olarak o durumdu.
İlgili: [[feedback_bulgu-listesi-ornektir-sinif-duzeltmesi-tarama-ister]] ·
[[feedback_satir-sayisi-artisi-cogaltma-degildir-satir-tekil-farki]] ·
[[feedback_kaydin-onerdigi-fix-yonu-de-bir-iddiadir]]
