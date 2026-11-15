---
name: feedback_gorunen-hata-son-denemenin-yanitidir-ilk-tekrarda-ham-iz-ve-kontrol
description: "Çok-denemeli bir araçta görünen hata SON denemenin yanıtıdır, asıl hata olmayabilir — aynı hata ikinci kez gelince TEKRARLAMA; her denemenin ham yanıtını izle + bilinen-iyi girdiyle kontrol denemesi"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

**Kural:** Bir araç aynı hatayı ikinci kez verdiğinde üçüncü kez aynı yoldan deneme. Önce iki ölçüm yap:
① **Ham iz:** aracın HER denemesinin isteği, yanıt kodu ve gövdesi ayrı ayrı görünmeli. Gerekirse aracı bir izleyiciyle sarmala.
② **Kontrol grubu:** aynı nesneye, aynı yol ve aynı transport ile çalıştığı bilinen bir girdi gönder (ör. sistemdeki aktif kaynağın kendisini, no-op olarak).
Kontrol geçer ama yeni girdi kalırsa sorun **içeriktedir**. Bu durumda kilit, oturum ve ağ hipotezlerinin hiçbiri doğru değildir.

**Why:** Vaka (bir SD paketi, 2026-11-12): ADT kaynak PUT'u üç tur boyunca `409 CTS_WBO_API 019` (kilit çakışması) gösterdi. Lider mesajı kanıt saydı ve kullanıcıyı SM12, IDE ve VPN kontrolüne yönlendirdi; VPN yenilendi ve aynı yoldan yeniden denendi. İzleyici ve no-op kontrolü gerçek durumu gösterdi: asıl hata ilk biçimin verdiği **400 `OO_SOURCE_BASED 011`** (kayıt anındaki tarama reddi) idi. Araç 400'den sonra transport'suz yedek biçimlere geçiyor, kendi kilidine çarpıyor ve yalnız SON yanıtı basıyordu. 400'ün sebebi metot imzasındaki türetilmiş RAP tipiydi (BE-55 ailesi). Üç yazım turu ve kullanıcının zamanı boşa gitti. Kural zaten yazılıydı (core §1.1 ÖNCE-ARA "yeniden denemeden önce ara" + PATTERN #19 kontrol grubu); eksik olan **uygulama anıydı**: hata mesajı kanıt yerine konmuştu.

**How to apply:**
- Tetik: bir aracın aynı hatası ikinci kez geldiğinde. Bu hem lider hem gateway için geçerlidir. Bilinen geçici sınıflarda (CSRF, `400 Session Timed Out`) tek bir tekrar meşrudur (bkz. `playbook/adt-mcp.md`, Session Timed Out maddesi). Bu ders yalnız "aynı hata, aynı yol, ikinci kez" anı içindir. **Genel bir "4xx'te tekrar yok" kuralı DEĞİLDİR**: öyle bir kural bilinen geçici 400/401'leri bozar ve bu yüzden bilinçli olarak yazılmadı.
- Kullanıcıyı sistem tarafında kontrole (SM12, oturum, ağ) yönlendirmeden ÖNCE kontrol grubunu koş.
- Tarihçe: vakadaki araç kusuru DEV_CORE#423 ile düzeltildi. `set_object_source` artık biçim döngüsünü yalnız transport biçiminin reddinde sürdürür; içerik reddinde durur ve O yanıtı raporlar. Ders araçtan bağımsızdır: yedekli ya da çok-denemeli her araçta görünen hata son denemenin yanıtı olabilir.

Son-doğrulama: 2026-11-12
Applies-to: ADT yazım araçları + genel olarak çok-denemeli/yedekli her araç; tüm profiller
prior-art: bulundu — ilkeyi core §1.1 ÖNCE-ARA (yeniden deneme anı) ve `lessons-learned` PATTERN #19 (kontrol grubu) taşıyor. Aracın çoklu yanıtı tek yanıtla örtmesi yazılı değildi ⇒ DEV_CORE#423. Kural genişletilmedi; bu ders yalnız uygulama anını işaretler. İlgili: [[feedback_arac-basarisizligini-zararsiz-sayma]] · [[feedback_iddia-yazma-aninda-kanit-kurallari]]
