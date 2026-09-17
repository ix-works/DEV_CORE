---
name: feedback_grup-bazli-genisletmede-her-grup-kendi-dali-ve-metodu
description: Müşteri grubu bazlı mantığı yeni gruplara açarken her grup KENDİ WHEN dalı + KENDİ MODIFY_<GRUP> metodu alır; OR ile birleştirme / başka grubun metodunu çağırma YOK — gövde bugün kopya olsa bile
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6feb8323-f0ff-4176-b8f5-f633eb79f129
---

Bir müşteri grubuna yazılmış manipülasyonu (ör. ZSD000_CL_IDOC_DATA_MODIFY `MODIFY_<MUSTERI-D>`) başka gruplara "çoğaltırken" kullanıcının beklediği yapı: `CASE` içinde her grup için ayrı `WHEN` + her grubun kendi `MODIFY_<GRUP>` metodu, gövdesi bugün kaynak metodun birebir kopyası.

**Why:** 2026-09-14'te iki kez düzeltildi: önce `WHEN <MUSTERI-D> OR <MUSTERI-A> …` → "her grubun case'i farklı olmalı"; sonra ayrı dallar ama hepsi `modify_<musteri-d>` → "modify_<musteri-a> olması gerek". Gerekçe (kullanıcı): ileride bir müşteride AKUEM/BELNR farklı belirlenebilir; değişiklik yalnız o grubun metoduna yazılacak, diğerlerini etkilemeyecek. Ortak metot/DRY çözümü (nötr ortak alt metot) önerildiğinde de "şu an birebir kopyalıyoruz" dedi.

**How to apply:** Grup/müşteri bazlı dağıtımda yapıyı baştan böyle kur; birleştirme ya da ortak çağrı önermeden kopyala. Saf okuyucu yardımcılar (ör. `DETERMINE_BELNR`) ortak kalabilir. Kopyaların birebirliğini script ile ölç (kod satırı karşılaştırması). "Çoğalt" talebinde yeni tasarım/ölçüm turu açma — kullanıcı bunu "yeni tasarım mı yapıyorsun" diye itiraz etti.
Son-doğrulama: 2026-09-14 · Applies-to: SAP ABAP grup/müşteri bazlı dispatch sınıfları (<PROJE> ZSD000)
