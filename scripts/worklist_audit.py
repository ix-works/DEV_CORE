#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worklist_audit.py — SAP "Inactive Objects" worklist denetimi (LİDER çalıştırır).

NE: ADT inactive-objects worklist'ini (GET /sap/bc/adt/activation/inactiveobjects) çeker,
her girdiyi CANLI yeniden-doğrular (active sürüm var mı? inactive sürüm var mı? sahip? transport?)
ve TAKSONOMIYE göre sınıflar. Worklist'e GÜVENMEZ — out-of-band (SE24/SE80 elle silme/aktive/edit,
başka process) değişiklikleri CANLI gerçeğe göre yakalar.

NEDEN: root CDS'e alan eklenince FOR-BEHAVIOR BDEF inactive düşer + class aktivasyonu BDEF'i
co-aktive etmez → sessiz inactive bağımlı. Gateway'in HTTP-200 doğrulaması bunu kaçırdı (2026-06-21).
Bu denetim, LİDER tarafından COMMIT-ANI + GÜN-SONU + ON-DEMAND çalıştırılır (ajan hot-path'inde DEĞİL).

KONSERVATİF: default yalnız RAPORLAR. `--discard-phantoms` ile YALNIZ PHANTOM (ne active ne inactive =
silinmiş, worklist bayat girdi) temizlenir — mekanizma canlı doğrulandı (2026-06-22, POST ?action=delete +
objectReferences envelope; her discard re-fetch ile teyit, HTTP-200'e körü körüne güvenme). Gerçek-inactive
(REAL_INACTIVE/INACTIVE_ONLY/STALE = WIP olabilir) ASLA otomatik aktive/discard EDİLMEZ — yalnız PHANTOM.

Kullanım:
    python scripts/worklist_audit.py                      # tüm worklist, rapor
    python scripts/worklist_audit.py --package ZSD001_CLC # pakete filtre + commit-gate (exit!=0)
    python scripts/worklist_audit.py --mine               # yalnız bağlantı-kullanıcısının objeleri
    python scripts/worklist_audit.py --discard-phantoms   # PHANTOM bayat girdileri temizle (yalnız phantom)
    python scripts/worklist_audit.py --json               # makine-okur çıktı

Exit: 0 = hedef-kapsamda gerçek-inactive YOK (commit güvenli); 1 = var (commit'ten önce çöz/raporla);
      2 = worklist okunamadı (soft, bağlantı/erişim).
"""
import argparse
import io
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

if sys.platform == "win32":
    for _s in ("stdout", "stderr"):
        _f = getattr(sys, _s)
        if hasattr(_f, "buffer"):
            setattr(sys, _s, io.TextIOWrapper(_f.buffer, encoding="utf-8", errors="replace"))

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

_NS = {"ioc": "http://www.sap.com/abapxml/inactiveCtsObjects",
       "adtcore": "http://www.sap.com/adt/core"}
_WORKLIST_URI = "/sap/bc/adt/activation/inactiveobjects"
_WORKLIST_ACCEPT = "application/vnd.sap.adt.inactivectsobjects.v1+xml"


def _fetch_worklist(adt):
    """Worklist XML'ini çek → ham metin | None (okunamadı)."""
    try:
        r = adt.session.get(f"{adt.url}{_WORKLIST_URI}",
                            headers={"Accept": _WORKLIST_ACCEPT}, timeout=25)
        return r.text if r.status_code == 200 else None
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] worklist GET: {exc}")
        return None


_DISCARD_CT = "application/vnd.sap.adt.inactivectsobjects.v1+xml"


def _csrf_token(adt):
    """CSRF token al (X-CSRF-Token: Fetch) — discard POST için."""
    try:
        r = adt.session.get(f"{adt.url}{_WORKLIST_URI}",
                            headers={"Accept": _WORKLIST_ACCEPT, "X-CSRF-Token": "Fetch"}, timeout=25)
        return r.headers.get("x-csrf-token") or r.headers.get("X-CSRF-Token")
    except Exception:  # noqa: BLE001
        return None


def _discard_phantom(adt, token, entry):
    """Tek girdiyi inactive-worklist'ten discard et (POST ?action=delete).

    Mekanizma CANLI doğrulandı (2026-06-22): envelope = adtcore:objectReferences (ioc DEĞİL;
    ioc gönderilince SAP 'expected objectReferences' ile reddeder). Class girdisi discard'ı
    alt metot (CLAS/OM) referanslarını da otomatik temizler. YALNIZ çağıran tarafından PHANTOM
    sınıflanmış girdiye uygulanmalı (REAL_INACTIVE/INACTIVE_ONLY/STALE = WIP → ASLA).
    Döner: True (HTTP 200) | False. Gerçek silinmeyi çağıran re-fetch ile doğrular.
    """
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
        f'<adtcore:objectReference adtcore:uri="{entry["uri"]}" adtcore:name="{entry["name"]}"/>'
        '</adtcore:objectReferences>'
    )
    try:
        r = adt.session.post(
            f"{adt.url}{_WORKLIST_URI}", params={"action": "delete"},
            headers={"X-CSRF-Token": token or "Fetch", "Content-Type": _DISCARD_CT,
                     "Accept": "application/xml"},
            data=body.encode("utf-8"), timeout=25)
        return r.status_code == 200
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] discard POST {entry['name']}: {exc}")
        return False


def _parse_entries(xml_text):
    """XML → obje-seviyesi girdiler. transport-seviyesi (boş object) + method (CLAS/OM) ELE.

    Döner: [{name, type, uri, user, deleted, transport}, ...] (yalnız ana objeler).
    """
    out, seen = [], set()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        print(f"[FAIL] worklist XML parse: {exc}")
        return None
    for entry in root.findall("ioc:entry", _NS):
        obj = entry.find("ioc:object", _NS)
        if obj is None:
            continue
        ref = obj.find("ioc:ref", _NS)
        if ref is None:
            continue                                   # transport-seviyesi (boş <ioc:object/>)
        a_type = ref.get(f"{{{_NS['adtcore']}}}type", "") or ""
        a_name = ref.get(f"{{{_NS['adtcore']}}}name", "") or ""
        a_uri = ref.get(f"{{{_NS['adtcore']}}}uri", "") or ""
        if a_type.endswith("/OM") or "#type=" in a_uri:
            continue                                   # method/sub-obje → ana class girdisi var
        key = a_uri.split("#")[0].rstrip("/")
        if not a_name or key in seen:
            continue
        seen.add(key)
        tr = entry.find("ioc:transport", _NS)
        tr_name = ""
        if tr is not None:
            tref = tr.find("ioc:ref", _NS)
            if tref is not None:
                tr_name = tref.get(f"{{{_NS['adtcore']}}}name", "") or ""
        out.append({
            "name": a_name.strip(),
            "type": a_type,
            "uri": key,
            "user": obj.get(f"{{{_NS['ioc']}}}user", "") or "",
            "deleted": (obj.get(f"{{{_NS['ioc']}}}deleted", "") or "").lower() == "true",
            "transport": tr_name,
        })
    return out


def _version_exists(adt, uri, version):
    """uri'nin verilen sürümü (active|inactive) SAP'de var mı? (object-structure GET)."""
    try:
        r = adt.session.get(f"{adt.url}{uri}", params={"version": version}, timeout=20)
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return None


def _object_package(client, name, simple_type):
    try:
        md = client.get_object_metadata(name, object_type=simple_type)
        if isinstance(md, dict):
            return md.get("package") or md.get("devclass") or None
        return None
    except Exception:  # noqa: BLE001
        return None


_SIMPLE = {"CLAS/OC": "class", "DDLS/DF": "ddls", "DCLS/DL": "dcl",
           "BDEF/BDO": "bdef", "SRVD/SRV": "srvd", "SRVB/SVB": "srvb",
           "INTF/OI": "interface", "PROG/P": "program", "DDLX/EX": "ddlx",
           "TABL/DT": "table", "DTEL/DE": "dtel", "DOMA/DD": "domain"}


def _classify(adt, client, e):
    """Bir girdiyi CANLI doğrula + sınıfla.

    Sınıflar:
      PHANTOM       — ne active ne inactive sürüm var (silinmiş; worklist bayat girdi)
      STALE         — active var, distinct inactive YOK (zaten aktif; bayat girdi)
      INACTIVE_ONLY — active YOK, inactive var (yaratılmış, hiç aktive edilmemiş — WIP/terk)
      REAL_INACTIVE — active VAR + distinct inactive VAR (gerçek bekleyen değişiklik)
      UNKNOWN       — sürüm okunamadı (soft)
    """
    uri = e["uri"]
    has_active = _version_exists(adt, uri, "active")
    has_inactive = _version_exists(adt, uri, "inactive")
    simple = _SIMPLE.get(e["type"])
    pkg = _object_package(client, e["name"], simple) if simple else None
    if has_active is None and has_inactive is None:
        cls = "UNKNOWN"
    elif not has_active and not has_inactive:
        cls = "PHANTOM"
    elif not has_active and has_inactive:
        cls = "INACTIVE_ONLY"
    elif has_active and not has_inactive:
        cls = "STALE"
    else:
        cls = "REAL_INACTIVE"
    return {**e, "package": pkg, "class": cls,
            "has_active": has_active, "has_inactive": has_inactive}


# commit-gate'i tetikleyen sınıflar (gerçek bekleyen inactive — yazım yan-etkisi olabilir).
# (PHANTOM = --discard-phantoms ile temizlenebilir; STALE = bayat, zararsız rapor.)
_GATE = {"REAL_INACTIVE", "INACTIVE_ONLY"}


def main():
    ap = argparse.ArgumentParser(description="SAP inactive-objects worklist denetimi (lider)")
    ap.add_argument("--package", default="", help="Yalnız bu pakete filtre + commit-gate exit kodu")
    ap.add_argument("--mine", action="store_true", help="Yalnız bağlantı-kullanıcısının objeleri")
    ap.add_argument("--discard-phantoms", action="store_true",
                    help="PHANTOM (silinmiş, ne active ne inactive) bayat girdileri temizle — YALNIZ phantom")
    ap.add_argument("--json", action="store_true", help="JSON çıktı")
    args = ap.parse_args()

    try:
        from sap_client import SAPClient  # type: ignore
        client = SAPClient()
        adt = getattr(client, "adt_client", None) or client
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] SAP client init: {exc}")
        return 2

    me = str(getattr(adt, "user", "") or getattr(client, "user", "") or "").upper()
    xml = _fetch_worklist(adt)
    if xml is None:
        print("[SOFT] worklist okunamadı (status!=200 / erişim). Commit-gate ATLANDI (soft).")
        return 2
    entries = _parse_entries(xml)
    if entries is None:
        return 2

    rows = [_classify(adt, client, e) for e in entries]

    # --discard-phantoms: YALNIZ PHANTOM girdileri temizle (silinmiş objelere yetim referans).
    # Gerçek-inactive (REAL_INACTIVE/INACTIVE_ONLY/STALE = WIP olabilir) ASLA dokunulmaz.
    if args.discard_phantoms:
        phantoms = [r for r in rows if r["class"] == "PHANTOM"]
        if not phantoms:
            print("  [discard] PHANTOM yok — temizlenecek bir şey yok.")
        else:
            token = _csrf_token(adt)
            posted = [r for r in phantoms if _discard_phantom(adt, token, r)]
            # Re-fetch + GERÇEK silinmeyi doğrula (HTTP-200'e körü körüne güvenme).
            xml2 = _fetch_worklist(adt)
            entries2 = _parse_entries(xml2) if xml2 else None
            still = {e["name"].upper() for e in (entries2 or [])}
            cleared = [r["name"] for r in posted if r["name"].upper() not in still]
            failed = [r["name"] for r in phantoms if r["name"].upper() in still]
            print(f"  [discard] PHANTOM temizlendi={len(cleared)} {cleared}"
                  + (f"; BAŞARISIZ={len(failed)} {failed}" if failed else ""))
            # Kalan rapor güncel worklist üzerinden olsun.
            if entries2 is not None:
                entries = entries2
                rows = [_classify(adt, client, e) for e in entries]

    if args.mine and me:
        rows = [r for r in rows if r["user"].upper() == me]
    pkg_filter = args.package.upper()
    in_scope = [r for r in rows if (not pkg_filter or (r["package"] or "").upper() == pkg_filter)]

    if args.json:
        print(json.dumps({"me": me, "package": pkg_filter or None,
                          "all": rows, "in_scope": in_scope}, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== INACTIVE-OBJECTS WORKLIST DENETİMİ (kullanıcı={me or '?'}"
              f"{', paket=' + pkg_filter if pkg_filter else ''}) ===")
        if not rows:
            print("  Worklist BOŞ — temiz.")
        for r in rows:
            scope = "  " if (not pkg_filter or (r["package"] or "").upper() == pkg_filter) else " ·"
            print(f"{scope}[{r['class']:13}] {r['name']:42} type={r['type']:9} "
                  f"pkg={r['package'] or '-':14} user={r['user'] or '-':10} tr={r['transport'] or '-'}")
        # öneri özeti
        phantom = [r for r in rows if r["class"] == "PHANTOM"]
        stale = [r for r in rows if r["class"] == "STALE"]
        real = [r for r in in_scope if r["class"] in _GATE]
        print("\n--- ÖZET / ÖNERİ ---")
        if phantom:
            print(f"  PHANTOM ({len(phantom)}): silinmiş/yok — worklist bayat girdisi. "
                  f"Temizlemek için: python scripts/worklist_audit.py --discard-phantoms")
        if stale:
            print(f"  STALE ({len(stale)}): zaten aktif, bayat girdi. (v1: rapor.)")
        if real:
            print(f"  ⚠️ GERÇEK-INACTIVE ({len(real)})"
                  f"{' [paket ' + pkg_filter + ']' if pkg_filter else ''} — KARAR GEREK:")
            for r in real:
                hint = ("yazım yan-etkisi olabilir → AKTİVE et" if r["class"] == "REAL_INACTIVE"
                        else "yaratılmış/aktive-edilmemiş → WIP mi, terk mi? (aktive/sil kararı insanda)")
                print(f"      - {r['name']} ({r['class']}, tr={r['transport'] or '-'}): {hint}")
        else:
            print("  ✅ Hedef kapsamda GERÇEK-INACTIVE yok — commit güvenli.")

    real_in_scope = [r for r in in_scope if r["class"] in _GATE]
    return 1 if real_in_scope else 0


if __name__ == "__main__":
    raise SystemExit(main())
