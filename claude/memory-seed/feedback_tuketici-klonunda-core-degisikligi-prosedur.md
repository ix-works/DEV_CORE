---
name: feedback_tuketici-klonunda-core-degisikligi-prosedur
description: "Çekirdeği klonlamış ama upstream'e yazamayan kurulumda core'u düzeltme isteği doğduğunda: DUR → kusur kurulumda mı çekirdekte mi ölç → YALNIZ Issue (fork+PR yolu yok), kanıt formatıyla"
metadata: 
  node_type: memory
  type: feedback
---

*"core'daki şu kuralı/scripti düzeltmem gerek"* düşüncesi doğduğu an, bu kurulumda
**dosyaya dokunmadan ÖNCE** duracaksın. Çekirdek canlı ve paylaşılmıştır: `core/` bir
junction'dır, o makinedeki **her proje** aynı fiziksel kopyaya bakar. Sessiz bir düzeltme
(a) bütün projelerin davranışını değiştirir (b) `session_start` D7 drift alarmı üretir
(c) bir sonraki `git -C core pull` ile çakışır ya da kaybolur.

**Sıra — atlanmaz:**
1. **Kusur kurulumda mı, çekirdekte mi?** `python core/scripts/ix_doctor.py --json` ve
   `python core/scripts/parity_probe.py`. `ix_doctor` FAIL varsa **önce onu kapat** —
   bildirimlerin çoğu aslında kurulum eksiğidir.
2. **Kanıt üret.** *"Bende çalışmıyor"* bulgu değildir. Bulgu = mekanizma + girdi + yanlış
   çıktı + **kontrol grubu** (çalıştığı bilinen vaka) + **kapsam beyanı** (neye bakmadın).
3. **Tek yol: Issue** (`ix-works/DEV_CORE`; yazma yetkisi gerektirmez). **Fork + PR ile kod
   önerme — bu süreçte kullanılmaz** (sahip kararı 2026-09-18): düzeltme fikrin varsa Issue'nun
   `ÖNERİ` bölümüne yaz; ölçüm, yazım ve PR sahibi tarafındadır. Komut Issue URL'i basmadıysa
   bildirim **açılmamıştır**. Sözlü bildirim kaybolur — arkasından mutlaka Issue.
4. **Bu arada lokal yama meşrudur ama GÖRÜNÜR olmalı:** kendi dalında (`fix/<ad>`), `main`'de
   değil; gün-sonunda `git -C core status` temiz olmalı; upstream düzeltmesi gelince yamayı
   geri al ve kusurun gerçekten kapandığını **ölç** ("merge edildi" ≠ "bende düzeldi").

⛔ **Repo PUBLIC:** bildirimde müşteri/sistem/kişi adı, SID, host, kullanıcı kodu, gerçek
belge numarası geçemez. Jenerik ad (`ZSD001`) ve `<PROJE-KOKU>` kullan. Kimlik taşıyan
bildirim düzenlenmez, **kapatılır** — yayın cache'lenir, geri alınamaz.

**Why:** Tüketici kurulum çekirdeği sahibinin hiç denemediği bir ortamda koşturur; sahibinin
makinesinde **yapısal olarak görünemeyen** kusurları ilk gören odur — yani bulgu değerlidir.
Değersiz olan, o bulgunun kayıtsız bir lokal yamaya dönüşmesidir: iki çekirdek sessizce
çatallanır ve fark her turda büyür. Prosedür bildirimi engellemez, **kaybolmasını** engeller.

**How to apply:** Tam prosedür, kanıt şablonunun başlıkları ve komutlar (Issue ·
`gh` kurulumu · `gh`'siz tarayıcı yolu) çekirdekte:
`playbook/howto-cekirdek-bulgu-bildirimi.md`. Talep yazarken şablonun **başlıklarını aynen**
kullan — karşı taraftaki lider metni ihbar sayar, kanıt saymaz ve iddiayı kendi makinesinde
yeniden ölçer; ölçebilmesi için ORTAM/YENİDEN ÜRETİM/KANIT alanları şart.
İlgili: [[feedback_kanit-yeniden-uretilebilir-bicimde-yazilir]] ·
[[feedback_kapsam-disi-bulgu-protokolu]] · [[feedback_adt-infra-degisikligi-once-uyar-onay]]
Son-doğrulama: 2026-09-18 (kanal Issue'ya indirildi; `cekirdek-bulgu` etiketi o gün oluşturuldu)
Applies-to: çekirdeği klonlayan her tüketici kurulum (tüm profiller)
