# docs/ — Mimari Dokümantasyonu

**Tek kaynak.** Belgeler burada yaşar; projelere **kopyalanmaz** (ADR 0020 — çoğaltma drift üretir).

| Dosya | İçerik |
|---|---|
| `ix-works-mimari-kilavuzu.md` | Tam referans belge (17 bölüm + 2 ek) — kaynak |
| `ix-works-yonetici-sunum.md` | Yönetici sunumu (10 slayt) — kaynak |

## Türetilmiş çıktılar

**PDF/HTML repoya konmaz** (binary şişmesi); kaynaktan üretilir:
- Referans PDF/HTML: markdown → HTML (python `markdown`) → PDF (Chromium `page.pdf`).
- Slayt PDF: slayt-CSS'li HTML → Chromium `page.pdf` (1280×720).

> Not: `marp` bu ortamda açık-tarayıcı profil çakışmasıyla takılıyor; PDF üretimi
> doğrudan Chromium (mmdc'nin puppeteer'ı) ile yapılır.
