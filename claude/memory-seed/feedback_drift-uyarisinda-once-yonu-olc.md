---
name: feedback_drift-uyarisinda-once-yonu-olc
description: "X şablondan/kanonikten SAPMIŞ" uyarısı görünce refleksle yenileme — önce YÖNÜ ölç; sapan taraf ileride olabilir ve "yenile" nasihati aktif bir korumayı sessizce geri alabilir
metadata:
  type: feedback
---

Bir sağlık kontrolü *"X şablondan/kanonikten SAPMIŞ"* dediğinde refleks **"kanonikten yenile"**dir.
⛔ Önce **farkın YÖNÜNÜ ölç**: sapan kopya **geride** mi, yoksa **ileride** mi? Kanonik olan
taraf, en güncel olan taraf **değildir** — biri düzeltilip diğerine işlenmemiş olabilir.

**Why:** 2026-08-22, `session_start` D7 denetimi projenin `scripts/hook_shim.py`'sini
*"template'ten SAPMIŞ"* diye işaretliyordu. Ölçüm: fark **TEK satırdı** ve **proje İLERİDEYDİ** —
`infra_write_guard` 20.08'de projeye eklenmiş, CORE şablonuna eklenmemişti. Nasihat uygulansaydı
guard **sessizce fail-open** olacaktı: junction kırıkken (yani korumanın en çok gerektiği anda)
infra yazımı serbest kalırdı. ⇒ **Drift uyarısının kendisi bir regresyon reçetesiydi.**

⭐ İkinci ders aynı vakadan: *"kapandı"* iddiası **kapının ÖLÇTÜĞÜ ölçütle** doğrulanır.
Ben `_FAIL_CLOSED` **satırının** eşitliğini ölçüp *"D7 kapandı"* dedim; oysa D7 **tam-dosya
SHA** kıyaslıyor ve şablona eklediğim 7 satırlık gerekçe yorumu SHA'yı ayırıyordu ⇒ uyarı
merge sonrası **devam edecekti**. Kapı yakaladı. *Ölçüt doğruydu, kapsamı eksikti* — bu evde
adı konmuş bir sınıf ([[kontrolun-kapsami-is-akisinin-seklinE-bagli]]).

**How to apply:**
- Drift uyarısında sıra: ① iki dosyayı **diff'le** ② farkın **hangi tarafın lehine** olduğunu
  belirle ③ ileri olan tarafı **kaynak** kabul et ④ sonra senkronla.
- Bir kopya güvenlik/koruma satırı taşıyorsa (`_FAIL_CLOSED`, allow/deny listesi, eşik) —
  yenileme o satırı **kaldırıyor mu** diye özellikle bak.
- Senkronu bitirdikten sonra **kapının kendi ölçütüyle** doğrula (SHA kıyaslıyorsa SHA'yı
  karşılaştır, satır değil). Komşu bir ölçütle *"kapandı"* deme.
- ⚠ Gerekçe/yorum eklemek de dosyayı değiştirir: tam-dosya hash kıyaslayan bir kontrolde
  **yorum bile drift'tir** ⇒ gerekçeyi changelog'a yaz, dosyayı davranış satırıyla sınırla.

İlgili: [[template-drift-crlf-inflation]] · [[sonucu-olc-uygulamayi-degil]] ·
[[exit0-degil-cikti-kaniti]] · [[yesil-sinyalin-kapsamini-sor]]
