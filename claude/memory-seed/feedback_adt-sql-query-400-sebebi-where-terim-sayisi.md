---
name: feedback_adt-sql-query-400-sebebi-where-terim-sayisi
description: "adt_sql_query 400'unun sebebi kolon sayisi ya da JOIN karmasikligi degil, WHERE TERIM SAYISI (olculdu 2/4 kosul OK, 7 kosul 400)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f07a9d9a-ccde-437b-818a-48086e4c73a7
---

`adt_sql_query` **400** dondugunde sebep **`WHERE` terim sayisidir** — kolon sayisi
ya da JOIN karmasikligi DEGIL.

Ayirt edici olcum (2026-09-06, <SISTEM>, `find_existing`'in JOIN'i):
- 4 tablolu JOIN + **2 kosul** → kostu
- 4 tablolu JOIN + **4 kosul** → kostu
- 4 tablolu JOIN + **7 kosul** → **400**

Karsi kanit (kolon sayisi degil): 8 kolonlu `SELECT vbeln, auart, vkorg, vtweg, spart,
waerk, vsbed, abrvw FROM vbak WHERE vbeln = '...'` sorunsuz kostu.

⚠ **ACIK / ACIKLANMADI:** `WHERE vbeln = 'X' AND vbtyp = 'E'` (yalnizca 2 terim) yine de
400 verdi; `WHERE vbtyp = 'E' AND vbeln > 'Y'` kostu. Bu cift aciklanmadi — yani terim
sayisi tek sebep olmayabilir, ama "geniş kolon listesi" ve "JOIN çok karmaşık"
teshisleri OLCUMLE YANLIS cikti.

**Why:** Yanlis teshis yanlis coz&uuml;me goturuyor — "JOIN cok karmasik" denip sorgu
parcalaniyor ya da daha kotusu programin ABAP tarafindaki SELECT'i "riskli" sanilip
gereksiz yere sadelestiriliyor. Oysa ABAP tarafindaki SELECT bu ARAC sinirindan
etkilenmez; sinir yalnizca ADT Data Preview ucundadir.

**How to apply:** 400 alinca once **WHERE terimlerini azalt** (parcalara bol, sonuclari
cagiran tarafta birlestir), kolon listesini degil. Bir programin canli SELECT'ini
dogrulayamiyorsan bunu *"JOIN calismiyor"* diye RAPORLAMA — **arac sinirini** raporla.
Bir 400'u "tabloya erisemiyorum" diye okumak `bulunamadi != yok` ihlaline goturur.
Ilgili: [[feedback_arac-basarisizligini-zararsiz-sayma]],
[[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]],
[[feedback_adt-include-objesi-prog-tipiyle-404-sahte-negatif]].

---

## EK ÖLÇÜM 2026-09-07 (<PAKET-F> ADIM-2, aynı sistem)

**Çalışan sürprizler — bunları "desteklenmiyor" sanıp deneme:**
- ⭐ **`NOT EXISTS` alt sorgusu ÇALIŞIYOR** (400 vermiyor):
  ```sql
  SELECT m~matnr FROM mara AS m WHERE m~matnr LIKE 'S%'
    AND NOT EXISTS ( SELECT * FROM mvke AS v WHERE v~matnr = m~matnr AND v~vkorg = '1400' )
  ```
  "Şu tabloda olup bunda olmayanlar" sorusunu tek turda cevaplıyor — iki listeyi çekip
  elde farkını almaya gerek yok.

**400 veren, ama terim sayısıyla açıklanamayan yeni vakalar:**
- `SELECT c~sndprn, s~stamid, s~stamno, COUNT(*) ... JOIN ... GROUP BY ...` → 400/500.
  Aynı JOIN deseni önceki turlarda çalışmıştı. **WHERE tek terime düşürülünce** (`s~stamno='035'`)
  koştu. ⇒ `GROUP BY` + JOIN kombinasyonu terim bütçesini daraltıyor.
- `SELECT DISTINCT stapa1, stapa2, stapa3 FROM edids WHERE stamid='V4' AND stamno='035'` → 400;
  **kolon 2'ye + WHERE 1 terime** düşürülünce koştu. ⇒ `DISTINCT` de bütçeyi daraltıyor.
- ⛔ **Baştan joker `LIKE` 400 verdi:** `SELECT lifnr, knref, ablad, kunnr, vkorg, vtweg, spart
  FROM t661w WHERE knref LIKE '%152%'` → 400 (**tek terim**). Aynı tablo `WHERE kunnr = '...'`
  ile sorunsuz koştu. ⇒ Sağ-joker (`'S%'`) çalışıyor, **sol-joker (`'%...'`) çalışmıyor**.
- ⚠ **400 her zaman YAPISAL DEĞİL:** `SELECT COUNT(*) FROM mara WHERE matnr LIKE 'S%'` bir
  turda 400 verdi, **aynı sorgu tekrarında koştu**. Bir kez 400 alınca sorguyu yeniden
  yazmadan **bir kez tekrar dene**; yoksa çalışan bir deseni yanlışlıkla "desteklenmiyor"
  diye kaydedersin.

**Desteklenmeyen (ölçüldü):** `substring(...)` → 400. `EDID4.SDATA` dilimlemesi araçta değil,
**okuduktan sonra Python'da** yapılır (`DTINT2` ile birlikte çekilir).

---

## EK ÖLÇÜM 2026-09-08 (EWM veri yüzeyi turu, aynı sistem — 126 çağrı)

⭐ **BÜTÇE YALNIZ `WHERE` DEĞİL — SELECT ALAN SAYISI DA SAYILIYOR** (bu kaydın başlığını daraltır):
**7 alan + 1 WHERE → 400** · **6 alan + 1 WHERE → 500** · **4 alan + 1 WHERE → OK**.
Lider aynı gün bağımsız doğruladı: `lips`'ten 14 alan → 500, 8 alan → 400, **6 alan → OK**.
⇒ Tek bir bütçe var; aşıldığında **400 de 500 de** gelebiliyor. "500 = başka bir sorun"
diye ayırma.

**Yeni ölçülen beş kısıt:**
| Kısıt | Sonuç | Çalışan biçim |
|---|---|---|
| `COUNT(*) **AS** CNT` | **500** | çıplak `SELECT COUNT(*)` |
| `GROUP BY` (JOIN'siz, sade) | **400** | değer başına ayrı `COUNT` |
| **kolon-kolon** karşılaştırma (`WHERE vrkme <> meins`) | **400** | kolon-literal (`WHERE umvkz > 1`) |
| bazı alanlarda `<>` (`handlingunitindicator <> 'A'`) | **400** | `= 'A'` ölçüp **çıkarma** yap |
| `SELECT *` bazı tablolarda (`T320`) | **400** | `adt_table_read T320` → OK |

⭐ **Namespace'li tablo:** `/SCWM/*` **tırnaksız, küçük harfle** yazılır —
`SELECT COUNT(*) FROM /scwm/aqua` çalışır. (Tırnak/büyük harf gerekmiyor.)

**How to apply (ek):** kolon-kolon karşılaştırması gerekiyorsa **dolaylı ölç** — ilgili
çevrim/fark kolonunu literal ile sına (ör. `vrkme<>meins` yerine `umvkz>1 OR umvkn>1`) ve
raporda **dolaylı olduğunu yaz**. `<>` reddedilirse `=` ile ölçüp toplamdan çıkar; sonucu
"aritmetik fark" diye niteleyerek ver, doğrudan ölçüm gibi sunma.

Kanonik ayrıntı: `governance/infra-findings.md` → **Q274**.

---

## EK ÖLÇÜM 2026-09-10 (<PAKET-B> AG→WE/ZW türetme turu, aynı sistem)

⭐ **YENİ, BÜTÇEDEN BAĞIMSIZ SEBEP: released CDS view'ını JOIN OPERANDI yapmak.**
`i_custsalespartnerfunc_2`'yi JOIN'e koyan her sorgu **400** verdi — 3 tablolu da,
**2 tablolu da**. Bu vaka bu kaydın diğer sebeplerinin HİÇBİRİYLE açıklanmıyor:
- `WHERE`'de yalnız **2 terim** vardı (bütçe sorunu değil),
- kolon adları **tahmin değildi** — *aynı adlarla tek-tablo sorgusu ÇALIŞTI*,
- ABAP keyword çakışması yoktu.

**Ayırt edici:** aynı released view **tek başına** (JOIN'siz) sorgulanınca sorunsuz koşuyor;
yalnız JOIN operandı olunca 400. ⇒ Sınır "released CDS okunamıyor" DEĞİL, *"freestyle
data-preview onu JOIN'de kabul etmiyor"*.

**How to apply:** Released bir CDS'i JOIN'li ölçmen gerekiyorsa **eşdeğer semantiği ham
tablolarla kur** (bu turda `knvp ⨝ zsd001_t_setype` koştu) ve raporda **ham tabloyla
ölçtüğünü YAZ** — released view'ın DCL'i (`#CHECK`) ham tabloda yok, yani iki ölçüm
farklı yetki rejiminde koşar; sayılar eşit çıksa bile bu **aynı ölçüm değildir**.
⚠ Bu turda released↔ham satır sayıları eşit çıktı (WE 90 / ZW 18) ama **tek kullanıcıyla**
(`<SAP_USER>`) — "hiçbir kullanıcı için süzmez" SONUCU ÇIKARILAMAZ. İlgili:
[[feedback_check-annotasyonu-fail-yonunu-belirlemez]].

---

## EK ÖLÇÜM 2026-09-11 (<PAKET-D> parti birleştirme doğrulaması, aynı sistem)

⭐ **PARALEL GÖNDERİM 400/500 ÜRETİYOR — sorgu biçimi değil.** Gateway doğrulama SQL'lerini paralel attı:
S0'ın ikinci sorgusu **500**, BE-1b **400** → aynı metinler **seri** tekrarda koştu. BE-3 brüt koşumu seri olarak
500 → 400 → araya basit bir sorgu girince 3. denemede **71** (doğru sonuç).
Ayrıca önceki kaydın aksine bu turda `GROUP BY … HAVING COUNT(*) > 1` (view entity üzerinde) **koştu**
(0 satır; pozitif kontrol `>= 1` → 99 grup); bug-expert aynı biçime `zsd001_v_dlv` üzerinde 500 almıştı.
Aynı günkü backend ölçümü: `zsd001_v_dlv` LEFT JOIN + `IS NULL` anti-join **sahte yetim** (50) listeledi →
sayım farkı yöntemi (alt 59 − INNER JOIN 59) doğru sonucu verdi.

**How to apply (ek):** doğrulama sorgularını **seri** koş. 400/500 alınca biçimi değiştirmeden önce
seri ve araya basit sorgu koyarak tekrar dene; iki tekrarda da düşmezse bütçe/biçim sebebine bak.
Anti-join için `LEFT JOIN … IS NULL` kullanma, **sayım farkı** kullan.

⛔ **AYNI GÜN 2. ÖLÇÜM — "paralel = flaky" hükmü ZAYIFLADI, sebebi DOĞRULANMADI.** Lider brifine alias'sız
`SELECT COUNT(*), SUM( a ), SUM( b ), SUM( c ) FROM zsd001_c_delivery_sum` yazdı → MCP'de 3×, ayrı süreçte 1× **400**,
ham metin: *"If inline declarations or "NEW" with generic reference are used, all expressions in the projection
list must have an alias name."* `AS cnt/qty/ntg/brg` eklenince iki kanalda da ilk denemede koştu.
⇒ **Birden çok ifade/aggregate içeren projeksiyonda HER ifadeye alias ver** (09-08'deki "`COUNT(*) AS CNT` → 500"
tek-ifade gözlemiyle çelişiyor; bugün aliased çoklu projeksiyon koştu). Aynı turda MCP'de tek başına
`SUM( ItemNetWeight )` bir kez 500 bir kez 400, ayrı süreçte koştu ⇒ MCP oturumu da kaynak olabilir.
**400 alınca ÖNCE hata GÖVDESİNİ oku** (sebep çoğu zaman metinde yazıyor) — sayı tahmini yapma.

---

## EK ÖLÇÜM 2026-09-16 (<PAKET-A> [İşle] teşhis turu, aynı sistem)

⛔ **YENİ SEBEP — `SELECT *`'IN TEKRARI SİSTEM KAYNAĞI TÜKETİYOR (aracın kendi yan etkisi).**
`SELECT * FROM ZSD001_C_PORTAL_HEAD` **500** verdi. Sebep sorguda ya da view'da DEĞİLDİ:
`adt_dump_list` **`GENERATE_SUBPOOL_DIR_FULL`** gösterdi — `CL_ADT_DP_OPEN_SQL_HANDLER`
kaynaklı **3 dump**. Yani art arda `SELECT *` çağrıları **geçici subroutine havuzunu**
tüketmiş; 500 o tükenmenin sonucu.

⚠ **Bu tuzağın tehlikesi teşhisi YANLIŞ HEDEFE çevirmesi:** 500 gelince refleks olarak
*"CDS view bozuk"* diye okundu ve az kalsın masum bir view suçlanacaktı. Gerçek fail
**ölçüm aracının kendisiydi**.

**How to apply (ek):** `adt_sql_query`'de **`SELECT *` KULLANMA** — açık kolon listesi ver
(bütçe gereği zaten 4-6 alan). Kolonları bilmiyorsan **bir kez** küçük `SELECT *` ile keşfet,
sonra açık listeye geç; keşfi tekrarlama. 500 alınca **`adt_dump_list`'e BAK** — dump
sorgunun değil aracın adına yazılıysa sebep tükenmedir, sorgu değil: biçimi değiştirmek
işe yaramaz, **bekle/seyrelt**. İlgili: [[feedback_arac-basarisizligini-zararsiz-sayma]].

⭐ **`<` ve `>` KARAKTERLERİ HTML-ESCAPE EDİLİYOR.** `WHERE datum < '19000101'` →
**HTTP 400** *"A Boolean expression was expected"*. Sebep sorgu mantığı değil, araç
katmanının karşılaştırma operatörünü kaçırması. **Çalışan biçim: `BETWEEN` / `NOT BETWEEN`.**
(Not: 09-08 ölçümünde `<>`'in bazı alanlarda 400 verdiği yazılıydı — bu onun *mekanizmasını*
açıklıyor olabilir, ama bu tur `<>` için ayrıca DOĞRULANMADI.)

⛔ **`LIKE` bir `DATS` kolonunda tip-uyumsuzluğu hatası verir** (`WHERE datum LIKE '%.%'`).
DATS içinde çöp veri aramak için `LIKE` kullanılamaz — `NOT BETWEEN '19000101' AND '99991231'`
ya da alanı `CHAR`'a çeviren bir view üzerinden git.
