---
name: feedback_yeni-mcp-tool-agent-allowlist-guncelle
description: "Yeni MCP tool eklenince agent allowlist'leri OTOMATİK güncellenmez; read-only'leri elle propagate et"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f36b29d2-30b2-439f-9223-5f24072650a2
---

MCP sunucusuna yeni tool eklendiğinde (ör. sap-adt'ye yeni read-only tool), **alt-ajanlar bunu
otomatik kullanamaz** — her ajanın `tools:` frontmatter allowlist'i statiktir; listede olmayan
tool'u ajan çağıramaz (MCP sunucusu sunsa bile). Yalnız **lider** deferred-listeden görür.

**Why:** Kullanıcı otomasyon/gate yerine **kontrollü + hatırlatma** istedi (gate-moratoryumu:
önce doküman, gate son çare). "Otomatik haberdar oluyor değil mi?" varsayımı yanlıştı — kod ≠ kablolama.

**How to apply:** Yeni MCP tool geldiğinde (T11 tetikleyici):
1. **read-only** tool'ları ilgili ajanların allowlist'ine ekle; **write/exec** tool'lar
   **gateway-only** kalır (single-writer değişmezi — asla non-gateway'e write verme).
2. Kanonik kaynak: `core/claude/agents/*.md` (6 ajan) **+** proje override'ları
   `claude-local/agents/*.md` (ör. backend-expert bu projede override — ikisini de güncelle,
   yoksa override core edit'ini EZER).
3. `.claude/agents/` overlay'ini yeniden üret: `ov.materyalize(proje, core, "agents")`
   (`core/scripts/utils/claude_overlay.py`) — junction değil, gerçek dizin + banner.
4. Canlı doğrula: tools sayısı + frontmatter `---` ile başlıyor + CRLF yok + `ov.durum()` temiz.
5. Core değişikliği = branch + PR (ix-works/DEV_CORE, public — agent def'lerinde sır yok).
6. Davranış-yüzeyi değişti → behavior-manifest güncelle (F2 false-flag olmasın).

2026-07-12: 11 read-only sap-adt tool (grep_source, impact_analysis, sql_query, msgclass_read,
dump_list, inactive_objects, feature_probe, unit_run, enhancement_options/read/enhancements)
6 ajana da verildi ("hepsini herkese, en basit"). Script: scratchpad/grant_readonly_tools.py deseni.

İlgili: [[feedback_tek-gateway-route-spawn-etme]] · [[feedback_arac-kod-fix-lider-isi]] · [[project_zsd001-edi-ve-excel-siparis]]

---
**Son-dogrulama:** 2026-09-17 (ilgili core dosyasinda allowlist otomasyonu YOK — mekanizma degismemis) · **Applies-to:** bu cekirdegi kullanan tum projeler

⚠ **ARAC IDDIASI** — bu ders *"bugun su arac/kapi boyle davraniyor"* der, yapisal bir olgu
degil. Arac surumu degismis olabilir: davranisa **dayanmadan once bir kez olc**. (Vaka: bir
kardes ders, dayandigi kusur duzeltildikten sonra 3 hafta bayat yasadi; tohuma alinmadan
once olculup elendi.)
