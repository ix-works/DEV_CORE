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

## 3. Kurulumu tazele — `team_setup.py`

```bash
python core/scripts/team_setup.py
```

Betik şu zinciri koşar (ölçüldü, `team_setup.py` main akışı):
junction'lar + **overlay materyalizasyonu** (`.claude/rules/00-claude-core.md`, `agents`) →
`.claude/settings.json` + `scripts/hook_shim.py` + **`.claude/active_package`** →
git-hooksPath (core + proje) → **CORE-INDEX** yenileme → plugin kurulumu + npm CLI'ler →
**memory tohumu** (`seed_memory.py`, merge-safe) → smoke testleri.

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

**Doğrulama:** çıktıda `FAIL` satırı yok · son satır `team_setup TAMAM` · `.claude/active_package` var.

## 4. Memory tohumunu doğrula

```bash
python core/scripts/seed_memory.py --dry-run
```

**Beklenen:** `Eklendi : 0` (adım 3 tohumladı) + `Atlandı : N (zaten mevcut, korundu)`.
`Eklendi` 0 değilse tohum adımı koşmamıştır → `python core/scripts/seed_memory.py` ile koş,
sonra `--dry-run`'ı tekrarla.

⚠ Tohum **merge-safe**: bu makinede yazılmış hiçbir ders ezilmez, `MEMORY.md`'ye yalnız **eksik**
satırlar eklenir. `--force` KULLANMA.

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

`ONCE` ↔ `SONRA` karşılaştır; kullanıcıya en az şunları ver: `memory.ders_sayisi` ·
`aktif_paket_drift` · kullanıcı-ayarlarında `permissions` doluluğu · `ix_doctor` FAIL sayısı.

Rapora ayrıca: ① adım 3b'de **ezilen** bir elle-düzeltme oldu mu ② atlanan adım ve **nedeni**
③ yol üstünde görülüp **düzeltilmeyen** kusurlar ④ ⛔ ölçemediğin her maddeyi
`ÖLÇÜLEMEDİ: <sebep>` diye yaz — *ölçülemedi ≠ temiz*.

## 9. İlgili

- [`../ONBOARDING.md`](../ONBOARDING.md) §0a (kurulum kapsamı) · §9.1 (`parity_probe`) · §7 (yükleme teyidi)
- [`../MAINTENANCE.md`](../MAINTENANCE.md) §5 (pull disiplini + drift) · §6b (tüketici klonu)
- [`howto-cekirdek-bulgu-bildirimi.md`](howto-cekirdek-bulgu-bildirimi.md) — çekirdekte kusur bulursan
