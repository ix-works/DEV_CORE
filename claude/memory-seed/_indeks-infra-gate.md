---
name: _indeks-infra-gate
description: İnfra, gate ve dosya yetkisi derslerinin tam indeksi
metadata: 
  node_type: memory
  type: reference
---

# İnfra · gate · dosya yetkisi — tohum indeksi

> Hook/validator/gate davranışı ve infra değişiklik disiplini. Bu dosya `MEMORY.md`'den link'lenir; dersler burada yaşar.

**4 ders.**

- [Ad sayan gate elenen adayi sayar](feedback_ad-sayan-gate-elenen-adayi-sayar.md) — Onay listesinde ham token deseniyle ad sayan bir gate, ELENEN adayları da sayar — sayı şişer
- [Hook dosya yolu windows bicimi ister](feedback_hook-dosya-yolu-windows-bicimi-ister.md) — Bash tool'undan çağrılan git/gh komutlarında -F/--file argümanı POSIX yol (/c/...) alırsa Python hook'u dosyayı OKUYAMAZ ve FAIL-CLOSED reddeder — Windows yolu (C:/...) ver
- ⭐ [Tuketici klonunda core degisikligi proseduru](feedback_tuketici-klonunda-core-degisikligi-prosedur.md) — upstream'e yazamayan kurulumda core'u düzeltme isteği: DUR → kurulum mu çekirdek mi ölç → fork+PR ya da Issue, kanıt formatıyla
- ⭐ [Cekirdek guncellemesi proseduru vardir](feedback_cekirdek-guncellemesi-proseduru-vardir.md) — "core güncelle" pull değildir: team_setup zinciri + overlay kapısı + makine-lokal yüzeyler

<!-- makine-okunur erişilebilirlik çapası (C-MEM-01): indeks bütünlüğü kapısı
     cift-koseli-parantez linki arar, markdown link saymaz. Liste yukarıdakiyle AYNI olmalı. -->
[[feedback_ad-sayan-gate-elenen-adayi-sayar]] · [[feedback_hook-dosya-yolu-windows-bicimi-ister]] · [[feedback_tuketici-klonunda-core-degisikligi-prosedur]] · [[feedback_cekirdek-guncellemesi-proseduru-vardir]]
