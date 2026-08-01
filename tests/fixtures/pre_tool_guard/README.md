# pre_tool_guard — payload fixture korpusu (kalıcı; koşucu: `tests/run_guard_fixture_tests.py`)

**Neden var (2026-08-01 adversarial bug-avı):** `pre_tool_guard`'ın kabuk-sözdizimi
modeli eksikti ve üç atlatma canlı repro edildi:

| # | Atlatma | Kontrol vakası | Kök |
|---|---|---|---|
| AV-16 | `git commit -am '<iz>'` → exit 0 | `-m` → exit 2 | `_GIT_M` lookbehind'i **kümelenmiş** kısa bayrağın içindeki `m`'yi reddediyordu → mesaj hiç çıkarılmadı |
| AV-17 | `git commit --file=<f>` → exit 0 | `-F <f>` → exit 2 | `--file` uzun biçimi hiç tanınmıyordu |
| AV-18 | `gh repo view --repo O/R && gh pr create -t t -b b` → exit 0 | hedefsiz tek komut → exit 2 | hedef-açıklık komutun TAMAMINDA aranıyordu; zincirdeki başka (salt-okuma) hedef sonraki mutasyonu serbest bırakıyordu |
| AV-18b | `gh pr view --repo <PRIVATE> && gh pr create --repo <PUBLIC> -b '<iz>'` → blok=False | tek komut PUBLIC → blok=True | görünürlük komutun TAMAMINDAKİ **ilk** `--repo`dan çözülüyordu (canlı iki repoyla ölçüldü) |
| AV-21 | core'un `git worktree`'sine sızıntılı yazma → exit 0 | `DEV_CORE\...` → exit 2 | core kimliği YOL-DİZGESİNDEN (`/core/`, `dev_core`) okunuyordu; worktree/klon adı tutmayınca kural sessizce kapalıydı |
| AV-21c | **ters yön (FP)**: `--project ../template_project` + göreli hedef → proje dosyası "core" sanıldı (CI PR #75 kırmızısı) | mutlak yollu koşum → temiz | göreli yolun `parents`'ı `..`/`.` ile biter; `.` = ÇALIŞMA DİZİNİ = core checkout'u |
| AV-21d | **FP**: core ağacının içindeki komşu depoya yazma bloklanıyordu | — | tırmanış hedefin kendi deposunun kökünde durmuyordu |

> **AV-21'in dersi çift yönlüdür:** işaret-tabanlı kimlik, "core ADINI kaybetse de tanı"
> problemini çözer ama "komşuyu core sanma" problemini AÇAR. Bu yüzden korpus iki yönü
> BİRLİKTE tutar: `blok.json`da worktree/ikiz pozitifleri, `serbest.json`da komşu-repo ve
> göreli-yol negatifleri. Biri düzeltilirken diğeri kırılırsa korpus kırmızı yanar.

Bu korpus o üç vakanın **yeniden-koşulabilir** hâlidir + her birinin varyantları +
**yanlış-pozitif** ekseni. Sıkılaştırmanın FP maliyeti vardır: FP meşru commit'i bloklar
ve "atlatma refleksi" doğurur (yaşanmış sınıf, 2026-07-30 POSIX-cd vakası) → `serbest.json`
`blok.json` kadar bağlayıcıdır, silinemez.

## Dosyalar
- `blok.json` — guard **exit 2** vermeli (+ `beklenen_imza` = o kuralın stderr imzası;
  "exit 2" tek başına yetmez, BAŞKA bir kural ateşlemiş olabilir — Z1 dersi).
- `serbest.json` — guard **exit 0** vermeli (yanlış-pozitif ekseni).
- `mesajlar/{temiz,kirli}.txt` — `-F` / `--file` vakalarının gerçek mesaj dosyaları.
- `agac/` — AV-21 iskeleti: `cekirdek_ikizi/` (core işaretlerini taşır, adında "core"
  GEÇMEZ) + `sahte_proje/` + `cekirdek_ikizi/komsu_proje/` (core ağacının İÇİNDE duran
  ayrı depo — işaret-tabanlı kimliğin komşu-repo FP'si). **`DOTGIT` dosyaları koşum anında
  `.git`e dönüştürülür**: git bir depoya `.git` adlı yol ekleyemez, ama "hedefin kendi
  deposunun kökü" sınırını sınamak için gerçek bir `.git` girdisi şarttır.
  Koşucu bu ağacı **geçici dizine kopyalar**:
  CI'da repo yolu zaten `.../DEV_CORE/...` olduğu için yerinde kullanılsaydı her fixture
  "core" sayılır ve "core DEĞİL" ekseni kurulamazdı (sahte-yeşil). Kopya yolunda "core"
  geçerse koşucu **durur** (sessiz bulaşma kontrolü).

## Determinizm (ağsız)
Guard, sızıntı gate'lerinde repo görünürlüğünü CANLI sorar (`gh repo view`) ve gerçek
desen sözlüğüyle tarar. Fixture koşucusu ikisini de **sabitler**:
`gorunurluk: public|private|canli` ve `tarayici: sentinel|gercek`. Böylece korpus ağsız,
kimlik-izsiz ve her makinede aynı sonucu verir (core PUBLIC olduğu için gerçek bir
kimlik izi buraya YAZILAMAZ zaten — `<SENTINEL>` yapay işareti kullanılır).

## Yer tutucular
- `<SENTINEL>` → koşucunun yapay "sızıntı" işareti (tarayıcı `sentinel` modundayken bulgu üretir).
- `<FIXTURE>` → bu dizinin mutlak yolu (POSIX eğik çizgili).
