#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guard_check_adlari — proje ruleset'inin `required_status_checks` adları (yeni-proje akışı F2).

KUSUR (yeni-proje akışı denetimi 2026-10-03, F2): `init_project` çıktısı ve PROJECT_BOOTSTRAP
STEP 6 `required_status_checks=[core-leak, behavior-surface]` diyordu. GitHub reusable
workflow'un check bağlamını `<çağıran job> / <çağrılan job adı>` diye adlandırır; canlı bir
proje ruleset'inde (salt-okur `gh api`, 2026-10-03) adlar `guard / validators` ·
`guard / behavior-surface` · `guard / core-leak`. Yani biçim yanlıştı ve `validators` eksikti
⇒ talimatı izleyen biri hiçbir koşuyla eşleşmeyen bir kontrol isterdi (PR "beklenen" diye takılır).

DÜZELTME: `init_project.guard_status_check_adlari()` adları `claude/workflows/guard.template.yml`
(çağıran) + `.github/workflows/project-guard.yml` (çağrılan) dosyalarından TÜRETİR.

VEKTÖRLER:
  G1  türetilen küme = canlı ruleset'te ölçülen üçlü (sıra: workflow sırası)
  G2  GERÇEK `main()` (repo_mode=full, geçici hedef) çıktısında aynı liste
  G3  PROJECT_BOOTSTRAP.md STEP 6 bloğu türetilen listeyle AYNI (doküman ↔ kod eşliği)
  G4  bayat `[core-leak, behavior-surface]` dizesi PROJECT_BOOTSTRAP + CODEOWNERS.template'te YOK
  G5  TÜRETME KANITI: kopya core'da job adı değişince çıktı değişir (sabit liste değil)
  G6  workflow okunamazsa None (çağıran ÖLÇÜLEMEDİ basar; sessiz yanlış ad yok)
  G7  repo_mode=local çıktısında ruleset satırı YOK (yalnız full'da basılır — kontrol)

MUTASYON (bellekte; çapa tam 1 kez bulunmazsa exit 2):
  --mutasyon-onek-yok   `<çağıran> / ` öneki düşer   → G1, G2, G3, G5 düşer
TABAN (eski kod): --kaynak <init_project.py>  → G1, G2, G3, G5, G6 düşer (fonksiyon yok /
  eski satır). Eski DOKÜMAN (PROJECT_BOOTSTRAP + CODEOWNERS.template) G3 + G4'te düşer.

Çıkış: 0 beklendiği gibi · 1 sapma · 2 KURULAMADI
"""
from __future__ import annotations

import contextlib
import io
import re
import shutil
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
INIT = CORE / "scripts" / "init_project.py"
CAGIRAN = CORE / "claude" / "workflows" / "guard.template.yml"
CAGRILAN = CORE / ".github" / "workflows" / "project-guard.yml"
BOOTSTRAP_DOC = CORE / "PROJECT_BOOTSTRAP.md"
CODEOWNERS = CORE / "claude" / "CODEOWNERS.template"
# Canlı ölçüm (2026-10-03, salt-okur `gh api repos/<ORG>/<REPO>/rulesets/<id>`) — sıra workflow sırası.
BEKLENEN = ["guard / core-leak", "guard / validators", "guard / behavior-surface"]
BAYAT = "[core-leak, behavior-surface]"

GECERLI_KIP = ("--mutasyon-onek-yok",)
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

SONUC: list[tuple[str, bool]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul)))
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if not kosul and detay else ""))


def _degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    n = metin.count(eski)
    if n != 1:
        print(f"[DURDU] KURULAMADI: {ad} capasi {n} kez bulundu (1 bekleniyordu): {eski[:70]!r}")
        sys.exit(2)
    return metin.replace(eski, yeni)


def kaynak_metni() -> str:
    if TABAN is not None:
        return TABAN.read_text(encoding="utf-8")
    m = INIT.read_text(encoding="utf-8")
    if "--mutasyon-onek-yok" in KIP:
        m = _degistir(m, '    return [f"{onek} / {ad}" for ad in isler]\n',
                      "    return list(isler)\n", "onek-yok")
    return m


def yukle(src: str):
    """`__file__` DAİMA gerçek yol: CORE_ROOT ve `utils` importu oradan çözülür."""
    mod = types.ModuleType("init_project_x")
    mod.__file__ = str(INIT)
    exec(compile(src, str(INIT), "exec"), mod.__dict__)
    return mod


def cli(mod, hedef: Path, repo_mode: str) -> tuple[int, str]:
    eski, sys.argv = sys.argv, ["init_project.py", str(hedef), "--name", "PROVA",
                                "--repo-mode", repo_mode]
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            rc = mod.main()
    finally:
        sys.argv = eski
    return rc, out.getvalue()


def turet(mod, core_root: Path):
    f = getattr(mod, "guard_status_check_adlari", None)
    if f is None:
        return "FONKSIYON-YOK"
    return f(core_root)


def kopya_core(kok: Path, cagrilan_metin: str | None) -> Path:
    (kok / "claude" / "workflows").mkdir(parents=True)
    shutil.copy2(CAGIRAN, kok / "claude" / "workflows" / CAGIRAN.name)
    if cagrilan_metin is not None:
        (kok / ".github" / "workflows").mkdir(parents=True)
        (kok / ".github" / "workflows" / CAGRILAN.name).write_text(cagrilan_metin, encoding="utf-8")
    return kok


def main() -> int:
    mod = yukle(kaynak_metni())
    tmp = Path(tempfile.mkdtemp(prefix="guard_adlari_"))
    try:
        adlar = turet(mod, CORE)
        kontrol("G1 türetilen ad listesi = canlı ruleset üçlüsü", adlar == BEKLENEN, f"adlar={adlar}")

        rc, cikti = cli(mod, tmp / "proje_full", "full")
        satir = next((s.strip() for s in cikti.splitlines() if "required_status_checks" in s), "")
        kontrol("G2 GERÇEK main() (full) çıktısında aynı liste",
                rc == 0 and satir == f"+ required_status_checks=[{', '.join(BEKLENEN)}]",
                f"rc={rc} satir={satir!r}")

        doc = BOOTSTRAP_DOC.read_text(encoding="utf-8")
        m = re.search(r"^\s*required_status_checks\s*=\s*\[(.*)\]\s*$", doc, re.M)
        doc_liste = [x.strip() for x in m.group(1).split(",")] if m else None
        kontrol("G3 PROJECT_BOOTSTRAP STEP 6 bloğu = türetilen liste (doküman ↔ kod)",
                doc_liste is not None and doc_liste == adlar, f"doc={doc_liste} kod={adlar}")

        kontrol("G4 bayat öneksiz liste PROJECT_BOOTSTRAP + CODEOWNERS.template'te YOK",
                BAYAT not in doc and BAYAT not in CODEOWNERS.read_text(encoding="utf-8"))

        degisik = CAGRILAN.read_text(encoding="utf-8").replace(
            "    name: validators\n", "    name: validators-yeni\n")
        if degisik == CAGRILAN.read_text(encoding="utf-8"):
            print("[DURDU] KURULAMADI: G5 capasi `    name: validators` project-guard.yml'de yok")
            return 2
        g5 = turet(mod, kopya_core(tmp / "core_g5", degisik))
        kontrol("G5 TÜRETME: kopya core'da job adı değişince çıktı değişir",
                g5 == ["guard / core-leak", "guard / validators-yeni", "guard / behavior-surface"],
                f"g5={g5}")

        g6 = turet(mod, kopya_core(tmp / "core_g6", None))
        kontrol("G6 project-guard.yml yok → None (ÖLÇÜLEMEDİ dalı)", g6 is None, f"g6={g6}")

        rc7, cikti7 = cli(mod, tmp / "proje_local", "local")
        kontrol("G7 KONTROL repo_mode=local → ruleset satırı basılmaz",
                rc7 == 0 and "required_status_checks" not in cikti7, f"rc={rc7}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if tmp.exists():
            print(f"[UYARI] kum silinemedi: {tmp}")

    ok = sum(1 for _, k in SONUC if k)
    etiket = f" [TABAN {TABAN}]" if TABAN else (f" [{' '.join(sorted(KIP))}]" if KIP else "")
    print(f"\nguard_check_adlari{etiket}: {ok}/{len(SONUC)} PASS")
    return 0 if ok == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
