---
name: feedback_ajan-model-secimi-olculdu-ayri-politika-yazilmadi
description: "Alt-ajanları iş-tipine göre ucuz modele indirme fikri 2026-08-29'da ÖLÇÜLDÜ ve BİLİNÇLİ olarak yapılmadı: kazanç tavanı %4-8, hata maliyeti asimetrik. Tekrar açmadan önce bu kaydı oku"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 199aed41-f1ec-4c03-ae34-a0b1b09c15be
---

**Alt-ajanlara iş-tipine göre model seçme politikası ÖLÇÜLDÜ ve YAZILMADI — bu bir ihmal
değil, kullanıcı kararıdır (2026-08-29).** Konu yeniden açılırsa sıfırdan ölçme; aşağıdaki
sayılar ve gerekçe geçerlidir.

## Ölçülen durum (n'leriyle)

- **Politika zaten VAR ve ateşliyor:** model `.claude/agents/<rol>.md` frontmatter'ındaki
  `model:` alanından geliyor. opus = `adt-gateway` · `backend-expert` · `bug-expert` ·
  `infra-expert` · sonnet = `frontend-expert` · `sap-feature` · `sap-research`.
  ⚠ *"Kuralı agent dosyasına yazmak işe yaramaz, onu lider okumaz"* **model alanı için
  YANLIŞTIR** — frontmatter modeli seçen mekanizmanın kendisidir (ölçüldü: sonnet ilan edilen
  rol sonnet-5'te koştu).
- **731 spawn / 30 gün.** 135'inde lider `model` parametresini elle geçmiş; bunların **85'i
  boşa** (zaten varsayılanı tekrar yazmış). Gerçek sapma **36**, ve bu 36 spawn yalnız
  **12 epizot** — üç epizot 25'ini taşıyor. ⇒ Sapmalar kural değil, **tur ruh hâli**.
- **`infra-expert`: 72 spawn'ın 72'si opus.** 64'ünde parametre hiç geçilmemiş, 8'i zaten
  varsayılan olan `opus`. Sonnet **0**. Şablonda `model: opus` ilk spawn gününden (08-01)
  beri 8 sürümün 8'inde. ⇒ Bu rolde alternatif hiç **düşünülmemiş**.
- **Ucuza inebilecek dilim %7–14** (iki bağımsız kanal): 118 core commit'in %72'si kod/kapı
  dosyasına, %14'ü kural metnine, **%14'ü saf dokümana** dokunuyor · token'ı ölçülen 5 infra
  koşusunda gösterge-işi payı **$13,64/$187,42 = %7**.
- **Kazanç tavanı %4–8** — çünkü fiyat farkı tam 2,5× ama yalnız o dilimde:
  `%14 × (1 − 1/2,5) ≈ %8`.

## Why — neden yapılmadı

1. **Ödül küçük, kapı her spawn'da açılıyor.** Her infra spawn'ına bir sınıflandırma adımı
   eklemenin bedeli, ~%8'lik tavanı aşıyor.
2. ⭐ **Hata maliyeti SİMETRİK DEĞİL.** Yanlış sınıflandırma rastgele iki yöne kaymaz: bir
   **kapıyı** "gösterge" sanmak, hatası **sessiz** düşen işi ucuz modele verir. Bu evde
   defalarca ölçülen *"beyan var, koruma yok"* sınıfına (`Q197`–`Q201`, `Q204`–`Q206`) yeni
   bir giriş kapısı olurdu. [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]] ·
   [[feedback_gate-moratoryumu-bes-sart]].
3. **Tasarruf garantisi yok.** 2,5× yalnız tur sayısı sabitse geçerli. Maliyet turla
   süperlineer büyüyor (ölçülen koşularda ~`tur^1,4`) ⇒ **başabaş ~1,9× tur** (üsse göre
   1,6–2,5× aralığı). Sonnet'in bu işlerde kaç tur attığı **ölçülmedi**; yerel infra-sonnet
   kanıtı **sıfır** (72/72 opus).

⛔ **Karar gerekçesi ŞU DEĞİL:** *"sınıflandırma zor"*. Zor olan **geriye dönük** çıkarımdı
(72 koşuyu brif metninden ayıklamak); spawn anında lider ne isteyeceğini zaten bilir, çıkarım
yapmaz. Gerekçe **sayılar ve asimetri** — bunu karıştırma, yoksa yanlış sebeple doğru karar
üç ay sonra yanlış tarafa döner.

## How to apply

- Konu geri gelirse: **önce bu kaydı oku**, ölçümü tekrarlama. Değişmesi gereken tek şey
  varsa **fiyat oranı** ya da **rol dağılımı**dır; ikisini de kontrol et.
- **Tek seferlik override serbest ve zaten kullanılıyor:** apaçık gösterge işi (statusline
  segmenti, salt-okuma döküm) çıkarsa lider o an `Agent(model: "sonnet")` geçebilir —
  gateway'de fiilen böyle yapılıyor (7 spawn, 5'i salt-okuma teşhis; 2 canlı yazma da
  sorunsuz geçti çünkü o yol **kapı-yoğun**: içerik-karşılaştırmalı readback + syntax + ATC +
  inactive + liderin bağımsız ölçümü). Kural/kapı/doküman **gerekmiyor**.
- ⛔ `bug-expert`'i ucuza indirme cazibesine kapılma: sonnet'te ürettiği 88 bulgunun
  **isabeti** kanıtlı (3/3 örneklem doğru, 35'i kapandı) ama **kaçırması** hiçbir artefaktla
  ölçülemez — kaçırılan BLOCKER iz bırakmaz. Ölçülemeyen tarafı, ölçülen tarafla telafi etme.

## Ölçüm nerede yapılır (tekrar gerekirse)

- ⭐⭐ **DÜZELTME (aynı gün, 2026-08-29 akşam):** Alt-ajan transkriptleri **KALICI** olarak
  `~/.claude/projects/<proje>/<session>/subagents/agent-*.jsonl` altındadır — 30 günde
  **713 dosya + `agent-*.meta.json`** (`agentType`, `isFork`, `parentAgentId`). İlk ölçüm
  yalnız kök `*.jsonl`'i (78 dosya) taradığı için bunları görmedi ve *"n=22, veri yalnız
  temp'te"* diye **yanlış** yazıldı. Yukarıdaki n=22 sınırı gerçek değildi; tam korpus
  **675 koşu**. `TOKEN-DENETIM-30G-2026-08-28.md` §0 bu yolu zaten belgeliyordu
  (*"780 dosya"*) — önce o okunsaydı hata olmazdı. ⇒ **Ölçüme başlamadan önce donmuş
  denetimin YÖNTEM bölümünü oku.** `%TEMP%/…/tasks/*.output` aynı içeriğin geçici kopyasıdır.
- ⚠ **Dedup tuzağı (ölçüldü):** transkript her içerik bloğunu **ayrı satıra** yazar, aynı
  `message.id` ile. `(message.id, requestId)` dedup'ını satır düzeyinde uygularsan ikinci
  satırdaki `tool_use` blokları düşer ⇒ araç sayısı 3-4× eksik, hata oranı %55 gibi imkânsız
  çıkar. Doğrusu: tur = usage taşıyan benzersiz `(id, requestId)`; araç = benzersiz `tool_use.id`.
- ⚠ **Ad tuzağı:** spawn'ların **%80'i özel `name`'li** (549/682) ve `meta.agentType` o adı
  taşır, rolü değil. Rol bazlı ölçüm için ana transkriptten `name → subagent_type` haritası
  kurulmalı; kurulmazsa "rol" tablosu yalnız adsız %20'yi görür (taraflı).
- Ana transkriptte (`~/.claude/projects/<proje>/*.jsonl`) **sidechain 0 satır** — alt-ajan
  turları orada YOK. `~/.claude/tasks/` yalnız görev-takip json'u, **usage taşımaz**.
- Spawn sayımı ana transkriptten yapılır: `Agent`/`Task` `tool_use` → `input.subagent_type`
  + `input.model`; **dedup `tool_use.id` ile** (ham sayım ±1 oynar).
- ⚠ **Brif metninden sınıflandırma ÇÜRÜKTÜR** — her infra brifi aynı guardrail kalıbını
  ("kuralı gevşetme", "validator süiti yeşil", "CI") taşır, anahtar-kelime sayacı hedefi
  değil kalıbı ölçer (statusline işi bile `kapi=20` verdi).
  [[feedback_tarama-ciktisi-hipotezdir-is-listesi-degil]].
- ⚠ **Dosya-adı deseni de çürüktür** — adında `check_`/`validator` geçmeyen gerçek kapılar
  (`verify_*`, `post_validate` matcher, `settings` hook kablolaması) gösterge kovasına düşer.
  Çalışan ölçüt: *değişen dosyaların tamamı, hiçbir otomatik kontrolün okumadığı saf doküman mu?*

Aynı aile: [[feedback_subagent-karar-kurali]] (kaç ajan — bu kayıt **hangi model** eksenidir) ·
[[feedback_karar-verimliligi-asiri-kapi-yok]] · [[feedback_devreye-alma-once-etki-olc]].
