#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""populate_tables: CURR alani unitOfMeasure aliyordu (B-13) + CSV kolon sozlesmesi (B-9/B-14).

KOK: build_ddl karari `type == 'CURR'` ile veriyordu. CSV'nin `type` kolonu ABAP veri
tipi DEGIL, DTEL adidir ('netwr', 'menge_d'). Kosul HICBIR ZAMAN tutmuyordu -> currency
dali ULASILAMAZ olu koddu; her tutar alani @Semantics.quantity.unitOfMeasure aliyordu.
Uretici (populate_tables) ile denetci (check_cds_currency_reference) celisiyordu:
denetci 'netwr'i CURR sayip amount.currencyCode bekler ve yoklugunu BLOCKER isaretler.

FIX: karar (1) acik CSV kolonu `unit_kind`, (2) yoksa PAYLASILAN DTEL sozlugu
(utils/ddic_semantics.py -- denetci ile AYNI kaynak), (3) o da bilmiyorsa 'quantity'
(eski davranis) + GORUNUR uyari. Gecersiz unit_kind = FAIL-CLOSED hata.

Bu korpus S(enaryo) + M(utasyon) tasir:
  S1-S4  uc-baglam + ozel-DTEL: dogru annotation uretiliyor mu
  S5-S8  CSV kolon sozlesmesi: eksik/ekstra/gecersiz/hic-yok
  M1-M4  fix'i sok -> korpus KIRMIZI olmali (yesil kalirsa korpus bu degismezi olcmuyor)

Kosum: python tests/fixtures/populate_tables_unit_kind/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import io
import re
import sys
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SCRIPTS = CORE / "scripts"
PT_PATH = SCRIPTS / "populate_tables.py"
DS_PATH = SCRIPTS / "utils" / "ddic_semantics.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


# ---------------------------------------------------------------------------
# Yukleyici — mutasyon icin KAYNAK METNI yamalanabilir surumu yukler.
# ---------------------------------------------------------------------------
pt_mod_refs: list = []   # GC-koruma: modulun kurdugu stdout wrapper'lari


def load(pt_mut=None, ds_mut=None):
    """populate_tables + utils.ddic_semantics'i TAZE namespace'e yukler.

    ⚠ populate_tables import aninda `io.TextIOWrapper(sys.stdout.buffer)` kurar
    (win32 dali). Sadece sys.stdout'u geri koymak YETMEZ: o wrapper GC'ye girince
    sardigi GERCEK buffer'i KAPATIR -> sonraki print "I/O operation on closed file"
    ile patlar (olculdu). Bu yuzden import sirasinda stdout'u ATILABILIR bir
    BytesIO'ya baglayip wrapper'i ona sardiriyoruz; gercek stdout'a hic dokunulmaz.
    """
    ds_src = DS_PATH.read_text(encoding="utf-8")
    pt_src = PT_PATH.read_text(encoding="utf-8")
    if ds_mut:
        ds_src = ds_mut(ds_src)
    if pt_mut:
        pt_src = pt_mut(pt_src)

    ds_mod = types.ModuleType("utils.ddic_semantics")
    ds_mod.__file__ = str(DS_PATH)
    exec(compile(ds_src, str(DS_PATH), "exec"), ds_mod.__dict__)

    saved_mod = sys.modules.get("utils.ddic_semantics")
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.modules["utils.ddic_semantics"] = ds_mod
    # Atilabilir buffer'lar — modulun stdout gaspi buraya yonlensin
    cop_out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    cop_err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    sys.stdout, sys.stderr = cop_out, cop_err
    try:
        pt_mod = types.ModuleType("populate_tables")
        pt_mod.__file__ = str(PT_PATH)
        exec(compile(pt_src, str(PT_PATH), "exec"), pt_mod.__dict__)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
        # Modulun kurdugu wrapper'lari canli tut (GC -> close zincirini kes)
        pt_mod_refs.append((cop_out, cop_err))
        if saved_mod is None:
            sys.modules.pop("utils.ddic_semantics", None)
        else:
            sys.modules["utils.ddic_semantics"] = saved_mod
    return pt_mod


def fld(name, typ, key="N"):
    return {"name": name, "is_key": key, "type": typ, "description": name.lower()}


def annotations_of(ddl: str, field: str) -> list[str]:
    """Alanin HEMEN USTUNDEKI @annotation satirlari (DDIC kurali: bitisik olmali)."""
    out, pending = [], []
    for line in ddl.splitlines():
        s = line.strip()
        if s.startswith("@"):
            pending.append(s)
            continue
        m = re.match(r"^(?:key\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*:", s)
        if m:
            if m.group(1).lower() == field.lower():
                return pending
            pending = []
        elif s:
            pending = []
    return out


# ---------------------------------------------------------------------------
# Gercek korpustan turetilmis sekiller (adlar jenerik: ZSD001 = core placeholder)
# ---------------------------------------------------------------------------
QUAN_ONLY = dict(
    table_name="ZSD001_T_TRANS",
    fields=[fld("MANDT", "MANDT", "Y"), fld("MENGE", "menge_d"), fld("MEINS", "meins")],
    unit_refs={"menge": "meins"},
)
CURR_ONLY = dict(
    table_name="ZSD001_T_AMTIT",
    fields=[fld("MANDT", "MANDT", "Y"), fld("NETWR_REF", "netwr"), fld("WAERK", "waerk")],
    unit_refs={"netwr_ref": "waerk"},
)
MIXED = dict(
    table_name="ZSD001_T_MIXIT",
    fields=[fld("MANDT", "MANDT", "Y"), fld("MENGE", "menge_d"), fld("VRKME", "vrkme"),
            fld("NETWR_REF", "netwr"), fld("WAERK", "waerk")],
    unit_refs={"menge": "vrkme", "netwr_ref": "waerk"},
)
CUSTOM_DTEL = dict(  # miktar alani Z'li DTEL -> sinif ancak REFERANS DTEL'inden cikar
    table_name="ZSD001_T_DORIT",
    fields=[fld("MANDT", "MANDT", "Y"), fld("QUANTITY", "ZSD001_E_ORDQTY"),
            fld("SALES_UNIT", "vrkme")],
    unit_refs={"quantity": "sales_unit"},
)


def ddl_of(pt, spec, unit_kinds=None):
    return pt.build_ddl(spec["table_name"], "Test", "A", "ALLOWED",
                        spec["fields"], spec["unit_refs"], unit_kinds or {})


def run_main(pt, csv_text: str, tmp_name: str):
    """main()'i CSV kolon sozlesmesi icin kosar. Kolon kontrolleri SAP'ye
    dokunmadan once donduğu icin baglanti gerekmez."""
    p = HERE / tmp_name
    p.write_text(csv_text, encoding="utf-8")
    buf = io.StringIO()
    saved_argv, saved_out = sys.argv, sys.stdout
    sys.argv = ["populate_tables.py", "--package", "ZSD001_CLC",
                "--transport", "DUMMY", "--csv", str(p), "--dry-run"]
    sys.stdout = buf
    try:
        try:
            rc = pt.main()
        except BaseException as e:          # SAPADTClient() offline patlayabilir
            rc = "EXC:%s" % type(e).__name__
    finally:
        sys.argv, sys.stdout = saved_argv, saved_out
        p.unlink(missing_ok=True)
    return rc, buf.getvalue()


HDR8 = "table_name,table_desc,delivery_class,data_maint,field_name,is_key,type,description"
HDR9 = HDR8 + ",unit_field"
HDR10 = HDR9 + ",unit_kind"


# ---------------------------------------------------------------------------
# SENARYOLAR
# ---------------------------------------------------------------------------
def senaryolar(pt) -> list[tuple[str, bool, str]]:
    r = []

    # S1 — QUAN-only (MEVCUT tuketici sekli): eski davranis AYNEN surmeli
    d = ddl_of(pt, QUAN_ONLY)
    r.append(("S1 QUAN-only menge->meins: quantity.unitOfMeasure",
              "@Semantics.quantity.unitOfMeasure : 'zsd001_t_trans.meins'" in annotations_of(d, "menge"),
              str(annotations_of(d, "menge"))))
    r.append(("S1b QUAN-only meins marker: unitOfMeasure:true",
              "@Semantics.unitOfMeasure : true" in annotations_of(d, "meins"),
              str(annotations_of(d, "meins"))))

    # S2 — CURR (B-13'un ta kendisi): DTEL sozlugunden OTOMATIK cikarim
    d = ddl_of(pt, CURR_ONLY)
    r.append(("S2 CURR netwr->waerk: amount.currencyCode",
              "@Semantics.amount.currencyCode : 'zsd001_t_amtit.waerk'" in annotations_of(d, "netwr_ref"),
              str(annotations_of(d, "netwr_ref"))))
    r.append(("S2b CURR waerk marker: currencyCode:true",
              "@Semantics.currencyCode : true" in annotations_of(d, "waerk"),
              str(annotations_of(d, "waerk"))))
    r.append(("S2c CURR alani unitOfMeasure ALMAMALI",
              not any("unitOfMeasure" in a for a in annotations_of(d, "netwr_ref")),
              str(annotations_of(d, "netwr_ref"))))

    # S3 — KARISIK tablo: ikisi ayni tabloda birbirini bozmamali
    d = ddl_of(pt, MIXED)
    r.append(("S3 karisik: menge -> quantity.unitOfMeasure",
              "@Semantics.quantity.unitOfMeasure : 'zsd001_t_mixit.vrkme'" in annotations_of(d, "menge"),
              str(annotations_of(d, "menge"))))
    r.append(("S3b karisik: netwr_ref -> amount.currencyCode",
              "@Semantics.amount.currencyCode : 'zsd001_t_mixit.waerk'" in annotations_of(d, "netwr_ref"),
              str(annotations_of(d, "netwr_ref"))))
    r.append(("S3c karisik: vrkme=unit marker, waerk=currency marker",
              "@Semantics.unitOfMeasure : true" in annotations_of(d, "vrkme")
              and "@Semantics.currencyCode : true" in annotations_of(d, "waerk"),
              "vrkme=%s waerk=%s" % (annotations_of(d, "vrkme"), annotations_of(d, "waerk"))))

    # S4 — Z'li DTEL: sinif REFERANS alanin DTEL'inden cikarilmali (ikinci sinyal).
    # ⚠ Sadece annotation'a bakmak YETMEZ: ikinci sinyal kaldirilsa da sonuc
    # 'quantity' cikar (varsayilan ayni yon). Ayirt edici KANIT uyari-IZIDIR:
    # cozulduyse uyari YOK, varsayilana dusulduyse uyari VAR.
    w4 = []
    d = pt.build_ddl(CUSTOM_DTEL["table_name"], "Test", "A", "ALLOWED",
                     CUSTOM_DTEL["fields"], CUSTOM_DTEL["unit_refs"], {}, warn=w4.append)
    r.append(("S4 Z-DTEL quantity->sales_unit(vrkme): quantity dali + UYARI YOK",
              "@Semantics.quantity.unitOfMeasure : 'zsd001_t_dorit.sales_unit'" in annotations_of(d, "quantity")
              and w4 == [],
              "annots=%s warns=%s" % (annotations_of(d, "quantity"), w4)))

    # S4b — ayni ikinci sinyalin CURRENCY yonu: Z'li tutar DTEL'i + standart CUKY ref.
    # Bu, S4'un yon-ikizidir (ikinci sinyal yalniz quantity'ye degil currency'ye de calisir).
    spec4b = dict(
        table_name="ZSD001_T_ZAMT",
        fields=[fld("MANDT", "MANDT", "Y"), fld("TUTAR", "ZSD001_E_ZAMT"), fld("WAERS", "waers")],
        unit_refs={"tutar": "waers"},
    )
    w4b = []
    d = pt.build_ddl(spec4b["table_name"], "Test", "A", "ALLOWED",
                     spec4b["fields"], spec4b["unit_refs"], {}, warn=w4b.append)
    r.append(("S4b Z-DTEL tutar->waers(CUKY): currency dali + UYARI YOK",
              "@Semantics.amount.currencyCode : 'zsd001_t_zamt.waers'" in annotations_of(d, "tutar")
              and "@Semantics.currencyCode : true" in annotations_of(d, "waers")
              and w4b == [],
              "tutar=%s waers=%s warns=%s" % (annotations_of(d, "tutar"),
                                              annotations_of(d, "waers"), w4b)))

    # S5 — ACIK unit_kind DTEL sozlugunu EZER (sozluk bilmese de calisir)
    spec = dict(CURR_ONLY)
    spec["fields"] = [fld("MANDT", "MANDT", "Y"), fld("TUTAR", "ZSD001_E_AMT"), fld("PARA", "ZSD001_E_CUR")]
    spec["unit_refs"] = {"tutar": "para"}
    d = ddl_of(pt, spec, unit_kinds={"tutar": "currency"})
    r.append(("S5 acik unit_kind=currency bilinmeyen DTEL'i currency yapar",
              "@Semantics.amount.currencyCode : 'zsd001_t_amtit.para'" in annotations_of(d, "tutar")
              and "@Semantics.currencyCode : true" in annotations_of(d, "para"),
              "tutar=%s para=%s" % (annotations_of(d, "tutar"), annotations_of(d, "para"))))

    # S6 — bilinmeyen DTEL + referans da bilinmiyor -> eski davranis + UYARI
    spec2 = dict(spec)
    warns = []
    d = pt.build_ddl("ZSD001_T_UNK", "T", "A", "ALLOWED", spec2["fields"],
                     spec2["unit_refs"], {}, warn=warns.append)
    r.append(("S6 bilinmeyen DTEL: quantity'ye duser AMA uyarir (sessiz degil)",
              "@Semantics.quantity.unitOfMeasure : 'zsd001_t_unk.para'" in annotations_of(d, "tutar")
              and len(warns) == 1 and "unit_kind belirlenemedi" in warns[0],
              "warns=%s" % warns))

    # S7 — CSV: zorunlu kolon eksik -> ERKEN ve ACIK FAIL (B-9)
    rc, out = run_main(pt, "table_name,field_name,is_key,type\nZSD001_T_X,MANDT,Y,MANDT\n", "_s7.csv")
    r.append(("S7 eksik zorunlu kolon -> exit 1 + eksik kolon adlari yazilir",
              rc == 1 and "zorunlu kolon" in out and "table_desc" in out,
              "rc=%r out=%r" % (rc, out[:200])))

    # S8 — CSV: gecersiz unit_kind -> FAIL-CLOSED (sessizce quantity'ye DUSMEZ)
    csv = (HDR10 + "\n"
           + "ZSD001_T_X,T,A,ALLOWED,MANDT,Y,MANDT,Client,,\n"
           + "ZSD001_T_X,T,A,ALLOWED,NETWR,N,netwr,Tutar,WAERS,curency\n")
    rc, out = run_main(pt, csv, "_s8.csv")
    r.append(("S8 gecersiz unit_kind -> exit 1 (fail-closed)",
              rc == 1 and "gecersiz unit_kind" in out,
              "rc=%r out=%r" % (rc, out[:200])))

    # S9 — CSV: unit_kind kolonu HIC YOK (9 kolonlu eski CSV) -> calisir + INFO
    csv = (HDR9 + "\n"
           + "ZSD001_T_X,T,A,ALLOWED,MANDT,Y,MANDT,Client,\n"
           + "ZSD001_T_X,T,A,ALLOWED,MENGE,N,menge_d,Miktar,MEINS\n"
           + "ZSD001_T_X,T,A,ALLOWED,MEINS,N,meins,Birim,\n")
    rc, out = run_main(pt, csv, "_s9.csv")
    r.append(("S9 unit_kind kolonu yok -> zorunlu-kolon FAIL'i YOK + INFO satiri",
              "zorunlu kolon" not in out and "unit_kind" in out and "eski davranis" in out,
              "rc=%r out=%r" % (rc, out[:300])))

    # S10 — CSV: 8 kolonlu EN ESKI CSV (unit_field de yok) hala kabul edilir
    csv = (HDR8 + "\n" + "ZSD001_T_X,T,A,ALLOWED,MANDT,Y,MANDT,Client\n")
    rc, out = run_main(pt, csv, "_s10.csv")
    r.append(("S10 8-kolonlu eski CSV: zorunlu-kolon FAIL'i YOK",
              "zorunlu kolon" not in out and "unit_field" in out,
              "rc=%r out=%r" % (rc, out[:300])))

    # =====================================================================
    # #32 ②  —  (b) `[SKIP] zaten var -> return True` SAHTE YESILI
    #             (a) LOCK yanitindaki CORRNR OKUNMUYORDU
    # Olculmus vaka (2026-08-19): yarim shell uzerinde kosuldu, ekrana
    # "1 basarili, 0 hatali" yazdi, exit 0 verdi; `adt_get` readback'i TEK
    # SATIRLIK shell gosterdi => hicbir sey yazilmamisti. "Obje VAR" ile
    # "obje DOGRU" ayni sey degildir.
    # =====================================================================
    FIELDS = [{"name": "mandt", "is_key": "Y", "type": "mandt", "description": ""},
              {"name": "vbeln", "is_key": "Y", "type": "vbeln", "description": ""},
              {"name": "posnr", "is_key": "N", "type": "posnr", "description": ""}]
    TAM_DDL = pt.build_ddl("ZT", "d", "A", "LIMITED", FIELDS)
    SHELL_DDL = ("@EndUserText.label : 'd'\ndefine table zt {\n"
                 "  key mandt : mandt not null;\n}")

    class _Resp:
        def __init__(s, code=200, text=""):
            s.status_code, s.text = code, text

    class _Sess:
        """GET'i URL'e gore YONLENDIRIR: varlik-GET ile kaynak-GET AYRI yanit alir.
        (Tek yanit verilirse 500 vektoru varlik-GET'i de dusurur ve akis CREATE
        dalina sapar -> harness hatasi, kod hatasi degil. Olculdu 2026-08-29.)"""
        def __init__(s, exists_resp, src_resp=None, corrnr="DS4K900029"):
            s._e, s._s = exists_resp, (src_resp if src_resp is not None else exists_resp)
            s.put_params = None
            s._corrnr = corrnr
        def get(s, url, **k):
            return s._s if url.endswith("/source/main") else s._e
        def post(s, url, **k):
            if (k.get("params") or {}).get("_action") == "LOCK":
                c = ("<CORRNR>%s</CORRNR>" % s._corrnr) if s._corrnr else ""
                return _Resp(200, "<asx><LOCK_HANDLE>H1</LOCK_HANDLE>%s</asx>" % c)
            return _Resp(200, "")
        def put(s, url, **k):
            s.put_params = k.get("params")
            return _Resp(200, "")
        def delete(s, url, **k):
            return _Resp(200, "")

    class _Client:
        def __init__(s, exists_resp, src_resp=None, corrnr="DS4K900029"):
            s.url = "https://x"
            s.session = _Sess(exists_resp, src_resp, corrnr)

    def _cagir(c):
        tut = io.StringIO()
        saved = sys.stdout
        sys.stdout = tut
        try:
            sonuc = pt.create_one(c, "tok", "ZT", "d", "A", "LIMITED",
                                  FIELDS, "PKG", "TR001")
        finally:
            sys.stdout = saved
        return sonuc, tut.getvalue()

    # --- S11: obje VAR ama YARIM SHELL -> sahte yesil YOK ------------------
    c = _Client(_Resp(200, ""), _Resp(200, SHELL_DDL))
    sonuc, out = _cagir(c)
    r.append(("S11 #32(b): var-ama-yarim-shell -> False (sahte yesil yok)",
              sonuc is False and "icerik farkli" in out,
              "donen=%r out=%r" % (sonuc, out[:200])))

    # --- S12: ⭐ IDEMPOTANS CAPASI — gercekten AYNI ise yine True, yazma YOK
    # Duzeltmenin BOZMAMASI gereken sey: ayni obje uzerinde tekrar kosmak
    # hatasiz gecmeli ve HICBIR yazma yapmamali.
    c = _Client(_Resp(200, ""), _Resp(200, TAM_DDL))
    sonuc, out = _cagir(c)
    r.append(("S12 #32(b) FP capasi: icerik ESLESIYOR -> True ve PUT YOK (idempotans)",
              sonuc is True and c.session.put_params is None,
              "donen=%r put=%r" % (sonuc, c.session.put_params)))

    # --- S13: readback OLCULEMEDI -> "olculemedi != temiz" ----------------
    c = _Client(_Resp(200, ""), _Resp(500, "err"))
    sonuc, out = _cagir(c)
    r.append(("S13 #32(b): readback olculemedi -> False (olculemedi != temiz)",
              sonuc is False and "DOGRULANAMADI" in out,
              "donen=%r out=%r" % (sonuc, out[:200])))

    # --- S14: #32(a) CORRNR OTORITESI -------------------------------------
    # Kontrol gruplu canli olcum (2026-08-19): S-tipi GOREV verilince 9/9 tablo
    # `CTS_WBO_API 020` (409); K-tipi ISTEK verilince 9/9 pushed. SAP'nin lock
    # yanitindaki CORRNR otoritedir -> PUT onunla gitmeli.
    c = _Client(_Resp(404, ""), corrnr="DS4K900029")
    sonuc, out = _cagir(c)
    pp = c.session.put_params or {}
    r.append(("S14 #32(a): PUT corrNr, lock yanitindaki CORRNR ile gider",
              pp.get("corrNr") == "DS4K900029",
              "PUT corrNr=%r (istenen TR001)" % pp.get("corrNr")))

    # --- S15: FP capasi — CORRNR DONMEZSE istenen transport korunur -------
    c = _Client(_Resp(404, ""), corrnr=None)
    sonuc, out = _cagir(c)
    pp = c.session.put_params or {}
    r.append(("S15 #32(a) FP capasi: CORRNR yoksa istenen transport korunur + uyarilir",
              pp.get("corrNr") == "TR001" and "CORRNR yok" in out,
              "PUT corrNr=%r out=%r" % (pp.get("corrNr"), out[:160])))

    return r


# ---------------------------------------------------------------------------
# MUTASYONLAR — fix'i sok, korpus KIRMIZI olmali
# ---------------------------------------------------------------------------
MUTASYONLAR = [
    ("M1 B-13'u geri getir (karar yine `type == 'CURR'`)",
     lambda s: s.replace(
         "            kind = classify_unit_kind(\n"
         "                type_by_name.get(value_field, ''),\n"
         "                type_by_name.get(ref_field, ''),\n"
         "            )",
         "            kind = (UNIT_KIND_CURRENCY\n"
         "                    if type_by_name.get(value_field, '').upper() == 'CURR'\n"
         "                    else UNIT_KIND_QUANTITY)"),
     None),
    ("M2 acik unit_kind yok sayilsin (kolon olu koda donsun)",
     lambda s: s.replace("        kind = unit_kinds.get(value_field)",
                         "        kind = None"),
     None),
    ("M3 gecersiz unit_kind sessizce quantity'ye dussun (fail-open)",
     None,
     lambda s: s.replace(
         "    raise UnitKindError(\n"
         "        \"gecersiz unit_kind: %r (gecerli: %s veya bos birak)\"\n"
         "        % (raw, '/'.join(VALID_UNIT_KINDS))\n"
         "    )",
         "    return None")),
    ("M4 ikinci sinyal (referans DTEL) kaldirilsin",
     None,
     lambda s: s.replace("    r = (ref_dtel or '').strip().casefold()",
                         "    r = ''")),

    # --- #32 degismezleri: M1-M4 bunlarin HICBIRINI sinamaz --------------
    ("M5 #32(b) fix'i geri al: var-ise kosulsuz `return True` (sahte yesil)",
     lambda s: s.replace(
         "        durum, detay, canli = readback_dogrula(client, table_name, len(fields))",
         "        durum, detay, canli = 'AYNI', 'readback YOK', 0"),
     None),

    ("M6 #32(b) SINIR: 'olculemedi'yi TEMIZ say (fail-open)",
     lambda s: s.replace("        return 'OLCULEMEDI', f'kaynak GET status={r.status_code}', None",
                         "        return 'AYNI', 'olculemedi ama temiz sayildi', 0"),
     None),

    ("M7 #32(a) CORRNR'i yok say (PUT yine istenen transport ile gitsin)",
     lambda s: s.replace("            params={'corrNr': etkin_transport, 'lockHandle': handle},",
                         "            params={'corrNr': transport, 'lockHandle': handle},"),
     None),
]


def main() -> int:
    print("=" * 78)
    print("populate_tables_unit_kind — B-13/B-9/B-14 korpusu")
    print("=" * 78)

    pt = load()
    sonuc = senaryolar(pt)
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik = []
    for ad, pt_mut, ds_mut in MUTASYONLAR:
        try:
            m_pt = load(pt_mut=pt_mut, ds_mut=ds_mut)
            m_res = senaryolar(m_pt)
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:
            yakalandi, kacan = True, ["yukleme hatasi: %s" % type(e).__name__]
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    # Mutasyonun GERCEKTEN uygulandigini kanitla (yama tutmazsa sahte-YESIL olur)
    print("\n--- yama-tuttu kanidi ---")
    ham_pt = PT_PATH.read_text(encoding="utf-8")
    ham_ds = DS_PATH.read_text(encoding="utf-8")
    yama_kirik = []
    for ad, pt_mut, ds_mut in MUTASYONLAR:
        src, mut = (ham_pt, pt_mut) if pt_mut else (ham_ds, ds_mut)
        degisti = mut(src) != src
        print("  [%s] %s" % ("degisti" if degisti else "YAMA TUTMADI", ad))
        if not degisti:
            yama_kirik.append(ad)

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI (korpus bu degismezi olcmuyor): %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI (sahte-yesil riski): %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
