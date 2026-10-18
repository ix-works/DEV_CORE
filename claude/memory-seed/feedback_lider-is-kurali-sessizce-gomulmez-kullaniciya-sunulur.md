---
name: lider-is-kurali-sessizce-gomulmez-kullaniciya-sunulur
description: "Lider/ajanın tasarım sırasında koyduğu bir İŞ KURALI (hangi kayıt dışlanır, neye izin verilir) koda sessizce gömülmez — karar olarak kullanıcıya sunulur"
metadata: 
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: ecbcb0c5-488c-4417-8153-32a36e13dde5
  modified: 2026-09-22T16:41:13.779Z
---

Tasarım/build sırasında lider ya da ajan bir **iş kuralı** koyarsa (ör. "M tipi lot transfer hedefi olamaz",
"şu durumdaki kayıt listelenmez") bu kural koda/CDS süzgecine **sessizce gömülmez**; kullanıcıya
"bu benim kararım, onaylıyor musun?" diye ayrı bir karar maddesi olarak sunulur ve karar artefakta (RESUME/FS) yazılır.

**Why:** Bir projede (2026-09-22): hedef lot listesinden M (MIGO) lotlarını dışlayan kural liderin onaysız kararıydı;
kullanıcı "hedef lot boş geliyor" diye fark etti, "neden, bir sebebi var mı?" diye sordu. Açıkça "benim kararımdı" denince
kullanıcı tersini seçti (M hedef olabilir) ⇒ DDIC + sınıf + 2 CDS yeniden yazıldı. Onay ilk seferde alınsaydı tek tur yeterdi.

**How to apply:** Build brifinde/tasarımda "şunu dışla / yasakla / sınırla" türü her satırı işaretle; kaynağı
(kullanıcı kararı · FS · TS) yoksa onay listesine koy. Kullanıcı sorduğunda kural onaysızsa bunu açıkça söyle.
Son-doğrulama: 2026-09-22 · Applies-to: tüm projeler, iş kuralı içeren build/tasarım turları.
