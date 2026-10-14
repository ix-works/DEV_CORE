---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-10-12
status: active
---

# HOWTO — ATC bulgusu düzeltme kalıpları (önce FAE / iç içe okuma)

> **Ne:** sık ATC bulgu sınıfları için **gözden geçirilmiş düzeltme kalıbı** + *"düzeltmeden önce neyi
> okumadan emin olamazsın"* listesi + *"bu kalıbın yanlış olabileceğini gösteren işaretler"*.
> **Ne değil:** gate ya da otomatik düzeltici değildir (ADR 0019). Kalıp **öneridir**; her düzeltme
> bug-gate + canlı ATC yeniden koşumuyla kanıtlanır.
> Fikir kaynağı: dış bir pazardaki ATC düzeltme kalıbı dosyaları — **yalnız yapı** alındı (kalıp / gerekli
> bağlam / düşük güven işareti); kontrol kimliği listeleri ve güven oranları **alınmadı** (doğrulanamadı).

## 0. Genel kurallar (her bulgu sınıfı)

- **Priority-1 zorunlu düzeltilir;** Priority-2/3 ancak kullanıcı onayıyla geçilir — `checklists/bug-checklist-backend.md` **BE-12**.
- **Bulgunun YAZILDIĞI sınıfı doğru oku:** "iç içe veritabanı okuması" ailesi bulguyu döngüyü içeren
  sınıfa değil **`SELECT`'i içeren metodun sınıfına** yazar ⇒ önce/sonra sayımını orada yap.
- **Sınıflandırma kimlikle yapılır, metinle değil:** ADT ATC sonucunda `checkId` bir **GUID**'dir;
  "metinde `FOR ALL ENTRIES` geçiyor mu" türü arama kümelemeyi bozar ⇒ GUID + mesaj metni birlikte.
- **Önce/sonra karşılaştırmasında satır numarası kullanma:** bir satır kaydırması her bulguyu "yeni"
  gösterir. Parmak izi = obje + birim (metot/include) + `checkId` + mesaj.
- **Pseudo-comment / pragma ile muafiyet** yalnız kullanıcı onayıyla ve satır üstünde gerekçe yorumuyla.
  Muafiyet adı tahmin edilmez — denetim sınıfının kaynağında `#EC` sabiti aranır. Bir tüketici projede
  2026-09-28'de S/4 alan uzunluğu genişletme bulgusu için `"#EC CI_FLDEXT_OK[<not no>]` biçiminin
  çalıştığı (bulgunun push sonrası kalktığı) ölçüldü — köşeli parantezde **not numarası** şarttır.
  ⚠ **Pseudo-comment sessizce YOK SAYILIYORSA** ilk bakılacak yer: denetlenen sistemde **ve** merkezi
  ATC sisteminde ilgili SAP notunun uygulanmış olması (dış kaynak SAP Note 2754597 / KBA 3624162'yi
  gösteriyor — numaralar **DOĞRULANAMADI**, uygulamadan önce SAP'de oku).
- **"Incorrect Pretty Print state"** birim başına yalnız İLK farkı bildirir — satırı düzeltmek kapatmaz;
  birimi SAP Pretty Printer ucuyla bütün olarak biçimle (`adt-classes.md` Pretty Printer bölümü).

## 1. İç içe veritabanı okuması (döngü içinde `SELECT`) — EN SIK Priority-1

**Kalıp:** döngüden ÖNCE tek toplu okuma → bellekte erişim.

```abap
" ÖNCE: LOOP AT lt_items INTO ls_item. SELECT SINGLE … WHERE key = ls_item-key. … ENDLOOP.
TYPES tt_lookup TYPE HASHED TABLE OF ty_lookup WITH UNIQUE KEY key.   " erişim anahtarıyla tipli
DATA lt_lookup TYPE tt_lookup.
IF lt_items IS NOT INITIAL.                        " ⛔ boş sürücü tablo = TÜM tabloyu okur
  SELECT key, field1, field2
    FROM <tablo_ya_da_released_cds>
    FOR ALL ENTRIES IN @lt_items
    WHERE key = @lt_items-key
    INTO TABLE @lt_lookup.
ENDIF.
LOOP AT lt_items INTO DATA(ls_item).
  READ TABLE lt_lookup INTO DATA(ls_hit) WITH TABLE KEY key = ls_item-key.
  IF sy-subrc <> 0.
    CONTINUE.                                      " ⛔ bulunamadıysa ls_hit ÖNCEKİ turun değerini taşır
  ENDIF.
  " … ls_hit kullanımı …
ENDLOOP.
" Standart tablo kalacaksa: okumadan sonra SORT lt_lookup BY key + BINARY SEARCH + aynı sy-subrc kontrolü (§4).
" Anahtar tekil değilse HASHED UNIQUE yerine SORTED NON-UNIQUE KEY seç: UNIQUE tabloya yinelenen
" anahtar SELECT … INTO TABLE'da çalışma zamanı hatasıdır (istisna adı bu evde ölçülmedi).
```

**Okumadan emin olamazsın (gerekli bağlam):**
- Sürücü tablo **boş olabilir mi?** Boşsa FAE koşulsuz okur — `coding-patterns.md` §24.
- Okunan değer **toplanıyor mu?** FAE sonuç kümesine örtük **DISTINCT** uygular; SELECT listesinde
  kaynağın tam tekil anahtarı yoksa eşit değerli satırlar teke iner, toplam eksik çıkar — **BE-44**.
- `GROUP BY` / aggregate gerekiyor mu? FAE ile birlikte yazılamaz — `coding-patterns.md` §23 (JOIN `@itab` yolu).
- Okuma bir **standart CDS**'ten mi? DCL reddi hata değil 0 satır döner — `adt-cds.md` CDS-DCL-01/BE-67.

**Bu kalıbın YANLIŞ olabileceğini gösteren işaretler (düşük güven):**
- Döngü içindeki okuma **önceki turun yazdığı** veriyi görmek zorunda (aynı LUW'da sıralı bağımlılık).
- Sürücü tablo çok büyük ve okunan tablo küçük — tamamını bir kez okumak daha doğru olabilir.
- Okuma bir metot çağrısının arkasında — düzeltme çağrılanın sınıfında yapılır, döngüyü taşımak bulguyu taşımaz.

## 2. `SELECT *`

**Kalıp:** açık alan listesi. **Gerekli bağlam:** okunan yapının **tüm tüketicileri** — yapı bir
metottan dönüyor ya da başka bir rutine aktarılıyorsa hangi alanların kullanıldığı oradan okunur.
**Düşük güven:** hedef `CORRESPONDING`/dinamik atama ile dolduruluyor, ya da yapı bir arayüz
parametresi (tüketiciler paket dışında).

## 3. Alan uzunluğu genişletmesi (ör. malzeme numarası)

**Kalıp:** sabit uzunluklu yardımcı değişken yerine veri elemanı tipi; `+off(len)` alt-dize ve
`WRITE … TO` ile kesmeyi kaldır. **Gerekli bağlam:** değer gerçekten genişletilmiş uzunlukta taşınıyor
mu (yoksa bulgu kullanıcı onayıyla muaf tutulabilir — §0). **Düşük güven:** değer bir dış arayüzde
(IDoc/dosya) sabit genişlikli alana yazılıyor — kesme orada **sözleşmenin** parçası olabilir; sessiz
kesilme yerine açık kontrol + hata mesajı.

## 4. Sıralama varsayımı

**Kalıp:** `SELECT SINGLE`'ı tam anahtarla yaz; çok satırlı okumada sıra gerekiyorsa `ORDER BY`;
`BINARY SEARCH` öncesi aynı anahtarla `SORT`. **Gerekli bağlam:** tablonun anahtarı (DDIC) ve
`READ TABLE … BINARY SEARCH` çağrılarının kullandığı anahtar. **Düşük güven:** `WITH EMPTY KEY`
tabloda ölçütsüz `SORT`/`DELETE ADJACENT DUPLICATES`.

## 5. Toplu düzeltme yapılacaksa

Çok sayıda bulgunun yapay zekâ ile toplu düzeltilmesi planlanıyorsa iş **kuyruk-dikiş sözleşmesiyle**
yürür: [`howto-kuyruk-dikis-sozlesmesi.md`](howto-kuyruk-dikis-sozlesmesi.md) — model kararları dosyada,
doğrulama kodda, cevapsız bulgu açık kalır. Tek yazıcı + bug-gate + reviewer pre-flight şartları aynen geçerlidir.

## İlgili

- [`coding-patterns.md`](coding-patterns.md) §23-§24 · [`checklists/bug-checklist-backend.md`](checklists/bug-checklist-backend.md) BE-12 · BE-31 · BE-44
- prior-art: bulundu (dağınık) — BE-12/BE-44, `coding-patterns.md` §23-24 ve ATC tohum dersleri; ayrı bir düzeltme kalıbı sayfası yoktu.
