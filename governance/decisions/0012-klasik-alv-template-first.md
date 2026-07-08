# ADR 0012 — Klasik ALV: Template-First (reusable class DEĞİL)

**Durum:** Kabul edildi (2026-06-03)
**Karar veren:** Kullanıcı (Özgür) — açık talimat
**Bağlam katmanı:** L2 (standart) + L3 (template) — T7
**İlişki:** gap-analysis #C3 (klasik ALV kütüphanesi) yönünü **REVİZE eder**; ADR 0008 (UI5 liste ALV-paritesi) ayrıdır, etkilenmez.

---

## Bağlam

C3 kapsamında klasik ALV için **reusable kütüphane** `ZSD000_CL_ALV_GRID` / `ZSD000_CL_ALV_EVENT` yaratılmıştı (instantiate edilen global class'lar). C1 (ZSD000_P_ALV_TEMP1) entegrasyonunda görüldü ki:

- Klasik ALV'de **field catalog (alan başlıkları/title), hotspot kolonları, event davranışı, özel toolbar/fonksiyon kodları** programdan programa **tamamen farklı** ve **program-spesifik**.
- Bunları reusable bir class'a taşımak, dışarıdan **çok sayıda program-spesifik parametre** (fcat title listesi, hotspot kolon listesi, event callback'leri...) geçirmeyi zorunlu kılar → class'ın arayüzü şişer, kırılganlaşır; inline kodlamaktan **daha çirkin ve bakımı zor**.

## Karar

Klasik ALV kurulumu (field catalog + layout + event handler) **her programda İNLİNE kodlanır** — instantiate edilen reusable class KULLANILMAZ. Standart pattern = programa lokal `lcl_event` (+ gerekirse `lcl_data`/`lcl_alv`) + `lvc_t_fcat`'i TR title/hotspot ile elle kur + `set_table_for_first_display( ... it_fieldcatalog )` + `SET HANDLER`.

**Kanonik template (kopyalanır + özelleştirilir):** [`playbook/templates/classic-alv-list.prog.abap`](../../playbook/templates/classic-alv-list.prog.abap).

`ZSD000_CL_ALV_GRID` / `ZSD000_CL_ALV_EVENT` global class'ları **silindi** (artık template kod referansı, instantiate edilmez).

## Gerekçe

- Program-spesifik konfig (title/hotspot/event/toolbar) inline daha okunur + esnek; parametre yağmuru yok.
- ALV-paritesi (sort/filtre/Excel/kolon-perso) zaten `CL_GUI_ALV_GRID` + `set_table_for_first_display( i_save='A' )` built-in'inden gelir → reusable sarıcıya gerek yok.
- Tutarlılık template ile sağlanır (kanonik kod), yapay soyutlama ile değil.

## Sonuçlar

- `standards/06-coding-classic-dialog.md` §2-§3: template-first; reusable `ZSD000_CL_ALV_*` referansı kaldırıldı; template'e yönlendirir.
- Ekran/GUI status hâlâ AI üretir (`ZSD000_FM_SCREEN_GEN`, playbook §6) — bu karar yalnız ALV-kurulum katmanını değiştirir.
- Hiyerarşik/tree liste (eski C3 tree ayağı) gerekirse: o da **template** olarak (lcl + CL_GUI_ALV_TREE inline), reusable class değil.
- Çalışan örnek: `ZSD000_P_ALV_TEMP1` (template inline; fcat TR title + VBELN hotspot + lcl_event).
