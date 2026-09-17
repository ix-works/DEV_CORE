---
name: feedback_performans-onerisi-de-bir-iddiadir-maliyeti-once-olc
description: "Bir hızlandırma önerisi de ölçülmemiş bir iddiadır. Maliyetin NEREDE olduğunu ölçmeden kaldıraç önerme — 'rapor uzunluğu' gibi göze çarpan kalem çoğu zaman gürültüdür; ölçüm aracı zaten repoda olabilir."
metadata:
  node_type: memory
  type: feedback
---

**KURAL:** *"Şunu kısarsak hızlanır"* cümlesi bir **iddiadır** ve ölçüm ister. Kullanıcı
*"önce önerini söyle, performansını ıspatla, sonra gerekirse değiştir"* dediğinde doğru
sıra budur; ama beklemeden de böyle davranılmalı. Önce **maliyet dağılımını** çıkar,
sonra kaldıraç öner.

**ÖLÇÜLMÜŞ VAKA (2026-09-09, ZSD001 doküman turu).** Kullanıcı *"bu ajan 25 dk ne yapıyor,
daha hızlı yolu yok mu"* diye sordu. İlk cevabımda **ölçmeden** bir kaldıraç önerdim:
*"rapor uzunluğunu kısarsam token'ın belki üçte biri gider."* Kullanıcı ısrar etti; ölçtüm,
**önerim çürüdü**:

| kalem | pay |
|---|---|
| araç-çağrısı girdisi (Edit/Write içeriği = **asıl ürün**) | **%95,2** |
| lidere rapor (`SendMessage`) | %19,5 (araç girdisinin içinde) |
| serbest anlatı metni | **%4,8** |

Yani raporu yarıya indirmek ~%10 token kazandırırdı, üçte bir değil — ve **duvar saatinden
0**, çünkü rapor tek turda yazılıyor.

**Ölçüm asıl şunu gösterdi:** duvar saatinin sürücüsü **tur sayısı**. `doc-kd-toplama`
237 araç çağrısını **398 model gidiş-gelişinde** yaptı; turların **%40'ı hiç araç
çağırmıyor**. Ve ayırt edici bulgu: **≥3 araç çağrısı yapan 12 alt-ajanın 12'sinde de
`max batch = 1`** — hiçbiri bir kez bile aynı turda iki araç çağırmadı. 12/12 aynı davranış
⇒ tercih değil **yapısal** (nedeni ÖLÇÜLMEDİ; hipotez olarak bırakıldı).

Ayrıca "yavaş" sanılan araç **suçsuz** çıktı: Playwright harness'ı 16 ekran görüntüsünü
**27 saniyede** üretiyordu (çıktı dosyalarının zaman damgası 10:37:55 → 10:38:22) — 25
dakikanın **%2'si**. Chrome eklentisine geçmek daha da yavaş olurdu
([[feedback_tarayici-araci-secimi-playwright-vs-chrome-eklentisi]]).

**Why:** Göze çarpan kalem (uzun raporlar) ile maliyetli kalem (ürün üretimi + tur sayısı)
aynı şey değildir. Ölçmeden önerilen kaldıraç, doğru görünen ama etkisiz bir değişiklik
yaptırır; üstelik **gerçek kaldıracı gizler** — rapor kısıtı uygulansaydı "iyileştirme
yaptık" sanılıp tur sayısı hiç bakılmadan kalırdı.
[[feedback_sonucu-olc-uygulamayi-degil]] ve [[feedback_iddia-yazma-aninda-kanit-kurallari]]
ile aynı disiplin; burada iddia **kendi süreç önerimdir**.

**How to apply:**
- **Ölçüm aracı zaten repoda olabilir** — bu vakada `core/scripts/agent_time_report.py`
  vardı ve doğrudan cevabı verdi (üretim %48 · araç %19 · boşta %27 · lider-bekleme %6 ·
  batch medyanı 1 · tekrar-okuma %66 · mükerrer çağrı %32). Önce ara.
- Ham ölçüm: alt-ajan transkriptleri
  `~/.claude/projects/<slug>/<session>/subagents/agent-*.jsonl`. `type=="assistant"`
  girdilerinde `content[]` içinden `text` / `thinking` / `tool_use` ayrıştır; **tur sayısı**,
  **araçsız tur oranı**, **tur başına araç sayısı (batch)** ve **karakter dağılımı** çıkar.
- Duvar saati ile token maliyetini **ayrı** raporla: rapor kısmak token'ı azaltır ama turu
  azaltmaz; tur azaltmak ikisini birden azaltır.
- Aracın kendisini suçlamadan önce **aracın süresini ölç** (çıktı dosyalarının ilk/son
  mtime farkı yeterli).
- Ölçüm önerini çürütürse **öneriyi geri çek ve bunu açıkça yaz**. Nedeni ölçülmemiş bir
  bulgu (burada `batch=1`) **iş listesine dönüştürülmez**, "ölçülmemiş iz" olarak bırakılır.
