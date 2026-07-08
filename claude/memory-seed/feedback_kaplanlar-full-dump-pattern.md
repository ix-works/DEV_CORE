---
name: feedback-<legacy_source>-full-dump-pattern
description: "Sprintlerde \"kapsam içi mi\" kararı vermeden ÖNCE, ilgili tüm <LEGACY_SOURCE> objelerini (struct/DTEL/domain) tam indir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7091c15c-424a-42a9-bcf8-7c3f51f36d33
---

Sprintlerde "bu <LEGACY_SOURCE> objesi TD'ye alınacak mı?" kararı vermeden **önce**, ilgili tüm objeler <LEGACY_SOURCE> dump'ına indirilmelidir. TD'ye alıp almama kararı sonra sprintte verilir.

**Why:** Karar 2026-05-14'te Sprint 6 başlangıcında verildi. Kullanıcı: "sen \<legacy_source> klasörüne hepsini indir, TD ye alıp almayacağımza orda karar veririz sprintlerde". Sebep: kapsam dışı sanılan obje sprintte ihtiyaç olarak çıkabilir; indirme ucuz, kanonik kaynak yoksa tahminle yaratma riski yüksek (özellikle TR text). Ayrıca usage analizi kararı için gerekli.

**How to apply:**
- <LEGACY_SOURCE> SAP'sinden VPN ile çek: `GET /sap/bc/adt/ddic/structures/<name>/source/main` (DDL `.asddls`), `GET /sap/bc/adt/ddic/dataelements/<name>` (DTEL XML), `GET /sap/bc/adt/ddic/domains/<name>` (domain XML).
- Kaydet: `<LEGACY_SOURCE>
- Recursive: DTEL'lerin domain referansları, domain'lerin value table'ları → hepsi Z ise onları da indir.
- TD'ye alıp alınmama kararı sprintte → kullanıcıya usage analizi sun (Kap.refs + TD.refs).

İlgili: [[feedback_zli-obje-text-tahmin-yasak]], [[feedback_<legacy_source>-field-adlari-sistem-bagimli]]
