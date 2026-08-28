#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B3-01 — SAP-bagimli validator ailesinin `IX-GATE-STATUS` URETICI ucu.

KUSUR (2026-08-01 bug-avi, `B3-01`; 2026-08-28'de duzeltildi):
`run_review` zincirinde **BLOCKER** siniflandirilmis SAP-bagimli validator'lar, SAP
baglantisi kurulamadiginda `print(UYARI...)` + `return 0` veriyordu. Tuketici
(`run_review.py`) `rc == 0`'i `PASS` sayiyordu ⇒ **baglanti kesikken gate SESSIZCE
YESIL yaniyordu**: koruma, girdisi yokken kendini kapatiyordu (fail-open).

Genel SKIP altyapisi 2026-08-29'da kuruldu (`IX-GATE-STATUS` sozlesmesi + tuketici
`run_review.py:271-386`) ama BU AILE o altyapiya HIC baglanmamisti — sozlesmenin iki
ucu vardi, birbirine degmiyordu. Bu korpus URETICI ucunu civiller.

⛔ SAP'YE BAGLANMAZ. Butun vektorler **izole bir agacta** kosar: sandbox
`<tmp>/scripts/` altina validator'in KOPYASI + `_gate_status.py` + **SAHTE**
`sap_adt_lib.py` yazilir. Validator'in kendi `sys.path.insert(0, parents[1])` satiri
sandbox `scripts/`i isaret ettigi icin sahte modul gercegini golgeler. Gercek kaynaga
ASLA yazilmaz (komsu kirlenmesi yasagi).

UC AYAK:
  KIRMIZI  — taban surum (`git show HEAD:`) ayni kosulda `IX-GATE-STATUS` BASMAZ
             ve tuketici onu `PASS` sayar.
  YESIL    — duzeltilmis surum `SKIPPED measured=false` basar, tuketici `SKIP` sayar.
  POZITIF  — baglanti VARKEN gate HALA OLCUYOR: temiz obje `OK measured=true`,
  KONTROL    BOZUK obje `rc=1` (yani fix gate'i toptan SKIP'e DUSURMEDI).

Kosum:
    python tests/fixtures/sap_gate_skip_sozlesmesi/run.py
    python tests/fixtures/sap_gate_skip_sozlesmesi/run.py --mutasyon-failopen
    python tests/fixtures/sap_gate_skip_sozlesmesi/run.py --mutasyon-hepsi-skip
    python tests/fixtures/sap_gate_skip_sozlesmesi/run.py --mutasyon-kismi
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

CORE = Path(__file__).resolve().parents[3]
VAL = CORE / "scripts" / "validators"

# Tuketicinin regex'inin AYNISI DEGIL — BILEREK bagimsiz yazildi. Tuketiciden import
# etseydik iki uc ayni hatayi paylasabilirdi; burada bicimi BAGIMSIZ dogruluyoruz.
# (Ayrica V-KOPRU vektoru gercek tuketiciyi ayrica cagirir.)
BEYAN_RE = re.compile(
    r"^IX-GATE-STATUS: gate=(\S+) status=(\S+) measured=(true|false) reason=(\S+)\s*$",
    re.M)

SONUC: list[tuple[bool, str]] = []

# Hangi mutasyon hangi validator'da anlamli? (bkz. sandbox() icindeki gerekce)
MUT_HEDEF = {
    "failopen": {"check_struct_field_dtel_active", "check_sap_active_version"},
    "kismi": {"check_struct_field_dtel_active"},
    "hepsi-skip": {"check_struct_field_dtel_active", "check_sap_active_version"},
}


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((kosul, ad))
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if detay else ""))


# ── SAHTE sap_adt_lib ──────────────────────────────────────────────────────────
# Davranis env `IX_FAKE_SAP` ile secilir. GERCEK AG ERISIMI YOK.
SAHTE_LIB = '''# -*- coding: utf-8 -*-
"""SAHTE sap_adt_lib — fixture izolasyonu. AG ERISIMI YOK."""
import os


class _Yanit:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


class _Oturum:
    def get(self, url, **kw):
        mod = os.environ.get("IX_FAKE_SAP", "ok")
        if mod == "http500":
            return _Yanit(500, "")
        if mod == "get_patlar":
            raise OSError("sahte ag hatasi")
        if mod == "yok404":
            return _Yanit(404, "")
        if mod == "kismi":
            # ilk DTEL okunur, 'bar' iceren ikinci istek patlar (kismi korluk)
            if "bar" in url:
                return _Yanit(500, "")
            return _Yanit(200, '<x adtcore:version="active"/>')
        if mod == "inaktif":
            return _Yanit(200, '<x adtcore:version="inactive"/>')
        if mod == "metadatasiz":
            return _Yanit(200, "<x/>")
        # mod == "ok"
        if "/source/main" in url:
            return _Yanit(200, "define structure ZSD001_S_TEST { alan : zsd001_e_foo; }")
        return _Yanit(200, '<x adtcore:version="active"/>')


class SAPADTClient:
    def __init__(self, *a, **kw):
        if os.environ.get("IX_FAKE_SAP", "ok") == "yok":
            raise ConnectionError("sahte: .conn_adt yok / baglanti kurulamadi")
        self.url = "https://sahte.invalid"
        self.session = _Oturum()
'''

# Artefaktlar
ART_Z_DTEL = "define structure ZSD001_S_TEST {\n  alan_a : zsd001_e_foo;\n}\n"
ART_Z_DTEL_IKI = ("define structure ZSD001_S_TEST {\n"
                  "  alan_a : zsd001_e_foo;\n  alan_b : zsd001_e_bar;\n}\n")
ART_Z_DTEL_YOK = "define structure ZSD001_S_TEST {\n  alan_a : abap.char(10);\n}\n"


def sandbox(tmp: Path, validator: str, taban: bool = False,
            mutasyon: str = "") -> Path:
    """Izole agac kur; validator'in kopyasini dondur.

    taban=True  -> `git show HEAD:` surumu (KIRMIZI ayagi; duzeltme ONCESI kod)
    """
    kok = tmp / (("taban_" if taban else "fix_") + validator + ("_" + mutasyon if mutasyon else ""))
    vdir = kok / "scripts" / "validators"
    vdir.mkdir(parents=True, exist_ok=True)
    (kok / "scripts" / "sap_adt_lib.py").write_text(SAHTE_LIB, encoding="utf-8")

    hedef = vdir / f"{validator}.py"
    if taban:
        r = subprocess.run(["git", "-C", str(CORE), "show",
                            f"HEAD:scripts/validators/{validator}.py"],
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            raise SystemExit(f"HATA: taban surum alinamadi: {r.stderr[:200]}")
        hedef.write_text(r.stdout, encoding="utf-8", newline="")
    else:
        shutil.copy2(VAL / f"{validator}.py", hedef)
        gs = vdir / "_gate_status.py"
        shutil.copy2(VAL / "_gate_status.py", gs)

        # ── MUTASYONLAR (yalnizca sandbox kopyasinda) ──────────────────────────
        if mutasyon == "failopen":
            # Fix'i SOK: baglanti dalindaki beyan kaldirilir (duzeltme oncesi davranis).
            s = hedef.read_text(encoding="utf-8")
            yeni = s.replace("        sap_baglanti_yok(_GATE)\n", "")
            _yama_tuttu(s, yeni, "failopen", hedef)
            hedef.write_text(yeni, encoding="utf-8", newline="")
        elif mutasyon == "hepsi-skip":
            # "Her seyi SKIP yap" = GEVSETME. Bu mutasyon onu simule eder; POZITIF
            # KONTROL vektorleri dusmezse korpus o gevsetmeyi yakalayamiyordur.
            s = gs.read_text(encoding="utf-8")
            yeni = s.replace('measured={"true" if measured else "false"} ',
                             'measured=false ')
            _yama_tuttu(s, yeni, "hepsi-skip", gs)
            gs.write_text(yeni, encoding="utf-8", newline="")
        elif mutasyon == "kismi" and validator in MUT_HEDEF["kismi"]:
            # ⚠ HEDEF KAPSAMI: `kismi` degismezi YALNIZ dtel_active'de yasar. Mutasyonu
            # her validator'a uygulamaya calismak "YAMA TUTMADI" ile durur (dogru), ama
            # o durus mutasyonun ANLAMSIZ oldugunu degil YANLIS YERE uygulandigini
            # gosterir. Hedef kumesi bu yuzden ACIKCA yazilir.
            s = hedef.read_text(encoding="utf-8")
            yeni = s.replace("                okunamayan.append(dtel)\n", "")
            yeni = yeni.replace("            okunamayan.append(dtel)\n", "")
            _yama_tuttu(s, yeni, "kismi", hedef)
            hedef.write_text(yeni, encoding="utf-8", newline="")
    return hedef


def _yama_tuttu(eski: str, yeni: str, ad: str, dosya: Path) -> None:
    """Mutasyonun sessizce NO-OP'a donmesine karsi capa (kayitli tuzak)."""
    if eski == yeni:
        raise SystemExit(f"YAMA TUTMADI: --mutasyon-{ad} {dosya.name} icinde hicbir sey "
                         f"degistirmedi -> olculen sayilar ANLAMSIZ olurdu.")


def kos(script: Path, artefakt: Path | None, fake: str,
        ek: list[str] | None = None) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["IX_FAKE_SAP"] = fake
    env["PYTHONIOENCODING"] = "utf-8"
    # Gercek projenin .conn_adt'sine ASLA dokunma: sandbox'i proje koku goster.
    env["CLAUDE_PROJECT_DIR"] = str(script.parents[2])
    cmd = [sys.executable, str(script)] + ([str(artefakt)] if artefakt else []) + (ek or [])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, cwd=str(script.parents[2]), timeout=60)
    return r.returncode, r.stdout, r.stderr


def beyan(stdout: str) -> tuple[str, str, str, str] | None:
    m = BEYAN_RE.findall(stdout or "")
    return m[-1] if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon-failopen", action="store_true")
    ap.add_argument("--mutasyon-hepsi-skip", action="store_true")
    ap.add_argument("--mutasyon-kismi", action="store_true")
    ap.add_argument("--mutasyon-cevrimdisi-genis", action="store_true",
                    help="cevrimdisi indirimi TUM BLOCKER'lari yutsun (gevsetme cakisi)")
    a = ap.parse_args()
    mut = ("failopen" if a.mutasyon_failopen else
           "hepsi-skip" if a.mutasyon_hepsi_skip else
           "kismi" if a.mutasyon_kismi else
           "cevrimdisi-genis" if a.mutasyon_cevrimdisi_genis else "")

    print(__doc__.strip().splitlines()[0])
    print(f"MOD: {'MUTASYON --' + mut if mut else 'NORMAL'}\n")

    with tempfile.TemporaryDirectory(prefix="ix_b301_") as td:
        tmp = Path(td)
        art = tmp / "artefaktlar"
        art.mkdir()
        a1 = art / "ZSD001_S_TEST.struct.ddls"
        a1.write_text(ART_Z_DTEL, encoding="utf-8")
        a2 = art / "ZSD001_S_IKI.struct.ddls"
        a2.write_text(ART_Z_DTEL_IKI, encoding="utf-8")
        a3 = art / "ZSD001_S_YOK.struct.ddls"
        a3.write_text(ART_Z_DTEL_YOK, encoding="utf-8")

        # ══ KIRMIZI AYAK — taban surum (duzeltme ONCESI) ════════════════════════
        print("-- KIRMIZI: taban surum (git show HEAD:) baglanti YOKken --")
        tb = sandbox(tmp, "check_struct_field_dtel_active", taban=True)
        rc, out, _ = kos(tb, a1, "yok")
        kontrol("R1 taban: baglanti yok -> rc=0 (fail-open)", rc == 0, f"rc={rc}")
        kontrol("R1b taban: IX-GATE-STATUS satiri BASILMIYOR (tuketici PASS sayar)",
                beyan(out) is None, f"beyan={beyan(out)}")
        tb2 = sandbox(tmp, "check_sap_active_version", taban=True)
        rc, out, _ = kos(tb2, None, "yok", ek=["--name", "ZSD001_S_TEST", "--object-type", "structure"])
        kontrol("R2 taban: check_sap_active_version baglanti yok -> beyan YOK",
                rc == 0 and beyan(out) is None, f"rc={rc}")

        # ══ YESIL AYAK — duzeltilmis surum, ayni kosul ══════════════════════════
        print("\n-- YESIL: duzeltilmis surum, AYNI kosul --")
        fx = sandbox(tmp, "check_struct_field_dtel_active", mutasyon=mut)
        rc, out, _ = kos(fx, a1, "yok")
        b = beyan(out)
        kontrol("V1 baglanti yok -> SKIPPED measured=false (rc DEGISMEDI)",
                rc == 0 and b is not None and b[1] == "SKIPPED" and b[2] == "false"
                and b[3] == "sap-baglanti-yok", f"rc={rc} beyan={b}")
        kontrol("V1b beyan gate adini TASIR (tuketici stem ile eslestirir)",
                b is not None and b[0] == "check_struct_field_dtel_active", f"beyan={b}")

        fx2 = sandbox(tmp, "check_sap_active_version", mutasyon=mut)
        rc, out, _ = kos(fx2, None, "yok",
                         ek=["--name", "ZSD001_S_TEST", "--object-type", "structure"])
        b = beyan(out)
        kontrol("V2 check_sap_active_version baglanti yok -> SKIPPED measured=false",
                rc == 0 and b is not None and b[2] == "false", f"rc={rc} beyan={b}")

        rc, out, _ = kos(fx2, None, "http500",
                         ek=["--name", "ZSD001_S_TEST", "--object-type", "structure"])
        b = beyan(out)
        kontrol("V3 non-200 -> SKIPPED measured=false (baglanti VAR, cevap YOK)",
                rc == 0 and b is not None and b[2] == "false"
                and b[3].startswith("sap-get-http"), f"rc={rc} beyan={b}")

        rc, out, _ = kos(fx2, None, "metadatasiz",
                         ek=["--name", "ZSD001_S_TEST", "--object-type", "structure"])
        b = beyan(out)
        kontrol("V4 version metadata yok -> SKIPPED measured=false",
                rc == 0 and b is not None and b[2] == "false", f"rc={rc} beyan={b}")

        # ══ POZITIF KONTROL — gate HALA OLCUYOR ════════════════════════════════
        # ⛔ EN KRITIK AYAK: "her seyi SKIP yap" bir GEVSETMEDIR. Asagidaki dort
        #    vektor fix'in gate'i toptan SKIP'e dusurmedigini civiller.
        print("\n-- POZITIF KONTROL: baglanti VARKEN gate hala olcuyor --")
        rc, out, _ = kos(fx, a1, "ok")
        b = beyan(out)
        kontrol("P1 baglanti var + DTEL aktif -> OK measured=TRUE, rc=0",
                rc == 0 and b is not None and b[1] == "OK" and b[2] == "true",
                f"rc={rc} beyan={b}")

        rc, out, err = kos(fx, a1, "yok404")
        b = beyan(out)
        kontrol("P2 GERCEK IHLAL (DTEL SAP'de yok) -> rc=1 BLOKLUYOR",
                rc == 1, f"rc={rc}")
        kontrol("P2b gercek ihlalde beyan measured=true (olctu ve BULDU)",
                b is not None and b[2] == "true" and b[1] == "FINDING", f"beyan={b}")

        rc, out, _ = kos(fx2, None, "inaktif",
                         ek=["--name", "ZSD001_S_TEST", "--object-type", "structure"])
        kontrol("P3 GERCEK IHLAL (version=inactive) -> rc=1 BLOKLUYOR", rc == 1, f"rc={rc}")

        rc, out, _ = kos(fx, a3, "yok")
        b = beyan(out)
        kontrol("P4 FP CAPASI: Z DTEL YOK artefakt, baglanti YOKken bile measured=TRUE "
                "(kapsam-disi hukmu gercek bir olcumdur; SKIP'e dusurulmedi)",
                rc == 0 and b is not None and b[1] == "OK" and b[2] == "true",
                f"rc={rc} beyan={b}")

        # ══ KISMI KORLUK ════════════════════════════════════════════════════════
        print("\n-- KISMI KORLUK: bazi DTEL okunamadi --")
        rc, out, err = kos(fx, a2, "kismi")
        b = beyan(out)
        kontrol("V5 bir DTEL non-200 -> 'hepsi aktif' DEMEZ, SKIPPED measured=false",
                rc == 0 and b is not None and b[2] == "false"
                and b[3] == "kismi-okunamadi", f"rc={rc} beyan={b}")
        kontrol("V5b eski YALAN cumle ('hepsi aktif') artik BASILMIYOR",
                "hepsi aktif" not in out, f"out={out[:120]!r}")

        # ══ UCUNCU BAGLAM — farkli cwd + pozisyonel artefakt yerine bayrak ══════
        print("\n-- 3. BAGLAM: yabanci cwd (import kablolamasi) --")
        r = subprocess.run(
            [sys.executable, str(fx2), "--name", "ZSD001_S_TEST", "--object-type", "structure"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=dict(os.environ, IX_FAKE_SAP="yok", PYTHONIOENCODING="utf-8",
                     CLAUDE_PROJECT_DIR=str(fx2.parents[2])),
            cwd=str(tmp), timeout=60)
        kontrol("V6 yabanci cwd'den kosum: _gate_status import'u COZULUYOR (ImportError yok)",
                r.returncode == 0 and beyan(r.stdout) is not None,
                f"rc={r.returncode} err={r.stderr[-160:]!r}")

        # ══ KOPRU — GERCEK tuketici bu beyani okuyor mu? ════════════════════════
        print("\n-- KOPRU: uretici <-> GERCEK tuketici (run_review.gate_durum_beyani) --")
        spec = importlib.util.spec_from_file_location("_rr", VAL / "run_review.py")
        rr = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(rr)
        rc, out, _ = kos(fx, a1, "yok")
        tb_beyan = rr.gate_durum_beyani(out, "check_struct_field_dtel_active.py")
        kontrol("V7 GERCEK tuketici beyani AYRISTIRIYOR (iki uc birbirine DEGIYOR)",
                tb_beyan is not None and tb_beyan["measured"] == "false",
                f"tuketici={tb_beyan}")
        rc_ok, out_ok, _ = kos(fx, a1, "ok")
        kontrol("V7b tuketici temiz kosumda measured=true goruyor (PASS kalir)",
                (rr.gate_durum_beyani(out_ok, "check_struct_field_dtel_active.py") or {})
                .get("measured") == "true")

    # ══ CEVRIMDISI MOD (B3-01 EK, 2026-08-28) — bilincli cikis yolu ═══════════
    # Kullanici VPN'siz calisirken 5 gorev zinciri BLOCKER veriyordu. Cozum: operator
    # ACIKCA "cevrimdisiyim" desin (bayrak/env), o zaman YALNIZ `measured=false`
    # kaynakli BLOCKER SKIP'ler WARNING'e insin. ⛔ Otomatik cikarim YOK.
    print("\n-- CEVRIMDISI MOD: N1 varsayilan / P1 bayrak / K1 gercek ihlal --")
    izole = tmp / "izole_review"
    (izole / "scripts").mkdir(parents=True)
    shutil.copytree(VAL, izole / "scripts" / "validators")
    shutil.copytree(CORE / "scripts" / "utils", izole / "scripts" / "utils")
    (izole / "scripts" / "sap_adt_lib.py").write_text(SAHTE_LIB, encoding="utf-8")
    rr_yol = izole / "scripts" / "validators" / "run_review.py"

    if mut == "cevrimdisi-genis":
        # GEVSETME MUTASYONU: indirim `olcum_yok` sartini YOK SAYSIN => gercek bulgu
        # (FAIL) da yutulsun. K1 bunu yakalamazsa korpus gevsemeyi olcemiyordur.
        _s = rr_yol.read_text(encoding="utf-8")
        _y = _s.replace(
            "    indirilen = [r for r in results\n"
            "                 if r['status'] == 'SKIP' and r['severity'] == 'BLOCKER'\n"
            "                 and r.get('olcum_yok')] if cevrimdisi else []",
            "    indirilen = [r for r in results\n"
            "                 if r['severity'] == 'BLOCKER'] if cevrimdisi else []")
        _yama_tuttu(_s, _y, "cevrimdisi-genis", rr_yol)
        rr_yol.write_text(_y, encoding="utf-8", newline="")

    a_temiz = izole / "ZSD001_S_TEMIZ.struct.ddls"
    a_temiz.write_text(ART_Z_DTEL, encoding="utf-8")
    a_kirli = izole / "ZSD001_S_KIRLI.struct.ddls"
    # `netwr` CURR_DTELS'te, `waers` CUKY_DTELS'te => annotation eksikligi BLOCKER
    # (check_cds_currency_reference, SAP GEREKTIRMEZ => gercek OLCULMUS bulgu).
    a_kirli.write_text("define structure ZSD001_S_KIRLI {\n"
                       "  alan_a     : zsd001_e_foo;\n"
                       "  tutar      : netwr;\n"
                       "  parabirimi : waers;\n}\n", encoding="utf-8")

    def review(artefakt, cevrimdisi_mi):
        cmd = [sys.executable, str(rr_yol), "--task", "struct_creation",
               "--artifact", str(artefakt), "--json"]
        if cevrimdisi_mi:
            cmd.append("--cevrimdisi")
        env = dict(os.environ, IX_FAKE_SAP="yok", PYTHONIOENCODING="utf-8",
                   CLAUDE_PROJECT_DIR=str(izole))
        env.pop("IX_CEVRIMDISI", None)
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, cwd=str(izole), timeout=180)
        try:
            return r.returncode, json.loads(r.stdout)
        except Exception:
            return r.returncode, {"_stdout": r.stdout[-400:], "_stderr": r.stderr[-400:]}

    rc_n1, d_n1 = review(a_temiz, False)
    kontrol("C1 VARSAYILAN korundu: bayraksiz + SAP yok -> verdict BLOCKER, exit 1",
            d_n1.get("verdict") == "BLOCKER" and rc_n1 == 1
            and d_n1.get("skipped_blocker_count") == 1,
            f"rc={rc_n1} verdict={d_n1.get('verdict')} skipped_blocker={d_n1.get('skipped_blocker_count')}")
    kontrol("C1b varsayilanda cevrimdisi ALANLARI kapali",
            d_n1.get("cevrimdisi") is False and d_n1.get("offline_downgraded_count") == 0,
            f"cevrimdisi={d_n1.get('cevrimdisi')}")

    rc_p1, d_p1 = review(a_temiz, True)
    kontrol("C2 BAYRAKLA: verdict WARNING, exit 0 (offline akis ACIK)",
            d_p1.get("verdict") == "WARNING" and rc_p1 == 0,
            f"rc={rc_p1} verdict={d_p1.get('verdict')}")
    kontrol("C2b GURULTU: skipped_blocker KAYBOLMADI + indirilen gate ADIYLA raporlu",
            d_p1.get("skipped_blocker_count") == 1
            and d_p1.get("offline_downgraded_count") == 1
            and "check_struct_field_dtel_active.py" in (d_p1.get("offline_downgraded_gates") or [])
            and d_p1.get("kapsam_eksik") is True,
            f"skipped_blocker={d_p1.get('skipped_blocker_count')} "
            f"indirilen={d_p1.get('offline_downgraded_gates')} "
            f"kapsam_eksik={d_p1.get('kapsam_eksik')}")

    rc_k1, d_k1 = review(a_kirli, True)
    kontrol("⛔ C3 EN KRITIK: bayrak ACIK + GERCEK IHLAL -> verdict BLOCKER KALIYOR",
            d_k1.get("verdict") == "BLOCKER" and rc_k1 == 1,
            f"rc={rc_k1} verdict={d_k1.get('verdict')} "
            f"failed_blocker={d_k1.get('failed_blocker_count')}")
    kontrol("C3b gercek bulgu FAIL olarak sayiliyor (SKIP'e/indirime karismadi)",
            d_k1.get("failed_blocker_count") == 1,
            f"failed_blocker={d_k1.get('failed_blocker_count')}")
    kontrol("C4 FP CAPASI: gate DOSYASI YOK kaynakli SKIP indirilMEDI "
            "(cevrimdisi olmak silinmis gate'i affetmez)",
            d_p1.get("offline_downgraded_count") == 1,
            f"indirilen={d_p1.get('offline_downgraded_gates')}")

    # ══ DG-03: CI CORE-INDEX backstop'u TAUTOLOJI olmamali ════════════════════
    # `build_core_index.py --ci-check` UC dalli: (a) damgadaki core-commit klonlanan
    # core HEAD'iyle AYNI + indeks taze -> OK measured=true ; (b) ayni + BAYAT -> rc=1
    # (GERCEKTEN BLOKLAR) ; (c) FARKLI commit -> SKIPPED measured=false (dokuman-kumesi
    # farki bayatlik DEGILDIR; sahte-yesil yerine durust "olcemedim").
    print("\n-- DG-03: build_core_index --ci-check uc dal --")
    ci = subprocess.run([sys.executable, str(CORE / "scripts" / "build_core_index.py"),
                         "--ci-check"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=120,
                        env=dict(os.environ, PYTHONIOENCODING="utf-8"), cwd=str(CORE))
    cb = beyan(ci.stdout)
    kontrol("V9 --ci-check MAKINECE OKUNUR beyan basiyor (uc daldan biri)",
            cb is not None and cb[0] == "build_core_index", f"beyan={cb}")
    kontrol("V9b --ci-check dali gecerli: OK/FINDING -> measured=true, "
            "SKIPPED -> measured=false (kova ile beyan TUTARLI)",
            cb is not None and ((cb[1] == "SKIPPED") == (cb[2] == "false")),
            f"beyan={cb}")
    # ⚠ (b) dali (gercek bayatlik -> rc=1) bu korpusta OTOMATIK kosulmaz: gercek core
    # agacina dosya eklemeyi gerektirir (komsu kirletme yasagi). Elle olculdu ve
    # changelog'a yazildi; recete: playbook disi, `governance/infra-test-recipes.md`.

    # ══ B2-13: `--strict` BEYANI <-> MEKANIK durustlugu ════════════════════════
    # Bu vektor bir GATE degil bir REGRESYON CAPASIDIR: yeni bir validator
    # `--strict`i sessizce (help= olmadan, gövdede kullanmadan) beyan ederse burada
    # dusur. ⛔ Bayragin KALDIRILMASI cozum DEGILDIR: `run_all_validators.py:164-165`
    # `--strict`i KAYITLI HER validator'a iletir; `parse_args()` kullanan bir
    # validator'da beyan yoksa `unrecognized arguments` -> rc=2 -> run_all FAIL
    # (olculdu 2026-08-28). NO-OP olmasi da ADR 0019 §54 geregi BILINCLIDIR.
    print("\n-- B2-13: --strict beyani <-> mekanik durustlugu --")
    tek_re = re.compile(r'add_argument\(([\'\"])--strict\1,\s*action=([\'\"])store_true\2\)')
    sessiz = []
    for p in sorted(VAL.glob("*.py")):
        s = p.read_text(encoding="utf-8", errors="replace")
        kullaniyor = ("args.strict" in s or re.search(r"\ba\.strict\b", s))
        if tek_re.search(s) and not kullaniyor:
            sessiz.append(p.name)
    kontrol("V8 `--strict` beyan edip NE kullanan NE aciklayan validator YOK "
            "(beyan var / mekanik yok sinifi kapali)",
            not sessiz, f"sessiz={sessiz}")

    # ── ozet ──────────────────────────────────────────────────────────────────
    gecen = sum(1 for ok, _ in SONUC if ok)
    print(f"\n{'=' * 62}\nSONUC: {gecen}/{len(SONUC)}")
    if gecen != len(SONUC):
        print("Dusen vektorler: " + ", ".join(ad for ok, ad in SONUC if not ok))
    if mut:
        print(f"(MUTASYON --{mut}: dusus BEKLENIR; tam puan = korpus o degismez icin BOS)")
        return 0
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
