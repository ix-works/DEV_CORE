---
name: cl-fdt-xl-mutlak-iliski-target-core005
description: "SAP cl_fdt_xl_spreadsheet, Target'ı MUTLAK yazılmış xlsx'i okuyamaz (FDT_EXCEL_CORE005 \"Çalışma sayfasının yüklenmesi olanaksız\") — openpyxl/OpenXML SDK çıktısı böyledir; test dosyası üretirken Target'ı göreli yap"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: eb086373-3ff5-4f0b-9566-83527256cc5a
  modified: 2026-09-28T17:17:54.247Z
---

SAP `CL_FDT_XL_SPREADSHEET` sayfa dosyasının yolunu `workbook_folder ('xl/') && ilişki Target` diye **düz birleştirir** (get_worksheet_by_name ~:2370; kök `_rels/.rels` Target'ı da `/` ile bölünüp klasöre çevrilir ~:2828). Excel Target'ı **göreli** yazar (`worksheets/sheet1.xml`). openpyxl 3.1.x worksheet Target'ını **mutlak** yazar (`/xl/worksheets/sheet1.xml`) → `xl//xl/worksheets/sheet1.xml` aranır → bulunamaz → `MESSAGE E005(FDT_EXCEL_CORE)`. OpenXML SDK (.NET, `x:` önekli) çıktısı kök Target'ı da mutlak yazar (`/xl/workbook.xml`).

**Why:** Bir projede, 2026-09-28: Python ile üretilen test xlsx'leri SAP'de E005 verdi. İlk hipotez (openpyxl `inlineStr`, sharedStrings yok) YANLIŞTI — düzeltildi, hata aynen sürdü. Kök neden SAP'nin kendi kaynağı okunarak bulundu; taklit betiği kontrol grubunda eski dosyayı düşürdü, yeniyi geçirdi.

**How to apply:**
- SAP'ye yüklenecek xlsx'i Python ile üretiyorsan: `xl/_rels/workbook.xml.rels` içinde `Target="/xl/` → `Target="` yap (+ tercihen sharedStrings). (Vaka projesinde bir xlsx üretici betik + SAP yol taklidi betiği tutuldu; tüketici repoda.)
- Başka araçtan (ERP export, .NET) gelen dosya E005 verirse: kullanıcıya **Excel'de açıp kaydet** dedirt (Excel göreli yazar) — ya da okuma kodunu değil dosyayı düzelt.
- Dosya-biçimi hatasında tahmin yürütme: SAP okuyucu sınıfının kaynağını `docu_get`-tarzı salt-okur GET ile oku, hata mesajının `MESSAGE` satırından geriye yürü.

Son-doğrulama: 2026-09-28 — SAP kaynağı + taklit + **kullanıcı canlı teyidi** (Target göreli dosyalar SAP'de okundu: 006 ve 051 mesajları geldi)
Applies-to: s4_private (CL_FDT_XL_SPREADSHEET); diğer profillerde ölçülmedi
prior-art: yok (memory + core playbook/standards + SOURCE_CODES'ta FDT_EXCEL_CORE aranmadı → 0 eşleşme)
