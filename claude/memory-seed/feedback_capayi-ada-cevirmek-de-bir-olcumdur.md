---
name: feedback_capayi-ada-cevirmek-de-bir-olcumdur
description: "Çürük satır-no çapasını AD çapasına çevirmek bir düzeltme değil YENİ BİR ÖLÇÜMDÜR — hedefi açmadan çevirirsen çürük çapayı SESSİZ YANLIŞ çapayla değiştirirsin, ki bu daha kötüdür (ölçülmüş vaka 2026-09-02)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e0774ea9-348e-4e2c-ae54-bd02ef91d832
---

**Kural:** Bir satır-no çapasını (`dosya.cds:60`) ad/kalem çapasına (*"`vbrk` join'inde"*)
çevirirken **hedefi aç ve oku**. Çevirme işlemi bir *biçim düzeltmesi* değil, **yeni bir
içerik iddiasıdır** — ve yanlış çevrilirse ortaya çıkan kayıt, düzelttiğin çürük çapadan
**daha kötüdür**.

**Neden daha kötü — asimetri burada:**
| | çürük satır-no çapası | yanlış ad çapası |
|---|---|---|
| Görünürlük | Hedef açılınca **hemen** belli olur (alakasız satır çıkar) | **Makul okunur**, alakalı bir şeyi işaret eder |
| Zamanla | Kendini ele verir (kayma büyür) | **Çürümez** — kalıcı olarak yanlış |
| Otorite | "eski, bayatlamış" diye okunur | "ölçülmüş, ada bağlanmış" diye okunur |

⇒ Satır-no çapası **gürültülü** yanlıştır; ad çapası **sessiz** yanlıştır. Sessiz yanlışı
tercih etmek bir gerileme.

**Why — ölçülmüş vaka, 2026-09-02 (ZSD001 `A-22` / EKR-04 künyesi):**
1. Bug kapısı 11 çürük satır-no çapası buldu; lider *"sayıları güncelleme, **çapayı ada
   çevir**"* dedi (doğru karar — satır-no'yu düzeltmek aynı tuzağı yeniden kurar).
2. Lider `EK-B` #29 hücresinde `` `cds/ZSD001_I_TAHSIS.cds:60` `` çapasını
   *"**başlıktaki `vbrk` inner join'inde** zaten var"* diye çevirdi — **hedefi açmadan**.
3. Ölçüm: `fk.fkart = prm.fkart` **`:62`**'de, `inner join zsd001_t_param as prm` (`:60`)
   ON'unun içinde. `vbrk` join'inin ON'u **yalnız** `on fk.vbeln = fp.vbeln` (`:57`).
   ⇒ Çeviri **yanlış**.
4. ⛔ En can alıcı kısım: **`HEAD`'deki eski hâl içerik olarak DOĞRUYDU** (*"`:60`'ta zaten
   aynı join'de"* — `:60` `prm` join'inin başlangıcı). Düzeltme, doğru bir kaydı yanlış
   yaptı. Tur **0/3 yanlıştan 1/3 yanlışa** gitti.
5. Kardeş **iki** kopya (`TS-05` #29 · aynı CDS'in kendi yorumu) **doğruyu** yazıyordu —
   yani doğru cevap zaten dosyadaydı, bakılmadı.
6. Aynı turda ikinci vaka: bir CDS yorumu *"bu dosyanın **başlığındaki** DD07T dersi"*
   dedi; ölçüm — başlık `:52`'de bitiyor, ders bloğu `:73-76`, yani **JOIN bölümünde**.
   Kalıp doğru, **konum** yanlış. Karşıt kontrol: kardeş dosyanın aynı kalıbı gerçekten
   başlıktaydı ⇒ kalıp değil **bu vaka** hatalıydı.

**How to apply:**
1. **Çevirmeden önce hedefi aç.** `sed -n '<NN>p' <dosya>` — okuduğun şey, yazacağın adın
   gerçekten karşılığı mı? Ad çapası bir **isim** değil, bir **iddiadır**.
2. **Kardeş kopyalara bak.** Aynı olgu birden çok yerde yazılıysa (kod yorumu · TS · karar
   kaydı) çoğunluk genelde doğrudur; tek başına sapan kopya **senin yazdığındır**.
3. **Ad çapası TEKİL çözülmeli.** *"başlıktaki `inner join vbrk as fk`"* ancak o metin
   dosyada **birebir** ve **tek** geçiyorsa çapadır. Sıfır ya da çoğul eşleşen ad çapası,
   satır-no çapasından iyi değildir — `grep -c` ile ölç.
4. **Konum sıfatlarını ölç:** *"başlıktaki"*, *"yukarıdaki"*, *"aynı bloktaki"* birer
   konum İDDİASIDIR. Başlığın nerede bittiğini ölçmeden *"başlıktaki"* yazma.
5. **Ordinal atıf ≠ satır-no çapası.** *"TS §5.2.7 satır 21-22"* bir **ordinal**dir;
   renumber yapılmadıysa **korunur, çevrilmez**. İkisini aynı cümlede *"ada çevrildi"*
   diye toplamak, yapılmamış icrayı beyan etmek olur
   ([[feedback_flag-degil-icra-bekleyen-is-kapat]] sınıfı — aynı turda o da yaşandı).
6. Düzeltme turu bittiğinde **kapı aç** — bu vakayı yakalayan şey ikinci kapıydı, birinci
   kapı değil ([[feedback_duzeltme-turu-kendi-regresyonunu-uretir]]).

**Ayırt edici:** [[feedback_kanit-yeniden-uretilebilir-bicimde-yazilir]] çapanın **çürümesini**
anlatır (*"satır no verme, komut/alıntı ver"*); bu kayıt **çürüğü onarma anını** anlatır —
onarımın kendisi ölçülmemişse yeni ve daha sinsi bir yalan üretir.

İlgili: [[feedback_karar-degisince-kaydi-ayni-turda-guncelle]] ·
[[feedback_kapi-kosarken-dosya-donar-md5-teyidi]] · [[feedback_ters-yon-kontrolu]] ·
[[feedback_kopya-sayimi-tek-sozdizimi-desenine-dayanma]]
