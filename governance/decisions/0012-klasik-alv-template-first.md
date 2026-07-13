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

---

## Karar Rafinasyonu (2026-07-13) — Field catalog: DDIC-structure mi, manuel mi? (ÖNCE SOR)

**Karar veren:** Kullanıcı — açık talimat (canlı Excel-upload ALV dersi).

Yukarıdaki "inline `lvc_t_fcat` elle kur", **her kolonu elle yazmak zorunlu** demek DEĞİLDİR. Field
catalog iki yolla kurulabilir — **ikisi de ADR 0012'ye uygundur** (inline, program-lokal; reusable
wrapper class DEĞİL):

1. **DDIC-structure-merge (tipli/kompleks grid için TERCİH):** program-özel bir Z output structure
   (`Z…_S_…`) tanımla → `set_table_for_first_display( i_structure_name = 'Z…_S_…' )` **veya**
   `LVC_FIELDCATALOG_MERGE( i_structure_name = … )` ile base fcat üret → sonra YALNIZ title/hotspot/
   `no_out`/edit/sıralama tweak'i inline yap. Tipler, uzunluklar, **QUAN birim-referansı (ondalık)**,
   CURR para-referansı DDIC'ten **otomatik** gelir → manuel hata kaynağı kapanır.
2. **Manuel `lvc_t_fcat` (basit rapor için meşru):** kolon-kolon `fieldname`/`coltext`/`outputlen` elle.

**KURAL — hangisi kullanılacağı bir KARARDIR; sessizce seçme:** field catalog'u DOĞRUDAN kurmadan
**ÖNCE kullanıcıya SOR** ("structure ile mi, manuel fcat mi?") **ya da TS'te netleştir + gerekçelendir**
(std04 §4.5). Her ikisi de her durumda anlamlı değildir:
- **Structure tercih:** miktar+birim ondalık · para+PB · çok kolon · kod→açıklama (tanım) kolonları ·
  tekrar-kullanım. *(Manuel fcat'te ondalık/referans/tanım elle kurulur → sessiz hata: miktarın yanlış
  ondalıkla gösterimi, kod-alanlarının tanım kolonlarının eksikliği, içeriğe göre optimize olmayan kısa
  kolon genişliği — bunların hepsi manuel-fcat kaynaklıdır.)*
- **Manuel meşru:** basit/ad-hoc rapor · az kolon · hesaplanan/tipik-olmayan alanlar · geçici çıktı.

**Enforcement:** judgment-rule → TS'te fcat-yaklaşımı **belirtilir** (std04 §4.5 maddesi) + reviewer/
checklist denetler. Otomatik gate ile "daima structure" DAYATILMAZ (basit raporda structure zorlamak
yanlış olur — merdiven ilkesi).
