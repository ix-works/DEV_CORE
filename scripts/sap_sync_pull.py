#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sap_sync_pull.py — PULL-BEFORE-EDIT yardımcısı (ADR 0016 revize).

Bir SAP objesinin canlı AKTİF source'unu çeker → repo dosyasına yazar (CRLF korur) →
seans-tazelik store'una (.claude/.session_fresh.json) damgalar. `pull_before_edit.py`
PreToolUse hook'u, bayat bir objeyi düzenlemeden önce bunu çalıştırmayı önerir.

Kullanım:
    python scripts/sap_sync_pull.py ZSD001_I_BOOKING --type ddls --session <sid>
    python scripts/sap_sync_pull.py ZSD001_I_BOOKING --type ddls --session <sid> --offline

--offline: SAP erişilemezken ÇEKMEDEN taze damgalar (escape; canlıdan ezme riskini bilerek kabul).
"""
import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows cp1252 konsolu Türkçe karakterde (ı/ş/ç) çöker → UTF-8'e zorla.
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/ importları

from utils.project_config import project_root  # noqa: E402

# ADR 0020: junction'da __file__ DEV_CORE'a çözülür → tazelik damgası PROJE köküne yazılmalı
ROOT = project_root()
FRESH_STORE = ROOT / ".claude" / ".session_fresh.json"
SESSION_MARKER = ROOT / ".claude" / ".current_session"


def _resolve_session(explicit: str) -> str:
    """--session verildiyse onu kullan; yoksa SessionStart'ın yazdığı marker'dan oku
    (proaktif pull'da agent session_id bilmek zorunda kalmasın). Hiçbiri yoksa 'default'
    (PreToolUse hook gerçek session_id ile eşleşmeyince yine bloklar → fail-safe)."""
    if explicit:
        return explicit
    try:
        return json.loads(SESSION_MARKER.read_text(encoding="utf-8")).get("session_id") or "default"
    except Exception:
        return "default"

# ⚠ DDIC okuma-yolu TEK KAYNAKTAN gelir: `object_types.ddic_read_mode()`.
# Burada YEREL BIR TIP KUMESI TUTMA. Eskiden bu dosya `atom.py`'dekinin ELLE
# KOPYALANMIS bir esdegerini tasiyordu ve BES tipin hepsini XML yoluna sokuyordu;
# `atom.py` duzeltilse bile burasi geride kalirdi -> `adt_get` DDL, `sap_sync_pull`
# XML dondururdu (okuma tutarsizligi). Ayrica XML govdesi repo dosyasina HAM yazilir,
# DDL ayiklamasi YAPILMAZ: table/structure pull'u repo'daki DDL'i XML zarfiyla ezerdi.


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp(session_id: str, obj: str) -> None:
    """Seans-tazelik store'una damgala. Store başka seanstansa SIFIRLA (seans-bazlı)."""
    try:
        store = json.loads(FRESH_STORE.read_text(encoding="utf-8"))
    except Exception:
        store = {}
    if store.get("session_id") != session_id:
        store = {"session_id": session_id, "objects": {}}
    store.setdefault("objects", {})[obj.upper()] = _now_iso()
    FRESH_STORE.parent.mkdir(parents=True, exist_ok=True)
    FRESH_STORE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Pull-before-edit: canlıyı çek + repo'ya yaz + taze damgala")
    ap.add_argument("name", help="SAP obje adı (Z*/Y*)")
    ap.add_argument("--type", default="ddls",
                    help="Obje tipi (ddls/bdef/srvd/srvb/class/program/structure/table/...)")
    ap.add_argument("--session", default="",
                    help="Seans kimliği (hook'tan). Boşsa .claude/.current_session marker'ından okunur.")
    ap.add_argument("--offline", action="store_true",
                    help="SAP'den ÇEKMEDEN taze damgala (SAP erişilemezken escape; ezme riskini kabul)")
    ap.add_argument("--force", action="store_true",
                    help="Yereldeki commit'lenmemiş değişikliği EZ — bilerek canlı aktif sürüme dön (FIX-B escape).")
    args = ap.parse_args()
    obj = args.name.upper()
    session = _resolve_session(args.session)

    if args.offline:
        _stamp(session, obj)
        print(f"[OFFLINE] {obj} fetch YAPILMADI, seans-taze damgalandı. "
              f"DİKKAT: canlıdaki belgelenmemiş değişikliği ezme riskini kabul ettin.")
        return 0

    try:
        from sap_client import SAPClient
        import sap_adt_lib as L
        from source_drift import write_repo_from_live
        client = SAPClient()
    except Exception as exc:
        print(f"[FAIL] SAP client init edilemedi: {exc}")
        print("SAP erişilemiyorsa: aynı komutu --offline ile çalıştırıp devam edebilirsin.")
        return 1

    t = args.type.lower().strip()
    try:
        from object_types import ddic_read_mode           # TEK KAYNAK (bkz. yukarıdaki not)
        ddic_mode, ddic_canon = ddic_read_mode(t)
    except Exception as exc:
        print(f"[FAIL] DDIC tip sınıflandırması yapılamadı ({exc}) — pull ATLANDI. "
              f"Sessizce yanlış uçtan okumaktansa DURUYORUZ; object_types.py'yi kontrol et.")
        return 1

    try:
        if ddic_mode == "xml":
            # dataelement/domain/tabletype: `/source/main` YOK → obje XML'i okunur.
            # ⚠ Bu tiplerde repo dosyası da XML'dir; DDL ayıklaması SÖZ KONUSU DEĞİL.
            src = client.get_ddic_object(ddic_canon, obj)
            res = write_repo_from_live(obj, src, object_type=ddic_canon, force=args.force)
        else:
            # source-based (cds/ddls/bdef/srvd/srvb/class/program/interface/dcl/ddlx)
            # **ve DDL-uçlu DDIC** (ddic_mode == "ddl": table/structure — `/source/main`
            # ucu GERÇEKTEN var, ölçüldü 2026-08-09). Bu yol `get_object_source(active)`
            # kullanır ⇒ FIX-B/C/D koruma zinciri (dirty · shrink · geçmiş-commit) tablo
            # ve struct için de DEVREYE GİRER; XML yolunda bunların hiçbiri yoktu.
            # canlı AKTİF source çek + repo dosyasına yaz (CRLF-korur, tip-farkında).
            res = L.sync_repo_from_live(
                object_url=None, object_name=obj, object_type=t,
                client=client.adt_client, force=args.force
            )
    except Exception as exc:
        print(f"[FAIL] {obj} ({t}) canlıdan çekilemedi: {exc}")
        print("SAP erişilemiyorsa: aynı komutu --offline ile çalıştırıp devam edebilirsin (ezme riskini kabul).")
        return 1

    if res.get("blocked_dirty"):
        # FIX-B: yerelde commit'siz değişiklik var → pull EZMEDİ (WIP korundu). Taze
        # DAMGALAMADIK ve exit 1 — manuel çağıran (gateway/ajan) net "korundu" sinyali alır.
        # (Edit yolunu bloklamaz: pull_before_edit hook'u dirty dosyayı zaten MUAF tutar.)
        print(f"[KORUMA] {obj} ({t}) PULL ATLANDI — {res.get('reason')}")
        print(f"  repo_path={res.get('repo_path')}")
        print(f"  → Yerel commit'siz emek EZİLMEDİ. Bilerek canlıya dönmek istiyorsan: "
              f"python scripts/sap_sync_pull.py {obj} --type {t} --force")
        return 1

    if res.get("blocked_behind"):
        # FIX-D: canlı içerik, dosyanın GECMIS bir commit'iyle birebir ayni -> pull
        # "tazeleme" degil, kendi gecmisimize DONUS. Commit'li yerel is ezilirdi.
        print(f"[KORUMA] {obj} ({t}) PULL ATLANDI — {res.get('reason')}")
        print(f"  repo_path={res.get('repo_path')}")
        print(f"  eslesen_gecmis_commit={res.get('behind_commit')}")
        print(f"  → Once KONTROL ET: bu obje push edildi mi, AKTIVE edildi mi? "
              f"(pull AKTIF surumu okur; inaktifte bekleyen yeni surumu gormez.)")
        print(f"  → Bilerek canliya donmek istiyorsan: "
              f"python scripts/sap_sync_pull.py {obj} --type {t} --force")
        return 1

    if res.get("blocked_shrink"):
        # FIX-C: canlı AKTİF sürüm yerelden belirgin KÜÇÜK → pull EZMEDİ. "Yerel temiz =
        # bayat" DEĞİLDİR: obje push edilmemiş ya da push edilip AKTİVE EDİLMEMİŞ olabilir
        # (pull AKTİF okur). exit 1 → çağıran net "korundu" sinyali alır.
        print(f"[KORUMA] {obj} ({t}) PULL ATLANDI — {res.get('reason')}")
        print(f"  repo_path={res.get('repo_path')}")
        print(f"  → Önce KONTROL ET: obje canlıda AKTİF mi? (push edilmiş ama aktive edilmemiş "
              f"olabilir — o hâlde yerel doğru, pull YANLIŞ olurdu.)")
        print(f"  → Yine de canlıya dönmek istiyorsan: "
              f"python scripts/sap_sync_pull.py {obj} --type {t} --force")
        return 1

    if not res.get("written"):
        print(f"[WARN] repo'ya YAZILMADI ({res.get('reason')}) — repo_path={res.get('repo_path')}. "
              f"Taze damgalanMADI (working-copy taze değil). Repo'da bu objenin source dosyası yoksa "
              f"yeni obje olabilir (gate zaten muaf) ya da --file/--type'ı kontrol et.")
        return 1

    _stamp(session, obj)
    print(f"[OK] {obj} ({t}) canlıdan çekildi → {res.get('repo_path')} → seans-taze damgalandı. "
          f"Artık düzenleyebilirsin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
