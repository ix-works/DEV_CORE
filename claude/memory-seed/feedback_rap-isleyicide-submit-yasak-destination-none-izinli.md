---
name: feedback_rap-isleyicide-submit-yasak-destination-none-izinli
description: 7.58 RAP işleyicisinde SUBMIT/iş planlama yasak; ayrı oturumda iş planlamak için CALL FUNCTION … DESTINATION 'NONE' (modify fazında, SM59 kaydı gerekmez) — belgeden; çalışma anı ölçülmedi
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

RAP davranış işleyicisinde (action/modify fazında) `SUBMIT` ve iş planlama (`JOB_OPEN`/`JOB_CLOSE`'un dolaylı yaptığı SUBMIT dahil) 7.58'de **transactional context ihlalidir** ve çalışma zamanı hatası verir. Belgedeki çıkış yolu şudur: modify fazında **sRFC'ye izin verilir**. İşi planlayan kodu RFC'li bir FM'e koy ve `CALL FUNCTION '<FM>' DESTINATION 'NONE'` ile çağır. Bu çağrı ayrı bir oturum ve ayrı bir LUW açar, SM59 kaydı gerektirmez ve paket başka sistemlere taşındığında ek kurulum istemez. `save` fazında sRFC de yasaktır.

**Why:** 2026-11-06'daki bir TS doc-gate'inde BLOCKER bulundu: "Arka plan işini kur" eylemi işleyicide doğrudan iş planlıyordu. Kaynak: 7.58 ABAP belgesindeki `abapinvalid_stmts_in_rap_methods` tablosu (SUBMIT ✘; RFC modify fazında ✔, save fazında ✘). Davranış çalışma anında henüz ölçülmedi.

**How to apply:** Bir RAP eyleminden iş planlamak ya da rapor çalıştırmak gerekiyorsa iki yol var:
1. DESTINATION 'NONE' ile çağrılan FM. Çağıranın `S_RFC` yetkisi olmalıdır; bunu rol önerisine yaz.
2. Kuyruk satırı + olay (`BP_EVENT_RAISE`) + dağıtıcı iş.

Strict modda yasak deyim listesini hedef sürümün kendi belgesinden oku; daha yeni bir sürümün belgesi kanıt sayılmaz. İlgili: [[feedback_rap-validation-operation-trigger]].

Son-doğrulama: 2026-11-06 (belge) · Applies-to: s4_private 2023+ (BASIS 758), RAP managed/unmanaged strict(2)
