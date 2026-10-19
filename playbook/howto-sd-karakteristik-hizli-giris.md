---
applies_to: [s4_private]
---

# HOWTO — Satış belgelerinde karakteristik değerlerin hızlı girişi (Mill Products)

> **Ne zaman açılır:** varyant konfigürasyonlu (konfigüre edilebilir) malzemelerle çalışan bir satış
> sürecinde kullanıcı şunlardan birini söylediğinde:
> - *"VA21/VA22'de 10 nolu kalemi tüm karakteristik değerleriyle 20'ye kopyalamak istiyoruz"*
> - *"çok kalemli teklifte her kalemi tek tek konfigüre etmek çok uzun sürüyor"*
> - *"genel kalem / yerel kalem alanı açılmıyor"*
>
> **Ne anlatır:** IMG düğümü **"Satış belgelerinde karakteristik değerlerin hızlı girişi"** altındaki
> aktivitelerin her biri: ne işe yarar, neden kullanılır, hangi tabloya ne yazar, hangisi zorunludur.
> Ardından kullanım, doğrulama, sorun giderme ve teknik anatomi gelir.
>
> **Kim yapar:** uyarlamayı danışman ya da operatör yapar. Bu belge karar ve kontrol listesidir.
>
> **Kanıt düzeyi:** bir s4_private 2025 sisteminde ölçüldü (2026-10-19). Kaynaklar:
> - IMG ağacı (`TNODEIMG`/`CUS_IMGACH`/`CUS_ACTOBJ`) ve SAP IMG ile alan F1 dokümantasyonu (`DOKTL`)
> - ADT kaynak okuması
> - kullanıcının GUI testi
>
> Başka sürüm ya da sistemde her adımı canlıda teyit et. Bu belge hipotezdir, otorite değil.

## 0. Ne işe yarar — iş amacı

Standart varyant konfigürasyonunda her kalemin karakteristikleri **tek tek**, ayrı bir konfigürasyon
ekranında girilir. Bir teklifte aynı ürünün az farklı 20 varyantı varsa 20 kez aynı ekrana girilir.
Mill Products'ın hızlı giriş işlevi bu yükü üç yoldan azaltır:

| İşlev | Ne yapar | Kullanıcıya faydası |
|---|---|---|
| **Karakteristiklere genel bakış ekranı** | Kalemler satır, seçilen karakteristikler sütun olarak tek tabloda listelenir; değerler doğrudan bu tabloya girilir | Konfigürasyon ekranına girip çıkmadan çok kalemi hızlı doldurma ve karşılaştırma |
| **Genel kalem → yerel kalem devralma** (inheritance) | Bir kalem *genel kalem* olur, ona bağlanan *yerel kalemler* onun karakteristik değerlerini devralır | **Aynı belge içinde** kalemi konfigürasyonuyla "kopyalama": yalnız farklı olan değer değiştirilir |
| **Müşteri malzemesi bilgi kaydından devralma** | Kalem kategorisine bağlı olarak müşteri-malzeme bilgi kaydındaki karakteristikleri kaleme taşır | Müşteriye özel sabit değerlerin her siparişte yeniden girilmemesi |

SAP dokümantasyonuna göre karakteristik görüntüleri yalnız satış belgelerinde değil, şu işlemlerde de
kullanılır:
- satış belgeleri (sorgu, teklif, sipariş, teslimat planı, sözleşme)
- Enjoy satınalma siparişi
- mal hareketleri
- üretim siparişi ve üretim siparişi teyidi
- ticari sözleşme (yalnız `/SAPMP/GEN_01_TRADE_CM_COMBI` switch'i açıksa)

Bu belge **satış belgesi** tarafını kapsar.

### Yanlış yollar — önce bunları ele

| Yanlış yol | Neden değil |
|---|---|
| Kopya kontrol (VTAA) | Belgeden belgeye kopyalar; **aynı belge içinde** kalemden kaleme devralma yapmaz |
| IMG'de "kopyala / copy" araması | Düğüm adında bu kelime geçmez, arama **bulamaz** |
| Standart kalem genel bakışında "Genel kalem" sütunu aramak | Bu sütun orada yoktur; yalnız "Karakteristiklere genel bakış" ekranında bulunur |
| Varyant konfigürasyon modelini (CU41/CT04) değiştirmek | Devralma modelle değil, satış belgesi uyarlamasıyla açılır |

## 1. Ön koşul — switch / business function

Ölçülen sistemde `/SAPMP/*` switch'leri zaten açıktı; ek business function **gerekmedi**. Başka bir
sistemde ilk iş, SFW5'te Mill Products / `/SAPMP/` switch'lerinin durumunu canlıda görmektir.
- Switch'ler kapalıysa IMG düğümü ve alanlar görünmez, bu belge de o sistemde geçerli olmaz.
- Business function açmak **geri alınamaz** bir sistem kararıdır; kullanıcıya ayrıca sunulur.

Konfigüre edilebilir malzeme, sınıf (sınıf türü 300) ve karakteristikler zaten hazır olmalıdır. Bu
işlev konfigürasyonu kolaylaştırır, modeli yerine koymaz.

## 2. IMG yapısı (ölçüldü)

Düğüm **"Satış belgelerinde karakteristik değerlerin hızlı girişi"** bir *referans* düğümdür (`TNODEIMG`
`NODE_TYPE = REF`). Ayrı bir ağaçtaki **"Satış belgelerinde kalem konfigürasyonu"** düğümünü gösterir;
iki ad da aynı içeriğe çıkar. Altında 5 aktivite vardır:

| Aktivite (TR metin) | Aktivite ID | IMG işlem kodu | Bakım nesnesi | Yazdığı yer |
|---|---|---|---|---|
| Karakteristik değerleri için özellikler belirle | `ISMP/SAPMP/SD_TVAK1` | `S_KA5_12001198` | görünüm `/SAPMP/SD_TVAK_1` | TVAK (belge türü) |
| Genel/yerel grubu kaldır | `ISMP/SAPMP/SD_TVAK_2` | `S_KA5_12001199` | görünüm `/SAPMP/SD_TVAK_2` | TVAK |
| Karakteristik görüntüsü için uygulama grubu tanımla | `ISMP/SAPMP/V_VBMUEH` | `S_KA5_12001201` | görünüm `/SAPMP/V_VBMUEH` | `/SAPMP/VBMUEH` |
| Genel bakış ekranı için karakteristik görüntüsünü tanımla | `ISMP/SAPMP/SD_MUEBS` | `S_KA5_12001200` | görünüm kümesi `/SAPMP/SD_MUEBERSICHT` (SM34) | VBMUE / VBMUET / VBMUEZ |
| Müşteri malzemesi bilgi kaydından karakteristik değerleri devral | `MPWSD_MILL_GPOSTYP` | `S_KM5_93000007` | görünüm `V_MILL_TVAP_SE` | TVAP (kalem kategorisi) |

**Bu düğümde OLMAYAN ama zorunlu olan adım:** VOV8'deki belge türü alanı `TVAK-UEVOR`
(bkz. §3.2). Düğüm tek başına tamamlanırsa "uyarlama tamam ama alan açılmıyor" tablosu çıkar.

## 3. Aktiviteler — ne yapar, neden, ne zaman

Alan adları DDIC TR etiketidir. "SAP açıklaması" sütunu, alanın F1 (DTEL) ya da IMG dokümantasyonunun
özetidir. Sistemde bu dokümanlar yalnız İngilizce bulundu.

### 3.1 `SD_TVAK1` — Karakteristik değerleri için özellikler belirle  *(temel aktivite — ZORUNLU)*

**Ne yapar (IMG dokümanı):** belge türü bazında, karakteristiklerin genel kalemden ona bağlı yerel
kalemlere **devralınmasını** (inheritance) açar. Devralmanın ek işlevlerini seçer: devralma günlüğü,
elle girilmiş değerin ezilmesi, karakteristik seçim listesi. Belge türü başına karakteristik
görüntüsünün varsayılanını tutacak bir karakteristik de tanımlanabilir.

| Alan (TVAK) | TR etiket | SAP açıklaması | Değer · ne zaman |
|---|---|---|---|
| `/SAPMP/CEACT` | Konfigürasyonu etkinleştir | Belge türü için karakteristiklerin hızlı girişinin etkin olup olmadığı | **X — zorunlu.** Bütün mantığın ana anahtarıdır |
| `/SAPMP/PDACT` | Aktarımı etkinleştir | Genel kalemin değerlerinin bağlı yerel kalemlere devralınıp devralınamayacağı | **X**: mevcut kalemlere sonradan "Aktarım" (devralma) yapılacaksa |
| `/SAPMP/PUSER` | Aktarım: Kullanıcı değerlerinin üzerine yaz | Devralmada genel kalem değerleri, yerel kaleme **elle girilmiş** değerleri ezsin mi | X: genel kalem her zaman kazanır · boş: yerel kalemdeki elle değişiklik korunur |
| `/SAPMP/PPROT` | Günlük aktarımı | Devralma için hata günlüğü **otomatik** gösterilsin mi | Günlük her zaman oluşur ve @DH@ "Inheritance Log" düğmesiyle açılır. **Veritabanına kaydedilmez**, belge kapanınca silinir |
| `/SAPMP/PAUSW` | Karakteristik seçim listesinin aktarımı | Devralmada bir seçim listesi sunulsun mu | X: kullanıcı hangi karakteristiklerin devralınacağını seçer; **yalnız seçilenler** kopyalanır |
| `MILL_SE_ATNAM` | Karakteristik adı | Karakteristik görüntüsünün **varsayılanını** tutan karakteristik | İsteğe bağlı. Karakteristik sınıf türü 300'deki bir varyant sınıfına atanmış olmalı; malzeme konfigüre edilirken görüntünün varsayılanı bu değerden gelir |

**Neden:** CEACT olmadan hızlı giriş mantığı hiç çalışmaz. PDACT/PUSER/PPROT/PAUSW ise "devralma ne
kadar serbest, ne kadar kontrollü olsun" sorusunun cevabıdır; bu bir iş kararıdır, kullanıcıyla
konuşulur.

### 3.2 VOV8 `TVAK-UEVOR` — Genel bakış ekranı için işlev kodu önerisi  *(ZORUNLU — düğümde yok)*

**Ne yapar (F1):** satış belgesinin ilk ekranından sonra hangi **genel bakış ekranına** gidileceğini
belirler. Standart örnekte müşteri malzeme numarasıyla giriş ekranı açılır.

**Değer:** **`MILL_SE_UE`**. Belge açılınca genel bakış olarak **"Karakteristiklere genel bakış"**
ekranı gelir (SAPMV45A ekran 4001 + alt ekran 4434). "Genel kalem" sütunu ve karakteristik değer
sütunları **yalnız bu ekrandadır**.

**Neden zorunlu (ölçülen vaka):**
- `CEACT`, `PDACT`, `PPROT`, `PUSER` ve `PAUSW` X iken alan **açılmadı**.
- `UEVOR = MILL_SE_UE` girilince açıldı ve kopyalama çalıştı (kullanıcı GUI testi).

### 3.3 `V_VBMUEH` — Karakteristik görüntüsü için uygulama grubu tanımla  *(isteğe bağlı)*

**Ne yapar (IMG dokümanı):** işlemlere *uygulama grubu* atar. Uygulama grubu, hangi işlemde hangi
karakteristik görüntülerinin seçilebileceğini süzer.

| Alan (`/SAPMP/VBMUEH`) | TR etiket | Anlamı |
|---|---|---|
| `/SAPMP/ANWID` | İşlem | Hızlı girişi olan işlem (satış belgesi, satınalma siparişi, mal hareketi…) |
| `/SAPMP/ZUORD` | Uygulama grubu | Grup kodu. Aynı grup birden çok işleme atanabilir. `*` = o işlemde **bütün** görüntüler seçilebilir |

**Neden / ne zaman:**
- Hiç kayıt girilmezse, hızlı girişi olan bütün işlemlerde **bütün** karakteristik görüntüleri seçilebilir.
- Süzmek yalnız çok sayıda görüntü varken ve süreçler ayrışıyorsa anlamlıdır. Örnek: satınalma
  görüntüleri satışta görünmesin.

### 3.4 `SD_MUEBS` — Genel bakış ekranı için karakteristik görüntüsünü tanımla  *(isteğe bağlı ama pratikte gerekli)*

**Ne yapar (IMG dokümanı):** *karakteristik görüntüsü* tanımlar: hızlı giriş ekranında hangi
karakteristiklerin, hangi sırayla ve hangi genişlikte **sütun** olacağı.

Adımlar:
1. Görüntüye ad ve açıklama ver.
2. Gerekirse bir uygulama grubu ata (§3.3).
3. Solda "Karakteristik ataması"nı seç.
4. Karakteristikleri sırayla gir.

| Tablo · alan | TR etiket | Anlamı |
|---|---|---|
| VBMUE `MUEBS` · `/SAPMP/ZUORD` | Karakteristik görüntüsü · Uygulama grubu | Görüntü başlığı ve hangi işlem grubunda geçerli olduğu |
| VBMUET | — | Görüntü metni |
| VBMUEZ `FOLGE` · `ATNAM` · `CLENG` | Sıra · Karakteristik adı · Görüntülenen sütun genişliği | Sütunlar (pratikte ≤10 karakteristik) |

**Neden:** görüntü tanımlanmazsa ekranda değer sütunu olmaz. Kalemler ve "Genel kalem" sütunu yine
görünür, ama karakteristikler tabloda **hızlı girilemez**; devralma çalışır, hızlı giriş zayıflar.
**Etkisi:** yalnız değer sütunlarıdır; "Genel kalem" sütununun varlığını **etkilemez**.
**Kullanıcıya özel varsayılan:** kullanıcı parametresi `VAM` (SU3) ile kullanıcıya özel varsayılan
görüntü atanabilir; belge türü varsayılanı `MILL_SE_ATNAM`'dır (§3.1).

### 3.5 `SD_TVAK_2` — Genel/yerel grubu kaldır  *(isteğe bağlı)*

**Ne yapar:** belge türü bazında, bir yerel kalemin genel kaleme bağının **sonradan kaldırılıp
kaldırılamayacağını** belirler.

| Alan (TVAK) | TR etiket | SAP açıklaması |
|---|---|---|
| `/SAPMP/GAUF` | Genel/yerel grup kaldırma olanaklı | Bağ kaldırılınca yerel kalem **normal kalem** gibi işlenir |

**Neden / ne zaman:** kullanıcı bir kalemi yanlışlıkla bağladıysa ya da kalem artık bağımsız
yaşayacaksa gerekir. Boş bırakılırsa bağ kalıcıdır.

### 3.6 `MPWSD_MILL_GPOSTYP` — Müşteri malzemesi bilgi kaydından karakteristik değerleri devral  *(isteğe bağlı)*

**Ne yapar (IMG + F1):** kalem kategorisi bazında, müşteri-malzeme bilgi kaydındaki karakteristik
konfigürasyonunun hızlı girişte kaleme **devralınıp devralınmayacağını** ve çakışmada hangisinin
kazanacağını belirler. Yalnız malzemenin konfigürasyonunda var olan karakteristikler devralınır.

| Alan (TVAP) | TR etiket | Değerler |
|---|---|---|
| `MILL_SE_KKNMT` | Müşteri malzemesinden karakteristiklerin devralımı için gös. | ` ` devralınmaz · `1` devralınır, çakışmada **bilgi kaydı** kazanır · `2` devralınır, çakışmada **genel kalem** kazanır |

**Neden / ne zaman:** müşteriye özel sabit spesifikasyonlar (örn. müşterinin standart ambalajı ya da
toleransı) bilgi kaydında tutuluyorsa her siparişte yeniden girilmesin diye kullanılır.
- **DOĞRULANMADI:** bilgi kaydında konfigürasyonun nerede tutulduğu. `KNMT`'de `CUOBJ`/`MILL_SE*`
  alanı yok (ölçüldü); büyük olasılıkla `IBINOWN` üzerinden bağlanıyor.
- Bu kısım kullanılacaksa önce canlıda ölç.

## 4. Asgari set — hangi ihtiyaç hangi adımları ister

| İhtiyaç | Gerekli adımlar |
|---|---|
| Yeni kalemi mevcut kalemin konfigürasyonuyla yaratmak (aynı belgede) | §3.1 `CEACT` + §3.2 `UEVOR` |
| Mevcut kaleme sonradan devralma ("Aktarım") | + §3.1 `PDACT` |
| Karakteristikleri tabloda hızlı girmek / karşılaştırmak | + §3.4 görüntü (+ gerekirse §3.3) |
| Devralmayı kontrollü yapmak | + §3.1 `PUSER` / `PAUSW` / `PPROT` (iş kararı) |
| Bağı sonradan koparabilmek | + §3.5 `GAUF` |
| Müşteri bilgi kaydından değer almak | + §3.6 `MILL_SE_KKNMT` |

### Taşıma notu

Hepsi client'a bağlı customizing'dir. QA/PRD'ye giderken §3.1 ve **§3.2 (VOV8 `UEVOR`) aynı pakette**
gitmelidir. Ölçülen vakada ikisi ayrı zamanlarda yapıldı; biri unutulursa hedef sistemde aynı arıza
tekrar eder. Customizing isteğini taşımadan önce içeriğini gözle kontrol et: aynı isteğe ilgisiz kayıt
girmiş olabilir.

## 5. Kullanım (VA21 / VA22)

1. Belgeyi aç. Genel bakış "Karakteristiklere genel bakış" olarak gelir (§3.2'nin etkisi).
2. Gerekirse karakteristik görüntüsünü seç (§3.4).
3. Ekrandaki **kapsam** listesinde **"Tüm kalemler"**i seç. Kod davranışı (`conf_field_control_pbo`):
   - "Yalnız genel" seçilirse "Genel kalem" sütunu gizlenir.
   - "Genel + yerel" seçilirse alan kilitli gelir.
4. Kaynak kalemi (örn. 10) konfigüre et. Bu kalem **genel kalem** olur.
5. **Yeni kalemde devralma:** yeni satırda "Genel kalem" alanına `10` yaz. Değerler kalem yaratılırken
   devralınır.
6. **Mevcut kaleme sonradan devralma:** genel kalemi işaretle, ardından "Aktarım"ı seç (§3.1 `PDACT`
   şart, fcode `/SAPMP/PROP`). `PAUSW` açıksa karakteristik seçim listesi gelir; `PPROT` açıksa günlük
   otomatik görünür.
7. Yalnız farklı olan değerleri değiştir, sonra kaydet.

Devralma kuralları:
- Yalnız **aynı adlı** karakteristikler devralınır. Farklı sınıftaki malzemede ortak olmayan
  karakteristik boş kalır.
- Yerel kalem **kendi** konfigürasyon nesnesini (`VBAP-CUOBJ`) taşır. Devralma bir kopyalamadır; canlı
  bir bağ değildir. Sonradan genel kalemi değiştirmek yerel kalemi kendiliğinden güncellemez; yeniden
  "Aktarım" gerekir.

Sistem mesajları (`/SAPMP/PUR`, TR metinleri T100'den):

| No | Metin | Anlamı |
|---|---|---|
| 015 | Yerel kalem &1 genel kalem olarak kullanılamaz | Zincir kurulamaz: yerel kalem başka bir kalemin genel kalemi olamaz |
| 022 | Kalem &1 genel kalemdir; buraya genel kalem girmeyin. | Genel kaleme genel kalem girilmiş |
| 023 | Genel kalem olarak &1 kaleminden farklı olarak bir kalem numarası girin | Kalem kendini göstermiş |

## 6. Doğrulama — ölç, varsayma

```sql
-- belge türü: iki zorunlu alan + devralma ayarları
SELECT auart, uevor, /sapmp/ceact, /sapmp/pdact, /sapmp/puser, /sapmp/pprot, /sapmp/pausw,
       /sapmp/gauf, mill_se_atnam
  FROM tvak WHERE auart = '<BELGE_TURU>'
-- beklenen: UEVOR = 'MILL_SE_UE' ve CEACT = 'X'

-- kalem kategorisi: müşteri bilgi kaydından devralma
SELECT pstyv, mill_se_kknmt FROM tvap WHERE pstyv = '<KALEM_KATEGORISI>'

-- görüntüler ve uygulama grupları
SELECT * FROM vbmue      -- görüntü başlıkları
SELECT * FROM vbmuez     -- görüntü sütunları
SELECT * FROM /sapmp/vbmueh

-- kaydedilmiş devralma: yerel kalemler
SELECT vbeln, posnr, mill_se_gposn, cuobj FROM vbap WHERE vbeln = '<BELGE>'
-- beklenen: yerel kalemde MILL_SE_GPOSN = genel kalem no; her kalemin kendi CUOBJ'u
```

Ölçülen vakada kullanıcı devralmanın GUI'de çalıştığını gördü. Ancak aynı sistemde `MILL_SE_GPOSN`
dolu VBAP kaydı **0** çıktı; deneme kaydedilmemiş olabilir. Kaydedilmiş bir devralmanın VBAP'ta nasıl
göründüğü bu yüzden **DOĞRULANMADI**. İlk kayıtlı devralmada son sorguyla ölç.

**Raporlama:**
- Karakteristik değerleri şu zincirle okunur: `VBAP-CUOBJ → IBINOWN → IBIN → IBINVALUES`
  (+ `IBSYMBOL`).
- Yerel kalem kendi CUOBJ'unu taşıdığı için rapor genel kalemi ayrıca çözmek zorunda değildir.
- "Hangi kalemden devralındı" bilgisi gerekiyorsa `MILL_SE_GPOSN` ayrı bir kolon olarak eklenir.

## 7. Sorun giderme

| Belirti | Bak | Çare |
|---|---|---|
| Uyarlama tamam ama "Genel kalem" alanı ya da sütunu hiç yok | TVAK `UEVOR` | `MILL_SE_UE` gir (⭐ en sık; ölçülen vakanın kök nedeni) |
| Hızlı giriş ekranı hiç gelmiyor | TVAK `UEVOR` + `CEACT` | §3.1 + §3.2 |
| Ekran geliyor ama sütun gizli | Kapsam listesi | "Tüm kalemler" seç |
| Alan görünüyor ama kilitli | Kapsam listesi; satırda genel kalem zaten dolu olabilir | "Tüm kalemler" seç; alan doluysa giriş kapalıdır (kod davranışı) |
| "Aktarım" düğmesi yok | TVAK `/SAPMP/PDACT` | X |
| Devralmada elle girilmiş değer ezildi ya da ezilmedi | TVAK `/SAPMP/PUSER` | İş kararına göre ayarla |
| Bazı karakteristikler devralınmadı | Ad eşleşmesi; `PAUSW` seçim listesi | Aynı adlı karakteristik mi, listede seçildi mi kontrol et |
| Değer sütunları boş ya da yok | VBMUE/VBMUEZ, `/SAPMP/VBMUEH`, `VAM`, `MILL_SE_ATNAM` | §3.3 – §3.4 (sütunun varlığını etkilemez) |
| Bağ koparılamıyor | TVAK `/SAPMP/GAUF` | §3.5 |
| Hiçbir Mill işlevi ya da IMG düğümü yok | SFW5 `/SAPMP/` switch'leri | §1 (kullanıcı kararı) |
| Uyarlamadan önce açılmış VA22 oturumu | Tampon | İşlemden çıkıp yeniden gir |

## 8. Teknik anatomi — kod okuması neden yanılttı

- FM `MILL_SE_ACTIVATE` yalnız `TVAK-/SAPMP/CEACT`'a bakar. Kodu okuyan *"kapı bu"* sanar.
- Çağrı yerleri SAPMV45A include'larıdır:
  - `MILL_SE_MV45A_O01` (PBO modülü `set_item_configuration_active`)
  - `MILL_SE_MV45A_I01`
  - `MILL_SE_MV45A_FCODE_POCO`
- Alan kontrolü `MILL_SE_MV45A_F01` içindeki `conf_field_control_pbo`'dadır (`*VBAP-MILL_SE_GPOSN`
  sütunu). Mantık aktif değilse sütunu gizler.
- Ama bu modüller yalnız **4001/4434 ekranının akışında** koşar. O ekrana ulaştıran şey belge türünün
  genel bakış işlev kodudur (`TVAK-UEVOR`). `CEACT = X` iken bile ekran hiç çağrılmazsa alan görünmez.
- **Ders:** bir PBO kapısını okumak, o ekranın çağrıldığını kanıtlamaz. Ekrana giden fcode ya da
  navigasyon ayrıca ölçülür.

## 9. Kapsam beyanı

- **Ölçülenler:**
  - IMG ağacı ve aktiviteler (`TNODEIMG`/`TNODEIMGR`/`CUS_IMGACH`/`CUS_IMGACT`/`CUS_ACTOBJ`)
  - IMG ve alan dokümantasyonu (`DOKTL` `HY`/`DE`, yalnız EN mevcut)
  - DDIC TR etiketleri ve T100 mesajları
  - Mill include kaynakları
  - `UEVOR` etkisi (kullanıcı GUI testi)
- **Ölçülmeyenler:**
  - kaydedilmiş devralmanın VBAP görünümü
  - `MILL_SE_KKNMT` bilgi kaydı tarafı
  - `GAUF` ile bağı kaldırmanın GUI yolu
  - satınalma, mal hareketi ve üretim tarafı
  - S/4 2025 dışındaki sürümler
- **prior-art:** yok (2026-10-19, `path=core` araması: MILL_SE / LO-VC / IBINVALUES → 0 dosya).
- **Kısa referans satırı:** [`modules/referans/sd/spro.md`](modules/referans/sd/spro.md) "Varyant konfigürasyonu".
