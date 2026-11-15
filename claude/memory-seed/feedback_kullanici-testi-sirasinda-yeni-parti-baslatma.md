---
name: kullanici-testi-sirasinda-yeni-parti-baslatma
description: "Kurulum/kapanış talimatı bitince plandaki sonraki partiyi SORMADAN başlatma — plan dosyası anlık onay değildir; öner, bekle"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Bir rapor geliştirmesinde yaşananlar:
- Kullanıcı "bitince kapıdan geçir ve DEV'e kur" dedi.
- Kurulumdan hemen sonra, RESUME planındaki sonraki partiyi (sayı biçimi + kılavuz) sormadan başlattım ve yeni bir FE ajanı açtım.
- Kullanıcı "neden tekrar fe ajanı başladı" diye sordu. Gerekçeyi dinledikten sonra "devam etsin, bitince kur, **yeni bişey başlatma**" dedi.

**Why:** Kullanıcı süre ve ajan maliyetine duyarlı (aynı gün "çok gereksiz iş uzadı" şikâyeti de oldu). Plan dosyasında yazılı olmak, o anki onay yerine geçmez. Kurulum talimatı yalnız o kurulumun kapsamını verir; sonraki partiyi kapsamaz.

**How to apply:**
- Bir kurulum ya da kapanış talimatı tamamlanınca DUR.
- Plandaki sonraki partiyi kısa bir öneriyle sun: ne yapılacak, neden, kaç dakika sürer. Başlatmadan önce kullanıcının "evet" demesini bekle.
- Zorunlu kapılar (bug-gate, kurulum doğrulaması) bu kuralın dışında kalır; bunlar istenen işin parçasıdır.

Son-doğrulama: 2026-11-15 · Applies-to: kullanıcıyla çok partili build/deploy turları
İlgili: [[aralikli-hata-avina-butce-koy-ilerlemeyi-izle]]
