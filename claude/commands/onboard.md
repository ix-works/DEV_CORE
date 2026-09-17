---
description: Yeni/güncellenen geliştiriciyi bu repo'nun Claude ortamına paralel hale getirir (pull + setup + doğrula + brief)
---

Sen bu geliştiricinin Claude ortamını repo sahibiyle **birebir paralel** hale getiriyorsun.
Metodoloji **`core/` junction'ındadır** (canlı çekirdek — ADR 0020): script/validator/hook/MCP
tek fiziksel kopyadan gelir, komutlar `python core/scripts/...` ile çağrılır. Adımları SIRAYLA
yürüt; her adımı kısa raporla; başarısızsa DUR → sebep + çözüm önerisi. "Neden"leri anlatan
el kitabı: `core/ONBOARDING.md` — detay gereken her yerde oraya yönlendir.

## ADIM 1 — Güncelle (git)
- Proje kökünde misin? (`CLAUDE.md` + `.mcp.json` + `project.yaml` görünür olmalı.) `git status` — çalışma ağacı kirliyse bildir, `git pull` öncesi commit/stash için ONAY bekle.
- `git pull` (proje reposu) + **çekirdek de güncellensin:** `git -C core pull` (makinedeki TEK fiziksel DEV_CORE — güncelleme tüm projelere birden yansır).

## ADIM 2 — Kurulum: `python core/scripts/team_setup.py`
- İdempotent TEK komut; fiili adımları: Python-sürüm kontrolü → `pip install` (MCP requirements) → **4 junction** (`core` + `.claude/agents|skills|commands`) → eksik proje dosyalarını tamamlama → core hooksPath → Claude Code **plugin kurulumu** (`setup_plugins.py`) + npm CLI'ler (playwright-cli, ast-grep, mmdc, marp; non-fatal) → **memory tohumu** (`seed_memory.py` — CORE `claude/memory-seed`'den, merge-safe: var olanı EZMEZ) → `.conn_adt` var-mı kontrolü → smoke testler. Çıktıyı özetle.
- ⛔ **Overlay ezme kapısı (T2.5):** çıktıda `FARK VAR — onaysız ezme YOK` görürsen betik `return 1` ile çıkmıştır ve **plugin + memory tohumu HİÇ koşmamıştır**. Fark raporunu kullanıcıya göster, sonra `python core/scripts/team_setup.py --overlay-onayli` ile tekrar koş. Her koşumda ateşlemez — baştan bu bayrakla başlama. Doğrulama: son satır `team_setup TAMAM`.
- **ÖNEMLİ:** Plugin'ler ve memory tohumu **yeni Claude oturumunda** aktifleşir → kurulum sonrası kullanıcıya "Claude Code'u kapat-aç" de. `claude` CLI PATH'te yoksa veya bir plugin kurulamadıysa AÇIKÇA belirt (manuel: `claude plugin install <ad>@claude-plugins-official`).

## ADIM 3 — Kişisel SAP bağlantısı + MCP — ŞİFRE ASLA SOHBETE YAZILMAZ
- `.conn_adt` yoksa: şablonu göster — `core/claude/conn_adt.template` (tek sistem; çoklu-tier/çoklu-sistem: `conn/*.env.template`, ADR 0010) — ve **kullanıcının kendi SAP kimliğiyle** proje kökünde `.conn_adt` oluşturmasını iste. Şifreyi SEN sorma/yazma; dosya gitignore'dadır, repoya gitmez.
- `.mcp.json` repo'da → Claude Code `sap-adt` MCP server onayı ister; onaylanmadıysa "/mcp ile bağlan" de. `core/mcp_servers/` kodu pull ile değiştiyse `/mcp` ile **yeniden bağlan** (otomatik restart YOK; hook'lar restart istemez).
- SAP bağlantı sağlığı: `python core/scripts/sap_doctor.py` (bağlantı + tier + master-lang + canlı auth).

## ADIM 3b — Makine-lokal yüzeyler (klonla GELMEZ, `team_setup` ÜRETMEZ)
- **Kullanıcı-düzeyi izin tabanı (ELLE):** `core/claude/user-settings.template.json` içindeki `permissions.allow`/`deny` + `defaultMode` bloklarını `~/.claude/settings.json` ile **birleştir** (mevcut anahtarları silme). Bu dosya yoksa rutin komutlar sürekli onay sorusu çıkarır ve otonom adımlar yarıda kalır — iki makine arasında ölçülen **en büyük** davranış farkı buydu. ⛔ D32: SAP-yazma/davranış-yüzeyi araçları listeye EKLENMEZ. `model`/`autoMode` şablonda bilerek yok.
- **`gh` (GitHub CLI):** `gh auth status` çalışmıyorsa `winget install --id GitHub.cli -e` (yetki yoksa `--scope user` ya da taşınabilir zip) → `gh auth login`. Kurulamıyorsa DUR sayılmaz; PR/CI ayağı + `ix_doctor` katman-3 eksik kalır, raporda **nedeniyle** yaz.
- **git global taban:** `core.autocrlf false` · `core.longpaths true` · `init.defaultBranch main`.
- Tam liste: `core/ONBOARDING.md` **§0a KURULUM KAPSAMI** (hangi yüzeyi kim üretir, nasıl doğrulanır).

## ADIM 4 — Doğrula
- `python core/scripts/ix_doctor.py` → 7-katman kurulum taraması (junction/git/GitHub-enforce/Claude-katmanı/MCP/validator/iş-akışı) — FAIL yok olmalı.
- `python core/scripts/validators/run_all_validators.py --quick` → OK olmalı.
- **İkinci bir makineyle eşliği ölçmek istersen:** `python core/scripts/parity_probe.py --out .tmp/parity.json` → iki raporu karşılaştır (`core/ONBOARDING.md` §9.1).
- 📌 **Güncelleme** (ilk kurulum değil) yapıyorsan kanonik prosedür: `core/playbook/howto-cekirdek-guncelleme.md` (slash: `/core-guncelle`).

## ADIM 5 — İş durumu + işletim modeli brief'i (kısa)
- Aktif paketin son `SESSION_NOTES.md` girişini oku, 1-2 satırla aktar (aktif paket belirsizse kullanıcıya sor).
- 5-6 satır özet: **ADR 0005 KESİN YASAKLAR** (kök `CLAUDE.md` başı) · **tek-yazıcı** (ADR 0018: SAP'ye yalnız `adt-gateway` yazar) · **pull-before-edit** (ADR 0016) · **reviewer pre-flight** (ADR 0006: `run_review.py`) · yeni bilgi nereye → `core/CLAUDE.core.md` §4 SORU 0. Detay: `core/ONBOARDING.md` + `CLAUDE.md` + `core/AGENTS.md`.

## SONUÇ
"✅ Ortamın repo sahibiyle paralel: kurallar/hook'lar/MCP/roller aktif, bağlantı doğrulandı." de. Eksik kalan (örn. `.conn_adt` doldurulmadı, MCP onaylanmadı, plugin kurulamadı) varsa AÇIKÇA listele.
