---
name: atc-pseudo-comment-satir-basina-tek-ve-bulgu-satirina
description: "ATC pseudo-comment: bir program satırına YALNIZ BİR \"#EC — aynı satırdaki ikincisi sessizce yok sayılır; VALUE/FOR içindeki WHERE bulgusunda #EC bulgunun raporlandığı WHERE satırında olmalı. Ad ATC bulgusunun belge bağlantısından okunur"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 558cf803-e863-47bd-a743-3e15bcb13a3b
  modified: 2026-10-15T09:51:08.998Z
---

ATC bulgusunu pseudo-comment ile muaf tutarken üç ölçülmüş kural:
1. **Satır başına tek `"#EC`.** `… "#EC CI_NESTED "#EC CI_STDSEQ` yazılırsa yalnız İLKİ tutar, ikinci bulgu ATC'de kalır (hata/uyarı yok, sessiz). Birden çok muafiyet gereken ifade satırlara bölünür, her satır sonunda tek `"#EC`. Kaynak: ABAP belgesi ABENPSEUDO_COMMENT ("Only one pseudo comment can be specified per program line").
2. **Yer:** `LOOP … WHERE` gibi düz ifadelerde `"#EC` ifadenin herhangi bir satır sonunda tutar. Ama `VALUE …( FOR x IN t WHERE ( … ) ( … ) )` içindeki WHERE kaynaklı bulguda (CI_STDSEQ) `"#EC` FOR satırında TUTMADI; bulgunun raporlandığı WHERE satırının sonuna taşınınca tuttu. Kural: bulgunun ATC'de gösterdiği satıra koy.
3. **Ad kaynağı:** her bulgunun ATC sonucundaki `atom:link rel="documentation"` (Accept `application/vnd.sap.adt.docu.v1+html`) metni "Finding can be suppressed with pseudo comment …" der — ad oradan okunur. Aynı belge muafiyet edilemeyen bulguyu da söyler ("Cannot be suppressed using a pragma or pseudo-comment"; ör. RAP BEHV "READ … is not implemented" = MESSAGEGFN + SLIN W333).

⛔ Denetim sınıfı kaynağını (CL_CI_TEST_SCAN) okuyup "CS ile aranır, aynı satırda iki tane olur" diye ÇIKARIM yapıldı — canlı ATC çürüttü. Kaynak okuması hükmü değil, ölçüm (push + ATC) hükmüdür.

**Why:** Bir projede, 2026-10-15: tur 6'da 7 ifadede ikinci `"#EC` tutmadı (7 bulgu kaldı); tur 7'de satır bölünce 6'sı tuttu, VALUE/FOR WHERE'deki 1 bulgu kaldı; tur 8'de WHERE satırına taşınınca 0. Her deneme bir push turu + ATC demekti.

**How to apply:** Gerekçeli muafiyet turunda baştan satır başına tek `"#EC` yaz, çoklu bulgulu ifadeyi böl, VALUE/FOR/REDUCE içi bulgularda `"#EC`'i bulgunun satır numarasına koy. Push sonrası ATC'de "0" görünce worklist `objectSetIsComplete="true"` + aynı koşuda bulgu raporlayan bir kontrol sınıfıyla "koşmadı" olasılığını ele.

Son-doğrulama: 2026-10-15 — canlı ATC (projenin ATC varyantı) tur 6/7/8
Applies-to: s4_private (ATC / Code Inspector pseudo-comment)
prior-art: bulundu [[atc-fle-bulgusu-ci-fldext-ok-not-numarali]] (ad + not numarası; satır sonu); core playbook/howto-atc-duzeltme-kaliplari.md :29-33 (onay + gerekçe; "sessizce yok sayılıyorsa" maddesi) — satır başına tek kuralı ve VALUE/FOR yerleşimi YOK (yazıldığı tarihte).
