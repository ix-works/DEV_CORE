---
name: test-yazmadan-once-acik-onay
description: "Uygulama testi (ABAP Unit/karakterizasyon dahil) yazmadan ÖNCE kullanıcıya sor, açık onay al — test işi uzatır; kullanıcı gerektiğinde kendisi ister"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 880f32a3-6ded-4fb3-bc19-5cfb127088b3
---

Uygulama testi yazmaya başlamadan önce kullanıcıya sor ve **açık onay** al — ABAP Unit, karakterizasyon testi, yeni ccau test metodu dahil. Alt-ajan brifine de "yeni test yazma (kullanıcı onayı yok)" maddesi konur.

**Why:** 2026-10-04'te bir paketin ATC P2 düzeltme turunda lider, kullanıcıya sormadan iki aşamalı karakterizasyon testi (5 yeni test, ~446 satır, ~16 dk ajan + gateway koşusu) yazdırdı. Kullanıcı: "benden açık onay almadan test yazma, test işi uzatıyor; komplex senaryo fazla olduğunda ben isterim. Bu uygulama için teste gerek yok, iç yazışma maili, yanlış olsa bile testte gözükür ve düzeltiriz."

**How to apply:** Davranışı korunması gereken refactor'da bile varsayılan = testsiz; doğrulama mevcut kontroller (mevcut testler yeşil kalır, önizleme/salt-okur karşılaştırma, kullanıcı testi). Test gerekli görünüyorsa önce maliyet+gerekçeyle SOR. Mevcut testleri koşmak (regresyon) onay gerektirmez; yalnız YENİ test yazmak gerektirir. Kritiklik değerlendirmesini kullanıcı yapar (iç yazışma ≠ kritik).

**Kapsam sınırı:** bu kural SAP **uygulama** testleri içindir (ABAP Unit, karakterizasyon, UI test). Çekirdeğin kendi altyapı değişikliklerindeki fixture/regresyon testleri (infra-fix prosedürü F3 üç-bağlam testi) bu kuralın DIŞINDADIR — orada test, teslimin kendisidir.
Son-doğrulama: 2026-10-04 · Applies-to: bu çekirdeği kullanan tüm projeler, SAP uygulama geliştirme (kullanıcı kararı 2026-11-12: tüm core kullanıcılarına)
