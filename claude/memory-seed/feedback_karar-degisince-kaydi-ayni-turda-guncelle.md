---
name: feedback_karar-degisince-kaydi-ayni-turda-guncelle
description: "Kullanıcı kararı değişince/genişleyince karar KAYDINI AYNI TURDA güncelle — güncellenmemiş kayıt, alt-ajanın gözünde OTORİTEDİR ve doğru bulgusunu geri çektirir (ölçülmüş vaka 2026-09-02)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e0774ea9-348e-4e2c-ae54-bd02ef91d832
---

**Kural:** Bir kararı belgeye (`EK-B`, `RESUME`, `TS`) yazdıktan **sonra** kullanıcı o kararı
değiştirir ya da genişletirse, kaydı **aynı turda** güncelle — alt-ajana yeni kararı
`SendMessage` ile bildirmek **yetmez**. Ajanlar kaydı **bağımsız kanıt** olarak okur; bayat kayıt
onların gözünde **senin mesajından daha otoriterdir** (çünkü belgedir, konuşma değil).

**Why — ölçülmüş vaka, 2026-09-02 (ZSD001 `A-22` / `D-R63`):**
1. `K2`/`K3` kararları alındı → `EK-B`'ye `D-R63` yazıldı: **25 → 28**, önizlemede
   `Müşteri : 0000123456 (KUNRG)` (ham kod).
2. backend-expert `AR-1`'de **çelişki** bildirdi: bu evde *"Müşteri"* **çözülmüş cari adı**
   demektir (`TS-06:535` ↔ `:558` *"Müşteri (kod)"*), emsal `I_Customer` ile çözüyor.
   **Bulgusu doğruydu.**
3. Lider ölçtü, kullanıcıya **ayrı** sordu, kullanıcı **kod + ad çifti**ni seçti (**25 → 30**);
   ajana `SendMessage` gitti.
4. **Ama `EK-B` hâlâ (1)'deki hâlindeydi.** Ajan onu okudu, `EK-B:3884`'teki eski önizlemeyi
   kanıt gösterdi ve **kendi doğru `MusteriAd` önerisini GERİ ÇEKTİ.**

⇒ Ajan **kusursuz** davrandı: iddiasını kanıta bağladı, kanıt olarak projenin kendi kayıt
belgesini kullandı. **Bayat olan kayıttı.** Zarar: doğru bir bulgu, yazan kişinin kendi bayat
belgesi yüzünden geri çekildi. Mesajlar çakıştığı için fark edildi; çakışmasaydı **sessizce**
eksik kod yazılacaktı.

**How to apply:**
1. **Karar → kayıt → ajan** sırası tek işlemdir. `AskUserQuestion` cevabı geldiği anda kaydı
   güncelle, **sonra** ajana yaz. Ters sıra yarış durumu üretir.
2. Aşılan kaydı **silme** — tarihsel değeri var (kararın nasıl geliştiği). Üstüne
   *"BU KAYIT AŞILDI, geçerli olan: …"* şerhi + yeni bloğa **açık işaretçi** koy.
3. Bir ajan sana **belgeden alıntıyla** itiraz ediyorsa, önce *"belge güncel mi"* diye sor —
   ajanı değil **kendi kaydını** şüpheli say.
4. Çok turlu bir kararda ara-kayıt tutuyorsan, kaydın başına **"canlı / aşılabilir"** damgası vur.

**Ayırt edici:** bu kuralın OKUYAN tarafı [[feedback_capadaki-acik-madde-devralmadan-once-olculur]]
(*"çapadaki açık madde bir iddiadır"*); burada anlatılan **YAZAN** tarafıdır — kendi yazdığın
belge, güncellenmezse başkasını yanıltan bir iddiaya dönüşür.
İlgili: [[feedback_kanit-tazeligi-indeks-ve-zaman-sirasi]] · [[feedback_kapsam-niteleyicisini-dusurme]] ·
[[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] · [[feedback_lider-ajan-paralel-yazim-cakismasi]]
