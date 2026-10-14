<!--
ŞABLON — FS ÖZETİ (standards/04 §9.2a). Kullanım: bu dosyayı paketin docs/ klasörüne kopyala,
<...> yer tutucularını doldur, bu yorum bloğunu sil.
SINIR: PDF'e çevrildiğinde EN FAZLA 2 A4 SAYFA (scripts/build_doc_pdf.py + scripts/html_to_pdf.js varsayılan
biçimi). Ölçüm 2026-10-12: boş şablon 1 sayfa; her bölümü dolu örnek (3 cümle amaç, 3 satır kapsam,
5 adım akış, 2 risk) 2 sayfa. Taşıyorsa özet değil ikinci bir FS yazıyorsun — ayrıntı tam FS'e gider. Özet tam FS'in YERİNE GEÇMEZ; çelişkide tam FS geçerlidir.
AÇIK MADDE TEK YERDE: açık kararlar burada LİSTELENMEZ, yalnız sayısı + tam FS bölüm bağlantısı verilir.
Teslim: .md + .pdf (.html ara çıktısı repoda tutulmaz).
-->

# FS Özeti — <Geliştirme adı>

| Paket | FS sürümü | Tarih | Tam FS |
|---|---|---|---|
| <ZSD001> | <v1.0> | <YYYY-AA-GG> | <tam FS dosyasının göreli yolu> |

> **Açık karar: <N>** — ayrıntı tam FS **BÖLÜM 11-B**; onay tam FS **BÖLÜM 12**. *(Liste ve onay tablosu burada tekrarlanmaz — açık madde tek yerde yaşar.)*

## 1. Ne ve neden

<2-3 cümle: hangi iş sorunu çözülüyor, bugün nasıl yapılıyor, yeni çözüm ne değiştiriyor.>

## 2. Kim kullanır

<Rol / birim — kaç kullanıcı, hangi sıklıkta.>

## 3. Kapsam

| Kapsamda | Kapsam dışında |
|---|---|
| <madde> | <madde — neden dışarıda> |

## 4. Ana akış (en fazla 5 adım)

1. <Kullanıcı … yapar>
2. <Sistem … yapar>
3. <…>

## 5. Bağımlılıklar ve riskler

- <Ana veri / uyarlama / başka geliştirme bağımlılığı>
- <Bilinen risk ve azaltımı>

