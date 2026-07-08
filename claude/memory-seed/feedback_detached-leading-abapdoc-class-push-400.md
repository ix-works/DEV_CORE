---
name: feedback_detached-leading-abapdoc-class-push-400
description: "Source-based class push 400 OO_SOURCE_BASED 012 'unknown comments which can't be stored' = YETİM YORUM (metot-arası, koda bağsız); mesaj LİTERAL doğru"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7a28f63f-6ff0-4fe7-88d3-e6cc7c9c76c5
---

`adt_push_source` ile source-based class push'ta **`OO_SOURCE_BASED 012` "The class contains unknown comments which can't be stored" (400)** — **MESAJ LİTERAL DOĞRU (yanıltıcı değil):** kök neden **YETİM YORUM** = hiçbir `METHOD/TYPES/CONSTANTS/DATA` deklarasyonuna bağlı olmayan, metot/deklarasyon **ARASINDA boşlukta** duran `"`/`*` yorum. Source-based class save-scan her yorumu bir kod öğesine bağlamaya çalışır; bağlanamayanı saklayamaz → 400. **KESİN KANIT (2026-06-15, ZSD001 C4):** kullanıcı temizlenmiş (yetim yorumlar çıkarılmış) full class'ı **SE24'te aktive etti** + asıl class'tan 3 yetim yorum (metot silinince/`copy_from_voyage` kaldırılınca arada kalan notlar) silinince push GEÇTİ.

**Bağlı yorumlar SORUNSUZ:** bir bildirimin HEMEN ÜSTÜ + method-İÇİ inline + statement-yanı. **Yetim:** ENDMETHOD↔METHOD arası, METHODS↔METHODS arası, ENDCLASS sonrası, deklarasyonlar arası boşlukta. **En sık sebep:** bir metodu/alanı silip YORUMUNU bırakmak → yorum yetim kalır.

**Why / META-DERS (bu tuzakta 12+ tur patinaj):** "unknown comments" mesajı yüzünden kovaladığımız HER ŞEY CONFOUND'du — `"!` ABAP-Doc, CLASS-öncesi comment konumu, emoji/`↔⏳→`, Türkçe `İ/ı`, char10 built-in-length, **public `TYPES FOR CREATE \_assoc`**, boyut/eşik. Hepsi "düzeltildi" çünkü minimal izolasyon testleri zaten yetim yorum İÇERMİYORDU (o yüzden geçtiler), asıl class içeriyordu. Doğru teşhis ancak (1) **push hata-truncation fix**'i (`set_object_source` `response.text[:300]` ile kesiyordu → tam yanıt: tek-mesaj, satır-no yok = comment'in kendisi) + (2) **kullanıcının SE24 testi** (temiz full class aktive → kod geçerli, yetim-yorum izole) ile geldi.

**How to apply:** Source-based class push'ta `OO_SOURCE_BASED 012` görürsen → **YETİM YORUM ara** (her yorum bir bildirime bitişik mi? metot/deklarasyon arasında boşlukta yorum var mı? → kaldır veya sonraki öğeye bitişikle). Metot/alan silerken yorumunu da sil. **Hızlı kesin teşhis:** (a) hatayı truncate etmeden TAM al; (b) **SE24'te (section-based) test** — geçerse kod sağlam, source-PUT sorunu; (c) **method-by-method include push** (section-based, save-scan'i tamamen atlar) = garantili yedek. Tahminle construct kovalama — minimal test'ler confound geçirir. ZSD001 booking C4 (`ZCL_SD001_BOOKING_API`), 2026-06-15. İlgili: [[feedback_source-based-class-type-c-trap-ve-vague-scan-bisect]] · [[feedback_push-failure-stale-lock-persistent-session]] · [[feedback_inline-post-empty-source-trap]].
