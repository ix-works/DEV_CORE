---
name: feedback_capadaki-acik-madde-devralmadan-once-olculur
description: "Çapadaki 'açık/bekliyor' cümleleri ZAMAN-DAMGALI iddialardır — devralmadan önce ölçülür; yazıldıktan sonraki iş çapaya geri dönmez"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 147413fa-85a8-4e1e-8abc-7c28606ff1f5
---

**Vaka (2026-09-01, ölçüldü):** Kullanıcı *"resume ve diğer iş listelerindeki maddelerin
güncelliklerini kontrol et"* dedi. Üç çapa canlıya/git'e karşı ölçüldü → **12 bayat iddia**:

| Çapa | Bayat iddia | Gerçek |
|---|---|---|
| <PAKET-A> | "üç tur repoda bekliyor, SAP'ye gitmedi" (30.08 gün sonu) | 9 dosyanın **6'sı canlıda repo ile aynı** — push'lar **31.08 sabahı** yapılmış (`REPOSRC` damgası) |
| <PAKET-A> | "`PRECHECK.ccau` canlıda hiç yok" | **var**, 249 satır, fark 0 |
| <PAKET-B> | "<MUSTERI-A> `T661W` satır 1 açık" · "<MUSTERI-C> ana veri `V4 034`'ü kaldıran tek şey" | ikisi de **girilmiş**; `V4 034` başka sebeple sürüyor |
| <PAKET-C> | "Git commit henüz yapılmadı" | commit `577da372` / PR #242 — **aynı gün** yapılmış |

⇒ Ortak mekanizma: **çapa bir ZAMAN FOTOĞRAFIDIR.** Gün-sonunda yazılır; iş ertesi sabah
devam eder; çapaya geri dönen olmaz. Kimse yalan yazmadı — cümleler **yazıldıkları an doğruydu**.

**Why:** Var olan kural ([[feedback_takim-sureklilik-gun-sonu-resume]] §KAPANIŞ DİSİPLİNİ:
*"kapanış anı = artefakt anı"*) **üretici** tarafını bağlar ve pratikte delinir — bugün üç
belgede birden delinmişti. Bu kayıt **tüketici** tarafının kapısıdır: çapayı okuyan, onu
*ölçüm* değil *iddia* sayar. Bayat çapanın bedeli ölçüldü: (a) yanlış teşhis — <MUSTERI-C>'in
blocker'ı ana veri sanıldı, oysa `VTRNR`↔`BSTKD` uyuşmazlığıydı; (b) **regresyon riski** —
"repoda bekliyor" cümlesi drift YÖNÜNÜ varsayıyordu, oysa `ZCL_SD022_PRECHECK.clas`'ta canlı
repodan İLERİDEYDİ (`INTO` klozu strict-mode düzeltmesi); repo push edilseydi düzeltme geri
alınır, aktivasyon düşerdi ([[feedback_drift-uyarisinda-once-yonu-olc]] ·
[[feedback_privileged-access-strict-mode-into-sonda]]).

**How to apply:**
1. **"Nerede kalmıştık" turunda çapayı OKUMA + DEVRALMA — ÖLÇ.** Her `açık/bekliyor/yok`
   cümlesi bir iddiadır. Ucuz ölçümler: `git log`/`git show` (commit iddiaları) · canlı md5 ↔
   repo md5 (push iddiaları) · tek `SELECT` (ana veri/uyarlama iddiaları) · `REPOSRC`/`E071`
   (kim ne zaman yazdı).
2. **Ölçümü çapaya GERİ YAZ** — tarih + yöntemle. Tarihçe bloğunu silme; üstüne
   "⛔ AŞILDI/ÇÜRÜDÜ — <tarih>" bandı koy ki eski cümle bir daha devralınmasın.
3. **Yönü asla varsayma:** "repoda bekliyor" ≠ "repo ileride". İki tarafı da ölç.
4. ⚠ **Kendi ölçümün de bayatlar/eksilir:** aynı turda 08-31'de yazdığımız *"<MUSTERI-G>'nin 52 IDoc'unun
   tamamı boş `SNDPRN` ⇒ CPI düzeltmesinin hiçbir etkisi yok"* hükmü çürüdü — aynı gün
   `SNDPRN` DOLU 50 IDoc daha vardı, 12'si postlanmıştı. Tek değere daraltılmış sayma,
   kapsam-aşırı hükmü taşıyamaz ([[feedback_kapsam-niteleyicisini-dusurme]] ·
   [[feedback_onay-da-bir-iddiadir-mekanizmayi-olcmeden-net-deme]]).
5. **Ana veri/uyarlama satırlarını çapada takip kalemi yapma** — zaten kullanıcının alanı ve
   en hızlı bayatlayan sınıf ([[feedback_uyarlama-verisi-acik-kalem-degil]]); kanonik listeye
   link ver, değeri kayda geçirme.

**⟳ TEKRAR 2026-09-04 — YENİ KIVRIM: bayat cümle ESKİ çapada değil, BUGÜN YAZILAN kayıtta doğdu.**
Sabah yazılan kuyruk kaydı (`deferred-triggers.md` → `T-SM12KILIT`, commit `40b31a87`)
*"`ZCL_SD022_HATA_TEXTS.ccau` 31.08'den beri SM12 kilidi yüzünden push edilemiyor, EN ESKİ AÇIK
KALEM"* diyordu. Ölçüm: kalem **09-01 akşamı KAPANMIŞTI** — aynı repodaki çapa (`<PAKET-A>-…-RESUME.md:400`)
✅ CANLI diyor ve kanıtı bugünkünün **birebir aynısı** (normalize md5 `804ac32b…`, `inactive_objects`
2→0, `adt_unit_run` 20/0). `git log -S "31.08'den beri"` → ifade repoya **yalnız** o commit'le,
kapanıştan **3 gün sonra** girmiş. **Bedeli:** kullanıcıdan gereksiz **SM12 kontrolü** istendi +
zaten canlı olan gövde yeniden push edildi.
⇒ **Kural genişler:** "çapa zaman fotoğrafıdır" YETMEZ — **yeni yazılan kayıt da bayat doğabilir**;
kayıt TAZE diye ölçümden muaf değildir. İki yönlü kapı: ① kuyruk kaydı **yazan** taraf, kalemi
kapatmış olabilecek çapayı obje adıyla `grep`lemeden madde açmaz; ② kaydı **devralan** taraf,
tarihi ne olursa olsun ölçer. ⛔ En ucuz kapı burada **obje adıyla repo araması**ydı: kanıt aynı
repoda, aynı adla duruyordu (`grep -n HATA_TEXTS governance/*RESUME*`) — 5 saniyelik iş.
📌 Ayrıca: kullanıcı *"bana sorabilirdin"* dedi — **kullanıcı ekranındaki durum (SM12 vb.) için
tahmin/araç-turu yerine doğrudan sormak** hem ucuz hem kesindir ([[feedback_karar-sormadan-once-erisilebilirlik-olc]]).

Son-doğrulama: 2026-09-04 (yukarıdaki tekrar) · 2026-09-01 · prior-art: arandı — [[feedback_takim-sureklilik-gun-sonu-resume]]
(üretici tarafı) ve [[feedback_kanit-tazeligi-indeks-ve-zaman-sirasi]] (kanıt tazeliği) VAR;
tüketici-tarafı kapısı YOKTU. Applies-to: tüm projeler.
