---
name: feedback_exporting-tablo-parametresi-hedefi-temizler
description: ABAP'ta EXPORTING tablo parametresi aktüel tabloyu boşaltır — zincirlenmiş çağrıda önceki mesajlar sessizce kaybolur
metadata:
  node_type: memory
  type: feedback
---

**`METHODS m EXPORTING et TYPE ..._t`** çağrıldığında ABAP, gövdeye girmeden **aktüel parametreyi
ilk değerine döndürür** (tablo ⇒ boşaltır). Bu yüzden *"önce kendi mesajlarımı topladım, sonra
ikinci çağrının mesajlarını **aynı** tabloya aldım"* deseni **ilk kümeyi yok eder**.

**Why:** semptom kullanıcıya *"hata yok"* gibi görünür — düzeltme turunun uyarıları kaybolduğu
için ekran sessizleşir. Dump yok, `sy-subrc` yok, log yok; `abaplint`/ATC/syntax **geçer** ve
runtime da hata vermez. Yalnız çıktı eksilir ⇒ ancak mesaj **sayısı** karşılaştırmasıyla yakalanır.

**How to apply:** her çağrıya **ayrı** tablo ver, sonra `APPEND LINES OF lt_ikinci TO lt_birinci`.
`CHANGING`'e çevirmek işe yarar ama **imza değişikliğidir**, tüm çağıranları etkiler — çağrı
yerinde ayrı tablo daha dar bir çözümdür. ⛔ Kendi metodunu çağırırken de geçerli: yönü **imzadan**
teyit et, *"benim metodum, nasıl davrandığını bilirim"* yeterli değil.

Kanonik kayıt: core `playbook/checklists/bug-checklist-backend.md` → **BE-78**.
Ölçülen vaka: <PAKET-A> `redo_from_step` → `process_message` zinciri, 2026-09-16.
Kuzeni: [[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]]

Son-doğrulama: 2026-09-16 · Applies-to: ABAP (tüm profiller)
