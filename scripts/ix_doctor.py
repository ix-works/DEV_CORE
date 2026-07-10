#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ix_doctor.py — geçiş-sonrası KURULUM sağlık taraması (F2; sap_doctor'un kardeşi).

sap_doctor "SAP bağlantısı sağlıklı mı?" sorusuna bakar; ix_doctor "canlı-çekirdek
kurulumu (junction + git + GitHub-enforce + Claude-katmanı + MCP + validator +
iş-akışı) uçtan uca sağlıklı mı?" sorusuna bakar. 7 katman, her kontrol kanıt-satırı
basar; katman durumu = kontrollerin en kötüsü (FAIL > WARN > PASS).

Katmanlar (GECIS-EXEC-CHECKLIST BLOK F / F2.1–F2.7):
  1. FS+BAĞIMLILIK : 4 junction → gerçek core'a çözülüyor · managed-policy ·
                     plugin envanteri (setup_plugins --list) · CLI mevcudiyeti
  2. GIT           : remote org tutarlı · main==origin/main · stable tag ·
                     hooksPath · global baseline · working-tree temizliği
  3. GITHUB-ENFORCE: ruleset ACTIVE · CI yeşil · repo tree'de core-sızıntısı yok
                     (gh CLI yoksa katman SKIP+WARN)
  4. CLAUDE        : settings/shim template-drift (D7) · SHIM_SURUM · behavior-
                     manifest ↔ ağaç (F2) · hook smoke (örnek-stdin) ·
                     freeze-guard CANLI test (stdin-simülasyon, gerçek yazma YOK)
  5. MCP/SAP       : .conn_adt var+placeholder'sız · MCP server dosyaları
                     junction'dan erişilebilir · (--live-sap ile) canlı probe
  6. VALIDATORS+PERF: run_all_validators TAM PASS + süre · session_start <1.5sn
  7. İŞ-AKIŞI SMOKE: memory (MEMORY.md dolu) · deploy-zinciri import-sağlığı ·
                     aktif paket .rules.md

Kullanım (PROJE kökünden):
    python core/scripts/ix_doctor.py                # tam tarama (ağ denemesi yok*)
    python core/scripts/ix_doctor.py --layer 4      # tek katman
    python core/scripts/ix_doctor.py --live-sap     # katman 5'te canlı SAP probe
    python core/scripts/ix_doctor.py --json         # makine-okur özet
    (* katman 2 git-fetch + katman 3 gh-api kısa timeout'lu ağ kullanır; SAP'ye
       default'ta ASLA çıkılmaz.)

Exit: 0 = FAIL yok · 1 = en az bir FAIL.
Proje kökü: utils/project_config.project_root() (env CLAUDE_PROJECT_DIR → cwd; D24 —
__file__ junction üzerinden CORE'a çözülür, PROJE kökü için ASLA kullanılmaz).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# CORE kökü: bu dosya core-içi varlık → __file__ MEŞRU (D24 istisnası; proje kökü DEĞİL)
CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT / "scripts"))
from utils.project_config import project_root, cfg  # noqa: E402

PROJ = project_root()
PASS, WARN, FAIL, SKIP = "PASS", "WARN", "FAIL", "SKIP"
_TAG = {PASS: "[PASS]", WARN: "[WARN]", FAIL: "[FAIL]", SKIP: "[skip]"}

Sonuc = tuple  # (tag, mesaj)


# ---------------------------------------------------------------- yardımcılar

def _run(args: list[str], cwd: Path | None = None, stdin_text: str | None = None,
         timeout: int = 120, env: dict | None = None) -> tuple[int, str]:
    """Subprocess koş → (rc, stdout+stderr). Hata/timeout'ta rc=-1."""
    try:
        r = subprocess.run(args, cwd=str(cwd) if cwd else None, input=stdin_text,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=env)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, f"TIMEOUT ({timeout}s)"
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def _hook_env() -> dict:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(PROJ)
    return env


def _git(repo: Path, *args: str, timeout: int = 15) -> tuple[int, str]:
    return _run(["git", "-C", str(repo), *args], timeout=timeout)


def _sha16(p: Path) -> str:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except Exception:
        return "?"


def _readlink(p: Path) -> Path | None:
    """Junction/symlink hedefi (\\\\?\\ öneki soyulur — team_setup ile aynı desen)."""
    try:
        ham = str(os.readlink(p))
        if ham.startswith("\\\\?\\"):
            ham = ham[4:]
        return Path(ham)
    except (OSError, ValueError):
        return None


def _remote_org_repo(repo: Path) -> tuple[str, str]:
    """origin URL'sinden (org, repo) çıkar; yoksa ('','')."""
    rc, out = _git(repo, "remote", "get-url", "origin")
    if rc != 0:
        return "", ""
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?\s*$", out.strip())
    return (m.group(1), m.group(2)) if m else ("", "")


def _yaml_list(key: str) -> list[str]:
    v = cfg(key)
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v else []
    return [str(x) for x in v]


# ---------------------------------------------------------------- katman 1

def katman1() -> list[Sonuc]:
    r: list[Sonuc] = []

    # 1a — junction'lar: var + gerçek core'a çözülüyor (team_setup planıyla birebir).
    #      OVERLAY (2026-07-09): `claude-local/<tip>` varsa o tip junction DEĞİL gerçek
    #      dizindir (core + proje override) — bu bir sızıntı değil, tasarım. Ayrıca
    #      güncelliği denetlenir. Detay: utils/claude_overlay.py
    sys.path.insert(0, str(CORE_ROOT / "scripts"))
    from utils import claude_overlay as _ov  # type: ignore

    plan = [("core", PROJ / "core", CORE_ROOT)]
    for _tip in _ov.TIPLER:
        if _ov.overlay_var_mi(PROJ, _tip):
            mod, sorunlar = _ov.durum(PROJ, CORE_ROOT, _tip)
            if sorunlar:
                for s in sorunlar:
                    r.append((WARN if "GÜNCELLENDİ" in s else FAIL, f"overlay {s}"))
            else:
                r.append((PASS, f"overlay .claude/{_tip}: güncel (core + proje override)"))
        else:
            plan.append((f".claude/{_tip}", PROJ / ".claude" / _tip,
                         CORE_ROOT / "claude" / _tip))

    for ad, link, hedef in plan:
        if not link.exists():
            r.append((FAIL, f"junction YOK: {ad} — onarım: python core/scripts/team_setup.py --repair-junctions"))
            continue
        m = _readlink(link)
        if m is None:
            r.append((FAIL, f"{ad} junction DEĞİL gerçek klasör — sızıntı riski, elle incele"))
        elif m.resolve() != hedef.resolve():
            r.append((FAIL, f"junction YANLIŞ hedefe: {ad} → {m} (beklenen: {hedef})"))
        else:
            r.append((PASS, f"junction sağlam: {ad} → {hedef}"))

    # 1b — managed-policy (D33): var + şablonla eş (placeholder DOLU)
    tpl = CORE_ROOT / "claude" / "managed-policy.template.json"
    mp = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "ClaudeCode" / "managed-settings.json"
    if not mp.exists():
        r.append((WARN, f"managed-policy YOK: {mp} — kurulum (admin): şablonu doldur+kopyala → "
                        f"core/claude/{tpl.name} (placeholder'ları makinedeki dondurulmuş kökle değiştir)"))
    else:
        try:
            metin = mp.read_text(encoding="utf-8")
            veri = json.loads(metin)
            deny = (veri.get("permissions") or {}).get("deny") or []
            if "<ESKI_KOK>" in metin:
                r.append((FAIL, f"managed-policy placeholder DOLDURULMAMIŞ (<ESKI_KOK>): {mp}"))
            elif not deny:
                r.append((WARN, f"managed-policy'de permissions.deny BOŞ — şablonla eş değil: {mp}"))
            else:
                eksik = [p for p in ("Write(", "Edit(", "Bash(") if not any(d.startswith(p) for d in deny)]
                if eksik:
                    r.append((WARN, f"managed-policy şablondan eksik deny sınıfı: {', '.join(eksik)} ({mp})"))
                else:
                    r.append((PASS, f"managed-policy mevcut + placeholder'sız ({len(deny)} deny kuralı): {mp}"))
        except Exception as e:
            r.append((WARN, f"managed-policy OKUNAMADI ({e}): {mp}"))

    # 1c — plugin envanteri (setup_plugins --list; claude CLI ister)
    sp = CORE_ROOT / "scripts" / "setup_plugins.py"
    rc, out = _run([sys.executable, str(sp), "--list"], cwd=PROJ, timeout=120)
    if rc != 0:
        r.append((WARN, f"setup_plugins --list koşamadı (exit {rc}) — {out.strip().splitlines()[-1][:100] if out.strip() else 'çıktı yok'}"))
    else:
        eksikler = [ln.strip() for ln in out.splitlines() if "✗" in ln]
        if eksikler:
            r.append((WARN, f"eksik plugin ({len(eksikler)}): "
                            + "; ".join(e.split("—")[0].replace("✗ EKSİK", "").strip() for e in eksikler)
                            + " — kur: python core/scripts/setup_plugins.py"))
        else:
            r.append((PASS, "plugin envanteri temiz (setup_plugins --list: eksik yok)"))

    # 1d — CLI mevcudiyeti (yalnız shutil.which; sürüm-çağrısı YOK)
    for ad, kur in (("node", "Node.js LTS kur → https://nodejs.org"),
                    ("npm", "Node.js LTS ile gelir → https://nodejs.org"),
                    ("claude", "npm install -g @anthropic-ai/claude-code")):
        yol = shutil.which(ad)
        r.append((PASS, f"CLI mevcut: {ad} ({yol})") if yol
                 else (FAIL, f"CLI YOK: {ad} — kurulum: {kur}"))
    for ad, kur in (("playwright-cli", "npm install -g @playwright/cli"),
                    ("ast-grep", "npm install -g @ast-grep/cli"),
                    ("mmdc", "npm install -g @mermaid-js/mermaid-cli"),
                    ("marp", "npm install -g @marp-team/marp-cli")):
        yol = shutil.which(ad)
        r.append((PASS, f"CLI mevcut (opsiyonel): {ad}") if yol
                 else (WARN, f"opsiyonel CLI yok: {ad} — kurulum: {kur}"))
    return r


# ---------------------------------------------------------------- katman 2

def _repo_git_kontrol(etiket: str, repo: Path, beklenen_org: str) -> list[Sonuc]:
    r: list[Sonuc] = []
    org, ad = _remote_org_repo(repo)
    if not org:
        r.append((FAIL, f"{etiket}: origin remote YOK/çözülemedi ({repo})"))
        return r
    if beklenen_org and org != beklenen_org:
        r.append((FAIL, f"{etiket}: remote org '{org}' ≠ beklenen '{beklenen_org}' ({org}/{ad})"))
    else:
        r.append((PASS, f"{etiket}: remote = {org}/{ad}"))

    # main == origin/main (kısa fetch; ağ yoksa yerel ref'lerle kıyas notu)
    frc, _ = _git(repo, "fetch", "--quiet", "origin", "main", timeout=10)
    rc1, yerel = _git(repo, "rev-parse", "refs/heads/main")
    rc2, uzak = _git(repo, "rev-parse", "refs/remotes/origin/main")
    if rc1 != 0 or rc2 != 0:
        r.append((FAIL, f"{etiket}: main/origin-main ref çözülemedi (main yok mu?)"))
    elif yerel.strip() == uzak.strip():
        taze = "" if frc == 0 else " (fetch başarısız — yerel ref'lerle kıyas)"
        r.append((PASS, f"{etiket}: main == origin/main ({yerel.strip()[:12]}){taze}"))
    else:
        _, sayi = _git(repo, "rev-list", "--left-right", "--count", "refs/heads/main...refs/remotes/origin/main")
        r.append((FAIL, f"{etiket}: main ≠ origin/main (ileri...geri = {sayi.strip() or '?'})"))

    # working tree temiz mi (kirli = WARN, FAIL değil)
    _, st = _git(repo, "status", "--porcelain")
    kirli = [ln for ln in st.splitlines() if ln.strip()]
    r.append((PASS, f"{etiket}: working tree temiz") if not kirli
             else (WARN, f"{etiket}: working tree KİRLİ ({len(kirli)} kalem; ilk: {kirli[0].strip()[:60]})"))
    return r


def katman2() -> list[Sonuc]:
    r: list[Sonuc] = []
    # Beklenen org: project.yaml `github_org` → yoksa PROJE remote'undan türet (hardcode YOK)
    beklenen_org = str(cfg("github_org") or "") or _remote_org_repo(PROJ)[0]
    if beklenen_org:
        r.append((PASS, f"beklenen GitHub org (remote-deseninden): {beklenen_org}"))
    else:
        r.append((WARN, "beklenen org türetilemedi (proje remote'u yok + project.yaml github_org yok)"))

    r += _repo_git_kontrol("proje", PROJ, beklenen_org)
    r += _repo_git_kontrol("core", CORE_ROOT, beklenen_org)

    # stable tag (core rollback çapası — D20b)
    rc, out = _git(CORE_ROOT, "rev-parse", "--short", "refs/tags/stable")
    r.append((PASS, f"core stable tag mevcut → {out.strip()}") if rc == 0
             else (FAIL, "core'da 'stable' tag YOK — rollback çapası eksik (MAINTENANCE.md)"))

    # hooksPath (D19)
    rc, out = _git(CORE_ROOT, "config", "core.hooksPath")
    if rc == 0 and out.strip() == "scripts/git-hooks":
        r.append((PASS, "core hooksPath = scripts/git-hooks"))
    else:
        r.append((FAIL, f"core hooksPath set DEĞİL (mevcut: '{out.strip() or '-'}') — "
                        "düzelt: git -C core config core.hooksPath scripts/git-hooks"))

    # global git baseline
    for anahtar, beklenen, fix in (
            ("core.autocrlf", "false", "git config --global core.autocrlf false"),
            ("init.defaultBranch", "main", "git config --global init.defaultBranch main"),
            ("core.longpaths", "true", "git config --global core.longpaths true")):
        rc, out = _run(["git", "config", "--global", "--get", anahtar], timeout=10)
        deger = out.strip()
        if rc == 0 and deger.lower() == beklenen:
            r.append((PASS, f"global {anahtar} = {beklenen}"))
        else:
            r.append((WARN, f"global {anahtar} = '{deger or '-'}' (beklenen {beklenen}) — düzelt: {fix}"))
    return r


# ---------------------------------------------------------------- katman 3

def katman3() -> list[Sonuc]:
    r: list[Sonuc] = []
    gh = shutil.which("gh")
    if not gh:
        return [(SKIP, "gh CLI yok — GitHub-enforce katmanı atlandı"),
                (WARN, "gh CLI kur (https://cli.github.com) + `gh auth login` → bu katman koşulabilsin")]
    org, repo = _remote_org_repo(PROJ)
    if not org:
        return [(WARN, "proje remote'u çözülemedi — gh kontrolleri atlandı")]
    tam = f"{org}/{repo}"

    # 3a — ruleset'ler ACTIVE
    rc, out = _run([gh, "api", f"repos/{tam}/rulesets"], timeout=30)
    if rc != 0:
        r.append((WARN, f"ruleset API okunamadı ({tam}): {out.strip().splitlines()[0][:100] if out.strip() else '?'}"))
    else:
        try:
            rs = json.loads(out)
            aktif = [x.get("name", "?") for x in rs if x.get("enforcement") == "active"]
            r.append((PASS, f"aktif ruleset ({len(aktif)}): {', '.join(aktif)}") if aktif
                     else (FAIL, f"{tam}: hiç ACTIVE ruleset yok ({len(rs)} kayıt)"))
        except Exception as e:
            r.append((WARN, f"ruleset yanıtı parse edilemedi: {e}"))

    # 3b — CI yeşil: required-check yüzeyi = son pull_request-event koşusu (ruleset PR'ı
    #      gate'ler); PR koşusu hiç yoksa son koşu neyse o. Son genel koşu ayrıca kırmızıysa
    #      (örn. kasıtlı-kirli test branch'i) WARN olarak raporlanır — sağlık FAIL'i değil.
    rc, out = _run([gh, "api", f"repos/{tam}/actions/runs?per_page=10"], timeout=30)
    if rc != 0:
        r.append((WARN, f"CI runs API okunamadı ({tam})"))
    else:
        try:
            runs = json.loads(out).get("workflow_runs") or []
            if not runs:
                r.append((WARN, f"{tam}: hiç CI koşusu yok"))
            else:
                secili = next((x for x in runs if x.get("event") == "pull_request"), runs[0])
                sonuc = secili.get("conclusion")
                mesaj = (f"CI ({secili.get('event','?')}-koşusu): {secili.get('name','?')} "
                         f"@{secili.get('head_branch') or '?'} → {sonuc or secili.get('status')}")
                r.append((PASS, mesaj) if sonuc == "success" else (FAIL, mesaj))
                son = runs[0]
                if son is not secili and son.get("conclusion") not in (None, "success"):
                    r.append((WARN, f"son genel CI koşusu kırmızı: {son.get('name','?')} "
                                    f"@{son.get('head_branch') or '?'} ({son.get('event')}) → "
                                    f"{son.get('conclusion')} — kasıtlı test değilse incele"))
        except Exception as e:
            r.append((WARN, f"CI yanıtı parse edilemedi: {e}"))

    # 3c — org-repo tree'de core-içerik sızıntısı yok
    rc, out = _run([gh, "api", f"repos/{tam}/git/trees/HEAD?recursive=1",
                    "--jq", "[.truncated, ([.tree[].path | select(startswith(\"core/\"))] | length)] | @tsv"],
                   timeout=60)
    if rc != 0:
        r.append((WARN, f"repo tree okunamadı ({tam})"))
    else:
        parcalar = out.strip().split("\t")
        try:
            kesik, sayi = parcalar[0] == "true", int(parcalar[1])
        except Exception:
            kesik, sayi = False, -1
        if sayi == 0:
            not_ = " (tree kesik — kısmi tarama)" if kesik else ""
            r.append((PASS, f"{tam} tree'sinde core/ yolu YOK (sızıntı temiz){not_}"))
        elif sayi > 0:
            r.append((FAIL, f"{tam} tree'sinde {sayi} adet core/ yolu VAR — SIZINTI (R1)"))
        else:
            r.append((WARN, "tree sızıntı sayımı parse edilemedi"))
    return r


# ---------------------------------------------------------------- katman 4

def _shim_yolu() -> Path:
    return PROJ / "scripts" / "hook_shim.py"


def _hook_kos(hook: str, stdin_json: dict, timeout: int = 60) -> tuple[int, str, float]:
    """Hook'u proje shim'i üzerinden (D15 zinciri) örnek-stdin ile koş."""
    shim = _shim_yolu()
    if shim.exists():
        args = [sys.executable, str(shim), hook]
    else:  # shim yoksa doğrudan core hook (drift kontrolü zaten ayrıca FAIL verir)
        args = [sys.executable, str(CORE_ROOT / "scripts" / "hooks" / f"{hook}.py")]
    t0 = time.perf_counter()
    rc, out = _run(args, cwd=PROJ, stdin_text=json.dumps(stdin_json), timeout=timeout, env=_hook_env())
    return rc, out, time.perf_counter() - t0


def katman4() -> list[Sonuc]:
    r: list[Sonuc] = []

    # 4a — settings.json ↔ template drift (D7, hash)
    ciftler = [
        (PROJ / ".claude" / "settings.json", CORE_ROOT / "claude" / "settings.template.json", "settings.json"),
        (_shim_yolu(), CORE_ROOT / "claude" / "hook_shim.template.py", "hook_shim.py"),
    ]
    for yerel, tpl, ad in ciftler:
        if not yerel.exists():
            r.append((FAIL, f"{ad} YOK — üret: python core/scripts/team_setup.py"))
        elif _sha16(yerel) == _sha16(tpl):
            r.append((PASS, f"{ad} template ile hash-eş ({_sha16(yerel)})"))
        else:
            r.append((WARN, f"{ad} template'ten SAPMIŞ (D7: {_sha16(yerel)} ≠ {_sha16(tpl)}) — "
                            f"bilinçliyse manifest'e işle; değilse core/claude/{tpl.name} ile diff'le"))

    # 4b — SHIM_SURUM eşliği
    surum = re.compile(r'SHIM_SURUM\s*=\s*"([^"]+)"')
    try:
        yerel_v = (surum.search(_shim_yolu().read_text(encoding="utf-8")) or [None, "?"])[1]
        tpl_v = (surum.search((CORE_ROOT / "claude" / "hook_shim.template.py").read_text(encoding="utf-8")) or [None, "?"])[1]
        r.append((PASS, f"SHIM_SURUM eş: {yerel_v}") if yerel_v == tpl_v and yerel_v != "?"
                 else (WARN, f"SHIM_SURUM ayrık: yerel={yerel_v} template={tpl_v} — shim'i template'ten yenile"))
    except Exception as e:
        r.append((FAIL, f"SHIM_SURUM okunamadı: {e}"))

    # 4c — behavior-manifest ↔ ağaç (F2)
    try:
        import behavior_manifest  # CORE_ROOT/scripts sys.path'te
        sapmalar = behavior_manifest.verify_quiet(PROJ)
        if not sapmalar:
            r.append((PASS, "behavior-manifest: canlı ağaç manifest ile EŞ"))
        else:
            r.append((FAIL, f"behavior-manifest SAPMASI ({len(sapmalar)}): "
                            + " · ".join(sapmalar[:4]) + (" …" if len(sapmalar) > 4 else "")))
    except Exception as e:
        r.append((FAIL, f"behavior-manifest kontrolü koşamadı: {e}"))

    # 4d — hook smoke (örnek-stdin; session_start'a session_id VERİLMEZ →
    #      .current_session marker'ı EZİLMEZ)
    rc, out, sure = _hook_kos("session_start", {})
    if rc == 0 and "hookSpecificOutput" in out:
        r.append((PASS, f"hook smoke session_start: exit 0 + JSON çıktı ({sure:.2f}s)"))
    else:
        r.append((FAIL, f"hook smoke session_start: exit {rc} — {out.strip().splitlines()[-1][:100] if out.strip() else 'çıktı yok'}"))

    rc, out, _ = _hook_kos("pre_tool_guard",
                           {"tool_name": "Bash", "tool_input": {"command": "echo ix_doctor-smoke"}})
    r.append((PASS, "hook smoke pre_tool_guard (zararsız komut): exit 0") if rc == 0
             else (FAIL, f"hook smoke pre_tool_guard: exit {rc} (zararsız komutta blok/hata!) — {out.strip()[:100]}"))

    # 4e — (KALDIRILDI 2026-07-10) FREEZE-GUARD R10 sağlık denetiminde silindi:
    #      donmuş kök git-remote'ta yedekli → yazma geri-alınabilir, runtime guard'a ait
    #      değil (merdiven kriteri). Koruma OS izniyle (icacls) ya da klasörü park ederek
    #      yapılır. Bu canlı test de onunla birlikte kaldırıldı.

    # 4f — KABLOLAMA GATE (2026-07-09 denetimi): guard'ın KOD'da koruduğu her araç,
    #      settings.json PreToolUse matcher'ında da var mı?
    #      Vaka: guard `PowerShell`i tanıyordu, matcher yalnız `Bash` idi → Bash'te
    #      bloklanan komut PowerShell'den GEÇİYORDU (canlı A/B ile kanıtlandı). Guard'ı
    #      doğrudan çağıran testler yeşildi. "Kod-seviyesi koruma" ≠ "korunuyor".
    r.extend(_kablolama_kontrol())
    return r


_GUARD_KORUDUGU_TOOLLAR = ("Bash", "PowerShell", "Edit", "Write", "MultiEdit", "NotebookEdit")


def _kablolama_kontrol() -> list:
    """pre_tool_guard'ın koruduğu her tool, PreToolUse matcher'ıyla ona yönleniyor mu?"""
    import json as _json
    r = []
    ayar = PROJ / ".claude" / "settings.json"
    if not ayar.exists():
        return [(SKIP, "kablolama kontrolü: .claude/settings.json yok")]
    try:
        d = _json.loads(ayar.read_text(encoding="utf-8"))
    except Exception as e:
        return [(FAIL, f"kablolama kontrolü: settings.json okunamadı ({type(e).__name__})")]

    matcherlar = []
    for blok in (d.get("hooks", {}) or {}).get("PreToolUse", []) or []:
        kancalar = _json.dumps(blok.get("hooks", []))
        if "pre_tool_guard" in kancalar:
            matcherlar.append(blok.get("matcher", ".*"))

    if not matcherlar:
        return [(FAIL, "kablolama: PreToolUse'da pre_tool_guard'a giden HİÇBİR matcher yok — guard ÖLÜ")]

    kapsanmayan = []
    for tool in _GUARD_KORUDUGU_TOOLLAR:
        if not any(re.fullmatch(m, tool) for m in matcherlar):
            kapsanmayan.append(tool)
    if kapsanmayan:
        r.append((FAIL, f"kablolama DELİK: guard bu tool'ları kodda koruyor ama matcher yönlendirmiyor "
                        f"→ {', '.join(kapsanmayan)}. Kod-seviyesi koruma, kablolanmadan KORUMA DEĞİLDİR."))
    else:
        r.append((PASS, f"kablolama: guard'ın koruduğu {len(_GUARD_KORUDUGU_TOOLLAR)} tool'un tamamı "
                        f"PreToolUse matcher'ında ({len(matcherlar)} blok)"))
    return r


# ---------------------------------------------------------------- katman 5

_CONN_ZORUNLU = ("ADT_SAP_URL", "ADT_SAP_USER", "ADT_SAP_PASSWORD", "ADT_SAP_CLIENT")


def katman5(live_sap: bool) -> list[Sonuc]:
    r: list[Sonuc] = []

    # 5a — .conn_adt var + zorunlu alanlar dolu + placeholder'sız
    conn = PROJ / ".conn_adt"
    if not conn.exists():
        r.append((FAIL, f".conn_adt YOK ({conn}) — PROJECT_BOOTSTRAP STEP 4 ile doldur"))
    else:
        alanlar: dict[str, str] = {}
        for ln in conn.read_text(encoding="utf-8", errors="replace").splitlines():
            s = ln.strip()
            if "=" in s and not s.startswith("#"):
                k, v = s.split("=", 1)
                alanlar[k.strip()] = v.strip()
        eksik = [k for k in _CONN_ZORUNLU if not alanlar.get(k)]
        ph = [k for k, v in alanlar.items() if "__DOLDUR__" in v or v.startswith("<")]
        if eksik:
            r.append((FAIL, f".conn_adt eksik alan: {', '.join(eksik)}"))
        elif ph:
            r.append((FAIL, f".conn_adt placeholder DOLDURULMAMIŞ: {', '.join(ph)}"))
        else:
            r.append((PASS, f".conn_adt tamam ({len(alanlar)} alan; zorunlu 4/4 dolu, placeholder yok)"))

    # 5b — MCP server dosyaları junction üzerinden erişilebilir
    mcp = PROJ / "core" / "mcp_servers" / "sap_adt" / "server.py"
    r.append((PASS, f"MCP server junction'dan erişilebilir: {mcp}") if mcp.is_file()
             else (FAIL, f"MCP server dosyası junction'dan ERİŞİLEMİYOR: {mcp}"))

    # 5c — canlı SAP probe (yalnız --live-sap; default'ta ağ denemesi YOK)
    if not live_sap:
        r.append((SKIP, "canlı SAP probe atlandı (default; koşmak için --live-sap)"))
    else:
        rc, out = _run([sys.executable, str(CORE_ROOT / "scripts" / "sap_doctor.py")],
                       cwd=PROJ, timeout=180, env=_hook_env())
        son = next((ln for ln in reversed(out.strip().splitlines()) if ln.strip()), "?")
        r.append((PASS, f"canlı SAP probe (sap_doctor exit 0): {son[:110]}") if rc == 0
                 else (FAIL, f"canlı SAP probe BAŞARISIZ (sap_doctor exit {rc}): {son[:110]}"))
    return r


# ---------------------------------------------------------------- katman 6

def katman6() -> list[Sonuc]:
    r: list[Sonuc] = []

    # 6a — run_all_validators TAM PASS + süre
    rav = CORE_ROOT / "scripts" / "validators" / "run_all_validators.py"
    t0 = time.perf_counter()
    rc, out = _run([sys.executable, str(rav)], cwd=PROJ, timeout=600, env=_hook_env())
    sure = time.perf_counter() - t0
    if rc == 0:
        r.append((PASS, f"run_all_validators TAM PASS ({sure:.1f}s)"))
    else:
        kuyruk = [ln for ln in out.strip().splitlines() if ln.strip()][-4:]
        r.append((FAIL, f"run_all_validators FAIL (exit {rc}, {sure:.1f}s): " + " | ".join(kuyruk)))

    # 6b — session_start hook süresi (<1.5sn hedef; F2-P.1)
    rc, _, sure = _hook_kos("session_start", {})
    if rc != 0:
        r.append((FAIL, f"session_start süre ölçümü: hook exit {rc}"))
    elif sure < 1.5:
        r.append((PASS, f"session_start süresi {sure:.2f}s (< 1.5s hedef)"))
    else:
        r.append((WARN, f"session_start süresi {sure:.2f}s — 1.5s hedefini AŞIYOR (F2-P kaldıraçları: "
                        "Ö3 throttle / manifest-daralt)"))
    return r


# ---------------------------------------------------------------- katman 7

def katman7() -> list[Sonuc]:
    r: list[Sonuc] = []

    # 7a — memory: proje slug'ından türetilen klasörde MEMORY.md dolu (seed_memory deseni)
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(PROJ))
    mem = Path.home() / ".claude" / "projects" / slug / "memory" / "MEMORY.md"
    if mem.is_file() and mem.stat().st_size > 0:
        r.append((PASS, f"memory dolu: {mem} ({mem.stat().st_size} bayt)"))
    elif mem.is_file():
        r.append((WARN, f"MEMORY.md BOŞ: {mem} — tohumla: python core/scripts/seed_memory.py"))
    else:
        r.append((FAIL, f"memory YOK: {mem} — tohumla: python core/scripts/seed_memory.py"))

    # 7b — deploy zinciri import-sağlığı (deploy YOK; yalnız --help exit 0)
    rc, out = _run([sys.executable, str(CORE_ROOT / "scripts" / "deploy_ui.py"), "--help"],
                   cwd=PROJ, timeout=60, env=_hook_env())
    r.append((PASS, "deploy_ui --help exit 0 (deploy zinciri import-sağlıklı)") if rc == 0
             else (FAIL, f"deploy_ui --help exit {rc}: {out.strip().splitlines()[-1][:100] if out.strip() else '?'}"))

    # 7c — aktif paket .rules.md (L4)
    pkg = str(cfg("active_package") or "")
    if not pkg:
        r.append((WARN, "project.yaml active_package boş — .rules.md kontrolü atlandı"))
    else:
        from utils.project_config import source_dir
        adaylar = list(source_dir().glob(f"*/{pkg}/.rules.md"))
        r.append((PASS, f"aktif paket .rules.md mevcut: {adaylar[0]}") if adaylar
                 else (FAIL, f"aktif paket .rules.md YOK: {source_dir()}\\*\\{pkg}\\.rules.md — "
                             f"bootstrap: python core/scripts/bootstrap_package.py {pkg}"))
    return r


# ---------------------------------------------------------------- rapor

KATMANLAR: list[tuple[int, str]] = [
    (1, "FS + BAĞIMLILIK (junction/policy/plugin/CLI)"),
    (2, "GIT (remote/main/stable/hooksPath/baseline/tree)"),
    (3, "GITHUB ENFORCE (ruleset/CI/sızıntı)"),
    (4, "CLAUDE KATMANI (drift/manifest/hook-smoke/freeze-guard)"),
    (5, "MCP / SAP (.conn_adt/junction-erişim/canlı-probe)"),
    (6, "VALIDATORS + PERF (run_all + session_start süresi)"),
    (7, "İŞ-AKIŞI SMOKE (memory/deploy-zinciri/.rules.md)"),
]


def _katman_durum(kontroller: list[Sonuc]) -> str:
    taglar = [t for t, _ in kontroller]
    if FAIL in taglar:
        return FAIL
    if WARN in taglar:
        return WARN
    return PASS


def main() -> int:
    ap = argparse.ArgumentParser(description="Kurulum sağlık taraması (7 katman; sap_doctor'un kardeşi)")
    ap.add_argument("--layer", type=int, choices=range(1, 8), default=None,
                    help="Yalnız tek katmanı koş (1-7)")
    ap.add_argument("--live-sap", action="store_true",
                    help="Katman 5'te canlı SAP probe (default: ağ denemesi YOK)")
    ap.add_argument("--json", action="store_true", help="Makine-okur JSON özet")
    args = ap.parse_args()

    kosucular = {1: katman1, 2: katman2, 3: katman3, 4: katman4,
                 5: lambda: katman5(args.live_sap), 6: katman6, 7: katman7}

    secili = [k for k in KATMANLAR if args.layer is None or k[0] == args.layer]
    rapor: list[dict] = []
    for no, ad in secili:
        t0 = time.perf_counter()
        try:
            kontroller = kosucular[no]()
        except Exception as e:  # katman izolasyonu: biri patlasa diğerleri koşar
            kontroller = [(FAIL, f"katman çalıştırılamadı: {type(e).__name__}: {e}")]
        rapor.append({"no": no, "ad": ad, "durum": _katman_durum(kontroller),
                      "sure_sn": round(time.perf_counter() - t0, 1),
                      "kontroller": [{"tag": t, "mesaj": m} for t, m in kontroller]})

    n_fail = sum(1 for k in rapor if k["durum"] == FAIL)
    n_warn = sum(1 for k in rapor if k["durum"] == WARN)
    cikis = 1 if n_fail else 0

    if args.json:
        print(json.dumps({"proje": str(PROJ), "core": str(CORE_ROOT),
                          "katmanlar": rapor, "fail": n_fail, "warn": n_warn,
                          "exit": cikis}, ensure_ascii=False, indent=1))
        return cikis

    print("=" * 72)
    print("IX DOCTOR — kurulum sağlık taraması (F2; 7 katman)")
    print(f"proje: {PROJ}   core: {CORE_ROOT}")
    print("=" * 72)
    for k in rapor:
        print(f"\n── KATMAN {k['no']} · {k['ad']}  →  {_TAG[k['durum']]}  ({k['sure_sn']}s)")
        for c in k["kontroller"]:
            print(f"   {_TAG[c['tag']]} {c['mesaj']}")
    print("\n" + "-" * 72)
    ozet = " · ".join(f"K{k['no']}={k['durum']}" for k in rapor)
    print(f"ÖZET: {ozet}")
    if n_fail:
        print(f"SONUÇ: {n_fail} katman FAIL, {n_warn} katman WARN — kurulum SAĞLIKSIZ (STOP kuralı: önce düzelt).")
    elif n_warn:
        print(f"SONUÇ: FAIL yok, {n_warn} katman WARN — çalışılabilir; WARN'lar gerekçelendirilmeli (F2.8).")
    else:
        print("SONUÇ: Tüm katmanlar PASS — kurulum sağlıklı.")
    return cikis


if __name__ == "__main__":
    raise SystemExit(main())
