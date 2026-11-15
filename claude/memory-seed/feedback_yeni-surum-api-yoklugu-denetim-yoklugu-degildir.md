---
name: feedback_yeni-surum-api-yoklugu-denetim-yoklugu-degildir
description: "Eski sürümde yeni denetim API'sinin (ör. CL_ABAP_TX, CC_STMT) bulunmaması 'eski sürümde denetim yok' demek değildir — eski sürümün kendi çalışma anı denetimini (SNAPT döküm tanımı) ayrıca ara"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Bir sürüm karşılaştırmasında "X sürümünde bu denetim yok" demeden önce yalnız yeni sürümün mekanizmasını (sınıf, denetim grubu, belge sayfası) değil, eski sürümün KENDİ çalışma anı korumasını da ara. SAP'de bunun en ucuz kanıtı `SNAPT` tablosudur (ERRID = döküm adı, LANGU = E): döküm metni yasak deyim listesini olduğu gibi verir.

**Why:** 2026-11-05'te bir S/4 1909 sistemi için "1909'da RAP işlem fazı denetimi yok" iddiası kuruldu. İddia, `CL_ABAP_TX`/`CC_STMT` için ölçülen 0 satıra dayanıyordu ve TS'e ve kullanıcıya bu şekilde yazıldı. Bug-gate `BEHAVIOR_ILLEGAL_STATEMENT` dökümünü buldu; döküm COMMIT, ROLLBACK, SUBMIT, CALL TRANSACTION, LEAVE, MESSAGE ve RAISE EXCEPTION çıkışını yasaklıyordu. İddia daraltıldı ve kullanıcıya düzeltme bildirildi. Ölçüm doğruydu; ondan çıkarılan sınıf iddiası fazla genişti.

**How to apply:** Bir sürümde yeteneğin bulunmadığını iddia ederken:
1. Yeni mekanizmanın yokluğunu ölç.
2. Eski sürümün döküm ve hata tanımlarını (SNAPT, T100) ara.
3. İddiayı yalnız ölçülen eksene daralt (ör. "faz bazlı sRFC denetimi yok").

İlgili: "bulunamadı ≠ yok", [[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]].

Son-doğrulama: 2026-11-05
Applies-to: SAP sürüm karşılaştırması (s4_private, ecc); genel: yetenek-yokluğu iddiaları
