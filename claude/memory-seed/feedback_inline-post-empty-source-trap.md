---
name: feedback_inline-post-empty-source-trap
description: "CDS inline-source POST children'ı boş bırakabilir; create sonrası status-200 değil SOURCE içeriğini doğrula"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 221a6a93-26fb-43be-9837-c5989e246ea5
---

`create_ddls_ve.py` gibi inline-source POST (shell-create XML içine `<ddl:source>` gömme) ile çoklu CDS yaratımında **children boş kalabiliyor**: 2026-06-09'da ZSD001_I_SEVKEMRI_ITEM + _DORBN SAP'de `source=""` (boş shell) yaratıldı, sadece root'a source yazıldı. "R3a interface CDS CANLI" notu over-claim'di — children parse-geçersizdi (`SDDL_PARSER_MSG 013 "does not contain a valid definition"`). 2026-06-10'da BDEF aktivasyonu "Type ZSD001_I_SEVKEMRI is unknown" verince ortaya çıktı.

**Why:** Yaratım scripti "active-GET 200" ile doğruluyordu ama 200 = obje VAR demek, SOURCE dolu/valid demek DEĞİL. Boş inactive version aktif görünüp BDEF/servis gibi bağımlı objeleri sessizce kırıyor (saatler sonra patlıyor).

**How to apply:** (1) CDS/DDLS yaratımından sonra `adt_get include_source=true` ile **source içeriğini** teyit et (`len>0` + `define` var); status 200'e güvenme. (2) Çoklu/kompozisyon CDS'te inline-source POST yerine **LOCK+PUT source/main** tercih et (güvenilir yazım) — bkz `repush_sevkemri_cds.py`. (3) Recovery: local repo dosyasından 3'ünü LOCK+PUT + toplu aktive. (4) Genel kural: [[feedback_done-tam-kapsam-dogrula]] — "CANLI" demeden tam içerik doğrula, [[feedback_reviewer-checklist-vs-wired-validator]] (status≠doğru sonuç teması).
