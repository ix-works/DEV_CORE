# docs/ — Mimari Dokümantasyonu

**Bu dizin kanonik kaynaktır.** Belgeler burada düzenlenir; projelerdeki kopyalar birer *aynadır*.

| Dosya | İçerik |
|---|---|
| `ix-works-mimari-kilavuzu.md` | Tam referans belge (17 bölüm + 2 ek) — kaynak |
| `ix-works-yonetici-sunum.md` | Yönetici sunumu (10 slayt) — kaynak |

## Ayna (mirror) mekanizması

Bir belge bir projede de bulunmak isteyebilir (ör. `template_project` referans iskeleti).
Kopya **bire bir aynı** olmalıdır ve bir gate'le zorlanır — kopya, tazelik kontrolü olmadan
kesinlikle bayatlar (2026-07-10 provasında üç şablonda aynı anda yaşandı).

```powershell
python core/scripts/sync_docs_mirror.py            # <proje>/docs/*.md aynasını tazele
python core/scripts/sync_docs_mirror.py --check    # yalnız kontrol (exit 1 = bayat)
```

Gate: `scripts/validators/check_docs_mirror.py` (**C-DOC-01**) — `run_all_validators` ve proje
pre-commit'inde koşar. Projede `docs/` yoksa sessizce SKIP eder.

> Belgeyi **proje kopyasında düzenlemeyin.** Değişiklik DEV_CORE'da PR ile yapılır, sonra ayna
> senkronlanır (tek-kaynak ilkesi, ADR 0020).

## Türetilmiş çıktılar

**PDF/HTML repoya konmaz** (binary şişmesi); kaynaktan üretilir:
- Referans PDF/HTML: markdown → HTML (python `markdown`) → PDF (Chromium `page.pdf`).
- Slayt PDF: slayt-CSS'li HTML → Chromium `page.pdf` (1280×720).

> Not: `marp` bu ortamda açık-tarayıcı profil çakışmasıyla takılıyor; PDF üretimi
> doğrudan Chromium (mmdc'nin puppeteer'ı) ile yapılır.
