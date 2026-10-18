---
name: kd-mock-yanit-sekli-gercek-be-yi-izlemeli
description: "KD ekran görüntüsü mock'u yalnız TEMİZ veri değil, BE'nin gerçek yanıt ŞEKLİNİ izlemeli — sabit başarı, eksik T100, ham değer yorumu, atlanan çok satırlı sonuç, BE'nin hiç üretmediği satır = BLOCKER"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: b1af0150-5131-413f-8def-25d523d2fa1a
  modified: 2026-10-01T22:00:31.417Z
---

KD (kullanıcı kılavuzu) görselleri kurgusal veriyle (Playwright route mock / client-model injection) çekilirken mock'un **verisi** temiz olsa bile **yanıt şekli** gerçek arka ucu izlemezse kılavuz, sistemin hiç üretmediği bir ekranı belgeler. DOC-KD-01 bugün yalnız "temiz/uydurma veri" der; şekil eksenini söylemez.

**Ölçülen vakalar (bir projede, 2026-10-01/02, iki ayrı KD — iki ayrı ajan, aynı sınıf):**
- SaveAndReprocess mock'u **sabit başarı** dönüyordu; gerçek BE hata kalınca 221 üretmez, Basarili=false ile hata penceresi açar.
- Kontrol Et mock'u ön-kontrolün **hiç üretmediği** P-03/P-04 satırlarını gösteriyordu.
- Mock T100'de **eksik mesaj** (235) → boş Açıklama.
- Ham "E" değeri ekranda "Hata" diye yorumlanmış; BE'nin bapiret2 başına **çok satırlı** sonucu (227 + adım satırları) atlanmış.
- Ters aktarım kaydında mock kaynak/hedefi **takas ediyordu**; BE `ls_rev = ls_tr` ile korur ⇒ satır "Çıkan" değil "Giren".
- Durum adları mock'ta "Hazır"; BE DD07T'den **BÜYÜK HARF** basar ("HAZIR") — alıntı birebirliği bozuldu.
- Her vaka bağımsız bug-gate'te yakalandı (2× BLOCKER, 1× MEDIUM sınıfı); düzeltme turları da **kendi** fazla-geniş iddialarını üretti (3 tur).

**Why:** Mock'u UI'ın beklediği şekle göre yazmak kolaydır (UI'ı mutlu eder); BE'nin gerçek dallarını (hata yolu, kilit yolu, mükerrer yolu, metin kaynağı) okumadan yazılan mock, UI'ın "mutlu yol" varsayımını belgeye taşır.

**How to apply:**
- KD mock'unu kurarken her eylem için BE metodunu oku: dönen mesaj **sırası, tipi, sayısı**, başarısız dal, metin kaynağı (MSAG/DD07T — canlıdan birebir al).
- Mock'ta görünen her satır için "BE bunu üretir mi?" sorusunu sor; üretmediği satır = uydurma.
- KD yazar brifine ve KD gate brifine bu ekseni AÇIKÇA yaz (alt-ajanlar memory görmez).
- Core terfi adayı: doc-checklist DOC-KD-01'e "yanıt şekli" ekseni (yazıldığı tarihte kuyruk kaydıydı; core'a onaysız yazılmaz).

Son-doğrulama: 2026-10-02
Applies-to: KD görsel üretimi (mock/route-intercept), tüm profiller
prior-art: DOC-KD-01 (core doc-checklist) yalnız veri temizliğini kapsıyor — şekil ekseni yok; memory'de eşdeğer ders yok (grep "mock" 2026-10-02).
