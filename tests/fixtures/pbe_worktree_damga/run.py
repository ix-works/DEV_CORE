#!/usr/bin/env python3
"""pbe_worktree_damga — #435: worktree cwd'sinden (env boş) koşan çekicinin damgası kapıya ULAŞIR.

KUSUR (DEV_CORE Issue #435, 2026-11-15): kapı (`hooks/pull_before_edit`) store + anahtarı KENDİ
kökünden çözer (`CLAUDE_PROJECT_DIR` → cwd). Oturum ana projeden açılınca kapının kökü ANA
projedir; kanonik worktree (`<parent>/.wt/<proje>/<dal>`) ana kökün DIŞINDA olduğundan kapı ana
store'da dosyanın MUTLAK anahtarına bakar. Çekici worktree cwd'sinden `CLAUDE_PROJECT_DIR` boşken
koşunca damgayı WORKTREE store'una GÖRELİ anahtarla yazıyordu → kapı bloklamaya devam ediyordu.
ÇARE (yalnız damgalayıcı; kapı DEĞİŞMEDİ): `source_drift.tazelik_damgala` birincil store'a ek
olarak dosyanın git'ten (`rev-parse --show-toplevel --git-common-dir`) türetilen ana çalışma
ağacının + kendi ağacının store'una, o kökün kapısının hesaplayacağı anahtarla yazar. Ek hedef,
o kökün SessionStart marker'ı BAŞKA seansı gösteriyorsa yazılmaz (o seansın damgaları silinmesin).

GERÇEK GİRİŞ NOKTALARI: kapı = `hooks/pull_before_edit.py` alt süreci (stdin payload) · çekiciler
= `sap_sync_pull.py --offline --file` · `pull_msag_textpool.py msag --offline --file` ·
`fetch_ui_source.py --damgala --offline` alt süreçleri (SAP'ye gitmez). Gerçek git deposu +
`git worktree add` ile ağaç-dışı `.wt` kurulur. `scripts/` kuma KOPYALANIR (mutasyon kopyaya).

VAKALAR
  V1a/V1b/V1c  çekici cwd=wt, env boş; kapı env=ANA → 0 (ABAP / mesaj sınıfı / UI)  ← kusur
  V1d          UI çıktısı ek store'u "(yazıldı)" basar, ⚠ YOK
  V2           aynı damga, kapı env=WT (oturum worktree'de) → 0 (kendi ağacının store'u)
  K1           dosya ana projede, cwd=ana → 0 + ek store satırı YOK (tekilleştirme)
  K2 / K2b     cwd=wt, env=ANA → kapı(ANA) 0 (eski davranış) / kapı(WT) 0 (yeni)
  K3 / K3b     cwd=ana (env boş), dosya wt → kapı(ANA) 0 (eski davranış) / kapı(WT) 0 (yeni)
  K4           damga YOK → kapı 2 (pozitif kontrol; ana + wt dosyası)
  G1           ana marker BAŞKA seans → ana store BAYT-AYNI kalır + "YAZILMADI" notu; wt store yazılır
  C3           git OLMAYAN dizin (3. bağlam) → bugünkü davranış: yalnız birincil store, ek satır yok
  U1           git_agac_kokleri: worktree dosyasında (ana, wt)
  U2/U2b       UI uyarısı: worktree'de ana kök türetilemezse ⚠ (project.yaml VARKEN de); türetilirse yok
  U3           UI uyarısı: git dışı + project.yaml yok → ⚠ (eski davranış korunur)
  PR #448 bağımsız kapısı (WARNING) düzeltme turu:
  F1 / F1b     marker yok/bozuk/boş-sid + store BAŞKA seansın → dokunulmaz / store yoksa yazılır
  U1b          ana ağacın alt dizininden (git `--git-common-dir`i burada GÖRELİ verir) → (ana, ana)
  F2 / F2b     `--separate-git-dir <X>/.git` → ana = çalışma ağacı · bare depo worktree'si → ana None
  F2c          ayrık git dizinli deponun BAĞLI worktree'si → git dizininin ebeveynine store YAZILMAZ
  F3 / F3b     projeyi kapsayan depo / proje içinde iç içe depo → o köke store YAZILMAZ ("ATLANDI")

MUTASYONLAR (her biri exit 1 = DÜŞTÜ olmalı; 3 = KURULAMADI)
  --mutasyon-yardimci-yok   ek hedef türetilmez (yardımcı geri alındı) → V1a/b/c KIRMIZI
  --mutasyon-ek-anahtar     ek store'a birincil kökün anahtarı yazılır → V1a KIRMIZI
  --mutasyon-koruma-yok     başka seansın store'u sıfırlanır → G1 KIRMIZI
  --mutasyon-uyari-eski     UI uyarısı yine `project.yaml` koşuluna bağlı → U2 KIRMIZI
  --mutasyon-koruma-store-yok   marker okunamazken store sahibine bakılmaz → F1 KIRMIZI
  --mutasyon-ana-gitdir         ana kök yine `--git-common-dir` ebeveyninden → F2 KIRMIZI
  --mutasyon-ana-ayrik-yok      ana ağaçtayken de `worktree list` ilk kaydı kullanılır → F2 KIRMIZI
  --mutasyon-proje-kontrol-yok  proje olmayan git köküne de yazılır → F3 F3b KIRMIZI

Koşum: python tests/fixtures/pbe_worktree_damga/run.py [--mutasyon-…]   (exit 0 = PASS)
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "scripts"
SID = "S-ANA"

MUTASYONLAR = {
    "--mutasyon-yardimci-yok": [(
        "source_drift.py",
        "    ana, agac = git_agac_kokleri(path)\n    goruldu = {_yol_kimligi(FRESH_STORE)}\n",
        "    ana, agac = None, None\n    goruldu = {_yol_kimligi(FRESH_STORE)}\n")],
    "--mutasyon-ek-anahtar": [(
        "source_drift.py",
        "    anahtar = tazelik_anahtari(path, kok)\n",
        "    anahtar = tazelik_anahtari(path, ROOT)\n")],
    "--mutasyon-koruma-yok": [(
        "source_drift.py",
        "    if sahip and sahip != session_id:\n",
        "    if False:\n")],
    "--mutasyon-koruma-store-yok": [(
        "source_drift.py",
        "        if store_sahibi and store_sahibi != session_id:\n",
        "        if False:\n")],
    "--mutasyon-ana-gitdir": [(
        "source_drift.py",
        "    ana = agac if gd == ortak else _ana_calisma_agaci(d, env)\n",
        "    _o = Path(satirlar[2])\n"
        "    _o = _o if _o.is_absolute() else (d / _o).resolve()\n"
        "    ana = _o.parent if _o.name.lower() == \".git\" else None\n")],
    "--mutasyon-ana-ayrik-yok": [(
        "source_drift.py",
        "    ana = agac if gd == ortak else _ana_calisma_agaci(d, env)\n",
        "    ana = _ana_calisma_agaci(d, env)\n")],
    "--mutasyon-proje-kontrol-yok": [(
        "source_drift.py",
        "        if not _proje_koku_mu(Path(kok)):\n",
        "        if False:\n")],
    "--mutasyon-uyari-eski": [(
        "fetch_ui_source.py",
        "            and (kok_wt or not (Path(REPO) / \"project.yaml\").is_file())):\n",
        "            and (not (Path(REPO) / \"project.yaml\").is_file())):\n")],
}

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def _sil(d: Path) -> None:
    def _ac(func, path, _exc):  # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)  # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def kopya_kur(kum: Path, kip: str | None) -> Path:
    hedef = kum / "core" / "scripts"
    shutil.copytree(SCRIPTS, hedef, ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
    for rel, eski, yeni in MUTASYONLAR.get(kip or "", []):
        yol = hedef / rel
        metin = yol.read_text(encoding="utf-8")
        if metin.count(eski) != 1:
            print(f"[KURULAMADI] mutasyon yamasi kaynaga UYMADI ({kip}: {rel}, "
                  f"esleme={metin.count(eski)}) — sahte-yesil riski, SAYI RAPORLANMIYOR")
            raise SystemExit(3)
        yol.write_text(metin.replace(eski, yeni), encoding="utf-8", newline="\n")
    return hedef


def git(kok: Path, *arg: str) -> None:
    subprocess.run(["git", "-C", str(kok), *arg], check=True, capture_output=True)


ABAP = "SOURCE_CODES/SD/ZSD001_CLC/classes/ZCL_SD001_A.clas.abap"
MSAG = "SOURCE_CODES/SD/ZSD001_CLC/messages-ZSD001.csv"
APP = "SOURCE_CODES/SD/ZSD001_CLC/ui/app1"
UI_JS = APP + "/webapp/Component.js"
DEPLOY_YAML = ("specVersion: \"4.0\"\nmetadata:\n  name: ns.app\ntype: application\nbuilder:\n"
               "  customTasks:\n    - name: deploy-to-abap\n      afterTask: generateCachebusterInfo\n"
               "      configuration:\n        app:\n          name: ZSD001_APP1\n"
               "        exclude:\n          - /test/\n")


def depo_kur(kum: Path) -> tuple[Path, Path]:
    ana = kum / "proje"
    for rel, govde in ((ABAP, "CLASS zcl_sd001_a DEFINITION.\n"),
                       (MSAG, "MSGNR;TEXT\n001;Ornek\n"),
                       (UI_JS, "sap.ui.define([], function () { return {}; });\n"),
                       (APP + "/webapp/manifest.json", "{}\n"),
                       (APP + "/ui5-deploy.yaml", DEPLOY_YAML),
                       (APP + "/ui5.yaml", "specVersion: \"4.0\"\n"),
                       ("project.yaml", "source_root: SOURCE_CODES\n")):
        p = ana / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(govde.encode("utf-8"))
    git(ana, "init", "-q")
    for c in (["config", "user.email", "fx"], ["config", "user.name", "fx"],
              ["config", "core.autocrlf", "false"], ["add", "-A"], ["commit", "-q", "-m", "taban"]):
        git(ana, *c)
    wt = kum / ".wt" / "proje" / "dal"          # kanonik biçim: ana kökün DIŞI
    wt.parent.mkdir(parents=True, exist_ok=True)
    git(ana, "worktree", "add", "-q", "-b", "dal", str(wt))
    return ana, wt


def _env(proje: Path | None) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("IX_") and k not in ("CLAUDE_PROJECT_DIR", "CLAUDE_CWD", "INIT_CWD",
                                                     "COPILOT_CWD", "PWD", "GIT_DIR", "GIT_WORK_TREE")}
    if proje is not None:
        env["CLAUDE_PROJECT_DIR"] = str(proje)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def kapi(scripts: Path, proje: Path, dosya: Path, sid: str = SID) -> tuple[int, str]:
    govde = json.dumps({"tool_name": "Edit", "session_id": sid,
                        "tool_input": {"file_path": str(dosya)}}).encode("utf-8")
    r = subprocess.run([sys.executable, str(scripts / "hooks" / "pull_before_edit.py")],
                       input=govde, capture_output=True, env=_env(proje), cwd=str(proje), timeout=60)
    return r.returncode, r.stderr.decode("utf-8", "replace")


def kos(cwd: Path, env_proje: Path | None, *arg: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, *arg], capture_output=True, env=_env(env_proje),
                       cwd=str(cwd), timeout=180)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")


def abap_cek(scripts, cwd, env_proje, dosya, sid=SID):
    return kos(cwd, env_proje, str(scripts / "sap_sync_pull.py"), "ZCL_SD001_A",
               "--type", "class", "--file", str(dosya), "--offline", "--session", sid)


def msag_cek(scripts, cwd, env_proje, dosya, sid=SID):
    return kos(cwd, env_proje, str(scripts / "pull_msag_textpool.py"), "msag",
               "--name", "ZSD001", "--file", str(dosya), "--offline", "--session", sid)


def ui_cek(scripts, cwd, env_proje, app, sid=SID):
    return kos(cwd, env_proje, str(scripts / "fetch_ui_source.py"), "--app-dir", str(app),
               "--karsilastir", str(app / "webapp"), "--damgala", "--offline", "--session", sid)


def git_kokleri_al(cwd: Path, scripts: Path, dosya: Path) -> tuple:
    """`source_drift.git_agac_kokleri(dosya)` — ayrı süreçte (önbellek/ortam sızmasın)."""
    kod = ("import sys, json; sys.path.insert(0, sys.argv[1]); import source_drift as s; "
           "print(json.dumps([str(x) if x else None for x in s.git_agac_kokleri(sys.argv[2])]))")
    rc, out = kos(cwd, None, "-c", kod, str(scripts), str(dosya))
    try:
        a, t = json.loads(out.strip().splitlines()[-1])
        return (Path(a) if a else None), (Path(t) if t else None)
    except Exception:
        return "HATA", out[-300:]


def store(kok: Path) -> Path:
    return kok / ".claude" / ".session_fresh.json"


def temizle(*kokler: Path) -> None:
    for k in kokler:
        s = store(k)
        if s.exists():
            s.unlink()


def marker(kok: Path, sid: str) -> None:
    m = kok / ".claude" / ".current_session"
    m.parent.mkdir(parents=True, exist_ok=True)
    m.write_text(json.dumps({"session_id": sid}), encoding="utf-8")


def senaryolar(scripts: Path, kum: Path) -> None:
    ana, wt = depo_kur(kum)
    marker(ana, SID)
    wt_abap, wt_msag, wt_ui = wt / ABAP, wt / MSAG, wt / UI_JS

    # K4 — pozitif kontrol: damga yokken kapı bloklar
    temizle(ana, wt)
    rc_w, _ = kapi(scripts, ana, wt_abap)
    rc_a, _ = kapi(scripts, ana, ana / ABAP)
    kontrol("K4 damga YOK -> kapi 2 (wt dosyasi + ana dosyasi)", rc_w == 2 and rc_a == 2,
            f"wt={rc_w} ana={rc_a}")

    # V1a — kusur: ABAP çekicisi wt cwd, env boş; kapı env=ANA
    temizle(ana, wt)
    rc_c, out = abap_cek(scripts, wt, None, wt_abap)
    rc, err = kapi(scripts, ana, wt_abap)
    kontrol("V1a ABAP: cekici cwd=wt env bos -> kapi(env=ANA) 0", rc_c == 0 and rc == 0,
            f"cekici rc={rc_c} kapi rc={rc}\n{out[-500:]}\n{err[-300:]}")
    # V2 — aynı damga, oturum worktree'de açılmış (kapı env=WT)
    rc2, err2 = kapi(scripts, wt, wt_abap)
    kontrol("V2 ayni damga, kapi(env=WT) 0 (dosyanin kendi agacinin store'u)", rc2 == 0,
            f"rc={rc2} {err2[-200:]}")

    # V1b — mesaj sınıfı çekicisi
    temizle(ana, wt)
    rc_c, out = msag_cek(scripts, wt, None, wt_msag)
    rc, err = kapi(scripts, ana, wt_msag)
    kontrol("V1b MSAG: cekici cwd=wt env bos -> kapi(env=ANA) 0", rc_c == 0 and rc == 0,
            f"cekici rc={rc_c} kapi rc={rc}\n{out[-500:]}\n{err[-300:]}")

    # V1c/V1d — UI çekicisi
    temizle(ana, wt)
    rc_c, out = ui_cek(scripts, wt, None, wt / APP)
    rc, err = kapi(scripts, ana, wt_ui)
    kontrol("V1c UI: cekici cwd=wt env bos -> kapi(env=ANA) 0", rc_c == 0 and rc == 0,
            f"cekici rc={rc_c} kapi rc={rc}\n{out[-700:]}\n{err[-300:]}")
    kontrol("V1d UI ciktisi ek store'u '(yazıldı)' basar, ⚠ YOK",
            f"ek store={store(ana)} (yazıldı)" in out and "CLAUDE_PROJECT_DIR BOŞ" not in out,
            out[-700:])

    # K1 — dosya ana projede, cwd=ana: ek hedef YOK (tekilleştirme)
    temizle(ana, wt)
    rc_c, out = abap_cek(scripts, ana, None, ana / ABAP)
    rc, _ = kapi(scripts, ana, ana / ABAP)
    kontrol("K1 dosya ana, cwd=ana -> kapi 0, ek store satiri YOK, wt store YOK",
            rc_c == 0 and rc == 0 and "ek store" not in out and not store(wt).exists(),
            f"cekici rc={rc_c} kapi rc={rc}\n{out[-400:]}")

    # K2 — cwd=wt, env=ANA
    temizle(ana, wt)
    rc_c, out = abap_cek(scripts, wt, ana, wt_abap)
    rc, _ = kapi(scripts, ana, wt_abap)
    rc_wt, _ = kapi(scripts, wt, wt_abap)
    kontrol("K2 KONTROL (eski davranis) cwd=wt env=ANA -> kapi(ANA) 0", rc_c == 0 and rc == 0,
            f"cekici rc={rc_c} ana={rc}\n{out[-400:]}")
    kontrol("K2b YENI: ayni damga kapi(WT) 0 (dosyanin agaci da yazildi)", rc_wt == 0,
            f"wt={rc_wt}\n{out[-400:]}")

    # K3 — cwd=ana env boş, dosya wt (kapının ekrana yazdığı komut biçimi)
    temizle(ana, wt)
    rc_c, out = abap_cek(scripts, ana, None, wt_abap)
    rc, _ = kapi(scripts, ana, wt_abap)
    rc_wt, _ = kapi(scripts, wt, wt_abap)
    kontrol("K3 KONTROL (eski davranis) cwd=ana env bos, dosya wt -> kapi(ANA) 0",
            rc_c == 0 and rc == 0, f"cekici rc={rc_c} ana={rc}\n{out[-400:]}")
    kontrol("K3b YENI: ayni damga kapi(WT) 0", rc_wt == 0, f"wt={rc_wt}\n{out[-400:]}")

    # G1 — ana kökün etkin seansı BAŞKA: ana store'a dokunulmaz
    temizle(ana, wt)
    marker(ana, "T-BASKA")
    store(ana).parent.mkdir(parents=True, exist_ok=True)
    store(ana).write_text(json.dumps({"session_id": "T-BASKA",
                                      "objects": {"X": "2026-01-01T00:00:00Z"}}), encoding="utf-8")
    once = store(ana).read_bytes()
    rc_c, out = abap_cek(scripts, wt, None, wt_abap)
    rc_wt, _ = kapi(scripts, wt, wt_abap)
    kontrol("G1 ana marker BASKA seans -> ana store BAYT-AYNI + 'YAZILMADI' notu; kapi(WT) 0",
            rc_c == 0 and store(ana).read_bytes() == once and "YAZILMADI" in out and rc_wt == 0,
            f"cekici rc={rc_c} wt={rc_wt} ana_store={store(ana).read_text(encoding='utf-8')[:160]}"
            f"\n{out[-400:]}")
    marker(ana, SID)

    # F1 (PR #448 kapısı) — marker YOK / bozuk / boş sid + store BAŞKA seansın: dokunulmaz
    mk = ana / ".claude" / ".current_session"
    sonuc = []
    for ad, ham in (("yok", None), ("bozuk", "{bozuk"), ("bos-sid", json.dumps({"session_id": ""}))):
        temizle(ana, wt)
        if mk.exists():
            mk.unlink()
        if ham is not None:
            mk.write_text(ham, encoding="utf-8")
        store(ana).write_text(json.dumps({"session_id": "T-BASKA",
                                          "objects": {"X": "2026-01-01T00:00:00Z"}}), encoding="utf-8")
        once = store(ana).read_bytes()
        rc_c, out = abap_cek(scripts, wt, None, wt_abap)
        sonuc.append((ad, rc_c == 0 and store(ana).read_bytes() == once and "YAZILMADI" in out,
                      out[-300:]))
    kontrol("F1 marker yok/bozuk/bos-sid + ana store BASKA seansin -> ana store BAYT-AYNI + 'YAZILMADI'",
            all(ok for _, ok, _ in sonuc), "\n".join(f"{a}: {o}" for a, ok, o in sonuc if not ok))
    # F1b kontrol: marker yok + store YOK -> yazılır, kapı(ANA) geçer
    temizle(ana, wt)
    if mk.exists():
        mk.unlink()
    rc_c, out = abap_cek(scripts, wt, None, wt_abap)
    rc, _ = kapi(scripts, ana, wt_abap)
    kontrol("F1b KONTROL: marker yok + store yok -> ek store yazilir, kapi(ANA) 0",
            rc_c == 0 and rc == 0 and store(ana).is_file(), f"cekici rc={rc_c} kapi rc={rc}\n{out[-300:]}")
    marker(ana, SID)

    # U1b (PR #448 Ö1-b) — ana ağacın ALT dizininden: git `--git-common-dir`i göreli verir (Windows'ta da)
    a, t = git_kokleri_al(kum, scripts, ana / "SOURCE_CODES" / "SD" / "x.abap")
    kontrol("U1b ana agacin alt dizini -> (ana, ana)",
            isinstance(a, Path) and isinstance(t, Path) and a.resolve() == ana.resolve()
            and t.resolve() == ana.resolve(), f"{a} {t}")

    # U1 — yardımcının kendisi
    kod = ("import sys, json; sys.path.insert(0, sys.argv[1]); import source_drift as s; "
           "print(json.dumps([str(x) if x else None for x in s.git_agac_kokleri(sys.argv[2])]))")
    rc_u, out_u = kos(kum, None, "-c", kod, str(scripts), str(wt_abap))
    try:
        a, t = json.loads(out_u.strip().splitlines()[-1])
        u1 = bool(rc_u == 0 and a and t and Path(a).resolve() == ana.resolve()
                  and Path(t).resolve() == wt.resolve())
    except Exception:
        u1 = False
    kontrol("U1 git_agac_kokleri(wt dosyasi) -> (ana, wt)", u1, out_u[-300:])

    # U2 — worktree'de ana kök türetilemezse ⚠ (project.yaml worktree'de VAR)
    kod = ("import sys; sys.path.insert(0, sys.argv[1]); import source_drift as s; "
           "s.git_agac_kokleri = lambda p: (None, None); import fetch_ui_source as F; "
           "from pathlib import Path; print(F.damga_yeri(Path(sys.argv[2])))")
    rc_u, out_u = kos(wt, None, "-c", kod, str(scripts), str(wt / APP / "webapp"))
    kontrol("U2 UI: wt cwd + env bos + ana kok TURETILEMEDI -> ⚠ (project.yaml varken de)",
            rc_u == 0 and (wt / "project.yaml").is_file() and "CLAUDE_PROJECT_DIR BOŞ" in out_u
            and "worktree" in out_u, out_u[-400:])
    # U2b kontrol: ana kök türetilebiliyorsa ⚠ YOK
    kod2 = ("import sys; sys.path.insert(0, sys.argv[1]); import fetch_ui_source as F; "
            "from pathlib import Path; print(F.damga_yeri(Path(sys.argv[2])))")
    rc_u, out_u = kos(wt, None, "-c", kod2, str(scripts), str(wt / APP / "webapp"))
    kontrol("U2b KONTROL: ayni yer, git calisiyor -> ⚠ YOK",
            rc_u == 0 and "store=" in out_u and "CLAUDE_PROJECT_DIR BOŞ" not in out_u, out_u[-400:])


def ucuncu_baglam(scripts: Path, kum: Path) -> None:
    """C3/U3 — git OLMAYAN dizin: bugünkü davranış (yalnız birincil store) aynen."""
    duz = kum / "gitsiz"
    f = duz / ABAP
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"CLASS zcl_sd001_a DEFINITION.\n")
    git_mi = subprocess.run(["git", "-C", str(duz), "rev-parse", "--show-toplevel"],
                            capture_output=True).returncode == 0
    if git_mi:
        kontrol("C3 [KURULAMADI] gecici dizin bir git deposunun icinde — 3. baglam olculemedi",
                False, str(duz))
        return
    rc_c, out = abap_cek(scripts, duz, None, f)
    rc, _ = kapi(scripts, duz, f)
    kontrol("C3 git disi dizin -> rc 0, birincil store yazildi, ek store satiri YOK, kapi 0",
            rc_c == 0 and store(duz).is_file() and "ek store" not in out and rc == 0,
            f"cekici rc={rc_c} kapi rc={rc}\n{out[-400:]}")
    app = duz / APP
    (app / "webapp").mkdir(parents=True, exist_ok=True)
    (app / "webapp" / "Component.js").write_bytes(b"x\n")
    (app / "ui5-deploy.yaml").write_bytes(DEPLOY_YAML.encode())
    rc_c, out = ui_cek(scripts, duz, None, app)
    kontrol("U3 UI git disi + project.yaml YOK -> ⚠ (eski davranis korunur)",
            rc_c == 0 and "CLAUDE_PROJECT_DIR BOŞ" in out and "proje kökü DEĞİL" in out, out[-500:])


def git_bicimleri(scripts: Path, kum: Path) -> None:
    """F2/F3 (PR #448 kapısı) — ayrık git dizini · bare ana · kapsayan depo · iç içe depo."""
    # F2 — `git init --separate-git-dir`: ana kök git dizininin EBEVEYNİ değil, çalışma ağacıdır
    sep = kum / "sepw"
    gd = kum / "gitdizinleri" / "sepw" / ".git"      # kapının ölçtüğü biçim: `<X>/.git`
    gd.parent.mkdir(parents=True, exist_ok=True)
    sep.mkdir(parents=True, exist_ok=True)
    git(sep, "init", "-q", "--separate-git-dir", str(gd))
    f = sep / ABAP
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"x\n")
    (sep / "project.yaml").write_bytes(b"source_root: SOURCE_CODES\n")
    for c in (["config", "user.email", "fx"], ["config", "user.name", "fx"], ["add", "-A"],
              ["commit", "-q", "-m", "t"]):
        git(sep, *c)
    a, t = git_kokleri_al(kum, scripts, f)
    kontrol("F2 ayrik git dizini (ana agactan) -> ana = calisma agaci (git dizininin ebeveyni DEGIL)",
            isinstance(a, Path) and a.resolve() == sep.resolve() and isinstance(t, Path)
            and t.resolve() == sep.resolve(), f"{a} {t}")
    # F2c — ayrık git dizinli deponun BAĞLI worktree'si: git ana ağacı yanlış bilir (gd.parent);
    # o kök proje değil ⇒ oraya store YAZILMAZ
    swt = kum / ".wt" / "sepw" / "dal"
    swt.parent.mkdir(parents=True, exist_ok=True)
    git(sep, "worktree", "add", "-q", "-b", "dal", str(swt))
    rc_c, out = abap_cek(scripts, swt, None, swt / ABAP)
    kontrol("F2c ayrik git dizinli deponun bagli worktree'si -> git dizini ebeveynine store YAZILMAZ",
            rc_c == 0 and not store(gd.parent).exists(), f"cekici rc={rc_c}\n{out[-300:]}")
    # F2b — bare depodan açılmış worktree: ana çalışma ağacı YOK
    kaynak = kum / "bkaynak"
    kaynak.mkdir()
    (kaynak / "a.txt").write_bytes(b"x\n")
    for c in (["init", "-q"], ["config", "user.email", "fx"], ["config", "user.name", "fx"],
              ["add", "-A"], ["commit", "-q", "-m", "t"]):
        git(kaynak, *c)
    bare = kum / "b.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(kaynak), str(bare)], check=True,
                   capture_output=True)
    bwt = kum / "bwt"
    git(bare, "worktree", "add", "-q", str(bwt))
    bf = bwt / ABAP
    bf.parent.mkdir(parents=True, exist_ok=True)
    bf.write_bytes(b"x\n")
    a, t = git_kokleri_al(kum, scripts, bf)
    kontrol("F2b bare depo worktree'si -> ana None, agac = worktree",
            a is None and isinstance(t, Path) and t.resolve() == bwt.resolve(), f"{a} {t}")

    # F3 — projeyi KAPSAYAN depo (proje kökünde git yok, üstte var): kapsayana yazılmaz
    dis = kum / "dis"
    dis.mkdir()
    (dis / "a.txt").write_bytes(b"x\n")
    for c in (["init", "-q"], ["config", "user.email", "fx"], ["config", "user.name", "fx"],
              ["add", "-A"], ["commit", "-q", "-m", "t"]):
        git(dis, *c)
    proj = dis / "proj"
    pf = proj / ABAP
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_bytes(b"x\n")
    (proj / "project.yaml").write_bytes(b"source_root: SOURCE_CODES\n")
    rc_c, out = abap_cek(scripts, proj, None, pf)
    rc, _ = kapi(scripts, proj, pf)
    kontrol("F3 kapsayan depo (proje degil) -> dis/.claude store YAZILMAZ + 'ATLANDI'; birincil kapi 0",
            rc_c == 0 and rc == 0 and not store(dis).exists() and "ATLANDI" in out,
            f"cekici rc={rc_c} kapi rc={rc} dis_store={store(dis).exists()}\n{out[-300:]}")
    # F3b — proje İÇİNDE iç içe depo: iç deponun köküne yazılmaz
    ic = proj / "SOURCE_CODES" / "ic"
    ic.mkdir(parents=True)
    git(ic, "init", "-q")
    icf = ic / "ZCL_SD001_A.clas.abap"
    icf.write_bytes(b"x\n")
    rc_c, out = abap_cek(scripts, proj, None, icf)
    kontrol("F3b ic ice depo -> ic/.claude store YAZILMAZ + 'ATLANDI'",
            rc_c == 0 and not store(ic).exists() and "ATLANDI" in out,
            f"cekici rc={rc_c} ic_store={store(ic).exists()}\n{out[-300:]}")


def main(argv: list[str]) -> int:
    kipler = [a for a in argv if a.startswith("--")]
    if any(k not in MUTASYONLAR for k in kipler) or len(kipler) > 1:
        print(f"[KULLANIM] gecerli kipler: {sorted(MUTASYONLAR)} (en fazla bir) — verilen: {kipler}")
        return 2
    kip = kipler[0] if kipler else None
    print("=" * 78)
    print(f"pbe_worktree_damga — #435 worktree damgasi{'  KIP=' + kip if kip else ''}")
    print("=" * 78)
    kum = Path(tempfile.mkdtemp(prefix="pbe_wt_damga_"))
    try:
        scripts = kopya_kur(kum, kip)
        for bolum in (senaryolar, ucuncu_baglam, git_bicimleri):
            try:
                bolum(scripts, kum)
            except BaseException as exc:  # noqa: BLE001 — çökme != FAIL: bölüm adıyla görünür
                if isinstance(exc, KeyboardInterrupt):
                    raise
                kontrol(f"[BOLUM COKTU] {bolum.__name__}", False, f"{type(exc).__name__}: {exc}")
    finally:
        _sil(kum)
    kirik = [a for a, ok, _ in SONUC if not ok]
    for ad, ok, detay in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
        if not ok:
            print(f"         gorulen: {detay}")
    print(f"\n{len(SONUC) - len(kirik)}/{len(SONUC)} PASS")
    return 1 if kirik else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
