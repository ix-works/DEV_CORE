---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: backend
last-updated: 2026-10-04
status: active
---

# How-To: SFP form objesi OLMADAN PDF üretmek — AI'ın yazdığı XDP + `CL_FP_ADS_UTIL=>RENDER_PDF` (+ mail eki)

> **Ne zaman:** Bir belge PDF olarak (çoğu kez mail eki) üretilecek, ama ortada bir SFP form/interface
> (SFPF/SFPI) yok ve Adobe Designer ile layout çizecek bir operatör de yok. Bu yolda yerleşimi
> **AI yazar**: düz XML olan bir XFA şablonu (XDP) ve onu dolduracak XML veri hazırlar, ADS bunları
> PDF'e çevirir.
> **Ne zaman DEĞİL:** Form Designer'da düzenlenmeye devam edecekse, NAST/Output Management'tan basılacaksa
> ya da yasal bir çıktıysa (e-İrsaliye/e-Fatura) → klasik SFP yolu, bkz. [`../standards/07-output-forms.md`](../standards/07-output-forms.md).
> **Standarttaki yeri:** std 07 §1b ("Yol D"). Checklist satırları `AF-XDP-*` ([`checklists/adobe-forms-creation.md`](checklists/adobe-forms-creation.md)).

Kanıt düzeyi: aşağıdaki her "✅" maddesi **canlı ölçüldü** (S/4 private 2025, DEV, 2026-10-04): 1 sayfalık
bir sevk belgesi (başlık ızgarası, Code39 barkod, tekrarlı kart, gruplu kalem tablosu + ara/genel toplam,
stok blokları, altbilgi) render edildi, mail eki olarak dış posta kutusuna gönderildi ve açıldı.
"⚠ ölçülmedi" maddeleri öyle okunmalı.

---

## 0. Yol seçimi (araştırmanın özeti)

| Yol | Ne yapar | Durum |
|---|---|---|
| **D — XDP + `RENDER_PDF`** (bu dosya) | Yerleşim ve veri birer string; form objesi yok, standart tabloya yazım yok | ✅ çalıştı — **önerilen** |
| A — SFPF/SFPI'yi programatik yarat (`CL_FP_WB_FORM`/`CL_FP_WB_INTERFACE=>CREATE`, `CL_FP_HELPER=>CONVERT_XSTRING_TO_FORM`; abapGit'in SFPF serileştiricisinin yöntemi) | Designer'da sonradan açılabilen gerçek form | released DEĞİL · context XML'i GUID'li nesne grafı (zor) · form deposuna SAP API'siyle yazar ⇒ ADR 0005 yorumu kullanıcı kararıdır · ⚠ denenmedi |
| SmartForms → OTF → `CONVERT_OTF` → PDF | Klasik | yerleşim yeniden çizilir; Türkçe/barkod PDF'te ⚠ ölçülmedi |
| Spool/liste → PDF, SALV PDF export | Düz liste | yerleşim yok → elenir |
| Saf ABAP PDF kütüphaneleri | — | yerleşik 3 font: **Ğ İ Ş yok** → Türkçe için elenir |
| Tarayıcıda PDF (jsPDF vb.) | — | font gömme + büyük yük (HTTP 414) → elenir |

**ADT notu:** ADT'de SFPF/SFPI düzenleme collection'ı **yok** (discovery'de ölçüldü) ⇒ Yol A'yı ADT'den
yürütmek mümkün değil; Yol D'nin hiçbir adımı ADT'ye form objesi yazdırmaz.

**Ön koşul:** ADS ayakta olmalı. Ölçüm: `TSP01`'de ADS'in ürettiği güncel spool var mı (ölçülen vakada ADS
biçimli — `ADSP` — spool'lar sayıldı; son tarihine bak) — yoksa Basis'e ADS bağlantı testini sor.
ADS yoksa bu yol da çalışmaz.

---

## 1. API (✅ başarılı yol canlı; hata yolu kaynak okuması)

```abap
DATA ls_opt TYPE cl_fp_ads_util=>ty_gs_options_pdf.
ls_opt-embed_fonts = abap_true.                     " Türkçe glifler için ŞART (§3.4)

TRY.
    cl_fp_ads_util=>render_pdf( EXPORTING iv_xml_data     = lv_data_x   " XML veri, UTF-8 xstring
                                          iv_xdp_layout   = lv_xdp_x    " XDP şablon, UTF-8 xstring
                                          iv_locale       = 'tr_TR'     " sayı/tarih biçimi
                                          is_options      = ls_opt
                                IMPORTING ev_pdf          = lv_pdf      " xstring
                                          ev_pages        = lv_pages    " int4
                                          ev_trace_string = lv_trace ). " ADS izi — hatada oku
  CATCH cx_fp_ads_util INTO DATA(lx).
    " ev_trace_string ve (varsa) hata PDF'i istisnadan ÖNCE dolar → hatada izi yaz/logla
    " (⚠ canlı hata koşusu yapılmadı — CL_FP_ADS_UTIL kaynağında RAISE'den önce dolduğu okundu)
ENDTRY.
```

- String → UTF-8 xstring: `cl_web_http_utility=>encode_utf8( )` (✅ kullanılan) — `cl_abap_conv_codepage=>create_out( )->convert( )` da olur (⚠ bu yolda denenmedi).
- `ev_pages`'i **her koşuda logla/göster**: yerleşim kusurunun en ucuz sinyali beklenmeyen sayfa sayısıdır (§3.1).
- Released durumu: sınıf ARS'de **released (C1)** listelenmişti (araştırma, 2026-10-04; ⚠ bu dosyada yeniden
  ölçülmedi); hedef sistemde `SEOSUBCODF`/ADT ile metodun imzasını yeniden ölç.

---

## 2. XDP'yi yazmak — iskelet

XFA 3.3 düz XML'dir. Aşağıdaki iskelet canlıda render edilen tam şablondan **kısaltıldı** (öğe ve öznitelikler
aynı; ⚠ bu kısa hâli ayrıca render edilmedi):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xdp:xdp xmlns:xdp="http://ns.adobe.com/xdp/">
<template xmlns="http://www.xfa.org/schema/xfa-template/3.3/">
<subform name="data" layout="tb" locale="tr_TR" restoreState="auto">
 <pageSet>
  <pageArea name="A4" id="A4">
   <contentArea name="CA" x="9mm" y="8mm" w="192mm" h="281mm"/>
   <medium stock="a4" short="210mm" long="297mm"/>
  </pageArea>
 </pageSet>
 <!-- akışlı içerik: tb = yukarıdan aşağı, lr-tb = soldan sağa sonra alt satır -->
 <subform name="HDR" layout="lr-tb" w="192mm">
  <bind match="dataRef" ref="$record.HDR"/>
  <field name="BELGE_NO" w="48mm" h="6mm"><ui><textEdit/></ui>
   <font typeface="Arial" size="9pt" weight="bold"/><bind match="dataRef" ref="$.BELGE_NO"/></field>
 </subform>
 <subform name="ITEMS" layout="tb" w="192mm">
  <bind match="dataRef" ref="$record.ITEMS"/>
  <subform name="ROW" layout="lr-tb" w="192mm">
   <occur min="0" max="-1"/>                          <!-- tekrarlı satır -->
   <bind match="dataRef" ref="$.ROW[*]"/>
   <field name="MATNR" w="40mm" minH="5mm"><ui><textEdit multiLine="1"/></ui>
    <font typeface="Arial" size="7.5pt"/><bind match="dataRef" ref="$.MATNR"/></field>
  </subform>
 </subform>
</subform>
</template>
<config xmlns="http://www.xfa.org/schema/xci/3.0/">
 <present><destination>pdf</destination><pdf><fontInfo/><version>1.7</version></pdf></present>
</config>
</xdp:xdp>
```

Veri: kök eleman adı XDP'nin kök subform adıyla aynı (`<data>…</data>`), altında `HDR`, `ITEMS/ROW` …

**Bağlama kuralları** (ilk üçü ✅ render'da gözlendi):
- `$record.A.B` = veri kökünden mutlak yol · `$.A` = en yakın **bağlı** ata subform'un veri düğümüne göre.
- `X[*]` + `<occur min="0" max="-1"/>` = tekrarlı subform (her veri örneği bir kopya).
- **Adsız** subform ya da `<bind match="none"/>` veri bağlamını DEĞİŞTİRMEZ (görsel gruplama için güvenli).
  **Adlı + bind'siz** subform ad eşlemesi yapar ⇒ bağlam kayabilir — adlı subform'a daima açık `bind` ver
  (⚠ XFA davranışına dayanan önlem; kaymanın kendisi gözlenmedi, şablon bu durumu baştan önledi).
- Sabit metin `draw`, veriye bağlı metin `field`. Etiket + değer kutusu = `draw` + `field` içeren küçük adsız subform.
- Barkod (✅ Code39, bu biçimle okundu):
  `<ui><barcode type="code3Of9" dataLength="10" moduleWidth="0.25mm" wideNarrowRatio="3.0" textLocation="none" checksum="none"/></ui>`
  — numarayı barkodun altına ayrı bir `field` olarak yaz (`textLocation="none"`).

---

## 3. TUZAKLAR (hepsi bu yolda yaşandı)

### 3.1 ⛔ Çok kolonlu tablo satırında (`lr-tb`) kolon toplamı kapsayıcıya eşitse son kolon alt satıra kayabilir
Ölçülen vaka: **11 kolonlu** kalem tablosu satırında (ve 8 hücreli ara/genel toplam satırında) kolon toplamı tam
192 mm, kapsayıcı da 192 mm idi: son kolon (onay kutusu) **her satırda** alt satıra düştü, satır yüksekliği
ikiye katlandı, belge 1 yerine **2 sayfa** oldu; başlık satırı da kaydı. Hata, uyarı ya da ADS iz satırı **yok**
— sinyal yalnız `ev_pages` ve gözle bakış.
Aynı belgede toplamı yine tam 192 olan **2-4 elemanlı** satırlar (kart başlığı 60+132, altbilgi 125+67,
3 parçalı başlık, 4×48 ızgara) **kaymadı**. ⇒ Mekanizma (eleman sayısıyla biriken yuvarlama mı, başka bir şey mi)
ve eşik **ölçülmedi**.
**Kural:** çok kolonlu tablo satırlarında kolon toplamını kapsayıcıdan **1 mm küçük** tut (örn. 191/192);
birleşik etiketli toplam satırları da aynı toplamı izlesin. Kasıtlı sarılan ızgaralar (toplamı kapsayıcının
katı olan kart dizileri) bu kuralın konusu değildir.
✅ Doğrulandı: yalnız bir kolonu 1 mm daraltmak (toplam 191) satırları tek satıra indirdi, belge **1 sayfa**
oldu (§7, v2).

### 3.2 ⛔ Büyük harfli sabit etiketlerde Türkçe `İ` — yabancı sözcükte YANLIŞ
Etiketler büyük harfle yazılırken "Booking" → **"BOOKİNG"** oldu (Türkçe büyük harf dönüşümü). Türkçe
sözcükte doğru olan (`SEVKİYAT`, `MÜŞTERİ`), yabancı sözcükte/kısaltmada yanlıştır (`BOOKING`, `INCOTERMS`, `BL NO`).
**Kural:** büyük harfli etiketleri elle yaz; `İ` geçen her etiketi listele ve tek tek oku
(`grep -o "<text>[^<]*İ[^<]*</text>"` — sözcük başındaki `İ`'yi de yakalar: `İNCOTERMS` ✗).

### 3.3 Uzun metin alanı = `multiLine="1"` + `minH` (sabit `h` DEĞİL)
Sabit `h` verilen alanda uzun metin **kesilir**; `minH` + `multiLine` satır yüksekliğini büyütür.
Tablo satırlarında tüm hücrelere `minH` ver (biri büyürse satır büyür).

### 3.4 Font: `typeface="Arial"` + `embed_fonts = abap_true` + projenin yerel ayarı (✅ TR projede `tr_TR`)
ADS'in sunucusunda Arial var; PDF'e ArialMT / Arial-BoldMT gömüldü, ş ğ ı İ Ş Ğ Ü Ö Ç doğru çıktı.
Gömme kapalıysa görüntüleyicinin yedek fontu Türkçe glifleri bozabilir (⚠ kapalı hâl ölçülmedi).

### 3.5 XDP'yi ABAP'a gömmek: üretici script, elle kopyalama DEĞİL
XDP ~35-40 KB'tır ve elle ABAP literal'ine çevrilemez. Yerleşim kaynağı `.xdp` dosyası olarak repoda durur;
küçük bir script onu ABAP metoduna (`rv_xml = rv_xml && \`…\` && nl.` satırları) çevirir:
- ters tırnak kaçışı (`` ` `` → ` `` `), satır başına ≤ 255 karakter (uzun satırı parçala),
- yazmadan önce **bağlama simülasyonu**: her `bind ref`'i örnek veride çöz, çözülemeyen = hata,
  hiçbir alana bağlanmayan veri yaprağı = uyarı (veri ↔ yerleşim adı kayması render'dan önce yakalanır),
- `--check` kipi: ABAP dosyası `.xdp` ile güncel mi (repo'da ikisi ayrı yaşar, kayabilir).
Ürün kodunda XDP'nin nerede saklanacağı (sınıf metodu / MIME deposu / Z tablo) ayrı bir tasarım kararıdır
(⚠ yalnız "sınıf metodu" ölçüldü).

### 3.6 Deneme koşusu: `IF_OO_ADT_CLASSRUN` + base64 çıktı
ADT classrun ile koş; PDF'i base64'e çevirip sabit uzunluklu satırlarla yaz (başlangıç/bitiş işaret satırları
arasında), yerelde çöz ve aç. `ev_pages`, PDF baytı ve ADS izinin başını da yaz. Sayfa sayısını yerelde
**bağımsız** say (`pypdf`): ADS sayfa nesnelerini sıkıştırılmış nesne akışına koyar ⇒ ham `/Type /Page`
regex'i **0** verir (ölçüldü) — o sayı hüküm değildir. PDF'i görsel olarak **aç ve oku** — bayt/sayfa sayısı
yerleşim kusurunu söylemez (§3.1'deki kusur ancak bakınca görüldü).

---

## 4. PDF'i mail eki yapmak (✅ — CL_BCS)

```abap
DATA(lo_req) = cl_bcs=>create_persistent( ).
DATA(lo_doc) = cl_document_bcs=>create_document( i_type = 'HTM' i_subject = lv_kisa_konu   " CHAR50 keser
                 i_text = cl_bcs_convert=>string_to_soli( iv_string = lv_html_govde ) ).
lo_doc->add_attachment( i_attachment_type    = 'PDF'
                        i_attachment_subject = CONV #( lv_ek_adi_uzantisiz )
                        i_attachment_size    = CONV #( xstrlen( lv_pdf ) )
                        i_att_content_hex    = cl_bcs_convert=>xstring_to_solix( iv_xstring = lv_pdf )
                        i_attachment_header  = VALUE soli_tab( ( line = |&SO_FILENAME={ lv_dosya_adi }.pdf| ) ) ).
lo_req->set_document( lo_doc ).
lo_req->set_message_subject( ip_subject = lv_uzun_konu ).          " > 50 kr konu (✅ 95 kr, Türkçe)
lo_req->set_sender( cl_cam_address_bcs=>create_internet_address( i_address_string = lv_gonderen ) ). " §1 howto-abap-email
lo_req->add_recipient( i_recipient = cl_cam_address_bcs=>create_internet_address( i_address_string = lv_alici ) ).
lo_req->set_send_immediately( abap_true ).
IF lo_req->send( ) = abap_true.
  COMMIT WORK.        " RAP içindeysen BURADA DEĞİL — ayrı LUW (howto-abap-email §7.1)
ENDIF.
```

Gönderen politikası, SOES ile teslim teşhisi ve RAP'tan gönderimdeki LUW kuralı:
[`howto-abap-email.md`](howto-abap-email.md) §1, §7.

⛔ **Mail gönderen classrun'u yeniden deneyen bir araçla koşma.** Bazı ADT istemcileri 200 dışı yanıtta
POST'u tekrarlar ⇒ mail iki kez gider. Mail gönderen deneme koşusunu **tek POST** atan küçük bir script ile koş;
zaman aşımı olursa **tekrarlama**, önce SOST/SOOD'a bak.

⛔ Deneme sınıfında `COMMIT WORK` varsa projenin RAP-commit kapısı satır içi muafiyet ister
(`"#NO_RAP_COMMIT_CHECK <gerekçe>` — BE-26); classrun RAP bağlamı değildir.

---

## 5. Akış (deneme → ürün)

1. Yol kararı + kapsam (sayfa sayısı, barkod, Türkçe, tekrarlı bloklar) — kullanıcıyla.
2. AI: `.xdp` + örnek veri `.xml` (gerçek veri biçiminde, en kötü durum: uzun malzeme adı, çok satır).
3. Üretici script (§3.5) → deneme sınıfı (§3.6) → gateway push + aktivasyon + readback.
4. Tek koşu → PDF'i aç → kusur listesi (sayfa sayısı, taşma, glif, barkod okunurluğu, büyük harf `İ`).
5. Düzeltme turu (v2, v3 …) aynı sınıfla. Kullanıcı onayı.
6. Ürünleştirme tasarımı: XDP'nin saklandığı yer, gerçek veri eşlemesi, çoklu belge, hata yolu (ADS kapalıysa ne olur).
7. **Deneme sınıfı + script'ler silinir** (kişisel test adresi taşıyabilir).

---

## 6. ⚠ Ölçülmemiş / açık

- Çok sayfalı akış: sayfa kırılımında tablo başlığının tekrarı (`overflowLeader`), "Sayfa n/N" — ölçülmedi.
- Çok belgede süre/boyut (örn. 50 belge × PDF) — ölçülmedi.
- `embed_fonts = abap_false` davranışı — ölçülmedi.
- Yol A (programatik SFPF) — denenmedi.
- s4_public / BTP ABAP'ta `CL_FP_ADS_UTIL` erişimi — ölçülmedi (bu yüzden `applies_to: [s4_private]`).

## 7. Ölçüm geçmişi
- 2026-10-04 v1: 87.732 bayt, **2 sayfa** (beklenen 1) — §3.1 kolon kayması + §3.2 "BOOKİNG"; ArialMT/Arial-BoldMT gömülü,
  Türkçe glifler + Code39 doğru; CL_BCS eki dış posta kutusuna ulaştı.
- 2026-10-04 v2 (yalnız kolon toplamı 192→191 mm + etiket düzeltmeleri): 87.271 bayt, **1 sayfa** (`ev_pages` 1 ·
  `pypdf` 1; kontrol grubu v1 aynı yöntemle 2), A4; ADS render 607 ms; mail SOST `718 I`, tek gönderi.

## İlgili
- [`howto-abap-email.md`](howto-abap-email.md) — gönderen, alıcı, konu, gövde, ek tuzakları
- [`../standards/07-output-forms.md`](../standards/07-output-forms.md) — SFP yolu + §1b Yol D
- [`checklists/adobe-forms-creation.md`](checklists/adobe-forms-creation.md) — `AF-XDP-*`
