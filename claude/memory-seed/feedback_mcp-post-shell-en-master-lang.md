---
name: feedback_mcp-post-shell-en-master-lang
description: "MCP adt_post_shell objeyi EN master language yaratıyor — Z obje create'te masterLanguage=TR garantile + post-create doğrula (ADR 0005 D)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 08868cc7-ead9-4d38-b6fe-2fd1fd3eb04c
---

`mcp__sap-adt__adt_post_shell` (ve genel MCP obje create) objeyi
**`adtcore:masterLanguage="EN"`** ile yaratıyor — MCP şemasında language
parametresi yok; server-side guardrail TR *text*'i zorluyor ama master
language'ı **zorlamıyor**. 2026-05-15 ORDER pilotunda `ZCL_SD001_ORDER`
behavior class'ı MCP ile EN yaratıldı; kullanıcı yakaladı ("objeleri EN
yaratıyorsun, TR olmalı"). ADR 0005 D ihlali.

**Why:** ADR 0005 D — tüm Z obje master language **TR** olmalı (kesin yasak).
masterLanguage create anında set edilir, in-place değişmez → düzeltme = sil +
raw-REST TR ile yeniden yarat + (RAP'ta) BDEF ile birlikte reactivate. Maliyetli;
baştan TR yaratmak şart.

**KANITLANDI (2026-05-15):** `adt_delete` → `create_rap_service.py step_bclass`
(raw REST, shell `masterLanguage="TR"`) → `bactivate` → SE24 "Original Language"
**TR** oldu (TADIR dahil). Yani raw-REST TR create TADIR-LANGU'yu da doğru set
eder. ⚠️ SE24 buffer recreate sonrası hemen yenilenmeyebilir (önce EN göründü,
aktivasyon/refresh sonrası TR) — doğrulamada SE24'ü yenilet.

**How to apply:** Z obje (özellikle class/BDEF/SRVD vb.) **raw ADT REST** ile
yarat, shell XML'e `adtcore:masterLanguage="TR"` (+ `adtcore:language="TR"`)
koy — `scripts/create_rap_service.py` step_bclass/step_bdef/step_srvd bunu
yapıyor (content-type'lar sistemin `/sap/bc/adt/discovery`'sinden). MCP
post_shell'i Z obje create için TR gerektiğinde **kullanma** (yalnız source
push/activate/get/search için güvenli). Her create sonrası
`adt_get include_source=false` → `adtcore:masterLanguage="TR"` **doğrula**
(reviewer checklist C-RAP-LANG-01, playbook adt-rap.md §32.6c).
**EK KANIT (2026-06-02, ZSD000_CL_ALV_GRID / C3):** SAPClient.create_object (MCP + script)
TR yaratMAZ — body'de masterLanguage var ama (a) adtcore:language="TR" YOK, (b) sap-language
HEADER'da değil query-param'da. Çalışan reçete YALNIZCA `create_rap_service.py`'de:
csrf() discovery sap-language=TR + bclass_shell_xml (masterLanguage="TR" **VE** language="TR")
+ POST header'da sap-client/sap-language=TR + Content-Type CLAS v4. **AMA** ZSD000_CL_ALV_GRID
ilk yaratımı EN'di → isim "EN-STICKY": delete+recreate aynı isimle, doğru reçeteyle bile EN
geliyor (SKILL operational-lessons: "EN yaratılıp silinmiş isim tekrar EN gelir → farklı
isimle doğrula"). DERS: **TR'yi İLK yaratımda yakala**; isim zehirlenirse TADIR-LANGU reset
(SE03/operatör) veya yeni isim gerekir. SYSTEMIC FIX **YAPILDI (2026-06-02, commit 1fe5f65b):** kök sebep SAPADTClient session
default header'ında sap-client vardı ama **sap-language YOKTU** → ilk auth EN logon.
Fix: `self.session.headers` 'sap-language': self.language. KANIT: fresh ZSD000_CL_LANGT2
standart create_object → masterLanguage=TR. Artık TÜM create (MCP+script) TR. + guard:
`scripts/validators/check_sap_master_language.py` (post-create masterLanguage!=TR → BLOCKER).
Neden daha önce fark edilmedi: RAP objeleri create_rap_service.py (kendi TR isteği) yolundan
TR geliyordu; MCP post_shell/genel create_object yolu EN idi ama o yoldan class az yaratıldı.
Bkz. [[feedback_zli-obje-text-tahmin-yasak]],
[[project_zsd015-ui-paradigm-all-or-nothing]].
