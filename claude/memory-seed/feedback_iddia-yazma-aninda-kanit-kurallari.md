---
name: feedback_iddia-yazma-aninda-kanit-kurallari
description: "Lider'in kendi iddialarına kanıt eşiği — rakam ve teşhis YAZMA ANINDA tetiklenen 4 kural; compact sonrası her rakam doğrulanmamış sayılır"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8d6ce828-8cbd-420e-8853-f622a6f79a24
---

Kullanıcı 2026-08-10'da sordu: *"son günlerde çok fazla 'benim hatam' demeye başladın,
ortak bir sebebi olabilir mi?"* — ve ardından: *"bunları nasıl yapmayı planlıyorsun,
neye göre yapacağım diyorsun?"* İkinci soru kritikti: niyet beyanı bu evde **kural
sayılmaz** (*gate'lenmemiş kural ≈ kuralsız*). Bu yüzden kurallar **gözlenebilir yazma
anına** bağlandı, "dikkatli ol"a değil.

**Ortak kök (ölçülen kalıp):** ajanlar **az önce ölçtükleri** şeyi söylüyor; lider
**okuduğunun hatırasını** söylüyor. Lider sürekli aktarıyor/özetliyor, her aktarım bir
sıkıştırma, sıkıştıkça niteleyici düşüyor. Sonuç: ajanlara "TAHMİN YASAK" yazıp kendine
uygulamamak. Aynı gün 6 vaka: `changedAt` bugüne dönmüş → *"iş olmuş"* (içerik okunmadı,
aktif kaynak ESKİYDİ) · `adt_lock_check:false` → *"kilit yok"* (o uç SM12'yi göremiyor,
`/adt/locks` bu sistemde **404**) · iki derleme hatası → *"bağımsız"* (ikincisi birincinin
gölgesiydi) · satır numarasından IS_LINK_UP tezi (kodun **çürüttüğü** tezi playbook'a geri
sokacaktı) · `SeBalanceQty=10` (ölçüm **5** diyordu; 10 = `SeQty`) · "gecikmenin sebebi
infra" (infra **paralel** koşuyordu, gerçek darboğaz FE'ydi).

**KURALLAR — yazma anına bağlı, dördü de:**
1. **Rakam yazarken:** brifinge/mesaja giren her sayı ya **bağlamda görünür bir araç
   çıktısından kopyalanır** ya **yeniden ölçülür**. *"Hatırlıyorum" geçersiz.*
2. **"Şu yüzden oldu" cümlesi kurarken:** ikinci ölçüm ≤1 araç çağrısı ise **önce onu koş**,
   sonra cümleyi yaz. Zaman damgası varsa içerik de var; aracın `false`'u varsa **ne
   göremediği** de belli.
3. **Hata fark ettiğimde:** düzelt, devam et. Yalnız **kullanıcının kararını değiştiriyorsa**
   söyle. Dokuz kez "benim hatam" demek hesap vermek değil **gürültü** — gerçek olanları
   görünmez kılar.
4. **🔴 COMPACT SONRASI:** özetlenen bağlamda **ölçülmüş sayı ile hatırlanan sayı aynı metne
   dönüşür**, ayırt edilemez. ⇒ Compact sonrası **her rakam doğrulanmamış sayılır**;
   brifinge girecekse **yeniden ölçülür**. (Bu kural compact'i aşar çünkü hafıza açılış
   protokolünde yeniden yüklenir — kullanıcının tespiti.)

5. **🔴 ÇAPA VERİRKEN — tazelik YETMEZ, KATEGORİ de doğrulanır (2026-08-10 vakası).** Lider
   brifinge `<MALZEME-1>/MA02 → 237−236−5 = −4` çapasını yazdı. **İki ayrı kusur:** (a) rakam **bir
   gün içinde çürümüştü** (SE miktarı 5→1 geri alınmıştı ⇒ bugün **0**) — üstelik düzeltme
   liderin **kendi hafıza kaydında yazılıydı**, brifinge geçerken eski hâli kopyalandı;
   (b) daha ağırı: `−4` bir **AvailableStock** (stok guard) sayısı, hedef yorum ise
   `window_qty`/`net_open` (GetOpenQty motoru) hakkında — **farklı formül**. Yani rakam taze
   olsaydı bile **yanlış yöne yönlendirecekti**. Ajan ikisini de yakalayıp yazmayı reddetti.
   ⇒ Çapa verirken iki soru: *"bugün hâlâ doğru mu?"* **ve** *"bu sayı ölçtüğüm şeyin
   formülünden mi geliyor?"* ⇒ **Kalıcı artefakta (yorum/doküman) VERİ değil MEKANİZMA yaz:
   veri çürür, mekanizma çürümez.**

**Why:** Bu hatalar tek tek küçük ama sınıf olarak pahalı: yanlış rakam ajanı yanlış yere
gönderir (bir tur), tek-sinyal teşhisi saatlerce yanlış eksende arattırır (bir vaka: 5 deneme
/ ~1 saat transport kovalandı, sebep kendi koyduğumuz guard'dı), ve sürekli özür trafiği
gerçek uyarıyı bastırır.

**How to apply:** Kural **yazarken** ateşlenir, sonradan denetlemede değil — o yüzden
uygulanabilir. Üçüncünün doğal yaptırımı kullanıcıdır (bu turda o fark etti, işe yaradı).
İlgili: [[feedback_dogrulama-sezgileri-dort-kural]] · [[feedback_kopya-sayimi-tek-sozdizimi-desenine-dayanma]] ·
[[feedback_sonucu-olc-uygulamayi-degil]] · [[feedback_arac-basarisizligini-zararsiz-sayma]]

## 5. ⭐ ÖLÇÜLMÜŞ İDDİANIN DA SON KULLANMA TARİHİ VAR — özellikle BRİFİNGE girerken (2026-08-21)

Kurallar 1-4 *"ölçtün mü?"* diye sorar. Bu kural *"ölçtüğün ŞEY hâlâ o mu?"* diye sorar.

**Vaka.** `A-13`'ün üç sınıfı SAP'ye push edildi; gateway readback ile `sha256` **birebir**
eşitliği kanıtladı. Lider bunu doğru şekilde *"canlı = yerel"* diye kaydetti. **Sonra** ATC
düzeltme turu koştu ve dosyalar **yalnız çalışma ağacında** değişti (push edilmedi). Lider,
bir sonraki kapının brifingine *"canlı = yerel (lider `sha256` ile doğruladı)"* cümlesini
**yeniden ölçmeden** taşıdı. Ölçüm: yerel **3031** satır / `FOR ALL ENTRIES` **6** · canlı
**2996** / **0**. ⇒ Cümle **ölçüldüğü an doğruydu**, brifinge girdiği an **yanlıştı**.

**Neden kural 1'e sığmıyor:** kural 1 *rakam* der ve *"hatırlıyorum geçersiz"* der. Buradaki
iddia bir **rakam değil, durum**tu; üstelik **hatırlanan değil, gerçekten ölçülmüştü**. Kusur
ölçümde değil, **ölçüm ile kullanım arasında geçen olayda**.

**⛔ BRİFİNG ÖZEL BİR YERDİR — asıl zarar burada.** Kendi kafamdaki bayat bilgi bir sonraki
ölçümde düzelir. **Brifinge giren bayat bilgi ise taze-bağlamlı bir ajana TALİMAT olur** ve o
ajanın bayatlığı fark etmesinin **hiçbir yolu yoktur** — kendi başına ölçmedikçe. Bu vakada
kapı bağımsız ölçtüğü için yakaladı; ölçmeseydi *"canlı ATC = 10 P1"* rakamını **fix'in
doğrulaması** sanacaktık, oysa **baseline**'dı.

**How to apply:**
- **Brifinge bir DURUM iddiası yazarken sor:** *"bu ölçümden sonra bu durumu değiştirebilecek
  bir şey oldu mu?"* Push · pull · düzeltme turu · başka ajanın yazması → **hepsi değiştirir**.
  Şüphe varsa ölçüm **tek komutsa** koş; değilse iddiayı **tarihiyle** yaz:
  *"push anında (11:02) eşitti; sonraki turlar ölçülmedi"*.
- ⭐ **En ucuz sigorta:** brifingde durumu **iddia etme**, ajana **ölçtür**. *"Canlı = yerel"*
  yerine *"canlı ile yereli karşılaştır ve sonucu raporla"* yaz — hem doğru olur hem bir
  ölçüm daha kazanırsın.
- Aynı aile: [[feedback_kanit-tazeligi-indeks-ve-zaman-sirasi]] · [[feedback_sonucu-olc-uygulamayi-degil]] ·
  [[feedback_yesil-sinyalin-kapsamini-sor]] (bu, onun **zaman eksenli** kardeşi: yeşilin
  kapsamı gibi, **tazeliği** de sorulur).

## 6. ⭐ İLK ÖLÇÜM BULGU DEĞİLDİR — ölçümün KENDİSİ doğrulanmadan yayımlanmaz (2026-08-29)

Kurallar 1-2 *"ölçtün mü?"* diye sorar. Bu kural *"**ölçümün kendisi** doğru mu?"* diye sorar.
Kullanıcı: *"hipoteze dayalı bana cevap veya öneri sunma, mutlaka kanıtla, teyit et."*

**Vaka — tek oturumda dört kez, hepsi kullanıcıya sunulduktan SONRA çürüdü:**
| sunulan | ölçünce |
|---|---|
| *"kalıcı öğrenim diske yazılmıyor"* | memory'ye 30 kayıt / 9 gün (~2,5/gün) |
| **`0/37 oturum açılışta çapa okuyor`** (tablo halinde) | **35/35 okuyor**, medyan 28. kayıtta — fark yalnız **pencereydi** (ilk 12 kayıt hook/attachment) |
| *"82 Bash/koşu = validator koş→düzelt→yeniden koş döngüsü"* | 328 Bash / 326 benzersiz = **%0,6** tekrar; koşu-içi tekrar **%0** |
| *"MEMORY.md 3× okunmuş = israf"* | 3 ayrı koşuda, her taze ajan kendi hafızasını okur — **tasarım** |

**Kök:** hata "ölçmemek" değildi — **ölçtüm, ilk sonucu bulgu sayıp yayımladım, doğrulayıcı
ölçümü sonra koştum.** Kural 2 mekanizma *cümlesine* bakar; buradaki kusur **ölçümün kendi
artefaktıydı** (pencere/eşik/kapsam), yani cümle değil **veri** yanlıştı.

**⛔ En keskin sezgi — MUTLAK SONUÇ ÖLÇÜM HATASIDIR:** `0/37` ve `35/35` **aynı gün, aynı
soru, zıt cevap**; tek fark pencere genişliğiydi. Bir ölçüm `0`, `%100` ya da "hiç" diyorsa
**önce ölçümden şüphelen, dünyadan değil.** (Aynı aile: *bir günlük sıfır, sıfır değildir*.)

**How to apply — yayımlamadan önce, ölçüm başına bir tane:**
- **Duyarlılık:** pencereyi/eşiği değiştir, sonuç dönüyor mu? (12 kayıt → tümü: 0 → 35)
- **Tek vaka aç:** sonucun bir örneğini elle doğrula — sayım deseni gerçekten o şeyi mi sayıyor?
- **Ters yön:** [[feedback_ters-yon-kontrolu]] — ileri temizse ikizini koş.
- **Mekanizma ≠ histogram:** araç dağılımından davranış çıkarma; davranışı ayrıca ölç.
- 🔴 **Hipotezi kullanıcıya ANLATMA.** Sessizce test et, **yalnız hayatta kalanı** sun.
  *"Hipotezim çürüdü"* cümlesi hesap verme değil **gürültü** (kural 3'ün aynısı).
- 🔴 **Öneriyi kanıt seviyesine göre etiketle:** ölçülen kısım ile yargı kısmı **ayrı yazılır**.
  Yargı kısmı öneri değil **deney önerisidir** — [[feedback_dogrula-once-flag-spekulatif-blocker-yasak]].
