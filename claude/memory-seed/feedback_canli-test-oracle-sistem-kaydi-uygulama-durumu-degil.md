---
name: feedback_canli-test-oracle-sistem-kaydi-uygulama-durumu-degil
description: "Canlı uçtan uca testte doğruluk kaynağı uygulamanın kendi durum alanı DEĞİL, standart sistemin kaydıdır (önce/sonra anlık görüntü farkı); taklit edilen standart API'nin commit/rollback varsayımı ayrıca ölçülür — yoksa onaysız yazım gibi en ağır kusur yüzlerce yeşil testin arkasında yaşar"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Yazan bir ürünün (fiyat onayı, belge aktarımı vb.) canlı testinde başarı ölçütü, uygulamanın kendi durum alanları değildir ("simülasyon F, 0 hata, durum=Onayda" gibi). Ölçüt standart sistemin kaydıdır: test anahtarlarına ait standart tabloların (koşul kaydı için A<nnn>/KONH/KONP; değişiklik izi için iş kullanıcısına göre CDHDR) eylemden önce ve sonra alınan anlık görüntüleri arasındaki FARK. Beklenmeyen her fark FAIL'dir.

**Why:** Vaka 2026-11-14 (bir SD fiyat onayı uygulaması). Onay öncesi simülasyon işi standart fiyat API'sini çağırıyor, sonra ROLLBACK ediyordu. API'nin varsayılanı (`IV_SYNC = abap_true`, "Save data in update task") kaydı yine de kalıcı olarak yazdı. Sonuçta onaylanmamış fiyat SAP'ye gitti ve onaycının ekranındaki "Mevcut" sütunu yeni fiyatı gösterdi (Fark %0).
- 444 mock UI testi bunu göremezdi.
- ABAP birim testleri API'yi TEST-SEAM ile taklit ediyordu ve kusur tam olarak bu taklidin arkasındaydı.
- Daha önceki bir canlı turda simülasyon 2 gerçek kayıt yazmıştı. Lider uygulamanın durum alanlarını okuyup "uçtan uca geçti" dedi ve koşul tablolarına (A<nnn>/KONH) bakmadı.
- Kusuru kullanıcı yakaladı: "bir sürü test yapıyorsun, bu hatayı yakalayamıyorsan bu testler ne için".

**How to apply:**
- Yazan bir ürünün canlı testi, FS'ten çıkarılan ürün değişmezleriyle başlar. Örnekler: "onaysız sıfır yazım", "onaylanan = SAP'deki kayıt birebir", "ret/revize sıfır yazım", "hata ⇒ ya hepsi ya hiçbiri". Her değişmez canlıda, standart tablo farkıyla ölçülür.
- Her canlı eylem önce/sonra anlık görüntü farkıyla sarılır. Bu yöntem kimsenin aklına gelmeyen yan etkileri de yakalar.
- TEST-SEAM ile taklit edilen her standart API'nin commit/rollback/senkronluk davranışı, gerçek API'ye karşı bir kez ölçülür. Ölçülmeyen varsayım TS'te ve kodda DOĞRULANMADI olarak kalır.
- Raporda "mock'ta ekran testi geçti" ile "canlıda iş kuralı doğrulandı" ayrı satırlarda yer alır. Test sayısı bir kapsam iddiası değildir.

İlgili: [[feedback_sessiz-yanlis-fiyat-gorunur-eksikten-agir]] · [[feedback_ui-testi-dom-varligi-gorunurluk-ve-olay-parametresi]] · [[feedback_arac-basarisizligini-zararsiz-sayma]] · [[feedback_done-tam-kapsam-dogrula]]
Son-doğrulama: 2026-11-14 · Applies-to: standart veriye yazan tüm ürünler (s4_private/ecc; API/BAPI/BDC yolları)
prior-art: kısmi — "çalıştı mesajı ≠ çalıştı" (core §1.1) ve done-tam-kapsam vardı; "test oracle = standart tablo farkı" ve "seam'in API varsayımı ölçülür" yoktu
