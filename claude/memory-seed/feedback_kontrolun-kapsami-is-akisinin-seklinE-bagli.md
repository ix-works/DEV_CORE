---
name: feedback_kontrolun-kapsami-is-akisinin-seklinE-bagli
description: "Bir guard'ın kapsamı araç/spawn biçimine bağlıysa, iş akışının şekli değiştiğinde kural ihlal edilmez — HİÇ ÇAĞRILMAZ"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 08f4a439-ebf4-425b-9d0a-f815401919b3
---

Bir kontrol *"hangi araçla / hangi biçimde çalıştığına"* bağlıysa, kapsamı **iş akışının şeklinin bir fonksiyonudur**. Akış değişince kural ihlal edilmez — **hiç çağrılmaz**, ve bu **sessizdir**.

**İki canlı vaka, aynı gün (2026-08-20), aynı guard ailesi:**

1. **Araç ekseni.** `infra_write_guard` matcher'ı `Edit|Write|MultiEdit`. Oturumun auto-mode talimatı *"dosya değişikliklerini **Bash** ile yap"* diyordu ⇒ **17 infra dosyası** guard hiç ötmeden değişti. Aynı gün, aynı işi `Write` ile yapan ajan **bloklandı**. Aynı iş, aynı yetki, **zıt sonuç**. ⭐ Kör nokta zaten kayıtlıydı; **yeni olan**, oturum ayarının o kör noktayı *istisna* değil **ana yol** yapmasıydı.
2. **Spawn ekseni.** Aynı guard'ın muafiyeti `agent_type == "infra-expert"`. Ajanı `name: infra-parti4` ile spawn edince harness `agent_type` alanına **tipi değil ADI** koydu ⇒ muafiyet çöktü, onaylı iş durdu. Guard'ın 2026-08-19 ölçümü **yanlış değil, EKSİKTİ**: **adsız** spawn'la yapılmıştı, "ad verilip verilmediği" ekseni hiç denenmemişti.

**Nasıl uygula:**
- Bir kontrolün *"çalışıyor"* kanıtını okurken sor: **hangi eksende ölçülmüş, hangi eksen denenmemiş?** Tek senaryoda ölçülen kimlik/kapsam, ikinci eksende çöker.
- İnfra yüzeyine dokunacak ajanın brifingine *"düzenlemeyi `Edit`/`Write` ile yap — Bash guard'ı atlar"* satırını koy.
- ⛔ Guard'ı **bilerek atlatma**: kör noktadan geçmek onayın kendisini geçersizleştirir. Bir ajan bunu reddettiyse **doğru** davranmıştır.
- Kör noktayı kapatmadan muafiyeti genişletme — kontrolü **iki kez** zayıflatır.

İlgili: [[feedback_dogrulama-sezgileri-dort-kural]] (kod ≠ kablolama) · [[feedback_yesil-sinyalin-kapsamini-sor]] · [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]]
