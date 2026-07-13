#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""push_textpool.py — Klasik ABAP program text-pool (selection texts + text symbols) PUT + aktivasyon.

NEDEN AYRI ARAÇ: `adt_push_source` / MCP push_source SADECE source/main'i kapsar; text element'ler
ayrı endpoint'tedir (std/06 §5, deferred-trigger C4). Bu araç o boşluğu doldurur.

Endpoint yapısı (canlı ZSD001'den doğrulandı, 2026-06-28):
  /sap/bc/adt/textelements/programs/<prog>           → index (type PROG/PX)
  /sap/bc/adt/textelements/programs/<prog>/source/symbols     (Content-Type vnd.sap.adt.textelements.symbols.v1)
  /sap/bc/adt/textelements/programs/<prog>/source/selections  (... .selections.v1)
  /sap/bc/adt/textelements/programs/<prog>/source/headings    (... .headings.v1)

SOURCE format (canlıdan):
  symbols     : "@MaxLength:NN\\r\\nB00=Başlık\\r\\nB01=..."   (3-harf sembol adı, padding YOK)
  selections  : "NAME    =Etiket\\r\\n\\r\\nNAME2   =..."       (ad 8-haneye SOLA yaslı, aralarda boş satır)

Akış: csrf → GET(etag) → lock(prog, corrNr=transport) → PUT(her alt-kaynak, If-Match+lockHandle+corrNr)
      → UNLOCK → activate(PROG/P + PROG/PX; unlock'tan SONRA — PROG/PX self-conflict 403 önlenir)
      → readback GET (?version=active doğrulama). Ayrıca PUT öncesi offline @MaxLength ön-kontrolü.

ADR 0005: yalnız Z/Y program. Transport ZORUNLU (corrNr). TR master-lang .conn_adt'den gelir.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sap_client import SAPClient  # noqa: E402

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

SUB_CTYPE = {
    "symbols":    "application/vnd.sap.adt.textelements.symbols.v1",
    "selections": "application/vnd.sap.adt.textelements.selections.v1",
    "headings":   "application/vnd.sap.adt.textelements.headings.v1",
}


def _read_payload(path: str) -> str:
    # CRLF normalize: ADT canlı format \r\n kullanır.
    # SONDAKİ newline'ı KIRP: canlı ADT formatında son entry'den sonra \r\n YOKtur
    # (ZSD001/ZSD001 probe ile teyit). Trailing \r\n phantom boş sembol/selection satırı
    # yaratır → SAP DS512 "Text elements contain errors" ile reddeder.
    txt = Path(path).read_text(encoding="utf-8")
    txt = txt.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    return txt.replace("\n", "\r\n")


def _check_symbol_maxlengths(payload: str) -> list:
    """symbols payload'ında her metnin uzunluğu kendi @MaxLength'ini AŞIYOR mu.

    SAP DS512 ("Text elements contain errors") tam bunu der — ama PUT anında + şifreli.
    Bu ön-kontrol push'tan ÖNCE net mesajla yakalar (2026-07-12 dersi). Döner:
    [(sym, text, textlen, maxlen), ...]. Format: her sembolü kendi '@MaxLength:NN' satırı
    önceler; ardından 'SYM=metin'. (=limit sorun değil; yalnız > aşımı DS512 verir.)
    """
    viol = []
    cur_max = None
    for raw in payload.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        m = re.match(r"@MaxLength:(\d+)\s*$", line)
        if m:
            cur_max = int(m.group(1))
            continue
        m = re.match(r"(\S{1,3})=(.*)$", line)
        if m and cur_max is not None:
            text = m.group(2)
            if len(text) > cur_max:
                viol.append((m.group(1), text, len(text), cur_max))
            cur_max = None
    return viol


def main() -> int:
    ap = argparse.ArgumentParser(description="Klasik program text-pool PUT + aktivasyon")
    ap.add_argument("--program", required=True, help="Z/Y program adı (örn ZSD001_P_SOZLESME_KOPYALA)")
    ap.add_argument("--transport", required=True, help="Modifiable transport (corrNr), örn <TRANSPORT>")
    ap.add_argument("--symbols-file", help="symbols (TEXT-xxx / blok başlık) payload dosyası")
    ap.add_argument("--selections-file", help="selection texts payload dosyası")
    ap.add_argument("--headings-file", help="list headings payload dosyası")
    ap.add_argument("--no-activate", action="store_true", help="Aktivasyonu atla (yalnız PUT)")
    args = ap.parse_args()

    prog = args.program
    if not prog[:1].upper() in ("Z", "Y"):
        print(f"[BLOCK] ADR 0005: yalnız Z/Y program. Verilen: {prog}")
        return 2

    subs = []
    for name, f in (("symbols", args.symbols_file),
                    ("selections", args.selections_file),
                    ("headings", args.headings_file)):
        if f:
            subs.append((name, _read_payload(f)))
    if not subs:
        print("[BLOCK] En az bir payload (--symbols-file/--selections-file/--headings-file) gerekir.")
        return 2

    # 2.5) OFFLINE @MaxLength ön-kontrolü — symbols'te metin @MaxLength'i aşarsa SAP DS512
    #      ("text elements contain errors") ile PUT'u REDDEDER (şifreli + round-trip). Push'tan
    #      ÖNCE net mesajla yakala (2026-07-12 dersi: C07/C09/D03 aşımı → DS512 → boş kolon).
    for _name, _payload in subs:
        if _name != "symbols":
            continue
        _viol = _check_symbol_maxlengths(_payload)
        if _viol:
            print("[BLOCK] symbols: metin @MaxLength'i AŞIYOR → SAP DS512 verir (push öncesi yakalandı):")
            for _sym, _txt, _tl, _ml in _viol:
                print(f'        {_sym}="{_txt}"  uzunluk={_tl} > @MaxLength:{_ml}  (+{_tl - _ml})')
            print("        Çözüm: @MaxLength'i büyüt VEYA metni kısalt.")
            return 2

    c = SAPClient()
    adt = c.adt_client
    base = adt.url.rstrip("/")
    prog_l = prog.lower()
    root = f"{base}/sap/bc/adt/textelements/programs/{prog_l}"
    # Lock/unlock hedefi = TEXTELEMENTS (REPT) kaynağı, PROGRAM değil. textelements PUT,
    # REPT resource'un lock handle'ını ister; program (PROG) lock'u "invalid lock handle"
    # (SADT_RESOURCE 026, HTTP 423) ile reddedilir. (ZSD001 notu: "REPT-lock".)
    te_url = f"/sap/bc/adt/textelements/programs/{prog_l}"
    # Aktivasyon hedefi = program; pre-audit PROG/P + PROG/PX'i birlikte toplar.
    prog_obj_url = f"/sap/bc/adt/programs/programs/{prog_l}"

    adt.fetch_csrf_token(force_refresh=True)

    # 1) Mevcut etag'leri al (If-Match için).
    # ÖNEMLİ: tüm istekler _get_headers() ile gider → x-sap-adt-sessiontype:stateful
    # (lock'un denemeler arası ayakta kalması için) + X-CSRF-Token + sap-client.
    # Raw session.get/put bunları set etmediği için 403 CSRF + lock-kaybı oluyordu (fix 2026-06-28).
    etags = {}
    for name, _ in subs:
        hdr = adt._get_headers(accept_type=SUB_CTYPE[name])
        r = adt._request_with_csrf_retry("get", f"{root}/source/{name}", headers=hdr, timeout=30)
        etags[name] = r.headers.get("ETag", "")
        print(f"[GET] {name}: status={r.status_code} etag={etags[name]}")

    # 2) Program objesini kilitle (corrNr=transport).
    print(f"[LOCK] {te_url} (REPT, corrNr={args.transport})")
    lock_handle = adt.lock_object(te_url, access_mode="MODIFY", transport=args.transport)
    print(f"[LOCK] handle={(lock_handle or '')[:40]}...")

    # textelements PUT endpoint'i lockHandle'ı ZORUNLU ister (SADT_RESOURCE 017).
    # NO_LOCK_SUPPORT/implicit TOLERE EDİLMEZ — sessizce lockHandle'sız PUT atmak 400 yer.
    # Genelde gerçek-handle gelmemesi = stale enqueue (EU 510 same-user) → SM12'de temizle.
    if not lock_handle or lock_handle in ("NO_LOCK_SUPPORT", "IMPLICIT_LOCK"):
        print(f"[BLOCK] Gerçek lock handle alınamadı (={lock_handle}). textelements PUT için ZORUNLU.")
        print(f"        Olası sebep: {prog} üzerinde stale enqueue (EU 510). SM12'de kilidi sil, tekrar dene.")
        return 5

    try:
        # 3) Her alt-kaynağı PUT et.
        for name, payload in subs:
            url = f"{root}/source/{name}"
            headers = adt._get_headers(
                accept_type=SUB_CTYPE[name],
                content_type=SUB_CTYPE[name] + "; charset=utf-8",
            )
            if etags.get(name):
                headers["If-Match"] = etags[name]
            params = {"corrNr": args.transport}
            if lock_handle and lock_handle not in ("NO_LOCK_SUPPORT", "IMPLICIT_LOCK", None, ""):
                params["lockHandle"] = lock_handle
            r = adt._request_with_csrf_retry("put", url, headers=headers, params=params,
                                             data=payload.encode("utf-8"), timeout=60)
            ok = r.status_code in (200, 201, 204)
            print(f"[PUT] {name}: status={r.status_code} {'OK' if ok else 'FAIL'}")
            if not ok:
                print(f"      body: {r.text[:600]}")
                return 3
    finally:
        # 5) Unlock — DOĞRU helper (stateful + csrf). Raw POST csrf'siz başarısız olup
        #    lock'u SIZDIRIR (EU 510) → sonraki run'lar lock alamaz. unlock_object kullan.
        #    ⚠ PUT bitti; lock YALNIZ YAZMA içindi → aktivasyondan ÖNCE serbest bırak. Aksi halde
        #    PROG/PX aktivasyonu tool'un KENDİ textelements-lock'uyla çakışır → deterministik
        #    403 "already editing" self-conflict (2026-07-12 dersi: PROG/P farklı endpoint
        #    /programs olduğu için etkilenmiyordu; PROG/PX aynı textelements resource → çakışıyordu).
        try:
            ok_unlock = adt.unlock_object(te_url, lock_handle)
            print(f"[UNLOCK] {'done' if ok_unlock else 'FAILED — SM12 kontrol et'}")
        except Exception as exc:
            print(f"[UNLOCK] FAILED ({exc}) — SM12'de {prog} kilidini kontrol et")

    # 4) Aktivasyon — UNLOCK'TAN SONRA (İKİ AŞAMA; tek PROG/P-activate YETMEZ).
    if not args.no_activate:
        # 4a) Program (PROG/P) — text-symbol referansları + load regen.
        print(f"[ACTIVATE] {prog} (PROG/P)")
        res = adt.activate_object(prog, prog_obj_url)
        print(f"[ACTIVATE] PROG/P success={res.get('success')} errors={len(res.get('errors', []))}")
        for e in res.get("errors", [])[:10]:
            print(f"      E: {e.get('message')}")
        # 4b) Text-pool (PROG/PX) EXPLICIT seed — KRİTİK: program ZATEN AKTİFSE
        #     PROG/P-activate no-op'tur (activationExecuted=false) ve inactive PROG/PX'i
        #     PROMOTE ETMEZ → selections/symbols ACTIVE'de `?`/boş kalır (ekranda textsiz).
        #     Çözüm: PROG/PX'i DOĞRUDAN seed'le. (ZSD001_P_AMBALAJ_TAKIP 2026-06-28.)
        px_body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
            f'<adtcore:objectReference adtcore:uri="/sap/bc/adt/textelements/programs/{prog_l}"'
            f' adtcore:type="PROG/PX" adtcore:name="{prog.upper()}"/>'
            '</adtcore:objectReferences>'
        )
        ph = adt._get_headers(
            accept_type="application/vnd.sap.adt.objectactivation.result.v1+xml",
            content_type="application/xml",
        )
        pr = adt._request_with_csrf_retry(
            "post", f"{base}/sap/bc/adt/activation", headers=ph,
            data=px_body.encode("utf-8"),
            params={"method": "activate", "preauditRequested": "true"}, timeout=60)
        print(f"[ACTIVATE] PROG/PX status={pr.status_code}")
        if pr.status_code != 200:
            print(f"      body: {pr.text[:500]}")

    # 6) Readback DOĞRULAMA — ?version=active ŞART (working DEĞİL).
    #    BE-39: working/inactive readback PUT'lanan metni gösterip YANILTIR; oysa ekran
    #    ACTIVE sürümü kullanır. Active'de `=?` (selection placeholder) veya boş symbols =
    #    PROG/PX promote OLMADI → ekranda textsiz. Bu durumda HATA döndür.
    print("\n=== READBACK (?version=active) ===")
    rc = 0
    for name, _ in subs:
        hdr = adt._get_headers(accept_type=SUB_CTYPE[name])
        r = adt._request_with_csrf_retry(
            "get", f"{root}/source/{name}?version=active", headers=hdr, timeout=30)
        body = r.text
        print(f"--- {name} (status={r.status_code}, ACTIVE) ---")
        print(body)
        empty_sel = (name == "selections" and "=?" in body)
        empty_sym = (name == "symbols" and not body.strip())
        if empty_sel or empty_sym:
            print(f"[FAIL] {name} ACTIVE sürümde `?`/boş — PROG/PX promote OLMADI "
                  f"(explicit PROG/PX activation başarısız?). Ekranda text görünmez.")
            rc = 7
    if rc == 0:
        print("[OK] ACTIVE textpool gerçek metinleri taşıyor (ekranda görünür).")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
