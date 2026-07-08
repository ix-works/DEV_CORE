---
name: feedback_yeni-teknoloji-once-kural-seti
description: "Yeni teknoloji/pattern (RAP gibi) ile İLK KEZ SAP'ye yazmadan önce tam formal kural seti yaz — deney bile olsa"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 08868cc7-ead9-4d38-b6fe-2fd1fd3eb04c
---

Yeni bir SAP teknolojisi/pattern'i (RAP gibi) bu projede **ilk kez**
uygulanacaksa, SAP'ye veri yazmaya başlamadan **önce** tam formal kural setini
hazırla: L2 standard + L3 playbook (ÇALIŞAN/DENENEN-BAŞARISIZ iskeleti) + reviewer
checklist + run_review task tipi + L4 `.rules.md` naming reconcile + gerekiyorsa
validator reconcile. Kullanıcı 2026-05-15'te ORDER RAP pilotunda spike'ı durdurup
"RAP ilk kez yapıyoruz, önce kural setlerini/dökümanları hazırlasak" dedi ve
"tam formal standart şimdi" seçti (lean/inline değil).

**Why:** İlk-kez teknolojide deneme-yanılma riski yüksek; governance'ı sonraya
bırakmak ADR 0005/0006 ihlali ve playbook T2 borcu yaratır. Kullanıcı operatör
bağımlılığını ve patinajı reddediyor — kural-önce, yazma-sonra onun açık tercihi.
"Deney" olması formal governance'ı atlamak için gerekçe değil.

**How to apply:** Yeni teknolojiyle ilk SAP yazmasından önce DUR → kural seti
öner (katman haritası + kapsam çatalı: lean-pilot / tam-formal / inline) →
AskUserQuestion ile kapsamı netleştir → yaz → `run_all_validators` yeşil →
sonra SAP. Kanıtlanmamış adımı playbook'ta "KANITLANMADI" diye işaretle, asla
çalışıyormuş gibi sunma. ADR ise pilot/karar SONRASI (erken ADR yazma).
Bkz. [[project_zsd015-ui-paradigm-all-or-nothing]], [[feedback_playbook-once-oku]].
