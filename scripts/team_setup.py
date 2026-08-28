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
  --provision-worktree [P]: D16 — worktree'ye junction'lar + izlenmeyen runtime dosyaları
                            (.conn_adt, conn/, settings.local.json → hardlink/kopya).
                            P OPSİYONEL: verilmezse içinde bulunulan worktree provizyonlanır.

WORKTREE YAŞAM DÖNGÜSÜ (2026-08-29 — kayıt #80):
  KANONİK KÖK = `<proje.parent>/.wt/<proje.adı>/<dal-etiketi>` (sürücü/klasör sabiti YOK, D24).
  ⭐ Kök her reponun DIŞINDADIR: repo kökünden `rglob`/`os.walk` yapan araçlar (statusline,
     validator'lar, behavior_manifest) worktree kopyalarına YAPISAL olarak ulaşamaz — aynı
     hata sınıfı (bayat kopya taranması) mekanik olarak imkânsızlaşır.
  --wt-ac DAL             : kanonik yolda worktree aç + provizyonla (çağıran PATH üretmez)
  --wt-yolu DAL           : kanonik yolu yalnız BAS (script'ler için)
  --wt-denetim            : GÜN-SONU süpürgesi — kayıtsız yetim · `git cherry` ile main'e
                            gitmemiş commit · kirli ağaç · `gitdir`siz bayat metadata.
                            HİÇBİR ŞEY SİLMEZ; exit 1 = operatör müdahalesi gerek.
  --wt-kapat DAL|PATH     : kapat — silme sırası DAİMA junction-önce; denetim temiz değilse
                            `--zorla` ister; her adım tekrar-denemeli.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import shutil
import subprocess
import sys
import time
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


def _bag_kaldir(link: Path) -> None:
    """Bagi kaldir, HEDEFE DOKUNMA. Platform-guvenli (silme-matrisi kanitli).

    Windows junction = dizin reparse point => `rmdir` (icerige GIRMEZ).
    POSIX symlink   = dosya girdisi        => `unlink` (`rmdir` `NotADirectoryError` verir).
    Sira ONEMLI: once `is_symlink()` sorulur; Windows'ta junction `is_symlink()` False
    dondurur ve dogru sekilde `rmdir` dalina duser.
    """
    if link.is_symlink():
        link.unlink()
    else:
        link.rmdir()


def junction_kur(link: Path, hedef: Path) -> bool:
    """Windows: junction (`mklink /J`, admin gerektirmez) · POSIX: symlink. True=sağlam.

    ⚠ PLATFORM DALI (2026-08-29): eskiden `cmd /c mklink` KOSULSUZ cagriliyordu =>
    core POSIX'te (Linux gelistirici / konteyner / CI) kurulursa `FileNotFoundError: 'cmd'`.
    Bugune kadar zararsizdi cunku `team_setup.py` CI'da KOSMUYOR; ilk POSIX kurulumunda patlardi.
    Emsal desen ICAT EDILMEDI, repoda calisir halde duran iki kardesten alindi:
    `tests/fixtures/fs_docstd/run.py::_junction` (:213-222) ve
    `scripts/tests/guard_conformance.py::_core_link` (:59-70).
    Olculen sey her iki platformda AYNI: "<proje>/core baska bir agaca cozuluyor mu"
    (`os.readlink`/`resolve()`) — symlink bu olcum icin junction'in esdegeridir.
    """
    if link.exists() or link.is_symlink():   # kirik symlink `exists()` False dondurur
        mevcut = junction_hedefi(link)
        if mevcut and mevcut.resolve() == hedef.resolve():
            say(OK, f"junction sağlam: {link} → {hedef}")
            return True
        if mevcut:
            say(WARN, f"junction YANLIŞ hedefe: {link} → {mevcut}; yeniden kuruluyor")
            try:
                _bag_kaldir(link)  # linki kaldırır, HEDEFE DOKUNMAZ (silme-matrisi kanıtlı)
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
    if os.name == "nt":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(hedef)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            say(OK, f"junction kuruldu: {link} → {hedef}")
            return True
        say(FAIL, f"mklink başarısız: {(r.stderr or r.stdout).strip()}")
        return False
    try:
        os.symlink(str(hedef), str(link), target_is_directory=True)
    except OSError as exc:
        say(FAIL, f"symlink başarısız: {type(exc).__name__}: {exc}")
        return False
    say(OK, f"symlink kuruldu (POSIX): {link} → {hedef}")
    return True


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


# ===========================================================================
# WORKTREE YASAM DONGUSU (2026-08-29) — kanonik kok · gun-sonu denetimi · kapatma
# ---------------------------------------------------------------------------
# NEDEN: `--provision-worktree PATH` worktree'yi PROVIZYONLAR ama NEREDE acilacagini
# SOYLEMEZ. Yol her oturumda yeniden icat edildi; temizlik kimsenin gorevi degildi.
# Olculdu 2026-08-28: tek makinede DORT artik worktree, DORT farkli adlandirma
# (`<proje>/.claude/worktrees/agent-<id>` · `<kok>/.wt/core-<konu>` · `<kok>/_wt/<konu>` ·
# `<kok>/DEV_CORE-<dal>`); ikisi git'e kayitli, ikisi KAYITSIZ YETIM; en eskisi 3 haftalik.
#
# ⭐ KANONIK KOK REPO'NUN DISINDADIR — bu bir kolaylik degil, YAPISAL bir koruma:
# repo kokunden `rglob`/`os.walk` yapan araclar (statusline, validator'lar, behavior_manifest)
# oraya ULASAMAZ. Ic worktree'lerde ayni sinif iki kez isirdi (2026-08-18: 8 validator bayat
# kopyayi taradi · 2026-08-28: statusline Sprint/Transport'u donmus kopyadan cozdu).
# Budama listesi o hatalari SONRADAN kapatir; kokun disarida olmasi onlari MEKANIK olarak
# imkansizlastirir. Ikisi birbirinin yerine gecmez: budama ESKI/IC worktree'ler icin durur.
# ===========================================================================

WT_KOK_ADI = ".wt"


def wt_kok(proje: Path) -> Path:
    """KANONIK worktree koku: `<proje.parent>/.wt/<proje.adi>`.

    Olculdu 2026-08-29: bu kokte 7 worktree acildi ve calisti. Surucu/klasor SABIT
    VARSAYIMI YOK (D24) — kok proje yolundan turetilir, `C:\\...` gomulmez.
    """
    return proje.parent / WT_KOK_ADI / proje.name


def wt_ad(dal: str) -> str:
    """Dal adindan dizin etiketi: son '/'-segmenti (`infra/2026-08-29-x` -> `2026-08-29-x`)."""
    return dal.strip("/").split("/")[-1] or dal


def wt_yolu(proje: Path, dal: str) -> Path:
    """`<kanonik-kok>/<dal-etiketi>` — cagiranin PATH uretmesine gerek YOK."""
    return wt_kok(proje) / wt_ad(dal)


def _git(proje: Path, *arg: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(proje), *arg],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def _kayitli_worktreeler(proje: Path) -> list[tuple[Path, str]]:
    """`git worktree list --porcelain` -> [(yol, dal), ...] (ana agac HARIC)."""
    r = _git(proje, "worktree", "list", "--porcelain")
    sonuc, yol, dal = [], None, ""
    for satir in (r.stdout or "").splitlines():
        if satir.startswith("worktree "):
            yol, dal = Path(satir[9:].strip()), ""
        elif satir.startswith("branch "):
            dal = satir[7:].strip().replace("refs/heads/", "")
        elif not satir.strip() and yol is not None:
            sonuc.append((yol, dal)); yol, dal = None, ""
    if yol is not None:
        sonuc.append((yol, dal))
    ana = proje.resolve()
    return [(p, d) for p, d in sonuc if p.resolve() != ana]


def _disk_worktreeleri(proje: Path) -> list[Path]:
    """Kanonik kok + ESKI (repo-ici) konum: `<proje>/.claude/worktrees/`."""
    bulunan: list[Path] = []
    for kok in (wt_kok(proje), proje / ".claude" / "worktrees"):
        if kok.is_dir():
            bulunan += [d for d in kok.iterdir() if d.is_dir()]
    return bulunan


def _yetimde_ozgun_icerik(proje: Path, yetim: Path) -> list[str]:
    """④ git'siz yetimde OZGUN is var mi — icerik NESNE-VERITABANINDA var mi diye sorulur.

    ⛔ Duz dosya karsilastirmasi YETMEZ: olculdu 2026-08-28, satir-sonu gurultusu
    **150 "farkli" dosya** gosterdi, gercek fark **24**'tu. `git hash-object` icerigi
    normalize eder; `git cat-file -e` o nesnenin depoda olup olmadigini KESIN soyler.
    """
    ozgun: list[str] = []
    atla = {".git", "node_modules", "__pycache__", ".tmp", "dist", "core",
            ".claude", "worktrees"}
    for dirpath, dirnames, filenames in os.walk(yetim):
        dirnames[:] = [d for d in dirnames
                       if d not in atla and junction_hedefi(Path(dirpath) / d) is None]
        for ad in filenames:
            f = Path(dirpath) / ad
            h = _git(proje, "hash-object", str(f))
            sha = (h.stdout or "").strip()
            if not sha:
                continue
            if _git(proje, "cat-file", "-e", sha).returncode != 0:
                ozgun.append(str(f.relative_to(yetim)).replace("\\", "/"))
    return ozgun


def _bayat_wt_metadata(proje: Path) -> list[Path]:
    """`gitdir` dosyasi OLMAYAN `.git/worktrees/<ad>/` kalintilari.

    Olculdu 2026-08-28: `git worktree remove` dizini birakip metadata'yi yarim biraktiginda
    geriye yalniz `ORIG_HEAD` + bos `refs`/`logs` kalir ve **`git fetch` HER KOSUDA hata verir**.
    `git worktree prune` bunlari her zaman toplamaz => ayrica raporlanir.
    """
    r = _git(proje, "rev-parse", "--git-common-dir")
    kok = Path((r.stdout or "").strip() or (proje / ".git"))
    if not kok.is_absolute():
        kok = (proje / kok).resolve()
    d = kok / "worktrees"
    return [x for x in d.iterdir() if x.is_dir() and not (x / "gitdir").is_file()] \
        if d.is_dir() else []


def wt_denetim(proje: Path) -> int:
    """GUN-SONU WORKTREE SUPURGESI (`CLAUDE.core.md §1.1` gun-sonu adimi).

    Cikis: 0 = temiz · 1 = OPERATOR MUDAHALESI gerek (yetim / main'e gitmemis is / kirli agac).
    ⛔ Hicbir sey SILMEZ — silme ayri ve acik bir komuttur (`--wt-kapat`).
    """
    say(INFO, f"worktree denetimi — proje={proje}  kanonik kok={wt_kok(proje)}")
    bulgu = 0

    kayitli = _kayitli_worktreeler(proje)
    kayitli_yollar = {p.resolve() for p, _ in kayitli}
    diskte = _disk_worktreeleri(proje)

    # ① kayit <-> disk karsilastirmasi (kayitsiz yetim = fark)
    yetimler = [d for d in diskte if d.resolve() not in kayitli_yollar]
    say(INFO, f"① git'e kayitli: {len(kayitli)} · diskte: {len(diskte)} · KAYITSIZ YETIM: {len(yetimler)}")

    # ② her dal icin `git cherry -v main <dal>`
    # ⛔ `--is-ancestor` KULLANILMAZ: squash-merge'de YANILTIR. Olculdu 2026-08-28:
    #    bes dalin BESI de "merge edilmemis" gorundu, besi de `git cherry` ile `-` cikti.
    for yol, dal in kayitli:
        if not dal:
            say(WARN, f"② {yol} — detached HEAD, dal yok; `git cherry` kosulamadi"); bulgu = 1
            continue
        c = _git(proje, "cherry", "-v", "main", dal)
        if c.returncode != 0:
            say(WARN, f"② `git cherry` hata ({dal}): {(c.stderr or '').strip()[:120]}"); bulgu = 1
            continue
        satirlar = [s for s in (c.stdout or "").splitlines() if s.strip()]
        yeni = [s for s in satirlar if s.startswith("+")]
        say(OK if not yeni else FAIL,
            f"② {dal}: main'de OLMAYAN {len(yeni)} commit / toplam {len(satirlar)} "
            f"('-' = yamasi main'de ZATEN VAR)")
        if yeni:
            bulgu = 1
            for s in yeni[:5]:
                print(f"        {s}")

        # ③ calisma agaci kirli mi — SIDDET AYRILIR (korpusa karsi olculdu 2026-08-29)
        # `--ignored` VAZGECILMEZ: hasat edilmemis is gitignore'lu dizinlerde yasar
        # (olculmus vaka: 3 worktree'de commit'lenmemis infra-expert hafizasi, kayit #39 I-4).
        # ⛔ AMA `!!`yi FAIL saymak kapiyi KALICI KIRMIZI yapar: 6 canli worktree'de
        # 122 kaydin **104'u** (%85) yok-sayilan `.tmp/` scratch ve `__pycache__` idi
        # => uyari korlugu. Bu yuzden: izlenen/izlenmeyen degisiklik FAIL uretir,
        # yok-sayilanlar SCRATCH ELENDIKTEN sonra ayrica HASAT ADAYI olarak raporlanir.
        st = _git(yol, "status", "--short", "--ignored", "--untracked-files=all")
        satir3 = [s for s in (st.stdout or "").splitlines() if s.strip()]
        izlenen = [s for s in satir3 if not s.startswith("!!")]
        yoksayilan = [s for s in satir3 if s.startswith("!!")]
        hasat = [s for s in yoksayilan
                 if not any(g in s.replace("\\", "/")
                            for g in ("/.tmp/", " .tmp/", "__pycache__", ".pyc"))]
        say(OK if not izlenen else FAIL,
            f"③ {yol.name}: izlenen/izlenmeyen {len(izlenen)} kayit "
            f"(+{len(yoksayilan)} yok-sayilan, bunlarin {len(hasat)}'i HASAT ADAYI)")
        if izlenen:
            bulgu = 1
            for s in izlenen[:5]:
                print(f"        {s}")
        if hasat:
            bulgu = 1
            say(WARN, f"③b {yol.name}: gitignore'lu ama SCRATCH DEGIL — silmeden ONCE hasat et")
            for s in hasat[:5]:
                print(f"        {s}")

    # ④ git'siz yetimlerde ozgun icerik var mi
    for y in yetimler:
        ozgun = _yetimde_ozgun_icerik(proje, y)
        say(FAIL if ozgun else WARN,
            f"④ YETIM {y}: yalnizca-yetimde {len(ozgun)} dosya "
            f"({'SILME — once hasat et' if ozgun else 'icerigin tamami git nesne-veritabaninda'})")
        bulgu = 1
        for s in ozgun[:5]:
            print(f"        {s}")

    # ⑤ yarim kalan `.git/worktrees/<ad>` metadata'si (`git fetch`'i her koşuda bozar)
    bayat = _bayat_wt_metadata(proje)
    if bayat:
        bulgu = 1
        say(FAIL, f"⑤ `gitdir`siz metadata kalintisi: {len(bayat)} "
                  f"(git fetch'i bozar; `git worktree prune` denendikten sonra elle silinir)")
        for b in bayat[:5]:
            print(f"        {b}")

    say(OK if bulgu == 0 else FAIL,
        "worktree denetimi TEMIZ" if bulgu == 0 else "worktree denetimi: OPERATOR MUDAHALESI gerek")
    return bulgu


def wt_kapat(proje: Path, hedef: str, zorla: bool = False) -> bool:
    """Worktree'yi KAPAT — silme sirasi DAIMA junction-once.

    ⛔ SIRA HAYATIDIR: junction/symlink bir reparse point'tir; `rm -rf`/`rmtree` icine
    GIRERSE HEDEFI (canli core agacini) siler. Once baglar `rmdir`/`unlink` ile kaldirilir,
    SONRA agac silinir.
    ⚠ `git worktree remove` 2026-08-28'de DORT vakada da `Permission denied` verdi ve
    metadata'yi silip DIZINI BIRAKTI (kismi basarisizlik) => her adim TEKRAR DENENIR.
    ⛔ Once `wt_denetim` kosar; main'e gitmemis is ya da kirli agac varsa `--zorla` olmadan
    DOKUNMAZ (yikim-once/insa-sonra sinifi: kismi basarisizlikta kayip TOPLAM olur).
    """
    yol = Path(hedef)
    if not yol.is_absolute():
        yol = wt_yolu(proje, hedef)
    if not yol.exists():
        say(FAIL, f"worktree yok: {yol}"); return False

    if not zorla and wt_denetim(proje) != 0:
        say(FAIL, "denetim TEMIZ degil — kapatma YAPILMADI. Once hasat et ya da --zorla ver.")
        return False

    # 1) BAGLAR (junction/symlink) — hedefe DOKUNMADAN
    for rel in ("core", ".claude/agents", ".claude/skills", ".claude/commands", ".claude/rules"):
        bag = yol / rel
        if bag.is_symlink() or (bag.exists() and junction_hedefi(bag) is not None):
            try:
                _bag_kaldir(bag); say(OK, f"bag kaldirildi: {rel}")
            except OSError as exc:
                say(FAIL, f"bag KALDIRILAMADI: {rel} — {type(exc).__name__}: {exc}")
                return False                      # ⛔ bag dururken agaca DOKUNMA

    # 2) AGAC — once git'in kendi yolu, sonra rmtree; ikisi de TEKRAR DENEMELI
    for deneme in (1, 2, 3):
        if _git(proje, "worktree", "remove", "--force", str(yol)).returncode == 0 \
                and not yol.exists():
            break
        if yol.exists():
            shutil.rmtree(yol, ignore_errors=True)
        if not yol.exists():
            break
        say(WARN, f"silme {deneme}. denemede tamamlanmadi (handle kilidi?) — tekrar")
        time.sleep(1.0)

    _git(proje, "worktree", "prune")
    if yol.exists():
        say(FAIL, f"worktree DIZINI KALDI: {yol} — elle incele (baglar kaldirildi, hedef guvende)")
        return False
    say(OK, f"worktree kapatildi: {yol}")
    return True


def wt_ac(proje: Path, dal: str, taban: str = "origin/main") -> bool:
    """Kanonik yolda worktree AC + provizyonla. Cagiran PATH vermez — yol turetilir."""
    yol = wt_yolu(proje, dal)
    if yol.exists():
        say(FAIL, f"zaten var: {yol}"); return False
    yol.parent.mkdir(parents=True, exist_ok=True)
    _git(proje, "fetch", "-q", "origin")
    r = _git(proje, "worktree", "add", "-b", dal, str(yol), taban)
    if r.returncode != 0:
        say(FAIL, f"git worktree add: {(r.stderr or r.stdout).strip()[:200]}"); return False
    say(OK, f"worktree acildi: {yol} (dal={dal}, taban={taban})")
    return provision_worktree(yol, proje)


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
    # PATH artik OPSIYONEL (2026-08-29): verilmezse icinde bulunulan worktree provizyonlanir.
    # `const` bilerek bos dizge DEGIL bir SENTINEL: `if a.provision_worktree:` truthiness
    # testi bos dizgeyi "verilmedi" sanardi (sessiz NO-OP). Kontrol `is not None` ile yapilir.
    ap.add_argument("--provision-worktree", metavar="PATH", nargs="?", const="<CWD>",
                    help="D16 provizyonu. PATH verilmezse cwd (bir worktree ICINDE olmali).")
    ap.add_argument("--wt-ac", metavar="DAL",
                    help="Kanonik yolda (<proje.parent>/.wt/<proje>/<dal>) worktree AC + provizyonla.")
    ap.add_argument("--wt-yolu", metavar="DAL",
                    help="Kanonik worktree yolunu BAS (script'ler icin; hicbir sey yaratmaz).")
    ap.add_argument("--wt-denetim", action="store_true",
                    help="GUN-SONU worktree supurgesi: yetim + main'e gitmemis is + kirli agac + bayat metadata. Hicbir sey silmez.")
    ap.add_argument("--wt-kapat", metavar="DAL|PATH",
                    help="Worktree'yi kapat (junction-ONCE silme sirasi). Denetim temiz degilse --zorla ister.")
    ap.add_argument("--zorla", action="store_true", help="--wt-kapat: denetim bulgusuna ragmen sil.")
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
    if a.wt_yolu:
        print(wt_yolu(proje, a.wt_yolu)); return 0
    if a.wt_denetim:
        return wt_denetim(proje)
    if a.wt_kapat:
        return 0 if wt_kapat(proje, a.wt_kapat, zorla=a.zorla) else 1
    if a.wt_ac:
        return 0 if wt_ac(proje, a.wt_ac) else 1
    if a.provision_worktree is not None:
        if a.provision_worktree == "<CWD>":
            hedef = Path.cwd().resolve()
            gd = subprocess.run(["git", "-C", str(hedef), "rev-parse", "--git-dir"],
                                capture_output=True, text=True)
            if "worktrees" not in (gd.stdout or "").replace("\\", "/"):
                say(FAIL, f"PATH verilmedi ve cwd bir worktree DEGIL: {hedef} "
                          f"(kanonik kok: {wt_kok(proje)})")
                return 1
        else:
            hedef = Path(a.provision_worktree).resolve()
        return 0 if provision_worktree(hedef, proje) else 1
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
