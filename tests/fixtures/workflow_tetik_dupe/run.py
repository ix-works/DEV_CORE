#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""workflow_tetik_dupe fixture — guard tetigi AYNI SHA'yi iki kez dogrulamamali.

NEDEN VAR (2026-08-13, infra-kuyruk kaydi; proje reposu `governance/infra-findings.md`):
Proje `guard.yml`'i `on: push` (DALSIZ) + `pull_request` tasiyordu. PR dalina atilan her
push'ta GitHub iki ayri kosu baslatir (push olayi + pull_request olayi) ve ikisi de AYNI
head SHA'yi dogrular -> PR basina 3 kosu x 3 job = 9 job, 3'u saf cogaltma.
CANLI OLCUM (`gh run list`, bir PROJE reposunun ard arda BES PR dongusu): besinde de
branch-push ve pull_request kosulari ayni head SHA'ya sahipti. `template_project`
(public) ayni deseni tasiyordu -> vaka degil SINIF.

FIX: `push:` -> `push: branches: [main]`. Kaybolan koruma YOK (asagida V3/V4 capalari):
silinen branch-push kosusunda `behavior-surface` zaten no-op'tu (REF != refs/heads/main).

⛔ NEDEN `concurrency` DEGIL: olculdu — branch-push kosusu, pull_request kosusu DOGMADAN
bitiyor (bir dongude 05:35:07->05:35:31 bitti, PR kosusu 05:35:33 dogdu). `cancel-in-progress`
iptal edecek kosu bulamazdi; tasarruf 0. Bu fixture o secenegi degil, tetik-daraltmayi kilitler.

⚠ BAGIMLILIK: bu repo BILEREK pyyaml tasimaz (`scripts/utils/project_config.py` lite-parser
kullanir; core-ci yalniz requests/urllib3/python-dotenv kurar). Bu yuzden asagidaki `on:`
cozumleyicisi ELDE yazilmistir — `import yaml` CI'da COKERDI.

SENARYOLAR (V1/V2 AYIRT EDICI; V3/V4 FP capasi; V5/V6/V7 kapsam+3.baglam; V8 cozumleyici):
  V1 ESKI tetik (donmus literal) + PR-dalina-push -> 2 kosu   (bozuk hal URETILEBILIYOR mu)
  V2 CANLI sablon dosyasi        + PR-dalina-push -> 1 kosu   (ASIL KAYIT; mutasyonda duser)
  V3 FP: canli sablon PR ACILISINDA hala kosuyor   -> 1
  V4 FP: canli sablon MAIN-PUSH'ta hala kosuyor    -> 1  (behavior-surface F1 savunmasi ayakta)
  V5 KAPSAM (bilincli daralma): dal-push (PR yok) ve TAG-push -> 0   [karar, kaza degil]
  V6 3.BAGLAM (gorev-disi): repo'nun KENDI core-ci.yml'i ZATEN temiz -> 1  (kontrol grubu)
  V7 reusable project-guard.yml tetik TASIMAZ (workflow_call) -> fix dogru dosyada mi
  V8 cozumleyici FP capasi: `branches:[develop]` main-push'ta 0 -> dal listesi GERCEKTEN
     okunuyor (varlik-tespiti degil), yoksa V4 bedava gecerdi
"""
from __future__ import annotations

import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")

SABLON = REPO / "claude" / "workflows" / "guard.template.yml"
CORE_CI = REPO / ".github" / "workflows" / "core-ci.yml"
REUSABLE = REPO / ".github" / "workflows" / "project-guard.yml"

# 2026-08-13 ONCESI hal — DONMUS LITERAL (tarihsel sartname; dosyadan okunmaz ki fix
# geri alinsa bile V1 "bozuk hal boyleydi" demeye devam etsin).
ESKI_TETIK = "on:\n  push:\n  pull_request:\n"


# ── `on:` blogu cozumleyicisi (elde; pyyaml YOK — dosya basindaki nota bkz) ──────────
def on_blogu(metin: str) -> dict[str, dict]:
    """Workflow metninden `on:` blogunu cikar: {olay: {"branches": [...] | None}}.

    Yalniz bu repoda kullanilan sekilleri tanir: `push:` (bos) · `push:` + `branches: [a, b]`
    veya `- a` liste · `pull_request:` · `workflow_call:`. Taninmayan sekil sessizce
    YUTULMAZ -> `_COZULEMEDI` anahtari eklenir ve `kosu_sayisi` patlar.
    """
    satirlar = metin.splitlines()
    bas = None
    for i, s in enumerate(satirlar):
        if s.rstrip() == "on:" or (s.startswith("on:") and s[3:4] in (" ", "")):
            bas = i
            break
    if bas is None:
        return {"_COZULEMEDI": {}}

    kuyruk = satirlar[bas][3:].strip()          # inline sekil: `on: push`
    if kuyruk and not kuyruk.startswith("#"):
        return {kuyruk: {"branches": None}}

    olaylar: dict[str, dict] = {}
    aktif = None
    for s in satirlar[bas + 1:]:
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        girinti = len(s) - len(s.lstrip())
        if girinti == 0:                        # blok bitti
            break
        govde = s.strip()
        if girinti <= 2:                        # olay adi
            if not govde.endswith(":"):
                olaylar["_COZULEMEDI"] = {}
                break
            aktif = govde[:-1]
            olaylar[aktif] = {"branches": None}
        else:                                   # olay alt-anahtari
            if aktif is None:
                olaylar["_COZULEMEDI"] = {}
                break
            if govde.startswith("branches:"):
                deger = govde[len("branches:"):].strip()
                if deger.startswith("[") and deger.endswith("]"):
                    olaylar[aktif]["branches"] = [
                        d.strip().strip("'\"") for d in deger[1:-1].split(",") if d.strip()
                    ]
                elif deger == "":
                    olaylar[aktif]["branches"] = []      # blok liste; `- x` satirlari gelir
                else:
                    olaylar["_COZULEMEDI"] = {}
                    break
            elif govde.startswith("- ") and olaylar[aktif].get("branches") == []:
                olaylar[aktif]["branches"].append(govde[2:].strip().strip("'\""))
            # diger alt-anahtarlar (types:, paths:) bu sinif icin ilgisiz -> yok sayilir
    return olaylar


# ── GitHub tetik semantigi modeli ────────────────────────────────────────────────────
# KAYNAK: GitHub Actions dokumantasyonu "Events that trigger workflows" — `push` olayi
# `branches` filtresi verilmezse TUM dal VE etiket push'larinda tetiklenir; `pull_request`
# AYRI bir olaydir (varsayilan tipler: opened/synchronize/reopened). Yani PR dalina push =
# IKI olay = IKI kosu. Model, CANLI olcumle capraz dogrulandi (ayni head SHA iki kosuda).
def kosu_sayisi(tetik: dict[str, dict], olay: str, ref: str) -> int:
    """Verilen `on:` blogu, (olay, ref) icin KAC kosu uretir?"""
    if "_COZULEMEDI" in tetik:
        raise AssertionError("cozumleyici `on:` blogunu anlayamadi — fixture sessizce gecmez")
    n = 0
    if olay in ("dal-push", "main-push", "tag-push", "pr-dalina-push"):
        if "push" in tetik:
            dallar = tetik["push"].get("branches")
            if dallar is None:                      # filtre YOK -> her dal + her etiket
                n += 1
            elif ref.startswith("refs/heads/") and ref[len("refs/heads/"):] in dallar:
                n += 1
    if olay in ("pr-acilis", "pr-dalina-push") and "pull_request" in tetik:
        n += 1                                      # opened / synchronize
    return n


SENARYOLAR: list[tuple[str, bool, str]] = []


def vektor(ad: str, beklenen: int, gercek: int, not_: str = "") -> None:
    SENARYOLAR.append((ad, beklenen == gercek, f"beklenen={beklenen} gercek={gercek} {not_}"))


def main() -> int:
    canli = on_blogu(SABLON.read_text(encoding="utf-8"))
    eski = on_blogu(ESKI_TETIK)

    # V1 — bozuk hal URETILEBILIYOR mu (yoksa V2 neyi kanitladigini bilemeyiz)
    vektor("V1 ESKI tetik + PR-dalina-push = CIFT kosu",
           2, kosu_sayisi(eski, "pr-dalina-push", "refs/heads/feature"),
           "(dalsiz push + pull_request)")

    # V2 — ASIL KAYIT (AYIRT EDICI): canli sablon dosyasi tek kosu uretmeli.
    #      Sablon geri alinirsa YALNIZ bu vektor duser.
    vektor("V2 CANLI sablon + PR-dalina-push = TEK kosu",
           1, kosu_sayisi(canli, "pr-dalina-push", "refs/heads/feature"),
           f"({SABLON.relative_to(REPO).as_posix()})")

    # V3/V4 — FP capalari: fix ASIRI daraltmadi. (V2'den AYRI tutulur; birlestirilirse
    # "dogru vaka bozulmadi" kaniti sessizce kaybolur.)
    vektor("V3 FP: canli sablon PR ACILISINDA kosuyor",
           1, kosu_sayisi(canli, "pr-acilis", "refs/pull/1/merge"))
    vektor("V4 FP: canli sablon MAIN-PUSH'ta kosuyor",
           1, kosu_sayisi(canli, "main-push", "refs/heads/main"),
           "(behavior-surface F1 savunmasi ayakta)")

    # V5 — BILINCLI KAPSAM DARALMASI (gevseme cetveli capasi): bunlar KARAR'dir, kaza degil.
    #      Degismez korunur: main'e inen her sey ya PR ya main-push kosusundan gecer.
    vektor("V5a KAPSAM: PR'siz dal-push artik kosmuyor (KARAR)",
           0, kosu_sayisi(canli, "dal-push", "refs/heads/feature"))
    vektor("V5b KAPSAM: tag-push artik kosmuyor (KARAR)",
           0, kosu_sayisi(canli, "tag-push", "refs/tags/v1"))

    # V6 — 3. BAGLAM (gorev-disi dosya): DEV_CORE'un KENDI CI'i bastan beri temiz = kontrol
    #      grubu. Burasi KIRMIZIYA donerse fix yanlis yone genisletilmis demektir.
    core_ci = on_blogu(CORE_CI.read_text(encoding="utf-8"))
    vektor("V6 3.BAGLAM core-ci.yml + PR-dalina-push = TEK kosu",
           1, kosu_sayisi(core_ci, "pr-dalina-push", "refs/heads/feature"),
           "(kontrol grubu: bu dosya DEGISTIRILMEDI)")

    # V7 — reusable workflow tetik TASIMAZ; fix'in dogru dosyada oldugunun capasi.
    reusable = on_blogu(REUSABLE.read_text(encoding="utf-8"))
    SENARYOLAR.append((
        "V7 project-guard.yml yalniz workflow_call tasiyor",
        set(reusable) == {"workflow_call"},
        f"cozulen={sorted(reusable)}",
    ))

    # V8 — COZUMLEYICI FP capasi: dal listesi GERCEKTEN okunuyor mu? (Yalniz "branches var mi"
    #      diye baksaydi V4 bedava gecerdi.)
    develop = on_blogu("on:\n  push:\n    branches: [develop]\n  pull_request:\n")
    vektor("V8 cozumleyici: branches[develop] MAIN-push'ta kosmuyor",
           0, kosu_sayisi(develop, "main-push", "refs/heads/main"))

    gecen = sum(1 for _, ok, _ in SENARYOLAR if ok)
    for ad, ok, detay in SENARYOLAR:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}  — {detay}")
    print(f"workflow_tetik_dupe: {gecen}/{len(SENARYOLAR)}")
    return 0 if gecen == len(SENARYOLAR) else 1


if __name__ == "__main__":
    raise SystemExit(main())
