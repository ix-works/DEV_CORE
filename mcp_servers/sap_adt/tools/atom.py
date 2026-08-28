"""Atom tools — single ADT REST operation each.

- adt_get          : Read object source/metadata
- adt_post_shell   : Create empty Z shell (no source)
- adt_push_source  : Push source body to existing object
- adt_activate     : Activate object

All tools:
- Return structured JSON: {ok: bool, ...}
- Capture SAPClient stdout chatter into 'client_log' field (does not pollute MCP stdio)
- Apply ADR 0005 guardrails before any SAP HTTP call
- Map SAPADTError subclasses to error codes (auth/not_found/locked/exists/...)
"""
from __future__ import annotations

import contextlib
import io
import re
import tempfile
from pathlib import Path
from typing import Any, Optional

from mcp_servers.sap_adt._app import mcp, log, profil_tool
from mcp_servers.sap_adt._reviewer import (
    reject_payload,
    run_reviewer,
    task_for_push,
)
from mcp_servers.sap_adt.guardrails import (
    GuardrailViolation,
    reject_standard_delete,
    require_customer_namespace,
    require_transport,
    require_writable_tier,
)
from mcp_servers.sap_adt._conn import get_active_tier

# Lazy import — SAPClient pulls auth + .conn_adt; defer until first call.
_client = None
_sap_client_sig0 = None        # yüklü sap_client modülünün (size, sha1) imzası — bayat-süreç backstop'u
_sap_client_mtime_seen = None  # son stat'lanan mtime; fast-path (mtime değişmedikçe hash atlanır)


# ADR 0016 REVİZE (2026-06-16): pre-push DRIFT GUARD (M1) + post-write REPO SYNC (M2)
# KALDIRILDI. Sebep: repo≠canlı symmetric kıyası KASITLI edit'leri de blokluyordu
# (working-tree ≠ live her edit'te doğal). Yeni model = PULL-BEFORE-EDIT: edit'ten ÖNCE
# güncel çekilir (PreToolUse Edit|Write hook, scripts/hooks/pull_before_edit.py + seans
# tazelik), böylece push'ta ayrıca kontrol gerekmez. Bkz. ADR 0016 + scripts/sap_sync_pull.py.

# ── READBACK-GATE (2026-06-21, onaylı) ──────────────────────────────────────
# Sorun (kanıt: ZSD001_I_SHIP_POOL `where` kaybı): yazım SAP'de TAM oturmayabilir
# (activate eksik/kısmi, ya da aktif sürüm push edilenden geride kalır) ama tool "ok"
# döner → sessizce drift. Çözüm: activate SONRASI aktif source'u çek + push edilenle
# normalize-compare; fark varsa BLOCKER (ok=False). Delete sonrası: obje hâlâ varsa BLOCKER.
# Maliyet ölçüldü ~50ms/obje (sıcak session). XML-DDIC source taşımaz → content-compare ATLA
# (composite create + _activate_and_verify alan-verify'i kapsar).
# NAME-COLLISION FIX (2026-06-21, gw-deliv kanıtı): ZSD001_I_SHIP_POOL hem DDLS (CDS) hem
# BDEF olabilir. Yalnız İSİMLE key'lersek BDEF push'u CDS kaydını EZER → BDEF aktive edilince
# readback CDS-source ile kıyaslayıp SAHTE-mismatch verir. Çözüm: (name.upper(), type_key) ile key.
_LAST_PUSHED: dict[tuple[str, str], tuple[str, str]] = {}   # (name.upper(), type_key) -> (object_type, source)
_TYPE_KEY_CANON = {
    "cds": "ddls", "cdsview": "ddls", "ddl": "ddls", "ddls": "ddls",
    "behaviordefinition": "bdef", "bdef": "bdef",
    "servicedefinition": "srvd", "srvd": "srvd",
    "clas": "class", "class": "class", "intf": "interface", "interface": "interface",
    "prog": "program", "program": "program",
}


def _type_key(t: str) -> str:
    """Tip eşanlamlılarını kanonikleştir (cds/ddl→ddls, behaviordefinition→bdef, ...)."""
    t = (t or "").lower().strip()
    return _TYPE_KEY_CANON.get(t, t)


_SOURCE_BASED_TYPES = {
    "ddls", "cds", "cdsview", "ddl", "bdef", "behaviordefinition",
    "srvd", "servicedefinition", "class", "clas", "program", "prog",
    "interface", "intf", "dcl", "accesscontrol", "ddlx", "metadataextension",
}


def _content_readback(client, name: str, object_type: str) -> dict:
    """Activate sonrası: AKTİF source'u çek + bu seansta push edilenle normalize-compare.

    Yalnız source-based tip + bu seansta push kaydı varsa çalışır (salt re-activate'te
    push kaydı yok → atla). Fark = yazım tam oturmadı → blocker sinyali.

    Returns: {} (uygulanmaz) | {content_verified: True}
           | {content_verified: False, content_mismatch: True, content_reason, content_diff}
           | {content_verified: None, content_reason} (readback yapılamadı — soft)
    """
    t = (object_type or "").lower().strip()
    if t not in _SOURCE_BASED_TYPES:
        return {}
    rec = _LAST_PUSHED.get((name.upper(), _type_key(object_type)))
    if not rec:
        return {}
    _, pushed = rec
    try:
        import sap_adt_lib as L  # type: ignore
        from source_drift import normalize_source  # type: ignore
        adt = getattr(client, "adt_client", None) or client
        url = L._resolve_source_url(name, t)
        if not url:
            return {"content_verified": None,
                    "content_reason": f"source URL çözülemedi (type={t}) — content readback atlandı"}
        with _capture_stdout():   # SAPClient stdout chatter MCP stdio'yu kirletmesin
            live = adt.get_object_source(url, version="active")
    except Exception as exc:  # noqa: BLE001
        return {"content_verified": None, "content_reason": f"content readback exception: {exc}"}

    if normalize_source(live) == normalize_source(pushed):
        return {"content_verified": True}
    import difflib
    diff = "\n".join(difflib.unified_diff(
        normalize_source(pushed).splitlines(), normalize_source(live).splitlines(),
        fromfile="pushed", tofile="active", lineterm="", n=1))[:1500]
    return {
        "content_verified": False,
        "content_mismatch": True,
        "content_reason": ("AKTİF source push edilenle EŞLEŞMİYOR — yazım SAP'de tam oturmadı "
                           "(activate eksik/kısmi ya da aktif sürüm geride; 'where'-kaybı sınıfı). "
                           "Re-push + re-activate gerekli; pull etmeden ÖNCE düzelt."),
        "content_diff": diff,
    }


def _exists_after_delete(client, name: str, object_type: str):
    """Delete sonrası varlık readback → (durum, sebep).

    durum: True = hâlâ var (silme oturmadı) · False = YOKLUĞU KANITLI (silme oturdu)
           · None = doğrulama KOŞAMADI (iddia yok).

    ⛔ 2026-08-01 bug-avı, "doğrulama koşamadı = doğrulandı" sınıfı: burada eskiden
    `return md is not None` yazıyordu. `get_object_metadata` HER istisnayı yutup `None`
    döndürdüğü için (sap_client.py: `except Exception: print("[ERROR]..."); return None`)
    aşağıdaki `except` dalı bu yolda HİÇ ateşlenmiyordu → HTTP 500 / 403-logon / timeout /
    bağlantı kopması hepsi `md=None` → `False` → **`delete_verified: True`**. Yani silmenin
    OTURDUĞUNA dair kanıt üretilemediği durum, "oturdu" diye raporlanıyordu (silme geri
    alınamaz ve bir sonraki adım bu iddiaya dayanır: yeniden yaratma / TR kapatma).
    Artık yokluk yalnız KANITLI ise (404 imzası ya da temiz-boş yanıt) beyan edilir.
    """
    log_buf = io.StringIO()
    try:
        with _capture_stdout() as out:   # SAPClient stdout chatter MCP stdio'yu kirletmesin
            md = client.get_object_metadata(name, object_type=object_type)
        log_buf.write(out.getvalue())
        if md is not None:
            return True, ""
        sinif = _bos_sonuc_sinifi(log_buf.getvalue())
        if sinif == "yok":
            return False, ""
        return None, (
            f"Silme sonrası varlık readback KOŞAMADI ({sinif}) — obje okunamadı ve sebep "
            f"BULUNAMADI-DEĞİL bir hata. Bu 'silindi' KANITI DEĞİLDİR; SE80/adt_get ile "
            f"elle teyit et. Log: {log_buf.getvalue().strip()[:200]}"
        )
    except Exception as exc:  # noqa: BLE001
        # NotFound/erişilemez → 'yok' iddiası etme; soft
        return None, f"Silme sonrası varlık readback yapılamadı ({type(exc).__name__}: {exc})."


def _get_client():
    global _client, _sap_client_sig0, _sap_client_mtime_seen
    if _client is None:
        from sap_client import SAPClient  # type: ignore
        _client = SAPClient()
        _sap_client_sig0 = _module_file_sig("sap_client")     # yüklü sürümün imzası (bayat-süreç baz)
        _sap_client_mtime_seen = _module_file_mtime("sap_client")  # fast-path başlangıç mtime'ı
        _record_active_binding(_client)
        log.info("SAPClient initialised")
    else:
        _guard_binding_current(_client)  # cache'li client bağlantı-stale ise REDDET (backstop)
        _guard_module_current()          # sap_client.py disk'te değişti ise (bayat-süreç) REDDET
    return _client


def _module_file_mtime(modname: str):
    """Yüklü modülün disk dosyasının mtime'ı; bilinemezse None. (fast-path stat'ı.)"""
    try:
        import sys, os
        f = getattr(sys.modules.get(modname), "__file__", None)
        return os.path.getmtime(f) if f and os.path.isfile(f) else None
    except Exception:  # noqa: BLE001
        return None


def _module_file_sig(modname: str):
    """Yüklü modülün disk dosyasının (size, sha1) imzası; bilinemezse None.

    Yükleme anında çağrılır → o anki disk içeriği = belleğe yüklenen kod. Sonradan
    dosya değişirse imza ayrışır. (mtime DEĞİL hash: git checkout/CRLF mtime'ı değiştirip
    yanlış-pozitif yapabilir; içerik-hash yalnız gerçek kod değişiminde tetikler.)"""
    try:
        import sys, os, hashlib
        m = sys.modules.get(modname)
        f = getattr(m, "__file__", None)
        if not f or not os.path.isfile(f):
            return None
        data = open(f, "rb").read()
        return (len(data), hashlib.sha1(data).hexdigest())
    except Exception:  # noqa: BLE001
        return None


def _guard_module_current() -> None:
    """Backstop: MCP server uzun-ömürlü süreç → `sap_client.py` fix'ten ÖNCE yüklendiyse
    bellekte BAYAT kod çalıştırır (örn. classrun sahte 'does not implement if_oo_adt_classrun~main').

    On-disk `sap_client.py` yüklü sürümden FARKLI ise süreç bayat → ADT işlemini RED + actionable
    mesaj. `_guard_binding_current` (bağlantı-bayatlığı) ile paralel ikinci katman.

    PERF: normalde yalnız bir `stat()` (mtime). mtime değişmedikçe içerik HASH'lenmez (fast-path)
    → ADT çağrısı başına ek maliyet ≈ birkaç µs. Hash yalnız dosya gerçekten değişince (nadir) koşar.
    Check kendisi kırılırsa fail-open (yanlış-pozitif ADT'yi brick etmesin)."""
    global _sap_client_mtime_seen
    try:
        if _sap_client_sig0 is None:
            return
        mt = _module_file_mtime("sap_client")
        if mt is not None and mt == _sap_client_mtime_seen:
            return  # fast-path: dosya mtime'ı değişmemiş → hash gereksiz
        cur = _module_file_sig("sap_client")  # mtime değişti → içeriği hash'le (git-checkout no-op olabilir)
        _sap_client_mtime_seen = mt
        if cur is None:
            return
        stale = cur != _sap_client_sig0
    except Exception:  # noqa: BLE001
        return
    if stale:
        raise RuntimeError(
            "MCP SERVER BAYAT KOD: 'sap_client.py' disk'te güncellendi ama bu süreç eski sürümü "
            "bellekte çalıştırıyor (örn. adt_classrun sahte 'does not implement' hatası verebilir). "
            "ADT işlemi REDDEDİLDİ — '/mcp' ile yeniden bağlan ya da MCP server'ı restart et."
        )


def _guard_binding_current(client) -> None:
    """Backstop (ADR 0010): cache'li client'in BAGLI oldugu sistem .conn_adt ile ayni mi?

    switch_tier .conn_adt'yi degistirir ama bu surecin client'i eski sisteme bagli kalir
    (/mcp restart edilene dek). Ayrisirsa ADT islemini RED — yoksa istek eski sisteme
    gider ama tier guard yeni sistemi okur (write DEV der, ECC QA'ya gider → felaket).
    Hook (pre_tool_guard) asil katman; bu ikinci katman (bypass yok). Check kendisi
    kirilirsa fail-open (hook yakalar)."""
    try:
        from urllib.parse import urlparse
        from mcp_servers.sap_adt._conn import _conn_value
        adt = getattr(client, "adt_client", None)
        bound_url = getattr(adt, "url", "") or ""
        bound_cl = str(getattr(adt, "client", "") or "")
        cur_url = _conn_value("ADT_SAP_URL", "") or ""
        cur_cl = str(_conn_value("ADT_SAP_CLIENT", "") or "")
        bh = (urlparse(bound_url if "://" in bound_url else "https://" + bound_url).hostname or "").lower()
        ch = (urlparse(cur_url if "://" in cur_url else "https://" + cur_url).hostname or "").lower()
        differ = (bh and ch and bh != ch) or (bound_cl and cur_cl and bound_cl != cur_cl)
    except Exception:
        return  # guard'in kendi hatasi ADT'yi tamamen bricklemesin (hook authoritative)
    if differ:
        raise RuntimeError(
            f"BAĞLANTI TUTARSIZLIĞI (ADR 0010): MCP '{bh}' (client {bound_cl}) sistemine bağlı "
            f"ama .conn_adt artık '{ch}' (client {cur_cl}). switch_tier yapıldı, /mcp restart "
            f"EDİLMEDİ. ADT işlemi REDDEDİLDİ — önce '/mcp' ile yeniden bağlan."
        )


def _record_active_binding(client) -> None:
    """MCP'nin CANLI bagli oldugu sistemi .claude/.mcp_active_system'e yaz (fiili url/client ile).

    Asil yazici _conn.write_mcp_binding_state (acilista da kullanilir). Burada gercek
    bagli host/client gecilir → fiili hedef dogrulanir. Asla client yaratimini kirmaz."""
    try:
        from mcp_servers.sap_adt._conn import write_mcp_binding_state
        adt = getattr(client, "adt_client", None)
        write_mcp_binding_state(
            url=getattr(adt, "url", None),
            client=getattr(adt, "client", None),
        )
    except Exception:  # pragma: no cover - state yazimi asla baglanmayi kirmaz
        pass


def _err_from_exc(exc: Exception) -> dict:
    """Map SAPADTError subclasses (and generic Exception) to structured response."""
    from sap_adt_lib import (  # type: ignore
        SAPAuthenticationError,
        SAPConnectionError,
        SAPObjectNotFoundError,
        SAPObjectExistsError,
        SAPLockError,
        SAPActivationError,
        SAPValidationError,
        SAPADTError,
    )
    if isinstance(exc, SAPAuthenticationError):
        code = "auth_failed"
    elif isinstance(exc, SAPConnectionError):
        code = "connection_failed"
    elif isinstance(exc, SAPObjectNotFoundError):
        code = "not_found"
    elif isinstance(exc, SAPObjectExistsError):
        code = "already_exists"
    elif isinstance(exc, SAPLockError):
        code = "locked"
    elif isinstance(exc, SAPActivationError):
        code = "activation_failed"
    elif isinstance(exc, SAPValidationError):
        code = "validation_error"
    elif isinstance(exc, SAPADTError):
        code = "sap_error"
    else:
        code = "unexpected"
    out = {
        "ok": False,
        "error": code,
        "message": str(exc),
    }
    if isinstance(exc, SAPLockError) and getattr(exc, "lock_owner", None):
        out["lock_owner"] = exc.lock_owner
    if isinstance(exc, SAPActivationError) and getattr(exc, "errors", None):
        out["errors"] = exc.errors
    return out


@contextlib.contextmanager
def _capture_stdout():
    """SAPClient methods print to stdout. In MCP stdio mode stdout is the protocol channel.
    Capture it so client chatter does not break JSON-RPC framing."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


# DDIC okuma-yolu TEK KAYNAKTAN gelir: `scripts/object_types.py` ->
# `DDIC_XML_ONLY_TYPES` / `DDIC_DDL_SOURCE_TYPES` / `ddic_read_mode()`.
# ⚠ Burada YEREL BIR KOPYA TUTMA. 2026-06-16'da bes DDIC tipi tek kume halinde
# XML-okuyucuya yonlendirilmisti; dogrusu ikiye ayriliyor:
#   * dataelement/domain/tabletype -> `/source/main` YOK (404) -> obje XML'i okunur.
#   * table/structure              -> GERCEK `/source/main` DDL ucu VAR (canli olculdu
#     2026-08-09; Z ve STANDART objelerde 200) -> duz DDL okunur.
# Ayni kural `scripts/sap_sync_pull.py`'de de gecerlidir; iki tuketici de ayni
# fonksiyonu cagirir (eskiden iki bagimsiz literal vardi ve ayrisiyordu).


def _ddic_read_mode(object_type: str) -> tuple[Optional[str], Optional[str]]:
    """`(mode, canonical)` — mode: 'ddl' | 'xml' | None. Tek kaynak: object_types.

    `(None, None)` DDIC-DEGIL demektir ve cagiran genel yola duser. Bu dal SESSIZ
    bir yanlis-cevap uretmez: genel yol `client.download_object` -> `get_source_url`
    zincirinden gecer, o da AYNI `object_types` modulunu kullanir. Yani modul
    gercekten yuklenemiyorsa `sap_client` import'u da coker ve `_get_client()`
    `ok:false` ile patlar; bilinmeyen tipte ise `get_source_url` ValueError atar ->
    `_err_from_exc` -> `ok:false`. Iki halde de sessiz `exists:false` YOKTUR.
    """
    try:
        from object_types import ddic_read_mode  # type: ignore
        mode, canonical = ddic_read_mode(object_type)
        return (mode, canonical)
    except Exception as exc:  # noqa: BLE001
        log.warning("object_types.ddic_read_mode yuklenemedi (%s) — DDIC ozel yolu atlandi", exc)
        return (None, None)


def _ddic_uri_seg(canonical_type: Optional[str]) -> Optional[str]:
    """Kanonik DDIC tipi -> ADT uc segmenti (ör. 'ddic/tables'); cozulemezse None.

    Yol tablosu object_types.OBJECT_TYPES'tadir — burada IKINCI bir kopya TUTULMAZ.
    """
    if not canonical_type:
        return None
    try:
        from object_types import OBJECT_TYPES  # type: ignore
        seg = OBJECT_TYPES[canonical_type]["url_path"]
    except Exception:
        return None
    return seg if isinstance(seg, str) and seg else None


# ⭐ TABLO <-> YAPI KARDES-UC ESLEMESI (2026-08-18 vakasi, kayit #8).
# Olculdu: `ZSD000_S_SCREEN_FIELD` / `ZSD000_S_SCREEN_BUTTON` (DDIC YAPI) CANLIDA VARDI,
# ama `adt_get(object_type="tabl")` `exists:false` dedi (`adt_search_objects` ikisini de
# buldu). Sebep: `tabl` `/ddic/tables/` ucuna gider, YAPILAR `/ddic/structures/` altinda
# yasar -> arac "YANLIS UCA SORDUM"u "OBJE YOK" diye raporluyordu.
# ⛔ NEDEN TEHLIKELI: "on kosul DDIC objesi yok" sonucu ya build'i durdurur ya da MUKERRER
# obje yaratma karari uretir (ADR 0005-D'ye kadar giden zincir).
# SINIF: `check_abaplint` SKIP=exit 0 ile AYNI aile -- "yok" ile "bakamadim" ayni cevaba
# dusuyor. Politika (bu evin kurali): YOKLUK IDDIASI KANIT ISTER.
# ⇒ Ilk uc 404 verirse KARDES uc de denenir; ikisi de 404 ise yokluk iddiasi GUCLENIR
# (`probed_endpoints` delili), kardes uc olculemezse yokluk BEYANI DARALTILIR
# (`sibling_probe: unavailable:...` + warning). Iki yon de kapsanir: bir GELISTIRICI
# `structure` tipiyle bir TABLOyu da sorabilir -- ayni kusur sinifinin diger yuzu.
_DDL_KARDES_SEG = {
    "ddic/tables": ("ddic/structures", "structure"),
    "ddic/structures": ("ddic/tables", "table"),
}


# "BULUNAMADI != YOK" (ölçüldü 2026-07-31, dört ayrı vaka aynı gün).
# adt_get, ulaşılamayan SAP'te de `ok:true, exists:false` döndürüyordu; obje CANLIDA
# VARDI ve client_log'da NameResolutionError yazıyordu. Bir ajan buna dayanıp
# "obje yok, yaratayım" derse ADR 0005-A sınırına dayanır. Bu yüzden ağ/erişim
# kaynaklı boş sonuç artık `exists:false` DEĞİL, açık HATA döner.
_UNREACHABLE_MARKERS = (
    "NameResolutionError", "getaddrinfo", "ConnectionError", "ConnectTimeout",
    "Max retries exceeded", "ReadTimeout", "SSLError", "ProxyError",
    "Connection refused", "Connection aborted",
)

# Doğrudan okuma yolu OLMAYAN tipler: /source/main eklenerek 404 alınır ve obje
# yanlışlıkla "yok" görünür. FM örneği ölçüldü (2026-07-31): ZSD001_FM_X canlıda
# VARdı, adt_get(type='func') exists:false dedi -- çünkü FM'in kaynağı
# /functions/groups/<fg>/fmodules/<fm>/source/main altındadır, fonksiyon grubu
# adı da tek başına FM adından çıkarılamaz.
_NO_DIRECT_READ_HINT = {
    "func": ("FM'in kaynağı fonksiyon grubu altındadır "
             "(/functions/groups/<fg>/fmodules/<fm>/source/main) ve grup adı FM adından "
             "çıkarılamaz. Doğru yol: adt_search_objects ile gerçek URI'yi al, sonra ham GET."),
    "function": ("FM'in kaynağı fonksiyon grubu altındadır; adt_search_objects ile URI al."),
}


def _bos_sonuc_sinifi(log_text: str) -> str:
    """Alt katmanın YUTTUĞU boş sonucu ÜÇ-DEĞERLİ sınıflandır.

    Döner: `"yok"` (yokluk KANITLI) · `"ulasilamadi"` (ağ/erişim) · `"belirsiz"`
    (hata var ama yokluk imzası YOK — ör. HTTP 500/403).

    ⛔ SINIF-KURALI (2026-08-01 bug-avı, "doğrulama koşamadı = doğrulandı"):
    `sap_client` katmanındaki okuyucular (`get_ddic_object`, `get_object_metadata`, ...)
    HER istisnayı yutup `None` döndürür ve sebebi yalnız stdout'a `[ERROR] ...` diye basar.
    Bu yüzden üst kattaki `except` dalları o yollarda HİÇ ateşlenmez; `None`'ı doğrudan
    "obje yok" saymak, "sunucu patladı"yı "yok"la AYNI cevaba düşürür. Kanıt tek yerden
    üretilsin diye sınıflandırma bu TEK fonksiyonda toplandı; `adt_get` (DDIC + klasik),
    delete-readback ve lock-probe aynı kaynağı kullanır.

    Kanıt kaynağı: `SAPADTError.__str__` = `"[<status>] <mesaj>"` → durum kodu log'a
    DÜŞER. 404 = yokluk kanıtı; 4xx/5xx = kanıt DEĞİL.
    """
    lt = log_text or ""
    if any(m in lt for m in _UNREACHABLE_MARKERS):
        return "ulasilamadi"
    dusuk = lt.lower()
    kodlar = set(re.findall(r"\[(\d{3})\]", lt))
    if kodlar - {"404"}:            # 500/403/502... → yokluk BEYAN EDİLMEZ
        return "belirsiz"
    if "404" in kodlar:
        return "yok"
    yokluk_imzasi = any(s in dusuk for s in
                        ("not found", "notfound", "404", "does not exist",
                         "bulunamadı", "bulunamadi"))
    hata_izi = "[error]" in dusuk
    if hata_izi and not yokluk_imzasi:
        return "belirsiz"
    # Temiz-boş yanıt (hata izi yok) ya da kesin bulunamadı imzası.
    return "yok"


def _miss_or_unreachable(name: str, object_type: str, log_text: str) -> dict:
    """Boş sonucu SINIFLANDIR: gerçekten 'obje yok' mu, yoksa 'ulaşamadım' mı?

    exists:false yalnızca SAP'ye ULAŞILDIĞI ve objenin gerçekten bulunmadığı
    durumda döner. Ağ/erişim izi varsa ok:false + unreachable döner -- çağıran
    bunu "yok" diye okuyamasın. (Sınıflandırma: `_bos_sonuc_sinifi`.)
    """
    _sinif = _bos_sonuc_sinifi(log_text)
    if _sinif == "ulasilamadi":
        return {
            "ok": False,
            "error": "unreachable",
            "name": name.upper(),
            "type": object_type,
            "message": (
                "SAP'ye ULAŞILAMADI — bu sonuç 'obje yok' DEĞİLDİR. Bağlantı/DNS/VPN "
                "kontrol et ve tekrar ölç. ⛔ Bu cevaba dayanıp obje YARATMA (ADR 0005-A)."
            ),
            "client_log": log_text,
        }
    # ⚠ YOKLUK İDDİASI KANIT İSTER (2026-08-01 bug-avı, W2-MCPT-01).
    # `_UNREACHABLE_MARKERS` yalnız AĞ katmanını tanır. Sunucu/yetki hataları (HTTP 500,
    # 502, 403 logon) o listeye girmez ve eskiden sessizce `exists:false`e düşerdi —
    # yani "sunucu patladı" ile "obje yok" AYNI cevabı veriyordu. Ölçüldü: 500/403/
    # timeout/bağlantı-kopması dördü de `ok:true, exists:false`.
    # Politika: log'da bir HATA izi varsa ve o iz KESİN bir bulunamadı imzası DEĞİLSE,
    # yokluk BEYAN EDİLMEZ → `ok:false` + belirsiz. Temiz-boş yanıt (hata izi yok) eskisi
    # gibi `exists:false` kalır; 404 imzası da öyle (kontrol grubu bunu doğrular).
    if _sinif == "belirsiz":
        return {
            "ok": False,
            "error": "belirsiz",
            "name": name.upper(),
            "type": object_type,
            "message": (
                "Obje okunamadı ve sebep BULUNAMADI-DEĞİL bir hata (ör. HTTP 500/403). "
                "Bu sonuç 'obje yok' DEĞİLDİR — sunucu/yetki hatası da olabilir. "
                "⛔ Bu cevaba dayanıp obje YARATMA ya da SİLME (ADR 0005-A). "
                "Hatayı gider, tekrar ölç."
            ),
            "client_log": log_text,
        }
    out = {"ok": True, "name": name.upper(), "type": object_type, "exists": False,
           "client_log": log_text}
    hint = _NO_DIRECT_READ_HINT.get((object_type or "").lower().strip())
    if hint:
        out["warning"] = (
            f"'{object_type}' tipi bu uçtan doğrudan okunamaz — exists:false BURADA "
            f"'obje yok' anlamına GELMEYEBİLİR. {hint}"
        )
    return out


# =============================================================================
# adt_get
# =============================================================================

def _read_source_object(name: str, uri_seg: str, type_label: str) -> dict:
    """Kaynak-endpoint'li obje oku (`.../source/main`) — `download_object`'in desteklemediği
    tipler için (ör. BDEF). Raw GET (Accept text/plain), READ-ONLY. (private helper — tool DEĞİL)
    """
    client = _get_client()
    log_buf = io.StringIO()
    try:
        adt = getattr(client, "adt_client", None) or client
        from urllib.parse import quote
        url = (adt.url + "/sap/bc/adt/" + uri_seg + "/"
               + quote(name.lower(), safe="") + "/source/main")
        with _capture_stdout() as out:
            r = adt.session.get(url, headers={"Accept": "text/plain"}, verify=False, timeout=60)
        log_buf.write(out.getvalue())
        if r.status_code == 404:
            # ⚠ YOKLUK KANITI ACIK YAZILIR. Ham `requests` GET'i stdout'a hicbir sey
            # basmaz -> log BOS kalir -> `_bos_sonuc_sinifi("")` "temiz-bos yanit"
            # dalindan "yok" dondururdu; yani dogru sonuc KAZAYLA cikardi. Durum kodunu
            # log'a yazinca siniflandirma 404 KANITINA dayanir (kanit-zinciri gorunur).
            log_buf.write("[404] GET %s\n" % url)
            return _miss_or_unreachable(name, type_label, log_buf.getvalue().strip())
        if r.status_code != 200:
            return {"ok": False, "name": name.upper(), "type": type_label,
                    "error": "http_%d" % r.status_code, "message": (r.text or "")[:500],
                    "client_log": log_buf.getvalue().strip()}
        out_ok = {"ok": True, "name": name.upper(), "type": type_label, "exists": True,
                  "source": r.text, "client_log": log_buf.getvalue().strip()}
        if not (r.text or "").strip():
            # 200 ama GOVDE BOS: obje VAR fakat kaynagi yok (create-POST'un biraktigi
            # shell/placeholder — playbook adt-tables-structures §28.1). Sessizce bos
            # source dondurmek "obje bos" yanilgisi uretir ve pull yolunda repo dosyasini
            # bosaltmaya calisir (write_repo_from_live FIX-C shrink korumasi yakalar).
            out_ok["source_empty"] = True
            out_ok["warning"] = (
                "Uc 200 dondu ama SOURCE BOS. Obje VAR; kaynagi bos (shell/placeholder "
                "olabilir — create yapildi ama DDL PUT edilmedi ya da aktive edilmedi). "
                "Bu sonucu 'obje bos/silinebilir' diye OKUMA; once SE11/adt ile teyit et."
            )
        return out_ok
    except Exception as exc:
        return _err_from_exc(exc)


@profil_tool()
def adt_get(name: str, object_type: str = "class", include_source: bool = True) -> dict:
    """Get an SAP ADT object: existence, metadata, and (optionally) source.

    Args:
        name: Object name (case-insensitive, normalised to upper on SAP side).
        object_type: ADT object type. Common: 'class', 'doma', 'dtel', 'tabl', 'view',
                     'ddls' (CDS), 'fugr', 'func', 'enqu', 'msag', 'prog'.
        include_source: If True, also fetches source text. Set False for fast metadata-only.

    Returns:
        {ok, name, type, exists, source?, metadata?, client_log}
        On miss:  {ok: true, exists: false, name, type}
        On error: {ok: false, error, message}

    ⭐ TABLO/YAPI KARDES-UC (2026-08-18 vakasi): `tabl` `/ddic/tables/`e, `structure`
    `/ddic/structures/`e sorar. Istenen uc 404 verirse KARDES uc de denenir:
      • kardeste BULUNURSA → `exists: true` + `resolved_type` / `resolved_endpoint` +
        `sibling_probe: "checked_found"` + tip duzeltmesi `warning`'i,
      • ikisi de 404 → `sibling_probe: "checked_absent"` + `probed_endpoints` (yokluk delili),
      • kardes uc OLCULEMEZSE → `sibling_probe: "unavailable:<sebep>"` + warning
        (yokluk beyani o uc ile SINIRLIDIR; "bakamadim" != "yok").
    ⛔ Bu fallback DDIC yapisi/tablosu icindir. DDIC objesinin varligini kritik bir kararda
    (obje YARATMA/SILME) `adt_get` ile TEK BASINA olcme — `adt_search_objects` ile capraz
    kontrol et (ADR 0005-A).
    """
    # MSAG (mesaj sınıfı): adt_get msag tipini DESTEKLEMEZ → özel messageclass endpoint'i.
    if (object_type or "").lower().strip() in ("msag", "messageclass"):
        return adt_msgclass_read(name)
    # BDEF (behavior definition): download_object DESTEKLEMEZ → source/main endpoint'i (raw GET).
    if (object_type or "").lower().strip() in ("bdef", "behaviordefinition"):
        return _read_source_object(name, "bo/behaviordefinitions", "bdef")

    client = _get_client()
    log_buf = io.StringIO()

    # DDIC tipleri IKI YOLA ayrilir (bkz. `_ddic_read_mode` notu):
    #   'ddl' (table/structure) -> GERCEK `/source/main` ucu var -> DUZ DDL oku.
    #   'xml' (dtel/doma/ttyp)  -> `/source/main` YOK -> obje XML'i oku.
    ddic_mode, ddic_canonical = _ddic_read_mode(object_type)
    if ddic_mode == "ddl":
        # Tablo/struct'un KAYNAGI DDL'dir: repo dosyalari da DDL tasir (bkz.
        # source_drift._TYPE_TO_EXTENSIONS) ve create yolu DDL'i `PUT /source/main`
        # ile yazar. XML zarfi dondurmek okuyucuyu (ve pull yolunu) DDL yerine
        # `<blue:blueSource>` govdesiyle besliyordu.
        seg = _ddic_uri_seg(ddic_canonical)
        if seg is None:
            # Sozlesme ihlali: mode='ddl' geldi ama uc segmenti cozulemedi. SESSIZCE
            # XML yoluna DUSMEK yasak — cagiran DDL bekliyor, XML zarfi alirdi ve bunu
            # fark etmezdi (§127 "dogrulama kosamadi = dogrulandi" sinifi). ACIK HATA.
            return {
                "ok": False,
                "error": "ddic_uri_unresolved",
                "name": name.upper(),
                "type": object_type,
                "message": (
                    f"DDIC tipi '{ddic_canonical}' icin ADT uc segmenti (url_path) "
                    "cozulemedi — kaynak OKUNMADI. Bu sonuc 'obje yok' ya da 'kaynak bos' "
                    "DEGILDIR. object_types.OBJECT_TYPES tablosunu kontrol et."
                ),
            }
        r = _read_source_object(name, seg, object_type)
        # Kardes-uc fallback: tablo ucunda 404 -> YAPI ucunu da dene (ve tersi).
        # Bkz. `_DDL_KARDES_SEG` notu (kayit #8, 2026-08-18 ZSD000_S_SCREEN_* vakasi).
        if r.get("ok") is True and r.get("exists") is False and seg in _DDL_KARDES_SEG:
            kardes_seg, kardes_tip = _DDL_KARDES_SEG[seg]
            r2 = _read_source_object(name, kardes_seg, object_type)
            if r2.get("ok") is True and r2.get("exists") is True:
                # Obje VAR — yalnizca YANLIS UCA sorulmustu. `type` cagiranin verdigi
                # deger olarak KALIR (sozlesme sabit); dogru tip AYRI alanda bildirilir.
                r2["type"] = object_type
                r2["requested_endpoint"] = seg
                r2["resolved_endpoint"] = kardes_seg
                r2["resolved_type"] = kardes_tip
                r2["sibling_probe"] = "checked_found"
                r2["warning"] = (
                    "TIP DUZELTMESI: '%s' tipi '%s' ucuna sorar, ama bu obje '%s' "
                    "ucunda bulundu (kanonik tip: '%s'). Kaynak DOGRU objeden okundu. "
                    "Sonraki cagrilarda object_type='%s' kullan."
                    % (object_type, seg, kardes_seg, kardes_tip, kardes_tip)
                )
                return r2
            if r2.get("ok") is True and r2.get("exists") is False:
                # Iki ucta da 404 -> yokluk iddiasi GUCLENDI (delil listesi acik yazilir).
                r["sibling_probe"] = "checked_absent"
                r["probed_endpoints"] = [seg, kardes_seg]
            else:
                # Kardes uc OLCULEMEDI -> yokluk beyani DARALTILIR ("bakamadim" != "yok").
                r["sibling_probe"] = "unavailable:%s" % (r2.get("error") or "bilinmeyen")
                r["probed_endpoints"] = [seg]
                r["warning"] = (
                    "exists:false YALNIZ '%s' ucu icin KANITLIDIR. Kardes uc ('%s') "
                    "OLCULEMEDI (%s) — obje bir YAPI/TABLO olarak orada duruyor olabilir. "
                    "⛔ Bu cevaba dayanip obje YARATMA; adt_search_objects ile capraz kontrol et."
                    % (seg, kardes_seg, r2.get("error") or "bilinmeyen")
                )
        return r

    ddic_xml_type = ddic_canonical if ddic_mode == "xml" else None
    if ddic_xml_type is not None:
        try:
            with _capture_stdout() as out:
                xml = client.get_ddic_object(ddic_xml_type, name)
            log_buf.write(out.getvalue())
            if xml is None:
                # ⚠ "BULUNAMADI ≠ YOK" — DDIC dalı (2026-08-01 bug-avı, W2-MCPT-01).
                # Eskiden `exists: xml is not None` yazıyordu ve `None` gelen HER durum
                # "obje yok" sayılıyordu. Ama alt katman (`sap_client.get_ddic_object`)
                # **her istisnayı yutup None döndürür** → aşağıdaki `except` dalı bu tipler
                # için HİÇ ateşlenmez. Ölçüldü (stub'lu kontrol grubuyla):
                #   gerçek 404      → exists:false   ✔ doğru
                #   HTTP 500 / 403  → exists:false   ✘ ok:true ile, 404'ten AYIRT EDİLEMEZ
                #   ReadTimeout     → exists:false   ✘
                #   bağlantı kopuk  → exists:false   ✘
                # Sonuç: ajan "yok" sanıp yeniden YARATIR (ADR 0005-A sınırı) ya da mevcut
                # objeyi ezer. Aynı sınıf `class` yolunda 2026-07-31'de kapatılmıştı;
                # DDIC dalı geride kalmıştı.
                # POLİTİKA: yokluk iddiası KANIT ister. `exists:false` yalnız log'da KESİN
                # bir bulunamadı imzası varsa döner; aksi halde yokluk BEYAN EDİLMEZ.
                return _miss_or_unreachable(name, object_type, log_buf.getvalue().strip())
            return {
                "ok": True,
                "name": name,
                "type": object_type,
                "exists": True,
                "source": xml,
                "metadata": xml,
                "client_log": log_buf.getvalue().strip(),
            }
        except Exception as exc:
            from sap_adt_lib import SAPObjectNotFoundError, SAPADTError  # type: ignore
            if isinstance(exc, SAPObjectNotFoundError) or (
                isinstance(exc, SAPADTError) and getattr(exc, "status_code", None) == 404
            ):
                return _miss_or_unreachable(name, object_type, log_buf.getvalue().strip())
            return _err_from_exc(exc)

    try:
        with _capture_stdout() as out:
            source = None
            metadata = None
            if include_source:
                source = client.download_object(name, object_type=object_type, save_local=False)
            metadata = client.get_object_metadata(name, object_type=object_type)
        log_buf.write(out.getvalue())
        # Alt katman istisna ATMADAN None dönebiliyor (ör. ağ hatası yutulmuşsa). O hâlde
        # "obje yok" değil "ulaşamadım" olabilir -- sınıflandırmayı _miss_or_unreachable yapar.
        if source is None and metadata is None:
            return _miss_or_unreachable(name, object_type, log_buf.getvalue().strip())
        return {
            "ok": True,
            "name": name,
            "type": object_type,
            "exists": True,
            "source": source,
            "metadata": metadata,
            "client_log": log_buf.getvalue().strip(),
        }
    except Exception as exc:
        from sap_adt_lib import SAPObjectNotFoundError  # type: ignore
        if isinstance(exc, SAPObjectNotFoundError):
            return _miss_or_unreachable(name, object_type, log_buf.getvalue().strip())
        return _err_from_exc(exc)


# =============================================================================
# adt_msgclass_read  (mesaj sınıfı / MSAG okuma — adt_get msag DESTEKLEMEZ)
# =============================================================================
_MC_NS_MC = "http://www.sap.com/adt/MessageClass"
_MC_NS_AC = "http://www.sap.com/adt/core"


def _parse_msgclass_xml(xml_text: str) -> dict:
    """ADT `mc:messageClass` XML → {name, master_language, description, messages:[...]}.

    Kanıt (canlı MSAG doğrulaması, 2026-07-12): her mesaj `<mc:messages mc:msgno mc:msgtext
    mc:selfexplainatory mc:documented>` attribute'ları taşır; metin HTML-escape'li (ET çözer).
    """
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_text)

    def _ac(a: str):
        return root.get("{%s}%s" % (_MC_NS_AC, a))

    messages = []
    for el in root.findall("{%s}messages" % _MC_NS_MC):
        def _g(a: str, _el=el):
            return _el.get("{%s}%s" % (_MC_NS_MC, a))
        messages.append({
            "no": _g("msgno"),
            "text": _g("msgtext"),
            "selfexplanatory": (_g("selfexplainatory") == "true"),
            "documented": (_g("documented") == "true"),
        })
    return {
        "name": _ac("name"),
        "master_language": _ac("masterLanguage"),
        "description": _ac("description"),
        "messages": messages,
    }


@profil_tool()
def adt_msgclass_read(name: str) -> dict:
    """Read a message class (MSAG) and ALL its messages via ADT. READ-ONLY.

    Neden ayrı tool: `adt_get` msag tipini DESTEKLEMEZ ve `adt_table_read` T100'ü
    filtreleyemez (WHERE param yok; T100 preview 400 verir). Bu tool resmî ADT kaynağını
    kullanır: ham GET `/sap/bc/adt/messageclass/{name}`
    (Accept `application/vnd.sap.adt.mc.messageclass+xml`) → XML parse.

    Referans: marcellourbani/vscode_abap_remote_fs (Message Class Editor). CANLI-DOĞRULANDI
    (2026-07-12): `/messages` alt-path'i 404; kök `/messageclass/{name}` +
    `.mc.messageclass+xml` Accept çalışır (reference'ın `.v2+xml` header'ı 406 verir —
    sunucu kabul-tipini kendi bildirir).

    Args:
        name: Mesaj sınıfı adı (ör. 'ZSD001').

    Returns:
        {ok, name, exists, master_language?, description?, count?, messages?, client_log}
        messages: [{no, text, selfexplanatory, documented}, ...] (text: '&' çözülmüş, master dil).
        On miss: {ok: true, exists: false, name}
    """
    client = _get_client()
    log_buf = io.StringIO()
    try:
        adt = getattr(client, "adt_client", None) or client
        from urllib.parse import quote
        url = adt.url + "/sap/bc/adt/messageclass/" + quote(name.lower(), safe="")
        with _capture_stdout() as out:
            r = adt.session.get(
                url,
                headers={"Accept": "application/vnd.sap.adt.mc.messageclass+xml"},
                verify=False, timeout=60,
            )
        log_buf.write(out.getvalue())
        if r.status_code == 404:
            return {"ok": True, "name": name.upper(), "exists": False,
                    "client_log": log_buf.getvalue().strip()}
        if r.status_code != 200:
            return {"ok": False, "name": name.upper(), "error": "http_%d" % r.status_code,
                    "message": (r.text or "")[:500], "client_log": log_buf.getvalue().strip()}
        parsed = _parse_msgclass_xml(r.text)
        return {
            "ok": True,
            "name": parsed["name"] or name.upper(),
            "exists": True,
            "master_language": parsed["master_language"],
            "description": parsed["description"],
            "count": len(parsed["messages"]),
            "messages": parsed["messages"],
            "client_log": log_buf.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_post_shell
# =============================================================================

# ⛔ CREATE'IN "BASARISIZ" DONUSU DE KANIT DEGILDIR (kayitlar #20 + #49 — ayni kokun iki yuzu).
#
# Olculmus iki vaka:
#   2026-08-19 `ZCL_SD000_GET_IDOCDATA`: MCP **400** raporladi, obje FIILEN YARATILMISTI
#     (3. ve 4. denemede sunucu `ExceptionResourceAlreadyExists` dedi; TADIR'dan dogrulandi).
#     ⚠ AYNI turda GERCEK bir 400 da vardi: sinif kisa metni siniri
#     `adtcore:descriptionTextLimit="60"`, verilen aciklama 80 karakterdi. Yani iki AYRI 400:
#     (a) gercek (metin > sinir)  (b) sahte (create basarili ama 400 raporlandi).
#   2026-08-21 `A-13` (uc sinif): donus `[ERROR] [500] Failed to create CLAS/OC` -> `ok:false`,
#     ama kabuk UCUNDE DE GERCEKTEN YARATILDI (`adt_get exists=true` · TADIR DEVCLASS dolu,
#     DELFLAG bos).
#
# ⛔ NEDEN CIDDI — RETRY TUZAGI: `ok:false` gorunce dogal refleks TEKRAR DENEMEKTIR. Bir
# gateway bunu bilmeden yapti -> 400 ("zaten var") aldi; zarar OLMADI ama bu yalniz SAP'nin
# ikinci yaratmayi reddetmesi sayesinde. Idempotent OLMAYAN bir obje tipinde ayni refleks
# MUKERRER YARATMA uretirdi. ⇒ "exit 0 != kanit"in TERS YUZU: `ok:false` DA kanit degil.
#
# ⚠ MEKANIK SEBEP (olculdu, `sap_client.create_object`): o katman HER istisnayi YUTAR,
# sebebi yalnizca stdout'a `[ERROR] ...` diye basar ve `None` doner. Yani buradaki
# `except Exception` dali create hatalarinda HIC atesLENMEZ; tek sinyal `client_log`'tur.
# Bu, `_bos_sonuc_sinifi`nin cozdugu sinifin aynisidir -> sinyal LOG'DAN cikarilir.
_CREATE_HATA_IMZALARI = (
    # (imza (kucuk harf), donus kodu, aciklama)
    ("exceptionresourcealreadyexists", "already_exists",
     "SAP 'kaynak ZATEN VAR' dedi — obje mevcut. ⛔ TEKRAR YARATMAYA CALISMA."),
    ("resourcealreadyexists", "already_exists",
     "SAP 'kaynak ZATEN VAR' dedi — obje mevcut. ⛔ TEKRAR YARATMAYA CALISMA."),
    ("descriptiontextlimit", "description_too_long",
     "GERCEK 400: kisa metin (description) SAP'nin tip-basina sinirini ASIYOR. "
     "Ham govdedeki `adtcore:descriptionTextLimit` degerine bak (sinif icin olculen: 60) "
     "ve aciklamayi KISALT. Bu bir sahte-400 DEGILDIR."),
)


def _create_hata_sinifi(log_text: str) -> tuple[str, str]:
    """create `None` dondugunde sebebi LOG'dan sinifla -> (kod, aciklama).

    Log'da tanidik bir imza yoksa `("create_failed", "")` doner — UYDURMA YOK.
    """
    dusuk = (log_text or "").lower()
    for imza, kod, aciklama in _CREATE_HATA_IMZALARI:
        if imza in dusuk:
            return kod, aciklama
    kodlar = sorted(set(re.findall(r"\[(\d{3})\]", log_text or "")))
    if kodlar:
        return "create_failed", "SAP HTTP durum(lari): %s (ham sebep client_log'da)." % ", ".join(kodlar)
    return "create_failed", ""


def _varlik_sondasi(name: str, object_type: str) -> tuple[Optional[bool], str]:
    """Create hatasi SONRASI objenin GERCEKTEN var olup olmadigini olc.

    Uc-degerli: `True` (var) · `False` (yok) · `None` (OLCULEMEDI — "yok" DEGIL).
    ⛔ `None`'i "yaratilmadi" diye okuma; bu ayrimin kaybi kaydin ta kendisidir.
    """
    try:
        p = adt_get(name=name, object_type=object_type, include_source=False)
    except Exception as exc:  # noqa: BLE001 — teshis bozulmasin
        return None, "unavailable:%s" % type(exc).__name__
    if p.get("ok") is True and p.get("exists") is True:
        return True, "checked_found"
    if p.get("ok") is True and p.get("exists") is False:
        return False, "checked_absent"
    return None, "unavailable:%s" % (p.get("error") or "bilinmeyen")


@profil_tool()
def adt_post_shell(
    object_type: str,
    name: str,
    package: str,
    transport: str,
    description: str,
    extra: dict | None = None,
) -> dict:
    """Create an empty SAP object shell (inactive, no source yet).

    Use adt_push_source + adt_activate after this for atom flow.
    Composite tools (adt_*_create) chain these three atomically.

    Args:
        object_type: 'class', 'doma', 'dtel', 'tabl', 'ddls', 'msag', ...
        name: Customer-namespace name (Z* or Y*).
        package: Target SAP package.
        transport: Modifiable transport request number.
        description: Short description (TR for Z* objects per ADR 0005 §D).
        extra: Object-specific parameters (e.g., {'datatype':'CHAR','length':10} for domain).

    ⛔ **`ok: false` "OBJE YARATILMADI" DEMEK DEGILDIR — RETRY ETMEDEN ONCE OKU.**
    Olculdu (2026-08-19 ve 2026-08-21, dort obje): arac `400` / `500` raporladi, kabuk
    **fiilen YARATILMISTI**. Bu yuzden hata donusune artik bir **VARLIK SONDASI** eklidir:
      • `exists_after: true`  → obje SAP'de VAR. ⛔ **TEKRAR YARATMAYA CALISMA** (mukerrer
        obje riski); `adt_push_source` ile devam et.
      • `exists_after: false` → obje yok, yeniden denenebilir.
      • `exists_after: null`  → **OLCULEMEDI** ("yok" DEGIL). `exists_probe`'a bak, elle dogrula.
    `error` degerleri: `already_exists` (SAP `ExceptionResourceAlreadyExists`) ·
    `description_too_long` (**GERCEK** 400 — kisa metin SAP sinirini asiyor, olculen sinif
    siniri 60) · `create_failed` (siniflanamadi; ham sebep `client_log`'da).
    ⇒ Yan kural (iki kez ise yaradi): ADT 400'lerinde **ham govdeyi oku** — sebep orada
    yazilidir (kolon adi · metin siniri · zaten var). Govdeyi okumadan "flakiness" deme.

    Returns:
        {ok, name, type, object_url?, result?, client_log}
        On failure: {ok: false, error, message, exists_after, exists_probe, client_log}
        On guardrail block: {ok: false, error: 'guardrail_violation', code, message}
    """
    try:
        require_writable_tier(get_active_tier(), what=f"{object_type} create")
        require_customer_namespace(name, what=object_type)
        require_transport(transport, what=f"{object_type} create")
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()
    try:
        with _capture_stdout() as out:
            result = client.create_object(
                object_type=object_type,
                name=name,
                package=package,
                description=description,
                transport=transport,
                **(extra or {}),
            )
        log_text = out.getvalue().strip()
        if result:
            # `create_object` basarida obje URL'ini (str) doner. Eskiden yalniz
            # `result if isinstance(result, dict)` yaziliydi -> str URL her zaman None'a
            # dusuyordu ve docstring'in vaat ettigi `object_url` HIC dolmuyordu.
            return {
                "ok": True,
                "name": name,
                "type": object_type,
                "object_url": result if isinstance(result, str) else None,
                "result": result if isinstance(result, dict) else None,
                "client_log": log_text,
            }

        # ── BASARISIZ GORUNEN DONUS: "olmadi" mi, "oldu ama hata raporlandi" mi? ──
        # (kayitlar #20 + #49 — retry tuzagi; gerekce icin yukaridaki blok notuna bak)
        kod, aciklama = _create_hata_sinifi(log_text)
        var_mi, sonda = _varlik_sondasi(name, object_type)
        if var_mi is True:
            mesaj = ("⚠ CREATE HATA RAPORLADI **AMA OBJE SAP'DE VAR** (varlik sondasi: "
                     "adt_get exists=true). ⛔ TEKRAR YARATMAYA CALISMA — mukerrer obje "
                     "riski. Kabuk hazir; `adt_push_source` ile devam et.")
        elif var_mi is False:
            mesaj = "Obje yaratilmadi (varlik sondasi: adt_get exists=false)."
        else:
            mesaj = ("⚠ Obje yaratildi mi OLCULEMEDI (varlik sondasi: %s). Bu sonuc "
                     "'yaratilmadi' DEGILDIR — ⛔ KOR RETRY YAPMA; once adt_get / TADIR ile "
                     "varligi ELLE olc." % sonda)
        return {
            "ok": False,
            "error": kod,
            "name": name,
            "type": object_type,
            "message": (mesaj + (" " + aciklama if aciklama else "")).strip(),
            "exists_after": var_mi,
            "exists_probe": sonda,
            "client_log": log_text,
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_push_source
# =============================================================================

@profil_tool()
def adt_push_source(
    name: str,
    object_type: str,
    source: str,
    transport: str | None = None,
    skip_reviewer: bool = False,
    ack_drop: str = "",
) -> dict:
    """Push source text to an existing SAP object.

    The shell must exist (use adt_post_shell first, or composite tools).
    Activation is a separate step — call adt_activate after.

    Reviewer pre-flight (ADR 0006) runs automatically on the source text
    (written to a temp file, passed to scripts/validators/run_review.py).
    BLOCKER verdict rejects the push. Use skip_reviewer=True only for emergencies
    (and document why in the commit message).

    Args:
        name: Object name (Z*/Y*).
        object_type: 'class', 'ddls', 'prog', 'tabl', ...
        source: Source body text (full content; partial diffs not supported).
        transport: Modifiable transport (optional if object already has assignment).
        skip_reviewer: Bypass reviewer pre-flight (NOT recommended).
        ack_drop: Comma-separated table field names whose DROP is explicitly
            approved (user+lead, ADR 0005-B). Forwarded to the embedded reviewer's
            --ack-drop → ONLY these named drops become ACK-WARNING; any un-named
            drop or any TYPE/RENAME change still BLOCKER. This is the targeted,
            auditable alternative to skip_reviewer for intentional table DROPs —
            the rest of the drop-guard (and all other checks) stay active.

    Returns:
        {ok, name, type, result, client_log, reviewer?}
    """
    try:
        require_writable_tier(get_active_tier(), what=f"{object_type} push")
        require_customer_namespace(name, what=object_type)
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()
    tmp_file = None
    reviewer_warn = None
    try:
        # Write source to temp file first — needed by both reviewer and SAPClient.push_object.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=f".{object_type}.txt",
            delete=False,
        ) as f:
            f.write(source)
            tmp_file = Path(f.name)

        # Reviewer pre-flight (ADR 0006) — automatic, single point of enforcement.
        if not skip_reviewer:
            task = task_for_push(object_type)
            review = run_reviewer(task, str(tmp_file), ack_drop=ack_drop)
            if review.is_blocker:
                return reject_payload(name, object_type, review)
            # G2 (2026-07-31): SKIP artik SESSIZ degil — "PRE-FLIGHT KOSMADI" bilgisi
            # yanita girer (checklist!=wired sinifinin reviewer versiyonuna karsi).
            # Davranis DEGISMEZ (push yine gecer); yalniz gorunurluk.
            reviewer_warn = review.to_dict()
            if review.verdict == "SKIP":
                reviewer_warn["notice"] = (
                    f"PRE-FLIGHT KOSMADI ({review.skip_reason}) — bu tip icin "
                    "validator zinciri tanimli degil; 'reviewer PASS' SANMA.")

        # ADR 0016 REVİZE: pre-push DRIFT GUARD (M1) KALDIRILDI — kasıtlı edit'leri de
        # blokluyordu (repo≠canlı her meşru edit'te doğal). Tazelik artık edit-ÖNCESİ
        # pull-before-edit hook ile sağlanır → push'ta ayrı drift-kontrolü gerekmez.
        with _capture_stdout() as out:
            result = client.push_object(
                object_name=name,
                object_type=object_type,
                transport=transport,
                source_file=str(tmp_file),
            )
        ok = bool(result and (result.get("success") if isinstance(result, dict) else True))
        resp = {
            "ok": ok,
            "name": name,
            "type": object_type,
            "result": result if isinstance(result, dict) else None,
            "client_log": out.getvalue().strip(),
        }
        if reviewer_warn:
            resp["reviewer"] = reviewer_warn

        # ── READBACK GÖRÜNÜRLÜĞÜ (2026-08-01 bug-avı, "doğrulama koşamadı = doğrulandı") ──
        # `push_object` aktivasyon sonrası AKTİF kaynağı yüklenenle kıyaslar. Bu kıyas
        # KOŞAMADIĞINDA (okuma hatası / tip kapsam dışı) eskiden yanıtta HİÇBİR iz kalmıyordu
        # → `ok:true` hem "doğrulandı" hem "doğrulanamadı" anlamına geliyordu. Artık üç değer
        # AÇIKÇA yüzeye çıkar. Davranış (ok) DEĞİŞMEZ — yalnız görünürlük (reviewer SKIP
        # görünürlüğüyle aynı desen, 2026-07-31).
        if isinstance(result, dict):
            rb = result.get("readback_ok")
            resp["readback_verified"] = rb if rb in (True, False) else None
            if resp["readback_verified"] is None:
                resp["readback_notice"] = (
                    "READBACK KOŞMADI/ÖLÇÜLEMEDİ — canlı aktif kaynak yüklenenle "
                    "KIYASLANAMADI. Bu 'yazım doğrulandı' DEĞİLDİR; kritik objede "
                    "adt_get(version=active) ile elle teyit et. "
                    + str(result.get("readback_reason", "")).strip()
                ).strip()

        # Aktivasyon-oncesi canli syntax-check (push_object icinde) basarisizsa yuzeye cikar:
        # push upload etti ama AKTIVE ETMEDI -> ok=False + hatalar (gateway net gorsun, nested kalmasin).
        if isinstance(result, dict) and result.get("syntax_precheck") == "failed":
            resp["ok"] = False
            resp["syntax_precheck"] = "failed"
            resp["syntax_errors"] = result.get("syntax_errors", [])

        # Readback-gate: push edilen source'u kaydet → adt_activate sonrası AKTİF source ile
        # normalize-compare için (yazımın tam oturduğunu doğrula). Upload başarılıysa.
        if ok:
            _LAST_PUSHED[(name.upper(), _type_key(object_type))] = (object_type, source)

        # Sprint 6 T10 — post-push consistency check.
        # Struct/table push'larda placeholder kalma veya version=inactive durumlarını
        # yakalamak için reviewer'ı tekrar (post-mode) çağır.
        if ok and not skip_reviewer:
            obj_lower = (object_type or "").lower()
            if obj_lower in ("structure", "struct"):
                post = run_reviewer("struct_post_create", str(tmp_file))
                resp["post_check"] = {
                    "ok": post.passed,
                    "verdict": post.verdict,
                    "blocker_count": post.blocker_count,
                    "warning_count": post.warning_count,
                }
                if post.skip_reason:
                    resp["post_check"]["skip_reason"] = post.skip_reason
                if not post.passed:
                    resp["ok"] = False
            elif obj_lower in ("tabl", "ddls", "dtel", "doma"):
                # Generic active-version check via the same orchestrator.
                post = run_reviewer("sap_active_check", str(tmp_file))
                resp["post_check"] = {
                    "ok": post.passed,
                    "verdict": post.verdict,
                }
                if post.skip_reason:
                    resp["post_check"]["skip_reason"] = post.skip_reason
                if not post.passed:
                    resp["ok"] = False
        return resp
    except Exception as exc:
        return _err_from_exc(exc)
    finally:
        if tmp_file and tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass


# =============================================================================
# adt_activate
# =============================================================================

@profil_tool()
def adt_delete(
    name: str,
    object_type: str,
    transport: str | None = None,
) -> dict:
    """Delete a Z/Y namespace SAP object.

    Hard guardrail (ADR 0005 §A): only Z*/Y* objects deletable. Standard SAP
    objects → reject. Caller bears responsibility for downstream impact;
    where-used analysis is the caller's job (not done here).

    Args:
        name: Object name (must be Z*/Y*).
        object_type: 'class', 'doma', 'dtel', 'tabl', 'ddls', 'msag', 'prog', ...
        transport: Modifiable transport for the delete entry.

    Returns:
        {ok, name, type, deleted, client_log}
    """
    try:
        require_writable_tier(get_active_tier(), what=f"{object_type} delete")
        reject_standard_delete(name, object_type)
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()
    try:
        with _capture_stdout() as out:
            deleted = client.delete_object(
                object_name=name,
                object_type=object_type,
                transport=transport,
                confirm=False,  # MCP context: no interactive prompt possible
            )
        resp = {
            "ok": bool(deleted),
            "name": name,
            "type": object_type,
            "deleted": bool(deleted),
            "client_log": out.getvalue().strip(),
        }
        # Readback-gate: silme GERÇEKTEN oturdu mu — obje hâlâ varsa BLOCKER.
        # ÜÇ-DEĞERLİ: True/False/None; None ASLA True'ya katlanmaz (bkz. _exists_after_delete).
        if resp["ok"]:
            still, sebep = _exists_after_delete(client, name, object_type)
            if still is True:
                resp["ok"] = False
                resp["deleted"] = False
                resp["delete_verified"] = False
                resp["delete_reason"] = ("Silme sonrası obje HÂLÂ mevcut (readback) — silme "
                                         "oturmadı. Lock/transport/bağımlılık kontrol et, tekrar dene.")
            elif still is False:
                resp["delete_verified"] = True
            else:
                resp["delete_verified"] = None
                resp["delete_reason"] = sebep or (
                    "Silme sonrası varlık readback yapılamadı (soft; manuel teyit).")
        # _LAST_PUSHED temizliği — silinen objenin bayat push kaydı kalmasın (tüm tip-varyantları).
        for _k in [k for k in _LAST_PUSHED if k[0] == name.upper()]:
            _LAST_PUSHED.pop(_k, None)
        return resp
    except Exception as exc:
        return _err_from_exc(exc)


# Aktivasyon obje URI segmentleri (tip → ADT path; /source/main YOK). Çoklu-obje atomik
# aktivasyon (interface DDLS + BDEF + class aynı /activation POST'ta — ADIM-1 tipi RAP
# zincirleri) + activate_object'in bilmediği tipler (bdef/srvd) için.
_ACTIVATION_URI_SEG = {
    "ddls": "ddic/ddl/sources", "cds": "ddic/ddl/sources", "cdsview": "ddic/ddl/sources",
    "bdef": "bo/behaviordefinitions", "behaviordefinition": "bo/behaviordefinitions",
    "class": "oo/classes", "clas": "oo/classes",
    "srvd": "ddic/srvd/sources", "servicedefinition": "ddic/srvd/sources",
    "dcl": "acm/dcl/sources", "accesscontrol": "acm/dcl/sources",
    "ddlx": "ddic/ddlx/sources", "metadataextension": "ddic/ddlx/sources",
    "domain": "ddic/domains", "doma": "ddic/domains",
    "dataelement": "ddic/dataelements", "dtel": "ddic/dataelements",
    "table": "ddic/tables", "tabl": "ddic/tables", "structure": "ddic/structures",
    "program": "programs/programs", "prog": "programs/programs",
    # 2026-08-01 (T1.6 pilot bulgusu): klasik program+include co-activation'ı için include
    # tipi eksikti -> adt_activate(also=[{object_type:"include"}]) unsupported_type veriyordu.
    "include": "programs/includes", "prog/i": "programs/includes",
    "srvb": "businessservices/bindings", "servicebinding": "businessservices/bindings",
    # 2026-08-22 (kayit #70): `fugr` bu sozlukte HIC YOKTU -> `_activation_uri` None
    # donuyor, `also=[{object_type:"fugr"}]` atomik co-activate'i `unsupported_type` ile
    # reddediliyordu. Segment repoda zaten kanitli tek kaynakta: `scripts/object_types.py`
    # FUGR `url_path='functions/groups'` (kardes tuketici: `query.py` iki yerde ayni esleme).
    "fugr": "functions/groups", "functiongroup": "functions/groups",
}


# ⛔ AKTIVASYON READBACK'i (kayit #70, olculdu 2026-08-22 bir FUGR uzerinde; ornek ad
# `ZSD001_FG_ORNEK`):
#   `adt_activate(object_type='fugr')`      -> **`activated: true`**
#   ayni anda HAM `POST /activation`        -> **`activationExecuted="false"`**
#   `adt_inactive_objects`                  -> ayni FUGR (FUGR/F) **LISTEDE**
#   bagimsiz ucuncu kanit (ATC)             -> "The program SAPL<FUGR> contains
#                                              **inactive parts**"
# ⇒ SINIF: sessiz sahte-yesil. Arac "aktive ettim" diyor, obje INAKTIF kaliyor; yalniz
# `adt_activate` donusune bakan bir ajan YANLIS sonuca varir.
#
# ⚠ BUGUNKU BOSLUK YAPISALDIR: klasik yolun TEK dogrulamasi `_content_readback`'tir, o da
# (a) yalniz `_SOURCE_BASED_TYPES` icin ve (b) yalniz bu seansta `adt_push_source` kaydi
# varsa kosar. `fugr` (ve dtel/doma/tabl gibi XML-DDIC tipleri, ayrica salt re-activate)
# ⇒ **HIC dogrulanmiyor**. Bu sonda o bosluga, kaydin KENDI kullandigi bagimsiz sinyalle
# (aktive-bekleyen worklist'i) cevap verir.
#
# ⛔ NEDEN `activate_and_verify` YOLUNA (srvb gibi) TASINMADI: `srvb`'de gerekce
# "`activate_object` bu tipi DESTEKLEMIYOR"du. `fugr` DESTEKLENIYOR ve klasik yol FUGR icin
# GEREKLI olan iki-fazli pre-audit + `ioc:inactiveObjects` alt-obje toplamasini yapiyor
# (FUGR'un FF/I alt-objeleri tam da bu yolla aktive ediliyor). Tipi ref-yoluna tasimak bu
# mekanizmayi KAYBETTIRIR ve CALISAN aktivasyonlari bozabilir -> SAP'siz olculemez.
# ⇒ Dar ve olculebilir olan secildi: klasik yol KORUNDU, ustune BAGIMSIZ readback konuldu.
_AKTIVASYON_WORKLIST_UC = "/sap/bc/adt/activation/inactiveobjects"


def _aktivasyon_readback(client, adlar: list) -> tuple[Optional[bool], str, list]:
    """Aktivasyondan SONRA obje(ler) hala 'aktive bekliyor' listesinde mi?

    Uc-degerli: `True` (aktivasyon DOGRULANDI — listede yok) · `False` (hala INAKTIF) ·
    `None` (**OLCULEMEDI**; "dogrulandi" DEGIL — `sebep` alanina bak).
    ⛔ Olcum kurulamamasini "temiz" sayma: bu kaydin kok sinifi tam olarak odur.
    """
    import xml.etree.ElementTree as ET
    hedef = {(a or "").strip().upper() for a in adlar if (a or "").strip()}
    if not hedef:
        return None, "unavailable:isim_yok", []
    try:
        from mcp_servers.sap_adt.tools.query import _IOC_NS  # tek kaynak (yerel kopya YOK)
        adt = getattr(client, "adt_client", None) or client
        with _capture_stdout():
            r = adt.session.get(adt.url + _AKTIVASYON_WORKLIST_UC,
                                headers={"Accept": "application/*"}, verify=False, timeout=45)
        if getattr(r, "status_code", None) != 200:
            return None, "unavailable:http_%s" % getattr(r, "status_code", "?"), []
        root = ET.fromstring(r.text or "")
        hala: list = []
        for entry in root.findall("ioc:entry", _IOC_NS):
            obj = entry.find("ioc:object", _IOC_NS)
            ref = obj.find("ioc:ref", _IOC_NS) if obj is not None else None
            if ref is None:
                continue                      # transport-seviyesi girdi (bos object)
            ad = (ref.get("{%s}name" % _IOC_NS["adtcore"], "") or "").strip().upper()
            tip = ref.get("{%s}type" % _IOC_NS["adtcore"], "") or ""
            if ad in hedef and ad not in [h["name"] for h in hala]:
                hala.append({"name": ad, "type": tip})
        return (not hala), ("checked_inactive" if hala else "checked_active"), hala
    except Exception as exc:  # noqa: BLE001 — teshis bozulmasin
        return None, "unavailable:%s" % type(exc).__name__, []


def _activation_uri(name: str, object_type: str):
    from urllib.parse import quote
    seg = _ACTIVATION_URI_SEG.get((object_type or "").lower().strip())
    if not seg:
        return None
    return f"/sap/bc/adt/{seg}/{quote(name.lower(), safe='')}"


@profil_tool()
def adt_activate(name: str, object_type: str = "class", also: list | None = None) -> dict:
    """Activate an SAP object — single, OR multiple objects ATOMICALLY (one /activation POST).

    Atomik çoklu-obje aktivasyon (RAP zincirleri): birbirine bağımlı objeler (ör. interface
    DDLS + onun BDEF'i + behavior class) AYNI istekte aktive edilmeli → `also` ile ek objeleri
    ver, hepsi tek POST'ta aktive + doğrulanır (activationExecuted + type=E parse; sahte-OK
    imkansız). bdef/srvd gibi activate_object'in desteklemediği tipler de bu yolda çalışır.

    Args:
        name: Birincil obje adı (Z*/Y*).
        object_type: 'class', 'ddls', 'bdef', 'srvd', 'tabl', ...
        also: Atomik co-activate ek objeler: [{"name": "...", "object_type": "..."}, ...].
              None/boş → tek-obje aktivasyon (klasik yol).

    Returns:
        {ok, name, type, activated, errors?, warnings?, refs?, client_log}

    ⛔ **KLASIK YOLDA AKTIVASYON READBACK'i** (kayit #70, olculmus sahte-OK vakasi — `fugr`).
    Tek-obje klasik aktivasyonda, alt katman "aktive edildi" derse obje **bagimsiz olarak**
    aktive-bekleyen worklist'inde (`/activation/inactiveobjects`) aranir:
      • `activation_verified: true`  → obje listede YOK, aktivasyon dogrulandi.
      • `activation_verified: false` → obje HALA listede ⇒ **SAHTE-OK**: `ok=false`,
        `activated=false`, `error="activation_not_executed"`, `still_inactive=[...]`.
      • `activation_verified: null`  → sonda kosamadi ⇒ iddia **KANITLANMADI** (`warning`).
        Bu "dogrulandi" DEGILDIR.
    ⚠ `also=` (atomik cok-obje) ve `srvb` yollari zaten `activate_and_verify` ile
    `activationExecuted` + `type=E` parse eder; readback onlarda TEKRARLANMAZ.
    """
    try:
        require_writable_tier(get_active_tier(), what=f"{object_type} activate")
        require_customer_namespace(name, what=object_type)
        for o in (also or []):
            require_customer_namespace(o.get("name", ""), what=o.get("object_type", "object"))
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()

    # --- ATOMİK ÇOKLU-OBJE AKTİVASYON (also verildiyse) ---
    if also:
        refs = []
        pairs = [(name, object_type)] + [(o.get("name"), o.get("object_type")) for o in also]
        for n, t in pairs:
            uri = _activation_uri(n, t)
            if not uri:
                return {"ok": False, "error": "unsupported_type",
                        "message": f"Aktivasyon URI çözülemedi: {n} (type={t}). "
                                   f"Desteklenen tipler: {sorted(set(_ACTIVATION_URI_SEG))}"}
            refs.append((uri, n))
        try:
            from create_rap_service import csrf, activate_and_verify  # type: ignore
            adt = getattr(client, "adt_client", None) or client
            with _capture_stdout() as out:
                tok = csrf(adt)
                activate_and_verify(adt, tok, refs)   # activationExecuted!=true / type=E → raises
            resp = {
                "ok": True,
                "name": name,
                "type": object_type,
                "activated": True,
                "refs": [n for _, n in refs],
                "client_log": out.getvalue().strip(),
            }
            # Readback-gate: her aktive edilen source-based obje için içerik doğrula.
            rb_all = {}
            for n, t in pairs:
                rb = _content_readback(client, n, t)
                if rb:
                    rb_all[n.upper()] = rb
                    if rb.get("content_verified") is False:
                        resp["ok"] = False
            if rb_all:
                resp["content_readback"] = rb_all
            return resp
        except Exception as exc:
            return _err_from_exc(exc)

    # --- TEK-OBJE AKTİVASYON ---
    # srvb gibi activate_object'in DESTEKLEMEDİĞİ tipler: kanonik /activation POST
    # (activation-ref, segment _ACTIVATION_URI_SEG'den) yoluyla aktive et — activationExecuted
    # + type=E parse → sahte-OK imkansız (gateway'in elle REST workaround'unu typed yapar,
    # ders 2026-06-22 SRVB). Çalışan/source-tabanlı tipler (class/tabl/...) klasik
    # activate_object yolunda kalır (içerik readback-gate'i korunur, regresyon yok).
    _ref_only = {"srvb", "servicebinding"}
    if (object_type or "").lower().strip() in _ref_only:
        uri = _activation_uri(name, object_type)
        try:
            from create_rap_service import csrf, activate_and_verify  # type: ignore
            adt = getattr(client, "adt_client", None) or client
            with _capture_stdout() as out:
                tok = csrf(adt)
                activate_and_verify(adt, tok, [(uri, name)])   # !=true / type=E → raises
            return {
                "ok": True, "name": name, "type": object_type, "activated": True,
                "refs": [name], "client_log": out.getvalue().strip(),
                "note": "activation-ref yolu (activate_object bu tipi desteklemiyor). "
                        "OData $metadata tazelemek gerekiyorsa ayrıca adt_publish_service çağır.",
            }
        except Exception as exc:
            return _err_from_exc(exc)

    try:
        with _capture_stdout() as out:
            activated = client.activate_object(name, object_type=object_type)
        log_text = out.getvalue()

        # Parse a few signals from client log (best-effort; structured result is already in 'activated')
        errors: list[str] = []
        warnings: list[str] = []
        for line in log_text.splitlines():
            if line.startswith("  - ") and "warning" in log_text.lower():
                warnings.append(line[4:].strip())

        resp = {
            "ok": True,
            "name": name,
            "type": object_type,
            "activated": bool(activated),
            "client_log": log_text.strip(),
        }

        # Readback-gate: aktive edilen source-based obje için AKTİF source'u push edilenle
        # karşılaştır. Fark → yazım tam oturmadı → BLOCKER (ok=False). XML-DDIC/kayıtsız → no-op.
        rb = _content_readback(client, name, object_type)
        if rb:
            resp.update(rb)
            if rb.get("content_verified") is False:
                resp["ok"] = False

        # ⛔ AKTIVASYON READBACK'i (kayit #70 — sahte-OK). `_content_readback` KAYNAK
        # esitligini olcer; bu sonda AKTIVASYON DURUMUNU olcer ve kapsami farklidir
        # (fugr/XML-DDIC + salt re-activate icin TEK dogrulama). Gerekce: `_aktivasyon_readback`.
        # ⚠ Yalniz `activated` TRUE iddiasindayken calisir — zaten "olmadi" diyorsa
        # cakismasi anlamsiz ve fazladan HTTP maliyeti olur.
        if resp.get("activated") is True:
            akt_ok, akt_sonda, akt_kalan = _aktivasyon_readback(client, [name])
            resp["activation_verified"] = akt_ok
            resp["activation_probe"] = akt_sonda
            if akt_ok is False:
                # SAHTE-OK yakalandi: obje HALA aktive-bekleyen worklist'inde.
                resp["ok"] = False
                resp["activated"] = False
                resp["still_inactive"] = akt_kalan
                resp["error"] = "activation_not_executed"
                resp["message"] = (
                    "⛔ SAHTE-OK YAKALANDI: alt katman 'aktive edildi' dedi ama obje HALA "
                    "aktive-bekleyen worklist'inde (%s). Aktivasyon GERCEKLESMEDI — bu "
                    "sonuca dayanip zincirin devamina (publish / bagimli obje / test) GECME. "
                    "Ham yaniti gor: POST /sap/bc/adt/activation -> `activationExecuted`."
                    % ", ".join("%s (%s)" % (h["name"], h["type"]) for h in akt_kalan)
                )
            elif akt_ok is None:
                resp["warning"] = (
                    "Aktivasyon DOGRULANAMADI (sonda: %s) — 'aktive edildi' iddiasi bu "
                    "cagride KANITLANMADI. Kritik zincirde `adt_inactive_objects` ile elle olc."
                    % akt_sonda
                )

        # ADR 0016 REVİZE: post-write REPO SYNC (M2) KALDIRILDI — gereksiz (push edince repo
        # zaten ≈ canlı; tazelik bir sonraki edit'te pull-before-edit hook ile sağlanır).
        return resp
    except Exception as exc:
        return _err_from_exc(exc)


@profil_tool()
def adt_publish_service(name: str, version: str = "0001") -> dict:
    """(Re)publish an OData V2 service binding (SRVB) — refreshes the OData $metadata.

    SRVD expose / underlying CDS değişince, yayınlanmış OData metadata'sının (entity set +
    property) yeni hâli yansıtması için SRVB republish gerekir. Bu, raw `/businessservices/
    odatav2/publishjobs` POST'unun TYPED, guardrailed muadili (raw-Bash classifier bloğunu
    önler). Sonuç doğrulaması = `GET /sap/opu/odata/sap/<NAME>/$metadata` (çağıran yapar).

    Args:
        name: Service binding (SRVB) adı, ör. ZSD001_UI_BOOKING_O2.
        version: Servis sürümü (default '0001').

    Returns:
        {ok, name, status_code, published, body, client_log}
    """
    try:
        require_writable_tier(get_active_tier(), what="service publish")
        require_customer_namespace(name, what="service binding")
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()
    try:
        from create_rap_service import csrf, publish_xml, PUBLISH_V2  # type: ignore
        adt = getattr(client, "adt_client", None) or client
        with _capture_stdout() as out:
            tok = csrf(adt)
            r = adt.session.post(
                adt.url + PUBLISH_V2,
                params={"servicename": name, "serviceversion": version},
                headers={"X-CSRF-Token": tok, "Content-Type": "application/xml",
                         "Accept": "application/xml, application/vnd.sap.as+xml;charset=UTF-8;"
                                   "dataname=com.sap.adt.StatusMessage",
                         "sap-client": "100", "sap-language": "TR"},
                data=publish_xml(name).encode("utf-8"), verify=False, timeout=120,
            )
        published = r.status_code in (200, 201, 202)
        return {
            "ok": published,
            "name": name,
            "status_code": r.status_code,
            "published": published,
            "body": (r.text or "")[:900],
            "client_log": out.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_classrun  (gap-analysis C1 — ABAP çalıştırma kanalı)
# =============================================================================

@profil_tool()
def adt_classrun(name: str) -> dict:
    """Bir IF_OO_ADT_CLASSRUN sınıfını çalıştır (ADT classrun, F9-run muadili).

    ADT-only ABAP execute kanalı. RFC FM (RPY_DYNPRO_INSERT/RS_CUA_*) çağıran generator
    sınıflarını çalıştırmak için (ekran/GUI status üretimi — C1). Kod ÇALIŞTIRIR (yazma
    yapabilir) → ADR 0010 tier guard: yalnızca DEV.

    ⛔ **PUSH+ACTIVATE SONRASI ÇIKTI BAYAT OLABİLİR — TEK BAŞINA KANIT DEĞİLDİR.**
    Ölçülmüş vaka (2026-08-19, `ZCL_SD000_GET_IDOCDATA`): sınıfa `c_docnum = '204075'`
    sabiti eklenip push+activate edildi; `adt_classrun` **HTTP 200 + dolu, akla yatkın**
    çıktı verdi — ama **eski kodun** çıktısı (sabit sanki BOŞ). **İkinci çağrı da aynı bayat
    sonucu** verdi ⇒ tek seferlik aksaklık DEĞİL, tekrarlanabilir. Kaynak tarafı dört
    bağımsız okumayla temiz ölçüldü (`source/main` default = `?version=active` =
    `?version=inactive`, aynı sha, sabit VAR; `adt_inactive_objects` count 0).
    **Kök sebep kaynakta değil, ÇALIŞTIRAN OTURUMDA:** MCP sunucusu tek uzun-ömürlü ABAP
    oturumu kullanır (`sap-contextid` çerezi) ve **sınıf load'u o oturumda bayat kalır;
    aktivasyon onu tazelemez.** Kanıt: TAZE oturumdan (yeni logon, kendi süreç,
    `SAPClient().run_classrun(...)`) aynı sınıf DOĞRU çalıştı.
    ⚠ Bu, *"araç başarısız"* değil **"araç başarılı görünerek yanlış söylüyor"** sınıfıdır —
    `adt_transport_list` sahte-sıfırı ve `adt_post_shell` sahte-400'ü ile aynı raf.

    ✅ **DOĞRU YÖNTEM (ikisinden BİRİ zorunlu):**
      1. **Taze oturumda koştur** — `python -c "...; SAPClient().run_classrun('<AD>')"`
         (ayrı süreç, yeni logon), **veya**
      2. **Çıktıyı kaynakla ÇAPRAZ KONTROL et** — çıktıda yeni koda ÖZGÜ bir imza
         (yeni başlık satırı, yeni sabitin değeri) görünüyor mu? Görünmüyorsa sonucu
         "davranış yanlış" diye RAPORLAMA; önce bayatlığı ele.

    ⚠ Bu tool bugün dönüşünde bayatlık ölçmez (`session_age`/`context_reused` alanı YOK —
    oturum tazeleme/uyarı alanı infra kuyruğunda AÇIK kalemdir). Yani aşağıdaki `Returns`
    sözleşmesinde **tazelik kanıtı yoktur**; kanıtı çağıran üretir.

    Args:
        name: Sınıf (Z*/Y*, if_oo_adt_classrun~main implement etmeli).

    Returns:
        {ok, class, status, output} — output = out->write konsol çıktısı.
        ⚠ `ok: true` çıktının GÜNCEL olduğunu KANITLAMAZ (yukarıdaki bayatlık şerhi).
    """
    try:
        require_writable_tier(get_active_tier(), what="classrun execute")
        require_customer_namespace(name, what="class")
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()
    try:
        with _capture_stdout() as out:
            res = client.run_classrun(name)
        if isinstance(res, dict):
            res.setdefault("client_log", out.getvalue().strip())
        return res
    except Exception as exc:
        return _err_from_exc(exc)
