---
name: feedback_edi-tasariminda-otorite-orijinal-mesaj-dosyasi
description: "EDI/CPI tasarımında otorite ORİJİNAL MESAJ DOSYASI + .mmap kuralıdır — SAP DEV'deki IDoc'lar test verisi taşır, tasarım onlardan türetilmez"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6feb8323-f0ff-4176-b8f5-f633eb79f129
---

EDI/CPI işinde bir alanın "doğru değeri" **orijinal müşteri mesaj dosyasından** ve
**mapping kuralından (`.mmap`)** okunur. SAP'deki IDoc'lar bu amaçla **otorite DEĞİLDİR**.

**Why:** Çalışma sistemi (DEV) bir **test** sistemidir. Mapping geliştirme turlarında
onlarca deneme mesajı işlenir; IDoc'ların bir kısmı yanlış/eksik veri taşır. Dahası
IDoc, mapping'in ÇIKTISIDIR — mapping kusurluysa IDoc kusuru sadakatle yansıtır ve
"canlı ölçüm" görüntüsü altında yanlış tasarıma götürür.

2026-09-07 (<PROJE> ZSD001/<MUSTERI-A>): bu kural bir oturumda **3 kez** ihlal edildi.
Sonuç: (1) "mesaj boşaltma noktası taşımıyor" — yanlıştı, mesaj `LOC+11` taşıyor,
`E1EDKA1/ABLAD` **maplenmemiş** olduğu için IDoc'a geçmiyordu; (2) "248 planın `BSTKD`'si
yanlış, düzeltilmeli" — orijinal dosyalara göre **294 planın 294'ü doğruydu**; üretilen
düzeltme listesi silindi. Gerçek kusur mapping'deydi: kalem düzeyindeki `RFF+ON` başlık
segmentine basıldığı için tek sözleşme numarası tüm IDoc'a yayılıyor ("yanlış çift").
Kullanıcı kuralı hatırlattığında ölçüm 10 dakikada tersine döndü.

⛔ **NÜKS DESENİ (4. ihlal, aynı gün):** kural "tasarım kurarken" diye okunup
**teşhis/anomali avı muaf** sanıldı. `205480` planı termin satırsız güncelleyince
IDoc segmentleri kazılmaya başlandı (`E1EDP16`, `PRGRS`, docnum ikili araması,
`EDIDC` partileri, domain değerleri). Cevap ilk adımda otoritedeydi: canlı mmap'te
`E1EDP16/PRGRS` **tek brick, `const 'D'`**; eski sürüm V2 `'1'` basıyordu ⇒ o IDoc
hatalı turdan kalmadır, kurcalanacak bir şey yoktur. Yapılan onlarca sorgu tasarıma
**sıfır** katkı verdi. Kullanıcı: *"yine idoc lardaki dataya göre iş yapmaya başladın"*.

⛔ **NÜKS 5 (2026-09-14, ZSD000 IDoc data modify):** bu sefer ihlal **brifingde** doğdu — lider,
"deneme işe yaradı mı / grup hazır mı" sorusu için ajana EDIDC/EDIDS durum dağılımı, `V4 015`
sayısı ve örnek IDoc analizi yazdırdı (~50 IDoc örneklendi). Kullanıcı: *"sistemdeki idoclara
göre iş yapma, deneme idocları test idocları vs. bir çok idoc var. takılma onlara"*. Deneme
sonucunu kullanıcı zaten biliyordu ([[feedback_kullanicinin-bildigi-is-gercegini-olcmek-yerine-sor]]).

**How to apply:**
- ⭐ **Brif yazarken de kontrol et:** brifte `EDIDC`/`EDIDS`/`EDID4` istatistiği, "IDoc örneği",
  "durum dağılımı" geçiyorsa DUR — o soru ya kullanıcıya sorulur ya mmap/orijinal dosyadan ya da
  ana veri/uyarlamadan (T661W, T663A, VBAK) cevaplanır. IDoc sayımı "etki/başarı" kanıtı DEĞİLDİR.
- **Kural teşhiste de geçerlidir.** "Şu IDoc neden böyle davrandı?" sorusu, IDoc'u
  otorite yapmaz. Önce sor: *bu sorunun cevabı mmap'te veya orijinal dosyada var mı?*
  Varsa oradan al ve DUR — segment arkeolojisine girme.
- **Tek IDoc'un sapması nüfus bulgusu DEĞİLDİR.** Bir IDoc beklenmedik davrandığında
  varsayılan hüküm "bayat/hatalı turdan kalma"dır; aksini iddia etmek için önce
  mmap+orijinal dosya çelişkisi gösterilir.
- **Çıkış kapısı koy:** mmap kuralı sorunu açıkladığı anda ölçümü bitir, rapor et.
  Sonraki sorgu ancak kullanıcı isterse koşulur.
- Bir EDI alanının doğru değerini sormadan önce **ham mesaj klasörünü bul** (<MUSTERI-A>:
  `gen/gate_realdata.py` içindeki `VARSAYILAN_SRC`; ortam değişkeniyle ezilebilir).
  Ayrıştır, mmap kuralıyla eşle, SONRA konuş.
- IDoc'u yalnız **doğrulama** için kullan: "mapping bu değeri doğru mu taşımış?" — asla
  "doğru değer nedir?" için.
- IDoc ile orijinal dosya çeliştiğinde varsayılan hüküm: **mapping kusuru**, veri değil.
- Karşıt kontrol kur: aynı alanı DOLDURAN çalışan bir müşteri var mı (<MUSTERI-A> `E1EDP10/VTRNR`
  0/336 ↔ <MUSTERI-D> 198/198 ⇒ kusur <MUSTERI-A> mapping'inde).
- Bir hedef alanın mmap'te **hiç bulunmaması** da bir bulgudur; "boş geliyor" ile
  "maplenmemiş" AYRI şeylerdir ve ayırt edilmeden teşhis yazılmaz.

İlişkili: [[feedback_kardes-artefakt-benzerligi-kip-semantigini-kanitlamaz]] ·
[[feedback_sonucu-olc-uygulamayi-degil]] · [[project_dev-sistem-prd-tasima-kullanici-talimati]] ·
[[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]]
