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

> **Field catalog — DDIC-structure mi, manuel `lvc_t_fcat` mi? (SHOULD — ÖNCE SOR):** fcat'i DOĞRUDAN
> kurmadan önce kullanıcıya **SOR** ("structure ile mi, manuel mi?") ya da **TS'te belirt + gerekçelendir**
> (std04 §4.5). **Structure-merge TERCİH** — tipli/kompleks grid: miktar+birim ondalık, para+PB, çok kolon,
> kod→tanım (açıklama) kolonları, tekrar-kullanım. Program-özel `Z…_S_…` structure + `set_table_for_first_display(
> i_structure_name = … )` / `LVC_FIELDCATALOG_MERGE` → sonra yalnız title/hotspot/`no_out`/edit tweak. DDIC
> tipleri + **QUAN birim-referansı (ondalık)** + CURR referansı OTOMATİK → manuel hata kaynağı (yanlış ondalık,
> eksik tanım kolonu, kısa genişlik) kapanır. **Manuel meşru:** basit/az-kolon/ad-hoc rapor. Detay + gerekçe:
> [ADR 0012 "Karar Rafinasyonu (2026-07-13)"](../governance/decisions/0012-klasik-alv-template-first.md).

> **ALV event'lerinde SATIR KİMLİĞİ = `es_row_no-row_id` (MUST).** `hotspot_click`/`double_click`
> handler'ında iç tabloyu `READ TABLE … INDEX es_row_no-row_id` ile oku; **`e_row-index` /
> `e_row_id-index` KULLANILMAZ.** Gerekçe: `LVC_S_ROW` (`e_row`/`e_row_id`) = `INDEX` + **`ROWTYPE`**
> — `ROWTYPE` satırın ara-toplam/toplam satırı olabileceğini söyler; `do_sum`, sıralama veya filtre
> etkinken `INDEX` artık iç tablo indeksi değildir → yanlış satır okunur ya da toplam satırında
> sessiz no-op olur. `LVC_S_ROID` (`es_row_no`) = **`ROW_ID`** = çıktı tablosu satır numarası.
> Handler imzasına `es_row_no`'yu **eklemeyi unutma** (event onu sunar). Sözdizimi doğru olduğu
> için **aktivasyon/ATC/abaplint hepsi geçer** — hata yalnız sıralı/toplamlı gridde görülür.
> Kanonik hâli template'te hazırdır ([`classic-alv-list.prog.abap`](../playbook/templates/classic-alv-list.prog.abap));
> denetim: `playbook/checklists/bug-checklist-backend.md` **BE-63**.

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
- **İSTİSNA — kanonik klasik-ALV template (ADR 0012; kullanıcı kararı 2026-08-01):**
  `playbook/templates/classic-alv-list.prog.abap` ve ondan türeyen programların **iskelet
  etiketleri** (fieldcat/başlık gibi template-çekirdeği) inline kalabilir — template
  canlı-çalışan kanıtlanmış örnektir (ZSD000_P_ALV_TEMP1 ailesi), master dil projenin
  `master_language`'i ve tek-dilli çalışılıyor; salt bu kural için şablonu değiştirmek
  risk/maliyet üretir. **Seçim-ekranı metinleri istisnaya DAHİL DEĞİL** — onlar
  selection-text ile yazılır (canlı pratik: paket `programs/textpool/` örnekleri).
  Template ileride başka sebeple revize edilirse text-element'e geçiş o pakette değerlendirilir.
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
- **Seçim-ekranı adları ≤ 8 KARAKTER (SAP sınırı) → `SELECT-OPTIONS s_<ad>` · `PARAMETERS p_<ad>`.**
  9+ karakterli ad aktivasyonda reddedilir; `so_`/`pa_` önekleri 8'i kolayca aşar (`so_docnum` = 9 karakter).
  Statik kontroller (abaplint / run_review / bug-gate) GEÇER — yalnız canlı aktivasyon yakalar
  (kanıt: klasik JOB programı build 2026-07-14; `so_*` → `s_*` rename gerekti). Checklist: `BE-58`.

## 7. ADR 0005 klasik yüzeyi

- Std tabloya direkt `INSERT/UPDATE/MODIFY` YASAK → BAPI/RFC (modül `bapi.md`).
- Std program/exit/screen değiştirme YASAK; Z program + Z include.
- Z text TR (§5). Transport kullanıcının verdiği aktif TR'ye (yaratma yok).

## 9. Datafield'lı diyalog ekranı (modal form) + DDIC bağlama + F4 karar tablosu

> **Ne zaman bu bölüm?** Ekran çok-satır bir liste/rapor DEĞİL, DDIC yapıya bağlı data-field'lardan
> oluşan TEK KAYITLIK modal form (düzeltme/ekleme/transfer diyaloğu). Liste ekranı için §3 (ALV)
> geçerlidir; ikisi aynı programda bir arada olabilir (liste + ondan açılan diyaloglar).
> **Kanonik şablon:** [`playbook/templates/classic-dynpro-dialog.prog.abap`](../playbook/templates/classic-dynpro-dialog.prog.abap).
> **Derin referans (karar ağacı + tuzak → aksiyon tablosu):**
> [`playbook/howto-classic-dynpro-datafield-screens.md`](../playbook/howto-classic-dynpro-datafield-screens.md).

**DDIC bağlama (MUST):** diyalog ekranının data-field'ları program-lokal `gs_*` struct + elle
`MOVE-CORRESPONDING` köprüsü ile DEĞİL, **DDIC yapıya doğrudan bağlanarak** (`FROM_DICT='X'`,
ekran-tarafı `MATCHCODE` BOŞ) kurulur. Global work area'nın adı DDIC yapı adıyla aynı olmalı
(`DATA zsd001_s_dlg TYPE zsd001_s_dlg.`) — ekran alanları `<YAPI>-<ALAN>` diye adreslenir.
Kazanç: etiket/uzunluk/`CONVERSION_EXIT`/arama-yardımı DDIC'ten gelir, elle senkron gerekmez.

**Dinamik alan kilidi (SHOULD):** kapsam-içi bir kayıt otomatik dolduruluyorsa alan `LOOP AT
SCREEN` ile PBO'da kilitlenir (`screen-input = 0`); kapsam-dışıysa giriş-etkin bırakılır
(regresyon yok). Çağrı **PBO'da** olmak zorundadır (PAI'de sessiz kayıp).

**Ekran-başına AYRI fcode (MUST):** fonksiyon tanımının metin+quickinfo'su **program-genelidir**,
ekran-bazlı DEĞİL. İki diyalog ekranı aynı kaydet/iptal fcode'unu paylaşırsa, quickinfo'su
ikisinde birden doğru OLAMAZ — her diyalog ekranı **kendi** fcode'unu taşır.

**F4 karar tablosu (özet — detay `howto-classic-dynpro-datafield-screens.md` §2):**

| Mekanizma | Ne zaman | Maliyet |
|---|---|---|
| DTEL'e bağlı standart SHLP | Data element zaten bağlıysa | Bedava |
| Yapı bileşenine `with value help` attachment | Standart SHLP mantıksal uyuyor ama DTEL'de yok | Düşük — DDIC yapı değişikliği + ekran **regen** |
| Buton + popup (`REUSE_ALV_POPUP_TO_SELECT`) | Süzgeç gerekli VE Z SHLP gerekirdi | Orta — Z SHLP **yaratılamaz** (araç sınırı), bu tek yol |
| POV modülü | Veriye bağlı süzgeç | Bu üreteçte **desteklenmiyor** — buton+popup ile telafi |

⚠ **Attachment bileşene yapılır, ekran alan adına değil** — aynı yapıda aynı tipten iki alan
varsa (ör. iki `lgort_d`) attachment tek yoldur, isim-eşleşmesi yeterli değildir. ⚠ Ekrandaki
elle `MATCHCODE` DDIC attachment'ın önüne geçer — yeni ekranda `MATCHCODE` boş bırakılır.
⚠ Bir DDIC objesini değiştirmek, onu generate-anında gömen ekranı otomatik güncellemez —
**regen** ayrı bir adımdır, baştan plana konur.

## 10. İlgili
- ALV (klasik): **ADR 0012 template-first** → `playbook/templates/classic-alv-list.prog.abap` (örnek `ZSD000_P_ALV_TEMP1`). Ekran/status üretimi: `playbook/adt-fugr-functions.md` §6. Adobe çıktı: `standards/07-output-forms.md`
- Datafield diyalog: `playbook/templates/classic-dynpro-dialog.prog.abap` · `playbook/howto-classic-dynpro-datafield-screens.md`
- İskelet üretimi: `scripts/scaffold_classic_program.py` · RAP karşılaştırma: `standards/05`
- Modül semantiği: `governance/modules/<MOD>/`
