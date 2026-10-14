<!--
ŞABLON — ENTEGRASYON SAYFASI (EDI/CPI ve benzeri mesaj tabanlı arayüzler; standards/04 §9.2a).
Kullanım: paketin docs/ klasörüne kopyala, <...> yer tutucularını doldur, bu yorum bloğunu sil.
Teslim: .md + .pdf (.html ara çıktısı repoda tutulmaz).
Bu sayfa tek bir mesaj akışını (gönderen → dönüşüm → SAP) belgeler; FS/TS'in entegrasyon
bölümüne bağlantı olarak eklenir, onların yerine geçmez.
-->

# Entegrasyon Sayfası — <Akış adı>

| Paket | Sürüm | Tarih | Durum |
|---|---|---|---|
| <ZSD001> | <v1.0> | <YYYY-AA-GG> | <Taslak / Doğrulandı> |

## 1. Akış özeti

| Alan | Değer |
|---|---|
| Gönderen / alıcı | <iş ortağı rolü — gerçek ad değil, rol> |
| Yön | <Gelen / Giden> |
| Mesaj standardı ve sürümü | <ör. EDIFACT <tip> <sürüm> / VDA <no> / XML şeması> |
| Taşıma ve ara katman | <ör. SFTP → entegrasyon platformu → IDoc> |
| SAP girişi | <IDoc tipi / mesaj tipi / işlem kodu / API> |
| Tetik ve sıklık | <dosya gelişi / zamanlanmış / olay> |
| Karakter kodlaması | <dosya başına tespit edilir — aynı klasörde karışık kodlama olabilir> |

## 2. Otorite (neye göre doğrulanır)

- **Otorite = orijinal mesaj dosyası + eşleme tanımı** (ör. `.mmap` / mapping kaynağı) — `<dosya yolları>`.
- SAP'de oluşmuş IDoc/belge **otorite değildir**: test sistemi önceki eşleme turlarından kalmış yanlış
  veri taşıyabilir. Teşhis de otoriteden başlar.
- Çok mesajlı zarfta **her mesaj ayrı** ölçülür; yalnız ilk mesaja bakmak, başlık taşıma kusurlarını gizler.

## 3. Eşleme tablosu

| # | Kaynak (segment / alan / konum) | Hedef (segment / alan) | Dönüşüm / kural | Zorunlu | Örnek değer | Kaynak referansı |
|---|---|---|---|---|---|---|
| M-01 | <UNH…/DTM+137> | <E1EDK03-DATUM> | <biçim çevirimi> | E | <örnek> | <eşleme tanımı satırı / spec §> |

## 4. Ana veri ve uyarlama bağımlılıkları

| Bağımlılık | Nerede tutulur | Eksikse ne olur |
|---|---|---|
| <ör. iş ortağı belirleme> | <tablo / uyarlama adımı> | <hangi mesajla durur> |

## 5. Hata ve yeniden işleme

| Düşme noktası | Nasıl görülür (izleme ekranı / kuyruk / durum kodu) | Kim düzeltir | Yeniden işleme yolu |
|---|---|---|---|
| <ara katman> | | | |
| <SAP girişi> | | | |

## 6. Test vakaları

| # | Girdi dosyası (otorite) | Beklenen SAP sonucu | Gerçekleşen | Sonuç |
|---|---|---|---|---|
| T-01 | <dosya adı> | <belge türü / alanlar> | <kullanıcı teyidi ile doldurulur> | |

> Test sonucu kullanıcıyla teyit edilir; SAP'deki bir belgenin varlığı tek başına "doğru" demek değildir.

## 7. KAPSAM BEYANI

- **Bakılanlar:** <kaç dosya / kaç mesaj / hangi tarih aralığı>
- **Bakılmayanlar:** <ör. yalnız ilk zarf okundu, eski sürüm mesajlar dışarıda>
- **Ölçülemeyenler:** <ÖLÇÜLEMEDİ — neden>
