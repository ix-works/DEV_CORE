---
applies_to: [all]
---
# HOWTO — Silme Kontrolü (delete guard): backend kuralından kullanıcının gördüğü mesaja

> **Ne zaman oku:** bir kaydın "neden silinemediği" kullanıcıya anlatılacaksa; RAP `validation ... on save { delete; }` yazarken; bir FE silme akışına dokunurken.
> **Kaynak:** gerçek bir turdan (2 gün, 7 app, 13 BE guard, 6 bug-gate turu). Her madde yaşanmış bir vakadır.
> `applies_to: ecc, s4_private, s4_public, btp_abap` (RAP maddeleri s4_*/btp; FE maddeleri freestyle UI5 + OData V2)

---

## 1. Guard 5 KATMANDIR — biri eksikse kural ÖLÜ KODDUR

```
(1) BE validation VAR mı
 → (2) BDEF'te KABLOLU mu  (validation <ad> on save { delete; })
 → (3) DOĞRU ENTITY'de mi  (root vs child)
 → (4) mesaj BELGE NO taşıyor mu (ve tavana sığıyor mu)
 → (5) FE o yola GİDİYOR mu / mesajı BASIYOR mu
```

**Vaka:** 13 guard canlıydı, hepsi kablolu, mesajları belge numaralıydı — **ama kullanıcı hiçbirinde
numarayı görmüyordu**, çünkü FE (5) katmanında backend'i **hiç çağırmıyordu**.
→ *"Backend doğru"* ≠ *"kullanıcı görüyor"*. **Kabul ölçütü kullanıcının gördüğü metindir.**

---

## 2. FE kapısı ≠ iş kuralı — iş kuralı TEK KAYNAKTA (backend)

FE'de "sil'e basmayı engelleme" ön-kontrolü üç hasar verir:
1. **Backend'i kısa devre yapar** → gerçek mesaj hiç üretilmez, BE kuralı **ulaşılamaz kod** olur
2. **Bayat veriye dayanır** — sayaç liste yüklenirken okunmuştur; sonra kayıt eklenirse yanlış karar
3. **Mesajı ikiye böler** → iki yerde bakım, kaçınılmaz drift

**KAPI DEĞİLDİR (kalmalı, kaldırma):** satır-seçim kontrolü ("önce satır seç") · düzenleme-modu
(`enabled="{ui>/editable}"`) · kilit (`!readOnly`) · veri-kaybı guard'ı (`_hasPendingChanges`) ·
gösterim affordance'ı (ilişkili kayıt yoksa "Göster" butonunu gizlemek).

---

## 3. ⛔ FE kapısını KALDIRMADAN ÖNCE backend karşılığını DOĞRULA

**Kapı kaldırmak = koruma silmek**, arkasında BE kuralı yoksa.

**Vaka (lider hatası):** bir "Sil" butonunun bayat sayaca dayanan kapısı kaldırılacaktı; gerekçe
*"backend zaten reddeder"*di. Ölçüldü: ilgili BDEF alt-bloğunda `delete;` **vardı** ama
**validation YOKTU**. Kaldırılsaydı silme **sessizce başarılı** olacak, bağlı kayıt yetim kalacaktı.

**Kontrol listesi (dördü de EVET olmalı):** validation var mı · **doğru entity'de mi** ·
`on save { delete; }` ile kablolu mu · mesajı belge numarası taşıyor mu.
Biri bile HAYIR → **kapı KALIR**, önce BE kuralı yazılır.

⚠ **Kandırıcı komşu kurallar.** Root entity'yi koruyan bir validation child'ı korumaz;
`on save { create; update; }` delete'i kapsamaz. *"Bu alanda bir validation var"* yetmez —
**hangi entity, hangi tetikleyici** sorusu cevaplanmalı.

---

## 4. `delete;` olup validation'ı olmayan her entity = korumasız yol → ENVANTER ÇIKAR

BDEF taraması bir kerelik envanterdir. Entity bazında matris:

| entity | `delete;` var mı | validation var mı | kablolu mu | handler (dosya:satır) | mesaj belge no taşıyor mu | canlıda aktif mi | tüketen UI app |
|---|---|---|---|---|---|---|---|

Örnek sonuç (bir pakette): **19 entity `delete;` taşıyor → 13 korumalı, 6 korumasız.**
Korumasızların her biri için **veri kaybı senaryosunu SQL ile doğrula** (hangi tablo hangi alan
üzerinden yetim referansa düşer) — "teorik risk" yazma, ölç.

---

## 5. Cascade delete child validation'ı tetikler mi — **BO BAZINDA ÖLÇÜLÜR, GENELLENEMEZ**

**Vaka:** bir BO'da "cascade'de kalem validation'ı tetikleniyor" ölçümü kayıtlıydı. Başka bir BO'nun
kökü için **aynı şey varsayıldı** — o BO'da hiç ölçülmemişti.
→ Bir BO'daki ölçümü diğerine taşıma. Her BO için ayrı runtime testi.
⚠ **Kesin boşluk her hâlükârda var:** 0 kalemli bir başlıkta tetiklenecek child guard yoktur.

---

## 6. RAP mesajı 50 KARAKTERDE SESSİZCE KESİLİR → belge no ÖNEKTEN HEMEN SONRA

`new_message_with_text` ile üretilen metin OData yüzeyine **tam 50 karakterde kesilerek** çıkıyor
(canlı ölçüm). Kesme hem `error.message.value` hem `errordetails[].message` alanlarında →
**payload'ın hiçbir yerinde tam metin yok**, FE kurtaramaz.

**Kural:** belge numarası mesajın SONUNA değil **öneğin hemen ardına** konur; toplam uzunluk
**hesaplanır** (sabit "ilk 3" varsayımı yok); sığmayan adet `+N` ile **GÖRÜNÜR** yapılır —
**sessiz kırpma yok**.
**Önek bütçesi ≤ 34** = 50 − 1 (boşluk) − 10 (belge no) − 1 (boşluk) − 4 (`+999`).

**Birim testi İKİ sözleşmeyi de kanıtlamalı:**
1. **UZUNLUK** — her N için metin ≤ 50
2. **FAYDA** — bir numara sığıyorsa metinde **GERÇEKTEN görünüyor** (kullanılan her önek × birkaç N)

> Yalnız (1) test edilirse **numarasız** bir mesaj da yeşil geçer — oysa biçimin asıl amacı numaraydı.

---

## 7. FE-08 — LİSTE DARALINCA/YENİDEN SIRALANINCA SEÇİM BAYATLAR → YANLIŞ KAYIT SİLİNİR

**Mekanizma:** `setData` / binding refresh → satırlar **yeniden indekslenir**.
- `sap.m.Table`: `rememberSelections` **varsayılan true** → seçim binding-context yoluyla geri yüklenir
- `sap.ui.table.Table`: seçim **indeks-bazlı** (`getSelectedIndex()` / `getSelectedIndices()`),
  kayıt `aList[iIdx]` ile okunur
→ A silinince B "seçili" görünür → sonraki Sil **YANLIŞ kaydı** siler.

**Çözüm — çağrı yerlerine DAĞITMA, ortak GİRİŞ NOKTASINA al:**
```js
_reload: function () {
    this._clearSelection();   // <-- burada; tüm çağrı yolları otomatik kapanır
    ...
}
```
Ölçülen kazanç bir turda: **7 dağıtık temizleme → 2 giriş noktası**, net kod azalması.

**Dikkat edilecekler:**
- **Sınıf sınırı:** `Child._reload` girişine koyup `Parent._reload`'a koymamak, değişmezi tek sınıfta
  bırakır → `Parent`'a ileride eklenecek çağrı guard'sız kalır. Maliyeti bir no-op satır.
- **Giriş-guard'ı, o fonksiyondan GEÇMEYEN yolu kapsamaz.** Modeli doğrudan güncelleyen bir başarı
  yolu varsa oradaki temizlik **kaldırılmamalı** (asimetrik görünür, sebebi gerçektir). *"Bu yol
  gerçekten o fonksiyondan geçiyor mu"* → ölç, varsayma.
- **API:** `sap.ui.table.Table` → `clearSelection()` · `sap.m.ListBase` → `removeSelections(true)`.
  `bAll=true` **şart**: hatırlanan seçim kümesini de siler, yoksa `setData` sonrası seçim geri gelir.
- ⛔ **`rowsUpdated`'a BAĞLAMA.** `sap.ui.table` onu `VerticalScroll` · `FirstVisibleRowChange` ·
  `Resize` · `Zoom` · `Render` sebepleriyle de fırlatır → **scroll ederken ve pencere boyutlanırken
  seçim silinir** = yeni regresyon.
- **Zamanlama:** auto-refresh (`refreshAfterChange`) senkron bir çağrı değil → temizliği
  `remove()` sonrasına değil **`success` callback'ine** koy.
- **Item tablosu dışını da tara:** ilişkili-kayıt/atama/konteyner tabloları da seçim-bazlı silme
  yapıyor olabilir. Ve **listeyi yeniden SIRALAYAN** her yer (filtre+yeniden-ekle) aynı sınıftadır.
- **Grid'in native kolon-menüsü sort/filter'ı** binding'i app kodundan geçmeden yeniden kurabilir —
  personalizer/util katmanı varsa o yol ayrı değerlendirilir.

> Bu sınıfın bir turda **7 varyantı** çıktı ve hiçbiri ilk gün görünmüyordu.

---

## 8. Model-only silme → ANINDA DB SİLME dönüşümü YENİ BİR SÖZLEŞME AÇAR

**Öncesi:** silme yalnız client model'den çıkarıyordu, gerçek DELETE `onSave` diff'indeydi →
kullanıcı kaydetmeden çıkarsa **hiçbir şey olmamıştı** (geri alınabilir).
**Sonrası:** silme **anında ve geri alınamaz**. Bu üç şeyi zorunlu kılar:

1. **Pending-change guard'ı TÜM düzenlenebilir alanları kapsamalı — BAŞLIK DAHİL.**
   Kapsamazsa: kullanıcı başlığı değiştirir → kalem siler → `_reload()` başlığı DB'den geri kurar
   → **düzenleme sessizce kaybolur**, tek geri bildirim başarı toast'ıdır.
2. **Detektör `onSave` MERGE payload'ıyla 1:1 olmalı.** Payload'da olup detektörde olmayan her alan
   = sessiz veri kaybı. **App'ler arası kopyalama YASAK** — her app'in kendi payload'ından ve kendi
   view'ındaki düzenlenebilir kontrollerden ölç. (Bir turda: app A 4+3 alan, app B/C 3+2, app D/E 3+1.)
3. Kullanıcının *"Kaydet'e basmadan hiçbir şey yazılmaz"* zihin modeli kırıldığı için
   *"demek diğerleri de işlendi"* varsayması **makul** hâle gelir → tuzak daha keskin.

**Kıyas ipucu:** alan listesini kıyaslarken tarih için **epoch normalizasyonu** (`+new Date(v)`)
şart — DatePicker `dateValue` **Date nesnesi** verir, ham `!==` referans kıyası yapıp eşit tarihte
bile `true` der. Boolean için `!!` (Edm.Boolean `undefined` vs `false`).

---

## 9. PARALEL `remove` = KİLİT ÇAKIŞMASI (`useBatch:false` ise)

`Promise.all(ops)` + `new Promise` executor'ı **senkron** → istekler push anında uçar.
`useBatch:false` → changeset yok → **kısmi silme mümkün**, paralellik gerçek ağ paralelliğidir ve
aynı BO'da kilit çakıştırır. → **Sıralı çalıştır** (thunk + sıralı koşucu).

⚠ **Thunk'a çevirirken KAPANIŞ TUZAĞI:** build anında hesaplanan değerler thunk'ın **içine**
alınırsa final değere kayar. Vaka: `ItemNo: ("00000"+maxNo).slice(-6)` içeri alınsaydı birden çok
yeni kalem **AYNI anahtarla** create edilecekti. → Değeri **build anında sabitle**.
📌 Bilinçli sonuç: sıralıda ilk hatadan sonraki op'lar çalışmaz (paralelde hepsi denenirdi).

---

## 10. Hata mesajı parser'ı ÇOK SATIRLI olmalı

Bir validation **birden fazla engeli aynı anda** raporlayabilir (`innererror.errordetails[]`).
Yalnız `error.message.value` okuyan parser ikinci satırı **yutar**.
→ Ana mesaj + `errordetails[]` birleştir; `severity` alanı **yoksa atlama** (Gateway bazen göndermiyor);
mükerrer satırı ele; çözümlenemezse jenerik mesaja düş (fallback'i koru).

⚠ **Paylaşılan util'i TEK TÜKETİCİ için DEĞİŞTİRME.** Önce `where-used` çıkar; başka çağıranı varsa
yalnız **çağrı yerini** yeni parser'a çevir. (Vaka: util'in ikinci bir çağıranı vardı; ayrıca kardeş
app'te **ayna kopyası** bulunuyordu — birini değiştirmek ikisini ayrıştırırdı.)

---

## 11. i18n — eksik anahtar = kullanıcıya bozuk dil

Yerelleştirilmiş bundle (`i18n_<lang>.properties`) **kısmi override** olabilir; eksik anahtar base'e
düşer. Base **ASCII-translit** ise kullanıcı **diyakritiksiz** metin görür.
**Vaka:** silme onay dialogu `Secili 1 kalem silinsin mi?` olarak çıkıyordu; aynı yerde kardeş app
doğruydu. Ayrıca base'de bir **yazım hatası** vardı — 6 bug-gate turu, `node --check`, grep ve
kablolama doğrulaması bunu **göremezdi**; ancak ekranda görülünce çıktı.
→ Silme/onay/uyarı metinleri **her iki dosyada** olmalı.
→ Kardeş app'ten metin **kopyalamadan önce anlamını kontrol et** — aynı anahtar farklı app'te farklı
ifade taşıyabilir (kopyalamak o app'in dilini bozar).
→ `{0}` placeholder kümeleri base ↔ override **birebir** olmalı; MessageFormat'ta tek-apostrof tuzağı.

---

## 12. KABUL ÖLÇÜTÜ — statik doğrulama runtime'ın YERİNE GEÇMEZ

Bir turda: `node --check`, grep, kablolama doğrulaması, **6 bug-gate turu** — hepsi geçti.
Runtime testinde yine de yeni kusur çıktı (bozuk dil + yazım hatası), ve asıl kabul kanıtı
("mesaj **silme anında** ve **belge numarasıyla** çıkıyor") ancak tarayıcıda alındı.

**Silme akışı için minimum runtime test seti:**
1. Engellenmesi **kanıtlı** bir kayıtta silme → mesaj görünüyor mu · **belge numarası var mı** ·
   uzunluk tavanın altında mı · **silme anında mı** (kaydetme anında değil)
2. **Seçim regresyonu:** silme/reddi sonrası grid'de satır **seçili kalıyor mu** →
   `getSelectedItems().length` / `getSelectedIndices()` ile **sayıyla** doğrula, gözle değil
3. **Pending guard:** düzenle → kaydetme → sil → uyarı çıkıyor mu · **düzenleme korunuyor mu**
4. Her denemenin **önü ve ardı** DB sorgusuyla doğrulanır — "veri değişmedi" iddiası ölçülür

⛔ **Test verisi YARATMA.** Engellenecek kayıt yoksa *"DOĞRULANAMADI (sebep)"* yaz — bu değerli
bilgidir, eksiklik değil.
⛔ **Engellenmesi kanıtlanmamış bir kayıtta silme DENEME.** Guard'ın canlıda **var, güncel ve
kablolu** olduğu doğrulanmadan gerçek silme denemesi yapılmaz — guard eski sürümdeyse silme
**başarılı olur** ve kayıt geri alınamaz.

---

## 13. ARAÇ SINIRI ≠ YOKLUK (bu konuda üç kez ısırdı)

- **Behavior pool'un `source/main`'i BOŞTUR.** `adt_get(class)` / `adt_grep_source` onu çeker →
  CCIMP araması **0 eşleşme** döner. Bu **"metot yok" DEĞİLDİR**. CCIMP `includes/implementations`'tan
  ham GET ile çekilir. (Ölçüm: `main` 166 bayt, `implementations` 21.264 bayt.)
- `adt_lock_check` bazı obje tiplerini desteklemez → "kilit yok" demek değil, **araç sınırı**.
- **Genel kural:** bir araç boş döndüğünde önce **aracın kapsamını** doğrula, sonucu "yok" diye yazma.

📖 İlgili: `adt-classes.md §24.8` (test include'u POST≠PUT) · `ui-freestyle-odata-v2.md` ·
`ui-backend-rap.md` · `lessons-learned.md` (süreç dersleri)
