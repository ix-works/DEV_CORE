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

Q175 (canlı ölçüm 2026-09-13, DDLS) — iki davranış bu dosyada yaşar:
  ① PUT `412 SADT_RESOURCE 043` ("Client ETag <A> does not match the object ETag <B>"):
     bekleyen inaktif sürüm YOKKEN bile envelope GET'in ETag'i (aktif) sunucunun beklediği
     değil. Gövdedeki <B> ile **TEK** retry, **YENİ bir LOCK döngüsünde** (ölçülen başarılı
     retry yeni lock'la yapıldı; aynı lock içinde retry ÖLÇÜLMEDİ). İkinci 412 = FAIL.
     ETag hâlâ LOCK'tan ÖNCE elde edilir (ilk GET ya da 412 gövdesi) — lock ile PUT arasına
     GET girmez (2026-07-30 423 vakası, `sap_adt_lib.fetch_source_etag` docstring'i).
  ② Başarılı PUT objeyi **hemen inaktife düşürür** (DDLS ölçüldü). Bu yüzden PUT sonrası:
     aktive-bekleyen listesi (`get_inactive_objects`) → listedeyse `activate_object` →
     liste YENİDEN okunur (aktivasyon yanıtının "başarılı"sına tek başına güvenilmez, Q187)
     → açıklama `?version=active` üzerinden okunur. Herhangi biri tutmazsa exit 1 ve objenin
     inaktif kaldığı açıkça yazılır.
  `--force-put`: açıklama zaten aynıysa da yazma yolunu koşar (canlı doğrulama; içerik değişmez).
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


# 412 gövdesi (canlı, SADT_RESOURCE 043): `T100KEY-V2` = sunucunun beklediği (object) ETag;
# aynı değer mesaj metninde "does not match the object ETag <B> in the server" olarak da geçer.
_ETAG_V2_RE = re.compile(r'<entry key="T100KEY-V2">([^<\s]+)</entry>')
_ETAG_METIN_RE = re.compile(r'object ETag (\S+) ')


def _etag_from_412(text: str):
    """412 gövdesinden sunucunun beklediği ETag; çıkarılamazsa None (tahmin YOK)."""
    text = text or ""
    if "SADT_RESOURCE" in text and '<entry key="T100KEY-NO">043</entry>' in text:
        m = _ETAG_V2_RE.search(text)
        if m:
            return m.group(1)
    m = _ETAG_METIN_RE.search(text)
    return m.group(1) if m else None


def _lock_put_unlock(adt, url, full, ctype, data, etag, transport):
    """TEK LOCK → PUT → UNLOCK döngüsü. Döner: (http_kodu | None (lock alınamadı), gövde, corrNr)."""
    try:
        lock_handle = adt.lock_object(url, access_mode="MODIFY", transport=transport)
    except Exception as exc:
        print(f"[FAIL] lock: {exc}")
        return None, "", None
    try:
        headers = adt._get_headers(ctype, ctype)
        headers["X-sap-adt-sessiontype"] = "stateful"
        if etag:
            headers["If-Match"] = etag
        params = {"lockHandle": lock_handle}
        # corrNr, İSTENEN transport'tan değil LOCK YANITINDAN türetilir (kanonik kalıp:
        # sap_client.py::push_object → `_last_lock_effective_transport or transport`).
        # SAP, objenin gerçekte kayıtlı olduğu transport'u CORRNR ile döndürür; istenen ile
        # farklıysa istenen'i kullanmak objenin kayıtlı OLMADIĞI bir transport'a yazmak demektir
        # → SAP kilidi verir ama değişikliği reddeder (423). Bkz. playbook/known-errors.md §12.7.
        # CORRNR boşsa `or` sayesinde davranış bugünküyle BİREBİR aynıdır (regresyon yok).
        eff_transport = getattr(adt, "_last_lock_effective_transport", None) or transport
        if eff_transport:
            params["corrNr"] = eff_transport
        pr = adt.session.put(full, headers=headers, params=params,
                             data=data, timeout=adt.timeout_default)
        return pr.status_code, (pr.text or ""), eff_transport
    finally:
        try:
            adt.unlock_object(url, lock_handle)
        except Exception as exc:
            print(f"[WARN] unlock: {exc}")


def _inactive_listed(adt, name: str, url: str):
    """Obje aktive-bekleyen listesinde mi? (True/False, iz) — okunamazsa (None, sebep).

    Kaynak `sap_adt_lib.get_inactive_objects` (ayrıştırılamayan yanıtı "liste boş" SAYMAZ,
    istisna fırlatır). Eşleşme: ad (büyük harf) ya da URI (`#` öncesi) obje URL'i/altı.
    """
    try:
        entries = adt.get_inactive_objects()
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    root = url.lower()
    for e in entries or []:
        e_name = (e.get("name") or "").strip().upper()
        e_uri = (e.get("uri") or "").split("#", 1)[0].lower()
        if e_name == name or e_uri == root or e_uri.startswith(root + "/"):
            return True, f"{e_name} ({e.get('type')})"
    return False, ""


_TEKRAR_NOTU = ("Script'i yeniden koşmak bunu DÜZELTMEYEBİLİR ([NOOP] dalı yalnız parametresiz "
                "GET'e bakar) — `adt_inactive_objects` ile bak, `adt_activate` ile aktive et.")


def _activate_and_verify(adt, name: str, url: str, full: str, desc: str) -> int:
    """PUT oturduktan SONRA: gerekirse aktivasyon + bağımsız readback. 0 = doğrulandı."""
    listed, trace = _inactive_listed(adt, name, url)
    if listed is None:
        print(f"[FAIL] PUT oturdu ama aktive-bekleyen listesi OKUNAMADI ({trace}) — obje {name} "
              f"İNAKTİF KALMIŞ OLABİLİR, aktif durum DOĞRULANAMADI. {_TEKRAR_NOTU}")
        return 1
    if listed:
        print(f"[INFO] açıklama PUT'u objeyi inaktife düşürdü (aktive-bekleyen: {trace}) → aktivasyon")
        try:
            res = adt.activate_object(name, url) or {}
        except Exception as exc:
            res = {"success": False, "errors": [{"message": f"{type(exc).__name__}: {exc}"}]}
        if not res.get("success"):
            errs = "; ".join(str(e.get("message", "")) for e in (res.get("errors") or []))
            print(f"[FAIL] aktivasyon BAŞARISIZ — obje {name} İNAKTİF KALDI (yeni açıklama "
                  f"yalnız inaktif sürümde). Hata: {errs[:300] or '(mesaj yok)'}. {_TEKRAR_NOTU}")
            return 1
        listed, trace = _inactive_listed(adt, name, url)
        if listed is not False:
            state = f"hâlâ listede: {trace}" if listed else f"liste okunamadı: {trace}"
            print(f"[FAIL] aktivasyon 'başarılı' dedi ama bağımsız readback tutmadı ({state}) — "
                  f"obje {name} İNAKTİF KALDI ya da doğrulanamadı. {_TEKRAR_NOTU}")
            return 1
    rb = adt.session.get(full, headers={"Accept": "application/*"}, params={"version": "active"},
                         timeout=adt.timeout_default)
    now = _desc_in(rb.text or "") if rb.status_code == 200 else None
    if now == desc:
        print(f"[OK] {name}: açıklama güncellendi + AKTİF sürümde readback DOĞRULANDI → {now!r} "
              f"(aktive-bekleyen listesinde yok)")
        return 0
    print(f"[FAIL] readback uyuşmuyor — AKTİF sürümdeki açıklama: {now!r} (beklenen {desc!r}, "
          f"HTTP {rb.status_code}). PUT aktif sürüme oturmadı.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Mevcut Z/Y objesinin açıklamasını (adtcore:description) değiştir")
    ap.add_argument("name")
    ap.add_argument("--type", required=True, help="class/bdef/srvb/srvd/ddls/...")
    ap.add_argument("--desc", required=True, help="Yeni TR açıklama")
    ap.add_argument("--transport", default=None, help="Değiştirilebilir transport (corrNr)")
    ap.add_argument("--dry-run", action="store_true", help="Yazma; sadece mevcut→yeni göster")
    ap.add_argument("--force-put", action="store_true",
                    help="Açıklama zaten aynıysa da LOCK/PUT/aktivasyon yolunu koş "
                         "(canlı doğrulama; içerik değişmez)")
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

    if old is None:
        print("[FAIL] Envelope'da adtcore:description attribute'u bulunamadı — güvenli değiştirilemez.")
        return 1
    if old == args.desc:
        if not args.force_put:
            print("[NOOP] Açıklama zaten istenen değer — değişiklik yok.")
            return 0
        print("[FORCE-PUT] Açıklama aynı; envelope DEĞİŞTİRİLMEDEN yazma yolu koşulacak.")
        new_body = body
    else:
        # 2) Tek attribute değiştir (geri kalan envelope birebir korunur)
        new_body = body.replace(f'adtcore:description="{old}"', f'adtcore:description="{args.desc}"', 1)
        if new_body == body or _desc_in(new_body) != args.desc:
            print("[FAIL] Attribute değişimi uygulanamadı (beklenmeyen envelope formatı).")
            return 1

    if args.dry_run:
        print("[DRY-RUN] Yazılmadı. (gerçek için --dry-run kaldır + --transport ver)")
        return 0

    # 3+4) LOCK → PUT envelope (aynı content-type, stateful, If-Match, lockHandle, corrNr) → UNLOCK
    data = new_body.encode("utf-8")
    status, text, eff_transport = _lock_put_unlock(adt, url, full, ctype, data, etag, args.transport)
    if status is None:
        return 1
    if status == 412:
        server_etag = _etag_from_412(text)
        if not server_etag:
            print(f"[FAIL] PUT → HTTP 412 ama gövdeden sunucunun beklediği ETag ÇIKARILAMADI — "
                  f"retry YAPILMADI: {text[:300]}")
            return 1
        if server_etag == etag:
            print("[FAIL] PUT → HTTP 412 ve sunucunun beklediği ETag gönderilenle AYNI — "
                  "retry anlamsız, YAPILMADI.")
            return 1
        # ⚠ Sunucunun ETag'iyle yazmak `If-Match`'in kayıp-güncelleme korumasını ATLAR. Retry
        # YALNIZ envelope ilk okumadan beri BAYT BAYT aynıysa yapılır (eşzamanlı değişiklik yok).
        # Bu GET UNLOCK'tan SONRA, yeni LOCK'tan ÖNCE — lock penceresine girmez (ölçülen başarılı
        # retry de yeni lock'tan önce GET yapmıştı).
        fresh = adt.session.get(full, headers={"Accept": "application/*"}, timeout=adt.timeout_default)
        if fresh.status_code != 200 or (fresh.text or "") != body:
            print(f"[FAIL] PUT → HTTP 412 ve envelope ilk okumadan bu yana DEĞİŞMİŞ ya da yeniden "
                  f"okunamadı (HTTP {fresh.status_code}) — eşzamanlı bir değişikliğin üzerine "
                  f"yazmamak için retry YAPILMADI.")
            return 1
        print(f"[RETRY] PUT → HTTP 412 (gönderilen ETag {etag} ≠ sunucunun beklediği {server_etag}). "
              f"TEK retry, yeni LOCK döngüsüyle.")
        status, text, eff_transport = _lock_put_unlock(adt, url, full, ctype, data, server_etag,
                                                       args.transport)
        if status is None:
            return 1
        if status == 412:
            print(f"[FAIL] retry de HTTP 412 — ikinci retry YOK (döngü koruması). {text[:300]}")
            return 1
    if status not in (200, 204):
        print(f"[FAIL] PUT → HTTP {status}: {text[:300]}")
        # 423 = §12.7'nin semptomu → ORTAK teşhis (metni kopyalama; bkz. helper docstring).
        if status == 423:
            print(adt.put_423_diagnosis(url, eff_transport))
        return 1

    # 5) AKTİVASYON (gerekirse) + READBACK — "updated" mesajına güvenme (ADR 0006 / BE-15, Q175)
    return _activate_and_verify(adt, name, url, full, args.desc)


if __name__ == "__main__":
    raise SystemExit(main())
