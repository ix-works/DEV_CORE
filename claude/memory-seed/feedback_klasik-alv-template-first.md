---
name: feedback_klasik-alv-template-first
description: "Klasik ABAP ALV kurulumu reusable class DEĞİL, programa inline template-first (ADR 0012); field title/hotspot/event program-spesifik"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c874b6ce-b5f4-4780-8a44-b99611c71492
---

Klasik ABAP'ta ALV (CL_GUI_ALV_GRID) kurulumu — field catalog (TR title), hotspot kolonları, event handler (double_click/hotspot/user_command), layout, özel toolbar — **her programda İNLİNE kodlanır** (programa lokal `lcl_event` + elle `lvc_t_fcat`). Instantiate edilen reusable ALV class KULLANILMAZ. Kanonik template: `playbook/templates/classic-alv-list.prog.abap` (kopyala+özelleştir). Çalışan örnek: ZSD000_P_ALV_TEMP1.

**Why:** Kullanıcı (2026-06-03): "zsd000_cl_alv_grid'i class yapmanın anlamı yok, template kalabilir ama fonksiyonlar ana programda kodlanmalı; yoksa dışarıdan programa özgü çok fazla parametre almak gerekir — field-catalog'da field title vs." Field title/hotspot/event programdan programa tamamen farklı → reusable class arayüzü şişer/kırılganlaşır. Reusable `ZSD000_CL_ALV_GRID`/`ZSD000_CL_ALV_EVENT` silindi (ADR 0012, gap#C3 reusable-class yönünü revize eder). ALV-paritesi (sort/filtre/Excel/kolon-perso) zaten CL_GUI_ALV_GRID + set_table_for_first_display(i_save='A') built-in'inden gelir.

**How to apply:** Yeni klasik ALV/liste programı → `playbook/templates/classic-alv-list.prog.abap`'ı kopyala, fcat'i (TR title + gereken kolonlarda hotspot=abap_true) + lcl_event'i program ihtiyacına göre doldur. Ekran 0100 + STAT0100 ayrıca AI ile üretilir → [[project_dynpro-gui-status-uretici]]. Tree liste de aynı şekilde inline (lcl_tree + CL_GUI_ALV_TREE), reusable class değil. ADR 0008 UI5 liste paritesi AYRIDIR (TablePersonalizer.js), bu kararla karışmaz. İlke: [[feedback_generic-tool-program-spesifik-isim-verme]] gibi — yapay soyutlama yerine doğru kapsam.
