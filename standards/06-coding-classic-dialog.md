---
applies_to: [s4_private]
layer: L2
scope: project-wide
type: coding-standard
applies-to: classic-dialog
last-updated: 2026-06-29
source: gap-analysis #C2 (sc4sap common/ desenleri + <LEGACY_SOURCE> SEVKEMRİ klasik dialog)
---

# Klasik Dialog ABAP — Kodlama Standardı (report / module pool / Dynpro / ALV)

> **Ne zaman klasik?** standards/05 §2: Z transactional doküman + RAP uygunsa → RAP.
> Liste/rapor, klasik GUI ekranı, Adobe çıktısı, eski <LEGACY_SOURCE> paritesi → **klasik dialog**.
> RAP + freestyle UI5 değil, SAP GUI tarafı (Dynpro + CL_GUI_ALV_GRID).
>
> ⚠️ **Bu standart şu an GENERIC** (genel ABAP/sc4sap deseni). Task'ta "<LEGACY_SOURCE> source'larından
> damıt" vardı ama **<LEGACY_SOURCE>/SEVKEMRİ source'ları bu checkout'ta yok** → damıtılamadı. <LEGACY_SOURCE>
> source'ları geldiğinde gerçek desenlerle **refine et** (deferred-trigger register).

## 1. Include yapısı (ZORUNLU — tüm kod tek body'de OLMAZ)

Klasik program tüm kodu tek REPORT body'sinde tutmaz; **include'lara bölünür**. **Main program** sadece `INCLUDE` ifadeleri + event blokları (`START-OF-SELECTION`, `INITIALIZATION`, ...) içerir.

**İsimlendirme (KARAR 2026-06-03):** include = programın `_P_`'si yerine `_I_` (Include) + tip-suffix `_<X>01`:

```
ZSD<pkg>_P_<PRG>                  (Main / REPORT — INCLUDE'lar + event blokları)   ör: ZSD000_P_SIPARIS
  ├ ZSD<pkg>_I_<PRG>_T01   (TOP)  — TABLES, TYPES, DATA, CONSTANTS, SELECT-OPTIONS, CLASS DEFINITION
  ├ ZSD<pkg>_I_<PRG>_C01   (CLS)  — CLASS IMPLEMENTATION (LCL_*)
  ├ ZSD<pkg>_I_<PRG>_F01   (F01)  — FORM rutinleri (iş mantığı)
  ├ ZSD<pkg>_I_<PRG>_O01   (O01)  — PBO modülleri (MODULE ... OUTPUT: SET PF-STATUS/TITLEBAR)
  ├ ZSD<pkg>_I_<PRG>_I01   (I01)  — PAI modülleri (MODULE ... INPUT: user_command)
  └ ZSD<pkg>_I_<PRG>_S01   (S01)  — selection-screen events (opsiyonel)
```
> Not: `ZSD000_P_ALV_TEMP1/2/3` şablonları **tek-body** bırakıldı (sadece ALV/screen-gen deseni gösterir); GERÇEK programda kod yukarıdaki gibi include'lara bölünür.
- Tip harfi: **T**op / **C**ls / **O**utput-PBO / **I**nput-PAI / **F**orm / **S**election. Sıra no `01` (büyük include → 02, 03...).
- Include'lar **INCLUDE objesi (PROG/I)** olarak yaratılır (standalone program değil). Repo: `programs/includes/<NAME>.prog.abap`.
- ⚠️ `ZSD000_I_*` prefix'i CDS view-entity ile paylaşılır (ADR 0009 / .rules.md); include'lar suffix (`_T01/_C01...`) + klasör (programs/includes) ile ayrışır — kullanıcı kararı (2026-06-03).
- Main minimal. Modülerleştirme: iş mantığı **FORM** veya tercihen **OO** (LCL_* — aşağı).

## 2. OO pattern (tercih) — LCL_DATA + LCL_ALV + LCL_EVENT

| Sınıf | Sorumluluk |
|---|---|
| `LCL_DATA` (veya `LCL_MODEL`) | Veri okuma/iş mantığı (SELECT, hesap) |
| `LCL_ALV` | ALV grid kurulumu (field catalog, layout, toolbar) |
| `LCL_EVENT` (handler) | ALV event'leri (double_click, user_command, toolbar) |
| `LCL_APP` / controller (singleton) | Akış orkestrasyonu (<LEGACY_SOURCE> `lcl_main_controller` deseni) |

> ⭐ **TEMPLATE-FIRST (ADR 0012):** ALV kurulumu (field catalog TR title + hotspot, layout,
> event) **programa İNLİNE** kodlanır — reusable `ZSD000_CL_ALV_*` class KULLANILMAZ (silindi;
> program-spesifik title/hotspot/event'i dışarıdan parametrelemek class'ı şişirir).
> **Kanonik template (kopyala+özelleştir):** [`playbook/templates/classic-alv-list.prog.abap`](../playbook/templates/classic-alv-list.prog.abap). Çalışan örnek: `ZSD000_P_ALV_TEMP1`.

## 3. ALV kuralı (CL_GUI_ALV_GRID + Docking vs SALV)

| Senaryo | Araç |
|---|---|
| Salt-okunur liste, basit | **SALV factory** (`CL_SALV_TABLE`) — hızlı, az kod |
| Editable / toolbar / hücre event / kolon-perso | **CL_GUI_ALV_GRID** + `CL_GUI_DOCKING_CONTAINER` |

**Liste ekranı ALV-paritesi (her liste — OTOMATİK):** kolon-başlığı sort/filtre + filtre çubuğu +
Kolonlar göster/gizle + Excel export. Klasik ALV'de bunlar `CL_GUI_ALV_GRID` +
`set_table_for_first_display( i_save = 'A' )` **built-in**'inden gelir (template'te hazır) — reusable sarıcı gerekmez. (UI5 tarafı ayrı: ADR 0008 / TablePersonalizer.js.)

## 4. Dynpro / GUI status — AI ÜRETİR (C1 TAMAM, 2026-06-03)

> ⭐ **Klasik Dynpro ekranı + GUI status artık AI tarafından üretiliyor** — operatör SE51/SE41 ŞART DEĞİL.
> Yeni klasik dialog/ALV programı yazınca **bu flow'u öner ve uygula**. Tam reçete: [`playbook/adt-fugr-functions.md`](../playbook/adt-fugr-functions.md) §6.

**Üreteç:** `ZSD000_FM_SCREEN_GEN` (RFC FM, FG `ZSD000_FG_SCREEN_GEN`). `/sap/bc/soap/rfc` (dialog context, `sap-language=TR`) ile çağrılır; tek çağrıda:
1. `RPY_DYNPRO_INSERT` → boş Dynpro (screen) + PBO/PAI flow logic.
2. `RS_CUA_INTERNAL_FETCH`(standart donör) → prune+retarget → `RS_CUA_INTERNAL_WRITE` → `RS_CUA_GENERATE` → GUI status + titlebar. fcode'ları programın PAI'sine map'le (F3→BACK, Shift+F3→EXIT, F12→CANCEL).

**KRİTİK (playbook §6):** classrun bunu YAPAMAZ (dialog şart → "Session Timed Out") → RFC FM + SOAP-RFC; `RS_CUA_INTERNAL_WRITE` sonrası `RS_CUA_GENERATE` ŞART (yoksa runtime `00264`); SOAP-RFC'de `sap-language` ŞART. Üreteç RFC-enable bir-kerelik SE37.

**Program tarafı (Z source, normal):**
- PBO: `MODULE status_xxxx OUTPUT` (SET PF-STATUS / SET TITLEBAR). PAI: `MODULE user_command_xxxx INPUT`.
- `OK_CODE` / `SY-UCOMM` → `CASE` ile dağıt (BACK/EXIT/CANCEL). *(dispatch deseni — SHOULD)*
- **`CLEAR ok_code` ZORUNLU** (CASE değerlendirmesi sonrası): atlanırsa sticky-komut tuzağı (önceki UCOMM bir sonraki PAI'de tekrar tetiklenir). *(MUST — denetlenebilir: PAI/INPUT module'de `ok_code` okunuyor ama `CLEAR ok_code`/`CLEAR sy-ucomm` yok → ihlal; regex-gate adayı.)*
- **Navigasyon hedefi (MUST):** BACK(F3)/CANCEL(F12) → seçim ekranına dön (`LEAVE TO SCREEN 0`); EXIT(Shift+F3) → `LEAVE PROGRAM`. BACK/CANCEL'da `LEAVE PROGRAM` = ana-menüye atlama tuzağı, YASAK. Executable report'ta `LEAVE TO SCREEN 0`, CALL SCREEN'den START-OF-SELECTION'a döner → runtime seçim ekranına döner.

## 5. Text element / selection text (TR-master — gap-analysis #C4, ADR 0005-D)

- **Tüm metinler text element/selection text** olarak (literal gömme YASAK — constants rule).
- TEXT-xxx, selection texts, GUI title, status text → **TR ve tam**. ADR 0005-D: Z text TR.
- **Two-pass dil kuralı:** create EN gelirse → TR'ye senkronla; master = TR
  ([[feedback_mcp-post-shell-en-master-lang]]).
- **⚠️ TEYİT EDİLDİ (2026-06-02): `push_source` text pool'u KAPSAMAZ** — sadece `source/main`.
  Text element'ler/selection text'ler **ayrı endpoint**tedir:
  `/sap/bc/adt/textelements/{programs|classes}/<obj>` (GET Accept=application/* → `<rept:textElement>`;
  yazmak için PUT). Yani TEXT-xxx / selection text'li bir obje için **`adt_textpool` tool gerekir**
  (push_source yetmez). Şu an objelerimizde text element yok (sadece ABAP Doc açıklama = source/main'de).
  → `adt_textpool` tool, **text element'li ilk klasik program**da yapılacak (deferred-trigger register).

## 6. Constants / magic literal

- Magic sayı/string YASAK → `CONSTANTS` veya text element. `c_*` (constant), `gv_/lv_` (global/local var),
  `gt_/lt_` (tablo), `gs_/ls_` (struct), `go_/lo_` (obje ref). Naming: standards/01.

## 7. ADR 0005 klasik yüzeyi

- Std tabloya direkt `INSERT/UPDATE/MODIFY` YASAK → BAPI/RFC (modül `bapi.md`).
- Std program/exit/screen değiştirme YASAK; Z program + Z include.
- Z text TR (§5). Transport kullanıcının verdiği aktif TR'ye (yaratma yok).

## 8. İlgili
- ALV (klasik): **ADR 0012 template-first** → `playbook/templates/classic-alv-list.prog.abap` (örnek `ZSD000_P_ALV_TEMP1`). Ekran/status üretimi: `playbook/adt-fugr-functions.md` §6. Adobe çıktı: `standards/07-output-forms.md`
- İskelet üretimi: `scripts/scaffold_classic_program.py` · RAP karşılaştırma: `standards/05`
- Modül semantiği: `governance/modules/<MOD>/`
