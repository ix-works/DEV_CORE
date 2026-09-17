---
name: feedback_sendmessage-gorevi-sessizce-islenmemis-olabilir
description: "Ajanın çıktısı henüz yokken 'görev işlenmedi' sonucuna atlama — çalışıyor olabilir; yeniden tetiklemeden önce ajandan ilerleme kanıtı iste"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2caf4c00-51c1-475d-9676-09ad5b0e676b
---

Bir ajana `SendMessage` ile ek görev verdikten sonra çıktı artefaktını ölçmek **doğrudur**,
ama **"artefakt henüz yok" ≠ "görev işlenmedi"** — ajan o sırada çalışıyor olabilir.
Yeniden tetiklemeden önce ya ajandan ilerleme kanıtı iste (tek satırlık durum sorusu), ya
da ölçümü ajanın kendi "bitti" mesajından SONRA yap. Aksi hâlde aynı işi ikinci kez
koşturursun.

**Yardımcı sinyal ama tek başına yetmez:** "idle/available" bildiriminin özeti bir ÖNCEKİ
işin cümlesini taşıyabilir — yeni görevi bitirmiş gibi okunur. Yani ne bildirim özeti ne de
tek bir dosya ölçümü tek başına karar vermeye yeter; **ikisi + ajanın açık beyanı** birlikte.

**Why:** 2026-08-17 ZSD001 TS turunda "released RAP BO sondası" ek görevi verildi. Ajanın
idle bildirimi bir önceki turun özetini taşıyordu; rapor dosyasında beklenen `§EK-1`
başlığı yoktu ve mtime talepten eskiydi ⇒ "işlenmemiş" sonucuna varılıp görev yeniden
gönderildi. Gerçekte ajan yazım aşamasındaydı; ölçüm **bayat kopyaya** denk gelmişti
(dosya 15 dk sonra 65 KB / 768 satır olarak yazıldı). Zarar sınırlı kaldı (ajan tekrar
koşmayıp eksik kalan iki noktayı kapattı), ama yöntem yanlıştı.

⭐ **AYNI HATA İKİNCİ KEZ — ve bu kez kayıt CONTEXT'TEYDİ (2026-08-29, ZSD001 `214`).**
Ajana ikinci görev kuyruğa verildi. Ajanın idle bildirimi geldi ve yalnız BİRİNCİ işi
raporluyordu (`31 FOR TESTING`, `214`'ten söz yok). Lider ölçtü: hedef dosyalarda `214`
**0 geçiş**, md5'ler birinci işin çıktısında ⇒ *"görev düştü"* sonucuna varıp **yeniden
gönderdi** ve bunu kullanıcıya **kesin bir olgu gibi** bildirdi.
⛔ **Sonuç: dayanaksızdı.** Ajan kendi transkript sırasını gösterdi — ilk brif ULAŞMIŞ, icra
edilmiş, liderin "yeniden gönderiyorum" mesajı ondan SONRA gelmişti. `.ccau` mtime `14:11:16`,
liderin ölçümü bundan **önce**ydi ⇒ ölçüm ajan **çalışırken** alınmıştı.

📌 **Sinyal sayımı da şişmişti.** Lider "üç bağımsız sinyal" dedi; gerçekte:
① idle bildiriminin eski işi anlatması → **bu kaydın 2026-08-17'de zaten güvenilmez ilan
ettiği** sinyal · ② "0 geçiş" ve ③ "md5 değişmemiş" → **aynı ölçümün iki yüzü**, ayrı kanıt
değil. Yani 1,5 sinyal 3 sayıldı. ⇒ **Sinyalleri saymadan önce BAĞIMSIZ mı diye sor.**

⚠ **"Dosyada iz yok" bir DROP kanıtı DEĞİLDİR** — yalnız "o an henüz yazılmamış" der.
Ayırt edici sinyal dosya değil, **ajanın tamamlama/idle beyanıdır** ve o beyan bir ÖNCEKİ işi
taşıyabildiği için **tek başına da yetmez.** Elinde kesin ayrım yoksa **"düştü" DEME** —
kullanıcıya da öyle bildirme.

⭐⭐ **YİNE DE YENİDEN GÖNDERECEKSEN İKİ ŞART (bu turda biri unutuldu):**
① **Çapayı YENİDEN ÖLÇ.** İlk görevin kendi çıktısı brifingteki dondurma çapasını
(md5 + satır + sayım) bayatlatır; kopyala-yapıştır gönderim ajanı çapa kontrolünde HAKLI
olarak durdurur. Bu turda çapa `2bc19194…`/`06f27d11…` → `230b355f…`/`5d946324…` olmuştu;
lider yeniden ölçtüğü için tur kaybedilmedi.
② ⛔ **"ZATEN YAPTIYSAN TEKRARLAMA" cümlesini brife KOY.** Bu turda konmadı; mükerrer işten
korunmayı ajanın kendi kontrolü sağladı — **tasarım değil, şans.**

Aynı aile: [[feedback_kapi-kosarken-dosya-donar-md5-teyidi]] ·
[[feedback_ajan-olumsuz-donusu-kanitla-sorgula]] (ajanın karşı-kanıtı liderinkinden güçlü
olabilir) · [[feedback_iddia-yazma-aninda-kanit-kurallari]].

**How to apply:** Ek görev brifinginde beklenen çıktıyı **adıyla** iste (yeni bölüm
başlığı/dosya adı) — ölçüm tek grep'e insin. "Bitti" mesajı gelmeden ölçüp karar verme;
ölçtüysen de sonucu ajana **soru** olarak götür ("§EK-1 göremiyorum, durum ne?"), doğrudan
yeniden tetikleme. Aynı aile: [[feedback_dogrulama-sezgileri-dort-kural]] (bulunamadı ≠
sonuç) · [[feedback_exit0-degil-cikti-kaniti]] · [[feedback_agent-stall-watchdog-mekanizmasi]]
(gerçek stall için watchdog/heartbeat ayrı bir mekanizmadır).

---

## ⭐⭐ ÜÇÜNCÜ VAKA (2026-09-10, ZSD000 FE turu) — ve kaydın nihayet ŞABLONA bağlanması

**Aynı hata, üçüncü kez** — bu kez kayıt context'teydi **ve** lider onu okumuştu.
Lider koşan bir FE ajanına bir kararı **iptal eden** mesaj gönderdi. Ajanın raporu eski
tasarımı anlatıyordu ve kodda iptal edilen ölçüt duruyordu ⇒ lider *"mesajım ona ulaşmamış"*
ve *"üç mesajımın ikisini geç işledi"* diye **kullanıcıya olgu gibi bildirdi**.
⛔ **Dayanaksızdı.** Bir sonraki ölçümde kod değişmiş çıktı (`RE_NO_SCHEDULE` 2/2 dosyada **0**,
md5'ler farklı): ajan talimatı **almış ve uygulamış**, bayat olan **rapordu** — mesaj ondan
sonra işlenmişti. Yani kaydın *"'düştü' DEME"* kuralı okunmuş olmasına rağmen ihlal edildi.

⭐ **Neden okumak yetmedi — ve düzeltme:** bu kayıt **liderin** hafızasındaydı, ama
**hiçbir ajan brifine girmiyordu** ve lider tarafında da bağlayıcı bir madde yoktu. Kullanıcı
bunu tam olarak teşhis etti (birebir): *"bunu ajanlara verdiğin prompt standardına eklemen
bunu kalıcı hale getirmez mi… yani ajanlara iş verirken nasıl bir içerikte prompt hazırlaman
gerektiğini anladığın yere"*. ⇒ Kayıt **iki yere** bağlandı (2026-09-10):
- **Ajan tarafı** — `core/claude/templates/spawn-brief.md` §8 **TALİMAT-DEĞİŞİKLİĞİ TEYİDİ**:
  kararı değiştiren mesaj gelince ajan, işe başlamadan önce değişikliği **KENDİ CÜMLESİYLE**
  özetler (*"aldım"* yetmez — yanlış anlamayı yakalayan şey özetin kendisidir), hangi aşamada
  olduğunu yazar ve **"zaten yaptıysan tekrarlama"** kuralına uyar. Kapsam DAR: yalnız kararı
  değiştiren mesajlar (her mesaja teyit = gürültü).
- **Lider tarafı** — `core/governance/agent-teams-operating-model.md` **§4A-E**: kararı
  değiştiren mesaj gönderildiyse teslim **rapordan değil KODDAN** doğrulanır (içerik-çapası
  `grep` + `md5`); *"ajan mesajı almadı"* demek **ölçülmemiş bir suçlamadır**.

📌 **Genel ders — kaydın kendisi hakkında:** bir ders üç kez tekrarlıyorsa sorun *hatırlamamak*
değil, dersin **icra noktasına bağlanmamış** olmasıdır. Memory kaydı **liderin** okuduğu yerdir;
davranışı değiştiren şey **şablon + bağlayıcı madde**dir. ⇒ Üçüncü tekrarda kaydı zenginleştirmek
yetmez, **nereye bağlanmadığını** sor. İlgili: [[feedback_ajan-kurali-brifingde-degil-taniminda-yasar]] ·
[[feedback_iddia-kac-yerde-yasiyorsa-o-kadar-yerde-kapatilir]] ·
[[feedback_flag-degil-icra-bekleyen-is-kapat]].
