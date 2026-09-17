# -*- coding: utf-8 -*-
"""parity_probe.py - IKI MAKINE ARASI CLAUDE ORTAMI ESLIK OLCUMU (SALT-OKUNUR).

NE YAPAR: Bu makinedeki Claude Code calisma yuzeyinin parmak izini cikarir ve tek bir
JSON dosyasina yazar. Ayni script HER IKI makinede kosulur, JSON'lar diff'lenir
(kontrol grubu disiplini - PATTERN #19: ayni enstruman, iki vaka).

NE YAPMAZ: Hicbir proje/core dosyasini DEGISTIRMEZ. SAP'ye baglanmaz. Ag kullanimi
yalnizca ix_doctor'un kendi katmanlarindadir (--no-doctor ile kapatilir).
SIR YAZMAZ: .conn_adt ve settings.local.json ICERIGI rapora GIRMEZ - yalnizca
var-mi + sayim. --anon ile kullanici adi/host maskelenir.

KULLANIM (proje kokunde, ornegin C:\\IX\\<PROJE>):
    python parity_probe.py                 # tam olcum (ix_doctor + validators dahil)
    python parity_probe.py --no-doctor     # ix_doctor'u atla (hizli, agsiz)
    python parity_probe.py --anon          # kullanici adi/host maskele
Cikti: parity-<host>-<YYYYMMDD-HHMM>.json (proje kokune) + ekrana ozet.
"""
from __future__ import annotations
import argparse, hashlib, json, os, platform, re, socket, subprocess, sys, tempfile
from datetime import datetime
from pathlib import Path

SURUM = "parity_probe/1.2"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def run(cmd, cwd=None, timeout=60):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return {"rc": p.returncode, "out": (p.stdout or "").strip(),
                "err": (p.stderr or "").strip()[:500]}
    except FileNotFoundError:
        return {"rc": -1, "out": "", "err": "KOMUT YOK"}
    except subprocess.TimeoutExpired:
        return {"rc": -2, "out": "", "err": "TIMEOUT %ss" % timeout}
    except Exception as e:
        return {"rc": -3, "out": "", "err": "%s: %s" % (type(e).__name__, e)}


def sha16(p: Path):
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except Exception:
        return None


def hook_envanteri(settings: dict):
    out = []
    for ev, arr in (settings.get("hooks") or {}).items():
        for m in arr:
            for h in m.get("hooks", []):
                a = h.get("args") or []
                ad = Path(a[-1]).name if a else str(h.get("command", ""))[:30]
                out.append("%s:%s" % (ev, ad))
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Claude ortami eslik olcumu (salt-okunur)")
    ap.add_argument("--no-doctor", action="store_true", help="ix_doctor + validators kosumunu atla")
    ap.add_argument("--anon", action="store_true", help="kullanici adi / host maskele")
    ap.add_argument("--proje", default=".", help="proje koku (default: cwd)")
    ap.add_argument("--out", default=None, help="rapor dosyasi yolu (default: sistem temp)")
    a = ap.parse_args()

    if a.proje != ".":
        PROJ = Path(a.proje).resolve()
        koku_veren = "--proje"
    else:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from utils.project_config import project_root  # type: ignore
            PROJ = Path(project_root()).resolve()
            koku_veren = "utils.project_config.project_root()"
        except Exception as e:
            PROJ = Path.cwd().resolve()
            koku_veren = "cwd (project_config import HATASI: %s)" % type(e).__name__
    HOME = Path.home()
    CORE = PROJ / "core"
    C = PROJ / ".claude"
    R: dict = {"_surum": SURUM, "_zaman": datetime.now().isoformat(timespec="seconds")}

    def mask(s):
        if not a.anon or not s:
            return s
        s = str(s).replace(HOME.name, "<USER>")
        return re.sub(r"(?i)users[\\/][^\\/]+", "Users/<USER>", s)

    # ------------------------------------------------------------ 0. kimlik
    R["makine"] = {
        "host": "<HOST>" if a.anon else socket.gethostname(),
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "proje_koku": mask(str(PROJ)),
        "cwd_proje_mi": (PROJ / "CLAUDE.md").exists() and (PROJ / "project.yaml").exists(),
        "proje_koku_kaynagi": koku_veren,
    }

    # ------------------------------------------------------------ 1. harness
    cv = run(["claude", "--version"], timeout=30)
    us = HOME / ".claude" / "settings.json"
    ud = {}
    if us.exists():
        try:
            ud = json.loads(us.read_text(encoding="utf-8"))
        except Exception as e:
            ud = {"_parse_hatasi": str(e)}
    ucmd = HOME / ".claude" / "CLAUDE.md"
    ep = ud.get("enabledPlugins")
    R["harness"] = {
        "claude_version": cv["out"].splitlines()[0] if cv["out"] else "OLCULEMEDI (%s)" % cv["err"],
        "kullanici_settings_var": us.exists(),
        "kullanici_settings_anahtarlari": sorted(k for k in ud.keys()),
        "model": ud.get("model", "<yok>"),
        # autoMode ICERIGI org/host metni tasiyabilir -> yalnizca SEKLI raporlanir
        "autoMode": (("ayarli (anahtarlar: %s)" % ",".join(sorted(ud["autoMode"].keys())))
                     if isinstance(ud.get("autoMode"), dict)
                     else (str(ud.get("autoMode")) if "autoMode" in ud else "<yok>")),
        "enabledPlugins": sorted(ep.keys()) if isinstance(ep, dict) else (ep if ep is not None else "<yok>"),
        "kullanici_CLAUDE_md_var": ucmd.exists(),
        "kullanici_CLAUDE_md_bayt": ucmd.stat().st_size if ucmd.exists() else 0,
        "plugins_dizini_var": (HOME / ".claude" / "plugins").exists(),
    }

    # ------------------------------------------------------------ 2. proje claude katmani
    rules = sorted(p.name for p in (C / "rules").glob("*.md")) if (C / "rules").is_dir() else []
    core_kopya = C / "rules" / "00-claude-core.md"
    sj = C / "settings.json"
    sd = {}
    if sj.exists():
        try:
            sd = json.loads(sj.read_text(encoding="utf-8"))
        except Exception as e:
            sd = {"_parse_hatasi": str(e)}
    tpl = CORE / "claude" / "settings.template.json"
    td = {}
    if tpl.exists():
        try:
            td = json.loads(tpl.read_text(encoding="utf-8"))
        except Exception:
            pass
    kanca = hook_envanteri(sd)
    kanca_tpl = hook_envanteri(td)
    sl = C / "settings.local.json"
    sl_allow = -1
    if sl.exists():
        try:
            sl_allow = len(((json.loads(sl.read_text(encoding="utf-8"))).get("permissions") or {}).get("allow") or [])
        except Exception:
            sl_allow = -2
    cmd_md = PROJ / "CLAUDE.md"
    cmd_txt = cmd_md.read_text(encoding="utf-8", errors="replace") if cmd_md.exists() else ""
    R["claude_katmani"] = {
        "claude_dizini_var": C.is_dir(),
        "rules_dosyalari": rules,
        "core_kopyasi_var": core_kopya.exists(),
        "core_kopyasi_bayt": core_kopya.stat().st_size if core_kopya.exists() else 0,
        "core_kopyasi_sha16": sha16(core_kopya),
        "core_kopyasi_ilk_satir": (core_kopya.read_text(encoding="utf-8", errors="replace").splitlines() or [""])[0][:120] if core_kopya.exists() else None,
        "settings_json_var": sj.exists(),
        "kanca_sayisi": len(kanca),
        "kancalar": kanca,
        "template_kanca_sayisi": len(kanca_tpl),
        # OLCULEMEDI != TEMIZ: kaynak dosya yoksa "fark yok" DENMEZ
        "kanca_template_farki": (sorted(set(kanca) ^ set(kanca_tpl)) if (sj.exists() and tpl.exists())
                                 else ["OLCULEMEDI: %s yok" % ("settings.json" if not sj.exists() else "core/claude/settings.template.json")]),
        "statusLine_var": bool(sd.get("statusLine")),
        "settings_local_var": sl.exists(),
        "settings_local_allow_sayisi": sl_allow,
        "hook_shim_var": (PROJ / "scripts" / "hook_shim.py").exists(),
        "hook_shim_sha16": sha16(PROJ / "scripts" / "hook_shim.py"),
        "CLAUDE_md_bayt": len(cmd_txt.encode("utf-8")),
        "CLAUDE_md_yasak_damgasi": ("KESIN YASAKLAR" in cmd_txt.replace("\u0130", "I").upper()),
        "agents_dizini": ("symlink" if (C / "agents").is_symlink() else ("junction-veya-dizin" if (C / "agents").is_dir() else "YOK")),
        "agent_tanimlari": sorted(p.name for p in (C / "agents").glob("*.md")) if (C / "agents").is_dir() else [],
        "skill_sayisi": len(list((C / "skills").glob("*/SKILL.md"))) if (C / "skills").is_dir() else 0,
        "command_sayisi": len(list((C / "commands").glob("*.md"))) if (C / "commands").is_dir() else 0,
    }

    # ------------------------------------------------------------ 3. junction / core
    def baglanti(p: Path):
        d = {"var": p.exists(), "symlink_mi": p.is_symlink(), "hedef": None}
        try:
            d["hedef"] = mask(str(p.resolve()))
        except Exception:
            pass
        return d

    def g(*x):
        return run(["git", "-C", str(CORE), *x], timeout=30)["out"]

    core_self = Path(__file__).resolve().parents[1]      # CORE-03: core'un KENDI yolu
    try:
        junction_ayni = CORE.resolve() == core_self
    except Exception:
        junction_ayni = None
    R["core"] = {
        "junction": baglanti(CORE),
        "bu_script_in_evi": mask(str(core_self)),
        "junction_ayni_evi_gosteriyor": junction_ayni,
        "skills": baglanti(C / "skills"),
        "commands": baglanti(C / "commands"),
        "dal": g("rev-parse", "--abbrev-ref", "HEAD"),
        "head": g("log", "--oneline", "-1"),
        "remote": g("config", "--get", "remote.origin.url"),
        "kirli_satir": len([x for x in g("status", "--short").splitlines() if x.strip()]),
        "origin_main_gerisinde": g("rev-list", "--count", "HEAD..origin/main"),
        "son_fetch": None,
        "hooksPath": g("config", "--get", "core.hooksPath"),
        "CLAUDE_core_md_var": (CORE / "CLAUDE.core.md").exists(),
        "scripts_sayisi": len(list((CORE / "scripts").glob("*.py"))) if (CORE / "scripts").is_dir() else 0,
        "hook_sayisi": len(list((CORE / "scripts" / "hooks").glob("*.py"))) if (CORE / "scripts" / "hooks").is_dir() else 0,
        "validator_sayisi": len(list((CORE / "scripts" / "validators").glob("check_*.py"))) if (CORE / "scripts" / "validators").is_dir() else 0,
        "playbook_md_sayisi": len(list((CORE / "playbook").rglob("*.md"))) if (CORE / "playbook").is_dir() else 0,
        "rules_md_sayisi": len(list((CORE / "claude" / "rules").glob("*.md"))) if (CORE / "claude" / "rules").is_dir() else 0,
        "memory_seed_sayisi": len(list((CORE / "claude" / "memory-seed").glob("*.md"))) if (CORE / "claude" / "memory-seed").is_dir() else 0,
        "adr_sayisi": len(list((CORE / "governance" / "decisions").glob("*.md"))) if (CORE / "governance" / "decisions").is_dir() else 0,
    }
    fh = CORE / ".git" / "FETCH_HEAD"
    if fh.exists():
        R["core"]["son_fetch"] = datetime.fromtimestamp(fh.stat().st_mtime).isoformat(timespec="minutes")

    R["proje_repo"] = {
        "dal": run(["git", "-C", str(PROJ), "rev-parse", "--abbrev-ref", "HEAD"])["out"],
        "head": run(["git", "-C", str(PROJ), "log", "--oneline", "-1"])["out"],
        "kirli_satir": len([x for x in run(["git", "-C", str(PROJ), "status", "--short"])["out"].splitlines() if x.strip()]),
        "remote": run(["git", "-C", str(PROJ), "config", "--get", "remote.origin.url"])["out"],
    }

    # ------------------------------------------------------------ 3b. yol hijyeni
    # NEDEN: kurulum sabit klasor VARSAYMAZ (team_setup D24) ama YOLUN KENDISI uc
    # sinifta kirilma uretir: (a) tasima/yeniden-adlandirma sonrasi YETIM memory slug'i
    # (b) bayat junction hedefi (c) senkron klasoru (OneDrive/Dropbox) icindeki calisma koku.
    SYNC_IZLERI = ("onedrive", "dropbox", "google drive", "googledrive", "yandex.disk", "icloud")
    yollar = {"proje": str(PROJ), "core": str(CORE.resolve()) if CORE.exists() else str(CORE)}
    sync_bulgu = {k: [t for t in SYNC_IZLERI if t in v.lower()] for k, v in yollar.items()}
    junction_kirik = None
    if CORE.exists():
        try:
            junction_kirik = not CORE.resolve().is_dir()
        except Exception:
            junction_kirik = True
    R["yol_hijyeni"] = {
        "proje_yolu_uzunluk": len(str(PROJ)),
        "core_yolu_uzunluk": len(yollar["core"]),
        "bosluk_iceriyor": {k: (" " in v) for k, v in yollar.items()},
        "ascii_disi_iceriyor": {k: any(ord(c) > 127 for c in v) for k, v in yollar.items()},
        "senkron_klasoru_izi": {k: v for k, v in sync_bulgu.items() if v} or "YOK",
        "ONEDRIVE_env": bool(os.environ.get("OneDrive") or os.environ.get("OneDriveCommercial")),
        "core_junction_kirik": junction_kirik,
        "CLAUDE_PROJECT_DIR_env": mask(os.environ.get("CLAUDE_PROJECT_DIR", "<yok>")),
        "git_longpaths": run(["git", "config", "--global", "core.longpaths"])["out"] or "<yok>",
        "git_autocrlf": run(["git", "config", "--global", "core.autocrlf"])["out"] or "<yok>",
    }

    # ------------------------------------------------------------ 4. memory
    try:
        sys.path.insert(0, str(CORE / "scripts"))
        from utils.claude_paths import auto_memory_dizini  # type: ignore
        mem_dir = Path(auto_memory_dizini(PROJ))
        kaynak = "core/utils.claude_paths"
    except Exception as e:
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(PROJ))
        mem_dir = HOME / ".claude" / "projects" / slug / "memory"
        kaynak = "yerel-slug-turetimi (%s)" % type(e).__name__
    tipler = {}
    dosyalar = []
    if mem_dir.is_dir():
        for p in sorted(mem_dir.glob("*.md")):
            if p.name == "MEMORY.md" or p.name.startswith("_indeks"):
                if p.name == "MEMORY.md":
                    continue
            dosyalar.append(p.name)
            try:
                t = re.search(r"^\s*type:\s*(\w+)", p.read_text(encoding="utf-8", errors="replace"), re.M)
                k = t.group(1) if t else "<yok>"
                tipler[k] = tipler.get(k, 0) + 1
            except Exception:
                pass
    seed_dir = CORE / "claude" / "memory-seed"
    seed_adlar = sorted(p.name for p in seed_dir.glob("*.md") if p.name != "MEMORY.md") if seed_dir.is_dir() else []
    eksik_seed = sorted(set(seed_adlar) - set(dosyalar))
    mm = mem_dir / "MEMORY.md"
    R["memory"] = {
        "dizin": mask(str(mem_dir)),
        "dizin_kaynagi": kaynak,
        "dizin_var": mem_dir.is_dir(),
        "ders_dosyasi_sayisi": len(dosyalar),
        "tip_dagilimi": tipler,
        "MEMORY_md_var": mm.exists(),
        "MEMORY_md_bayt": mm.stat().st_size if mm.exists() else 0,
        "MEMORY_md_satir": len(mm.read_text(encoding="utf-8", errors="replace").splitlines()) if mm.exists() else 0,
        "seed_manifest_var": (mem_dir / ".seed-manifest.json").exists(),
        "seed_havuzu_sayisi": len(seed_adlar),
        "tohumlanmamis_seed_sayisi": len(eksik_seed),
        "tohumlanmamis_seed_ilk20": eksik_seed[:20],
        "memory_git_var": (mem_dir / ".git").exists(),
        "dosya_adlari": dosyalar,
    }
    # YETIM SLUG: proje klasoru TASINDI/YENIDEN ADLANDIRILDI ise eski yoldan turetilen
    # slug altinda dolu bir memory kalir ve YENI oturum onu HIC gormez (sessiz kayip).
    yetim = []
    kokler = HOME / ".claude" / "projects"
    if kokler.is_dir():
        for d in kokler.iterdir():
            md = d / "memory"
            if not md.is_dir() or md.resolve() == mem_dir.resolve():
                continue
            n = len([x for x in md.glob("*.md") if x.name != "MEMORY.md"])
            if n:
                yetim.append({"slug": mask(d.name), "ders": n})
    yetim.sort(key=lambda x: -x["ders"])
    R["memory"]["diger_slug_klasorleri"] = yetim[:10]
    R["memory"]["yetim_supheli"] = bool(yetim and yetim[0]["ders"] > len(dosyalar))

    # ------------------------------------------------------------ 5. MCP / profil
    mcp = PROJ / ".mcp.json"
    sunucular = []
    if mcp.exists():
        try:
            sunucular = sorted((json.loads(mcp.read_text(encoding="utf-8")).get("mcpServers") or {}).keys())
        except Exception:
            sunucular = ["<parse-hatasi>"]
    py = PROJ / "project.yaml"
    profil = {}
    if py.exists():
        txt = py.read_text(encoding="utf-8", errors="replace")
        for k in ("sap_profile", "release", "master_language", "source_root",
                  "active_package", "cleancore_policy", "repo_mode"):
            m = re.search(r"^%s\s*:\s*([^\s#]+)" % k, txt, re.M)
            profil[k] = m.group(1).strip('"') if m else "<YOK>"
    ap_state = C / "active_package"
    ap_val = ap_state.read_text(encoding="utf-8", errors="replace").strip() if ap_state.exists() else None
    rc_status = PROJ / ".tmp" / "recall-index.status"
    R["mcp_ve_profil"] = {
        "mcp_json_var": mcp.exists(),
        "mcp_sunuculari": sunucular,
        "conn_adt_var": (PROJ / ".conn_adt").exists(),
        "conn_dizini_var": (PROJ / "conn").is_dir(),
        "project_yaml": profil,
        "active_package_state": ap_val or "<YOK>",
        "aktif_paket_drift": (ap_val != profil.get("active_package")),
        "validators_local_var": (PROJ / "scripts" / "validators-local").is_dir(),
        "playbook_local_var": (PROJ / "playbook-local").is_dir(),
        "recall_index_status": rc_status.read_text(encoding="utf-8", errors="replace")[:300] if rc_status.exists() else "<YOK>",
        "governance_resume_sayisi": len(list((PROJ / "governance").glob("*-RESUME.md"))) if (PROJ / "governance").is_dir() else 0,
    }

    # ------------------------------------------------------------ 6. kosumlar
    R["kosumlar"] = {}
    if not a.no_doctor:
        d = run([sys.executable, str(CORE / "scripts" / "ix_doctor.py"), "--json"],
                cwd=str(PROJ), timeout=900)
        ozet = None
        if d["out"]:
            try:
                j = json.loads(d["out"][d["out"].find("{"):])
                ozet = {"fail": j.get("fail"), "warn": j.get("warn"),
                        "katmanlar": j.get("katmanlar")}
            except Exception as e:
                ozet = {"_parse_hatasi": str(e), "ham_son": d["out"][-2000:]}
        R["kosumlar"]["ix_doctor"] = {"rc": d["rc"], "err": d["err"], "ozet": ozet}
        v = run([sys.executable, str(CORE / "scripts" / "validators" / "run_all_validators.py"), "--quick"],
                cwd=str(PROJ), timeout=900)
        R["kosumlar"]["validators_quick"] = {"rc": v["rc"],
                                             "son_satirlar": v["out"].splitlines()[-12:],
                                             "err": v["err"][:300]}
    else:
        R["kosumlar"]["atlandi"] = "--no-doctor"

    # ------------------------------------------------------------ yaz + ozet
    ad = "parity-%s-%s.json" % ("ANON" if a.anon else socket.gethostname(),
                                datetime.now().strftime("%Y%m%d-%H%M"))
    # Rapor PROJE KOKUNE YAZILMAZ (repoyu kirletmemek icin) - gecici klasore yazilir.
    hedef = Path(a.out) if a.out else Path(tempfile.gettempdir()) / ad
    hedef.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")

    ck = R["claude_katmani"]
    p = print
    p("=" * 74)
    p("PARITY PROBE - %s  (%s)" % (R["makine"]["host"], R["_zaman"]))
    p("=" * 74)
    p("proje            : %s  (proje-kokunde-mi=%s)" % (R["makine"]["proje_koku"], R["makine"]["cwd_proje_mi"]))
    p("claude / python  : %s / py%s" % (R["harness"]["claude_version"], R["makine"]["python"]))
    p("model / autoMode : %s / %s" % (R["harness"]["model"], R["harness"]["autoMode"]))
    p("CORE KOPYASI     : %s  (%s bayt, sha=%s)" % (
        "VAR" if ck["core_kopyasi_var"] else "*** YOK ***",
        ck["core_kopyasi_bayt"], ck["core_kopyasi_sha16"]))
    p("rules dosyalari  : %s" % ck["rules_dosyalari"])
    p("kanca            : %s adet (template %s; fark=%s)" % (
        ck["kanca_sayisi"], ck["template_kanca_sayisi"], ck["kanca_template_farki"] or "YOK"))
    p("agents/skills/cmd: %s / %s skill / %s komut" % (
        len(ck["agent_tanimlari"]), ck["skill_sayisi"], ck["command_sayisi"]))
    p("settings.local   : %s, allow=%s" % ("var" if ck["settings_local_var"] else "YOK",
                                           ck["settings_local_allow_sayisi"]))
    p("core junction    : %s" % R["core"]["junction"]["hedef"])
    p("core dal/head    : %s | %s" % (R["core"]["dal"], R["core"]["head"][:60]))
    p("core gerilik     : origin/main'e '%s' commit geride (son fetch %s)" % (
        R["core"]["origin_main_gerisinde"] or "?", R["core"]["son_fetch"]))
    p("core envanteri   : scripts=%s hooks=%s validators=%s playbook=%s rules=%s seed=%s adr=%s" % (
        R["core"]["scripts_sayisi"], R["core"]["hook_sayisi"], R["core"]["validator_sayisi"],
        R["core"]["playbook_md_sayisi"], R["core"]["rules_md_sayisi"],
        R["core"]["memory_seed_sayisi"], R["core"]["adr_sayisi"]))
    p("MEMORY           : %s ders %s  MEMORY.md=%s bayt/%s satir" % (
        R["memory"]["ders_dosyasi_sayisi"], R["memory"]["tip_dagilimi"],
        R["memory"]["MEMORY_md_bayt"], R["memory"]["MEMORY_md_satir"]))
    p("  tohumlanmamis  : %s / %s seed  (manifest=%s)" % (
        R["memory"]["tohumlanmamis_seed_sayisi"], R["memory"]["seed_havuzu_sayisi"],
        R["memory"]["seed_manifest_var"]))
    yh = R["yol_hijyeni"]
    p("YOL HIJYENI      : senkron-izi=%s  junction-kirik=%s  bosluk=%s  ascii-disi=%s" % (
        yh["senkron_klasoru_izi"], yh["core_junction_kirik"],
        yh["bosluk_iceriyor"], yh["ascii_disi_iceriyor"]))
    if R["memory"]["diger_slug_klasorleri"]:
        p("  DIGER SLUG'LAR : %s%s" % (
            R["memory"]["diger_slug_klasorleri"][:3],
            "   <-- YETIM SUPHESI (tasima/yeniden-adlandirma?)" if R["memory"]["yetim_supheli"] else ""))
    p("MCP / profil     : %s  conn_adt=%s  %s" % (
        R["mcp_ve_profil"]["mcp_sunuculari"], R["mcp_ve_profil"]["conn_adt_var"],
        R["mcp_ve_profil"]["project_yaml"]))
    if "ix_doctor" in R["kosumlar"]:
        o = R["kosumlar"]["ix_doctor"]["ozet"] or {}
        p("ix_doctor        : fail=%s warn=%s (rc=%s)" % (
            o.get("fail"), o.get("warn"), R["kosumlar"]["ix_doctor"]["rc"]))
        for k in (o.get("katmanlar") or []):
            p("   KATMAN %s %-46s %s" % (k.get("no"), str(k.get("ad"))[:46], k.get("durum")))
        vq = R["kosumlar"]["validators_quick"]
        p("validators quick : rc=%s | %s" % (vq["rc"], (vq["son_satirlar"] or ["?"])[-1][:60]))
    p("=" * 74)
    p("RAPOR YAZILDI: %s" % hedef)
    p("Bu dosyayi lidere ver. Icinde sifre/izin-listesi ICERIGI YOKTUR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
