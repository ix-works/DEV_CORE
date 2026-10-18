---
name: feedback_adt-get-dtel-ana-dil-metnini-dondurur
description: "adt_get DTEL 'language=TR' dese de objenin ANA DİL (std: EN) etiketini döndürür — TR alıntısını DD04T DDLANGUAGE='T'den al"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 2b5ea0bf-6c01-4fdc-acb8-b62e8c4bccb5
  modified: 2026-10-09T19:24:22.418Z
---

Bir projenin geçmiş penceresinde std DTEL `ROUTE`'un etiketi `adt_get` ile "alıntılandı" → **"Route"** yazıldı.
Re-gate DD04T'yi okudu: `DDLANGUAGE='T'` satırında `SCRTEXT_L='Rota'`; "Route" yalnız E/D satırlarında.
`adt_get` yanıtı `language="TR"` taşısa da `masterLanguage="EN"` olan objenin **ana dil** metnini verdi (2026-10-09).

**Why:** "alıntı" damgası metni doğru kılmaz; yanlış dilden alıntı, kullanıcıya İngilizce etiket olarak sızar ve
alıntı kuralı onay turunu da atlattığı için kimse yakalamaz.

**How to apply:** std (ana dili EN olan) DTEL/domain metnini TR ekrana alıntılarken `adt_sql_query`
`SELECT scrtext_l, reptext FROM dd04t WHERE rollname = '<DTEL>' AND ddlanguage = 'T' AND as4local = 'A'` ile oku.
Z objelerde (ana dil TR) `adt_get` doğru dili verir — fark ana dildedir. İlgili: [[feedback_mcp-post-shell-en-master-lang]]

Son-doğrulama: 2026-10-09 · Applies-to: SAP ADT, DTEL/domain metin alıntısı (tüm profiller)
