---
applies_to: [s4_private]
---
# Checklist — Klasik Dialog Program (report / module pool / Dynpro / ALV) Oluşturma

> **Manuel pre-flight.** Yeni klasik program yazmaya başlamadan / push öncesi bu liste
> **elle** geçilir. Klasik dialog için otomatik reviewer task'ı (henüz) yok → bu checklist
> kör noktaları kapatır (std 06'daki ~7 ZORUNLU kuralın unutulmaması; özellikle CLC-07
> include-bölme — 2026-06-03'te tek-body yazılıp unutuldu, bkz. lessons-learned PATTERN #8).
>
> **Standart:** [`../../standards/06-coding-classic-dialog.md`](../../standards/06-coding-classic-dialog.md) ·
> **Üreteç/CUA reçetesi:** [`../adt-fugr-functions.md`](../adt-fugr-functions.md) §6 ·
> **ALV deseni:** [`../templates/classic-alv-list.prog.abap`](../templates/classic-alv-list.prog.abap)

---

## Faz 1 — Yapı (kod yazmadan)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| CLC-07 | **Tek-body YAZMA.** Kod include'lara bölündü mü? main = `INCLUDE`'lar + event blokları; `ZSD<pkg>_I_<PRG>_T01`(TOP)/`_C01`(CLS)/`_O01`(PBO)/`_I01`(PAI)/`_F01`(FORM), **PROG/I** objeleri | BLOCKER | std 06 §1 |
| CLC-NAM | Program `ZSD<pkg>_P_*`, include'lar `ZSD<pkg>_I_<PRG>_<X>01`, class `ZSD<pkg>_CL_*` | BLOCKER | std 01 / .rules.md |

## Faz 2 — ALV (template-first)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| CLC-ALV1 | ALV kurulumu (field catalog TR-title + hotspot, event, layout) programa **İNLİNE** (lcl_event + `lvc_t_fcat`) — reusable `ZSD000_CL_ALV_*` class KULLANILMADI (silindi) | BLOCKER | ADR 0012 |
| CLC-ALV2 | Field catalog kolon başlıkları (`coltext`) **TR ve tam** | BLOCKER | ADR 0005-D |
| CLC-ALV3 | Liste ekranı = CL_GUI_ALV_GRID built-in (sort/filtre/Excel/kolon-perso) — ALV-paritesi otomatik | WARNING | ADR 0008 |

## Faz 3 — Ekran + GUI status (AI üretir)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| CLC-SCR1 | Screen + STAT<n>/TIT<n> **`ZSD000_FM_SCREEN_GEN`** ile üretildi (SOAP-RFC, dialog; classrun YAPAMAZ — "Session Timed Out"). Operatöre SE51/SE41 GEREKMEZ | BLOCKER | playbook §6 |
| CLC-SCR2 | CONTAINER: screen 200x255 + CUST_CTRL `element_of` BOŞ + `c_resize_v/h='X'` + `c_line_min/c_coln_min=1` (resize) | BLOCKER | §6.1.1 |
| CLC-SCR3 | Split = tek CC + `cl_gui_splitter_container` (kodda), 2 container DEĞİL | WARNING | §6.1.2 |
| CLC-SCR4 | Toolbar/menü temiz: `men`/`mtx`/`but` REFRESH; **`act` KORU** (yoksa `00256` geçersiz fonksiyon) | WARNING | §6.1.2 |
| CLC-SCR5 | BACK/EXIT/CANCEL + ESC çalışır (normal type + `user_command`; ESC=F12=CANCEL). RS_CUA_WRITE sonrası **GENERATE** şart (yoksa `00264`). **Navigasyon hedefi:** BACK/CANCEL → seçim ekranı (`LEAVE TO SCREEN 0`), EXIT → `LEAVE PROGRAM`; BACK'te `LEAVE PROGRAM` = ana-menüye atlama = BLOCKER | BLOCKER | §6.1.2 / §4 |

## Faz 4 — Metin + ADR 0005

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| CLC-TXT | TEXT-xxx / selection text / GUI title **TR ve text-element** (literal gömme YASAK). `adt_textpool` (push_source text pool'u kapsamaz) | BLOCKER | std 06 §5 |
| CLC-005 | Std tabloya direkt INSERT/UPDATE/MODIFY YASAK → BAPI/RFC; std program/exit/screen değiştirme YASAK; transport kullanıcının verdiği aktif TR | BLOCKER | ADR 0005 |

---

> **NOT — şablonlar istisna:** `ZSD000_P_ALV_TEMP1/2/3` kasıtlı **tek-body** (sadece ALV/screen-gen deseni). CLC-07 gerçek programlar için.
