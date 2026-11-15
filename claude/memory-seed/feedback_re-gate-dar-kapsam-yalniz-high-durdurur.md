---
name: feedback_re-gate-dar-kapsam-yalniz-high-durdurur
description: "Düzeltme sonrası re-gate yalnız değişen satırlara bakar; yalnız HIGH turu durdurur, MEDIUM/LOW aynı turda düzeltilir, yeni gate açılmaz"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Bir düzeltme turundan sonraki bug-gate (re-gate) **yalnız o turda değişen satırlara ve bunların doğrudan çağıranlarına** bakar. Dosyanın ya da paketin tamamı taranmaz ve test takımlarının hepsi baştan koşulmaz.

Hüküm kuralı:
- **Yalnız HIGH** bulgu BLOCKER'dır ve yeni bir tur açar. HIGH örnekleri: derlenmeyen kod, sessiz yanlış fiyat/veri, ADR 0005 ya da güvenlik ihlali.
- MEDIUM/LOW bulgular "aynı turda düzelt" listesine girer. Düzeltilirler ve **yeniden gate açılmadan** geçerler.

Builder tarafında tam regresyon da tur sonunda **bir kez** koşulur.

**Eski iki dersle ilişkisi:** [[feedback_duzeltme-turu-kendi-ciktisina-kapi-ister]] ve [[feedback_duzeltme-turu-kendi-regresyonunu-uretir]] geçerlidir: her düzeltme turu kendi çıktısına bir kapı koşar ve o kapı bu dersteki dar re-gate'tir. Bu ders yalnız re-gate'in **kapsamını** ve **hangi bulgunun yeni tur açtığını** belirler. MEDIUM/LOW düzeltmesi kapısız geçer, ancak düzeltme yalnız bulgunun gösterdiği yeri değiştiriyorsa. Düzeltme yeni bir mantık dalı, yeni bir dosya ya da bulgunun dışında bir davranış değişikliği getiriyorsa o yeni yüzey bir sonraki dar re-gate'e girer.

**Why:** Kullanıcı (2026-11-08, bir SD paketi): "yine bug çalıştı kaç defa çalışacak … ne zaman bitecek". Her düzeltme küçük yeni kusurlar getirdi ve build→gate→fix→re-gate döngüsü saatlerce uzadı (UI ajanı ~3 saat). Gate'ler gerçek HIGH'lar yakaladı: derlenmeyen bir iş planlama çağrısı, para birimi ondalığı yüzünden 100 kat yanlış fiyat ve bir kip bloğu kusuru. Maliyetli olan gate'in kendisi değil, kapsamı ve MEDIUM/LOW bulgularda yeniden tur açmasıydı. Kullanıcı önerilen dar kapsam kuralına "evet, öyle yapman gerek zaten" dedi.
**How to apply:** Re-gate brifine iki satır yaz: kapsam ("yalnız bu turun diff'i + çağıranları") ve hüküm kuralı ("yalnız HIGH BLOCKER; MEDIUM/LOW düzeltme listesine, WARNING"). Yeni bir build'in ilk gate'i tam kapsamlı kalır. Bağlantılı: [[feedback_lider-build-yapmaz-experte-dagit]]. BUG GATE kuralı (core §1.1) geçerliliğini korur; yalnız re-gate'in kapsamı daralır.

Son-doğrulama: 2026-11-08
Applies-to: tüm projeler, expert build → bug-gate döngüsü
