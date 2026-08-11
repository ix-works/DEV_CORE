---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-05-14
status: active
---

# Bilinen Hatalar ve Çözümlü Durumlar

## 31. Bilinen Hatalar ve Çözümlü Durumlar

### 12.1 SmartFilterBar — Vkorg/Vtweg/Spart Görünmüyor

**Sebep:** CDS/SADL mekanizmasıyla oluşturulan entity type'ında property'ler SEGW'den `filterable` yapılamıyor.

**Çözüm A (Uygulandı):** MPC_EXT `DEFINE` metodunda `set_filterable( iv_filterable = abap_true )` çağrısı.

**Çözüm B (Uygulandı):** SmartFilterBar tamamen kaldırılıp manuel `sap.m` Panel + Input/Select yapıldı. SmartTable `smartFilterId` bağlantısı da kaldırıldı.

### 12.2 sap.f.DynamicSideContent — 404

**Sebep:** `sap/f` kütüphanesi SAPUI5 1.120'de yüklenmedi / 404 veriyor.

**Çözüm:** `sap.ui.layout.Splitter` (orientation="Horizontal", 70%/30%) kullanıldı.
- `xmlns:l="sap.ui.layout"` namespace eklendi
- `xmlns:f="sap.f"` ve manifest `libs`'den `sap.f` kaldırıldı

### 12.3 manifest.json Annotation URL — 400

**Sebep:** `ZSD_ORDER_SRV_VAN` annotation servisi SAP'de kayıtlı değil.

**Çözüm:** `mainAnnotation` dataSource ve `settings.annotations` array'i manifest'ten tamamen kaldırıldı.

### 12.4 i18n Dil Sorunu

**Çözüm:**
```json
"i18n": {
  "bundleUrl": "i18n/i18n.properties",
  "supportedLocales": ["", "tr"],
  "fallbackLocale": ""
}
```
`fallbackLocale: ""` boş string — varsayılan `.properties` dosyasını kullanır.

### 12.5 syntax_check.py Yanlış Hata Raporu

**Durum:** `syntax_check.py` bazen gerçekte hata olmayan durumları hata olarak raporlar.
Özellikle CDS/class interaksiyonunda ve SADL mekanizmasıyla oluşturulan entity type'larda.

**Kural:** syntax_check hata verse bile `activate_object.py` dene. Gerçek aktivasyon başarılı olabilir. SAP GUI'den kontrol et.

---


### 12.6 Klasik Dynpro/GUI-status üretimi (C1) — dialog/generate/lock hataları

Hepsi `RPY_DYNPRO_INSERT` / `RS_CUA_INTERNAL_*` ile klasik ekran/status üretiminde çıktı; **tam reçete + çözümler: [`adt-fugr-functions.md`](adt-fugr-functions.md) §6.** Özet:

| Hata | Sebep / Çözüm |
|---|---|
| `400 "Session Timed Out"` (classrun) | RPY/RS_CUA **dialog context** ister → `adt_classrun` yapamaz. RFC-enabled FM + `/sap/bc/soap/rfc`. |
| `does not implement if_oo_adt_classrun~main` (HTTP **200** gövdesinde) | Mesaj **DOĞRU**, araç bozuk değil: (1) sınıf **aktive edilmemiş** → aktif sürüm boş kabuk (classrun aktif sürümü koşar) · (2) çağıran süreç **bayat stateful oturum** tutuyor (obje başka süreçte aktive edildi). → aktive et + **`adt_inactive_objects`** doğrula · oturum RESET. ⛔ **taze class adıyla yeniden yaratma** (yanlış reçete, geri alındı 2026-07-31). [`adt-classes.md`](adt-classes.md) §24.9 |
| `00264 "GUI status ... durumu eksik / not generated"` | `RS_CUA_INTERNAL_WRITE` tanımı yazar ama load üretmez → sonrasında `RS_CUA_GENERATE` çağır. |
| `423 InvalidLockHandle` (FM source push) | `set_object_source` retry/ETag stateful lock'u bozar → sıkı lock→PUT→activate→unlock (`set_function_module_source`). |
| `400 "Parameter comment blocks are not allowed"` | FM imzası `*"` block ile push edildi → **satır-içi ABAP imza** yaz. |
| `mandatory parameter BIV` (RABAX) | `RS_CUA_INTERNAL_WRITE` BIV zorunlu → FETCH'ten gelen biv'i geçir. |
| GUI status Almanca | SOAP-RFC çağrısında `sap-language` yok → logon-default dil. `sap-language=TR` geç. |
| Geri/Çıkış çalışmıyor | Donör status jenerik `&F03/&F15/&F12` map'liyor → program PAI `BACK/EXIT/CANCEL` bekliyor. pfk fcode'larını re-map et. |

### 12.7 `423` push'ta — obje o TRANSPORT'a kayıtlı değil (lock verilir, değişiklik reddedilir)

**Belirti:** Bir obje (tipik olarak CLASS) push edilirken **`423 InvalidLockHandle`**. Lock çağrısı
**başarılı** görünür, handle döner — ama PUT reddedilir. Aynı oturumda **başka objeler sorunsuz
push edilir** (bu yüzden "araç bozuk" sanılır).

**Kök sebep:** Objeyi, **kayıtlı olmadığı** bir transport (`corrNr`) ile değiştirmeye çalışmak.
SAP bu durumda kilidi VERİR ama PUT'u reddeder; `423` bunun türevidir. Sık senaryo: elde bir
**görev (S)** numarası vardır (`DS4K9xxxxx`), ama obje **üst istek (K)** altında ya da **başka
bir görevde** kayıtlıdır.

> ⛔ **DÜZELTME 2026-08-10 — bu paragraf eskiden şunu diyordu:** *"SAP … `MODIFICATION_SUPPORT=NoModification`
> der ve `CORRNR` **boş** döner"*. **İKİSİ DE ÖLÇÜLMEMİŞTİ** (cümle dış referanstan yazılmıştı) ve
> `NoModification` kısmı **ÇÜRÜTÜLDÜ**: bu sistemde **her** CLAS kilidi bu değeri döndürür —
> başarıyla push edilen sağlıklı sınıflar dahil (5/5, §12.7b). Yani değer bu vakanın **belirtisi
> değildir**, ayırt edici gücü yoktur. `CORRNR` de ölçülen 5 sağlıklı sınıfta **DOLU** döndü.
> ⇒ Bu vakanın tek kesin teşhisi aşağıdaki **E071 sorgusudur**; lock yanıtındaki alanlara bakma.

**Teşhis (tek sorgu, kesin):**
```sql
SELECT trkorr, pgmid, object, obj_name FROM e071 WHERE obj_name = '<OBJE>'
```
Kullandığın `corrNr` bu listede YOKSA sebep budur.
(Ölçülmüş vaka — **aynı oturum, aynı araç, iki sınıf**: `ZCL_A` kullanılan görevde kayıtlıydı
→ **geçti**; `ZCL_B` yalnız üst istek + başka bir görevde kayıtlıydı → **423**. Fark obje tipinde
ya da araçta değil, **transport kaydında**.)

**ÇÖZÜM — `corrNr`'ı SABİT YAZMA, LOCK YANITINDAN OKU.**
`lock_object()` etkin transport'u `_last_lock_effective_transport`'a koyar (docstring'i bunu uyarır).
Kanonik kalıp:
```python
lock_handle = adt.lock_object(OBJ_URL, transport=TRANSPORT)
eff = getattr(adt, '_last_lock_effective_transport', None) or TRANSPORT
params = {'lockHandle': lock_handle, 'corrNr': eff}     # ← eff, TRANSPORT DEĞİL
```
⛔ **`corrNr = TRANSPORT` (sabit) yazan her script bu hataya açıktır.** Bugüne kadar iki kez ısırdı.

**⛔ YANLIŞ TEŞHİS UYARISI — bu tuzağa iki kez düşüldü:**
Semptom `register_object_in_transport()`'un CSRF ön-alımına yıkıldı (*"`self.csrf_token`'ı eziyor"*).
**YANLIŞ.** ① O ön-alım **kasıtlı ve zorunlu**: SAP `/cts/*` uçlarında `/discovery` token'ını
yanıltıcı bir **403** ile reddeder. ② Fonksiyonun kendisi **"Bug 19"** düzeltmesidir (R3TR ön-kaydı
olmadan CTS **her include için ayrı K+S transport** açıyordu) — kaldırmak o hatayı geri getirir.
③ `CORRNR` boş dönmesi kodda zaten **hata değil `[INFO]`** sayılır (`sap_adt_lib.py:2384-2387`),
yani "CORRNR yok ⇒ enqueue ölü" zinciri **kodun kendi davranışıyla çelişir**.
⇒ **`register_object_in_transport`'a DOKUNMA.**

**Kontrol grubu doğru eksende kurulmalı (PATTERN #19):** "sınıf ↔ include" değil,
**"çalışan sınıf ↔ patlayan sınıf"**. Yanlış eksen, kök sebebi 10 gün boyunca gizledi.

**📌 Tarihçe / bu kaydın var oluş sebebi:** Aynı kalıp **2026-07-30**'da çözülmüştü
(proje `SESSION_NOTES`'ta kayıtlı) ama **core'a terfi etmedi (T1 kaçtı)** ⇒ 2026-08-09'da
**yanlış teşhisle yeniden keşfedildi** ve paylaşılan araca neredeyse yanlış bir düzeltme yapılacaktı.
Ders: *proje notunda çözülen ADT kalıbı core'a terfi etmezse, çözülmemiş sayılır.*

---

### 12.7b `NoModification` CLAS'ta NORMAL DEĞERDİR — §12.7'den türetilen guard'ın yanlış-pozitifi (2026-08-10)

> ⛔ **BU BÖLÜM §12.7'yi SINIRLANDIRIR.** §12.7 gerçek bir vakayı anlatır (obje o transport'a
> kayıtlı değil). Ama o kaydın *"SAP `MODIFICATION_SUPPORT=NoModification` der"* cümlesi
> **ölçülmemişti** ve yanlıştı. Bu değere göre kurulan guard **tüm class-push yolunu kapattı.**

**Belirti (guard yürürlükteyken):** Her sınıf push'u, SAP'ye tek bir yazma bile denenmeden,
*"SAP granted the lock but reports the object as NOT modifiable"* + §12.7 atfı ile düşer.
Mesaj transport'u işaret ettiği için teşhis oraya sapar; SAP tarafında **hiçbir şey yanlış değildir.**

**KÖK SEBEP (ölçüldü — 8 obje / 2 paket / 2 tip; ayrım ekseni OBJE TİPİ):**

| Tip | Örnek sayısı | `MODIFICATION_SUPPORT` | Gerçek durum |
|---|---|---|---|
| **CLAS** | 5 | **`NoModification` (5/5)** | Hepsi aktif geliştirilen sınıf; hepsi aynı gün başarıyla push edildi |
| **DDLS** | 3 | boş (3/3) | Sağlıklı |

İki farklı paket çaprazlandı ⇒ ayrım **paket/obje/transport değil, TİP**. Sağlıklı sınıf da,
§12.7 vakasındaki sınıf da aynı değeri döndürür ⇒ **değerin ayırt edici gücü YOKTUR.**

**⛔ GUARD'IN KENDİ YORUMU İTİRAFTI** (`sap_adt_lib.py`, PR #99):
> *"`NoModification` DEĞERİ dış referanstan gelir (abap-adt-api `AdtLock`); **bizde CANLI ÖRNEĞİ YOK.**"*

Sözleşmenin **şekli** bir DDLS ölçümünden alınmış (`boş = normal`), **anlamı** dış dokümandan
varsayılmıştı; CLAS'ın ne döndürdüğü hiç ölçülmemişti. ⇒ **Ölçülmemiş bir değere göre KAPI KURMA.**
Ölçemiyorsan değeri **kaydet ve yaz**, ama akışı ona bağlama. *(Aynı gün yazılan kayıt, riski
"koruma çalışmaz, meşru push bloklanmaz" diye tahmin etmişti — **o tahmin de yanlış çıktı.**)*

**ZAMAN EKSENİ — teşhisi tek hamlede çözen soru: "bu daha önce çalışıyor muydu?"**

| Olay | Tarih |
|---|---|
| CLAS push'ları **başarıyla** çalışıyor | …2026-07-13 · 2026-07-28 |
| **Guard merge (#99)** | **2026-08-09 15:40** |
| Tüm CLAS push'ları bloke | 2026-08-09 17:30+ |

📌 İlk kontrol grubu **CLAS↔DDLS** eksenindeydi ve doğruydu ama **yetmedi**; kilidi açan
`git log -S'<guard-sembolü>' -- <araç>` oldu. **Regresyonu ayıran şey tip değil, TARİHTİR.**

**MERDİVEN — bir obje yazılamıyorsa, ucuzdan pahalıya:**
1. **Bu obje tipi DAHA ÖNCE yazılabiliyor muydu?** → araç tarafında `git log -S` + objenin
   `changedAt`'i. **Evet ise regresyon ara, SAP'yi kovalama.**
2. **Aynı anda başka tip yazılabiliyor mu?** (CLAS↔DDLS) → tip-bağımlı guard'ı ele verir.
3. **`e071` sorgusu** → §12.7'nin gerçek vakası. *(Bugün bu teşhis, PUT gerçekten 423 verince
   `set_object_source` tarafından otomatik basılır — kilit anında DEĞİL.)*
4. **`EU 510`** *"Kullanıcı X zaten Y öğesini düzenliyor"* → editör/enqueue kilidi.
   ⚠ Yalnız **aktivasyon** çağrısından döner, lock çağrısından DEĞİL.

**⛔ `adt_lock_check` BU SİSTEMDE İŞLEVSİZ:** `GET /sap/bc/adt/locks` → **HTTP 404**
(`ExceptionResourceNotFound`). Uç yok ⇒ tool bir kilidi **asla** tespit edemez ve sessizce
`locked: false` der. 2026-08-10'da bu "kilit yok" diye okundu. **404'ü "hayır" sayan
sessiz-başarısızlık** — buradaki `false` kanıt değildir.

**⛔ ÇAREN BİR SONRAKİ ENGELİ YARATIR.** Teşhis için kullanıcıya *"SE24'ten bak"* dendi → SE24
**düzenleme kilidi yarattı** → o kilit bir sonraki turu blokladı (`EU 510` gerçekten çıktı).
⇒ **GUI'de bir şey yaptırırken kapanışını da söyle:** *"aç → yap → **KAPAT** → SM12'yi kontrol et."*
Bir SAP ekranını açmak **durum yaratır**.

**📌 IS_LINK_UP** (`sap_adt_lib.py`): *"`IS_LINK_UP='X'` → obje, kullanıcının görevi OLMAYAN
YABANCI bir isteğe kayıtlı"* demektir. SAP'nin döndürdüğü `CORRNR` otoritedir; onunla savaşma.
(2026-08-10'da "K vs S görevi" diye bir tez kuruldu — **yanlıştı**; başarıyla yazılan objeler de
aynı `CORRNR`'ı raporluyordu.)

**Regresyonun ikinci, SESSİZ yüzeyi:** guard yürürlükteyken `clear_enqueue_lock()` de her sınıf
için başarısız oluyordu — istisnayı yutup `False` döndüğü için **hiç görünmeden.** Yani kilit
sorununu çözmek için başvurulan araç, yanlış teşhisi besliyordu. (Fixture V19 bunu bekçilik eder.)

**Çapa:** `tests/fixtures/lock_modification_support/run.py` (25 vektör; `--mutasyon` ile fırlatan
sürüme karşı 9 ayırt edici FAIL). Tanıma (casefold + TAM eşitlik) korunur ama **hiçbir değer
akışı kesmez**; §12.7 teşhisi 423'te basılır.

---

### 12.7c `423 InvalidLockHandle` CLASS push'ta — sebep transport DEĞİL, **PUT'un 1. denemesi** (2026-08-11; vaka: bir `ZSD0NN_CL_*_DOCU_RUN` sınıfı)

> ⛔ **BU BÖLÜM §12.7'yi İKİNCİ KEZ SINIRLANDIRIR.** §12.7 *"obje o transport'a kayıtlı değil"*
> der; bu vakada obje **kayıtlıydı** ve push **aynı transport'la** geçti. §12.7'nin teşhisi
> 2026-08-10'da bu vakaya uygulandı ve **saatler kaybettirdi.**

**Belirti:** `push_object.py` / MCP `adt_push_source` → LOCK **200** + handle döner, PUT
**4/4 yaklaşımda 423** *"Resource CLASS X is not locked (invalid lock handle: …)"*.
`E071` sorgusu objeyi kullanılan transport'ta **KAYITLI** gösterir, `E070`'te `TRSTATUS='D'`.

**KÖK SEBEP (kod-kanıtlı — `sap_adt_lib.py::set_object_source`, `transport_approaches`):**

| # | Yaklaşım | Bu vakada |
|---|---|---|
| 1 | **`X-sap-adt-transport` header'ı, `corrNr` query param'ı YOK** | SAP reddeder **ve lock handle'ı yakar** |
| 2 | `corrNr` query param'ı (= çalışan biçim) | **ölü handle** ile gider → 423 |
| 3 | header + param | ölü handle → 423 |
| 4 | transport'suz | ölü handle → 423 |

⇒ `423` **yaklaşım-sırasının artefaktıdır**, transport kaydının değil. Aynı istek biçimi (`corrNr`
query) **taze bir lock'la ilk seferde 200** verir.

**ÇALIŞAN YÖNTEM (CLASS için sıkı lock→PUT→unlock, TEK session — FM `adt-fugr-functions.md §2b`'nin
sınıf uyarlaması; o ders yalnız FM'e yazılmıştı, CLASS'a hiç uygulanmamıştı):**
1. `session.headers['X-sap-adt-sessiontype'] = 'stateful'` · `fetch_csrf_token(force_refresh=True)`
2. **ETag'i LOCK'TAN ÖNCE** çek: `GET /oo/classes/<c>/source/main?version=active` → `ETag`
   ⚠ **YENİ obje istisnası (2026-08-11 ölçümü):** obje **daha hiç aktive edilmemişse**
   (`adt_post_shell` ile yeni yaratılmış kabuk), `?version=active` **BAYAT bir ETag** verir ve
   PUT **412** döner: `Client ETag <A> does not match the object ETag <B>` (ölçülen: A/B yalnız
   son hanelerde ayrışıyordu — `…091040001000001` ↔ `…091041000000001`).
   ⇒ **Yeni objede ETag'i `version` parametresiz `GET`'ten al** (güncel sürüm). Kabuk→ilk-push
   akışında adım 2 böyle okunmalıdır; **aktive edilmiş objelerde `?version=active` doğrudur.**
   📌 Vaka: `ZEWM000_CL_PACI_ITEM_MOD` ilk push'u — parametresiz ETag ile **PUT 200**, 423 hiç
   görülmedi (yani bu vaka 423 değil **412** sınıfıdır; teşhisi karıştırma).
3. `POST /oo/classes/<c>?_action=LOCK&accessMode=MODIFY&corrNr=<TR>` → `LOCK_HANDLE`
4. **`PUT /oo/classes/<c>/source/main?lockHandle=<h>&corrNr=<TR>`** + `If-Match: <etag>` +
   `Content-Type: text/plain; charset=utf-8` → **200**
5. `POST /oo/classes/<c>?_action=UNLOCK&lockHandle=<h>` → sonra `adt_activate` (ayrı çağrı)

**DENENEN BAŞARISIZ (tekrarlama):**
| Deneme | Sonuç |
|---|---|
| `push_object.py` / MCP `adt_push_source` (generic `set_object_source`) | 423 ×4 |
| PUT'u `X-sap-adt-transport` header'ıyla, `corrNr` query'siz göndermek | 423 + handle yanar |
| `adt_lock_check` ile teşhis | `GET /adt/locks` → **404** (bkz. §12.7b) |

**⚠ İDDİANIN KAPSAMI (dürüst sınır):** yaklaşım-1'in handle'ı yaktığı **güçlü çıkarımdır**
(aynı biçim ölü handle'la 423, taze handle'la 200) ama tek başına izole edilmiş değildir:
sıkı-lock yolu ETag'i de farklı seçer (lib **inactive-önce** dener, sıkı yol **active** kullanır).
Hata kodu `412` değil `423` olduğu için ETag hipotezi zayıftır, **ama çürütülmemiştir.**

> **↑ Bu paragrafa 2026-08-11 eki:** ETag boyutunun **gerçek** olduğu artık ölçüldü — yeni bir
> sınıfta yanlış ETag seçimi **412** üretti (yukarıdaki adım-2 istisnası). Bu, iki hata kodunun
> **ayrı sebepleri** olduğunu doğruluyor: `423` = yanılmış lock handle · `412` = yanılmış ETag.
> Dolayısıyla yukarıdaki "ETag hipotezi zayıf" cümlesi **423 vakası için** geçerliliğini korur;
> ETag'in kendi başına bir hata sınıfı ürettiği ise ayrıca kanıtlanmıştır.

**TEŞHİS UYARISI — `<CORRNR/>` boşluğu SEBEP DEĞİL SONUÇTUR:** başarısız push sırasında lock
yanıtı `<CORRNR/>` boş döndü; **başarılı push'tan sonraki** temiz LOCK aynı objede
`<CORRNR>…</CORRNR><CORRUSER>…</CORRUSER>` **dolu** döndürdü. §12.7b'nin *"lock yanıtındaki alanlara
bakma"* kuralı `MODIFICATION_SUPPORT` gibi **CORRNR için de** geçerlidir.

**KİLİT HİJYENİ — `adt_lock_check` 404 verdiğinde pozitif kanıt üret:** iş bitince **taze bir LOCK
dene → 200 ⇒ sızmış/yabancı kilit YOK** (olsaydı `EU 510`/409 gelirdi) → hemen `UNLOCK`.
"Tool `locked: false` dedi" kanıt değildir (§12.7b sessiz-başarısızlık).
