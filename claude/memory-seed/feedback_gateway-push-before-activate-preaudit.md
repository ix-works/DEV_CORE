---
name: feedback_gateway-push-before-activate-preaudit
description: "gateway push_object class/interface'te push-before-activate canlı kernel-preaudit koşar; save-scan≠activation hata ayrımı"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 21262368-09b4-4420-bcf2-29943f39c4fb
---

Gateway `push_object` (sap_client.py) artık **class/interface** push'unda upload(inactive) SONRASI, activate ÖNCESİ **canlı kernel-preaudit** koşar → `valid:false` → AKTİVE ETMEZ, `syntax_precheck:failed` + `syntax_errors` döner. abaplint/run_review'in kaçırdığı **aktivasyon-only** kernel hataları (tanımsız değişken, tip-uyumsuz, released-CDS alan adı — BE-21..25/BE-51) + aktivasyon sahte-OK (BE-39) aktivasyondan ÖNCE, temiz structured hatayla yakalanır.

**Why:** abaplint statik katman kernel-only hataları görmüyor (repo abaplint syntax kapalı + DDIC yok); yalnız SAP kernel görür. Eskiden bu hatalar ancak aktivasyonda (sahte-OK riskiyle) ya da SE24'te çıkıyordu → saatler kaybı.

**How to apply:** Kanonik core'da (bug-checklist **BE-55/BE-56** + MODERN-SYNTAX not + guard kodu, DEV_CORE PR#31). **KRİTİK ayrım — iki hata sınıfı:**
- **Save-scan hataları** (inline `TYPE STANDARD TABLE OF` metot-imzası, string-template escape BE-47, METHODS param-sırası BE-48) → `OO_SOURCE_BASED 011`, **upload-anında** düşer (`source_uploaded:false`); guard'a GELMEZ, zaten push başarısız olur.
- **Aktivasyon-only hataları** (tanımsız değişken, tip-çözüm) → save-scan geçer (`source_uploaded:true`), guard tam burada `syntax_precheck:failed` verir.
- Kapsam yalnız class/interface (prog/fugr/**include** DIŞLANDI — standalone include preaudit FAKE, BE-46). SOFT fail (preaudit koşulamazsa aktivasyona devam).

İlgili: [[feedback_araci-basarisizligini-zararsiz-sayma]] · [[project_zsd001-teslimat-plani-edi-idoc]]
