---
name: feedback_baglanti-tutarsizligi-adt-blok
description: ".conn_adt ile MCP'nin canli baglantisi ayrisikken (switch_tier yapildi ama /mcp restart edilmedi) HICBIR ADT islemi yapma; kullaniciyi sebebiyle uyar — kod gate ile dayatildi"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 98abb347-958c-4aee-b22e-8fb867e88232
---

`.conn_adt` ile MCP'nin **canli bagli oldugu** sistem ayrisikken (kullanici `switch_tier` ile sistem degistirdi ama `/mcp` restart etmedi) **HICBIR ADT islemi yapilmamali** — okuma dahil. Bu durumda DUR, kullaniciyi **sebebini aciklayarak** uyar, `/mcp` iste, bekle.

**Why:** MCP client baglantiyi ilk cagrida `.conn_adt`'den okuyup surec boyunca cache'ler. `switch_tier` dosyayi aninda degistirir ama MCP eski sisteme bagli kalir. Sonuc: ADT istegi ESKI sisteme gider ama tier readonly-guard (get_active_tier) YENI sistemi okur → "DEV'e yaziyorum" sanip fiilen baska sisteme ( or. ECC QA) islem yapma riski. Felaket potansiyeli: yanlis sistemde mutasyon. Kullanici talimati (2026-06-09): "bu tutarsizlik aktifken ADT ile hicbir islem yapma, kullaniciyi uyar; muhakkak calismali, koda gore kurgula" → hatirlamaya birakilamaz.

**How to apply:** Mekanizma KOD ile dayatildi (hatirlama degil):
- MCP canli baglantisini `.claude/.mcp_active_system`'e yazar — `server.main()` acilista (`.conn_adt`'den intended) + `atom._record_active_binding` ilk-baglaniste (fiili url/client). Yazici: `_conn.write_mcp_binding_state()`.
- `scripts/hooks/pre_tool_guard.py`: `mcp__sap-adt__*` cagrilarini `.conn_adt` host/client != `.mcp_active_system` ise **exit 2 ile REDDEDER** (stderr → Claude). Bash MUAF (script'ler taze .conn_adt okur, tutarsizlik olamaz); `ping` MUAF.
- `atom._get_client` backstop: cache'li client host'u `.conn_adt`'den ayrisirsa RuntimeError.
- statusline: `!MCP=<sistem> (/mcp)` uyarisi gosterir (gorsel).

Blok mesaji gelince: kullaniciya tutarsizligi acikla + `/mcp` iste. Commit `e703ae68`. ADR 0010 uzantisi. Iliskili: [[feedback_mcp-post-shell-en-master-lang]], cok-sistem slotlari conn/README.md.
