---
name: feedback_belge-incelemesinde-fable-kayit-duzeni-opus-tasarim
description: "Büyük FS/TS doc-gate'inde hızlı kontrol listesi turu yalnız kayıt düzenini yakaladı; güçlü modelle senaryo odaklı inceleme BLOCKER + 3 HIGH buldu — iki tür inceleme ayrı koşulur"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Büyük ve çok kez revize edilmiş bir FS/TS'te **kontrol listesine dayanan tek bir doc-gate yeterli değildir.** Vaka (bir SD paketi, 2026-11-07): hızlı/ucuz bir modelle koşulan bug-expert doc-gate'i WARNING verdi (0 BLOCKER/HIGH; 9 bulgunun 8'i sayım, etiket ya da eşleme bulgusuydu). Aynı belgeye ilk turun raporu gösterilmeden **güçlü bir modelle senaryo odaklı** bir inceleme koşuldu ve 1 BLOCKER, 3 HIGH, 6 MEDIUM buldu:
- BLOCKER: yedek yol yalnız son kaydı kaydediyordu, satırlar başarılı görünüyordu (sessiz eksik fiyat). Önceki sürümün kaynağıyla canlıda doğrulandı.
- HIGH: yüzde ölçeği çelişkisi; simülasyon sırasında açık kalan düzenleme penceresi; bir kipte tek satırın 'ya hepsi ya hiçbiri' kuralını delmesi.

Vakada kullanılan modeller: ilk tur Fable, ikinci tur Opus. Model adları sürüme bağlıdır. Ders model adına değil **tur türüne** bağlıdır: kontrol listesi turu ↔ senaryo turu.

**Why:** Kullanıcı az sayıdaki bulguyu şüpheli buldu ("bu kadar az bulgu normal değil") ve ikinci inceleme istedi; ölçüm kullanıcıyı haklı çıkardı. Kontrol listesi turu yalnız "baktığım yüzeyde bulgu yok" der. Durum geçişi, LUW/commit, eşzamanlılık ve birim/ölçek açıkları senaryo kurulmadan görünmez.

**How to apply:** Belge kapısında iki ayrı tur planla:
1. Kayıt düzeni/kontrol listesi turu (hızlı model yeterli).
2. Bağımsız, senaryo odaklı tasarım incelemesi (güçlü model). Eksenler: durum makinesi, hata/yeniden deneme, eşzamanlılık, sessiz yanlış veri, yetki, tahminsiz kodlanabilirlik, hedef sürüm uyumu, standart veriye yazma. En az 25 senaryo kurulur ve ilk turun raporu bu incelemeye VERİLMEZ.

"0 BLOCKER" sonucunu tasarımın doğru olduğu diye okuma; kapsam beyanına bak. Not: bug-expert'te Write aracı yok, bu yüzden rapor dosyasını lider yazar.

Kapsam: tek vaka, tek belge. "Güçlü model her zaman daha çok bulur" iddiası ÖLÇÜLMEDİ. Vakada iki değişken birlikte değişti: model ve senaryo odaklı brif.

Son-doğrulama: 2026-11-07
Applies-to: FS/TS doc-gate (tüm profiller), bug-expert model seçimi
