<!-- URETILMIS DOSYA — elle duzenleme. Uretici: core/scripts/build_core_index.py
     Tazelik gate'i: core/scripts/validators/check_core_index_fresh.py -->

# CORE-INDEX — metodoloji dokumanlarinin aranabilir dizini

> **Neden var:** `core/` bir junction'dir; `Grep` ve `Glob` junction'i TAKIP ETMEZ
> (gitignore'dan bagimsiz — olculdu). Kokten arama core'u GORMEZ ve sifir sonuc
> "boyle bir kural yok" diye okunur. Bu dosya GERCEK bir dosyadir: kokten aranir,
> bulunur ve dogru `core/...` yolunu verir. `Read("core/...")` calisir.
>
> **Arama receti (D29):** `Grep(path="core")` · `Glob(path="core/playbook", "*.md")`
> · `rg -L --no-ignore <p>` · `find -L core`. Kokten path'siz arama = sessiz sifir.


## `core/playbook/` (42 dosya)

- [`core/playbook/00-discipline-and-principles.md`](../core/playbook/00-discipline-and-principles.md) — ADT Disiplini, Hızlı Erişim ve Genel Prensipler
- [`core/playbook/adt-cds.md`](../core/playbook/adt-cds.md) — CDS View (DDLS/DF)
- [`core/playbook/adt-classes.md`](../core/playbook/adt-classes.md) — ABAP Class — Create, OSQLC ve Push+Activate Tam Akış
- [`core/playbook/adt-domain-dtel.md`](../core/playbook/adt-domain-dtel.md) — DDIC Domain ve Data Element (DTEL)
- [`core/playbook/adt-foundation.md`](../core/playbook/adt-foundation.md) — ADT Foundation — Logon, Download, Push, Lock, SQL, Paket, Transport, Search, Where-Used, ATC, OData Metadata
- [`core/playbook/adt-fugr-functions.md`](../core/playbook/adt-fugr-functions.md) — Function Group (FUGR) ve Function Module (FM) ADT pattern'leri
- [`core/playbook/adt-lock-objects.md`](../core/playbook/adt-lock-objects.md) — Lock Object (ENQU/DL)
- [`core/playbook/adt-mcp.md`](../core/playbook/adt-mcp.md) — ADT — MCP Tool Kullanımı (Coordinator için)
- [`core/playbook/adt-message-class.md`](../core/playbook/adt-message-class.md) — Mesaj Sınıfı (MSAG)
- [`core/playbook/adt-programs.md`](../core/playbook/adt-programs.md) — ABAP Report (PROG/P)
- [`core/playbook/adt-rap.md`](../core/playbook/adt-rap.md) — RAP — View Entity / BDEF / Behavior / Service Definition / Service Binding / Publish
- [`core/playbook/adt-tables-structures.md`](../core/playbook/adt-tables-structures.md) — DDIC Structure, Table Type ve Z Tablo
- [`core/playbook/checklists/adobe-forms-creation.md`](../core/playbook/checklists/adobe-forms-creation.md) — Checklist — Adobe Forms Çıktı (driver + interface spec) Oluşturma
- [`core/playbook/checklists/bug-checklist-backend.md`](../core/playbook/checklists/bug-checklist-backend.md) — Bug-Checklist — Backend (ABAP / RAP / CDS / DDIC)
- [`core/playbook/checklists/bug-checklist-frontend.md`](../core/playbook/checklists/bug-checklist-frontend.md) — Bug-Checklist — Frontend (freestyle UI5 + OData V2)
- [`core/playbook/checklists/cds-creation.md`](../core/playbook/checklists/cds-creation.md) — Reviewer Checklist — CDS Creation/Update (DDLS)
- [`core/playbook/checklists/classic-dialog-creation.md`](../core/playbook/checklists/classic-dialog-creation.md) — Checklist — Klasik Dialog Program (report / module pool / Dynpro / ALV) Oluşturma
- [`core/playbook/checklists/core-script-development.md`](../core/playbook/checklists/core-script-development.md) — Reviewer Checklist — CORE Script / Validator / Hook Geliştirme
- [`core/playbook/checklists/doc-checklist.md`](../core/playbook/checklists/doc-checklist.md) — Doc-Checklist — Kullanıcı/Teknik Dökümanlar (KD / FS / TS)
- [`core/playbook/checklists/domain-dtel-creation.md`](../core/playbook/checklists/domain-dtel-creation.md) — Checklist — DDIC Domain / Data Element (DTEL) Oluşturma
- [`core/playbook/checklists/itg-s2-signoff.md`](../core/playbook/checklists/itg-s2-signoff.md) — Reviewer Checklist — ITG S2 Sign-off (ADR 0022)
- [`core/playbook/checklists/packing-consumption-creation.md`](../core/playbook/checklists/packing-consumption-creation.md) — Reviewer Checklist — Ambalajlama Talimatı Tüketimi (Packing Consumption)
- [`core/playbook/checklists/rap-creation.md`](../core/playbook/checklists/rap-creation.md) — Reviewer Checklist — RAP Object Creation (view entity / BDEF / SD / SB)
- [`core/playbook/checklists/rap-troubleshoot.md`](../core/playbook/checklists/rap-troubleshoot.md) — Checklist — RAP Troubleshoot + Unit-Test (BOTD)
- [`core/playbook/checklists/struct-creation.md`](../core/playbook/checklists/struct-creation.md) — Reviewer Checklist — Struct Creation (DDIC Structure)
- [`core/playbook/checklists/table-update.md`](../core/playbook/checklists/table-update.md) — Reviewer Checklist — Table ALTER / Update (Z Table Field Ekleme/Değiştirme)
- [`core/playbook/checklists/ui-backend-rap-creation.md`](../core/playbook/checklists/ui-backend-rap-creation.md) — Checklist — UI Uygulaması RAP Backend Oluşturma
- [`core/playbook/checklists/ui-freestyle-creation.md`](../core/playbook/checklists/ui-freestyle-creation.md) — Checklist — Freestyle UI5 (OData V2 / RAP tüketen) Oluşturma
- [`core/playbook/coding-patterns.md`](../core/playbook/coding-patterns.md) — ABAP Coding Patterns — Range, FOR ALL ENTRIES, İç Tablo, Kur Dönüşümü
- [`core/playbook/howto-document-lock.md`](../core/playbook/howto-document-lock.md) — How-To: VA02-Tarzı Belge Kilidi (App-Level, ortak ZSD000)
- [`core/playbook/howto-dynpro-gui-status-generation.md`](../core/playbook/howto-dynpro-gui-status-generation.md) — Klasik Dynpro ekranı + GUI status'u AI'ın RFC FM ile (SOAP-RFC, dialog context) üretmesi
- [`core/playbook/howto-kullanici-dokumani-pdf-ekran-goruntulu.md`](../core/playbook/howto-kullanici-dokumani-pdf-ekran-goruntulu.md) — How-To: Markdown Dökümanı → Ekran Görüntülü Şık PDF (KD/FS/TS)
- [`core/playbook/howto-packing-instruction-consumption.md`](../core/playbook/howto-packing-instruction-consumption.md) — How-To — Ambalajlama Talimatı Tüketimi (POP/POF → kasa + kasa-içi adet)
- [`core/playbook/howto-rap-eml-sales-order-create-update.md`](../core/playbook/howto-rap-eml-sales-order-create-update.md) — How-to: Released Sales Order BO (I_SalesOrderTP) EML ile create / update
- [`core/playbook/intake-triage.md`](../core/playbook/intake-triage.md) — Geliştirme talebi alım protokolü — kapsam-sınıflama + 3-eksen araştırma + kanıtlı değerlendirme
- [`core/playbook/known-errors.md`](../core/playbook/known-errors.md) — Bilinen Hatalar ve Çözümlü Durumlar
- [`core/playbook/lessons-learned.md`](../core/playbook/lessons-learned.md) — Tekrarlayan hata pattern'leri ve trigger phrases
- [`core/playbook/modules/sd.md`](../core/playbook/modules/sd.md) — ITG modül kural-paketi (SD) — tetik-haritası + kontrol + soru + ders (bilgi-deposu DEĞİL)
- [`core/playbook/odata-services.md`](../core/playbook/odata-services.md) — OData Services — Pricing Simulation, Function Import, UpdateSO, BAPIRET2
- [`core/playbook/README.md`](../core/playbook/README.md) — Playbook — SAP ADT Operasyonel Pattern Bankası
- [`core/playbook/ui-backend-rap.md`](../core/playbook/ui-backend-rap.md) — UI Uygulaması RAP Backend — Operasyonel Tecrübe Bankası
- [`core/playbook/ui-freestyle-odata-v2.md`](../core/playbook/ui-freestyle-odata-v2.md) — Freestyle UI5 + OData V2 (RAP tüketen) — Operasyonel Tecrübe Bankası

## `core/standards/` (10 dosya)

- [`core/standards/01-naming.md`](../core/standards/01-naming.md) — NTTDATA ABAP Development Naming Guideline
- [`core/standards/02-coding-backend.md`](../core/standards/02-coding-backend.md) — OpenCode / Opus — SAP S/4HANA Geliştirme Kuralları
- [`core/standards/03-coding-ui-fiori.md`](../core/standards/03-coding-ui-fiori.md) — SAP Fiori UI5 Geliştirme Kuralları
- [`core/standards/04-documentation-fs-ts.md`](../core/standards/04-documentation-fs-ts.md) — SAP Geliştirme Dökümantasyon Kuralları
- [`core/standards/05-coding-rap.md`](../core/standards/05-coding-rap.md) — RAP — RESTful Application Programming Standardı
- [`core/standards/06-coding-classic-dialog.md`](../core/standards/06-coding-classic-dialog.md) — Klasik Dialog ABAP — Kodlama Standardı (report / module pool / Dynpro / ALV)
- [`core/standards/07-output-forms.md`](../core/standards/07-output-forms.md) — Çıktı / Form Standardı — Adobe Forms (+ SmartForms/SAPscript)
- [`core/standards/08-classic-gui-f1-help.md`](../core/standards/08-classic-gui-f1-help.md) — Klasik GUI Uygulama — In-System Kullanıcı Dokümanı (F1 / SE61) Standardı
- [`core/standards/09-packing-instruction-consumption.md`](../core/standards/09-packing-instruction-consumption.md) — SAP Ambalajlama Talimatı (Packing Instruction) TÜKETİMİ — Standart
- [`core/standards/README.md`](../core/standards/README.md) — Standards — Kurumsal & Proje Standartları

## `core/governance/decisions/` (22 dosya)

- [`core/governance/decisions/0001-tek-branch-main.md`](../core/governance/decisions/0001-tek-branch-main.md) — ADR 0001 — Tek Branch (Sadece `main`)
- [`core/governance/decisions/0002-package-naming.md`](../core/governance/decisions/0002-package-naming.md) — ADR 0002 — Paket Adlandırma (ZSDxxx_CLC Suffix)
- [`core/governance/decisions/0003-layered-rule-architecture.md`](../core/governance/decisions/0003-layered-rule-architecture.md) — ADR 0003 — 4-Katmanlı Kural Mimarisi (L1-L4) ve Kod Gate Enforcement
- [`core/governance/decisions/0004-erp-modul-bazli-organizasyon.md`](../core/governance/decisions/0004-erp-modul-bazli-organizasyon.md) — ADR 0004 — ERP/ Modül-Bazlı Klasör Organizasyonu
- [`core/governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md`](../core/governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md) — ADR 0005 — SAP Standart Obje Koruma + Sistem State Müdahale Yasakları
- [`core/governance/decisions/0006-reviewer-agent-pattern.md`](../core/governance/decisions/0006-reviewer-agent-pattern.md) — ADR 0006 — Reviewer Agent Pattern (Pre-Flight Quality Gate)
- [`core/governance/decisions/0007-sap-adt-mcp-server.md`](../core/governance/decisions/0007-sap-adt-mcp-server.md) — ADR 0007 — SAP ADT MCP Server
- [`core/governance/decisions/0008-liste-ekrani-alv-paritesi-standardi.md`](../core/governance/decisions/0008-liste-ekrani-alv-paritesi-standardi.md) — ADR 0008 — Liste Ekranı ALV-Paritesi Standardı (<PROJECT_NAME> Geneli)
- [`core/governance/decisions/0009-ortak-value-help-cds-politikasi.md`](../core/governance/decisions/0009-ortak-value-help-cds-politikasi.md) — ADR 0009 — Ortak (Foundation) Value-Help CDS Politikası
- [`core/governance/decisions/0010-tier-bazli-readonly-guard.md`](../core/governance/decisions/0010-tier-bazli-readonly-guard.md) — ADR 0010 — Tier-bazlı Readonly Guard + Multi-System Bağlantı
- [`core/governance/decisions/0011-veri-cikarma-pii-guard.md`](../core/governance/decisions/0011-veri-cikarma-pii-guard.md) — ADR 0011 — Veri-Çıkarma / PII (KVKK) Guard
- [`core/governance/decisions/0012-klasik-alv-template-first.md`](../core/governance/decisions/0012-klasik-alv-template-first.md) — ADR 0012 — Klasik ALV: Template-First (reusable class DEĞİL)
- [`core/governance/decisions/0013-kaynak-referans-dokuman-ayrimi-ref_docs.md`](../core/governance/decisions/0013-kaynak-referans-dokuman-ayrimi-ref_docs.md) — 0013 — Kaynak/Referans Doküman Ayrımı: `ref_docs/`
- [`core/governance/decisions/0014-document-lock-app-level-vs-draft.md`](../core/governance/decisions/0014-document-lock-app-level-vs-draft.md) — 14. Belge Kilidi: App-Level Kilit Tablosu (Draft yerine, bilinçli istisna)
- [`core/governance/decisions/0016-source-drift-onleme-repo-canli-senkron.md`](../core/governance/decisions/0016-source-drift-onleme-repo-canli-senkron.md) — 0016 — Source DRIFT Önleme: Repo ↔ Canlı SAP Senkron (Kod-Gate)
- [`core/governance/decisions/0017-ui-build-dogrulama-kanonik-desen-tuzak-gate.md`](../core/governance/decisions/0017-ui-build-dogrulama-kanonik-desen-tuzak-gate.md) — ADR 0017 — Freestyle UI Build Doğrulama: Kanonik Desen + Statik Tuzak Gate + Runtime Smoke + Lider Protokolü
- [`core/governance/decisions/0018-agent-takim-yapisi-katman-expert-bug-gate.md`](../core/governance/decisions/0018-agent-takim-yapisi-katman-expert-bug-gate.md) — ADR 0018 — Agent Takım Yapısı: Katman-Expert + Bug_Expert Gate + Lazy Lifecycle + Audit
- [`core/governance/decisions/0019-kural-enforcement-mimarisi-3-eksen-coverage-check.md`](../core/governance/decisions/0019-kural-enforcement-mimarisi-3-eksen-coverage-check.md) — ADR 0019 — Kural-Enforcement Mimarisi: 3-Eksen Sınıflandırma + Coverage-Check Keystone + Kademeli Gate-Doğum
- [`core/governance/decisions/0020-canli-cekirdek-junction-mimarisi.md`](../core/governance/decisions/0020-canli-cekirdek-junction-mimarisi.md) — ADR 0020 — Canlı çekirdek (DEV_CORE) + junction çoklu-proje mimarisi
- [`core/governance/decisions/0021-kesin-yasaklar-fiziksel-damga.md`](../core/governance/decisions/0021-kesin-yasaklar-fiziksel-damga.md) — ADR 0021 — KESİN YASAKLAR: fiziksel damga + drift-guard (import'a bağlı değil)
- [`core/governance/decisions/0022-intake-triage-gate.md`](../core/governance/decisions/0022-intake-triage-gate.md) — ADR 0022 — Intake Triage Gate (ITG)
- [`core/governance/decisions/0023-hook-kablolamasi-plugin-e-tasinmaz.md`](../core/governance/decisions/0023-hook-kablolamasi-plugin-e-tasinmaz.md) — ADR 0023 — Hook kablolaması plugin'e TAŞINMAZ (fail-closed-on-absence ifade edilemez)

---

**Toplam 74 dokuman.** Bu dosya uretilmistir; icerik degistiginde `build_core_index.py` yeniden kosulur.
