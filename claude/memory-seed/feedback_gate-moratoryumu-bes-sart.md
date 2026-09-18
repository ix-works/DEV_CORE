---
name: feedback_gate-moratoryumu-bes-sart
description: "Yeni gate/guard/validator/hook açmak için 5 şart; gate son çaredir, kök sebep genelde gereksiz çoğaltmadır"
metadata:
  node_type: memory
  type: feedback
---

Yeni bir **gate** (validator / hook / guard kuralı / pre-commit / CI job / run_review zinciri /
checklist'te gate iddia eden satır) ancak **beş şartın hepsi** sağlanınca açılır:

1. Hata **GERÇEKTEN yaşandı** (varsayım/ihtimal değil).
2. Sonuç **geri alınamaz VEYA sessiz** (ikisi de değilse → statik kontrole in; merdiven ilkesi).
3. **Başka hiçbir katman** (tasarım/validator/pre-commit/CI) zaten yakalamıyor.
4. **ÖNCE dokümanla hatırlatma denendi** (L1a `CLAUDE.core.md §1.1` · `core/claude/rules/` ·
   skill · checklist) ve **yetmediği görüldü.** Gate SON ÇARE.
5. Kullanıcıya **detaylı izah + AÇIK ONAY** — *auto-mode'da bile*. Gömülü onay
   ("hepsini yap", "devam et", "erteleme") bu izni **VERMEZ**.

**Kapsam dışı** (5 şart aranmaz): mevcut gate'in **onarımı** · bir gate'i **kaldırmak**
(teşvik edilir, yalnız bildir) · zorlama yapmayan yardımcı araç.

**Why:** 2026-07-10 — bir belge iki repoya kopyalandı → kopya bayatlar → tazelik gate'i
(C-DOC-01) → gate CI'da kaçınılmaz kırmızı verdi → `--admin` ile bypass edildi → bypass'ı
önlemek için guard kural 10. **Kural kuralı doğurdu.** Kök sebep kural eksikliği değil,
gereksiz çoğaltmaydı; kopya kaldırılınca iki gate birden düştü.

**How to apply:** Gate yazma isteği geldiğinde önce sor: *"Bu bir çoğaltma/karmaşa sonucu mu?
Onu kaldırsam gate gereksizleşir mi?"* Sonra 5 şartı tek tek yaz ve kullanıcıya göster.
**Bir gate'i silmek, bir gate eklemekten daha sık doğru cevaptır.**

İlgili: [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]] (tersi de doğru) ·
[[feedback_adt-infra-degisikligi-once-uyar-onay]] · [[feedback_karar-verimliligi-asiri-kapi-yok]]
