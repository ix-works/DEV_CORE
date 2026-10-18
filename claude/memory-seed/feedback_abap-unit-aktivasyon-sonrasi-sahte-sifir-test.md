---
name: feedback_abap-unit-aktivasyon-sonrasi-sahte-sifir-test
description: "push+activate'ten hemen sonraki ilk adt_unit_run HARMLESS testli sınıfta method_count:0 dönebilir — sahte sıfır; kontrol grubu + ikinci koşu"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: f8d56f37-86fc-4a73-a58c-77a0248dc5ab
  modified: 2026-09-28T15:01:28.492Z
---

Yeni yaratılıp aktive edilen bir sınıfta **ilk** `adt_unit_run` `method_count:0` döndü (bir projede,
2026-09-28). Test sınıfı zaten `RISK LEVEL HARMLESS` idi. Kontrol grubu (aynı sistemde testli başka bir sınıf) aynı anda 19 test döndü;
aynı gövdeyle ham POST ve aracın 2. çağrısı **22** döndü. Kök neden ölçülmedi (test include'unun geç üretilmesi ya da
oturum önbelleği olabilir).

**Why:** "0 test" yeşil görünür ya da "test yok" diye okunur — kırmızı bir testi gizleyebilir (o sınıfta 1 test gerçekten kalıyordu).

**How to apply:** aktivasyon sonrası `method_count:0` görürsen sonucu kabul etme: bilinen testli bir sınıfla kontrol grubu
koş + aynı sınıfı ikinci kez koş. Beklenen test sayısını (`grep -c "FOR TESTING"`) brife yaz, sayı tutmazsa DUR.

Son-doğrulama: 2026-09-28 · Applies-to: s4_private, adt_unit_run (MCP sap-adt)
