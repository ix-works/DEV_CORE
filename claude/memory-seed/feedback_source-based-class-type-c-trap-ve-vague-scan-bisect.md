---
name: feedback_source-based-class-type-c-trap-ve-vague-scan-bisect
description: "Source-based ABAP class'ta method-param TYPE c LENGTH n save-scan'i kırar (TYPE string kullan); vague OO_SOURCE_BASED hatada baseline+tek-tek-push bisect"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8c1257a6-fbd9-48f4-9ef0-5040be6f1540
---

ZSD001_CL_SO_MANAGER'a sipariş-notu metotları eklerken yaşanan uzun patinaj (2026-06-11). Üç ayrı ders:

**1) TYPE c LENGTH n method-param TUZAĞI (asıl suçlu):**
Source-based ABAP class'ta **METHOD parametresinde** `TYPE c LENGTH 100` → save reddedilir: `OO_SOURCE_BASED / ExceptionResourceScanDuringSaveFailure` (HTTP 400, **satır no YOK**). İlginç: aynı `TYPE c LENGTH 220` TYPES/struct component'inde sorunsuz çalışır — sadece method imzasında kırıyor. **Çözüm:** method param/exporting'de `TYPE string` veya DDIC data element kullan, generic `c LENGTH n` KULLANMA.

**2) Vague save-scan hatasında DOĞRU yöntem (patinajı engelleyen):**
`ResourceScanDuringSaveFailure` satır vermez → **tahmin etme/feature suçlama** (ben yanlışlıkla SAVE_TEXT'i suçladım, oysa o masumdu). Kullanıcının dayattığı disiplin: (a) lokali aktif SAP sürümüyle birebir aynı yap (`adt_get` source/main → diske yaz), (b) push → **temiz baseline doğrula**, (c) değişiklikleri **TEK TEK** ekle, her birinde push → kıran tam değişikliği bulursun. **Why:** lokal ABAP derleyici yok + hata satırsız; körlemesine bisect pahalı, baseline+atomik-adım kesin sonuç verir. **How to apply:** [[feedback_done-tam-kapsam-dogrula]] gibi — "uploaded/activated" mesajına GÜVENME; `adt_get` aktif source ile diff'le persist'i DOĞRULA (push_object "Source uploaded" yanıltıcı olabilir, activate değişmemiş sürümü aktive edebilir).

**3) RAP unmanaged static-action'da sipariş text YAZMA — PERSIST TUZAĞI (kritik):**
⚠️ Bu akışta **EML CREATE BY \_Text VE default SAVE_TEXT PERSIST ETMEZ** (runtime kanıtlı): EML → buffer'da OK (fc=0) ama RAP commit ayrı text-MODIFY'ı flush etmez; SAVE_TEXT default → subrc=0 ama text-memory COMMIT WORK ister, RAP tetiklemez → VA03/READ boş. **ÇÖZÜM: `SAVE_TEXT savemode_direct='X'`** (senkron direkt DB). Okuma: EML `READ BY \_Text` çalışır (aynı VBBK). EML _Text recipe syntax doğru + entity `use update` destekler ama persist etmez. Text ID 0001/Z006/Z007, object VBBK. **PROCES DERSİ: buffer-içi başarı (fc=0/subrc=0) ≠ PERSIST → read-back/VA03 ile DOĞRULA. Takılınca yaklaşım değiştirme (EML↔SAVE_TEXT 2 kez bailout yaptım); asıl sorun ortogonaldı (COMMIT) — runtime diag (REPORTED+subrc mesaja) ile root-cause bul.** [[feedback_done-tam-kapsam-dogrula]]
