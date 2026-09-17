---
name: feedback_yerel-suit-ci-ikizi-degil
description: "Yerel test süiti CI'ın ikizi değil — aynı commit, Windows'ta yeşil, Linux CI'da kırmızı olabilir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 08f4a439-ebf4-425b-9d0a-f815401919b3
---

**Yerel süit ile CI aynı kod olsa da aynı ORTAM değildir.** "Yerel yeşil ⇒ CI yeşil" bir çıkarım değil, bir **varsayımdır** — ve ölçülmeden kullanılırsa geç ve pahalı patlar.

**Vaka (2026-08-20, `DEV_CORE#150`), aynı commit:**

| Ortam | Sonuç |
|---|---|
| Windows, **10+ ardışık koşum** | `145/145`, mutasyon `[YAKALANDI]` |
| `ubuntu-latest` (CI), tek koşum | **`144/145`**, aynı mutasyon **`[KACTI]`** |

Kaçan şey bir *üretim* bug'ı değildi: **korpusun kendisi** platforma bağlıydı. Bash yol-çıkarımını test eden FP çapası, Linux'ta mutasyonu ayırt edemiyordu.

⭐ **Asıl ders:** infra-expert charter'ı `F3`te zaten **üç bağlam** ister ve üçüncüsünü *"başka paket / proje-şekli / **kabuk**"* diye tanımlar. Korpus dokuz senaryosunu yalnız Windows'ta doğrulamıştı ⇒ kusur üretim kodunda değil, **kanıtın kapsamındaydı**. Kural vardı, uygulanmadı.

**Nasıl uygula:**
- Kabuk/yol/dosya-sistemi davranışına dokunan bir korpusun **3. bağlamı OS olmalı** — "başka bir dizin" yetmez.
- ⛔ Bir düzeltmenin kapatma kanıtı olarak **yerel yeşili sunma**; bu sınıfta kanıt **CI koşumudur**.
- ⭐ PR'ı açıp **CI'ı hakem yapmak** ucuz ve dürüst bir ölçümdür — merge'i CI'a bağla, "bende çalışıyor"a değil. Bu vakada tam olarak öyle yakalandı.

İlgili: [[feedback_dogrulama-sezgileri-dort-kural]] · [[feedback_yesil-sinyalin-kapsamini-sor]] · [[feedback_debugger-farki-aslinda-kullanici-farki]] (aynı aile: ortam farkı sanılan şey)

## ⛔ SÜİTİ NE ZAMAN KOŞARSIN — KRİTER, RİTÜEL DEĞİL (2026-09-04, kullanıcı uyarısı)

Kullanıcı: *"gerekmiyorsa neden çalıştırıyon, neye göre çalıştırıyon, bu tarz gereksiz
çalıştırmalar bize zaman kaybettiriyor."* Vaka: gün sonunda tam süit başlatıldı; o günün iki
değişikliği **`infra-expert.md` frontmatter'ında bir satır** ve **bir üreteç docstring'i**ydi.
Süit 7+ dk koştu ve kullanıcı tarafından durduruldu. **Sebep bir kriter değil, "gün sonu"
kelimesinin tetiklediği ezber kontrol listesiydi.** Bu kaydın kendi maddesi (*"CI'ı hakem yap"*)
zaten bunu yasaklıyordu — kural vardı, uygulanmadı (aynı desen: `Q264`).

**KOŞ** — değişiklik süitin ölçtüğü **çalıştırılabilir kodu** değiştirdiyse:
`scripts/**.py` · hook'lar · validator'lar · `core/` Python · test korpusunun kendisi.

⛔ **KOŞMA** — değişiklik yalnız şunlarsa: markdown/doküman · `governance/**` kuyruk kayıtları ·
`claude/agents/*.md` ajan tanımları · yorum/docstring · PR/commit metni.
Bu sınıfta süit **sıfır ek bilgi** üretir; kapı zaten **CI**'dır (`gates` / `guard / *`).

**Karar yöntemi (10 saniye, ezber değil):** `git diff --stat` çıktısına bak — *"dokunulan dosyalar
süitin kapsamında mı?"* Sorunun cevabı hayırsa **koşma**. "Gün sonu mu?" sorusu bu kararın
girdisi **değildir**. Emin değilsen süiti değil, **hedefli tek fixture'ı** koş.

📌 Aynı aile: [[feedback_infra-turunun-maliyeti-testte-degil-kanit-uretiminde]] (maliyet test
koşumunda değil gereksiz kanıt üretiminde) · [[feedback_sonucu-olc-uygulamayi-degil]].
