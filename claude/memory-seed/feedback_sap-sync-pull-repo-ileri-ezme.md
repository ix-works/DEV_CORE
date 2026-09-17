---
name: feedback_sap-sync-pull-repo-ileri-ezme
description: "sap_sync_pull, repo canlıdan İLERİ olduğunda working-tree'yi sessizce bayat canlıyla eziyor — pull'dan ÖNCE çapa ölç"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f9acbee7-543c-4920-a414-8358ac408be3
---

`sap_sync_pull.py`, PULL-BEFORE-EDIT'in **"canlı daima ileri"** varsayımını taşır. Bu varsayım
**yanlış olabilir**: commit'lenmiş ama SAP'ye push edilmemiş iş varsa **repo ilerdedir** ve araç
working-tree'yi bayat canlı sürümle **sessizce EZER** — üstelik `[OK] canlıdan çekildi` der.

**Why:** 2026-08-02'de tek oturumda **3 kez** tetiklendi (`ZSD001_CL_ESLES`, `ZSD001_I_AMBTAK_T01`,
ve bir kez daha). Üçünde de iş **commit'liydi** → `git checkout HEAD --` ile geri alındı, kayıp olmadı.
**Commit'lenmemiş WIP olsaydı kayıp KALICI olurdu.** Sınıf: **geri alınamaz + sessiz**.
Aynı gün ikinci sessiz kusur: `--type func` → `"canlı obje yok (404)"` **ve `exit 0`**.
Bugünkü güvenlik ağı **dikkat**tir, mekanizma değil.

**How to apply:**
1. **Pull'dan ÖNCE bir çapa ölç.** Repoda olup canlıda olmaması gereken bir sembol seç, canlıda ara
   (`adt_grep_source` / `adt_get`). Örnek: canlı `O02`'de `gt_excl_esl` **0×**, repoda **5×** ⇒ repo
   ileri ⇒ **pull KOŞMA**, `--offline` damgala.
2. Pull koştuysan ve dosya beklenmedik şekilde değiştiyse: **`git diff` ile bak, `git checkout HEAD --`
   ile geri al.** "Araç çekti, demek ki canlı doğru" DEME.
3. Canlı sürümü **karşılaştırma için** almak istiyorsan `adt_get(include_source=True)` kullan —
   working-tree'ye yazmaz.
4. Bir objede drift bulursan **aynı commit'in diğer objelerini de tara**: push yarım kalmış olabilir.

Son-doğrulama: 2026-08-02 · Applies-to: SAP ADT projeleri (s4_private; araç core `scripts/`de)
İlgili: [[feedback_source-drift-pull-before-edit-model]] · [[feedback_arac-basarisizligini-zararsiz-sayma]] ·
[[project_zsd001-beyanname-eslesme]]

---
**Son-dogrulama:** 2026-08-02 (ders yazim tarihi — o gunden beri YENIDEN OLCULMEDI) · **Applies-to:** bu cekirdegi kullanan tum projeler

⚠ **ARAC IDDIASI** — bu ders *"bugun su arac/kapi boyle davraniyor"* der, yapisal bir olgu
degil. Arac surumu degismis olabilir: davranisa **dayanmadan once bir kez olc**. (Vaka: bir
kardes ders, dayandigi kusur duzeltildikten sonra 3 hafta bayat yasadi; tohuma alinmadan
once olculup elendi.)
