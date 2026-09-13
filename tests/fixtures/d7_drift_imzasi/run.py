#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D7 DRIFT IMZASI — AYNI OLGUYU olcen IKI KAPI, IKI FARKLI TANIM (kayit Q212).

NEDEN BU KORPUS VAR
-------------------
*"Projenin `.claude/settings.json`'u sablondan sapmis mi"* sorusunu bu depoda IKI kapi
soruyordu ve TANIMLARI AYRISMISTI:
  · `scripts/hooks/session_start.py::_drift_kontrol` -> DAVRANISSAL imza
    (`_anlamli_imza`: JSON'da `_comment*` atilir, metinde CRLF/son-bosluk sayilmaz)
  · `scripts/ix_doctor.py::katman4` 4a kolu          -> HAM `sha256(read_bytes())`
Canli olcum (ayni dosya, ayni an): `session_start` **es** (`33522a6e2f10dcc5 ==
33522a6e2f10dcc5`) · `ix_doctor` **`[WARN] settings.json template'ten SAPMIS`**.
Tek fark `_comment*` anahtarlariydi -> davranis TASIMAZLAR.
⇒ `ix_doctor`in HER kosumu bir yanlis-pozitif basiyordu. Yanlis-pozitif ureten uyari
**uyari korlugu** yaratir: gercek drift geldiginde ayni satir gorunur, ayni sekilde
gormezden gelinir. Kapi "var"dir ama bilgi TASIMAZ.

⛔ BU KORPUSUN OLCTUGU SEY TEK BIR CEVAP DEGIL, IKI KAPININ ANLASMASIDIR:
   "sahte WARN gitti" ile "kapi koreldi" AYNI GORUNUR (ikisinde de WARN yok).
   Ayirt edici olcut CIFT YONLUDUR ve ikisi de bu korpusta yasar:
     (a) davranis TASIMAYAN fark (`_comment*` · CRLF · anahtar sirasi) -> SESSIZ
     (b) davranis TASIYAN fark (hook girdisi dusmus · matcher degismis) -> HALA WARN
   (a) olmadan fix olculmemis, (b) olmadan fix asiri-gevsemis olur.

TASARIM GEREKCESI (ICAT DEGIL, EVIN KENDI KARARI):
   `governance/infra-changelog.md` `behavior_manifest` kaydinin *"TASARIM KARARI — taban
   neden NORMALIZE edilmedi"* blogu bu ayrimi ZATEN yaziyor:
     · **D7 = iki BAGIMSIZ URETILMIS artefaktin kiyasi** (proje settings <-> sablon)
       => *"orada normalizasyon ZORUNLUDUR"*.
     · `behavior_manifest.uretilen_hash` = dosyanin KENDI kayitli gecmisiyle kiyasi
       => bayt-bayt kalir (normalize etmek OLCULMEMIS bir gevsetme olurdu).
   Yani `ix_doctor`in ham-sha'si bilincli bir karar DEGIL, **bayat bir kopyaydi**.
   Recete `governance/infra-test-recipes.md` **B3**'te de yaziliydi ("imza 6'lisi":
   yorum->AYNI · CRLF->AYNI · hook-sil->FARKLI · matcher->FARKLI · bozuk-JSON->"?" ·
   sira->AYNI) — ama YALNIZ bir kapiya uygulaniyordu. Bu korpus onu IKI kapiya birden
   uygular ve **fark olmadigini** cakar.

SENARYOLAR
  A-blogu (settings.json = JSON dali; recete B3'un "imza 6'lisi", IKI KAPIDA birden)
    V1  `_comment_x` eklendi          -> ES        ⭐ KOK VAKA (sahte WARN'in kaynagi)
    V2  CRLF farki                    -> ES
    V3  anahtar SIRASI degisti        -> ES
    V4  ⭐ POZITIF KONTROL: bir hook GIRDISI silindi   -> SAPMIS (kapi korelmedi)
    V5  ⭐ POZITIF KONTROL: bir matcher degisti        -> SAPMIS
    V6  bozuk JSON                    -> OLCULEMEDI (TEMIZ sayilmaz)
  B-blogu (hook_shim.py = metin dali)
    V7  yalniz CRLF                   -> ES
    V8  yalniz son-bosluk/newline     -> ES
    V9  ⭐ POZITIF KONTROL: SHIM_SURUM degisti -> SAPMIS
    V10 yerel dosya YOK               -> YOK (iki kapi da soyler)
  C-blogu (asil degismez)
    V11 ⭐ FARK YOK: A+B'nin ON vektorunun ONUNDA da iki kapinin HUKMU AYNI
  D-blogu (KABLOLAMA — gercek giris noktasi; elle fonksiyon cagirmak kablolama kaniti degil)
    V12 ⭐ `python scripts/ix_doctor.py --layer 4` (yorumlu proje) -> D7 satiri PASS,
        ciktida "SAPMIŞ" YOK
    V13 ⭐ ayni CLI, GERCEK sapma -> D7 satiri WARN + "SAPMIŞ" (kapi CLI'da da canli)
    V14 gercek `session_start` alt-sureci (yorumlu proje) -> enjekte edilen baglamda
        D7 uyarisi YOK.  ⚠ IKI TUZAK: (1) cikti JSON'DAN cozulur — ham stdout'ta Turkce
        aramak `ensure_ascii=True` yuzunden sahte-KIRMIZI verir. (2) `_drift_kontrol`
        YALNIZ junction'lar SAGLAMKEN kosar (`main()` else-dali) ⇒ sandbox'ta GERCEK
        junction kurulur; kurulmazsa V14 ERISILEMEZ-YESIL olur (hicbir sey olcmez).
    V15 ayni alt-surec, GERCEK sapma -> baglamda "SAPMIS (D7)" VAR  ⭐ V14'un
        trivial-yesil OLMADIGINI kanitlayan es-vektor
  E-blogu (TEK KAYNAK — sinif sessizce yeniden bolunemez)
    V16 ⭐ `_comment` normalizasyonunu YAPAN dosya `scripts/` altinda TAM 1
    V17 ⭐ iki tuketici de `utils.drift_imzasi`i import eder + `ix_doctor`da sablona
        karsi ham-sha kiyasi KALMADI (Q303: `team_setup.py` beyanli UCUNCU tuketici —
        yalniz pre-commit YOK onarim metni; kume TAM esitlik, V27 literal taramasi onu da kapsar)
  F-blogu (OLCULEMEDI != TEMIZ; ortak modul yoksa)
    V18 ⭐ modul yok -> `ix_doctor` D7 FAIL + "ÖLÇÜLEMEDİ" (PASS DEGIL, SESSIZ DEGIL)
    V19 ⭐ modul yok -> `session_start` sorun listesi BOS DEGIL + "OLCULEMEDI"

  G-blogu (Q245② — UCUNCU CIFT `scripts/git-hooks/pre-commit`, 2026-09-13)
    Neden: `init_project` kopyayi dogumda BIR KEZ yazar, `team_setup` icerige bakmaz ⇒ sablon
    sertlestikce dogmus projelerin kopyasi SESSIZCE geride kaliyordu (canli vaka: bir projede
    core-sizinti kapisi fail-open kaldi, hicbir katman gormedi). Sablonda yer tutucu YOK.
    V20 pre-commit sablonla BAYT-ES -> ES (ix_doctor bunu SATIRLA soyler: "imza EŞ")
    V21 yalniz SATIR SONU ters -> ES  ⭐ ham bayt SAHTE sapma uretmez (canli olcum: sablon
        CRLF calisma kopyasi <-> iki projenin LF calisma kopyasi, imza ayni)
    V22 ⭐ POZITIF: bir `exit 1` -> `exit 0` (fail-open) -> SAPMIS
    V23 pre-commit YOK -> YOK
    V24a ⭐ YOK onarimi: sablonun core-GORELI TAM yolu + "KOPYALA"; `team_setup ile uret` DEGIL
         (team_setup.dosya_tamamla pre-commit URETMEZ)
    V24b SAPMA onarimi: TAM yol (`tpl.name` `git-hooks/`u dusururdu) + manifest ONERILMEZ
         (pre-commit behavior-manifest yuzeyinde degil)
    V25 ⭐ CLI `ix_doctor --layer 4`, yalniz pre-commit sapmis -> [WARN] pre-commit SAPMIŞ
    V26 ⭐ gercek `session_start` alt-sureci (junction'li) -> baglamda pre-commit SAPMIS (D7),
        settings SAPMIS YOK (sapma dogru cifte atfediliyor)
    V27 ⭐ cift listesi TEK KAYNAK (`utils.drift_imzasi.D7_CIFTLERI`): tuketicilerde literal
        `ciftler = [` / sablon yolu YOK
    ⚠ `hukum(..., "precommit")` TUM SATIRLARA GERI DUSMEZ: eski kodda pre-commit satiri hic
      yoktur; geri dusus settings/shim'in ES'ini pre-commit hukmu sanar (V20 trivial-yesil).
    ⭐ ESKI-KOD KARSITLIGI (olculdu 2026-09-13): bu korpus Q245② ONCESI agaca (git archive
      b9697b8) kopyalanip kosuldu -> 18/28 · duser V20·V21·V22·V23·V24a·V24b·V11·V25·V26·V27.

KOSUM (sayilar OLCULDU 2026-09-13, tahmin DEGIL; `run_battery` tek komutu):
    python tests/fixtures/d7_drift_imzasi/run.py                 -> 28/28, exit 0 (~16 sn)
    ... --mutasyon-hamsha        -> 19/28 · duser V1·V2·V3·V6·V7·V8·V21·V11·V12
                                    (ix_doctor ham sha'ya doner = sahte WARN geri gelir;
                                     V21 = pre-commit satir sonu da sahte sapma olur)
    ... --mutasyon-korel         -> 19/28 · duser V4·V5·V9·V22·V24b·V13·V15·V25·V26
                                    (ortak imza SABIT doner = kapi korelir; V6 duSMEZ ve bu
                                     DOGRUDUR: mutasyon `try` govdesindeki donusu degistirir,
                                     bozuk JSON hala `except` dalindan OKUNAMADI doner)
    ... --mutasyon-sessiz        -> 26/28 · duser V6·V11 (okunamayan dosya TEMIZ sayilir)
    ... --mutasyon-modul-sessiz  -> 26/28 · duser V18·V19 (modul yokken D7 hic konusmaz)
    ... --mutasyon-precommit-yok -> 19/28 · duser V20·V21·V22·V23·V24a·V24b·V11·V25·V26
                                    (Q245② oncesi davranis: pre-commit hic olculmez)
    ... --mutasyon-yanlis-onarim -> 27/28 · duser V24a (settings/shim onarimi kopyalanmis)
⛔ HICBIR KIPTE DUSMEYENLER capadir, kusur degil: V10 (dosya YOK dali imzadan ONCE karar
   verir) · V16/V17/V27 (statik tek-kaynak envanteri) · V14 (D7 SESSIZ olmali — sessizligi
   BOZAN bir mutasyon bu kumede yok; V14'un trivial olmadigini V15 kanitlar).
Cikis: 0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (capa bayat / kontrol grubu bozuk)

⛔ MUTASYON GERCEK KAYNAGA YAZILMAZ: her kip icin `scripts/` + `claude/` GECICI bir CORE
   agacina kopyalanir ve mutasyon ORADA uygulanir.
⛔ HER KAPI OLCUMU AYRI BIR ALT-SURECTE kosar. Sebep olculdu (ilk yazim boyle DEGILDI ve
   F-blogu sahte-YESIL verdi): ayni surecte iki farkli agactan modul yuklenince `utils`
   paketi `sys.modules`'ta ONBELLEKLENIR ve ikinci agac BIRINCININ `utils`'ini kullanir
   -> silinmis/mutasyonlu modul "hala duruyor" gibi gorunur, kontrol grubu da anlamsizlasir.
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

SONUC: list[tuple[str, bool, str]] = []
_GECICI: list[str] = []


def kayit(ad: str, ok: bool, not_: str = "") -> None:
    SONUC.append((ad, bool(ok), not_))


def _tmp(onek: str = "d7imza_") -> Path:
    d = Path(tempfile.mkdtemp(prefix=onek))
    _GECICI.append(str(d))
    return d


def _sil(d: Path) -> None:
    """Q319: Windows'ta salt-okur girdi `rmtree(ignore_errors=True)` ile SESSİZCE kalır."""
    def _ac(func, path, _exc):                       # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)                       # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def temizle() -> None:
    for d in _GECICI:
        _sil(d)                                      # Q319: kopyalanan scripts/ salt-okur


def dur(mesaj: str) -> None:
    print(f"[DOGRULANAMADI] {mesaj}")
    temizle()
    sys.exit(2)


# ── MUTASYON CAPALARI ────────────────────────────────────────────────────────
CAPA = {
    "--mutasyon-hamsha": ("scripts/ix_doctor.py",
        "        y, t = anlamli_imza(yerel), anlamli_imza(tpl)\n",
        "        import hashlib as _h  # MUTASYON: ham sha (Q212 oncesi davranis)\n"
        "        y = _h.sha256(yerel.read_bytes()).hexdigest()[:16]\n"
        "        t = _h.sha256(tpl.read_bytes()).hexdigest()[:16]\n"),
    "--mutasyon-korel": ("scripts/utils/drift_imzasi.py",
        "        return hashlib.sha256(norm).hexdigest()[:16]\n",
        "        return \"MUT-SABIT\"  # MUTASYON: imza korlestirildi (her sey es gorunur)\n"),
    "--mutasyon-sessiz": ("scripts/ix_doctor.py",
        "        if OKUNAMADI in (y, t):\n",
        "        if False:  # MUTASYON: okunamayan/bozuk dosya TEMIZ sayiliyor\n"),
    "--mutasyon-modul-sessiz": ("scripts/ix_doctor.py",
        "    if anlamli_imza is None:\n",
        "    if anlamli_imza is None:\n        return []  # MUTASYON: modul yoksa D7 susar\n"),
}
# `--mutasyon-modul-sessiz` IKI tuketiciyi birden soker (V18 ix, V19 session_start):
# tek-noktali mutasyon savunma-derinliginde ISKALAR (bu evde olculmus sinif).
EK_CAPA = {
    "--mutasyon-modul-sessiz": ("scripts/hooks/session_start.py",
        "    if _anlamli_imza is None:\n",
        "    if _anlamli_imza is None:\n        return []  # MUTASYON: modul yoksa D7 susar\n"),
}
CAPA.update({
    # Q245② — pre-commit cifti listeden DUSER (= Q245② ONCESI davranis: kopya hic olculmez)
    "--mutasyon-precommit-yok": ("scripts/utils/drift_imzasi.py",
        "    for rel_y, rel_t, ad, yok, sapma in D7_CIFTLERI:\n",
        "    for rel_y, rel_t, ad, yok, sapma in D7_CIFTLERI[:2]:  # MUTASYON: pre-commit cifti yok\n"),
    # Q245② — naif fix: settings/shim onarim metni pre-commit'e KOPYALANIR (team_setup
    # pre-commit URETMEZ -> operatoru hicbir sey yapmayan komuta yollar)
    "--mutasyon-yanlis-onarim": ("scripts/utils/drift_imzasi.py",
        "     _PRECOMMIT_YOK,\n",
        "     _GENEL_YOK,  # MUTASYON: settings/shim onarimi pre-commit'e kopyalandi\n"),
})
GECERLI_KIP = set(CAPA)


def core_agaci(mut: str | None, modulsuz: bool = False) -> Path:
    """`scripts/` + `claude/` gecici CORE koku (gerekirse mutasyonlu)."""
    kok = _tmp("d7core_")
    shutil.copytree(REPO / "scripts", kok / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(REPO / "claude", kok / "claude",
                    ignore=shutil.ignore_patterns("__pycache__"))
    for t in ("agents", "skills", "commands"):
        (kok / "claude" / t).mkdir(exist_ok=True)
    if mut:
        for rel, eski, yeni in [CAPA[mut]] + ([EK_CAPA[mut]] if mut in EK_CAPA else []):
            hedef = kok / rel
            src = hedef.read_text(encoding="utf-8")
            if src.count(eski) != 1:
                dur(f"mutasyon capasi bayat: {rel} icinde {src.count(eski)} eslesme "
                    f"(1 bekleniyordu) · kip={mut}")
            hedef.write_text(src.replace(eski, yeni, 1), encoding="utf-8", newline="\n")
    if modulsuz:
        (kok / "scripts" / "utils" / "drift_imzasi.py").unlink()
    return kok


# ── ISCI (her olcum AYRI, TEMIZ bir yorumlayicida) ───────────────────────────
ISCI = r'''
import json, os, sys, importlib.util
from pathlib import Path
kok = Path(os.environ["D7_KOK"]); kapi = os.environ["D7_KAPI"]
proj = Path(os.environ["D7_PROJ"])
rel = "scripts/ix_doctor.py" if kapi == "ix" else "scripts/hooks/session_start.py"
spec = importlib.util.spec_from_file_location("_d7_hedef", kok / rel)
m = importlib.util.module_from_spec(spec); sys.modules["_d7_hedef"] = m
spec.loader.exec_module(m)
if kapi == "ix":
    m.PROJ = proj
    cikti = [[str(t), str(s)] for t, s in m._d7_drift()]
else:
    m.PROJ = proj; m.CORE = proj / "core"
    cikti = [["", str(s)] for s in m._drift_kontrol()]
sys.stdout.write("<<<D7JSON>>>" + json.dumps(cikti, ensure_ascii=False))
'''


def olc(kok: Path, kapi: str, p: Path) -> list[tuple[str, str]]:
    env = dict(os.environ)
    env.update({"D7_KOK": str(kok), "D7_KAPI": kapi, "D7_PROJ": str(p),
                "CLAUDE_PROJECT_DIR": str(p), "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    r = subprocess.run([sys.executable, "-"], input=ISCI, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=180)
    ham = r.stdout or ""
    if "<<<D7JSON>>>" not in ham:
        dur(f"isci cokti (kapi={kapi}): rc={r.returncode} stderr={(r.stderr or '')[-400:]!r}")
    return [(a, b) for a, b in json.loads(ham.split("<<<D7JSON>>>", 1)[1])]


# ── PROJE KURULUMU ───────────────────────────────────────────────────────────
def _junction(link: Path, hedef: Path) -> None:
    """Windows'ta junction, POSIX'te DIZIN SYMLINK'i.

    ⚠ 2026-09-09: bu yardimci ilk yazildiginda KOSULSUZ `cmd /c mklink /J` idi ->
    Linux CI'da `FileNotFoundError: [Errno 2] 'cmd'` ile COKUYORDU (iki vektor birden
    dustu: bolum-1 ve bolum-4 `--mutasyon-hamsha`). Windows'ta yesildi, o yuzden
    gozden kacti; kusur URUNDE degil SANDBOX KURULUMUNDAYDI.

    Neden symlink DENK: tuketici `session_start._junction_kontrol` ayrimi
    `os.readlink(p)` ile yapar (bkz. scripts/hooks/session_start.py) -- bu cagri
    Windows junction'inda da POSIX dizin symlink'inde de HEDEFI dondurur, gercek
    klasorde `OSError` atar. Yani sandbox iki platformda da AYNI seyi olcer.
    """
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(hedef)],
                       capture_output=True, text=True, timeout=60)
    else:
        os.symlink(hedef, link, target_is_directory=True)


_PC_TPL = ("claude", "git-hooks", "pre-commit.template")
_SABLON = object()   # `precommit` varsayilani: sablonun BAYT-ES kopyasi


def proje(kok: Path, settings: bytes | None, shim: bytes | None,
          junctionli: bool = False, precommit=_SABLON) -> Path:
    """Izole sahte PROJE koku. Gercek `.claude/` ASLA kullanilmaz.

    `core/claude/` altina UC sablon KONUR: `ix_doctor` sablonu CORE_ROOT'tan,
    `session_start` PROJ/core'dan okur -> ayni baytlar olmadan kiyas ADIL OLMAZ.
    `junctionli=True` ise `core` + `.claude/{agents,skills,commands}` GERCEK junction
    olur; `session_start.main()` D7 kolunu YALNIZ o zaman kosar (else-dali).

    `precommit` (Q245②): varsayilan = sablonun BAYT-ES kopyasi. A/B blogu vektorleri boylece
    pre-commit YOK gurultusu tasimaz (V14'un "D7 uyarisi YOK" hukmu da pre-commit'i kapsar).
    `None` -> dosya yazilmaz (YOK vektoru).
    """
    p = _tmp("d7proj_") / "proje"
    (p / ".claude").mkdir(parents=True)
    (p / "scripts").mkdir()
    if junctionli:
        _junction(p / "core", kok)
        for t in ("agents", "skills", "commands"):
            _junction(p / ".claude" / t, kok / "claude" / t)
    else:
        (p / "core" / "claude" / "git-hooks").mkdir(parents=True)
        for ad in ("settings.template.json", "hook_shim.template.py"):
            shutil.copy2(kok / "claude" / ad, p / "core" / "claude" / ad)
        shutil.copy2(kok.joinpath(*_PC_TPL), p.joinpath("core", *_PC_TPL))
    if settings is not None:
        (p / ".claude" / "settings.json").write_bytes(settings)
    if shim is not None:
        (p / "scripts" / "hook_shim.py").write_bytes(shim)
    if precommit is _SABLON:
        precommit = kok.joinpath(*_PC_TPL).read_bytes()
    if precommit is not None:
        (p / "scripts" / "git-hooks").mkdir(parents=True, exist_ok=True)
        (p / "scripts" / "git-hooks" / "pre-commit").write_bytes(precommit)
    return p


ES, SAPMIS, OLCULEMEDI, YOK = "ES", "SAPMIS", "OLCULEMEDI", "YOK"
# ⚠ Aksan tablosu EKSIK BIRAKILAMAZ: ilk yazimda `Ü` yoktu ve `ÖLÇÜLEMEDİ` hicbir kovaya
# girmedi -> V6 sahte-KIRMIZI verdi (kusur kodda degil SINIFLANDIRICIDAYDI).
_TR = str.maketrans("ŞİÇÖÜĞıİşçöüğ", "SICOUGIISCOUG")


def _sinifla(metin: str) -> str:
    t = metin.translate(_TR).upper().translate(_TR)
    if "OLCULEMEDI" in t or "OKUNAMADI" in t:
        return OLCULEMEDI
    if "SAPMIS" in t:
        return SAPMIS
    if "YOK —" in t or "YOK -" in t:
        return YOK
    return ES


SATIR_YOK = "SATIR-YOK"


def pc_satirlari(kok: Path, kapi: str, p: Path) -> list[str]:
    return [m for _, m in olc(kok, kapi, p) if "pre-commit" in m]


def hukum(kok: Path, kapi: str, p: Path, hedef: str) -> str:
    satirlar = olc(kok, kapi, p)
    if hedef == "precommit":
        # ⛔ "tum satirlara geri dus" YAPILMAZ: Q245② oncesi kodda pre-commit satiri HIC yoktur
        # ve geri dusus settings/shim'in ES'ini pre-commit hukmu sanardi (eski kodda V20
        # trivial-yesil olurdu). `ix_doctor` ES'i de SATIRLA soyler ([PASS] ... imza EŞ);
        # `session_start` temizken SESSIZDIR -> orada satirsizlik ES'tir.
        ilgili = [m for _, m in satirlar if "pre-commit" in m]
        if not ilgili:
            return SATIR_YOK if kapi == "ix" else ES
        return _sinifla(" ".join(ilgili))
    anahtar = "settings.json" if hedef == "settings" else "hook_shim.py"
    ilgili = [m for _, m in satirlar if anahtar in m] or [m for _, m in satirlar]
    return _sinifla(" ".join(ilgili)) if ilgili else ES


# ── VEKTOR TABLOSU ───────────────────────────────────────────────────────────
def vektorler(kok: Path):
    """(ad, hedef, settings_bayt, shim_bayt, beklenen_hukum)"""
    tj = (kok / "claude" / "settings.template.json").read_bytes()
    ts = (kok / "claude" / "hook_shim.template.py").read_bytes()
    veri = json.loads(tj.decode("utf-8"))

    yorumlu = dict(veri)
    yorumlu["_comment_q212"] = "insan notu -- davranis TASIMAZ"
    b_yorumlu = json.dumps(yorumlu, indent=2, ensure_ascii=False).encode("utf-8")

    b_crlf = tj.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    b_sira = json.dumps(dict(reversed(list(veri.items()))), indent=2,
                        ensure_ascii=False).encode("utf-8")

    # POZITIF KONTROL 1: bir PreToolUse hook GIRDISI dusuruldu (davranis TASIR)
    eksik = json.loads(tj.decode("utf-8"))
    dusen = None
    for k, bloklar in eksik.get("hooks", {}).items():
        if isinstance(bloklar, list) and bloklar:
            dusen = (k, bloklar.pop(0))
            break
    if dusen is None:
        dur("sablonda dusurulebilir hook girdisi yok -> V4 POZITIF KONTROLU kurulamiyor")
    b_eksik = json.dumps(eksik, indent=2, ensure_ascii=False).encode("utf-8")

    # POZITIF KONTROL 2: bir matcher degistirildi (davranis TASIR)
    mat = json.loads(tj.decode("utf-8"))
    degisti = False
    for bloklar in mat.get("hooks", {}).values():
        if not isinstance(bloklar, list):
            continue
        for b in bloklar:
            if isinstance(b, dict) and "matcher" in b:
                b["matcher"] = "ZZZ_MUTASYON_MATCHER"
                degisti = True
                break
        if degisti:
            break
    if not degisti:
        dur("sablonda `matcher` tasiyan blok yok -> V5 POZITIF KONTROLU kurulamiyor")
    b_matcher = json.dumps(mat, indent=2, ensure_ascii=False).encode("utf-8")

    b_bozuk = b"{ bu gecerli JSON DEGIL "

    s_crlf = ts.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    s_bosluk = ts + b"\n\n   \n"
    s_gercek = ts.replace(b'SHIM_SURUM = "', b'SHIM_SURUM = "9.9-MUT', 1)
    if s_gercek == ts:
        dur("hook_shim sablonunda `SHIM_SURUM = \"` capasi yok -> V9 kurulamiyor")

    # ── G-blogu (Q245②): scripts/git-hooks/pre-commit ────────────────────────
    tp = kok.joinpath(*_PC_TPL).read_bytes()
    # Satir sonu TERSI (sablon hangi bicimdeyse oteki): Windows calisma kopyasi CRLF, CI/LF
    # blob LF -> ikisi de bu vektorle olculur. Canli olcum (2026-09-13): sablon CRLF (md5
    # ad79..) <-> iki projenin calisma kopyasi LF (md5 3300..) = HAM baytta SAHTE sapma.
    tp_lf = tp.replace(b"\r\n", b"\n")
    tp_ters = tp_lf if tp_lf != tp else tp_lf.replace(b"\n", b"\r\n")
    # POZITIF KONTROL: bir `exit 1` -> `exit 0` = kapinin bir dali FAIL-OPEN olur (Q245'in
    # canli vakasi: kopyada core-sizinti kapisi fail-open kalmisti).
    tp_failopen = tp.replace(b"exit 1", b"exit 0", 1)
    if tp_failopen == tp:
        dur("pre-commit sablonunda `exit 1` capasi yok -> V22 POZITIF KONTROLU kurulamiyor")

    return [
        ("V1 `_comment_x` eklendi -> ES (⭐ sahte WARN'in kaynagi)", "settings", b_yorumlu, ts, tp, ES),
        ("V2 CRLF farki -> ES", "settings", b_crlf, ts, tp, ES),
        ("V3 anahtar SIRASI degisti -> ES", "settings", b_sira, ts, tp, ES),
        ("V4 ⭐ POZITIF: hook GIRDISI silindi -> SAPMIS", "settings", b_eksik, ts, tp, SAPMIS),
        ("V5 ⭐ POZITIF: matcher degisti -> SAPMIS", "settings", b_matcher, ts, tp, SAPMIS),
        ("V6 bozuk JSON -> OLCULEMEDI (TEMIZ sayilmaz)", "settings", b_bozuk, ts, tp, OLCULEMEDI),
        ("V7 hook_shim yalniz CRLF -> ES", "shim", tj, s_crlf, tp, ES),
        ("V8 hook_shim yalniz son-bosluk -> ES", "shim", tj, s_bosluk, tp, ES),
        ("V9 ⭐ POZITIF: SHIM_SURUM degisti -> SAPMIS", "shim", tj, s_gercek, tp, SAPMIS),
        ("V10 hook_shim YOK -> YOK", "shim", tj, None, tp, YOK),
        ("V20 pre-commit sablonla BAYT-ES -> ES (ix_doctor'da SATIRLA)", "precommit", tj, ts, tp, ES),
        ("V21 pre-commit yalniz SATIR SONU ters -> ES (ham bayt sahte sapma uretmez)",
         "precommit", tj, ts, tp_ters, ES),
        ("V22 ⭐ POZITIF: pre-commit'te `exit 1`->`exit 0` (fail-open) -> SAPMIS",
         "precommit", tj, ts, tp_failopen, SAPMIS),
        ("V23 pre-commit YOK -> YOK", "precommit", tj, ts, None, YOK),
    ]


# ── D-BLOGU: gercek giris noktalari ──────────────────────────────────────────
def cli_ix(kok: Path, p: Path) -> tuple[int, str]:
    env = dict(os.environ)
    env.update({"CLAUDE_PROJECT_DIR": str(p), "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8"})
    r = subprocess.run([sys.executable, str(kok / "scripts" / "ix_doctor.py"), "--layer", "4"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def d7_satirlari(cikti: str) -> list[str]:
    return [s.strip() for s in cikti.splitlines()
            if ("settings.json" in s or "hook_shim.py" in s) and s.strip().startswith("[")]


def alt_surec_ss(kok: Path, p: Path) -> str:
    """Gercek `session_start` alt-sureci -> enjekte edilen BAGLAM metni.

    ⚠ Cikti JSON'dan COZULUR: hook `json.dumps` varsayilaniyla basar (`ensure_ascii=True`)
    => Turkce harfler `\\uXXXX` olarak durur; ham stdout'ta aramak sahte-KIRMIZI verir.
    """
    env = dict(os.environ)
    env.update({"CLAUDE_PROJECT_DIR": str(p), "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8"})
    r = subprocess.run([sys.executable, str(kok / "scripts" / "hooks" / "session_start.py")],
                       input=json.dumps({"session_id": "D7-FIXTURE", "source": "startup"}),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=240)
    ham = r.stdout or ""
    try:
        d = json.loads(ham)
        return str(d.get("hookSpecificOutput", {}).get("additionalContext", ""))
    except Exception:
        return f"[COZULEMEDI] rc={r.returncode} {ham[:200]} ERR={(r.stderr or '')[:200]}"


# ── E-BLOGU: statik tek-kaynak envanteri ─────────────────────────────────────
def envanter(kok: Path) -> tuple[list[str], list[str]]:
    """(normalizasyonu YAPAN dosyalar, ortak modulu IMPORT eden dosyalar)"""
    yapan, tuketici = [], []
    for f in sorted((kok / "scripts").rglob("*.py")):
        if "__pycache__" in f.parts:
            continue
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel = f.relative_to(kok).as_posix()
        # Normalizasyonu YAPAN = `_comment` onekini eleyen KOD. Capa `startswith("_comment")`
        # CAGRISIDIR — duz `_comment` gecisi degil: bu evde "markoru TARIF eden metin BEYAN
        # sayilmaz" dersi olculmustur (aciklama yorumu fixture'i kirmizi yakardi).
        if 'startswith("_comment")' in src:
            yapan.append(rel)
        if "utils.drift_imzasi import" in src or "from utils import drift_imzasi" in src:
            tuketici.append(rel)
    return yapan, tuketici


# ── ANA AKIS ─────────────────────────────────────────────────────────────────
def main() -> int:
    kipler = [a for a in sys.argv[1:] if a.startswith("--")]
    for k in kipler:
        if k not in GECERLI_KIP:
            print(f"[KULLANIM] bilinmeyen kip: {k} · gecerli: {sorted(GECERLI_KIP)}")
            return 3
    if len(kipler) > 1:
        print("[KULLANIM] tek seferde TEK mutasyon kipi")
        return 3
    mut = kipler[0] if kipler else None

    kok = core_agaci(mut)
    tablo = vektorler(kok)

    # ⛔ KONTROL GRUBU — ORTAMI da kopyalar. Kiyas MUTASYONLU agacla YAPILMAZ: mutasyonun
    # isi zaten hukmu degistirmektir, o yuzden mutasyonlu agaci "gercek gibi davranmali"
    # diye sinamak aracin KENDI kabul olcutunu bozar (ilk yazimda tam bu oldu:
    # `--mutasyon-korel` KURULAMADI diye exit 2 verdi, oysa mutasyon calisiyordu).
    # Dogru kiyas: GERCEK agac <-> AYRI, MUTASYONSUZ bir gecici agac. Tutmazsa olculen
    # sey mutasyon degil ORTAMDIR (KURULAMADI != KACTI).
    # ⛔ UCLU ESITLIK: `a == b` TEK BASINA YETMEZ — iki agac AYNI sekilde bozuksa kiyas
    # yine tutar ve kontrol grubu sessizce kor olur. Beklenen hukum (`bek0`) da kiyasa girer.
    kok_taban = kok if mut is None else core_agaci(None)
    ad0, hedef0, sj0, sh0, pc0, bek0 = tablo[0]
    a = hukum(REPO, "ix", proje(REPO, sj0, sh0, precommit=pc0), hedef0)
    b = hukum(kok_taban, "ix", proje(kok_taban, sj0, sh0, precommit=pc0), hedef0)
    if not (a == b == bek0):
        dur(f"kontrol grubu bozuk: gercek agac '{a}' · mutasyonsuz gecici agac '{b}' · "
            f"beklenen '{bek0}' ({ad0}) -> olculen sey mutasyon degil ORTAM")

    # ── A+B+G blogu: her vektor, IKI kapida ──────────────────────────────────
    ayni = 0
    for ad, hedef, sj, sh, pc, bek in tablo:
        p = proje(kok, sj, sh, precommit=pc)
        h_ix = hukum(kok, "ix", p, hedef)
        h_ss = hukum(kok, "ss", p, hedef)
        kayit(ad, h_ix == bek and h_ss == bek,
              f"ix_doctor={h_ix} session_start={h_ss} beklenen={bek}")
        if h_ix == h_ss:
            ayni += 1

    # ── G blogu devam: ONARIM METNI (Q245②) ─────────────────────────────────
    # Pre-commit'in onarim yolu settings/shim'inkinden FARKLIDIR (team_setup onu URETMEZ ·
    # manifest yuzeyinde degil). Olculen: mesaj sablonun core-GORELI TAM yolunu tasir
    # (`tpl.name` `git-hooks/`u dusururdu) ve YOK dalinda `team_setup ile uret` DEMEZ.
    tsh = (kok / "claude" / "hook_shim.template.py").read_bytes()
    tjs = (kok / "claude" / "settings.template.json").read_bytes()
    tpc = kok.joinpath(*_PC_TPL).read_bytes()
    tpc_failopen = tpc.replace(b"exit 1", b"exit 0", 1)
    p_yok = proje(kok, tjs, tsh, precommit=None)
    p_sap = proje(kok, tjs, tsh, precommit=tpc_failopen)
    tam_yol = "core/claude/git-hooks/pre-commit.template"
    yok_ix, yok_ss = pc_satirlari(kok, "ix", p_yok), pc_satirlari(kok, "ss", p_yok)
    sap_ix, sap_ss = pc_satirlari(kok, "ix", p_sap), pc_satirlari(kok, "ss", p_sap)
    yok_metin = " ".join(yok_ix + yok_ss)
    kayit("V24a ⭐ pre-commit YOK onarimi: sablon TAM yolu + KOPYALA, `team_setup ile uret` DEGIL "
          "(iki kapida)",
          bool(yok_ix) and bool(yok_ss) and all(tam_yol in s and "KOPYALA" in s
                                                for s in yok_ix + yok_ss)
          and "team_setup.py ile uret" not in yok_metin.split("(core.hooksPath")[0],
          f"ix={yok_ix} ss={yok_ss}")
    sap_metin = " ".join(sap_ix + sap_ss)
    kayit("V24b pre-commit SAPMA onarimi: core-GORELI TAM yol (git-hooks/ dusmez) + manifest "
          "onerilmez (iki kapida)",
          bool(sap_ix) and bool(sap_ss) and all(tam_yol in s for s in sap_ix + sap_ss)
          and "core/claude/pre-commit.template" not in sap_metin
          and "manifest'e" not in sap_metin,
          f"ix={sap_ix} ss={sap_ss}")

    kayit(f"V11 ⭐ FARK YOK: {len(tablo)} vektorun {len(tablo)}'inde iki kapinin hukmu AYNI",
          ayni == len(tablo), f"ayni={ayni}/{len(tablo)}")

    # ── D blogu: gercek giris noktasi (kablolama) ────────────────────────────
    ts = (kok / "claude" / "hook_shim.template.py").read_bytes()
    b_yorumlu = tablo[0][2]
    b_eksik = tablo[3][2]

    p_temiz = proje(kok, b_yorumlu, ts)
    rc, out = cli_ix(kok, p_temiz)
    satirlar = d7_satirlari(out)
    kayit("V12 ⭐ CLI `ix_doctor --layer 4` (yorumlu proje) -> D7 PASS, 'SAPMIŞ' YOK",
          bool(satirlar) and all("SAPMI" not in s for s in satirlar)
          and any("imza EŞ" in s for s in satirlar),
          f"rc={rc} D7_satirlari={satirlar}")

    p_drift = proje(kok, b_eksik, ts)
    rc2, out2 = cli_ix(kok, p_drift)
    satirlar2 = d7_satirlari(out2)
    kayit("V13 ⭐ CLI, GERCEK sapma -> D7 WARN + 'SAPMIŞ' (kapi korelmedi)",
          any("SAPMI" in s for s in satirlar2),
          f"rc={rc2} D7_satirlari={satirlar2}")

    # ⚠ JUNCTION'LI sandbox SART: `main()` D7'yi yalniz junction'lar saglamken kosar.
    pj_temiz = proje(kok, b_yorumlu, ts, junctionli=True)
    pj_drift = proje(kok, b_eksik, ts, junctionli=True)
    ctx = alt_surec_ss(kok, pj_temiz)
    ctx2 = alt_surec_ss(kok, pj_drift)
    kayit("V14 gercek `session_start` alt-sureci (yorumlu) -> baglamda D7 uyarisi YOK",
          "SAPMIS (D7)" not in ctx and "COZULEMEDI" not in ctx
          and "JUNCTION SORUNU" not in ctx,
          f"baglam_kuyruk={ctx[-300:]!r}")
    kayit("V15 ⭐ gercek alt-surec, GERCEK sapma -> baglamda 'SAPMIS (D7)' (V14 trivial degil)",
          "SAPMIS (D7)" in ctx2, f"baglam_kuyruk={ctx2[-300:]!r}")

    # Q245② — ayni iki giris noktasi, YALNIZ pre-commit sapmis (settings/shim BAYT-ES)
    tpc = kok.joinpath(*_PC_TPL).read_bytes()
    tpc_failopen = tpc.replace(b"exit 1", b"exit 0", 1)
    tjs = (kok / "claude" / "settings.template.json").read_bytes()
    p_pc = proje(kok, tjs, ts, precommit=tpc_failopen)
    rc3, out3 = cli_ix(kok, p_pc)
    pc_cli = [s.strip() for s in out3.splitlines()
              if "pre-commit" in s and s.strip().startswith("[")]
    kayit("V25 ⭐ CLI `ix_doctor --layer 4`, pre-commit fail-open sapmasi -> [WARN] pre-commit SAPMIŞ",
          any(s.startswith("[WARN]") and "SAPMI" in s for s in pc_cli),
          f"rc={rc3} pre-commit_satirlari={pc_cli}")
    pj_pc = proje(kok, tjs, ts, junctionli=True, precommit=tpc_failopen)
    ctx3 = alt_surec_ss(kok, pj_pc)
    kayit("V26 ⭐ gercek `session_start` alt-sureci, pre-commit sapmasi -> baglamda "
          "'pre-commit template'ten SAPMIS (D7)'",
          "pre-commit template'ten SAPMIS (D7)" in ctx3
          and "settings.json template'ten SAPMIS" not in ctx3,
          f"baglam_kuyruk={ctx3[-300:]!r}")

    # ── E blogu: TEK KAYNAK ──────────────────────────────────────────────────
    yapan, tuketici = envanter(kok)
    kayit("V16 ⭐ `_comment` normalizasyonunu YAPAN dosya TAM 1 (kopya-tanim yok)",
          yapan == ["scripts/utils/drift_imzasi.py"], f"yapan={yapan}")
    ix_src = (kok / "scripts" / "ix_doctor.py").read_text(encoding="utf-8")
    ham_kiyas = "hashlib.sha256(p.read_bytes())" in ix_src or "def _sha16" in ix_src
    # Q303 (2026-09-13): `team_setup.py` UCUNCU tuketici — yalniz `D7_CIFTLERI`in pre-commit
    # YOK onarim metnini okur (imza hesaplamaz). Kume TAM esitlik olarak kalir: beyansiz yeni
    # bir tuketici hala V17'yi dusurur.
    kayit("V17 ⭐ tuketiciler (iki D7 kapisi + team_setup onarim metni) ortak modulu import "
          "eder + ix_doctor'da ham-sha kiyasi YOK",
          set(tuketici) == {"scripts/ix_doctor.py", "scripts/hooks/session_start.py",
                            "scripts/team_setup.py"}
          and not ham_kiyas,
          f"tuketici={sorted(tuketici)} ham_sha_kaldi={ham_kiyas}")
    # Q245② — CIFT LISTESI de tek kaynakta: tuketicilerde literal `ciftler = [` YOK, sablon
    # yolu (`pre-commit.template`) tuketicide GECMEZ, `D7_CIFTLERI` yalniz ortak modulde.
    ss_src = (kok / "scripts" / "hooks" / "session_start.py").read_text(encoding="utf-8")
    ts_src = (kok / "scripts" / "team_setup.py").read_text(encoding="utf-8")
    ortak_src = (kok / "scripts" / "utils" / "drift_imzasi.py").read_text(encoding="utf-8")
    literal = [ad for ad, s in (("ix_doctor", ix_src), ("session_start", ss_src),
                                ("team_setup", ts_src))
               if "ciftler = [" in s or "pre-commit.template" in s]
    kayit("V27 ⭐ D7 cift listesi TEK KAYNAK: tuketicilerde literal liste/sablon yolu YOK, "
          "`D7_CIFTLERI` ortak modulde pre-commit'i tasir",
          not literal and "D7_CIFTLERI = (" in ortak_src
          and '"claude/git-hooks/pre-commit.template"' in ortak_src,
          f"literal_kalan={literal}")

    # ── F blogu: OLCULEMEDI != TEMIZ ─────────────────────────────────────────
    kok_ms = core_agaci(mut, modulsuz=True)
    p_ms = proje(kok_ms, (kok / "claude" / "settings.template.json").read_bytes(), ts)
    ms_ix = olc(kok_ms, "ix", p_ms)   # BAYT-ES proje: modul olsaydi hukum 'ES' olurdu
    ms_metin = " ".join(m for _, m in ms_ix)
    kayit("V18 ⭐ ortak modul YOK -> ix_doctor D7 FAIL + 'ÖLÇÜLEMEDİ' (PASS/SESSIZ DEGIL)",
          bool(ms_ix) and any(t == "FAIL" for t, _ in ms_ix) and "ÖLÇÜLEMEDİ" in ms_metin,
          f"satir_sayisi={len(ms_ix)} metin={ms_metin[:220]!r}")
    ms_ss = [m for _, m in olc(kok_ms, "ss", p_ms)]
    kayit("V19 ⭐ ortak modul YOK -> session_start sorun BOS DEGIL + 'OLCULEMEDI'",
          bool(ms_ss) and any("OLCULEMEDI" in s for s in ms_ss), f"sorunlar={ms_ss}")

    # ── RAPOR ────────────────────────────────────────────────────────────────
    print("=" * 78)
    print(f"D7 DRIFT IMZASI (Q212) — kip: {mut or 'taban'}")
    print("=" * 78)
    dusen = 0
    for ad, ok, not_ in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + (f"   -> {not_}" if not_ and not ok else ""))
        if not ok:
            dusen += 1
    print(f"TOPLAM: {len(SONUC) - dusen} PASS / {dusen} FAIL")
    temizle()
    return 1 if dusen else 0


if __name__ == "__main__":
    raise SystemExit(main())
