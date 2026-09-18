---
name: feedback_run-sql-query-max-rows-sessiz-kirpma
description: run_sql_query.py varsayilani --max-rows 100; kirpma SESSIZDIR ve "kayit yok" bulgusu gibi okunur (2026-09-07 vakasi: VBPA 551 satirin ilk 100'u -> "80 belgede AG partneri yok" YANLIS bulgusu)
metadata:
  node_type: memory
  type: feedback
---

`core/scripts/run_sql_query.py` (ve `adt_sql_query`'nin `row_limit`'i) **sessizce kirpar**:
varsayilan `--max-rows` **100**'dur, limit dolunca uyari YOKTUR, cikti gecerli gorunur.

**Olculmus vaka (2026-09-07, <PAKET-F> Adim 3):** bir alt ajan `VBPA`'yi limit vermeden cekti →
ilk 100 satir geldi → "119 canli TP'nin 80'inde baslik `VBPA(AG,000000)` YOK" ve buna bagli
"10 satir mukerrer TP riski" diye raporladi. Lider `--max-rows 2000` ile yeniden cekti →
**551 satir**; 17 <MUSTERI-A> TP'sinin **17'sinde de** baslik AG partneri VAR, gercek risk **3 satir**.
⇒ Eksiklik **veride degil OLCUMDE** dogmustu.

**Why:** Kirpilmis cekim, "kayit yok" bulgusundan **ayirt edilemez** — ve tam da o kiliga girer:
JOIN'i bos dusen satirlar "sistem kusuru" gibi okunur, yanlis kok-neden ve yanlis is listesi uretir.
Bu, `bulunamadi != yok` ihlalinin arac-kaynakli bicimidir.

**How to apply:**
1. Her cekimde `--max-rows` / `row_limit` **ACIKCA** verilir (buyuk secilir).
2. Donen satir sayisi limite **ESITSE kirpilmis varsay** — once `SELECT COUNT(*)` ile beklenen
   buyuklugu olc, sonra cek, ikisini karsilastir.
3. "X yok" siniftaki her bulgu, **cekimin TAM oldugu gosterilmeden** olgu sayilmaz;
   alt ajan raporlarinda bu ilk sorulacak sorudur.
Ilgili: [[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] · [[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]] ·
[[feedback_arac-basarisizligini-zararsiz-sayma]] · [[feedback_kapsam-niteleyicisini-dusurme]]
