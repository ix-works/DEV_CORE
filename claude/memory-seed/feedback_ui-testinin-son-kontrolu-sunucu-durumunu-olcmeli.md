---
name: feedback_ui-testinin-son-kontrolu-sunucu-durumunu-olcmeli
description: Kayıt senaryosunun son kontrolü ekrandaki (kirli) modeli okursa test sahte-yeşildir — sunucu/mock durumunu ölç ve mutasyonla kanıtla
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Bir UI kayıt senaryosunun "kaydedildi mi" kontrolü ekrandaki JSON modelini ya da alan değerini okursa, kayıt başarısız olduğunda da **yeşil** kalır. Çünkü başarısız kayıt modeli sıfırlamaz ve kullanıcının yazdığı değer ekranda durmaya devam eder. Son kontrol sunucu ya da mock tarafındaki kalıcı durumu ölçmelidir: yeniden okuma isteği ya da mock'un kabul/ret sayacı. Bir test grubunun gerçekten koruma sağladığını göstermenin tek yolu mutasyondur: ilgili kodu bozup testin kırmızıya düştüğünü görmek.

**Why:** Bir SD paketinin strateji ekranında düzenleme ve onay senaryoları, gerçekçi mock 412/428 dönerken yeşil kalıyordu, çünkü kirli modeli okuyorlardı. Aynı gece rapor dalında Excel içerik testleri koda sokulan hatalarda yeşil kaldı, çünkü xlsx içeriğine bakmıyorlardı. İçerik denetimi eklenince 13 mutasyonun 13'ü yakalandı. Mock'un gerçekçi olmaması da aynı sınıfı besler: çocuk varlıkta If-Match denetlenmediği için mutasyon hayatta kalmıştı. (2026-11-12)

**How to apply:** Brife iki madde yaz: "son kontrol sunucu durumunu ölçer" ve "her düzeltme mutasyonla kırmızıya düşürülür". Gate'ten bir mutasyon tablosu iste. Dosya üreten akışlarda (xlsx/pdf) içeriği hücre ya da düzey bazında oku.

Son-doğrulama: 2026-11-12
Applies-to: Playwright/mock tabanlı UI testleri, freestyle UI5
