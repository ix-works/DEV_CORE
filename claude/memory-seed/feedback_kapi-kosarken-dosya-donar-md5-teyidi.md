---
name: feedback_kapi-kosarken-dosya-donar-md5-teyidi
description: Bug-gate koşarken artefakt DONAR; dondurma liderin ölçümüyle değil ÜRETİCİNİN md5 teyidiyle başlar — yoksa kapı bayat sürüm ölçer
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c613ab5b-9b21-4fae-8c5a-7ee49cb6d82c
---

Bir artefakt bağımsız kapıya (bug-expert) verildiğinde **kapı koşarken dosya DONDURULUR**:
üretici tek satır bile yazmaz, gelen yeni bilgi kuyruğa alınır, kapı raporundan sonra tek turda uygulanır.

⛔ **Dondurma, liderin kendi ölçümüyle BAŞLAMAZ.** Doğru sıra:
1. Lider: "dondur"
2. Üretici: "donduruldu, **md5 = X**"
3. Lider: üreticinin bildirdiği **X'i tırnak içinde tekrarlayarak** kapıyı açar

Lider "dondurdum @ <kendi ölçtüğü md5>" derse, üretici o sırada kuyruktaki bir talebi bitiriyor
olabilir ve çapa **bir tur geride** kalır.

**Çapa = md5, satır sayısı DEĞİL.** Satır sayısı sondaki newline yüzünden ±1 oynuyor
(`wc -l` 875 / editör 876) ve boşuna "tutarsızlık" tartışması açıyor.

**Kapıya da söyle:** "raporunun başına ölçtüğün md5'i yaz". Uyuşmazlık o an görülür.
Kapı md5 uyuşmazlığı görürse **durmasın**: diskte tek kopya varsa onu ölçüp devam etsin ve
farkı raporlasın — durmak boşuna zaman kaybı olur (bu doğru davranışı bugün kapı kendiliğinden gösterdi).

**Why:** 2026-08-26, tek bir sınıf değişikliğinde **dört kez** kapı bayat sürümle başladı. Dördünde de
sebep aynıydı: dondurma teyidini beklemeden kapıyı açmak. Bir keresinde kapı 785 satırlık sürümü
ölçerken dosya 792'ydi; bulguların satır numaraları tutmadı, tazelik tartışması tur yedi.
Kullanıcı sonunda haklı olarak "neden bu kadar uzun sürdü bir class değişikliği" diye sordu —
sürenin büyük kısmı bu çakışmalardı, işin kendisi değil.

**How to apply:** Kapı açmadan önce üreticiden "donduruldu + md5" teyidi al. Teyit gelmeden
`Agent` spawn etme. Aynı kural düzeltme turları için de geçerli: yaz → dondur → teyit → kapı.

### ⛔ `BUG_GATE_READY` DONDURMA TEYİDİ DEĞİLDİR — asıl tetikleyici KUYRUK (2026-09-04, 5. tekrar)

Kural yukarıda yazılıydı ve **yine ateşlemedi**. Sebebi ders: `BUG_GATE_READY` raporu **içinde md5
taşır** ve tam da bu yüzden dondurma teyidi *gibi görünür*. Değildir — çünkü rapor "yazmayı
bıraktım" demez, **"bu turu bitirdim"** der. Ajanın **posta kuyruğunda liderin daha önce gönderdiği
bir mesaj** duruyorsa, rapordan sonra onu işler ve yazmaya devam eder.

**Ölçülmüş vaka (aynı turda İKİ ajanda birden):** ikisi de `BUG_GATE_READY` + md5 gönderdi, ben
o md5'lerle kapıları açtım, sonra ikisi de **rapordan ~2 dk sonra** dosyaya yazdı — çünkü
kuyruklarında benim daha önce yolladığım mesajlar vardı (FE'de "Yol 1 onaylandı"nın iki
uygulanmamış şartı, BE'de bağlayıcı sözleşme). Sonuç: iki kapı da bayat çapayla açıldı,
FE'nin beyan ettiği md5 diskte **hiç var olmadı**. Kapılar yakaladı (biri dondurulmuş kopya
alarak, diğeri yeni md5'le devam ederek) — ama tur yedi.

⇒ **Doğru refleks:** `BUG_GATE_READY` geldiğinde kapıyı AÇMA; önce sor —
*"kuyruğunda işlenmemiş mesajım var mı? Dosyalar donduruldu mu? Şu andaki md5 nedir?"*
Özellikle **kendi gönderdiğin mesajları say**: rapordan önce yolladığın her mesaj potansiyel
bir yazım turudur. Bu, liderin kendi hatasıdır — üreticinin değil.

⇒ Üreticiye baştan söyle: *"yeni şart gelirse ÖNCE 'çapa X, düzenleme yapacağım, kapıyı durdur'
de, sonra yaz."* (Bugün FE bu dersi kendisi çıkardı ve yazdı.)

#### Sadeleştirme (BE kapısının damıtımı) — **md5'in VARLIĞI dondurma teyidi değildir**

Kök mekanizma `BUG_GATE_READY`'den daha genel: üreticinin mesajındaki bir md5, tek başına
**ilerleme raporundan ayırt edilemez**. *"İşte şu an ne ürettim"* ile *"artık yazmayı bıraktım"*
mesaj metninde AYNI görünür; ikincisi **açıkça söylenmezse** birincisi olarak varsayılır.
⇒ Kapı açan mesajda çapayı tekrarlarken, o çapanın **"donduruldu" teyidinden mi yoksa ilerleme
raporundan mı** geldiği belli olmalı. Teyit yoksa kapı AÇILMAZ.

#### ⭐ Hasarın gerçek biçimi: kapı kendi çıktısını HAYALETE asar

Yukarıdaki 08-26 vakası gürültülüydü (satır numaraları tutmadı, kendini ele verdi). 09-04'te
hasar **sessiz** biçim aldı: bayat çapayla yazılan brifingin iki maddesi, **artık var olmayan
kodun özelliklerini sınamamı istedi** ("`default_zw` hiçbir koşulda dolmuyor mu?",
"`lv_partner_for_addr` sadeleştirmesi davranışı koruyor mu?") — ikisi de *keşfedilecek* değil
**doğrulanacak önerme** olarak çerçevelenmişti. Brifingin premisine güvenen bir kapı, olmayan
koda dair **kanıtlı görünen hüküm** yazardı. Bu, [[feedback_karar-degisince-kaydi-ayni-turda-guncelle]]
dersinin brifing katmanındaki hâlidir: bayat kayıt ajanın gözünde OTORİTEDİR.
⇒ Brifingde bir önermeyi "doğrula" diye verirken, o önermenin ölçüldüğü ÇAPAYI da yaz.

#### Ucuz teşhis sinyali: **mtime kümelenmesi**

Uyuşmazlıkta ilk soru "hangi dosyalar tutmadı" değil, **"mtime'lar kümeleniyor mu"** olmalı —
tek `ls` kök nedeni verir. 09-04 ölçümü: uyuşan 3 dosya `17:06`, uyuşmayan 2 dosya `17:14`.
- kısmî uyuşmazlık + **ayrı zaman kümesi** ⇒ "üretici rapordan SONRA yazdı"
- tüm dosyalar kaymış ⇒ "yanlış dal / yanlış kopya"

#### ⛔ Brifing şablonundaki ÇELİŞKİ — düzelt

Brifinglerimdeki *"çapa tutmazsa DUR ve bana yaz"* cümlesi bu kaydın *"durmasın: diskteki tek
kopyayı ölçüp devam etsin, farkı raporlasın"* kuralıyla ÇELİŞİYOR. Kapı bu turda kaydı tercih
etti ve **doğru** yaptı — durmuş olsaydık bir tur kaybederdik, iki bayat önerme yine yakalanırdı.
⇒ Brifinge *"çapa tutmazsa DURMA: diskteki kopyayı ölç, farkı raporun başına yaz, devam et"* yaz.

**Sahiplik:** bunu "lider hatası" değil, **teyit adımı olmayan bir el-değiştirme protokolünün
öngörülebilir çıktısı** olarak kaydet. Aynı turda **iki bağımsız kapıda birden** tekrarladı —
kusur kişide değil akıştadır.

İlgili: [[feedback_ajan-okuma-disiplini-tazelik]], [[feedback_duzeltme-turu-kendi-ciktisina-kapi-ister]],
[[feedback_lider-ajan-paralel-yazim-cakismasi]]


#### ⭐ AYNI SINIF **COMMIT ADIMINDA** DA VAR — `md5sum` ile `git add` arasi bir YAZMA PENCERESIDIR (2026-09-05, 6. tekrar; bu kez lider)

Yukarisi hep *kapi acma* adimini konusuyor. Bugun ayni mekanizma **commit adiminda** tekrarladi ve
kayda gecmemisti. Olculen vaka: `fix-ekr02-msgdiag` "KOD DONDU + md5 `7d2fe53f`" dedi; ben diski
olctum → `f66228c0` (uyusmadi, delta'yi inceledim, sagalam buldum), sonra `git add` + commit ettim.
Commit'in ICINDE cikan md5 **`f7af494b`** idi — yani `md5sum` ile `git add` arasindaki ~1 arac
cagrisi suresinde ajan bir kalem daha (B14) yazdi ve ben **incelemedigim bir delta'yi commit ettim**.
Commit govdesine de yanlis yazdim ("B1-B13" — gercekte B1-B14).

⛔ Yanilticiligi sudur: `git diff HEAD` commit'ten SONRA **bos** doner (disk = commit), yani hata
kendini gizler. Yakalayan sey `git status`in beklenmedik sessizligi oldu — dosya "M" listesinde
gorunmuyordu ama md5 degismisti; ikisi ancak "commit zaten yeni icerigi almis" ile uzlasiyordu.

⇒ **Kural:** `git add`den ONCE md5'i YENIDEN olc ve commit govdesine **o** md5'i yaz. "Olctum" ile
"commit ettim" ayni an degildir; arada gecen her arac cagrisi bir yazma penceresidir.
⇒ Daha ucuzu: `git add` + `git commit`i **tek** arac cagrisinda, hemen oncesinde md5 ile birlikte
kos (`md5sum … && git add … && git commit …`) — pencere kapanir.
⇒ Ajan tarafinda kok neden: **"KOD DONDU" brifi HENUZ BITMEMISKEN soylendi.** Ajanin brifinde
B12/B13/B14 + B4-genisletme kalemleri duruyordu; "dondu" demesi kacak degisiklik degil, **ERKEN
DONMA BEYANI** idi. ⇒ Brife yaz: *"KOD DONDU yalniz brifteki TUM kalemler bittiginde soylenir;
kismi teslimde 'ARA TESLIM + md5' de."*


#### ⭐ 7. tekrar (2026-09-06, ZSD001 TP yükleyici): tetikleyici **ÖLÇÜM İSTEĞİYDİ** — okuma isteği de yazma üretir

Bugünkü vaka öncekilerden farklı bir yerden geldi ve kayıtta yoktu. Sıra: düzeltme emri → ajan
"KOD DONDU-3" + md5 → ben md5'i diskte doğruladım → **dondurma teyidi İSTEMEDEN** kapıyı açtım →
kapı `b26ece7a` ile başladı, ajan `82b55d59`'a yazdı, kapıya düzeltme yollamak zorunda kaldım.

⛔ Kök neden, kuyrukta duran bir **iş** emri değildi: düzeltme emrimin sonuna eklediğim
*"conversion-exit sınıfını dosya genelinde bir kez daha tara ve negatif testle göster"* cümlesiydi.
Bu **salt okuma** isteğidir — ve tam da bu yüzden zararsız sanılır. Değildir: ajan ölçümü yaptı,
emri ÇÜRÜTEN bir sonuç buldu (`AUART`'ın da CONVEXIT'i varmış) ve **doğru davranarak** bulguyu
kodun yorumuna yazdı. Yani *"yalnız ölç"* dediğim adım bir dosya yazımına dönüştü.

⇒ **Kural genişler:** dondurma penceresini açan şey "yazma emri" değil, **cevaplanmamış herhangi
bir istektir**. Ölçüm/analiz/doğrulama istekleri de sayılır — çünkü kayda değer her bulgunun
doğal varış yeri artefaktın kendisidir (yorum, doc, test).
⇒ Pratik: kapı açmadan önce *"kuyruğunda işlenmemiş **hiçbir** isteğim kalmadı mı — ölçüm
istekleri dahil?"* diye sor. "Yazma emri kalmadı" yetmez.
⇒ Ölçüm isteğini kapı turuna sarkıtacaksan baştan çerçevele: *"ölç ve BANA yaz, dosyaya YAZMA."*

Yan not (bugün ölçüldü, ayrı ders değil): ölçüm emrimin kendisi hatalıydı — "conversion exit'i olan
tam iki alan var" dedim, canlı `DD04L` **üç** gösterdi; ayrıca `KDMAT(IDNEX)`/`ABLAD(TEXT25)` diye
yazdığım parantezler conversion exit değil **domain** adlarıydı. Ajanın emri çürütmesi doğru işti.
⇒ [[feedback_aktardigin-olcum-emre-donusunce-kanitini-tasi]] burada da geçerli: emre koyduğun her
sayı bir iddiadır ve ajan onu ölçmekle yükümlüdür.


### ⛔⛔ 7 TEKRARDAN SONRAKİ ASIL DERS: **BU KAYDA 8. PARAGRAF YAZMAK ÇÖZÜM DEĞİL**

Bu dosya 2026-08-26'dan beri **yedi** vaka biriktirdi. Her seferinde kural okundu, doğru
yazıldı, zenginleştirildi — ve **bir sonraki turda yine ateşlemedi**. Kullanıcı 2026-09-06'da
haklı olarak sordu: *"ee bunlardan bir ders çıkardın mı, tekrarlamamak için?"*

⇒ **Kanıt açık: kaydın İÇERİĞİ değil, BİÇİMİ yanlış.** *"Şu anda şunu yapmayı hatırla"*
biçimindeki bir kural, tam da unutulduğu anda hatırlanmayı gerektirir — kendi kendini
baltalar. (Aynı tur, aynı sınıf: [[feedback_kararlari-once-topla-sonra-dispatch]] de vardı,
o da ateşlemedi — yedi kalemlik düzeltmeyi üç parçada gönderdim.)

## ÇÖZÜM — dondurma HANDSHAKE'İNİ KALDIR, kapıya SNAPSHOT ver

Kök neden iki taraflı, zorlanmayan bir el sıkışma protokolü. Onu tamamen **ortadan kaldır**:

1. Lider, kapıyı açmadan hemen önce artefaktı **salt-okunur bir anlık kopyaya** alır
   (scratchpad altında `gate-<ad>-<zaman>/`), md5'leri kopya üzerinde ölçer.
2. Brifingde kapıya **kopyanın yolunu** verir, canlı yolu değil.
3. Üretici bu sırada yazmaya devam edebilir — **umursanmaz**, çünkü kapı sabit bir artefakt
   inceliyor. "Dondur / donduruldu / md5 teyidi" adımları **gereksizleşir**.
4. Kapı raporu geldiğinde lider `diff kopya canlı` ile aradaki değişimi görür; boşsa rapor
   doğrudan geçerli, değilse **yalnız delta** yeniden bakılır.

⇒ Bu, sınıfı hatırlamaya değil **yapıya** bağlar: md5 çakışması *tanım gereği* imkânsız hale
gelir. Snapshot maliyeti bir `cp`; şimdiye kadarki maliyet ~7 kayıp tur.

⚠ İstisna: kapının canlı SAP'ye bakması gerekiyorsa (where-used, DB ölçümü) o kısım canlıdır —
snapshot yalnız **kaynak dosyalar** içindir.

## İkinci yapısal kural: DÜZELTME EMRİ TEK PARÇADIR
Kapı raporu geldiğinde bulguları **tek emirde** topla. "Şimdi 5 kalem gönderip sonra 2 kalem
daha eklemek" her ek parça için bir tur + bir yazma penceresi üretir. Kapı raporu bitmeden
emir yazmaya başlama.

**How to apply:** Kapı açacağın an refleks *"dondurmasını istedim mi?"* DEĞİL,
**"snapshot aldım mı?"** olsun — birincisi karşı tarafa bağlı, ikincisi tek başına senin
elinde ve doğrulanabilir.

#### ⛔ YUKARIDAKİ "SNAPSHOT" ÇÖZÜMÜNE KENDİ İTİRAZIM (aynı tur, kullanıcı sınaması üzerine)

Kullanıcı *"yapacağın değişikliği de iyi analiz et — gerçekten çalışacak mı, yan etkileri"*
diye sordu. Sınadım; **snapshot'ı ÇÖZÜLMÜŞ diye yazmam erkendi.** Üç kusuru var:

1. **Yan etki:** kapı emsal için canlı repo'yu grep'liyor. Hedef dosya hem snapshot'ta hem
   repo'da bulunacağı için kapı **aynı dosyanın iki sürümünü** okuyup çelişkili hüküm kurabilir.
   Çaresi brifinge "repo grep'i yalnız emsal içindir, hedef dosyaları hariç tut" yazmak —
   yani **yine hatırlanması gereken bir kural**; çözüm kendi teşhisini kısmen baltalıyor.
2. **`Agent` aracının hazır `isolation: "worktree"` seçeneği bu vakada İŞE YARAMAZ** — dosyalar
   git'te **untracked** (`??`), worktree'ye hiç girmezler. (Ölçüldü; önermeden önce bakıldı.)
3. **Yanlış problemi çözüyor.** 2026-09-06 turunda md5 yarışının maliyeti ~2 mesajdı (kapı
   sapmayı kendi yakalayıp devam etti — kayıttaki "durmasın" kuralı çalıştı). Asıl maliyet
   **yedi kalemlik düzeltmeyi üç parçada göndermek** ve **zaten aşılmış bir raporu reddetmek**ti.

⇒ **Sağ kalan kural:** *"düzeltme emri TEK parçadır, kapı raporu bitmeden emir yazmaya başlama"*.
Bu ucuz, yan etkisiz ve ölçülen hasarın büyük kısmını kapatıyor.
⇒ Snapshot **iptal değil, ERTELENDİ**: yalnız üretici gerçekten paralel yazıyorsa ve kapı uzun
sürecekse başvurulacak taktik — varsayılan protokol değil.

#### ⭐ ASIL KATMAN SORUSU — bu kayıt kendi emsalini görmezden gelmiş

[[feedback_ajan-kurali-brifingde-degil-taniminda-yasar]]: *"aynı hata tekrar ediyorsa kural
YANLIŞ KATMANDA yaşıyordur; brifingi zenginleştirme, TANIMA damgala."* Bu dosya sekiz tekrar
biriktirdi ve her seferinde **kendi içine** bir paragraf daha yazdı — yani tam olarak emsalin
"yapma" dediği şey. Lider hatasının kalıcı katmanı ajan tanımı değil, **her turda otomatik
yüklenen** katmandır: `.claude/settings.json:85` `PreToolUse` zinciri (bugün `Agent` spawn'ında
BRIFING-LINT + PRIOR-ART nudge'ları zaten basıyor) ya da kök `CLAUDE.md`.
⇒ Ölçüm: bu kuralın `.claude/` + `core/scripts/hooks/` altında kalıcı karşılığı **0 satır**.
⇒ Karar kullanıcıya sunuldu (2026-09-06): hook dalı eklensin mi — META-İNFRA, tüm projeleri
paylaşan çekirdeği etkiler.
