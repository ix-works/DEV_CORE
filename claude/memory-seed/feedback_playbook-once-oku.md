---
name: feedback-playbook-once-oku
description: "SAP ADT işlem yapmadan önce playbook'taki ilgili pattern'i (özellikle annotation/field referans formatları) MUTLAKA oku — eski kaynaktan körü körüne kopyalama yapma"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7091c15c-424a-42a9-bcf8-7c3f51f36d33
---

SAP ADT'de obje yaratma/güncelleme yaparken **playbook'taki ilgili pattern'i okumadan deneme yanılma yapma**. Özellikle annotation syntax, alan reference format, qualified isimlendirme konularında.

**Vaka 2026-05-14** — `ZSD001_T_BOOKHD`'ye `order_amount: netwr` + `order_currency: waerk` alanları eklerken:
- İlk denememde `@Semantics.amount.currencyCode : 'order_currency'` yazdım (sadece field adı)
- SAP "annotation uncomplete" dedi
- Sonra `@AbapCatalog.referenceField` denemesini düşündüm
- Kullanıcı uyardı: "tablo yaratırken playbook okumadın mı?"
- Playbook §15 (Z tablo) tam syntax'ı yazıyordu: `'TABLE_NAME.FIELD_NAME'` **qualified format** + `@Semantics.currencyCode : true` marker
- 5 dakika kayboldu deneme yanılma ile

**🔁 TEKRAR (2026-06-13) — CDS yaratma patinajı (T4 recurrence).** Yeni `ZSD000_I_PARTNER_EC_VH` VH'ını yaratırken `adt_push_source` (→423 not locked) → `adt_post_shell` ddls (→DDLS/DF desteklemez) → `create_cds_view.py` (→CSRF flaky) diye dolaştım. **Oysa `playbook/adt-cds.md` §30.1 + "Tuzaklar" bu sırayı ZATEN yazmıştı** ("create_cds_view → post_shell diye dolanıldı = zaman kaybı"). Eksik bir bilgi YOKTU — playbook'u okumadan tahminle denedim (bu memory'nin TAM uyardığı şey, 2. kez). Çözüm: raw-REST inline POST shell → `adt_push_source` (obje var → source+activate). **KOD GATE eklendi (pasif not yetmedi, T11):** (1) `playbook/adt-cds.md` tepesine "⚡ TEK CDS YARATMA" kanonik 3-adım + denenen-başarısız tablosu; (2) `scripts/hooks/post_tool_failure.py` artık CDS-fail imzalarında (DDLS/DF, "valid definition yok", "not locked") GENERIC değil **spesifik reçeteyi** enjekte ediyor; (3) `skill_injector._WORKTYPES`'a "CDS view-entity YARATMA" iş-türü. İlişkili: [[feedback_create-cds-view-xml-escape]], [[feedback_inline-post-empty-source-trap]].

**Yapılması GEREKMEYEN:**
- "Annotation şu olabilir herhalde" diye tahmin etmek
- <LEGACY_SOURCE>/eski source'tan körü körüne kopyalama (sistem versiyonu farklı olabilir, alan adları değişmiş olabilir)
- Hata mesajı belirsizse ("uncomplete", "unknown", "missing") direkt alternatifler denemek

**Yapılması GEREKEN:**
1. ADT işlem öncesi `playbook/README.md`'ye git, obje tipine göre dosyayı bul (`adt-tables-structures.md`, `adt-cds.md`, vb.)
2. İlgili section'da ÇALIŞAN YÖNTEM'i oku
3. Özellikle "annotation isimleri", "field referansı", "tip referansı" kısımlarına dikkat
4. **Standart SAP tablolarındaki alan adları sistem versiyonuna göre değişebilir** — kullanmadan önce `GET /sap/bc/adt/ddic/tables/<name>/source/main` ile teyit
5. Eski <LEGACY_SOURCE> source'tan kopya yapıyorsan, field adları yeni sistemle eşleşiyor mu kontrol (örn. `vsartkat` eski → `vktra` yeni T173'te)

**Why:** Playbook'un amacı zaten "denenmiş, çalışan" pattern'leri toplamak. Documentation'a güvenmek tahmin yapmaktan hızlı, güvenli, doğru. Pattern bilmeden iş yapmak LESSONS_LEARNED #4 (Doc ≠ Enforcement) anti-pattern'i.

**How to apply:** Her ADT işlem öncesi 30 saniye playbook'a bak. Şüpheliyse dur, oku, sonra başla.

İlgili: [[feedback_zli-obje-text-tahmin-yasak]], [[feedback_legacy-draft-txt-files]], LESSONS_LEARNED #6 (Trust without verify)
