#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""team_setup.py — Geliştirici/proje kurulumu ve onarımı (ADR 0020; canlı-çekirdek modeli).

CORE içinde yaşar; hedef PROJE cwd'den veya --project ile alınır (D24: kökler
__file__-türetimli, sabit sürücü/klasör varsayımı YOK).

Yaptıkları:
  1. Python >= 3.10 + pip install (MCP requirements)
  2. CORE reposunda `core.hooksPath scripts/git-hooks` (D19 — pre-commit gate'leri)
  3. PROJE'de 4 JUNCTION kur/doğrula (admin gerektirmez, mklink /J; D25: tek tek rapor):
       core / .claude\\agents / .claude\\skills / .claude\\commands
  4. Eksik proje-lokal dosyaları template'ten tamamla (settings.json, hook_shim.py)
  5. Claude Code plugin'leri (setup_plugins.py; non-fatal) + seed_memory (--no-seed ile atla)
  6. Smoke: statusline + MCP import
  --repair-junctions      : yalnız junction kur/onar + rapor (session_start'ın önerdiği komut)
  --provision-worktree P  : D16 — worktree'ye junction'lar + izlenmeyen runtime dosyaları
                            (.conn_adt, conn/, settings.local.json → hardlink/kopya)
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CORE_ROOT = Path(__file__).resolve().parent.parent          # D24
MIN_PY = (3, 10)
REQ_FILE = CORE_ROOT / "mcp_servers" / "sap_adt" / "requirements.txt"

OK, WARN, FAIL, INFO = "[ OK ]", "[WARN]", "[FAIL]", "[INFO]"


def say(lv: str, msg: str) -> None:
    print(f"{lv} {msg}")


def junction_hedefi(link: Path) -> Path | None:
    """Junction/symlink hedefini döndür; değilse None.
    Windows readlink '\\\\?\\' extended-length öneki döndürür — kıyas için soyulur
    (soyulmazsa sağlam junction 'YANLIŞ hedefe' sanılıp gereksiz yeniden kurulur)."""
    try:
        ham = str(os.readlink(link))
        if ham.startswith("\\\\?\\"):
            ham = ham[4:]
        return Path(ham)
    except (OSError, ValueError):
        return None


def junction_kur(link: Path, hedef: Path) -> bool:
    """mklink /J (admin gerektirmez). True=sağlam."""
    if link.exists():
        mevcut = junction_hedefi(link)
        if mevcut and mevcut.resolve() == hedef.resolve():
            say(OK, f"junction sağlam: {link} → {hedef}")
            return True
        if mevcut:
            say(WARN, f"junction YANLIŞ hedefe: {link} → {mevcut}; yeniden kuruluyor")
            try:
                link.rmdir()  # linki kaldırır, HEDEFE DOKUNMAZ (silme-matrisi kanıtlı)
            except OSError as exc:
                # Aynı sınıf, Q30 (2026-08-27): Windows'ta dizin/bağ kaldırma dışarıdan
                # tutulan bir handle yüzünden ANLIK olarak WinError 5 verebilir. Eskiden
                # istisna main()'e kadar çıkıp kurulumun kalan adımlarını atlatıyordu.
                say(FAIL, f"junction kaldirilamadi: {link} — {type(exc).__name__}: {exc}")
                return False
        else:
            say(FAIL, f"{link} junction DEĞİL gerçek klasör — elle incele, DOKUNMADIM")
            return False
    link.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(hedef)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        say(OK, f"junction kuruldu: {link} → {hedef}")
        return True
    say(FAIL, f"mklink başarısız: {(r.stderr or r.stdout).strip()}")
    return False


def junctions(proje: Path, overlay_onayli: bool = False) -> bool:
    """5 junction (D25: her biri TEK TEK raporlanır — kopuk agents/skills SESSİZ semptom verir).
    core · .claude/agents · .claude/skills · .claude/commands · .claude/rules (L1b, 2026-07-10).

    OVERLAY (opt-in, 2026-07-09): `claude-local/<tip>/*.md` varsa o tip için junction YERİNE
    gerçek dizin üretilir (core + proje override). Yoksa davranış aynen junction — mevcut
    projeler etkilenmez. Detay: utils/claude_overlay.py
    """
    import sys as _sys
    _sys.path.insert(0, str(CORE_ROOT / "scripts"))
    from utils import claude_overlay as ov  # type: ignore

    ok = junction_kur(proje / "core", CORE_ROOT)
    for tip in ov.TIPLER:
        # ⚠ TİP-BAŞINA YALITIM (2026-08-27, Q30): tek bir tipte fırlayan istisna eskiden
        # main()'e kadar çıkıyordu ⇒ döngünün KALAN tipleri + dosya_tamamla + hookspath_*
        # + _core_index_yenile HİÇ koşmuyordu. Ölçülmüş vaka: `materyalize`
        # `PermissionError [WinError 5]` verdi, `.claude/agents` boş kaldı ve kurulumun
        # geri kalan 5 adımı sessizce atlandı. Yalıtım SUSTURMAZ: FAIL satırı basılır ve
        # ok=False ile main() 1 döner.
        try:
            if ov.overlay_var_mi(proje, tip):
                basarili, mesaj = ov.materyalize(proje, CORE_ROOT, tip, onayli=overlay_onayli)
                print(f"  [{'OK' if basarili else 'FAIL'}] overlay .claude/{tip} — {mesaj}")
            else:
                basarili = junction_kur(proje / ".claude" / tip, CORE_ROOT / "claude" / tip)
        except Exception as exc:  # noqa: BLE001
            say(FAIL, f".claude/{tip} KURULAMADI — {type(exc).__name__}: {exc} "
                      f"(diger tipler denenmeye DEVAM ediyor; kurulum yine de BASARISIZ sayilir)")
            basarili = False
        ok = ok and basarili
    return ok


def _core_index_yenile(proje: Path) -> None:
    """`governance/CORE-INDEX.md`'i tazele — core/ junction'i Grep/Glob'a gorunmez oldugu
    icin metodolojinin TEK kokten-aranabilir giris noktasi budur (2026-07-09 denetimi)."""
    uretici = CORE_ROOT / "scripts" / "build_core_index.py"
    if not uretici.is_file():
        return
    r = subprocess.run([sys.executable, str(uretici)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env=dict(os.environ, CLAUDE_PROJECT_DIR=str(proje)))
    print(f"  [{'OK' if r.returncode == 0 else 'FAIL'}] CORE-INDEX: "
          f"{(r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr).strip() else '?'}")


def _sha(yol: Path) -> str:
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def shim_tazele(proje: Path) -> bool:
    """`scripts/hook_shim.py`'yi şablondan TAZELE — AÇIK ONAYLA (`--tazele-shim`).

    NİÇİN VAR (2026-08-22, kullanıcı kararı: "araç yazsın, rol değil"):
    prosedür *"META-İNFRA (hook_shim) = yalnız LİDER"* der; `infra_write_guard` ise
    *"muaf yalnız infra-expert"* der ⇒ **kesişim BOŞ, kimse meşru yazamıyordu.**
    `dosya_tamamla` idempotenttir ve mevcut dosyayı EZMEZ ⇒ sürüklenen bir shim'i
    tazeleyecek onaylı yol YOKTU. Bu fonksiyon o yolu açar; **rolü değiştirmez.**

    ⛔ VARSAYILAN DAVRANIŞ DEĞİŞMEZ: bayraksız koşumda bu fonksiyon HİÇ çağrılmaz,
    `dosya_tamamla` bugünkü gibi idempotent kalır ve hiçbir dosya ezilmez.

    ⚠⚠ TERS YÖN — ASIL TEHLİKE (ölçülmüş, 2026-08-22): proje kopyası şablondan
    **İLERİDE** olabilir. Tam bugün yaşandı: `infra_write_guard` projedeki shim'de
    kabloluydu, şablonda YOKTU ⇒ körlemesine tazeleme AKTİF BİR KORUMAYI **sessizce
    fail-open** yapardı. Bu yüzden tazeleme **farkı ekrana basmadan YAPILMAZ** ve
    proje-özel satırlar ADEDİYLE + gürültülü bir uyarıyla bildirilir. Aynı ders
    `claude_overlay` kapısında da kayıtlı (elle düzeltmeyi sessizce ezme).
    """
    hedef = proje / "scripts" / "hook_shim.py"
    kaynak = CORE_ROOT / "claude" / "hook_shim.template.py"
    if not kaynak.is_file():
        say(FAIL, f"şablon YOK: {kaynak} — tazeleme yapılamaz")
        return False
    if not hedef.is_file():
        say(WARN, f"{hedef} YOK — tazelenecek bir kopya yok; normal üretim yolu "
                  f"(dosya_tamamla) zaten oluşturur")
        return False

    onceki_sha, sablon_sha = _sha(hedef), _sha(kaynak)
    if onceki_sha == sablon_sha:
        say(OK, f"hook_shim.py ZATEN şablonla aynı (sha256 {onceki_sha[:12]}) — "
                f"tazeleme gereksiz, dosyaya DOKUNULMADI")
        return True

    eski = hedef.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    yeni = kaynak.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    fark = list(difflib.unified_diff(yeni, eski, fromfile="ŞABLON (core)",
                                     tofile="PROJE kopyası", n=2))
    # `fromfile=ŞABLON`, `tofile=PROJE` ⇒ "+" = YALNIZ PROJEDE olan satır (proje İLERİDE),
    # "-" = yalnız şablonda olan satır (proje GERİDE). Yön okunmadan tazeleme YAPILMAZ.
    proje_ozel = [l for l in fark if l.startswith("+") and not l.startswith("+++")]
    sablon_ozel = [l for l in fark if l.startswith("-") and not l.startswith("---")]

    print(f"\n  --- hook_shim FARK RAPORU (tazelemeden ÖNCE) ---")
    print(f"  şablon sha256 : {sablon_sha}")
    print(f"  proje   sha256: {onceki_sha}")
    for satir in fark:
        print("  " + satir.rstrip("\n"))
    print(f"  --- yalnız PROJEDE: {len(proje_ozel)} satır · "
          f"yalnız ŞABLONDA: {len(sablon_ozel)} satır ---")
    if proje_ozel:
        say(WARN, f"⚠ TERS YÖN: proje kopyası şablondan İLERİDE görünüyor "
                  f"({len(proje_ozel)} satır YALNIZ projede). Tazeleme bu satırları "
                  f"SİLER. Ölçülmüş vaka: projede kablolu bir hook şablonda yoktu ⇒ "
                  f"körlemesine tazeleme aktif korumayı SESSİZCE fail-open yapardı. "
                  f"Devam ediliyor (bayrak AÇIK onaydır) ama önce yedek alınır.")

    yedek = hedef.with_suffix(f".py.yedek-{onceki_sha[:8]}")
    shutil.copyfile(hedef, yedek)
    say(OK, f"yedek alındı: {yedek.name} (tazeleme GERİ ALINABİLİR)")

    shutil.copyfile(kaynak, hedef)
    sonraki_sha = _sha(hedef)
    if sonraki_sha != sablon_sha:
        say(FAIL, f"tazeleme DOĞRULANAMADI: sonuç sha256 {sonraki_sha[:12]} != "
                  f"şablon {sablon_sha[:12]}")
        return False
    say(OK, f"hook_shim.py TAZELENDİ — doğrulandı: sonuç sha256 == şablon sha256 "
            f"({sonraki_sha[:12]})")
    return True


def dosya_tamamla(proje: Path) -> None:
    """Eksik proje-lokal dosyaları template'ten üret (idempotent — var olanı EZMEZ).

    ⛔ BU FONKSİYON DEĞİŞMEDİ (2026-08-22): tazeleme AYRI ve OPT-IN bir yoldur
    (`shim_tazele` + `--tazele-shim`). Buraya "farklıysa ez" eklemek, kurulumun
    rutin bir adımını sessiz bir ezme aracına çevirirdi.
    """
    tpl = CORE_ROOT / "claude"
    hedefler = [
        (proje / ".claude" / "settings.json", tpl / "settings.template.json"),
        (proje / "scripts" / "hook_shim.py",  tpl / "hook_shim.template.py"),
    ]
    for hedef, kaynak in hedefler:
        if hedef.exists():
            say(OK, f"mevcut: {hedef.name} (drift denetimi: session_start D7)")
        else:
            hedef.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(kaynak, hedef)
            say(OK, f"template'ten üretildi: {hedef}")


def hookspath_core() -> None:
    """D19: core reposunda versiyonlanan git-hook'ları etkinleştir."""
    gh = CORE_ROOT / "scripts" / "git-hooks"
    if not gh.is_dir():
        say(WARN, "core scripts/git-hooks henüz yok (B11) — hooksPath atlandı")
        return
    r = subprocess.run(["git", "-C", str(CORE_ROOT), "config",
                        "core.hooksPath", "scripts/git-hooks"], capture_output=True, text=True)
    say(OK if r.returncode == 0 else FAIL, f"core.hooksPath=scripts/git-hooks ({CORE_ROOT})")


def hookspath_proje(proje: Path) -> None:
    """PROJE reposunda pre-commit gate'ini kabla (2026-07-10 template provası).

    `init_project` `scripts/git-hooks/pre-commit`i üretir; ama `core.hooksPath` set
    edilmezse git onu ASLA çalıştırmaz — dosya var, gate yok. TD'de bu boşluk aylarca
    açık kaldı ve pre-commit elle kuruldu. Kod ≠ kablolama.
    """
    hook = proje / "scripts" / "git-hooks" / "pre-commit"
    if not (proje / ".git").exists():
        say(WARN, "proje git reposu değil — pre-commit kablolaması atlandı (repo_mode=none)")
        return
    if not hook.is_file():
        say(WARN, "proje scripts/git-hooks/pre-commit yok — init_project --force ile üret")
        return
    try:
        os.chmod(hook, os.stat(hook).st_mode | 0o111)  # POSIX'te çalıştırılabilir olmalı
    except OSError:
        pass
    r = subprocess.run(["git", "-C", str(proje), "config",
                        "core.hooksPath", "scripts/git-hooks"], capture_output=True, text=True)
    say(OK if r.returncode == 0 else FAIL, f"proje core.hooksPath=scripts/git-hooks ({proje})")


def provision_worktree(worktree: Path, proje: Path) -> bool:
    """D16: worktree'de junction'lar + git'in getirmediği runtime dosyaları."""
    say(INFO, f"worktree provizyonu: {worktree} (ana proje: {proje})")
    ok = junctions(worktree)
    for rel in (".conn_adt", ".claude/settings.local.json"):
        src, dst = proje / rel, worktree / rel
        if not src.exists():
            say(WARN, f"kaynakta yok, atlandı: {rel}")
            continue
        if dst.exists():
            say(OK, f"zaten var: {rel}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(src, dst)  # hardlink: aynı volume, admin istemez
            say(OK, f"hardlink: {rel}")
        except OSError:
            shutil.copyfile(src, dst)
            say(OK, f"kopya (hardlink olmadı): {rel}")
    src_conn, dst_conn = proje / "conn", worktree / "conn"
    if src_conn.is_dir() and not dst_conn.exists():
        shutil.copytree(src_conn, dst_conn)
        say(OK, "conn/ kopyalandı")
    return ok


def npm_clis() -> None:
    """Token-verimli CLI'ler (governance/tooling-plugins.md; makine-düzeyi, repo'da DEĞİL):
    playwright-cli = ADR 0017 ui-smoke gate'i + tarayıcı-doğrulamanın TEMELİ (skill core'da,
    binary global gerekir). NON-FATAL: yoksa playwright-MCP-plugin'ine düşülür."""
    if not shutil.which("npm"):
        say(WARN, "npm YOK — playwright-cli/ast-grep/mmdc/marp atlandı "
                  "(node kur, sonra: npm i -g @playwright/cli @ast-grep/cli)")
        return
    clis = [
        ("playwright-cli", "@playwright/cli@latest", "token-verimli tarayıcı doğrulama (ADR 0017 ui-smoke)"),
        ("ast-grep", "@ast-grep/cli@latest", "yapısal kod arama/refactor (AST)"),
        ("mmdc", "@mermaid-js/mermaid-cli@latest", "Mermaid → SVG/PNG (FS/TS/KD)"),
        ("marp", "@marp-team/marp-cli@latest", "Markdown → slayt (PDF/PPTX)"),
    ]
    for binary, pkg, desc in clis:
        if shutil.which(binary):
            say(OK, f"{binary} kurulu ({desc})")
            continue
        r = subprocess.run(["npm", "install", "-g", pkg], capture_output=True, text=True)
        say(OK if r.returncode == 0 else WARN,
            f"{binary} {'kuruldu' if r.returncode == 0 else 'KURULAMADI (opsiyonel): ' + (r.stderr or '')[:120]}")


def alt_arac(proje: Path, ad: str, non_fatal_msg: str) -> None:
    """core scripts/<ad> aracını proje cwd'siyle koş (non-fatal)."""
    script = CORE_ROOT / "scripts" / ad
    if not script.exists():
        return
    r = subprocess.run([sys.executable, str(script)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=proje)
    say(OK if r.returncode == 0 else WARN,
        f"{ad} (exit {r.returncode}) {(r.stdout or '').strip().splitlines()[-1][:70] if (r.stdout or '').strip() else non_fatal_msg}")


def smoke(proje: Path) -> None:
    st = CORE_ROOT / "scripts" / "statusline.py"
    try:
        r = subprocess.run([sys.executable, str(st)], input="{}", capture_output=True,
                           text=True, cwd=proje, timeout=30)
        say(OK if r.returncode == 0 else WARN, f"statusline smoke (exit {r.returncode})")
    except subprocess.TimeoutExpired:
        say(WARN, "statusline smoke timeout")
    env = dict(os.environ, PYTHONPATH=str(CORE_ROOT), CLAUDE_PROJECT_DIR=str(proje))
    r = subprocess.run([sys.executable, "-c",
                        "import mcp_servers.sap_adt.server; print('import-ok')"],
                       capture_output=True, text=True, cwd=proje, env=env, timeout=60)
    say(OK if "import-ok" in (r.stdout or "") else WARN,
        f"MCP server import smoke ({((r.stdout or r.stderr) or '').strip()[:60]})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", default=".", help="Proje kökü (default: cwd)")
    ap.add_argument("--repair-junctions", action="store_true")
    ap.add_argument("--overlay-onayli", action="store_true", help="T2.5: overlay fark-raporu onayi — mevcut .claude kopyalari uretilecekten farkliysa ancak bu bayrakla EZILIR")
    ap.add_argument("--tazele-shim", action="store_true",
                    help="scripts/hook_shim.py'yi sablondan TAZELE (ACIK onay). Once FARK "
                         "raporu + sha256 basar, yedek alir, sonra sha esitligini dogrular. "
                         "Bayraksiz kosumda hicbir dosya EZILMEZ (davranis degismez).")
    ap.add_argument("--provision-worktree", metavar="PATH")
    ap.add_argument("--no-install", action="store_true")
    ap.add_argument("--no-seed", action="store_true")
    ap.add_argument("--no-plugins", action="store_true")
    ap.add_argument("--no-smoke", action="store_true")
    a = ap.parse_args()

    proje = Path(a.project).resolve()
    print(f"team_setup — core = {CORE_ROOT}\n            proje = {proje}\n")

    if a.tazele_shim:
        # AYRI ve ERKEN dal: tazeleme tek işi yapar, kurulumun geri kalanını koşturmaz
        # (yan etki yüzeyi mümkün olduğunca dar).
        return 0 if shim_tazele(proje) else 1
    if a.provision_worktree:
        return 0 if provision_worktree(Path(a.provision_worktree).resolve(), proje) else 1
    if a.repair_junctions:
        ok = junctions(proje, overlay_onayli=a.overlay_onayli)
        _core_index_yenile(proje)
        return 0 if ok else 1

    if sys.version_info < MIN_PY:
        say(FAIL, f"Python {MIN_PY[0]}.{MIN_PY[1]}+ gerekli"); return 1
    say(OK, f"Python {sys.version.split()[0]}")

    if not a.no_install and REQ_FILE.exists():
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                            str(REQ_FILE)], capture_output=True, text=True)
        say(OK if r.returncode == 0 else WARN, "pip install (MCP requirements)")

    if not junctions(proje, overlay_onayli=a.overlay_onayli):
        say(FAIL, "junction kurulumu TAMAMLANAMADI — yukarıdaki satırlara bak")
        return 1
    dosya_tamamla(proje)
    hookspath_core()
    hookspath_proje(proje)
    # 2026-07-10 template provası: CORE-INDEX yalnız `--repair-junctions` yolunda
    # üretiliyordu → her YENİ proje C-IDX-01 FAIL ile açılıyordu (ilk `run_all_validators`
    # kırmızı). Kurulumun bir parçası olmalı: junction Grep/Glob'a görünmez, indeks tek
    # kökten-aranabilir giriş noktası (D29).
    _core_index_yenile(proje)

    if not a.no_plugins:
        alt_arac(proje, "setup_plugins.py", "plugin kurulumu (claude CLI gerekli)")
        npm_clis()  # playwright-cli + ast-grep + mmdc + marp (non-fatal)
    if not a.no_seed:
        alt_arac(proje, "seed_memory.py", "memory tohumu")

    if not (proje / ".conn_adt").exists():
        say(WARN, ".conn_adt YOK — SAP için doldurulmalı (PROJECT_BOOTSTRAP STEP 4)")
    if not a.no_smoke:
        smoke(proje)
    say(OK, "team_setup TAMAM — kabul gate'i: oturum aç → ekran-teyidi + MCP ping + validators")
    return 0


if __name__ == "__main__":
    sys.exit(main())
