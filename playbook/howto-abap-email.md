---
applies_to: [ecc, s4_private, s4_public]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-07-15
status: active
---

# ABAP'ten E-posta Gönderme — HTML gövde (+ ek-dosya) · `SO_DOCUMENT_SEND_API1`

ABAP program/JOB'undan **kurumsal HTML mail** (opsiyonel ek-dosya) göndermenin kanonik yolu +
**tekrar eden tuzaklar**. Bu playbook'un her kuralı CANLI yaşanmış bir bug'dan doğdu.
**Yeni mail yazmadan §6 checklist'i oku.**

## 0. Kanonik yol + emsal desenler

- **FM:** `SO_DOCUMENT_SEND_API1` — `commit_work = abap_true`; background-uyumlu (JOB'da çalışır).
- **İki emsal desen (çalışan):**
  - **FORM-tabanlı** klasik mail include (`ZSD001_I_<PRG>_F01` gibi): 255-char `html_add` + sender=`sy-uname`.
  - **Class-tabanlı** worker (`ZCL_SD001_MAIL_PROCESSOR` gibi): inline-style hizalı tablo + `html_add` chunk +
    başarı/hata ayrımı + ABAP-Unit test-edilebilir. Uzun/tekrarlı mantık için tercih et.
- ⚠ **Anti-pattern:** geniş (8+ kolon) tabloyu doğrudan gövdeye basan eski mail'ler — §3.1/§3.2/§3.4 kuralları
  tam bu bug'lardan çıktı (bkz. tuzaklar).

## 1. Gönderen (sender) — ASLA sabit kullanıcı

```abap
sender_address      = CONV soextreci1-receiver( sy-uname ).
sender_address_type = 'B'.   " B = SAP internal user (sy-uname)
```
- ⛔ **Sabit kullanıcı adı GÖMME** (`CONSTANTS gc_sender ... VALUE '<SAP_USER>'`). JOB'u kim koşarsa ondan gitmeli.
- ⛔ **`type='U'` (SMTP) + değere SAP kullanıcı-adı** verme — tip/değer uyumsuz (canlı bug: `type='U'` ama değer
  bir SAP user-id idi → gönderen bozuk). SAP user → `'B'`; gerçek SMTP adresi → `'U'`.

## 2. Alıcılar (`somlreci1`) — dinamik, pasif-hariç

```abap
APPEND VALUE #( receiver   = <email>          rec_type = 'U'   " U = SMTP adresi
                copy       = COND #( WHEN typ = 'CC'  THEN abap_true )
                blind_copy = COND #( WHEN typ = 'BCC' THEN abap_true ) ) TO lt_reci.
```
- Alıcılar **DİNAMİK bir Z bakım tablosundan** gelir (muhattap/grup bazlı; ör. `ZSD001_T_MAIL`) — koda gömülü adres YOK.
- **Aktif/pasif deseni:** `WHERE pasif <> 'X'` (boş=aktif; yeni satır default aktif). Alıcı yoksa o kaydı ATLA (job-log), akışı kesme.

## 3. HTML gövde — 5 TUZAK (hepsi canlı-yaşandı)

### 3.1 ⛔ `<head><style>` class-CSS YOK → INLINE style ŞART
Mail istemcileri (**Outlook / Gmail / SAP mail viewer**) `<head><style>` içindeki **class-CSS'i YOK SAYAR**
→ kenarlık/renk/genişlik/hizalama hiç uygulanmaz → etiket+değer **bitişik** render olur, tablolar hizasız.
**FIX:** stili doğrudan elemana `style="..."` ile ver (class değil):
```abap
|<td style="width:160px;background:#f5faff;border:1px solid #ccc;padding:5px 8px;color:#555;">{ label }</td>|
```

### 3.2 ⛔ `html_add` tek-atama SESSİZCE KESER → 255-char CHUNK ŞART
`solisti1-line` = **CHAR255**. `ls_line-line = iv_line` (tek atama) 255'i aşan string'i **sessizce keser**
→ tag **ortadan kopar** → bir sonraki satırın `<tr>`'i kalan `</` parçasına bitişir → **`</<tr>`** gibi
bozuk tag → tüm tablo bozulur. (15-kolonlu bir satır ~300+ char → kaçınılmaz.)
**FIX (kanonik):** WHILE + offset ile 255'lik parçalara böl:
```abap
FORM html_add USING iv_line TYPE string CHANGING ct TYPE <soli_tab>.
  DATA(lv_len) = strlen( iv_line ). DATA lv_off TYPE i.
  IF lv_len = 0. APPEND VALUE #( ) TO ct. RETURN. ENDIF.
  WHILE lv_off < lv_len.
    DATA(lv_take) = COND i( WHEN lv_len - lv_off > 255 THEN 255 ELSE lv_len - lv_off ).
    APPEND VALUE #( line = iv_line+lv_off(lv_take) ) TO ct.
    lv_off = lv_off + lv_take.
  ENDWHILE.
ENDFORM.
```
> ⚠ Kod yorumu "bu FORM otomatik böler" DİYE yazılı olsa bile GERÇEKTE bölmüyor olabilir — kaynağı doğrula.
> `SO_DOCUMENT_SEND_API1` HTM gövdeyi ara-satır sokmadan **yeniden birleştirir** → 255-bölme render'ı bozmaz.

### 3.3 Hizalı tablo = `<table><td>` (div/span/class DEĞİL)
Etiket|değer hizası için **2-kolon `<table>`** + **sabit etiket-kolon genişliği** + inline kenarlık/padding.
`<div class="kv"><span class="k">` deseni §3.1 yüzünden hizasız çıkar.

### 3.4 Sayı formatı — locale güvenli, birim-doğru
- **ADET / adet (piece):** TAM SAYI → `|{ val DECIMALS = 0 }|`. Ondalık gösterme (canlı bug: 10 adet → "10.000").
- **Miktar / KG / tutar:** ondalıklı → `|{ val DECIMALS = 3 }|` (alanın decimal'ine göre).
- ⛔ **`WRITE ... TO` KULLANMA** — locale ondalık-ayracını bozar. String-template default'u **kanonik**
  (nokta ondalık, gruplamasız) = locale-bağımsız. [[feedback_abap-decimal-odata-serialize-locale]]

### 3.5 Türkçe karakter (encoding)
- Gövde `<meta http-equiv="Content-Type" content="text/html;charset=utf-8">` + `contents_txt` + sender type `'B'`
  → gövde-içi Türkçe **genelde çalışır** (ör. "Sn. İlgili", "Müşteri", "gönderilmiştir").
- ⚠ **RİSK:** gönderen SU01 tam-adı + malzeme adı (`maktx`) gibi metinler SAPconnect **codepage** dönüşümünde
  bozulabilir (Türkçe ı/ş → "?"). **Tam UTF-8 garanti** gerekiyorsa → veriyi **ek-dosya olarak BINARY UTF-8** üret (§5).

## 4. Konu (subject / `sodocchgi1-obj_descr`)
- `obj_descr` = **CHAR50**. En kritik bilgi **BAŞTA**; taşarsa `obj_descr = COND #( WHEN strlen( s ) > 50 THEN s(50) ELSE s )`.
- Durum ibaresini (BAŞARILI/HATALI vb.) **öne** koy (inbox'ta ilk bakışta ayırt).
- ⚠ Türkçe **Ş/İ** konu alanında codepage riski taşıyabilir → kritik değilse konuyu **ASCII** tut; tam Türkçe'yi gövdeye bırak.
- ⚠ **Sabit-genişlik alan + `ALPHA = OUT` tuzağı:** CHAR16 (belge no vb.) alanlarda `|{ f ALPHA = OUT }|`
  alan genişliğini koruyup **trailing-space** üretir → konuda boşluk + 50-aşım + kırpma. `condense( |{ f ALPHA = OUT }| )` ile temizle.

## 5. EK-DOSYA (attachment) — kısa gövde + dosya
**Ne zaman:** **8+ kolonlu / geniş tablo** çoğu inbox'ta gövdede taşar (§3 tuzakları da) → **kısa HTML gövde +
ek-dosya**. Operasyonel/işlenecek veri (filtre/sırala) → **Excel**; sabit/resmî arşiv → **PDF**.

### 5.1 Excel eki — yöntem seçimi (Türkçe-güvenlik sırasına göre)
1. **abap2xlsx varsa (`ZCL_EXCEL`, açık-kaynak, standart DEĞİL):** gerçek `.xlsx` → **en temiz** (uyarısız, tam UTF-8).
   `NEW zcl_excel_writer_2007( )->write_file( lo_excel )` → xstring → CL_BCS `add_attachment` (§7). ⚠ önce `ZCL_EXCEL`
   sistemde KURULU mu doğrula; değilse kurulum Basis onayı ister (kurma).
2. **abap2xlsx YOKSA → MHTML (`.xls`-as-HTML, UTF-8+BOM) — CANLI-KANITLI (2026-07):** batch-güvenli (saf string,
   GUI/OLE yok), Türkçe BOM ile korunur, sayı-tipi hücre-bazında **locale-bağımsız** verilebilir. **Varsayılan seç.**
3. **CSV/TXT + UTF-8 BOM:** en basit; ⚠ düz `string_to_soli` YETMEZ (Excel Türkçe'yi ANSI sanar) → `cl_abap_conv_codepage`/
   `cl_abap_codepage=>convert_to` + başa `cl_abap_char_utilities=>byte_order_mark_utf8` (BOM); `;` ayraç.

### 5.2 MHTML `.xls` — kanonik desen (canlı-kanıtlı)
Excel'in okuduğu MHTML tablo: `mso-number-format` (head'de `<style>` — **MHTML'de Excel bunu OKUR**, §3.1 e-posta
kuralının İSTİSNASI) + hücre-bazında `x:num`/`x:str` (çift-emniyet):
```html
<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel">
<head><meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<style> .txt{mso-number-format:"\@";}  .int{mso-number-format:"0";}  .dec{mso-number-format:"0\.000";} </style></head>
<body><table>
  <tr><td class="txt" x:str="10000123">10000123</td>   <!-- metin: baştaki sıfır korunur -->
      <td class="int" x:num="492">492</td>              <!-- ADET: tam sayı -->
      <td class="dec" x:num="3.000">3.000</td></tr>     <!-- KG: 3-ondalık -->
</table></body></html>
```
- **HTML-escape ŞART** (`& < > "`): özellikle malzeme adındaki **inç `"`** (`3/4"`) → `&quot;` (aksi halde `x:str` attribute'unu kırar). `&` önce escape et (çift-escape yok).
- Sayıyı string-template ile bas: ADET `|{ v DECIMALS = 0 }|`, KG `|{ v DECIMALS = 3 }|` — kanonik (nokta ondalık, §3.4).
- **UTF-8 BOM:** gövdenin başına `EFBBBF` (xstring) ekle: `CONCATENATE lv_bom lv_body_x IN BYTE MODE` (Türkçe için ŞART, yoksa Excel ANSI sanar).

### 5.3 Ekleme — `SO_DOCUMENT_SEND_API1` `packing_list` 2. entry (canlı-kanıtlı)
```abap
DATA(lv_xstr) = <bom + mhtml string → xstring>.        " cl_abap_conv_codepage=>create_out( )->convert( )
DATA(lt_hex)  = cl_bcs_convert=>xstring_to_solix( lv_xstr ).
" object_header: dosya adı
APPEND |&SO_FILENAME=Stok_Listesi_{ sy-datum }.xls| TO lt_objhead.
" packing_list — 1) HTM gövde, 2) XLS ek
APPEND VALUE #( transf_bin = space     head_num = 0  body_start = 1  body_num = lv_bodyln
                doc_type = 'HTM' ) TO lt_pack.
APPEND VALUE #( transf_bin = abap_true head_start = 1 head_num = 1  body_start = 1  body_num = lines( lt_hex )
                doc_size = xstrlen( lv_xstr ) doc_type = 'XLS'      " ⚠ doc_type CHAR3 → '.xlsx' sığmaz, 'XLS'
                obj_descr = 'Stok Listesi' ) TO lt_pack.
CALL FUNCTION 'SO_DOCUMENT_SEND_API1'
  EXPORTING document_data = ls_hdr  commit_work = abap_true       " ⛔ COMMIT ŞART
           sender_address = CONV #( sy-uname ) sender_address_type = 'B'
  TABLES packing_list = lt_pack  object_header = lt_objhead
         contents_txt = lt_body  contents_hex = lt_hex  receivers = lt_reci.
```
- ⚠ **`doc_type` = CHAR3** → gerçek `.xlsx` (4 harf) temiz sığmaz; MHTML'de `'XLS'` + dosya adı `.xls` kullan.
- ⚠ **`doc_size = xstrlen( )`** (gerçek bayt) ver → son SOLIX satırının padding'i trimlenir (yoksa ek sonunda çöp bayt).
- ⛔ **`commit_work = abap_true`** yoksa "gönderildi görünür ama hiç çıkmaz" (en sık hata).

## 7. Modern alternatif — `CL_BCS` (yeni işler için önerilir; araştırma, canlı-doğrulanmadı)
`SO_DOCUMENT_SEND_API1` çalışır/desteklenir ama **CL_BCS** (Business Communication Services, Basis 6.40+ / tüm S/4)
SAP'nin modern-önerdiği yol. **Migration DEĞMEZ** (bug-free üretim koduna dokunma); **yeni işlerde + ek-dosyada** tercih et.
Kazançlar: `packing_list` derdi YOK · `cx_bcs` tek `TRY` · `cl_bcs_convert=>string_to_soli()` **otomatik 255-böler** (§3.2'nin OO karşılığı).
```abap
TRY.
    DATA(lo_send) = cl_bcs=>create_persistent( ).
    DATA(lo_doc)  = cl_document_bcs=>create_document(
      i_type = 'HTM'   " ⚠ RAW DEĞİL — RAW istenmeyen satır-sonu ekler
      i_text = cl_bcs_convert=>string_to_soli( iv_html )  i_subject = CONV #( iv_subject ) ).  " subject CHAR50 sürüyor
    lo_doc->add_attachment( i_attachment_type = 'XLS' i_attachment_subject = 'Rapor.xls'
                            i_att_content_hex = cl_bcs_convert=>xstring_to_solix( lv_xstr ) ).
    lo_send->set_document( lo_doc ).
    lo_send->set_sender( cl_sapuser_bcs=>create( sy-uname ) ).      " sabit-user YOK (§1)
    lo_send->add_recipient( cl_cam_address_bcs=>create_internet_address( iv_email ) ).
    lo_send->send( ).  COMMIT WORK.                                  " ⛔ COMMIT ŞART
  CATCH cx_bcs INTO DATA(lx). " job-log; akışı kesme
ENDTRY.
```
> **Türkçe-en-güvenli ek** = `.xlsx` (abap2xlsx) veya BOM'lu binary — encoding dosyanın İÇİNDE, SAPconnect codepage'inden bağımsız (§3.5 riskini kesin çözer).

## 6. CHECKLIST (mail yazmadan önce)
- [ ] Gönderen `sy-uname` / type `'B'` (sabit-user YOK, tip/değer uyumlu)
- [ ] Alıcılar dinamik tablodan, `pasif <> 'X'`; alıcı yoksa atla (log)
- [ ] Gövde **INLINE style** (head-CSS class YOK)
- [ ] `html_add` **255-chunk** (tek-atama YOK — sessiz kesme/bozuk-tag riski)
- [ ] Hizalı tablo `<table><td>` + sabit etiket-kolonu
- [ ] ADET **tam sayı** / KG ondalıklı; **`WRITE...TO` YOK**
- [ ] Konu ≤50, kritik-bilgi + durum-ibaresi BAŞTA, ASCII; `ALPHA=OUT`→`condense`
- [ ] Türkçe: gövde `charset=utf-8` meta; kritik metin bozulursa **ek binary** (§5)
- [ ] **8+ kolon geniş tablo → gövde yerine EK-DOSYA** (§5)

---

## İlgili
- [`adt-message-class.md`](adt-message-class.md) — mail metinleri mesaj-sınıfında tutulacaksa
- [`lessons-learned.md`](lessons-learned.md) · [`known-errors.md`](known-errors.md)
