---
name: feedback_kapi-zinciri-derlemeyi-gormez
description: Kapi zinciri PASS, artefaktin CALISTIGI degildir - ABAP'ta DERLEMEYI, UI5'te RENDER'i gormez; ikisinde de otorite gercek calistirmadir
metadata:
  type: feedback
---

`check_abaplint` tuned kural setinde **`check_syntax` KAPALI** ⇒ ad/tip
çözümlemesi yapılmaz. Validator bunu kendi çıktısında yazıyor:
*"bu sonuç DERLEME KANITI DEĞİLDİR (otoriter syntax: adt_syntax_check)"*.

**Ölçülmüş vaka (2026-08-30, `ZCL_SD022_IDOC_PARSER`):** 4 kapı turu +
abaplint + `run_all_validators` hepsi yeşilken gateway push'unda **iki ayrı
aktivasyon hatası** çıktı:
- `ty_s_err_id` **PRIVATE**'ta tanımlı ama **PROTECTED** imzada kullanılıyor
  (hem bildirim sırası hem görünürlük ihlali),
- test sınıfında `iv_msgno = space` — CHAR literali **NUMC 10** formal
  parametreye uymuyor (türev olarak aynı çağrıdaki `DATA(...)` satır-içi
  bildirimleri de "unknown" hatası verdi; **tek düzeltme üçünü kapattı**).

**Sonuç — planlamaya etkisi:** kapı PASS'i "aktive edilmeye hazır" demek
değildir. Yeni/büyük bir sınıfta gateway turunu **tek seferlik** varsayma;
1-2 iterasyon normaldir. Gateway'e *"hata çıkarsa DUR, kaynağa dokunma,
bana getir"* talimatı ver — düzeltme lider/uzman işidir, tek yazıcı
kuralı korunur.

**Ucuz ön-tarama (lider yapabilir):** sınıf tanım bölümünü ayrıştırıp her
yerel `ty_*`/`c_*` için (a) ilk kullanım < bildirim satırı, (b) PRIVATE'ta
bildirilip PUBLIC/PROTECTED imzada kullanım — ikisini de tara. Ayrıca
**formal parametreye literal** geçen yerleri ayır (atama ≠ parametre
bağlama; ABAP yalnız ikincisinde sıkı tip denetler).

Bkz. [[feedback_exit0-degil-cikti-kaniti]] ·
[[feedback_yesil-sinyalin-kapsamini-sor]] ·
[[feedback_abaplint-parser-error-gercek-olabilir]] ·
[[feedback_source-based-class-type-c-trap-ve-vague-scan-bisect]]

---

### ⭐ AYNI SINIFIN FRONTEND HALI: kapi zinciri **RENDER**'i da gormez (2026-09-05, olculdu)

Yukarisi ABAP/derleme. Ayni mekanizma UI5'te **daha sinsi** bicimde tekrarladi.

**Olculmus vaka — ZSD001 `volvo_beyan`:** iki rota (`lots`/EKR-03, `alloc`/EKR-04)
tarayicida **BOMBOS** aciliyordu. Konsol: `failed to load 'sap/m/layoutData.js'` →
`The following error occurred while displaying routing target with name 'lots'`.
Kok neden: `<layoutData>` agregasyon etiketi **ondeksiz** yazilmis, yani view'in
varsayilan namespace'i `sap.m`'e dusmus; ebeveyni `<l:Splitter>` ise `sap.ui.layout`'ta.
`XMLTemplateProcessor.js:1452-1453` agregasyonu **ebeveynle ayni namespace** sartina
bagliyor ⇒ eslesmeyince UI5 onu KONTROL sanip `sap/m/layoutData.js` modulunu ariyor → 404 → view coker.

**Neden hicbir kapi gormedi — yapisal, kusur degil:**
- XML **gecerlidir**; iyi-biciml. testi gecer. Hata sozdizimsel degil **ANLAMSALDIR**.
- `node --check` JS'e bakar, view'a bakmaz.
- `check_ui5_freestyle_traps` / `check_list_view_grid` / `check_filter_search_pattern`
  desen tarar; namespace↔agregasyon eslesmesini **hic sorgulamaz**.
- Uc bagimsiz `bug-expert` kapisi bu iki ekrani inceledi ve **ucu de** raporunun sonuna
  *"calisma zamani OLCULMEDI"* serhi dustu — gorev sinirlari geregi hakliydilar.
⇒ Yesil kapi zinciri + "hazir" beyani + gecerli XML = **acilmayan ekran**.

**Kural:** bir ekran, **gercekten ACILIP render edildigi** gorulene kadar "hazir" DEGILDIR.
Beyan (uretici), statik kapi (validator) ve adversarial inceleme (bug-expert) ucu birden
yesil olabilir; ucu de bu sinifi **yapisal olarak** goremez.
⇒ UI turu bitince **ZORUNLU son adim:** her manifest route'unu tarayicida ac + konsolu oku.
Maliyeti dakikalar, yakaladigi sey BLOCKER. (Bu vakada 6 rotanin 2'si oluydu; oteki 4'u
kontrol grubu olarak ayni turda olculdu.)

**Ucuz sinif taramasi (lider yapabilir, saniyeler):** tum UI XML'lerini ayristir; kucuk
harfle baslayan her etiket bir agregasyondur — `childNode.namespaceURI != parent.namespaceURI`
olanlari listele. Olcum: 129 dosya / 1493 agregasyon etiketi → 40 uyusmazlik, 38'i OData
`$metadata`'daki `<atom:link>` (yanlis-pozitif), **gercek vaka tam 2**. Yani tarama
gurultusu dusuk, sinyali yuksek.

**Genel ders (ikisini birlestiren):** kapi zinciri artefaktin **SEKLINI** dogrular,
**CALISTIGINI** degil. ABAP'ta bunun otoritesi `adt_syntax_check`/aktivasyon; UI5'te
**tarayici**. Kapi PASS'ini "calisiyor" diye okumak, [[feedback_exit0-degil-cikti-kaniti]]
dersinin bir ust katmandaki hali.

---
**Son-dogrulama:** 2026-09-05 (ders yazim tarihi — o gunden beri YENIDEN OLCULMEDI) · **Applies-to:** bu cekirdegi kullanan tum projeler

⚠ **ARAC IDDIASI** — bu ders *"bugun su arac/kapi boyle davraniyor"* der, yapisal bir olgu
degil. Arac surumu degismis olabilir: davranisa **dayanmadan once bir kez olc**. (Vaka: bir
kardes ders, dayandigi kusur duzeltildikten sonra 3 hafta bayat yasadi; tohuma alinmadan
once olculup elendi.)
