---
name: feedback_ajan-idle-bildirimi-bayat-durum-yeni-durum-degil
description: "Ajanın idle_notification'ı ve mesajlar ÇAPRAZLANIR — bildirim ajanın o anki durumu değil, SON YANITINDAN önceki hâlidir; kararı tekrar yollamadan önce zaman sırasına bak"
metadata: 
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: b2250191-c65a-4d1d-95b6-f2dc84b8a65d
  modified: 2026-09-21T14:04:32.624Z
---

Uzun koşan bir ajanla (ör. adt-gateway) mesajlaşırken ajanın `idle_notification` özetleri ve ara raporları,
liderin gönderdiği karar mesajlarıyla **çaprazlanır**: ajan "karar bekliyorum" der, oysa karar zaten yoldadır ya da
okunmuştur. 2026-09-21'de (bir projenin SAP yazım fazlarında) aynı dört soru (a–d) üç kez yeniden soruldu, lider üç kez yeniden
yanıtladı; bir kez de ajan zaten bitmiş Faz-3'ü "başlat" dürtüsü aldı.

**Why:** Bildirim, ajanın turunu kapattığı anın özetidir; o turda okunmamış inbox mesajlarını yansıtmaz. "Bekliyorum"
cümlesi yeni bir durum değil, bayat bir fotoğraftır. Aksi hâlde lider aynı kararı tekrar tekrar yazar ya da ajanı
bitmiş işi yeniden koşmaya iter (idempotent değilse zarar).

**How to apply:** Bildirimdeki soruya yanıt vermeden önce: (1) aynı soruya daha önce yanıt gönderdin mi (kendi son
SendMessage'larına bak) (2) bildirimin timestamp'i son mesajından önce mi. Öyleyse yeniden yanıtlama; yalnız
kullanıcıya "bayat bildirim" de. Kararları numaralı ve **tek mesajda toplu** gönder (ör. "Kararlar a–d"), ajan
yeniden sorarsa "önceki X başlıklı mesajıma bak" diye çapa ver. İşi yeniden tetikleyen dürtüyü "zaten bittiyse
tekrar koşma, söyle" koşuluyla yaz.

Son-doğrulama: 2026-09-21 · Applies-to: lider ↔ uzun koşan alt-ajan (SendMessage), tüm profiller.
prior-art: yok (bağlantılı: [[feedback_sendmessage-gorevi-sessizce-islenmemis-olabilir]])
