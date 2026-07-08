---
name: feedback_mcp-stdio-subprocess-deadlock
description: "sap-adt MCP push'u 5-6 dk sürüyordu: stdio MCP server'da subprocess.run stdin vermeyince çocuk parent'ın stdin pipe'ını miras alıp 120s donuyor; fix stdin=DEVNULL"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8c1257a6-fbd9-48f4-9ef0-5040be6f1540
---

`adt_push_source` (ddls) çağrısı **5-6 dakika** sürüyordu. Kök sebep: push, reviewer'ı (run_review.py) **iki kez** subprocess olarak çağırır (atom.py pre-flight `cds_update` + post-check `sap_active_check`), her birinin timeout'u 120s idi. **İkisi de her seferinde 120s donuyordu** → ~4 dk boş bekleme + gerçek SAP push.

**Kök sebep — script DEĞİL, spawn:** Aynı `run_review.py ... --json` komutu **standalone 0.6s** (exit 0, doğru çalışır). MCP içinde tam 120s donar. Çünkü sap-adt MCP server **`type: stdio`** (.mcp.json) → JSON-RPC'yi stdin/stdout pipe'tan konuşur. `_reviewer.py` `subprocess.run(..., capture_output=True)` çocuğun stdout/stderr'ini yönlendirir ama **stdin'ini yönlendirmez** → çocuk parent MCP'nin **stdin pipe handle'ını miras alır**, Windows'ta bu handle üzerinde bloke olur → timeout'a kadar donar.

**Why:** stdio tabanlı bir MCP/agent server'dan subprocess spawn ederken stdin'i açıkça kapatmazsan (DEVNULL), çocuk JSON-RPC pipe'ını miras alır; klasik Windows deadlock. `capture_output=True` yalnız stdout/stderr'i kapsar, stdin'i DEĞİL.

**How to apply:** stdio MCP server'da HER `subprocess.run`/`Popen`'a **`stdin=subprocess.DEVNULL`** ver. Fix uygulandı (`mcp_servers/sap_adt/_reviewer.py`): `stdin=subprocess.DEVNULL` + timeout 120→30s (savunma; gerçek run <1s). **Etkili olması için MCP server restart gerekir** (çalışan process eski modülü tutar) → `/mcp` reconnect. **✅ DOĞRULANDI 2026-06-11:** restart sonrası ddls push'ta reviewer `verdict=PASS` + 4 validator gerçekten çalıştı (`skip_reason=""`, timeout YOK), post_check=PASS, süre saniyeler. stdin kök sebepti — timeout değil; ampirik teyit. Reviewer DEĞERLİ (blocker gate + version=active/boş-source post-check, [[feedback_inline-post-empty-source-trap]] ağı) — silmeye gerek yoktu, 1 satırlık spawn bug'ıydı. T12: MCP metodoloji = template port adayı. İlişkili: [[feedback_reviewer-checklist-vs-wired-validator]].
