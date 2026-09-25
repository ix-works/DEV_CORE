---
name: feedback_sayfa-kapanirken-senkron-xhr-gitmez
description: beforeunload/pagehide içindeki SENKRON XHR Chromium'da sunucuya hiç gitmez (try/catch yutar) — belge kilidi bırakma için fetch+keepalive+CSRF; bırakmadan sonra kilit bayrağını sıfırla
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Sayfa kapanırken/ayrılırken (`beforeunload`/`pagehide`/`unload`) açılan `XMLHttpRequest(..., false)` Chromium'da sunucuya **ulaşmaz**; `try/catch` içindeyse hiçbir iz bırakmaz. Doğrusu `fetch(url, {method:"POST", keepalive:true, credentials:"same-origin", headers:{"x-csrf-token": oModel.getSecurityToken()}}).catch(...)`. `sendBeacon` özel başlık (CSRF) taşıyamaz.

**Why:** ölçüldü (2026-09-25, Chromium 153, lokal sunucu, `beforeunload`/`pagehide`/`unload` × navigasyonla sayfadan ayrılış): senkron XHR 0/3 (normal anda 1/1), keepalive fetch 3/3 CSRF başlığıyla; gerçek uygulama fonksiyonları eski 0/5 · yeni 5/5. Belge kilidi reçetesi "senkron XHR" öneriyordu ⇒ kilit yalnız 5 dk zaman aşımıyla düşüyordu. Sekme KAPATMA ayırt edilemedi (`page.close({runBeforeUnload:true})`'da `sendBeacon` dahil hiçbiri ulaşmadı — ölçüm sınırı, iddia değil); Firefox/Safari/FLP ölçülmedi.

**How to apply:** unload isteğinde `fetch`+`keepalive`; URL `sServiceUrl + "/"` (sondaki `/` `sServiceUrl`'de yok — unutulursa 307→403 "No service found") + ana modelin client parametreleri ([[feedback_elle-kurulan-istek-sap-client-tasimaz]]). Bırakma artık gerçekten gittiği için: ekrandan çıkılan her yolda (geri/kayıt/silme) kilit bırakıldıktan sonra kilit bayrağını sıfırla ve unload dinleyicisi bayrağa baksın — yoksa listedeyken sekme kapanınca aynı belgeye tekrar bırakma gider ve kullanıcının başka sekmedeki kilidi düşer. Reçete `core/playbook/howto-document-lock.md` §4 ⚠ 1-2 · kontrol **FE-49** · ADR 0014 değişiklik notu.

Son-doğrulama: 2026-09-25 · Applies-to: freestyle UI5, sayfa kapanışında istek gönderen her ekran
