#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ix_doctor_repo_mode — K3 (GitHub-enforce) `repo_mode` LITE kiplerini okur (Q336).

KUSUR (Issue #275, 2026-09-18): `ix_doctor` `project.yaml` `repo_mode`'u okumuyordu.
PROJECT_BOOTSTRAP LITE akışı (`local`|`none`) STEP 1'i — ruleset kurulumu dahil — ATLATIR
ve `init_project` ruleset talimatını yalnız `full`'da basar; ama K3 ruleset yokluğunu FAIL
sayıyordu (sonuç hesap planına göre WARN↔FAIL değişiyordu). Remote'suz LITE projede ise
"proje remote'u çözülemedi" WARN'ı kalıcı gürültüydü.

⚠ GEVŞETME (bilinçli, dar — changelog'da `⚠GEVŞETME`): YALNIZ `local`/`none`'da ruleset + CI
SKIP. Bu korpusun işi SINIRI çivilemektir: anahtar yok · `full` · tanınmayan değer ⇒ çıktı
BUGÜNKÜ ile AYNI (R4/R5/R6/R7/R9). 3c (core-sızıntı tree taraması) LITE'ta da KOŞAR (R1).

VEKTÖRLER (her biri ayrı alt-süreç; gh SAHTE, git GERÇEK):
  R1  local + remote        → ruleset/CI SKIP (gerekçe `repo_mode=local` + "remote VAR" notu),
                               FAIL/WARN yok, ruleset/CI API ÇAĞRILMAZ, 3c KOŞAR (PASS)
  R2  none  + remote yok    → yalnız SKIP (3c dahil), WARN yok, gh HİÇ çağrılmaz
  R3  local + remote yok    → R2 ile aynı sınıf
  R4  full  + remote        → KONTROL: ruleset FAIL + CI WARN (bugünkü davranış)
  R5  anahtar YOK + remote  → R4 ile BAYT-EŞ (fail-safe)
  R6  tanınmayan değer      → R4 ile BAYT-EŞ (yazım hatası denetimi KAPATMAZ)
  R7  full  + remote yok    → bugünkü WARN "proje remote'u çözülemedi" AYNEN
  R8  local + remote + gh YOK → 3c ÖLÇÜLEMEDİ WARN'ı (sessiz geçmez)
  R9  full  + gh YOK        → bugünkü SKIP + WARN AYNEN
  R10 `LOCAL` (büyük harf)  → local sayılır (kırpma + küçük harf)

MUTASYON (bugünkü kaynaktan; çapa tam 1 kez bulunmazsa exit 2):
  --mutasyon-hep-skip      LITE ayrımı kalkar, HER kipte SKIP   → R4..R7, R9 düşer (sınır çivisi)
  --mutasyon-sizinti-atla  LITE'ta 3c de atlanır                → R1 düşer
  --mutasyon-sessiz-gh     LITE'ta gh yokken WARN düşer         → R8 düşer
TABAN (eski kod): --kaynak <ix_doctor.py>

⛔ Ağ yok, SAP yok. Sandbox projeler temp'te; remote URL'leri yer-tutucudur.
Çıkış: 0 beklendiği gibi · 1 sapma · 2 KURULAMADI
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
REPO = HERE.parents[2]
DOCTOR = REPO / "scripts" / "ix_doctor.py"
SENARYO = HERE / "_senaryo.py"
REMOTE = "https://github.com/ornek-org/ornek-repo.git"

GECERLI_KIP = ("--mutasyon-hep-skip", "--mutasyon-sizinti-atla", "--mutasyon-sessiz-gh")
KIP: set[str] = set()
TABAN: Path | None = None
_a = sys.argv[1:]
while _a:
    x = _a.pop(0)
    if x == "--kaynak" and _a:
        TABAN = Path(_a.pop(0)).resolve()
    elif x in GECERLI_KIP:
        KIP.add(x)
    else:
        print(f"[DURDU] bilinmeyen arguman: {x!r} — gecerli: {list(GECERLI_KIP)} + --kaynak")
        sys.exit(2)

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if not kosul and detay else ""))


def _degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    n = metin.count(eski)
    if n != 1:
        print(f"[DURDU] KURULAMADI: {ad} capasi {n} kez bulundu (1 bekleniyordu): {eski[:70]!r}")
        sys.exit(2)
    return metin.replace(eski, yeni)


def _kaynak_metni() -> str | None:
    if TABAN is not None:
        return TABAN.read_text(encoding="utf-8")
    if not KIP:
        return None
    m = DOCTOR.read_text(encoding="utf-8")
    if "--mutasyon-hep-skip" in KIP:
        m = _degistir(m, "    lite = mod in _LITE_REPO_MODLARI\n", "    lite = True\n", "hep-skip")
    if "--mutasyon-sizinti-atla" in KIP:
        m = _degistir(m, "    r += _katman3_sizinti(gh, tam)\n",
                      "    if not lite:\n        r += _katman3_sizinti(gh, tam)\n", "sizinti-atla")
    if "--mutasyon-sessiz-gh" in KIP:
        m = _degistir(m, "        if lite:   # remote VAR: 3c (sızıntı) anlamlı ama ölçülemiyor → sessiz geçilmez\n"
                         "            return r + [",
                      "        if lite:\n            return r\n            return r + [", "sessiz-gh")
    return m


def _git(p: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(p), *args], check=True, capture_output=True)


def proje(kok: Path, ad: str, repo_mode: str | None, remote: bool) -> Path:
    p = kok / ad
    p.mkdir(parents=True)
    satirlar = ["sap_profile: s4_private"]
    if repo_mode is not None:
        satirlar.append(f"repo_mode: {repo_mode}")
    (p / "project.yaml").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    _git(p, "init", "-q")
    if remote:
        _git(p, "remote", "add", "origin", REMOTE)
    return p


def kos(p: Path, gh: str, kaynak: Path | None, tmp: Path) -> tuple[list, list]:
    log = tmp / f"_ghlog_{p.name}_{gh}.json"
    env = {k: v for k, v in os.environ.items() if not k.startswith("IX_")}
    env.update(CLAUDE_PROJECT_DIR=str(p), PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(SENARYO), str(DOCTOR),
                        str(kaynak) if kaynak else "-", gh, str(log)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, cwd=str(p), timeout=120)
    try:
        sonuc = json.loads((r.stdout or "").strip().splitlines()[-1])
        cagri = json.loads(log.read_text(encoding="utf-8"))
    except Exception:
        print(f"[DURDU] KURULAMADI: senaryo {p.name}/{gh} cikti vermedi (rc={r.returncode}): "
              f"{(r.stderr or r.stdout)[-400:]}")
        sys.exit(2)
    return sonuc, cagri


def taglar(s: list) -> list[str]:
    return [t for t, _ in s]


def api(cagri: list, parca: str) -> bool:
    return any(parca in " ".join(c) for c in cagri)


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


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ix_repomode_"))
    try:
        metin = _kaynak_metni()
        kaynak = None
        if metin is not None:
            kaynak = tmp / "_ix_doctor_kaynak.py"
            kaynak.write_text(metin, encoding="utf-8", newline="\n")

        def k(ad, mod, remote, gh="var"):
            return kos(proje(tmp, ad, mod, remote), gh, kaynak, tmp)

        s1, c1 = k("r1_local_remote", "local", True)
        skip1 = [m for t, m in s1 if t == "SKIP"]
        kontrol("R1 local+remote: ruleset/CI SKIP (repo_mode=local + remote VAR notu), FAIL/WARN "
                "yok, ruleset/CI API cagrilmaz, 3c KOSAR",
                len(skip1) == 2 and all("repo_mode=local" in m for m in skip1)
                and "remote VAR (ornek-org/ornek-repo)" in skip1[0]
                and "FAIL" not in taglar(s1) and "WARN" not in taglar(s1)
                and not api(c1, "/rulesets") and not api(c1, "/actions/runs")
                and api(c1, "/git/trees/") and any(t == "PASS" and "sızıntı temiz" in m for t, m in s1),
                f"sonuc={s1} gh={c1}")

        s2, c2 = k("r2_none_yok", "none", False)
        kontrol("R2 none+remote yok: yalniz SKIP (3c dahil), WARN yok, gh HIC cagrilmaz",
                taglar(s2) == ["SKIP", "SKIP", "SKIP"] and all("repo_mode=none" in m for _, m in s2)
                and c2 == [], f"sonuc={s2} gh={c2}")

        s3, c3 = k("r3_local_yok", "local", False)
        kontrol("R3 local+remote yok: yalniz SKIP, WARN yok",
                taglar(s3) == ["SKIP", "SKIP", "SKIP"] and c3 == [], f"sonuc={s3}")

        s4, c4 = k("r4_full_remote", "full", True)
        kontrol("R4 full+remote (KONTROL): ruleset FAIL + CI WARN (bugunku davranis)",
                any(t == "FAIL" and "ACTIVE ruleset yok" in m for t, m in s4)
                and any(t == "WARN" and "hiç CI koşusu yok" in m for t, m in s4)
                and api(c4, "/rulesets") and api(c4, "/actions/runs"), f"sonuc={s4}")

        s5, _ = k("r5_anahtarsiz", None, True)
        kontrol("R5 anahtar YOK + remote: R4 ile BAYT-ES (fail-safe)", s5 == s4, f"sonuc={s5}")

        s6, _ = k("r6_taninmayan", "lokal", True)
        kontrol("R6 taninmayan deger ('lokal'): R4 ile BAYT-ES (yazim hatasi denetimi kapatmaz)",
                s6 == s4, f"sonuc={s6}")

        s7, _ = k("r7_full_yok", "full", False)
        kontrol("R7 full+remote yok: bugunku WARN AYNEN",
                s7 == [["WARN", "proje remote'u çözülemedi — gh kontrolleri atlandı"]], f"sonuc={s7}")

        s8, c8 = k("r8_local_ghyok", "local", True, gh="yok")
        kontrol("R8 local+remote+gh YOK: 3c OLCULEMEDI WARN'i (sessiz gecmez), FAIL yok",
                taglar(s8) == ["SKIP", "SKIP", "WARN"] and "ÖLÇÜLEMEDİ" in s8[2][1]
                and "sızıntı" in s8[2][1], f"sonuc={s8}")

        s9, _ = k("r9_full_ghyok", "full", True, gh="yok")
        kontrol("R9 full+gh YOK: bugunku SKIP+WARN AYNEN",
                s9 == [["SKIP", "gh CLI yok — GitHub-enforce katmanı atlandı"],
                       ["WARN", "gh CLI kur (https://cli.github.com) + `gh auth login` → bu katman koşulabilsin"]],
                f"sonuc={s9}")

        s10, _ = k("r10_buyuk_harf", "LOCAL", True)
        kontrol("R10 'LOCAL' → local sayilir (kirpma + kucuk harf)",
                taglar(s10)[:2] == ["SKIP", "SKIP"] and "repo_mode=local" in s10[0][1], f"sonuc={s10}")
    finally:
        _sil(tmp)

    ok = sum(1 for _, k_, _ in SONUC if k_)
    etiket = f" [TABAN {TABAN}]" if TABAN else (f" [{' '.join(sorted(KIP))}]" if KIP else "")
    print(f"\nix_doctor_repo_mode{etiket}: {ok}/{len(SONUC)} PASS")
    return 0 if ok == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
