---
name: feedback_gurultulu-duser-iddiasi-olculmeden-yazilmaz
description: "'Yanlış olursa GÜRÜLTÜLÜ düşer' bir güvenlik argümanı değil, hedef sistem hakkında ÖLÇÜLMEMİŞ bir olgu iddiasıdır — ters çıkarsa operatöre 'izlemene gerek yok' demiş olursun"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f911c8cf-83f3-4ff2-bd38-ae5ee4790ae5
---

Bir tasarım kararını *"yanlış giderse **gürültülü** başarısız olur, sessiz yanlış üretmez"* diyerek
savunuyorsan, o cümle bir gerekçe değil **hedef sistem hakkında bir olgu iddiasıdır** ve diğer her
iddia gibi **ölçülmeden yazılmaz**. Ters çıkarsa yalnız yanılmış olmazsın — okuyucuya
*"bunu izlemene gerek yok"* demiş olursun; yani **kaçınmayı iddia ettiğin sınıfı kendin üretirsin**.

**Vaka (2026-08-28, ZSD001 <MUSTERI-B>/<MUSTERI-E>):** `E1EDP16-PRGRS` için `FixValues` tablosuna
kapsanmayan bir kod gelirse ne olur? Dört artefakta birden şunu yazdım: *"`FixValues` boş bırakır →
IDoc `V4 215` ile **GÜRÜLTÜLÜ** düşer (sessiz yanlış yerine)."* Bunu **hiç ölçmedim** — SAP'nin
geçersiz niteleyiciyi reddettiğini "biliyordum".
**Bug-gate çürüttü, sonra ben bağımsız doğruladım:** domain `EDI_DATTYP`'in sabit değer listesinin
**ilk satırı BOŞ** (`DD07T.DOMVALUE_L = null`) ve metni **"Tag" = gün**. `LVED4F0Z` doğrulamayı
`READ TABLE LT_DD07V … DOMVALUE_L = E1EDP16-PRGRS` ile yapıyor ⇒ boş değer listede **olduğu için
geçiyor**; `V4 215` **hiç çıkmıyor** ve SAP satırı **sessizce "gün"** işliyor.
⇒ Güvence **tam tersineydi**. Üstelik aynı iddia, dün bulduğum gerçek bir kusurun gerekçesine de
sızmıştı: *"789 satır V4 215 alır"* demiştim; gerçekte o satırlar **sessizce** geçerdi
(785'i tesadüfen doğru, 4'ü sessizce yanlış) — kusur daha küçük ama **daha sinsi**ydi.

**Why:** *"Gürültülü düşer"* iddiası bir **izleme kararını** belirler: doğruysa hata kendini
gösterir, yanlışsa kimse bakmaz. Bu yüzden yanlış olduğunda maliyeti bulgunun kendisinden büyüktür.
İki ek tuzak: ① iddia **tek cümle** olduğu için review'da "gerekçe" sanılıp atlanır; ② bir kez
yazılınca **kardeş paketlere kopyalanır** (burada 1 spec → 4 artefakt). Ve asıl mesele: gerçek
koruma **metin değil kapıdır** — bu turda `PRGRS_TABLE` kapsama kapısı eklendi ve
**negatif testle** koşumu kanıtlandı.

**How to apply:**
- *"…olursa hata verir / düşer / bloklanır"* yazacaksan **önce ölç**: hangi kontrol, hangi tabloya
  bakıyor, hangi değer kümesi geçerli? SAP'de tipik yer: **domain sabit değerleri** (`DD07L`/`DD07T`)
  ve onu okuyan `DD_DOMVALUES_GET` çağrısı. ⚠ **Boş değer çoğu domainde MEŞRU bir sabit değerdir.**
- Ölçemiyorsan iddiayı **yazma**; yerine `[DOĞRULANMADI]` koy ve kararı ona dayandırma.
- Güvenliği metne değil **kapıya** bağla: kapsanmayan girdi gelirse **üretim dursun**. Kapıyı
  eklerken **negatif test** yap (beklenen değeri mutasyona uğrat, assert ateşlensin) — yoksa
  kapının koştuğunu değil yalnız var olduğunu bilirsin.
- Aynı cümleyi kardeş pakete kopyalarken **yeniden ölç**: hedef alan/domain farklı olabilir.

İlişkili: [[feedback_onay-da-bir-iddiadir-mekanizmayi-olcmeden-net-deme]] ·
[[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] (orada ajanın gerekçesi, burada **kendi**
gerekçen) · [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]] · [[feedback_hook-negatif-test-exit0-iki-anlamli]] ·
[[feedback_duzeltme-turu-kendi-regresyonunu-uretir]]

Son-doğrulama: 2026-08-28 (`EDI_DATTYP` boş sabit değeri canlı `DD07T` ile ölçüldü; 4 artefakt düzeltildi)
Applies-to: TÜM projeler · her spec/mapping/karar gerekçesi
