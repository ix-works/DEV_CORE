---
name: feedback_abaplint-parser-error-gercek-olabilir
description: "ccimp reviewer'da abaplint parser_error'ı körü körüne false-positive sayma — gerçek RAP syntax hatası olabilir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7a28f63f-6ff0-4fe7-88d3-e6cc7c9c76c5
---

Reviewer'da (run_review class_push) abaplint ccimp'i BDEF bağlamı olmadan tek-include parse eder; bu YÜZDEN bazı bulgular false-positive'dir (ör. "Unexpected CLASSDEFINITION" = behavior pool'da 2 handler class normaldir). AMA **`parser_error` / "Statement does not exist" bulgusunu körü körüne false-positive sayma** — gerçek RAP syntax hatası olabilir. ZSD001 booking C3'te abaplint "line 266 READ parser_error" dedim "false-positive" → SAP aktivasyonu type="E" FAIL etti: `validateContainerUnique` BY-association READ söz dizimi yanlıştı.

**Why:** abaplint READ ENTITIES'i tanımadığı için parser_error verir AMA aynı hata gerçek yanlış-sıra/yanlış-clause da olabilir; ikisi aynı görünür. Körü körüne geçmek aktivasyon patinajı yaratır (gateway yakalar, tur kaybı).

**How to apply:** ccimp reviewer'da parser_error çıkınca: (1) ilgili satırı çalışan örnekle (repo'daki aktif ccimp — ORDER/SE_B) KIYASLA; (2) emin değilsen `adt_syntax_check` ile inactive sürümü pre-audit et (otoriter); (3) "Unexpected CLASSDEFINITION" gibi yapısal-multi-class bulguları false-positive kabul edilebilir ama READ/MODIFY/söz-dizimi parser_error'ları DOĞRULA. Çalışan BY-assoc READ deseni (ZCL_SD001_ORDER.ccimp): `READ ENTITIES OF <root> IN LOCAL MODE ENTITY <Root> BY \_<Assoc> FROM VALUE #( ( <DüzKey> = ... ) ) RESULT lt.` — düz key adı (`%tky-` DEĞİL), FIELDS opsiyonel/sonra değil. Bkz. [[feedback_done-tam-kapsam-dogrula]] · [[feedback_playbook-once-oku]].
