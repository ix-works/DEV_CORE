---
name: feedback_ecc-referansi-is-anlayisi-icin-mimari-degil
description: "ECC/legacy dump'ı ve PRD verisi YALNIZ 'ne, neden, nasıl takip edilmek isteniyor'u anlamak içindir — kodlama/tablo mantığı/mimari ŞABLON DEĞİLDİR; S/4 tasarımı SD-LE-EDI-ABAP uzman gözüyle sıfırdan yapılır"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d3315d6e-2386-45aa-a1a5-4f5f18f46c42
---

**Kural (kullanıcı, 2026-08-17, ZSD001 <MUSTERI-D> Konsinye):** "ECC'deki her şeyi görmeni istememin sebebi ECC'deki gibi bir mimari kurmak istemem değil. **AYNISINI YAPMAYACAĞIZ.** Oradaki kodlama, tablo mantığından etkilenme. Asıl yapılmak isteneni anla ve **uzman bir SAP SD-LE-EDI-ABAP danışman olarak kendi tasarımını yap**."

**Why:** Legacy kod + örnek veri, iş ihtiyacını (neyin, hangi detayla, neden takip edildiği) somutlaştırmanın en hızlı yoludur; ama legacy'nin teknik seçimleri (Z tablo, alan reuse, FM zinciri, temel tip, partner tipi, mesaj yapısı) o günün kısıtlarının ürünüdür. Kullanıcı ZSD001'de iki kez uyardı: (1) 16.08 "SD/LE/EDI uzman gözden geçirmesi" turu 3 Z-tabloyu standartla değiştirdi; (2) 17.08 mutabakat sonrası "AYNISINI YAPMAYACAĞIZ" vurgusu — kararların bir kısmı hâlâ "ECC'de böyleydi, PO'ya dokunmayalım" refleksiyle alınmıştı.

**How to apply:**
- Legacy'den ÇIKARILACAK: iş kuralları, takip edilen büyüklükler (hangi alan, hangi granülarite), istisna/hata senaryoları, hacim, kullanıcı alışkanlıkları, örnek veri.
- Legacy'den ÇIKARILMAYACAK: Z tablo/alan tasarımı, alan reuse hileleri, IDoc temel tipi/partner tipi/mesaj yapısı seçimi, program/FM zinciri, ekran yapısı, mail/log mekanizması.
- Her tasarım kararında sırayla sor: **(1) S/4 standardı ne öneriyor? (2) Bu ihtiyaç için "dünyada nasıl yapılır"? (3) ECC'den farklıysa neden farklı — ECC izini korumak gerekçe DEĞİLDİR.** ("PO'ya dokunmamak", "ECC'de böyleydi" tek başına karar gerekçesi olamaz; kullanıcı açıkça isterse başka.)
- FS/TASARIM'da "ECC ile aynı" ifadesi görülünce → sinyal: iş kuralı mı (kalır) teknik seçim mi (yeniden değerlendir).
- Doküman gate'i (doc-checklist) bu soruyu sorsun: "bu karar ECC izinden mi, S/4 standardından mı türedi?"

İlgili: [[project_zsd001-<MUSTERI-D>-konsinye]], [[feedback_legacy-full-dump-pattern]], [[feedback_yeni-yetenek-once-arastir]], [[feedback_fs-ts-iki-zihniyet-disiplini]]
