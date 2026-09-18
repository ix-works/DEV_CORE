---
name: feedback_push-ok-mesaji-sahte-readback-esitligi
description: "Push '[OK] activated' + 5 yeşil kontrol kaynağın canlıya indiğini KANITLAMAZ; tek kanıt readback içerik eşitliğidir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 53c98875-36cc-4508-8ced-628721bdc5ab
---

Bir SAP push'unun **BAŞARILI** dönüşü, kaynağın canlıya indiğini kanıtlamaz. 2026-07-28'de bir CDS view'da ABAP tarzı `"` yorumu vardı (CDS DDL'de yorum `//` ve `/* */`'dir); SAP kaynağı **sessizce reddetti** ama push `[OK] Source uploaded` + `[OK] Object activated` dedi. **Beş kontrol de yeşildi:** `run_review` PASS · `abaplint` temiz · `run_all_validators` OK · `adt_syntax_check valid:true` · push mesajı OK. Kaynak canlıya **hiç inmedi** (canlı 4163 ch, yerel 5321 ch). Yakalayan tek şey **readback eşitliğiydi**.

Aynı gün ikinci sınıf: `.srvd`'de yorum → SAP *"will be deleted on save"* der ve yorumu **sessizce siler**, obje aktive olur; repo canlıdan sapar. Kanıt: kural yokken 3 SRVD **aylarca** sapık kaldı, objeler aktif ve çalışıyordu.

**Why:** [[feedback_arac-basarisizligini-zararsiz-sayma]] bir BAŞARISIZLIĞIN "zararsız" çerçevelenmesini yasaklar; bu onun **aynası** — bir BAŞARI mesajının kendisinin sahte olması. `adt_syntax_check` bu vakada INACTIVE sürümü okur, yani yeni kaynak hakkında **hiçbir şey söylemez**. Aynı kök: [[feedback_inline-post-empty-source-trap]] (status 200 = obje VAR, source dolu DEĞİL) ve [[feedback_done-tam-kapsam-dogrula]].

**How to apply:** (1) Push sonrası **içerik eşitliği** ara — `adt_get include_source=true` ile canlıyı oku, yüklenenle karşılaştır; "activated" mesajını kanıt sayma. (2) Fark varsa **biçim mi içerik mi** ayır: SAP bazı obje tiplerinde pretty-print eder (gerçek vaka: bir tabloda 12 fark satırı, hepsi hizalama boşluğu). Tüm boşluklar atıldığında hâlâ farklıysa → **gerçek içerik uyuşmazlığı**, push BAŞARISIZ sayılır. (3) Katman-özel yorum sözdizimi: `.cds` → `//` ve `/* */` (**`"` YASAK**) · `.srvd` → **hiç yorum yok** (yorum `.rules.md`'ye taşınır) · `.abap` → `"` ve `*`. (4) İkisi de artık gate'li: `check_cds_srvd_comment_syntax.py` (BE-58) + `push_object` içerik uyuşmazlığında `success=False` döner — ama **gate kanıt değil**, readback yine bakılır.
