#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ix_doctor.py — geçiş-sonrası KURULUM sağlık taraması (F2; sap_doctor'un kardeşi).

sap_doctor "SAP bağlantısı sağlıklı mı?" sorusuna bakar; ix_doctor "canlı-çekirdek
kurulumu (junction + git + GitHub-enforce + Claude-katmanı + MCP + validator +
iş-akışı) uçtan uca sağlıklı mı?" sorusuna bakar. 7 katman, her kontrol kanıt-satırı
basar; katman durumu = kontrollerin en kötüsü (FAIL > WARN > PASS).

Katmanlar (GECIS-EXEC-CHECKLIST BLOK F / F2.1–F2.7):
  1. FS+BAĞIMLILIK : 4 junction → gerçek core'a çözülüyor · managed-policy ·
                     plugin envanteri (setup_plugins --list) · CLI mevcudiyeti ·
                     (Windows) PowerShell politikası × npm .ps1 shim'i (Q339) ·
                     Claude Code sürümü ↔ ölçülmüş taban · hook yorumlayıcısı
                     gerçekten başlıyor mu (Q365①; ikisi de WARN-only)
  2. GIT           : remote org tutarlı · main==origin/main · stable tag ·
                     hooksPath · global baseline · working-tree temizliği
  3. GITHUB-ENFORCE: ruleset ACTIVE · CI yeşil · repo tree'de core-sızıntısı yok
                     (gh CLI yoksa katman SKIP+WARN; project.yaml `repo_mode` local|none
                     ise ruleset+CI SKIP — Q336)
  4. CLAUDE        : settings/shim template-drift (D7) · SHIM_SURUM · behavior-
                     manifest ↔ ağaç (F2) · hook smoke (örnek-stdin) · tanım dosyası
                     frontmatter'ı geçerli YAML mı (4g; `utils/frontmatter_lint`, WARN-only,
                     otomatik düzeltme YOK — bulgu ÇEKİRDEK/PROJE kaynağıyla ayrılır) ·
                     kanca kablolaması AD düzeyinde (4h) · şablon+proje kancalarının HER
                     BİRİ gerçek shim'den smoke (4i) · recall_inject içerik sondası (4j) — Q406
                     (freeze-guard canlı testi 2026-07-10'da R10 ile birlikte KALDIRILDI — bkz. 4e)
  5. MCP/SAP       : .conn_adt var+placeholder'sız · MCP server dosyaları
                     junction'dan erişilebilir · MCP server IMPORT edilebilir (Q335;
                     .conn_adt'den bağımsız) · (--live-sap ile) canlı probe
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

# ⭐ TEK KAYNAK (2026-09-09, kayıt Q212): D7'nin "sapma" TANIMI `utils/drift_imzasi`de;
# kardeş kapı `scripts/hooks/session_start.py` aynı modülü okur. Kopya-tanım bu turun
# TEŞHİSİYDİ (ham sha ↔ davranışsal imza ayrışması) — ikinci kopya AÇILMAZ.
# ⛔ Yüklenemezse D7 kolu PASS DEMEZ, "ÖLÇÜLEMEDİ" der (bkz. `_d7_drift`).
_IMZA_KAYNAGI = "utils.drift_imzasi"
try:
    from utils.drift_imzasi import anlamli_imza, OKUNAMADI, d7_ciftleri  # noqa: E402
except Exception as _imza_hatasi:  # pragma: no cover
    _IMZA_KAYNAGI = f"YOK ({type(_imza_hatasi).__name__})"
    anlamli_imza = None  # type: ignore
    OKUNAMADI = "?"
    d7_ciftleri = None  # type: ignore

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


# ⛔ `_sha16()` (ham `sha256(read_bytes())`) 2026-09-09'da SİLİNDİ (Q212) — tek tüketicisi
# D7 koluydu ve orada YANLIŞ ölçüttü. Ölü bir ham-hash yardımcısını düzeltilmiş kolun
# yanında bırakmak, bu turun teşhis ettiği kopya-tanım ayrışmasını yeniden davet ederdi.
# D7 için doğru ölçüt `utils.drift_imzasi.anlamli_imza`dır (yukarıdaki import).


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
    # Q286 (2026-09-12): ZORUNLU tip (`rules`) claude-local'siz de GERÇEK dizin olmalıdır;
    # eski `overlay_var_mi` dalı onu junction planına koyup "gerçek klasör — sızıntı riski"
    # FAIL'i basıyordu. Hâlâ junction ise ayrı ve açık bir WARN basılır (yüklenmiyor).
    _gerekli = getattr(_ov, "overlay_gerekli", _ov.overlay_var_mi)
    for _tip in _ov.TIPLER:
        _bag = PROJ / ".claude" / _tip
        if _tip in getattr(_ov, "ZORUNLU_TIPLER", ()) and _readlink(_bag) is not None:
            r.append((WARN, f".claude/{_tip} hâlâ JUNCTION — harness junction'daki talimatı dış "
                            f"import sayar, YÜKLEMEZ (Q286). Onarım: python core/scripts/"
                            f"team_setup.py --repair-junctions"))
            continue
        if _gerekli(PROJ, _tip):
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
    bulunan: dict[str, str] = {}
    for ad, kur in (("node", "Node.js LTS kur → https://nodejs.org"),
                    ("npm", "Node.js LTS ile gelir → https://nodejs.org"),
                    ("claude", "npm install -g @anthropic-ai/claude-code")):
        yol = shutil.which(ad)
        if yol:
            bulunan[ad] = yol
        r.append((PASS, f"CLI mevcut: {ad} ({yol})") if yol
                 else (FAIL, f"CLI YOK: {ad} — kurulum: {kur}"))
    for ad, kur in (("playwright-cli", "npm install -g @playwright/cli"),
                    ("ast-grep", "npm install -g @ast-grep/cli"),
                    ("mmdc", "npm install -g @mermaid-js/mermaid-cli@11.17.0"),  # pin: team_setup npm_clis
                    ("marp", "npm install -g @marp-team/marp-cli")):
        yol = shutil.which(ad)
        if yol:
            bulunan[ad] = yol
        r.append((PASS, f"CLI mevcut (opsiyonel): {ad}") if yol
                 else (WARN, f"opsiyonel CLI yok: {ad} — kurulum: {kur}"))

    # 1e — PowerShell yürütme politikası × npm `.ps1` shim'i (Q339; YALNIZ Windows)
    r += _ps_politika_kontrol(bulunan)
    # 1f — Claude Code sürümü ↔ ölçülmüş taban (Q365①; WARN-only ölçüm, gate DEĞİL)
    r += _claude_surum_kontrol(bulunan.get("claude"))
    # 1g — hook yorumlayıcısı GERÇEKTEN başlıyor mu (Q365①; sys.executable'dan BAĞIMSIZ)
    r += _yorumlayici_kontrol()
    return r


# ---------------------------------------------------------------- 1f / 1g (Q365①)
# NEDEN VAR (dış repo karşılaştırması 2026-10-12): 1d yalnız `claude`'un PATH'te VARLIĞINI
# söyler; çekirdeğin dayandığı yükleme mekanizmasının hangi sürümde ÖLÇÜLDÜĞÜNÜ söylemez.
# 4d hook smoke'u ise hook'u `sys.executable` ile koşar — Claude Code ise settings'teki
# `"command": "python"`ı KENDİ PATH çözümüyle başlatır. İkisi ayrışabilir: Windows'ta
# `WindowsApps\python.exe` Microsoft Store YÖNLENDİRİCİSİDİR (ölçüldü: `-c` ile rc=49,
# "Python was not found") ⇒ PATH'te önde olursa HİÇBİR hook başlamaz, `pre_tool_guard`
# bloklamaz (sessiz fail-open) ve 4d yine PASS der.
# ⛔ İKİSİ DE FAIL ÜRETMEZ (ADR 0019: ölçüm aracı, yeni gate değil) — WARN ile başlar.
# ⛔ ÖLÇÜLEMEDİ ≠ TEMİZ: ayrıştırılamayan sürüm / okunamayan settings PASS DEMEZ.
#
# TABAN = "ÖLÇÜLMÜŞ" taban, "desteklenen asgari" DEĞİL: çekirdek talimatının fiziksel kopya
# ile yüklenmesi (Q286, `.claude/rules/00-claude-core.md`) Claude Code 2.1.269'da ölçüldü
# (infra-changelog Q286 satırı). Daha eski sürümde bu mekanizma ÖLÇÜLMEDİ — bozuk olduğu
# KANITLANMADI. Taban yalnız yeni bir ölçümle yükseltilir/düşürülür (kaynağıyla birlikte).
CLAUDE_OLCULMUS_TABAN = (2, 1, 269)
_CC_SURUM_KAPSAM = ("kapsam: `claude --version` çıktısı, ix_doctor sürecinin PATH'iyle; "
                    "taban ÖLÇÜLMÜŞ sürümdür, uyumluluk sınırı değil; FAIL üretmez")
# Bilinen biçimler (ölçüldü: "2.1.296 (Claude Code)"). Başka biçim TAHMİN EDİLMEZ — eşleşmeyen
# çıktı ÖLÇÜLEMEDİ olur (sahte FAIL/PASS yok). Satır içinde rastgele sayı (node uyarısı,
# yol) YAKALANMASIN diye ikinci desen tam satırdır.
_CC_SURUM_DESENLERI = (
    re.compile(r"(?<![\w.])v?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.]+)?\s+\(Claude Code\)"),
    re.compile(r"^\s*v?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.]+)?\s*$"),
)


def _claude_surum_ayristir(cikti: str) -> tuple[int, int, int] | None:
    """`claude --version` çıktısından (major, minor, patch); tanınmazsa None."""
    for satir in (cikti or "").splitlines():
        for desen in _CC_SURUM_DESENLERI:
            m = desen.search(satir)
            if m:
                return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def _claude_surum_kontrol(claude_yol: str | None) -> list[Sonuc]:
    taban = ".".join(map(str, CLAUDE_OLCULMUS_TABAN))
    if not claude_yol:
        return [(SKIP, "Claude Code sürümü ölçülmedi — `claude` PATH'te yok (1d satırına bak)")]
    rc, out = _run([claude_yol, "--version"], timeout=30)
    surum = _claude_surum_ayristir(out) if rc == 0 else None
    if surum is None:
        ilk = next((s.strip() for s in out.splitlines() if s.strip()), "çıktı yok")
        return [(WARN, f"Claude Code sürümü ÖLÇÜLEMEDİ (`claude --version` rc={rc}: "
                       f"{ilk[:80]!r}) — tanınan biçim yok; sürüm BİLİNMİYOR (temiz demek "
                       f"DEĞİL) [{_CC_SURUM_KAPSAM}]")]
    s = ".".join(map(str, surum))
    if surum < CLAUDE_OLCULMUS_TABAN:
        return [(WARN, f"Claude Code {s} < ölçülmüş taban {taban} — çekirdek yükleme "
                       f"mekanizması (Q286) bu sürümde ÖLÇÜLMEDİ; güncelle: `claude update` "
                       f"[{_CC_SURUM_KAPSAM}]")]
    return [(PASS, f"Claude Code {s} ≥ ölçülmüş taban {taban} [{_CC_SURUM_KAPSAM}]")]


_YORUMLAYICI_ISARET = "IX-YORUMLAYICI-OK"
_YORUMLAYICI_KAPSAM = ("kapsam: settings'teki hook/statusLine komutları, ix_doctor sürecinin "
                       "PATH'iyle çözüldü — Claude Code'un hook ortamının PATH'i ÖLÇÜLMEDİ; "
                       "FAIL üretmez")
# `${X}` · `$X` · `%X%` — genişletilmemiş değişken (Claude Code genişletir; biz taklit etmeyiz)
_YORUMLAYICI_DEGISKEN = re.compile(r"\$\{[^}]*\}|\$[A-Za-z_]\w*|%[A-Za-z_]\w*%")
# python ailesi: python · python3 · python3.11 · pythonw · py · pyw · *python* (+ .exe/.cmd/.bat)
_YORUMLAYICI_PY_AILE = re.compile(r"(?:[\w.-]*python[\w.-]*?|pyw?)(?:\.(?:exe|cmd|bat))?", re.I)


def _min_py() -> tuple[int, int] | None:
    """Python tabanı TEK KAYNAKTAN: `team_setup.MIN_PY` (AST; import yan etkisi yok)."""
    import ast
    try:
        agac = ast.parse((CORE_ROOT / "scripts" / "team_setup.py").read_text(encoding="utf-8"))
        for d in agac.body:
            if (isinstance(d, ast.Assign) and any(isinstance(h, ast.Name) and h.id == "MIN_PY"
                                                  for h in d.targets)):
                v = ast.literal_eval(d.value)
                return int(v[0]), int(v[1])
    except Exception:  # noqa: BLE001
        return None
    return None


def _hook_komutlari(ayar: Path) -> dict[str, int]:
    """settings.json'daki hook + statusLine komutlarının YORUMLAYICI adı → adet.

    exec biçimi (`args` VAR): `command` alanının kendisi. Kabuk biçimi: ilk sözcük.
    Okuma/ayrıştırma hatası YUKARI çıkar (çağıran ÖLÇÜLEMEDİ'ye çevirir)."""
    veri = json.loads(ayar.read_text(encoding="utf-8"))
    sayac: dict[str, int] = {}

    def _ekle(kanca: dict) -> None:
        kom = str(kanca.get("command") or "").strip()
        if not kom:
            return
        if "args" in kanca:
            ad = kom
        else:
            m = re.match(r'\s*"([^"]+)"|\s*(\S+)', kom)
            ad = (m.group(1) or m.group(2)) if m else kom
        sayac[ad] = sayac.get(ad, 0) + 1

    for bloklar in (veri.get("hooks") or {}).values():
        for blok in bloklar or []:
            for kanca in blok.get("hooks") or []:
                if isinstance(kanca, dict):
                    _ekle(kanca)
    if isinstance(veri.get("statusLine"), dict):
        _ekle(veri["statusLine"])
    return sayac


def _yorumlayici_kontrol(ayar: Path | None = None) -> list[Sonuc]:
    """1g satırları. Her farklı yorumlayıcı için: PATH çözümü + `-c` probu + sürüm."""
    ayar = ayar or (PROJ / ".claude" / "settings.json")
    kaynak = ".claude/settings.json"
    if not ayar.is_file():
        ayar, kaynak = CORE_ROOT / "claude" / "settings.template.json", "settings ŞABLONU (proje kopyası yok)"
    try:
        komutlar = _hook_komutlari(ayar)
    except Exception as e:  # noqa: BLE001
        return [(WARN, f"hook yorumlayıcısı ÖLÇÜLEMEDİ — {kaynak} okunamadı "
                       f"({type(e).__name__}: {e}) [{_YORUMLAYICI_KAPSAM}]")]
    if not komutlar:
        return [(WARN, f"hook yorumlayıcısı ÖLÇÜLEMEDİ — {kaynak} içinde hook komutu yok "
                       f"[{_YORUMLAYICI_KAPSAM}]")]
    taban = _min_py()
    r: list[Sonuc] = []
    for ad, adet in sorted(komutlar.items()):
        # ÖLÇÜLEMEDİ (SKIP) iki durum — WARN değil, çünkü ölçülen bir kusur YOK (bug-gate ÖNERİ):
        # ① genişletilmemiş değişkenli yol: Claude Code'un genişletmesi taklit EDİLMEZ (tahmin olur)
        if _YORUMLAYICI_DEGISKEN.search(ad):
            r.append((SKIP, f"hook yorumlayıcısı `{ad}` ÖLÇÜLEMEDİ — yol genişletilmemiş değişken "
                            f"içeriyor ({adet} komut); ix_doctor kabuk/harness genişletmesini taklit "
                            f"ETMEZ — temiz demek DEĞİL [{_YORUMLAYICI_KAPSAM}]"))
            continue
        yol = ad if ("/" in ad or "\\" in ad) else shutil.which(ad)
        if not yol:
            r.append((WARN, f"hook yorumlayıcısı `{ad}` PATH'te YOK — {kaynak} içindeki {adet} "
                            f"komut HİÇ başlamaz (pre_tool_guard bloklamaz = sessiz fail-open) "
                            f"[{_YORUMLAYICI_KAPSAM}]"))
            continue
        # ② python ailesi DIŞI (node/bash/pwsh…): `-c` sürüm probu uygulanamaz → BAŞLAMIYOR demek
        #    sahte WARN olurdu. PATH çözümü yukarıda ÖLÇÜLDÜ (o WARN gerçektir); başlama ölçülmez.
        if not _YORUMLAYICI_PY_AILE.fullmatch(re.split(r"[\\/]", ad)[-1]):
            r.append((SKIP, f"hook yorumlayıcısı `{ad}` → {yol} ÖLÇÜLEMEDİ — python ailesi DEĞİL; "
                            f"`-c` sürüm probu uygulanamaz ({adet} komut) — temiz demek DEĞİL "
                            f"[{_YORUMLAYICI_KAPSAM}]"))
            continue
        rc, out = _run([yol, "-c", f"import sys; print('{_YORUMLAYICI_ISARET}', "
                                   f"*sys.version_info[:3])"], timeout=30)
        m = re.search(rf"^{_YORUMLAYICI_ISARET} (\d+) (\d+) (\d+)\s*$", out, re.M)
        if rc != 0 or not m:
            son = next((s.strip() for s in reversed(out.splitlines()) if s.strip()), "çıktı yok")
            ipucu = (" — Microsoft Store YÖNLENDİRİCİSİ (WindowsApps): gerçek Python'u PATH'te "
                     "öne al ya da Ayarlar > Uygulama yürütme diğer adları'ndan kapat"
                     if "windowsapps" in yol.lower() else "")
            r.append((WARN, f"hook yorumlayıcısı `{ad}` → {yol} BAŞLAMIYOR (rc={rc}: {son[:90]!r})"
                            f"{ipucu} — {adet} komut çalışmaz (pre_tool_guard bloklamaz = sessiz "
                            f"fail-open) [{_YORUMLAYICI_KAPSAM}]"))
            continue
        surum = tuple(int(x) for x in m.groups())
        s = ".".join(map(str, surum))
        farkli = ("" if os.path.normcase(os.path.realpath(yol)) ==
                  os.path.normcase(os.path.realpath(sys.executable))
                  else f" (ix_doctor'un kendi yorumlayıcısından FARKLI: {sys.executable})")
        if taban is None:
            r.append((WARN, f"hook yorumlayıcısı `{ad}` → {yol} çalışıyor (Python {s}) ama taban "
                            f"ÖLÇÜLEMEDİ (team_setup.MIN_PY okunamadı){farkli} [{_YORUMLAYICI_KAPSAM}]"))
        elif surum[:2] < taban:
            r.append((WARN, f"hook yorumlayıcısı `{ad}` → {yol} Python {s} < team_setup.MIN_PY "
                            f"{taban[0]}.{taban[1]}{farkli} [{_YORUMLAYICI_KAPSAM}]"))
        else:
            r.append((PASS, f"hook yorumlayıcısı `{ad}` → {yol} çalışıyor (Python {s} ≥ "
                            f"{taban[0]}.{taban[1]}; {adet} komut){farkli} [{_YORUMLAYICI_KAPSAM}]"))
    return r


# ---------------------------------------------------------------- 1e (Q339)
# NEDEN VAR (Issue #278, 2026-09-18): 1d `shutil.which` ile `npm.CMD`yi bulur ve PASS der;
# PowerShell ise çıplak `npm`i `npm.ps1`e çözer ve `Restricted`/`AllSigned` politikası onu
# BLOKLAR (`UnauthorizedAccess`). Araç kurulu ve sağlam, ama kullanıcının birincil
# kabuğunda çağrılamıyor — 1d'nin PASS'ı bunu söylemiyordu.
# ⛔ ALT SÜREÇ AÇILMAZ (`powershell Get-ExecutionPolicy` YASAK): alt süreç çağıranın
# SÜREÇ-kapsamlı politikasını (env `PSExecutionPolicyPreference`, örn. araçların açtığı
# `Bypass`) DEVRALIR ve kullanıcının etkin politikası yerine onu raporlar ⇒ yanlış PASS.
# Politika kayıt defterinden okunur; öncelik PowerShell'in kendi sırasıdır, SÜREÇ HARİÇ:
#   MachinePolicy (GPO, HKLM) > UserPolicy (GPO, HKCU) > CurrentUser (HKCU) > LocalMachine (HKLM)
# hiçbiri yoksa Windows İSTEMCİ varsayılanı `Restricted`.
# KAPSAM: Windows PowerShell 5.1 kayıt defteri. pwsh 7 politikası JSON dosyasında yaşar
# (powershell.config.json) — ÖLÇÜLMEZ; Windows Server varsayılanı (RemoteSigned) ayırt EDİLMEZ.
_WINDOWS = os.name == "nt"
_PS_GPO = r"SOFTWARE\Policies\Microsoft\Windows\PowerShell"
_PS_SHELLID = r"SOFTWARE\Microsoft\PowerShell\1\ShellIds\Microsoft.PowerShell"
_PS_ENGELLEYEN = ("restricted", "allsigned")
_PS_KAPSAM = ("kapsam: Windows PowerShell 5.1 kayıt defteri; pwsh 7 ve süreç kapsamı "
              "(PSExecutionPolicyPreference) ölçülmedi; FAIL üretmez")


def _kayit_oku(kok: str, yol: str, ad: str):
    """Kayıt defteri değeri; anahtar/değer YOKSA None. Başka her hata YUKARI çıkar
    (çağıran onu ÖLÇÜLEMEDİ'ye çevirir). 64-bit görünüm (32-bit Python'da HKLM\\SOFTWARE
    WOW6432Node'a yönlenir; PowerShell 64-bit görünümü okur)."""
    import winreg  # yalnız Windows; çağrı `_WINDOWS` ile korunur
    hive = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}[kok]
    try:
        with winreg.OpenKey(hive, yol, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            deger, _tip = winreg.QueryValueEx(k, ad)
            return deger
    except FileNotFoundError:
        return None


def _ps_tanimli(deger) -> bool:
    return deger is not None and str(deger).strip() not in ("", "Undefined")


def _ps_etkin_politika(okuyucu=None) -> tuple[str, str]:
    """(etkin politika, kaynak). Okuma hatası YUKARI çıkar."""
    oku = okuyucu or _kayit_oku
    for kok, kaynak in (("HKLM", "GPO/MachinePolicy"), ("HKCU", "GPO/UserPolicy")):
        etkin = oku(kok, _PS_GPO, "EnableScripts")
        if etkin is not None and str(etkin).strip() == "0":
            return "Restricted", f"{kaynak} — {kok}\\{_PS_GPO} EnableScripts=0"
        pol = oku(kok, _PS_GPO, "ExecutionPolicy")
        if _ps_tanimli(pol):
            return str(pol).strip(), f"{kaynak} — {kok}\\{_PS_GPO}"
    for kok, kaynak in (("HKCU", "CurrentUser"), ("HKLM", "LocalMachine")):
        pol = oku(kok, _PS_SHELLID, "ExecutionPolicy")
        if _ps_tanimli(pol):
            return str(pol).strip(), f"{kaynak} — {kok}\\{_PS_SHELLID}"
    return "Restricted", "varsayılan — hiçbir kapsamda kayıt yok (Windows istemci varsayılanı)"


def _ps_politika_kontrol(bulunan: dict[str, str], okuyucu=None) -> list[Sonuc]:
    """1e satırı. Windows-dışı: hiçbir şey eklenmez. FAIL YOK; okunamazsa ÖLÇÜLEMEDİ (WARN)."""
    if not _WINDOWS:
        return []
    shimler = sorted(ad for ad, yol in bulunan.items()
                     if yol and Path(yol).with_suffix(".ps1").is_file())
    try:
        pol, kaynak = _ps_etkin_politika(okuyucu)
    except Exception as e:  # noqa: BLE001
        return [(WARN, f"PowerShell yürütme politikası ÖLÇÜLEMEDİ ({type(e).__name__}: {e}) — "
                       f"npm .ps1 shim'lerinin ({', '.join(shimler) or 'yok'}) PowerShell'de "
                       f"çağrılabilirliği BİLİNMİYOR [{_PS_KAPSAM}]")]
    if pol.lower() in _PS_ENGELLEYEN and shimler:
        if kaynak.startswith("GPO"):
            care = ("politika GPO'dan geliyor, `Set-ExecutionPolicy` onu EZEMEZ — "
                    "`<ad>.cmd` ya da Git Bash kullan (kalıcı çözüm: BT/GPO)")
        else:
            care = ("`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` ya da "
                    "`<ad>.cmd` / Git Bash kullan")
        return [(WARN, f"PowerShell yürütme politikası {pol} ({kaynak}) — PowerShell'de çıplak "
                       f"{', '.join(shimler)} `.ps1` shim'ine çözülür ve BLOKLANIR "
                       f"(UnauthorizedAccess; 1d PASS'ı yalnız PATH varlığıdır). Çare: {care} "
                       f"[{_PS_KAPSAM}]")]
    if pol.lower() in _PS_ENGELLEYEN:
        return [(PASS, f"PowerShell yürütme politikası {pol} ({kaynak}) — PATH'teki CLI'ların "
                       f"yanında .ps1 shim'i yok, çağrılabilirliğe etkisi yok [{_PS_KAPSAM}]")]
    return [(PASS, f"PowerShell yürütme politikası {pol} ({kaynak}) — .ps1 shim'leri "
                   f"({len(shimler)}) PowerShell'de çalışır [{_PS_KAPSAM}]")]


# ---------------------------------------------------------------- katman 2

def _repo_git_kontrol(etiket: str, repo: Path, beklenen_org: str,
                     org_zorunlu: bool = True, beklenen_ad: str = "",
                     lite_kip: str = "") -> list[Sonuc]:
    r: list[Sonuc] = []
    org, ad = _remote_org_repo(repo)
    if not org:
        if lite_kip:
            # Yeni-proje akışı denetimi F3 (2026-10-03): LITE kipte (repo_mode local|none)
            # remote YOKLUĞU kurulum hatası değil, akışın kendisidir — K3'teki Q336 deseni.
            # Remote VARSA aşağıdaki denetimler kipten bağımsız aynen koşar.
            r.append((SKIP, f"{etiket}: origin remote denetimi atlandı — repo_mode={lite_kip}: "
                            f"LITE kipte remote beklenmez (PROJECT_BOOTSTRAP LITE akışı STEP 1'i atlar)"))
            return r
        r.append((FAIL, f"{etiket}: origin remote YOK/çözülemedi ({repo})"))
        return r
    if beklenen_org and org != beklenen_org:
        if org_zorunlu:
            r.append((FAIL, f"{etiket}: remote org '{org}' ≠ beklenen '{beklenen_org}' ({org}/{ad})"))
        elif beklenen_ad and ad == beklenen_ad:
            # Tüketici/fork topolojisi: çekirdek upstream'den ya da onun FORK'undan gelir,
            # proje ise klonlayanın KENDİ org'undadır. Repo ADI tuttuğu sürece bu meşrudur.
            r.append((PASS, f"{etiket}: remote = {org}/{ad} (proje org'undan farklı — "
                            f"upstream/fork topolojisi, repo adı '{beklenen_ad}' ile eşleşiyor)"))
        else:
            # Repo ADI da tutmuyorsa bu artık topoloji değil, YANLIŞ REPO olabilir → uyar.
            r.append((WARN, f"{etiket}: remote = {org}/{ad} — proje org'u '{beklenen_org}' değil "
                            f"VE repo adı beklenen '{beklenen_ad or '?'}' değil; doğru çekirdeği "
                            f"klonladığını doğrula (project.yaml `core_upstream: <org>/<repo>`)"))
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
    # ⚠ GEVŞETME (F3, dar — K3 Q336 ile AYNI sınır `_LITE_REPO_MODLARI`): yalnız `local`/`none`
    # kipinde ve yalnız proje remote'u YOKKEN iki satır FAIL/WARN yerine SKIP olur. Anahtar
    # yok / `full` / tanınmayan değer ⇒ bugünkü davranış AYNEN (yazım hatası denetimi kapatmaz).
    mod = _repo_modu()
    lite_kip = mod if mod in _LITE_REPO_MODLARI else ""
    # Beklenen org: project.yaml `github_org` → yoksa PROJE remote'undan türet (hardcode YOK)
    beklenen_org = str(cfg("github_org") or "") or _remote_org_repo(PROJ)[0]
    if beklenen_org:
        r.append((PASS, f"beklenen GitHub org (remote-deseninden): {beklenen_org}"))
    elif lite_kip:
        r.append((SKIP, f"beklenen org türetilmedi — repo_mode={lite_kip}: LITE kipte proje "
                        f"remote'u beklenmez (core remote'unun yalnız VARLIĞI denetlenir; "
                        f"org/ad kıyası yapılmaz)"))
    else:
        r.append((WARN, "beklenen org türetilemedi (proje remote'u yok + project.yaml github_org yok)"))

    r += _repo_git_kontrol("proje", PROJ, beklenen_org, lite_kip=lite_kip)
    # ⛔ core, PROJE org'una BAĞLI DEĞİLDİR (2026-09-17, ölçülmüş tüketici vakası): çekirdeği
    # klonlayan kişi kendi org'unda proje açar; core remote'u upstream ya da onun fork'udur.
    # Eskiden bu ayrım yoktu → o kurulumda katman-2 kalıcı FAIL veriyordu ve GERÇEK fail'ler
    # bu gürültüde kayboluyordu. Kontrol kalkmadı, ÖLÇÜTÜ değişti: org yerine REPO ADI.
    core_upstream = str(cfg("core_upstream") or "")           # "<org>/<repo>" (opsiyonel beyan)
    beklenen_core_ad = (core_upstream.split("/")[-1] if "/" in core_upstream
                        else (core_upstream or CORE_ROOT.name))
    r += _repo_git_kontrol("core", CORE_ROOT, beklenen_org,
                           org_zorunlu=False, beklenen_ad=beklenen_core_ad)

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

# Q336 (Issue #275, 2026-09-18): LITE kipler. PROJECT_BOOTSTRAP LITE akışı (repo_mode
# local|none) STEP 1'i — ruleset kurulumu dahil — ATLATIR; `init_project` ruleset
# talimatını yalnız `full`'da basar. ix_doctor bunu okumuyordu ⇒ local projede K3 kalıcı
# FAIL (ruleset yok) ve sonuç hesap planına göre WARN↔FAIL değişiyordu.
# ⚠ GEVŞETME (bilinçli, dar): YALNIZ bu iki değer. Anahtar yok / `full` / TANINMAYAN
# değer ⇒ bugünkü davranış AYNEN (fail-safe: yazım hatası denetimi kapatmaz).
_LITE_REPO_MODLARI = ("local", "none")


def _repo_modu() -> str:
    """project.yaml `repo_mode` (küçük harf, kırpılmış); yoksa "" (= full davranışı)."""
    v = cfg("repo_mode")
    return str(v).strip().lower() if v not in (None, "") else ""


def katman3() -> list[Sonuc]:
    r: list[Sonuc] = []
    mod = _repo_modu()
    lite = mod in _LITE_REPO_MODLARI
    org, repo = _remote_org_repo(PROJ)
    if lite:
        # INFO etiketi YOK (ix_doctor --json şeması PASS/WARN/FAIL/SKIP; parity_probe +
        # fixture'lar tüketir) ⇒ "remote var" bilgisi SKIP mesajının içinde taşınır.
        uzak = (f" · remote VAR ({org}/{repo}) ama bu kipte ruleset/CI beklenmez — kasıtlı "
                f"değilse ve GitHub korumaları isteniyorsa project.yaml `repo_mode: full` yap"
                if org else " · proje remote'u yok")
        r.append((SKIP, f"ruleset denetimi atlandı — repo_mode={mod}: LITE kipte GitHub "
                        f"ruleset beklenmez (PROJECT_BOOTSTRAP LITE akışı STEP 1'i atlar){uzak}"))
        r.append((SKIP, f"CI denetimi atlandı — repo_mode={mod}: LITE kipte CI koşusu beklenmez"))
        if not org:
            r.append((SKIP, f"core-sızıntı tree taraması atlandı — repo_mode={mod} ve proje "
                            f"remote'u yok (taranacak uzak ağaç yok)"))
            return r
    gh = shutil.which("gh")
    if not gh:
        if lite:   # remote VAR: 3c (sızıntı) anlamlı ama ölçülemiyor → sessiz geçilmez
            return r + [(WARN, "gh CLI yok — remote'lu projede core-sızıntı tree taraması "
                               "ÖLÇÜLEMEDİ; gh CLI kur (https://cli.github.com) + `gh auth login`")]
        return [(SKIP, "gh CLI yok — GitHub-enforce katmanı atlandı"),
                (WARN, "gh CLI kur (https://cli.github.com) + `gh auth login` → bu katman koşulabilsin")]
    if not org:
        return [(WARN, "proje remote'u çözülemedi — gh kontrolleri atlandı")]
    tam = f"{org}/{repo}"
    if not lite:
        r += _katman3_ruleset_ci(gh, tam)
    r += _katman3_sizinti(gh, tam)
    return r


def _katman3_ruleset_ci(gh: str, tam: str) -> list[Sonuc]:
    r: list[Sonuc] = []
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
    return r


def _katman3_sizinti(gh: str, tam: str) -> list[Sonuc]:
    r: list[Sonuc] = []
    # 3c — org-repo tree'de core-içerik sızıntısı yok (repo_mode'dan BAĞIMSIZ: remote'a
    #      push edilen her ağaçta sızıntı anlamlıdır)
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


def _hook_kos(hook: str, stdin_json: dict, timeout: int = 60,
              yorumlayici: str | None = None) -> tuple[int, str, float]:
    """Hook'u proje shim'i üzerinden (D15 zinciri) örnek-stdin ile koş.

    `yorumlayici` verilirse (4i, Q406) settings'teki komutun PATH çözümüyle koşulur —
    Claude Code'un gerçek giriş noktası; verilmezse `sys.executable` (4d/6b bugünkü gibi)."""
    shim = _shim_yolu()
    py = yorumlayici or sys.executable
    if shim.exists():
        args = [py, str(shim), hook]
    else:  # shim yoksa doğrudan core hook (drift kontrolü zaten ayrıca FAIL verir)
        args = [py, str(CORE_ROOT / "scripts" / "hooks" / f"{hook}.py")]
    t0 = time.perf_counter()
    rc, out = _run(args, cwd=PROJ, stdin_text=json.dumps(stdin_json), timeout=timeout, env=_hook_env())
    return rc, out, time.perf_counter() - t0


def _d7_drift() -> list[Sonuc]:
    """4a — proje kopyaları (`.claude/settings.json` · `hook_shim.py` · `scripts/git-hooks/pre-commit`)
    şablonlarından SAPMIŞ mı (D7). Çift listesi `utils.drift_imzasi.D7_CIFTLERI` (Q245②).

    ⭐ TEK KAYNAK (2026-09-09, kayıt Q212): "sapma"nın TANIMI artık
    `scripts/utils/drift_imzasi.py`de yaşar; kardeş kapı `scripts/hooks/session_start.py`
    AYNI tanımı oradan okur. Bu kol bugüne kadar HAM `_sha16` ile ölçüyordu ⇒ aynı dosya
    hakkında iki kapı İKİ FARKLI cevap veriyordu (ölçüldü: `session_start`
    `33522a6e2f10dcc5 == 33522a6e2f10dcc5` "sapma yok" derken bu kol
    `[WARN] settings.json template'ten SAPMIŞ` basıyordu). Tek fark `_comment*`
    anahtarlarıydı — davranış TAŞIMAZLAR ⇒ ix_doctor'ın HER koşumu bir yanlış-pozitif
    üretiyordu ve yanlış-pozitif üreten uyarı **uyarı körlüğü** yaratır.
    ⛔ Bu bir GEVŞETME DEĞİLDİR: normalize edilen alanlar (JSON yorum anahtarı, CRLF,
    son-boşluk) davranış taşımaz; bir hook girdisinin/matcher'ın DÜŞMESİ imzayı hâlâ
    değiştirir (fixture'ın pozitif kontrolü tam bunu ölçer).

    ⛔ ÖLÇÜLEMEDİ != TEMİZ (iki ayrı dal): (a) ortak modül yüklenemezse PASS DEĞİL FAIL
    (b) taraflardan biri okunamaz/bozuksa `"?" == "?"` sahte-PASS'ına düşülmez.
    """
    if anlamli_imza is None:
        return [(FAIL, f"D7 ÖLÇÜLEMEDİ — imza modülü yüklenemedi ({_IMZA_KAYNAGI}): "
                       "proje kopyalarının template-sapması (tüm D7 çiftleri) BU KOŞUMDA "
                       "ÖLÇÜLMEDİ (TEMİZ demek DEĞİL). Onarım: core kurulumunu doğrula "
                       "(python core/scripts/team_setup.py --repair-junctions)")]
    r: list[Sonuc] = []
    # Çift listesi + onarım metinleri TEK KAYNAKTA (`utils.drift_imzasi.D7_CIFTLERI`, Q245②):
    # settings.json · hook_shim.py · scripts/git-hooks/pre-commit. Kardeş: session_start.
    for yerel, tpl, ad, yok_onarim, sapma_onarim, tpl_rel in d7_ciftleri(PROJ, CORE_ROOT):
        if not yerel.exists():
            r.append((FAIL, f"{ad} YOK — {yok_onarim}"))
            continue
        y, t = anlamli_imza(yerel), anlamli_imza(tpl)
        if OKUNAMADI in (y, t):
            r.append((FAIL, f"{ad} D7 ÖLÇÜLEMEDİ — davranışsal imza çıkarılamadı "
                            f"(yerel={y} template={t}); okunamayan/bozuk dosya TEMİZ SAYILMAZ"))
        elif y == t:
            r.append((PASS, f"{ad} template ile davranışsal imza EŞ ({y})"))
        else:
            r.append((WARN, f"{ad} template'ten SAPMIŞ (D7: {y} ≠ {t}) — "
                            f"{sapma_onarim}; fark: core/{tpl_rel} ile diff'le"))
    return r


def katman4() -> list[Sonuc]:
    r: list[Sonuc] = []

    # 4a — proje kopyaları ↔ template drift (D7); imza + çift listesi `session_start` ile ORTAK (Q212 · Q245②)
    r += _d7_drift()

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

    # 4h/4i/4j — KANCA KABLOLAMASI + TÜM KANCALARA SMOKE + RECALL SAĞLIĞI (Q406, 2026-11-12):
    #      4a dosyayı tek imzayla kıyaslar (kanca adı vermez), 4d yalnız 2 kancayı koşar,
    #      4f yalnız pre_tool_guard'ın matcher'ına bakar ⇒ şablondaki 16 kancanın 14'ü
    #      ad düzeyinde hiç denetlenmiyordu ve fail-open recall_inject'in arızası sessizdi.
    r.extend(_kanca_kablolama())
    r.extend(_kanca_smoke())
    r.extend(_recall_saglik())

    # 4g — TANIM DOSYASI FRONTMATTER'I (2026-10-18, çekirdek PR #347 vakası): tırnaksız
    #      `description:` içindeki `: ` Claude Code'da LF'te tolere edildi, CRLF checkout'ta
    #      4 ajanı SESSİZCE düşürdü. Kapının çekirdek tarafı `core_precommit` 6. kontrol;
    #      bu kol KURULU makinede (proje + claude-local) aynı modülle ölçer.
    r.extend(_frontmatter_kontrol())
    return r


_CORE_KOPYA_DAMGA = re.compile(r"<!-- CORE-URETILDI: [^>]*?kaynak (core/\S+) -->")


def _frontmatter_kaynagi(f: Path, metin: str) -> tuple[bool, str]:
    """(çekirdek_mi, etiket). Çekirdek = yolu core köküne çözülen dosya (junction) YA DA
    `team_setup`'ın damgaladığı çekirdek kopyası (`.claude/rules/*` gibi fiziksel kopyalar
    proje içinde yaşar ama kaynağı çekirdektir; projede düzeltmek bir sonraki tazelemede
    ezilir ve çekirdek hatasını gizler)."""
    try:
        gercek = f.resolve()
    except OSError:
        gercek = f
    # İki kök: bu betiğin çekirdeği + projenin `core` bağının hedefi (betik bir worktree'den
    # koşulduğunda ikisi ayrışır; projedeki junction'lar ikincisine çözülür).
    kokler = {CORE_ROOT.resolve()}
    try:
        if (PROJ / "core").exists():
            kokler.add((PROJ / "core").resolve())
    except OSError:
        pass
    for core in kokler:
        if gercek == core or core in gercek.parents:
            return True, f"ÇEKİRDEK dosyası (core/{gercek.relative_to(core).as_posix()})"
    m = _CORE_KOPYA_DAMGA.search(metin)
    if m:
        return True, f"ÇEKİRDEK kopyası (team_setup üretti; kaynak {m.group(1)})"
    return False, "PROJE dosyası"


def _frontmatter_kontrol() -> list[Sonuc]:
    """4g — `.claude/{agents,commands,skills,rules}` + `claude-local/<tür>` frontmatter'ı.

    ⛔ ÖLÇÜLEMEDİ ≠ TEMİZ: ortak modül yüklenemezse FAIL (neden yazılı); okunamayan dosya WARN.
    UYARI sınıfı (`*`/`&` ile başlayan tırnaksız değer — çekirdeğin eski `paths:` biçimi;
    güncellenmemiş kopyalarda/proje kurallarında kalabilir) WARN DEĞİL, özet satırında sayılıp
    basılır (lider kararı 2026-10-18): aksi hâlde HER kurulu makinede
    K4 kalıcı sarıya boyanır ve uyarı körlüğü üretir (bu dosyadaki önek-dalı notuyla aynı ilke).
    """
    try:
        from utils import frontmatter_lint as FM  # noqa: E402
    except Exception as e:  # noqa: BLE001
        return [(FAIL, f"frontmatter denetimi ÖLÇÜLEMEDİ — ortak modül yüklenemedi "
                       f"({type(e).__name__}: {e}); tanım dosyaları BU KOŞUMDA ölçülmedi "
                       f"(TEMİZ demek DEĞİL)")]
    r: list[Sonuc] = []
    sayac: dict[str, int] = {}
    bilgi: list[str] = []
    n_engel = 0
    for kok_ad in ("claude-local", ".claude"):
        for tur in FM.TURLER:
            d = PROJ / kok_ad / tur
            if not d.is_dir():
                continue
            for f in sorted(d.rglob("*.md")):
                rel = f.relative_to(d)
                tt = FM.tanim_turu(f"{tur}/{rel.as_posix()}")
                if tt is None:
                    continue
                gosterim = f"{kok_ad}/{tur}/{rel.as_posix()}"
                try:
                    with open(f, encoding="utf-8", errors="replace", newline="") as fh:
                        metin = fh.read()
                except OSError as e:
                    r.append((WARN, f"frontmatter: {gosterim} okunamadı ({type(e).__name__}) — "
                                    f"ÖLÇÜLEMEDİ"))
                    continue
                if kok_ad == ".claude":
                    # overlay kopyası = claude-local kaynağının damgasız kopyası → bulgu bir kez
                    kaynak = PROJ / "claude-local" / tur / rel
                    try:
                        if kaynak.is_file() and kaynak.read_bytes() == f.read_bytes():
                            continue
                    except OSError:
                        pass
                sayac[tt[0]] = sayac.get(tt[0], 0) + 1
                cekirdek, etiket = _frontmatter_kaynagi(f, metin)
                for b in FM.bulgular(metin, tt[1]):
                    if b.seviye != FM.ENGEL:
                        bilgi.append(f"{gosterim}:{b.satir}")
                        continue
                    n_engel += 1
                    if cekirdek:
                        yol = (f"{etiket} — DOKUNMA: düzeltmesi çekirdekte yapılır; çekirdek "
                               f"hatası olarak bildir (core/playbook/howto-cekirdek-bulgu-bildirimi.md)")
                    else:
                        yol = (f"{etiket} — öneri: `{b.oneri}` (kullanıcıya göster, onayla "
                               f"uygula; otomatik düzeltme YOK)")
                    r.append((WARN, f"frontmatter GEÇERSİZ — {gosterim}:{b.satir} — {b.sorun} "
                                    f"({FM.satir_sonu_notu(metin)}) · {yol}"))
    toplam = sum(sayac.values())
    dokum = " · ".join(f"{t} {sayac.get(t, 0)}" for t in FM.TURLER)
    bilgi_notu = (f" · bilinen biçim (UYARI sınıfı, WARN değil — `*`/`&` ile başlayan tırnaksız "
                  f"değer; LF'te yükleniyor, CRLF'te kural KOŞULSUZ yüklenir — tırnakla) "
                  f"{len(bilgi)}: "
                  + ", ".join(bilgi[:6]) + (" …" if len(bilgi) > 6 else "")) if bilgi else ""
    kapsam = (f"[KAPSAM: .claude/<tür> + claude-local/<tür>; kullanıcı düzeyi ~/.claude BAKILMADI · "
              f"düzey 2: {FM.duzey2_durumu()} · {FM.KAPSAM_BEYANI}]")
    if toplam == 0:
        r.append((SKIP, f"frontmatter: taranacak tanım dosyası YOK (yüzey boş — 'geçerli' "
                        f"demek değildir) {kapsam}"))
    elif n_engel:
        r.append((WARN, f"frontmatter: {toplam} tanım dosyasında {n_engel} GEÇERSİZ satır "
                        f"({dokum}){bilgi_notu} {kapsam}"))
    else:
        r.append((PASS, f"frontmatter: {toplam} tanım dosyası geçerli ({dokum}){bilgi_notu} "
                        f"{kapsam}"))
    return r


# ⛔ ELLE TUTULAN KOPYA KALDIRILDI (2026-08-29, infra-findings 2026-08-22 "M11").
# Eskiden burada şu satır vardı:
#     _GUARD_KORUDUGU_TOOLLAR = ("Bash","PowerShell","Edit","Write","MultiEdit","NotebookEdit")
# Bu, `pre_tool_guard`ın koruduğu tool kümesinin İKİNCİ bir gerçeğiydi. Aynı olgu iki
# yerde yaşarsa biri bayatlar — ve BAYATLAMIŞTI: ölçüldü (2026-08-29) ki guard kodu
# bugün 16 tool adını işliyor, elle liste yalnız 6'sını taşıyordu ⇒ 10 MCP tool'u
# (`mcp__sap-adt__adt_push_source`, `…adt_activate`, `…adt_post_shell` …) ix_doctor'un
# kablolama kontrolünde HİÇ denetlenmiyordu. Kontrolün "guard'ın koruduğu 6 tool'un
# TAMAMI matcher'da" cümlesi doğruydu ama PAYDASI yanlıştı — sessiz kapsam kaybı.
# Küme artık `check_rule_gate_coverage.hook_tool_adlari()` ile guard'ın KENDİ AST'inden
# türetilir (N3'ün zaten kullandığı, bloklayan gate'teki okuyucu — kopya DEĞİL, ORTAK).
def _guard_korudugu_toollar() -> tuple[set[str], list[str], str]:
    """(tool kümesi, önek dalları, hata) — `pre_tool_guard`ın KODUNDAN türetilir.

    ⛔ ÖLÇÜLEMEDİ ≠ TEMİZ: türetme başarısız olursa (import kırık · hook
    ayrıştırılamıyor · yazım tanınmıyor) BOŞ küme dönmez — hata metni döner ve
    çağıran bunu PASS'a değil, ölçüm-hatasına çevirir. Boş küme dönseydi kontrol
    "0 tool'un tamamı matcher'da" diyerek SESSİZCE yeşile düşerdi (ölü gate).
    """
    import sys as _sys
    vdir = Path(__file__).resolve().parent / "validators"
    if str(vdir) not in _sys.path:
        _sys.path.insert(0, str(vdir))
    try:
        from check_rule_gate_coverage import hook_tool_adlari  # type: ignore
    except Exception as e:  # noqa: BLE001
        return set(), [], f"türetme modülü yüklenemedi ({type(e).__name__}: {e})"
    try:
        adlar, onekler, korler, hatalar, _olculemeyen = hook_tool_adlari()
    except Exception as e:  # noqa: BLE001
        return set(), [], f"hook AST taraması düştü ({type(e).__name__}: {e})"
    kume = adlar.get("pre_tool_guard", set())
    if not kume:
        # Guard'ın tool ayrımı okunamıyor: kör yazım ya da ayrıştırma hatası.
        neden = next((m for m in list(korler) + list(hatalar) if "pre_tool_guard" in m),
                     "pre_tool_guard kodunda tool adı ÇIKARILAMADI")
        return set(), onekler.get("pre_tool_guard", []), neden
    return set(kume), onekler.get("pre_tool_guard", []), ""


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

    korunan, onekler, turetme_hatasi = _guard_korudugu_toollar()
    if turetme_hatasi:
        # ⛔ SESSİZ YEŞİL YOK: küme türetilemediyse kontrol KOŞMADI demektir.
        r.append((FAIL, f"kablolama ÖLÇÜLEMEDİ: pre_tool_guard'ın koruduğu tool kümesi "
                        f"KODDAN türetilemedi → {turetme_hatasi}. Bu 'kablolama temiz' "
                        f"DEĞİLDİR; önce türetmeyi onar."))
        return r

    kapsanmayan = []
    for tool in sorted(korunan):
        if not any(re.fullmatch(m, tool) for m in matcherlar):
            kapsanmayan.append(tool)
    if kapsanmayan:
        r.append((FAIL, f"kablolama DELİK: guard bu tool'ları kodda koruyor ama matcher yönlendirmiyor "
                        f"→ {', '.join(kapsanmayan)}. Kod-seviyesi koruma, kablolanmadan KORUMA DEĞİLDİR."))
    else:
        # ⚠ PAYDA ÇIKTIYA BASILIR: "hepsi kapsandı" cümlesi payda görünmeden okunamaz
        # (M11'in ta kendisi: payda 6'ya düşmüştü ve cümle yine "tamamı" diyordu).
        # ⚠ PAYDA ÇIKTIYA BASILIR: "hepsi kapsandı" cümlesi payda görünmeden okunamaz
        # (M11'in ta kendisi: payda 6'ya düşmüştü ve cümle yine "tamamı" diyordu).
        # ⛔ ÖNEK DALLARI SESSİZ ATLANMAZ ama BULGU da değildir: enumere edilemez
        # olmaları YAPISAL bir sınırdır, onarılacak bir kusur değil. Kardeş gate
        # (`check_rule_gate_coverage`) da bunu bilgi satırı olarak basar, bulgu
        # saymaz — ayrı bir WARN üretmek her koşumda katman 4'ü sarıya boyar ve
        # uyarı körlüğü üretirdi (bu evde ölçülmüş sınıf).
        onek_notu = (f" · {len(onekler)} önek dalı ENUMERE EDİLEMEZ "
                     f"({', '.join(onekler)}) ⇒ o dalın kapsamı ÖLÇÜLMEDİ" if onekler else "")
        r.append((PASS, f"kablolama: guard'ın koruduğu {len(korunan)} tool'un tamamı "
                        f"PreToolUse matcher'ında ({len(matcherlar)} blok) "
                        f"[küme pre_tool_guard.py'den TÜRETİLDİ, elle liste YOK]{onek_notu}"))
    return r


# ---------------------------------------------------------------- 4h / 4i / 4j (Q406)
# NEDEN VAR (Q406, 2026-11-12, kullanıcı onayı): şablon 16 kanca bağlar; ix_doctor bunların
# yalnız 2'sini koşuyor (4d), yalnız 1'inin matcher'ına bakıyordu (4f); 4a tüm dosyayı tek
# imzayla kıyasladığı için bir kancanın DÜŞMESİ ile zararsız bir proje eki AYNI ad vermeyen
# WARN'ı basıyordu (ölçüldü: geçici kopyadan `recall_inject` silindi → yalnız "template'ten
# SAPMIŞ"; aynı WARN'ı başka bir tüketici yalnız kanca-dışı farkla da veriyordu).
# ⛔ GATE DEĞİL (ADR 0019): ix_doctor teşhistir — projeyi ve ayarları DEĞİŞTİRMEZ; yalnız
# `.tmp` altına yazar (4i smoke log satırları, 4j recall indeksini tazeleyebilir). Onarım AYRI
# ve açık onaylı yoldur (`team_setup --tazele-settings`, howto-cekirdek-guncelleme §6a ①).
# ⛔ ÖLÇÜLEMEDİ ≠ TEMİZ: modül/dosya okunamazsa satır PASS DEMEZ.
_TAZELE_SETTINGS = "python core/scripts/team_setup.py --tazele-settings"
_KANCA_KAPSAM = ("kapsam: YALNIZ .claude/settings.json'daki (olay, eşleyici, kanca adı) üçlüsü "
                 "şablona karşı (birleşik eşleyici ⊇ kapsama sayılır); settings.local.json yalnız "
                 "disableAllHooks + kanca VARLIĞI için okunur, birleştirilmez; kullanıcı ayarı "
                 "(~/.claude/settings.json), managed policy ve plugin kancaları OKUNMADI — bunlar "
                 "kancaları sessizce kapatabilir/ekleyebilir (ADR 0023 İkincil gerekçeler 1); "
                 "komut yorumlayıcısı 1g'de, kancanın ÇALIŞMASI 4i'de ölçülür; permissions/env/"
                 "statusLine bu satırda BAKILMADI")
_SMOKE_4D = ("session_start", "pre_tool_guard")     # 4d'de zaten koşulur (bugünkü ölçüt)
_SMOKE_KAPSAM = ("kapsam: zararsız örnek girdi — blok/yazma dalı TETİKLENMEZ, kancanın kararı "
                 "ölçülmez; çıktı İÇERİĞİ yalnız yan etkisiz sondası olan kancalarda ölçülür; "
                 "shim dışı proje kancaları (`?<komut>`) KOŞULMAZ; "
                 "yan etki: .tmp/instructions-loaded.log ve .tmp/config-changes.log'a birer "
                 "`ix_doctor_smoke` satırı (inspector A1 bu satırları SAYMAZ; session_start "
                 "YÜKLEME satırı yalnız sid'li satırı sayar)")
# 1g ile AYNI ölçüm sınırı — 4i yorumlayıcı FAIL'leri de taşır (F2b, 2026-11-12).
_PATH_SINIRI = ("yorumlayıcı ix_doctor sürecinin PATH'iyle çözüldü — Claude Code'un hook "
                "ortamının PATH'i ÖLÇÜLMEDİ")


def _kanca_modulu():
    from utils import kanca_kablolari as KK  # type: ignore  # CORE_ROOT/scripts sys.path'te
    return KK


def _json_oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _yerel_ayar_kancalari(yerel: Path, KK) -> list[Sonuc]:
    """settings.local.json (gitignore'lu, makine-yerel) — SALT-OKUR, WARN-only (F2a).

    Kıyasa girmez ve FAIL üretmez: Claude Code'un local katmanı settings.json ile nasıl
    birleştirdiği burada ÖLÇÜLMEDİ. Yalnız kancaları sessizce kapatabilecek/ekleyebilecek
    iki işaret görünür kılınır (ADR 0023 İkincil gerekçeler 1: local katmandaki kapatma
    repoda, CI'da, guard'da iz bırakmaz)."""
    if not yerel.is_file():
        return []
    try:
        v = _json_oku(yerel)
    except Exception as e:  # noqa: BLE001
        return [(WARN, f"settings.local.json OKUNAMADI ({type(e).__name__}) — local katmandaki "
                       f"kanca/disableAllHooks ÖLÇÜLEMEDİ (temiz demek DEĞİL)")]
    r: list[Sonuc] = []
    if KK.hepsi_kapali(v) or KK.kapali_belirsiz(v) is not None:
        r.append((WARN, f"settings.local.json `disableAllHooks: {v.get('disableAllHooks')!r}` — "
                        f"bu makinede kancalar KAPALI olabilir (pre_tool_guard dahil); repoda/CI'da "
                        f"iz bırakmaz. Birleştirme davranışı ÖLÇÜLMEDİ; bilinçli değilse anahtarı "
                        f"kaldır (§6a ②: kullanıcıya sor)"))
    yb = KK.baglantilar(v) if isinstance(v, dict) else []
    if yb:
        r.append((WARN, f"settings.local.json {len(yb)} kanca bağlantısı taşıyor ("
                        + ", ".join(KK.bicim(b) for b in yb[:4]) + (" …" if len(yb) > 4 else "")
                        + ") — 4h kıyasına ve 4i smoke'a GİRMEDİ (makine-yerel, ölçülmedi)"))
    return r


def _kanca_kablolama(ayar: Path | None = None, sablon: Path | None = None) -> list[Sonuc]:
    """4h — şablondaki HER kanca bağlantısı projede var mı (ad düzeyi)."""
    ayar = ayar or PROJ / ".claude" / "settings.json"
    sablon = sablon or CORE_ROOT / "claude" / "settings.template.json"
    try:
        KK = _kanca_modulu()
    except Exception as e:  # noqa: BLE001
        return [(FAIL, f"kanca kablolaması ÖLÇÜLEMEDİ — utils.kanca_kablolari yüklenemedi "
                       f"({type(e).__name__}: {e}); TEMİZ demek DEĞİL")]
    if not ayar.is_file():
        return [(FAIL, f"kanca kablolaması: .claude/settings.json YOK — HİÇBİR kanca kablolu "
                       f"değil (pre_tool_guard dahil). Onarım (§6a ①): python core/scripts/"
                       f"team_setup.py (şablondan üretir)")]
    try:
        p, s = _json_oku(ayar), _json_oku(sablon)
    except Exception as e:  # noqa: BLE001
        return [(FAIL, f"kanca kablolaması ÖLÇÜLEMEDİ — settings/şablon okunamadı "
                       f"({type(e).__name__}: {e}); TEMİZ demek DEĞİL")]
    r: list[Sonuc] = []
    if KK.hepsi_kapali(p):
        r.append((FAIL, "kanca kablolaması: settings.json `disableAllHooks: true` — kablolama ne "
                        "olursa olsun HİÇBİR kanca koşmaz (pre_tool_guard dahil = sessiz fail-open); "
                        "bilinçli değilse anahtarı kaldır (§6a ②: kullanıcıya sor)"))
    belirsiz = KK.kapali_belirsiz(p)
    if belirsiz is not None:
        r.append((WARN, f"kanca kablolaması: settings.json `disableAllHooks` bool DEĞİL "
                        f"({belirsiz!r}) — Claude Code'un bu değeri nasıl yorumladığı ÖLÇÜLMEDİ "
                        f"(kancaları kapatabilir ya da ayar dosyasını reddedebilir); bool yaz ya da "
                        f"anahtarı kaldır (§6a ②: kullanıcıya sor)"))
    r.extend(_yerel_ayar_kancalari(ayar.with_name("settings.local.json"), KK))
    k = KK.kiyas(p, s)
    n, adet = k["sablon_sayisi"], len(k["sablon_kanca"])
    ek = (f" · proje eki {len(k['ek'])} (BİLGİ, WARN değil — onarım SİLMEZ): "
          + ", ".join(KK.bicim(b) for b in k["ek"][:6]) + (" …" if len(k["ek"]) > 6 else "")
          if k["ek"] else "")
    if k["kapsanan"]:
        ek += (f" · birleşik eşleyiciyle KAPSANAN {len(k['kapsanan'])}: "
               + ", ".join(KK.bicim(b) for b in k["kapsanan"][:6]))
    for b, komut in k["bicim_farki"]:
        r.append((WARN, f"kanca {b[2]} ({b[0]}) TANINMAYAN biçimde kablolu: `{komut[:120]}` — ad "
                        f"ayrıştırılamadı (hook_shim.py kanca adını İLK argüman sayar); EKSİK "
                        f"sayılmadı, onarım EKLEMEZ (çift koşum olurdu); şablon biçimiyle "
                        f"karşılaştır (§6a ②) [{_KANCA_KAPSAM}]"))
    if k["eksik"]:
        r.append((FAIL, f"kanca kablolaması: şablonun {n} bağlantısından {len(k['eksik'])}'i "
                        f"projede YOK → " + ", ".join(KK.bicim(b) for b in k["eksik"])
                        + f" — bu kancalar HİÇ koşmaz. Onarım (§6a ①): {_TAZELE_SETTINGS} "
                          f"(yalnız EKSİKLERİ ekler, proje eklerine dokunmaz; önce fark + yedek), "
                          f"sonra `python core/scripts/ix_doctor.py --layer 4`{ek} [{_KANCA_KAPSAM}]"))
    for b, p_eslik in k["eslesik_farki"]:
        r.append((WARN, f"kanca eşleyicisi şablondan FARKLI: {b[2]} ({b[0]}) şablon `{b[1] or '-'}` "
                        f"↔ proje `{p_eslik or '-'}` — genişletme/daraltma olabilir, otomatik "
                        f"onarılmaz; şablonla karşılaştır (§6a ②) [{_KANCA_KAPSAM}]"))
    if not k["eksik"] and not KK.hepsi_kapali(p):
        r.append((PASS, f"kanca kablolaması: şablonun {n} bağlantısının ({adet} kanca) tamamı "
                        f"projede{ek} [{_KANCA_KAPSAM}]"))
    return r


def _smoke_ornekleri(token: str) -> dict[str, tuple[dict, tuple | None]]:
    """Kanca → (zararsız örnek stdin, içerik beklentisi). Beklenti: None (yalnız temiz çıkış) ·
    ("stdout", parça) · ("log", proje-göreli dosya, parça). ⛔ Şablona kanca eklenince buraya da
    örnek eklenir — eklenmezse 4i "örnek tanımsız" FAIL'i basar (korpus T1 çiviler)."""
    yaz = str(PROJ / ".tmp" / "ix_doctor_smoke.txt")
    w = {"tool_name": "Write", "tool_input": {"file_path": yaz, "content": ""}}
    kisa = {"prompt": "ix_doctor smoke"}
    return {
        "tooling_radar_check": ({}, None),
        "instructions_loaded_log": ({"hook_event_name": "InstructionsLoaded",
                                     "file_path": f"<ix_doctor_smoke {token}>",
                                     "memory_type": "Project", "load_reason": "ix_doctor_smoke"},
                                    ("log", ".tmp/instructions-loaded.log", token)),
        "skill_injector": (kisa, None),
        "intake_triage": (kisa, None),
        "recall_inject": (kisa, None),                 # içerik sondası 4j'de
        "infra_write_guard": (w, None),
        "pull_before_edit": (w, None),
        "sap_worktype_hint": ({"tool_name": "Read", "tool_input": {}}, None),
        "itg_backstop": ({"tool_name": "mcp__sap-adt__ping", "tool_input": {}}, None),
        "watchdog_launch": ({"tool_name": "Read", "tool_input": {}}, None),
        "post_validate": ({"tool_name": "Write", "tool_input": {"file_path": yaz},
                           "tool_response": {}}, None),
        "post_tool_failure": ({"tool_name": "Read", "tool_input": {}, "tool_response": "ok"}, None),
        "config_change_guard": ({"hook_event_name": "ConfigChange",
                                 "source": f"ix_doctor_smoke {token}"},
                                ("log", ".tmp/config-changes.log", token)),
        "pre_compact": ({"hook_event_name": "PreCompact", "trigger": "manual"},
                        ("stdout", '"systemMessage"')),
    }


def _smoke_yorumlayici(veri: dict, KK) -> tuple[str | None, Sonuc | None, str]:
    """Kanca komutlarının yorumlayıcısı (Claude Code'un çözeceği gibi, PATH'le).

    -> (yol | None, satır | None, not). None yol = `sys.executable` yedeği (kanca KODU yine
    ölçülür; yorumlayıcı arızası AYRI satırdır — §6a ② ile ③ karışmasın)."""
    adlar: dict[str, int] = {}
    for bloklar in (veri.get("hooks") or {}).values():
        for blok in bloklar if isinstance(bloklar, list) else []:
            for kanca in (blok.get("hooks") or []) if isinstance(blok, dict) else []:
                if not isinstance(kanca, dict) or not KK.shim_kancasi_mi(KK.kanca_adi(kanca)):
                    continue
                kom = str(kanca.get("command") or "").strip()
                if "args" not in kanca:
                    m = re.match(r'\s*"([^"]+)"|\s*(\S+)', kom)
                    kom = (m.group(1) or m.group(2)) if m else kom
                adlar[kom] = adlar.get(kom, 0) + 1
    if not adlar:
        return None, None, "yorumlayıcı: settings'te shim komutu yok → sys.executable"
    ad, adet = max(adlar.items(), key=lambda x: x[1])
    if _YORUMLAYICI_DEGISKEN.search(ad):
        return None, (SKIP, f"kanca smoke yorumlayıcısı `{ad}` ÖLÇÜLEMEDİ — genişletilmemiş "
                            f"değişken; smoke sys.executable ile koşuldu (temiz demek DEĞİL)"), \
            "yorumlayıcı ÖLÇÜLEMEDİ → sys.executable"
    yol = ad if ("/" in ad or "\\" in ad) else shutil.which(ad)
    if not yol:
        return None, (FAIL, f"kanca smoke: yorumlayıcı `{ad}` PATH'te YOK — settings'teki {adet} "
                            f"kanca komutu HİÇ başlamaz (pre_tool_guard bloklamaz = sessiz "
                            f"fail-open). §6a ②: Python kur / PATH'i düzelt (1g satırı). Kanca "
                            f"KODU aşağıda sys.executable ile ayrıca ölçüldü [{_PATH_SINIRI}]"), \
            "yorumlayıcı YOK → sys.executable yedeği"
    if not _YORUMLAYICI_PY_AILE.fullmatch(re.split(r"[\\/]", ad)[-1]):
        return None, (SKIP, f"kanca smoke yorumlayıcısı `{ad}` python ailesi DEĞİL — başlama "
                            f"ölçülmedi; smoke sys.executable ile koşuldu (temiz demek DEĞİL)"), \
            "yorumlayıcı python dışı → sys.executable"
    rc, out = _run([yol, "-c", f"print('{_YORUMLAYICI_ISARET}')"], timeout=30)
    if rc != 0 or _YORUMLAYICI_ISARET not in out:
        son = next((s.strip() for s in reversed(out.splitlines()) if s.strip()), "çıktı yok")
        return None, (FAIL, f"kanca smoke: yorumlayıcı `{ad}` → {yol} BAŞLAMIYOR (rc={rc}: "
                            f"{son[:90]!r}) — {adet} kanca komutu HİÇ çalışmaz (sessiz fail-open). "
                            f"§6a ②: gerçek Python'u PATH'te öne al (1g satırı). Kanca KODU aşağıda "
                            f"sys.executable ile ayrıca ölçüldü [{_PATH_SINIRI}]"), \
            "yorumlayıcı BAŞLAMIYOR → sys.executable yedeği"
    return yol, None, f"yorumlayıcı `{ad}` → {yol}"


def _smoke_sorunu(rc: int, out: str, beklenti: tuple | None) -> tuple[str, str] | None:
    """-> None (temiz) ya da (§6a sınıfı, açıklama)."""
    son = next((s.strip() for s in reversed(out.splitlines()) if s.strip()), "çıktı yok")[:110]
    if "CORE JUNCTION KOPUK" in out:
        return "①", ("shim çekirdek kancasını BULAMADI (core junction kopuk/eksik) — onarım: "
                      "python core/scripts/team_setup.py --repair-junctions")
    if "Traceback (most recent call last)" in out:
        return "③", f"kanca ÇÖKTÜ (Traceback, exit {rc}): {son!r}"
    if "GIRDI-PARSE-EDILEMEDI" in out:
        return "③", "örnek girdi OKUNAMADI (kanca stdin'i ayrıştıramadı)"
    if rc != 0:
        return "③", f"zararsız girdide exit {rc} (0 beklenir): {son!r}"
    if beklenti and beklenti[0] == "stdout" and beklenti[1] not in out:
        return "③", f"fail-open kanca SESSİZ kaldı — beklenen {beklenti[1]} çıktısı yok"
    if beklenti and beklenti[0] == "log":
        try:
            metin = (PROJ / beklenti[1]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            metin = ""
        if beklenti[2] not in metin:
            return "③", (f"fail-open kanca SESSİZ kaldı — {beklenti[1]}'e smoke satırı YAZILMADI "
                          f"(yazma hatası kancada sessizce yutuluyor)")
    return None


def _kanca_smoke(ayar: Path | None = None) -> list[Sonuc]:
    """4i — kablolu + şablondaki HER kanca gerçek giriş noktasından (`scripts/hook_shim.py
    <kanca>`, settings'teki yorumlayıcıyla) zararsız örnek girdiyle koşulur."""
    ayar = ayar or PROJ / ".claude" / "settings.json"
    try:
        KK = _kanca_modulu()
        s = _json_oku(CORE_ROOT / "claude" / "settings.template.json")
    except Exception as e:  # noqa: BLE001
        return [(FAIL, f"kanca smoke ÖLÇÜLEMEDİ — modül/şablon okunamadı ({type(e).__name__}: "
                       f"{e}); TEMİZ demek DEĞİL")]
    try:
        p = _json_oku(ayar) if ayar.is_file() else None
    except Exception:  # noqa: BLE001
        p = None                                     # 4h ÖLÇÜLEMEDİ der; smoke şablonla sürer
    sablon_adlar = [a for a in KK.kiyas({}, s)["sablon_kanca"] if KK.shim_kancasi_mi(a)]
    adlar = list(sablon_adlar)
    shim_disi: list[str] = []
    for _o, _m, a in KK.baglantilar(p or {}):
        if KK.shim_kancasi_mi(a):
            if a not in adlar:
                adlar.append(a)
        elif a not in shim_disi:
            shim_disi.append(a)
    yol, ysatir, ynot = _smoke_yorumlayici(p if p is not None else s, KK)
    r: list[Sonuc] = [ysatir] if ysatir else []
    if shim_disi:
        # F2c: shim'e gitmeyen proje kancası koşulmaz (örnek girdisi/beklentisi bilinmez) —
        # ölçülmediği SESSİZCE düşmesin, satırda ve özette sayılsın.
        r.append((SKIP, f"kanca smoke ÖLÇÜLMEDİ — shim dışı {len(shim_disi)} proje kancası: "
                        + ", ".join(f"`{a[1:][:70]}`" for a in shim_disi[:4])
                        + (" …" if len(shim_disi) > 4 else "")
                        + " (scripts/hook_shim.py'den geçmez; temiz demek DEĞİL)"))
    token = f"{os.getpid()}-{int(time.time() * 1000)}"
    ornek = _smoke_ornekleri(token)
    gecen: list[str] = []
    icerik: list[str] = []
    n_fail = orneksiz = 0
    for ad in adlar:
        if ad in _SMOKE_4D:
            continue
        if ad not in ornek:
            if ad in sablon_adlar:
                n_fail += 1
                r.append((FAIL, f"kanca smoke `{ad}`: şablon kancası için örnek girdi TANIMSIZ "
                                f"(ix_doctor `_smoke_ornekleri` şablonun gerisinde) — ölçülemedi; "
                                f"§6a ③ çekirdek hatası"))
            elif not (PROJ / "core" / "scripts" / "hooks" / f"{ad}.py").is_file():
                n_fail += 1
                r.append((FAIL, f"kanca `{ad}` projede KABLOLU ama çekirdekte YOK "
                                f"(core/scripts/hooks/{ad}.py) — her olayda shim hata basar; "
                                f"çekirdekten kaldırılmış bir kanca olabilir: kablosu kaldırılsın mı "
                                f"kullanıcıya sor (§6a ②)"))
            else:
                orneksiz += 1
                r.append((SKIP, f"kanca smoke `{ad}` ÖLÇÜLMEDİ — proje eki, örnek girdi tanımsız "
                                f"(temiz demek DEĞİL)"))
            continue
        stdin, beklenti = ornek[ad]
        rc, out, _sure = _hook_kos(ad, stdin, timeout=60, yorumlayici=yol)
        sorun = _smoke_sorunu(rc, out, beklenti)
        if sorun:
            n_fail += 1
            sinif, aciklama = sorun
            ek = (" — çekirdek dosyasına DOKUNMA; core/playbook/howto-cekirdek-bulgu-bildirimi.md"
                  if sinif == "③" else "")
            r.append((FAIL, f"kanca smoke `{ad}` FAIL — {aciklama} · §6a {sinif}{ek}"))
        else:
            gecen.append(ad)
            if beklenti:
                icerik.append(ad)
    toplam = len([a for a in adlar if a not in _SMOKE_4D]) + len(shim_disi)
    olcmedi = (f" · ÖLÇÜLMEDİ {orneksiz + len(shim_disi)} (shim dışı {len(shim_disi)}, "
               f"örneksiz proje eki {orneksiz})" if orneksiz or shim_disi else "")
    ozet = (f"kanca smoke: {len(gecen)}/{toplam} kanca gerçek giriş noktasından "
            f"(scripts/hook_shim.py <kanca>; {ynot}) temiz çıktı{olcmedi} · içerik ölçülen: "
            f"{', '.join(icerik) or 'yok'} · session_start + pre_tool_guard 4d'de [{_SMOKE_KAPSAM}]")
    r.append((FAIL, f"{ozet} — {n_fail} sorun yukarıda") if n_fail else (PASS, ozet))
    return r


_RECALL_DENEME = 3
_RECALL_KAPSAM = ("kapsam: kanca kablosu + .tmp/recall-index.json (var · JSON · kayıt · tazelik "
                  "= build_recall_index.kaynak_mtime) + .tmp/recall-index.status + gerçek giriş "
                  "noktasından en çok 3 örnek prompt'un ÇIKTI İÇERİĞİ (biri dönerse yeter); "
                  "isabet oranı ÖLÇÜLMEDİ; yan etki: projeyi ve ayarları DEĞİŞTİRMEZ, yalnız .tmp "
                  "altına yazar — indeks YOK/BAYAT ise kancanın kendi tazelemesini tetikler")


def _recall_indeks_durumu(idx: Path) -> tuple[str, list]:
    """-> (YOK | BOZUK | BOŞ | BAYAT | TAZE | TAZELİK-ÖLÇÜLEMEDİ, kayıtlar)."""
    if not idx.is_file():
        return "YOK", []
    try:
        kayit = json.loads(idx.read_text(encoding="utf-8")).get("kayit") or []
    except Exception:  # noqa: BLE001
        return "BOZUK", []
    if not kayit:
        return "BOŞ", []
    try:
        import build_recall_index as B  # type: ignore  # CORE_ROOT/scripts sys.path'te
        return ("TAZE" if idx.stat().st_mtime >= B.kaynak_mtime(PROJ) else "BAYAT"), kayit
    except Exception:  # noqa: BLE001
        return "TAZELİK-ÖLÇÜLEMEDİ", kayit


def _recall_saglik() -> list[Sonuc]:
    """4j — fail-open `recall_inject` sağlığı: kablo · indeks · status · ÖRNEK PROMPT İÇERİĞİ.

    ⛔ exit 0 kanıt DEĞİLDİR: kanca indeks yok/bozukken de 0 döner. Ölçüt, gerçek giriş
    noktasından koşulan örnek prompt'un `[JIT-RECALL]` + indeksteki bir kaydın başlığını
    DÖNDÜRMESİDİR. Örnek prompt `session_id`/`transcript_path` TAŞIMAZ ⇒ oturum-içi tekrar
    bastırma kaydı (`.tmp/recall-shown/`) yazılmaz."""
    idx = PROJ / ".tmp" / "recall-index.json"
    st = PROJ / ".tmp" / "recall-index.status"
    try:
        KK = _kanca_modulu()
        ayar = PROJ / ".claude" / "settings.json"
        kablolu = ("recall_inject" in {a for _o, _m, a in KK.baglantilar(_json_oku(ayar))}
                   if ayar.is_file() else False)
    except Exception:  # noqa: BLE001
        kablolu = None
    once, _ = _recall_indeks_durumu(idx)
    # İndeks yok/bayatsa kancanın KENDİ tazeleme yolu (Q287) gerçek giriş noktasından
    # tetiklenir: ≥40 karakterlik nötr prompt. Bozuk-ama-taze indeksi kanca yeniden ÜRETMEZ.
    if once in ("YOK", "BAYAT", "BOŞ", "TAZELİK-ÖLÇÜLEMEDİ"):
        _hook_kos("recall_inject", {"prompt": "ix_doctor recall saglik sondasi: indeks tazeleme "
                                              "tetigi (notr metin)"}, timeout=120)
    sonra, kayitlar = _recall_indeks_durumu(idx)
    try:
        durum = json.loads(st.read_text(encoding="utf-8")) if st.is_file() else {}
    except Exception:  # noqa: BLE001
        durum = {"sonuc": "OKUNAMADI"}
    st_ozet = (f"status sonuc={durum.get('sonuc', '<YOK>')} zaman={durum.get('zaman', '?')}"
               + (f" hata={str(durum.get('hata'))[:80]!r}" if durum.get("hata") else ""))
    onarim = "Onarım (§6a ①): python core/scripts/build_recall_index.py, sonra --layer 4"
    if not kayitlar:
        return [(FAIL, f"recall_inject sağlığı: indeks {sonra} (önce {once}) — kanca öneri "
                       f"ÜRETEMEZ ve fail-open olduğu için SESSİZDİR; {st_ozet}. {onarim} "
                       f"[{_RECALL_KAPSAM}]")]
    # Ö3 (2026-11-12): TEK sabit kayıt yanlış FAIL üretir — ölçüldü, gerçek indekslerde
    # kayıtların bir kısmı kendi başlığıyla sorulunca dönmüyor (62'de 1-3). Sırayla en çok
    # _RECALL_DENEME kayıt (önce `how:`) denenir; BİRİ dönerse kanca canlıdır, hiçbiri dönmezse FAIL.
    adaylar = ([k for k in kayitlar if str(k.get("id", "")).startswith("how:")]
               + [k for k in kayitlar if not str(k.get("id", "")).startswith("how:")])[:_RECALL_DENEME]
    denenen: list[str] = []
    for secim in adaylar:
        baslik = str(secim.get("baslik") or "")
        prompt = f"{baslik} {secim.get('oz') or ''}".strip()
        while len(prompt) < 60:
            prompt = f"{prompt} {baslik}".strip() or "ix_doctor recall sondasi"
        rc, out, _ = _hook_kos("recall_inject", {"prompt": prompt}, timeout=120)
        denenen.append(str(secim.get("id")))
        dondu = "[JIT-RECALL]" in out and baslik[:30] in out
        if dondu:
            break
    kablo = {True: "kablolu", False: "kablolu DEĞİL (4h)", None: "kablo ÖLÇÜLEMEDİ"}[kablolu]
    govde = (f"recall_inject sağlığı: {kablo} · indeks önce {once} → sonra {sonra} "
             f"({len(kayitlar)} kayıt) · {st_ozet} · örnek prompt (denenen {len(denenen)}: "
             f"{', '.join(denenen)}) ")
    if not dondu:
        son = next((s.strip() for s in reversed(out.splitlines()) if s.strip()), "çıktı yok")
        return [(FAIL, govde + f"HİÇBİRİ öneri DÖNDÜRMEDİ (son exit {rc}: {son[:90]!r}) — fail-open kanca "
                               f"SESSİZ; {onarim}; sürerse §6a ③ [{_RECALL_KAPSAM}]")]
    if kablolu is not True:
        return [(FAIL, govde + f"öneri DÖNDÜRDÜ ama kanca oturumda KOŞMAZ — onarım (§6a ①): "
                               f"{_TAZELE_SETTINGS} [{_RECALL_KAPSAM}]")]
    if sonra != "TAZE":
        return [(WARN, govde + f"öneri DÖNDÜRDÜ; indeks tazeliği {sonra} — {onarim} "
                               f"[{_RECALL_KAPSAM}]")]
    return [(PASS, govde + f"öneri DÖNDÜRDÜ (`[JIT-RECALL]` + `{baslik[:40]}`) [{_RECALL_KAPSAM}]")]


# ---------------------------------------------------------------- katman 5

_CONN_ZORUNLU = ("ADT_SAP_URL", "ADT_SAP_USER", "ADT_SAP_PASSWORD", "ADT_SAP_CLIENT")


def _mcp_import_kontrol() -> Sonuc:
    """5b2 — `mcp_servers.sap_adt.server` bu yorumlayıcıyla, `.mcp.json` sap-adt ORTAMIYLA
    (kullanıcı PYTHONPATH'i çalışma zamanındaki gibi EZİLİR) import edilebiliyor mu.

    ⛔ ÖLÇÜLEMEDİ ≠ TEMİZ: ortak yardımcı yüklenemezse PASS değil FAIL (neden yazılı).
    Başarısızlıkta mesaj, alt sürecin SON anlamlı satırını taşır (traceback başlığı DEĞİL).
    """
    try:
        from utils.mcp_import_denetimi import (mcp_import_denetimi, mcp_calisma_env,  # type: ignore
                                               onarim_metni, KAPSAM)
    except Exception as e:  # noqa: BLE001
        return (FAIL, f"MCP server import denetimi ÖLÇÜLEMEDİ — ortak yardımcı yüklenemedi "
                      f"({type(e).__name__}: {e}); import sağlığı BU KOŞUMDA ölçülmedi "
                      f"(TEMİZ demek DEĞİL)")
    ok, ayrinti = mcp_import_denetimi(CORE_ROOT, PROJ)
    ortam = mcp_calisma_env(CORE_ROOT, PROJ)[1]    # denetim ortamının kaynağı (.mcp.json / şablon)
    req = CORE_ROOT / "mcp_servers" / "sap_adt" / "requirements.txt"
    if ok:
        return (PASS, f"MCP server import edilebilir (import-ok; yorumlayıcı {sys.executable}; "
                      f"ortam {ortam}) [{KAPSAM}]")
    return (FAIL, f"MCP server IMPORT EDİLEMİYOR — {ayrinti} · sunucu açılmaz (oturumda "
                  f"sap-adt 'Connection closed'). Onarım: {onarim_metni(ayrinti, req, sys.executable)} "
                  f"(ortam {ortam}) [{KAPSAM}]")


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

    # 5b2 — MCP server IMPORT edilebiliyor mu (Q335-C, Issue #274). ⛔ `.conn_adt`'den
    #       BAĞIMSIZ koşar: dosya var ama import çöküyorsa sunucu hiç açılmaz (mcp 2.x
    #       vakası — 5b PASS, 5a bağlantısız projede FAIL'di ve kusuru HİÇBİR katman
    #       görmüyordu). Yöntem team_setup smoke'uyla ORTAK (`utils.mcp_import_denetimi`).
    r.append(_mcp_import_kontrol())

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
    from utils.claude_paths import auto_memory_dizini   # slug TEK KAYNAK (KAYIT S4)
    mem = auto_memory_dizini(PROJ) / "MEMORY.md"
    if mem.is_file() and mem.stat().st_size > 0:
        r.append((PASS, f"memory dolu: {mem} ({mem.stat().st_size} bayt)"))
    elif mem.is_file():
        r.append((WARN, f"MEMORY.md BOŞ: {mem} — tohumla: python core/scripts/seed_memory.py"))
    else:
        r.append((FAIL, f"memory YOK: {mem} — tohumla: python core/scripts/seed_memory.py"))

    # 7a2 — memory git (yeni-proje akışı denetimi F4, 2026-10-03): CLAUDE.core §1.1 gün-sonu
    # adımı memory'yi "kendi PRIVATE remote'lu git'inde" varsayar, ama tohum (seed_memory)
    # dizini git'siz doğurur ⇒ yedeksiz tek kopya. ⛔ YALNIZ GÖZLEM: WARN, FAIL YOK —
    # yeni bir gate ADR 0019 moratoryumuna tabidir. Kapsam: `.git` VARLIĞI + en az bir remote
    # TANIMI; push'un yapılıp yapılmadığı ve remote'un private olduğu ÖLÇÜLMEZ.
    mem_dir = mem.parent
    kur = "kurulum: PROJECT_BOOTSTRAP STEP 3 (e′) memory git adımı"
    if not mem_dir.is_dir():
        r.append((SKIP, f"memory git denetimi atlandı — memory dizini yok ({mem_dir})"))
    elif not (mem_dir / ".git").exists():
        r.append((WARN, f"memory dizini git'siz: {mem_dir} — yedeksiz tek kopya "
                        f"(CLAUDE.core §1.1 gün-sonu memory commit+push varsayar); {kur}"))
    else:
        rc, out = _git(mem_dir, "remote")
        uzaklar = [s.strip() for s in out.splitlines() if s.strip()] if rc == 0 else []
        if rc != 0:
            r.append((WARN, f"memory git remote listesi ÖLÇÜLEMEDİ (git remote rc={rc}): {mem_dir}"))
        elif not uzaklar:
            r.append((WARN, f"memory git'i var ama remote YOK: {mem_dir} — push edilemez, yedeksiz; {kur}"))
        else:
            r.append((PASS, f"memory git + remote tanımlı ({', '.join(uzaklar)}) "
                            f"[kapsam: push/görünürlük ölçülmedi]"))

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
    (4, "CLAUDE KATMANI (drift/manifest/hook-smoke/frontmatter)"),
    (5, "MCP / SAP (.conn_adt/junction-erişim/import/canlı-probe)"),
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
