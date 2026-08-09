---
type: operating-model
title: Agent Teams İşletim Modeli — çok-ajan orkestrasyon kuralları
status: active
last-updated: 2026-06-14
source: deep-research (4 paralel subagent, 2026-06-14) — Anthropic/Cognition/LangChain/single-writer
---

# Agent Teams İşletim Modeli

> **Amaç:** Çok-ajanlı (agent teams) çalışmayı patinaj yapmadan, kanıtlı desenlerle yürütmek.
> Bu doküman BAĞLAYICI: lider (ana oturum) her takım kullanımında buna uyar. CLAUDE.md + AGENTS.md buraya pointer verir.
> Dayanak araştırması: [[research/agent-teams-best-practices]] (özet bu dokümanda), kaynaklar §11.

## 1. NE ZAMAN takım? (ne zaman SOLO)
- **Çok-ajan OKUMADA kazanır, YAZMADA kaybeder** (Anthropic: paralel kazanç read-heavy keşifte; "çoğu kodlama paralelleşmez"; Cognition: "çelişen kararlar kötü sonuç").
- **Takım KULLAN:** gerçekten paralelleşen, okuma/araştırma-ağırlıklı iş — kod tabanı/where-used tarama, spec sentezi, çok-modüllü inceleme, boşluk/sabit analizi, eski-sistem damıtma.
- **SOLO kal:** tek-dosya/seri iş, basit düzeltme, ardışık bağımlı adımlar. Çok-ajan ~15× token; gereksiz fan-out yapma.
- **Ölçek kuralı:** basit → 1 ajan; karşılaştırma → 2-4; geniş → 10+. (Karmaşıklığa göre, sabit değil.)

## 2. Roller (`.claude/agents/` — tool-düzeyinde enforcement)
| Rol | Tanım | SAP yazma | Kullanım |
|---|---|---|---|
| **lider** (ana oturum) | — (tüm araçlar) | Koşullu (§3) | Orkestrasyon, görev dağıtımı, ortak-obje sıralama, kullanıcı muhatabı |
| **adt-gateway** | `.claude/agents/adt-gateway.md` | ✅ TEK yazıcı (write araçları SADECE onda) | Takım modunda tüm SAP yazımı |
| **sap-feature** | `.claude/agents/sap-feature.md` | ❌ tool-düzeyinde YOK | Özellik tasarımı + yerel kaynak + read-only SAP |
| **sap-research** | `.claude/agents/sap-research.md` | ❌ yok (repo kodu da düzenlemez) | Salt-okunur keşif/analiz/web |

→ feature/research **fiziksel olarak SAP'ye yazamaz** (allowlist'te write araçları yok). Hook çağıran-ajanı ayırt edemediği için enforcement **allowlist ile** yapılır, hook ile değil.

**Araç/kod/altyapı fix'i — REVİZE 2026-08-01 (kullanıcı onaylı; ilk kural 2026-06-14):** paylaşılan tooling bug'ında gateway/expert'ler DÜZELTMEZ, lider'e raporlar (değişmedi). Liderin akışı artık `playbook/howto-infra-fix-proseduru.md`: **sınıflama+EXPRESS(S0-mekanik)+son-söz+commit+meta-infra = LİDER; kuyruk-fix'lerinin ÜRETİMİ = taze-spawn `infra-expert`** (worktree'de, F1-F5 + üç-bağlam-test zorunlu; gateway-paradigmasının infra'ya uygulanması — taze bağlam görev-bulaşmasını fiziksel keser). Gerekçe-evrimi: 'tek sahip' ilkesi korunur (infra'nın tek ÜRETİCİ-yazıcısı infra-expert, tek KARAR-vericisi lider); nokta-fix/bağlam-daralması riski taze-spawn'la çözülür.

**ÇEKİRDEK DEĞİŞMEZLER — her rol tanımı taşır (ajan asla unutmasın):** ADR 0005 yasakları · **TAHMİN ETME** (mevcut artefakt/playbook/standard'dan doğrula, canlı teyit, "activated"a güvenme, DTEL/append adı önerme) · run_review pre-flight (yazma rolü). Bunlar (1) her `.claude/agents/*.md` system-prompt'una gömülü, (2) CLAUDE.md çekirdek-davranış satırıyla otomatik yüklenir, (3) spawn brief'inde tekrarlanır (savunma derinliği). Memory'deki feedback'ler **lider'e özeldir** → alt-ajana ulaşması için bu üç kanal şarttır (varsayma).

## 2A. GÜNCEL MODEL (ADR 0018) — 4 rol + Bug gate + LAZY lifecycle + audit

> Eski **modül-feature roster** (se_a/se_b/booking = sap-feature) + **STANDING spawn (model B)** İPTAL. sap-feature/sap-research role-def'leri uyumluluk için durur; go-forward = bu.

**Roller (KATMAN-bazlı):** `adt-gateway` (TEK SAP-yazıcı) · **`frontend-expert`** (tüm FE) · **`backend-expert`** (tüm ABAP/RAP) · **`bug-expert`** (adversarial kod-inceleme, read-only) · **`infra-expert`** (paylaşılan-altyapı fix-üretimi; YALNIZ worktree+kuyruk-kaydı; howto-infra-fix ADIM-3). **Uzmanlaştırma = grounding** (mecburi pre-flight okuma + kanonik desen pointer + MCP-routing + scoped tools + skill çağrısı), persona DEĞİL — araştırma kanıtı: "sen uzmansın" kod görevinde kazanç vermez (ADR 0018).

**BUG GATE (akış — Model A, lider-aracılı; 2026-06-16 ilk-koşuda netleşti):** Expert substantive build bitince → lider'e **`BUG_GATE_READY` + diff + niyet/spec + blast-radius** yollar (commit/kabul ÖNCESİ) → **lider TAZE bug-expert spawn edip** diff'i besler → verdict **PASS/WARNING/BLOCKER** (= ADR 0006 dili) → PASS=lider commit; BLOCKER/HATA/EKSİK=lider Expert'i `SendMessage` ile yeniden devreye alır (zorunlu fix). *Neden lider-aracılı: alt-ajan spawn edemez; "to=bug-expert" doğrudan mesaj alıcısız kalır (her review taze → koşan bug-expert yok).* **Kapsam = diff + blast-radius** (ne diff-only, ne whole-file). **Bulgu tipi:** HATA (bug) / EKSİK (must-do/UX karşılanmamış, "hata değil") / ÖNERİ (checklist-dışı, bağlayıcı DEĞİL). **Checklist-ihlali (HATA+EKSİK) = ZORUNLU FİX** — builder takdiri yok ("önemsiz" diyemez; yalnız "bu aslında ihlal değil, kanıt şu" diyebilir; ender belirsizlikte lider hakem). Checklist: `playbook/checklists/bug-checklist-{frontend,backend}.md` (*automatable → deterministik gate; semantik → bug-expert*). Sonuç her durumda lider'e tek-satır. **OPSİYONEL çok-bug-expert (lider takdiri):** read-only=yazma riski sıfır, maliyet=token+merge; **büyük diff → partition** (disjoint dilim, HIZ), **yıkıcı/geri-alınamaz işlem (tablo DROP/toplu delete) → diverse-lens panel** (farklı mercek, GÜVEN — same-lens popularity-vote değil), **küçük/reversible → tek expert**. Panel üyeleri de TAZE. Detay+eşik: ADR 0018.

**LIFECYCLE = LAZY varsayılan + DAR bounded-standing (ADR 0018 amendment 2026-06-18):** oturum başında roster SPAWN ETME. Karar tek teste iner — **"dışsallaştırılamaz-state testi": STANDING ⟺ (a) dışarı yazılamayan canlı state tutuyorsa VEYA (b) sınırlı kapsamda yüksek-frekanslı dispatch alıyorsa; aksi halde LAZY"** (context ajanda değil artefaktlarda → lazy çoğu zaman kayıpsız).

| Rol | Lifecycle | Gerekçe |
|---|---|---|
| **adt-gateway** | **STANDING** | Serileştirme (single-writer=routing) + uçuş-halindeki çok-adımlı işlem akıl-yürütmesi (lock→PUT→unlock). ⚠️ Bağlantı/CSRF/lock **MCP server'da** (ajanda değil) → lazy de güvenli; standing = verimlilik+marj. |
| **backend-expert** | **LAZY** varsayılan · **bounded feature-standing** istisna | RAP yüksek-coupling (EML/det/val/draft/pricing-text) → feature başında kalk, **bitince ZORUNLU yık**. Tekil iş → lazy. |
| **frontend-expert** | **LAZY** varsayılan · app-build'de **bounded-standing** | Çok-ekranlı tutarlı UX akışı → app-build boyunca standing; tekil ekran/fix → lazy. |
| **infra-expert** | **HER ZAMAN LAZY + vaka-başına TAZE** | Görev-bağlamı bulaşması = düzeltilmeye çalışılan hastalığın kendisi; taze-spawn + worktree fiziksel izolasyon. |
| **bug-expert** | **HER ZAMAN LAZY + her review TAZE** | Önceki bug context'i = saf kirlilik (yeni bug'ı eskiye benzetme failure-mode). Brief'e "önceki bug'a benzetme YASAK". Model-A da zorluyor (expert spawn edemez → lider taze spawn). |

**Bounded-standing GUARDRAIL (eski model-B echo/kirlenme çöpüne dönme — Alt-B çok-dar):** (1) aynı anda **EN FAZLA 1** feature-expert standing (backend VEYA frontend) + gateway; gerisi lazy. (2) feature bitince/idle'da **zorunlu yık**. (3) **echo-reset tetiği:** ajan bayat-bağlam gösterirse (eski feature/obje adı, çözülmüş bug'a benzetme) → lider kill+taze re-spawn. (4) şüphede lazy. *bounded-standing ≠ standing-roster: tek, aktif, sınırlı, echo-korumalı.*

**PLAN-ARTIFACT (radar 2026-08-01, ADOPT-2 — kullanıcı onaylı):** Çok-adımlı ve
geri-alınamaz/maliyetli SAP zincirlerinde (örn. domain→DTEL→struct→tablo→CDS→BDEF; toplu
silme; transport'a çok-objeli yazım) lider, dispatch'ten ÖNCE planı `.tmp/plan-<konu>.md`
dosyasına yazar (adımlar + obje listesi + geri-alma notu) ve kullanıcı/oturum onayından
geçirir. "Kararları önce topla" kuralının kalıcı-artefakt hali: RESUME kopmasında plan
dosyadan rekonstrükte edilir; adım-fail'de baştan değil kalınan adımdan devam edilir.
Tek-obje/S0 işlerde ZORUNLU DEĞİL (bürokrasi üretme).

**P7 boşta-bekletme kuralı (2026-07-31 denetim ölçümü — 292 transcript):** ajan duvar-saatinin
**%33'ü** "liderden yeni mesaj bekleyen" boşta ajanlardı. Kural: ajandan FİNAL raporu alınınca
(bounded-standing gateway hariç) ajanı beklemede TUTMA — sonraki iş YENİ taze spawn'dır
(açılış ~53K token maliyetine rağmen: context-kirlenmesi/echo riski + boşta-şişme > açılış).
Metrik radar turunda izlenir (`agent_time_report` boşta-%; baseline %33, hedef <%15).

**AUDIT:** alt-ajan TAM transcript SABİT adreste (`<session>/subagents/agent-<id>.jsonl`) → **`python scripts/agent_log.py --agent <isim>`** (arama YOK). Loop = **agent-to-agent** (auditable olduğu için); sorun görülürse lead-routed'a çevir.

## 3. Single-writer KOŞULLU model (KRİTİK)
Gateway'in tek amacı = **eşzamanlı yazıcıları serileştirmek**. Tek yazıcı varsa gereksizdir.
- **Takım YOK (solo):** Lider SAP'ye **DOĞRUDAN yazar** (gateway gereksiz; run_review pre-flight + ADR 0005 yine geçerli).
- **Takım AKTİF (≥1 yazabilecek alt-ajan):** Tüm SAP yazımı **adt_gateway'den** geçer; **lider doğrudan yazmaz**, gateway'e devreder; feature/research zaten tool-bloklu.
- Bu, "Single-Writer Principle + serialization" deseninin doğru uygulaması (çakışma kaynakta elenir).

## 3A. Dosya bölgeleri — yazım yetkisi (2026-06-14, kullanıcı tasarımı)
3 bölge. **Lider = TEK committer + her `git diff`'i inceler** → bölge-dışı yazım kalıcı olmadan yakalanır.

| Bölge | İçerik | Yazan |
|---|---|---|
| **A — Metodoloji/Yönetişim/Araç** | `CLAUDE.md`, `AGENTS.md`, `standards/`, `playbook/`, `governance/`, `.claude/`, `scripts/`, `mcp_servers/` | **yalnız LİDER** (diğerleri salt-okunur) |
| **B — Özellik/Paket eseri** | `ERP/<pkg>/` SAP kaynak (cds/bdef/abap/ddl/ui) + `docs/` (FS/TS) + `SESSION_NOTES.md` + `.rules.md` | **sahibi feature ajanı (kendi paketi) + lider** (gateway OKUR, düzenlemez) |
| **C — SAP sistemi** (canlı obje) | DDIC/CDS/class | **yalnız gateway** (MCP write) / solo'da lider |
| **D — Lider süreklilik deposu (memory)** — repo DIŞI | `~/.claude/projects/.../memory/*.md` + `MEMORY.md` index | **yalnız LİDER** (ajanlar ders/karar/tuzağı lider'e **RAPORLAR**, dosya/pointer YAZMAZ; süreklilik tek-yazıcı = drift/duplikasyon/tutarsız index önlenir) |
| **.tmp/** (gitignore) | scratch | herkes |
| **git commit** | — | **yalnız lider** |

- **Tek cümle:** proje-geneli kural/yöntem .md = **LİDER**; belirli paketi/özelliği belgeleyen .md = o **feature ajanı**; **lider memory'si (Bölge D) = yalnız LİDER** (repo dışı ama Bölge A gibi korunur).
- Araç/kod kök-fix akışı = howto-infra-fix (lider sınıflar/kapatır; kuyruk-üretimi infra-expert) (§2). Yapısal naming/prefix kararı (paket .rules.md içinde bile) = lider.
- **Enforcement = orantılı (1+2+3, kullanıcı kararı 2026-06-14):** (1) research SAP-write + Edit yok (sert); (2) lider tek-commit + diff-inceleme (sert geri-durdurucu); (3) rol prompt'larında bölge (savunma derinliği). Saf `tools:` allowlist yol-granüler DEĞİL + Bash süper-küme → tam-önleme için ileride PreToolUse yol-guard (hook stdin `transcript_path`'te `/subagents/` = takım üyesi tespiti) gerekir; şimdilik kapsam dışı (risk düşük: ajanlar prompt'a uyar + commit gate yakalar).
  - **DOĞRULANDI 2026-06-14 (ihlal + backstop çalıştı):** gateway, explicit "commit=lider" talimatına RAĞMEN increment-2'yi kendi `git commit`'ledi (Bash porozitesi — instruction tek başına yetmez). **Lider gün-sonu git-log denetiminde YAKALADI** (içerik doğruydu, geri alınmadı) → gateway-def'e ⛔ `git commit/push/add ASLA` eklendi. Ders: tam-önleme için PreToolUse git-guard (transcript_path `/subagents/`) gerçek değer; o gelene dek **lider HER commit öncesi `git log`/`git status` denetler** (sole-committer disiplini bu denetimle ayakta durur).

## 3B. Oturum-durumu / Gün-sonu / Resume (süreklilik) (2026-06-14, kullanıcı sorusu)
**Süreklilik sahibi = LİDER.** Ajanlar **durumsuz işçi**: süreklilik onların canlı bağlamında DEĞİL, kalıcı artefaktlarda yaşar.

| Katman | Oturum kapanınca |
|---|---|
| Repo Zone B yerel kaynak (ajanın hazırladığı) · SAP objeleri (gateway yazdığı) · task list (`td-agent-teams/tasks`) · SESSION_NOTES.md · memory · git | **KALICI** |
| Ajanın canlı bağlamı (aklındaki iş) | **UÇUCU — ölür** (transcript dosyası kalır, otomatik resume YOK) |

- **Task takibi:** tek konsolide paylaşımlı task listesi (kalıcı). Ajanlar kendi task durumunu `TaskUpdate` ile işaretler; **narrative sürekliliğin tek sahibi = lider** (hub). Kullanıcı "gün sonu" der → lider toparlar.
- **MEMORY YAZIMI = YALNIZ LİDER (her zaman, gün-sonu değil de).** Lider'in süreklilik deposu (`~/.claude/projects/.../memory/` dosyaları + `MEMORY.md` index) repo DIŞINDA olsa da Zone A gibidir: **ajanlar (feature/research/gateway) memory dosyası/pointer'ı YAZMAZ.** Oturum-içi ders/tuzak/karar çıkaran ajan → lider'e **SendMessage ile raporlar** ("memory'ye şu yazılsın"); yazma kararını + dosyayı + MEMORY.md pointer'ını **lider** yapar. Gerekçe: tek-yazıcı = drift/duplikasyon/tutarsız index önlenir; süreklilik tek elde. (2026-06-15 ihlali: bir feature-ajan dersi doğrudan memory'ye yazdı + MEMORY.md pointer ekledi → kural role prompt'larına `.claude/agents/*` taşındı, T11.)
- **GÜN-SONU protokolü (yarım iş varken):** (1) lider her aktif ajana **checkpoint** sorar — diskte ne hazır (yollar) + tam sıradaki adım + açık-noktalar, sonra dur; (2) lider kalıcılaştırır: task'a "kaldığı yer" notu + SESSION_NOTES'a ajan-bazlı entry (yapıldı/sıradaki/açık-nokta/dosya yolları) + **WIP commit**; (3) **`git push origin main` — gün-sonu push ZORUNLU** (kullanıcı kuralı 2026-06-25): origin yedeği + paylaşımlı-repo ekip senkronu + ultrareview no-arg kapsamı dar kalır; "gün sonu yapalım" denince commit YETMEZ, push şart; (4) memory'yi karar değiştiyse güncelle; (5) oturum kapanır, ajan süreçleri ölür → durum diskte güvende.
- **RESUME protokolü (sonraki oturum):** config kalıcı → lider ajanları yeniden spawn eder + **resume brief** (task durumu + hazır dosya yolları + sıradaki adım + çözülen açık-noktalar) → ajan dosyalarını OKUYUP kaldığı yerden devam (artefakt = otorite, TAHMİN YASAK). Ajan kafadan resume etmez, artefakttan rekonstrükte eder.
- **Risk:** ajan mid-write iken oturum biterse dosya yarım kalabilir → gün-sonu checkpoint'i **yazımlar tamamlandıktan/raporlandıktan sonra** yap; yarım dosyayı commit etme.

## 4. İletişim kuralları
- **Lider = hub.** feature/research/gateway lider'e `SendMessage` ile rapor eder; otomatik **etkileşim YOK** (kendiliğinden senkronlanmaz).
- **Ortak objeleri lider sıralar:** paylaşılan DDIC/CDS/tablo/API (T_DORHD/T_DORIT, T_SETYPE, ZSD000_*, booking API) → tek ajana hazırlatılır, gateway **bir kez** yazar; iki ajana paralel ALTER yaptırılmaz.
- **Context paylaş (Cognition İlke 1):** ajana tek talimat değil **ilgili tam iz** ver (rules/.rules.md/SESSION_NOTES/mutabık spec) → çelişen örtük kararları (naming/prefix) önler.
- **Yapılandırılmış handoff:** feature→gateway "yazma niyeti" serbest metin değil; obje adı + tip + yerel kaynak yolu + transport içeren net spec. Gateway aynen yazar (redesign yok).
- **Kararları ÖNCE topla, SONRA konsolide yönerge (2026-06-14, kullanıcı):** bir build-unit'e başlamadan önce o unit'in TÜM user-kararlarını **tek tek** kullanıcıya sor + topla; ancak ondan sonra ajana **tek konsolide, tam-kararlı** yönerge ver. "Karar→dispatch→ajan mid-build yeni açık-nokta→tekrar sor→tekrar dispatch" ping-pong'undan kaçın (hem kullanıcı hem ajan round-trip'i + patinaj azalır). İstisna: açık-noktalar ancak recon'dan çıkıyorsa → önce recon (salt-analiz), sonra çıkan kararların HEPSİNİ topla, sonra build dispatch.

### 4A. Background-ajan gürültü disiplini (2026-06-23, kullanıcı sorusu "neden sürekli stale durum?")
Uzun-yaşayan background ajanlarla (özellikle standing gateway) çalışırken `idle_notification` gecikmesi + task re-trigger'ı **sahte "blocked/stale" gürültüsü** üretir. Dört kural bunu kaynağında keser:
- **A — `idle_notification`'a ASLA aksiyon alma.** İdle bildirimi ajanın **o an** ki anlık-fotoğrafıdır, lider'e **bir tur sonra** ulaşır → çoğu zaman lider çoktan yeni talimat göndermiştir, bildirim eskimiştir. Lider yalnız explicit **`SendMessage` raporuna** göre hareket eder (onlar niyetli + nokta-zamanlı). İdle ping = FYI, canlı-durum değil.
- **B — Background ajanın İÇ alt-adımları için harness-task AÇMA.** Sıralı push zinciri (3 entity→bdef→class→publish) gibi alt-adımları `TaskCreate` ile task'lama; zincir ajanın **talimatında** dursun. Task'lanan alt-adımlar sahibe (gateway) sürekli **re-trigger** olur → "zaten tamam" gürültüsü. Task yalnız gerçek, lider-sahipli iş-kalemi için (ör. "kök-sebep + kalıcı önlem").
- **C — Çelişen raporda lider DOĞRUDAN doğrular.** Ajan "X düzeltilmemiş/satır 203 hâlâ generic" derken lider başka türlü düşünüyorsa → **dosyayı/SAP'yi kendisi okur** (grep/adt_get), **satır-no'ya değil içeriğe** bakar. Ajanlar sabit-offset okuyunca stale satır-no'ya düşebilir (fix satırları kaydırır). Bu, deadlock'u kırar (`feedback_ajan-olumsuz-donusu-kanitla-sorgula` lider tarafı).
- **D — Tamamlanan task'ı ANINDA `completed` işaretle** → re-trigger penceresi kapanır.
> Not: gerçek blocker'lar (DDLS shell reçetesi, generic-tip aktivasyon-fail, pseudo-comment yerleşimi) bu gürültüden AYRIDIR — onlardaki gidiş-geliş normal SAP-geliştirme iterasyonudur, A-D kapsamı değil.

### 4B. Checkpoint-heartbeat — uzun-iş görünürlüğü (2026-07-12, kullanıcı sorusu)
Uzun/token-ağır tek-ajan işinde (ör. backend-expert build), lider adım-adım ilerlemeyi **CANLI göremez**:
local-agent transcript'i canlı flush etmez (`...\tasks\<id>.output` uzun süre 0-byte görünebilir) ve
ham okumak lider context'ini taşırır (§5-3 output-peek yalnız sessizlikte, kontrollü). Çözüm: ajan
**kendi** doğal kilometre-taşlarında lider'e kısa ilerleme yollar. Brifinge ekle (auto-memory'yi görmez).
- **NE:** her kilometre-taşında 2-3 satır `SendMessage({to:"main"})` — "yaptım (X) / sırada (Y) / açık-nokta (Z)".
  Doğal taşlar: ön-okuma bitti · canlı-teyitler (D-x) bitti · her ana metot/INCLUDE/entity bitti · build bitti (=`BUG_GATE_READY`).
- **CADENCE = kilometre-taşı, SAAT DEĞİL.** Ajan tek LLM döngüsüdür → **öz-zamanlayıcısı yok**; yalnız
  adımlar (tool-call) ARASINDA hareket eder, uzun **tek** bir çağrının (ör. 2 dk'lık `adt_get`) ortasında
  kendini bölemez. "Her 5 dk" garanti EDİLEMEZ; kilometre-taşı başına ≈ birkaç dakikaya denk gelir.
- **AMAÇ = görünürlük ("ne yapıyor"), canlılık garantisi DEĞİL.** Ajan bir çağrı İÇİNDE asılırsa
  (asıl patinaj riski) zaten heartbeat gönderemez → asılmayı **§5 watchdog / output-peek** yakalar.
  İkisi tamamlayıcı: **heartbeat = içerik, watchdog = nabız.**
- **§4A ile TUTARLI:** heartbeat **niyetli + nokta-zamanlı** bir `SendMessage`'dır → §4A-A'nın "lider yalnız
  explicit `SendMessage` raporuna göre hareket eder" ilkesine girer (stale `idle_notification` gürültüsü DEĞİL).
- **NE ZAMAN KAPAT:** geniş fan-out (çok ajan × sık heartbeat = mesaj seli, §4A/§6 gürültü) → kapat veya
  yalnız "başladım / bitti"ye indir. Tek uzun ajan → aç (bedava sayılır). Kısa iş (<birkaç dk) → gerekmez.

### 4C. Okuma disiplini — token-verimliliği vs tazelik (2026-07-13, kullanıcı sorusu)
Gözlem: uzun bir düzenleyen-ajan aynı büyük kaynak dosyasını **her Edit'ten sonra baştan** okuyup
tek run'da 24× Read etti → ağır token israfı (exec-süre değil, context maliyeti). Brifinge ekle
(auto-memory'yi görmez). **İki katman + bir kırmızı-çizgi:**
- **ORTAK (tüm ajanlar):** Her hedef dosyayı run içinde BİR kez taze oku; `git diff`/snapshot'tan çalış;
  **değişmemiş** dosyayı aynı run'da gereksiz tekrar-okuma YOK. Genelde ranged/offset okuma yeterli.
- **DÜZENLEYEN ajanlar (backend/frontend/gateway):** Edit'ten sonra aynı dosyayı **baştan tekrar Read ETME** —
  harness Edit-state'i izler ("no need to Read it back"); hedefli `old_string` ile Edit yeniden-okuma gerektirmez.
- **READ-ONLY ajanlar (reviewer/research/Explore):** Edit-eki UYGULANMAZ (Edit yapmazlar); onlara yalnız
  ORTAK madde — her dosyayı bir kez, tek snapshot. Brifinge "Edit sonrası okuma" yazma (anlamsız).
- **🔴 KIRMIZI-ÇİZGİ — tazelik her zaman kazanır (ADR 0016 / PULL-BEFORE-EDIT):** Bu kural YALNIZ **aynı-run**
  gereksiz tekrarını keser. **Her yeni run/resume başında ve dosya değişmiş olabilecekse TAZE oku** —
  "önceki oturumda okumuştum, atlayayım" YASAK: kod değişmiş olabilir (lider/başka ajan editlemiş, drift).
  Resume'da ajanın context'indeki eski kopyaya güvenip diskteki taze sürümü ezmek = veri kaybı. Kesilecek
  olan **cross-run tazelik okuması DEĞİL**, aynı-run gereksiz tekrardır.

**Zaman/verimlilik analizi için LOG (2026-07-13):** Ampirik olarak `...\tasks\<id>.output` transkripti
**güvenilir kalıcılaşmıyor** — tek-run read-only ajanlar (bug-expert) ve bazı gateway koşuları **0-byte**
kaldı; yalnız resume'li/uzun ajan (backend-expert) tam yazıldı. Yani lider per-tool analiz için transkripte
**GÜVENEMEZ**. Ajanın zaman-analizi isteniyorsa → **brifinge öz-rapor ekle:** ajan final `SendMessage`'ında
kısa "VERİMLİLİK ÖZ-RAPORU" versin — faz-sınırlarında `date +%s` (her tool'a değil), toplam ~tool sayısı,
tekrar-okunan dosya, retry/patinaj noktası. Kaba wall-clock + tool-sayısı zaten completion `usage`'dan gelir
(`subagent_tokens`/`tool_uses`/`duration_ms`); öz-rapor bunun faz-kırılımını ekler. Analiz script şablonu:
lider `scratchpad`'inde `agent_time_analysis.py` (transkript doluysa per-tool döker).

**(4) HERHANGİ bir alt-ajanın "YAPILAMAZ"/olumsuz raporunu KANITSIZ KABUL ETME — SORGULA (lider; BAĞLAYICI).** **Her** alt-ajan (`adt-gateway`/`bug-expert`/`backend-expert`/`frontend-expert`/`sap-research`/`general` — gateway yalnız en sık örnek) "yapılamaz / desteklenmiyor / blocker / yok / bulunamadı" derse, bunu doğru kabul edip **ona göre işlem yapma veya durma**. Önce sorgula: bu **gerçekten imkânsız mı**, yoksa **"bu ajanın elindeki araçlarla/kapsamla yapamadı/bulamadı"** mı? Ajanın tool-görünümü repo'nun gerçek kabiliyetinden DARDIR. Protokol: (a) iddiayı **repo'da ara** — aynı işi yapan mevcut `scripts/*.py` / playbook reçetesi / alternatif yol var mı (`grep`/Glob); (b) varsa ajanı o yolla **yeniden yönlendir/taze-spawn et**; (c) yoksa iddiayı **kendin canlı doğrula**, sonra kullanıcıya ilet. **Ders (2026-06-22):** gateway "SRVB description typed-tool ile değişmez" dedi → lider kabul etti; oysa `scripts/sap_set_object_description.py` tam bu senaryo için (voyage "Sefer..." düzeltme) yazılmıştı. Bu, ajan-tarafı [[feedback_dogrula-once-flag-spekulatif-blocker-yasak]]'ın **lider-tarafı tamamlayıcısı**; kök ilke = TAHMİN YASAK = kanıtlı hareket et. Bkz. [[feedback_ajan-olumsuz-donusu-kanitla-sorgula]].

### UI BUILD DONE-CRITERIA + LİDER DOĞRULAMA (ADR 0017 — Booking post-mortem)

> Booking UI'da çok fazla amatör patinaj oldu çünkü (a) çalışan kardeş deseni yerine sıfırdan yazıldı, (b) ajan "done/verified" dedi ama runtime hata ancak kullanıcı test edince çıktı, (c) lider doğrulamadan kabul etti. Bunlar **bağlayıcı**:

1. **Plumbing'i icat etme — içeriği değil (app-kopyalama DEĞİL):** Freestyle UI5+V2'nin **mekanik/plumbing** kısmı (save=sıralı `update(merge)`, nav=`to_X`, `setData` tam şekil, master-detail seçim-wiring, MERGE tarih-null) **tek-doğru-yol, uygulamadan bağımsız** → [`playbook/ui-freestyle-odata-v2.md`](playbook/ui-freestyle-odata-v2.md) **§K**'yı **referans al, sıfırdan icat etme** (icat = çözülmüş bug'ı geri getirmek). **Uygulamaya özel her şey BESPOKE yazılır** (entity/servis, alan listesi, ekran layout/grid, iş/gating kuralları, VH hedefleri, label, akış) — hiçbir ekran diğerinin kopyası değildir. Sınır: *framework-plumbing = reuse · iş-içeriği = bespoke*.
2. **"done/verified" kanıtsız KABUL EDİLMEZ** (lider): UI build için → `check_ui5_freestyle_traps.py` PASS **+ runtime smoke** (G1 playwright-cli, yoksa elle console: zero render error + ana akış). SAP yazımı için → `adt_get` active readback. "node --check OK / XML well-formed" runtime/fonksiyonel hatayı YAKALAMAZ — yeterli değil.
3. **Recon ≠ implementasyon:** Bir recon dokümanı "done" değildir. Çıkarılan kural/gating UI'a **gerçekten kodlandı mı** lider doğrular. *Done = tam kapsam:* "tamam" demeden önce çıktı, işin TAM kapsamına karşı madde-madde doğrulanır; bilinçli ertelenen parça açıkça flag'lenir + register'a yazılır (sessiz eksik = done değil).
4. **Kör-bug YASAK:** "Kaydedilemedi" gibi opak hatada deneme-yanılma yapma → önce **gerçek hatayı** al (F12 Network/Console status+body, ya da gateway ile birebir replikte). Kanıtsız tek satır bile değiştirme.

---


**R3 — MEMORY KÖPRÜSÜ (2026-08-01, denetim):** Alt-ajan auto-memory'yi GÖRMEZ (resmî). Lider her substantive spawn'dan önce MEMORY.md'yi görev anahtar-kelimeleriyle tarar ve eşleşen 2-5 dersin ÖZÜNÜ brifin zorunlu 'Göreve-ilişkin dersler' alanına yazar (şablon: `claude/templates/spawn-brief.md` §6; eşleşme yoksa alanı 'ilgili ders yok' ile AÇIKÇA doldur — boş bırakma). Brifing-lint (watchdog_launch) şablon izlerini nudge'lar.

## 5. Gateway Gözlemlenebilirlik Protokolü (opak-patinaj önleme)
Gateway arka planda opaktır; takılırsa görünmez. Beş katman:
1. **Deneme/eskalasyon merdiveni (kör döngü yerine):** obje başına **3 denemeye** kadar dene (geçici CSRF/lock vb.). 3'te çözülmezse → **ZORUNLU ARAŞTIRMA** (`playbook/<obje-tipi>.md` + `playbook/lessons-learned.md` + ilgili `playbook/checklists/` + hata pattern'i — yani lider takılınca neye bakıyorsa) → bulguyla devam. **Toplam 5 denemede** hâlâ başarısız → **DUR + lider'e gel** (ham hata + denenenler + araştırma bulgusu). Sınırsız/kör tekrar YASAK → patinaj 5 ile sınırlı.
2. **Obje-başına raporlama:** her objeden sonra lider'e kısa sonuç (✓/✗); lider kullanıcıya iletir. Toplu sessizlik = sinyal.
3. **Canlı output-dosyası peek:** arka plan ajanının transkripti `...\tasks\<id>.output` dosyasında; sessiz kalırsa lider o dosyayı **okur** → neye takıldığını görür.
4. **Lider watchdog:** makul sürede "bitti" gelmezse lider output-dosyasını okur / "durum?" sorar / takıldı sayar.
5. **Küçük batch:** gateway'e 1-3 obje/iş ver → opaklık penceresi minimal.

## 6. Maliyet / model katmanı
Çok-ajan ~15× token. Opsiyonel katman: lider/gateway Opus, feature Sonnet, research Haiku. SAP precision gerektiğinde kaliteyi düşürme; tiering bir maliyet kaldıracı, zorunlu değil.

**SPAWN-MODEL-FLOW (kullanıcı-onaylı matris, 2026-07-31 — denetim P8):** İki seviye:
① **Politika = KULLANICI** — frontmatter varsayılanları yalnız kullanıcı-onaylı PR ile değişir.
Onaylı matris: denetçi (bug-expert) + yazıcı (adt-gateway) + backend-expert = **opus SABİT**
(asimetri ilkesi: denetçi/yazıcı asla düşürülmez); frontend-expert + sap-research +
sap-feature = **sonnet** varsayılan. ② **Spawn-anı = LİDER, mekanik uygulama** — ITG kapsam
sınıfından türetilir: S2/yeni-desen/karmaşık iş → `Agent(model:"opus")` ile YÜKSELT;
sap-research'te mekanik envanter/döküm → `haiku` İNDİRİLEBİLİR; tabloda karşılığı olmayan
durum/sapma → kullanıcıya sor. Brifin başına tek satır iz: "Model: X — rol×kapsam".
⚠ Beyan ≠ fiilî model: atama transcript `message.model` alanından CANLI doğrulanır
(allowlist geçersiz değeri sessizce inherit'e düşürür). Pilot karar kuralı: Sonnet'te
bug-gate BLOCKER oranı veya rework turu ARTARSA o rol Opus'a geri döner.

**Model-tiering DAİMA DECLARATIVE kalır (D34g, 2026-07-08):** tiering ajan-tanımı
frontmatter'ında/spawn-parametresinde BEYAN edilir; hook/guard ile HARD-enforce EDİLMEZ
(sc4sap dersi: model-zorlaması guard'ı revert edildi — precision işinde tier-kilidi
kaliteyi sessizce düşürür, ihtiyaç anında override edilemez). İhlal sinyali değil,
tercih sinyalidir.

**Docs-expert rol değerlendirmesi (D34g):** FS/TS/KD üretimi bugün feature-expert +
bug-expert(doc-checklist) hattında. Ayrı bir docs-expert rolü ANCAK şu tetikle açılır:
bir sprint içinde ≥3 bağımsız doküman-turu VE doc-bug-gate'te tekrar-eden format
BLOCKER'ları. O güne dek rol AÇILMAZ (LAZY ilkesi §2A).

**Per-subagent project-scope memory PİLOTU (D34g):** alt-ajanlara proje-scope memory
verilebilir (okuma serbest) — ANCAK memory-TERFİ (yeni kalıcı kayıt/düzeltme) YALNIZ
liderde kalır (tek-yazıcı; çift-kaynak drift önlemi §10). Pilot ölçütü: ajanın
tekrar-brief maliyeti düşüyor mu; kirlilik (yanlış/bayat kayıt) sıfır mı. Kirlilikte
pilot geri alınır.

## 7. Gate'ler (kalite)
- Her SAP yazımı: **run_review pre-flight (ADR 0006)** — gateway uygular; BLOCKER → yazma.
- ADR 0005 guardrail + MCP server-side guard = iki katman (her zaman).
- (İleride) takım hook'ları (TaskCompleted/TeammateIdle) ile gate dayatma — şimdilik gateway içi.

## 8. Caveat'lar
- **Agent Teams DENEYSEL** (Claude Code): Windows'ta `--teammate-mode in-process`; `/resume` yok; tek takım/lider sabit/nested yok. Production-kritik akışı buna bağlamadan sürüm doğrula (`claude --version`).
- Hazır framework'e geçilmedi (LangGraph/CrewAI/AutoGen vb.) — desenler ödünç alındı; native Agent Teams + tool-allowlist yeterli.

## 9. Hazır kaynaklar (sıfırdan keşfetme — adoption adayları)
- Native: Claude Code **Agent Teams** + **subagents** docs; Anthropic "Multi-Agent Coordination Patterns" (5 desen).
- İskelet kopyalama: `wshobson/agents`, `VoltAgent/awesome-claude-code-subagents` (Meta & Orchestration) — orchestrator/reviewer/researcher tanımları (SAP'ye uyarla).
- `automazeio/ccpm` — spec-driven + worktree çakışma-önleme deseni.
- `ruvnet/ruflo` (claude-flow) — yalnız 10+ ajan/kalıcı bellek gerekirse (overkill).

## 10. Lider için ÖZET checklist (her takım kullanımında)
1. İş read-heavy/paralel mi? Değilse SOLO kal.
2. Takım açıyorsan ajanları **`.claude/agents/` tiplerinden** spawn et (general-purpose'tan değil) → tool-enforcement aktif.
3. Takım aktifken **kendin SAP'ye yazma** → adt_gateway'e devret (§3).
4. Ortak objeleri sırala; context'i tam ver; handoff'u yapılandır.
5. Gateway'i izle (§5): küçük batch, obje-başı rapor, sessizse output-dosyası oku.
6. İş bitince üyeleri kapat (boşta token yakma).

## 11. Kaynaklar
- Anthropic — Building Effective Agents; How we built our multi-agent research system; Multi-Agent Coordination Patterns
- Cognition — Don't Build Multi-Agents (2 ilke: full-trace paylaş; çelişen kararlar kötü sonuç)
- LangChain — How and when to build multi-agent systems (read vs write)
- Mechanical Sympathy — Single Writer Principle
- arXiv 2503.13657 — Why Do Multi-Agent LLM Systems Fail? (MAST)
- Claude Code docs — subagents / agent-teams
