---
name: feedback_paylasim-onbellek-sorusu-kaynak-okumasiyla-cevaplanmaz
description: "Paylaşılıyor mu / önbellekten mi geliyor" soruları kaynak okumasıyla değil canlı ölçümle cevaplanır — anahtar çalışma zamanında doğar
metadata:
  node_type: memory
  type: feedback
---

*"X paylaşılıyor mu / önbellekten mi geliyor / aynı örnek mi?"* soruları **kaynak okumasıyla cevaplanmaz.** Okunan şey *mekanizma*dır; belirleyici olan **o çalıştırmadaki paylaşım anahtarının değeri** — ve anahtarı çoğu zaman senin kodun değil, **çerçevenin sarmalayıcısı** zenginleştirir.

**Why:** 2026-09-16'da UI5 `ODataModel` için *"metadata paylaşılıyor, ek maliyet yok"* hükmü **iki ayrı okuyucu** tarafından kaynaktan verildi ve **canlı ağ izi çürüttü** (paylaşılan `oServiceData`'ydı, `oMetadata` değil; anahtarlar `sap-language` yüzünden ayrışıyordu). Hüküm üç kez değişti, kullanıcıya iki kez yanlış bilgi gitti. ⭐ Asıl bedel: ilk kapı bu yanlış hükme dayanarak gerçek bir **asılma riskini eledi** — yanlış *"sorun yok"* bulgusu, bulgunun kendisinden pahalıdır.

**How to apply:** ağ izi · örnek kimliği (`a.x === b.x`) · sayaç ile **ÖLÇ**. Kaynak okuması hipotez üretir, hüküm değil. ⚠ İki okuyucunun aynı sonuca varması kanıt değildir — aynı dosyayı aynı eksik soruyla okuduysa hata da paylaşılır; bağımsızlık **yöntemde** olmalı: biri okur, öteki ölçer. Kanonik: `core/playbook/lessons-learned.md` **PATTERN #35** · komşu [[feedback_v2-function-import-buyuk-yuk-414-batch]]
