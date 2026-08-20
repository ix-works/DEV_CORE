#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIXTURE — advisory gate SOZLESMESI + kazara-terfi yasagi (K5, 2026-08-20).

NICIN VAR (olculmus): `check_rap_byassoc_keys_only` govdesinde `return 0  # SOFT` tasiyordu.
Sonuclari:
  (a) "gate" sayiliyordu — `check_rule_gate_coverage` onu 61 auto-gate IDDIASINA katiyordu,
      yani iddia gerceginden FAZLAYDI (arkasinda BLOKLAYAN script varmis gibi okunuyordu);
  (b) FIXTURE'LANAMIYORDU — `tests/run_fixture_tests.py` yorumunun kendi ifadesiyle:
      "ATLANDI: check_rap_byassoc_keys_only (kod her zaman `return 0` -- SOFT, fixture'la
      FAIL uretilemez)". Yani kapsanmayan tek sebep, gate'in KENDI tasarimiydi.

⛔ NE DEGISMEDI (kabul olcutu): default `exit 0` AYNEN durur. Canli korpusta 2 bulgu var ve
IKISI DE MESRU (ZCL_SD015_BOOKING.ccimp.abap:191/:316 — kodun kendi yorumu "Sayim icin KEY
okuma yeterli"); standards/05 §5.1 zaten "yalniz existence/line_exists gerekiyorsa FROM
yeterli" der. Default'u FAIL yapmak 2 DOGRU kodu bloklardi. S1 + M3 bunu civiler.

⭐ KAZARA TERFI YASAGI (S3 + M2): bayrak `--strict` OLAMAZ, cunku `run_all_validators --strict`
bayragi TUM validator'lara iletir ⇒ terfi karari kazara bir CAGIRANIN eline gecerdi
(ADR 0019 §54 shakeout dersi). Opt-in ad: `--bulguda-exit1`. `--strict` BILEREK NO-OP.

⭐ COVERAGE OZETI (S8/S9 + M6): `check_rule_gate_coverage` artik `# GATE-SEVERITY:` beyanini
okuyup `N iddia (B bloklayici · A advisory)` basar. S8 bir SAHTE-BEYAN capasidir: markoru
TARIF eden duz metin (bu yuzeyde: coverage'in kendi docstring'i) onu BEYAN etmis sayilamaz —
ilk surumde tam bu yuzden HARD olan `check_rule_gate_coverage` kendini "advisory" ilan etti.

IZOLASYON (F1): mutasyon GERCEK dosyaya YAZILMAZ; kardes `_mutant_byassoc_*.py` dosyasinda
yasar ve finally'de silinir. ⚠ Kardes adi FIXTURE ADIYLA ONEKLENIR: repoda `_mutant_post_validate.py`
adini IKI ayri fixture (fs_docstd + hook_bash_ve_stderr_kapsami) PAYLASIYOR ve bu, tam
sure boyunca ayakta kalan bir carpisma sinifidir — o sinifa katilmamak icin ad benzersiz.
"""
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
V = KOK / "scripts" / "validators"
GATE = V / "check_rap_byassoc_keys_only.py"
COV = V / "check_rule_gate_coverage.py"
MUT_GATE = V / "_mutant_byassoc_advisory.py"
MUT_COV = V / "_mutant_byassoc_coverage.py"

PROJE_YAML = ("sap_profile: s4_private\nrelease: '2025'\nmaster_language: TR\n"
              "source_root: SOURCE_CODES\ncleancore_policy: balanced\n")

# KIRLI: BY \_assoc + FROM, ALL FIELDS/FIELDS( YOK -> tek bulgu.
KIRLI_ABAP = """CLASS lcl_handler IMPLEMENTATION.
  METHOD validate_bad.
    READ ENTITIES OF zi_root IN LOCAL MODE
      ENTITY Root BY \\_Item
        FROM VALUE #( ( RootId = ls_root-RootId ) )
      RESULT lt_item.
  ENDMETHOD.
ENDCLASS.
"""

# TEMIZ: uc mesru bicim (ALL FIELDS WITH · FIELDS ( .. ) WITH · assoc'suz FROM).
TEMIZ_ABAP = """CLASS lcl_handler IMPLEMENTATION.
  METHOD ok_all_fields.
    READ ENTITIES OF zi_root IN LOCAL MODE
      ENTITY Root BY \\_Item
        ALL FIELDS WITH VALUE #( ( RootId = ls_root-RootId ) )
      RESULT lt_item.
  ENDMETHOD.
  METHOD ok_selected_fields.
    READ ENTITIES OF zi_root IN LOCAL MODE
      ENTITY Root BY \\_Item
        FIELDS ( Status Amount ) WITH VALUE #( ( RootId = ls_root-RootId ) )
      RESULT lt_item.
  ENDMETHOD.
  METHOD ok_no_assoc.
    READ ENTITIES OF zi_root IN LOCAL MODE
      ENTITY Root
        FROM VALUE #( ( RootId = ls_root-RootId ) )
      RESULT lt_root.
  ENDMETHOD.
  METHOD ok_all_fields_but_from_kelimesi_var.
    " ⭐ SAFE deseninin GERCEKTEN is gordugu tek vektor: ifadede `FROM` KELIMESI geciyor
    " (CORRESPONDING ... FROM ...) ama okuma modu ALL FIELDS WITH. `FROM` kontrolu tek
    " basina bunu ELEYEMEZ; eleyen SAFE'tir. Bu vektor olmadan SAFE'i soken mutasyon
    " (M5) hicbir senaryoyu kirmiyordu — yani korpus SAFE'i hic sinamiyordu (olculdu).
    READ ENTITIES OF zi_root IN LOCAL MODE
      ENTITY Root BY \\_Item
        ALL FIELDS WITH CORRESPONDING #( lt_keys FROM lt_source )
      RESULT lt_item.
  ENDMETHOD.
ENDCLASS.
"""

# S7 surucusu: "okunamayan dosya" TASINABILIR bicimde uretilemez (Windows'ta chmod, Linux'ta
# root farki, symlink yetkisi...). Bu yuzden read_text KOSUM ANINDA yonlendirilir.
# ⚠ Yonlendirme import'tan SONRA kurulur ama okuma main() icinde oldugu icin GEC KALMAZ;
# env (CLAUDE_PROJECT_DIR) ise import ONCESI kuruludur — REPO/ERP modul yuklenirken hesaplanir.
SURUCU = '''import importlib.util, pathlib, sys
hedef = sys.argv[1]
spec = importlib.util.spec_from_file_location("gate_altinda_test", hedef)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
_orig = pathlib.Path.read_text
def _patlat(self, *a, **k):
    if "UNREADABLE" in self.name:
        raise OSError("simulated unreadable file")
    return _orig(self, *a, **k)
pathlib.Path.read_text = _patlat
sys.argv = ["gate"]
sys.exit(m.main())
'''


def _agac(kok: Path, ad: str, govde: str) -> Path:
    d = kok / ad
    (d / "SOURCE_CODES" / "SD" / "ZTEST").mkdir(parents=True, exist_ok=True)
    (d / "project.yaml").write_text(PROJE_YAML, encoding="utf-8")
    (d / "SOURCE_CODES" / "SD" / "ZTEST" / "ZCL_TEST.ccimp.abap").write_text(govde, encoding="utf-8")
    return d


def kos(script: Path, agac: Path, *args: str):
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["CLAUDE_PROJECT_DIR"] = str(agac)
    p = subprocess.run([sys.executable, str(script), *args], cwd=str(agac), env=env,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=90)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def kos_surucu(script: Path, agac: Path, surucu: Path):
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["CLAUDE_PROJECT_DIR"] = str(agac)
    p = subprocess.run([sys.executable, str(surucu), str(script)], cwd=str(agac), env=env,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=90)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def senaryolar(gate: Path, cov: Path, kirli: Path, temiz: Path,
               okunamaz: Path, surucu: Path):
    s = []

    def ekle(ad, ok, detay=""):
        s.append((ad, ok, detay))

    rc, out = kos(gate, kirli)
    ekle("S1 ⭐ ADVISORY: bulgu VARKEN default exit 0 (canli 2 mesru kod BLOKLANMAZ)",
         rc == 0 and "[WARN]" in out, f"exit={rc}")

    rc, out = kos(gate, kirli, "--bulguda-exit1")
    ekle("S2 ⭐ OPT-IN: ayni korpus `--bulguda-exit1` ile exit 1 (gate artik FIXTURE'LANABILIR)",
         rc == 1 and "[WARN]" in out, f"exit={rc}")

    rc, out = kos(gate, kirli, "--strict")
    ekle("S3 ⭐ KAZARA TERFI YOK: `--strict` NO-OP (run_all --strict'i HEPSINE iletir)",
         rc == 0, f"exit={rc}")

    rc, out = kos(gate, temiz)
    ekle("S4a POZ.KONTROL: temiz korpus (ALL FIELDS WITH / FIELDS(..) WITH / assoc'suz) default 0",
         rc == 0 and "[OK]" in out, f"exit={rc}")

    rc, out = kos(gate, temiz, "--bulguda-exit1")
    ekle("S4b ⭐ POZ.KONTROL: bayrak HER SEYI kirmiyor — temiz korpus `--bulguda-exit1` ile de 0",
         rc == 0 and "[OK]" in out, f"exit={rc}")

    rc, out = kos(gate, kirli, "--selftest")
    ekle("S5 gomulu selftest: kirmizi yakalanir, yesil FP vermez (korpussuz da kosar)",
         rc == 0 and "[SELFTEST] OK" in out, f"exit={rc}")

    rc, out = kos_surucu(gate, okunamaz, surucu)
    ekle("S6 ⭐ FAIL-CLOSED: okunamayan dosya -> exit 2 ('OLCEMEDIM' != 'TEMIZ')",
         rc == 2 and "ÖLÇÜLEMEDİ" in out, f"exit={rc}")

    rc, out = kos(cov, kirli)
    ekle("S7 COVERAGE OZETI: `N iddia (B bloklayici · A advisory)` bicimi basiliyor",
         rc == 0 and "bloklayıcı" in out and "advisory" in out, f"exit={rc}")

    ekle("S8 ⭐ SAHTE-BEYAN CAPASI: markoru TARIF eden metin BEYAN sayilmaz — HARD olan "
         "`check_rule_gate_coverage` kendini advisory ILAN ETMEZ",
         "check_rule_gate_coverage.py" not in out.split("Özet:")[0], "advisory listesi")

    ekle("S9 BE-20 advisory olarak GORUNUYOR (iddia sismesi duzeldi)",
         "check_rap_byassoc_keys_only.py" in out and "BE-20" in out, "advisory listesi")

    return s


# (ad, hedef, donusum) — her biri korpusu KIRMIZI yapmali.
MUTASYONLAR = [
    ("M1 ⭐ fix'i SOK: `--bulguda-exit1` yok sayilsin (opt-in olmeden once)", "gate",
     lambda t: t.replace('bulguda_exit1 = "--bulguda-exit1" in argv',
                         'bulguda_exit1 = False')),
    ("M2 ⭐ SINIR: `--strict` de exit 1 versin (KAZARA TERFI geri gelsin)", "gate",
     lambda t: t.replace('bulguda_exit1 = "--bulguda-exit1" in argv',
                         'bulguda_exit1 = "--bulguda-exit1" in argv or "--strict" in argv')),
    ("M3 ⭐ DAVRANIS CAPASI: default'u HARD yap (2 mesru kod bloklanirdi)", "gate",
     lambda t: t.replace("        return 1 if bulguda_exit1 else 0",
                         "        return 1")),
    ("M4 fail-closed'u SOK: okunamayan dosya yine sessizce atlansin", "gate",
     lambda t: t.replace("            okunamadi += 1", "            pass")),
    ("M5 POZ.KONTROL SINIRI: SAFE desenini sok (ALL FIELDS WITH artik guvenli sayilmasin)", "gate",
     lambda t: t.replace('SAFE = re.compile(r"\\bALL\\s+FIELDS\\s+WITH\\b|\\bFIELDS\\s*\\(", re.IGNORECASE)',
                         'SAFE = re.compile(r"(?!x)x")')),
    ("M6 ⭐ coverage satir-basi capasini sok (duz metin anisi BEYAN sanilsin)", "cov",
     lambda t: t.replace('SEVERITY_RE = re.compile(r"^[ \\t]*#\\s*GATE-SEVERITY:\\s*([A-Za-z]+)", re.MULTILINE)',
                         'SEVERITY_RE = re.compile(r"#\\s*GATE-SEVERITY:\\s*([A-Za-z]+)")')),
]


def main() -> int:
    sb = Path(tempfile.mkdtemp(prefix="byassoc_adv_"))
    ham = {"gate": GATE.read_text(encoding="utf-8"), "cov": COV.read_text(encoding="utf-8")}
    kardes = {"gate": MUT_GATE, "cov": MUT_COV}
    try:
        kirli = _agac(sb, "kirli", KIRLI_ABAP)
        temiz = _agac(sb, "temiz", TEMIZ_ABAP)
        okunamaz = _agac(sb, "okunamaz", KIRLI_ABAP)
        (okunamaz / "SOURCE_CODES" / "SD" / "ZTEST" / "ZUNREADABLE.abap").write_text(
            KIRLI_ABAP, encoding="utf-8")
        surucu = sb / "surucu.py"
        surucu.write_text(SURUCU, encoding="utf-8")

        print("--- SENARYOLAR ---")
        sonuc = senaryolar(GATE, COV, kirli, temiz, okunamaz, surucu)
        kirik = [(a, d) for a, ok, d in sonuc if not ok]
        for ad, ok, detay in sonuc:
            print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
            if not ok:
                print("         gorulen: %s" % detay)
        print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

        print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
        kacan, yama_kirik, kurulamadi = [], [], []
        for ad, hedef, mut in MUTASYONLAR:
            bozuk = mut(ham[hedef])
            if bozuk == ham[hedef]:
                # YAMA TUTMADI: kaynak degismis, mutasyon ARTIK O KODU SINAMIYOR.
                print("  [YAMA TUTMADI] %s" % ad)
                yama_kirik.append(ad)
                continue
            yol = kardes[hedef]
            try:
                yol.write_text(bozuk, encoding="utf-8")
                g = yol if hedef == "gate" else GATE
                c = yol if hedef == "cov" else COV
                m_sonuc = senaryolar(g, c, kirli, temiz, okunamaz, surucu)
            except Exception as e:
                # ⛔ UCUNCU DEGER: kurulum hatasi "mutasyon kacti" DEGILDIR (olcum yapilamadi).
                print("  [KURULAMADI] %s -> %s: %s" % (ad, e.__class__.__name__, e))
                kurulamadi.append(ad)
                continue
            finally:
                try:
                    yol.unlink()
                except Exception:
                    pass
            kiranlar = [a for a, ok, _ in m_sonuc if not ok]
            if kiranlar:
                print("  [YAKALANDI] %s" % ad)
                print("         kiran senaryo(lar): %s" % ", ".join(kiranlar))
            else:
                print("  [KACTI] %s -> hicbir senaryo kirilmadi (korpus ZAYIF)" % ad)
                kacan.append(ad)

        izole = (GATE.read_text(encoding="utf-8") == ham["gate"]
                 and COV.read_text(encoding="utf-8") == ham["cov"]
                 and not MUT_GATE.exists() and not MUT_COV.exists())
        print("  [%s] F1 ⭐ izolasyon: gercek gate/coverage DEGISMEDI, mutant kardes dosya KALMADI"
              % ("PASS" if izole else "FAIL"))

        tamam = not kirik and not kacan and not yama_kirik and not kurulamadi and izole
        print("\n" + "=" * 78)
        if tamam:
            print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
            return 0
        if kurulamadi:
            print("FAIL — mutasyon KURULAMADI (olcum yapilamadi; korpus zayif DEMEK DEGIL): %s"
                  % "; ".join(kurulamadi))
        if yama_kirik:
            print("FAIL — mutasyon YAMASI TUTMADI (kaynak degismis, mutasyon o kodu sinamiyor): %s"
                  % "; ".join(yama_kirik))
        if kacan:
            print("FAIL — KACAN mutasyon (korpus zayif): %s" % "; ".join(kacan))
        if kirik:
            print("FAIL — senaryo(lar): %s" % "; ".join(a for a, _ in kirik))
        if not izole:
            print("FAIL — IZOLASYON: gercek kaynak degismis ya da mutant kardes dosya kalmis")
        return 1
    finally:
        for artik in (MUT_GATE, MUT_COV):
            try:
                artik.unlink()
            except Exception:
                pass
        shutil.rmtree(sb, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
