---
name: feedback_karar-verimliligi-asiri-kapi-yok
description: "Karar sorma disiplini — makul-default varken sorma/ilerle; gerçek karar gerekince tek tek + düz-dil açıkla; AskUserQuestion harness'i bloklar"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6b9195f9-e63c-4781-931d-b9672c867a85
---

Kullanıcının tekrar eden uyarıları: 2026-06-15 "kendini neden bloke ediyon, böyle verimli olmuyo"; 2026-06-18 iki kez AskUserQuestion reddi + "yine kendini bloke ettin", "ne bekliyon neden bekliyon". Aşırı onay kapısı + her küçük adımı teyide sunma + gereksiz re-teyit akışı yavaşlatıyor.

**İKİ KURAL (birbirini tamamlar):**

1. **Geri-alınabilir / makul-default olan → SORMA, ilerle.** En makul seçeneği SEÇ, YAP, tek satır "şöyle varsaydım, yanlışsa söyle" de. Alan yeri/isim/UI düzeni/commit yapısı/deploy kapsamı/açılış davranışı = sorma, uygula. Popup yığma, küçük soruları üst üste dizme.

2. **Gerçek karar gerektiğinde (geri-alınamaz + kullanıcı-tercihine-bağlı + makul-default-yok) → tek tek + açıklayarak sor.** Kuru option-listesi değil: (1) işin ne olduğunu iş/sade dille anlat, (2) neden seçim gerektiğini söyle, (3) her seçeneğin pratik sonucu + trade-off, (4) varsa öneri + gerekçe, (5) TEK karar sor. Birden çok gerçek karar varsa sırayla — biri bitince diğeri (çok-soru yığını şaşırtır).

**Why:** Sürekli kapı kullanıcıyı yorar + ajanı/takımı idle bırakır (lider beklerken herkes idle); AskUserQuestion harness'te forward progress'i BLOKLAR. Ama kullanıcı kararı *bilinçli* vermek istediğinde salt teknik özet yetersiz → o noktada açıklama derinliği şart. Denge = az kapı, ama açılan kapı kaliteli.

**How to apply:** ZORUNLU gate'ler kalır (tablo ALTER onayı, ADR0005 standart-obje yasakları, DTEL/append adı=kullanıcı, "done"=canlı teyit) — onlarda sor. Bunların DIŞINDA varsayımla ilerle. Yıkıcı silme / mimari çatallanma gibi gerçek kararda → yukarıdaki 5-adım açıklamayla TEK soru. İlgili: [[feedback_tek-soru-ve-bagimsiz-dokuman]] (bağımsız-tam döküman) · [[feedback_kararlari-once-topla-sonra-dispatch]] (gerçek kararları topla-tek-sor) · [[feedback_lider-bloke-olmama-background-dispatch]] (bloke=harness-zorunluluğu değil, yargı).
