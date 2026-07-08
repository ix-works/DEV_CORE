---
name: feedback_atc-priority-1-zorunlu
description: ATC bulgularında yalnızca Priority 1 zorunlu düzeltilir; Priority 2/3 kullanıcı onayıyla pass
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 535400ae-b5a0-4696-a522-033556d99bcf
---

ATC (Code Inspector / ZZNDBS_ATC variant) çalıştırıldığında: bir bulgunun **Priority of
finding = 1** olanları **ZORUNLU düzeltilir**. **Priority 2 ve 3** bulguları **şimdilik
kullanıcının açık onayıyla pass geçilebilir** (zorunlu değil).

**Why:** Proje kalite politikası (kullanıcı kararı 2026-06-02). Prio-1 = gerçek/kritik;
Prio-2/3 = düşük öncelik, şu aşamada bloke etmesin.

**How to apply:**
- `adt_atc_check` (mcp_servers/sap_adt/tools/query.py) yanıtında `priority_1_count`,
  `other_priority_count`, `must_fix` (prio1>0), `policy` alanları var.
- `must_fix=True` (Priority 1 bulgu var) → **DUR, düzelt** (forward progress yok).
- Sadece Priority 2/3 varsa → kullanıcıya bulguları **göster + açık onay iste** ("pass geçeyim mi?");
  onay gelirse pass. Sessizce/otomatik pass GEÇME — onay şart (ADR 0011 onay-kelimesi mantığı gibi).
- ATC variant sisteme özgü ZZNDBS_ATC (`.conn_adt` ADT_ATC_VARIANT). Bkz. [[feedback_mcp-post-shell-en-master-lang]] kardeşi reviewer kültürü (ADR 0006).
