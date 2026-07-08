# ADR 0018 — Agent Takım Yapısı: Katman-Expert + Bug_Expert Gate + Lazy Lifecycle + Audit

**Durum:** Kabul edildi (2026-06-16)
**Bağlam tetikleyici:** Booking post-mortem (ADR 0017) + agent-team yeniden tasarımı.

## Bağlam

Eski model: lider + modül-bazlı feature ajanları (ajan1-sipse/ajan2-ihrse/ajan3-booking = sap-feature) + sap-research + adt-gateway; oturum başında STANDING roster spawn (model B). Sorunlar: (a) **denetçi yok** — feature ajanı builder-yanlılığıyla "done" der, bug ancak kullanıcı test edince çıkar (Booking'in tüm çilesi); (b) modül-roster israfı — booking oturumunda sipse/ihrse ajanları HİÇ çalışmadı; (c) standing state → echo/kirlenme.

Araştırma (web+GitHub, ADR-kanıtlı): **persona-prompting kod görevinde kazanç vermez** (Wharton GAIL + arXiv 2311.10054) → uzmanlık grounding'den gelir; **adversarial code-review gate** kanıtlı değerli (Anthropic code-review plugin, affaan-m); **naive same-model panel tehlikeli** (popularity-trap) → deterministik gate + kanıt-zorunlu asıl FP filtresi.

## Karar — 4 rol + gate + lazy lifecycle + audit

### Roller (`.claude/agents/`)
- **adt-gateway** (mevcut) — TEK SAP yazıcı (single-writer). Değişmedi.
- **frontend-expert** — TÜM freestyle UI5+V2 frontend. SAP'ye yazamaz.
- **backend-expert** — TÜM ABAP/RAP/CDS/DDIC backend. SAP'ye yazamaz.
- **bug-expert** — adversarial kod-inceleme (read-only, kod yazmaz). YENİ.

**Uzmanlaştırma = grounding, persona DEĞİL** (araştırma kanıtı): rol-promtu = minimal persona + mecburi pre-flight okuma + kanonik desen pointer (FE §K / BE adt-rap §32-35) + MCP-routing + scoped tools + skill çağrısı. "Sen uzmansın" tek satır. Modül bilgisi (.rules.md) runtime inject.

### Bug_Expert gate (Booking'in eksik denetçisi)
- **Akış (Model A — lider-aracılı spawn; 2026-06-16 ilk-koşuda netleşti):** Expert substantive build'i bitirir → lider'e **`BUG_GATE_READY` sinyali + diff + niyet/spec + blast-radius** yollar (commit/kabul ÖNCESİ) → **lider TAZE bir bug-expert spawn eder** ve diff'i besler → Bug_Expert verdict (PASS/WARNING/BLOCKER = ADR 0006 dili) → PASS ise lider commit/kabul; BLOCKER/HATA/EKSİK ise lider Expert'i `SendMessage` ile yeniden devreye alır (zorunlu fix) → tekrar gate. **Sonuç her durumda lider'e tek-satır yansır** (görünürlük).
- **Neden Model A (expert-doğrudan değil):** alt-ajanların (frontend/backend-expert) tool setinde **Agent/spawn YOK** → expert yeni bug-expert *yaratamaz*, yalnız var-olana `SendMessage` atabilir. "Her review TAZE" kuralıyla ortada koşan bug-expert yok → expert'in mesajı alıcısız kalır (ilk koşuda gözlendi: expert "to=bug-expert" yolladı, idle bekledi). Tek spawn-yetkilisi lider/main → **gate'i lider tetikler**. (Reddedilen Model B = oturum-boyu standing bug-expert dispatcher: "lazy+taze" ile çelişir, reset disiplini ister.)
- **Kapsam = DIFF + BLAST-RADIUS** (ne diff-only=kaçırır, ne whole-file=gürültü). İlgisiz pre-existing kritik → AYRI işaretle, bloklama.
- **Kanıt-zorunlu 4-soru kapısı** (dosya:satır cite + somut failure-mode + çevre okundu + severity savunulabilir; ≥%80) → FP'yi eler. Spekülatif/stil/filler YASAK.
- **2-faz bul→doğrula:** önce deterministik gate (G3/adt_syntax_check/adt_atc_check) KOŞ, sonra checklist'e karşı semantik incele, her bulguyu çürütmeye çalış.
- **Checklist-ihlali = ZORUNLU FİX, tartışmasız** (builder takdiri yok): checklist'te yalnız must-do var, kozmetik yok. Builder yalnız "bu aslında ihlal DEĞİL, kanıt şu" diyebilir (şiddet değil doğruluk itirazı); ender belirsizlikte lider hakem.
- **Checklist:** `playbook/checklists/bug-checklist-{frontend,backend}.md` (lessons-learned+memory+G3+§K'dan). *Automatable madde → deterministik gate; semantik → Bug_Expert.*
- **Diversity:** tek Bug_Expert + deterministik gate yeterli; same-model panel FP elemez (popularity-trap). Gerçek-diversity panel (farklı model) ileride opsiyon.
- **Çok-Bug_Expert (OPSİYONEL mod — lider takdiri; 2026-06-16 öneri):** bug-expert read-only → **yazma riski sıfır**; gerçek maliyet = token + lider'in verdict-merge'i (risk değil). İki AYRI amaç, karıştırma:
  - **Partition (HIZ):** büyük diff'i **disjoint dilimlere** böl (obje-grubu veya concern başına bir expert) → paralel = wall-clock düşer + dilim-başına derinlik artar. Verdict-merge temiz (çakışmasız).
  - **Diverse-lens panel (GÜVEN, hız değil):** aynı kapsam, her expert'e **farklı mercek** (syntax/dump · aktivasyon-sırası · drift · scope-sızıntısı · güvenlik) → daha çok failure-mode yakalanır. Bu **same-lens popularity-vote DEĞİL** — her expert'in ayrı mandatı var → popularity-trap'e düşmez (üstteki uyarıyla çelişmez). Lider çelişen verdict'leri (biri PASS biri BLOCKER) reconcile eder; aynı-kapsam bulguları dedup eder.
  - **Eşik (ne zaman):** küçük/geri-alınabilir diff → **tek expert** (spawn+brief+merge overhead'i faydadan büyük). Büyük diff (tek expert context'i geriliyor) → **partition**. **Yıkıcı/geri-alınamaz** işlem (tablo kolon DROP, toplu delete, irreversible migration) → **diverse-lens panel** fazladan token'a değer. "Her review TAZE" kuralı korunur (panel üyeleri de taze spawn).
- Lider de kendi geliştirmesinde Bug_Expert kullanabilir.

### Lifecycle — lazy varsayılan + dar bounded-standing (AMENDMENT 2026-06-18)

**Çekirdek içgörü:** context ajanda değil **artefaktlarda** (kod/doc/memory/checklist/log) → lazy çoğu zaman kayıpsız. Standing'i tek teste indir:

> **STANDING ⟺ (a) dışsallaştırılamaz canlı state tutuyorsa, VEYA (b) sınırlı kapsamda yüksek-frekanslı dispatch alıyorsa. Aksi halde LAZY.** ("dışsallaştırılamaz-state testi")

**Rol-bazlı karar:**
- **gateway = STANDING.** ⚠️ Gerekçe NETLİĞİ: bağlantı/CSRF/stateful-lock/persistent-session **MCP server'da** yaşar (ayrı kalıcı süreç), ajanda DEĞİL ([[feedback_push-failure-stale-lock-persistent-session]]) → lazy gateway bile bağlantı-state'i kaybetmez. Gateway'i standing yapan GERÇEK sebep: **(1) serileştirme (single-writer = routing)** + **(2) uçuş-halindeki çok-adımlı işlem akıl-yürütmesi** (lock→PUT→unlock, BDEF+class birlikte-aktive — diziyi ortada re-spawn edersen sıra-bağlamı kopar; lock MCP'de durur ama "nerede kaldım" ajanda). Lazy de correctness-güvenli; standing = verimlilik + güvenlik-marjı.
- **backend / frontend-expert = LAZY varsayılan; bounded feature-standing İSTİSNA.** Yüksek-coupling işte (RAP BO: EML/determination/validation/draft/pricing-text zincirleri · çok-ekranlı tutarlı UX akışı) feature/workstream başında kalk, **feature bitince ZORUNLU yık**. Tekil ekran/düzeltme → lazy.
- **bug-expert = HER ZAMAN LAZY + her review TAZE.** Önceki bug'ın context'i saf kirlilik → en kötü failure-mode: yeni bug'ı eskisine benzetip yanlış iz. (Ayrıca Model-A: expert spawn edemez → lider zaten taze spawn eder; mimari de zorluyor.) Brief'e: **"önceki bug'a benzetme YASAK."**

**Bounded-standing GUARDRAIL'leri (Alt-B çok-dar — eski model-B echo/kirlenme çöpüne dönmemek için):**
1. **Aynı anda EN FAZLA 1 feature-expert standing** (backend VEYA frontend, aktif workstream'e göre) + gateway. Geri kalan her şey lazy. (Tek-takım/Windows in-process kısıtı da bunu dayatır.)
2. **Zorunlu yık:** feature/workstream bitince VEYA ajan idle'a düşünce kapat (boşta-israf yok).
3. **Echo-reset tetiği:** ajan bayat-bağlam belirtisi gösterirse (eski feature/obje adı, çözülmüş bug'a benzetme, yeni duruma eski karar taşıma) → lider **kill + taze re-spawn**.
4. **Şüphede lazy:** standing'in re-okuma/re-brief kazancı belirsizse lazy seç (artefakt-temelli olduğu için kayıp az).

→ Oturum başında roster spawn'ı KALDIR (model B iptal — bu amendment onu GERİ GETİRMEZ; bounded-standing ≠ standing-roster: tek, aktif, sınırlı, echo-korumalı). İhtiyaç anında spawn.

### Audit / observability (loop = agent-to-agent, denetlenebilir olduğu için)
- Alt-ajan TAM transcript'i **sabit adreste:** `~/.claude/projects/<proje>/<session-uuid>/subagents/agent-<id>.jsonl` (her tool_use/result + SendMessage). meta: `agent-<id>.meta.json = {"agentType":"<isim>"}`.
- **`scripts/agent_log.py`** — aktif session'ı otomatik çözer, `--list` / `--agent <isim>` ile okunabilir timeline. Lider **arama yapmadan** denetler.
- Agent-to-agent loop auditable olduğu için **agent-to-agent ile başla**; sorun görülürse lead-routed'a çevir.

## Sonuçlar
- Booking-tarzı geç-keşfedilen bug'lar → Bug_Expert gate ile build-zamanında yakalanır.
- Lider serbest (review offload) ama görünür (tek-satır özet + agent_log derin-audit).
- Persona değil grounding → expert promtları tekrar-kural değil pointer (skill/playbook'a iter).
- Roster israfı biter (lazy).

## İlgili
- Roller: `.claude/agents/{frontend-expert,backend-expert,bug-expert}.md`
- Checklist: `playbook/checklists/bug-checklist-{frontend,backend}.md`
- Audit: `scripts/agent_log.py`
- İşletim modeli: `governance/agent-teams-operating-model.md`
- Bağlı: ADR 0006 (reviewer verdict), 0007 (MCP), 0016 (drift-guard), 0017 (UI build gate), feedback_subagent-karar-kurali · feedback_done-tam-kapsam-dogrula
