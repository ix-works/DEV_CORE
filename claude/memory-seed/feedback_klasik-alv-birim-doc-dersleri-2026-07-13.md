---
name: feedback_klasik-alv-birim-doc-dersleri-2026-07-13
description: "<PAKET-E> oturumu core-terfi dersleri — klasik-ALV birim/fieldcat + ABAP loop + GUI-KD F1-DOCU; pointer'lar core'da"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9fac5cf8-9dc0-49a7-bbf6-02243dd60ce8
---

<PAKET-E> Excel-sipariş (klasik ALV/GUI) oturumunun kalıcı dersleri **core'a terfi etti** (memory=pointer):

**Birim (UNIT/MSEHI) — canlı ders:** UNIT-tipli alanda (VRKME/MEINS) **DAİMA iç MSEHI** sakla; dış kod (Excel/EDI 'ADT'=iç 'ST'nin TR MSEH3'ü) UNIT-alanında tutmak → save reddi + ALV `******`/BM302 (CUNIT dış'ı iç sanar). Dış→iç `CONVERSION_EXIT_CUNIT_INPUT` girişte bir kez; ALV/CUNIT dış'ı dile göre otomatik gösterir. **Çift unit-alanı (dış+iç) YANLIŞ** → tek iç-alan. → **bug-checklist BE-52**.

**ABAP loop tuzakları:** loop-içi `DATA` accumulator/`DATA..VALUE` flag iterasyonlar arası SIFIRLANMAZ → her iterasyon başı CLEAR (BE-50); değişkeni `DATA`'dan ÖNCE kullanmak SAP kernel'de "field unknown", abaplint hoist edip geçer → canlı syntax-check (BE-51). (Kullanıcı çok-satır senaryosuyla yakaladı.)

**Klasik ALV field catalog:** manuel `lvc_t_fcat` yerine **DDIC structure-merge** tercih (miktar ondalık QUAN-birim-ref + kod→tanım kolonları + oto-genişlik DDIC'ten); hangisi bir KARAR, ÖNCE SOR → **ADR 0012 rafinasyon + std06 + TS §4.5**. Kolon başlığı DTEL'den gelir → rol-doğru DTEL (KUNAG/KUNWE/NAME_AG/NAME_WE); standart yoksa TS'te netleştir (kolon-tamlık MUST). ALV cwidth_opt boş-grid'de optimize etmez → deferred first_display (BE-54). EML reported'ı generic'e indirgeme, error-type hepsini yüzeye çıkar (BE-53). Include def/impl co-activation reçetesi (BE-39). ⛔ **"classrun aynı-isim binding → taze isim" İDDİASI 2026-07-31'de ÇÜRÜTÜLDÜ** — taze isim işe yaramıyor, sebep sınıfın aktive edilmemesi ya da bayat oturum: [[feedback_classrun-teshis-yanlis-surum-ve-bayat-oturum]].

**GUI program KD → F1-DOCU VARSAYILAN:** klasik/GUI (tcode) KD iki-ayaklı — repo markdown/PDF + in-system F1-DOCU (RE fihrist, standart Yardım→Uygulama Yardımı, özel buton YOK, ZSD000_CL_DOCU). Kullanıcı istemeden yap → **std04 §4.6 KD-F1-01**. Bkz [[feedback_playbook-once-oku]], [[feedback_done-tam-kapsam-dogrula]].
