<!-- T4.1 DoD checklist'leri (denetim 2026-07-31 §8 Ayak-1). İlgili blokları doldur; ilgisizleri sil. -->

## Değişiklik özeti
<!-- ne + neden (1-3 cümle) -->

## DoD — Kural değişikliği (core'a kural yazan/değiştiren PR ise)
- [ ] Kanonik ev TEK (yeni kopya üretmedim; atıf verdim)
- [ ] Eski kopyalar/atıflar AYNI PR'da güncellendi
- [ ] Yüklenme kanalı beyanı doğru (her-oturum / on-demand / brifing — L1b tembel-tetik #17204 pasif)
- [ ] Nicel iddialara tarih + içerik-çapası kondu

## DoD — Kaldırma (gate/guard/validator/anahtar kaldıran PR ise)
- [ ] Ad `governance/removed-controls.md` sözlüğüne eklendi
- [ ] Aynı PR'da core+proje grep'i: "hâlâ aktif" anlatan metin kalmadı

## DoD — Çift-katman (ajan-tanımı / settings-template / pre-commit kaynağı ise)
- [ ] Yayılım adımı bu PR'ın parçası (team_setup senkron / template→proje) ya da açıkça planlandı

## DoD — Yeni gate (moratoryum 5-şartını geçtiyse)
- [ ] Fixture'lı negatif test AYNI PR'da (`tests/fixtures/<validator>/{bad,good}` + koşucu yeşil)
- [ ] Net-etki beyanı: +N/-M kontrol (trend ⑥)
