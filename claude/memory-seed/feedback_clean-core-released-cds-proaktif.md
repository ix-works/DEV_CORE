---
name: feedback_clean-core-released-cds-proaktif
description: "YENİ CDS/RAP kodu yazmadan ÖNCE released CDS tercih et (MARA değil I_Product), released-WARNING'i sessiz geçme; mevcut programlardaki ham tablo kullanımı muaftır (proje politikası aksini demiyorsa) — iş kalemi açılmaz, migrasyon önerilmez"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d6295d2a-8529-437b-ad66-d0d6ec8aebe0
---

CDS/RAP'te standart tablo okuyacağın zaman, **kod yazmaya başlamadan ÖNCE** released CDS successor'ını hatırla/kontrol et: `from mara` değil `from I_Product`. Otoriter harita: `governance/reference/released_successors.json` (SAP resmi PCE JSON'dan; MARA→I_Product+4, VBAP→I_SalesDocumentItem, LIPS→I_DeliveryDocumentItem...). `check_released_objects.py` reviewer'da WARNING verir ama **WARNING geçiştirilebilir** → ATC no-suppress disiplini gibi davran: ya released'a çevir, ya da bilinçli tablo kullanıyorsan **gerekçeni kullanıcıya bildir**. Sessiz pass YOK.

**Why:** Post-write WARNING reaktif; davranışı değiştirmesi için kuralı yazımdan ÖNCE içselleştirmem gerek. Clean Core Level A tercihi (ADR 0005-B READ'i yasaklamaz ama released CDS yeğlenir). Kullanıcı: "warning verdiğin için geçebilir ve yine MARA kullanmaya devam edebilirsin; en azından farkında olmalısın, hatta yazmadan önce hatırlamalısın."

**⚠GEVŞETME (kullanıcı onaylı 2026-11-12 — tüm core kullanıcıları): proaktif geçiş yalnız YENİ kod; mevcut programlar muaf.**
Kaynak kullanıcı kararı (2026-08-14, bir projede): *"Önceden yazılan programlarda bu değişikliği
yapmayacağımızı zaten kabul etmiştik. Yenilerde buna dikkat ederek yazıyoruz zaten. O nedenle bu eski
yazılmış programlardaki KNA1 vs. tablo kullanımı **bir bulgu olmamalı**."* 2026-11-12'de kullanıcı bu
kapsamın tohuma (tüm core kullanıcılarına) girmesini onayladı.

⇒ Mevcut/eski programlarda ham `KNA1`/`KNVV`/`KNVP`/`TVKO` vb. kullanımı **KABUL EDİLMİŞ
durumdur**; ne ATC prio-1 ne reviewer WARNING üzerinden **iş kalemi açılır**. Bu bulgular
envanterdir, borç değil. Released-CDS disiplini **yazılmakta olan** koda uygulanır.
⛔ Migrasyon **önerme**; kullanıcı özellikle istemedikçe gündeme getirme.
📐 **Kapsam (çekirdekle hizalı):** bu muafiyet **varsayılandır**; çekirdek CDS-DCL-02 / BE-68 gereği
migrasyon bir **proje politikası** kararıdır ⇒ projenin clean-core politikası (ör. `project.yaml`
`cleancore_policy: strict` ya da yazılı proje kararı) mevcut kodun da taşınmasını istiyorsa o geçerlidir.
Politika bunu söylemiyorsa bu kayıt uygulanır. ATC P1 kuralıyla ilişki: kardeş derste istisna satırı
([[feedback_atc-priority-1-zorunlu]] "İstisna — clean-core muafiyeti").

**Vaka (2026-08-14):** bir sipariş yönetimi sınıfında ATC 13 prio-1 (hepsi KNVV/KNA1/KNVP,
Note 0003067314) görüldü ve lider bunu ertelenmiş-iş listesine **"yapılacak"** diye yazdı —
yanlıştı, kullanıcı düzeltti. **Kök sebep: bu kayıt yarım yazılmıştı** — proaktif yarısı
("yazmadan önce released tercih et") vardı, muafiyet yarısı **hiçbir yerde yoktu** (grep = 0).
📌 **Ders: yarım yazılmış kural, yazılmamış kuraldan tehlikelidir** — var sanılır, eksik yarısı
her turda yeniden keşfedilir ve arada yanlış iş üretir.

**Yine de geçerli olan:** mevcut bir programa **yeni** kod eklerken o yeni kod released tercih
eder; ve teknik bir gerilim varsa (ör. halef `#CHECK` taşıyor ⇒ sessiz DCL reddi riski) bu,
migrasyona karşı **ek** bir sebeptir, tek başına sebep değil.

> **📌 KANONİK YER ÇEKİRDEK.** Bu kaydın hem teknik hem kapsam yarısı çekirdektedir — burası
> yalnız hatırlatıcıdır:
> · **`core/playbook/adt-cds.md` CDS-DCL-02** — released halefe geçiş karar kuralı (halefin
>   `authorizationCheck`'ini CANLI oku; `#CHECK` + guard ⇒ geçme, çünkü ham tablo DCL taşımaz,
>   halef taşır ⇒ 0 satır **fail-open**)
> · **checklist BE-68** — reviewer bunu kendi görür; "mevcut kodda ham tablo TEK BAŞINA bulgu
>   DEĞİLDİR" şerhi orada yazılı (yanlış-pozitif kalkanı)
> · sessiz-red sınıfının tamamı: **PATTERN #32** + **CDS-DCL-01** + **BE-67**
> Çelişki çıkarsa **çekirdek kazanır**; burayı güncelle.

**How to apply:** CDS/RAP işine başlarken `released_successors.json`'a bak (skill TETİKLEMELİ YÜKLEME CDS/RAP satırı + checklist C-CDS-FROM-04 / C-RAP-REL-01 hatırlatır). Tüm-tip released-API (class/FM) için SAP yerel ATC "Usage of APIs" otoriter. Dil-versiyonu/no-classic Clean Core aileleri bize uygulanmaz (dual-track on-prem). Bkz. [[feedback_atc-priority-1-zorunlu]] (aynı sessiz-pass disiplini).

**KULLANICI "MARM/std tablo kullan" DESE BİLE released successor varsa ONU kullan (2026-06-12, ZSD001 PAK):** Kullanıcı tüm alternatif CDS'leri bilemeyebilir; "MARM kullan" demesi **veriyi** kasteder, released eşdeğerini YASAKLAMAZ. Reviewer/`released_successors.json` bir successor öneriyorsa (MARM→I_ProductUnitsOfMeasure gibi) released'ı kullan. Kullanıcının sözü: "ben marm derim ama sistem zaten biliyor ve I_PRODUCTUNITSOFMEASURE kullan diyor; bu kullanmana engel olmamalı." Sadece released gerçekten işi yapamıyorsa (eksik alan vb.) std tabloya düş + gerekçeyi bildir. **Operasyonel tuzak:** released UoM çevrim alanları (I_ProductUnitsOfMeasure.QuantityNumerator=umrez / QuantityDenominator=umren) `@Semantics.quantity` (birim-referanslı) → aritmetik/CASE'te doğrudan kullanınca "Elements with required UNIT-reference are not supported" aktivasyon hatası; önce `cast( ... as abap.dec(n,m) )` ile birim semantiğini sıyır.

Son-doğrulama: 2026-11-12 (kapsam: muafiyet varsayılan, proje politikası üstün) · Applies-to: s4_private/s4_public/btp_abap — CDS/RAP/ABAP okuma kodu yazan tüm projeler
