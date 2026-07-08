---
name: feedback_subagent-karar-kurali
description: "Subagent kararı: önemsiz→kendin yap; token-ağır+paralelleşmez→tek subagent (context izolasyonu); token-ağır+paralelleşir→ÇOK subagent paralel fan-out. Paralelleşeni tek-subagent'a seri vermek ANTİ-PATTERN"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a1b6afef-4b32-4db8-92e7-c8825dc4ffa1
---

Subagent kararı 3 vaka:
1. **Önemsiz / ara-detaylar zaten lazım** → **kendin yap** (subagent indirection'ı gereksiz; tek subagent ≠ "kendin yapmak" ama bu durumda fark yok).
2. **Token-ağır, sadece SONUÇ lazım, paralelleşmez** → **tek subagent** — değeri **context izolasyonu** (ağır işi atılabilir pencerede yapıp ana context'e kısa sonuç döner; ben yapsaydım ara-döküm penceremi şişirirdi). Veya taze-gözle/adversarial 2. bakış.
3. **Token-ağır VE paralelleşir (bağımsız parçalar)** → **ÇOK subagent, paralel fan-out** (tek mesajda N Agent çağrısı): izolasyon + hız + parça-derinliği.

⛔ **ANTİ-PATTERN:** paralelleşen işi (N bağımsız kategori/dosya/paket) **tek subagent'a seri** verdirmek — izolasyonu alır, hızı+derinliği kaybeder. Paralelleştirince kendin de aynı işi tekrar koşma; sonucu bekle.

**Why:** Kullanıcı içgörüsü (2026-06-13): "tek ajan ≈ sen yap, neden ajana verip bekliyorsun? subagent çok kullanılınca mantıklı." Büyük oranda haklı — eksik nokta: tek subagent'ın context-izolasyon değeri (Explore/araştırma subagent'ları bunun için var). Tetikleyen hata: tooling-radar ilk run'ı 6 bağımsız kategoriyi **tek subagent**'a seri taradı (paralel olmalıydı) → kullanıcı yakaladı.

**How to apply:** Bir işi subagent'a vermeden önce sor: (a) önemsiz mi → kendin yap; (b) bağımsız parçalara bölünür mü → bölünürse **paralel fan-out** (her parça ayrı Agent, tek mesajda concurrent), bölünmezse tek subagent. "Geniş süpürme / N-kategori / N-dosya audit / N-paket tarama" = neredeyse her zaman fan-out. Kural L1'de: AGENTS.md §2 "Subagent/Orkestrasyon Kararı". İlgili: [[feedback_done-tam-kapsam-dogrula]].

---

## EK (2026-06-15): Subagent "Stream idle timeout" — kök sebep + dispatch disiplini

**Belirti:** sap-feature ajanları `Stream idle timeout - partial response received` ile yarıda ölüyor (IHR header-fill, SIP header-fill; biri 22 tool-use / sadece 821 çıktı-token sonra timeout). **Kullanıcı içgörüsü (2026-06-15):** "neden her seferinde sen elle bitiriyorsun? kök sebebi bulup tekrarı önle (T10/T11)."

**Kök sebep:** Ajan, büyük dosyaları (ör. FIT 795-satır controller + birkaç CDS) **kendi okuyup** dev context biriktiriyor, sonra **tek seferde uzun çıktı** üretiyor (tam dosya Write + çok-metot edit). Büyük input + uzun tek-üretim → model akışı idle-limitini aşıyor. Kod bug'ı değil; harness idle-timeout'u config edilemez → tetikleyeni azalt.

**How to apply (dispatch disiplini — timeout önleme):**
1. **Context'i hazır ver:** "şu 795 satırı oku" yerine ihtiyaç duyduğu ~40-satır snippet'i prompt'a göm. Küçük input = stall riski düşük.
2. **Küçük iş birimi:** tek ajana "CDS + 3 metot + i18n + view" yığma; tek artefakt / dar kapsam.
3. **İyi-kapsanmış cerrahi edit'i LİDER yapar:** context zaten lider'de yüklüyse, ajan yeniden-okuyup timeout riski almaktansa lider doğrudan editler (delegasyon = gerçekten paralel + ağır-okuma + bağımsız iş için). Bu, **[[feedback_arac-kod-fix-lider-isi]]** ve yukarıdaki "(a) önemsiz → kendin yap" ile uyumlu.
4. **Timeout olursa RESUME:** kısmi iş çoğu kez diskte (dosya kontrol et) → sıfırdan değil kaldığı yerden devam / SendMessage ile sürdür.
5. **Genel kural:** "her seferinde semptomu elle çöz" = anti-pattern; tekrar eden patinajda kök sebebi düzelt + buraya yaz (T10/T11).

---

## EK (2026-06-19): Aynı-uygulamada paralel = ÇAKIŞMA riski — DİKKATLİ böl ya da BÖLME

**Kullanıcı uyarısı:** Büyük çok-görevli FE pasını "paralel ajanlara bölmeliydim" çıkarımıma karşı — "**bunu çok dikkatli yapmalısın, gerekirse yapma; aynı uygulamada çakışma problemi yaşamayalım.**" **Çakışmadan kaçınmak hızdan ÖNCE gelir.**

**Kural (fan-out'un ön-koşulu = dosya-disjointluğu):** Paralel fan-out yalnız ajanların yazdığı **dosya setleri TEMİZ ayrışıyorsa** yapılır. İki ajan aynı dosyaya (ör. CreateSe.controller.js) yazacaksa = SERİ / tek-ajan. Aynı app içinde "PAK-kaldırma" + "KDMAT-ekleme" gibi işler aynı controller/fragment/i18n'e dokunur → paralelleştirilemez (tek-ajan, büyük pas kabul edilir; süre uzar ama çakışma yok). 

**Güvenli paralellik örnekleri (farklı dosya-domeni):** BE (CDS/ABAP) ‖ FE (UI JS/XML) ‖ read-only bug-gate/recon — domenleri ayrık, çakışmaz. Farklı APP'ler (sip_se ‖ ihr_se) de ayrık. **Riskli:** aynı app'in aynı katmanında iki yazıcı.

**How to apply:** Fan-out'tan önce her ajanın YAZACAĞI dosya setini listele → kesişim var mı? Kesişim=0 → paralel OK. Kesişim>0 → tek-ajan veya kesin-seri (biri bitince diğeri). Şüpheliyse paralelleştirme (büyük tek-pas, geç ama güvenli). Lider hâlâ bloke olmaz ([[feedback_lider-bloke-olmama-background-dispatch]]) — tek-ajan da background.

---

## EK (2026-06-24): Model-per-rol dial (kalite↑ kritikte, maliyet↓ rutinde)

Subagent dispatch'te modeli işe göre **dial** et (Agent `model` + `effort` opt'ları; `bug-expert`/`adt-gateway` zaten frontmatter'da `model: opus` pinli):
- **Kritik / kalite-belirleyici rol** (bug-expert gate, gateway SAP-yazımı, substantive build/tasarım) → **opus** (+ gerekirse `effort: high`). Hatanın bedeli yüksek; ucuz model kalite düşürür.
- **Rutin / mekanik read-only** (basit lookup, tek-dosya grep, dar recon) → daha **ucuz model** (sonnet/haiku) düşün — hız+maliyet kazancı, kalite riski düşük.
- **Şüphede opus.** Yanlış "rutin" sınıflaması (iş aslında zor çıkarsa) ucuz-modelle kalite düşürür → muhafazakâr ol.

**Why:** Kaynak: claude-code-best-practice incelemesi (2026-06-24) — "gating/karar=opus, orkestrasyon=haiku, build=opus" (model role'e göre dial'lanır). Repo'nun constitutional-validator/code-reviewer'ı opus; bizim deterministik-script gate'imiz daha güvenilir ama LLM-yargı rollerinde (bug-expert) model-gücü kaliteyi belirler.
