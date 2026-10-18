---
name: feedback_cl-bcs-set-message-subject-uzun-konu-canli-dogrulandi
description: "Mail konusu 50 karakteri aşacaksa CL_BCS `set_message_subject` — canlıda 95 kr + Türkçe/en-dash birebir (S/4 2025); SO_DOCUMENT_SEND_API1 / create_document i_subject CHAR50 keser"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 880f32a3-6ded-4fb3-bc19-5cfb127088b3
  modified: 2026-10-03T21:14:53.894Z
---

`SO_DOCUMENT_SEND_API1` (`sodocchgi1-obj_descr`) ve `cl_document_bcs=>create_document( i_subject )` konuyu **CHAR50**'de keser. Uzun konu gerekiyorsa: `lo_req->set_message_subject( ip_subject = <string> )` (CL_BCS send request). Ek adı için `add_attachment( i_attachment_header = VALUE soli_tab( ( line = |&SO_FILENAME=<ad>| ) ) )`.

**Why:** Canlı ölçüm 2026-10-03 (S/4 private 2025, DEV): `BCST_SR.SUBJECT` = 95 karakterlik konu, `– İ Ş` bozulmadan saklandı. core `playbook/howto-abap-email.md` §7 CL_BCS'i "canlı-doğrulanmadı" diye anıyor ve §4 "konuda Ş/İ codepage riski → ASCII tut" diyor — bu yolda risk ölçülmedi/gözlenmedi. (2026-10-04: gönderen olarak yetkili bir no-reply adresi verildiğinde DEV'den dış alıcıya ulaştı.)

**How to apply:** Yeni mail işinde konu >50 ya da Türkçe karakterli olacaksa CL_BCS + `set_message_subject` seç; RAP içinden gönderimde COMMIT için ayrı LUW (RFC FM `DESTINATION 'NONE'`, BE-26). **Terfi adayı:** core `howto-abap-email.md` §4/§7'ye "canlı doğrulandı" notu (çekirdek PR'ı ayrı iş).

Son-doğrulama: 2026-10-03 · Applies-to: s4_private 2025, ABAP mail (CL_BCS)
