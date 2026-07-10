---
name: feedback_api-call-ic-gateway-proxy
description: "RFC-dest kullanan TÜM API call'larda SM59 yerine ZBC001 helper + /iwfnd/cl_sutil_client_proxy iç gateway mimarisi (proje standardı)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9032e66e-45f9-47c0-af9b-23b771ffe0a7
---

RFC Destination / SM59 (`create_by_destination`, `create_by_url`) ile yapılan **TÜM** SAP-içi OData API call işlemlerinde artık bu mimari kullanılacak (kullanıcı kuralı, 2026-06-08):

- **Token+URL:** paylaşılan `ZBC001_CL_GET_TOKEN` (sahibi başka bir geliştirici, BC paketi). `get_token(iv_method)` → CSRF; `get_host(iv_method, iv_token)` → tam URL. **Bu sınıfa DOKUNMA — sadece kullan** (başka geliştiricinin shared objesi).
- **Çağrı motoru:** `/iwfnd/cl_sutil_client_proxy=>get_instance( )->web_request( )` — SAP Gateway iç loopback proxy. Harici HTTP / RFC dest / kimlik **yok**.
- **POST'u kendi paketin altında** yaz (ZBC001'ye genel POST eklenmez); response body parse için `cl_abap_conv_codepage=>create_in( )->convert( ev_response_body )`. Çalışan tam örnek: `ZQM001_CL_GET_TOKEN` (get_token + save_userdecision).
- `iv_method` formatı: `'<SERVICE_SRV>/<Entity>'` (GET_HOST `/sap/opu/odata/sap/` prefix'ini ekler).

**Why:** Eski SM59 deseni host'u config'e taşısa da `sap-client` kodda hardcoded ('100') kalıyordu → client (QA/PRD) değişiminde kırılıyordu. İç proxy: host=`TH_GET_VIRT_HOST_DATA`, client=`sy-mandt` (runtime) → sistem & client bağımsız, kimliksiz.

**How to apply:** Yeni API call yazarken veya RFC-dest kullanan mevcut kodu görünce bu mimariye çevir. İlk uygulama: `ZSD001_CL_SO_MANAGER->simulate_pricing` — **CANLI DOĞRULANDI 2026-06-08** (RAP behavior-handler içinde proxy sorunsuz, dump yok; eski cl_http_client comm-hatası MESSAGE→dump endişesi geçersiz çıktı).

**DİL TUZAĞI (kritik):** `ZBC001.get_host` URL'e yalnızca `sap-client` koyar, `sap-language` KOYMAZ. Eski SM59 kodu `sap-language: TR` header'ı veriyordu; bu mimaride vermezsen servis EN'de işler → UoM/text lookup patlar (`S4 HTTP 400: Unit ADT is not created in language EN`). ÇÖZÜM: POST request_uri = `|{ lo_api->get_host( iv_method = lc_method ) }&sap-language=TR|`.

Envanter (2026-06-08 repo taraması) + durum: (1) `ZSD001_CL_SO_MANAGER->simulate_pricing` ✅ migrate+canlı; (2) `ZSD000_CL_CUSTOMER_MAINTAIN` ✅ migrate+CANLI OK (4 HTTP method + build_url; kullanıcı BP/customer-maintain testi geçti 2026-06-08); (3) `ZSD001_CL_SO_MANAGER` (create_by_url, legacy prod) — kullanıcı kararıyla DOKUNULMADI. Klasik `CALL FUNCTION..DESTINATION` (network RFC) repo'da YOK. Standart dokümante edildi: **playbook/adt-rap.md §34 (kanonik) + §34-LEGACY (SM59 ikincil) + standards/02-coding-backend.md (BACKEND—SAP-içi API çağrısı kuralı)**. ZBC001 objesi repoda: ERP/ABAP/ZBC001_CLC/. İlgili: [[project_zsd001-rap-fittings]] · [[feedback_mcp-post-shell-en-master-lang]]
