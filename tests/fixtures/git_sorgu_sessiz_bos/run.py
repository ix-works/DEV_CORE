# -*- coding: utf-8 -*-
"""git_sorgu_sessiz_bos — deploy_ui `--all-changed`: ARIZA ≠ "değişiklik yok" (KAYIT S5).

KÖK: `changed_apps()` iki git komutu koşuyor ama ÇIKIŞ KODLARINA hiç bakmıyordu. `HEAD~1`
çözülemeyen bir ağaçta (tek-commit'lik repo, `--depth 1` shallow clone) git **exit 128 +
"fatal: ambiguous argument 'HEAD~1'"** verir; çıktıda yol satırı olmadığı için küme boş
kalır → çağıran bunu "değişen app yok" diye okur, **exit 0 ile hiçbir şey deploy etmez**.
Deploy'un sessizce atlanması, deploy'un bayat gitmesiyle aynı sınıftır: kullanıcı canlıda
göremeyene kadar fark edilmez (bu script'in var oluş sebebi tam olarak o vakadır).

Fixture GERÇEK git repoları kurar (sentetik; gerçek hedefe dokunmaz).

Koşum:  python tests/fixtures/git_sorgu_sessiz_bos/run.py
MUTASYON: changed_apps'te `if rc != 0` dalını kaldır → V1/V2 FAIL.
          main()'deki git_hatalari bloğunu kaldır → V2 FAIL.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


def git(repo: Path, *a) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *a], cwd=str(repo), capture_output=True, text=True)


def cagir(ui_root: Path) -> tuple[list, list]:
    """changed_apps()'i çağır; ESKİ tek-liste dönüşünü de tolere et.

    MUTASYON dostu: eski sürüm `list` döndürüyordu → burada `(liste, [])` sayılır, yani
    "hiç hata raporlamadı". Böylece fix-öncesi kod ÇÖKMEK yerine ÖLÇÜLEN bir sonuç verir
    ve hangi vektörlerin ayırt edici olduğu görünür (V3/V4 FP çapaları iki sürümde de geçer).
    """
    r = D.changed_apps(ui_root)
    if isinstance(r, tuple):
        return r
    return list(r), []


def repo_kur(commit_sayisi: int) -> Path:
    """ui/app1/webapp içeren sentetik git reposu; `commit_sayisi` kadar commit."""
    repo = Path(tempfile.mkdtemp(prefix="s5_")) / "proje"
    (repo / "ui" / "app1" / "webapp").mkdir(parents=True)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "test")
    for i in range(commit_sayisi):
        (repo / "ui" / "app1" / "webapp" / f"Main{i}.view.xml").write_text("<x/>", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", f"c{i}")
    return repo


# deploy_ui REPO'yu İMPORT ANINDA project_root()'tan okur → env önce kurulur.
TEK = repo_kur(1)          # HEAD~1 ÇÖZÜLEMEZ  (bozuk bağlam)
os.environ["CLAUDE_PROJECT_DIR"] = str(TEK)
sys.path.insert(0, str(KOK / "scripts"))
import deploy_ui as D  # noqa: E402

# ── V1 — BOZUK BAĞLAM: git arızası SESSİZ BOŞ LİSTEYE dönüşmüyor ───────────────
apps, hatalar = cagir(TEK / "ui")
kontrol("V1 tek-commit'lik repo (HEAD~1 yok): arıza RAPORLANIYOR, sessiz boş liste YOK",
        apps == [] and len(hatalar) >= 1 and "HEAD~1" in " ".join(hatalar),
        f"apps={apps} hatalar={hatalar}")

# ── V2 — KABLOLAMA: main() bu durumda exit 1 veriyor ("yok" demiyor) ──────────
eski_argv = sys.argv
sys.argv = ["deploy_ui.py", "--all-changed", "--ui-root", str(TEK / "ui")]
try:
    rc = D.main()
except SystemExit as e:      # argparse
    rc = e.code
finally:
    sys.argv = eski_argv
kontrol("V2 KABLOLAMA: --all-changed git arızasında exit 1 (0 = 'iş yok' YANLIŞ)",
        rc == 1, f"rc={rc}")

# ── V3 — TEMİZ BAĞLAM (FP ÇAPASI): 2 commit + değişiklik → app BULUNUR, hata YOK ─
COK = repo_kur(2)
D.REPO = COK                      # aynı süreçte 2. bağlam (import-anı REPO'yu değiştir)
apps, hatalar = cagir(COK / "ui")
kontrol("V3 FP ÇAPASI: sağlam repoda app BULUNUYOR ve hata listesi BOŞ (davranış aynı)",
        apps == ["app1"] and hatalar == [], f"apps={apps} hatalar={hatalar}")

# ── V4 — TEMİZ + DEĞİŞİKLİK YOK (FP ÇAPASI): meşru "boş" hâlâ meşru ───────────
BOS = repo_kur(2)
(BOS / "not.txt").write_text("ui disi degisiklik", encoding="utf-8")
git(BOS, "add", "-A"); git(BOS, "commit", "-qm", "ui-disi")
D.REPO = BOS
apps, hatalar = cagir(BOS / "ui")
kontrol("V4 FP ÇAPASI: son commit ui/ DIŞINDAysa boş liste + hata YOK (meşru 'iş yok')",
        apps == [] and hatalar == [], f"apps={apps} hatalar={hatalar}")

# ── V5 — 3. BAĞLAM (görev-dışı): git reposu OLMAYAN dizin ────────────────────
DEGIL = Path(tempfile.mkdtemp(prefix="s5_gitsiz_"))
(DEGIL / "ui" / "app1" / "webapp").mkdir(parents=True)
D.REPO = DEGIL
apps, hatalar = cagir(DEGIL / "ui")
kontrol("V5 3.BAĞLAM: git reposu OLMAYAN dizinde iki sorgu da arıza olarak raporlanıyor",
        apps == [] and len(hatalar) == 2, f"apps={apps} hatalar={hatalar}")

# ── V6 — sözleşme: changed_apps ARTIK ÇİFT dönüyor (çağıranı kırık bırakmasın) ─
ham = D.changed_apps(DEGIL / "ui")
kontrol("V6 sözleşme: changed_apps() -> (list, list) ikilisi döner",
        isinstance(ham, tuple) and len(ham) == 2,
        f"dönen tip={type(ham).__name__}")

for d in (TEK.parent, COK.parent, BOS.parent, DEGIL):
    shutil.rmtree(d, ignore_errors=True)

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)
