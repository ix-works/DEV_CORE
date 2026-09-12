#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_all_ozet_kipi — Q203: `run_all_validators --ozet` RAPORLAMAYI kisar, BULGUYU YUTMAZ.

KUSUR (olculdu 2026-09-13, tuketici proje, `--quick`, rc=0): pre-commit her commit'te
stdout 20.472 + stderr 3.697 = 24.169 karakter DEGISMEYEN warn-first rapor basiyordu;
kaydin ozellikle andigi `[ÖLÇÜLEMEDİ]` satiri (stderr) o gurultunun icinde kayboluyordu.
Fix: `--ozet` kipi (pre-commit sablonu kullanir) — ayni koşumda 4.299 karakter.

⛔ OZET KIPININ TIPIK HATASI "ozet gosterdi, bulguyu yuttu"dur (Q105/Q197/Q199 ailesi).
Bu korpusun omurgasi o yuzden NEGATIF testlerdir: bulgu varken ozet kipinde gorunuyor mu.

IZOLE KUM: gercek `run_all_validators.py` kaynagi (ya da mutanti) kuma kopyalanir;
VALIDATORS listesindeki her script `[OK]` basan bir STUB olur (liste kaynagin AST'inden
TURETILIR — elle kopya yok), senaryo davranisi `validators-local/` stub'larindadir.
Gercek agaca HICBIR sey yazilmaz.

  S1a AYRINTILI FORMAT PIN: bayraksiz stdout BEKLENEN metinle BAYT-ES, stderr de
  S1b `--ayrintili` == bayraksiz (stdout+stderr+rc)
  S1c FAIL'li ayrintili kosum da BAYT-ES (FAIL satiri + stderr FAIL mesaji)
  S2  ⭐ NEGATIF: `--ozet` + FAIL veren kapi -> TAM detay (12 govde satiri + stderr) + rc 1
  S3  ozet GIZLER + SAYAC: rc=0 kapinin govdesi yok, satirinda bulgu-etiketi/gizlenen
  S4a ⭐ GORUNUR-ZORUNLU (stdout): KAPSAM SIFIR + devam satirlari · [SKIP] · ascii-kucuk
      `dogrulanamadi` · measured=false -> basilir; komsu govde satiri basilmaz
  S4b ⭐ GORUNUR-ZORUNLU (stderr): `[ÖLÇÜLEMEDİ …]` + kucuk-harf Turkce `ölçülemedi`
  S5  EXIT PARITESI: ozet rc == ayrintili rc (temiz · FAIL · --strict · dosya-yok);
      --strict iletimi ozet kipinde de calisir ve FAIL detayi gorunur
  S6  validator DOSYASI YOK -> ozet kipinde `[FAIL] validator dosyası YOK` + rc 1
      + Ozet TABLOSUNDA `KOŞTURULAMADI` satiri, ozet VE bayraksiz kipte (Q296)
  S7  KAPSAM BEYANI sifir-bulgu aninda da basilir; son satir degismez
  S8a ⭐ 3. BAGLAM — GERCEK GIRIS NOKTASI: pre-commit SABLONU gercek `sh` + gercek git
      deposunda kosar -> rc 0 + "[pre-commit] OK" + ozet beyani, warn govdesi YOK
  S8b ayni sablon + FAIL veren kapi -> rc 1 + FAIL govdesi TAM + "validator ihlali"
  S9  3. BAGLAM-b CORE modu (project.yaml yok): rc paritesi + `[SKIP] … (core-modu)` satiri

MUTASYONLAR (her biri korpusu KIRMIZI yapmali; kaynak BELLEKTE bozulur, kuma yazilir):
  --mutasyon-fail-gizli        ozet, rc!=0 kapiya da uygulanir            -> S2
  --mutasyon-gorunur-yok       gorunur-zorunlu suzgeci hep False           -> S4a/S4b
  --mutasyon-stderr-gorunur-yok  stderr suzulmez (yalniz stdout)           -> S4b
  --mutasyon-exit              ozet kipinde FAIL'e ragmen exit 0          -> S2/S5
  --mutasyon-ayrintili-sizar   bayraksiz kosum da suzulur                 -> S1a
  --mutasyon-beyan-yok         kapsam beyani basilmaz                      -> S7
  --mutasyon-sayac-yok         kapi satirinda sayac yok                    -> S3
  --mutasyon-devam-yok         gorunur satirin devam satirlari (kok izi) yok -> S4a
  --mutasyon-turkce-yok        Turkce/buyuk-kucuk normalizasyonu yok       -> S4b
  --mutasyon-sablon-bayraksiz  pre-commit sablonu `--ozet` gecmez          -> S8a
  --mutasyon-tablo-eksik-yok   dosyasi olmayan validator tabloya girmez (Q296 oncesi) -> S6

Olcum kaldiraci (CI'da KULLANILMAZ): `Q203_RAV_KAYNAK` / `Q203_SABLON_KAYNAK` env'leri
korpusu baska bir kaynak dosyaya (ör. fix oncesi taban) karsi kosturur — "eski kod
KIRMIZI" iddiasini OLCMEK icin.

Kosum: python tests/fixtures/run_all_ozet_kipi/run.py [--mutasyon-…]
Cikis: 0 hepsi gecti | 1 dusen var | 2 alet gecersiz (yama tutmadi / sh yok / kip red)
"""
from __future__ import annotations

import ast
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
CORE = HERE.parents[2]
RAV = Path(os.environ.get("Q203_RAV_KAYNAK")
           or CORE / "scripts" / "validators" / "run_all_validators.py")
SABLON = Path(os.environ.get("Q203_SABLON_KAYNAK")
              or CORE / "claude" / "git-hooks" / "pre-commit.template")
PROJECT_CONFIG = CORE / "scripts" / "utils" / "project_config.py"
SH = shutil.which("sh") or shutil.which("bash")

PROFIL = "s4_private"
STRICT_SCRIPT = "check_console_utf8.py"   # --strict gelirse FAIL veren core stub'i
EKSIK_SCRIPT = "check_bdef_backtick.py"   # S6'da dosyasi silinen core stub'i
OZET_ETIKETI = "[özet: yalnız görünür-zorunlu satırlar]"


class YamaTutmadi(Exception):
    """Capa kaynakta yok -> ALET gecersiz (exit 2, sayi basilmaz)."""


# ── STUB DAVRANISLARI: (stdout satirlari, stderr satirlari, rc) ───────────────
STUB_CORE = (["[OK] stub temiz"], [], 0)
STUB_A = (["[OK] a_temiz GOVDE-A-7731 ihlal yok"], [], 0)
STUB_B = ([f"[WARN] GOVDE-B-{i} dosya.x:{i} uyari metni" for i in range(5)]
          + ["Ozet: 5 WARN (warn-first) GOVDE-B-OZET"],
          [f"[BULGU] STDERR-B-{i} miktar alani ham" for i in range(2)], 0)
STUB_C = ([
    "[OK] c temiz GOVDE-C-GIZLI",
    "⚠ KAPSAM SIFIR: 0 .x tarandı — ihlal yok DEĞİL",
    "   Kapsam doğru mu? KUM-KOK-IZI",
    "   (Sıfır kapsam meşru olabilir) DEVAM-IZI-2",
    "GOVDE-C-SONRA komsu satir gizli kalmali",
    "  [SKIP] alt-tarama SKIP-IZI-C argumansiz",
    "durum: dogrulanamadi ASCII-KUCUK-IZI",
    "sonda measured=false OLCUM-IZI",
], [
    "  [ÖLÇÜLEMEDİ · UYARI, rc'yi ETKİLEMEZ] hook-x: STDERR-OLCULEMEDI-IZI",
    "kısmen ölçülemedi KUCUK-TURKCE-IZI",
    "GOVDE-C-STDERR-GIZLI",
], 0)
STUB_D = (["[FAIL] GOVDE-D-0 ihlal"] + [f"   detay GOVDE-D-{i}" for i in range(1, 12)],
          ["STDERR-D-DETAY"], 1)

YERELLER_T = {"a_temiz.py": STUB_A, "b_uyari.py": STUB_B, "c_olculemedi.py": STUB_C}
YERELLER_F = {**YERELLER_T, "d_fail.py": STUB_D}
YERELLER_Z = {"a_temiz.py": STUB_A}


def _stub_kodu(stub, strict: bool = False) -> str:
    out, err, rc = stub
    kod = ("import sys\n"
           "for _s in (sys.stdout, sys.stderr):\n"
           "    _s.reconfigure(encoding='utf-8')\n"
           f"OUT = {out!r}\nERR = {err!r}\nRC = {rc!r}\n")
    if strict:
        kod += ("if '--strict' in sys.argv:\n"
                "    OUT, ERR, RC = ['[FAIL] STRICT-DETAY-E strict kipte ihlal'], [], 1\n")
    kod += ("for s in OUT:\n    print(s)\nsys.stdout.flush()\n"
            "for s in ERR:\n    print(s, file=sys.stderr)\n"
            "sys.exit(RC)\n")
    return kod


def _satirlar(lst) -> str:
    return "".join(s + "\n" for s in lst)


# ── KUM ───────────────────────────────────────────────────────────────────────
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


def validators_listesi(kaynak: str) -> list:
    for d in ast.parse(kaynak).body:
        if isinstance(d, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "VALIDATORS" for t in d.targets):
            return ast.literal_eval(d.value)
    raise YamaTutmadi("VALIDATORS listesi kaynakta bulunamadi")


def core_kur(core: Path, rav_kaynak: str, vlist: list, eksik: str | None = None) -> Path:
    vd = core / "scripts" / "validators"
    vd.mkdir(parents=True, exist_ok=True)
    ud = core / "scripts" / "utils"
    ud.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_CONFIG, ud / "project_config.py")
    rav = vd / "run_all_validators.py"
    rav.write_text(rav_kaynak, encoding="utf-8", newline="\n")
    for _label, script, *_ in vlist:
        if script == eksik:
            continue
        (vd / script).write_text(_stub_kodu(STUB_CORE, strict=(script == STRICT_SCRIPT)),
                                 encoding="utf-8")
    return rav


def proje_kur(proje: Path, yereller: dict | None) -> Path:
    proje.mkdir(parents=True, exist_ok=True)
    if yereller is None:          # CORE modu: project.yaml YOK
        return proje
    (proje / "project.yaml").write_text(
        f"sap_profile: {PROFIL}\nsource_root: SOURCE_CODES\n", encoding="utf-8")
    ld = proje / "scripts" / "validators-local"
    ld.mkdir(parents=True, exist_ok=True)
    for ad, stub in yereller.items():
        (ld / ad).write_text(_stub_kodu(stub), encoding="utf-8")
    return proje


def _env(proje: Path | None) -> dict:
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDE_PROJECT_DIR" and not k.startswith("IX_")}
    env["PYTHONIOENCODING"] = "utf-8"
    if proje is not None:
        env["CLAUDE_PROJECT_DIR"] = str(proje)
    return env


def kos(rav: Path, proje: Path, *args: str) -> tuple[int, str, str]:
    r = subprocess.run([sys.executable, str(rav), *args], cwd=str(proje), env=_env(proje),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=300)
    return r.returncode, r.stdout or "", r.stderr or ""


# ── BEKLENEN AYRINTILI METIN (format PIN'i — spesifikasyondan kurulur) ────────
def beklenen_ayrintili(vlist: list, yereller: dict) -> tuple[str, str]:
    out = (f"run_all_validators — mod: PROJE · profil: {PROFIL} · source_root: SOURCE_CODES\n")
    err = ""
    ran, failed, skipped = [], [], []
    for label, script, _extra, _scope, profiller in vlist:
        if "freshness" in script:
            skipped.append((label, "quick"))
            continue
        if profiller and PROFIL not in profiller:
            skipped.append((label, f"profil={PROFIL}"))
            continue
        out += f"\n--- {label} --- ({script})\n" + _satirlar(STUB_CORE[0])
        ran.append(label)
    for ad in sorted(yereller):
        s_out, s_err, rc = yereller[ad]
        label = f"LOCAL: {Path(ad).stem}"
        out += f"\n--- {label} --- ({ad})\n" + _satirlar(s_out)
        err += _satirlar(s_err)
        ran.append(label)
        if rc:
            failed.append(label)
    out += "\n" + "=" * 60 + "\nÖzet:\n"
    for label in ran:
        out += (f"  [{'FAIL' if label in failed else 'OK'}]   {label}"
                .replace("[OK]  ", "[OK]") + "\n")
    for label, neden in skipped:
        out += f"  [SKIP] {label} ({neden})\n"
    if failed:
        err += f"\n{len(failed)} validator FAIL — yukarıdaki çıktıları incele.\n"
    else:
        out += "\nTüm validator'lar OK\n"
    return out, err


# ── PRE-COMMIT SABLONU: gercek sh + gercek git deposu ─────────────────────────
def _git(depo: Path, *a):
    return subprocess.run(["git", *a], cwd=str(depo), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def sablon_kos(kum: Path, sablon_metni: str, rav_kaynak: str, vlist: list,
               yereller: dict) -> tuple[int, str]:
    depo = kum
    depo.mkdir(parents=True, exist_ok=True)
    _git(depo, "init", "-q")
    _git(depo, "config", "user.email", "t@t")
    _git(depo, "config", "user.name", "t")
    (depo / "dosya.txt").write_text("x\n", encoding="utf-8")
    _git(depo, "add", "dosya.txt")
    core_kur(depo / "core", rav_kaynak, vlist)
    proje_kur(depo, yereller)
    hook = depo / "pre-commit.sh"
    hook.write_text(sablon_metni, encoding="utf-8", newline="\n")
    env = _env(None)
    r = subprocess.run([SH, str(hook)], cwd=str(depo), env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ── SENARYOLAR ────────────────────────────────────────────────────────────────
def senaryolar(rav_kaynak: str, sablon_metni: str) -> list[tuple[str, bool, str]]:
    out: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, detay=""):
        out.append((ad, bool(kosul), detay))

    vlist = validators_listesi(rav_kaynak)
    etiket = {script: label for label, script, *_ in vlist}
    kum = Path(tempfile.mkdtemp(prefix="q203_"))
    try:
        rav1 = core_kur(kum / "core1", rav_kaynak, vlist)
        rav2 = core_kur(kum / "core2", rav_kaynak, vlist, eksik=EKSIK_SCRIPT)
        pT = proje_kur(kum / "pT", YERELLER_T)
        pF = proje_kur(kum / "pF", YERELLER_F)
        pZ = proje_kur(kum / "pZ", YERELLER_Z)
        pBos = proje_kur(kum / "pBos", None)

        tD = kos(rav1, pT, "--quick")
        tA = kos(rav1, pT, "--quick", "--ayrintili")
        tO = kos(rav1, pT, "--quick", "--ozet")
        fD = kos(rav1, pF, "--quick")
        fO = kos(rav1, pF, "--quick", "--ozet")
        sD = kos(rav1, pT, "--quick", "--strict")
        sO = kos(rav1, pT, "--quick", "--strict", "--ozet")
        eD = kos(rav2, pT, "--quick")
        eO = kos(rav2, pT, "--quick", "--ozet")
        zO = kos(rav1, pZ, "--quick", "--ozet")
        cD = kos(rav1, pBos, "--quick")
        cO = kos(rav1, pBos, "--quick", "--ozet")

        # S1a / S1b / S1c ─────────────────────────────────────────────────────
        b_out, b_err = beklenen_ayrintili(vlist, YERELLER_T)
        ekle("S1a AYRINTILI FORMAT PIN: bayraksiz stdout+stderr beklenen metinle BAYT-ES",
             tD[0] == 0 and tD[1] == b_out and tD[2] == b_err,
             f"rc={tD[0]} out_es={tD[1] == b_out} err_es={tD[2] == b_err} "
             f"out_len={len(tD[1])}/{len(b_out)}")
        ekle("S1b --ayrintili bayraksiz kosumla AYNI (stdout+stderr+rc)", tA == tD,
             f"rc={tA[0]}/{tD[0]}")
        f_out, f_err = beklenen_ayrintili(vlist, YERELLER_F)
        ekle("S1c FAIL'li ayrintili kosum da BAYT-ES (FAIL satiri + stderr FAIL mesaji)",
             fD[0] == 1 and fD[1] == f_out and fD[2] == f_err,
             f"rc={fD[0]} out_es={fD[1] == f_out} err_es={fD[2] == f_err}")

        # S2 ⭐ NEGATIF ────────────────────────────────────────────────────────
        eksik_govde = [s for s in STUB_D[0] if s not in fO[1]]
        ekle("S2 NEGATIF: --ozet + FAIL veren kapi -> TAM detay (stdout+stderr) + rc 1",
             fO[0] == 1 and not eksik_govde and "STDERR-D-DETAY" in fO[2]
             and "\n--- LOCAL: d_fail --- (d_fail.py)\n" in fO[1]
             and "  [FAIL]   LOCAL: d_fail\n" in fO[1],
             f"rc={fO[0]} eksik_govde={eksik_govde[:3]} stderr_detay={'STDERR-D-DETAY' in fO[2]}")

        # S3 ─────────────────────────────────────────────────────────────────
        gizli_sizan = [m for m in ("GOVDE-A-", "GOVDE-B-") if m in tO[1]] + \
                      [m for m in ("STDERR-B-",) if m in tO[2]]
        ekle("S3 OZET GIZLER + SAYAC: rc=0 govdesi yok, kapi satirinda bulgu-etiketi/gizlenen",
             tO[0] == 0 and not gizli_sizan
             and "  [OK] LOCAL: b_uyari  · bulgu-etiketi=7 · gizlenen=8 satır\n" in tO[1]
             and "  [OK] LOCAL: a_temiz  · bulgu-etiketi=0 · gizlenen=1 satır\n" in tO[1]
             and len(tO[1]) + len(tO[2]) < len(tD[1]) + len(tD[2]),
             f"rc={tO[0]} sizan={gizli_sizan} boyut ozet={len(tO[1]) + len(tO[2])} "
             f"ayrintili={len(tD[1]) + len(tD[2])}")

        # S4a / S4b ⭐ ────────────────────────────────────────────────────────
        gerekli_out = ["⚠ KAPSAM SIFIR: 0 .x tarandı", "KUM-KOK-IZI", "DEVAM-IZI-2",
                       "SKIP-IZI-C", "ASCII-KUCUK-IZI", "OLCUM-IZI"]
        eksik_out = [m for m in gerekli_out if m not in tO[1]]
        sizan_c = [m for m in ("GOVDE-C-GIZLI", "GOVDE-C-SONRA") if m in tO[1]]
        ekle("S4a GORUNUR-ZORUNLU stdout: KAPSAM SIFIR+devam · [SKIP] · ascii-kucuk · "
             "measured=false basilir, komsu govde basilmaz",
             not eksik_out and not sizan_c
             and f"--- LOCAL: c_olculemedi --- (c_olculemedi.py) {OZET_ETIKETI}\n" in tO[1]
             and "  [OK] LOCAL: c_olculemedi  · bulgu-etiketi=0 · gizlenen=3 satır\n" in tO[1],
             f"eksik={eksik_out} sizan={sizan_c}")
        eksik_err = [m for m in ("STDERR-OLCULEMEDI-IZI", "KUCUK-TURKCE-IZI") if m not in tO[2]]
        ekle("S4b GORUNUR-ZORUNLU stderr: [ÖLÇÜLEMEDİ] + kucuk-harf Turkce basilir, govde basilmaz",
             not eksik_err and "GOVDE-C-STDERR-GIZLI" not in tO[2],
             f"eksik={eksik_err} stderr={tO[2][-240:]!r}")

        # S5 ─────────────────────────────────────────────────────────────────
        strict_label = etiket.get(STRICT_SCRIPT, "?")
        parite = {"temiz": (tD[0], tO[0], 0), "fail": (fD[0], fO[0], 1),
                  "strict": (sD[0], sO[0], 1), "dosya-yok": (eD[0], eO[0], 1)}
        ekle("S5 EXIT PARITESI (temiz/fail/strict/dosya-yok) + --strict FAIL detayi ozette gorunur",
             all(a == b == c for a, b, c in parite.values())
             and "STRICT-DETAY-E" in sO[1]
             and f"\n--- {strict_label} --- ({STRICT_SCRIPT})\n" in sO[1],
             f"parite={parite} strict_detay={'STRICT-DETAY-E' in sO[1]}")

        # S6 ─────────────────────────────────────────────────────────────────
        eksik_label = etiket.get(EKSIK_SCRIPT, "?")
        # Q296 (2026-09-13): dosyasi olmayan validator artik Ozet TABLOSUNDA da gorunur.
        #   Onceden yalniz govdedeki [FAIL] satiri + stderr sayaci vardi, tabloda satir YOKTU
        #   (olculdu). Tablo satiri kanonik sirada, iki kipte de ayni metinle beklenir.
        tablo_satiri = (f"  [FAIL]   {eksik_label}  · KOŞTURULAMADI: validator dosyası YOK "
                        f"({EKSIK_SCRIPT})\n")
        tablo_eO = eO[1].split("\nÖzet:\n", 1)[-1] if "\nÖzet:\n" in eO[1] else ""
        tablo_eD = eD[1].split("\nÖzet:\n", 1)[-1] if "\nÖzet:\n" in eD[1] else ""
        ekle("S6 validator dosyasi YOK -> govdede [FAIL] satiri + Ozet TABLOSUNDA KOSTURULAMADI "
             "satiri (ozet + bayraksiz) + stderr FAIL sayaci + rc 1",
             eO[0] == 1
             and f"\n--- {eksik_label} --- ({EKSIK_SCRIPT})\n[FAIL] validator dosyası YOK\n" in eO[1]
             and "\n1 validator FAIL" in eO[2]
             and tablo_satiri in tablo_eO and tablo_satiri in tablo_eD,
             f"rc={eO[0]} tablo_ozet={tablo_satiri in tablo_eO} "
             f"tablo_bayraksiz={tablo_satiri in tablo_eD} out={eO[1][-200:]!r} "
             f"err={eO[2][-120:]!r}")

        # S7 ─────────────────────────────────────────────────────────────────
        kosan = sum(1 for _l, s, _e, _sc, p in vlist
                    if "freshness" not in s and not (p and PROFIL not in p)) + len(YERELLER_Z)
        son = [s for s in zO[1].splitlines() if s.strip()][-1:] or [""]
        ekle("S7 KAPSAM BEYANI sifir-bulgu aninda da basilir; son satir 'Tüm validator'lar OK'",
             zO[0] == 0
             and f"ÖZET KİPİ (--ozet): rc=0 veren {kosan} kapının gövdesi gizlendi" in zO[1]
             and "  Tam çıktı: aynı komutu --ozet OLMADAN koş.\n" in zO[1]
             and son[0] == "Tüm validator'lar OK",
             f"rc={zO[0]} son={son[0]!r} beklenen_kapi={kosan}")

        # S8a / S8b ⭐ 3. BAGLAM ───────────────────────────────────────────────
        rc, o = sablon_kos(kum / "depoT", sablon_metni, rav_kaynak, vlist, {"b_uyari.py": STUB_B})
        ekle("S8a 3.BAGLAM pre-commit SABLONU (gercek sh+git): rc 0 + OK + ozet beyani, "
             "warn govdesi YOK",
             rc == 0 and "[pre-commit] OK" in o and "ÖZET KİPİ (--ozet)" in o
             and "GOVDE-B-" not in o and "STDERR-B-" not in o,
             f"rc={rc} cikti={o[-300:]!r}")
        rc, o = sablon_kos(kum / "depoF", sablon_metni, rav_kaynak, vlist,
                           {"b_uyari.py": STUB_B, "d_fail.py": STUB_D})
        ekle("S8b ayni sablon + FAIL veren kapi -> rc 1 + FAIL govdesi TAM + 'validator ihlali'",
             rc == 1 and all(s in o for s in STUB_D[0]) and "STDERR-D-DETAY" in o
             and "validator ihlali" in o and "[pre-commit] OK" not in o,
             f"rc={rc} cikti={o[-300:]!r}")

        # S9 3. BAGLAM-b ─────────────────────────────────────────────────────
        ekle("S9 CORE modu: rc paritesi + [SKIP] (core-modu) satiri + beyan; yerel kesif yok",
             cD[0] == cO[0] == 0 and "mod: CORE" in cO[1]
             and "  [SKIP] Core-sızıntı kilidi (R1/2.7) (core-modu)\n" in cO[1]
             and "ÖZET KİPİ (--ozet)" in cO[1] and "GOVDE-" not in cO[1],
             f"rc={cD[0]}/{cO[0]}")
    finally:
        _sil(kum)
    return out


# ── MUTASYONLAR (kaynak BELLEKTE bozulur) ─────────────────────────────────────
def _yama(metin: str, eski: str, yeni: str, ad: str) -> str:
    if metin.count(eski) != 1:
        raise YamaTutmadi(f"{ad}: capa {metin.count(eski)} kez bulundu (1 bekleniyordu)")
    return metin.replace(eski, yeni, 1)


_OZET_KOSULU = "            if args.ozet and r.returncode == 0:\n"


def _m_rav(eski: str, yeni: str, ad: str):
    return lambda rav, sab: (_yama(rav, eski, yeni, ad), sab)


KIPLER = {
    "--mutasyon-fail-gizli": _m_rav(_OZET_KOSULU, "            if args.ozet:\n", "fail-gizli"),
    "--mutasyon-gorunur-yok": _m_rav(
        "    return any(t in n for t in _GORUNUR_ZORUNLU)\n", "    return False\n",
        "gorunur-yok"),
    "--mutasyon-stderr-gorunur-yok": _m_rav(
        "                g_err, d_err, e_err = _ozet_suz(r.stderr)\n",
        "                g_err, d_err, e_err = [], len((r.stderr or '').splitlines()), 0\n",
        "stderr-gorunur-yok"),
    "--mutasyon-exit": _m_rav("\n    if failed:\n", "\n    if failed and not args.ozet:\n",
                              "exit"),
    "--mutasyon-ayrintili-sizar": _m_rav(_OZET_KOSULU, "            if r.returncode == 0:\n",
                                         "ayrintili-sizar"),
    "--mutasyon-beyan-yok": _m_rav("    if args.ozet:\n        # KAPSAM BEYANI",
                                   "    if False:\n        # KAPSAM BEYANI", "beyan-yok"),
    "--mutasyon-sayac-yok": _m_rav(
        '            satir += f"  · bulgu-etiketi={etiket} · gizlenen={gizli} satır"\n', "",
        "sayac-yok"),
    "--mutasyon-devam-yok": _m_rav("_DEVAM_TAVANI = 6", "_DEVAM_TAVANI = 0", "devam-yok"),
    "--mutasyon-turkce-yok": _m_rav(
        '    s = s.replace("İ", "I").replace("ı", "i")\n'
        '    s = unicodedata.normalize("NFKD", s)\n'
        '    return "".join(c for c in s if not unicodedata.combining(c)).upper()\n',
        "    return s.upper()\n", "turkce-yok"),
    "--mutasyon-tablo-eksik-yok": _m_rav(
        "failed.append(label); ran.append(label); kosturulamadi[label] = ad; continue\n",
        "failed.append(label); continue\n", "tablo-eksik-yok"),
    "--mutasyon-sablon-bayraksiz": lambda rav, sab: (rav, _yama(
        sab, "run_all_validators.py --quick --ozet; then", "run_all_validators.py --quick; then",
        "sablon-bayraksiz")),
}


def main(argv: list[str]) -> int:
    print("=" * 78)
    print("run_all_ozet_kipi — --ozet raporlamayi kisar, bulguyu YUTMAZ (Q203)")
    print("=" * 78)
    kipler = [a for a in argv if a.startswith("--mutasyon")]
    if len(kipler) > 1 or (kipler and kipler[0] not in KIPLER):
        print(f"[KULLANIM] tek kip ver; gecerli: {', '.join(KIPLER)}")
        return 2
    if not SH:
        print("[DOGRULANAMADI] sh/bash bulunamadi — S8 kosulamaz (sessiz gecme YOK)")
        return 2
    for p in (RAV, SABLON, PROJECT_CONFIG):
        if not p.is_file():
            print(f"[DOGRULANAMADI] kaynak yok: {p}")
            return 2
    rav = RAV.read_text(encoding="utf-8")
    sab = SABLON.read_text(encoding="utf-8")
    if kipler:
        try:
            rav, sab = KIPLER[kipler[0]](rav, sab)
        except YamaTutmadi as e:
            print(f"[YAMA TUTMADI] {e} — hicbir sayi basilmadi")
            return 2
        print(f"MUTASYON KIPI: {kipler[0]} (korpus KIRMIZI olmali)")
    try:
        sonuc = senaryolar(rav, sab)
    except YamaTutmadi as e:
        print(f"[KURULAMADI] {e}")
        return 2
    kirik = [a for a, ok, _ in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
        if not ok:
            print(f"         gorulen: {detay}")
    print(f"\nSONUC: {len(sonuc) - len(kirik)}/{len(sonuc)}")
    if kipler:
        print("[DUSTU] mutasyon yakalandi" if kirik else "[KACTI] mutasyon YAKALANMADI")
    return 1 if kirik else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
