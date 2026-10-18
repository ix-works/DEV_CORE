---
description: Çekirdeği güncelle ve bu makinedeki tüm projeleri hizala — ek talimat gerektirmez (pull + team_setup + diğer projeler + makine-lokal yüzeyler + doğrula + ölç)
---

Kullanıcı çekirdeği (`core/` = bu makinedeki tek DEV_CORE klonu) güncellemeni istedi.
**Bu komut tek başına yeterlidir: kullanıcıdan ek talimat BEKLEME.** Aşağıdaki akışı sonuna
kadar yürüt; yalnız prosedürün "DUR" dediği yerde dur, çıktıyı göster ve sor.

**Kanonik prosedür: `core/playbook/howto-cekirdek-guncelleme.md`.** Bu komut onun kopyası
değil, yürütme sırasıdır; çakışmada **howto kazanır** (tek kaynak ilkesi).

1. **Howto'yu oku → başlangıcı ölç (§1):** `parity_probe` ÖNCE · `git -C core status --short`
   boş mu · dal `main` mi. Kirliyse DUR.
2. **Çek (§2):** `git -C core pull`.
3. ⭐ **Howto'yu YENİDEN OKU** — pull prosedürün kendisini güncellemiş olabilir; kalan adımları
   yeni kopyadan yürüt (bu komut dosyası da değişmiş olabilir; yeni hâli sonraki oturumda yüklenir).
4. **Bu proje (§3–§4):** `team_setup` → son satır `team_setup TAMAM` · 3b overlay kapısı ·
   3c MCP smoke · 3d yasak damgası · tohum doğrulaması.
5. **Diğer projeler (§3e):** bu çekirdeği kullanan projeleri bul, listeyi göster, her birinde
   `team_setup` + damga kontrolü + `ix_doctor` (her biri KENDİ kökünde, `CLAUDE_PROJECT_DIR` o projeye ayarlı).
6. **Makine-lokal yüzeyler (§5):** kullanıcı-düzeyi izin tabanı (elle birleştir) · `gh` · git global taban.
7. **Doğrula (§6):** `run_all_validators` + `ix_doctor` — FAIL yok.
8. **Ölç ve raporla (§8):** parity ÖNCE/SONRA farkı + proje başına tablo + atlananlar/ölçülemeyenler.
   Son cümle: *"Claude Code'u kapatıp açın; yeni oturumun ilk mesajında `✓ Yükleme: … core=YÜKLENDİ`
   görünmeli (diğer projelerde de ilk açılışta)."*

Bu turda kolayca kaçırılan üç şey:

1. ⛔ **Çalışma ağacı kirliyse pull ETME** — çekirdekte yerel yama olabilir; kullanıcıya sor,
   yamayı kendi dalına al, tur sonunda raporla.
2. ⛔ **`team_setup` overlay ezme kapısına (T2.5) takılırsa `return 1` ile çıkar ve plugin +
   memory tohumu HİÇ koşmaz.** Çıktının sonunda `team_setup TAMAM` satırını gör; `FARK VAR`
   yazıyorsa fark raporunu kullanıcıya göster, sonra `--overlay-onayli` ile tekrar koş.
   Kapı her turda ateşlemez — baştan `--overlay-onayli` ile başlama.
   ⛔ **`return 1`'in İKİNCİ sebebi MCP import smoke'udur** (`[FAIL] MCP server import smoke
   BAŞARISIZ …` + `team_setup BAŞARISIZ (MCP server import smoke)`): sap-adt MCP sunucusu bu
   yorumlayıcıyla import edilemiyor (ör. `mcp 2.x`). Burada **`--overlay-onayli` ÇARE DEĞİLDİR** —
   FAIL satırındaki onarımı uygula (`<python> -m pip install -r …/mcp_servers/sap_adt/requirements.txt`,
   `mcp<2` sınırını taşır), sonra team_setup'ı yeniden koş. Son satır `No module named
   'mcp_servers'` ise pip ÇARE DEĞİLDİR: `.mcp.json` sap-adt `env.PYTHONPATH` =
   `${CLAUDE_PROJECT_DIR:-.}/core` olmalı ve proje `core` bağı bulunmalı (FAIL satırı bunu söyler).
3. ⛔ **`team_setup` makine-lokal yüzeyleri üretmez:** `~/.claude/settings.json` izin tabanı
   (şablon: `core/claude/user-settings.template.json`, **elle birleştirilir**), `gh` kurulumu/auth,
   git global baseline. Bunlar atlanırsa kurulum çalışır **görünür** ama farklı davranır.
   ⛔ İzin listesi **taramayla üretilmez**: ekrana *"scan shell history / scan other repos"* gibi
   bir izin sihirbazı gelirse **hiçbir tarama seçilmez**, varsayılana basılmaz, önerdiği liste
   şablonla karşılaştırılmadan uygulanmaz (howto §5a). Kullanıcıyı bu adımdan ÖNCE uyar.

⛔ Bu tur SAP'ye yazmaz · `--force` kullanmaz · junction'a özyinelemeli silme uygulamaz.
⛔ Ölçemediğin hiçbir şeyi "temiz" sayma; raporda `ÖLÇÜLEMEDİ: <sebep>` diye yaz.

Sonuç: neyin değiştiğini (çekirdek commit'i, memory ders sayısı, kapanan FAIL'ler) ve
**atlanan/eksik kalan** her maddeyi nedeniyle birlikte listele.
