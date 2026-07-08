---
name: sap-abap-dev
description: >
  This skill should be used for ANY SAP ABAP development task in the <PROJECT_NAME>
  repo — creating or changing CDS views, RAP objects (BDEF/behavior/SRVD/SRVB),
  DDIC objects (domain/data element/structure/table), classes, programs, OData
  services, transports, lock objects, message classes, or freestyle UI5. Use it
  whenever the work touches SAP, ABAP, ADT, CDS, RAP, DDIC, a Z object, a package
  like ZSD001_CLC, transport <TRANSPORT>, or the .conn_adt connection. It routes to
  the project's layered rule architecture (general -> module -> package), enforces
  the ADR 0005 hard prohibitions, and surfaces hard-won operational lessons
  (TR master-language create, transport discipline, Windows encoding, no-retry).
  Triggers: "CDS yarat", "RAP", "BDEF", "behavior", "domain ekle", "DTEL",
  "struct", "tablo yarat", "SAP'ye push", "aktive et", "transport", "ZSD001",
  "OData servis", "freestyle UI", "SRVB publish", "where-used", "ATC".
version: 0.1.0
---

# SAP ABAP Geliştirme — <PROJECT_NAME> (Katmanlı Yönlendirme)

Bu skill, <PROJECT_NAME> deposundaki her SAP/ABAP işinin **giriş noktasıdır**. Bilgiyi
burada tekrarlamaz; doğru katmana yönlendirir (ADR 0003). Önce inviolable yasakları
hatırlatır, sonra genel → modül → paket sırasıyla hangi dosyanın okunacağını söyler,
ardından SAP yazma protokolünü ve tekrarlayan operasyonel tuzakları gösterir.

---

## TIER 0 — KESİN YASAKLAR (ADR 0005, bypass YOK)

Her SAP işleminden önce bunlar geçerlidir. İhlal riski varsa: **DUR → AÇIKLA →
ÖNERİ SUN → KULLANICIDAN İSTE → BEKLE.**

- **A — Standart SAP objeleri (Z ile başlamayan):** yaratma/değiştirme/silme YASAK.
  Append struct, alan ekleme, FM/BAdI/program/message-class değişikliği dahil. Bunu
  yapan script'i çalıştırma da yasak. Append field/DTEL adını **AI önermez** — kullanıcı belirler.
- **B — Standart tablo verileri:** direkt `INSERT/UPDATE/DELETE/MODIFY` YASAK (Z'li
  kodun içinde bile). Sıra: BAPI → RFC FM → transaction (BDC) → kullanıcıdan manuel. Asla direkt SQL.
- **C — Sistem state:** transport yaratma/release, package yaratma, enqueue lock silme YASAK.
- **D — Z'li obje yaratma:** TR login zorunlu (`sap-language=TR`), 4 field label TR ve
  tam, title/description boş bırakılmaz, activate öncesi REST GET ile doğrula.

Detay: `governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md`

---

## SAP YAZMA PROTOKOLÜ (her domain/DTEL/CDS/struct/class/RAP push öncesi)

1. **Reviewer pre-flight (ADR 0006):**
   `python scripts/validators/run_review.py --task <task_type> --artifact <path>`
   - PASS → yaz · WARNING → yaz + raporda belirt · BLOCKER → yazma, düzelt, tekrar review.
2. **MCP tool mu, script mi? (ADR 0007):**
   - Tek obje yaratım/aktivasyon/push/search/lock → **MCP `sap-adt` tool** (`adt_*`).
   - CSV'den batch (`populate_*.py`), validator, sprint gate, TD spec check → **script**.
   - MCP server zaten server-side guardrail uygular (Z/Y prefix, TR text, transport zorunlu).
3. **Bağlantı:** `.conn_adt` (sistem <SYSTEM_ID>, client 100, user <SAP_USER>, **TR**).
   Aktif transport `<TRANSPORT>`. Değerleri ASLA uydurma — dosyadan oku.

---

## KATMAN YÖNLENDİRME — "Bu konu hangi dosyada?"

Önce **genel**, gerekiyorsa **modül**, en sonunda **paket** seviyesine in. Çalışmaya
başlamadan önce aktif paketin son durumunu oku.

### Tier 1 — GENEL (proje geneli, tüm modüller)

| Konu | Dosya |
|---|---|
| AI davranışı (git, ADT işlem sırası, oturum protokolü) | `AGENTS.md` (L1) |
| Naming standardı | `standards/01-naming.md` (L2) |
| Klasik backend (SEGW/FE) kodlama | `standards/02-coding-backend.md` |
| RAP kodlama (view entity/BDEF/servis/publish) | `standards/05-coding-rap.md` |
| Fiori/UI5 kodlama + deploy | `standards/03-coding-ui-fiori.md` |
| FS/TS doküman şablonu | `standards/04-documentation-fs-ts.md` |
| ADT pattern bankası (obje tipine göre) | `playbook/adt-*.md` (L3) |
| Hata pattern + trigger phrases | `playbook/lessons-learned.md`, `playbook/known-errors.md` |
| Freestyle UI tecrübe (FE/BE) — yeni UI öncesi §0 PRE-FLIGHT | `playbook/ui-freestyle-odata-v2.md` + `ui-backend-rap.md` + `playbook/checklists/` |
| Mimari kararlar | `governance/decisions/` (ADR 0001–0009) |

ADT işlemi öncesi ilgili `playbook/adt-<tip>.md` ve `checklists/` **mutlaka okunur** —
annotation/syntax pattern tahmin edilmez.

#### TETİKLEMELİ YÜKLEME (iş türü → ÖNCE oku) — gap-analysis #8

İşe başlamadan, türüne göre **şunu oku** (her şeyi değil, ilgiliyi — token + tutarlılık):

| İş türü / tetik | ÖNCE oku |
|---|---|
| CDS view entity / RAP (BDEF/behavior/SRVD/SRVB/publish) | `standards/05-coding-rap.md` + `playbook/adt-rap.md` §32 + `playbook/checklists/rap-creation.md` · ⭐ **Clean Core: std tablo değil released CDS** (`from mara` DEĞİL `from I_Product`) — yazmadan ÖNCE `governance/reference/released_successors.json`'a bak |
| Managed RAP (create/update/delete) | ↑ + **etag/lock master kuralı** (`standards/05` §5; reviewer `check_rap_managed_etag.py`) |
| RAP **hata teşhisi / unit-test** (BDEF aktive olmuyor, validation tetiklenmiyor, dump, draft, ABAP Unit) | **`playbook/checklists/rap-troubleshoot.md`** — troubleshoot tablosu + **BOTD test-double** (`CL_BOTD_TXBUFDBL_BO_TEST_ENV`) pattern + ATC no-suppress |
| DDIC domain/DTEL | **`playbook/checklists/domain-dtel-creation.md`** + `standards/01` §5B (reuse-gate, TR-4-label) |
| DDIC struct/tablo | **`playbook/checklists/struct-creation.md` / `table-update.md`** + `standards/01` §5B |
| Klasik dialog (report/module pool/Dynpro) | `standards/06-coding-classic-dialog.md` + **`playbook/checklists/classic-dialog-creation.md` (ZORUNLU pre-flight)** — §1: tek-body YAZMA → include'lara böl (`ZSD<pkg>_I_<PRG>_T01/_C01/_O01/_I01/_F01`, PROG/I) · §4: Dynpro+GUI status `ZSD000_FM_SCREEN_GEN` ile AI üretir |
| Klasik ALV / liste ekranı | `standards/06` §2-3 + **ADR 0012 TEMPLATE-FIRST → `playbook/templates/classic-alv-list.prog.abap` kopyala+özelleştir** (fcat title+hotspot+event inline; reusable class YOK) + ekran/status: `playbook/adt-fugr-functions.md` §6 (ZSD000_FM_SCREEN_GEN) — **öner!** |
| **Dynpro ekranı / GUI status (PF-STATUS) üret** | `playbook/adt-fugr-functions.md` §6 — `ZSD000_FM_SCREEN_GEN` RFC FM (RPY_DYNPRO_INSERT + RS_CUA_FETCH/WRITE/GENERATE, SOAP-RFC dialog). classrun YAPAMAZ. **Yeni klasik program ekranı gerekince bu flow'u ÖNER.** |
| Adobe Forms / çıktı | **`playbook/checklists/adobe-forms-creation.md`** + `standards/07` (operatör=layout/interface, AI=driver+spec) |
| Freestyle UI5 (yeni UI) | `playbook/ui-freestyle-odata-v2.md` §0 + `ui-backend-rap.md` §0 PRE-FLIGHT + `governance/vscode-setup.md` |
| **UI app BSP'ye DEPLOY** (`npm run deploy`) | **`standards/03-coding-ui-fiori.md` §2.4.1** — NON-İNTERAKTİF: `.conn_adt` kimlik→`FIORI_TOOLS_USER/PASSWORD` env + **`--yes`** (prompt atla); CLI --username/--password=401; `tr -d '\r'`; mutlak `--prefix`. **"deploy edemem" DEME** (env boş = keychain/inline çözülür). Per-app `ui/<app>/RUN.md` deploy bölümü |
| Value-help / master | ADR 0009 (ortak `ZSD000_I_*` reuse) — kullanıcıya local mi ortak mı sor |
| Yeni program (her tür) | spec-mutabakat gate: `program_to_spec.py` taslak → düzelt → mutabakat → build |
| Modül semantiği (tablo/BAPI/exit/SPRO) | `governance/modules/<MOD>/` (bkz. Tier 2) |
| Bağlantı/tier şüphesi | `python scripts/sap_doctor.py` |
| **Eldeki araç/MCP/skill bir ihtiyacı çözmüyor → YENİ araç aranacak** | **İLK** `governance/tooling-plugins.md` §🔎 → küratörlü katalog [`marianfoo/sap-ai-mcp-servers`](https://github.com/marianfoo/sap-ai-mcp-servers) (resmi/topluluk, güncel). Sıfırdan internet taraması yerine önce buraya bak |
| **Released-object / "std tablo yerine ne?" (Clean Core)** | `python scripts/validators/check_released_objects.py <artifact>` veya reviewer (cds/rap/class_push zincirinde WARNING) — MARA→I_Product successor (otoriter, `governance/reference/released_successors.json`). ⚠️ **WARNING'i SESSİZ GEÇME** (ATC no-suppress gibi): ya released'a çevir ya gerekçeni kullanıcıya bildir. Tüm-tip API için native ATC "Usage of APIs" |
| **HER iş başında — ERTELENMİŞ TETİK kontrolü** | `governance/deferred-triggers.md` — iş türün bir ertelenmiş-işi tetikliyor mu? (AMDP→std, dump→tool, QA/PRD→keychain, e-İrsaliye...). Eşleşirse DUR→gündeme getir. NOT: Dynpro/GUI-status üretimi C1 ile ÇÖZÜLDÜ → `ZSD000_FM_SCREEN_GEN` flow'unu öner (playbook §6) |

### Tier 2 — MODÜL (ADR 0004, modül-bazlı organizasyon)

Objeler `ERP/<MODULE>/<PACKAGE>/` altında yaşar (`SD`, `MM`, `FI`, `CO`, `QM`, `PM`,
`EWM`). Modül = SAP fonksiyonel alanı; paket prefix'i modülü yansıtır
(`ZSD*` → SD). İndirilen objeyi paket adıyla eşleşen alt klasöre kaydet
(`cds/`, `classes/`, `functions/`, `structures/`, `tables/`).

**Modül-bilgi katmanı (gap-analysis #14):** O modülde çalışırken `governance/modules/<MOD>/`
referanslarını oku — `tables.md` (kilit tablolar), `bapi.md` (released BAPI/FM),
`enhancements.md` (BAdI/exit/BTE), `spro.md` (customizing), `tcodes.md`, `workflows.md`.
Şu an mevcut: **SD** (`governance/modules/SD/`). Yeni modül başlarken o klasör **artımlı** yazılır.

### Tier 3 — İŞ / PAKET (paket-spesifik, L4)

| Adım | Nasıl |
|---|---|
| Aktif paketi bul | `.claude/active_package` oku |
| Paket kuralları | `ERP/<MODULE>/<PKG>/.rules.md` (prefix, bağımlılık, **Bilinen İstisnalar**) |
| Güncel iş durumu | `ERP/<MODULE>/<PKG>/SESSION_NOTES.md` son entry |
| Sprint / iş listesi | `ERP/<MODULE>/<PKG>/SPRINT_PLAN.md` |
| **Spec kaynağı (conversion/referans)** | `ERP/<MODULE>/<PKG>/ref_docs/` — klasik DDL/struct/program spec'leri, ekran mockup'ları, csv'ler (ADR 0013). Build'de spec kaynağı; gerçek S4 objesi paket kökünde üretilir. Kök = yaşayan, `ref_docs/` = referans. |

Örn. aktif iş ZSD001 SEVKEMRİ → `ERP/SD/ZSD001_CLC/`. Yeni paket başlatılıyorsa:
`python scripts/bootstrap_package.py <PKG_FULL> --title "..."` (T5).

### Karar ağacı — yeni bilgi nereye yazılır?

```
Kapsam tek paket mi?  → evet: ERP/<MODULE>/<PKG>/.rules.md
                       → hayır ↓
Tip ne?  AI davranışı → AGENTS.md · stabil standart → standards/
         operasyonel "nasıl" → playbook/ · mimari karar → governance/decisions/
```

T1–T10 trigger'ları ve 5-saniye self-check için `CLAUDE.md` §3/§5.

---

## KOD GATE'LERİ (bypass yasak)

Tek komut: `python scripts/validators/run_all_validators.py` (`--quick` hızlı).
Sprint gate, TD spec, namespace whitelist, paket naming/sınır, script playbook-ref,
reviewer pre-flight hep buradan. Fail → forward progress YOK, önce düzelt.

---

## OPERASYONEL TUZAKLAR (tekrar eden — yazmadan önce oku)

Bu derslerin tamamı ve script şablonları: **`references/operational-lessons.md`**.
En kritik üçü:

- **TR master-language create:** SAP `masterLanguage="TR"` body attribute'unu ve
  `sap-language` header'ını yok sayar. Tek çalışan yöntem: login (`/discovery`)
  isteğinde `sap-client` + `sap-language=TR` **birlikte query param**. Daha önce EN
  yaratılıp silinmiş isim tekrar EN gelir → farklı isimle doğrula. Her create için ayrı session.
- **Transport disiplini:** numarayı uydurma, hafızadan/önceki context'ten alma,
  **hata mesajındaki transport numarasını ASLA kullanma** (başka geliştiriciye ait
  olabilir). 409/lock conflict → retry YOK (her retry ghost K-type transport yaratır)
  → kullanıcıya bildir, SM12 + SE10 sonrası tek retry.
- **Windows encoding:** konsol `cp1252` Unicode basamaz. Python `print()` ASCII-only
  (`[OK]/[FAIL]/[WARNING]`). Windows yolları raw string (`r'C:\...'`).

Clean-core obje farkındalığı (MARA→I_PRODUCT gibi; on-prem bağlam notuyla):
**`references/clean-core-replacements.md`**.

---

## Referans Dosyaları

- **`references/operational-lessons.md`** — TR create, transport, Windows encoding,
  buffer refresh, ABAP pitfall'ları, idempotent create, aktivasyon notları (script şablonlarıyla).
- **`references/clean-core-replacements.md`** — yasak standart obje → önerilen API/CDS
  eşleme tablosu + clean-core seviyeleri (farkındalık; bu proje on-prem klasik Z kullanır).
