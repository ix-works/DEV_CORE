#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""checklist_check fixture — ortak checklist kontrol programının kalibrasyonu.

Ne ölçülür (vektör aileleri):
  A  her A sınıfı maddenin kontrolü için EN AZ bir pozitif (FAIL/WARN) ve bir negatif
     (PASS/ELLE/UYGULANMAZ) örnek — `degerlendir` gerçek map satırıyla çağrılır. K0 kapsamı
     map'ten TÜRETİR: kontrolü olan her A maddesinin iki yönü de burada yoksa K0 düşer.
  T  BE-10b konumları: ölçülmüş (IMPLEMENTATION başı ↔ ilk METHOD · ENDMETHOD ↔ METHOD) ve
     ölçülmemiş (son ENDMETHOD ↔ ENDCLASS · ENDCLASS sonrası · DEFINITION ↔ IMPLEMENTATION)
     etiketleri + serbest bölgeler (DEFINITION, metot gövdesi, dosya başı) + girintili `"`.
  C  C sınıfı ipucu tarayıcısı aday bulsa da hüküm ELLE · B sınıfı `--sap` yoksa ÖLÇÜLEMEDİ.
  S  tohumlanmış hata paketi (geçici git deposu, iki commit, 7 bilinen hata + 1 önceden var)
     → diff kipinde 7'si FAIL, önceden var olan WARN, exit 1; `--files` kipinde önceden var FAIL.
  V  `--verify-report`: tam rapor · satır yok · ELLE · ÇELİŞKİ · ÇÜRÜTÜLDÜ (kanıtlı kabul,
     kanıtsız red) · hükümsüz kelime · yalnız `FAIL→F1` (kanıtsız) · okunamayan rapor (exit 2).
  X  exit kodları: kullanım 2 · bozuk/eksik map 2 · beklenmeyen istisna 2 · --help hüküm satırı.
  H  `--harita-denetim`: gerçek map OK · bilinmeyen alan · kontrolsüz A · blok yalnız BE-10b.
  R  `--reach` (geçici map) PASS/FAIL · mini YAML == PyYAML (yoksa ATLA) ·
     run_review class_push zinciri: kirli sınıf BLOCKER, temiz PASS (gerçek CLI).

Mutasyon kipleri (program kaynak METNİ değiştirilir, gerçek `__file__` ile exec edilir):
  --mutasyon-literal      ABAP literal içi boşluğa çevrilmez (literaldeki SQL kod sanılır)
  --mutasyon-degisen      diff kipinde değişmeyen satırdaki FAIL → WARN indirimi kapalı
  --mutasyon-blok         `seviye: blok` FAIL'i engelleyici sayılmaz
  --mutasyon-c-hukum      C sınıfı ipucu bulgusu hüküm olur (ELLE'ye zorlanmaz)
  --mutasyon-etiket       ölçülmemiş BE-10b konumları ölçülmüş diye etiketlenir
  --mutasyon-girintili    girintili `"` yorum satırı yorum sayılmaz
  --mutasyon-verify-elle  rapordaki ELLE satırı eksiklik sayılmaz
  --mutasyon-kanitsiz     rapordaki kanıtsız satır eksiklik sayılmaz
  --mutasyon-cokme        beklenmeyen istisna exit 1 döner (2 değil)
CORE-07: her kipin DÜŞMESİ BEKLENEN vektör kümesi `_BEKLENEN_DUSEN`'de PİNLİDİR ve EŞİTLİKLE
kıyaslanır. Çıkış: 0 taban yeşil · 1 mutasyon BEKLENEN kümeyle düştü · 2 SAPMA · 3
DOGRULANAMADI (çapa tam 1 kez eşleşmedi ya da mutant derlenmedi — "düştü" SAYILMAZ).

Koşum: python tests/fixtures/checklist_check/run.py [--mutasyon-...]   (exit 0 = PASS)
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
PROG = REPO / "scripts" / "validators" / "checklist_check.py"
RUN_REVIEW = REPO / "scripts" / "validators" / "run_review.py"
MAP = REPO / "playbook" / "checklists" / "checklist-map.yaml"

_GECERLI_KIP = frozenset({"--mutasyon-literal", "--mutasyon-degisen", "--mutasyon-blok",
                          "--mutasyon-c-hukum", "--mutasyon-etiket", "--mutasyon-girintili",
                          "--mutasyon-verify-elle", "--mutasyon-kanitsiz", "--mutasyon-cokme"})

_MUT = {
    "--mutasyon-literal": (
        "            else:\n                kod.append(ch)\n                kodsuz.append(\" \")\n"
        "            i += 1\n            continue\n        if ust == \"T\":",
        "            else:\n                kod.append(ch)\n                kodsuz.append(ch)\n"
        "            i += 1\n            continue\n        if ust == \"T\":"),
    "--mutasyon-degisen": (
        "            if dur == \"FAIL\" and not tum and d.degisen is not None",
        "            if False and dur == \"FAIL\" and not tum and d.degisen is not None"),
    "--mutasyon-blok": (
        "    blok = sonuc == \"FAIL\" and madde.get(\"seviye\") == \"blok\"",
        "    blok = False"),
    "--mutasyon-c-hukum": (
        "        sonuc = \"ELLE\"          # ipucu tarayıcısı hüküm vermez",
        "        pass"),
    "--mutasyon-etiket": (
        "        if kesinlik == OLCULMUS:",
        "        if True:"),
    "--mutasyon-girintili": (
        "    return ham.startswith(\"*\") or ham.lstrip().startswith('\"')",
        "    return ham.startswith(\"*\") or ham.startswith('\"')"),
    "--mutasyon-verify-elle": (
        "        if all(x == \"ELLE\" for x in hk):",
        "        if False:"),
    "--mutasyon-kanitsiz": (
        "        if not any(_kanit_mi(x) for x in h):",
        "        if False:"),
    "--mutasyon-cokme": (
        "        print(f\"[PROGRAM KOŞMADI] {type(e).__name__}: {e}\")\n        return 2",
        "        print(f\"[PROGRAM KOŞMADI] {type(e).__name__}: {e}\")\n        return 1"),
}

# Ölçülerek pinlendi (2026-10-18). Her küme NEDEN o vektörleri içerir:
#  literal      : BE-31/N-lit (literaldeki `FROM kna1` kod sanılır) + BE-01/N-lit (`'UPDATE mara SET'`)
#  degisen      : S2 (önceden var olan BE-47 diff kipinde de FAIL olur)
#  blok         : S1 (seed exit 1 → 0) + S4 (BLOK işareti) — run_review vektörü gerçek CLI'yı koşar, düşmez
#  c-hukum      : C1 · C2 (ipucu bulgusu WARN hüküm olur)
#  etiket       : yalnız T8 — mutasyon MESAJ katmanındadır (k_be10b); T3-T5 konum demetini
#                  (`yorum_bantlari`) ölçer, o katman değişmez (ilk tahmin {T3,T4,T5,T8} idi, ölçüm T8)
#  girintili    : T6 (girintili `"` bandı kaçar)
#  verify-elle  : V3
#  kanitsiz     : V6 · V8 (kanıtsız satırlar geçer)
#  cokme        : X5 (enjekte istisna) + X3 (normal kipte ayrıştırılamayan map ValueError'ı da
#                  aynı genel yakalayıcıdan geçer — ölçüldü, beklenen)
_BEKLENEN_DUSEN = {
    "--mutasyon-literal": {"BE-31/N-lit", "BE-01/N-lit"},
    "--mutasyon-degisen": {"S2"},
    "--mutasyon-blok": {"S1", "S4"},
    "--mutasyon-c-hukum": {"C1", "C2"},
    "--mutasyon-etiket": {"T8"},
    "--mutasyon-girintili": {"T6"},
    "--mutasyon-verify-elle": {"V3"},
    "--mutasyon-kanitsiz": {"V6", "V8"},
    "--mutasyon-cokme": {"X3", "X5"},
}

SONUC: list[tuple[str, bool, str]] = []
ATLA: list[tuple[str, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


def yukle(kaynak: str) -> types.ModuleType:
    """Kaynak METNİNİ gerçek `__file__` ile exec et (dataclass için modül sys.modules'ta olmalı)."""
    ad = "_checklist_check_fx"
    m = types.ModuleType(ad)
    m.__file__ = str(PROG)
    sys.modules[ad] = m
    exec(compile(kaynak, str(PROG), "exec"), m.__dict__)
    return m


def kos(G, argv: list[str]) -> tuple[int, str]:
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon), contextlib.redirect_stderr(io.StringIO()):
        rc = G.main(argv)
    return rc, tampon.getvalue()


def tablo(cikti: str) -> dict[str, str]:
    out = {}
    for s in cikti.splitlines():
        if s.startswith("| ") and not s.startswith("| ID ") and not s.startswith("|---"):
            h = [x.strip() for x in re.split(r"(?<!\\)\|", s.strip().strip("|"))]
            if len(h) >= 4:
                out[h[0]] = h[2] + " ¦ " + h[3]
    return out


# ═══════════════════════════════════════════════════════════════ A vektörleri ══
# (ad, madde_id, {rel: içerik}, hedef_rel, beklenen_sonuç_kümesi[, eski_metin])
CLS = "p/classes/zcl_t.clas.abap"
PRG = "p/programs/zab_p_t.prog.abap"
CDS = "p/cds/zi_t.cds"
BDF = "p/behaviors/zi_t.bdef"
VIEW = "a/webapp/view/Main.view.xml"
JS = "a/webapp/controller/Main.controller.js"
XMLNS = ('<mvc:View xmlns:mvc="sap.ui.core.mvc" xmlns="sap.m" xmlns:core="sap.ui.core" '
         'xmlns:f="sap.ui.layout.form">\n')

SINIF_ARA = ("CLASS zcl_t DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    METHODS m1.\n    METHODS m2.\nENDCLASS.\n"
             "CLASS zcl_t IMPLEMENTATION.\n  METHOD m1.\n  ENDMETHOD.\n{ARA}  METHOD m2.\n    \" gövde yorumu serbest\n"
             "  ENDMETHOD.\nENDCLASS.\n")
TS_MESAJ = "## Mesajlar\n\n| No | Metin |\n|---|---|\n| 001 | {M} |\n"
BDEF_SIL = ("managed implementation in class zbp_t unique;\ndefine behavior for ZI_T alias Kalem\n{\n"
            "  delete;\n  validation valSil on save { delete; }\n}\n")
IMP_SIL = ("CLASS lhc DEFINITION INHERITING FROM cl_abap_behavior_handler.\n  PRIVATE SECTION.\n"
           "    METHODS valsil FOR VALIDATE ON SAVE IMPORTING keys FOR Kalem~valSil.\nENDCLASS.\n"
           "CLASS lhc IMPLEMENTATION.\n  METHOD valsil.\n"
           "    READ ENTITIES OF zi_t IN LOCAL MODE ENTITY {ENT} ALL FIELDS WITH CORRESPONDING #( keys ) RESULT DATA(r).\n"
           "  ENDMETHOD.\nENDCLASS.\n")

VEKTORLER = [
    ("BE-01/P", "BE-01", {CLS: "    UPDATE mara SET matkl = 'X' WHERE matnr = lv_m.\n"}, CLS, {"FAIL"}),
    ("BE-01/N", "BE-01", {CLS: "    UPDATE ztab SET f = 1 WHERE k = 2.\n"}, CLS, {"PASS"}),
    ("BE-01/N-lit", "BE-01", {CLS: "    lv_sql = 'UPDATE mara SET matkl = 1'.\n"}, CLS, {"PASS"}),
    ("BE-03/P", "BE-03", {CLS: "    SELECT SINGLE * FROM afko INTO @DATA(ls) WHERE aufnr = @lv.\n"}, CLS, {"WARN"}),
    ("BE-03/N", "BE-03", {CLS: "    SELECT SINGLE * FROM zafko INTO @DATA(ls) WHERE aufnr = @lv.\n"}, CLS, {"PASS"}),
    ("BE-04/P", "BE-04", {CLS: "    lv_payload = 'x'.\n    WRITE lv_tutar TO lv_metin.\n"}, CLS, {"FAIL"}),
    ("BE-04/N", "BE-04", {CLS: "    lv_payload = 'x'.\n    lv_metin = |{ lv_tutar }|.\n"}, CLS, {"PASS"}),
    ("BE-05/P", "BE-05", {CDS: "define view entity ZI_T as select from ztab {\n  key cast( f as '/ABC/DTEL' ) as F\n}\n"}, CDS, {"FAIL"}),
    ("BE-05/N", "BE-05", {CDS: "define view entity ZI_T as select from ztab {\n  key cast( f as /abc/dtel ) as F\n}\n"}, CDS, {"PASS"}),
    ("BE-10a/P", "BE-10a", {CLS: "CLASS zcl_t DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    METHODS m IMPORTING iv_x TYPE c LENGTH 10.\nENDCLASS.\n"}, CLS, {"FAIL"}),
    ("BE-10a/N", "BE-10a", {CLS: "CLASS zcl_t DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    METHODS m IMPORTING iv_x TYPE string.\nENDCLASS.\n"}, CLS, {"PASS"}),
    ("BE-10b/P", "BE-10b", {CLS: SINIF_ARA.replace("{ARA}", "* metotlar arası\n")}, CLS, {"FAIL"}),
    ("BE-10b/N", "BE-10b", {CLS: SINIF_ARA.replace("{ARA}", "")}, CLS, {"PASS"}),
    ("BE-11/P", "BE-11", {BDF: "managed;\ndefine behavior for ZI_T\n{\n  field ( readonly ) created_by;\n}\n"}, BDF, {"WARN"}),
    ("BE-11/N", "BE-11", {BDF: "managed;\ndefine behavior for ZI_T\n{\n  field ( readonly ) created_by;\n  determination setAdmin on save { create; }\n}\n"}, BDF, {"PASS"}),
    ("BE-12/P", "BE-12", {CLS: "    LOOP AT lt_a INTO DATA(ls_a).\n      SELECT SINGLE f FROM ztab INTO @DATA(lv) WHERE k = @ls_a-k.\n    ENDLOOP.\n"}, CLS, {"FAIL"}),
    ("BE-12/N", "BE-12", {CLS: "    SELECT f FROM ztab INTO TABLE @DATA(lt).\n    LOOP AT lt INTO DATA(ls).\n    ENDLOOP.\n"}, CLS, {"ELLE"}),
    ("BE-26/P", "BE-26", {"p/classes/zbp_t.clas.locals_imp.abap": "    COMMIT WORK.\n"}, "p/classes/zbp_t.clas.locals_imp.abap", {"FAIL"}),
    ("BE-26/N", "BE-26", {"p/classes/zbp_t.clas.locals_imp.abap": "    lv = 1.\n"}, "p/classes/zbp_t.clas.locals_imp.abap", {"PASS"}),
    ("BE-28/P", "BE-28", {CLS: "  METHOD m BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT.\n    -- açıklama\n    et = select * from ztab;\n  ENDMETHOD.\n"}, CLS, {"FAIL"}),
    ("BE-28/N", "BE-28", {CLS: "  METHOD m BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT.\n    -- aciklama\n    et = select * from ztab;\n  ENDMETHOD.\n"}, CLS, {"ELLE"}),
    ("BE-30/P", "BE-30", {CLS: "    go_grid->set_table_for_first_display( EXPORTING is_layout = ls_l it_outtab = gt_d ).\n"}, CLS, {"FAIL"}),
    ("BE-30/N", "BE-30", {CLS: "    go_grid->set_table_for_first_display( EXPORTING is_layout = ls_l CHANGING it_outtab = gt_d ).\n"}, CLS, {"PASS"}),
    ("BE-31/P", "BE-31", {CLS: "    SELECT SINGLE name1 FROM kna1 INTO @DATA(lv) WHERE kunnr = @lv_k.\n"}, CLS, {"FAIL"}),
    ("BE-31/N", "BE-31", {CLS: "    SELECT SINGLE CustomerName FROM i_customer INTO @DATA(lv) WHERE Customer = @lv_k.\n"}, CLS, {"PASS"}),
    ("BE-31/N-lit", "BE-31", {CLS: "    lv_sql = 'SELECT name1 FROM kna1'.\n"}, CLS, {"PASS"}),
    ("BE-33/P", "BE-33", {CDS: "define view entity ZI_U as select from za { key a as K }\nunion select from zb { key b as K }\n"}, CDS, {"FAIL"}),
    ("BE-33/N", "BE-33", {CDS: "@Metadata.ignorePropagatedAnnotations: true\ndefine view entity ZI_U as select from za { key a as K }\nunion select from zb { key b as K }\n"}, CDS, {"PASS"}),
    ("BE-34/P", "BE-34", {CLS: "    DATA ls_ext TYPE bape_vbak.\n    ls_ext-zz1_f = 'X'.\n"}, CLS, {"FAIL"}),
    ("BE-34/N", "BE-34", {CLS: "* bape_vbak eski yol\n    ls_x-zz1_f = 'X'.\n"}, CLS, {"UYGULANMAZ"}),
    ("BE-35/P", "BE-35", {CLS: "    DATA lv TYPE char50.\n"}, CLS, {"WARN"}),
    ("BE-35/N", "BE-35", {CLS: "    DATA lv TYPE char40.\n"}, CLS, {"PASS"}),
    ("BE-36/P", "BE-36", {CLS: "    lv_r = lv_s+0( strlen( lv_s ) - 1 ).\n"}, CLS, {"FAIL"}),
    ("BE-36/N", "BE-36", {CLS: "    lv_r = lv_s+0(3).\n"}, CLS, {"PASS"}),
    ("BE-37/P", "BE-37", {CLS: "    DATA ls TYPE bape_sdsalesdoc.\n    ls-valuepart1 = lv.\n"}, CLS, {"FAIL"}),
    ("BE-37/N", "BE-37", {CLS: "    DATA ls TYPE bape_sdsalesdoc.\n    cl_cfd_bapi_mapping=>x( ).\n"}, CLS, {"PASS"}),
    ("BE-38/P", "BE-38", {CDS: "@AbapCatalog.sqlViewName: 'ZVT'\ndefine view ZI_K as select from ztab {\n  key f\n} where f in ('A', 'B')\n"}, CDS, {"FAIL"}),
    ("BE-38/N", "BE-38", {CDS: "@AbapCatalog.sqlViewName: 'ZVT'\ndefine view ZI_K as select from ztab {\n  key f\n} where f = 'A' or f = 'B'\n"}, CDS, {"PASS"}),
    ("BE-40/P", "BE-40", {CLS: "    SELECT * FROM zi_tf( p_client = @sy-mandt ) INTO TABLE @DATA(lt).\n"}, CLS, {"FAIL"}),
    ("BE-40/N", "BE-40", {CLS: "    SELECT * FROM zi_tf( p_datum = @sy-datum ) INTO TABLE @DATA(lt).\n"}, CLS, {"PASS"}),
    ("BE-41/P", "BE-41", {PRG: "  PERFORM yaz USING |{ lv_a }-{ lv_b }|.\n"}, PRG, {"FAIL"}),
    ("BE-41/N", "BE-41", {PRG: "  PERFORM yaz USING lv_metin.\n"}, PRG, {"PASS"}),
    ("BE-47/P", "BE-47", {CLS: "    lv = |{ lv_a }|{ lv_b }|.\n"}, CLS, {"FAIL"}),
    ("BE-47/N", "BE-47", {CLS: "    lv = |{ lv_a }\\|{ lv_b }|.\n"}, CLS, {"PASS"}),
    ("BE-48/P", "BE-48", {CLS: "    METHODS m EXPORTING ev TYPE i IMPORTING iv TYPE i.\n"}, CLS, {"FAIL"}),
    ("BE-48/N", "BE-48", {CLS: "    METHODS m IMPORTING iv TYPE i EXPORTING ev TYPE i.\n"}, CLS, {"PASS"}),
    ("BE-49/P", "BE-49", {"q/programs/zab_p_main.prog.abap": "REPORT zab_p_main.\n",
                          "q/programs/zab_i_mn_f01.prog.abap": "FORM x.\nENDFORM.\n"}, "q/programs/zab_i_mn_f01.prog.abap", {"FAIL"}),
    ("BE-49/N", "BE-49", {"q/programs/zab_p_main.prog.abap": "REPORT zab_p_main.\n",
                          "q/programs/zab_i_main_f01.prog.abap": "FORM x.\nENDFORM.\n"}, "q/programs/zab_i_main_f01.prog.abap", {"PASS"}),
    ("BE-50/P", "BE-50", {CLS: "    LOOP AT lt INTO ls.\n      DATA lv_n TYPE i VALUE 0.\n      lv_n = lv_n + 1.\n    ENDLOOP.\n"}, CLS, {"WARN"}),
    ("BE-50/N", "BE-50", {CLS: "    DATA lv_n TYPE i VALUE 0.\n    LOOP AT lt INTO ls.\n      lv_n = lv_n + 1.\n    ENDLOOP.\n"}, CLS, {"PASS"}),
    ("BE-51/P", "BE-51", {CLS: "  METHOD m.\n    lv_x = 1.\n    DATA lv_x TYPE i.\n  ENDMETHOD.\n"}, CLS, {"FAIL"}),
    ("BE-51/N", "BE-51", {CLS: "  METHOD m.\n    DATA lv_x TYPE i.\n    lv_x = 1.\n  ENDMETHOD.\n"}, CLS, {"PASS"}),
    ("BE-55/P", "BE-55", {CLS: "    METHODS m IMPORTING it_x TYPE STANDARD TABLE OF i.\n"}, CLS, {"FAIL"}),
    ("BE-55/N", "BE-55", {CLS: "    METHODS m IMPORTING it_x TYPE tt_x.\n"}, CLS, {"PASS"}),
    ("BE-57/P", "BE-57", {CLS: "    TYPES tt_x TYPE STANDARD TABLE OF i.\n    METHODS m RETURNING VALUE(rt) TYPE tt_x.\n"}, CLS, {"FAIL"}),
    ("BE-57/N", "BE-57", {CLS: "    TYPES tt_x TYPE STANDARD TABLE OF i WITH DEFAULT KEY.\n    METHODS m RETURNING VALUE(rt) TYPE tt_x.\n"}, CLS, {"PASS"}),
    ("BE-58/P", "BE-58", {PRG: "PARAMETERS p_uzunisim TYPE i.\n"}, PRG, {"FAIL"}),
    ("BE-58/N", "BE-58", {PRG: "PARAMETERS p_kisa TYPE i.\n"}, PRG, {"PASS"}),
    ("BE-59/P", "BE-59", {CDS: "define view entity ZI_T as select from ztab as a {\n  key a.k,\n  concat( a.f, ' - ' ) as T\n}\n"}, CDS, {"FAIL"}),
    ("BE-59/N", "BE-59", {CDS: "define view entity ZI_T as select from ztab as a {\n  key a.k,\n  concat_with_space( a.f, '-', 1 ) as T\n}\n"}, CDS, {"PASS"}),
    ("BE-60/P", "BE-60", {BDF: BDEF_SIL, "p/classes/zbp_t.clas.locals_imp.abap": IMP_SIL.replace("{ENT}", "Kalem")},
     "p/classes/zbp_t.clas.locals_imp.abap", {"FAIL"}),
    ("BE-60/N", "BE-60", {BDF: BDEF_SIL, "p/classes/zbp_t.clas.locals_imp.abap": IMP_SIL.replace("{ENT}", "Baslik")},
     "p/classes/zbp_t.clas.locals_imp.abap", {"PASS"}),
    ("BE-61/P", "BE-61", {CDS: "define view entity ZI_T as select from ztab {\n  key f \" açıklama\n}\n"}, CDS, {"FAIL"}),
    ("BE-61/N", "BE-61", {CDS: "define view entity ZI_T as select from ztab {\n  key f // açıklama\n}\n"}, CDS, {"PASS"}),
    ("BE-61/P-srvdsrv", "BE-61", {"p/srvd/zui_t.srvd.srvdsrv": "// yorum\ndefine service ZUI_T {\n  expose ZC_T;\n}\n"},
     "p/srvd/zui_t.srvd.srvdsrv", {"FAIL"}),
    ("BE-61/N-srvdsrv", "BE-61", {"p/srvd/zui_t.srvd.srvdsrv": "define service ZUI_T {\n  expose ZC_T;\n}\n"},
     "p/srvd/zui_t.srvd.srvdsrv", {"PASS"}),
    ("BE-62/P", "BE-62", {BDF: "// `alan` açıklaması\nmanaged;\n"}, BDF, {"FAIL"}),
    ("BE-62/N", "BE-62", {BDF: "// alan açıklaması\nmanaged;\n"}, BDF, {"PASS"}),
    ("BE-63/P", "BE-63", {CLS: "    READ TABLE gt_d INTO gs_d INDEX e_row-index.\n"}, CLS, {"FAIL"}),
    ("BE-63/N", "BE-63", {CLS: "    READ TABLE gt_d INTO gs_d INDEX es_row_no-row_id.\n"}, CLS, {"PASS"}),
    ("BE-71/P", "BE-71", {CLS: "CLASS lcl DEFINITION.\n  PUBLIC SECTION.\n    METHODS m IMPORTING it_x TYPE tt_x.\nENDCLASS.\n"
                                "CLASS lcl IMPLEMENTATION.\n  METHOD m.\n    CALL FUNCTION 'Z_F'\n      TABLES\n        t_x = it_x.\n  ENDMETHOD.\nENDCLASS.\n"}, CLS, {"FAIL"}),
    ("BE-71/N", "BE-71", {CLS: "CLASS lcl DEFINITION.\n  PUBLIC SECTION.\n    METHODS m IMPORTING it_x TYPE tt_x.\nENDCLASS.\n"
                                "CLASS lcl IMPLEMENTATION.\n  METHOD m.\n    DATA(lt_k) = it_x.\n    CALL FUNCTION 'Z_F'\n      TABLES\n        t_x = lt_k.\n  ENDMETHOD.\nENDCLASS.\n"}, CLS, {"PASS"}),
    ("BE-76/P", "BE-76", {CLS: "CLASS lhc DEFINITION INHERITING FROM cl_abap_behavior_handler.\nENDCLASS.\nCLASS lhc IMPLEMENTATION.\n"
                                "  METHOD m.\n    WAIT UP TO 1 SECONDS.\n  ENDMETHOD.\nENDCLASS.\n"}, CLS, {"FAIL"}),
    ("BE-76/N", "BE-76", {CLS: "CLASS lhc DEFINITION INHERITING FROM cl_abap_behavior_handler.\nENDCLASS.\nCLASS lhc IMPLEMENTATION.\n"
                                "  METHOD m.\n    lv = 1.\n  ENDMETHOD.\nENDCLASS.\n"}, CLS, {"PASS"}),
    ("BE-81/P", "BE-81", {CLS: "    FIND PCRE `a b` IN lv.\n"}, CLS, {"FAIL"}),
    ("BE-81/N", "BE-81", {CLS: "    FIND PCRE `a\\sb` IN lv.\n"}, CLS, {"PASS"}),
    ("BE-85/P", "BE-85", {CLS: "    TYPES tt_x TYPE STANDARD TABLE OF i WITH EMPTY KEY.\n    DATA lt_x TYPE tt_x.\n    SORT lt_x.\n"}, CLS, {"FAIL"}),
    ("BE-85/N", "BE-85", {CLS: "    TYPES tt_x TYPE STANDARD TABLE OF i WITH EMPTY KEY.\n    DATA lt_x TYPE tt_x.\n    SORT lt_x BY table_line.\n"}, CLS, {"PASS"}),
    ("BE-86/P", "BE-86", {CLS: "    lv_m = |{ lv_x ALPHA = OUT }|.\n"}, CLS, {"WARN"}),
    ("BE-86/N", "BE-86", {CLS: "    lv_m = condense( |{ lv_x ALPHA = OUT }| ).\n"}, CLS, {"PASS"}),
    ("BE-87/P", "BE-87", {CLS: "  \"! Tür açıklaması\n  TYPES: BEGIN OF ty_s,\n           f TYPE i,\n         END OF ty_s.\n"}, CLS, {"FAIL"}),
    ("BE-87/N", "BE-87", {CLS: "  \"! Metot açıklaması\n  METHODS m.\n"}, CLS, {"PASS"}),
    ("FE-01/P", "FE-01", {JS: "oModel.read(\"/HeaderSet('1')/_Items\", {});\n"}, JS, {"FAIL"}),
    ("FE-01/N", "FE-01", {JS: "oModel.read(\"/HeaderSet('1')/to_Items\", {});\n"}, JS, {"PASS"}),
    ("FE-06/P", "FE-06", {VIEW: XMLNS + "  <VBox>\n    <items>\n      <core:Title text=\"B\"/>\n    </items>\n  </VBox>\n</mvc:View>\n"}, VIEW, {"FAIL"}),
    ("FE-06/N", "FE-06", {VIEW: XMLNS + "  <f:SimpleForm>\n    <f:content>\n      <core:Title text=\"B\"/>\n    </f:content>\n  </f:SimpleForm>\n</mvc:View>\n"}, VIEW, {"PASS"}),
    ("FE-11/P", "FE-11", {"a/webapp/i18n/i18n.properties": "a=A\n", "a/webapp/i18n/i18n_tr.properties": "a=A\n",
                          VIEW: XMLNS + "  <Text text=\"{i18n>b}\"/>\n</mvc:View>\n"}, VIEW, {"FAIL"}),
    ("FE-11/N", "FE-11", {"a/webapp/i18n/i18n.properties": "a=A\n", "a/webapp/i18n/i18n_tr.properties": "a=A\n",
                          VIEW: XMLNS + "  <Text text=\"{i18n>a}\"/>\n</mvc:View>\n"}, VIEW, {"PASS"}),
    ("FE-13/P", "FE-13", {"a/webapp/view/List.view.xml": XMLNS + "  <Table>\n    <columns>\n" + "      <Column/>\n" * 6
                          + "    </columns>\n  </Table>\n</mvc:View>\n"}, "a/webapp/view/List.view.xml", {"FAIL"}),
    ("FE-13/N", "FE-13", {"a/webapp/view/List.view.xml": XMLNS.replace(">\n", ' xmlns:t="sap.ui.table">\n')
                          + "  <t:Table>\n    <t:columns>\n      <t:Column/>\n    </t:columns>\n  </t:Table>\n</mvc:View>\n"},
     "a/webapp/view/List.view.xml", {"PASS"}),
    ("FE-26/P", "FE-26", {"a/webapp/manifest.json": '{"sap.ui5": {"models": {"ui": {"type": "sap.ui.model.json.JSONModel",\n'
                          '  "settings": {"data": {"a": 1}}}}}}\n'}, "a/webapp/manifest.json", {"FAIL"}),
    ("FE-26/N", "FE-26", {"a/webapp/manifest.json": '{"sap.ui5": {"models": {"ui": {"type": "sap.ui.model.json.JSONModel",\n'
                          '  "settings": {"a": 1}}}}}\n'}, "a/webapp/manifest.json", {"PASS"}),
    ("FE-32/P", "FE-32", {JS: "oB.filter(new Filter({ path: 'A', operator: 'Contains', value1: s, caseSensitive: false }));\n"}, JS, {"FAIL"}),
    ("FE-32/N", "FE-32", {JS: "oB.filter(new Filter({ path: 'A', operator: 'Contains', value1: s }));\n"}, JS, {"ELLE"}),
    ("FE-33/P", "FE-33", {VIEW: XMLNS + "  <f:Form>\n    <f:FormElement>\n      <f:fields>\n        <HBox/>\n      </f:fields>\n"
                          "    </f:FormElement>\n  </f:Form>\n</mvc:View>\n"}, VIEW, {"FAIL"}),
    ("FE-33/N", "FE-33", {VIEW: XMLNS + "  <f:Form>\n    <f:FormElement>\n      <f:fields>\n        <Input/>\n      </f:fields>\n"
                          "    </f:FormElement>\n  </f:Form>\n</mvc:View>\n"}, VIEW, {"PASS"}),
    ("FE-35/P", "FE-35", {VIEW: XMLNS + "  <Text text=\"{OpenQty}\"/>\n</mvc:View>\n"}, VIEW, {"FAIL"}),
    ("FE-35/N", "FE-35", {VIEW: XMLNS + "  <Text text=\"{path: 'OpenQty', formatter: '.fmt'}\"/>\n  <Label text=\"{i18n>OpenQty}\"/>\n</mvc:View>\n"},
     VIEW, {"PASS"}),
    ("FE-42/P", "FE-42", {JS: "oModel.callFunction('/Kaydet', { method: 'POST', urlParameters: { Veri: JSON.stringify(aSatir) } });\n"}, JS, {"FAIL"}),
    ("FE-42/N", "FE-42", {JS: "oModel.callFunction('/Kaydet', { method: 'POST', urlParameters: { Id: sId } });\n"}, JS, {"PASS"}),
    ("FE-43/P", "FE-43", {JS: "var o = new sap.ui.model.odata.v2.ODataModel(\"/x/\", { useBatch: false });\n"}, JS, {"FAIL"}),
    ("FE-43/N", "FE-43", {JS: "var o = new sap.ui.model.odata.v2.ODataModel(\"/x/\", { metadataUrlParams: oAna.mMetadataUrlParams });\n"}, JS, {"PASS"}),
    ("FE-46/P", "FE-46", {"a/webapp/index.html": "<script id=\"sap-ui-bootstrap\" src=\"https://ui5.sap.com/resources/sap-ui-core.js\"></script>\n"},
     "a/webapp/index.html", {"FAIL"}),
    ("FE-46/N", "FE-46", {"a/webapp/index.html": "<script id=\"sap-ui-bootstrap\" src=\"/sap/public/bc/ui5_ui5/resources/sap-ui-core.js\"></script>\n"},
     "a/webapp/index.html", {"PASS"}),
    ("FE-47/P", "FE-47", {JS: "oModel.callFunction('/F', { urlParameters: { Tarih: null } });\n"}, JS, {"FAIL"}),
    ("FE-47/N", "FE-47", {JS: "oModel.callFunction('/F', { urlParameters: { Tarih: sTarih } });\n"}, JS, {"PASS"}),
    ("FE-49/P", "FE-49", {JS: "window.addEventListener(\"beforeunload\", function () {\n  var x = new XMLHttpRequest();\n"
                          "  x.open(\"POST\", sUrl, false);\n  x.send();\n});\n"}, JS, {"FAIL"}),
    ("FE-49/N", "FE-49", {JS: "window.addEventListener(\"beforeunload\", function () {\n  var x = new XMLHttpRequest();\n"
                          "  x.open(\"POST\", sUrl, true);\n  x.send();\n});\n"}, JS, {"PASS"}),
    ("FE-50/P", "FE-50", {VIEW: XMLNS + "  <MultiInput id=\"mi\"/>\n</mvc:View>\n"}, VIEW, {"FAIL"}),
    ("FE-50/N", "FE-50", {VIEW: XMLNS + "  <MultiInput id=\"mi\"/>\n</mvc:View>\n",
                          JS: "this.byId('mi').addValidator(function (o) { return o; });\n"}, VIEW, {"ELLE"}),
    ("FE-51/P", "FE-51", {VIEW: XMLNS + "  <Table mode=\"MultiSelect\" enableSelectAll=\"false\"/>\n</mvc:View>\n"}, VIEW, {"FAIL"}),
    ("FE-51/N", "FE-51", {VIEW: XMLNS + "  <Table mode=\"MultiSelect\" enableSelectAll=\"false\"/>\n</mvc:View>\n",
                          JS: "if (oEvent.getParameter(\"selectAll\")) { geriAl(); }\n"}, VIEW, {"PASS"}),
    ("DOC-KD-11/P", "DOC-KD-11", {"d/docs/KD-T.md": "# Kılavuz\n\n![ekran](img/yok.png)\n"}, "d/docs/KD-T.md", {"FAIL"}),
    ("DOC-KD-11/N", "DOC-KD-11", {"d/docs/KD-T.md": "# Kılavuz\n\n![ekran](img/var.png)\n", "d/docs/img/var.png": "x"},
     "d/docs/KD-T.md", {"ELLE"}),
    ("DOC-KD-13/P", "DOC-KD-13", {CLS: "    write_object_doc( ).\n    lo->add( iv_line = '" + "x" * 80 + "' ).\n"}, CLS, {"FAIL"}),
    ("DOC-KD-13/N", "DOC-KD-13", {CLS: "    write_object_doc( ).\n    lo->add( iv_line = 'kısa satır' ).\n"}, CLS, {"PASS"}),
    ("DOC-KD-15/P", "DOC-KD-15", {"d/docs/KD-T.html": "<pre class=\"mermaid\">flowchart TD</pre>\n"}, "d/docs/KD-T.html", {"FAIL"}),
    ("DOC-KD-15/P-md", "DOC-KD-15", {"d/docs/KD-T.md": "```mermaid\nflowchart TD\n```\n"}, "d/docs/KD-T.md", {"WARN"}),
    ("DOC-KD-15/N", "DOC-KD-15", {"d/docs/KD-T.html": "<img src=\"akis.png\">\n"}, "d/docs/KD-T.html", {"PASS"}),
    ("DOC-KD-16/P", "DOC-KD-16", {"d/docs/KD-T.md": "## Genel Bakis\n\n[git](#yok-baslik)\n"}, "d/docs/KD-T.md", {"FAIL"}),
    ("DOC-KD-16/N", "DOC-KD-16", {"d/docs/KD-T.md": "## Genel Bakis\n\n[git](#genel-bakis)\n"}, "d/docs/KD-T.md", {"PASS"}),
    ("DOC-KD-16/P-html", "DOC-KD-16", {"d/docs/KD-T.html": "<a href=\"#x\">x</a>\n"}, "d/docs/KD-T.html", {"FAIL"}),
    ("DOC-KD-16/N-html", "DOC-KD-16", {"d/docs/KD-T.html": "<h2 id=\"x\">X</h2>\n<a href=\"#x\">x</a>\n"}, "d/docs/KD-T.html", {"PASS"}),
    ("DOC-FS-05/P", "DOC-FS-05", {"d/docs/FS-T.md": "# FS\n\nBu kural DEV'de ölçüldü.\n"}, "d/docs/FS-T.md", {"WARN"}),
    ("DOC-FS-05/N", "DOC-FS-05", {"d/docs/FS-T.md": "# FS\n\nSistem siparişi kaydeder.\n"}, "d/docs/FS-T.md", {"ELLE"}),
    ("DOC-FS-06a/P", "DOC-FS-06a", {"d/docs/FS-T.md": "# FS\n\n| Versiyon | Tarih | Açıklama |\n|---|---|---|\n| 1.0 | 01.01.2026 | "
                                    + "a" * 420 + " |\n"}, "d/docs/FS-T.md", {"WARN"}),
    ("DOC-FS-06a/N", "DOC-FS-06a", {"d/docs/FS-T.md": "# FS\n\n| Versiyon | Tarih | Açıklama |\n|---|---|---|\n| 1.0 | 01.01.2026 | ilk |\n"},
     "d/docs/FS-T.md", {"PASS"}),
    ("DOC-FS-07/P", "DOC-FS-07", {"d/docs/FS-T.md": "# FS\n\nFR-01 kuralı.\n"}, "d/docs/FS-T.md", {"FAIL"},
     "# FS\n\nFR-01 ve FR-02 kuralı.\n"),
    ("DOC-FS-07/N", "DOC-FS-07", {"d/docs/FS-T.md": "# FS\n\nFR-01 ve FR-02 kuralı (yeniden yazıldı).\n"}, "d/docs/FS-T.md", {"ELLE"},
     "# FS\n\nFR-01 ve FR-02 kuralı.\n"),
    ("DOC-TS-05/P", "DOC-TS-05", {"d/docs/TS-T.md": TS_MESAJ.replace("{M}", "Kayıt & bulunamadı")}, "d/docs/TS-T.md", {"FAIL"}),
    ("DOC-TS-05/N", "DOC-TS-05", {"d/docs/TS-T.md": TS_MESAJ.replace("{M}", "Kayıt &1 bulunamadı")}, "d/docs/TS-T.md", {"ELLE"}),
]


def dosyalari_yaz(kok: Path, dosyalar: dict[str, str]) -> None:
    for rel, icerik in dosyalar.items():
        p = kok / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(icerik.encode("utf-8"))      # LF korunur (write_text CRLF'e çevirirdi)


def degerlendir(G, harita: dict, kok: Path, dosyalar: dict[str, str], hedef: str, mid: str,
                eski: str | None = None, sap: bool = False):
    dosyalari_yaz(kok, dosyalar)
    ds = [G.Dosya(rel, icerik, yol=kok / rel, eski_kaynak=(eski if rel == hedef else None))
          for rel, icerik in dosyalar.items()]
    c = G.Baglam(kok, ds, sap=sap, sap_kok=kok)
    madde = harita[mid]
    secilen = [d for d in ds if G.glob_eslesir(d.rel, madde.get("uygulanir") or [])]
    if hedef not in [d.rel for d in secilen]:
        return None, f"hedef `{hedef}` maddenin globuna girmedi ({madde.get('uygulanir')})"
    secilen = [d for d in secilen if d.rel == hedef]
    s = G.degerlendir(madde, secilen, c)
    return s, f"{s.sonuc} · {s.kanit[:110]}"


def a_vektorleri(G, harita: dict, tmp: Path) -> None:
    for i, v in enumerate(VEKTORLER):
        ad, mid, dosyalar, hedef, beklenen = v[:5]
        eski = v[5] if len(v) > 5 else None
        s, detay = degerlendir(G, harita, tmp / f"a{i}", dosyalar, hedef, mid, eski)
        kontrol(f"{ad} {'pozitif' if '/P' in ad else 'negatif'} beklenen={sorted(beklenen)}",
                s is not None and s.sonuc in beklenen, detay)
    # K0: kontrolü olan her A maddesinin pozitif VE negatif vektörü var mı (map'ten türetilir)
    eksik = []
    for mid, m in harita.items():
        if m.get("sinif") != "A" or not m.get("kontrol"):
            continue
        yonler = {v[0].split("/", 1)[1][0] for v in VEKTORLER if v[1] == mid}
        if not {"P", "N"} <= yonler:
            eksik.append(f"{mid}({''.join(sorted(yonler)) or '-'})")
    kontrol("K0 kontrolü olan her A maddesinin pozitif+negatif vektörü var", not eksik, f"eksik: {eksik}")


# ═══════════════════════════════════════════════════════════════ T: BE-10b ══
def t_vektorleri(G) -> None:
    def bant(metin):
        return G.yorum_bantlari(metin)

    OL, OLM = G.OLCULMUS, G.OLCULMEMIS
    impl = ("CLASS zcl_t DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    METHODS m1.\nENDCLASS.\n"
            "CLASS zcl_t IMPLEMENTATION.\n{A}  METHOD m1.\n  ENDMETHOD.\n{B}ENDCLASS.\n{C}")
    kume = bant(impl.format(A="* baş\n", B="", C=""))
    kontrol("T1 `CLASS … IMPLEMENTATION.` ↔ ilk METHOD → ölçülmüş", [(b[0], b[3]) for b in kume] == [(6, OL)], repr(kume))
    kume = bant(SINIF_ARA.replace("{ARA}", "* ara 1\n\n* ara 2\n"))
    kontrol("T2 ENDMETHOD ↔ METHOD (boş satırlı bant tek bant) → ölçülmüş",
            [(b[0], b[1], b[3]) for b in kume] == [(9, 11, OL)], repr(kume))
    kume = bant(impl.format(A="", B="* son\n", C=""))
    kontrol("T3 son ENDMETHOD ↔ ENDCLASS → ölçülmemiş", [(b[0], b[3]) for b in kume] == [(8, OLM)], repr(kume))
    kume = bant(impl.format(A="", B="", C="* dosya sonu\n"))
    kontrol("T4 IMPLEMENTATION `ENDCLASS.` sonrası → ölçülmemiş", [(b[0], b[3]) for b in kume] == [(9, OLM)], repr(kume))
    ara_def = ("CLASS zcl_t DEFINITION PUBLIC.\n  PUBLIC SECTION.\nENDCLASS.\n* araya\nCLASS zcl_t IMPLEMENTATION.\n"
               "  METHOD m1.\n  ENDMETHOD.\nENDCLASS.\n")
    kume = bant(ara_def)
    kontrol("T5 DEFINITION `ENDCLASS.` ↔ `CLASS … IMPLEMENTATION.` → ölçülmemiş", [(b[0], b[3]) for b in kume] == [(4, OLM)], repr(kume))
    kume = bant(SINIF_ARA.replace("{ARA}", "    \" girintili yorum\n"))
    kontrol("T6 girintili `\"` metotlar arasında yorum sayılır → ölçülmüş bant", [(b[0], b[3]) for b in kume] == [(9, OL)], repr(kume))
    serbest = ("* dosya başı yorumu serbest\n\" başlık\nCLASS zcl_t DEFINITION PUBLIC.\n  \" tanımda yorum serbest\n"
               "* tanımda yıldız serbest\n  PUBLIC SECTION.\n    METHODS m1.\nENDCLASS.\nCLASS zcl_t IMPLEMENTATION.\n"
               "  METHOD m1.\n* gövdede yıldız serbest\n    \" gövdede tırnak serbest\n  ENDMETHOD.\nENDCLASS.\n")
    kume = bant(serbest)
    kontrol("T7 serbest bölgeler (dosya başı · DEFINITION · metot gövdesi) bant üretmez", kume == [], repr(kume))
    d = G.Dosya("p/classes/zcl_t.clas.abap", impl.format(A="* baş\n", B="* son\n", C=""))
    msj = [b.mesaj for b in G.k_be10b(d, None)]
    ok = (len(msj) == 2 and "[ölçülmüş konum]" in msj[0] and "ölçülmemiş konum" not in msj[0]
          and "ölçülmemiş konum" in msj[1] and "ÖLÇÜLMEDİ" in msj[1] and "[ölçülmüş konum]" not in msj[1])
    kontrol("T8 mesaj etiketi: ölçülmüş ↔ 'ölçülmemiş konum … ÖLÇÜLMEDİ' AYRI kesinlikte", ok, repr(msj))
    yildiz = SINIF_ARA.replace("{ARA}", "   * sütun 1 değil\n")
    kume = bant(yildiz)
    kontrol("T9 `*` yalnız 1. sütunda yorum: girintili `*` bant sayılmaz", kume == [], repr(kume))


# ═══════════════════════════════════════════════════════════════ C / B ══
def cb_vektorleri(G, harita: dict, tmp: Path) -> None:
    s, d = degerlendir(G, harita, tmp / "c1", {CLS: "    SELECT SINGLE * FROM but000 INTO @DATA(ls).\n"}, CLS, "BE-19")
    kontrol("C1 C ipucu aday bulsa da hüküm ELLE (kanıtta 'ipucu')", s is not None and s.sonuc == "ELLE" and "ipucu" in s.kanit, d)
    s, d = degerlendir(G, harita, tmp / "c2", {VIEW: XMLNS + "  <Input type=\"Number\"/>\n</mvc:View>\n"}, VIEW, "FE-07")
    kontrol("C2 FE-07 ipucu (type=Number) → ELLE", s is not None and s.sonuc == "ELLE" and "ipucu" in s.kanit, d)
    s, d = degerlendir(G, harita, tmp / "b1", {CLS: "    lv = 1.\n"}, CLS, "BE-88")
    kontrol("B1 BE-88 `--sap` yok → ÖLÇÜLEMEDİ", s is not None and s.sonuc == "ÖLÇÜLEMEDİ", d)
    s, d = degerlendir(G, harita, tmp / "b2", {CLS: "  METHOD m.\n    lv = 1.\n  ENDMETHOD.\n"}, CLS, "BE-88", sap=True)
    kontrol("B2 BE-88 `--sap` var, `.conn_adt` yok → ÖLÇÜLEMEDİ (temiz DEĞİL)", s is not None and s.sonuc == "ÖLÇÜLEMEDİ", d)
    s, d = degerlendir(G, harita, tmp / "b3", {CLS: "    lv = 1.\n"}, CLS, "BE-80")
    kontrol("B3 kontrolsüz B maddesi → ELLE", s is not None and s.sonuc == "ELLE", d)


# ═══════════════════════════════════════════════════════════ S: tohum paketi ══
TOHUM_CLS_1 = ("CLASS zcl_tohum DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    METHODS m1.\n    METHODS m2.\nENDCLASS.\n"
               "CLASS zcl_tohum IMPLEMENTATION.\n  METHOD m1.\n    lv = |{ lv_a }|{ lv_b }|.\n  ENDMETHOD.\n"
               "  METHOD m2.\n  ENDMETHOD.\nENDCLASS.\n")
TOHUM_CLS_2 = ("CLASS zcl_tohum DEFINITION PUBLIC.\n  PUBLIC SECTION.\n    \"! Tür\n    TYPES: BEGIN OF ty_s,\n"
               "             f TYPE i,\n           END OF ty_s.\n    TYPES tt_x TYPE STANDARD TABLE OF i WITH EMPTY KEY.\n"
               "    METHODS m1.\n    METHODS m2.\nENDCLASS.\n"
               "CLASS zcl_tohum IMPLEMENTATION.\n  METHOD m1.\n    lv = |{ lv_a }|{ lv_b }|.\n  ENDMETHOD.\n"
               "* m2 açıklaması\n  METHOD m2.\n    DATA lt_x TYPE tt_x.\n    SORT lt_x.\n  ENDMETHOD.\nENDCLASS.\n")
TOHUM_JS_1 = "sap.ui.define([], function () {\n  return {};\n});\n"
TOHUM_JS_2 = ("sap.ui.define([], function () {\n  oModel.read(\"/HeaderSet('1')/_Items\", {});\n"
              "  oModel.callFunction('/F', { urlParameters: { Tarih: null } });\n  return {};\n});\n")
TOHUM_HTML_1 = "<script id=\"sap-ui-bootstrap\" src=\"/sap/public/bc/ui5_ui5/resources/sap-ui-core.js\"></script>\n"
TOHUM_HTML_2 = "<script id=\"sap-ui-bootstrap\" src=\"https://ui5.sap.com/resources/sap-ui-core.js\"></script>\n"
TOHUM_KD_1 = "## Genel Bakis\n\nMetin.\n"
TOHUM_KD_2 = "## Genel Bakis\n\nMetin. [git](#yok-baslik)\n"
TOHUM_HATALAR = {"BE-10b", "BE-85", "BE-87", "FE-01", "FE-46", "FE-47", "DOC-KD-16"}


def _git(kok: Path, *a: str) -> None:
    subprocess.run(["git", "-C", str(kok), "-c", "user.name=fixture", "-c", "user.email=fixture@localhost",
                    "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *a],
                   check=True, capture_output=True)


def s_vektorleri(G, tmp: Path) -> None:
    kok = tmp / "tohum"
    kok.mkdir()
    try:
        _git(kok, "init", "-q")
    except Exception as e:
        for ad in ("S1", "S2", "S3", "S4", "S5"):
            ATLA.append((ad, f"git yok ({type(e).__name__})"))
        return
    yollar = {"pkg/classes/zcl_tohum.clas.abap": (TOHUM_CLS_1, TOHUM_CLS_2),
              "app/webapp/controller/Main.controller.js": (TOHUM_JS_1, TOHUM_JS_2),
              "app/webapp/index.html": (TOHUM_HTML_1, TOHUM_HTML_2),
              "app/docs/KD-TOHUM.md": (TOHUM_KD_1, TOHUM_KD_2)}
    dosyalari_yaz(kok, {r: v[0] for r, v in yollar.items()})
    _git(kok, "add", "-A")
    _git(kok, "commit", "-q", "-m", "taban")
    dosyalari_yaz(kok, {r: v[1] for r, v in yollar.items()})
    _git(kok, "add", "-A")
    _git(kok, "commit", "-q", "-m", "hatalar")
    rc, out = kos(G, ["--repo", str(kok), "--diff", "HEAD~1..HEAD", "--kind", "auto"])
    t = tablo(out)
    yakalanan = {i for i in TOHUM_HATALAR if t.get(i, "").startswith("FAIL")}
    kontrol(f"S1 tohum paketi: {len(TOHUM_HATALAR)} bilinen hatanın hepsi FAIL + exit 1 (blok BE-10b)",
            yakalanan == TOHUM_HATALAR and rc == 1,
            f"rc={rc} kaçan={sorted(TOHUM_HATALAR - yakalanan)}")
    kontrol("S2 önceden var olan BE-47 (değişmeyen satır) diff kipinde WARN '(önceden var)'",
            t.get("BE-47", "").startswith("WARN") and "önceden var" in t.get("BE-47", ""), t.get("BE-47", "YOK"))
    rc2, out2 = kos(G, ["--repo", str(kok), "--files", "pkg/classes/zcl_tohum.clas.abap", "--kind", "backend"])
    t2 = tablo(out2)
    kontrol("S3 `--files` kipinde önceden var olan BE-47 FAIL + KAPSAM BEYANI bunu söyler",
            t2.get("BE-47", "").startswith("FAIL") and "önceden var olan ihlaller de FAIL sayılır" in out2,
            t2.get("BE-47", "YOK"))
    kontrol("S4 BE-10b satırı `FAIL (BLOK)` + ENGELLEYİCİ satırı",
            t.get("BE-10b", "").startswith("FAIL (BLOK)") and "ENGELLEYİCİ: BE-10b" in out, t.get("BE-10b", "YOK"))
    kontrol("S5 tablo başlığı altında kanonik hüküm satırı + KAPSAM BEYANI",
            G.HUKUM_SATIRI in out and "### KAPSAM BEYANI" in out and "ÇÜRÜTÜLDÜ" in G.HUKUM_SATIRI, out[:200])


# ═══════════════════════════════════════════════════════ V: --verify-report ══
def v_vektorleri(G, tmp: Path) -> None:
    kok = tmp / "verify"
    dosyalari_yaz(kok, {CLS: "    lv = |{ lv_a }|{ lv_b }|.\n    DATA lv_t TYPE char40.\n"})
    taban = ["--repo", str(kok), "--files", CLS, "--kind", "backend", "--ids", "BE-47,BE-35"]
    bas = "| ID | Sınıf | Sonuç | Kanıt |\n|---|---|---|---|\n"

    def dene(ad, govde, beklenen_rc, isaret, aciklama):
        r = kok / f"{ad}.md"
        r.write_bytes((bas + govde).encode("utf-8"))
        rc, out = kos(G, taban + ["--verify-report", str(r)])
        ok = rc == beklenen_rc and all(x in out for x in isaret)
        kontrol(f"{ad} {aciklama}", ok, f"rc={rc} beklenen={beklenen_rc} · {out[out.find('### --verify'):][:260]!r}")

    tam47 = "| BE-47 | A | FAIL→F1 | satır 1 şablonda kaçışsız `}|{` |\n"
    tam35 = "| BE-35 | A | PASS | char40 güvenli aralıkta |\n"
    dene("V1", tam47 + tam35, 0, ["- satır yok: 0", "- kanıtsız: 0"], "tam rapor → exit 0")
    dene("V2", tam47, 1, ["- satır yok: 1 → BE-35", "RAPOR EKSİK: satır yok"], "satır eksik → exit 1 + kategori")
    dene("V3", tam47 + "| BE-35 | A | ELLE | |\n", 1, ["- ELLE: 1 → BE-35"], "ELLE bırakılmış → exit 1")
    dene("V4", "| BE-47 | A | PASS | bence sorun yok |\n" + tam35, 1, ["- ÇELİŞKİ: 1 → BE-47"], "program A-FAIL, rapor PASS → ÇELİŞKİ")
    dene("V5", "| BE-47 | A | ÇÜRÜTÜLDÜ | `}|{` literal içinde, şablon değil; derleme kanıtı ekte |\n" + tam35, 0,
         ["- ÇELİŞKİ: 0", "ÇÜRÜTÜLDÜ — korpus kalibrasyon adayı (1", "BE-47 (program: FAIL)"],
         "kanıtlı ÇÜRÜTÜLDÜ kabul + kalibrasyon listesinde")
    dene("V6", "| BE-47 | A | ÇÜRÜTÜLDÜ | |\n" + tam35, 1, ["- kanıtsız: 1 → BE-47"], "kanıtsız ÇÜRÜTÜLDÜ reddedilir")
    dene("V7", "| BE-47 | A | BULGU | satır 1 |\n" + tam35, 1, ["- hükümsüz: 1 → BE-47"], "sözlük dışı kelime → hükümsüz")
    dene("V8", "| BE-47 | A | FAIL→F1 | |\n" + tam35, 1, ["- kanıtsız: 1 → BE-47"], "yalnız `FAIL→F1` kanıt sayılmaz")
    rc, out = kos(G, taban + ["--verify-report", str(kok / "yok-rapor.md")])
    kontrol("V9 okunamayan rapor → exit 2 [PROGRAM KOŞMADI] (eksiklik DEĞİL)",
            rc == 2 and "[PROGRAM KOŞMADI]" in out, f"rc={rc} {out[-160:]!r}")


# ═════════════════════════════════════════════════════════════ X: exit kodları ══
def x_vektorleri(G, tmp: Path) -> None:
    rc, out = kos(G, [])
    kontrol("X1 argümansız → exit 2 (kullanım)", rc == 2, f"rc={rc}")
    rc, out = kos(G, ["--repo", str(tmp / "yok-dizin"), "--files", "a.abap"])
    kontrol("X2 --repo dizin değil → exit 2", rc == 2, f"rc={rc}")
    bozuk = tmp / "bozuk.yaml"
    bozuk.write_bytes("maddeler:\n  - id: BE-01\n    bu satır ayrıştırılamaz\n".encode("utf-8"))
    (tmp / "x").mkdir(exist_ok=True)
    dosyalari_yaz(tmp / "x", {CLS: "    lv = 1.\n"})
    rc, out = kos(G, ["--repo", str(tmp / "x"), "--files", CLS, "--harita", str(bozuk)])
    kontrol("X3 bozuk map (normal kip) → exit 2 [PROGRAM KOŞMADI]", rc == 2 and "[PROGRAM KOŞMADI]" in out, f"rc={rc} {out[:160]!r}")
    rc, out = kos(G, ["--harita-denetim", "--harita", str(tmp / "olmayan.yaml")])
    kontrol("X4 eksik map (--harita-denetim) → exit 2 [PROGRAM KOŞMADI]", rc == 2 and "[PROGRAM KOŞMADI]" in out, f"rc={rc} {out[:160]!r}")
    asil = G.girdileri_topla

    def patla(*_a, **_k):
        raise ZeroDivisionError("enjekte")
    G.girdileri_topla = patla
    try:
        rc, out = kos(G, ["--repo", str(tmp / "x"), "--files", CLS])
    finally:
        G.girdileri_topla = asil
    kontrol("X5 beklenmeyen istisna → exit 2 `[PROGRAM KOŞMADI] ZeroDivisionError: enjekte`",
            rc == 2 and "[PROGRAM KOŞMADI] ZeroDivisionError: enjekte" in out, f"rc={rc} {out[:160]!r}")
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        rc = G.main(["--help"])
    kontrol("X6 --help hüküm sözlüğünü basar, exit 0", rc == 0 and "FAIL→F<n>" in tampon.getvalue()
            and "ÇÜRÜTÜLDÜ" in tampon.getvalue(), f"rc={rc}")


# ═══════════════════════════════════════════════════════ H: --harita-denetim ══
def h_vektorleri(G, tmp: Path) -> None:
    rc, out = kos(G, ["--harita-denetim"])
    kontrol("H1 gerçek map ↔ checklist ↔ kontrol tutarlı (exit 0)", rc == 0 and "[OK]" in out, out[-300:])
    metin = MAP.read_bytes().decode("utf-8")

    def madde_blogu(mid):
        i = metin.index(f"  - id: {mid}\n")
        j = metin.find("\n  - id: ", i + 1)
        return i, (j + 1 if j >= 0 else len(metin))

    def dene(ad, yeni, isaret, aciklama):
        p = tmp / f"{ad}.yaml"
        p.write_bytes(yeni.encode("utf-8"))
        rc, out = kos(G, ["--harita-denetim", "--harita", str(p)])
        kontrol(f"{ad} {aciklama}", rc == 1 and isaret in out, f"rc={rc} {out[-260:]!r}")

    i, j = madde_blogu("BE-47")
    blok = metin[i:j]
    dene("H2", metin[:i] + blok.rstrip("\n") + "\n    zirva: x\n" + metin[j:], "zirva", "bilinmeyen alan → exit 1")
    blok2 = "\n".join(s for s in blok.splitlines() if not s.strip().startswith(("kontrol:", "not:"))) + "\n"
    dene("H3", metin[:i] + blok2 + metin[j:], "BE-47", "kontrolsüz ve `not`suz A → exit 1")
    dene("H4", metin[:i] + blok.replace("seviye: uyari", "seviye: blok") + metin[j:], "BE-47", "blok yalnız BE-10b → exit 1")


# ═══════════════════════════════════════ R: --reach · YAML eşliği · run_review ══
def r_vektorleri(G, tmp: Path) -> None:
    p = tmp / "reach.yaml"
    p.write_bytes(("maddeler:\n  - id: BE-10b\n    yazan_kanali: playbook/checklists/bug-checklist-backend.md\n").encode("utf-8"))
    rc, out = kos(G, ["--reach", "--harita", str(p)])
    kontrol("R1 --reach: yazan_kanali dosyasında ID geçiyor → PASS exit 0", rc == 0 and "| BE-10b |" in out and "PASS" in out, out[-200:])
    p.write_bytes(("maddeler:\n  - id: BE-10b\n    yazan_kanali: claude/agents/olmayan-ajan.md\n").encode("utf-8"))
    rc, out = kos(G, ["--reach", "--harita", str(p)])
    kontrol("R2 --reach: yazan_kanali dosyası yok → FAIL exit 1", rc == 1 and "dosya yok" in out, out[-200:])
    try:
        import yaml  # type: ignore
    except Exception:
        ATLA.append(("R3", "PyYAML kurulu değil — mini ayrıştırıcı eşliği ölçülmedi"))
    else:
        resmi = (yaml.safe_load(MAP.read_text(encoding="utf-8")) or {}).get("maddeler")
        mini = G.harita_oku(MAP)
        fark = [a.get("id") for a, b in zip(resmi or [], mini) if a != b]
        kontrol("R3 mini YAML ayrıştırıcı == yaml.safe_load (gerçek map)",
                resmi == mini, f"len {len(resmi or [])}/{len(mini)} fark={fark[:5]}")
    kirli = tmp / "rr" / "ZCL_RR.abap"
    temiz = tmp / "rr" / "zcl_rr2.clas.abap"
    dosyalari_yaz(tmp / "rr", {"ZCL_RR.abap": SINIF_ARA.replace("{ARA}", "* bant\n").replace("zcl_t", "zcl_rr"),
                               "zcl_rr2.clas.abap": SINIF_ARA.replace("{ARA}", "").replace("zcl_t", "zcl_rr2")})
    for ad, yol, beklenen_blok in (("R4", kirli, True), ("R5", temiz, False)):
        r = subprocess.run([sys.executable, str(RUN_REVIEW), "--task", "class_push", "--artifact", str(yol)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        out = r.stdout + r.stderr
        satir = next((s for s in out.splitlines() if s.strip().endswith("checklist_check.py")), "")
        if beklenen_blok:
            ok = r.returncode != 0 and "✗ [BLOCKER] checklist_check.py" in satir and "VERDICT: BLOCKER" in out \
                and "[ölçülmüş konum]" in out
        else:
            ok = "✓ [BLOCKER] checklist_check.py" in satir and "| BE-10b | A | PASS |" in out
        kontrol(f"{ad} run_review class_push (gerçek CLI, ad `.clas.abap` {'değil' if beklenen_blok else 'olan'}) → "
                f"{'BLOCKER' if beklenen_blok else 'PASS'}", ok, f"rc={r.returncode} satır={satir!r}")


def main(kip: str | None) -> int:
    kaynak = PROG.read_bytes().decode("utf-8")
    if kip:
        eski, yeni = _MUT[kip]
        n = kaynak.count(eski)
        if n != 1:
            sys.stderr.write("[DOGRULANAMADI] mutasyon capasi %d kez eslesti (beklenen 1): %s "
                             "-> hicbir sayi raporlanmadi.\n" % (n, kip))
            return 3
        kaynak = kaynak.replace(eski, yeni, 1)
        print("mutasyon:", kip)
        try:
            compile(kaynak, str(PROG), "exec")
        except SyntaxError as e:
            sys.stderr.write("[DOGRULANAMADI] mutant DERLENMEDI (%s): %s\n" % (kip, e))
            return 3
    G = yukle(kaynak)
    harita = {m["id"]: m for m in G.harita_oku(MAP)}
    tmp = Path(tempfile.mkdtemp(prefix="cc_fx_"))
    try:
        a_vektorleri(G, harita, tmp)
        t_vektorleri(G)
        cb_vektorleri(G, harita, tmp)
        s_vektorleri(G, tmp)
        v_vektorleri(G, tmp)
        x_vektorleri(G, tmp)
        h_vektorleri(G, tmp)
        r_vektorleri(G, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    hata = 0
    for ad, ok, detay in SONUC:
        hata += 0 if ok else 1
        print("[%s] %-78s %s" % ("ok" if ok else "FAIL", ad, "" if ok else detay))
    for ad, neden in ATLA:
        print("[ATLA] %s — %s" % (ad, neden))
    gecen = len(SONUC) - hata
    print("%d/%d OK" % (gecen, len(SONUC)) + (" · %d ATLA" % len(ATLA) if ATLA else ""))
    if kip:
        dusen = {ad.split()[0] for ad, ok, _ in SONUC if not ok}
        beklenen = _BEKLENEN_DUSEN[kip] - {a for a, _ in ATLA}
        if dusen != beklenen:
            print("[SAPMA] %s: beklenen=%s dusen=%s fazla=%s eksik=%s -> exit 2"
                  % (kip, sorted(beklenen), sorted(dusen), sorted(dusen - beklenen), sorted(beklenen - dusen)))
            return 2
        print("[BEKLENEN] %s: dusen kume = beklenen %s" % (kip, sorted(beklenen)))
        return 1
    return 1 if hata else 0


if __name__ == "__main__":
    kip = None
    for _a in sys.argv[1:]:
        if _a.startswith("--mutasyon"):
            if _a not in _GECERLI_KIP:
                print("[KULLANIM] bilinmeyen mutasyon kipi: %s · gecerli kipler: %s"
                      % (_a, ", ".join(sorted(_GECERLI_KIP))))
                sys.exit(3)
            kip = _a
    sys.exit(main(kip))
