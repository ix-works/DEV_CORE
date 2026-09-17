---
name: feedback_exit0-degil-cikti-kaniti
description: "exit 0 / OK / 'yenilendi' isin yapildiginin kaniti degildir — kanit CIKTInin kendisidir (dosya hash'i, icerigi, gorunuru)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d383af41-032c-4b3e-9882-e6ca57bdef9d
---

**`exit 0` işin yapıldığının kanıtı DEĞİLDİR. Kanıt ÇIKTIDIR** — dosyanın hash'i, içeriği,
ve gerekiyorsa **gösterdiği şey**.

**Why:** Bir araç "başardım" derken yalnızca *kendi adımının hata fırlatmadığını* söyler; ürettiğini
iddia ettiği şeyi üretip üretmediğini söylemez. 2026-08-10'da **tek turda üç ayrı araç katmanında**
aynı sınıf çıktı:

| Araç | "OK" dedi | Gerçek |
|---|---|---|
| `build_*_pdf_*.py` | 18/18 `OK` | `.html` 18/18 ama **`.pdf` 8/18**; bir dosyanın PDF'i **bir aydır** bayattı |
| `shot()` (playwright capture) | exit 0 | hatayı `catch`'te yutup diziye `FAIL` yazıyor; 3 görsel çekilmemiş hâlde "yenilendi" raporlandı |
| `fiori run --open false` | sessizce koştu | auto-open'ı kapatmadı, `"false"`'u URL yoluna yapıştırıp **gerçek Chrome** açtı |

**How to apply:**
1. **Ölçütü çıktıya bağla.** "Script koştu" değil → `git hash-object <dosya>` ≠ taban blob.
   Zaman damgası **yetmez** (dokunulmuş ama içerik aynı olabilir).
2. **Ölçüt üç kademede incelir** — hangisinin gerektiğini işin doğası söyler:
   *dosya değişti mi* → *doğru mu değişti* → **doğru şeyi mi gösteriyor**.
   Vaka: picker ekran görüntüsünün hash'i değişti (veri farklıydı) ama tablo kaydırılmadığı için
   yeni kolonlar **çerçeve dışındaydı** — hash "değişti" diyordu, resim yanlıştı. Görsel çıktıda
   son kademe **gözle bakmaktır**; sayısal vekili yoktur.
3. **"AYNI" iki anlama gelir** ve hash bunları ayırt etmez: (a) üretildi, sonuç özdeş (b) **üretilmedi**.
   Ayırmak için aracın kendi log'unu (ör. `shots[]` FAIL listesi) okut.
4. **Kendi doğrulama script'in de bu kurala tabi.** Aynı gün liderin tek satırlık kontrolü, `grep`
   hata verdiği hâlde ekrana *"(bos = temiz)"* yazdı — sahte-temiz. Çıkış kodunu kontrol etmeyen
   bir kontrol, hatayı temizlik sanar.
5. **Ajan raporu iddiadır.** "5/5 yenilendi" dendiğinde ölç: 4 app'te sayı tutmadı.

İlgili: [[feedback_arac-basarisizligini-zararsiz-sayma]] · [[feedback_push-ok-mesaji-sahte-readback-esitligi]]
· [[feedback_dogrulama-sezgileri-dort-kural]] · [[feedback_sonucu-olc-uygulamayi-degil]]
⇒ **CORE'A TERFİ ADAYI** (metodoloji; `playbook/lessons-learned.md` PATTERN olarak).

### 🔇 SESSİZ İZLEYİCİ — çıktının YOKLUĞU da kanıt değildir (2026-08-21)

`exit 0` iki anlamlıysa, **hiç çıktı olmaması** üç anlamlıdır: *"olay yok"* · *"filtre tutmadı"* ·
*"üretici zaten hiç çalışamıyordu"*. Bir izleyici (monitor / watcher / poll döngüsü) kurarken
**susmasının bilgi taşıdığını varsayma** — susma, ancak *"ateşleyebildiğini"* kanıtladıysan bilgidir.

**Ölçülmüş vaka:** CI'ı izlemek için kurulan poll döngüsü, durumu `jq` ile süzüyordu. **Bu makinede
`jq` KURULU DEĞİL** (`command -v jq` → boş; `comm` var). Döngüdeki `2>/dev/null` ve `|| echo '[]'`
fallback'leri *"command not found"*u **yuttu** ⇒ süzülmüş küme daima boş ⇒ ne olay basıldı ne de
çıkış koşulu gerçekleşti; izleyici 900 sn timeout'a kadar **yapısal olarak hiç konuşamadan** koştu.
CI çoktan yeşildi; sonuç ancak **elle bakınca** görüldü.

**⇒ Somut kural:** `gh` çıktısını süzerken **sistem `jq`'suna borulama** — `gh`'nin **kendi**
`--jq` bayrağını kullan (`gh pr view … --jq '.state'`); o gömülüdür, ayrı kuruluma bağlı değildir.

**How to apply:**
1. İzleyiciyi kurmadan önce **iç komutu bir kez elle koş** ve **satır ürettiğini gör**.
2. Bağımlılığı ölç: `command -v <araç>` — yoksa dallan, sessizce boş küme üretme.
3. ⛔ Hata yutan sus-pus fallback'ler (`2>/dev/null`, `|| echo '[]'`) izleyicinin **kör noktasıdır**;
   hatayı yutacaksan **görünür bir "KOŞAMADI" satırı** bas (bu evin fail-loud sözleşmesi).
4. Uzun sessizlikte *"demek ki henüz bitmedi"* deme → **bir kez elle ölç**.

⭐ Bu, *"kontrol koştu ≠ kontrol baktı"* ailesinin izleyici hâlidir; aynı gün üç kardeşi ölçüldü
(`brifing-lint` §2/§6'yı hiç ölçmüyordu · memory-nudge %100 ateşleyip hedefi 0/7 kaçırdı ·
`intake_triage` metodoloji kelimelerini modül kancası sandı).
