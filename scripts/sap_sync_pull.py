#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sap_sync_pull.py — PULL-BEFORE-EDIT yardımcısı (ADR 0016 revize).

Bir SAP objesinin canlı AKTİF source'unu çeker → repo dosyasına yazar (CRLF korur) →
seans-tazelik store'una (.claude/.session_fresh.json) damgalar. `pull_before_edit.py`
PreToolUse hook'u, bayat bir objeyi düzenlemeden önce bunu çalıştırmayı önerir.

Kullanım:
    python scripts/sap_sync_pull.py ZSD001_I_BOOKING --type ddls --session <sid>
    python scripts/sap_sync_pull.py ZSD001_I_BOOKING --type ddls --session <sid> --offline
    python scripts/sap_sync_pull.py ZCL_SD001_X --type implementations --file <yol>.ccimp.abap
    python scripts/sap_sync_pull.py ZSD001_I_X_TOP --type auto --file <yol>.prog.abap

--offline: SAP erişilemezken ÇEKMEDEN taze damgalar (escape; canlıdan ezme riskini bilerek kabul).

Q352 (2026-09-26):
  · Damga DOSYAYA yazılır (`source_drift.tazelik_anahtari`; kapı aynı fonksiyonla okur).
  · `--type class` ana kaynağın yanında repo'daki alt-include'ları da KENDİ uçlarından çeker
    ve her birini ayrı damgalar; tek include için `--type implementations|testclasses|...`.
  · `--type auto`: tip canlı ADT aramasından (tam ad + dosya ailesi) çözülür; 0/>1 aday → DUR.
"""
import argparse
import io
import sys
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
# Q352: seans-tazelik store'unun YAZIMI (kilit + atomik) ve seans kimliği
# çözümü `source_drift`e taşındı (public: `tazelik_damgala` / `seans_kimligi`) —
# kapı ve diğer çekiciler aynı yolu kullanır. Burada yerel kopya YOK.


# ⚠ DDIC okuma-yolu TEK KAYNAKTAN gelir: `object_types.ddic_read_mode()`.
# Burada YEREL BIR TIP KUMESI TUTMA. Eskiden bu dosya `atom.py`'dekinin ELLE
# KOPYALANMIS bir esdegerini tasiyordu ve BES tipin hepsini XML yoluna sokuyordu;
# `atom.py` duzeltilse bile burasi geride kalirdi -> `adt_get` DDL, `sap_sync_pull`
# XML dondururdu (okuma tutarsizligi). Ayrica XML govdesi repo dosyasina HAM yazilir,
# DDL ayiklamasi YAPILMAZ: table/structure pull'u repo'daki DDL'i XML zarfiyla ezerdi.


def _dosya_coz(arg_file: str):
    """`--file` → Path (göreliyse PROJE köküne göre). Verilmediyse None."""
    if not arg_file:
        return None
    p = Path(arg_file)
    return p if p.is_absolute() else (ROOT / p)


def _dosya_tutarsizligi(obj: str, t: str, repo_file) -> str:
    """`--file` obje adı ve `--type` ile tutarlı mı? Tutarlıysa "", değilse hata metni.

    Bug gate M1 (2026-09-26): `--file` doğrulanmıyordu → `ZCL_BASKA --type class --file
    ZCL_SD001_X.clas.abap` BAŞKA objenin kaynağını yazıp damgalıyor, `[OK]` diyordu.
    ① Ad: dosya adının ilk noktaya kadarki gövdesi (BÜYÜK) == obje adı. Farklı ad taşıyan
       meşru bir aile ÖLÇÜLMEDİ (tüketici korpusta `#` namespace dosyası 0; FM/include/
       alt-include dosyaları da obje adını taşır) → gevşetme YOK.
    ② Tip: dosya kapının sınıflandırmasıyla (`pbe_siniflandir`, TEK KAYNAK) uyuşmalı —
       alt-include dosyası yalnız alt-include tipiyle ve AYNI türle; tipi dosyadan kesin
       olan dosya yalnız o tiple; `auto` ailesindeki dosya `auto` ya da uzantısını kabul
       eden açık bir tiple (`source_drift._TYPE_TO_EXTENSIONS`).
    """
    try:
        from source_drift import pbe_siniflandir, _TYPE_TO_EXTENSIONS
        from object_types import (is_class_include, normalize_class_include,
                                  normalize_object_type)
    except Exception as exc:  # noqa: BLE001
        return f"--file doğrulanamadı ({exc}) — yazma/damga YOK"
    def _n(x: str) -> str:
        # `normalize_object_type` bdef/srvb gibi tiplerde ValueError atar → ham ad (küçük harf)
        try:
            return normalize_object_type(x)
        except Exception:  # noqa: BLE001
            return str(x).lower().strip()

    govde = repo_file.name.split(".", 1)[0].upper()
    if govde != obj.upper():
        return (f"--file '{repo_file.name}' obje adı '{govde}' taşıyor, istenen '{obj}' — "
                f"başka objenin dosyası YAZILMAZ/DAMGALANMAZ")
    s = pbe_siniflandir(repo_file)
    if not s:
        return (f"--file '{repo_file.name}' PULL-BEFORE-EDIT kapsamında bir kaynak dosyası "
                f"değil (kaynak kökü/uzantı) — yazma/damga YOK")
    include_istek = is_class_include(t)
    if s["tur"] == "sinif_include" or include_istek:
        if not (s["tur"] == "sinif_include" and include_istek
                and normalize_class_include(t) == s["tip"]):
            return (f"--file '{repo_file.name}' türü '{s['tip']}', istenen --type '{t}' — "
                    f"sınıf alt-include'u yalnız KENDİ türüyle çekilir (ör. --type {s['tip']})")
        return ""
    if t == "auto":
        return ""  # aile uyumu auto dalında ayrıca denetlenir (tipi kesin dosya → red)
    if s["tip"] != "auto":
        if _n(t) != _n(s["tip"]):
            return (f"--file '{repo_file.name}' tipi '{s['tip']}', istenen --type '{t}' — "
                    f"tutarsız (ör. --type {s['tip']})")
        return ""
    izinli = _TYPE_TO_EXTENSIONS.get(t) or _TYPE_TO_EXTENSIONS.get(_n(t)) or ()
    if not repo_file.name.lower().endswith(tuple(izinli)):
        return (f"--file '{repo_file.name}' uzantısı --type '{t}' ile uyuşmuyor "
                f"(izinli: {', '.join(izinli) or '-'}) — `--type auto` kullan")
    return ""


def _damgala(session: str, repo_path) -> str:
    """YAZILAN/DOĞRULANAN dosyayı seans-taze damgala → anahtar (boşsa damgalanmadı).

    TEK KAYNAK: `source_drift.tazelik_damgala` (anahtar = `tazelik_anahtari`; kapı aynı
    fonksiyonla okur). Yüklenemezse damga YAZILMAZ: yön güvenli (kapı 'taze değil' der).
    """
    try:
        from source_drift import tazelik_damgala
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] tazelik damgası yüklenemedi ({exc}) — {repo_path} damgalanMADI "
              f"(kapı bu dosyayı 'taze değil' sayar).")
        return ""
    return tazelik_damgala(session, repo_path, ROOT)


def _sonuc(etiket: str, t: str, res: dict, session: str, komut_eki: str = "",
           komut_tipi: str = "") -> int:
    """Tek dosyanın çekme sonucunu bildir; yalnız GERÇEKTEN yazılan/eşit bulunan dosya damgalanır.

    Döner: 0 = taze damgalandı · 1 = çekilmedi/korundu (damga YOK).
    `komut_tipi`: önerilen tekrar komutunun `--type`i (verilmezse `t`). `--type auto` ile
    çözülen tip (ör. `function`) doğrudan çekilebilir bir tip OLMAYABİLİR → auto dalı
    tekrar komutunu yine `auto` ile basar (bug gate L1: "source URL türetilemedi" döngüsü).
    """
    yol = res.get("repo_path")
    tekrar = (f"python core/scripts/sap_sync_pull.py {etiket} --type {komut_tipi or t}"
              f"{komut_eki} --force")
    if res.get("blocked_dirty"):
        # FIX-B: yerelde commit'siz değişiklik var → pull EZMEDİ (WIP korundu). Taze
        # DAMGALAMADIK ve exit 1 — manuel çağıran (gateway/ajan) net "korundu" sinyali alır.
        # (Edit yolunu bloklamaz: pull_before_edit hook'u dirty dosyayı zaten MUAF tutar.)
        print(f"[KORUMA] {etiket} ({t}) PULL ATLANDI — {res.get('reason')}")
        print(f"  repo_path={yol}")
        print(f"  → Yerel commit'siz emek EZİLMEDİ. Bilerek canlıya dönmek istiyorsan: {tekrar}")
        return 1
    if res.get("blocked_behind"):
        # FIX-D: canlı içerik, dosyanın GECMIS bir commit'iyle birebir ayni -> pull
        # "tazeleme" degil, kendi gecmisimize DONUS. Commit'li yerel is ezilirdi.
        print(f"[KORUMA] {etiket} ({t}) PULL ATLANDI — {res.get('reason')}")
        print(f"  repo_path={yol}")
        print(f"  eslesen_gecmis_commit={res.get('behind_commit')}")
        print(f"  → Once KONTROL ET: bu obje push edildi mi, AKTIVE edildi mi? "
              f"(pull AKTIF surumu okur; inaktifte bekleyen yeni surumu gormez.)")
        print(f"  → Bilerek canliya donmek istiyorsan: {tekrar}")
        return 1
    if res.get("blocked_shrink"):
        # FIX-C: canlı AKTİF sürüm yerelden belirgin KÜÇÜK → pull EZMEDİ. "Yerel temiz =
        # bayat" DEĞİLDİR: obje push edilmemiş ya da push edilip AKTİVE EDİLMEMİŞ olabilir
        # (pull AKTİF okur). exit 1 → çağıran net "korundu" sinyali alır.
        print(f"[KORUMA] {etiket} ({t}) PULL ATLANDI — {res.get('reason')}")
        print(f"  repo_path={yol}")
        print(f"  → Önce KONTROL ET: obje canlıda AKTİF mi? (push edilmiş ama aktive edilmemiş "
              f"olabilir — o hâlde yerel doğru, pull YANLIŞ olurdu.)")
        print(f"  → Yine de canlıya dönmek istiyorsan: {tekrar}")
        return 1
    if not res.get("written"):
        print(f"[WARN] {etiket} ({t}) repo'ya YAZILMADI ({res.get('reason')}) — repo_path={yol}. "
              f"Taze damgalanMADI (working-copy taze değil). Repo'da bu objenin source dosyası "
              f"yoksa yeni obje olabilir (kapı zaten muaf) ya da --file/--type'ı kontrol et.")
        return 1
    if not _damgala(session, yol):
        return 1
    print(f"[OK] {etiket} ({t}) canlıdan çekildi → {yol} → DOSYA seans-taze damgalandı.")
    return 0


def _aday_sec(obj: str, aile: str, adt_client):
    """`--type auto`: ADT quickSearch TAM-AD sonucu + dosya-ailesi süzgeci → (uri, adt_tipi, tip).

    TAHMİN YOK: 0 aday ya da >1 aday → ValueError (mesaj adayları sayar). Aile tablosu
    `object_types.AUTO_AILE_ADT_TIPLERI` (TEK KAYNAK, canlı ölçüm notu orada).
    """
    import xml.etree.ElementTree as ET
    from object_types import AUTO_AILE_ADT_TIPLERI
    izinli = AUTO_AILE_ADT_TIPLERI.get(aile or "")
    if not izinli:
        raise ValueError(f"bilinmeyen dosya ailesi: {aile!r}")
    xml = adt_client.search_objects(obj, max_results=50)
    ns = "{http://www.sap.com/adt/core}"
    tum, aday = [], []
    for el in ET.fromstring(xml).iter(ns + "objectReference"):
        ad = (el.get(ns + "name") or "").upper()
        if ad != obj:
            continue
        typ, uri = el.get(ns + "type") or "", (el.get(ns + "uri") or "").split("#")[0]
        tum.append(typ)
        if typ in izinli and (uri, typ) not in [(u, t) for u, t, _ in aday]:
            aday.append((uri, typ, izinli[typ]))
    if len(aday) == 1:
        return aday[0]
    if not aday:
        raise ValueError(
            f"canlıda '{obj}' adıyla '{aile}' ailesinden obje YOK (tam-ad sonuçları: "
            f"{tum or 'hiç'}). Yeni obje olabilir (kapı dosya yoksa zaten muaf); "
            f"varsa tipi açıkça ver (--type program|include|class|table|...).")
    raise ValueError(
        f"'{obj}' için {len(aday)} aday var ({[t for _, t, _ in aday]}) — tahmin YOK. "
        f"Tipi açıkça ver (--type ...).")


def _auto_dosya(obj: str):
    """--file verilmemiş `auto` çağrısı: repo'da bu adla TEK auto-aileli dosya varsa o."""
    from source_drift import _pbe_adaylari
    adaylar = [(f, s) for f, s in _pbe_adaylari(obj) if s["tip"] == "auto"]
    if len(adaylar) == 1:
        return adaylar[0]
    raise ValueError(
        f"'{obj}' için repo'da {len(adaylar)} aday dosya var "
        f"({[f.name for f, _ in adaylar] or 'hiç'}) — hangisi? `--file <yol>` ver.")


def _hedef_dosyalar(obj: str, t: str, repo_file):
    """--offline için damgalanacak dosya(lar). Tahmin YOK: çözülemezse boş liste."""
    if repo_file is not None:
        return [repo_file] if repo_file.is_file() else []
    try:
        from object_types import is_class_include, normalize_class_include
        from source_drift import find_repo_class_include_file, find_repo_source_file
        if is_class_include(t):
            f = find_repo_class_include_file(obj, normalize_class_include(t))
        elif t == "auto":
            f = _auto_dosya(obj)[0]
        else:
            f = find_repo_source_file(obj, object_type=t)
    except Exception:
        return []
    return [f] if f else []


def _sinif_includelari(obj: str, session: str, client, force: bool) -> int:
    """Sınıfın repo'da bulunan alt-include'larını KENDİ uçlarından çek + AYRI damgala.

    Eskiden burada yalnız "ÇEKİLMEDİ" uyarısı vardı (çekme yolu kurulmamıştı; segment
    adları o gün ölçülmemişti). Q283 (2026-09-13) dört segmenti ölçtü, Q352 (2026-09-26)
    yeniden ölçtü → yol kuruldu. Her include bağımsızdır: biri korunur/404 verirse diğerleri
    çekilir, korunan DAMGALANMAZ ve çıktı onu "ÇEKİLMEDİ" diye adlandırır.
    """
    try:
        import sap_adt_lib as L
        from object_types import get_class_include_url
        from source_drift import find_repo_class_includes
        includes = find_repo_class_includes(obj)
    except Exception as exc:
        print(f"[WARN] {obj}: alt-include listesi çıkarılamadı ({exc}) — alt-include'lar "
              f"ÇEKİLMEDİ, damgalanMADI (kapı onları 'taze değil' sayar).")
        return 1
    rc = 0
    for kind, f in includes:
        try:
            res = L.sync_repo_from_live(
                object_url=get_class_include_url(obj, kind), object_name=obj,
                object_type="class", client=client, force=force, repo_file=f)
        except Exception as exc:
            res = {"written": False, "repo_path": str(f), "reason": f"çekilemedi ({exc})"}
        if not res.get("repo_path"):
            res["repo_path"] = str(f)
        if _sonuc(f"{obj}", kind, res, session, f' --file "{f}"'):
            print(f"  [!] ALT-INCLUDE ÇEKİLMEDİ: {f.name} — damgalanMADI.")
            rc = 1
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="Pull-before-edit: canlıyı çek + repo'ya yaz + taze damgala")
    ap.add_argument("name", help="SAP obje adı (Z*/Y*)")
    ap.add_argument("--type", default="ddls",
                    help="Obje tipi (ddls/bdef/srvd/srvb/class/program/include/structure/table/... ; "
                         "sınıf alt-include'u: implementations|testclasses|definitions|macros "
                         "(eşanlamlı ccimp|ccau|ccdef|ccmac); `auto` = tipi canlı ADT aramasıyla çöz)")
    ap.add_argument("--file", default="",
                    help="Repo dosyası (kapının verdiği yol). Damga BU dosyaya yazılır; "
                         "verilmezse ad + tipten bulunur.")
    ap.add_argument("--session", default="",
                    help="Seans kimliği (hook'tan). Boşsa .claude/.current_session marker'ından okunur.")
    ap.add_argument("--offline", action="store_true",
                    help="SAP'den ÇEKMEDEN taze damgala (SAP erişilemezken escape; ezme riskini kabul)")
    ap.add_argument("--force", action="store_true",
                    help="Yereldeki commit'lenmemiş değişikliği EZ — bilerek canlı aktif sürüme dön (FIX-B escape).")
    args = ap.parse_args()
    obj = args.name.upper()
    from source_drift import seans_kimligi
    session = seans_kimligi(args.session)
    t = args.type.lower().strip()
    repo_file = _dosya_coz(args.file)
    if repo_file is not None:
        hata = _dosya_tutarsizligi(obj, t, repo_file)
        if hata:
            print(f"[FAIL] {obj} ({t}) {hata}")
            return 1

    if args.offline:
        hedefler = _hedef_dosyalar(obj, t, repo_file)
        if not hedefler:
            print(f"[FAIL] {obj} ({t}) --offline: damgalanacak repo dosyası çözülemedi "
                  f"(damga DOSYAYA yazılır). `--file <yol>` ver.")
            return 1
        rc = 0
        for f in hedefler:
            if _damgala(session, f):
                print(f"[OFFLINE] {f} fetch YAPILMADI, seans-taze damgalandı. "
                      f"DİKKAT: canlıdaki belgelenmemiş değişikliği ezme riskini kabul ettin.")
            else:
                # bug gate L2: damga yazılamadıysa başarı iddia EDİLMEZ (kapı hâlâ bloklar)
                print(f"[FAIL] {f} --offline: damga YAZILAMADI — kapı bu dosyayı 'taze değil' sayar.")
                rc = 1
        return rc

    try:
        from sap_client import SAPClient
        import sap_adt_lib as L
        from source_drift import write_repo_from_live
        client = SAPClient()
    except Exception as exc:
        print(f"[FAIL] SAP client init edilemedi: {exc}")
        print("SAP erişilemiyorsa: aynı komutu --offline ile çalıştırıp devam edebilirsin.")
        return 1

    dosya_eki = f' --file "{repo_file}"' if repo_file is not None else ""

    # ── SINIF ALT-INCLUDE'u: kendi ucundan (`/oo/classes/<C>/includes/<segment>`) ──────
    try:
        from object_types import is_class_include, normalize_class_include, get_class_include_url
        include_mi = is_class_include(t)
    except Exception:
        include_mi = False
    if include_mi:
        kind = normalize_class_include(t)
        try:
            from source_drift import find_repo_class_include_file
            hedef = repo_file or find_repo_class_include_file(obj, kind)
        except Exception as exc:
            print(f"[FAIL] {obj} ({kind}) include dosyası aranamadı: {exc}")
            return 1
        if hedef is None:
            print(f"[WARN] {obj} ({kind}) repo'da include dosyası yok — çekilmedi, damgalanMADI.")
            return 1
        try:
            res = L.sync_repo_from_live(
                object_url=get_class_include_url(obj, kind), object_name=obj,
                object_type="class", client=client.adt_client, force=args.force, repo_file=hedef)
        except Exception as exc:
            print(f"[FAIL] {obj} ({kind}) canlıdan çekilemedi: {exc}")
            return 1
        return _sonuc(obj, kind, res, session, dosya_eki)

    # ── TİPİ CANLIDAN ÇÖZ (`--type auto`) ──────────────────────────────────────────────
    if t == "auto":
        try:
            if repo_file is not None:
                from source_drift import pbe_siniflandir
                s = pbe_siniflandir(repo_file) or {}
                aile = s.get("aile")
                if not aile:
                    raise ValueError(f"{repo_file.name} `auto` ailesinden değil "
                                     f"(tipi dosya adından kesin; açık --type ver)")
            else:
                repo_file, s = _auto_dosya(obj)
                aile = s["aile"]
                dosya_eki = f' --file "{repo_file}"'
            uri, adt_tipi, cozulen = _aday_sec(obj, aile, client.adt_client)
        except Exception as exc:
            print(f"[FAIL] {obj} (auto) tip çözülemedi — pull ATLANDI, damgalanMADI: {exc}")
            return 1
        print(f"[TİP] {obj}: canlı ADT araması → {adt_tipi} ({cozulen}) · {uri}")
        try:
            res = L.sync_repo_from_live(object_url=uri, object_name=obj, object_type=cozulen,
                                        client=client.adt_client, force=args.force,
                                        repo_file=repo_file)
        except Exception as exc:
            print(f"[FAIL] {obj} ({cozulen}) canlıdan çekilemedi: {exc}")
            return 1
        rc = _sonuc(obj, cozulen, res, session, dosya_eki, komut_tipi="auto")
        if cozulen == "class":
            rc = max(rc, _sinif_includelari(obj, session, client.adt_client, args.force))
        return rc

    try:
        from object_types import ddic_read_mode           # TEK KAYNAK (bkz. yukarıdaki not)
        ddic_mode, ddic_canon = ddic_read_mode(t)
    except Exception as exc:
        print(f"[FAIL] DDIC tip sınıflandırması yapılamadı ({exc}) — pull ATLANDI. "
              f"Sessizce yanlış uçtan okumaktansa DURUYORUZ; object_types.py'yi kontrol et.")
        return 1

    ek = {"repo_file": repo_file} if repo_file is not None else {}
    try:
        if ddic_mode == "xml":
            # dataelement/domain/tabletype: `/source/main` YOK → obje XML'i okunur.
            # ⚠ Bu tiplerde repo dosyası da XML'dir; DDL ayıklaması SÖZ KONUSU DEĞİL.
            src = client.get_ddic_object(ddic_canon, obj)
            res = write_repo_from_live(obj, src, object_type=ddic_canon, force=args.force, **ek)
        else:
            # source-based (cds/ddls/bdef/srvd/srvb/class/program/interface/dcl/ddlx)
            # **ve DDL-uçlu DDIC** (ddic_mode == "ddl": table/structure — `/source/main`
            # ucu GERÇEKTEN var, ölçüldü 2026-08-09). Bu yol `get_object_source(active)`
            # kullanır ⇒ FIX-B/C/D koruma zinciri (dirty · shrink · geçmiş-commit) tablo
            # ve struct için de DEVREYE GİRER; XML yolunda bunların hiçbiri yoktu.
            # canlı AKTİF source çek + repo dosyasına yaz (CRLF-korur, tip-farkında).
            res = L.sync_repo_from_live(
                object_url=None, object_name=obj, object_type=t,
                client=client.adt_client, force=args.force, **ek
            )
    except Exception as exc:
        print(f"[FAIL] {obj} ({t}) canlıdan çekilemedi: {exc}")
        print("SAP erişilemiyorsa: aynı komutu --offline ile çalıştırıp devam edebilirsin (ezme riskini kabul).")
        return 1

    rc = _sonuc(obj, t, res, session, dosya_eki)

    # ⛔ SINIF ALT-INCLUDE'LARI (Q352): eskiden burada yalnız "ÇEKİLMEDİ" uyarısı basılıyordu —
    # pull `/source/main`i okur, `.ccimp/.ccau/.ccdef/.ccmac` AYRI ADT uçlarındadır ve damga
    # obje ADINA yazıldığı için kapı onları da TAZE sayıyordu (bayat `.ccimp` sessizce
    # düzenlenebiliyordu). Artık: (1) damga DOSYAYA yazılır → ana kaynağın damgası include'u
    # KAPSAMAZ; (2) repo'daki her include kendi ucundan çekilip AYRI damgalanır. Çekilemeyen
    # include "ÇEKİLMEDİ" diye adlandırılır ve damgalanmaz — çıktı yapılmayanı iddia etmez.
    try:
        from object_types import normalize_object_type
        sinif_mi = normalize_object_type(t) == "class"
    except Exception:
        sinif_mi = False
    if sinif_mi:
        rc = max(rc, _sinif_includelari(obj, session, client.adt_client, args.force))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
