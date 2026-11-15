---
name: feedback_ui5-mockserver-batch-etag-iki-nokta-keser
description: "UI5 MockServer $batch ayrıştırıcısı başlık değerini ':' ile böler — ETag ':' içerirse If-Match kesilir, sahte 412 çıkar"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

UI5 MockServer, $batch içindeki istek başlıklarını ':' karakterinden böler. ETag değeri ':' içeriyorsa (ör. `W/"2026-11-08T12:00:00"`) If-Match başlığı kesilmiş olarak iletilir ve mock'un ETag denetimi **sahte bir 412** verir. Mock'ta ETag'i ':' içermeyen bir biçimde üret (ör. yalnız rakamlardan oluşan bir damga).

**Why:** Bir SD paketinin UI uyum turunda (2026-11-08) If-Match/428/412 testi bu yüzden yanlış bir kırmızı verdi. Kusur UI kodunda değil mock ayrıştırıcısındaydı; bu davranış gerçek Gateway'in davranışını yansıtmaz.
**How to apply:** Mock'a ETag/If-Match eklerken bu sınırı göz önünde tut. Mock'ta 412 görünce önce başlığın kesilip kesilmediğine bak. Aynı turdan iki yan not: Git Bash'te `kill <MSYS PID>` Windows sunucu sürecini durdurmaz, `taskkill //PID <WinPID> //F` kullan (bkz. [[feedback_powershell-commandline-filtresi-kendi-kabugunu-yakalar]]). `rg`'ye yol verilmezse stdin'i bekler ve takılır.

Son-doğrulama: 2026-11-08 (tek vaka, mock sürümü ölçülmedi)
Applies-to: freestyle UI5 + OData V2 MockServer yerel testleri
