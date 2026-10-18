---
applies_to: [all]
---

# HOWTO — Çekirdek güncellemesi (`core güncelle` / `/core-guncelle`)

> **Ne zaman:** kullanıcı *"core güncelle"* dediğinde · yeni bir çekirdek turu merge edildiğinde ·
> `session_start` *"origin'in gerisindesin"* uyarısı verdiğinde · yeni bir makinede kurulum
> tazelenirken. **Kim:** o makinede çalışan Claude, kullanıcı gözetiminde.
>
> **İlk kurulum değil, GÜNCELLEME prosedürüdür.** İlk kez kurulan bir makine için
> [`../ONBOARDING.md`](../ONBOARDING.md) ve `/onboard` komutu geçerlidir; bu dosya onun
> **güncelleme** yoludur ve aynı `team_setup` zincirini kullanır.
>
> ⭐ **Tek giriş noktası `/core-guncelle`'dir ve ek talimat gerektirmez** — bu dosyanın tamamını
> (bu makinedeki diğer projeler dahil, §3e) sonuna kadar yürütür. ⭐ **Adım 2'deki `pull`'dan
> SONRA bu dosyayı YENİDEN OKU:** pull prosedürün kendisini de güncelleyebilir; kalan adımları
> eski kopyadan yürütme.

## 0. Sınırlar

- ⛔ Yalnız buradaki adımlar koşulur. Yol üstünde başka bir kusur görürsen **düzeltme** —
  not al, sonunda raporla (kapsam-dışı bulgu protokolü).
- ⛔ Bu tur **SAP'ye hiçbir şey yazmaz**.
- ⛔ `--force` yok: `git push --force` · `init_project --force` · `seed_memory --force`
  bu prosedürün parçası değildir.
- ⛔ Junction'a özyinelemeli silme YOK (`rm -rf` bir junction'a girerse **hedefi** siler).
- ✅ Her adımın doğrulaması var. Doğrulama beklenen çıktıyı vermiyorsa **DUR**, çıktıyı
  kullanıcıya olduğu gibi göster, tahminle ilerleme.
- 📌 Komutlar **proje kökünden** çalışır; sabit sürücü/klasör yolu yazma (D24).

## 1. Başlangıç durumunu ölç

```bash
python core/scripts/parity_probe.py --out .tmp/parity-ONCE.json
git -C core status --short
git -C core branch --show-current
```

**Beklenen:** `status --short` boş, dal `main`.

**Kirliyse DUR** — çekirdekte yerel değişiklik var; `pull` onu çakıştırır ya da kaybeder.
Kullanıcıya sor: bilinçli bir yama mı?
- Bilinçliyse kendi dalına al (`git -C core checkout -b fix/<ad>`) ya da `git -C core stash`;
  sonra `main`'e dön ve **yamayı tur sonunda raporla** (upstream'e bildirilmesi gerekir —
  [`howto-cekirdek-bulgu-bildirimi.md`](howto-cekirdek-bulgu-bildirimi.md)).
- Değilse kullanıcı onayıyla geri al.

## 2. Çekirdeği güncelle

```bash
git -C core checkout main
git -C core pull
git -C core log --oneline -3
```

**Doğrulama:** yeni commit'ler görünüyor · `git -C core status --short` yine boş.

📌 Makinede **tek** fiziksel çekirdek vardır (ADR 0020): bu pull o makinedeki **tüm** projeleri
birden etkiler. Başka projede yarım iş varsa kullanıcıya söyle.

⛔ **Proje reposunu da AYNI TURDA çek** (proje kökünden):

```bash
git status --short                  # BOŞ olmalı
git branch --show-current           # main olmalı
git pull --ff-only
```

Ağaç kirliyse ya da dal `main` değilse **DUR**, kullanıcıya sor (orada yarım iş olabilir).
Neden: proje kök `CLAUDE.md`'sindeki yasak damgası ve projeye ait kurulum dosyaları çekirdekle
birlikte değişebilir. Yalnız çekirdek çekilirse damga kanonikle eşleşmez ve `pre_tool_guard`
SAP-yazma araçlarını **fail-closed bloklar** (vaka 2026-09-25: kanonik damga değişti, proje
repoları ayrı PR'larla güncellendi; çekirdeği tek başına çeken makinede `check_kesin_yasaklar`
FAIL verirdi). §3e'deki her proje için aynı üç komut o projenin kökünde koşulur.

## 3. Kurulumu tazele — `team_setup.py`

```bash
python core/scripts/team_setup.py
```

Betik şu zinciri koşar (ölçüldü, `team_setup.py` main akışı):
junction'lar + **overlay materyalizasyonu** (`.claude/rules/00-claude-core.md`, `agents`) →
`.claude/settings.json` + `scripts/hook_shim.py` + **`.claude/active_package`** →
git-hooksPath (core + proje) → **şablon sapması raporu** → **CORE-INDEX** yenileme → plugin
kurulumu + npm CLI'ler → **memory tohumu** (`seed_memory.py`, merge-safe) → smoke testleri.

- **Şablon sapması (2026-10-03):** `dosya_tamamla` var olan `settings.json` / `hook_shim.py` /
  `pre-commit`'i **ezmez**; sapmışsa `[WARN] <dosya> şablondan SAPMIŞ (… yalnız PROJEDE N ·
  yalnız ŞABLONDA M) — <komut>` basar (D7 imzası, exit kodu değişmez). `settings.json`'da
  yalnız proje eki varsa `[INFO] N proje eki` (meşru). WARN görürsen: hook_shim →
  `python core/scripts/team_setup.py --tazele-shim`, pre-commit → `--tazele-precommit`
  (ikisi de önce farkı ve yönü basar, yedek alır; **TERS YÖN** satırı varsa proje İLERİDEDİR —
  satırları okumadan onaylama). settings için otomatik tazeleme YOK: `git diff --no-index
  core/claude/settings.template.json .claude/settings.json` ile elle birleştir. Satırın
  sonundaki `şablon kıyası (…)` özeti neye BAKILMADIĞINI da yazar.
- **CORE-INDEX:** içerik ve damgadaki `core-commit` aynıysa dosya yeniden yazılmaz
  (`[ OK ] değişmedi`); core-commit değiştiyse yazılır. Güncelleme turunda core-commit **her
  zaman** değişir ⇒ dosya yazılır ve **proje PR'ıyla commit edilir — fark yalnız damga satırı
  olsa bile** (PATTERN #28 ⑤). Gerekçe: proje CI'ındaki `build_core_index --ci-check` tazeliği
  ancak damgadaki core-commit klonlanan `main` HEAD'ine eşitken ölçer, değilse C-IDX-01
  `SKIPPED` kalır. Commit edilmeyen damga ayrıca proje ağacını kirli bırakır: sonraki turda §2
  "kirli → DUR" ve `ix_doctor` "çalışma ağacı kirli" uyarısı bundan doğar (ölçüldü 2026-10-18:
  aynı makinede üç projede önceki turun indeksi commit'siz kalmıştı). İstisna: core `main`'de
  değilken üretilen indeks commit edilmez (PATTERN #28 ①–④).

### 3b. Overlay ezme kapısı (T2.5) — **koşullu**

Çekirdek turu `CLAUDE.core.md` · `claude/rules/*` · `claude/agents/*` dosyalarına dokunduysa ve
bu projedeki materyalize kopya farklıysa betik şunu basar ve **`return 1` ile çıkar**:

```
FARK VAR — onaysız ezme YOK (T2.5)
```

⚠ **Bu bir hata değil, kapıdır** — ama ÇIKIŞ noktası kritiktir: kapı ateşlerse **plugin
kurulumu ve memory tohumu HİÇ koşmaz**. *"team_setup çalıştı"* demek bu yüzden yeterli değildir;
çıktının sonunda `team_setup TAMAM` satırını gör.

Kapı ateşlerse: **fark raporunu OKU ve kullanıcıya göster** (bu makinede elle düzeltilmiş bir
dosya ezilecek mi?), sonra onayla:

```bash
python core/scripts/team_setup.py --overlay-onayli
```

⭐ **Kapı her güncellemede ateşlemez** (ölçüldü 2026-09-18: overlay kaynakları değişmeyen bir
turda hiç ateşlemedi, zincir tek koşumda tamamlandı). *"Nasılsa ateşler"* diye baştan
`--overlay-onayli` ile başlama — o bayrak fark raporunu görmeden ezme iznidir.

### 3c. MCP import smoke — `return 1`'in İKİNCİ sebebi (Q335, 2026-09-18)

Kurulumun sonunda team_setup, sap-adt MCP sunucusunu `.mcp.json` ortamıyla import etmeyi dener.
Import başarısızsa (ör. makinede `mcp 2.x` kurulu) şunu basar ve **`return 1` ile çıkar**
(`team_setup TAMAM` basılmaz):

```
[FAIL] MCP server import smoke BAŞARISIZ — exit 1: <son anlamlı hata satırı> · … Onarım: …
[FAIL] team_setup BAŞARISIZ (MCP server import smoke) — …
```

⛔ **Bu durumda `--overlay-onayli` ÇARE DEĞİLDİR** — overlay kapısıyla ilgisi yoktur. FAIL
satırındaki onarımı uygula (`<python> -m pip install -r core/mcp_servers/sap_adt/requirements.txt`;
requirements `mcp<2` sınırını taşır ve kurulu 2.x'i `--upgrade`'siz indirir), sonra team_setup'ı
yeniden koş. `ix_doctor --layer 5` aynı denetimi 5b2 satırında yapar. ⚠ Son satır
`No module named 'mcp_servers'` ise sorun paket değil YOLDUR — pip çare DEĞİLDİR: `.mcp.json`
sap-adt `env.PYTHONPATH` = `${CLAUDE_PROJECT_DIR:-.}/core` olmalı ve proje `core` bağı bulunmalı
(`team_setup --repair-junctions`); `.mcp.json` bozuksa (geçersiz JSON / `sap-adt` yok) denetim
ÖLÇÜLEMEDİ der ve çare dosyayı onarmaktır. FAIL satırındaki çare metni bu ayrımı kendisi yapar.

**Doğrulama:** çıktıda `FAIL` satırı yok · son satır `team_setup TAMAM` · `.claude/active_package` var.

### 3d. KESİN YASAKLAR damgası — **koşullu** (2026-09-25)

`team_setup` kök `CLAUDE.md`'deki yasak damgasını **yenilemez**. Kanonik
(`claude/kesin-yasaklar.canonical.md`) değişmişse damga sapar ve iki kapı ateşlenir:
`check_kesin_yasaklar` **FAIL** + `pre_tool_guard` SAP-yazma araçlarını **fail-closed BLOKLAR**.

```bash
python core/scripts/sync_yasaklar.py --check     # [EŞ] ise adım biter
python core/scripts/sync_yasaklar.py             # [SAPMA] ise damgala
```

Kök `CLAUDE.md` davranış yüzeyidir ⇒ değişiklik **PR ile** girer (doğrudan main'e değil).
Birden çok proje aynı makinedeyse komutu **her proje kökünde ayrı** koş (§3e).
⛔ `--root <üst klasör>` KULLANMA: tarama çekirdeğin test fixture'larını ve `.wt` kopyalarını da
"proje" sayar ve damgalama kipinde onlara YAZAR (ölçüldü 2026-10-18: üst klasörde `--check`
gerçek projelerin yanında 10+ fixture/worktree yolu listeledi).

### 3e. Aynı makinedeki DİĞER projeler — **zorunlu** (2026-10-18)

Makinede tek çekirdek vardır; pull hepsini etkiler. `session_start` her projede yalnız çekirdek
kural kopyasını (`00-claude-core.md`) kendiliğinden tazeler — `agents`/`settings`/`hook_shim`
sapması, memory tohumu (her projenin hafıza klasörü ayrıdır) ve yasak damgası **yalnız
`team_setup`'ın koştuğu projede** hizalanır. Bu çekirdeği kullanan projeleri bul (proje kökünden):

```bash
python -c "import pathlib;c=pathlib.Path('core').resolve();[print(p) for p in sorted(c.parent.iterdir()) if (p/'project.yaml').is_file() and (p/'core').exists() and (p/'core').resolve()==c]"
```

Ölçüt: çekirdeğin üst klasöründeki, `project.yaml` taşıyan ve `core` bağı **bu** çekirdeğe
çözülen klasörler. Başka yerde duran proje bu listeye girmez — varsa kullanıcı söyler.
⛔ **ONAY — tek soru, tek sefer:** listeyi kullanıcıya göster ve hangilerinde kurulum yapılacağını
SOR (çoklu seçim: hepsi / bazıları / hiçbiri; AskUserQuestion varsa onunla). Diğer projeler başka
müşterinin işi olabilir ya da o an başka bir oturumda açık olabilir; `team_setup` oranın ayar
dosyalarını ve hafızasını değiştirir. Onaysız hiçbir projeye dokunulmaz; seçilmeyen proje §8
raporunda `atlandı (kullanıcı seçimi)` olarak yazılır. Liste boşsa soru sorulmaz.
Seçilen her proje `<P>` için (her biri kendi kökünde):

```bash
(cd "<P>" && git status --short && git branch --show-current && git pull --ff-only)  # §2 kuralı: kirli/main değil → DUR
(cd "<P>" && CLAUDE_PROJECT_DIR="<P>" python core/scripts/team_setup.py)        # 3b/3c kuralları aynen
(cd "<P>" && python core/scripts/sync_yasaklar.py --check)                      # 3d
(cd "<P>" && CLAUDE_PROJECT_DIR="<P>" python core/scripts/ix_doctor.py)         # FAIL yok mu — bulgular §6a
```

⚠ Araçlar proje kökünü önce `CLAUDE_PROJECT_DIR`'den okur: değişkeni o projeye ayarlamazsan
**içinde bulunduğun projeyi** ölçer/kurarsın. ⚠ Projenin çalışma ağacı kirliyse (`git -C "<P>"
status --short`) `team_setup`'tan önce kullanıcıya söyle — orada yarım iş olabilir. Overlay
kapısı (3b) her projede ayrı ateşleyebilir; fark raporu o proje için gösterilir. Sonuç §8
raporunda **proje başına bir satır** olur.
`team_setup` o projenin `governance/CORE-INDEX.md`'sini yazdıysa o da **o projenin PR'ıyla**
commit edilir (§3'teki CORE-INDEX maddesi). Bunu onay sorusunun içinde söyle — tek soru,
kurulumla birlikte bu commit'i de kapsar. Projede commit yapılamıyorsa (yetki yok, dal
korumalı, kullanıcı istemedi) §8 satırına `CORE-INDEX commit edilmedi: <sebep>` yaz.

## 4. Memory tohumunu doğrula

```bash
python core/scripts/seed_memory.py --dry-run
```

**Beklenen:** `Eklendi : 0` + `Güncellenecek : 0` (adım 3 tohumladı ve güncelledi) +
`Atlandı : N (zaten mevcut, korundu)`. `Eklendi`/`Güncellenecek` 0 değilse tohum adımı koşmamıştır
→ `python core/scripts/seed_memory.py` ile koş, sonra `--dry-run`'ı tekrarla.

⚠ Tohum **merge-safe**: bu makinede yazılmış ya da düzenlenmiş hiçbir ders ezilmez, `MEMORY.md`'ye
yalnız **eksik** satırlar eklenir. `--force` KULLANMA.

**Gövde güncellemesi (core #318, 2026-10-03):** tohumda gövdesi değişen dosya, yerel kopya
`.seed-manifest.json`'daki sha ile **bayt-bayt aynıysa** (bu makinede dokunulmamış) tohumun yeni
hâliyle yazılır → özette `Güncellendi : N` + ad listesi. Yerel kopya düzenlenmişse ya da manifest
kaydı yoksa dosyaya **dokunulmaz** ve son satır `[UYARI] N tohum dosyası elle birleştirme bekliyor`
olur (team_setup çıktısında da bu satır görünür) — listedeki dosyayı tohumla **elle birleştir**;
yerelde zenginleştirilmiş içerik varsa koru. `[UYARI]` varken çıktı *"her şey güncel"* DEMEZ.

**Birleştirdikten sonra uyarıyı kapat (core #322):** birleştirilmiş kopya tohumla bayt-bayt eşit
olmadıkça araç onu her koşumda yine "düzenlenmiş" sayar — Claude Code'un frontmatter'a kendiliğinden
eklediği alanlar (`originSessionId`, `modified`) yüzünden eşitlik pratikte de kurulamaz. Birleştirme
bittiğinde dosya başına bir kez:

```bash
python core/scripts/seed_memory.py --birlestirildi <dosya>   # birden çok: bayrağı tekrarla
```

Araç manifest'e o dosya için tohumun güncel sha'sını yazar → sonraki koşumlar sessiz; tohum o
dosyada **yeniden** ilerlerse uyarı geri gelir (yine birleştir, yine işaretle). Bayrak bir
**beyandır**, birleştirmeyi denetlemez — çıktıdaki `[BİLGİ] tohumun N satırı yerel kopyada yok`
satırı yalnız ipucudur. Dokunulmamış dosya işaretlenemez (araç onu kendisi günceller), `--force`
ve `--terfi-adaylari` ile birlikte verilemez (exit 2).

⛔ **TEK SEFERLİK KURTARMA — #318 ÖNCESİ tohumlanmış makine:** eski sürüm atlanan dosyaya da
**yeni** sha'yı manifest'e yazıyordu ⇒ o makinede eski gövdeli kopya artık "dokunulmamış" olarak
tanınmaz (araç onu düzenlenmiş/yerel-ileri sayar ve güncellemez; `seed_memory.py --help` SINIR
notu). Bu makinede #318 sonrası **ilk** güncellemede aşağıdaki döngüyü bir kez koş — bütün tohum
dosyalarını tarar (`MEMORY.md` hariç: o kullanıcının indeksidir, silinmez):

```bash
C=core ; M=<bu makinenin memory dizini>
for p in "$C"/claude/memory-seed/*.md; do f=${p##*/}; q=claude/memory-seed/$f
  [ "$f" = MEMORY.md ] && continue; [ -f "$M/$f" ] || continue
  git -C "$C" show "HEAD:$q" | diff -q --strip-trailing-cr - "$M/$f" >/dev/null && continue
  hit=; for sha in $(git -C "$C" log --format=%h -- "$q"); do
    git -C "$C" show "$sha:$q" | diff -q --strip-trailing-cr - "$M/$f" >/dev/null && { hit=$sha; break; }
  done
  [ -n "$hit" ] && echo "SIL+SEED ($hit) $f" || echo "ELLE $f"
done
```

`SIL+SEED` = yerel kopya dokunulmamış eski bir tohum sürümüdür → **o dosyayı** sil; listedekiler
bitince `seed_memory.py`'yi bir kez koş. `ELLE` = yerel kopya bu makinede düzenlenmiştir →
⛔ **SİLME**, tohumla elle birleştir, sonra `--birlestirildi <dosya>` (yukarıda). Güncel olan ve
yerelde bulunmayan dosya basılmaz.
⛔ Denetimsiz *"sil + yeniden koş"* talimatı verme: yerelde zenginleştirilmiş ders kaybolur.
Silinip yeniden tohumlanan dosyanın manifest kaydı tohum sha'sıyla yazılır ⇒ sonraki
güncellemeler yine otomatik akar.

⭐ **TERS YÖN (Q325):** yukarıdaki adım yalnız *tohum → makine* yönünü doğrular. Bu makinede
yazılmış bir dersin tohuma girip girmediğini `python core/scripts/seed_memory.py --terfi-adaylari`
söyler (SALT-OKUNUR; hiçbir şey yazmaz/kopyalamaz). Kararın kendisi ders yazılırken
`metadata.seed:` alanına konur — kural `CLAUDE.core.md` §5'tedir, burada TEKRARLANMAZ.

## 5. Makine-lokal yüzeyler — `team_setup` bunları YAPMAZ

Bu üçü klonla gelmez ve betik üretmez; ilk kurulumda bir kez, sonra değiştikçe yapılır.
Tam liste: [`../ONBOARDING.md`](../ONBOARDING.md) **§0a KURULUM KAPSAMI**.

**5a. Kullanıcı-düzeyi ayarlar (ELLE):** `claude/user-settings.template.json` içindeki
`permissions.allow` · `permissions.deny` · `defaultMode` bloklarını `~/.claude/settings.json`
ile **birleştir** (mevcut anahtarları silme; `permissions` hiç yoksa olduğu gibi ekle).
⛔ Şablonda `model`/`autoMode` bilerek yoktur — hesap/plan bağımlı. ⛔ **D32:** SAP-yazma ve
davranış-yüzeyi araçları bu listeye eklenmez.

⛔ **İzin listesi TARAMAYLA ÜRETİLMEZ — tek kaynak şablondur.** Bu adımda ekrana izin öneren bir
sihirbaz/soru gelebilir (ölçülmüş vaka 2026-09-18, tüketici makine: *"also scan shell history"* ·
*"also scan your other repos"* · *"how you use Claude here"*). Kaynağı bu prosedür DEĞİLDİR ve
**varsayılanına basılmaz**:
- **Tarama seçeneklerinin HİÇBİRİ seçilmez.** Kabuk geçmişi elle yazılmış şifre/token taşıyabilir
  (ör. UI deploy parolası, bağlantı bilgisi) ve okunduğu an oturum kaydına girer — **geri alınamaz**.
  Diğer repolar başka proje/müşteri içeriğidir, kapsam dışıdır. Geçmişten türeyen liste ayrıca
  bir kez koşmuş SAP-yazma komutunu da aday yapar (D32 ihlali).
- Yalnız tarif eden, izin vermeyen sorular (kullanım biçimi gibi) zararsızdır; gerçeğe uyanı seç.
- Sihirbaz sonunda bir izin listesi önerirse **uygulama**: önce şablonla karşılaştır; şablonda
  olmayan her satır için kullanıcıya sor. Emin değilsen reddet — şablonu elle birleştirmek yeter.
- Soru ekrana gelmeden kullanıcı bu adıma gelmişse ona **önceden** söyle: *"izin önerisi/tarama
  sorusu çıkarsa hiçbir taramayı seçme."* (Vakada kullanıcı varsayılana basmak üzereydi ve
  yalnız sorduğu için durdu; ekrandaki varsayılanın ne olduğu **ölçülmedi** — bu yüzden kural
  varsayılana güvenmez.)

```bash
python -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/settings.json'),encoding='utf-8'));p=d.get('permissions',{});print('allow',len(p.get('allow',[])),'deny',len(p.get('deny',[])),'mode',p.get('defaultMode'))"
```

**5b. `gh` (GitHub CLI)** — `gh --version` çalışıyorsa atla. `winget install --id GitHub.cli -e`
(yönetici yetkisi yoksa `--scope user`, o da olmazsa cli/cli releases'ten taşınabilir zip →
kullanıcı klasörü → PATH) → yeni terminal → `gh auth login` (GitHub.com · HTTPS · tarayıcıyla) →
`gh auth status`. ⚠ **Kurulamıyorsa DUR SAYILMAZ:** prosedürün kalanı çalışır; yalnız PR/CI ayağı
ve `ix_doctor` katman-3 eksik kalır → raporda *"gh kurulamadı — sebep: …"* yaz.

**5c. git global taban** (makinede bir kez):
```bash
git config --global core.autocrlf false
git config --global core.longpaths true
git config --global init.defaultBranch main
```

## 6. Doğrula

```bash
python core/scripts/validators/run_all_validators.py
python core/scripts/ix_doctor.py
```

**Beklenen:** validator'da **FAIL yok** (WARN/BİLGİ olabilir) · `ix_doctor` FAIL yok.
CORE-INDEX FAIL verirse: `python core/scripts/build_core_index.py`.

### 6a. `ix_doctor` bir şey bulursa — her satırı ÜÇ sınıftan birine koy

`ix_doctor` **salt-okurdur**: hiçbir şeyi düzeltmez, Issue açmaz; her kontrol için PASS/WARN/FAIL
ve çoğunda bir `onarım:` / `düzelt:` ipucu basar. Ne yapılacağına **bu adımı yürüten** karar
verir. FAIL'ler **ve** WARN'lar tek tek, sırayla şu üç sınıftan birine konur:

| Sınıf | Ölçüt | Ne yapılır |
|---|---|---|
| **① ONAR** (Claude yapar) | Satır bir onarım komutu veriyor **ve** komut yalnız bu projenin kurulumunu ya da çekirdek klonunun yerel ayarını değiştiriyor: `team_setup` (`--repair-junctions` dahil) · `seed_memory` · `build_core_index` · `git -C core config …` | Komutu koş → `ix_doctor`'u (gerekirse `--layer N`) yeniden koş → satırın PASS olduğunu göster. Hâlâ FAIL ise ③'e geç. |
| **② KULLANICI** (Claude yapamaz ya da yapmamalı) | Kimlik/şifre (`.conn_adt`) · yetki ya da hesap (`gh auth`, repo/ruleset/CI sahipliği, hafıza yedeği için repo açmak) · yazılım kurulumu (CLI, Claude Code sürümü, plugin) · makine geneli ya da yönetici ayarı (managed-policy, PowerShell politikası, git **global** ayarları) · yarım iş olabilecek durum (çalışma ağacı kirli, `main ≠ origin/main`) | Ne gerektiğini tek satırla söyle, satırdaki ipucunu ver, kullanıcının yapmasını bekle; sonra yeniden ölç. Şifre ya da anahtarı Claude yazmaz. |
| **③ ÇEKİRDEK HATASI** (sahibine bildirilir) | Kurulum doğru olduğu hâlde çekirdeğin kendi dosyası ya da aracı yanlış davranıyor: ① uygulandığı hâlde süren FAIL · hook smoke / guard kablolaması FAIL'i · yolu çekirdeğe çözülen bir dosyada frontmatter uyarısı · `katman çalıştırılamadı` (aracın kendisi çöktü) | Çekirdek dosyasına yerelde **DOKUNMA** (junction'dır, her projeyi etkiler, sonraki güncellemede çakışır). [`howto-cekirdek-bulgu-bildirimi.md`](howto-cekirdek-bulgu-bildirimi.md) §1–§2 biçiminde Issue **taslağı** hazırla, kullanıcıya göster; Issue public yayındır ⇒ **açık onayla** açılır. Çekirdek sahibinin makinesindeysen Issue yerine çekirdekte normal infra düzeltme süreci işler. |

- **Emin değilsen ②'ye koy ve sor** — yanlış sınıf ①'de geri alınamaz bir değişiklik, ③'te gereksiz
  bir Issue üretir. ③'ten önce bildirim kılavuzunun §1'ini uygula: bildirimlerin çoğu aslında kurulum eksiğidir.
- Projenin **kendi** dosyasında (`claude-local/`, proje içi tanım dosyası) bulunan kusur ③ değildir:
  `ix_doctor`'un önerdiği düzeltmeyi kullanıcıya göster, onayla uygula.
- §8 raporunda her FAIL/WARN satırı sınıfıyla ve sonucuyla yazılır (`① onarıldı → PASS` ·
  `② kullanıcıya bırakıldı: <ne>` · `③ Issue taslağı: açıldı #N | kullanıcı açmadı`).

📌 Proje ile çekirdek **farklı GitHub org'undaysa** (tüketici/fork topolojisi) katman-2'de
beklenen satır `[PASS] core: remote = <org>/<repo> (proje org'undan farklı — upstream/fork
topolojisi …)`. **WARN** çıkıyorsa repo adı tutmuyor demektir → yanlış çekirdek klonlanmış
olabilir, kullanıcıya bildir.

## 7. Oturumu kapat-aç

⛔ **Atlanamaz.** Memory, kurallar, izinler ve plugin'ler **oturum başında** yüklenir; 1-6 arası
yapılanlar açık oturumda görünmez.

**Doğrulama (yeni oturumda):** açılışta `[Session başladı — <PROJE>]` bloğu gelir ve içinde
`✓ Yükleme: … core=YÜKLENDİ` satırı bulunur. Gelmiyorsa `../ONBOARDING.md` §7.

## 8. Sonucu ölç ve raporla

```bash
python core/scripts/parity_probe.py --out .tmp/parity-SONRA.json
```

`ONCE` ↔ `SONRA` karşılaştır (`python core/scripts/parity_probe.py --diff .tmp/parity-ONCE.json
.tmp/parity-SONRA.json`); kullanıcıya en az şunları ver: `memory.ders_sayisi` ·
`aktif_paket_drift` · kullanıcı-ayarlarında `permissions` doluluğu · `ix_doctor` FAIL sayısı.

**Proje başına tablo (§3e):** proje · `team_setup TAMAM` mı · yasak damgası `[EŞ]` mi ·
`ix_doctor` FAIL/WARN sayısı ve §6a sınıflarına dağılımı · CORE-INDEX commit'i (PR no ya da
`commit edilmedi: <sebep>`) · atlandıysa nedeni.

Rapora ayrıca: ① adım 3b'de **ezilen** bir elle-düzeltme oldu mu ② atlanan adım ve **nedeni**
③ yol üstünde görülüp **düzeltilmeyen** kusurlar ④ ⛔ ölçemediğin her maddeyi
`ÖLÇÜLEMEDİ: <sebep>` diye yaz — *ölçülemedi ≠ temiz*.

## 9. İlgili

- [`../ONBOARDING.md`](../ONBOARDING.md) §0a (kurulum kapsamı) · §9.1 (`parity_probe`) · §7 (yükleme teyidi)
- [`../MAINTENANCE.md`](../MAINTENANCE.md) §5 (pull disiplini + drift) · §6b (tüketici klonu)
- [`howto-cekirdek-bulgu-bildirimi.md`](howto-cekirdek-bulgu-bildirimi.md) — çekirdekte kusur bulursan
