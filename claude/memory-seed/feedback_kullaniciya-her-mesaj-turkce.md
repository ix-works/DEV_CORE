---
name: feedback_kullaniciya-her-mesaj-turkce
description: "Kullanıcıya giden HER metin Türkçe — ara durum bildirimleri, iş sırasında yazılan kısa notlar ve özetler dahil; İngilizce ara bildirim yazma"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: e2469e37-2d33-4baa-b061-98cf3e292371
---

Kullanıcıya görünen tüm metin Türkçe yazılır — nihai yanıt kadar **iş arasındaki kısa durum
bildirimleri** ("şunu başlatıyorum, sonra şunu yapacağım" türü) de.

**Why:** 2026-09-25'te bir paket turunda ara bildirimler İngilizce yazıldı; kullanıcı:
*"bu tarz geri bildirimleri türkçe yapabilir misin"*.

**How to apply:** araç çağrıları arasındaki her kullanıcıya dönük cümle Türkçe. Kod, komut, dosya
adı, teknik terim (keepalive, sap-client) olduğu gibi kalır. Alt-ajan brifleri zaten Türkçe.

**Tekrar (2026-10-03):** uzun infra turunda (çok ajanlı PR döngüsü) ara bildirimler ve AskUserQuestion
dışındaki kısa notlar yine İngilizce kaydı; kullanıcı: *"DURUM NEDİR, TÜRKÇE YAZ BANA"*. Kayma, ajan
raporları/araç çıktıları İngilizce-ağır olduğunda oluyor ⇒ her kullanıcıya dönük cümleyi yazmadan önce dili kontrol et.

Son-doğrulama: 2026-10-03 · Applies-to: bu çekirdeği kullanan tüm projelerdeki oturumlar (kullanıcı kararı 2026-11-12: tüm core kullanıcılarına)
