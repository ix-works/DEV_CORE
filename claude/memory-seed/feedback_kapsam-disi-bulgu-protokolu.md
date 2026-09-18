---
name: feedback_kapsam-disi-bulgu-protokolu
description: Kapsam dışı bug bulunca düzeltmeye girişme — karar ağacı (bizden doğdu / işi etkiliyor / mutlaka çözülmeli / ilgisiz) ve her dalda kanıt zorunlu
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a6e5bd03-5005-49aa-a91b-295e6840fa17
---

Kullanıcı kuralı (2026-08-08, iki adımda verildi):

> *"Bu değişiklikleri yaparken benim söylediklerim haricinde bir bug/hata bulursan hemen düzeltmeye
> çalışma, kanıtlı örnekle bana sun ve onayımı iste."*
> + *"hatta işi engellemiyorsa planın sonuna **açık kalem** maddesi olarak da ekleyebilirsin; ama
> **mutlaka çözülmesi gerekiyorsa**, veya **senin yaptığın bir şeyi etkiliyorsa**, veya **senin
> yaptığın bir şeyden kaynaklanıyorsa** yapabilirsin."*

**KARAR AĞACI** — bulunan her kapsam-dışı kusur için:

| Koşul | Aksiyon |
|---|---|
| (a) **bizim değişikliğimizden doğdu** (regresyon) | **DÜZELT** — işin parçası, ayrı onay gerekmez |
| (b) **yapmakta olduğumuz işi etkiliyor/engelliyor** | **DÜZELT**, bildirerek |
| (c) **mutlaka çözülmeli** (veri kaybı / geri alınamaz / yanlış veri üretiyor) | **DERHAL bildir**, düzeltme onayla |
| (d) **engellemiyor, ilgisiz** | *(2026-08-14'te DARALTILDI — aşağı bak)* → **PROGRAM/KOD kusuru ise: DÜZELT.** Yalnız program-dışı işler (uyarlama verisi, yetki/rol, araç-altyapı, kullanıcı-tercihi) açık kalem olur |
| **(e) ⛔ bulduğun şey bir DEFECT değil — ONAYLI BİR KURAL sana uygulanamaz/yanlış geliyor** | **KENDİ YORUMUNU UYGULAMA → SOR.** *(2026-08-21'de eklendi — aşağı bak)* |

### ⛔ (e) DALI — "onaylı kuralı yeniden yorumlama" AYRI ve DAİMA-SOR (2026-08-21)

**Ayrım:** (a)-(d) dalları bir **kusur** bulduğunda ne yapacağını söyler. (e) dalı, bulduğun
şeyin kusur **olmadığı**, onaylı bir kuralın (spec/TS maddesi/karar kaydı) o noktada
**uygulanamaz göründüğü** hâldir. ⇒ Bu bir **karar**dır, düzeltme değil — ve karar
**kullanıcınındır**.

- ⛔ **"Uygula ve beyan et" YETMEZ.** Beyan kodun/raporun içinde kalır; kural yazılı, senin
  yorumun değil. Kuralın gerçekten uygulanamaz olduğunu göstermek onu **değiştirme yetkisi vermez**.
- ⛔ **"İki seçenek var, ikisi de kötü" varsayımını sorgula.** Ölçülmüş vaka: ajan ikili bir
  seçim varsaydı, **üçüncü yolu aramadı**; kapı üçüncü yolu buldu.
- ✅ Doğru davranış: **DUR → kuralın hangi noktada çakıştığını kanıtla → seçenekleri (varsa
  üçüncüyü de) sun → SOR.**

**Ölçülmüş vaka (`YK-4`, 21.08):** `TS-04:1443` *"hatasız satırlar YAZILIR · dosya bütünlüğü
kuralı YOKTUR"* diyordu. Toplu `MODIFY`'da `sy-subrc` parti seviyesinde olduğu için ajan
`ROLLBACK` + partiyi tümden ret seçti ve *"tek dürüst davranış"* diye savundu — yani **yok denen
kuralı fiilen koyuyordu**. Kapı **BLOCKER** verdi, bir tam tur maliyeti. Ajan beyanını geri aldı:
*"ikili bir seçim olduğunu VARSAYDIM, üçüncü yolu ARAMADIM."* Üçüncü yol: parti düşünce
yazılanları geri oku, yalnız eksik kalanları reddet — 0 lot yerine **99**.

⚠ **(d)'yi DARALTMAZ:** kanıtlanmış bir program kusuru hâlâ **sorulmadan düzeltilir**. (e) yalnız
*"onaylı kuralı yeniden yorumlama"* hâlini ayırır. Sınır sorusu: **"düzeltiyor muyum, yoksa
kuralı mı değiştiriyorum?"**

⇒ Bu dalı dayatan **`D2` kancası** planlandı (*kural kimliği anılıyor ∧ yazma işi ∧ "yeniden
yorumlama" freni yok* → **%4,8** ateşleme, `YK-4` brifinin **2/2'sini** yakalıyor;
ölçüm: `governance/PLAN-2026-08-21-BRIFING-DISIPLINI.md` §8.3).

### ⚠ (d) DALININ DARALTILMASI — kullanıcı kuralı 2026-08-14

> *"programlar ile ilgili şeyleri ertelemene gerek yok, yapılması gerekiyorsa yap"*

**Tetikleyici vaka:** lider iki program kusurunu (ATC Prio-1 nested SELECT · teslimat no
görüntü-biçimi tutarsızlığı) ölçüp kanıtladıktan sonra kullanıcıya *"düzeltelim mi, kayda mı
geçelim?"* diye sordu. Kullanıcı bunu gereksiz bir kapı olarak gördü.

**Kural:** Bir **program/kod** kusuru kanıtlandıysa ve düzeltilmesi gerekiyorsa, "açık kalem mi
düzeltme mi" diye **SORULMAZ** — düzeltilir. Soru sormak, kusuru ertelemenin kibar biçimidir.
- ⇒ *"düzeltelim mi, kayda mı geçelim?"* sorusu **program kusurları için sorulmaz.**
- Kayda geçirme (deferred-triggers) düzeltmenin **alternatifi değil**, düzeltme gerçekten
  yapılamayacaksa (başka bir tur/kişi/sistem gerekiyorsa) başvurulan yol.
- (a)/(b)/(c) dalları aynen geçerli; değişen yalnız (d)'nin **program kusurları** kısmı.

**Hâlâ açık kalem / onay gerektirenler** (bu daraltmanın DIŞINDA):
uyarlama-verisi ve ana-veri değerleri ([[feedback_uyarlama-verisi-acik-kalem-degil]]) · yetki/rol
ataması · **araç-altyapı değişikliği** (hook/validator/MCP/script — ADT-infra kuralı ayrı ve
onay ister, [[feedback_adt-infra-degisikligi-once-uyar-onay]]) · kullanıcı-tercihine bağlı
fonksiyonel kararlar · standart SAP objeleri (ADR 0005).

**Why (daraltma):** kanıtlanmış bir kod kusurunu soruya çevirmek kullanıcıya karar değil **iş**
yüklüyor — ölçümü zaten yapan taraf kararı da verebilir. Bu, [[feedback_karar-verimliligi-asiri-kapi-yok]]
kuralının kapsam-dışı bulgulara uygulanmış hâli; kapsam sprawl'ı endişesi (aşağıdaki Why) düzeltmeyi
**sormakla** değil, düzeltmeyi **ölçülü ve izole** tutmakla çözülür.

**Her dalda kanıt zorunlu** (a/b/c/d fark etmez): dosya + **içerik çapası** (çıplak satır no
bayatlar), mümkünse **canlı örnek kayıt/veri** (*"şu belgede şu değer şöyle çıkıyor, oysa şöyle
olmalı"*). Kanıtsız bulgu "bug" diye yazılmaz → *"ŞÜPHE — doğrulanmadı, nasıl doğrulanır: X"*.
Sunum alanları: **ne · nerede · neden kusur · kanıt · kullanıcıya etkisi (bugün görünür mü, latent
mi) · maliyet/risk + öneri.**

**Why:** kapsamı yol boyunca dağınık genişletmek bu projede ölçülmüş en pahalı hata — "3 app'lik
küçük düzeltme" sanılan bir tur **7 app / 6 review turu / 2 gün** olmuştu ve kullanıcı *"neden tek
tek yapıyorsun"* demek zorunda kalmıştı. Ama bulguyu **sessizce yutmak** da yanlış: değerli
bulgular (canlı sızıntılar) o turda ancak kullanıcı *"atladığımız bir şey kalmasın"* dediği için
yakalanmıştı. (d) dalı bu ikisini birlikte çözüyor — bulgu kaybolmuyor, akış da durmuyor.

**How to apply:** görev başında bulgu-kovası aç (*"AÇIK KALEMLER"*). Ajan brifinglerine karar
ağacını **açıkça yaz** (alt-ajanlar bu memory'yi görmez). Ajanlardan bulguları **ayrı başlıkta**
ve 6 alanlı formatta iste; "yapılacak" listesine yalnız kullanıcının maddeleri girer. Tur sonunda
açık kalemler `governance/deferred-triggers.md`'ye **tetik koşuluyla** taşınır — kaybolmaz, gizlenmez.

İlgili: [[feedback_kararlari-once-topla-sonra-dispatch]] · [[feedback_cok-katmanli-degisiklik-yonetimi]] ·
[[feedback_dogrula-once-flag-spekulatif-blocker-yasak]] · [[feedback_flag-degil-icra-bekleyen-is-kapat]] ·
[[feedback_soru-once-tartis-act-etme]]

Son-doğrulama: 2026-08-21 ((e) dalı eklendi — onaylı kuralı yeniden yorumlama = UYGULAMA, SOR;
(d) daraltması 2026-08-14'ten beri aynen geçerli)
Applies-to: her proje / her tur; özellikle çok maddeli (S2) turlar ve alt-ajanlı çalışma
