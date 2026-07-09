---
marp: true
theme: default
paginate: true
size: 16:9
---

<!-- _paginate: false -->

# ix-works Mimarisi

## Çoklu-Proje SAP Geliştirme için Metodoloji Çekirdeği

Yönetici Özeti — Kurulum ve İşletim

---

## Çözülen Sorun

Birden çok SAP projesi aynı metodolojiyi (standartlar, kalite kapıları, araçlar) kullanır.

Klasik yaklaşım — her projeye bir **kopya**:

- Kopyalar zamanla birbirinden uzaklaşır (**drift**)
- Bir düzeltme bir projede yapılır, diğerlerine taşınmaz
- Hangi kopyanın güncel olduğu belirsizleşir
- Proje sayısı arttıkça bakım yükü **katlanır**

---

## Çözüm: Canlı Çekirdek + Junction

Metodolojinin tamamı **tek bir merkezde** (DEV_CORE) tutulur; her projeye işletim-sistemi
düzeyinde bağlantı (**junction**) ile bağlanır.

```
        ┌─────────────┐
        │  DEV_CORE   │  ← metodoloji tek kaynak
        │ (standart,  │    (kurallar, kalite kapıları,
        │  kural,     │     araçlar, kurumsal hafıza)
        │  araç)      │
        └──────┬──────┘
     junction  │  junction
     ┌─────────┼─────────┐
     ▼         ▼         ▼
  Proje-A   Proje-B   Proje-C   ← her biri ayrı repo,
                                   çekirdeği anlık devralır
```

Kopya yoktur → drift yapısal olarak imkânsız.

---

## Üç Temel Özellik

**1. Kural ile uygulama ayrılmaz**
Her kalite kuralı atlanamayan bir teknik kapıyla zorlanır. İnsan disiplinine değil,
mimariye dayanır → kişiden bağımsız tutarlı kalite.

**2. Yapay-zekâ ajanı da kurallara tabidir**
Ajanın her eylemi (dosya yazma, SAP erişimi, komut) gerçek zamanlı denetlenir; kural-dışı
eylem **eylem anında** reddedilir.

**3. Denetlenebilir ve geri alınabilir**
Her değişiklik inceleme (PR) + otomatik kontrol (CI) sürecinden geçer; merkez bilinen-iyi
noktaya tek adımda döndürülebilir.

---

## Ne Kazandırır

| Özellik | Karşılığı |
|---|---|
| Yaz-bir-kez, devral-her-yerde | Bir kural/ders tüm projelere anında yayılır |
| Biriken kurumsal hafıza | Her hata bir sonrakini önler; bilgi kurumda kalır |
| Kanıta dayalı çalışma | Ajan doğrulamadan aksiyon almaz → yanlış-varsayım azalır |
| İşe-orantılı süreç | Küçük işe sürtünme yok; kapsamlı işe disiplin atlanmaz |
| Sıfır-eforla yeni proje | Yeni proje çekirdeği otomatik devralır |

---

## Kalite Kapıları

Bir geliştirme talebi geldiğinde sistem:

1. İşin **kapsamını** sınıflar (küçük düzeltme / lokalize / kapsamlı)
2. İlgili SAP modülünün kontrol-listesini yükler
3. Üç eksende araştırır: **alan bilgisi + canlı sistem + kurumsal hafıza**
4. SAP'ye yazım öncesi bir **ön-inceleme** kapısından geçer

Her kural, arkasında onu uygulayan bir araç olduğu için **belgede kalıp uygulanamaz**.

---

## Güvenlik, Gizlilik, Uyumluluk

- **KVKK / veri gizliliği** — hassas veri okuması sistem katmanına göre onay ister
- **Fikri-sermaye koruması** — çekirdek metodoloji proje repolarına gönderilemez;
  müşteri kimliği dış-paylaşımda sızmaz
- **Donmuş yedekler** — arşiv köklere yazma reddedilir (okuma serbest)
- **Denetim izi** — her değişiklik PR + CI + geçmiş kaydıyla uçtan uca izlenir

---

## GitHub Çalışma Akışı

```
  kısa dal → PR → otomatik kontrol (CI) → inceleme → birleştir → stable etiket
```

- Doğrudan ana dala yazım **kapalı** (kural seti zorlar)
- Her değişiklik incelemeden geçer
- Hata → `stable` etiketine tek adımda geri dönüş (rollback)

Çekirdek ve projeler ayrı repolardır; yalnız dosya düzeyinde bağlıdır.

---

## Kurumsal Ortam Uyumu

- Windows üzerinde çalışır, şirket-içi (on-prem) SAP'ye VPN ile bağlanır
- Çoklu sistem katmanı (geliştirme / kalite / üretim) ayrı yönetilir
- Dört SAP profili desteklenir: ECC, S/4 private, S/4 public, BTP ABAP
- Kendi sağlığını denetleyen kontrol araçları (kurulum bütünlüğü + kural doğrulama)

---

<!-- _paginate: false -->

# Özet

**Tek metodoloji çekirdeği + junction** ile çoklu-proje SAP geliştirme:

kopya-drift yok · her kural zorlanır · yapay-zekâ ajanı denetlenir ·
her değişiklik izlenebilir ve geri alınabilir.

Ayrıntı: *ix-works Mimarisi — Kurulum ve İşletim Kılavuzu* (tam referans belge)
