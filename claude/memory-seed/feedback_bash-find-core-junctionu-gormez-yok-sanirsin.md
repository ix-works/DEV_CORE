---
name: feedback_bash-find-core-junctionu-gormez-yok-sanirsin
description: "Bash `find` Windows junction'ını (core/) traverse ETMEZ — `find . -name X` ve `find core -name X` core altındaki dosyayı BULAMAZ ve sessizce boş döner; 'YOK' sanırsın. Doğru araç PowerShell Get-ChildItem -Recurse."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e0774ea9-348e-4e2c-ae54-bd02ef91d832
---

**Kural:** `core/` altında bir dosyanın var olup olmadığını **Bash `find` ile ölçme**. `find` bu
makinede Windows **junction**'ını traverse etmez ve **hata vermeden boş döner** — bu, "yok" ile
ayırt edilemeyen bir çıktıdır. Doğru araç:

```powershell
Get-ChildItem "<PROJE-KOKU>\core\scripts" -Recurse -Filter "check_ui_odata_refs.py" | Select FullName
```

Doğrudan yol vererek `ls core/<tam/yol>` **çalışır** (junction'ın içine girmeyi değil, tek yolu
çözmeyi gerektirir) — tuzak yalnız **özyinelemeli aramada**.

**Why:** Ölçülmüş vaka 2026-09-02. `find . -name "check_ui_odata_refs.py"` ve
`find core -name ...` **ikisi de boş** döndü; ben de bir alt-ajana *"bu script YOK"* diye yazmaya
gidiyordum. Aynı anda bug-expert de `core/scripts/validators/check_ui_odata_refs.py` yolunu
deneyip `[Errno 2]` aldı. İki bağımsız "yok" sinyali vardı ve **ikisi de yanlıştı**: dosya
`core/scripts/check_ui_odata_refs.py`'de duruyordu (`validators/` altında değil), PowerShell
`Get-ChildItem -Recurse` ilk denemede buldu. Yanlış "YOK" kabul edilseydi bir alt-ajanın
**gerçekten koştuğu** kapı raporu "fabrikasyon" diye damgalanacaktı — yani hata, ölçüm hatasından
**suçlamaya** dönüşecekti.

**How to apply:**
1. `core/` altında **arama** yapacaksan PowerShell `Get-ChildItem -Recurse` kullan; Bash `find`
   sonucunu "yok" kanıtı sayma (`Grep` aracının `path=core/` kuralı D29 ile aynı sınıf, ama D29
   Grep içindir — `find` ayrı ve daha sinsi, çünkü **hiç uyarı vermez**).
2. Bir script'in **kanonik yolu ve kullanımı** için önce playbook'a bak, dizin tahminine değil:
   `core/playbook/ui-freestyle-odata-v2.md:212` `check_ui_odata_refs.py`'nin çağrı satırını
   birebir veriyordu. ⚠ O satırdaki `ERP/` **tarihsel** addır — K12 ile `SOURCE_CODES/` oldu.
3. Alt-ajan brifine script yolu yazarken **yolu ölç**, dizin adını hatırlamaya çalışma; yanlış
   yol ajanın turunu yakar ve sahte "YOK" bulgusu üretir (bu turda iki `SendMessage` düzeltmesi
   gerekti).

**Bağlam notu (ayrı, faydalı):** `check_ui_odata_refs.py` SRVB doğrulaması için **canlı `$metadata`
HTTP GET** yapar (`.conn_adt`) — `adt_get(object_type='srvb')` başarısız olduğunda o bir **araç
sınırıdır**, "servis yok" değildir; bu script doğru kanaldır.

İlgili: [[feedback_ajan-olumsuz-donusu-kanitla-sorgula]] · [[feedback_dogrulama-sezgileri-dort-kural]] ·
[[feedback_core-index-dala-bagli]] · [[feedback_metadata-alan-dogrulama-tip-kapsamli-olmali]]

---

📌 **TEKRAR 2026-09-08 (3. kez):** `find . -name "deploy_ui.py"` **boş** döndü; dosya
`core/scripts/deploy_ui.py`'de duruyordu. ⚠ Aynı körlük **`Grep` aracında da** var — D29'un
*"metodoloji araması DAİMA `path=core/` ile"* kuralı bunun arama-aracı yüzü; `find` yüzü budur.
Bir core script'i "yok" görünüyorsa **önce `core/` altına açıkça bak**, sonra yokluğa hükmet.
