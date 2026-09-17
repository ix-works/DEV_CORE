---
name: feedback_sadl-gateway-dats-donusum-hatasi-tum-entity-seti-oldurur
description: "Gateway'in 'In the context of Data Services an unknown internal server error occurred' hatasi = SADL donusum hatasi; TEK bozuk DATS satiri butun entity setini oldurur, ABAP dump YAZILMAZ; teshis $skip bisection + tek-alan $select"
metadata:
  node_type: memory
  type: feedback
---

**Belirti:** OData/Fiori ekrani acilmiyor, mesaj:
*"In the context of Data Services an unknown internal server error occurred"*.
**ST22'de dump YOK**, SAP tarafinda hicbir iz yok — bu yuzden "kod bozuk" sanilip
CDS/controller saatlerce bosuna okunur.

**Mekanizma (2026-09-16, <SISTEM>/100, ZSD001 `PortalDevral` butonu):**
SADL, DDIC tipini OData tipine cevirirken (`DATS` → `Edm.DateTime`) exception aliyor ve
**yutuyor**; Gateway onu bu jenerik metne sariyor. Kok neden **VERI**, kod degil:
`ZSD001_T_FITORDH.DATUM` alaninda **`'07.09.26'`** duruyordu (kardes satirlar `20260825`).
⭐ **8 karakterlik tarih-olmayan bir deger bir `DATS` alanina FIZIKSEL OLARAK SIGAR** —
DDIC (`ROLLNAME=DATUM, INTTYPE='D', LENG 8`) bunu reddetmez, SE16N/eski yukleyici yazabilir.
Hata ancak **OData'ya cikarken** dogar.

⛔ **TEK satir BUTUN entity setini oldurur** — 4 satirin 3'u saglamdi, ekran yine de hic
acilmadi. "Bazi kayitlar gelmiyor" degil, **hicbir sey gelmiyor**.

**Why:** Hatanin metni sebeple ilgili SIFIR bilgi tasir ve dump olmadigi icin normal ABAP
teshis refleksleri (ST22, where-used, kod okuma) **tanim geregi bos doner**. Yanlis katmani
(CDS view / FE controller) sucla_yip tur kaybetmek bu hatanin varsayilan sonucudur.

**How to apply — teshis receti (ucu de OData ucundan, ABAP'tan degil):**
1. `$top`/`$skip` ile **ikili arama**: `$skip=0,1,2…` → hangi SATIR oldurdugunu bul.
   (FE cogu zaman `$top` gondermez ⇒ tum kume cekilir ⇒ tek satir hepsini goturur.)
2. O satirda **alan alan `$select`**: her alani tek basina iste → hangi ALAN oldurdugunu bul.
   Saglam alanlar 200 doner, bozuk alan 500.
3. Bulunan alani **ham tabloda** oku (`adt_sql_query`, acik kolon listesi) ve DDIC tipiyle
   karsilastir. `$orderby`'i sucla_madan once cikar ve test et — bu vakada masumdu.
4. Duzeltme **veridir**: Z tablosuysa SE16N'den duzelt/sil (ADR 0005-B standart tablo
   degil). Standart tabloysa BAPI/transaction yolunu ara.

⚠ **Ayni tabloda `ZFIYAT` alani da cop tasiyordu (`2026-08-73`) ama ZARARSIZDI** — cunku
`CHAR12`. ⇒ Kural *"cop veri patlatir"* degil, **"cop veri TIPI DONUSTURULEN alandaysa
patlatir"**. Tarama yaparken tip-donusturulen alanlara (DATS/TIMS/DEC/QUAN) bak.

**Sertlestirme (AYRI karar, otomatik yapma):** bir bozuk satirin tum ekrani oldurmesi
tasarim kusurudur; CDS'te alani `CHAR`'a cevirip FE'de tolere etmek mumkun (bu vakada FE'nin
`_fmtPortalDate`'i zaten hem `/Date(...)/` hem duz string kabul ediyordu). Ama bu
**davranis degisikligidir** — kullaniciya sor, kendiliginden yapma.

Ilgili: [[feedback_arac-basarisizligini-zararsiz-sayma]] ·
[[feedback_metadata-alan-dogrulama-tip-kapsamli-olmali]] ·
[[feedback_adt-sql-query-400-sebebi-where-terim-sayisi]]
