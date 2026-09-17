---
name: feedback_infra-expert-spawn-ad-verme
description: "infra-expert'i spawn ederken ASLA custom `name` verme — guard kimliği `agent_type`'tan okur, `name` onu ezer ve muafiyet düşer; ajan hiçbir infra dosyasına yazamaz"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: bda2fe1e-cef5-4f3b-86a0-0f7e53c888c0
---

`infra-expert`'i `Agent` ile açarken **`name` parametresi VERME.** Yalnız
`subagent_type: "infra-expert"` yeterlidir. Custom ad verirsen `agent_type` **o ad** olur;
`infra_write_guard` muafiyeti `MUAF_AJANLAR = {"infra-expert"}` ile **tam eşleşme** arar
⇒ muafiyet düşer ⇒ ajan `scripts/hooks/**`, `scripts/validators/**` ve `scripts/*.py`'ye
**hiç yazamaz** (exit 2). `tests/**` ve `governance/**` açık kalır, bu yüzden ajan bir süre
ilerliyormuş gibi görünür ve blok ancak üretim koduna gelince patlar.

**Why:** 2026-08-22'de bu tuzağa **üçüncü kez** düşüldü (20.08 · 21.08 · 22.08). Her seferinde
bir ajan turu yarıda kesildi ve **halef spawn + devir raporu** gerekti. ⭐ Asıl ders şu:
2. vakanın `infra-findings` kaydı çözümü **birebir yazıyordu** (*"Geçici ve bedelsiz workaround:
infra işini ad vermeden spawn et"*) — kayıt doğruydu, tamdı, bulunabilirdi ve **yine düşüldü**.
⇒ Sorun bilgi eksikliği değil, **bilginin doğru ANDA hatırlanmaması**. Bu yüzden mekanik bir
kapı adayı kuyrukta (`infra-kuyruk-RESUME` N1); o gelene kadar panzehir bu kayıttır.

**How to apply:**
- `Agent(subagent_type: "infra-expert", prompt: ...)` — **`name` YOK.** Ajanı sonradan
  adreslemen gerekirse dönen `agentId` ile `SendMessage` at.
- Diğer rollerde (`bug-expert`, `frontend-expert`, `adt-gateway`…) ad vermek **zararsızdır** —
  yalnız `infra_write_guard` muafiyeti kimlik-eşleşmesine bakıyor.
- Ajan *"guard beni bloklıyor"* derse: ⛔ guard'ı gevşetme, ⛔ `MUAF_AJANLAR`'a dokunma,
  ⛔ Bash/`sed` ile yazdırma (bu **bypass**tır ve bu evde açıkça yasaktır) → **ad vermeden
  yeniden spawn et**, worktree'deki iş kaybolmaz.
- Halefe mutlaka **devir raporu** aldır (ne diskte, ne yarım, hangi reçete okundu) — selefin
  okuduğu playbook reçeteleri en değerli devir kalemidir.

İlgili: [[yeni-gate-hook-uretimi-infra-expert]] · [[infra-icin-ayri-acik-onay-sart]] ·
[[arac-basarisizligini-zararsiz-sayma]]

---
**Son-dogrulama:** 2026-08-22 (ders yazim tarihi — o gunden beri YENIDEN OLCULMEDI) · **Applies-to:** bu cekirdegi kullanan tum projeler

⚠ **ARAC IDDIASI** — bu ders *"bugun su arac/kapi boyle davraniyor"* der, yapisal bir olgu
degil. Arac surumu degismis olabilir: davranisa **dayanmadan once bir kez olc**. (Vaka: bir
kardes ders, dayandigi kusur duzeltildikten sonra 3 hafta bayat yasadi; tohuma alinmadan
once olculup elendi.)
