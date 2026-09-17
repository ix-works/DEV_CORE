---
name: feedback_sizinti-taramasinin-arama-uzayi-prin-main-deltasidir
description: "Gerçek-veri/PII sızıntı taramasında arama uzayı 'teslim dökümanları' DEĞİL, PR'ın main'e koyacağı DELTA'dır (git diff origin/main...HEAD + git status). Ayrıca üretilmiş artefakt kirliyse ÜRETEÇ de o uzayın içindedir."
metadata:
  node_type: memory
  type: feedback
---

**KURAL — iki parçalı:**

**(1) Arama uzayı = PR'ın main'e koyacağı DELTA.** Sızıntı taraması (gerçek müşteri adı,
PII, canlı ana veri) yaparken uzay "teslim ettiğim dökümanlar" değildir. Uzay şudur:
```
{ git diff --name-only origin/main...HEAD } ∪ { git status --porcelain }
```
Yani **commit'li + commit'siz**, dalın main'e taşıyacağı her dosya. Bir dosyanın "teslim
artefaktı olmaması" onu uzaydan çıkarmaz — merge onu yine de main'e koyar.

**(2) Üretilmiş artefakt kirliyse ÜRETEÇ de kirlidir, ve o da uzaydadır.** `.pdf`/`.html`
temizlenip `build_*.py` bırakılırsa bir sonraki koşum kirliliği geri getirir; üstelik
üreteç genelde **daha çok** taşır (yorumunda "canlı X'ten okudum" der).

**ÖLÇÜLMÜŞ VAKA (2026-09-09, ZSD001 teslimat toplama listesi).** Doküman kapısı BLOCKER
vermişti: "gerçek müşteri verisi". Ben düzeltmeden sonra tarayıp **"0 eşleşme, temiz"**
dedim — uzayım `KD.md` + `KD.html` + `webapp/help/` + `localService/` idi. Kapı ikinci
turda `docs/shipment/mock_toplama/` altında **<MUSTERI-B> OTOMOTIV SAN. VE TİC. A.Ş** +
`<CARI-2>` + `REXROTH …` buldu. İki ayrı ölçüm boşluğu:
- **Benimki:** dar uzay. Doğru uzayı kurunca (**101 dosya**) gerçek kirlilik yalnız
  `mock_toplama/` çıktı (7 dosya); kalan 8 eşleşme zararsızdı (dizin adı
  `<musteri-b>_cpi_delfor`, mühendislik notundaki müşteri numarası, main'de zaten var olan dosya).
- **Kapınınki:** yalnız çıktıya baktı. `build_mock.py:266-268` gerçek `SoldTo`/ad taşıyordu
  ve `:118-120` bunu **canlı KNA1'den** okuduğunu yazıyordu
  (`SELECT kunnr,name1 FROM kna1 WHERE kunnr='<CARI-2>'`). Ayrıca kapı `git status`'taki
  `??` işaretine bakıp "henüz commit edilmemiş, risk var" dedi; `origin/main` karşılaştırması
  yapsaydı görecekti: **14/14 dosya zaten dalda commit'li**, PR onları taşıyacaktı.

**Why:** "Teslim dökümanı" bir **rol** tanımıdır, git'in umurunda değildir. Merge, rolüne
bakmadan delta'nın tamamını main'e yazar. Ve bu sessiz bir kusurdur: doküman kapıları
FS/TS/KD'ye bakacak şekilde kurgulanmıştır, yan klasördeki mock/scratch üretimini
görmezler. [[feedback_hicbir-yerde-yok-demeden-once-nerelere-baktigini-yaz]] burada
"nereye baktığını yaz"ın ötesine geçer: **uzayı git'e sorduracaksın**, kendi kafandan
kurmayacaksın.

**How to apply:**
- Sızıntı/PII taramasından önce uzayı üret ve **dosya sayısını yaz** ("101 dosya tarandı").
  Sayı yazmıyorsan uzay beyan edilmemiştir.
- PDF'i `grep`'lemek işe yaramaz — `pymupdf` ile metin çıkar, sonra tara.
- Her eşleşmeyi **triyaj et**: dizin adı / proje anlatısı / mühendislik notu ≠ teslim
  dökümanındaki örnek veri. Ham eşleşme sayısı bulgu sayısı değildir
  ([[feedback_ham-satir-sayisi-is-nesnesi-sayisi-degildir]]).
- Kirli çıktı bulursan **üreteci de aç**: `build_*.py` / `capture_*.js` / `gen_*.py`.
  Düzeltmeyi üretece yap, sonra çıktıyı **yeniden üret** — elle metin değiştirirsen
  üreteçle disk ayrışır ve bir sonraki koşum geri getirir.
- Bir dosyanın "yeni/riskli" olup olmadığını `git status`'un `??` işaretinden çıkarma;
  ayırt edici test **`git cat-file -e origin/main:<dosya>`**'dır.
