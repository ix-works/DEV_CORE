---
name: feedback_inactive-worklist-audit-http200-degil
description: "SAP-yazımlı commit ÖNCESİ + gün-sonu: worklist_audit.py çalıştır (lider); HTTP-200 ≠ aktif, root-CDS-alan-ekleme FOR-BEHAVIOR BDEF'i sessizce inactive bırakır"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9548d6ed-a1eb-45a3-a12a-b9873f4b16c7
---

**SAP-yazımı içeren bir işi COMMIT etmeden ÖNCE + GÜN-SONU + on-demand:** lider `python scripts/worklist_audit.py --package <PKG>` çalıştırır. `REAL_INACTIVE`/`INACTIVE_ONLY` (exit 1) çıkarsa → çöz (gateway'e aktive ettir) ya da raporla, SONRA commit. Bu LİDER'in işi (ajan değil — commit + gün-sonu checkpoint lider'in; bkz. [[feedback_takim-sureklilik-gun-sonu-resume]] · [[feedback_gateway-git-commit-push-yasak]]).

**Why (2026-06-21 olayı):** Root CDS'e alan eklenince (ZSD001_I_SHIP_POOL'a PakFactor/SeStatus) o CDS'in `FOR BEHAVIOR` **BDEF'i inactive düşer**; CDS-aktivasyonu BDEF'i **co-aktive ETMEZ** → sessiz inactive bağımlı (+ srvb). Gateway "BDEF aktif" dedi çünkü doğrulama **HTTP 200**'e bakıyordu = "obje VAR" ≠ "AKTİF". Kullanıcı saatler sonra şans eseri fark etti; yanlış-"bitti" commit'e + teste sızmıştı.

**How to apply:**
- **Doğrulama:** "obje var mı" (HTTP 200) DEĞİL, **version=active** + distinct-inactive yok mu. Worklist'e GÜVENME (bayat/phantom girdi taşır — `deleted=false` bile yanıltıcı); her girdiyi **CANLI re-verify** et (active+inactive sürüm existence). `worklist_audit.py` bunu yapar: PHANTOM (ikisi de yok=silinmiş) / STALE (zaten aktif) / INACTIVE_ONLY / REAL_INACTIVE. Out-of-band (SE24/SE80 elle silme/aktive) CANLI gerçeğe göre yakalanır.
- **Konservatif:** PHANTOM/STALE zararsız (v1 rapor). REAL_INACTIVE/INACTIVE_ONLY = WIP olabilir → otomatik aktive/discard ETME, RAPORLA insan karar. Başka-transport'a dokunma.
- **WIP-güvenli:** devam-eden inactive WIP'i bloklamasın diye gate "paket temiz mi" DEĞİL "bu işin commit'inde yan-etki inactive var mı" mantığında (commit-anı snapshot; per-her-mikro-yazım DEĞİL — option B, kullanıcı kararı).
- **atom.py name-collision fix (aynı gün):** readback-gate `_LAST_PUSHED`'ı (name,type) ile key'ler — ZSD001_I_SHIP_POOL hem DDLS hem BDEF; eski sadece-isim key BDEF push'unu CDS'in üstüne yazıp BDEF aktive'inde sahte-mismatch veriyordu (`content_mismatch` FALSE-POSITIVE). Worklist endpoint: `GET /sap/bc/adt/activation/inactiveobjects` (Accept: application/vnd.sap.adt.inactivectsobjects.v1+xml). İlgili: [[feedback_source-drift-name-collision-fixed]].
- **Açık (v2):** phantom/stale worklist girdisini DISCARD mekanizması henüz doğrulanmadı → auto-clean yok (yalnız rapor); gateway canlı keşfedince eklenir.
