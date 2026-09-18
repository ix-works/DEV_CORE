---
name: feedback_v2-function-import-buyuk-yuk-414-batch
description: OData V2 callFunction büyük yük taşıyorsa HTTP 414 — duvar Web Dispatcher, çözüm o tek çağrı için useBatch:true ikinci model
metadata:
  node_type: memory
  type: feedback
---

OData **V2** `callFunction` parametreleri **URL'e** serileştirir ⇒ dosya/base64/`JSON.stringify(dizi)` taşıyan function import **HTTP 414** verir. Duvar **SAP Web Dispatcher**'dır (414 gövdesinin kendi metniyle kanıtlanır), **ICM değil** — `icm/HTTP/max_request_size_KB` gövde sınırıdır, ilgisizdir ve oraya bakmak bir tur kaybettirir.

**Why:** semptom satır sayısıyla doğrusal büyür ⇒ az veriyle çalışır, eşiği geçen ilk kayıtta patlar. Teşhis sırasında iki sahte yol var: (a) duvarı yükseltmek — log'a dosya içeriği düşer, RISE/PCE'de müşteride değil, sınır kalkmaz ötelenir (b) `x-www-form-urlencoded` gövde — Gateway **HTTP 200** döner ama gövdeyi **sessizce yok sayar**.

**How to apply:** kanonik reçete `core/standards/03-coding-ui-fiori.md` **§18.5a** (ölçülmüş eşik, ham `$batch` gövde biçimi — ⛔ kapanış ayracından önceki **boş satır zorunlu**, yoksa `400 malformed syntax` ve mesaj boyutu işaret etmez). Kontrol maddeleri: `bug-checklist-frontend.md` **FE-42** (yükün kendisi) · **FE-43** (ikinci modelde `metadataUrlParams` devri) · **FE-44** (istemci-tarafı boyut kapısı). Bir 414 bulduğunda **tüm `callFunction` sitelerini tara** — bu bir sınıftır, vaka değil. Kardeş vakalar: [[project_zsd001-<MUSTERI-D>-konsinye]] ve `governance/deferred-triggers.md` §2026-09-16. Ders zinciri: [[feedback_paylasim-onbellek-sorusu-kaynak-okumasiyla-cevaplanmaz]]
