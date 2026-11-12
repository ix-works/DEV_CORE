---
name: feedback_agent-briefing-sendmessage-main
description: "Ajan araç yüzeyi ne `tools:` beyanından ne de ÖNCEKİ ÖLÇÜMDEN kesin çıkarılır (2026-10-18: adsız arka-plan kipinde beyan 8/8 isabet, ama 08-29 karşı-ölçümü duruyor → yedek madde şart) — SendMessage 2026-08-23 adlı spawn'da VARDI, 2026-08-29 adsız arka-plan infra-expert'te YOKTU (ikisi de ölçüldü); brif HER İKİ hâlde de çalışacak biçimde yazılır"
metadata: 
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: a54ee6d9-6b08-4223-9ec8-2806bf40444a
---

⛔ **`tools:` BEYANI, ÇALIŞMA ZAMANI ARAÇ YÜZEYİ DEĞİLDİR.**

> **Tohum notu (2026-11-12):** bu dersin ilk tohum hâli *"brifte `SendMessage({to:"main"})` ZORUNLU —
> yoksa rapor gelmez"* diyordu. O mekanizma iddiası sonradan **dört kez** yanlışlandı (aşağıda). Güncel
> kural: `SendMessage` iste, ama brif **kanal yoksa da** çalışacak yedek maddeyi aynı paragrafta taşısın.

**Ölçüm 2026-08-23 (kesin):** `.claude/agents/backend-expert.md` → `tools:` satırında `SendMessage`
**YOK** (dosya okundu, 24 araç sayıldı). Aynı ajan spawn edildi ve `SendMessage`'ı **başarıyla
çağırdı** — `{"success":true}`; iki ara raporu lider'e o kanaldan ulaştı.
⇒ Harness `SendMessage`'ı o kipte iletişim primitifi olarak **allowlist'ten bağımsız enjekte etti**.
⚠ Spawn ekranındaki rol listesi de `SendMessage`'ı göstermez — **o liste de beyandır, ölçüm değil.**

**Bu, 2026-08-22 ölçümünü çürütmez, YENİDEN YORUMLAR:** o gün 4 ajanın hiçbiri
`SendMessage` *kullanmamıştı* ve 4/4 rapor geldi. Bundan *"araç yok"* sonucu çıkarılmıştı —
**kullanmamak ≠ olmamak**. Doğru okuma: final rapor **her hâlükârda** ulaşır, ara heartbeat ise
**mümkündür**.

⛔⛔ **KARŞI-ÖLÇÜM 2026-08-29 — YUKARIDAKİ OLGU İDDİASI TEK BAŞINA GEÇERLİ DEĞİL.**

`infra-expert` **arka planda, AD VERİLMEDEN** spawn edildi. Ajan `SendMessage`'ı çağırdı, harness reddetti:
> `Error: No such tool available: SendMessage. SendMessage is disabled for this session, in subagents as well as here.`

⚠ Hata metninin kendisi **yanıltıcı**: *"disabled for this session"* diyor, oysa **lider aynı
oturumda `SendMessage`'ı başarıyla kullanıyordu** (ajanlara mesaj gitti, ajanlar aldı ve uyguladı).
⇒ **Yön asimetrik:** lider → ajan **çalışır**, ajan → lider **çalışmaz**. Hata metnine değil,
**hangi yönün ölçüldüğüne** bak.

**İki ölçüm çelişmiyor — kapsamları farklı.** 08-23: `backend-expert`, **adlı** spawn, çalıştı.
08-29: `infra-expert`, **adsız/arka-plan** spawn, çalışmadı. Aynı turda **adlı** üç
`general-purpose` ajanı ara rapor **gönderebildi**.
⇒ Belirleyici değişken tek başına `tools:` beyanı DEĞİL; **spawn kipi** (adlı-takım vs
adsız-arka-plan) ve rolün araç kısıtı. Hiçbiri **kalıcı olgu** değildir.

⭐ **Asıl ders — bu kayıt defalarca aynı yerden yanlışlandı:** her seferinde tek bir ölçüm
**kalıcı olgu** sanıldı. Doğru davranış: kanalın varlığını **tura özgü** kabul et ve brifi
**kanal yoksa da çalışacak** biçimde yaz.

⛔ **Operasyonel tuzak (2026-08-29'da gerçekleşti):** adsız arka-plan ajanının **giden kanalı
olmayabilir** ⇒ *"ara rapor ver"* talimatı o kipte **yapısal olarak uygulanamayabilir**. Lider bunu
bilmeden 7 ajana ara-rapor sözleşmesi dayattı; kullanıcının açık talebi karşılanamadı ve bu ancak
**ilk ajan bitince** görüldü.
**Panzehir:** brifte *"kanal yoksa ara raporları NİHAİ raporun başına `### AR-1` / `### AR-2`
başlıklarıyla, o anki hâliyle taşı"* maddesi **baştan** bulunsun.

**Doğru brifing cümlesi:**
> Ara heartbeat'i `SendMessage({to:"main"})` ile gönder (her ana adım sonunda 2-3 satır).
> Final mesajın zaten rapordur. Büyük ara-çıktıyı `.tmp/` altına yaz, mesajda yolunu ver.
> Araç yoksa ara raporları nihai raporun başına `### AR-n` başlıklarıyla taşı; DERHAL maddesinde DUR.

⛔ **ŞUNU YAZMA:** *"Araç listende `SendMessage` YOK — final raporun tek kanalın."*
Bu cümle **olguya aykırı olabilir** ve zararı tek yönlü: ajan buna uyup **sessiz koşar**, sen de
*"sessiz bekleme kusurdur"* maddesini brifin kendi hatalı öncülüyle ihlal ettirirsin.
Vaka (2026-08-23, bir build turu): ajan cümleyi **ölçerek çürüttü** ve uymadı; uysaydı tur boyunca
sessiz kalacaktı.

**Why:** Bu kayıt **iki kez** yanlış gerekçeyle yazıldı. ① İlk hâli *"SendMessage ZORUNLU"*
diyordu, mekanizma iddiası yanlıştı. ② İkinci hâli *"bu rollerde YOK"* diyordu — **beyanı ölçüm
sandı**. Her ikisinde de kayıt **doğru görünürken zarar verdi**. Asıl kural beyanın yönünden
bağımsızdır: **yetenek iddiası davranışla doğrulanır, tanım dosyasıyla değil.**

**How to apply:** Bir ajandan bir eylem isteyeceksen ve emin değilsen: **"aracın yok" DEME** —
*"varsa şunu yap; yoksa eşdeğerini yap ve bana bildir"* de. Olumsuz yetenek iddiası, olumlu iddia
kadar kanıt ister (*bulunamadı ≠ yok*). Ajan bir yetenek iddianı çürütürse **devral, savunma**.
İlişkili: [[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] · [[feedback_ajan-olumsuz-donusu-kanitla-sorgula]] ·
[[feedback_yesil-sinyalin-kapsamini-sor]] · [[feedback_agent-stall-watchdog-mekanizmasi]]
(heartbeat **canlılık** ölçer, **ilerleme** değil) · [[feedback_lider-ajan-paralel-yazim-cakismasi]]

⛔ **2026-09-13 — AYNI TUZAĞA DÖRDÜNCÜ KEZ DÜŞÜLDÜ (lider).** `adt-gateway` **adsız arka-plan**
spawn'ında `SendMessage` yoktu (ajan beyanı: *"bu ortamda `SendMessage` aracı yok"*). AR-1'i nihai
mesajla gönderip DURDU; lider `SendMessage(to: agentId)` ile yeniden uyandırdı, tur ikiye bölündü.
Buna rağmen lider ① gateway brifine kanal-yoksa yedeğini **koymamıştı** ② ölçümü proje kuyruğuna
yazarken belirleyiciyi yine **`tools:` satırı** sandı ve düzeltme yönü olarak "`tools:`'a
`SendMessage` ekle" yazdı. Bu kayıt tam bunun yanlış olduğunu söylüyordu (`infra-expert.md`'nin
`tools:` satırında `SendMessage` VAR, 08-29'da yine de yoktu). Aynı gün üç infra-expert brifi de
yedeksiz gitti; spawn sonrası ek mesajla düzeltildi.
⚠ **Aynı gün karşı-veri:** adsız arka-plan `infra-expert` `SendMessage`'ı **başarıyla**
kullandı (ara soru lidere ulaştı) — 08-29'da aynı rol/kip YOKTU. ⇒ Aynı kip + aynı günde rol
başına farklı sonuç (gateway yok · infra-expert var). Kalıcı kural çıkarılamaz; yedek şart.
⇒ **Brif şablonu kuralı:** `SendMessage` isteyen HER brif, aynı paragrafta *"çağır; yoksa HB/AR'leri
nihai raporun başına taşı, DERHAL maddesinde DUR"* yedeğini taşır. Tanım dosyası okunarak
"var/yok" hükmü verilmez.

⭐ **2026-10-18 — adsız arka-plan kipinde beyan sonucu belirledi (tek oturum, aynı gün).**
| Rol | `tools:`'ta SendMessage | Sonuç |
|---|---|---|
| infra-expert (×5, ayrı turlar) | var | gönderdi (AR-1…3 dahil) |
| bug-expert (1. doküman kapısı) | yok | gönderemedi ("aracım yok") |
| frontend-expert (KD turu, DEV_CORE #342'den önce spawn) | yok | gönderemedi |
| bug-expert (2. kapı, DEV_CORE #342 + team_setup sonrası) | **var** | **gönderdi** (AR-1, AR-2) |
⇒ Bu kipte beyan o gün belirleyiciydi ve 6 role `SendMessage` eklendi (DEV_CORE #342). ⚠ Bu, 08-29'daki
karşı-ölçümü (beyanlı infra-expert → `No such tool available`) silmez ⇒ **yedek madde brifte KALIR**.
Ek tuzak: proje-lokal override (`claude-local/agents/<rol>.md`) çekirdek tanımını gölgeler — #342 sonrası
bir projenin backend-expert kopyasında SendMessage yoktu, çünkü dalda eski override duruyordu (`team_setup` "1 proje-lokal override").

Son-doğrulama: **2026-10-18** (adsız arka-plan: beyanlı 6/6 gönderdi · beyansız 2/2 gönderemedi). Önceki: **2026-09-13** (`adt-gateway` adsız arka-plan spawn'ı → kanal yok; lider→ajan yönü yeniden uyandırma olarak çalıştı). Önceki: 2026-08-29 (`infra-expert` adsız arka-plan → `No such tool available`) · 2026-08-23 (`backend-expert`, adlı spawn, `success:true`).
Applies-to: TÜM projeler · her alt-ajan brifingi
