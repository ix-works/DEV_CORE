---
applies_to: [s4_private]
layer: L2
scope: project-wide
type: coding-standard
applies-to: output-forms
last-updated: 2026-06-02
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
- **PDF:** `ls_formoutput-pdf` (XSTRING) → spool, e-posta eki, veya download.
- **Hata:** `FP_JOB_OPEN/CLOSE` exception + `cl_fp` / `cx_fp_runtime` yakala; ADS bağlantısı
  (SFP ADS config) operatör/Basis kurar.
- ADR 0005: Z driver program (Z namespace), std output objesine dokunma; NAST config operatör.

## 4. İlgili
- Driver iş mantığı: `standards/06-coding-classic-dialog.md` · Output config: `governance/modules/<MOD>/spro.md` (NACE/NAST)
- Statutory TR: gap-analysis #10 (BOOKING/ORDER sprint'inde)
