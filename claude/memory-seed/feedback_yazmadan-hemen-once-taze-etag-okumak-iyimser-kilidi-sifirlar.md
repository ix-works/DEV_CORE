---
name: feedback_yazmadan-hemen-once-taze-etag-okumak-iyimser-kilidi-sifirlar
description: "If-Match için yazmadan hemen önce taze etag okumak iyimser kilidi fiilen kapatır — kullanıcının GÖRDÜĞÜ sürümün etag'i taşınır"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

İyimser eşzamanlılıkta (ETag / If-Match) gönderilecek etag, **kullanıcının ekranda gördüğü sürümün** etag'idir; yani yükleme ya da diyalog açılışı anında alınan etag. Kayıttan milisaniyeler önce yeniden okunan "taze" etag, başka bir oturumun araya giren değişikliğini kabul etmiş olur. Bu durumda 412 yalnız okuma ile yazma arasındaki milisaniyelik pencerede tutar ve başka kullanıcının metni **sessizce ezilir**. Başarılı bir yazımdan sonra yanıttaki yeni etag saklanır. Yanıtta etag başlığı yoksa eski etag korunur; sonraki yazım 412 alır, bu da güvenli yöndür.

**Why:** Bir SD paketinin mail şablonu ekranında 412 kutusu "kaydedilemez" diyordu, ama İptal'e basıp tekrar Kaydet'e basınca kayıt geçiyor ve B oturumunun metni eziliyordu (bug-gate BLOCKER). Kontrol grubu: yükleme anındaki etag'i taşıyan genel ayarlar ekranı 412'yi doğru tutuyordu. (2026-11-12)

**How to apply:** "Taze etag" yardımcısını yalnız görülen sürümün anlamsız olduğu yerlerde kullan, ör. eylem (action) çağrıları. Düzenlenen verinin MERGE'ünde kullanma. Gate'e şu sondayı koy: A görür → B değiştirir → A kaydeder ⇒ 412 beklenir; İptal sonrası tekrar Kaydet de 412 almalıdır.

Son-doğrulama: 2026-11-12
Applies-to: OData V2 / RAP etag master-dependent, freestyle UI5
