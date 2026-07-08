#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sap_set_object_description.py — Mevcut bir Z/Y objesinin adtcore:description'ını değiştir.

Açıklama (short text) yalnız create-time'da set ediliyor; sonradan değiştirmenin tek yolu
objenin ANA envelope'unu GET → tek attribute (adtcore:description) değiştir → lock → PUT →
unlock. Blast-radius: SADECE description attribute'u (geri kalan envelope birebir korunur).

Generic + reusable (class/bdef/srvb/srvd/...) — copy-create edilmiş objelerde ORDER-default
("Sefer...") açıklamayı düzeltmek için. Object source'a DOKUNMAZ.

Kullanım:
    python scripts/sap_set_object_description.py <NAME> --type <T> --desc "<TR metin>" --transport <TR>
    python scripts/sap_set_object_description.py <NAME> --type <T> --desc "..." --dry-run   # yazmadan göster

ADR 0005-D: yeni text TR olmalı (master language zaten TR; bu sadece description). Yazma sonrası
readback ile DOĞRULAR (yeni değer canlıda var mı) — "updated" mesajına güvenmez.
"""
import argparse
import io
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    for _s in ("stdout", "stderr"):
        _st = getattr(sys, _s)
        if hasattr(_st, "buffer"):
            setattr(sys, _s, io.TextIOWrapper(_st.buffer, encoding="utf-8", errors="replace"))

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Obje tipi → ANA obje URL segmenti (/source/main DEĞİL — envelope description burada).
_MAIN_URI_SEG = {
    "class": "oo/classes", "clas": "oo/classes",
    "bdef": "bo/behaviordefinitions", "behaviordefinition": "bo/behaviordefinitions",
    "srvb": "businessservices/bindings", "servicebinding": "businessservices/bindings",
    "srvd": "ddic/srvd/sources", "servicedefinition": "ddic/srvd/sources",
    "ddls": "ddic/ddl/sources", "cds": "ddic/ddl/sources",
    "ddlx": "ddic/ddlx/sources", "metadataextension": "ddic/ddlx/sources",
    "dcl": "acm/dcl/sources", "accesscontrol": "acm/dcl/sources",
    "prog": "programs/programs", "program": "programs/programs",
}


def _main_url(name: str, object_type: str):
    from urllib.parse import quote
    seg = _MAIN_URI_SEG.get((object_type or "").lower().strip())
    if not seg:
        return None
    return f"/sap/bc/adt/{seg}/{quote(name.lower(), safe='')}"


def _desc_in(xml: str):
    m = re.search(r'adtcore:description="([^"]*)"', xml)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Mevcut Z/Y objesinin açıklamasını (adtcore:description) değiştir")
    ap.add_argument("name")
    ap.add_argument("--type", required=True, help="class/bdef/srvb/srvd/ddls/...")
    ap.add_argument("--desc", required=True, help="Yeni TR açıklama")
    ap.add_argument("--transport", default=None, help="Değiştirilebilir transport (corrNr)")
    ap.add_argument("--dry-run", action="store_true", help="Yazma; sadece mevcut→yeni göster")
    args = ap.parse_args()

    name = args.name.upper()
    if not re.match(r"^[ZY]", name):
        print(f"[RED] {name}: yalnız Z/Y objesi (ADR 0005-A).")
        return 2
    url = _main_url(name, args.type)
    if not url:
        print(f"[RED] Tip '{args.type}' için ana URL segmenti yok. Desteklenen: {sorted(set(_MAIN_URI_SEG))}")
        return 2

    try:
        from sap_client import SAPClient
        adt = SAPClient().adt_client
    except Exception as exc:
        print(f"[FAIL] SAP client init: {exc}")
        return 1

    full = f"{adt.url}{url}"
    # 1) GET envelope (+ ETag + Content-Type)
    r = adt.session.get(full, headers={"Accept": "application/*"}, timeout=adt.timeout_default)
    if r.status_code != 200:
        print(f"[FAIL] GET {url} → HTTP {r.status_code}: {r.text[:200]}")
        return 1
    body = r.text
    etag = r.headers.get("ETag") or r.headers.get("etag")
    ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip() or "application/xml"
    old = _desc_in(body)
    print(f"[GET] {name} ({args.type}) ctype={ctype} etag={'var' if etag else 'yok'}")
    print(f"      mevcut açıklama: {old!r}")
    print(f"      yeni  açıklama : {args.desc!r}")

    if old == args.desc:
        print("[NOOP] Açıklama zaten istenen değer — değişiklik yok.")
        return 0
    if old is None:
        print("[FAIL] Envelope'da adtcore:description attribute'u bulunamadı — güvenli değiştirilemez.")
        return 1

    # 2) Tek attribute değiştir (geri kalan envelope birebir korunur)
    new_body = body.replace(f'adtcore:description="{old}"', f'adtcore:description="{args.desc}"', 1)
    if new_body == body or _desc_in(new_body) != args.desc:
        print("[FAIL] Attribute değişimi uygulanamadı (beklenmeyen envelope formatı).")
        return 1

    if args.dry_run:
        print("[DRY-RUN] Yazılmadı. (gerçek için --dry-run kaldır + --transport ver)")
        return 0

    # 3) LOCK
    try:
        lock_handle = adt.lock_object(url, access_mode="MODIFY", transport=args.transport)
    except Exception as exc:
        print(f"[FAIL] lock: {exc}")
        return 1

    # 4) PUT envelope (aynı content-type, stateful, If-Match, lockHandle, corrNr)
    try:
        headers = adt._get_headers(ctype, ctype)
        headers["X-sap-adt-sessiontype"] = "stateful"
        if etag:
            headers["If-Match"] = etag
        params = {"lockHandle": lock_handle}
        if args.transport:
            params["corrNr"] = args.transport
        pr = adt.session.put(full, headers=headers, params=params,
                             data=new_body.encode("utf-8"), timeout=adt.timeout_default)
        put_ok = pr.status_code in (200, 204)
        if not put_ok:
            print(f"[FAIL] PUT → HTTP {pr.status_code}: {pr.text[:300]}")
    finally:
        try:
            adt.unlock_object(url, lock_handle)
        except Exception as exc:
            print(f"[WARN] unlock: {exc}")

    if not put_ok:
        return 1

    # 5) READBACK — "updated" mesajına güvenme; canlıdan teyit et (ADR 0006 / BE-15)
    rb = adt.session.get(full, headers={"Accept": "application/*"}, timeout=adt.timeout_default)
    now = _desc_in(rb.text) if rb.status_code == 200 else None
    if now == args.desc:
        print(f"[OK] {name}: açıklama güncellendi + readback DOĞRULANDI → {now!r}")
        return 0
    print(f"[FAIL] readback uyuşmuyor — canlı açıklama: {now!r} (beklenen {args.desc!r}). PUT oturmadı.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
