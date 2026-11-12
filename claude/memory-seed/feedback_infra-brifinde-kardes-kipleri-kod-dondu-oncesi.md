---
name: feedback_infra-brifinde-kardes-kipleri-kod-dondu-oncesi
description: "Paylaşılan modül/validator değiştiren infra brifinde KOD DONDU öncesi kardeş fixture'ların TÜM mutasyon kiplerini (run_battery --kardes-tam) koşturmayı açıkça iste"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 661be744-bf24-44a1-a38a-999a39ca6fba
---

İnfra-expert'e ortak modül (ör. `ad_politikasi`) ya da birden çok validator değiştiren iş verirken brifte **"KOD DONDU öncesi `run_battery <ana> --kardes <değişen dosyaya bağlı fixture'lar> --kardes-tam --precommit`"** açıkça yazılır. `--kardes` tek başına kardeşlerin yalnız TABANINI koşar, kiplerini koşmaz; CI da koşucu başına yalnız ilk kipi koşar.

**Why:** DEV_CORE #402 (2026-11-08): ajan bataryayı `--kardes-tam`'sız koştu → değişen satıra çapalı bir kardeş kipi (`cds_curr --mutasyon-ad-harf`) KURULAMADI, iki kipin ilan kümesi bayat kaldı; yerelde görünmedi, CI kırmızıya döndü, bug-gate BLOCKER verdi ⇒ bir tam düzeltme + doğrulama turu (~1 saat). Kullanıcı süreyi sorguladı.

**How to apply:** Değişen dosyaya başvuran kipli fixture'ları spawn öncesi listele (kip_tara benzeri `git grep`), brifin araç bölümüne `--kardes-tam` komutunu tam haliyle yaz; KOD DONDU raporunda kip sayısını iste. Kanonik tarif: core `governance/infra-test-recipes.md` B97/B100 (`--kardes-tam` eklendi).
Son-doğrulama: 2026-11-08 · Applies-to: core infra turları (validator/ortak util değişiklikleri)
Bağlantı: [[feedback_paralel-infra-pr-ortak-dosya-rebase-sonrasi-tam-suit]] · [[feedback_brifinge-koydugun-yolu-once-kendin-kos]]
