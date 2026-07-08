# Checklist — Adobe Forms Çıktı (driver + interface spec) Oluşturma

> **Puan-flight.** Adobe Form işine başlarken geçilir. Layout SAP-yazması DEĞİL (operatör/GUI işi)
> → otomatik reviewer gate yok; bu checklist elle geçilir. AI **driver + interface spec** yapar.
>
> **Standart:** [`../../standards/07-output-forms.md`](../../standards/07-output-forms.md) ·
> **Driver iş mantığı:** [`../../standards/06-coding-classic-dialog.md`](../../standards/06-coding-classic-dialog.md)

---

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| AF-DIV-01 | **İş bölümü:** Layout (SFP Form Builder + Adobe Designer) + Interface = **OPERATÖR** (GUI). AI bunları YAPMAZ | BLOCKER | std 07 §1 |
| AF-DIV-02 | AI yapar: **driver program** (veri topla → form çağır → spool/PDF) + **interface'i SPEC olarak** ver (alanlar/tipler) — operatör SFP'de yaratır | BLOCKER | std 07 §1 |
| AF-IF-01 | **Interface = sözleşme:** driver'ın geçtiği parametreler ↔ SFP interface **birebir** (ad/tip). Spec netleştirilmeden driver yazma | BLOCKER | std 07 §3 |
| AF-DRV-01 | Driver `FP_*` API deseni: `FP_JOB_OPEN` → `FP_FUNCTION_MODULE_NAME` → call → `FP_JOB_CLOSE`; `ls_outputparams`/`ls_docparams` | WARNING | std 07 §2 |
| AF-DRV-02 | Dil/ülke: `ls_docparams-langu = 'TR'`, `-country`; statutory çıktı TR (e-İrsaliye/e-Fatura/GİB) gerekiyorsa #10-TR ref | WARNING | std 07 §3 |
| AF-DRV-03 | PDF: `ls_formoutput-pdf` (XSTRING) → spool / e-posta eki / download (ihtiyaca göre) | WARNING | std 07 §3 |
| AF-NAM-01 | Driver program `ZSD<pkg>_P_*`, klasik program ise include'lara böl (std 06 §1) | BLOCKER | std 01 / std 06 §1 |
| AF-005 | Z driver (Z namespace); **standart output objesine dokunma**; NAST/NACE/ADS config = operatör/Basis | BLOCKER | ADR 0005 |
