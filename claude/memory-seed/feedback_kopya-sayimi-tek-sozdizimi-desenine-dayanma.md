---
name: feedback_kopya-sayimi-tek-sozdizimi-desenine-dayanma
description: "Kopya/ihlal sayımını tek bir sözdizimi desenine (grep) dayandırma — kopya biçimini değiştirerek saklanır; premise'i view'ın GERÇEKTEN okuduğu kaynakta ölç"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8d6ce828-8cbd-420e-8853-f622a6f79a24
---

İki kardeş hata, aynı turda (2026-08-09, merkezî kullanılabilir-stok):

**1. Sayımı tek grep desenine dayandırma.** *"Aynı formül 11 objede tekrar ediyor"* dedim; desen
`end as abap.dec( 15, 3 ) ) as AvailableStock` idi — yani **CASE'li** yazımı arıyordu.
`ZSD001_I_ORDERPRICE` aynı formülü **CASE'siz** yazdığı için ağa takılmadı. Gerçek sayı 12'ydi.
⇒ Kopya, **biçimini değiştirerek saklanır**. Sayım iddiası kuracaksan en az iki farklı eksenden
ölç (sözdizimi + alan adı + tüketilen agregatların `where_used`'ı) ya da "en az N" de.

**2. Premise'i yanlış tabloda ölçme.** *"`''` anahtarı serbest, çünkü MARD'da boş-lgort satırı
YOK (114 satır ölçüldü)"* diye tasarıma yazdım. Ölçüm doğruydu ama **view MARD'ı okumuyordu** —
`I_MaterialStock` okuyor ve orada boş-lgort **VAR** (2 satır / 102 birim). Sonuç tesadüfen
ayakta kaldı (bir `<> ''` süzgeci yüzünden), premise çürüktü. Bug gate BLOCKER verdi.
⇒ Bir premise'i doğrularken **kodun GERÇEKTEN okuduğu kaynağı** ölç, "benzerini" değil.

**Why:** İkisi de "ölçtüm" hissi verip yanlış sonuca güven kazandırır — en tehlikeli tür,
çünkü kanıtlı görünür. İkincisi tasarım dokümanına *"ölçülmüş dayanak"* etiketiyle girdi ve
kodun bir süzgecinin gerekçesi olarak durdu; kaldırılsaydı özdeşlik sessizce çökerdi.

**3. ŞEMA-VARSAYIMIYLA DESEN YAZMA — sıfır sonuç "yok" DEĞİL (yeni vaka 2026-09-01, lider).**
CPI mapping XML'inde dolu `vmdefault` saydım: `grep -o 'vmdefault="[^"]\+"'`. **7 dosyada da 0** çıktı
ve bunu bir alt-ajan brifine *"teslim edilen hiçbir `.mmap`'te dolu `vmdefault` yok"* diye **olgu**
olarak yazdım. Gerçek: XML'in biçimi `<param name="vmdefault"><value>D</value></param>` — yani
`vmdefault="` dizisi dosyada **hiç geçmiyor**; desen yapısal olarak **hiçbir şeyi** yakalayamazdı.
Doğru desenle (`name="vmdefault"><value>[^<]\+</value>`) ölçüm: <MUSTERI-E>'te **1 dolu** (`D`),
teşhis artefaktlarında **58/54**. Ajan bunu buldu ve brifle **çelişki** olarak raporladı.
⇒ Ders: bir alanı grep'lemeden önce **gerçek sözdizimini dosyadan GÖR** (`grep -o 'vmdefault.\{0,25\}'`
gibi geniş bir turla). **Sıfır sonuç iki anlamlıdır:** "yok" ya da "desen tutmadı" — ve
ayırt edilmeden **olgu diye başkasına aktarılamaz** ([[feedback_aktardigin-olcum-emre-donusunce-kanitini-tasi]]).
⚠ Aynı turda ikinci bir grep (`vmdefault.\{0,20\}`) doğru sayıyı gösteriyordu; iki ölçümüm
**çelişiyordu** ve çelişkiyi fark etmedim — kontrol grubu (bilerek DOLU olan teşhis dosyası) ilk
desende de 0 verdiğinde alarm çalmalıydı.

**4. BÜYÜK/KÜCÜK HARF DUYARLILIĞI — beyan edilen arama uzayını SESSİZCE daraltır (yeni vaka 2026-09-08, lider).**
`ZSD001_I_DELIVERED_QTY`'nin tüketicilerini saydım: `grep -rn "ZSD001_I_DELIVERED_QTY"` → **4 tüketici**, hepsi CDS association'ı. Bunu bir kapı brifine *"dört tüketici, hepsi `vbap`'tan seçiyor ⇒ delta 0"* diye **doğrulama sözleşmesi** olarak yazdım. Gerçek: **5**. Kaçan
`ZCL_SD018_SO_EXCUPL_PROCESSOR.clas.abap:1184` — ABAP kaynağı `FROM zsd001_i_delivered_qty` diye
**küçük harfle** yazıyor. Canlı `adt_where_used` onu döndürdü, benim grep'im döndüremezdi.
⭐ Zararı sıradan değildi: kaçan tüketici diğer 4'ten **farklı sınıftaydı** — diğerleri değeri
yalnız gösterirken o, `max(dispatched, delivered)` ile Excel yükleyicisinin **miktar-azaltma alt
sınırını** kuruyor, yani bir **yazma kararı**. ⇒ "Zarar profili" iddiam da eksikti.
⚠ Karşı yönde de yanılgı vardı: kapı aynı view için **6** tüketici saymıştı — ikisi yalnız
**yorumda** geçen tip-emsali atıflarıydı. Ham `grep` hem **eksik** hem **fazla** sayar.
⇒ Ders: **ABAP kaynağı küçük harf, CDS/doküman büyük harf yazar** — obje adı ararken `grep -i`
varsayılandır. Ve bir tüketici listesi **koda dayalı otoriteyle** (`adt_where_used`) kurulur;
grep onu **doğrular**, yerine geçmez. `where_used` çıktısındaki `DEVC/K` satırları **paket**tir,
tüketici değil — sayımdan düşer (o turda 9 referansın 4'ü paketti).

**5. AD ÇALIŞMA ZAMANINDA KURULUYORSA GREP YAPISAL OLARAK SIFIR VERİR (yeni vaka 2026-09-10, lider).**
ZSD001 FE-34 turunda bir alt-ajan brifine ölçüt yazdım: *"`SoldToInvalid` bayrağının var olup
olmadığını grep ile doğrula; **yoksa yazma**."* Literal grep 5/5 dosyada **0** döndü — ama bayrak
**gerçekti**. Ad hiçbir yerde sabit yazılmıyor: yazan taraf `var sInv = oCfg.field + "Invalid"`
(`CreateSe.controller.js:530`), okuyan taraf `if (h[f] && h[f + "Invalid"])` (`:652`), eşleme ise
`VH` sözlüğünde (`hSoldTo → field:"SoldTo"`, 5/5 dosyada). Yani `"SoldToInvalid"` dizisi kaynakta
**hiç geçmiyor**, buna rağmen çalışma zamanında `/header/SoldToInvalid` **var** ve `onSave`'i
bloklayabiliyor. Ajan bunu ölçtü ve ölçütümü **çürüttü**; brifim uygulansaydı kusur **en tipik
alanda** (AG) açık kalırdı.
⇒ Bu, §3'ün (şema-varsayımıyla desen) kardeşi ama daha sinsi: orada **sözdizimini** yanlış
biliyordum, burada ad **kaynakta hiç yok** — hiçbir desen düzeltmesi onu bulamazdı. Doğru refleks:
bir property/alan adı arıyorsan önce **onu ÜRETEN ifadeyi** ara (`+ "Invalid"`, `` `${x}_id` ``,
`CONCATENATE`, `ASSIGN COMPONENT`, sözlük/registry tabloları), sonra sabit adı.
⭐ **Ve ölçütü ALAN LİSTESİ değil KURAL yap.** Brifimdeki hata yalnız grep değildi; ölçütü
*"şu ad var mı?"* diye kurmuştum. Doğru ölçüt işin kendisiydi: *"bu fonksiyon bu alana geçerli
bir değer YAZDI mı? Yazdıysa bayrağı temizlenir."* Kural biçimindeki ölçüt dinamik adlardan
etkilenmez ([[feedback_capa-liste-degil-KURAL-olmali]]).

**How to apply:** (a) Sayım/kapsam iddiasını **tek malzeme/tek dosya/tek desenle** test etme —
bu turda BLOCKER tam da bu yüzden kaçmıştı (test malzemesi `<MALZEME-1>`'nin boş-lgort stoğu yoktu).
(b) "Ölçülmüş dayanak" yazarken **hangi tabloda/view'da** ölçtüğünü cümlenin içine yaz; okuyan
kaynak eşleşmesini denetleyebilsin. İlgili: [[feedback_dogrulama-sezgileri-dort-kural]] ·
[[feedback_sonucu-olc-uygulamayi-degil]] · [[project_zsd000-merkezi-avail-stock]]
