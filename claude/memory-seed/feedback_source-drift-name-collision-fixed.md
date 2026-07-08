---
name: feedback_source-drift-name-collision-fixed
description: Drift-guard (ADR 0016) aynı-adlı farklı-tip dosyada sahte drift veriyordu — object_type filtresi eklendi (kök-fix)
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 612f1395-101e-440c-93a8-f64bda823d69
---

> **⚠️ GÜNCEL (ADR 0016 REVİZE): drift HARD-BLOCK (M1/M2) ARTIK YOK.** Aşağıdaki
> "sahte drift HARD-BLOCK" senaryosu o dönemin pre-push drift-block mekanizmasıdır;
> sonradan KALDIRILDI → şimdi **PULL-BEFORE-EDIT** modeli (edit-öncesi tazelik;
> [[feedback_source-drift-pull-before-edit-model]]). Bu dosyadaki `object_type`
> kök-fix'i hâlâ geçerli ve değerli — ama artık hard-block içinde değil, **pull
> helper'ın yolunda** (aynı-adlı DDLS↔BDEF doğru dosyayı kıyaslar/çeker) yaşıyor.

Source-drift guard (ADR 0016), repo dosyasını YALNIZ obje ADIYLA eşliyordu (`object_type` yok sayılıyordu). Aynı ada sahip iki tip dosya paylaşan objelerde (ör. `ZSD001_I_BOOKING` → `.cds`=DDLS interface + `.bdef`=BDEF) çoklu-eşleşme tiebreak'i `SOURCE_EXTENSIONS` sırasına göre `.bdef`'i seçiyordu → DDLS push'unda guard, canlı DDLS interface'i (57 satır) repo BDEF dosyasıyla (120 satır) kıyaslayıp **SAHTE drift HARD-BLOCK** veriyordu. `skip_reviewer` drift'i atlamaz (tasarım) → tek meşru yol kök-fix.

**Kök-fix (2026-06-16):** `scripts/source_drift.py` → `find_repo_source_file` + `detect_drift_with_fetch` + `write_repo_from_live`'a `object_type` parametresi + `_TYPE_TO_EXTENSIONS` map (ddls→.cds/.asddls/.ddls · bdef→.bdef · srvd→.srvd · srvb→.srvb · class→.abap · dcl/ddlx...) ile aday-filtresi. `scripts/sap_adt_lib.py` `detect_source_drift`+`sync_repo_from_live` çağrıları `object_type` geçiriyor. Tip None/bilinmiyor → eski rank-fallback (geriye-uyumlu; standalone validator kırılmaz). Doğrulandı: `ZSD001_I_BOOKING` ddls→.cds, bdef→.bdef.

**Why:** Name-collision objeler (DDLS↔BDEF aynı ad; srvd↔srvb) ileride aynı tuzağa düşerdi → runbook'u durdurur. Drift guard değerli (canlı silinmesini önler), silme değil düzeltme.

**How to apply:** `/mcp restart` GEREKİR (sap_adt_lib `source_drift`'i lazy-import eder; ilk push'ta sys.modules'a cache'lenir → eski kod). Restart sonrası DDLS/BDEF aynı-ad push'ları doğru dosyayı kıyaslar. Araç fix'i = lider işi ([[feedback_arac-kod-fix-lider-isi]]); gateway tespit etti ama düzeltmedi (lane disiplini doğru). Bkz. ADR 0016.
