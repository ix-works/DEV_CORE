---
name: feedback_inactive-objects-tadir-capraz-kontrol-bozuk
description: "adt_inactive_objects'in TADIR DELFLAG çapraz kontrolü çalışmıyor — count sahte pozitif; TADIR ile elle doğrula"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f9acbee7-543c-4920-a414-8358ac408be3
---

`adt_inactive_objects`, docstring'inde her girdiyi **TADIR `DELFLAG`** ile çapraz kontrol edip
silinmişleri `count`/`inactive_objects`'ten çıkarmayı ve `stale_deleted`'a taşımayı vaat eder.
**Bu çapraz kontrol fiilen ÇALIŞMIYOR** ve `warning` da vermiyor ⇒ **sessiz yanlış**.

**Why:** 2026-08-02 gün-sonu turunda `count=2`, `stale_deleted_count=0`, iki girdide de
`tadir_deleted:false` döndü (`ZCL_SD001_DIAGTMP`, `ZCL_SD001_PRECHECK_TEST`). Aynı anda TADIR
sorgusu **ikisinin de `DELFLAG='X'`** olduğunu gösterdi — objeler silinmiş, geriye bayat worklist
kaydı kalmış. `count=0` bu projede **gün-sonu / commit-öncesi "aktive bekleyen obje yok"**
kontrolüdür; sahte pozitif iki yönde de zarar verir: olmayan iş varmış gibi görünür **ve**
alışkanlık hâline gelince gerçek bir inaktif obje "her zamanki 2 kayıt" sanılıp atlanır.
📌 Tool'un kendi docstring'inde anlatılan **2026-07-29 vakasının tekrarı** — fix yazılmış, tutmamış.

**How to apply:**
1. `adt_inactive_objects` çıktısındaki `tadir_deleted:false` iddiasına **güvenme**.
2. `count > 0` ise TADIR'dan elle doğrula:
   `SELECT obj_name, delflag FROM tadir WHERE pgmid='R3TR' AND object='CLAS' AND obj_name IN (…)`
   `DELFLAG='X'` → obje silinmiş, **aktive bekleyen iş DEĞİL**.
3. Gün-sonu "temiz" kararını yalnız bu doğrulamadan sonra ver.
4. Düzeltme **core**'da (`mcp_servers/sap_adt/`, DEV_CORE); kayıt proje kuyruğunda (PR #81).

⭐ **GÜNCELLEME 2026-08-23 — İKİ ŞEY DEĞİŞTİ (ölçüldü, <PAKET-A> turu):**
1. ⛔ **"warning da vermiyor" ARTIK DOĞRU DEĞİL.** Araç bugün kusuru **açıkça beyan etti**:
   `tadir_check: "FAILED: ADT data preview sorgusu KOŞMADI — [400] Failed to run query"`,
   `tadir_deleted: null`. ⇒ *sessiz yanlış* değil, **beyan edilmiş ölçülemedi**. Bu önemli:
   `tadir_deleted:null` görünce "false" gibi okuma — *"ölçemedim"* demektir.
2. **Arıza ARALIKLI, kalıcı değil.** Aynı oturumda ardışık iki çağrı: birincisi `count:2` +
   `tadir_check: FAILED`; ikincisi `count:0` + `stale_deleted:2` + `tadir_deleted:true` (DOĞRU).
   ⇒ **Tek ölçüm yeterli değil**: `count > 0` görünce ÖNCE `tadir_check` alanına bak, `FAILED`
   ise **tekrar çağır**; ısrar ederse TADIR'dan elle doğrula (aşağıdaki 2. madde).
   ⚠ Bu, *"gün-sonu temiz mi"* kararını doğrudan etkiler: ilk ölçüm "2 obje bekliyor" derken
   gerçek **0**'dı. Ters yön de mümkündür — gerçek bir inaktif obje aynı yolla gizlenebilir.

Son-doğrulama: 2026-08-23 (önceki: 2026-08-02) · Applies-to: SAP ADT MCP (tüm projeler)
İlgili: [[feedback_inactive-worklist-audit-http200-degil]] · [[feedback_arac-basarisizligini-zararsiz-sayma]] ·
[[feedback_dogrulama-sezgileri-dort-kural]]
