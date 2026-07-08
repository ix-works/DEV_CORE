# ONBOARDING — Bu repo'nun Claude ortamına paralel hale gelmek

> **Amaç:** Repo'yu lokaline çeken **her geliştirici**, repo sahibiyle **birebir aynı** Claude
> ortamına (aynı kurallar, hook'lar, MCP araçları, roller, kod-gate'ler) sahip olur.
> **Çekirdek fikir:** _Ortam = repo'nun kendisi._ Ayar dosyaları version-control'de; clone =
> ortamı da çekmek demektir.

---

## TL;DR — 2 adımda paralel ol

1. Repo'yu çek/aç (Claude Code ile bu klasörü aç).
2. Claude'a şunu yaz: **`/onboard`**
   (Slash-command yoksa: aşağıdaki **"Paste-Prompt"**'u yapıştır.)

Claude geri kalanını yürütür: `git pull` → bağımlılık kurulumu → `.conn_adt` rehberi → MCP
onayı/yeniden-bağlanma → doğrulama → işletim modeli brief'i.

---

## Ne OTOMATİK gelir (clone'da, ekstra iş yok)

| Katman | Nerede (committed) | Clone'da |
|---|---|---|
| Davranış kuralları (L1–L4) | `CLAUDE.md`, `AGENTS.md`, `standards/`, `playbook/`, `governance/` | Otomatik yüklenir |
| **Hook'lar** (pull-before-edit, pre_tool_guard, post_validate, skill_injector, session_start…) | `.claude/settings.json` + `scripts/hooks/` | **Otomatik aktif** (exec-form + `${CLAUDE_PROJECT_DIR}`, taşınabilir) |
| **MCP server** (sap-adt: 11 tool + ADR 0005 guardrail) | `.mcp.json` + `mcp_servers/` | Claude **onay sorar** → aktif |
| Roller (gateway / expert / bug-expert) | `.claude/agents/` | Otomatik |
| Skills | `.claude/skills/` | Otomatik |
| Validatörler / kod-gate'ler | `scripts/validators/` | Otomatik |

> Yani senin gördüğün "edit öncesi SAP'den çek", "edit'i hook bloklasın", "SAP yazmadan reviewer"
> gibi davranışların **hepsi settings.json + scripts/hooks**'ta — commit'li → herkeste aynı çalışır.

## Ne PER-DEVELOPER (otomatikleşemez — bir kez)

1. **Bağımlılıklar:** python paketleri + npm CLI'lar → `python scripts/team_setup.py` (tek komut).
2. **`.conn_adt`:** senin **kişisel** SAP kullanıcı/şifren. `.gitignore`'da → repoya gitmez, her dev kendi yaratır. Şablon: `conn/*.env.template` + `conn/README.md`. **Şifreyi Claude sohbetine yazma**, dosyayı kendin düzenle.
3. **MCP onayı:** Claude Code projeyi açınca `sap-adt`'yi onaylamanı ister (bir kez).
4. **MCP yeniden-bağlama:** `git pull` `mcp_servers/` kodunu değiştirdiyse `/mcp` ile **reconnect** (otomatik restart yok). _Hook'lar reconnect istemez — her çağrıda taze._

---

## Paste-Prompt (slash-command kullanamıyorsan)

Aşağıyı Claude'a olduğu gibi yapıştır:

```
Bu repo'nun sahibiyle Claude ortamımı PARALEL hale getir. Sırayla:
1) git durumunu kontrol et (temizse) `python scripts/team_setup.py` çalıştır — pull + bağımlılık
   kurulumu + MCP/statusline smoke. Çıktıyı özetle.
2) `.conn_adt` var mı bak; yoksa conn/README.md + conn/*.env.template formatını göster, ŞİFREMİ
   SORMADAN kendi SAP kimliğimle dosyayı oluşturmamı iste (gitignore'da).
3) sap-adt MCP server'ını onaylamamı hatırlat; mcp_servers/ değiştiyse `/mcp` reconnect dediğini söyle.
4) `python scripts/sap_doctor.py` + `python scripts/validators/run_all_validators.py --quick` ile doğrula.
5) Aktif olan kuralları/hook'ları/MCP'yi/rolleri ve ADR 0005 yasaklarını + tek-yazıcı (ADR 0018) +
   pull-before-edit (ADR 0016) + reviewer (ADR 0006) modelini 5-6 satırla brief et.
Eksik kalan adımı açıkça listele. (Detay: ONBOARDING.md + CLAUDE.md + AGENTS.md.)
```

---

## Doğrulama (paralel olduğunu nasıl anlarsın)

- `python scripts/sap_doctor.py` → tüm katmanlar OK (bağlantı + tier + master-lang + MCP + auth).
- `python scripts/validators/run_all_validators.py --quick` → OK.
- Yeni oturum ilk yanıtı **CLAUDE.md §2 "Ekran Teyidi"** formatıyla başlamalı (hook protokolü enjekte eder).
- Bir SAP kaynağını düzenlemeyi denediğinde **pull-before-edit hook** devreye girer (bayatsa bloklar).

## Sık sorulanlar

- **"MCP otomatik kurulur mu, restart ister mi?"** Config (`.mcp.json`) otomatik gelir; server kodu repo'da, deps `team_setup` kurar. Kod değişince `/mcp` reconnect (manuel). Hook'lar restart istemez.
- **"Kurallar/hook'lar herkeste aynı mı?"** Evet — `.claude/settings.json` + `scripts/hooks` commit'li. Kişisel olan tek şey `.conn_adt` ve `.claude/settings.local.json` (gitignore'da).
- **"Modül bağımsız mı?"** Evet — kurallar proje-geneli (L1-L3) + paket-spesifik (L4 `ERP/<MODULE>/<PKG>/.rules.md`). Yeni modül/paket: `python scripts/bootstrap_package.py`.

---

> Bu doküman ve `/onboard` komutu **DEVELOPMENT_TEMPLATE_FILES** template reposuna da
> (kimlik placeholder'lanarak) port edilir — yeni projeler aynı onboarding'i devralır.
