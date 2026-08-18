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
| CLC-SCR6 | **DONÖR AÇIKÇA verildi** (`IV_SRC_PROG`/`IV_SRC_STATUS`) ve `EV_MESSAGE`'da `nav_remap=ON(F3/Sh+F3/F12->BACK/EXIT/CANCEL)` GÖRÜLDÜ. `nav_remap=OFF` → çağrı yanlış, ekran KULLANILMADAN düzeltilir (varsayılan minimal donör `&F2..&F5` üretir; `WHEN 'BACK'` bekleyen PAI yakalamaz) | BLOCKER | howto-dynpro §2.1 |
| CLC-SCR7 | Üreteç kılavuzundaki `<!-- FM-IMZA -->` bloğu FM kaynağıyla SENKRON (parametre eklendi/kaldırıldıysa kılavuz aynı turda güncellendi) | WARNING | `check_fm_signature_doc_sync.py` (warn-first) |
| CLC-SCR5 | BACK/EXIT/CANCEL + ESC çalışır (normal type + `user_command`; ESC=F12=CANCEL). RS_CUA_WRITE sonrası **GENERATE** şart (yoksa `00264`). **Navigasyon hedefi:** BACK/CANCEL → seçim ekranı (`LEAVE TO SCREEN 0`), EXIT → `LEAVE PROGRAM`; BACK'te `LEAVE PROGRAM` = ana-menüye atlama = BLOCKER | BLOCKER | §6.1.2 / §4 |

## Faz 4 — Metin + ADR 0005

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| CLC-TXT | TEXT-xxx / selection text / GUI title **TR ve text-element** (literal gömme YASAK). `adt_textpool` (push_source text pool'u kapsamaz) | BLOCKER | std 06 §5 |
| CLC-005 | Std tabloya direkt INSERT/UPDATE/MODIFY YASAK → BAPI/RFC; std program/exit/screen değiştirme YASAK; transport kullanıcının verdiği aktif TR | BLOCKER | ADR 0005 |

## Faz 5 — Datafield diyalog ekranı (modal form — liste DEĞİL)

> Yalnız ekran DDIC yapıya bağlı data-field'lardan oluşan TEK KAYITLIK modal form ise geçerli
> (düzeltme/ekleme/transfer diyaloğu). Şablon: [`../templates/classic-dynpro-dialog.prog.abap`](../templates/classic-dynpro-dialog.prog.abap) ·
> Derin referans: [`../howto-classic-dynpro-datafield-screens.md`](../howto-classic-dynpro-datafield-screens.md).

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| CLC-DLG1 | Data-field'lar DDIC yapıya bağlı (`FROM_DICT='X'`, ekran `MATCHCODE` BOŞ) — elle `gs_*` program-lokal struct + `MOVE-CORRESPONDING` köprüsü YOK | BLOCKER | std 06 §9 |
| CLC-DLG2 | Dinamik alan kilidi (`LOOP AT SCREEN`) varsa çağrı **PBO'da** (PAI'de sessiz kayıp) | BLOCKER | howto §1 |
| CLC-DLG3 | Her diyalog ekranı **kendi** kaydet/iptal fcode'unu taşıyor — birden çok ekran aynı fcode'u paylaşmıyor (paylaşırsa quickinfo çakışır) | BLOCKER | howto §3.3 |
| CLC-DLG4 | F4 mekanizması karar tablosuna göre seçildi (DTEL-std → attachment → buton+popup → POV-yok); Z SHLP **denenmedi** (araç sınırı) | WARNING | std 06 §9 F4 tablosu |
| CLC-DLG5 | Attachment kullanılıyorsa `where` bloğu parametre eşlemesini AÇIKÇA veriyor (aynı tipte 2. alan varsa özellikle) | BLOCKER | howto §2.2 |
| CLC-DLG6 | CUA turu: `BUT` deltası **yazmadan önce** hesaplandı + tur-başı sayaçla kıyaslandı; final `FUNDTL` diff alındı (kaybolan fcode yok) | BLOCKER | howto §3.5 / §4 |
| CLC-DLG7 | DDIC yapı değişti VE ekran daha önce üretilmişti ise **regen** adımı planlandı (obje aktif ≠ tüketici güncel) | BLOCKER | howto §2.2 |
| CLC-DLG8 | Her giriş alanının **AYRI `TYPE='TEXT'` etiket satırı** var (`FROM_DICT='X'` + `TEXT` BOŞ → metin DDIC'ten). Giriş alanı kendi etiketini GETİRMEZ; eksikliği SESSİZDİR (FM uyarı vermez) | BLOCKER | howto §1.1 |

---

> **NOT — şablonlar istisna:** `ZSD000_P_ALV_TEMP1/2/3` kasıtlı **tek-body** (sadece ALV/screen-gen deseni). CLC-07 gerçek programlar için. `classic-dynpro-dialog.prog.abap` da aynı istisnaya tabidir (Faz 5 gerçek diyalog programları için).
