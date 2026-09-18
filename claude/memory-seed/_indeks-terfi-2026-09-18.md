---
name: _indeks-terfi-2026-09-18
description: 2026-09-18 tohum terfisi (54 ders) — konu başlıklarıyla gruplu tam indeks
metadata: 
  node_type: memory
  type: reference
---

# 2026-09-18 tohum terfisi — tohum indeksi

> Bu dersler mevcut konu hub'larına DEĞİL bu dosyaya yazıldı: tohumlama merge-safe'tir, kurulu bir
> makinede var olan hub'ı EZMEZ ⇒ oraya eklenen satır o makineye hiç ulaşmaz. Yeni bir hub dosyası
> ise her makineye kopyalanır ve `MEMORY.md`'deki tek satırı `seed_memory` indekse ekler.

**54 ders.**

## Kanıt · ölçüm · doğrulama disiplini

- ⭐ [Ayni hash degil olu kod](feedback_ayni-hash-degil-olu-kod.md) — Kopya dosya silmeden önce REFERANS ölç — aynı hash'te olmak ölü olmak değildir
- ⭐ [Dogrulama sezgileri dort kural](feedback_dogrulama-sezgileri-dort-kural.md) — Doğrulama sezgileri — 2026-07-09'un dört ayrı hatası tek dört cümleye indirgeniyor; gate'lerin pointer'ı yerine BUNLAR hatırlanmalı
- ⭐ [Duzeltme turu kendi ciktisina kapi ister](feedback_duzeltme-turu-kendi-ciktisina-kapi-ister.md) — Düzeltme turu, bug ÜRETİCİSİDİR — zincir kapı→düzeltme→KAPI olmalı. Bir turu denetlemek, o turun ÜRETTİĞİNİ denetlemek değildir; ikinci kapı DAR olsun (değişen satır + değişen sayının diğer geçtiği yerler) ve BAŞKA göz koşsun
- ⭐ [Duzeltme turu kendi regresyonunu uretir](feedback_duzeltme-turu-kendi-regresyonunu-uretir.md) — Kapı bulgusunu kapatan düzeltme, kapatırken YENİ bir regresyon üretebilir — ikinci kapı bunun için var; birinci kapı o kodu HİÇ GÖRMEDİ
- ⭐ [Kapsam niteleyicisini dusurme](feedback_kapsam-niteleyicisini-dusurme.md) — Bir ölçümü aktarırken kapsam niteleyicisini düşürmek doğru cümleyi YANLIŞ yapar — "HLEVEL=02'de boş" ≠ "28 satırın tamamında boş"; sayı iddiası açılıp sayılmadan aktarılmaz
- ⭐ [Metadata alan dogrulama tip kapsamli olmali](feedback_metadata-alan-dogrulama-tip-kapsamli-olmali.md) — $metadata'da alan doğrulaması DAİMA tip-kapsamlı yapılır — belge-geneli arama SAP__Signature/SADL altyapı tiplerinden sahte eşleşme üretir (canlı vaka 2026-08-07)
- ⭐ [Paylasim onbellek sorusu kaynak okumasiyla cevaplanmaz](feedback_paylasim-onbellek-sorusu-kaynak-okumasiyla-cevaplanmaz.md) — "Paylaşılıyor mu / önbellekten mi geliyor" soruları kaynak okumasıyla değil canlı ölçümle cevaplanır — anahtar çalışma zamanında doğar
- ⭐ [Run sql query max rows sessiz kirpma](feedback_run-sql-query-max-rows-sessiz-kirpma.md) — run_sql_query.py varsayilani --max-rows 100; kirpma SESSIZDIR ve "kayit yok" bulgusu gibi okunur (2026-09-07 vakasi: VBPA 551 satirin ilk 100'u -> "80 belgede AG partneri yok" YANLIS bulgusu)
- ⭐ [Yesil sinyalin kapsamini sor](feedback_yesil-sinyalin-kapsamini-sor.md) — Yeşilin KAPSAMINI sor — iki yüzü var: (1) dar bir aracın "0 bulgu"su geniş güvence sanılır (kusur araçta değil, okumada), (2) doğrulama ölçütündeki SABİT SAYI bayatlayınca ölçüt kendi boşluğunu yeşil gösterir

## Ajan · takım yönetimi

- ⭐ [Agent stall watchdog mekanizmasi](feedback_agent-stall-watchdog-mekanizmasi.md) — Background agent izleme: transcript CANLI değil, heartbeat/watchdog CANLILIK ölçer İLERLEME değil. ⚠ Yapısal olarak ENGELLENEN ajan sessiz kalır (yazacak yeri yoktur, charter yasağına uyar) — brifinge 'engellenirsen DERHAL bildir' maddesi + lidere ilerleme çapası şart. ⚠ VARYANT 3: ListAgents/TaskOutput adlandırılmış in-process ajanı GÖREMEZ (yanlış negatif) — canlılığın tek kanıtı SendMessage probe'udur.
- ⭐ [Ajan okuma disiplini tazelik](feedback_ajan-okuma-disiplini-tazelik.md) — düzenleyen-ajan Edit sonrası re-read YOK; run başı taze oku; read-only'ye Edit-eki yazma
- ⭐ [Infra turunun maliyeti testte degil kanit uretiminde](feedback_infra-turunun-maliyeti-testte-degil-kanit-uretiminde.md) — İnfra turu yavaşsa suçlu test koşumu değil, F2 envanterinin dinamik koşuma kayması ve F0b'nin tavansız olmasıdır — ölçmeden hızlandırma yapma
- ⭐ [Paralel duzenlenen dosyaya satir no cakma](feedback_paralel-duzenlenen-dosyaya-satir-no-cakma.md) — Başka bir ajanın düzenlediği dosyaya satır numarası çakmak — şerh dakikalar içinde bayatlar, metin çapası kullan
- ⭐ [Tek gateway route spawn etme](feedback_tek-gateway-route-spawn-etme.md) — Standing gateway varken yeni gateway spawn etme; SAP yazımını mevcut tek-yazıcıya route et + task owner doğru ata

## Karar · iletişim · iş yönetimi

- ⭐ [Cok katmanli degisiklik yonetimi](feedback_cok-katmanli-degisiklik-yonetimi.md) — Çapraz-kesen değişikliği katman katman keşfetme — önce tüm yüzeyi tara, sonra tek partide ilerle. ⭐ Kararın YAYILIM YÜZEYİ karar kaydına yazılır (dosya:bölüm ✅/⏳); liste tamamlanmadan karar KAPANMAZ — boş tablo kayıttan da kötüdür
- ⭐ [Flag degil icra bekleyen is kapat](feedback_flag-degil-icra-bekleyen-is-kapat.md) — Bir işi 'pending/awaiting push' diye flag'lemek onu YAPMAK değildir — ya icra et ya açıkça ertele
- ⭐ [Kapsam disi bulgu protokolu](feedback_kapsam-disi-bulgu-protokolu.md) — Kapsam dışı bug bulunca düzeltmeye girişme — karar ağacı (bizden doğdu / işi etkiliyor / mutlaka çözülmeli / ilgisiz) ve her dalda kanıt zorunlu
- ⭐ [Onay isteme formati](feedback_onay-isteme-formati.md) — Kullanıcıdan onay isterken 5 şeyi VER: hangi kural/mekanizma tetikledi · tam olarak ne yapılacak (obje/kapsam) · neden şimdi gerekiyor · onaylamazsa ne olur · senin önerin. 'Araç çalışmadı, onay ver' bir talep değil şikâyettir — kullanıcı neyi onayladığını bilemez.
- ⭐ [Once yuzey taramasi sonra is listesi](feedback_once-yuzey-taramasi-sonra-is-listesi.md) — Çok katmanlı işte (BE+FE+veri) önce TÜM yüzeyi tara, matris/iş listesi çıkar; katmanları sırayla keşfetme
- ⭐ [Sorulari tek tek sor oneriyle](feedback_sorulari-tek-tek-sor-oneriyle.md) — Birden fazla soru gerektiğinde hepsini bir arada değil TEK TEK sor — detaylı bağlam + öneri ile

## İnfra · gate · dosya yetkisi

- ⭐ [Core index dala bagli](feedback_core-index-dala-bagli.md) — CORE-INDEX proje reposunda ama içeriği `core/` junction'ının O AN hangi DALDA durduğuna bağlıdır. Core'da dal değiştirince indeks yeniden üretimi doküman sayısını DÜŞÜREBİLİR — 'doküman silinmiş' gibi görünür, oysa yalnız o dalda yok. Küçülen indeksi sorgusuz commit'leme.
- ⭐ [Devreye alma once etki olc](feedback_devreye-alma-once-etki-olc.md) — Bir gate/veri/tooling değişikliğini uygulamadan ÖNCE kablolamayı ve yükü ÖLÇ; bozma ihtimali varsa yapma, önce araştır
- ⭐ [Gate moratoryumu bes sart](feedback_gate-moratoryumu-bes-sart.md) — Yeni gate/guard/validator/hook açmak için 5 şart; gate son çaredir, kök sebep genelde gereksiz çoğaltmadır
- ⭐ [Gecmis temizligi refs pull tuzagi](feedback_gecmis-temizligi-refs-pull-tuzagi.md) — Git geçmişi temizlenecekse: force-push YETMEZ (refs/pull kalır) + temizlikten SONRA PR açma
- ⭐ [Hook negatif test exit0 iki anlamli](feedback_hook-negatif-test-exit0-iki-anlamli.md) — Hook negatif-testinde exit 0 iki anlamlıdır (serbest MI, parse-fail Mİ?) — boru harness'ı ortam-bağımlı; pozitif kontrol zorunlu
- ⭐ [Infra icin ayri acik onay sart](feedback_infra-icin-ayri-acik-onay-sart.md) — Hook/validator/gate/paylaşılan araç işi — YARATMA ya da DEĞİŞTİRME — kullanıcıdan AYRI ve AÇIK onay ister; başka bir onayın içine gömülemez, lider infra'yı pas geçip kendisi de yapamaz
- ⭐ [Kapi tek tarayicidan ibaret degildir](feedback_kapi-tek-tarayicidan-ibaret-degildir.md) — Bir kapının neyi yakaladığını ölçerken TEK yardımcı fonksiyonu denemek kapı hakkında hüküm vermez — kapı birden çok tarayıcıdan oluşabilir; ölçümü kapının GİRİŞ NOKTASINDAN yap
- ⭐ [Merge yalniz ci yesilse admin bypass yasak](feedback_merge-yalniz-ci-yesilse-admin-bypass-yasak.md) — PR merge komutu CI sonucuna KOŞULLU bağlanır (state==SUCCESS); `--admin` DEV_CORE'da hiç gerekmiyordu (ruleset gates required, reviews=0) ve bypass = kırmızıyı main'e sokmak. 2026-08-29: koşulsuz zincir kırmızı PR #181'i merge etti → revert #182
- ⭐ [Yasaklar fiziksel her projede](feedback_yasaklar-fiziksel-her-projede.md) — KESİN YASAKLAR her projede FİZİKSEL kural olmalı, link/import'a bağlı değil
- ⭐ [Yeni gate hook uretimi infra expert](feedback_yeni-gate-hook-uretimi-infra-expert.md) — Yeni gate/hook-dalı/validator/paylaşılan araç ÜRETİMİ de infra-expert işidir (fix'e özgü değil) — lider yalnız EXPRESS-mekanik + tasarım kararı + diff-review + commit; 'kablolamayı garanti et' baskısı bunu kaldırmaz

## Araç · kabuk · kodlama tuzakları

- ⭐ [Auto mode deny kararsiz yeniden dene](feedback_auto-mode-deny-kararsiz-yeniden-dene.md) — Auto-mode reddi İKİ katman: 'Blocked by classifier' KARARSIZDIR (3 kez dene) · 'has been denied' = settings deny KURALI, tekrar boşuna — kuralı bul, tam-komut allow ekle. 'Çıktı yok' = başarı olabilir, DAİMA ölç.
- ⭐ [Bash find core junctionu gormez yok sanirsin](feedback_bash-find-core-junctionu-gormez-yok-sanirsin.md) — Bash `find` Windows junction'ını (core/) traverse ETMEZ — `find . -name X` ve `find core -name X` core altındaki dosyayı BULAMAZ ve sessizce boş döner; 'YOK' sanırsın. Doğru araç PowerShell Get-ChildItem -Recurse.
- ⭐ [Canli production obje degisimi auto mode kapat](feedback_canli-production-obje-degisimi-auto-mode-kapat.md) — Canlı/deployed production SAP objesini (mevcut BO/BDEF/behavior) değiştirmek permission classifier'ın production-koruma soft-deny'ına takılır; en basit çözüm = kullanıcı auto-mode'u kapatır → doğrudan prompt onayı. Dar-permission-ekleme ile uğraşma.
- ⭐ [Git bash sap uri yol donusumu msys no pathconv](feedback_git-bash-sap-uri-yol-donusumu-msys-no-pathconv.md) — Git Bash, `/sap/bc/adt/...` gibi `/` ile başlayan argümanları Windows yoluna çevirir (`C:/Program Files/Git/sap/...`) → Python'a bozuk URI gider, InvalidURL; `MSYS_NO_PATHCONV=1` ile koş

## SAP · ABAP · RAP

- ⭐ [Adt preview bos char null render](feedback_adt-preview-bos-char-null-render.md) — ADT data-preview boş CHAR'ı `null` render eder — SQL NULL DEĞİL. Kanonik: core/playbook/adt-cds.md T13.
- ⭐ [Adt sql query 400 sebebi where terim sayisi](feedback_adt-sql-query-400-sebebi-where-terim-sayisi.md) — adt_sql_query 400'unun sebebi kolon sayisi ya da JOIN karmasikligi degil, WHERE TERIM SAYISI (olculdu 2/4 kosul OK, 7 kosul 400)
- ⭐ [Check annotasyonu fail yonunu belirlemez](feedback_check-annotasyonu-fail-yonunu-belirlemez.md) — DCL `#CHECK` tek başına ne fail-open ne fail-closed demektir — yön TÜKETİCİNİN tasarımının özelliğidir; ayrıca DCL'in VAR olduğu ayrıca ölçülmelidir
- ⭐ [Cok parametreli shlp ilk alan devralma](feedback_cok-parametreli-shlp-ilk-alan-devralma.md) — F4 devralma AD-BAZLIDIR ('ilk parametre gelir' YANLIŞ — ölçüldü+canlı test); asıl tuzak: düzeltme sonrası testin kapanışı yazılmayınca eski kusur aylarca 'açık' sanılır
- ⭐ [Edid4 sdata lchr dtint2 ile okunur](feedback_edid4-sdata-lchr-dtint2-ile-okunur.md) — IDoc segment verisi (EDID4.SDATA, LCHR) adt_sql_query ile OKUNUR — koşul: uzunluk alanı DTINT2 ile BİRLİKTE ve AÇIK alan listesiyle; SELECT * ve tek başına sdata 400 verir (Z class gerekmez)
- ⭐ [Exporting tablo parametresi hedefi temizler](feedback_exporting-tablo-parametresi-hedefi-temizler.md) — ABAP'ta EXPORTING tablo parametresi aktüel tabloyu boşaltır — zincirlenmiş çağrıda önceki mesajlar sessizce kaybolur
- ⭐ [Gateway push before activate preaudit](feedback_gateway-push-before-activate-preaudit.md) — gateway push_object class/interface'te push-before-activate canlı kernel-preaudit koşar; save-scan≠activation hata ayrımı
- ⭐ [Inactive objects tadir capraz kontrol bozuk](feedback_inactive-objects-tadir-capraz-kontrol-bozuk.md) — adt_inactive_objects'in TADIR DELFLAG çapraz kontrolü çalışmıyor — count sahte pozitif; TADIR ile elle doğrula
- ⭐ [Klasik alv birim doc dersleri 2026 07 13](feedback_klasik-alv-birim-doc-dersleri-2026-07-13.md) — <PAKET-E> oturumu core-terfi dersleri — klasik-ALV birim/fieldcat + ABAP loop + GUI-KD F1-DOCU; pointer'lar core'da
- ⭐ [Push ara kopyasi bayatlar readback bunu goremez](feedback_push-ara-kopyasi-bayatlar-readback-bunu-goremez.md) — Push aracına verilen ARA KOPYA (scratch/staging) düzeltme turunda bayat kalır; readback kapısı bunu YAPISAL OLARAK göremez çünkü kıyas canlı↔kopya, canlı↔repo değildir
- ⭐ [Push ok mesaji sahte readback esitligi](feedback_push-ok-mesaji-sahte-readback-esitligi.md) — Push '[OK] activated' + 5 yeşil kontrol kaynağın canlıya indiğini KANITLAMAZ; tek kanıt readback içerik eşitliğidir
- ⭐ [Sap yazma hatasi once known errors](feedback_sap-yazma-hatasi-once-known-errors.md) — SAP yazma/aktivasyon hatası tekrarlıyorsa ÖLÇMEDEN ÖNCE known-errors.md'de SEMPTOMU ara — hata kodu bazlı kanonik dosya odur ve çalışan yöntemi de taşır
- ⭐ [Transport numarasi istek mi gorev mi rules md otoritedir](feedback_transport-numarasi-istek-mi-gorev-mi-rules-md-otoritedir.md) — Push araçlarına İSTEK (K-tipi) numarası verilir, GÖREV (S-tipi) değil — ve doğru numaranın otoritesi çapa değil paketin .rules.md'sidir (aynı hata 3 kez)

## UI · freestyle UI5

- ⭐ [Deploy ui statik varlik korlugu](feedback_deploy-ui-statik-varlik-korlugu.md) — deploy_ui.py yalnız Component-preload'ı kanıtlar; in-app yardım (webapp/help/**) kör noktadır → verify_ui_static_assets.py ayrıca koşulmalı. Ham byte kıyası BSP enjekte-metası yüzünden 12/12 yanlış-pozitif verir.
- ⭐ [Ui local run paket workspace node modules](feedback_ui-local-run-paket-workspace-node-modules.md) — UI5 uygulamasını lokal çalıştırırken app dizininde npm install YAPMA — paketin ui/ workspace'inden başlat
- ⭐ [V2 function import buyuk yuk 414 batch](feedback_v2-function-import-buyuk-yuk-414-batch.md) — OData V2 callFunction büyük yük taşıyorsa HTTP 414 — duvar Web Dispatcher, çözüm o tek çağrı için useBatch:true ikinci model

## Doküman · spec

- ⭐ [Enduser doc no sa38 se38 program run](feedback_enduser-doc-no-sa38-se38-program-run.md) — Son kullanıcı dokümanında SA38/SE38/SE80 ile program çalıştırma ASLA önerilmez; erişim yoksa yöneticiye yönlendir
- ⭐ [Fs govdesi analiz gunlugu degil uc katman](feedback_fs-govdesi-analiz-gunlugu-degil-uc-katman.md) — FS/TS/KD gövdesi = kapanmış hedef durum; karar günlüğü (11-A/11-B/EK-B) ve analiz süreci AYRI katman — sürüm etiketi/gate-ID/'canlı ölçüldü'/kullanıcı alıntısı gövdeye yazılmaz (İLKE-2b)
- ⭐ [Fs ts iki zihniyet disiplini](feedback_fs-ts-iki-zihniyet-disiplini.md) — FS'i kullanıcı-gözüyle, TS'i developer-gözüyle yaz; danışman katkısı=öneri(onay); açık nokta build'e ertelenmez; TS FS'i denetler
- ⭐ [Mesaj envanteri tasarim asamasinda kurgulanir](feedback_mesaj-envanteri-tasarim-asamasinda-kurgulanir.md) — Bir geliştirmenin üreteceği HER mesaj TS'te envanterlenir (no/tip/birebir metin ≤73/numaralı yer tutucu/üretim noktası/kullanıcı aksiyonu); build ortasında doğan mesaj bloke eden onay turu açar

<!-- makine-okunur erişilebilirlik çapası (C-MEM-01): indeks bütünlüğü kapısı
     cift-koseli-parantez linki arar, markdown link saymaz. Liste yukarıdakiyle AYNI olmalı. -->
[[feedback_ayni-hash-degil-olu-kod]] · [[feedback_dogrulama-sezgileri-dort-kural]] · [[feedback_duzeltme-turu-kendi-ciktisina-kapi-ister]] · [[feedback_duzeltme-turu-kendi-regresyonunu-uretir]] · [[feedback_kapsam-niteleyicisini-dusurme]] · [[feedback_metadata-alan-dogrulama-tip-kapsamli-olmali]] · [[feedback_paylasim-onbellek-sorusu-kaynak-okumasiyla-cevaplanmaz]] · [[feedback_run-sql-query-max-rows-sessiz-kirpma]] · [[feedback_yesil-sinyalin-kapsamini-sor]] · [[feedback_agent-stall-watchdog-mekanizmasi]] · [[feedback_ajan-okuma-disiplini-tazelik]] · [[feedback_infra-turunun-maliyeti-testte-degil-kanit-uretiminde]] · [[feedback_paralel-duzenlenen-dosyaya-satir-no-cakma]] · [[feedback_tek-gateway-route-spawn-etme]] · [[feedback_cok-katmanli-degisiklik-yonetimi]] · [[feedback_flag-degil-icra-bekleyen-is-kapat]] · [[feedback_kapsam-disi-bulgu-protokolu]] · [[feedback_onay-isteme-formati]] · [[feedback_once-yuzey-taramasi-sonra-is-listesi]] · [[feedback_sorulari-tek-tek-sor-oneriyle]] · [[feedback_core-index-dala-bagli]] · [[feedback_devreye-alma-once-etki-olc]] · [[feedback_gate-moratoryumu-bes-sart]] · [[feedback_gecmis-temizligi-refs-pull-tuzagi]] · [[feedback_hook-negatif-test-exit0-iki-anlamli]] · [[feedback_infra-icin-ayri-acik-onay-sart]] · [[feedback_kapi-tek-tarayicidan-ibaret-degildir]] · [[feedback_merge-yalniz-ci-yesilse-admin-bypass-yasak]] · [[feedback_yasaklar-fiziksel-her-projede]] · [[feedback_yeni-gate-hook-uretimi-infra-expert]] · [[feedback_auto-mode-deny-kararsiz-yeniden-dene]] · [[feedback_bash-find-core-junctionu-gormez-yok-sanirsin]] · [[feedback_canli-production-obje-degisimi-auto-mode-kapat]] · [[feedback_git-bash-sap-uri-yol-donusumu-msys-no-pathconv]] · [[feedback_adt-preview-bos-char-null-render]] · [[feedback_adt-sql-query-400-sebebi-where-terim-sayisi]] · [[feedback_check-annotasyonu-fail-yonunu-belirlemez]] · [[feedback_cok-parametreli-shlp-ilk-alan-devralma]] · [[feedback_edid4-sdata-lchr-dtint2-ile-okunur]] · [[feedback_exporting-tablo-parametresi-hedefi-temizler]] · [[feedback_gateway-push-before-activate-preaudit]] · [[feedback_inactive-objects-tadir-capraz-kontrol-bozuk]] · [[feedback_klasik-alv-birim-doc-dersleri-2026-07-13]] · [[feedback_push-ara-kopyasi-bayatlar-readback-bunu-goremez]] · [[feedback_push-ok-mesaji-sahte-readback-esitligi]] · [[feedback_sap-yazma-hatasi-once-known-errors]] · [[feedback_transport-numarasi-istek-mi-gorev-mi-rules-md-otoritedir]] · [[feedback_deploy-ui-statik-varlik-korlugu]] · [[feedback_ui-local-run-paket-workspace-node-modules]] · [[feedback_v2-function-import-buyuk-yuk-414-batch]] · [[feedback_enduser-doc-no-sa38-se38-program-run]] · [[feedback_fs-govdesi-analiz-gunlugu-degil-uc-katman]] · [[feedback_fs-ts-iki-zihniyet-disiplini]] · [[feedback_mesaj-envanteri-tasarim-asamasinda-kurgulanir]]
