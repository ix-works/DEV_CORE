---
name: hook-negatif-test-exit0-iki-anlamli
description: "Hook negatif-testinde exit 0 iki anlamlıdır (serbest MI, parse-fail Mİ?) — boru harness'ı ortam-bağımlı; pozitif kontrol zorunlu"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 262fbb58-1a4d-43dd-b25c-186cd7a60340
---

Hook'u sentetik payload'la test ederken **exit 0 "serbest" demek DEĞİLDİR** — bozuk/parse
edilemeyen JSON da 0 döner (fail-safe) ve stderr SESSİZDİR. İki alet tuzağı aynı sahte
"bypass" okumasını üretir: elle yazılan `\\` kabuğa tek `\` iner (geçersiz JSON escape) ve
boru harness'ının güvenilirliği **ortam-bağımlıdır** (aynı payload iki ortamda zıt sonuç
verdi; PS 5.1 stderr'i UTF-16LE+BOM'a da çevirebilir).

**Why:** 2026-08-13'te guard "bypass edildi" diye okundu; guard sağlamdı, ölçüm aleti bozuktu.
Neredeyse yanlış bir infra-bulgu kaydı açılıyordu.

**How to apply:** Payload'daki Windows yollarını `/` ile yaz; dosyaya kaydet + `<` ile ver;
"serbest" hükmünden önce **bloklaması bilinen payload'la pozitif kontrol** koş ve blok
MESAJINI gör. Kanonik reçete: core `governance/infra-test-recipes.md` **B0b** (+ CLAUDE.core
§7 parantezi). İlgili: [[exit0-degil-cikti-kaniti]] · [[dogrulama-sezgileri-dort-kural]]

Son-doğrulama: 2026-08-13 · Applies-to: tüm profiller (hook/guard negatif-testi, Windows)
