---
name: feedback_tek-soru-ve-bagimsiz-dokuman
description: Tip/uygulama dökümanları delta değil bağımsız-tam olmalı (link içermez); soru-sorma disiplini ayrı dosyada
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6b9195f9-e63c-4781-931d-b9672c867a85
---

Kullanıcı düzeltmesi (2026-06-14): **Tip/uygulama dökümanı = bağımsız ve TAM, delta DEĞİL.** Bir SE tipi (SIP_SE/IHR_SE) için döküman yazarken "FIT_SE'ye göre farklar" (delta) raporu İSTENMİYOR. Her döküman kendi başına o tipin TÜM fonksiyonalitesini (aynı olanlar dahil) içermeli, başka tipe/dökümana LİNK içermemeli. Model: FIT_SE fonksiyonalitesini al → o tipe göre revize et → bağımsız tam döküman üret.

**Why:** Delta dökümanı tek başına okunamaz/eksiktir; aynı olan özellik belirtilmeyince döküman kullanılamaz.

**How to apply:** Spawn edilen ajanlara "delta/fark raporu" değil "tam bağımsız fonksiyonel döküman" görevi ver. İlgili: [[feedback_done-tam-kapsam-dogrula]] · [[project_sprint-plan-rap-revize]].

> NOT: "tek seferde tek soru" + soru-sorma disiplini bu dosyadan çıkarıldı → kanonik ev [[feedback_karar-verimliligi-asiri-kapi-yok]] (karar sorma disiplini).
