---
description: Çekirdeği güncelle ve kurulumu hizala (pull + team_setup + makine-lokal yüzeyler + doğrula + ölç)
---

Kullanıcı çekirdeği (`core/` junction'ı = canlı DEV_CORE) güncellemeni istedi.

**Kanonik prosedür: `core/playbook/howto-cekirdek-guncelleme.md` — ÖNCE ONU OKU, adımları
oradan yürüt.** Bu komut dosyası o prosedürün kopyası değildir; kısa hatırlatıcısıdır ve
çakışma halinde **howto kazanır** (tek kaynak ilkesi).

Sıra: ① durum ölç + `git -C core status` temiz mi ② `git -C core pull` ③ `team_setup.py`
④ tohum doğrula ⑤ makine-lokal yüzeyler (kullanıcı ayarları · `gh` · git global taban)
⑥ validator + `ix_doctor` ⑦ oturumu kapat-aç ⑧ ölç ve raporla.

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
