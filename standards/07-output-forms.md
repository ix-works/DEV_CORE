---
applies_to: [s4_private]
layer: L2
scope: project-wide
type: coding-standard
applies-to: output-forms
last-updated: 2026-10-04
source: gap-analysis #C6
---

# Çıktı / Form Standardı — Adobe Forms (+ SmartForms/SAPscript)

> **İş bölümü (kritik):** Adobe Form **layout'u** (Form Builder SFP + Adobe LiveCycle
> Designer) GUI işidir, otomatlanamaz. AI **driver program + interface/context**'i yapar.

## 1. İş bölümü

| Parça | Kim | Araç |
|---|---|---|
| **Layout** (alan yerleşimi, tasarım) | **Operatör** | SFP (Form Builder) + Adobe Designer |
| **Interface** (context, import params, global data) | Operatör (SFP) — AI **spec verir** | SFP interface |
| **Driver program** (veri topla, form çağır, spool/PDF) | **AI (Z program)** | ABAP + FP_* API |
| Veri sağlayan CDS/SELECT/BAPI | AI | standards/05/06 |

> ⚠️ Yeni teknoloji: SAP yeni gelişiminde **Adobe Forms** (SmartForms değil). SAPscript legacy.

## 1b. Yol D — form objesi OLMADAN, AI'ın yazdığı yerleşim (✅ canlı 2026-10-04)

§1'in iş bölümü **SFP form objesi** (SFPF/SFPI) içindir. Belge yalnız PDF olarak (çoğu kez mail eki)
üretilecekse ve Designer'da bakım beklenmiyorsa ikinci bir yol vardır: yerleşimi AI **XFA 3.3 XDP** (düz XML)
olarak yazar, veri XML'i ABAP'ta kurulur, `CL_FP_ADS_UTIL=>RENDER_PDF` ADS'e gönderip PDF xstring alır.
SFPF/SFPI yaratılmaz, standart tabloya yazım yoktur.

| | SFP yolu (§1-§2) | Yol D |
|---|---|---|
| Layout | Operatör, Designer (GUI) | AI, `.xdp` dosyası (repoda, diff'lenebilir) |
| Bakım | Designer'da | Metin düzenleme + yeniden render |
| Çıktı yönetimi (NAST/OM, spool) | Var | Yok — PDF xstring (mail eki / indirme) |
| Ne zaman | Basılı/yasal çıktı, operatör bakımı, output yönetimi | Mail eki, iç belge, hızlı yineleme |

**Kural:** Yol D **kullanıcının açık seçimiyle** açılır (yerleşim AI'da kalır, Designer bakımı yoktur — bunu
kullanıcı bilerek seçer). Reçete + tuzaklar: [`../playbook/howto-pdf-ads-xdp.md`](../playbook/howto-pdf-ads-xdp.md).
Yasal çıktı (e-İrsaliye/e-Fatura) bu yoldan YAPILMAZ (§3).


## 2. Driver program deseni (AI yazar)

```abap
" 1. Form'un generated FM adını bul
CALL FUNCTION 'FP_FUNCTION_MODULE_NAME'
  EXPORTING i_name = 'ZSDxxx_FORM_AD'   " Adobe Form adı
  IMPORTING e_funcname = lv_fm_name.

" 2. ADS job aç
CALL FUNCTION 'FP_JOB_OPEN' CHANGING ie_outputparams = ls_outputparams.

" 3. Generated FM'i çağır (context = interface)
CALL FUNCTION lv_fm_name
  EXPORTING /1bcdwb/docparams = ls_docparams
            is_header = ...  it_items = ...
  IMPORTING /1bcdwb/formoutput = ls_formoutput.   " PDF = ls_formoutput-pdf

" 4. Job kapat
CALL FUNCTION 'FP_JOB_CLOSE'.
```

## 3. Kurallar

- **Interface = sözleşme:** Driver'ın geçtiği parametreler ile SFP interface birebir.
  AI interface'i **spec olarak** verir (alanlar/tipler), operatör SFP'de yaratır.
- **Dil/ülke:** `ls_docparams-langu` (TR), `-country`. Statutory çıktı (Türkiye e-İrsaliye/
  e-Fatura) → **SAP Document Compliance / eDocument** (NAST/output management, gap-analysis #10).
- **PDF:** `ls_formoutput-pdf` (XSTRING) → spool, e-posta eki, veya download. E-posta eki deseni (CL_BCS,
  gönderen politikası, RAP'tan LUW): [`../playbook/howto-abap-email.md`](../playbook/howto-abap-email.md) §1, §7.
- **Hata:** `FP_JOB_OPEN/CLOSE` exception + `cl_fp` / `cx_fp_runtime` yakala; ADS bağlantısı
  (SFP ADS config) operatör/Basis kurar.
- ADR 0005: Z driver program (Z namespace), std output objesine dokunma; NAST config operatör.

## 4. İlgili
- Driver iş mantığı: `standards/06-coding-classic-dialog.md` · Output config: `governance/modules/<MOD>/spro.md` (NACE/NAST)
- Statutory TR: gap-analysis #10 (BOOKING/ORDER sprint'inde)
- Form objesi olmadan PDF (Yol D): [`../playbook/howto-pdf-ads-xdp.md`](../playbook/howto-pdf-ads-xdp.md)
