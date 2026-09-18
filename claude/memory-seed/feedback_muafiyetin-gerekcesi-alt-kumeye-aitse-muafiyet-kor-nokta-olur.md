---
name: muafiyetin-gerekcesi-alt-kumeye-aitse-muafiyet-kor-nokta-olur
description: "Bir kapının bilinçli muafiyeti gerekçesinden GENİŞ yazılmışsa (dosya-bazlı muafiyet, gerekçe yalnız o dosyanın bir bölümü için geçerli) muafiyet kör noktaya döner ve dokunulmazlığı yüzünden en uzun yaşayan kör nokta olur — düzeltmenin AÇIKLAMA metni bile o boşluktan sızabilir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 983e6e2d-a02a-440c-8a2c-6e3d0fb4a0f2
---

Bir kapı/validator bir dosyayı **bilinçli olarak** muaf tutuyorsa, muafiyetin **gerekçesinin
kapsamı** ile **muafiyetin kapsamını** ayrı ayrı sor. Gerekçe çoğu zaman dosyanın bir
**alt-kümesi** için geçerlidir; muafiyet ise **dosyanın tamamına** yazılır. Aradaki fark
kör noktadır — ve *bilinçli* olduğu için kimse ona bakmaz.

**Vaka (2026-09-18, Q329):** public çekirdeğin kimlik-sızıntı kapısı (`core_precommit.py`)
kendi desen-sözlüğü dosyalarını `SCAN_EXEMPT` ile taramadan muaf tutuyordu. Gerekçe yazılıydı
ve **doğruydu**: *"kendileri desen tanımlar"* — dosya kendi deseninde boğulurdu. Ama gerekçe
yalnız **desen literalleri** için geçerliydi; muafiyet **dosyanın tamamını**, yani
**düz-yazı yorum ve docstring'leri de** kapsıyordu.

Ölçüm: o üç dosyanın yorumlarında **8 gerçek kimlik izi**. En eskisi **38 gündür** public
repoda. ⭐ **Dördü aynı gün girmişti** — hem de bir sızıntı temizliğinin (PR #265) **17 saat
sonrasında**, *"bu ad allowlist'e ALINMADI çünkü gerçek bir müşteri paketidir"* diyen
**gerekçe yorumlarının içinde**. Karar doğruydu; kararı **anlatan metin** sızıntıydı.

⛔ **İki alt-ders:**
1. **Düzeltmenin açıklaması da taranan yüzeydir.** "Şu gerçek adı allowlist'e almadım" demek
   için o adı yazmak zorunda değilsin; tarif yeter (*"Q326'nın jenerik saydığı 4 harfli ad"*).
2. **Muafiyeti kapanış ölçümü yakaladı, denetim değil.** Bulgu, Q327'ye *"sızıntının yaşı"*
   eklenirken koşulan `git log -S<ad>` çıktısının **beklenen iki commit yerine üç** dönmesiyle
   doğdu. Kapanış kaydını *ölçerek* yazmak, kapanmadığını gösterdi.

**Why:** Kapsam eksikliği (desen dar, liste kısa) er geç bir FP/FN'le görünür hale gelir.
Bilinçli muafiyet görünmez: gerekçesi yazılı olduğu için okuyan kişi *"burası bilerek böyle"*
deyip geçer. Bu yüzden muafiyet, aynı kapının **en uzun yaşayan** kör noktasıdır.

**How to apply:** Bir muafiyet satırı gördüğünde (`SCAN_EXEMPT`, `ALLOWED_TOKENS`, `# noqa`,
`exclude:`, `.gitignore` istisnası) şunu sor: *gerekçe dosyanın NERESİ için geçerli, muafiyet
NERESİNİ kapsıyor?* Fark varsa ölç — muaf yüzeyi kapının **kendi fonksiyonlarıyla** elle tara
ve **pozitif kontrol** koy (sentetik bir vaka hâlâ yakalanıyor mu), yoksa "0 bulgu" kör
taramadan ayırt edilemez. Daraltma adayları: muafiyeti **satır/token bazlı** yap, ya da
kaldırıp gerçek literalleri var olan token-allowlist mekanizmasına gerekçeli ekle.
Kıyas için: [[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] ·
[[feedback_tek-seferlik-script-paylasilan-modulun-desenini-yeniden-turetmez]]
