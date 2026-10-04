---
applies_to: [s4_private]
---
# Checklist — Adobe Forms Çıktı (driver + interface spec) Oluşturma

> **Puan-flight.** Adobe Form işine başlarken geçilir. Layout SAP-yazması DEĞİL (operatör/GUI işi)
> → otomatik reviewer gate yok; bu checklist elle geçilir. AI **driver + interface spec** yapar.
>
> **Hangi tablo?** **SFP yolu** (form objesi var) → ilk tablo. **Yol D** (form objesi yok, AI XDP yazar — std 07 §1b)
> → ikinci tablo + ilk tablodan yalnız **AF-005**; AF-DIV-02 · AF-IF-01 · AF-DRV-01..03 · AF-NAM-01 SFP'ye özgüdür,
> Yol D'de **uygulanmaz** (interface/driver programı yoktur; çağıran Z sınıf/FM projenin genel adlandırmasına uyar).
>
> **Standart:** [`../../standards/07-output-forms.md`](../../standards/07-output-forms.md) ·
> **Driver iş mantığı:** [`../../standards/06-coding-classic-dialog.md`](../../standards/06-coding-classic-dialog.md)

---

**SFP yolu:**

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| AF-DIV-01 | **İş bölümü:** Layout (SFP Form Builder + Adobe Designer) + Interface = **OPERATÖR** (GUI). AI bunları YAPMAZ. **İstisna:** kullanıcının açıkça seçtiği **Yol D** (form objesi yok; AI XDP yazar — std 07 §1b) — bu satır SFP form objesi içindir | BLOCKER | std 07 §1 · §1b |
| AF-DIV-02 | AI yapar: **driver program** (veri topla → form çağır → spool/PDF) + **interface'i SPEC olarak** ver (alanlar/tipler) — operatör SFP'de yaratır | BLOCKER | std 07 §1 |
| AF-IF-01 | **Interface = sözleşme:** driver'ın geçtiği parametreler ↔ SFP interface **birebir** (ad/tip). Spec netleştirilmeden driver yazma | BLOCKER | std 07 §3 |
| AF-DRV-01 | Driver `FP_*` API deseni: `FP_JOB_OPEN` → `FP_FUNCTION_MODULE_NAME` → call → `FP_JOB_CLOSE`; `ls_outputparams`/`ls_docparams` | WARNING | std 07 §2 |
| AF-DRV-02 | Dil/ülke: `ls_docparams-langu = 'TR'`, `-country`; statutory çıktı TR (e-İrsaliye/e-Fatura/GİB) gerekiyorsa #10-TR ref | WARNING | std 07 §3 |
| AF-DRV-03 | PDF: `ls_formoutput-pdf` (XSTRING) → spool / e-posta eki / download (ihtiyaca göre) | WARNING | std 07 §3 |
| AF-NAM-01 | Driver program `ZSD<pkg>_P_*`, klasik program ise include'lara böl (std 06 §1) | BLOCKER | std 01 / std 06 §1 |
| AF-005 | Z driver (Z namespace); **standart output objesine dokunma**; NAST/NACE/ADS config = operatör/Basis | BLOCKER | ADR 0005 |

**Yol D (XDP + `CL_FP_ADS_UTIL=>RENDER_PDF`)** ([`../howto-pdf-ads-xdp.md`](../howto-pdf-ads-xdp.md)) — ilk tablodan yalnız AF-005 ile birlikte:

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| AF-XDP-01 | Yol D kullanıcının **açık seçimi** (Designer bakımı olmayacağı söylendi); yasal çıktı DEĞİL | BLOCKER | std 07 §1b |
| AF-XDP-02 | `.xdp` + örnek veri `.xml` repoda kaynak; ABAP'taki kopya **üretici script**le üretilir ve `--check` ile güncel (elle kopya YOK) | WARNING | howto §3.5 |
| AF-XDP-03 | **Çok kolonlu tablo satırlarında** (`lr-tb`) kolon toplamı kapsayıcıdan **1 mm küçük** (eşitken 11 kolonlu satırda son kolon kaydı; kasıtlı sarılan kart ızgaraları hariç) | WARNING | howto §3.1 |
| AF-XDP-04 | Büyük harfli sabit etiketlerde yabancı sözcük `İ` taraması (`BOOKİNG` ✗) | WARNING | howto §3.2 |
| AF-XDP-05 | `typeface="Arial"` + `embed_fonts = abap_true`; locale = projenin yerel ayarı (TR projede `tr_TR`) | BLOCKER | howto §1, §3.4 |
| AF-XDP-06 | Deneme koşusunda `ev_pages` beklenenle aynı **ve** PDF açılıp gözle okundu (bayt/sayfa yerleşim kusurunu söylemez) | BLOCKER | howto §3.6 |
| AF-XDP-07 | Mail gönderen deneme koşusu **tek POST** (yeniden deneyen araç YOK); deneme sınıfı iş bitince silinir | WARNING | howto §4, §5 |
