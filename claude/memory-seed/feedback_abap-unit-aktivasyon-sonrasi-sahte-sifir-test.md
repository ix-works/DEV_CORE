---
name: feedback_abap-unit-aktivasyon-sonrasi-sahte-sifir-test
description: "push+activate'ten hemen sonraki ilk adt_unit_run HARMLESS testli sınıfta method_count:0 dönebilir — sahte sıfır; kontrol grubu + bekle + ikinci koşu; kalıcı 0'da taze süreç, sonra yeniden aktivasyon (sınıf + fonksiyon grubu)"
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

**Tekrar vakası (2026-11-08, başka proje, S/4 2025, 14 yeni sınıf):** 3 sınıfta ilk koşu 0 döndü, ~4–5 dk sonra tam sonuç geldi.
Bir sınıfta 0 **25 dakikadan uzun süre kalıcı** kaldı; kontrol grubu aynı pencerede 10/10 döndü. Sınıf içerik değiştirilmeden **yeniden aktive
edildi** (rejenerasyon) ve ≥4 dk sonra 5/5 döndü. Kök neden yine ölçülmedi. Sıra: kontrol grubu → ≥4 dk bekle → ikinci 0'da
yeniden aktive et → yeniden koş. O da 0 dönerse "DOĞRULANMADI" diye raporla, FAIL değil.

**Üçüncü vaka (2026-11-10, aynı sistem, fonksiyon grubu + sınıf):** fonksiyon grubunda MCP aracı ≥5 dk arayla 2 kez `0` döndü. Aynı
gövde taze bir Python sürecinden POST edilince 3 döndü, ARDINDAN MCP de 3 döndü. Sınıfta ise aktivasyondan hemen sonra
hem taze süreç hem MCP `0` gördü; ~4,5 dk sonra 16 döndü. ⇒ "yalnız MCP oturum önbelleği" açıklaması TEK BAŞINA tutmuyor, çünkü taze süreç
de 0 gördü. "Geçen süre" ile "ilk taze koşunun yüklemeyi tetiklemesi" birbirinden ayrıştırılamadı. Pratik sıra değişmedi; ek ucuz bir adım var:
MCP inatla 0 dönüyorsa yeniden aktivasyondan önce aynı gövdeyi taze bir süreçten bir kez koş.

Son-doğrulama: 2026-11-10 · Applies-to: s4_private, adt_unit_run (MCP sap-adt) — sınıf + fonksiyon grubu
