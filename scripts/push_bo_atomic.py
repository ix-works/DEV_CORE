#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""push_bo_atomic.py — RAP BO kaynaklarını ATOMİK güncelle (ddls + bdef + ccimp).

NEDEN VAR (MCP boşluğu):
  `adt_push_source` (MCP) **bdef ve class-include (ccimp) DESTEKLEMEZ** — kanıt:
  `scripts/object_types.py::OBJECT_TYPES` içinde `bdef` girdisi hiç yok. Bu iki obje
  tipi ancak raw ADT REST ile yazılabilir. Bu script o boşluğu kapatır.

NİYE ATOMİK:
  BO parçaları (interface CDS + projection + bdef + behavior pool) birbirine kenetlidir
  (`unmanaged implementation in class ...`). Ayrı ayrı aktive edilirse arada TUTARSIZ
  PENCERE oluşur → runtime dump / sessiz inactive. Bu script TÜM kaynakları önce
  `inactive` PUT eder, sonra HEPSİNİ **tek `/activation` POST**'unda birlikte aktive eder.

YÖNTEM: LOCK → PUT(inactive) → UNLOCK  ×N  →  tek atomik `/activation`.
  Kaynak DİSKTEN okunur (LLM üretimi yok — repo neyse o gider).

⚠ AKTİVASYON YANITI SIKI PARSE EDİLİR (playbook `adt-rap.md`: "200 ama aktive etmedi"):
  `activationExecuted="false"` VEYA `type="E"|"A"` VEYA `severity="E"|"A"` → **FAIL**.
  HTTP 200 tek başına başarı DEĞİLDİR. ("activated" mesajına güvenme.)

KULLANIM:
    python core/scripts/push_bo_atomic.py --transport <TRANSPORT> \
      --ddls  ZSD001_I_BOOKING_ITEM=<path>.cds \
      --ddls  ZSD001_C_BOOKING_ITEM=<path>.cds \
      --bdef  ZSD001_I_BOOKING=<path>.bdef \
      --ccimp ZCL_SD001_BOOKING=<path>.ccimp.abap

    # yalnız aktivasyon (PUT atla; inactive kalmış objeleri toparlamak için)
    python core/scripts/push_bo_atomic.py --transport <TRANSPORT> --activate-only \
      --bdef ZSD001_I_BOOKING= --ccimp ZCL_SD001_BOOKING=

ÇIKIŞ KODLARI: 0=OK · 2=PUT başarısız (aktivasyon YAPILMADI) · 5=aktivasyon FAIL

GEÇMİŞ (T6):
  2026-07-09'da proje `scripts/TempScripts/`'ten core'a terfi. Önceki sürüm donmuş eski
  dünya kökünü (`<eski-proje-kökü>`) hard-code ediyordu → çalıştıran kişi YANLIŞ sistemin
  `.conn_adt`'sini okurdu (ADR 0010 riski) ve `activationExecuted` kontrolü YOKTU.
  Bu sürüm: bağlantı/client/dil `.conn_adt`'den (sap_adt_lib), transport CLI'dan,
  proje kökü hard-code DEĞİL (CORE-01 / ADR 0020). 14 objelik canlı push'ta kanıtlandı.

BAĞLANTI: `sap_adt_lib` `.conn_adt`'yi env `CLAUDE_PROJECT_DIR` → cwd sırasıyla bulur.
  `set_explicit_working_dir` GEREKMEZ — çağırma (proje kökünü sabitler, çoklu-proje kırar).
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# core/scripts import yolu — ATAMA DEĞİL, proje kökü türetmez (CORE-01 muaf).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sap_adt_lib import SAPADTClient  # noqa: E402  # type: ignore

ACTIVATION = "/sap/bc/adt/activation"

_TRANSIENT = ("service cannot be reached", "cannot be reached", "service unavailable",
              "503 service", "500 internal", "icm_http", "partner not reached")


def _transient(r) -> bool:
    if r.status_code in (500, 502, 503):
        return True
    if r.status_code == 400:
        return any(t in (r.text or "")[:800].lower() for t in _TRANSIENT)
    return False


def retry(fn, what: str, n: int = 6):
    """Geçici ICM/bağlantı hatalarında yeniden dene. Kalıcı hatayı GİZLEME — yanıtı döndür."""
    last = None
    for i in range(n):
        try:
            r = fn()
            if _transient(r):
                print(f"   [retry {i+1}/{n}] {what}: geçici ICM (status={r.status_code})")
                last = r
                time.sleep(4)
                continue
            return r
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"   [retry {i+1}/{n}] {what}: bağlantı blip ({type(e).__name__})")
            time.sleep(4)
    if last is not None:
        return last
    raise RuntimeError(f"{what}: bağlantı kurulamadı ({n} deneme)")


def uri_for(kind: str, name: str) -> str:
    n = name.lower()
    if kind == "ddls":
        return f"/sap/bc/adt/ddic/ddl/sources/{n}"
    if kind == "bdef":
        return f"/sap/bc/adt/bo/behaviordefinitions/{n}"
    if kind == "class":
        return f"/sap/bc/adt/oo/classes/{n}"
    raise ValueError(f"bilinmeyen obje tipi: {kind}")


class Pusher:
    def __init__(self, client: SAPADTClient, transport: str):
        self.c = client
        self.transport = transport
        # sap-client / dil `.conn_adt`'den — hard-code YOK (çoklu-sistem güvenliği)
        self.params = {"sap-client": self.c.client, "sap-language": self.c.language}

    def csrf(self) -> str:
        r = retry(lambda: self.c.session.get(
            self.c.url + "/sap/bc/adt/discovery", params=self.params,
            headers={"X-CSRF-Token": "Fetch"}, verify=False, timeout=30), "csrf")
        return r.headers.get("X-CSRF-Token", "")

    def put_inactive(self, kind: str, name: str, path: str, tok: str) -> bool:
        """LOCK → PUT source (aktive ETMEZ) → UNLOCK. Unlock finally'de garanti."""
        obj = uri_for(kind, name)
        put_uri = obj + ("/includes/implementations" if kind == "class" else "/source/main")
        src = Path(path).read_text(encoding="utf-8")

        lr = retry(lambda: self.c.session.post(
            self.c.url + obj,
            params={"_action": "LOCK", "accessMode": "MODIFY", "corrNr": self.transport},
            headers={"X-CSRF-Token": tok, "X-sap-adt-sessiontype": "stateful",
                     "Accept": "application/*,application/vnd.sap.as+xml;"
                               "dataname=com.sap.adt.lock.result"},
            verify=False, timeout=30), f"{name} LOCK")
        m = re.search(r"<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>", lr.text)
        if not m:
            print(f"[FAIL] {name} LOCK status={lr.status_code} :: {lr.text[:300]}")
            return False
        handle = m.group(1)

        ok = False
        try:
            pr = retry(lambda: self.c.session.put(
                self.c.url + put_uri,
                params={"corrNr": self.transport, "lockHandle": handle},
                headers={"X-CSRF-Token": tok, "Content-Type": "text/plain; charset=utf-8",
                         "Accept": "*/*", **self.params},
                data=src.encode("utf-8"), verify=False, timeout=60), f"{name} PUT")
            print(f"[PUT] {name} ({kind}) status={pr.status_code}")
            if pr.status_code in (200, 201, 204):
                ok = True
            else:
                print("   BODY: " + pr.text[:400].replace("\n", " "))
        finally:
            ur = retry(lambda: self.c.session.post(
                self.c.url + obj, params={"_action": "UNLOCK", "lockHandle": handle},
                headers={"X-CSRF-Token": tok, "X-sap-adt-sessiontype": "stateful"},
                verify=False, timeout=15), f"{name} UNLOCK")
            print(f"   [unlock] {name} status={ur.status_code}")
        return ok

    def activate_many(self, refs: list[tuple[str, str]], tok: str) -> bool:
        """Tüm objeleri TEK POST'ta aktive et. Yanıtı SIKI parse et."""
        body = ['<?xml version="1.0" encoding="UTF-8"?>',
                '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">']
        for kind, name in refs:
            body.append(f'  <adtcore:objectReference adtcore:uri="{uri_for(kind, name)}" '
                        f'adtcore:name="{name.upper()}"/>')
        body.append('</adtcore:objectReferences>')

        r = retry(lambda: self.c.session.post(
            self.c.url + ACTIVATION,
            params={"method": "activate", "preauditRequested": "false"},
            headers={"X-CSRF-Token": tok, "Content-Type": "application/xml",
                     "Accept": "application/xml", **self.params},
            data="\n".join(body).encode("utf-8"), verify=False, timeout=180), "ACTIVATE")

        txt = r.text or ""
        # HTTP 200 YETMEZ: SAP "aktive etmedim" diyebilir ve yine 200 döner.
        executed_false = 'activationExecuted="false"' in txt
        has_err = any(s in txt for s in ('type="E"', 'type="A"',
                                         'severity="E"', 'severity="A"'))
        ok = (r.status_code < 400) and not has_err and not executed_false
        print(f"[ACTIVATE] status={r.status_code} executedFalse={executed_false} "
              f"errMsg={has_err} -> {'OK' if ok else 'FAIL'}")
        if txt.strip():
            print("   RESP: " + txt[:1200].replace("\n", " "))
        return ok


def _parse_pairs(pairs: list[str]) -> list[tuple[str, str]]:
    out = []
    for p in pairs or []:
        name, _, path = p.partition("=")
        out.append((name.strip(), path.strip()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "push_bo_atomic").split("\n")[0])
    ap.add_argument("--ddls", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--bdef", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--ccimp", action="append", default=[], metavar="CLASS=PATH")
    ap.add_argument("--transport", required=True, help="açık transport (release EDİLMEZ)")
    ap.add_argument("--activate-only", action="store_true",
                    help="PUT atla, yalnız atomik aktivasyon (inactive toparlama)")
    a = ap.parse_args()

    client = SAPADTClient()
    pusher = Pusher(client, a.transport)
    tok = pusher.csrf()
    print(f"CSRF: {'ok' if tok else 'YOK'} | URL={client.url} | client={client.client} "
          f"| dil={client.language}")
    if not tok:
        print("[ABORT] CSRF alınamadı.", file=sys.stderr)
        return 1

    refs: list[tuple[str, str]] = []
    for kind, pairs in (("ddls", a.ddls), ("bdef", a.bdef), ("class", a.ccimp)):
        for name, path in _parse_pairs(pairs):
            if not a.activate_only:
                if not path:
                    print(f"[ABORT] {name}: yol verilmedi (--activate-only mi demek istedin?)",
                          file=sys.stderr)
                    return 2
                if not pusher.put_inactive(kind, name, path, tok):
                    print(f"\n[ABORT] {name} PUT başarısız — aktivasyon YAPILMADI "
                          f"(tutarsız pencere açılmadı).", file=sys.stderr)
                    return 2
            refs.append((kind, name))

    if not refs:
        print("[ABORT] obje verilmedi.", file=sys.stderr)
        return 1

    print(f"\n=== ATOMİK ACTIVATE ({len(refs)} obje): {[n for _, n in refs]} ===")
    if not pusher.activate_many(refs, tok):
        print("\n[ABORT] Aktivasyon FAIL — DUR. Canlı durumu `worklist_audit.py` ile "
              "netleştir; kendi başına düzeltmeye çalışma.", file=sys.stderr)
        return 5

    print(f"\n[DONE] {[n for _, n in refs]} atomik aktive edildi.")
    print("⚠ Readback ZORUNLU: `adt_get` ile canlı source + version=active doğrula "
          "(bu çıktı 'yazdım' der, 'doğru yazdım' demez).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
