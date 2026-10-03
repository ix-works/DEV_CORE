#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TEAM_SETUP SABLON SAPMASI + TAZELEME + CORE-INDEX YAZIM + ALT SUREC ENV (2026-10-03, F12/F5).

NEDEN BU KORPUS VAR (yeni-proje akisi denetimi, paket 2)
--------------------------------------------------------
F12a  `team_setup.dosya_tamamla` var olan dosyaya `[ OK ] mevcut` basip geciyordu: kum
      projede `settings.json` / `hook_shim.py` / `pre-commit` sablondan sapmis olsa da
      `team_setup TAMAM` + exit 0. Sapma ancak SONRAKI oturumda `session_start` D7'de
      gorunuyordu. Cozum: `sablon_sapmasi` — D7'nin TEK KAYNAGI (`utils.drift_imzasi`)
      ile kurulum aninda GOZLEM (exit kodu DEGISMEZ).
      YON AYRIMI (lider karari): settings.json'da yalniz-PROJE eki = INFO (mesru; her
      kosumda WARN uyari korlugu uretir), yalniz-SABLON ogesi = WARN. hook_shim/pre-commit:
      HER fark WARN (proje ILERIDE olabilir).
F12b  pre-commit icin onayli tazeleme yolu yoktu -> `--tazele-precommit` (`shim_tazele`
      deseni genellestirildi: fark + yon sayimi + yedek + sha dogrulamasi).
F12c  her `team_setup` izlenen `governance/CORE-INDEX.md`de yalniz zaman damgasi farki
      (`git status` ` M`) uretiyordu -> icerik + core-commit ayniysa YAZILMAZ.
      ⛔ core-commit `--ci-check`in GIRDISIDIR: core-commit degisince yine yazilir (C4).
F5    `alt_arac` (seed_memory/setup_plugins) + smoke statusline alt sureclerine
      `CLAUDE_PROJECT_DIR` gecmiyordu: ortamda BASKA projenin degeri varsa tohum o projenin
      hafizasina gidiyordu (D1 gercek zincirle olcer).

⛔ IZOLASYON: kum `tempfile.mkdtemp()` (kisa %TEMP% — uzun yol memory slug'inda MAX_PATH'i
asar) · `CLAUDE_CONFIG_DIR` kuma · mutasyon/taban kopyalari `scripts/_zz_*.py` kardes
dosyada (CORE_ROOT ayni cozulsun) ve finally'de SILINIR · kum silinmeden ONCE junction'lar
`rmdir` ile kaldirilir (rmtree junction'a girerse HEDEFI siler). SAP/ag YOK.

KOSUM:  python tests/fixtures/team_setup_sablon_sapmasi/run.py
        ... --mutasyon-sapma-sessiz        (sablon_sapmasi cagrisi kalkar)      -> A2 A4 A5
        ... --mutasyon-ek-warn             (settings allow eki WARN'a doner)     -> A3
        ... --mutasyon-info-genis          (INFO allow-disi eklere acilir)       -> A3b A3c A3d
        ... --mutasyon-bos-kap             (bos {}/[] yaprak uretmez)            -> A10
        ... --mutasyon-import-korumasiz    (--tazele-* import'u korumasiz)       -> A11
        ... --mutasyon-eksik-info          (settings EKSIGI INFO'ya duser)       -> A2
        ... --mutasyon-precommit-yok       (--tazele-precommit hicbir sey yapmaz) -> B2
        ... --mutasyon-fark-sessiz         (fark govdesi basilmadan tazelenir)   -> B2b
        ... --mutasyon-index-her-zaman     (icerik ayniyken de yazar)            -> C2 C6
        ... --mutasyon-index-damga-kor     (core-commit farkinda da yazmaz)      -> C4
        ... --mutasyon-env-yok             (alt_arac env gecirmez)               -> D1 D2
        ... --mutasyon-env-yok-statusline  (smoke statusline env gecirmez)       -> D3
ESKI KOD: --ts <scripts/ altinda dosya> --ci <scripts/ altinda dosya>
        (ornek: `git show <taban>:scripts/team_setup.py > scripts/_zz_taban_ts.py`).
Cikis:  0 hepsi gecti · 1 sapma (mutasyonda: BEKLENEN vektorler dustu = yakalandi)
        · 2 DOGRULANAMADI (capa tutmadi / beklenen vektor dusmedi)
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
SCRIPTS = REPO / "scripts"
TS = SCRIPTS / "team_setup.py"
CI = SCRIPTS / "build_core_index.py"
SABLON_SETTINGS = REPO / "claude" / "settings.template.json"
SABLON_SHIM = REPO / "claude" / "hook_shim.template.py"
SABLON_PC = REPO / "claude" / "git-hooks" / "pre-commit.template"

# team_setup'in CORE-INDEX ureticisini cagirdigi satir — kopya team_setup'i kopya
# ureticiye yoneltmek icin (mutasyon/taban kipleri). count != 1 => DOGRULANAMADI.
CAPA_URETICI = 'uretici = CORE_ROOT / "scripts" / "build_core_index.py"'
# settings INFO dalinin kosulu (PR #321 inceleme sonrasi bicim)
CAPA_INFO = ('        if (rel_y == ".claude/settings.json" and ayr is not None and proje_ozel\n'
             '                and not sablon_ozel and not allow_disi):\n')
DZ = SCRIPTS / "utils" / "drift_imzasi.py"
CAPA_ONEK = "CORE_ROOT = Path(__file__).resolve().parent.parent          # D24\n"

# (dosya, eski, yeni, beklenen-dusen)
MUTLAR = {
    "--mutasyon-sapma-sessiz": (
        "ts", "    sablon_sapmasi(proje)\n", "    pass  # MUTASYON\n", {"A2", "A4", "A5"}),
    "--mutasyon-ek-warn": (
        "ts", CAPA_INFO, "        if False:  # MUTASYON\n", {"A3"}),
    "--mutasyon-eksik-info": (
        "ts", CAPA_INFO,
        "        if (rel_y == \".claude/settings.json\" and ayr is not None  # MUTASYON\n"
        "                and not allow_disi):\n", {"A2"}),
    # PR #321 inceleme: INFO dali allow-disi eklere de acilir (ilk surumun hatasi) -> A3b-d
    "--mutasyon-info-genis": (
        "ts", CAPA_INFO,
        "        if (rel_y == \".claude/settings.json\" and ayr is not None and proje_ozel\n"
        "                and not sablon_ozel):  # MUTASYON\n", {"A3b", "A3c", "A3d"}),
    # bos kap yaprak uretmez -> A10 ("yalniz SIRA" yanlis mesaji geri gelir)
    "--mutasyon-bos-kap": (
        "dz", "            if isinstance(n, (dict, list)) and not n:\n",
        "            if False:  # MUTASYON\n", {"A10"}),
    # import korumasi kalkar -> A11 (ham traceback)
    "--mutasyon-import-korumasiz": (
        "ts", "    except Exception as e:  # noqa: BLE001\n"
              "        say(FAIL, f\"{rel_yerel}: şablon yolu ÖLÇÜLEMEDİ",
        "    except ImportError as e:  # MUTASYON  # noqa: BLE001\n"
        "        raise\n        say(FAIL, f\"{rel_yerel}: şablon yolu ÖLÇÜLEMEDİ", {"A11"}),
    "--mutasyon-precommit-yok": (
        "ts", '            ok = kopya_tazele(proje, "scripts/git-hooks/pre-commit") and ok\n',
        "            pass  # MUTASYON\n", {"B2"}),
    "--mutasyon-fark-sessiz": (
        "ts", '    for satir in fark:\n        print("  " + satir.rstrip("\\n"))\n',
        "    pass  # MUTASYON\n", {"B2b"}),
    "--mutasyon-index-her-zaman": (
        "ci", "    if HEDEF.is_file():\n        mevcut_ham = ",
        "    if False:  # MUTASYON\n        mevcut_ham = ", {"C2", "C6"}),
    "--mutasyon-index-damga-kor": (
        "ci", "                and simdiki is not None and _kayitli_core_commit() == simdiki):\n",
        "                ):  # MUTASYON\n", {"C4"}),
    "--mutasyon-env-yok": (
        "ts", "                       text=True, encoding=\"utf-8\", errors=\"replace\", cwd=proje,\n"
              "                       env=dict(os.environ, CLAUDE_PROJECT_DIR=str(proje)))\n",
        "                       text=True, encoding=\"utf-8\", errors=\"replace\", cwd=proje)\n",
        {"D1", "D2"}),
    "--mutasyon-env-yok-statusline": (
        "ts", "                           text=True, cwd=proje, timeout=30,\n"
              "                           env=dict(os.environ, CLAUDE_PROJECT_DIR=str(proje)))  # F5\n",
        "                           text=True, cwd=proje, timeout=30)\n", {"D3"}),
}

SONUC: list[tuple[str, bool, str]] = []


def kontrol(kimlik: str, ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((kimlik, bool(kosul), ad))
    print(f"  [{'PASS' if kosul else 'FAIL'}] {kimlik} {ad}"
          + (f"  -- {detay}" if not kosul and detay else ""))


# ── kum ──────────────────────────────────────────────────────────────────────
def _bag_mi(p: Path) -> bool:
    if p.is_symlink():
        return True
    try:
        os.readlink(p)
        return True
    except (OSError, ValueError):
        return False


def _sil(kok: Path) -> None:
    """ONCE baglar (junction/symlink) hedefe dokunmadan kaldirilir, SONRA agac."""
    for dp, dn, _fn in os.walk(kok):
        for d in list(dn):
            p = Path(dp) / d
            if _bag_mi(p):
                try:
                    p.unlink() if p.is_symlink() else os.rmdir(p)
                except OSError:
                    pass
                dn.remove(d)

    def _ac(func, path, _exc):  # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    shutil.rmtree(kok, **kw)  # type: ignore[arg-type]


def proje_kur(kok: Path, ad: str, git: bool = True) -> Path:
    """Sablonla BAYT-ES uc kopya tasiyan sahte 'mevcut makine' projesi."""
    p = kok / ad
    (p / ".claude").mkdir(parents=True)
    (p / "scripts" / "git-hooks").mkdir(parents=True)
    shutil.copyfile(SABLON_SETTINGS, p / ".claude" / "settings.json")
    shutil.copyfile(SABLON_SHIM, p / "scripts" / "hook_shim.py")
    shutil.copyfile(SABLON_PC, p / "scripts" / "git-hooks" / "pre-commit")
    (p / "project.yaml").write_text("active_package: ZSD001_CLC\n", encoding="utf-8", newline="\n")
    if git:
        subprocess.run(["git", "init", "-q", str(p)], check=True, capture_output=True)
    return p


def settings_yaz(p: Path, degistir) -> None:  # noqa: ANN001
    yol = p / ".claude" / "settings.json"
    d = json.loads(yol.read_text(encoding="utf-8"))
    degistir(d)
    yol.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                   newline="\n")


def env_temiz(**ek: str) -> dict:
    e = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    e["PYTHONIOENCODING"] = "utf-8"
    e.update(ek)
    return e


def kos_ts(ts: Path, proje: Path, *ek: str, env: dict | None = None,
           seed: bool = False) -> tuple[int, str]:
    arg = [sys.executable, str(ts), "--project", str(proje), "--no-install",
           "--no-plugins", "--no-smoke", *ek]
    if not seed:
        arg.append("--no-seed")
    r = subprocess.run(arg, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600, env=env or env_temiz())
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def kos_ci(ci: Path, proje: Path, *ek: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(ci), *ek], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300,
                       env=env_temiz(CLAUDE_PROJECT_DIR=str(proje)))
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def satirlar(out: str, *parca: str) -> list[str]:
    return [s for s in out.splitlines() if all(x in s for x in parca)]


def git(p: Path, *a: str) -> str:
    r = subprocess.run(["git", "-C", str(p), "-c", "user.email=fixture",
                        "-c", "user.name=fixture", "-c", "core.autocrlf=false", *a],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


# ── vektorler ────────────────────────────────────────────────────────────────
def a_blogu(ts: Path, tmp: Path) -> None:
    print("\n-- A: F12a sablon sapmasi (kurulum ANINDA, gozlem) --")
    # A1 KONTROL GRUBU: uc kopya sablonla es -> hic SAPMIS/eki satiri yok
    p = proje_kur(tmp, "a1")
    rc, out = kos_ts(ts, p)
    kontrol("A1", "KONTROL: sablonla ES proje -> WARN yok, kapsam satiri '3 es', rc 0",
            rc == 0 and not satirlar(out, "SAPMIŞ") and "3 eş" in out
            and "team_setup TAMAM" in out, f"rc={rc} sapmis={satirlar(out, 'SAPMIŞ')}")

    # A2 settings GERIDE: sablondaki bir allow ogesi projede YOK -> WARN
    p = proje_kur(tmp, "a2")
    settings_yaz(p, lambda d: d["permissions"]["allow"].pop())
    rc, out = kos_ts(ts, p)
    w = satirlar(out, "[WARN]", "settings.json şablondan SAPMIŞ")
    kontrol("A2", "settings GERIDE (yalniz sablonda 1 oge) -> WARN + rc 0 + TAMAM (gate degil)",
            rc == 0 and len(w) == 1 and "yalnız ŞABLONDA 1 öğe" in w[0]
            and "team_setup TAMAM" in out, f"rc={rc} w={w}")

    # A3 settings yalniz permissions.allow EKI (canli tuketici sekli: 3 ek allow) -> INFO
    # ⛔ PR #321 inceleme: ilk surum SessionEnd hook ekini de INFO diye CIVILIYORDU (yanlis).
    uc_allow = ["Bash(python core/scripts/validators/zz_a.py:*)",
                "Bash(python core/scripts/validators/zz_b.py:*)",
                "Bash(python core/scripts/validators/zz_c.py:*)"]
    session_end = [{"hooks": [{"type": "command",
                               "command": "python scripts/hook_shim.py watchdog_stop"}]}]
    p = proje_kur(tmp, "a3")
    settings_yaz(p, lambda d: d["permissions"]["allow"].extend(uc_allow))
    rc, out = kos_ts(ts, p)
    i = satirlar(out, "[INFO]", "settings.json: 3 proje eki")
    kontrol("A3", "settings yalniz ALLOW EKI -> WARN YOK, INFO '3 proje eki' (uyari korlugu yok)",
            rc == 0 and not satirlar(out, "[WARN]", "settings.json") and len(i) == 1,
            f"info={i} warn={satirlar(out, '[WARN]', 'settings.json')}")

    def _warn_allow_disi(kimlik: str, ad_: str, degistir, n: int) -> None:  # noqa: ANN001
        pp = proje_kur(tmp, kimlik.lower())
        settings_yaz(pp, degistir)
        _rc, o = kos_ts(ts, pp)
        w_ = satirlar(o, "[WARN]", "settings.json şablondan SAPMIŞ")
        kontrol(kimlik, ad_,
                len(w_) == 1 and f"{n}'i permissions.allow DIŞI" in w_[0]
                and not satirlar(o, "[INFO]", "settings.json:"),
                f"warn={w_} info={satirlar(o, '[INFO]', 'settings.json:')}")

    _warn_allow_disi("A3b", "settings `disableAllHooks` eki -> WARN (1 allow DISI), INFO DEGIL",
                     lambda d: d.update({"disableAllHooks": True}), 1)
    _warn_allow_disi("A3c", "settings `hooks.SessionEnd` eki (kaldirilmis hook) -> WARN, "
                            "INFO DEGIL",
                     lambda d: d["hooks"].update({"SessionEnd": session_end}), 1)

    def _karisik(d):  # noqa: ANN001
        d["permissions"]["allow"].extend(uc_allow)
        d["hooks"]["SessionEnd"] = session_end
    _warn_allow_disi("A3d", "settings allow + hooks KARISIK -> WARN (yalniz 1'i allow DISI)",
                     _karisik, 1)

    # A10 bos kap eki: yaprak sayilir, "yalniz SIRA" denmez
    p = proje_kur(tmp, "a10")

    def _bos(d):  # noqa: ANN001
        d["env"]["ZZ_BOS"] = {}
        d["permissions"]["zz"] = []
    settings_yaz(p, _bos)
    rc, out = kos_ts(ts, p)
    w = satirlar(out, "[WARN]", "settings.json şablondan SAPMIŞ")
    kontrol("A10", "bos kap eki ({} / []) -> 'yalniz PROJEDE 2 oge', 'yalniz SIRA' DEGIL",
            len(w) == 1 and "yalnız PROJEDE 2 öğe" in w[0] and "SIRA" not in w[0], f"w={w}")

    # A4 hook_shim proje ILERIDE -> WARN + --tazele-shim onerisi
    p = proje_kur(tmp, "a4")
    hedef = p / "scripts" / "hook_shim.py"
    hedef.write_bytes(hedef.read_bytes() + b"# PROJE-OZEL: sablonda YOK\n")
    once = hedef.read_bytes()
    rc, out = kos_ts(ts, p)
    w = satirlar(out, "[WARN]", "hook_shim.py şablondan SAPMIŞ")
    kontrol("A4", "hook_shim ILERIDE -> WARN (yalniz PROJEDE 1) + '--tazele-shim' + 'İLERİDE'",
            len(w) == 1 and "yalnız PROJEDE 1 satır" in w[0] and "--tazele-shim" in w[0]
            and "İLERİDE" in w[0], f"w={w}")

    # A5 pre-commit GERIDE -> WARN + --tazele-precommit onerisi
    p5 = proje_kur(tmp, "a5")
    pc = p5 / "scripts" / "git-hooks" / "pre-commit"
    govde = pc.read_bytes().split(b"\n")
    pc.write_bytes(b"\n".join(govde[:3] + govde[4:]))
    pc_once = pc.read_bytes()
    rc5, out5 = kos_ts(ts, p5)
    w = satirlar(out5, "[WARN]", "pre-commit şablondan SAPMIŞ")
    kontrol("A5", "pre-commit GERIDE -> WARN (yalniz SABLONDA 1) + '--tazele-precommit'",
            len(w) == 1 and "yalnız ŞABLONDA 1 satır" in w[0] and "--tazele-precommit" in w[0],
            f"w={w}")
    kontrol("A8", "GOZLEM YAZMAZ: bayraksiz kosumda sapmis hook_shim + pre-commit EZILMEDI",
            hedef.read_bytes() == once and pc.read_bytes() == pc_once, "")

    # A6 yalniz `_comment*` farki -> davranis tasimaz -> ES (D7 ile ayni)
    p = proje_kur(tmp, "a6")
    settings_yaz(p, lambda d: d.update({"_comment_proje": "yalniz not"}))
    rc, out = kos_ts(ts, p)
    kontrol("A6", "yalniz _comment farki -> ES sayilir (D7 normalizasyonu), WARN/INFO yok",
            not satirlar(out, "settings.json şablondan") and not satirlar(out, "proje eki")
            and "3 eş" in out, "")

    # A7 bozuk JSON -> OLCULEMEDI (sessiz OK degil)
    p = proje_kur(tmp, "a7")
    (p / ".claude" / "settings.json").write_text("{bozuk", encoding="utf-8")
    rc, out = kos_ts(ts, p)
    kontrol("A7", "bozuk settings -> WARN 'ÖLÇÜLEMEDİ' + kapsam '1 ölçülemedi'",
            bool(satirlar(out, "[WARN]", "settings.json", "ÖLÇÜLEMEDİ"))
            and "1 ölçülemedi" in out, "")

    # A9 3. BAGLAM: git reposu OLMAYAN proje (repo_mode=none) -> kiyas git'ten bagimsiz
    p = proje_kur(tmp, "a9", git=False)
    hedef = p / "scripts" / "hook_shim.py"
    hedef.write_bytes(hedef.read_bytes().replace(b"import runpy", b"import runpy  # x", 1))
    rc, out = kos_ts(ts, p)
    kontrol("A9", "3. BAGLAM gitsiz proje: hook_shim sapmasi yine WARN "
                  "(pre-commit kablolamasi atlansa da)",
            bool(satirlar(out, "[WARN]", "hook_shim.py şablondan SAPMIŞ")), "")


def b_blogu(ts: Path, tmp: Path) -> None:
    print("\n-- B: F12b --tazele-precommit --")
    p = proje_kur(tmp, "b2")
    pc = p / "scripts" / "git-hooks" / "pre-commit"
    # ⚠ Satir sonundan BAGIMSIZ ekleme: autocrlf'li Windows checkout'ta sablon CRLF tasir
    # (olculdu: ilk yazimda `b"#!/bin/sh\n"` eslesmedi, mutasyon kurulmadan "ZATEN ayni" dondu).
    sat = pc.read_bytes().split(b"\n")
    sat.insert(1, b"# ESKI SURUM" + (b"\r" if sat[0].endswith(b"\r") else b""))
    pc.write_bytes(b"\n".join(sat))
    kontrol("B2-kurulum", "kurulum: kopya sablondan GERCEKTEN farkli (sahte-yesil degil)",
            pc.read_bytes() != SABLON_PC.read_bytes(), "")
    shim = p / "scripts" / "hook_shim.py"
    shim.write_bytes(shim.read_bytes() + b"# shim-ozel\n")
    shim_once = shim.read_bytes()
    rc, out = kos_ts(ts, p, "--tazele-precommit")
    kontrol("B2", "--tazele-precommit: FARK RAPORU + tazeler (sonuc == sablon bayt)",
            rc == 0 and "pre-commit FARK RAPORU" in out
            and pc.read_bytes() == SABLON_PC.read_bytes(), f"rc={rc} cikti={out[-300:]!r}")
    i_f, i_t = out.find("@@"), out.find("pre-commit TAZELENDİ")
    kontrol("B2b", "GERCEK diff govdesi (@@) TAZELENDI'den ONCE basilir",
            i_f != -1 and i_t != -1 and i_f < i_t, f"@@={i_f} taz={i_t}")
    yed = list((p / "scripts" / "git-hooks").glob("pre-commit.yedek-*"))
    kontrol("B2c", "yedek alinir (pre-commit.yedek-<sha8>) + sonuc SHA ile duyurulur",
            len(yed) == 1 and "sonuç sha256 == şablon sha256" in out, f"yedek={yed}")
    kontrol("B2d", "--tazele-precommit hook_shim'e DOKUNMAZ (yan etki yuzeyi dar)",
            shim.read_bytes() == shim_once, "")

    p = proje_kur(tmp, "b3")
    pc = p / "scripts" / "git-hooks" / "pre-commit"
    pc.write_bytes(pc.read_bytes() + b"# PROJE-OZEL koruma (sablonda YOK)\n")
    rc, out = kos_ts(ts, p, "--tazele-precommit")
    yed = list((p / "scripts" / "git-hooks").glob("pre-commit.yedek-*"))
    kontrol("B3", "TERS YON: proje ILERIDE -> 'TERS YÖN' + '1 satır YALNIZ projede' + yedekte satir",
            "TERS YÖN" in out and "1 satır YALNIZ projede" in out and len(yed) == 1
            and b"PROJE-OZEL koruma" in yed[0].read_bytes(), f"cikti={out[-300:]!r}")

    p = proje_kur(tmp, "b4")
    rc, out = kos_ts(ts, p, "--tazele-precommit")
    kontrol("B4", "zaten ayni -> 'tazeleme gereksiz', yedek YOK",
            rc == 0 and "tazeleme gereksiz" in out
            and not list((p / "scripts" / "git-hooks").glob("pre-commit.yedek-*")),
            f"rc={rc} cikti={out[-300:]!r}")

    # A11 (bayrak yolu) modul YUKLENEMEZ -> FAIL + OLCULEMEDI, traceback YOK, dosya
    # DEGISMEZ. `sys.modules[...] = None` import'u ImportError'a cevirir.
    p = proje_kur(tmp, "a11")
    pc = p / "scripts" / "git-hooks" / "pre-commit"
    pc.write_bytes(pc.read_bytes() + b"# sapma\n")
    shim = p / "scripts" / "hook_shim.py"
    shim.write_bytes(shim.read_bytes() + b"# sapma\n")
    once_pc, once_sh = pc.read_bytes(), shim.read_bytes()
    src = ("import sys, runpy\n"
           "sys.modules['utils.drift_imzasi'] = None\n"
           f"sys.argv = ['team_setup.py', '--project', r'{p}', '--tazele-shim', "
           "'--tazele-precommit']\n"
           f"runpy.run_path(r'{ts}', run_name='__main__')\n")
    r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300, env=env_temiz())
    out = (r.stdout or "") + (r.stderr or "")
    f = satirlar(out, "[FAIL]", "ÖLÇÜLEMEDİ")
    kontrol("A11", "drift_imzasi YUKLENEMEZ -> --tazele-* FAIL 'ÖLÇÜLEMEDİ' x2, Traceback YOK, "
                   "exit 1, iki dosya DEGISMEDI",
            r.returncode == 1 and len(f) == 2 and "Traceback" not in out
            and pc.read_bytes() == once_pc and shim.read_bytes() == once_sh,
            f"rc={r.returncode} fail={f} cikti={out[-300:]!r}")

    p = tmp / "b5"
    (p / "scripts").mkdir(parents=True)
    rc, out = kos_ts(ts, p, "--tazele-precommit")
    kontrol("B5", "kopya YOK -> exit 1 + YOK, yoktan dosya URETMEZ",
            rc == 1 and "YOK" in out
            and not (p / "scripts" / "git-hooks" / "pre-commit").exists(), f"rc={rc}")


def c_blogu(ts: Path, ci: Path, tmp: Path) -> None:
    print("\n-- C: F12c CORE-INDEX icerik ayniysa YAZILMAZ --")
    p = tmp / "c1"
    (p / "governance").mkdir(parents=True)
    hedef = p / "governance" / "CORE-INDEX.md"
    rc, out = kos_ci(ci, p)
    kontrol("C1", "ilk uretim yazar", rc == 0 and hedef.is_file(), out[-200:])
    once = hedef.read_bytes() if hedef.is_file() else b""
    rc, out = kos_ci(ci, p)
    kontrol("C2", "icerik + core-commit ayni -> YENIDEN YAZILMAZ (bayt ayni, 'değişmedi')",
            rc == 0 and hedef.read_bytes() == once and "değişmedi" in out, out[-200:])
    rc, out = kos_ci(ci, p, "--check")
    kontrol("C7", "atlanan yazimdan sonra --check (C-IDX-01) OK", rc == 0, out[-200:])

    # C3 KONTROL: icerik gercekten degisince yazilir
    bozuk = once.replace(b"## `core/playbook/`", b"## `core/playbook-ESKI/`", 1)
    hedef.write_bytes(bozuk)
    kos_ci(ci, p)
    rc2, out2 = kos_ci(ci, p, "--check")
    kontrol("C3", "KONTROL: icerik degisince YAZILIR ve --check yesile doner",
            bozuk != once and hedef.read_bytes() != bozuk and rc2 == 0, out2[-200:])

    # C4 icerik ayni ama damgadaki core-commit FARKLI -> YAZILIR (--ci-check girdisi)
    metin = hedef.read_text(encoding="utf-8")
    eski = metin.replace("core-commit: ", "core-commit: 0000000x", 1)
    hedef.write_text(eski, encoding="utf-8", newline="\n")
    rc, out = kos_ci(ci, p)
    yeni = hedef.read_text(encoding="utf-8")
    kontrol("C4", "core-commit farkli (icerik ayni) -> YAZILIR, damga guncel core-commit'i tasir",
            "0000000x" in eski and "0000000x" not in yeni, out[-200:])

    # C5 damgasiz eski bicim -> yazilir
    hedef.write_text(yeni.split("\n", 1)[1], encoding="utf-8", newline="\n")
    kos_ci(ci, p)
    kontrol("C5", "damgasiz eski dosya -> YAZILIR (damga eklenir)",
            hedef.read_text(encoding="utf-8").startswith("<!-- uretim:"), "")

    # C6 UCTAN UCA: gercek team_setup iki kez, arada commit -> git status TEMIZ
    p = proje_kur(tmp, "c6")
    kos_ts(ts, p)
    git(p, "add", "governance/CORE-INDEX.md")
    # `--no-verify`: team_setup projenin pre-commit'ini KABLOLADI; kumda gate'ler anlamsiz.
    git(p, "commit", "-q", "--no-verify", "-m", "ilk")
    izlendi = git(p, "ls-files", "governance/CORE-INDEX.md").strip()
    kos_ts(ts, p)
    st = git(p, "status", "--porcelain", "--", "governance/CORE-INDEX.md").strip()
    kontrol("C6", "UCTAN UCA: ikinci team_setup izlenen CORE-INDEX'te ' M' URETMEZ",
            izlendi == "governance/CORE-INDEX.md" and st == "",
            f"izlendi={izlendi!r} status={st!r}")


def d_blogu(ts: Path, tmp: Path) -> None:
    print("\n-- D: F5 alt surec CLAUDE_PROJECT_DIR sabitlenir --")
    sys.path.insert(0, str(SCRIPTS))
    from utils.claude_paths import proje_slug  # type: ignore
    p = proje_kur(tmp, "d1")
    baska = tmp / "baska"
    baska.mkdir()
    cfg = tmp / "cfg"
    rc, out = kos_ts(ts, p, seed=True,
                     env=env_temiz(CLAUDE_PROJECT_DIR=str(baska), CLAUDE_CONFIG_DIR=str(cfg)))
    dogru = cfg / "projects" / proje_slug(p) / "memory"
    yanlis = cfg / "projects" / proje_slug(baska) / "memory"
    kontrol("D1", "GERCEK ZINCIR: ortamda BASKA proje varken seed_memory tohumu DOGRU projeye",
            dogru.is_dir() and any(dogru.iterdir()) and not yanlis.exists(),
            f"dogru={dogru.is_dir()} yanlis={yanlis.exists()} "
            f"cikti={satirlar(out, 'seed_memory')}")

    yakala = tmp / "yakala.json"
    src = (
        "import json, os, runpy, subprocess, sys, pathlib\n"
        "sys.argv = ['team_setup.py']\n"
        f"m = runpy.run_path(r'{ts}')\n"
        "kayit = []\n"
        "def sahte(*a, **k):\n"
        "    arg = a[0] if a else k.get('args')\n"
        "    kayit.append((str(arg[1]) if len(arg) > 1 else '',"
        " (k.get('env') or {}).get('CLAUDE_PROJECT_DIR')))\n"
        "    return subprocess.CompletedProcess(arg, 0, '', '')\n"
        "subprocess.run = sahte\n"
        f"P = pathlib.Path(r'{p}')\n"
        "m['alt_arac'](P, 'statusline.py', 'x')\n"
        "n = len(kayit)\n"
        "try:\n    m['smoke'](P)\nexcept Exception:\n    pass\n"
        "json.dump({'alt': kayit[:n], 'smoke': kayit[n:n+1],"
        " 'ana_env': os.environ.get('CLAUDE_PROJECT_DIR')},\n"
        f"          open(r'{yakala}', 'w', encoding='utf-8'))\n")
    subprocess.run([sys.executable, "-c", src], capture_output=True, timeout=300,
                   env=env_temiz(CLAUDE_PROJECT_DIR=str(baska)))
    try:
        y = json.loads(yakala.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        y = {"hata": repr(e)}
    kontrol("D2", "alt_arac alt surecine CLAUDE_PROJECT_DIR=<proje> (ortamdaki BASKA deger EZILIR)",
            bool(y.get("alt")) and all(v == str(p) for _a, v in y["alt"]), f"{y}")
    kontrol("D3", "smoke statusline alt surecine CLAUDE_PROJECT_DIR=<proje>",
            bool(y.get("smoke")) and y["smoke"][0][1] == str(p), f"{y}")
    kontrol("D4", "KONTROL: team_setup surecinin KENDI ortami degismedi (project_root semantigi)",
            y.get("ana_env") == str(baska), f"{y}")


# ── ana ──────────────────────────────────────────────────────────────────────
def _arg(argv: list[str], ad: str) -> Path | None:
    if ad not in argv or argv.index(ad) + 1 >= len(argv):
        return None
    d = Path(argv[argv.index(ad) + 1])
    return d if d.is_absolute() else (REPO / d)


def main() -> int:
    argv = sys.argv[1:]
    for a in argv:
        if a.startswith("--mutasyon") and a not in MUTLAR:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + ", ".join(sorted(MUTLAR)))
    secili = [a for a in argv if a in MUTLAR]

    ts_kaynak, ci_kaynak = _arg(argv, "--ts") or TS, _arg(argv, "--ci") or CI
    for k in (ts_kaynak, ci_kaynak):
        if k.resolve().parent != SCRIPTS.resolve() or not k.is_file():
            print(f"[DOGRULANAMADI] kaynak scripts/ altinda bir dosya olmali: {k}")
            return 2

    gecici: list[Path] = []
    ts, ci = ts_kaynak, ci_kaynak
    try:
        ts_metin = ts_kaynak.read_bytes().decode("utf-8")
        ci_metin = ci_kaynak.read_bytes().decode("utf-8")
        if secili:
            dosya, eski, yeni, _b = MUTLAR[secili[0]]
            if dosya == "dz":
                hedef_metin = DZ.read_bytes().decode("utf-8")
            else:
                hedef_metin = ts_metin if dosya == "ts" else ci_metin
            if hedef_metin.count(eski) != 1:
                print(f"[DOGRULANAMADI] mutasyon capasi {hedef_metin.count(eski)} kez bulundu "
                      f"({secili[0]}) -> mutasyon uygulanmadi; sonuc ANLAMSIZ olurdu.")
                return 2
            if dosya == "ts":
                ts_metin = ts_metin.replace(eski, yeni, 1)
            elif dosya == "ci":
                ci_metin = ci_metin.replace(eski, yeni, 1)
            else:
                # drift_imzasi `utils` paketinden import edilir: kardes kopya yolu yok =>
                # kopya team_setup'a mutant modulu `sys.modules`a ONCEDEN yukleyen on-ek
                # eklenir (gercek kaynaga YAZILMAZ).
                dz_mut = SCRIPTS / "utils" / "_zz_tsss_dz.py"
                gecici.append(dz_mut)
                dz_mut.write_bytes(hedef_metin.replace(eski, yeni, 1).encode("utf-8"))
                if ts_metin.count(CAPA_ONEK) != 1:
                    print("[DOGRULANAMADI] team_setup'ta CORE_ROOT capasi bulunamadi")
                    return 2
                ts_metin = ts_metin.replace(CAPA_ONEK, CAPA_ONEK + (
                    "import importlib.util as _iu  # MUTASYON on-eki\n"
                    "_sp = _iu.spec_from_file_location('utils.drift_imzasi', "
                    "str(CORE_ROOT / 'scripts' / 'utils' / '_zz_tsss_dz.py'))\n"
                    "_mm = _iu.module_from_spec(_sp); sys.modules['utils.drift_imzasi'] = _mm\n"
                    "_sp.loader.exec_module(_mm)\n"), 1)
        if secili or ts_kaynak != TS or ci_kaynak != CI:
            # Kopya team_setup KOPYA ureticiyi cagirsin (C6 uctan uca ayni kaynagi olcsun).
            if ts_metin.count(CAPA_URETICI) != 1:
                print("[DOGRULANAMADI] team_setup'ta uretici capasi bulunamadi")
                return 2
            ci = SCRIPTS / "_zz_tsss_ci.py"
            ts = SCRIPTS / "_zz_tsss_ts.py"
            gecici += [ci, ts]
            ci.write_bytes(ci_metin.encode("utf-8"))
            ts.write_bytes(ts_metin.replace(
                CAPA_URETICI, 'uretici = CORE_ROOT / "scripts" / "_zz_tsss_ci.py"', 1)
                .encode("utf-8"))

        tmp = Path(tempfile.mkdtemp(prefix="tsss_"))
        try:
            a_blogu(ts, tmp)
            b_blogu(ts, tmp)
            c_blogu(ts, ci, tmp)
            d_blogu(ts, tmp)
        finally:
            _sil(tmp)
            print(f"[kum-temizligi] kum duruyor mu: {'EVET' if tmp.exists() else 'hayir'}")
    finally:
        for g in gecici:
            try:
                g.unlink()
            except FileNotFoundError:
                pass
        kalan = [g.name for g in gecici if g.exists()]
        if kalan:
            print(f"[kalinti-kontrolu] TEMIZLIK BASARISIZ: {kalan}")

    gecen = sum(1 for _k, ok, _a in SONUC if ok)
    dusen = {k for k, ok, _a in SONUC if not ok}
    print(f"\nteam_setup_sablon_sapmasi: {gecen}/{len(SONUC)}")
    if secili:
        beklenen = MUTLAR[secili[0]][3]
        if not beklenen <= dusen:
            print(f"[DOGRULANAMADI] MUTASYON {secili[0]}: beklenen {sorted(beklenen)} dusmedi "
                  f"(dusen: {sorted(dusen)}) -> korpus bu degismezi OLCMUYOR")
            return 2
        print(f"  (MUTASYON {secili[0]} YAKALANDI: beklenen {sorted(beklenen)} dustu; "
              f"tum dusen {sorted(dusen)})")
        return 1
    if dusen:
        print("Dusen: " + ", ".join(sorted(dusen)))
    return 0 if not dusen else 1


if __name__ == "__main__":
    raise SystemExit(main())
