---
name: _indeks-terfi-2026-11-15
description: 2026-11-15 tohum terfisi (20 ders, DEV_CORE#441) — konu başlıklarıyla gruplu tam indeks
metadata:
  node_type: memory
  type: reference
---

# 2026-11-15 tohum terfisi — tohum indeksi

> Bu dersler mevcut konu hub'larına DEĞİL bu dosyaya yazıldı: kurulu bir makinede hub yerelde
> düzenlenmişse tohumlama onu EZMEZ ⇒ oraya eklenen satır o makineye ulaşmaz. Yeni bir hub dosyası
> ise her makineye kopyalanır ve `MEMORY.md`'deki tek satırını `seed_memory` indekse ekler
> (2026-10-18 ve 2026-11-12 terfilerinin emsali). Kaynak: tüketici bir klonun Issue ile gönderdiği
> 23 ders. 3'ü çekirdekte zaten kanonik olduğu için tohuma alınmadı (çoğaltma drift üretir).
> Çekirdek kuralına dayanan dersler (gün sonu, `--wt-denetim`) kısa tutuldu ve çekirdeğe atıf verir.

**20 ders.** UI 7 · Kanıt 4 · Ajan 3 · Süreç 3 · SAP 3

## UI · freestyle UI5

- [Ui testi dom varligi gorunurluk ve olay parametresi](feedback_ui-testi-dom-varligi-gorunurluk-ve-olay-parametresi.md) — DOM'da var olmak görünür olmak değildir (rect + elementFromPoint); olay parametre adı UI5 kaynağından; üretim kodunu kopyalayan düzenek aynı hatayı taşır
- [Ui testinin son kontrolu sunucu durumunu olcmeli](feedback_ui-testinin-son-kontrolu-sunucu-durumunu-olcmeli.md) — Kayıt senaryosunun son kontrolü ekrandaki kirli modeli okursa test sahte-yeşildir; sunucu/mock durumunu ölç, mutasyonla kanıtla
- [Onay diyalogu afterclose](feedback_onay-diyalogu-afterclose-once-sozu-sonuclandir-sonra-destroy.md) — Promise sarmalı onay diyalogunda afterClose önce sözü sonuçlandırır, SONRA destroy; tersi Esc'te sözü asılı bırakır
- [Yazmadan hemen once taze etag okumak](feedback_yazmadan-hemen-once-taze-etag-okumak-iyimser-kilidi-sifirlar.md) — If-Match'e kullanıcının GÖRDÜĞÜ sürümün etag'i gider; yazmadan önce taze etag okumak iyimser kilidi sıfırlar
- [Ui5 yapici ayarinda suslu parantez baglamadir](feedback_ui5-yapici-ayarinda-suslu-parantez-baglamadir.md) — Yapıcıya verilen `{…}` içeren metin bağlama sayılır ve boşalır; setter ile ver
- [Ui5 mockserver batch etag iki nokta keser](feedback_ui5-mockserver-batch-etag-iki-nokta-keser.md) — MockServer $batch başlığı ':' ile böler; ':' içeren ETag sahte 412 üretir (tek vaka)
- [Cdn surum varligi surum dosyasiyla kanitlanmaz](feedback_cdn-surum-varligi-surum-dosyasiyla-kanitlanmaz.md) — Maket/yerel çalıştırmada CDN sürümü sap-ui-version.json 200 ile kanıtlanmaz; kütüphane dosyasını ölç

## Kanıt · ölçüm

- [Canli test oracle sistem kaydi](feedback_canli-test-oracle-sistem-kaydi-uygulama-durumu-degil.md) — Canlı testte doğruluk kaynağı standart sistemin kaydıdır (önce/sonra farkı); taklit edilen API'nin commit varsayımı ayrıca ölçülür
- [Gorunen hata son denemenin yanitidir](feedback_gorunen-hata-son-denemenin-yanitidir-ilk-tekrarda-ham-iz-ve-kontrol.md) — Çok-denemeli araçta görünen hata son denemenin yanıtı olabilir; aynı hata ikinci kez gelince ham iz + kontrol grubu
- [Yeni surum api yoklugu denetim yoklugu degildir](feedback_yeni-surum-api-yoklugu-denetim-yoklugu-degildir.md) — Yeni denetim API'sinin yokluğu eski sürümde denetim yok demek değildir; SNAPT/T100'ü ara
- [Kayit tarihi saatten alinir](feedback_kayit-tarihi-saatten-alinir.md) — Kayda yazılan tarih çıkarımla değil `date`/`git log`'dan; `grep -c` satır sayar, geçiş değil

## Ajan · takım

- [Bekci yeniden kurulunca tabani kayar](feedback_bekci-yeniden-kurulunca-tabani-kayar-sabit-baslangic-ver.md) — Monitor yeniden kurulunca agent_stall_watch tabanı kayar; sabit `--baslangic` ver, BAKMADIGI satırını süzme
- [Re gate dar kapsam yalniz high durdurur](feedback_re-gate-dar-kapsam-yalniz-high-durdurur.md) — Düzeltme sonrası re-gate yalnız değişen satırlara bakar; yalnız HIGH yeni tur açar
- [Belge incelemesinde kayit duzeni ve tasarim turu](feedback_belge-incelemesinde-fable-kayit-duzeni-opus-tasarim.md) — Büyük FS/TS'te kontrol listesi turu ile senaryo odaklı tasarım incelemesi ayrı koşulur

## Süreç · oturum · git

- [Ekran teyidi gorev mesajinda da ilk cikti](feedback_ekran-teyidi-gorev-mesajinda-da-ilk-cikti.md) — İlk mesaj iş istese de Ekran Teyidi ilk metin çıktısıdır; compact sonrası istenmez
- [Gun sonu dal pr ile maine girer](feedback_gun-sonu-dal-pr-ile-maine-girer.md) — Gün sonu = iş dalı PR ile main'e girer; dalı push'lamak yetmez (çekirdek §1.1)
- [Wt denetim entegrasyon dali hukmu](feedback_wt-denetim-entegrasyon-dali-uzerinden-birlesen-dal-hukmu.md) — `--wt-denetim` ② FAIL'inde entegrasyon dalı yolu: PR'dan üç ölçüm, ③ temiz değilse `--zorla` yok; `--is-ancestor` yalnız dal→entegrasyon gerçek merge'ünde

## SAP · ABAP / RAP

- [Rap isleyicide submit yasak](feedback_rap-isleyicide-submit-yasak-destination-none-izinli.md) — RAP işleyicide SUBMIT/iş planlama yasak; DESTINATION 'NONE' sRFC modify fazında izinli (belgeden, ölçülmedi)
- [Read entities bo disi tamponu gormez](feedback_read-entities-bo-disi-tamponu-gormez.md) — additional save'de BO-dışı tabloya yazılacak satırlar READ ENTITIES'te görünmez; DB ∪ tampon (tasarım, ölçülmedi)
- [Sessiz yanlis fiyat gorunur eksikten agir](feedback_sessiz-yanlis-fiyat-gorunur-eksikten-agir.md) — Sessiz yanlış fiyat, görünür fiyat eksikliğinden daha ağır risktir

<!-- makine-okunur erişilebilirlik çapası (C-MEM-01): indeks bütünlüğü kapısı
     cift-koseli-parantez linki arar, markdown link saymaz. Liste yukarıdakiyle AYNI olmalı. -->
[[feedback_ui-testi-dom-varligi-gorunurluk-ve-olay-parametresi]] · [[feedback_ui-testinin-son-kontrolu-sunucu-durumunu-olcmeli]] · [[feedback_onay-diyalogu-afterclose-once-sozu-sonuclandir-sonra-destroy]] · [[feedback_yazmadan-hemen-once-taze-etag-okumak-iyimser-kilidi-sifirlar]] · [[feedback_ui5-yapici-ayarinda-suslu-parantez-baglamadir]] · [[feedback_ui5-mockserver-batch-etag-iki-nokta-keser]] · [[feedback_cdn-surum-varligi-surum-dosyasiyla-kanitlanmaz]] · [[feedback_canli-test-oracle-sistem-kaydi-uygulama-durumu-degil]] · [[feedback_gorunen-hata-son-denemenin-yanitidir-ilk-tekrarda-ham-iz-ve-kontrol]] · [[feedback_yeni-surum-api-yoklugu-denetim-yoklugu-degildir]] · [[feedback_kayit-tarihi-saatten-alinir]] · [[feedback_bekci-yeniden-kurulunca-tabani-kayar-sabit-baslangic-ver]] · [[feedback_re-gate-dar-kapsam-yalniz-high-durdurur]] · [[feedback_belge-incelemesinde-fable-kayit-duzeni-opus-tasarim]] · [[feedback_ekran-teyidi-gorev-mesajinda-da-ilk-cikti]] · [[feedback_gun-sonu-dal-pr-ile-maine-girer]] · [[feedback_wt-denetim-entegrasyon-dali-uzerinden-birlesen-dal-hukmu]] · [[feedback_rap-isleyicide-submit-yasak-destination-none-izinli]] · [[feedback_read-entities-bo-disi-tamponu-gormez]] · [[feedback_sessiz-yanlis-fiyat-gorunur-eksikten-agir]]
