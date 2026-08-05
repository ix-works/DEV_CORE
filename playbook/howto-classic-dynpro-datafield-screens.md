---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: howto
applies-to: backend (classic dialog)
last-updated: 2026-08-06
status: active
purpose: Datafield'lı (DDIC yapıya bağlı) klasik Dynpro diyalog ekranı üretimi — karar ağacı, arama-yardımı mekanizmaları, üreteç/CUA turu, doğrulama protokolü
---

# HOW-TO — Klasik Dynpro Datafield/Diyalog Ekranı (DDIC-bağlı modal formlar)

> **Amaç:** `classic-alv-list.prog.abap` yalnız **liste/rapor** ekranını kapsar (ALV grid, salt-
> okunur satır çokluğu). Bu dosya, **modal diyalog** ekranlarını kapsar — DDIC yapıya bağlı
> data-field'lardan oluşan TEK KAYITLIK giriş/düzeltme formları (ör. "kayıt düzeltme", "transfer",
> "yeni satır ekle" popup'ları). Şablon: [`templates/classic-dynpro-dialog.prog.abap`](templates/classic-dynpro-dialog.prog.abap).
>
> **Kaynak:** bir stok-hareket takip programının v2 build'i — 3 modal diyalog ekranı
> (düzeltme/transfer/kayıt-ekle) + malzeme F4'ü + depo-yeri F4'ü sondası. Bu dosyanın
> her satırı canlı-ölçülmüş bir vakaya dayanır; iddia ≠ tahmin.
>
> Üreteç kullanım kılavuzu (ADIM-ADIM, ALV/CUA temeli): [`howto-dynpro-gui-status-generation.md`](howto-dynpro-gui-status-generation.md).
> Bu dosya onu **tekrarlamaz**, datafield-özel kısmı (arama-yardımı + CUA çok-ekran tuzakları)
> ekler. Include yapısı: [`../standards/06-coding-classic-dialog.md`](../standards/06-coding-classic-dialog.md) §1.
> Pre-flight checklist: [`checklists/classic-dialog-creation.md`](checklists/classic-dialog-creation.md).

---

## 0. Karar ağacı — ALV mi, datafield-diyalog mu, karışık mı?

```
Ekran çok satır gösteriyor mu (rapor/liste/bakım grid)?
  ├─ EVET, salt-okuma veya satır-bazlı düzenleme → LİSTE → classic-alv-list.prog.abap
  └─ HAYIR, TEK KAYIT'lık form (birkaç alan, kaydet/iptal) → DİYALOG → BU dosya

Diyalog nereden açılıyor?
  ├─ Bir liste/grid'in satırından ("düzelt", "sil", "ekle" butonu) → modal Dynpro,
  │    çağıran ekran `CALL SCREEN <n>` ile açar, PAI'de LEAVE TO SCREEN 0 ile döner
  └─ Bağımsız (kendi CALL SCREEN 0100'ü) → ALV template ile aynı iskelet, ama içi
       datafield ise yine BU dosyanın deseni geçerli

Aynı programda ikisi de var mı (liste + ondan açılan diyaloglar)?
  → NORMAL. Canlı örnek: ana bakım grid'i (0100/0200, ALV-şablonu) + 3 modal
    diyalog (0300/0400/0500, bu şablon). Tek programda iki desen bir arada yaşar.
```

**Ayrım neden önemli:** ALV template ekran-üretecine `IT_BUTTONS` ile app-toolbar butonu
verir ama alan (`IT_FIELDS`) VERMEZ (liste zaten ALV grid'in kendi kolonlarını kullanır).
Diyalog ekranı ise **her data-field'ı `IT_FIELDS`'ta DDIC yapıya bağlı olarak** verir — bu
farkın anlaşılmaması, elle-bildirilen `gs_*` program-lokal struct'lara geri dönüşe yol açar
(aşağıdaki §1'de neden yanlış olduğu anlatılıyor).

---

## 1. DDIC yapıya bağlama (`FROM_DICT`) — neden, nasıl, kazanç

**Neden:** ekran alanı DDIC yapının bir bileşenine bağlanınca (`TEMPLATE = 'Z..._S_...-ALAN'` +
`FROM_DICT = 'X'`) etiket, uzunluk, `CONVERSION_EXIT`, ve (varsa) arama-yardımı **DDIC'ten
gelir** — elle verilmez. Kazanç ölçülmüş: bir yapının `QUAN`/`DATS` alanı payload'da kısa
uzunlukla (`len008`/`len013`) gönderilse bile canlı ekran alanı DDIC'in gerçek uzunluğuna
(`010`/`017`, `DD04L.OUTPUTLEN`) çıktı — **SAP bunu kendisi düzeltti**, elle senkron gerekmedi.

**⚠ Eskimiş gerekçe — geri dönme:** *"ekran alanları program yapısına bağlı olduğu için
`FROM_DICT` kullanılamaz"* iddiası bir projede uzun süre yazılı durdu ve **döngüseldi**
(seçimin sonucunu sebep gibi sunuyordu — üreteç `FROM_DICT`'i baştan destekliyordu, hiç
denenmemişti). Program-lokal `gs_duz`/`gs_trf`/`gs_tah` gibi ad-hoc struct'lar + ekran↔yapı
arası `MOVE-CORRESPONDING` köprüsü kurulmuşsa, bu bir **geçiş borcudur** — DDIC yapısına
geçilince köprü **tamamen silinir** (kod referansı 0 kalmalı), yarım bırakılmaz.

**Nasıl (ekran üreteci tarafı — gateway işi, bu dosyada tekrar edilmez):** `IT_FIELDS` satırı
`TEMPLATE = '<YAPI>-<ALAN>'` + `FROM_DICT = 'X'` + `MATCHCODE` **BOŞ** taşır. Program tarafında
tek gereken: global work area'nın adı DDIC yapı adıyla **aynı** olması (`DATA zsd001_s_dlg TYPE
zsd001_s_dlg.`) — ekran alanları `ZSD001_S_DLG-ALAN` diye adreslenir.

---

## 2. ⭐ ARAMA YARDIMI — 4 MEKANİZMA ve hangisi ne zaman

Bir diyalog alanına F4 gerektiğinde **dört** farklı mekanizma vardır; hangisinin
kullanılacağı alanın DDIC kökenine ve süzgeç ihtiyacına bağlıdır.

| # | Mekanizma | Ne zaman | Maliyet |
|---|---|---|---|
| ① | **DTEL'e bağlı standart arama yardımı** | Alanın data element'i zaten bir standart SHLP'ye bağlıysa (ör. malzeme grubu → `MAT1`, üretim yeri → `H_T001W`, parti → `MCH1`) | **Bedava** — DDIC bağlaması (`FROM_DICT`) yeterli, hiçbir ek iş gerekmez |
| ② | **Yapı bileşenine search-help attachment** | DTEL'de arama yardımı YOK ama bir standart SHLP mantıksal olarak uyuyor (ör. depo yeri) — `with value help <shlp> where <param> = <yapı>.<alan>` DDIC yapı tanımına yazılır | Düşük — DDIC yapı değişikliği (bir sonraki bölüm ②'nin KENDİ altında) |
| ③ | **Buton + popup** (`REUSE_ALV_POPUP_TO_SELECT`) | Süzgeç gerekiyor (ör. "yalnız şu malzeme tipleri") VE bir Z arama yardımı (SHLP) gerekirdi ama **yaratılamaz** (§2.1) | Orta — birkaç FORM, program içinde kalır |
| ④ | **POV modülü** (`PROCESS ON VALUE-REQUEST`) | Veriye bağlı süzgeç (ör. "yalnız serbest bakiyesi olan kayıtlar") — statik DDIC attachment YETMEZ | **Bu ekran üretecinde ŞU AN DESTEKLENMİYOR** (§2.4) — ertelenir, ③ ile telafi edilir |

### 2.1 ⛔ Z arama yardımı (SHLP) mevcut araç setiyle YARATILAMAZ

Bu bir "denenmedi" değil, **üç bağımsız kanıtla ölçülmüş sınırdır** (kontrol gruplu):

1. `adt_get(object_type="shlp")` → açık ret; desteklenen tip listesinde `shlp` yok.
2. **ADT backend'inde koleksiyon yok:** `/sap/bc/adt/discovery` iki filtreyle tam tarandı
   (118 + 71 koleksiyon) — data element/domain/structure/table/lock object/service
   definition/… hepsi var, `searchhelp`/`shlp` adında koleksiyon **yok**. `adt_search_objects`'in
   döndürdüğü `/sap/bc/adt/vit/wb/object_type/shlpdh/…` URI'si **VIT köprüsüdür** (Eclipse
   içine gömülen SE11 ekranı) — POST'lanabilir REST kaynağı DEĞİL. *("Bulunan bir URI ≠
   yazılabilir bir uç" — bulundu ≠ var dersinin araç-katmanı hâli.)*
3. RFC yolu kapalı: `DDIF_SHLP_PUT`/`DDIF_SHLP_GET`/`DDIF_SHLP_ACTIVATE` üçünde de
   `TFDIR-FMODE=null` (RFC-enabled değil). Kontrol grubu: `RFC_READ_TABLE` ve
   `BAPI_MATERIAL_GET_DETAIL` → `FMODE='R'`.

**Sonuç:** süzgeçli F4 gerektiğinde ③ (buton+popup) kullanılır. Z SHLP gerçekten şartsa
yol SE11-elle + kullanıcı onayı (ADR 0009 süreci) — araç tarafında yapılacak bir şey yok.

### 2.2 ⭐ Mekanizma ②'nin kritik kuralı — attachment ALAN ADINA değil BİLEŞENE yapılır

Bir DDIC yapıya `with value help` eklerken, `where` bloğu **hangi ekran parametresinin hangi
SHLP parametresine denk geldiğini AÇIKÇA** belirtir:

```abap
define structure zsd001_s_dlg {
  ver_lgort  : lgort_d
    with value help h_t001l
      where lgort = zsd001_s_dlg.ver_lgort
        and werks = zsd001_s_dlg.ver_werks;
  alan_lgort : lgort_d                        " aynı yapıda İKİNCİ bir lgort_d alanı —
    with value help h_t001l                   " attachment TEK ayırt edici mekanizmadır;
      where lgort = zsd001_s_dlg.alan_lgort   " isim-eşleşmesi (alan adı = SHLP parametre
        and werks = zsd001_s_dlg.ver_werks;   " adı) burada ZATEN geçersizdir.
}
```

**Eskimiş yanlış-teşhis (iki kez tekrarlandı, ikisi de ölçümle çürütüldü):**

| İddia | Neden yanlış |
|---|---|
| *"Aynı yapıda iki `lgort_d` alanı var, ikisi aynı DDIC adını taşıyamaz ⇒ attachment yolu kapalı"* | Bağlama ekran ALANININ ADINA değil **yapı BİLEŞENİNE** yapılır — iki bileşen ayrı isimlerle (`ver_lgort`/`alan_lgort`) aynı SHLP'ye bağlanabilir. Canlı ölçüm: bir yapının 7 alanının tümü `MATCHCODE` boş + `FROM_DICT`, ikisi de `H_T001L`'e bağlıydı. |
| *"DDIC-bağlı alanda 'arama yardımı varsayılan parametreye düşer' kusuru doğamaz"* | **Ölçüm çürüttü.** `FROM_DICT` olsa bile, ekran alanı ile SHLP'nin parametresi arasında **eşleme kurulmazsa** (aşağıdaki H2), F4 seçilen satırın YANLIŞ bir alanını (ör. üretim yeri) ekran alanına yazar. DDIC'e bağlı olmak eşlemeyi **kendiliğinden kurmaz**. |

**⚠ Ekrandaki elle `MATCHCODE` DDIC attachment'ının ÖNÜNE GEÇER.** Bir alana geçmişte elle
`MATCHCODE='<SHLP>'` verilmişse ve yapıya sonradan attachment eklenmişse, ekran **elle
matchcode'u kazanır** — attachment ekrana hiç inmez. Yeni ekran açan geliştirici için kural:
alanları DDIC yapısına bağla (`FROM_DICT='X'`) VE ekran-tarafı `MATCHCODE` **BOŞ** bırak;
"elle etiket/matchcode workaround"unu **yeniden kurma**.

**⚠ İkinci koşul — bir DDIC objesini değiştirmek, o DDIC'i GENERATE ANINDA GÖMEN tüketiciyi
otomatik güncellemez.** Klasik Dynpro, ekran ÜRETİLDİĞİ anda DDIC bilgisini (matchcode dahil)
gömer. Yapıya attachment eklemek CANLI ve AKTİF olsa bile, **ekran daha önce üretilmişse**
değişiklik ekrana kendiliğinden inmez — ekranın (yalnız gerekli alanlarla, bkz. §4) **bir kez
daha üretilmesi (regen)** gerekir. *Obje aktif ≠ tüketici güncel.* Bir sonraki DDIC→dynpro
işinde regen adımı **baştan plana konur**, "gerekirse yaparız" diye ertelenmez.

### 2.3 Tanıdık semptomda önce ARA, sonra deney kur

Bir F4 kusuru "çözüldü" denip sonra aynı semptomla geri geldiğinde, önce **önceki turun
teşhis notlarını** (görev-içi geçici dosyalar, SESSION_NOTES, memory) ara — kök sebep
muhtemelen zaten yazılmıştır. Bir vakada elle `MATCHCODE` geri konularak "çözüldü" denmişti;
oysa üç gün önceki bir teşhis notu kusurun **`MATCHCODE`'un yokluğu değil parametre
eşlemesinin yokluğu** olduğunu zaten yazmıştı. O rapora bakılmadan aynı deney (matchcode
ekleme) tekrar kuruldu ve tekrar çürüdü. **Kural: tanıdık semptomda ÖNCE geçmiş teşhis
notları aranır, SONRA yeni deney kurulur.**

### 2.4 Mekanizma ④ (POV) — bu üreteçte YOK, veriye-bağlı F4 için erteleme + telafi

Ekranları üreten FM'in akış mantığı **sabit 4 satır** yazar (yalnız `PBO/MODULE status_<n>`
+ `PAI/MODULE user_command_<n>`) — `PROCESS ON VALUE-REQUEST` bloğu **üretmiyor**. Veriye
bağlı bir F4 (ör. "yalnız serbest bakiyesi > 0 olan kayıtlar") standart DDIC mekanizmasıyla
ifade edilemez ve POV, üreteç bunu desteklemediği için **elle bakım gerektirir** — bu, ekran
her `IV_RECREATE='X'` ile yeniden üretildiğinde **silinir**. Bu sınıf F4'ler için:

- **Telafi (işlevsel kayıp yok):** ekrana bir **`Bakiye`/`Listele` butonu** eklenir
  (`REUSE_ALV_POPUP_TO_SELECT` ile salt-görüntüleme popup'ı) — kullanıcı veriyi görüp
  alana **elle** yazar. F4 değil ama bilgi erişimi kaybolmaz.
- **Paylaşılan araca dokunmadan önce, sorunun KENDİ katmanında (DDIC) çözümü olup
  olmadığı sorulur.** Bir vakada POV yolu (ortak üretece `IT_FLOW` parametresi eklemek)
  planlanmışken, aynı ihtiyacın (depo-yeri F4'ü, veriye bağlı DEĞİL) mekanizma ②
  (attachment) ile çözülebildiği görüldü ve POV planı **iptal edildi** — ortak araca hiç
  dokunulmadı. *Paylaşılan bir bileşimi genişletmeden önce, dar/yerel bir çözüm
  (burada: tek DDIC yapı) var mı diye sorulmalı.*

---

## 3. Ekran üreteci turu — ölç → payload → yaz → doğrula

### 3.1 Tur sırası (ZORUNLU)

1. **`IV_MODE='READ'`** ile mevcut ekranın container/alan/toolbar durumunu ölç (tur-başı
   sayaçlar: `TITLES`/`FUN`/`PFK`/`BUT`/`MEN`/`F2C`, aşağıda §3.2).
2. Payload'ı **canlı-üreten kaynak payload'dan** kur (bir önceki turun kendisi — bkz. §3.4
   "dökümden yeniden inşa" tuzağı), gerekirse üzerine değişiklik ekle.
3. **`IV_MODE='WRITE'`** ile yaz.
4. Final sayaçları ölç, **tur-başı ile kıyasla** (§3.5 doğrulama protokolü). "Activated/
   üretildi" mesajına güvenilmez.

### 3.2 CUA tuzağı ① — `IT_BUTTONS` hedef status'ün toolbar'ını HER ÇAĞRIDA yeniden kurar

> ⛔ **DÜZELTİLMİŞ KURAL** — önceki iddia *"`IT_BUTTONS` `IV_RECREATE` ile KURAR,
> `IV_RECREATE`'siz sadece EKLER"* **YANLIŞTI**, kullanılmasın.

**Doğrusu (üreteç kaynağından, satır-referanslı):** her `WRITE` çağrısı hedef status'ün
application-toolbar'ını (`but` tablosu) **koşulsuz `REFRESH` eder**, sonra **yalnız o çağrının
`IT_BUTTONS`'ında verilen** butonlarla yeniden kurar. **`IV_RECREATE` bu davranışı
DEĞİŞTİRMEZ** — o parametre yalnız Dynpro'yu (alan/flow) yeniden kurar, toolbar'ı değil.

⇒ **KURAL:** o turda dokunulmayan (payload'a konulmayan) bir status'ün önceki turlarda
eklenmiş butonu, o status **hiç WRITE edilmese bile**, o status **aynı çağrının hedefi
DEĞİLSE etkilenmez** — ama status'ün KENDİSİ o turda WRITE ediliyorsa VE `IT_BUTTONS`'ı o
statüsün TÜM butonlarını içermiyorsa, **eksik bırakılan buton düşer.** Yani: *"payload'ında
OLMAYAN ama o status'te ÖNCEDEN VAR OLAN bir buton, o status her yeni WRITE turunda
KAYBOLUR."* Bu, fonksiyon TANIMLARI (`fun`/`pfk`/`act`) için geçerli **değildir** — onlar
yalnız eklenir/güncellenir, asla silinmez (aşağıdaki §3.3 ile karıştırılmamalı).

**Neden bu iddia daha önce ters çıkmıştı — dar-ölçümün geniş-genellenmesi:** ilk gözlem
`FUN`/`PFK` **sayaçlarını** ölçmüştü; bunlar **program-geneli**dir ve fonksiyon tanımları hiç
silinmediği için zaten hiç azalmaz. *"Hedef status'ün `IT_BUTTONS`'ından bir butonu atla ve o
status'ten düşüyor mu bak"* deneyi hiç yapılmamıştı. **Bir davranış iddiası, o davranışı
ÜRETEN deneyle kurulmalıdır** — yan bir sayacın değişmemesi, farklı bir tablonun aynı şekilde
davrandığını göstermez.

### 3.3 CUA tuzağı ② — donör-çakışan fcode her WRITE'ta donör etiketine döner

Üreteç, standart donör (bir SAP-standart status havuzu) fonksiyon tanımlarını (`fun`) referans
alır. Bir fcode **donörde de varsa** (ör. donörün kendi "Kaydet" benzeri bir fonksiyonu) ve
o turun `IT_BUTTONS`'ında **verilmezse**, o fcode'un metin/quickinfo'su donörünkine
**sessizce döner** — hem de bu değişiklik o turda **dokunulmayan başka bir ekranda** görünür
(fonksiyon tanımı program-geneli olduğu için).

**KURAL:** *payload'ında OLMAYAN ama DONÖRDE BULUNAN bir fcode, her yeni ekran turunda donör
etiketine geri döner.* ⚠ Bu, §3.2'deki toolbar-kaybı kuralından **AYRI bir mekanizmadır**
(biri `but`u, biri `fun`u etkiler) — ikisi aynı anda oluşabilir.

**Neden sayaçlar bu sınıfı GÖRMEZ:** `FUN`/`PFK`/`BUT`/`TITLES` **hiç değişmez** — kaybolan
yalnız **etiket + quickinfo**metnidir, ama kullanıcıya birden çok canlı ekranda görünür.
Sayaç-bazlı doğrulama "her şey yolunda" der; **kontrol grubu ölçümü ZORUNLU** (donörde
OLMAYAN fcode'lar hiç etkilenmez, donörde OLAN fcode'lar payload'da yoksa düşer — bu ayrım
"üreteç butonları bozuyor" hipotezini "tam olarak donör-çakışması" olarak daraltır).

**REÇETE (iki katman):**
1. **Süreç:** ekran turunun sonunda `IV_MODE='READ'` **`FUNDTL` dökümünü tur-başıyla
   diff'le.** Sayaçlar tek başına yetmez.
2. **Tasarım:** birden çok status aynı fcode'u kullanıyorsa tooltip ekrana özel OLAMAZ
   (öznitelik program-genelidir) → **ayrı fcode ver** (§4'ün ayrı-fcode kuralı). "Jenerik
   etiket yaz" uzlaşması **denenip GERİ ALINMIŞTIR** — jenerik etiket çarenin değil sorunun
   tarifidir.
3. **Bundan sonraki her CUA turunda**, o turda WRITE edilecek her status için, o statüsün
   donör-çakışan fcode'ları (varsa) **payload'a KONULUR** — yoksa el değmeden bozulur. Ya da:
   donör-çakışanların HEPSİNİ İÇEREN status **en son** koşulur.

### 3.4 ⚠ Payload'ı DÖKÜMDEN yeniden inşa etme — kaynak-otorite payload'ı kullan

`IV_MODE='READ'` çıktısı (alan dökümü: konum/tip/format/uzunluk/görünürlük/…) **`FROM_DICT`
bayrağını taşımaz.** Bir ekranı bu dökümden yeniden inşa etmek, dökümün taşımadığı özniteliği
(DDIC bağını) **sessizce siler.** Kural: *bir dökümden yeniden inşa, dökümün TAŞIMADIĞI
özniteliği sessizce siler.* Kaynak-otorite payload (canlı ekranı üreten payload'ın kendisi,
görev dosyalarında saklanmışsa) VARKEN dökümden inşa ETME.

**Ek risk — bayat payload dosyası:** repo'da/görev-dosyalarında duran bir payload, bir
sonraki CUA turundan **önceki** bir durumu yansıtıyor olabilir (ör. bir status'e sonradan
buton eklenmiş ama payload dosyası ondan önceki turdan kalmış). §3.5'in önden-hesap adımı
tam olarak bu riski yakalamak içindir — payload'ı "güncel" varsaymadan önce §3.5 uygulanır.

### 3.5 CUA tuzağı ③ — per-status toolbar araçla OKUNAMAZ → `BUT` deltasını ÖNDEN hesapla

Bir status'ün **şu an** hangi butonları taşıdığı doğrudan tooling ile okunamaz (toolbar
ikili/binary formatta saklanır; obje-tipi anahtar taşımaz). Yani *"şu ekranda şu an hangi
butonlar var?"* sorusunun doğrudan cevabı yok — payload dosyası da tek başına güvenilir
"kaynak" değildir (§3.4).

**ÇARE — ölçülemeyen şeyi ÖLÇÜLEBİLENDEN türet:** `BUT` sayacı **program-geneli**dir ve tüm
status'lerin toplam toolbar-satır sayısını sayar ⇒ beklenen delta **gönderilecek setlerden
önceden hesaplanabilir**:

```
Δ BUT = Σ (her WRITE edilecek status için: gönderilen buton sayısı − o status'ün TAHMİN
           EDİLEN mevcut buton sayısı)
```

**KURAL: bu hesap CUA çağrısından ÖNCE yapılır ve tur-başı `BUT` sayacıyla kıyaslanır.**
Uyuşmuyorsa gönderilecek set YANLIŞTIR — **yazmadan önce** anlaşılır (script hedefe
uymuyorsa yazmadan `exit ≠ 0` vermelidir). Kontrol tur SONRASINDA yapılırsa (ölçülmüş
regresyon vakası: bir turda repo'daki bayat payload'dan "2 buton" sanılan bir status'ün
canlıda **3** butonu vardı; regresyon `BUT` deltasının beklenenden 1 fazla çıkmasıyla
**geriye doğru** teşhis edildi) — doğru teşhis ama **bir tur geç**; buton bu arada canlı
ekrandan gerçekten düşmüş oluyor.

### 3.6 GUI'de gözle doğrulanması ŞART olan maddeler (araçla okunamaz)

Toolbar etiketi/quickinfo, alan giriş/salt-okuma HİSSİ, ve diyakritik karakter render'ı
**hiçbiri sayaçla doğrulanamaz.** Her CUA turu sonunda kullanıcıya (SAP GUI'den) şu liste
sorulur: ① her diyalog ekranının KENDİ kaydet-fcode'unun doğru etiket/quickinfo taşıdığı,
② dinamik-kilitli alanın kapsam-içi/dışı senaryolarda doğru davrandığı, ③ yeni metinlerde
diyakritik (ç/ğ/ı/İ/ö/ş/ü) doğru göründüğü.

---

## 4. Doğrulama protokolü — tur başı ↔ final sayaç kıyası

Her CUA/ekran turunda şu sayaçlar tur-başı ve final'de ölçülür ve **birebir kıyaslanır**
(beklenmeyen bir fark = araştırılacak bulgu, "muhtemelen zararsız" denip geçilmez):

| Sayaç | Anlamı | Kapsam |
|---|---|---|
| `TITLES` | Titlebar sayısı | program-geneli |
| `FUN` / `FUNDTL` | Fonksiyon TANIM sayısı / dökümü (kod+metin+ikon+quickinfo) | program-geneli |
| `PFK` | Fonksiyon-tuşu eşleme sayısı | program-geneli |
| `BUT` | Toplam toolbar-satır sayısı (TÜM status'lerin toplamı) | program-geneli |
| `MEN` | Menü satırı sayısı | program-geneli |
| `F2C` | Alan-container eşleme sayısı | **ekran-bazlı** (tek status'ün Dynpro alan sayısı) |

**Kritik ayrım:** `TITLES/FUN/PFK/BUT/MEN` **program geneli**dir, ekran-bazlı DEĞİL — dört
farklı ekranda ölçülen bu sayaçların birebir aynı çıkması normaldir ve "ölçüm bozuldu"
anlamına gelmez; **bir sayının neyi saydığını yanlış bilmek**, gerçek bir farkı sahte
sanmaya (ya da tersini) yol açar. Yeni ders: *sayı beklenmedik çıkınca ilk soru "ne değişti?"
değil "bu sayı neyi sayıyor?"*

**Tam protokol:**
1. Tur-başı sayaçları `IV_MODE='READ'` ile ölç.
2. §3.5'in önden-hesaplanan `BUT` deltasını tur-başı sayaçla topla → beklenen final.
3. WRITE et.
4. Final sayaçları ölç → adım 2'nin beklentisiyle **birebir** kıyasla.
5. **`FUNDTL` diff'i al** (§3.3) — kaybolan fcode YOK, yalnız planlanan eklemeler var.
6. İçerik eşitliği: değişmeyen ekranların alan/flow/header'ı **birebir aynı** kalmalı.
7. `adt_inactive_objects` **0** (bu programın objelerinde) — kanıtı `adt_get`/canlı içerik
   okuması ile teyit et, "aktive edildi" mesajına güvenme.
8. §3.6'daki GUI-only maddeler kullanıcıya sorulur.

"Üretildi/aktive edildi" mesajına **hiçbir adımda** güvenilmez — her iddia yukarıdaki
ölçümlerden biriyle kanıtlanır.

---

## 5. Tuzak → aksiyon tablosu (özet)

| # | Tuzak | Aksiyon |
|---|---|---|
| T1 | Elle `gs_*` program-lokal struct + `MOVE-CORRESPONDING` köprüsü | DDIC yapıya bağla (`FROM_DICT`), köprüyü TAMAMEN sil — yarım bırakma |
| T2 | Aynı yapıda 2. alan olduğu için "DDIC attachment yolu kapalı" sanmak | Attachment BİLEŞENE yapılır, alan ADINA değil — iki bileşen aynı SHLP'ye bağlanabilir |
| T3 | "DDIC-bağlı alanda F4 parametre-karışması doğamaz" varsayımı | YANLIŞ — `FROM_DICT` eşlemeyi kurmaz; `where` bloğunda parametre AÇIKÇA verilmeli |
| T4 | Elle `MATCHCODE` bırakıp yanına attachment eklemek | Elle `MATCHCODE` attachment'ın ÖNÜNE GEÇER — ekran-tarafı `MATCHCODE`'u BOŞALT |
| T5 | DDIC değişti ama ekran regen edilmedi, "F4 hâlâ çalışmıyor" | Klasik Dynpro DDIC bilgisini generate-anında gömer → **regen ZORUNLU** adım, plana baştan konur |
| T6 | Z arama yardımı (SHLP) yaratmayı denemek | YAPILAMAZ (ölçülmüş araç sınırı) → buton+popup'a geç, tekrar deneme |
| T7 | Veriye bağlı F4 için POV yazmayı denemek | Bu üreteç POV üretmiyor → buton+popup (salt-görüntüleme) ile telafi et |
| T8 | Payload'ı `IV_MODE='READ'` dökümünden yeniden kurmak | Döküm `FROM_DICT` taşımaz → kaynak-otorite payload'ı kullan |
| T9 | Bir status'e `IT_BUTTONS`'ta eksik buton vermek ("zaten vardı" varsayımı) | `IT_BUTTONS` toolbar'ı HER ÇAĞRIDA sıfırdan kurar → o statüsün TÜM butonları her seferinde verilir |
| T10 | Donör-çakışan fcode'u (ör. standart bir "Kaydet" kodu) payload'a koymamak | Donörde var olan fcode her WRITE'ta donör etiketine döner → payload'a KONULMALI ya da ayrı fcode ver |
| T11 | Birden çok status aynı fcode'u paylaşıyor, farklı quickinfo bekliyor | Fonksiyon özniteliği (metin/quickinfo) program-genelidir → HER ekrana AYRI fcode ver |
| T12 | CUA turu sonrası kontrol (sayaç sonradan bakılıyor) | `BUT` deltasını YAZMADAN ÖNCE hesapla ve tur-başı sayaçla kıyasla |
| T13 | ATC/gate bulgu sayısını "toplam kapsam" sanmak (ör. literal-metin bulguları) | Bir kontrolün bulduğu sayı **alt sınırdır** — kapsamı koddan çıkar, gate'ten değil |
| T14 | Tanıdık F4 semptomunda direkt yeni deney kurmak | Önce görev-içi geçici dosyalar/SESSION_NOTES/memory'de önceki teşhisi ARA |

---

## İlgili

- [`templates/classic-dynpro-dialog.prog.abap`](templates/classic-dynpro-dialog.prog.abap) — kanonik şablon
- [`templates/classic-alv-list.prog.abap`](templates/classic-alv-list.prog.abap) — kardeş şablon (liste)
- [`howto-dynpro-gui-status-generation.md`](howto-dynpro-gui-status-generation.md) — üreteç temel kullanım kılavuzu
- [`adt-fugr-functions.md`](adt-fugr-functions.md) §6 — üreteç iç-mekanik referansı
- [`../standards/06-coding-classic-dialog.md`](../standards/06-coding-classic-dialog.md) — include bölme, ALV kuralı, F4 karar tablosu özeti
- [`checklists/classic-dialog-creation.md`](checklists/classic-dialog-creation.md) — pre-flight checklist
- [`lessons-learned.md`](lessons-learned.md) — PATTERN #22/#23 (bu dosyanın damıttığı tuzaklar)
