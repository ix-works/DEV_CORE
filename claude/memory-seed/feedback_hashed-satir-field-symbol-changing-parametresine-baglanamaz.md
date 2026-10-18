---
name: feedback_hashed-satir-field-symbol-changing-parametresine-baglanamaz
description: Hashed/sorted tablo satırını gösteren field-symbol metodun CHANGING parametresine bağlanamaz — anahtara yazılmasa da çağrı anında MOVE_TO_LIT_NOTALLOWED_NODATA; hiçbir statik kapı yakalamaz
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 8865df6b-2e94-44e8-8952-84b42fc53742
  modified: 2026-10-16T14:10:00.491Z
---

Hashed ya da sorted tablonun birincil anahtar alanları salt-okunurdur; bu yüzden satırı gösteren field-symbol "kısmen korumalı"dır. Böyle bir alan bir metodun **CHANGING** (referans) parametresine **bağlandığı anda** program düşer: `MOVE_TO_LIT_NOTALLOWED_NODATA` / `CX_SY_DYN_CALL_ILLEGAL_TYPE` ("field is at least partly protected against changes"). Metodun anahtar alana fiilen yazıp yazmaması önemsizdir; hata bağlamadan doğar. Dökümdeki alan adı (ör. `<LS_ITEM>-KUNNR`) anahtar alan olmayabilir — yapının ilk alanı görünür.

**Why:** Bir projede, 2026-10-16: `LOOP AT mt_item ASSIGNING <ls_item>. calc_quantities( CHANGING cs_out = <ls_item> ).` (mt_item HASHED UNIQUE KEY vbeln posnr) ilk çalıştırmada düştü. Sözdizimi, aktivasyon, abaplint, ATC (P1/P2 0) ve İKİ bug-gate geçti; ilk bug-gate riski görüp "anahtar alan yazılmıyor ⇒ güvenli" hükmü vermişti — yanlış çıkarım.

**How to apply:** sorted/hashed satırı değiştiren metoda satırı kopya olarak ver (`LOOP … INTO ls` → metot → `MODIFY TABLE itab FROM ls`). `<fs> = ls.` ile bütün satırı geri atamak da anahtara yazar, aynı döküm. Bug-gate'te "anahtar yazılmıyor" hükmü bu kalıp için kanıt değildir. Komşu: core BE-71 (salt-okunur aktüel → FM TABLES). prior-art: core BE-71 komşu; bu kalıp (metot CHANGING + hashed satır) yazılı değildi.

Son-doğrulama: 2026-10-16 · Applies-to: ABAP (tüm profiller), klasik rapor + sınıf
