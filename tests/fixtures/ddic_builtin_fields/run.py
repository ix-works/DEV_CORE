#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ddic_builtin_fields fixture — DEV_CORE #406: DTEL'siz (yerleşik `abap.*` tipli) alan listesi.

NEDEN VAR (2026-11-08, kullanıcı onayı — ADR 0019 beş şartı)
  `run_review --task table_creation|struct_creation` yerleşik tipli alana bakan hiçbir denetim
  koşturmuyordu: `key id : abap.numc(3)` · `cnt : abap.int4` · `note : abap.char(100)` taşıyan
  tablo `VERDICT: PASS` alıyordu; `check_struct_field_dtel_active` ise `measured=true
  reason=kapsam-disi-z-dtel-yok` diyerek "ölçtüm" okunuyordu. Düzeltme: yeni
  `check_ddic_builtin_fields.py` (LİSTELER, WARNING; yalnız iki yaratım zinciri) + dtel_active
  çıktısına "DTEL'siz alan: BAKILMADI" kapsam beyanı.

VEKTÖRLER (SAP'ye istek YOK: girdilerde Z DTEL yok, env `ADT_SAP_*` sahte adrese zorlanır)
  D1  bildirilen örnek → rc 1 · id/cnt/note listelenir · `mandt : mandt` listelenmez
  D2  DTEL'li tablo (çok satırlı foreign key, value help, annotation) → rc 0 · OK measured=true temiz
      · KAPSAM + BAKILMAYAN satırları 0-bulgu anında da basılır
  D3  hepsi gerekçeli istisna — kardeş `<GÖVDE>.README.md` (`- ` / `* ` madde işareti, BÜYÜK harfli
      alan adı) → rc 0 · hepsi-istisna-gerekceli · KAPSAM "README: okundu 1"
  D4  README'de gerekçesiz satır + yanlış ayırıcı (` - `) → rc 1 · ikisi de "GEREKÇESİZ"
  D5  `include x;` + `grp : include y with suffix _a;` → alan sayılmaz, include 2
  D6  çözülemeyen deyim (DTEL'siz alan yok) → rc 0 · SKIPPED measured=false deyim-cozulemedi
  D7  klasik `.tabl.xml` → rc 0 · measured=false klasik-xml-olculmedi
  D8  append (`extend type`) → rc 0 · measured=false append-olculmedi
  D9  namespace'li yapı + alan (`/XNS/`) → alan `/xns/fld` listelenir, `/xns/sd001_e_x` DTEL'li sayılır
  D10 yorum / blok yorum / dize içindeki `abap.` ve `;` alan sayılmaz
  D11 KAYNAK İÇİ `// dtel-istisna:` istisna SAYILMAZ (SAP tablo readback'i yorumu siler, yapı push
      400) → a ve b (aynı satırdaki iki alan — eski Ö1 belirsizliği yok) uyarı + "README'ye taşı"
  D15 bayat istisna: README'deki DDL'de olmayan / DTEL'li alan → [BİLGİ] satırı, rc etkilenmez
  D16 KISMİ: uyarı + çözülemeyen deyim aynı dosyada → reason `…-KISMI` + `[KISMİ]` satırı
  D17 namespace'li dosya adı `#xns#…` → README gövdesi dosya adının kendisi (`#xns#….README.md`)
  D12 ardışık iki annotation'lı alan ayrıştırılır (çözülemeyen deyim 0)
  D13 `define table function` dosyası → measured=false tablo-yapi-tanimi-yok
  D14 ÜÇÜNCÜ BAĞLAM: dizin kipi (CDS view atlanır + tablo + yapı + xml) + CRLF/BOM dosyası
  R1  run_review table_creation bildirilen örnek → VERDICT WARNING (eski: PASS), exit 0
  R2  run_review table_creation hepsi istisnalı (kardeş README) → VERDICT PASS
  R3  run_review table_creation DTEL'li tablo → VERDICT PASS
  R4  run_review struct_creation DTEL'siz yapı → yeni kayıt FAIL/WARNING, exit 0 (BLOCKER yok)
  R5  run_review table_creation çözülemeyen deyim → yeni kayıt SKIP (ölçüm yok), verdict ≠ PASS
  R6  zincir haritası: yalnız table_creation + struct_creation'da WARNING; run_all VALIDATORS'ta YOK
  T1  dtel_active kapsam-dışı dalı: "DTEL'siz … BAKILMADI" beyanı + hüküm aynen (rc 0, measured=true)

KULLANIM
  python tests/fixtures/ddic_builtin_fields/run.py                  # vektörler
  python tests/fixtures/ddic_builtin_fields/run.py --kok <ağaç>     # başka ağaç (mutant kum)
  python tests/fixtures/ddic_builtin_fields/run.py --mutasyon-<ad>  # tek mutasyon (KIPLER)
  Mutasyon çıkışı: 1 = ilan edilen küme TAM düştü · 2 = SAPMA · 3 = kurulamadı.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]

TABLO_ORNEK = """define table zsd001_t_demo {
  key mandt : mandt not null;
  key id : abap.numc(3) not null;
  cnt : abap.int4;
  note : abap.char(100);
}
"""

TABLO_DTELLI = """@EndUserText.label : 'Demo tablo; DTEL''li // yorum değil'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #RESTRICTED
define table zsd001_t_demo2 {
  key mandt : mandt not null;
  @AbapCatalog.foreignKey.screenCheck : true
  key vkorg : vkorg not null
    with foreign key [0..*,1] tvko
      where mandt = zsd001_t_demo2.mandt
        and vkorg = zsd001_t_demo2.vkorg;
  matnr : matnr
    with value help zsd001_sh_demo
      where matnr = zsd001_t_demo2.matnr;
  ernam : ernam;
}
"""

TABLO_ISTISNA = """define table zsd001_t_demo3 {
  key mandt : mandt not null;
  key id : abap.numc(3) not null;
  cnt : abap.int4;
  @EndUserText.label : 'Not'
  note : abap.char(100);
}
"""

README_ISTISNA = """# ZSD001_T_DEMO3

Tasarım onayı: kullanıcı, 2026-11-08 (alan + key + DTEL tablosu).

- dtel-istisna: id — teknik sayaç anahtarı
* dtel-istisna: CNT — ham sayaç, iş anlamı yok
dtel-istisna: note — serbest not metni, DTEL karşılığı yok
"""

TABLO_GEREKCESIZ = """define table zsd001_t_demo4 {
  key mandt : mandt not null;
  cnt : abap.int4;
  id : abap.numc(3);
}
"""

README_GEREKCESIZ = """- dtel-istisna: cnt
- dtel-istisna: id - tire ayırıcı kabul edilmez
"""

TABLO_BAYAT = """define table zsd001_t_demo9 {
  key mandt : mandt not null;
  matnr : matnr;
}
"""

README_BAYAT = """- dtel-istisna: eski_alan — kaldırılmış alan
- dtel-istisna: matnr — artık DTEL'li
"""

README_NS = """- dtel-istisna: /XNS/FLD — namespace'li bayrak
"""

YAPI_INCLUDE = """define structure zsd001_s_demo {
  include zsd001_s_bas;
  grp : include zsd001_s_ek with suffix _a;
  matnr : matnr;
}
"""

TABLO_COZULEMEZ = """define table zsd001_t_demo5 {
  key mandt : mandt not null;
  bu bir alan degil;
}
"""

YAPI_XML = """<?xml version="1.0" encoding="utf-8"?>
<abapGit version="v1.0.0"><asx:abap><asx:values><DD02V><TABNAME>ZSD001_S_DEMO</TABNAME></DD02V>
</asx:values></asx:abap></abapGit>
"""

APPEND = """extend type zsd001_s_demo with zsd001_s_demo_app {
  zz_alan : abap.char(4);
}
"""

YAPI_NS = """define structure /xns/sd001_s_demo {
  /xns/fld : abap.char(3);
  fld2 : /xns/sd001_e_x;
}
"""

TABLO_YORUM = """define table zsd001_t_demo6 {
  key mandt : mandt not null;
  // eski : abap.char(1);
  /* iptal : abap.char(2);
     iptal2 : abap.int4; */
  @EndUserText.label : 'x : abap.char(9); y'
  matnr : matnr;
}
"""

TABLO_KAYNAK_ISARET = """define table zsd001_t_demo7 {
  key mandt : mandt not null;
  // dtel-istisna: kaynak içi işaret artık geçersiz
  a : abap.int4; b : abap.int4; // dtel-istisna: iki alan aynı satırda
}
"""

TABLO_KISMI = """define table zsd001_t_demo10 {
  key mandt : mandt not null;
  -- eski alan abap.char(1)
  note : abap.char(100);
  f2 : abap.int4;
}
"""

TABLO_IKI_ANNOT = """define table zsd001_t_demo8 {
  key mandt : mandt not null;
  @Semantics.amount.currencyCode : 'zsd001_t_demo8.waers'
  @EndUserText.label : 'Tutar'
  netwr : netwr;
  @Semantics.currencyCode : true
  waers : waers;
}
"""

TABLO_FONK = """@EndUserText.label : 'tf'
define table function zsd001_tf_demo
returns { mandt : abap.clnt; }
implemented by method zcl_x=>m;
"""

CDS_VIEW = """define view entity ZSD001_I_DEMO as select from zsd001_t_demo { key id }
"""

S: list[tuple[str, bool, str]] = []


def ekle(ad: str, ok: bool, ayrinti: str = "") -> None:
    S.append((ad, ok, ayrinti))


def yaz(yol: Path, metin: str, crlf: bool = False, bom: bool = False) -> Path:
    yol.parent.mkdir(parents=True, exist_ok=True)
    veri = metin.replace("\n", "\r\n") if crlf else metin
    yol.write_bytes((b"\xef\xbb\xbf" if bom else b"") + veri.encode("utf-8"))
    return yol


def kos(kok: Path, kum: Path, betik: str, *argv: str) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(kum)
    env.pop("IX_CEVRIMDISI", None)
    # sap_adt_lib alt süreci ASLA gerçek sisteme düşmesin
    env.update(ADT_SAP_URL="https://sahte.invalid", ADT_SAP_CLIENT="000", ADT_SAP_USER="x",
               ADT_SAP_PASSWORD="x")
    r = subprocess.run([sys.executable, str(kok / "scripts" / "validators" / betik), *argv],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=180, cwd=str(kum), env=env)
    return r.returncode, r.stdout, r.stderr


_BEYAN = re.compile(r"^IX-GATE-STATUS:\s+gate=(\S+)\s+status=(\S+)\s+measured=(true|false)\s+"
                    r"reason=(\S+)\s*$", re.M)


def beyan(out: str):
    m = _BEYAN.findall(out)
    return m[-1] if m else None


def uyarilar(out: str) -> list[str]:
    return [ln.split(" · ")[1] for ln in out.splitlines() if ln.startswith("[UYARI]")]


def istisnalar(out: str) -> list[str]:
    return [ln.split(" · ")[1] for ln in out.splitlines() if ln.startswith("[İSTİSNA]")]


def kapsam(out: str) -> str:
    return next((ln for ln in out.splitlines() if ln.startswith("KAPSAM:")), "")


def kayit(js: dict, ad: str):
    return next((r for r in js.get("results", []) if r["validator"] == ad), None)


V = "check_ddic_builtin_fields.py"


def dogrudan(kok: Path, kum: Path) -> None:
    g = kum / "g"
    rc, out, err = kos(kok, kum, V, str(yaz(g / "zsd001_t_demo.tabl.ddl", TABLO_ORNEK)))
    ekle("D1", rc == 1 and uyarilar(out) == ["id", "cnt", "note"] and "mandt" not in uyarilar(out)
         and beyan(out) == ("check_ddic_builtin_fields", "FINDING", "true", "3-dtelsiz-alan")
         and "README: okundu 0 · yok 1" in kapsam(out) and "[KISMİ]" not in out,
         f"rc={rc} uyari={uyarilar(out)} beyan={beyan(out)} kapsam={kapsam(out)!r} err={err[-200:]}")

    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_t_demo2.tabl.ddl", TABLO_DTELLI)))
    k = kapsam(out)
    ekle("D2", rc == 0 and not uyarilar(out) and beyan(out) == (
        "check_ddic_builtin_fields", "OK", "true", "temiz") and "alan 4 (DTEL'li 4" in k
         and "çözülemeyen deyim 0" in k and any(ln.startswith("BAKILMAYAN:") for ln in out.splitlines()),
         f"rc={rc} beyan={beyan(out)} kapsam={k!r}")

    yaz(g / "ZSD001_T_DEMO3.README.md", README_ISTISNA)   # gövde harfi farklı: harf duyarsız bulunur
    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_t_demo3.tabl.ddl", TABLO_ISTISNA)))
    ekle("D3", rc == 0 and not uyarilar(out) and istisnalar(out) == ["id", "cnt", "note"]
         and beyan(out) == ("check_ddic_builtin_fields", "OK", "true", "hepsi-istisna-gerekceli")
         and "teknik sayaç anahtarı" in out and "README: okundu 1" in kapsam(out),
         f"rc={rc} uyari={uyarilar(out)} istisna={istisnalar(out)} beyan={beyan(out)} kapsam={kapsam(out)!r}")

    yaz(g / "zsd001_t_demo4.README.md", README_GEREKCESIZ)
    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_t_demo4.tabl.ddl", TABLO_GEREKCESIZ)))
    ekle("D4", rc == 1 and uyarilar(out) == ["cnt", "id"] and out.count("GEREKÇESİZ") == 2
         and not istisnalar(out), f"rc={rc} uyari={uyarilar(out)} istisna={istisnalar(out)}")

    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_s_demo.ddls.asddls", YAPI_INCLUDE)))
    k = kapsam(out)
    ekle("D5", rc == 0 and "include 2" in k and "alan 1 (DTEL'li 1" in k
         and beyan(out) == ("check_ddic_builtin_fields", "OK", "true", "temiz"),
         f"rc={rc} kapsam={k!r} beyan={beyan(out)}")

    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_t_demo5.tabl.ddl", TABLO_COZULEMEZ)))
    ekle("D6", rc == 0 and beyan(out) == ("check_ddic_builtin_fields", "SKIPPED", "false", "deyim-cozulemedi")
         and "çözülemeyen deyim 1" in kapsam(out) and "TEMİZ DEĞİL" in out,
         f"rc={rc} beyan={beyan(out)} kapsam={kapsam(out)!r}")

    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_s_demo.tabl.xml", YAPI_XML)))
    ekle("D7", rc == 0 and beyan(out) == ("check_ddic_builtin_fields", "SKIPPED", "false", "klasik-xml-olculmedi"),
         f"rc={rc} beyan={beyan(out)}")

    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_s_demo_app.ddls.asddls", APPEND)))
    ekle("D8", rc == 0 and beyan(out) == ("check_ddic_builtin_fields", "SKIPPED", "false", "append-olculmedi")
         and not uyarilar(out), f"rc={rc} beyan={beyan(out)} uyari={uyarilar(out)}")

    rc, out, _ = kos(kok, kum, V, str(yaz(g / "#xns#sd001_s_demo.ddls.asddls", YAPI_NS)))
    ekle("D9", rc == 1 and uyarilar(out) == ["/xns/fld"] and "· /xns/sd001_s_demo " in out
         and "DTEL'li 1" in kapsam(out), f"rc={rc} uyari={uyarilar(out)} kapsam={kapsam(out)!r}")

    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_t_demo6.tabl.ddl", TABLO_YORUM)))
    k = kapsam(out)
    ekle("D10", rc == 0 and not uyarilar(out) and "alan 2 (DTEL'li 2" in k and "çözülemeyen deyim 0" in k,
         f"rc={rc} uyari={uyarilar(out)} kapsam={k!r}")

    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_t_demo7.tabl.ddl", TABLO_KAYNAK_ISARET)))
    tasi = [ln for ln in out.splitlines() if ln.startswith("[KAYNAK-İÇİ İŞARET]")]
    ekle("D11", rc == 1 and uyarilar(out) == ["a", "b"] and not istisnalar(out) and len(tasi) == 2
         and all("zsd001_t_demo7.README.md" in ln for ln in tasi)
         and "kaynak-içi işaret (sayılmadı) 2" in kapsam(out),
         f"rc={rc} uyari={uyarilar(out)} istisna={istisnalar(out)} tasi={len(tasi)} kapsam={kapsam(out)!r}")

    yaz(g / "zsd001_t_demo9.README.md", README_BAYAT)
    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_t_demo9.tabl.ddl", TABLO_BAYAT)))
    bilgi = [ln for ln in out.splitlines() if ln.startswith("[BİLGİ] bayat istisna:")]
    ekle("D15", rc == 0 and len(bilgi) == 2 and any("eski_alan" in b and "DDL'de yok" in b for b in bilgi)
         and any("matnr" in b and "DTEL'li" in b for b in bilgi)
         and beyan(out) == ("check_ddic_builtin_fields", "OK", "true", "temiz"),
         f"rc={rc} bilgi={bilgi} beyan={beyan(out)}")

    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_t_demo10.tabl.ddl", TABLO_KISMI)))
    ekle("D16", rc == 1 and uyarilar(out) == ["f2"] and "[KISMİ]" in out
         and "KISMİ: liste eksik olabilir" in out
         and beyan(out) == ("check_ddic_builtin_fields", "FINDING", "true", "1-dtelsiz-alan-KISMI"),
         f"rc={rc} uyari={uyarilar(out)} beyan={beyan(out)}")

    g17 = kum / "g17"
    yaz(g17 / "#xns#sd001_s_demo.README.md", README_NS)
    rc, out, _ = kos(kok, kum, V, str(yaz(g17 / "#xns#sd001_s_demo.ddls.asddls", YAPI_NS)))
    ekle("D17", rc == 0 and istisnalar(out) == ["/xns/fld"] and not uyarilar(out)
         and "README: okundu 1" in kapsam(out),
         f"rc={rc} uyari={uyarilar(out)} istisna={istisnalar(out)} kapsam={kapsam(out)!r}")

    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_t_demo8.tabl.ddl", TABLO_IKI_ANNOT)))
    k = kapsam(out)
    ekle("D12", rc == 0 and "alan 3 (DTEL'li 3" in k and "çözülemeyen deyim 0" in k,
         f"rc={rc} kapsam={k!r}")

    rc, out, _ = kos(kok, kum, V, str(yaz(g / "zsd001_tf_demo.ddls.asddls", TABLO_FONK)))
    ekle("D13", rc == 0 and beyan(out) == ("check_ddic_builtin_fields", "SKIPPED", "false", "tablo-yapi-tanimi-yok")
         and not uyarilar(out), f"rc={rc} beyan={beyan(out)} uyari={uyarilar(out)}")

    # ③ ÜÇÜNCÜ BAĞLAM: dizin kipi + paket ağacı şekli + CRLF/BOM
    d = kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC"
    yaz(d / "cds" / "ZSD001_I_DEMO.ddls.asddls", CDS_VIEW)
    yaz(d / "tables" / "zsd001_t_demo.tabl.ddl", TABLO_ORNEK, crlf=True, bom=True)
    yaz(d / "structures" / "ZSD001_S_DEMO.ddls.asddls", YAPI_INCLUDE, crlf=True)
    yaz(d / "structures" / "zsd001_s_eski.tabl.xml", YAPI_XML)
    rc, out, _ = kos(kok, kum, V, str(kum / "SOURCE_CODES"))
    k = kapsam(out)
    ekle("D14", rc == 1 and uyarilar(out) == ["id", "cnt", "note"] and "4 dosya" in k
         and "tablo/yapı DDL 2" in k and "klasik .tabl.xml 1" in k and "atlanan 1" in k
         and "include 2" in k, f"rc={rc} uyari={uyarilar(out)} kapsam={k!r}")


def reviewer(kok: Path, kum: Path) -> None:
    g = kum / "r"

    def rr(task: str, dosya: Path):
        rc, out, err = kos(kok, kum, "run_review.py", "--task", task, "--artifact", str(dosya), "--json")
        try:
            return rc, json.loads(out[out.index("{"):])
        except Exception:
            return rc, {"_ham": (out + err)[-300:]}

    rc, js = rr("table_creation", yaz(g / "zsd001_t_demo.tabl.ddl", TABLO_ORNEK))
    r = kayit(js, V)
    ekle("R1", rc == 0 and js.get("verdict") == "WARNING" and r is not None and r["status"] == "FAIL"
         and r["severity"] == "WARNING" and js.get("blocker_count") == 0,
         f"rc={rc} verdict={js.get('verdict')} kayit={(r or {}).get('status')} {js.get('_ham', '')}")

    yaz(g / "zsd001_t_demo3.README.md", README_ISTISNA)
    rc, js = rr("table_creation", yaz(g / "zsd001_t_demo3.tabl.ddl", TABLO_ISTISNA))
    r = kayit(js, V)
    ekle("R2", rc == 0 and js.get("verdict") == "PASS" and r is not None and r["status"] == "PASS",
         f"rc={rc} verdict={js.get('verdict')} kayit={(r or {}).get('status')} {js.get('_ham', '')}")

    rc, js = rr("table_creation", yaz(g / "zsd001_t_demo2.tabl.ddl", TABLO_DTELLI))
    r = kayit(js, V)
    ekle("R3", rc == 0 and js.get("verdict") == "PASS" and r is not None and r["status"] == "PASS",
         f"rc={rc} verdict={js.get('verdict')} kayit={(r or {}).get('status')} {js.get('_ham', '')}")

    yapi = "define structure zsd001_s_demo2 {\n  matnr : matnr;\n  flag : abap.char(1);\n}\n"
    rc, js = rr("struct_creation", yaz(g / "zsd001_s_demo2.ddls.asddls", yapi))
    r = kayit(js, V)
    ekle("R4", rc == 0 and r is not None and r["status"] == "FAIL" and r["severity"] == "WARNING"
         and js.get("failed_blocker_count") == 0 and js.get("verdict") in ("WARNING",),
         f"rc={rc} verdict={js.get('verdict')} kayit={(r or {}).get('status')} "
         f"fb={js.get('failed_blocker_count')} {js.get('_ham', '')}")

    rc, js = rr("table_creation", yaz(g / "zsd001_t_demo5.tabl.ddl", TABLO_COZULEMEZ))
    r = kayit(js, V)
    ekle("R5", rc == 0 and r is not None and r["status"] == "SKIP" and r.get("olcum_yok") is True
         and js.get("verdict") == "WARNING",
         f"rc={rc} verdict={js.get('verdict')} kayit={(r or {}).get('status')} {js.get('_ham', '')}")

    # R6 — zincir haritası (modülü içe aktararak; kaynak metni değil)
    sys.path.insert(0, str(kok / "scripts" / "validators"))
    try:
        import importlib
        rv = importlib.import_module("run_review")
        rv = importlib.reload(rv)
        bulunan = {t: sev for t, zin in rv.TASK_VALIDATORS.items() for (ad, sev, _) in zin if ad == V}
        ra = (kok / "scripts" / "validators" / "run_all_validators.py").read_text(encoding="utf-8")
        ekle("R6", bulunan == {"table_creation": "WARNING", "struct_creation": "WARNING"}
             and V not in ra and str(Path(rv.__file__).resolve()).startswith(str(kok.resolve())),
             f"zincir={bulunan} run_all'da={V in ra} modul={rv.__file__}")
    finally:
        sys.path.pop(0)
        sys.modules.pop("run_review", None)


def dtel_active(kok: Path, kum: Path) -> None:
    rc, out, _ = kos(kok, kum, "check_struct_field_dtel_active.py",
                     str(yaz(kum / "t" / "zsd001_t_demo.tabl.ddl", TABLO_ORNEK)))
    ekle("T1", rc == 0 and "DTEL'siz (yerleşik abap.* tipli) alan: BAKILMADI" in out
         and "check_ddic_builtin_fields.py" in out
         and beyan(out) == ("check_struct_field_dtel_active", "OK", "true", "kapsam-disi-z-dtel-yok"),
         f"rc={rc} beyan={beyan(out)} out={out[:200]!r}")


def main(kok: Path) -> int:
    kum = Path(tempfile.mkdtemp(prefix="dbf_kum_"))
    try:
        yaz(kum / "project.yaml", "source_root: SOURCE_CODES\nsap_profile: s4_private\n")
        dogrudan(kok, kum)
        reviewer(kok, kum)
        dtel_active(kok, kum)
    finally:
        shutil.rmtree(kum, ignore_errors=True)
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    return 0 if n == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYON — her kural için kontrol grubu. Kum: ağacın `scripts/` kopyası + bu fixture;
# çapa tam 1 kez geçmeli (yoksa 3), düşen küme ilan edilenle TAM aynı olmalı (yoksa 2).
# ─────────────────────────────────────────────────────────────────────────────
_V = "scripts/validators/"
_DBF = _V + "check_ddic_builtin_fields.py"
MUTASYONLAR = {
    # istisna işaretini görmezden gel
    "--mutasyon-istisna-yok": (
        _DBF, "            if isaret:\n", "            if False:\n",
        {"D3", "D17", "R2"}),
    # gerekçesiz işareti istisna say (`_isaret_bul` içindeki `if gerekce:` mutasyonu NO-OP'tu:
    # boş gerekçe "" yine falsy döner — ölçüldü 2026-11-08, ilk kurulumda KAÇTI)
    "--mutasyon-gerekcesiz-gecer": (
        _DBF, "            if isaret:\n", "            if isaret is not None:\n",
        {"D4"}),
    # DTEL'li alanı da listele (her tipi yerleşik say) — DTEL'li alan taşıyan HER vektör düşer
    # (rc/uyarı listesi değişir); küme koşumdan (2026-11-08)
    "--mutasyon-dtelli-listele": (
        _DBF, "            y = _YERLESIK_RE.match(tip_ifade)\n",
        "            y = re.match(r'(.+?)(\\s*\\([^)]*\\))?\\Z', tip_ifade)\n",
        {"D1", "D2", "D3", "D4", "D5", "D6", "D9", "D10", "D11", "D12", "D14", "D15", "D16", "D17", "R2", "R3", "R5"}),
    # kapsam beyanını bastır
    "--mutasyon-beyan-bastir": (
        _DBF, '    print("BAKILMAYAN: klasik', '    (lambda *a: None)("BAKILMAYAN: klasik',
        {"D2"}),
    # bulguda rc 0 dön (eski "rc 0" tasarımı) ⇒ run_review verdict PASS'a döner
    "--mutasyon-rc-sifir": (
        _DBF, '        gate_status(_GATE, "FINDING", True, f"{len(uyari)}-dtelsiz-alan" + ("-KISMI" if kismi else ""))\n        return 1\n',
        '        gate_status(_GATE, "FINDING", True, f"{len(uyari)}-dtelsiz-alan" + ("-KISMI" if kismi else ""))\n        return 0\n',
        {"D1", "D4", "D9", "D11", "D14", "D16", "R1", "R4"}),
    # ölçülemeyeni temiz say (fail-open)
    "--mutasyon-olculemedi-temiz": (
        _DBF, '        gate_status(_GATE, "SKIPPED", False, sonuc["olculmedi"][0][2])\n',
        '        gate_status(_GATE, "OK", True, "temiz")\n',
        {"D6", "D7", "D8", "D13", "R5"}),
    # ilk annotation'dan sonrasını soyamayan çapa (\A geri)
    "--mutasyon-annot-capa": (
        _DBF, '    r"\\s*@[A-Za-z0-9_.]+', '    r"\\A\\s*@[A-Za-z0-9_.]+',
        {"D12"}),
    # yorumları maskeleme
    "--mutasyon-yorum-maskesiz": (
        _DBF, '            out.append(" " * (j - i))\n            i = j\n',
        '            out.append(metin[i:j])\n            i = j\n',
        # README biçiminde D3/R2 artık yoruma bağlı değil; D11 kaynak-içi işaret satırı sayımı düşer — koşumdan
        {"D10", "D11"}),
    # K1: kaynak içi `// dtel-istisna:` yeniden istisna sayılsın (eski tasarım; yapı push 400 ·
    # tablo readback'te siliniyor) — aynı satırdaki iki alanı da örter (Ö1)
    "--mutasyon-kaynak-ici-gecer": (
        _DBF, "            isaret = isaretler.get(alan.lower())\n",
        "            isaret = 'kaynak' if any(_KAYNAK_ISARET_RE.match(y.strip()) for y in "
        "yorumlar.get(ad_satiri, [])) else isaretler.get(alan.lower())\n",
        {"D11"}),
    # README alan adı büyük/küçük harf duyarlı olsun
    "--mutasyon-harf-duyarli": (
        _DBF, "        alan, kalan = m.group(1).lower(), m.group(2)\n",
        "        alan, kalan = m.group(1), m.group(2)\n",
        {"D3", "D17", "R2"}),
    # bayat istisna bilgisini bastır
    "--mutasyon-bayat-sessiz": (
        _DBF, '        sonuc["bilgi"].append(f"[BİLGİ] bayat istisna:',
        '        (lambda *a: None)(f"[BİLGİ] bayat istisna:',
        {"D15"}),
    # K3: uyarı + ölçülemeyen birlikteyken kısmilik görünmesin
    "--mutasyon-kismi-gizle": (
        _DBF, '    kismi = bool(uyari) and bool(sonuc["olculmedi"])\n', "    kismi = False\n",
        {"D16"}),
    # ayırıcı gevşesin (` - ` / `:` da gerekçe saysın)
    "--mutasyon-ayirici-gevsek": (
        _DBF, "        gerekce = kalan[len(_AYIRICI):].strip() if kalan.startswith(_AYIRICI) else \"\"\n",
        "        gerekce = kalan.lstrip('—-: ').strip()\n",
        {"D4"}),
    # zincirden çıkar (taban davranışı: bildirilen örnek PASS)
    "--mutasyon-zincirden-cikar": (
        _V + "run_review.py",
        "        ('check_ddic_builtin_fields.py', 'WARNING',\n"
        "         'DTEL\\'siz (yerleşik abap.* tipli) alan listesi — her biri kullanıcı onay kaydında adıyla geçmeli (BE-13 · C-TBL-CRE-01; #406)'),\n",
        "",
        {"R1", "R2", "R3", "R5", "R6"}),
    # dtel_active kapsam beyanını kaldır
    "--mutasyon-dtel-beyan-yok": (
        _V + "check_struct_field_dtel_active.py", "    print(_DTELSIZ_BEYANI)\n", "",
        {"T1"}),
}
KIPLER = sorted(MUTASYONLAR)


def _mutasyon(kip: str) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kum = Path(tempfile.mkdtemp(prefix="dbf_mut_"))
    try:
        shutil.copytree(REPO / "scripts", kum / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
        hedef = kum / "tests" / "fixtures" / BURASI.name
        shutil.copytree(BURASI, hedef, ignore=shutil.ignore_patterns("__pycache__"))
        dosya = kum / yol
        asil = dosya.read_bytes().decode("utf-8")
        if asil.count(eski) != 1:
            print(f"[KURULAMADI] {kip} -> capa {asil.count(eski)} kez ({yol})")
            return 3
        mutant = asil.replace(eski, yeni, 1)
        try:
            compile(mutant, str(dosya), "exec")
        except SyntaxError as exc:
            print(f"[KURULAMADI] {kip} -> mutant derlenmedi: {exc}")
            return 3
        dosya.write_bytes(mutant.encode("utf-8"))
        r = subprocess.run([sys.executable, str(hedef / "run.py"), "--kok", str(kum)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=600, cwd=str(kum))
        m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
        if not m:
            son = [x for x in (r.stdout + r.stderr).splitlines() if x.strip()][-1:] or ["-"]
            print(f"[ALT-SUREC SAYI VERMEDI] {kip} rc={r.returncode} son={son[0][:160]}")
            return 3
        dusen = {x.split()[1] for x in r.stdout.splitlines() if x.strip().startswith("[FAIL]")}
        print(f"{kip}: {m.group(0)} · dusen={sorted(dusen)} · ilan={sorted(beklenen)}")
        if dusen == beklenen:
            print("MUTASYON DUSTU (ilan edilen kume TAM)")
            return 1
        print(f"[SAPMA] fazla={sorted(dusen - beklenen)} eksik={sorted(beklenen - dusen)}")
        return 2
    finally:
        shutil.rmtree(kum, ignore_errors=True)


if __name__ == "__main__":
    _kipler = [a for a in sys.argv[1:] if a.startswith("--mutasyon")]
    if _kipler:
        if len(_kipler) != 1 or _kipler[0] not in MUTASYONLAR:
            print(f"[KULLANIM] gecerli kipler: {KIPLER}")
            sys.exit(2)
        sys.exit(_mutasyon(_kipler[0]))
    _kok = REPO
    if "--kok" in sys.argv:
        _kok = Path(sys.argv[sys.argv.index("--kok") + 1]).resolve()
    sys.exit(main(_kok))
