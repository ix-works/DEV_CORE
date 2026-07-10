#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart hook — yasaklar + protokol enjeksiyonu + SAĞLIK KONTROLLERİ (B9b, ADR 0020).

Statik: ADR 0005 yasak özeti + Ekran-Teyidi zorunluluğu + ADR 0018 çalışma modeli
(compact sonrası da diri kalsın diye her start/resume/compact'ta enjekte edilir).

Dinamik (v3 mimarisi):
  D25 — 4 junction TEK TEK sağlam mı (kopuk agents/skills SESSİZ semptom verir)
  D7  — settings.json + hook_shim.py template-drift'i
  F2  — behavior-manifest diff (kayıtsız/değişmiş davranış dosyası → BÜYÜK uyarı)
  Ö3  — DEV_CORE origin-geride mi (THROTTLE: saatte 1 fetch, 2 sn timeout, cache .tmp/)
  D20b— detached@stable ise sakin bilgi (origin-geride yanlış-alarmı üretme)

Proje kökü: env CLAUDE_PROJECT_DIR → cwd (B9-fix: __file__ junction'la CORE'a çözülür).
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

PROJ = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
CORE = PROJ / "core"


def _write_session_marker(data: dict) -> None:
    """Seans kimliği → .claude/.current_session (pull-before-edit, ADR 0016). Fail-safe."""
    try:
        sid = data.get("session_id")
        if not sid:
            return
        marker = PROJ / ".claude" / ".current_session"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"session_id": sid}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


STATIK = (
    "[session-loader hook]\n"
    "ZORUNLU: Yeni oturumun ILK yaniti CLAUDE.core.md §3 'Ekran Teyidi' formatiyla baslar.\n"
    "ADR 0005 KESIN YASAKLAR (bypass YOK):\n"
    "  A) Z/Y ile baslamayan standart SAP objesine dokunma (yarat/degistir/sil) yasak.\n"
    "  B) Standart tablo verisine direkt INSERT/UPDATE/DELETE/MODIFY yasak "
    "(BAPI->RFC->BDC->manuel sirasi).\n"
    "  C) Transport/package yaratma ve release etme yasak.\n"
    "  D) Z obje = master_language login + 4 alan label TAM o dilde (project.yaml).\n"
    "SAP yazma oncesi run_review.py (ADR 0006). Validator FAIL -> once duzelt (STOP).\n"
    "ARAMA (D29): metodoloji araması DAIMA path=core/ ile — kok-Grep core'u GORMEZ.\n"
    "\n"
    "CALISMA MODELI (ADR 0018 = LAZY/on-demand):\n"
    "  Oturum basinda roster SPAWN ETME. Ihtiyac aninda scoped spawn + bitince kapat.\n"
    "  Roller (.claude/agents/): adt-gateway (TEK SAP yazici; standing) ; frontend-expert ;\n"
    "     backend-expert ; bug-expert (adversarial, read-only, HER ZAMAN taze).\n"
    "  BUG GATE: expert substantive build bitince bug-expert'e -> PASS/WARNING/BLOCKER.\n"
    "  Kullanici 'solo' derse spawn etme. Detay: governance/agent-teams-operating-model.md"
)


def _junction_kontrol() -> list[str]:
    """D25: junction'lar tek tek. OVERLAY'li tipler (claude-local/<tip>) gerçek dizindir."""
    sorun = []
    try:
        sys.path.insert(0, str(CORE / "scripts"))
        from utils import claude_overlay as ov  # type: ignore
        overlayli = {t for t in ov.TIPLER if ov.overlay_var_mi(PROJ, t)}
        for t in overlayli:
            _, s = ov.durum(PROJ, CORE, t)
            sorun.extend(f"overlay {x}" for x in s if "GÜNCELLENDİ" not in x)
    except Exception:
        overlayli = set()

    plan = [("core", CORE)]
    plan += [(f".claude/{t}", PROJ / ".claude" / t)
             for t in ("agents", "skills", "commands") if t not in overlayli]
    for ad, p in plan:
        try:
            hedef = os.readlink(p)
        except (OSError, ValueError):
            hedef = None
        if not p.exists() or (hedef is None and not (p / ".").exists()):
            sorun.append(f"junction KOPUK/YOK: {ad} → onarim: python core/scripts/team_setup.py --repair-junctions")
        elif hedef is None:
            sorun.append(f"{ad} junction DEGIL gercek klasor — sizinti riski, elle incele")
    return sorun


def _yorumsuz(nesne):
    """`_comment*` anahtarlarını özyinelemeli at — JSON'da yorum yoktur, bunlar insan notudur."""
    if isinstance(nesne, dict):
        return {k: _yorumsuz(v) for k, v in nesne.items() if not k.startswith("_comment")}
    if isinstance(nesne, list):
        return [_yorumsuz(x) for x in nesne]
    return nesne


def _anlamli_imza(p: Path) -> str:
    """DAVRANIŞSAL imza: JSON'da yorum anahtarları, metinde CRLF/son-boşluk sayılmaz.

    2026-07-10: bu fonksiyon ham `_sha16` idi. TD'nin settings.json'u template'le
    kablolama olarak BİREBİR aynıyken, tek bir `_comment_yorumlar` anahtarı yüzünden
    her oturum "SAPMIS (D7)" diye bağırıyordu. Yanlış-pozitif üreten uyarı, uyarıya
    karşı bağışıklık yaratır — gerçek drift geldiğinde görülmez. Kapsam kaybı yok:
    atılan alanların ikisi de (yorum, satır-sonu) davranış taşımaz.
    """
    try:
        ham = p.read_bytes()
        if p.suffix == ".json":
            veri = _yorumsuz(json.loads(ham.decode("utf-8")))
            norm = json.dumps(veri, sort_keys=True, ensure_ascii=False).encode("utf-8")
        else:
            norm = ham.replace(b"\r\n", b"\n").strip()
        return hashlib.sha256(norm).hexdigest()[:16]
    except Exception:
        return "?"


def _drift_kontrol() -> list[str]:
    """D7: settings.json + hook_shim template'lerin gerisinde mi (davranışsal imza)."""
    sorun = []
    ciftler = [
        (PROJ / ".claude" / "settings.json", CORE / "claude" / "settings.template.json", "settings.json"),
        (PROJ / "scripts" / "hook_shim.py", CORE / "claude" / "hook_shim.template.py", "hook_shim.py"),
    ]
    for yerel, tpl, ad in ciftler:
        if not yerel.exists():
            sorun.append(f"{ad} YOK — team_setup ile uret")
            continue
        if not tpl.exists():
            continue
        y, t = _anlamli_imza(yerel), _anlamli_imza(tpl)
        if "?" in (y, t):
            sorun.append(f"{ad} OKUNAMADI/BOZUK — imza cikarilamadi (sessiz gecme)")
        elif y != t:
            sorun.append(f"{ad} template'ten SAPMIS (D7) — bilinçliyse manifest'e isle; degilse: "
                         f"template'ten yenile (fark: core/claude/{tpl.name} ile diff'le)")
    return sorun


def _yasaklar_kontrol() -> list[str]:
    """KESİN YASAKLAR fiziksel damgası kök CLAUDE.md'de var + kanonikle eş mi?
    (Damga junction'dan bağımsız güvence; bu kontrol junction sağlamken eşliği doğrular.)"""
    if not (PROJ / "project.yaml").exists() or not (PROJ / "CLAUDE.md").exists():
        return []
    try:
        sys.path.insert(0, str(PROJ / "core" / "scripts"))
        from utils import yasaklar_stamp  # type: ignore
        core = PROJ / "core"
        if not yasaklar_stamp.canonical_path(core).exists():
            return []
        ok, mesaj = yasaklar_stamp.check((PROJ / "CLAUDE.md").read_text(encoding="utf-8"), core)
        return [] if ok else [mesaj]
    except Exception as e:
        return [f"yasaklar-damga kontrolu calismadi: {e}"]


def _manifest_kontrol() -> list[str]:
    """F2: behavior-manifest diff (core'daki modülü yükle)."""
    try:
        sys.path.insert(0, str(CORE / "scripts"))
        import behavior_manifest  # type: ignore
        return behavior_manifest.verify_quiet(PROJ)
    except Exception as e:
        return [f"manifest kontrolu calismadi: {e}"]


def _origin_kontrol() -> list[str]:
    """Ö3+D20b: DEV_CORE origin-geride mi. THROTTLE: saatte 1 fetch (cache .tmp/),
    fetch timeout 2 sn; aradaki oturumlar cache'lenmiş sonucu gösterir."""
    out = []
    core_git = CORE / ".git"
    if not core_git.exists():
        return []
    # D20b: detached@stable sakin bilgi
    try:
        r = subprocess.run(["git", "-C", str(CORE), "symbolic-ref", "-q", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            out.append("core DETACHED HEAD'de (muhtemelen stable-rollback) — normal is icin: "
                       "git -C core switch main  (D20b; bu bir hata degil)")
            return out
    except Exception:
        pass
    cache = PROJ / ".tmp" / ".core_fetch_cache.json"
    simdi = time.time()
    durum = {}
    try:
        durum = json.loads(cache.read_text(encoding="utf-8"))
    except Exception:
        pass
    if simdi - float(durum.get("ts", 0)) > 3600:  # saatte 1
        try:
            subprocess.run(["git", "-C", str(CORE), "fetch", "--quiet", "origin", "main"],
                           capture_output=True, timeout=2)
        except Exception:
            pass  # ağ yok/yavaş → sessiz; cache'e yine de zaman yaz
        try:
            r = subprocess.run(["git", "-C", str(CORE), "rev-list", "--count", "HEAD..origin/main"],
                               capture_output=True, text=True, timeout=5)
            durum = {"ts": simdi, "behind": int((r.stdout or "0").strip() or 0)}
        except Exception:
            durum = {"ts": simdi, "behind": 0}
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(durum), encoding="utf-8")
        except Exception:
            pass
    behind = int(durum.get("behind", 0))
    if behind > 0:
        out.append(f"DEV_CORE origin'in {behind} commit GERISINDE — `git -C core pull` onerilir")
    return out


def _inspector() -> list[str]:
    """Inspector v1 (rapor-only): davranış katmanı GERÇEKTEN canlı mı?

    ⚠ Bu çağrı oturum açılışını ASLA bozamaz. Inspector çöker/yavaşlarsa sessizce atlanır —
    bir denetim aracı, denetlediği sistemi düşüremez. Geçerse tamamen SESSİZDİR
    (yanlış-pozitif üreten uyarı, uyarıya karşı bağışıklık yaratır — D7 dersi).
    """
    try:
        import importlib.util
        yol = CORE / "scripts" / "inspector.py"
        if not yol.is_file():
            return []
        spec = importlib.util.spec_from_file_location("_inspector", yol)
        if spec is None or spec.loader is None:
            return []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        bulgular, istat = mod.denetle(PROJ, CORE)
        if not bulgular:
            return []
        mod.rapor_yaz(PROJ, bulgular, istat)  # "detay şurada" dediğimiz dosya GERÇEKTEN yazılsın
        satirlar = [str(b).replace("\n", " ") for b in bulgular[:5]]
        if len(bulgular) > 5:
            satirlar.append(f"… +{len(bulgular) - 5} bulgu daha")
        satirlar.append(f"(negatif-testli gate: {istat['negatif_testli_gate']}/{istat['gate_toplam']} — v2 bekliyor)")
        satirlar.append("detay: .tmp/inspector-report.md · elle: python core/scripts/inspector.py")
        return satirlar
    except Exception:
        return []


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    _write_session_marker(data if isinstance(data, dict) else {})

    saglik: list[str] = []
    junctions = _junction_kontrol()
    if junctions:
        saglik += ["⛔ " + s for s in junctions]
        saglik.append("⛔ JUNCTION SORUNU VARKEN SAP-YAZMA YAPMA (guardrail eksik olabilir).")
    else:
        for s in _yasaklar_kontrol():
            saglik.append("⛔ KESİN YASAKLAR DAMGASI: " + s)
        for s in _drift_kontrol():
            saglik.append("⚠ " + s)
        for s in _manifest_kontrol():
            saglik.append("⛔ DAVRANIS-YUZEYI (F2): " + s)
        for s in _origin_kontrol():
            saglik.append("⚠ " + s)
        for s in _inspector():
            saglik.append("⚠ INSPECTOR: " + s)
    govde = STATIK
    if saglik:
        govde += "\n\n[SAGLIK KONTROLLERI — session_start]\n" + "\n".join(saglik)
        if any(x.startswith("⛔ DAVRANIS") for x in saglik):
            govde += ("\nKURAL: manifest-onaysiz davranis dosyasi varken bu oturumun "
                      "ciktisina GUVENME — lider'e bildir; gerekirse --safe-mode ile ac.")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": govde}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
