---
name: feedback_adt-table-read-pozisyonel-hizalama-tuzagi
description: "adt_table_read footgun YAPISAL ÇÖZÜLDÜ 2026-06-23 (pozisyonel data.data söküldü, yalnız rows_labeled döner); kolon-değer iddiasını rows_labeled'dan oku"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1420ec34-9257-4b0a-aef4-aee509c5b810
---

`adt_table_read` çıktısındaki `data.data` **pozisyonel dizidir** (satır içinde kolon-adı yok); `data.columns[]` ile gözle hizalamak **off-by-one hatasına açıktır** — özellikle **seyrek-dolu bir kolon null** ise, komşu dolu değer yanlış kolona atfedilir.

**Somut olay (2026-06-22, üst üste 3 kez ısırdı):** `ZSD001_T_DORIT` okunurken `BATCH` (idx11) ile `HU_IDENT` (idx12) karıştırıldı. Önce lider (önceki oturum) doğru saydı, sonra bir araştırma ajanı "BATCH=null, lider yanıldı" diye **yanlış** sonuç üretti (kendisi yanlış saydı), neredeyse lider de tekrar yanlış kabul ediyordu. **Kullanıcının alan-bilgisi durdurdu** ("hayır batch doluydu, eminim") — ham satır 16 kolon tek tek eşlenince BATCH gerçekten doluydu (`2000000078`). Bu, doğru olan teslimat-parti fix'ini neredeyse geri aldıracaktı.

**Why:** Yanlış-parse, [[feedback_dogrula-once-flag-spekulatif-blocker-yasak]] + [[feedback_arac-basarisizligini-zararsiz-sayma]] ile aynı aileden ama farklı kök: orada "doğrulamadan iddia", burada "doğru veriyi yanlış oku". "Kendim doğrulayayım" yeterli değildi — doğrulamanın KENDİSİ hizalama-hatasına açıktı.

**YAPISAL ÇÖZÜM (2026-06-23, commit 3823b4b1):** footgun artık disiplin-bağımlı değil — etiketleme başarılıysa `adt_table_read` ham pozisyonel `data.data`'yı çıktıdan **söküp atar** (`data.pop`), yalnız `data.rows_labeled` + `data.columns` + `_note` döner. Yanlış-hizalama artık **imkânsız** (hizalanacak ham dizi yok). Kolon alınamayan nadir durumda pozisyonel korunur (veri kaybı yok). Canlı + 4 uç-durum testiyle doğrulandı. Bu, "lider dikkatli + ajan-olumsuzunu re-verify" kırılgan savunmasını araç-seviyesi güvenliğe çevirdi (ADR 0019 ruhu).

**How to apply:**
1. Satır değerlerini DAİMA `data.rows_labeled` (`{KOLON: değer}` dict listesi) listesinden oku — ham pozisyonel dizi zaten dönmüyor.
2. Tek/birkaç kolon yeterliyse `adt_table_read(..., columns="BATCH,HU_IDENT")` ver → SELECT daralır.
3. Bir alan iddiası "sürpriz/çelişkili" çıkıyorsa (ör. çalışan bir fix'i yanlışlıyorsa) çapraz-doğrula; kullanıcı alan-bilgisiyle itiraz ederse ÖNCE onu ciddiye al.
4. ⚠️ Eski ders kalıcı: ajan "X yok/boş" raporunu kanıtsız kabul etme — footgun gitti ama [[feedback_ajan-olumsuz-donusu-kanitla-sorgula]] geçerli.
