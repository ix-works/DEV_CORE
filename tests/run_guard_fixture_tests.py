#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ENFORCES: C-LEAK-02  (ADR 0019 coverage binding — commit/PR sizinti + gh hedef ekseni)
"""run_guard_fixture_tests.py — pre_tool_guard PAYLOAD fixture korpusu (kalici, agsiz).

NEDEN (2026-08-01 adversarial bug-avi): guard'in kabuk-sozdizimi modeli eksikti; UC
atlatma canli repro edildi (AV-16 `git commit -am`, AV-17 `git commit --file=`,
AV-18 `gh ... --repo X && gh <mutasyon>` zinciri). Ucu de "kod dogru gorunuyor"
denetiminden gecmisti — yakalayan tek sey BOZUK GIRDIYLE KOSUM oldu.

Bu kosucu o vakalari + varyantlarini + YANLIS-POZITIF eksenini kalicilastirir:
  tests/fixtures/pre_tool_guard/blok.json     -> guard exit 2 vermeli (+ dogru imza)
  tests/fixtures/pre_tool_guard/serbest.json  -> guard exit 0 vermeli

ZORLAMALAR (mevcut harness'lerin dersleri):
  * IMZA kontrolu (Z1, guard_conformance'tan): `exit 2` YETMEZ — BASKA bir kural
    ateslemis olabilir ve "korunuyoruz" sanilir.
  * DETERMINIZM: guard sizinti gate'lerinde repo gorunurlugunu CANLI sorar
    (`gh repo view`) ve gercek desen sozlugunu kullanir. Fixture'lar bunlari
    `gorunurluk` (public|private|canli) ve `tarayici` (sentinel|gercek) ile SABITLER
    -> ag yok, kimlik izi yok, her makinede ayni sonuc.
  * SESSIZ ATLAMA YOK: bir vaka kosulamazsa FAIL sayilir (yesil isik degil).

Kosum:  python tests/run_guard_fixture_tests.py
        python tests/run_guard_fixture_tests.py --guard <baska_guard.py>   # MUTASYON testi
Cikis:  0 = korpusun tamami beklendigi gibi, 1 = en az bir sapma.

⚠ YESIL KORPUS TEK BASINA KANIT DEGILDIR. Korpusun gercekten OLCTUGUNU kanitlamak icin
mutasyon testi kosulur: fix ONCESI guard'a karsi (`git show <sha>:scripts/hooks/
pre_tool_guard.py > /tmp/eski.py`) `--guard /tmp/eski.py` -> AV vakalari FAIL vermeli.
Vermezse korpus bos-yesildir (bkz. 2026-07-09: "kosmayan test gate degildir").
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "pre_tool_guard"
GUARD = HERE.parent / "scripts" / "hooks" / "pre_tool_guard.py"

# Yapay "sizinti" isareti — GERCEK bir kimlik izi core'a YAZILAMAZ (public repo);
# bu yuzden tarayici `sentinel` modunda bu isarete bulgu uretir (bilesen-siniri
# dersi: "hangi dize sizintidir" sorusu genericize_common'in isi, bu kosucunun degil).
SENTINEL = "SIZINTI" + "-SENTINEL"

# Guard'i MODUL olarak yukleyip main()'i gercek payload ile kosan surucu.
# Neden dogrudan `python pre_tool_guard.py` degil: gorunurluk sorgusu ve desen
# sozlugu sabitlenemez -> korpus aga/repoya bagimli ve akiskan olurdu.
_SURUCU = r'''
import importlib.util, io, json, sys
guard, payload, gorunurluk, tarayici, sentinel = sys.argv[1:6]
spec = importlib.util.spec_from_file_location("ptg", guard)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
if gorunurluk in ("public", "private"):
    _pub = (gorunurluk == "public")
    m._repo_public_mu = lambda hay: (_pub, "org/public-core" if _pub else "org/private-proj")
elif gorunurluk == "esleme":
    # AV-18b: ZINCIRDE her segmentin hedefi FARKLI gorunurlukte olabilir. Tek-cevap
    # sabitleme bu sinifi ifade EDEMEZ -> hedefe gore cevap (hay icinde "public" gecerse
    # public). Boylece "once PRIVATE okuma, sonra PUBLIC yayin" agsiz kurulabilir.
    m._repo_public_mu = lambda hay: ((True, "org/public-core") if "public" in (hay or "").lower()
                                     else (False, "org/private-proj"))
if tarayici == "sentinel":
    m.sizintilari_bul = lambda metin, desen: (
        [(sentinel, "yapay-kategori")] if sentinel in (metin or "") else [])
_err = io.StringIO()
_gercek_err, _gercek_in = sys.stderr, sys.stdin
sys.stderr, sys.stdin = _err, io.StringIO(payload)
try:
    rc = m.main()
finally:
    sys.stderr, sys.stdin = _gercek_err, _gercek_in
sys.stdout.write("<<SONUC>>" + json.dumps({"rc": rc, "err": _err.getvalue()}))
'''


# AV-21 agaci: fixture iskeleti GECICI bir dizine KOPYALANIR, yerinde kullanilmaz.
# Neden: `_core_hedef_mi` hizli yolu yol-dizgesine bakar ve CI'da repo yolu zaten
# `.../DEV_CORE/...`tir -> repo ICINDEKI her fixture "core" sayilir, "core DEGIL"
# ekseni kurulamazdi (sahte-yesil). Temp kopya bu bulasmayi keser.
_AGAC_TMP = None


def _agac() -> str:
    global _AGAC_TMP
    if _AGAC_TMP is None:
        import shutil
        import tempfile
        hedef = Path(tempfile.mkdtemp(prefix="guardfix_")) / "agac"
        shutil.copytree(FIXTURE / "agac", hedef)
        # `DOTGIT` -> `.git`: git bir depoya `.git` adli yol EKLEYEMEZ, ama "hedefin kendi
        # deposunun koku" sinirini test etmek icin gercek bir `.git` girdisi sart. Iskelette
        # takma adla durur, materyalizasyonda gercek adina donusur.
        for d in hedef.rglob("DOTGIT"):
            d.rename(d.with_name(".git"))
        _AGAC_TMP = str(hedef).replace("\\", "/")
        if "core" in _AGAC_TMP.lower():      # sessiz bulasma kontrolu
            raise SystemExit(f"gecici agac yolunda 'core' geciyor: {_AGAC_TMP}")
    return _AGAC_TMP


def _yerlestir(x):
    """Yer tutuculari coz: <SENTINEL>, <FIXTURE>, <AGAC>, <EPOSTA>."""
    if isinstance(x, str):
        y = (x.replace("<SENTINEL>", SENTINEL)
              .replace("<FIXTURE>", str(FIXTURE).replace("\\", "/")))
        if "<AGAC>" in y:
            y = y.replace("<AGAC>", _agac())
        # Yapisal sizinti deseni (gercek tarayiciyi tetikler). PARCA PARCA kurulur:
        # literal hali JSON'da dursaydi core_precommit bu fixture dosyasini REDDEDERDI
        # (dogru davranis — core PUBLIC). Test, korudugu seyin kurbani olmamali.
        y = y.replace("<EPOSTA>", "birisi" + "@" + "sirket.com.tr")
        return y
    if isinstance(x, dict):
        return {k: _yerlestir(v) for k, v in x.items()}
    if isinstance(x, list):
        # ⚠ Ilk surumde LISTE dalı YOKTU: `MultiEdit.edits[]` icindeki yer tutucular
        # cozulmeden gidiyor, tarayici hicbir sey bulmuyor ve vaka "guard sizdirdi"
        # gibi gorunuyordu. Sahte-KIRMIZI da sahte-yesil kadar tehlikelidir: yanlis
        # yerde kok arattirir (bu kez fixture, gercek bir hata sanildi ve dogrulandi).
        return [_yerlestir(v) for v in x]
    return x


def _cagir(vaka: dict, guard: Path = None) -> tuple:
    if "ham_payload" in vaka:
        # SEKILSIZ payload vakalari (2026-08-01 W2-VH-01): guard'in stdin'ine
        # dict OLMAYAN ya da alan-tipleri yanlis bir govde verilir. Deger `null`/liste/
        # sayi/string olabilecegi icin normal {tool_name, tool_input} kalibi KULLANILAMAZ.
        # `"__HAM__"` ozel degeri: JSON bile olmayan ham metin (bos govde / kesik json).
        h = vaka["ham_payload"]
        payload = h if isinstance(h, str) and vaka.get("ham_metin") else json.dumps(h, ensure_ascii=False)
    else:
        payload = json.dumps({"tool_name": vaka["tool_name"],
                              "tool_input": _yerlestir(vaka["tool_input"])},
                             ensure_ascii=False)
    env, cwd = dict(os.environ), None
    env.pop("IX_GENERICIZE_BLOCKLIST", None)
    if vaka.get("proje_koku"):
        # CI kurulumunun BIREBIR sekli (PR #75): cwd = CORE deposu, --project = KISA goreli
        # kardes yol. `proje_koku_goreli` ile CLAUDE_PROJECT_DIR goreli verilir ->
        # `Path(...).parents` `..` ve `.` ile biter ve `.` core'un ta kendisidir.
        # ⚠ cwd olarak repo koku (HERE.parent) KULLANILMAZ: gecici agac oradan cok uzakta
        # kalir, goreli yol 12+ bilesen olur ve `.` arama DERINLIGININ disinda kalir ->
        # vaka sessizce "gecer" ve hicbir sey olcmez (ilk taslakta tam bu oldu; ara-surum
        # mutasyonunda FAIL VERMEDIGI icin yakalandi). cwd = agactaki core ikizi.
        cwd = _yerlestir("<AGAC>/cekirdek_ikizi")
        kok = _yerlestir(vaka["proje_koku"])
        env["CLAUDE_PROJECT_DIR"] = (os.path.relpath(kok, cwd)
                                     if vaka.get("proje_koku_goreli") else kok)
    else:
        env.pop("CLAUDE_PROJECT_DIR", None)
    # Guard yolu MUTLAK olmali: `proje_koku` vakalari cwd'yi degistirir ve goreli bir
    # `--guard` yolu orada cozulemez -> vaka "KOSULAMADI" verir (sahte-FAIL).
    r = subprocess.run(
        [sys.executable, "-", str(Path(guard or GUARD).resolve()), payload,
         vaka.get("gorunurluk", "canli"), vaka.get("tarayici", "gercek"), SENTINEL],
        input=_SURUCU, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120, env=env, cwd=cwd)
    if "<<SONUC>>" not in (r.stdout or ""):
        return None, (r.stderr or r.stdout or "")[-300:]
    d = json.loads(r.stdout.split("<<SONUC>>", 1)[1])
    return d["rc"], d["err"]


def _imza(err: str) -> str:
    for satir in (err or "").splitlines():
        if "⛔" in satir:
            return satir.strip()[:70]
    return "(imza yok)"


def kosum(sessiz: bool = False, guard: Path = None) -> tuple:
    """(gecen, toplam, hatalar) — run_fixture_tests.py buradan cagirir."""
    hatalar, gecen, toplam = [], 0, 0

    kirli = FIXTURE / "mesajlar" / "kirli.txt"
    if not kirli.is_file() or SENTINEL not in kirli.read_text(encoding="utf-8"):
        # Sessiz kayma korumasi: mesaj dosyasi ile kosucunun sentinel'i AYRISIRSA
        # -F/--file vakalari "temiz" gorunur ve korpus sahte-yesil basar.
        hatalar.append("mesajlar/kirli.txt sentinel'i tasimiyor — korpus GECERSIZ")

    for dosya, beklenen in ((FIXTURE / "blok.json", 2), (FIXTURE / "serbest.json", 0)):
        if not dosya.is_file():
            hatalar.append(f"fixture eksik: {dosya}")
            continue
        for vaka in json.loads(dosya.read_text(encoding="utf-8")):
            toplam += 1
            rc, err = _cagir(vaka, guard)
            if rc is None:
                hatalar.append(f"{vaka['ad']}: KOSULAMADI -> {err}")
                continue
            if rc != beklenen:
                hatalar.append(f"{vaka['ad']}: exit={rc} beklenen={beklenen} "
                               f"[{vaka.get('vaka', '')}] {_imza(err) if rc else ''}")
                continue
            bek_imza = vaka.get("beklenen_imza")
            if bek_imza and bek_imza not in (err or ""):
                hatalar.append(f"{vaka['ad']}: dogru exit ama YANLIS KURAL atesledi — "
                               f"beklenen '{bek_imza}', alinan {_imza(err)}")
                continue
            gecen += 1
            if not sessiz:
                print(f"  [OK]   {vaka['ad']}")
    return gecen, toplam, hatalar


def main() -> int:
    guard = None
    if "--guard" in sys.argv:
        guard = Path(sys.argv[sys.argv.index("--guard") + 1])
        print(f"⚠ MUTASYON MODU — test edilen guard: {guard}")
    print("pre_tool_guard payload fixture korpusu (blok + serbest)")
    gecen, toplam, hatalar = kosum(guard=guard)
    for h in hatalar:
        print(f"  [FAIL] {h}")
    print(f"\n{gecen}/{toplam} vaka beklendigi gibi")
    return 1 if hatalar else 0


if __name__ == "__main__":
    raise SystemExit(main())
