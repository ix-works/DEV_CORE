---
name: feedback_ajan-olumsuz-donusu-kanitla-sorgula
description: "HER alt-ajanın (gateway/bug-expert/backend/frontend/research) \"yapılamaz/blocker/yok\" raporunu kanıtsız kabul etme — sorgula, repo'da alternatif/script ara, kendin doğrula"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1420ec34-9257-4b0a-aef4-aee509c5b810
---

**HER alt-ajan** (gateway/bug-expert/backend-expert/frontend-expert/research/general — `adt-gateway` yalnız en sık örnek) "yapılamaz / desteklenmiyor / blocker / yok / bulunamadı" diye olumsuz dönerse, lider bunu **doğru kabul edip ona göre işlem yapmaz veya durmaz** — SORGULAR. Kural gateway'e özgü DEĞİL; her ajan dönüşü için geçerlidir.

**Why:** Ajanın tool-görünümü repo'nun gerçek kabiliyetinden DARDIR. "Yapılamaz" çoğu zaman "imkânsız" değil, "bu ajanın elindeki (typed) araçlarla yapamadım" demektir. Lider hızlı kabul ederse gerçek çözümü kaçırır. Somut ders (2026-06-22): gateway "SRVB description typed MCP tool ile değiştirilemez, ham REST riskli" dedi; lider önce kabul etti. Oysa `scripts/sap_set_object_description.py` TAM bu senaryo için yazılmıştı (copy-create objelerde voyage-kopyası "Sefer servisi baglama" açıklamasını düzeltme; srvb destekli, blast-radius sadece `adtcore:description`, readback'li). Kullanıcı hatırlattı.

**How to apply:** Ajan olumsuz/blocker dönünce → (a) "Bu gerçekten imkânsız mı, yoksa ajanın araç-kapsamı mı dar?" diye ayır. (b) İddiayı repo'da **ara** (Grep/Glob): aynı işi yapan mevcut `scripts/*.py`, playbook reçetesi, alternatif endpoint/yol var mı. (c) Varsa ajanı o yolla yeniden yönlendir/taze-spawn et. (d) Yoksa iddiayı **kendin canlı doğrula**, sonra kullanıcıya ilet. Bu, ajan-tarafı [[feedback_dogrula-once-flag-spekulatif-blocker-yasak]]'ın lider-tarafı tamamlayıcısıdır; kök ilke = TAHMİN YASAK = kanıtlı hareket et. İlgili: [[feedback_arac-kod-fix-lider-isi]] (paylaşılan tooling/yol bilgisi lider'in sorumluluğu).
