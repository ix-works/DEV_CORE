# -*- coding: utf-8 -*-
"""sap_kaynak_uzantilari — repoda bir SAP objesinin KAYNAĞINI taşıyan dosya uzantıları (TEK KAYNAK).

Tüketiciler (ikinci literal YAZILMAZ — biri büyüyünce diğeri sessizce eksik kalır):
  · `source_drift.SOURCE_EXTENSIONS` (drift/damga kapısı, `sap_sync_pull`) — bu tupleın kendisi
  · `init_project.GITATTRIBUTES` — yeni projenin `.gitattributes` SAP LF bloğu bu listeden üretilir

Neden `utils/` altında: `init_project` izole core iskeletlerinde (fixture'lar) yalnız
`scripts/utils` ile koşar; liste `source_drift.py`'de kalsaydı o iskeletler import'ta düşerdi.
Bağımlılığı yoktur (standart kütüphane bile import etmez).

Çift uzantılar (`.ddls.asddls`, `.tabl.ddl`) son-ek eşlemesiyle yakalanır. `.md` companion
dosyaları (ör. `*.srvb.md`) KASITLI dışarıda — onlar kaynak değil dokümantasyon.
`object_types.OBJECT_TYPES` dosya uzantılarının (XML olmayanların) her biri bu listedeki bir
uzantıyla biter; eşlik `tests/fixtures/init_project_iskelet` E4'te ölçülür.
"""

SAP_KAYNAK_UZANTILARI = (
    ".srvd",          # service definition
    ".srvb",          # service binding (source taşımaz ama tutarlılık için)
    ".bdef",          # behavior definition
    ".cds",           # CDS view (proje konvansiyonu)
    ".ddls",          # CDS DDL source
    ".asddls",        # CDS DDL source (SAP native ext)
    ".abap",          # class/program/include/fugr
    ".dcl",           # access control
    ".asdcls",        # access control (SAP native ext)
    ".ddlx",          # metadata extension
    ".asddlxs",       # metadata extension (SAP native ext)
    # Q352 (2026-09-26): Z tablo DDL'i bir tüketici evde `.tabl.ddl` / `.tabl` adlarıyla durur
    # (tüketici repo sayımı 12 + 1). Listede YOKKEN `sap_sync_pull --type table` dosyayı
    # BULAMIYOR, "damgalanmadı" deyip çıkıyordu; kapı da bu dosyaları hiç görmüyordu.
    ".tabl.ddl",      # tablo DDL (proje konvansiyonu)
    ".tabl",          # tablo DDL (proje konvansiyonu, kısa ad)
)
