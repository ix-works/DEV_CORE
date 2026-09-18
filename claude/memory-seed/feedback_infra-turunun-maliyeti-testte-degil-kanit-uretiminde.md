---
name: infra-turunun-maliyeti-testte-degil-kanit-uretiminde
description: "İnfra turu yavaşsa suçlu test koşumu değil, F2 envanterinin dinamik koşuma kayması ve F0b'nin tavansız olmasıdır — ölçmeden hızlandırma yapma"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 276c51e4-6137-42af-afb9-b43b2613eac7
---

Bir infra turu kabul edilemez uzunlukta sürdüğünde ilk refleks *"testleri azaltalım"*
olur. **Ölç önce:** 2026-09-04 gecesinde 6 paralel `infra-expert` koştu (T2 **6,2 sa**/4 kayıt ·
T5 4,8 · T6 4,8 · T9 3,0 · T8 2,5 · T10 **7,5 sa / TEK kayıt**). Test kadansı kuralı
(`infra-expert.md:126` "tam süit yalnız koşu sonunda bir kez") **zaten vardı ve ajanlar UYDU**.

Süreyi yiyen üç şey ölçüldü, üçü de **kanıt üretimi** tarafında:
1. **F2 sınıf-envanterinin dinamik koşuma kayması** — bir tur *1778 validator koşumu* yaptı
   (17 gate × 178 artefakt + 5 × 142), 25 dk timeout'a takıldı, daraltıp **tekrar** koştu.
2. **F3 harness'inin kurulup iki kez çürütülmesi** (kontrol grubu geçersiz çıktı, yeniden kuruldu).
3. **F0b'nin tavansız olması** — bir ajan 7,5 saatin çoğunu *"bu bilinçli bir karar mıydı"*
   aramasında geçirdi.

**Why:** Hızlandırma aracı (`run_battery.py`) doğru yazılmıştı ama **yanlış darboğazı** hedefliyordu;
etkisi gerçekti, sadece görünmedi çünkü asıl maliyet başka yerdeydi. Ölçmeden yapılan ikinci bir
hızlandırma turu da aynı yere bakardı. Ayrıca lider 6 ajanı başlatıp dönüşlerini bekledi —
7,5 saatlik tur **4. saatte kesilebilirdi**.

**How to apply:** Süre şikâyetinde önce **ajan raporlarındaki koşum sayılarını** oku (kaç dosya,
kaç koşum, kaç kez tekrarlandı), sonra kuralı ölç: *"bu sınır kalıcı olarak nerede yazılı?"*
Çözüm DEV_CORE #206 ile `claude/agents/infra-expert.md`'ye damgalandı: kayıt başına **45 dk** ·
paket **≤ 2 kayıt** · **90 dk'da zorunlu ara rapor** · F2 **STATİK** (grep/AST; dinamik envanter
lider onayına tabi) · F0b **≤ 4 arama** sonra `ARANDI-YOK` · harness iki kez çürüdüyse üçüncüyü
kurma. Lider tarafında: **60 dk'da bir ajan durumu kontrolü**. İlgili:
[[feedback_ajan-kurali-brifingde-degil-taniminda-yasar]] · [[feedback_sonucu-olc-uygulamayi-degil]] ·
[[feedback_agent-stall-watchdog-mekanizmasi]] · [[feedback_lider-bloke-olmama-background-dispatch]]
