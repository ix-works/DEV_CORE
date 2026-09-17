---
name: feedback_e070-as4date-istegin-tarihidir-obje-degisim-tarihi-adt-versions
description: "\"Bu obje ne zaman değişti\" sorusu E071×E070 ile ÇÖZÜLEMEZ — AS4DATE isteğin tarihidir; doğru araç ADT versions ucu (Accept - */* şart)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 84facfd3-9151-4893-8380-15c2cfd0d393
---

**`E070-AS4DATE` objenin değil İSTEĞİN tarihidir.** Uzun ömürlü bir transport request'te
(`<TRANSPORT>` gibi, aylarca açık kalan) `E071` ile bağlanan **tüm objeler aynı tarihi** gösterir.
Dolayısıyla *"bu obje ne zaman değişti / kırılma hangi değişiklikten geldi"* sorusu `E071 × E070`
join'iyle **ÇÖZÜLEMEZ** — çıkan tarih objeye ait değildir.

**Doğru araç:** ADT sürüm geçmişi ucu —
`/sap/bc/adt/oo/classes/<sinif>/includes/implementations/versions` (analog uçlar diğer obje
tipleri için de var). Dönen her sürümde gerçek `changedAt` damgası + satır sayısı + TR bulunur.
⚠ **`Accept: */*` ŞART**: `application/xml` ve `application/vnd.sap...versions.v1+xml`
**HTTP 406** verir. Ham GET deseni `core/scripts/sap_adt_lib.py` (`SAPADTClient()` →
`c.session.get(c.url + <yol>, verify=False)`).

**Why:** 2026-09-08'de booking `SQL 305` teşhisinde bir tur bu yanlış eksende harcandı; ölçüm
yapıldı ama **soruyu cevaplamıyordu**. Sürüm ucu kullanılınca cevap net çıktı: dump'ın doğduğu
`ALL FIELDS WITH` ifadesi **iki sürümde de birebir aynı** (arşiv 2026-07-28, aktif 2026-09-04) ⇒
kırılma **kod değil VERİ** regresyonuydu — bu, düzeltmenin yerini tamamen değiştirdi.

**How to apply:** "ne zaman değişti" sorusunda **önce** ADT versions ucuna git; `E070/E071` yalnız
*"bu obje hangi TR'de"* sorusunu cevaplar. Bir tarih ölçtüysen, **objeye mi isteğe mi ait**
olduğunu yaz — aksi hâlde ölçüm doğru, hüküm yanlış olur
([[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]]).
