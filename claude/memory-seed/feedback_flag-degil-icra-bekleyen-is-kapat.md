---
name: feedback_flag-degil-icra-bekleyen-is-kapat
description: "Bir işi 'pending/awaiting push' diye flag'lemek onu YAPMAK değildir — ya icra et ya açıkça ertele"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 418739be-f6dd-46e4-b0cf-fe5902b2d2fb
---

Bir işi durum mesajında "X bekliyor / awaiting push / pending" diye **flag'lemek onu YAPMAK değildir.** 2026-07-02: print CDS (ZSD001_I/C_TRDOC_PRINT — şöför+adres) önceki oturumda hazır+bug-gate PASS, "awaiting push" işaretlendi; sonraki konularda (driver-cancel → nakliye-düğüm → F4 → şöför-zorunlu) **iki kez daha flag'lendi ama hiç push edilmedi** → kullanıcı canlı çıktıda boş şöför/adres görünce ortaya çıktı. "commit push deploy" dendiğinde push kapsamı o-anki-değişen objelere daraltıldı, devreden print CDS dahil olmadı.

**Why:** Carry edilen SAP-yazma/deploy maddesi topic-switch'lerde sessizce düşer; "bekliyor" demek kullanıcıya "biliniyor/kontrol altında" hissi verir ama iş açık kalır. [[feedback_done-tam-kapsam-dogrula]] + [[feedback_arac-basarisizligini-zararsiz-sayma]] ile aynı kök.

**How to apply:** Bir SAP-yazma/deploy maddesini "bekliyor" diye işaretlediysen, o oturumu/bundle'ı kapatmadan ya (a) İCRA ET, ya (b) kullanıcıdan **açık "ertele" kararı** al. "commit push deploy" gibi kapanış komutunda kapsamı yalnız o-anki-diff'e daraltma — **açık pending SAP-maddelerini de dahil et** (veya neden hariç bıraktığını söyle). Şüphede: `source_drift` denetimi (local↔canlı) ile push'suz kalanı kanıtla — iddia etme. Deploy sonrası "done" demeden önce kullanıcının gördüğü uçtan-uca sonucu (çıktı/ekran) doğrula.
