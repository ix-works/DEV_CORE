---
name: feedback_adt-sql-query-400-sebebi-where-terim-sayisi
description: "adt_sql_query 400: kök sebep SATIR UZUNLUĞU — ADT freestyle tek satırı 255. karakterde keser; token ortası = 400, geçerli sınır = kırpılmış sorgu SESSİZCE koşar (ok:true, YANLIŞ veri). 'WHERE terim sayısı' ve 'anti-join sahte sonuç' teşhisleri ÇÜRÜDÜ (ikisi de kırpma). Çare: satırlara böl (devam satırı sütun-1 `*` ile başlamaz); core #312 araç kendisi böler (MCP restart şart)"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

## ⭐ GÜNCEL KURAL (2026-10-03 — önce bunu oku)

1. **Kök sebep satır uzunluğu.** ADT freestyle ucu (`/sap/bc/adt/datapreview/freestyle`) sorgu
   metnini **satır satır** okur ve **255 karakterden uzun satırın devamını keser**; hata metni
   kesimin düştüğü kelimeyi gösterir, sebebi değil. Dış teyit: vibing-steampunk issue #239 +
   SAP Note 2807133 (`CL_ADT_DP_FREESTYLE_RES` gövdeyi CHAR255 satırlara çevirir).
2. **255 aşımı 400 VERMEYEBİLİR.** Kesim **token ortasına** düşerse 400; **geçerli bir sınıra**
   düşerse SAP kırpılmış sorguyu koşar ve `ok:true` döner — **hata yok, veri yanlış** (düşen
   kuyruk: JOIN koşulu · OR dalı · süzgeç · `IS NULL` · kolon). Uzun satırlı bir sorgunun
   `ok:true`'su tek başına **kanıt değildir**.
3. **Çare: her satır <255 olacak biçimde böl.** ⛔ Devam satırını **sütun-1 `*`** ile başlatma —
   freestyle onu **tam-satır yorumu** sayar (`"` de satır-sonu yorumudur): `COUNT(` ⏎ `* )` →
   yanıltıcı 400 *"INTO is invalid here"*; aynı metin ` * )` (tek boşluk önekli) → 200.
4. **Araç düzeltmesi (core PR #312):** `sap_adt_lib.sql_satirlarini_kir` gönderimden önce uzun
   satırı literal/yorum DIŞINDAKİ boşluktan kırar, `*` ile başlayan devam satırına tek boşluk
   öneki koyar; tek atom (literal/yorum) 255'i aşıyorsa istek GİTMEZ (`SQLSatirKirilamadi`).
   ⚠ **MCP sunucusu yeniden başlatılmadan** eski kod koşmaya devam eder ⇒ #312 öncesi koşan
   oturumda >255 kr satırlı sorguyu **elle böl**.
5. **400 alınca önce `sap_error.message`'ı oku** (#312'den beri gövde kırpılmıyor). Terim/kolon
   sayısını azaltmak bir çözüm DEĞİL. Kısa (≤255) satırda gelen 400 başka sebeplidir — aşağıdaki
   "hâlâ geçerli" ölçümlere bak.

Son-doğrulama: 2026-10-03 · Applies-to: `adt_sql_query` / ADT data-preview freestyle (her profil)

## Kontrol gruplu ölçüm (2026-10-03, DEV, yalnız `T000`)

| Girdi | Sonuç |
|---|---|
| 213 kr tek satır | 200 |
| 309 kr tek satır, yalnız AND | **400** `A Boolean expression was expected in "MTEX"` — `mtext` 0-tabanlı indeks 251'de (252. karakter) başlıyor; hata yalnız ilk 4 harfi (`MTEX` = 252-255) gösteriyor ⇒ kesim tam 255'te (indeks tabanı hata metninden çıkarıldı, sorgu yeniden koşulmadı) |
| aynı sorgu satırlara bölünmüş | 200 |
| 288 kr tek satır, 14 `OR` | **400** `"O" is invalid here` — 255. karakter `OR`'un `O`'su |
| 252 kr tek satır, **13 `OR`** | **200** ⇒ "5+ OR → 400" teşhisi çürüdü |
| 273 kr tek satır, son koşul `AND mandt = '999'` | `ok:true`, `row_count:1` — **YANLIŞ** (son koşul düştü) |
| aynı sorgu, son koşuldan önce satır sonu | `row_count:0` — **DOĞRU** |

Geçmiş tarama (bir makinedeki transkriptler): >255 kr satırlı **229** çağrının 222'si hata,
**7'si `ok:true` kırpılmış** sonuç döndürmüş.

## ⛔ ÇÜRÜYEN TEŞHİSLER (bu kaydın eski gövdesi — kullanma)

- **"400'ün sebebi WHERE terim sayısıdır" (2026-09-06) — ÇÜRÜDÜ.** Dayanak çift: "4 koşul koştu"
  sorgusu **285 kr**'ydi (255'te geçerli sınırda kesildi → 3 koşulla SESSİZCE koştu); "7 koşul →
  400" sorgusu **331 kr**'ydi (255'te `a|~kunnr` token ortasında kesildi). Ölçülen şey terim
  sayısı değil satır uzunluğuydu.
- **"`LEFT JOIN … IS NULL` anti-join freestyle'da sahte sonuç verir, sayım farkı kullan"
  (2026-09-11) — YANLIŞ.** "Sahte yetim" listesinin sebebi: **282 kr**'lik tek satırda
  `AND p~… IS NULL` kuyruğu 255'te düştü → sorgu "tüm alt kalemler"e dönüştü. Doğru biçimde
  (bölünmüş) yeniden koşum 0 yetim verdi; pozitif kontrol (ON'a imkânsız koşul) anti-join'in
  bütün satırları döndürdüğünü gösterdi ⇒ anti-join freestyle'da **doğru çalışır**, satırları
  <255 tut. Sayım farkı geçerli ama zorunlu değil. (Kanonik CDS anti-join'i
  `playbook/adt-cds.md`'dedir; bu düzeltme onunla tutarlıdır.)
- **"Released CDS view'ı JOIN operandı yapınca 400" (2026-09-10) — büyük olasılıkla aynı kırpma,
  DOĞRULANAMADI.** Dayanak üç sorgu 472/401/323 kr, üçü de 255'te token ortasında kesiliyor;
  karşı kanıt aynı gün 255 kr'lik bir released view iki kez JOIN'li `ok:true`. Canlıda yeniden
  üretilmedi ⇒ kural olarak KULLANMA; gerekirse satırlara bölüp yeniden ölç.
- **"Bütçe" gözlemleri** (2026-09-07/08: "7 alan + 1 WHERE → 400", "`DISTINCT` / `GROUP BY` + JOIN
  bütçeyi daraltır") ve 2026-09-16'daki *"`<` HTML-escape ediliyor → 'A Boolean expression was
  expected'"* teşhisi aynı sınırın imzasını taşıyor (252 kr'lik tek satırda `<>` 200 döndü; `<`
  tek başına ölçülmedi) — **yeniden ölçülmedi (DOĞRULANAMADI)**. Uzun sorguda gördüysen önce böl.
- **AÇIK / ÖLÇÜLEMEDİ:** kısa `WHERE vbeln = 'X' AND vbtyp = 'E'` (2 terim) 400 verdi, `WHERE
  vbtyp = 'E' AND vbeln > 'Y'` koştu (2026-09-06). Sorgu metni izlenemedi ⇒ kırpmayla açıklanıp
  açıklanmadığı bilinmiyor; satır kısaysa sebep başkadır.

**Why:** Geçmiş taramadaki 7 sessiz kırpmanın **hiçbiri bir karara girmedi** — zarar sonuç
düzeyinde değil, **mekanizma** düzeyindeydi: kırpma yanlış adlandırıldı ve o yanlış ad kalıcı
kurallara yazıldı. Yanlış teşhis yanlış çözüme götürdü — terim azaltıldı, sorgu parçalandı, doğru çalışan
anti-join "araç tuzağı" diye yasaklandı; en kötüsü, 255 aşımı `ok:true` döndüğünde **yanlış veri
doğru sanıldı**. ABAP tarafındaki SELECT bu sınırdan etkilenmez; sınır yalnız ADT data-preview
ucundadır. Bir 400'ü "tabloya erişemiyorum" ya da "JOIN çalışmıyor" diye raporlama — araç sınırını
raporla. İlgili: [[feedback_arac-basarisizligini-zararsiz-sayma]],
[[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]].

---

## HÂLÂ GEÇERLİ ÖLÇÜMLER (kısa satırda; aynı sistem)

**Çalışan sürprizler — "desteklenmiyor" sanıp deneme:**
- ⭐ **`NOT EXISTS` alt sorgusu ÇALIŞIYOR** (2026-09-07):
  ```sql
  SELECT m~matnr FROM mara AS m WHERE m~matnr LIKE 'S%'
    AND NOT EXISTS ( SELECT * FROM mvke AS v WHERE v~matnr = m~matnr AND v~vkorg = '1400' )
  ```
- ⭐ **Namespace'li tablo** `/SCWM/*` **tırnaksız, küçük harfle** yazılır —
  `SELECT COUNT(*) FROM /scwm/aqua` çalışır (2026-09-08).
- `GROUP BY … HAVING COUNT(*) > 1` (view entity üzerinde) koştu (2026-09-11).

**Kısa satırda 400/500 veren biçimler (ölçüldü):**
- ⛔ **Baştan joker `LIKE`** (`WHERE knref LIKE '%152%'`, tek terim, kısa satır) → 400; sağ-joker
  (`'S%'`) çalışıyor (2026-09-07).
- `substring(...)` → 400 — dilimlemeyi okuduktan sonra Python'da yap.
- **Birden çok ifade/aggregate içeren projeksiyonda HER ifadeye alias ver:** alias'sız
  `SELECT COUNT(*), SUM( a ), … FROM <view>` → 400, ham metin *"…all expressions in the projection
  list must have an alias name."*; `AS cnt/…` eklenince ilk denemede koştu (2026-09-11).
- **Kolon-kolon karşılaştırma** (`WHERE vrkme <> meins`) → 400 (2026-09-08): dolaylı ölç (ilgili
  çevrim kolonunu literal ile sına) ve raporda **dolaylı olduğunu yaz**.
- ⛔ **`LIKE` bir `DATS` kolonunda** tip-uyumsuzluğu hatası verir — `NOT BETWEEN '19000101' AND
  '99991231'` kullan (2026-09-16).

**Ölçüm aracının kendi yan etkisi:**
- ⛔ **Art arda `SELECT *` geçici subroutine havuzunu tüketir** → 500; `adt_dump_list`'te
  `GENERATE_SUBPOOL_DIR_FULL` (`CL_ADT_DP_OPEN_SQL_HANDLER` kaynaklı) görünür. Tehlikesi teşhisi
  yanlış hedefe çevirmesi ("CDS view bozuk"). **`SELECT *` KULLANMA** — açık kolon listesi ver;
  kolonları bilmiyorsan bir kez küçük `SELECT *` ile keşfet. 500 alınca **`adt_dump_list`'e BAK**:
  dump aracın adına yazılıysa sebep tükenmedir — biçimi değiştirme, **bekle/seyrelt** (2026-09-16).
  (Kısa `SELECT * FROM T320` de bir turda 400 verdi, `adt_table_read T320` koştu — 2026-09-08.)
- ⚠ **400/500 her zaman yapısal değil:** aynı kısa sorgu bir turda 400, tekrarında koştu; paralel
  gönderimde 400/500 görüldü, seri tekrarda koştu (2026-09-07/11). Bir kez 400 alınca sorguyu
  yeniden yazmadan **bir kez seri tekrar dene**; "paralel = flaky" hükmünün sebebi DOĞRULANMADI.

**Released view ↔ ham tablo kıyası** (yetki rejimi): released view'ın DCL'i (`#CHECK`) ham tabloda
yoktur — ikisini aynı sayıyla bulmak tek kullanıcıyla "hiçbir kullanıcı için süzmez" sonucunu
VERMEZ. İlgili: [[feedback_check-annotasyonu-fail-yonunu-belirlemez]].

Tüketici projede kanonik ayrıntı (varsa): `governance/infra-findings.md` → Q274.
