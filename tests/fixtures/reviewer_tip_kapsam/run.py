#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reviewer_tip_kapsam fixture — push'un kabul ettigi HER tip reviewer haritasinda BEYANLI mi?

NEDEN VAR (2026-08-01 adversarial bug-avi, W2-MCPT-03 / MG-02):
Push katmani tip ESANLAMLILARINI kabul ediyor (`_TYPE_KEY_CANON`, `_ACTIVATION_URI_SEG`,
`_SOURCE_BASED_TYPES`), reviewer haritasi ise yalniz kanonik adlari taniyordu. Eksik anahtar
-> `.get()` None -> ADR 0006 pre-flight SESSIZCE atlanir. Olculdu:
    object_type="ddls"  -> BLOCKER + push RED
    object_type="cds"   -> SKIP     + push GECTI      (ayni obje, ayni ADT URL'i)
Ayni asimetri `tabl` <-> `table`/`structure`'da vardi ve orada sonucu daha agir:
`table_update` zinciri `check_table_field_drop` (VERI-KAYBI BLOCKER'i) tasir.

ASIL KUSUR TEK BIR EKSIK ANAHTAR DEGIL, IKI TABLONUN SESSIZCE AYRISABILMESIYDI.
Bu test o ayrismayi kalici olarak gorunur kilar: yeni bir tip push'a eklenip reviewer
haritasi unutulursa BURASI KIRILIR.

AYRIM (onemli): "eksik anahtar" ile "bilincli None" ayni sey DEGILDIR.
  - eksik  -> sessiz atlama = BUG
  - None   -> kayda gecmis karar ("zincir henuz yok") = kabul
Bu yuzden test ANAHTAR VARLIGI arar, deger DOLULUGU degil.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "mcp_servers").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))


def _yukle(rel: str, ad: str):
    spec = importlib.util.spec_from_file_location(ad, REPO / rel)
    m = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
    sys.modules[ad] = m
    spec.loader.exec_module(m)                          # type: ignore[union-attr]
    return m


def _sabitler(rel: str, adlar: set[str]) -> dict:
    """Modul-duzeyi sabitleri IMPORT ETMEDEN, AST ile oku.

    Neden import degil: `atom.py` MCP SDK'sini (`mcp` paketi) ceker; CI'da o paket YOK
    ve fixture "ModuleNotFoundError" ile FAIL veriyordu (2026-08-01 CI, PR #80). Bu
    dogru davranisti — sessiz gecmedi — ama testi CI'da kosulamaz kiliyordu. Ayrica
    import, MCP sunucusunu ayaga kaldirip yan-etki/log uretiyordu. AST ile okumak hem
    bagimliliksiz hem yan-etkisiz: bu test TABLOLARIN ICERIGINI karsilastirir, calisma
    zamani davranisini degil.
    """
    import ast
    agac = ast.parse((REPO / rel).read_text(encoding="utf-8"))
    out: dict = {}
    for d in agac.body:
        if isinstance(d, ast.Assign) and len(d.targets) == 1:
            t = d.targets[0]
            if isinstance(t, ast.Name) and t.id in adlar:
                try:
                    out[t.id] = ast.literal_eval(d.value)
                except Exception:
                    pass
    return out


def main() -> int:
    # Harita da AST ile okunur: `_reviewer` -> `_app` -> `mcp` SDK zinciri CI'da YOK.
    # Asil iddialar (kapsam + esanlamli esitligi) bagimliliksiz kosar; canli
    # `task_for_push` kontrolu import edilebiliyorsa EK olarak kosar ve edilemiyorsa
    # SESSIZ atlanmaz, "KOSULMADI" diye YAZILIR (yesil isik degil, beyan).
    rv_t = _sabitler("mcp_servers/sap_adt/_reviewer.py", {"OBJECT_TYPE_TO_TASK"})
    if "OBJECT_TYPE_TO_TASK" not in rv_t:
        print("  [FAIL] OBJECT_TYPE_TO_TASK AST ile okunamadi")
        return 1
    atom_t = _sabitler("mcp_servers/sap_adt/tools/atom.py",
                       {"_TYPE_KEY_CANON", "_ACTIVATION_URI_SEG", "_SOURCE_BASED_TYPES"})
    # 2026-08-09: DDIC tip kumeleri atom.py'den `scripts/object_types.py`ye TASINDI
    # (tek kaynak; iki tuketici ayrisiyordu). Kapsam DARALMASIN diye ayni birlesim
    # oradan okunur — ozellikle `tabletype`, atom'daki DIGER tablolarin HICBIRINDE
    # gecmez; yalniz bu kumeden gelir (kaldirilirsa sessizce kapsam kaybi olurdu).
    ot_t = _sabitler("scripts/object_types.py",
                     {"DDIC_XML_ONLY_TYPES", "DDIC_DDL_SOURCE_TYPES"})

    harita = rv_t["OBJECT_TYPE_TO_TASK"]
    kabul: set[str] = set()
    for ad, tablo in (("_TYPE_KEY_CANON", atom_t), ("_ACTIVATION_URI_SEG", atom_t),
                      ("_SOURCE_BASED_TYPES", atom_t),
                      ("DDIC_XML_ONLY_TYPES", ot_t), ("DDIC_DDL_SOURCE_TYPES", ot_t)):
        v = tablo.get(ad)
        if v is None:
            print(f"  [FAIL] tip tablosu okunamadi: {ad} (sessiz gecme YOK)")
            return 1
        kabul |= set(v.keys() if isinstance(v, dict) else v)

    if not kabul:
        print("  [FAIL] push tip tablolari BOS okundu — test hicbir sey olcmuyor")
        return 1

    eksik = sorted(t for t in kabul if t not in harita)
    sonuc = []
    sonuc.append(("push'un kabul ettigi tipler reviewer haritasinda BEYANLI",
                  not eksik, f"kabul={len(kabul)} eksik={eksik or 'yok'}"))

    # KONTROL GRUBU: bilinen dogru esleme hala duruyor mu (test kendi kendini kandirmasin)
    sonuc.append(("kontrol: ddls -> cds_update", harita.get("ddls") == "cds_update",
                  str(harita.get("ddls"))))
    sonuc.append(("kontrol: tabl -> table_update", harita.get("tabl") == "table_update",
                  str(harita.get("tabl"))))
    # ESANLAMLI ESITLIGI: ayni ADT hedefine yazan tipler AYNI task'i vermeli
    sonuc.append(("esanlamli esitligi: cds/cdsview/ddl == ddls",
                  {harita.get(k) for k in ("cds", "cdsview", "ddl")} == {harita.get("ddls")},
                  str({k: harita.get(k) for k in ("cds", "cdsview", "ddl", "ddls")})))
    sonuc.append(("esanlamli esitligi: table/structure == tabl (VERI-KAYBI guard'i)",
                  {harita.get(k) for k in ("table", "structure")} == {harita.get("tabl")},
                  str({k: harita.get(k) for k in ("table", "structure", "tabl")})))
    # CANLI kontrol (harita dogru ama FONKSIYON yanlissa yakalar). `mcp` SDK'si yoksa
    # (CI) kosulamaz -> SESSIZ ATLANMAZ, ekrana "KOSULMADI" yazilir ve sonuca DAHIL
    # EDILMEZ; boylece "yesil" gorunumu bir seyin kosmadigini gizlemez.
    try:
        rv = _yukle("mcp_servers/sap_adt/_reviewer.py", "rv_fx")
        sonuc.append(("CANLI task_for_push('table') veri-kaybi zincirini veriyor",
                      rv.task_for_push("table") == "table_update", str(rv.task_for_push("table"))))
        sonuc.append(("CANLI task_for_push('CDS') buyuk-harfte de cozuluyor",
                      rv.task_for_push("CDS") == "cds_update", str(rv.task_for_push("CDS"))))
    except Exception as exc:
        print(f"  [KOSULMADI] canli task_for_push kontrolu — modul yuklenemedi: "
              f"{type(exc).__name__}: {str(exc)[:60]}")
        print("              (AST tabanli kapsam iddialari YINE DE kosuldu; bu satir "
              "bir SINIRIN beyanidir, gecis degil.)")

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
