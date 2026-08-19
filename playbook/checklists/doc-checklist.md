---
applies_to: [s4_private]
---
# Doc-Checklist — Kullanıcı/Teknik Dökümanlar (KD / FS / TS)

> **Doc-Gate reviewer bunu kullanır** (kod bug-gate'inin doküman karşılığı, ADR 0018 deseni). KD/FS/TS **üretilince veya değişince**, lider'e "bitti" denmeden ÖNCE **bağımsız + TAZE** bir reviewer dökümanı bu listeye karşı inceler → verdict **PASS / WARNING / BLOCKER**. Self-verify (yazarın kendi kontrolü) YETMEZ — bağımsız göz şart.
>
> Her madde **HATA** (kural ihlali — zorunlu fix) / **EKSİK** (must-do karşılanmamış) / **ÖNERİ** (bağlayıcı değil) tiplenir. Kapsam = dökümanın TAM içeriği + üretilen artefaktlar (md + HTML + PDF + ekran görüntüleri + app'e bağlanan kopya).
>
> Kaynak: `standards/04-documentation-fs-ts.md` (§1.3 görsel ilkesi · §2.3 FS · §3.3 TS · §4.2-4.5 KD) · `playbook/howto-kullanici-dokumani-pdf-ekran-goruntulu.md` (üretim+§C doğrula) · ADR 0008 (grid-liste).

> **⛔ İKİNCİ KAPI — bir düzeltme turu, kendi çıktısına kapı koşmadan KAPANMAZ (2026-08-19).**
> `kapı → düzeltme → (kapı yok)` zinciri açık kaldıkça **düzeltmenin kendisi** bulgu üretir: bir RAP
> doküman setinin kapı turunda 6 kapının **44 HIGH/MEDIUM** bulgusunun **~%40'ı önceki düzeltme
> turlarının kendi çıktısından** doğdu. Vaka: *"şu iş kuralının arama penceresi kaldırıldı"* kararı
> TS'in 3 yerinde uygulandı, bir sonraki bölümün **normatif sözde-kodunda** kaldı ⇒ belgeye sadık
> geliştirici **iptal edilmiş kuralı** kodlayacaktı (mükerrer sipariş + teslimat + MÇ + fatura).
> **İkinci kapı DAR kapsamlıdır — tam yeniden okuma DEĞİL**, yalnız üç yüzey:
> ① değişen satırlar ② değişen her **sayının/adın** belgedeki DİĞER geçtiği yerler (DOC-CR-02)
> ③ kararın **yayılım listesi** (std 04 §2.0 İLKE-2b Katman-2 · yayılım tablosu).
> **Bağımsızlık:** ikinci kapıyı **birinci kapıyı koşan göz koşamaz.**
> ⚠ Dar kapsam kuralın parçasıdır, kolaylık değil: geniş tutulursa **"kapı yorgunluğu"** doğar ve
> gate mekanik onaya döner (= gate'in kendisini kaybetmek).

## §A — KULLANICI DÖKÜMANI (KD)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| DOC-KD-01 | **Ekran görüntüleri MOCK/TEMİZ örnek veriyle** — anlamlı/tutarlı uydurma kayıt (client-model injection). Kirli/gerçek backend kaydı (test çöpü "E2E Test"/"NR otomatik test", gerçek müşteri/PII, tutarsız satır) = ihlal. Gerçek UI evet, gerçek VERİ hayır | **BLOCKER** (HATA) | std §1.3 · howto §A/§D.0 |
| DOC-KD-02 | **Gerçek UI kullanılmış, mockup değil** (KD geliştirme-sonrası); görüntüler işaretli/numaralı (ok/daire/callout), ham değil | HIGH (HATA) | std §1.3 / §4.3 |
| DOC-KD-03 | **TÜM sub-screen'ler var** (dialog/popover/value-help-F4/picker/sihirbaz) — her biri ayrı bölüm + görüntü + alan/buton fonksiyonu; view+fragment envanteri KD'ye eşlendi (atlanan yok) | BLOCKER (EKSİK) | std §4.3 |
| DOC-KD-04 | **Grid-liste varsa BÖLÜM 4-A** (tablo başlık araçları: sıralama/filtreleme/kolonlar/varyant/Excel'e aktar/yenile + filtre çubuğu) sabit/fix anlatılmış | HIGH (EKSİK) | std §4-A · ADR 0008 |
| DOC-KD-05 | **Genel bakış: amaç + ARKA PLAN SONUCU** ("Kaydet'e basınca sistemde ne oluşur") yazılı | HIGH (EKSİK) | std §4.2 B2 |
| DOC-KD-06 | **Her tipik görev: adım adım akış + ekran görüntüsü**; emir kipi (tıkla/gir/seç) | HIGH (EKSİK) | std §4.2 B5 |
| DOC-KD-07 | **Alan rehberi** (ne/format/zorunlu + NEDEN/otomatik) + **HER buton/event operasyonu** arka-plan sonucuyla | HIGH (EKSİK) | std §4.2 B6/B7 |
| DOC-KD-08 | **Hata/mesaj tablosu**: mesaj **birebir** metin + anlam + **AKSİYON** ("ne yapmalısın") | HIGH (EKSİK) | std §4.2 B9 |
| DOC-KD-09 | **Teknik terim sızmamış** (tablo/FM/BAPI/kod yok); geçen her terim sözlükte sade; SSS + destek/iletişim var | MEDIUM (EKSİK) | std §4.2 B10-12 |
| DOC-KD-10 | **İçerik canlı UI ile güncel** (bayat ekran/akış yok — değişen UI'a göre revize edilmiş); ön koşullar (yetki/ana veri/erişim) var | HIGH (HATA) | std §4.2 B3 · feedback_done-tam-kapsam-dogrula |
| DOC-KD-11 | **Üretim doğrulandı** (howto §C): PDF gerçekten oluştu + sayfa makul; TÜM görseller HTML/PDF'de görünür (broken-image 0); app'e bağlandıysa help butonu doğru dosyayı açıyor + görseller app içinde de yükleniyor | HIGH (HATA) | howto §C |
| DOC-KD-12 | **Klasik GUI in-system F1 yardımı: fihrist + link'li detay (tek-düz-sayfa DEĞİL)** — RE fihrist (program adı) + ayrı TX detay sayfaları, `<DS:TX.<ad>>` link'lerle bağlı; üretim ZSD000_CL_DOCU + program-özel runner + gateway adt_classrun (DOCU_UPDATE — ADT REST klasik doc YAZAMAZ) | HIGH (EKSİK) | **standards/08** §1/§5 |
| DOC-KD-13 | **F1 ITF format** — her sayfa ilk satır `U1` başlık (DSYST 20-char title tuzağı → başlık U1'den gelir); bold=`<ZH>...</>` (canlı-teyitli, tag-içi-tag YOK, kapanış `</>`); TDLINE ≤132; gerçek TR + UTF-8 no-BOM + TR login; markdown/HTML-entity YOK | HIGH (HATA) | **standards/08** §3/§6 |
| DOC-KD-14 | **F1 içerik kaynağı canlı (uydurma YASAK)** — tip/değer tanımları domain fixed-value'dan (adt_get), kolon/formül FS+class'tan; varsa repo markdown KD'sine paralel; classrun readback (DOKHL state=A) + ATC Prio-1=0 doğrulandı | HIGH (HATA) | **standards/08** §5/§7 |
| DOC-KD-15 | **Ham diyagram-kaynağı KD çıktısına SIZMAMIŞ** — ` ```mermaid ` (veya başka diyagram-DSL) fence build'de render EDİLMEZ → html/pdf/app-help'te `<pre><code class="language-mermaid">flowchart…` ham KOD olarak görünür (kullanıcıya çirkin/anlamsız). Diyagram = **render edilmiş PNG** olmalı (`doc_tools.preprocess_mermaid_fences` / `render_mermaid` build'e bağlı). Kontrol: KD **md + html + pdf + app-help**'te `language-mermaid` ve ham `flowchart LR` = **0**; her diyagram `<img>`/`<figure>`. Broken-image (DOC-KD-11) bunu YAKALAMAZ — mermaid kod olarak render olur, kırık görsel değil. GATE: `check_kd_no_raw_mermaid.py`. (fit_se→booking tekrarı 2026-07-02.) | HIGH (HATA) | howto §C · doc_tools.py |
| DOC-KD-16 | **"İçindekiler" bağlantıları HEDEFLİ — ölü bağlantı = 0** (HTML *ve* PDF). Doküman içi `href="#x"`in karşılığı bir **`id="x"` VEYA `<a name="x">`** OLMALI (⛔ **ikisi de geçerli hedeftir** — bu evde eski usul `name=` çıpası kullanan KD'ler var ve tarayıcı onları onurlandırır; *yalnız `id=` sayan denetim bu dokümanları "%100 ölü" diye YANLIŞ raporlar — bu yanlış-pozitif 2026-08-13'te gerçekten yaşandı, 7 uygulama hatalı biçimde "kırık" gösterildi*). Kontrol **küme** kıyasıdır, sayı kıyası DEĞİL: `{href#} \ ({id} ∪ {a name})` = **boş** (howto §C kod bloğu); PDF'te `/Subtype /Link` sayısı ≈ iç bağlantı sayısı (**0 = hiçbiri tıklanabilir değil**). İki kök sebep ayrı ayrı bakılır: ① üretici `markdown.markdown(...)`'a **`toc` eklentisi vermemiş** → başlıkların HİÇBİRİNDE id yok, TÜM içindekiler ölü ② tek tük ölü bağlantı → kaynak md'deki elle yazılmış `#hedef` başlık metniyle uyuşmuyor (başlık uzamış · TR harf · `①`/`ⓘ` işareti). ⛔ **Bu kusur SESSİZDİR:** sayfa açılır, yerleşim kusursuzdur, build "OK" der; DOC-KD-11 (broken-image) ve DOC-KD-15 (ham mermaid) bunu **YAKALAMAZ** — kırık görsel yok, ham kod yok, yalnız tıklama etkisiz. Onarımda **başlığı değil href'i** düzelt (metin kaybı riski). | HIGH (HATA) | howto §B.2/§C · `build_doc_pdf.slug_tr` |

## §B — FONKSİYONEL SPESİFİKASYON (FS)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| DOC-FS-01 | **Gerçek ekran görüntüsü YOK** — ekran **mockup + yapısal tablolarla** (alan/buton/grid/etkileşim) tanımlı (tasarım-önce zihniyet, geliştirme bitmiş olsa bile) | HIGH (HATA) | std §1.3 |
| DOC-FS-02 | **Zorunlu bölümler tam** (kapak + doküman kontrolü + giriş + iş süreci + fonksiyonel gereksinim + UI/ekran + veri + entegrasyon + yetki + raporlama + hata + test + onay) | HIGH (EKSİK) | std §2.2 |
| DOC-FS-03 | **Ne/neden** odaklı (nasıl-implemente DEĞİL); iş diliyle, çözüm-tarafsız; gereksinimler izlenebilir/numaralı | MEDIUM (EKSİK) | std §2.3 |
| DOC-FS-04 | İç tutarlılık (FS↔TS↔KD no eşleşmesi; süreç adımları ↔ gereksinim ↔ ekran çelişkisiz) | MEDIUM (EKSİK) | std §1.1 |
| DOC-FS-05 | **Gövde = kapanmış hedef durum, analiz günlüğü DEĞİL** (İLKE-2b, 3 katman). Gövdede (§1.1 ve 11-A/11-B/EK Karar-Kanıt Günlüğü HARİÇ) şunlar **0**: sürüm etiketi ("v1.5'te eklendi", "(YENİ, R-12)"), doc-gate bulgu numarası ("H-C/M-2 netleşme"), araştırma/ölçüm süreci ("canlı ölçüldü", "ilk turda yanlış okunmuştu", "400 döndü", "RESEARCH-02 ters okumuştu"), kullanıcı alıntısı ("kullanıcı: '…'"), "önceden→şimdi" anlatısı. Reviewer üslup yargısı da yapar: her paragraf **bugün geçerli hâli** mi anlatıyor, yoksa **nasıl bulunduğunu** mu? (2026-08-17: 9 sürümlük FS gövdesi %25 işaretli satırla onaya sunulamadı). **KATMAN-0 (kural DIŞI, temizlenmez):** belgenin kendi kimlik satırları — kapak `| Versiyon | v1.2 |`, §1.1 versiyon tablosu (başlığı yazılmamış olsa da; yalnız SATIR UZUNLUĞU ölçütüne tabi), §1.3 ilgili-doküman satırı, altbilgi — ve belgenin KENDİ tanımladığı gap ID'sine (`| **H-1** | …` satırıyla tanımlanmış) atıf. **BAŞLIKLAR DA GÖVDEDİR** (H1 hariç): "## 6. ETKİLENEN OBJELER (canlı-doğrulanmış…)" gibi süreç izleri başlık parantezinde saklanamaz. **"Önceden→şimdi" anlatısı** da yasaktır ("artık … değil", "R-6 revizyonu", "bu revizyonla", "ilk taslakta") — gövde bugünkü hâli anlatır, değişimi değil. ⚠ Gate BİLEREK saymadığı iki belirsiz kalıp var (reviewer bakar): çıplak "artık" (Türkçede isim de: "artık miktar") ve çıplak "bu turda" (sürecin turu olabilir). GATE (warn-first, sayım): `check_fs_no_analysis_log.py` (kalıcı korpus `tests/fixtures/fs_docstd`). | HIGH (HATA) | std §2.0 İLKE-2b · §2.3 |
| DOC-FS-06 | **§1.1 kısa + 11-B birikmemiş** — versiyon satırı 1-2 satır ("ne değişti", madde/§ atfı; "neden/nasıl bulundu" yok); §11-B'de yalnız AÇIK (ya da bloke etmeyen) kararlar — kapanan karar gövdeye SONUÇ olarak işlenmiş, satırı EK "Karar ve Kanıt Günlüğü"ne inmiş (karar/kim/ne zaman/gerekçe/kanıt atfı; reddedilen seçenek "neden dışlandı" ile). ⭐ **YAYILIM TABLOSU (2026-08-19):** her karar kaydı **dokunulacak yerlerin listesini** taşır ve liste tamamlanmadan karar **kapanmış sayılmaz** — karar N yerde yaşar, düzeltme turu N-1'ini yapar. ⛔ **Boş/eksik yayılım tablosu ⇒ kayıt GEÇERSİZ** (tablo koyup boş bırakmak, tablo koymamaktan **daha kötüdür**: koruma sanısı üretir). | MEDIUM (EKSİK) | std §2.0 İLKE-2b · §2.2 B1.1/B11-B |
| DOC-FS-07 | **Yeniden yazım/temizlikte VERİ KAYBI = 0** — gövdeden çıkan her bilgi EK'e taşınmış (silinmemiş): kimlik kümeleri (FR/BR/AC/hata kodu/SCR/T/ÖK/G/karar no) eski = yeni; mockup blokları korunmuş; sayısal/kod değerleri (tablo/alan/tcode/miktar/tarih) yeni FS ∪ EK'te var; eski gövdenin her cümlesi yeni FS ∪ EK'te bulunuyor (bulanık eşleşme). Reviewer denklik raporunu (script çıktısı) kanıt olarak ister — "okudum, aynı" yetmez. | HIGH (HATA) | std §2.0 İLKE-2b · feedback_done-tam-kapsam-dogrula |

## §C — TEKNİK SPESİFİKASYON (TS)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| DOC-TS-01 | **Gerçek ekran görüntüsü YOK** — detaylı ekran/UI mockup + yapısal tablo (§4.5) | HIGH (HATA) | std §1.3 / §3.2 B4.5 |
| DOC-TS-02 | **Zorunlu bölümler tam** (teknik genel bakış + obje listesi + veri sözlüğü + ekran tasarımı + program/sınıf + DB erişim + enhancement + form + interface + hata + test + transport + onay) | HIGH (EKSİK) | std §3.2 |
| DOC-TS-03 | **Obje adları/alanlar canlı sistemle tutarlı** (uydurma değil; DDL/CDS/struct gerçeğiyle); naming standardına uygun. **Klasik program include'ları:** `<PKG>_I_<PRG>_<T01/C01/O01/I01/F01/S01>` — program-kökünden TÜRER; generic `_I_TOP`/`_I_F01` (kök+numaralı-suffix yok) YASAK (std 06 §1 · gate C-INC-NAME-01 · .rules.md include alt-kuralı) | HIGH (HATA) | std §3.3 · 01-naming · 06 §1 |
| DOC-TS-04 | **Clean-core/yasak farkındalığı** (std tablo yerine released CDS; ADR 0005 ihlali anlatılmıyor) | MEDIUM (ÖNERİ) | feedback_clean-core |

## §D — ÇAPRAZ KONTROLLER (tipten bağımsız — KD/FS/TS + EK'ler)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| DOC-CR-01 | **TERS-YÖN — her `A→B` varlık kontrolünün İKİZİ koşulur: "B var, atıf alıyor mu?"** Tek yönün temiz olması **yarım sonuçtur**; eksik yön tipik olarak *hiç yazılmamış* iş kuralını gizler. En az dört ikiz: ① **mesaj/metin katalogu** — katalogdaki her mesaj (özellikle `E`) belgede bir **üretim noktasına** bağlı mı (yalnız "belgede anılan her mesaj katalogda mı" DEĞİL) ② **onaylı adlar** — onay listesindeki her ad plan/uygulama tarafında geçiyor mu (yalnız "kullanılan her ad onaylı mı" DEĞİL) ③ **DDIC alanı** — her alan için *kim yazar / kim okur*; **ikisi de boşsa yetim alan** ④ **kabul kriteri** — her AC bir teste bağlı mı (yalnız "her test bir AC'ye bağlı mı" DEĞİL). *(2026-08-19: ileri yön ("anılan her mesaj katalogda mı") temizdi, ters yön hiç sorulmamıştı → **4 bulgu**, ikisinde iş kuralı belgede **hiç yazılmamıştı**.)* | HIGH (EKSİK) | bu dosya §İKİNCİ KAPI |
| DOC-CR-02 | **Sabit sayı/ad bayatlaması — bir rakam iki yerde yaşarsa biri bayatlar ve SAHTE YEŞİL verir.** ① Bir sayı/ad değiştiyse belgedeki **diğer tüm geçtiği yerler** güncellendi mi (ikinci kapının ② yüzeyi — teslimden önce **ESKİ** değeri belge genelinde ara). ② **Ölçüt sabit sayıya değil KAYNAĞA bağlanır:** "6+4 aktif" değil "onay listesindeki TÜM adlar aktif"; sabit sayı kalacaksa kaynağı yanına yazılır. ③ **Kapsama beyanı hangi KÜMEYİ kapsadığını söyler** — "T-01…T-40 kimliklerinin tamamı karşılandı" *T-nn tamlığını* ölçer, **kabul-kriteri kapsamasını değil**. *(2026-08-19: build planı A-18 ölçütü "6+4 aktif" **10 onaylı obje eksikken GEÇTİ**; test kapsama beyanı temizken **7 AC** — biri komple bir özellik — beyanın altından geçti.)* | HIGH (HATA) | bu dosya §İKİNCİ KAPI · CLAUDE.core §7 KAPSAM BEYANI |
| DOC-CR-03 | **Belge ↔ canlı teyit turu koşuldu mu** — TS build'e girmeden önce içindeki her *"canlıda mevcut / kurulu / bağlı / yapılacak"* iddiası **ölçüldü** mü (ad çakışması pozitif-kontrollü · reuse iddiaları **imza dahil** · uyarlama durumu · paket/inaktif · transport `E070`/`E071`'den). Kanıt = ölçüm çıktısı, "okudum doğru" değil. | HIGH (EKSİK) | [`howto-belge-canli-teyit-turu.md`](../howto-belge-canli-teyit-turu.md) |

## Verdict
- **PASS** → bitti denebilir.
- **WARNING** → yayınla + bulguyu lider'e/rapora yansıt.
- **BLOCKER / HATA / EKSİK** → düzelt + tekrar gate. (DOC-KD-01 mock-veri ve DOC-KD-03 sub-screen = en sık BLOCKER.)

> Checklist-DIŞI iyileştirme = `[ÖNERİ]` (bağlayıcı değil). Yeni tekrar-eden doküman tuzağı → buraya DOC-XX-NN satırı ekle ([[feedback_review-bulgulari-bug-checkliste-routing]] deseni).
