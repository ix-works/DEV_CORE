---
description: Yeni/güncellenen geliştiriciyi bu repo'nun Claude ortamına paralel hale getirir (pull + setup + doğrula + brief)
---

Sen bu geliştiricinin Claude ortamını, repo'nun sahibiyle **birebir paralel** hale getiriyorsun.
Aşağıdaki adımları SIRAYLA yürüt. Her adımı kısa raporla; bir adım başarısızsa DUR, sebebini söyle, çözüm öner, sonra devam.

## ADIM 1 — Ortam ön-kontrol
- Repo kökünde misin? (`CLAUDE.md` + `.mcp.json` + `scripts/team_setup.py` görünür olmalı.)
- Git repo mu, hangi branch, çalışma ağacı temiz mi? (`git status`)
- Çalışma ağacı kirliyse: kullanıcıya bildir, `git pull` öncesi commit/stash gerektiğini söyle, ONAY bekle.

## ADIM 2 — Güncelle + bağımlılıkları kur
- `python scripts/team_setup.py` çalıştır. Bu TEK komut: python sürüm kontrolü → `git pull` → `pip install -r mcp_servers/sap_adt/requirements.txt` → active_package wizard → `.conn_adt` kontrolü → statusline + MCP ping smoke. Çıktısını özetle.
- npm CLI'ları (ui5/fiori, mmdc, marp, playwright) gereken işler için: `python scripts/doc_tools.py check` ve gerekiyorsa team_setup'ın kurduğu listeye bak. Eksikse kullanıcıya hangi `npm i -g ...`'in gerektiğini söyle (sen global kurma — kullanıcı onaylasın).

## ADIM 2.4 — Gerekli Claude Code plugin'leri (ZORUNLU araçlar)
- `python scripts/setup_plugins.py` çalıştır. Bu, projenin sağlıklı çalışması için GEREKEN plugin'leri kurar (idempotent): **ui5** (Fiori/UI5 — control API + linter + manifest), **playwright** (UI tarayıcı doğrulama), **pyright-lsp**, **code-review**, **frontend-design**, **claude-md-management**, **skill-creator**, **plugin-dev** — hepsi `claude-plugins-official` marketplace'ten. Backend ABAP + frontend RAP/Fiori işi için bunlar şart.
- Çıktıyı özetle (Kurulu/Kurulacak/Başarısız). `claude` CLI PATH'te yoksa veya bir kurulum başarısızsa AÇIKÇA belirt + manuel komutu ver: `claude plugin install <ad>@claude-plugins-official`.
- **ÖNEMLİ:** Plugin'ler **yeni Claude oturumunda** aktif olur → kurulum sonrası kullanıcıya "Claude Code'u tamamen kapat-aç" de.

## ADIM 2.5 — Memory tohumu (proje sahibinin çalışma-disiplini kuralları)
- `python scripts/seed_memory.py` çalıştır. Bu, repoya committed `.claude/memory-seed/` (feedback memory = "nasıl çalışılır" kuralları) tohumunu bu makinedeki Claude proje-hafıza klasörüne kopyalar (merge-safe: var olanı EZMEZ). Böylece yeni geliştiricinin Claude'u, proje sahibiyle **aynı çalışma disiplinine** (build-dağıt, doğrula-önce-flag, tek-yazıcı, deploy-onayı vb.) sahip olur.
- Çıktıyı özetle (Eklendi/Atlandı). **ÖNEMLİ:** Tohum yeni oturumda yüklenir → seed sonrası kullanıcıya "yeni bir Claude oturumu aç" de (mevcut oturum eski memory ile başlamış olabilir).
- Not: Yalnız `feedback` tipi tohumlanır; projeye-özel work-state tohuma dahil değildir.

## ADIM 3 — Kişisel SAP bağlantısı (`.conn_adt`) — ŞİFRE ASLA SOHBETE YAZILMAZ
- `.conn_adt` var mı? Yoksa: `conn/README.md` + `conn/*.env.template` formatını göster, **kullanıcının kendi SAP kullanıcı/şifresiyle** `.conn_adt`'yi (repo kökünde, nokta ile) oluşturmasını iste. Şifreyi SEN sorma/yazma; kullanıcı dosyayı kendisi düzenlesin (`.conn_adt` gitignore'da, repoya gitmez).
- Tier/multi-system kullanılıyorsa `conn/` altındaki `.env` dosyalarını da kendi kimlikleriyle doldurmaları gerektiğini belirt (ADR 0010).

## ADIM 4 — MCP server (sap-adt) aktivasyonu
- `.mcp.json` repo'da var → Claude Code bu projeyi açınca `sap-adt` MCP server'ını **onaylamanı** ister. Onaylanmadıysa kullanıcıya "MCP onay dialog'unu kabul et / `/mcp` ile bağlan" de.
- **ÖNEMLİ:** `mcp_servers/` kodu `git pull` ile değiştiyse MCP stdio server'ı **`/mcp` ile yeniden bağlanmalı** (otomatik restart YOK). Hook'lar (scripts/hooks/) restart İSTEMEZ — her çağrıda taze çalışır.
- `python scripts/sap_doctor.py` ile bağlantı + tier + master-lang + MCP modül + canlı auth doğrula.

## ADIM 5 — Doğrula (paralel mi)
- `python scripts/validators/run_all_validators.py --quick` → OK olmalı.
- Statusline çalışıyor mu (team_setup smoke).
- Şunları teyit et ve kullanıcıya "AKTİF" diye raporla: hook'lar (PreToolUse pull-before-edit + pre_tool_guard, PostToolUse post_validate, UserPromptSubmit skill_injector, SessionStart protokol enjeksiyonu), MCP sap-adt (11 tool + ADR 0005 guardrail), roller (`.claude/agents/`), skills, validatörler.

## ADIM 6 — İşletim modeli brief'i (kısa)
Kullanıcıya 5-6 satırla özetle:
- **ADR 0005 KESİN YASAKLAR** (standart obje/tablo/transport koruma) — CLAUDE.md başı.
- **Tek-yazıcı modeli** (ADR 0018): SAP'ye yalnız `adt-gateway` yazar; expert'ler tasarlar, bug-expert inceler.
- **Pull-before-edit** (ADR 0016): SAP kaynağı düzenlemeden önce hook canlıyı çektirir; bayatsa edit'i bloklar.
- **Reviewer pre-flight** (ADR 0006): SAP yazma öncesi `run_review.py`.
- Yeni bilgi nereye → CLAUDE.md Bölüm 3-4 (trigger + karar ağacı).
- Detay: `ONBOARDING.md` + `CLAUDE.md` + `AGENTS.md`.

## SONUÇ
"✅ Ortamın repo sahibiyle paralel: kurallar/hook'lar/MCP/roller aktif, bağlantı doğrulandı. Artık aynı protokolle çalışabilirsin." de. Eksik kalan (örn. `.conn_adt` doldurulmadı, MCP onaylanmadı) varsa AÇIKÇA listele.
