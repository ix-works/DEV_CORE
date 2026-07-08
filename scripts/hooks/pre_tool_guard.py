#!/usr/bin/env python3
"""PreToolUse (matcher: Bash|mcp__sap-adt__*) — 2 katman guard.

1) ADR 0005-C: transport/package YARATMA ve TR RELEASE etme yasak (Bash/script dahil).
2) ADR 0010 BAGLANTI TUTARSIZLIGI: MCP'nin canli bagli oldugu sistem (.mcp_active_system)
   ile .conn_adt ayrisirsa (switch_tier yapildi ama /mcp restart edilmedi), TUM
   mcp__sap-adt__* islemleri REDDEDILIR — cunku MCP istegi eski sisteme gonderir ama
   tier guard yeni sistemi okur (ornek: write DEV der ama ECC QA'ya gider). Bash MUAF
   (script'ler her calismada taze .conn_adt okur → tutarsizlik olamaz). ping MUAF.

Tehlikeli/tutarsiz degilse sessiz (exit 0). Blokta exit 2 (stderr → Claude'a geri besler).
"""
import io
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

if sys.platform == "win32" and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# SADECE gerçek release/create-transport ENDPOINT/komut/FM token'ları.
# Prose-greedy (.*) desen YOK — git commit mesajı/grep/echo gibi metinleri yanlış
# bloklamamak için yalnızca normal yazıda geçmeyecek somut sinyaller (false-positive fix).
_DANGER = re.compile(
    r"(newreleasejobs"                       # ADT transport release endpoint segmenti
    r"|\breleaseTransport\b"                  # tool/fonksiyon adı
    r"|\bcreateTransport\b"
    r"|\btrint_release_request\b"             # release FM
    r"|\btr_release_request\b"
    r"|\bSCC1\b"                              # client copy by request (riskli)
    r"|/cts/transportrequests/\S+/newreleasejobs)",
    re.IGNORECASE,
)


# App-içi `npm install/ci/add` (npm run DEĞİL) — paket-seviye ui/ workspace ihlali (standards/03).
_NPM_INSTALL = re.compile(r"\bnpm\s+(?:install|ci|add|i)\b", re.IGNORECASE)

# Yalın `fiori deploy` — build YAPMAZ, eski dist'i yükler + "Successful" yalanı söyler
# (2026-07-06 stale-dist dersi). Kanonik yol scripts/deploy_ui.py (build+deploy+canlı-doğrulama).
# deploy_ui.py'nin kendi `npx fiori deploy` çağrısı Python subprocess'te → Bash tool'a görünmez (muaf).
_FIORI_DEPLOY = re.compile(r"\bfiori\s+deploy\b", re.IGNORECASE)


def _ui_app_subdir(path: str):
    """path bir UI app alt-dizini mi (`.../ui/<app>`, ui/ workspace kökü DEĞİL)?

    Dönüş: (ui_root, app) veya None. ui/ kökü `package.json` içinde 'workspaces' içeriyorsa
    onaylar (workspace olmayan repo'da false-positive yok). FS kontrolü yalnız npm-install
    görülünce çalışır (nadir) → sıcak-yol maliyeti yok."""
    if not path:
        return None
    p = path.replace("\\", "/")
    m = re.search(r"(.*/ui)/([^/]+)", p)
    if not m:
        return None
    ui_root, app = m.group(1), m.group(2).strip()
    if not app or app in (".", ".."):
        return None
    root = Path(__file__).resolve().parents[2]
    ui_path = Path(ui_root) if Path(ui_root).is_absolute() else (root / ui_root)
    pkg = ui_path / "package.json"
    try:
        if pkg.exists() and "workspaces" in pkg.read_text(encoding="utf-8", errors="ignore"):
            return (ui_root, app)
    except Exception:
        return None
    return None


def _host(url: str) -> str:
    if not url:
        return ""
    return (urlparse(url if "://" in url else "https://" + url).hostname or "").lower()


def _conn_field(text: str, key: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(key) and "=" in s:
            return s.split("=", 1)[1].strip()
    return ""


def _binding_mismatch() -> tuple:
    """(.conn_adt) ile (MCP'nin canli baglantisi=.mcp_active_system) ayrisik mi?

    Donus: (mismatch: bool, conn_label, mcp_label). Kanit yoksa (False, '', '')."""
    root = Path(__file__).resolve().parents[2]
    conn = root / ".conn_adt"
    state = root / ".claude" / ".mcp_active_system"
    if not conn.exists() or not state.exists():
        return (False, "", "")  # kanit yok → bloklamA
    try:
        ct = conn.read_text(encoding="utf-8", errors="ignore")
        cur_url, cur_cl = _conn_field(ct, "ADT_SAP_URL"), _conn_field(ct, "ADT_SAP_CLIENT")
        cur_sys = _conn_field(ct, "ADT_SAP_SYSTEM_NAME")
        st = json.loads(state.read_text(encoding="utf-8"))
        mcp_url, mcp_cl = st.get("url") or "", str(st.get("client") or "")
        mcp_sys = st.get("system") or ""
    except Exception:
        return (False, "", "")
    ch, mh = _host(cur_url), _host(mcp_url)
    differ = (bool(ch) and bool(mh) and ch != mh) or (bool(cur_cl) and bool(mcp_cl) and str(cur_cl) != mcp_cl)
    conn_label = cur_sys or ch or "?"
    mcp_label = mcp_sys or mh or "?"
    return (differ, conn_label, mcp_label)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    tool_name = data.get("tool_name", "") or ""
    # ADR 0010 — baglanti tutarsizligi gate: MCP eski sisteme bagliyken hicbir ADT islemi yapma.
    if tool_name.startswith("mcp__sap-adt__") and tool_name != "mcp__sap-adt__ping":
        mismatch, conn_label, mcp_label = _binding_mismatch()
        if mismatch:
            sys.stderr.write(
                "⛔ BAĞLANTI TUTARSIZLIĞI (PreToolUse guard, ADR 0010): "
                f".conn_adt artık '{conn_label}' sistemini işaret ediyor ama MCP hâlâ "
                f"'{mcp_label}' sistemine BAĞLI (switch_tier yapıldı, /mcp restart EDİLMEDİ). "
                "Bu durumda ADT isteği YANLIŞ sisteme gider (tier guard'ın okuduğu sistemle "
                "fiili hedef ayrışır → tehlikeli). İŞLEM REDDEDİLDİ. "
                "DUR → kullanıcıya bildir → kullanıcı '/mcp' ile yeniden bağlansın → tekrar dene.\n"
            )
            return 2  # blokla

    ti = data.get("tool_input", {}) or {}
    # Bash komutu veya MCP tool argümanları içinde ara
    hay = ""
    if isinstance(ti, dict):
        hay = ti.get("command", "") or json.dumps(ti, ensure_ascii=False)
    else:
        hay = str(ti)

    if _DANGER.search(hay):
        sys.stderr.write(
            "⛔ ADR 0005-C İHLALİ (PreToolUse guard): transport release/create veya "
            "package create teşebbüsü tespit edildi. Bu YASAK — transport'u kullanıcı "
            "release eder, yeni transport/package yaratılmaz. DUR → kullanıcıya bildir.\n"
        )
        return 2  # blokla

    # INLINE AKTİVASYON guard (2026-06-11 dersi / adt-rap §34-D): Bash içinde elle
    # '/sap/bc/adt/activation' POST'u activationExecuted'ı parse ETMEZ → HTTP 200 sahte-OK
    # üretir (metadata eski kalır, saatler kayboldu). Helper'a zorla.
    if (tool_name == "Bash" and "adt/activation" in hay and ".post(" in hay
            and "activate_and_verify" not in hay and "_activation_failures" not in hay):
        sys.stderr.write(
            "⛔ INLINE AKTİVASYON (PreToolUse guard, 2026-06-11 dersi / adt-rap §34-D): "
            "Bash içinde elle '/sap/bc/adt/activation' POST'u tespit edildi. Bu yol "
            "activationExecuted'ı PARSE ETMEZ → HTTP 200 SAHTE-OK üretir (metadata eski kalır). "
            "Bunun yerine create_rap_service.activate_and_verify(client, tok, refs) KULLAN — "
            "activationExecuted!=true VEYA type=E varsa exception fırlatır (sahte-OK imkansiz). "
            "İŞLEM REDDEDİLDİ.\n"
        )
        return 2  # blokla

    # YALIN FIORI DEPLOY guard (2026-07-06 stale-dist dersi): build'siz `fiori deploy` eski
    # dist'i yükler + "Deployment Successful" der ama canlıya bayat gider. Kanonik yol
    # scripts/deploy_ui.py (build ZORUNLU + deploy + canlı Component-preload==dist doğrulaması).
    if tool_name == "Bash" and _FIORI_DEPLOY.search(hay) and "deploy_ui.py" not in hay:
        sys.stderr.write(
            "⛔ YALIN FIORI DEPLOY (PreToolUse guard, 2026-07-06 stale-dist dersi): "
            "Doğrudan 'fiori deploy' BUILD YAPMAZ — eski dist/'i archive edip 'Deployment "
            "Successful' DER ama canlıya BAYAT içerik gider (3 tur sessiz stale, kullanıcı "
            "yakaladı). Bunun yerine KANONİK yolu kullan: "
            "`python scripts/deploy_ui.py --apps <app1,app2>` (build ZORUNLU + deploy + "
            "canlı Component-preload==dist HASH doğrulaması; 'Successful' yalanını yakalar). "
            "İŞLEM REDDEDİLDİ. Bkz. standards/03 §2.4.1 + feedback_ui-deploy-noninteractive madde 8.\n"
        )
        return 2  # blokla

    # APP-İÇİ NPM INSTALL guard (standards/03 §; paket-seviye ui/ npm workspace):
    # app dizininde `npm install/ci/add` YASAK → tooling ui/node_modules'a hoist'lu.
    # Sıcak-yol: npm-install içermeyen Bash'te _NPM_INSTALL.search anında fail (FS'ye dokunmaz).
    if tool_name == "Bash" and _NPM_INSTALL.search(hay):
        cdm = re.search(r"\bcd\s+(?:\"([^\"]+)\"|'([^']+)'|([^\s&|;]+))", hay)
        cd_target = next((g for g in (cdm.groups() if cdm else ()) if g), "") if cdm else ""
        hit = _ui_app_subdir(cd_target) or _ui_app_subdir(data.get("cwd", "") or "")
        if hit:
            ui_root, app = hit
            sys.stderr.write(
                f"⛔ APP-İÇİ NPM INSTALL (PreToolUse guard, standards/03): '{app}' app "
                f"dizininde npm install/ci/add YASAK — '{ui_root}' paket-seviye npm workspace "
                "kökü, tooling zaten ui/node_modules'a hoist'lu. Lokal çalıştırmak için KURULUM "
                "GEREKMEZ: app dizininden `npm run start-noflp` (canlı backend) / `start-mock`. "
                f"Bağımlılık eklemen gerekiyorsa `cd {ui_root} && npm install` (workspace kökü). "
                "İŞLEM REDDEDİLDİ.\n"
            )
            return 2  # blokla
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
