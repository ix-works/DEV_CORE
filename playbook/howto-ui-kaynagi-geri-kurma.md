---
applies_to: [s4_private]
---
# How-To: UI kaynağı yok ya da başka makinede revize edildi — BSP'den geri kur, eşle, güvenli deploy et

> **Ne zaman:** Freestyle UI5 uygulamasında değişiklik istendi ve **(a)** kaynak repoda/diskte YOK
> (yalnız SAP'ye deploy edilmiş), ya da **(b)** yerel kaynak var ama canlının başka bir makinede
> revize edilip deploy edildiğinden şüpheleniliyor, ya da **(c)** yerel kaynağın canlıyla aynı
> olduğu hiç ölçülmedi. `deploy_ui.py` ve `standards/03-coding-ui-fiori.md` §2.4.1 kaynağın
> yerelde **var ve güncel** olduğunu varsayar; bu dosya o varsayımı ölçen yoldur.
> Kaynak: Issue #304 (2026-09-26). Araç: `scripts/fetch_ui_source.py` (yalnız GET, SAP'ye yazmaz).
> ⛔ Kaynağı olmayan bir uygulamayı **tahminle yeniden yazma** ve eşliği ölçülmemiş bir kaynaktan
> **deploy etme** — ikisi de canlıdaki başka bir işi sessizce ezer.

## 0. Neden bu yol (ölçülmüş gerçekler)

| Gerçek | Sonuç |
|---|---|
| BSP'de **build çıktısı** durur (dist): küçültülmüş `X.js` + özgün `X-dbg.js` + `X.js.map` + `Component-preload.js` | Kaynak `-dbg` dosyalarından geri kurulur; `X.js.map`'in `sources`u `X-dbg.js`'i gösterir (3 BSP · 21/21 harita) |
| İndirme = `ABAP_REPOSITORY_SRV` zip (tek GET) | ICF yolu (`/sap/bc/ui5_ui5/…`) KULLANILMAZ: dizin listelemez, HTML'e meta enjekte eder (§2.4.2) |
| SAP metin dosyalarını **CRLF** saklar | Geri kurma metni LF yazar; ikili (PNG) ham kalır — PNG başlığı `\r\n` baytı taşır |
| `ui5 build` iki dönüşüm yapar: `.properties` → `\uXXXX`, manifest'e `flexBundle` + `supportedLocales` ekler | Yerelle kıyasta bunlar `BUILD-DONUSUMU` diye AYRI etiketlenir; başka hiçbir fark gevşetilmez |
| Yalnız **preload** kıyası eşliği kanıtlamaz | `-dbg`'deki yalnız-yorum farkı küçültmede kaybolur, preload EŞİT çıkar; iz `.map`'te kalır ⇒ eşlik kapısı preload **+ tam liste + kaynak haritası sondası** ister |

## 1. Ön koşul

- Proje kökünde `.conn_adt` (araç `deploy_ui.read_conn()` ile okur — env `CLAUDE_PROJECT_DIR` → cwd).
- Eşlik için `ui5` CLI: PATH'te yoksa bir kardeş uygulamanın `node_modules`'ı:
  `--ui5-cli "<ui>/node_modules/.bin/ui5"` (Windows'ta `ui5.cmd`).
- Git Bash'te `/sap/...` argümanı verirsen `MSYS_NO_PATHCONV=1` (araç URL'i kendisi kurar; normalde gerekmez).
- Çıktıyı **scratch** dizine yaz (`<scratch>` = oturumun geçici dizini); `--out` dolu dizine yazmaz.

## 2. Akış (sıra atlanmaz)

```
① İNDİR + ANLIK GÖRÜNTÜ  → ② EŞLİK  → ③ KARŞILAŞTIR  → ④ GERİ KUR / YERLEŞTİR
→ ⑤ DÜZENLE  → ⑥ LOKAL TEST  → ⑦ KULLANICI ONAYI  → ⑧ DEPLOY ÖNCESİ LİSTE + DRIFT
→ ⑨ deploy_ui.py  → ⑩ TAM LİSTE DOĞRULAMA
```

**① İndir + anlık görüntü** — sonraki her adım AYNI anlık görüntüyle çalışır:
```bash
python core/scripts/fetch_ui_source.py --bsp ZSD001_APP --zip-kaydet <scratch>/canli-ilk.zip \
       --out <scratch>/webapp-ilk
# BSP adı ui5-deploy.yaml'dan: --app-dir <ui>/<app>
```
`<scratch>/webapp-ilk` DONMUŞ kopyadır (⑧'deki drift kıyasının tabanı) — üzerinde çalışma.

**② Eşlik — geri kurulan kaynak canlıyı ÜRETİYOR mu?**
```bash
python core/scripts/fetch_ui_source.py --zip <scratch>/canli-ilk.zip --eslik --ui5-cli "<ui>/node_modules/.bin/ui5"
```
| Sonuç | Anlamı | Ne yapılır |
|---|---|---|
| `ESLIK-TAM` (rc 0) | preload sha eşit + tam liste birebir + harita temiz | devam |
| `ESLIK-SATIR-SONU` (rc 0) | içerik modül modül eşit; fark YALNIZ kaçışlı `\r\n` (canlı CRLF çalışma ağacından build edilmiş) | devam — ayrı kova, bayt-eş değildir |
| `ESLIK-YOK` (rc 1) | build canlıyı üretmiyor ya da `-dbg` özgün kaynak değil (TypeScript/transpile/özel build) | ⛔ **DUR** — kaynağı kullanıcıdan iste; geri kurulan dosyayla devam ETME |
| `OLCULEMEDI` (rc 2) | ağ / ui5 CLI yok / zip'te preload yok | ölçülmedi ≠ temiz — nedeni gider, yeniden koş |

**③ Karşılaştır** (yerel kaynak VARSA):
```bash
python core/scripts/fetch_ui_source.py --zip <scratch>/canli-ilk.zip --karsilastir <ui>/<app>/webapp
```
- `GERCEK-FARK` / `YALNIZ-CANLI` = canlıda, yerelde olmayan bir değişiklik var (başka makinede
  revize edilmiş). ⛔ Hangisinin otorite olduğuna **kullanıcı karar verir**; araç yerel dosyanın
  üzerine yazmaz. Diff'i kullanıcıya göster.
- `YALNIZ-YEREL` = deploy edilmemiş yerel dosya (ör. `test/**`) ya da henüz deploy edilmemiş iş.
- `BUILD-DONUSUMU` normaldir (i18n `\uXXXX`, manifest'in iki build alanı).

**④ Geri kur / yerleştir** (kaynak YOKSA ya da kullanıcı canlıyı otorite seçtiyse):
```bash
python core/scripts/fetch_ui_source.py --zip <scratch>/canli-ilk.zip --out <scratch>/webapp
```
- `<scratch>/webapp`'i `<ui>/<app>/webapp`'e taşı. `package.json` / `ui5.yaml` / `ui5-deploy.yaml`
  bir **kardeş uygulamadan** kopyalanır: `metadata.name` = manifest `sap.app.id`; `ui5-deploy.yaml`
  `app.name` = BSP, paket ve transport **kullanıcıdan** (ADR 0005-C: transport yaratılmaz).
- Geri kurulan hâli **ayrı bir commit** olarak kaydet ("canlıdan geri kuruldu"); asıl değişiklik
  sonraki commit'tir — diff okunabilir kalır.

**⑤ Düzenle** — normal FE akışı (standards/03). Düzenlemeden önce ③'ü yeniden koşmak ucuzdur.

**⑥ Lokal test** — `npm start` (proxy'li lokal sunucu; standards/03 §2.2–§2.3). ⚠ Çekirdekte **salt-okur
proxy YOK** (ertelenmiş kalem): lokal test canlı OData'ya bağlanır, yazan eylemleri (kaydet/post)
bilinçli tetikle ya da tetikleme.

**⑦ Kullanıcı onayı** — lokal test OK'si olmadan deploy yok.

**⑧ Deploy öncesi: liste + drift**
```bash
npm --prefix <ui>/<app> run build
python core/scripts/fetch_ui_source.py --app-dir <ui>/<app> --zip-kaydet <scratch>/canli-son.zip \
       --dist-karsilastir <ui>/<app>/dist
python core/scripts/fetch_ui_source.py --zip <scratch>/canli-son.zip --karsilastir <scratch>/webapp-ilk
```
- İlk komut: canlı ham liste ↔ deploy edilecek `dist`. `YALNIZ-CANLI` (rc 1) = canlıda olup yeni
  deploy kümesinde olmayan dosya (§2.4: yanlış `excludes` ile düşen `localService/**`) → bilinçli
  silme değilse DUR. `DEGISECEK` listesi senin değişikliklerinle örtüşmeli.
- İkinci komut **drift**'tir: `<scratch>/webapp-ilk` = ①'de donmuş geri kurulan hâl.
  `GERCEK-FARK` = sen çalışırken **başkası deploy etmiş** → DUR, kullanıcıya bildir.

**⑨ Deploy** — yalnız `python core/scripts/deploy_ui.py --app <app>` (§2.4.1; yalın `fiori deploy` YASAK).

**⑩ Tam liste doğrulama** — `deploy_ui` yalnız preload'u kanıtlar (§2.4.2):
```bash
python core/scripts/fetch_ui_source.py --app-dir <ui>/<app> --dist-karsilastir <ui>/<app>/dist \
       --karsilastir <ui>/<app>/webapp
```
Beklenen: `YALNIZ-CANLI=0 · değişecek=0 · yalnız-dist=0` ve `GERCEK-FARK=0`.

## 3. Kapsam sınırı (araç her koşumda KAPSAM BEYANI basar — oku)

- Ölçülen: `s4_private`, freestyle UI5 1.120, OData V2, JavaScript kaynak, @ui5/cli 4.x.
- **Ölçülmedi:** canlı TypeScript BSP (harita sondası yalnız sentetik `.ts` ile) · Fiori Elements ·
  namespace'li BSP adı (`/X/…`) · `s4_public`/`btp_abap` · deploy'un canlıdan dosya SİLME
  davranışı · ADT filestore yolu (`/sap/bc/adt/filestore/ui5-bsp/…`; bir makinede zaman aşımı).
- Canlı = indirilen zip anı; ICF servis katmanı ölçülmez.

## İlgili
- `scripts/fetch_ui_source.py` (docstring: kipler, çıkış kodları) · `scripts/deploy_ui.py` · `scripts/verify_ui_static_assets.py`
- [`../standards/03-coding-ui-fiori.md`](../standards/03-coding-ui-fiori.md) §2.4 (excludes notu) · §2.4.1 · §2.4.2
- [`ui-freestyle-odata-v2.md`](ui-freestyle-odata-v2.md)
