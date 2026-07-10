# ADR 0023 — Hook kablolaması plugin'e TAŞINMAZ (fail-closed-on-absence ifade edilemez)

**Durum:** REDDEDİLDİ (2026-07-10) — değerlendirildi, kanıtlandı, kapatıldı.
**Bağlam tetikleyici:** Senkronizasyon protokolü, "çoğaltmayı kaldır" adımı. `.claude/settings.json`
her projeye kopyalanan son davranış artefaktı; onu core'a taşımanın **tek** teknik yolu araştırıldı.

## Sorun

`.claude/settings.json` içindeki 16 hook'un **kablolaması** her projeye kopyalanır. Kopya drift
üretir: K1 (2026-07-09/10) — `sap_worktype_hint` ve `itg_backstop` bir projeye ve `template_project`'e
elle eklendi, `claude/settings.template.json`'a **hiç** eklenmedi ve hiçbir şey uyarmadı.

Junction'lı katmanlar (`core/`, `.claude/{agents,skills,commands,rules}`) bu sorundan muaf.
Hook kablolaması değil. `.claude/hooks/` diye bir yükleyici **yoktur** (2.1.206 binary'sinde o yol
yalnız sandbox'ın korunan-config listesinde ve bir prompt metninde geçer). Geriye tek aday kalır:
Claude Code **plugin**'i.

## Kanıt — plugin gerçekten yapabilir mi (evet)

`<plugin>/hooks/hooks.json` settings ile **aynı şemayı** kullanır. Binary'den:

```js
WTn = object({
  description: string().optional(),
  hooks: lazy(() => wQ()).describe("The hooks provided by the plugin, in the same format as the one used for settings")
})
```

`wQ()` = settings'in hook şeması. Aynı 30 olay adı, aynı `matcher` regex'i. Tüm kaynaklardan gelen
hook'lar tek kümede birleşir (`allHooks`) ve her sonuç `hookSource` taşır. Kaynaklar:
`userSettings · projectSettings · localSettings · policySettings · plugin`.

Yani **teknik olarak mümkündür.** Reddin sebebi yetenek eksikliği değildir.

## Karar — REDDEDİLDİ

Hook kablolaması `.claude/settings.json`'da, proje reposunda, commit'li kalır.

### Asıl gerekçe: bir plugin, YOKLUĞUNDA fail-closed davranmayı ifade edemez

`scripts/hook_shim.py` proje reposunda commit'li ~82 satırlık bir bekçidir. Tek işi: `core/`
bulunamazsa **bağırmak ve bloklayıcı hook'larda `exit 2` dönmek** — koruma yokken araç çalışmaz
(D15; 2026-07-09'da `return 1` → `return 2` düzeltmesi tam bu yüzden yapıldı).

Bir plugin bunu yapısal olarak sağlayamaz: **plugin yüklenmezse hook'ları kaydedilmez.**
"Guard eksik ⇒ aracı reddet" diyecek olan şey, zaten eksik olan guard'ın kendisidir. Yokluğu
haber verecek hiçbir şey geriye kalmaz.

Aynı ilke `scripts/git-hooks/pre-commit` için de geçerlidir: `core.hooksPath` var olmayan bir
dizini gösterirse git hook'ları **sessizce atlar** (fail-open). Bugünkü kopya, core'u bulamayınca
`set -e` ile commit'i durdurur (fail-closed). Bu yüzden o da taşınmadı.

> **Genel kural:** Çoğaltmayı kaldırırken **fail-closed → fail-open** takası yapılmaz.
> Bir kopyanın *gürültülü* bayatlaması, bir korumanın *sessizce* yok olmasından iyidir.
> (Aynı gerekçeyle `.gitignore` → `core.excludesFile` de reddedildi: local git config
> commit'lenmez, klonlayanda sırlar korumasız kalırdı.)

### İkincil gerekçeler

1. **`.claude/settings.local.json` gitignore'ludur.** Bir geliştirici oraya
   `{"enabledPlugins": {"<core-plugin>": false}}` yazarsa core'un tüm hook'ları o makinede
   sessizce kapanır — repoda, CI'da, guard'da iz yok. Bugün settings.json'daki hook bloğunu
   silmek commit'lenir ve F1 davranış-yüzeyi kontrolü yakalar.
2. **Kurulum/güven kapısı.** Plugin marketplace'ten çekilir ve kullanıcı onayı ister. Taze klonda
   "enabled" yazar ama plugin kurulu değilse hook yoktur. Devre-dışı yolu yalnız debug log yazar
   (`"will NOT register, plugin is disabled"`). *(`hook-load-failed` tanı tipinin kullanıcıya
   görünür uyarıya dönüşüp dönüşmediği DOĞRULANMADI.)*
3. **Bayat-ref tuzağı.** Plugin bir git ref'inden gelir; `stable`-tipi elle taşınan ref bayatlar
   (2026-07-10'da main'in 49 commit gerisindeydi). Aynı tuzak hook katmanına taşınırdı.

### Kazanç zaten küçüktü

Gate mimarisinin üç bileşeni var:

| Bileşen | Bugünkü taşıyıcı | Plugin ne değiştirirdi |
|---|---|---|
| Validator'lar (kod) | `core/` junction — kopya YOK | hiçbir şey |
| CI | reusable workflow (ADR yok; core `.github/workflows/project-guard.yml`) | hiçbir şey |
| Hook **kablolaması** | `.claude/settings.json` (kopya) | yalnız bunu taşırdı |

Yani tek bir dosyadaki kablolama için fail-closed özelliği feda edilirdi. Üstelik K1'in tekrarını
`C-TPL-01` (`check_settings_template_sync.py`) zaten engelliyor.

## Bu karar hangi koşulda YENİDEN AÇILIR

Tek bir koşul: **`policySettings` (managed policy) devreye girerse.** Kurumsal politika dosyası
plugin'i zorla etkin tutabilir ve proje/local ayarlar bunu ezemez (`SN()` yalnız
`policySettings.enabledPlugins` okur). O zaman "sessizce kapanır" itirazı düşer — kapatma yetkisi
kalmaz. Managed-policy kurulmadan bu ADR yeniden açılmaz.

Yeniden açılırsa ilk doğrulanacak şey: kurulu-olmayan/güvenilmeyen plugin durumunda kullanıcı
**görünür** bir uyarı alıyor mu (yukarıdaki 2. maddedeki doğrulanmamış nokta).

## Sonuç

- `.claude/settings.json` hook bloğu **class (b)** olarak kalır: şablondan üretilir, tazeliğini
  `C-TPL-01` + `session_start` D7 drift kontrolü denetler.
- `scripts/hook_shim.py` ve `scripts/git-hooks/pre-commit` **bilinçli kopya-artefaktlarıdır**;
  "drift" diye silinmeye çalışılmamalıdır. İkisi de fail-closed bekçidir.
- Çoğaltma kaldırma sırasında **her aday için sorulacak soru:** *bu artefakt yokken sistem
  bağırır mı, yoksa sessizce korumasız mı kalır?* Sessizse, kopya kalır.

## Alternatifler (reddedildi)

- **`.claude/hooks/` dizinini core'a symlink'lemek** — böyle bir yükleyici YOK (binary'de
  doğrulandı: yol yalnız korunan-config listesinde geçer).
- **`core.hooksPath` → `core/claude/git-hooks`** — junction kopunca git hook'ları sessizce atlar.
- **`core.excludesFile` → core'daki ignore dosyası** — local git config commit'lenmez; klonlayanda
  sırlar korumasız kalır (fail-open).
