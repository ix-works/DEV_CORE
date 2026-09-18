---
name: cok-parametreli-shlp-ilk-alan-devralma
description: "F4 devralma AD-BAZLIDIR ('ilk parametre gelir' YANLIŞ — ölçüldü+canlı test); asıl tuzak: düzeltme sonrası testin kapanışı yazılmayınca eski kusur aylarca 'açık' sanılır"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2caf4c00-51c1-475d-9676-09ad5b0e676b
---

**Düzeltilmiş kayıt (2026-08-17).** Klasik dynpro alanına bağlanan standart arama
yardımında, seçilen satırdan hangi değerin ekran alanına yazılacağı **ad-bazlı** belirlenir:
DDIC yapı tanımındaki `with value help <shlp> where <param> = <yapı>.<alan>` bloğu, attachment
tablosunda (`DD36S`, `SHTABLE`/`SHFIELD` kolonları) **isimle** kaydedilir. SHLP'nin kendi
arayüz sırası (`DD32S-FLPOSITION`) dönüş hedefini **belirlemez**.
⇒ *"Çok alanlı arama yardımında ilk parametre devralınır"* iddiası **YANLIŞTIR** — bu kaydın
ilk sürümü bu yanlışı taşıyordu, ölçüm ve canlı test çürüttü.

**Vaka ve asıl ders:** <PAKET-G>'nin depo yeri F4'ü uzun süre "seçince üretim yeri geliyor,
düzeltemedik" diye biliniyordu. Ölçüm: eşleme canlıda **doğru** (`LGORT`→`VER_LGORT`,
`WERKS`→`VER_WERKS`). Kullanıcı testi (2026-08-17): **F4 doğru çalışıyor, kusur yok.** Hata
çoktan düzeltilmişti; ama düzeltme sonrası GUI testi SESSION_NOTES'ta *"yarına devir"* diye
kuyruklanıp **hiç tarihli/sonuçlu kapatılmamıştı** ⇒ ekip aylarca kusuru açık sandı, üstüne
yeni kural üretildi.

**How to apply:**
1. **Kapanışı yaz.** Bir düzeltmenin son doğrulaması (özellikle regen/aktivasyon sonrası GUI
   testi) **tarihli ve sonuçlu** kapatılmazsa, kusur kayıtta sonsuza kadar açık kalır. "Yarına
   devir" bir kapanış değildir.
2. **Hatıra hipotezdir, kural değil.** Kullanıcının/notların "şu bozuktu" beyanı ölçülmeden
   kurala dönüştürülmez — özellikle mekanizma iddiası içeriyorsa (bkz. bu kaydın ilk sürümü).
3. **Metadata doğru ≠ runtime doğru; ama runtime yanlış sanısı da ölçülmeden yayılmaz.** İkisi
   arasında karar veren tek şey **taze, tarihli canlı test**tir.
4. **DDIC-attachment yolu kullanılabilirdir** (bu vakayla uçtan uca doğrulandı). PATTERN #23'ün
   gerçek tuzakları geçerli kalır: ekran alanındaki elle `MATCHCODE` attachment'ı **ezer**;
   DDIC değişince ekranın **regen** edilmesi gerekir. Popup yolu ise değer kümesinin **iş
   kuralıyla süzülmesi** gerektiğinde tercih edilir (ör. stok bazlı parti listesi) — mekanizmaya
   güvensizlikten değil.

İlgili: [[feedback_f4-arama-yardimi-tasarim-asamasinda-kurgulanir]] ·
[[feedback_dogrulama-sezgileri-dort-kural]] · `core/playbook/lessons-learned.md` PATTERN #23 ·
`core/playbook/howto-classic-dynpro-datafield-screens.md` §1-§2 ·
`<PAKET-A>/ref_docs/RESEARCH-07-SHLP-PARAMETRE-ESLEME.md`.
