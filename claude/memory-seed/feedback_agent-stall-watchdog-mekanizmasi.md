---
name: feedback_agent-stall-watchdog-mekanizmasi
description: "Background agent izleme: transcript CANLI değil, heartbeat/watchdog CANLILIK ölçer İLERLEME değil. ⚠ Yapısal olarak ENGELLENEN ajan sessiz kalır (yazacak yeri yoktur, charter yasağına uyar) — brifinge 'engellenirsen DERHAL bildir' maddesi + lidere ilerleme çapası şart. ⚠ VARYANT 3: ListAgents/TaskOutput adlandırılmış in-process ajanı GÖREMEZ (yanlış negatif) — canlılığın tek kanıtı SendMessage probe'udur."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e8c608cc-46db-459f-a9c4-65056297369a
---

Background/subagent'a (özellikle MCP-yazan gateway) iş verince, sağlığını **dıştan-gözlemlenebilir sinyalle + periyodik** izle — 20 dk körlük YASAK.

**Why:** GW v1 (2026-07-05) 20 dk sessiz takıldı; kök neden = `sap-adt` MCP stdio süreci activate anında öldü → gateway'in sıradaki MCP çağrısı **timeout'suz asıldı**. Kullanıcı: "iş verdiğin ajanları her 5 dk kontrol et; önleyemiyorsan zamanında haber veren mekanizma kur." MCP ölümü altyapı (client-timeout harness seviyesi, önlenemez) → çözüm = **zamanında tespit**.

**How to apply:**
- **Transcript'e GÜVENME:** agent `.output` dosyası CANLI değil — bitişte yazılır (çalışırken 0-byte kalır). "0-byte" ≠ takıldı. mtime/size agent sağlık sinyali DEĞİL.
- **Güvenilir sinyaller:** (1) agent'ın SAP/dosya üzerindeki **dış-gözlemlenebilir ilerlemesi** (curl ile SAP state fingerprint), (2) **heartbeat** (agent'a her iş-birimi sonrası `SendMessage({to:"main"})` zorunlu kıl), (3) MCP/SAP erişimi (curl discovery).
- **Mekanizma:** `scripts/agent_watchdog.sh <mode>` + **Monitor tool** (persistent). ~100s poll; her ~5dk **STATUS** (periyodik check-in), stall(~5dk ilerleme yok)/erişimsizde anında **ALERT**. Her stdout satırı harness'ı re-invoke eder (kesin çalışır — heartbeat/transcript'ten bağımsız). Gateway bitince `TaskStop`.
- **Stall aksiyonu:** agent kill → MCP `/mcp` reconnect (SAP/VPN sağlamsa yalnız stdio oturumu düşmüştür; `python scripts/sap_doctor.py` ile katman-katman doğrula) → kaldığın yerden resume (SAP state probe ile ne yapıldığını bul).
- **Belt-and-suspenders:** watchdog (dıştan) + zorunlu heartbeat (içeriden) = iki bağımsız kat.

## ⚠ VARYANT 2 (2026-08-19) — SESSİZLİK "TAKILDI" DEĞİL, **ENGELLENDİ** olabilir

**Vaka.** `#141`'in merge çatışmasını çözmesi için `isolation: "worktree"` ile infra ajanı açıldı.
**26 dakika boyunca ölçülebilir çıktı SIFIR:** uzak dal aynı sha · yeni CI koşumu yok · canlı ağaç
temiz · hiçbir dosya değişmemiş. Watchdog **"heartbeat 17s taze"** diyordu — yani **canlıydı**.

**Kök sebep LİDERDEYDİ (brifing hatası):** `isolation: "worktree"` **içinde bulunulan projenin**
(<PROJE>) worktree'sini açar; ama iş **başka bir repodaydı** (DEV_CORE). Ajanın charter'ı canlı
`core/` ağacına yazmayı **yasaklıyor** (doğru olarak) ⇒ ajanın **yazacak hiçbir yeri yoktu**.
Yasağa uydu, bekledi, **haber vermedi**. Lider bir DEV_CORE worktree'si açıp adresini yollayınca
**~8 dakikada** işi bitirdi (çatışma çözümü + push + CI yeşil).

**İki ayrı ders:**
1. **Heartbeat CANLILIK ölçer, İLERLEME ölçmez.** "Alive" ile "ilerliyor" farklı sorulardır; watchdog
   birincisini yanıtlıyordu ve **yeşil** diyordu. ⇒ İzleme sinyali **dış-gözlemlenebilir ilerleme**
   olmalı: uzak dal sha'sı · yeni commit · CI koşumu · değişen dosya. Bunlar sabitse **ilerleme yok**,
   heartbeat ne derse desin.
2. **Çok-repolu işte `isolation: "worktree"` YETMEZ.** Görev başka bir repodaysa ajanın yazacak yerini
   **lider açar** ve adresini brifinge yazar. ⚠ Aynı dal canlı ağaçta checkout ise git ikinci
   worktree'ye izin vermez ⇒ **yeni yerel dal** aç (`git worktree add -b wip/... <dizin> origin/<dal>`),
   ajan `git push origin HEAD:<PR-dalı>` ile PR'ın başını günceller.

### ⛔ GENELLEME (aynı gün ÜÇ kez) — brifing, ajanın ARAÇ YÜZEYİNE karşı denetlenmemişti

Yukarıdaki vaka tekil değildi; aynı gün **üç** ayrı ajan, brifingin istediği şeyi **fiziksel olarak
yapamadı** ve üçünde de kusur **brifingdeydi**:

| # | Ajan | Brifing ne istedi | Ajanın gerçeği |
|---|---|---|---|
| 1 | `bug-expert` ×2 | *"raporu `.tmp/…md`'ye yaz"* | Rolün **`Write` aracı YOK** (tanım gereği salt-okur) |
| 2 | `infra-expert` | `isolation: "worktree"` ile başka bir reponun işi | Worktree **içinde bulunulan projenin**; hedef repo başka ⇒ yazacak yer yok |
| 3 | `infra-expert` | *"her kalem sonunda `SendMessage to main`"* | Rolün **`SendMessage` aracı YOK** ⇒ heartbeat **imkânsız** |

⭐ **Üçü de doğru davrandı** — ikisi engeli bildirip işi başka yoldan teslim etti, biri kendi
worktree'sini açtı. Yani ajanlar değil, **görev tanımı** hatalıydı.

**Kural:** Bir brifingde bir ajandan **X yapmasını** istiyorsan, önce **X'in araç listesinde
olduğunu ÖLÇ** (`.claude/agents/*.md` `tools:` satırı — Agent aracının rol açıklaması da listeler).
Özellikle: `Write` (salt-okur roller yoktur), `SendMessage` (heartbeat/rapor isteyeceksen),
ve **çok-repolu işte worktree'yi lider açar** (bkz. VARYANT 2). Bu, [[feedback_yeni-mcp-tool-agent-allowlist-guncelle]]
kaydının kardeşi: orada *"yeni tool otomatik allowlist'e girmez"*, burada *"brifing otomatik
araç yüzeyine uymaz"*.

**Uygula:**
- **Her brifinge madde koy:** *"Yazacak yerin yoksa / bir yasakla çakışıyorsan **TAHMİN ETME, DERHAL
  `SendMessage to main` ile bildir** — engeli lider açar."* Sessiz bekleme **başarısızlıktır**.
- **Lider tarafı:** yalnız "bitince haber verilir"e güvenme — bu **stall'ı kapsamaz**. Dispatch ederken
  bir **ilerleme çapası** belirle (ör. *"ilk 10 dk içinde uzak dalda commit"*) ve o çapayı **ölç**.
- **Ölçerken doğru şeye bak:** `.output` dosyası 0-byte olabilir (bitişte yazılır) — sağlık sinyali
  **değildir**. Repo/CI tarafındaki iz **kanıttır**.
- Takıldığından şüphelenince **önce SOR** ([[feedback_sendmessage-gorevi-sessizce-islenmemis-olabilir]]);
  ama soruya *"engel neydi"* diye değil, **"hangi aşamadasın + neye takıldın"** diye sor — bu vakada
  cevap engeli anında ortaya çıkardı.

İlişkili: [[project_zsd001-batch-dummy-removal]] [[feedback_lider-bloke-olmama-background-dispatch]] [[feedback_arac-basarisizligini-zararsiz-sayma]] [[feedback_resolved-tooling-bugs]] [[feedback_hook-bakim-protokolu-t11]]

## ⚠ VARYANT 3 (2026-08-21) — **ARACIN GÖREMEMESİ ≠ AJANIN ÖLMESİ** (yanlış negatif)

**Vaka.** `A-13` build ajanı (`backend-expert`, adlandırılmış in-process subagent) spawn edildi.
Birkaç dakika sonra iki bağımsız araç da onu **bulamadı**:
`ListAgents` → *"No reachable agents"* · `TaskOutput(task_id="be-a13-motor")` → *"No task found"*.
Çalışma ağacı da temizdi (ajan henüz dosya yazmamıştı) ⇒ üç sinyal birden *"ajan öldü"* diyordu.

**Gerçek:** ajan **canlıydı ve çalışıyordu.** `SendMessage({to:"be-a13-motor"})` probe'una saniyeler
içinde ayrıntılı heartbeat döndü (TS-04'ün 1529 satırını okumuş, SNF↔sınıf eşlemesini ölçmüştü).

**Kök sebep — araç KAPSAMI:** `ListAgents` ve `TaskOutput`, **adlandırılmış in-process alt-ajanı
ad ile çözemiyor**. ⚠ `TaskStop` **çözebiliyor** (ad → iç ID; aynı oturumda iki kez çalıştı) ⇒
"bir araç adla buluyor" başka bir aracın da bulacağını **göstermez**.

**Neden tehlikeli:** "öldü" sonucuna varıp yeniden spawn etmek = **aynı build'in iki kopyası**
paralel koşar, aynı dosyalara yazar, token'ı ikiye katlar ve çakışan kaynak üretir. Sessiz değil,
ama fark edilmesi geç olur.

**How to apply:**
- **Canlılık ölçümünün TEK geçerli yolu `SendMessage` probe'udur** — ajanın kendi cevabı. Probe
  mesajına *"görevi değiştirmiyorum, baştan başlama, sadece durum bildir"* yaz; yoksa ajan
  brifingi yeniden yorumlayıp işi tekrarlayabilir.
- `ListAgents` boş dönüşü **kanıt değildir**; `TaskOutput` "no task found" da öyle. İkisi de
  yalnız **pozitif** yönde bilgi taşır (görürse vardır).
- Aynı aile: [[feedback_sendmessage-gorevi-sessizce-islenmemis-olabilir]] (artefakt yok ≠ iş
  yapılmadı) · [[feedback_dogrulama-sezgileri-dort-kural]] (bulunamadı ≠ sonuç) ·
  [[feedback_yesil-sinyalin-kapsamini-sor]] — bu, o kuralın **ters yönüdür**: kırmızı sinyalin
  de kapsamı sorulur. *"Bulamadım" diyen aracın neyi arayabildiğini bil.*
