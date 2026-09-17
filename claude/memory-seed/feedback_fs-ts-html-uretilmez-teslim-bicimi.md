---
name: feedback_fs-ts-html-uretilmez-teslim-bicimi
description: "FS/TS teslim biçimi .md + .pdf'tir — .html repoda DURMAZ ve güncellenmez; KD ise .md + .pdf + .html ister"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8f4adc5a-1688-42ff-8ec6-326eec08276e
---

**Kullanıcı kararı (2026-09-09):** *"fs-ts lerin .html leri çok gereksiz. sil onları ve güncelleme. fs-ts lerin .md ve .pdf leri gerek. kd dökümanının .md, .pdf, .html leri gerek."*

| Doküman | Teslim biçimi |
|---|---|
| **FS / TS** | `.md` + `.pdf` — **`.html` YOK** |
| **KD** (kullanıcı kılavuzu) | `.md` + `.pdf` + `.html` |

**Why:** FS/TS'in HTML'i kimse tarafından okunmuyordu; üç biçimi senkron tutmak her doküman turunda
bedel çıkarıyordu. KD'nin HTML'i ise **yük taşıyor** — uygulama içi kılavuz olarak
`ui/<app>/webapp/help/kullanici-kilavuzu.html`'e senkronlanıyor (BSP ile deploy edilir).

**How to apply:**
- `.html` **ara üründür**, zincir: `.md` → `docs/**/build_*_pdf_*.py` → `.html` → `node scripts/html_to_pdf.js` → `.pdf`.
  Üreticiler bozulmadı; FS/TS için HTML yerelde doğar, **git görmez**.
- Uygulama (2026-09-09): 48 takipli FS/TS `.html` `git rm -f` ile silindi; `.gitignore`'a
  `SOURCE_CODES/**/FS-*.html` + `SOURCE_CODES/**/TS-*.html` eklendi. 26 KD `.html` **dokunulmadı**.
- Doküman turunda FS/TS için **yalnız `.md` düzenle, sonra `.pdf` üret**. HTML'i commit'leme,
  HTML'de içerik sondası arama, "html bayat" diye bulgu yazma.
- ⚠ Ayrı ve **açık** kalem: 33 FS/TS `.md`'nin `.pdf`'i yok (gerçek boşluklar <PAKET-A> · <PAKET-B> ·
  <PAKET-C>-v2 · <PAKET-D> · <PAKET-E> · <PAKET-F> · <PAKET-G>; kalanlar taslak/parça/ref_docs). Bu kararla
  yaratılmadı, önceden vardı.

İlgili: [[feedback_turetilmis-artefakt-sondasi-tablo-hucresini-krar]] · [[feedback_teslim-paketi-artefakttan-ayri-yasar]] · [[feedback_dokuman-turu-donmus-kod-ister-paralel-kosturma]]
