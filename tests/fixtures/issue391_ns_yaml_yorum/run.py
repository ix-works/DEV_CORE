# -*- coding: utf-8 -*-
"""issue391_ns_yaml_yorum — namespace'li paket: `project.yaml` tırnaklı `#` + paket sınır kapısı.

DEV_CORE Issue #391 (2026-11-07). İKİ AYRI EKSEN, iki ayrı kök:
  (b) `utils/project_config._yaml_lite` yorumu `ham.split("#", 1)` ile kesiyordu — tırnak içinde
      de. abapGit namespace gösterimi `#NSPC#` olduğu için namespace'li istisna girdisi sessizce
      bozuluyordu: satır içi `["#NSPC#SD001:^#NSPC#CL_SD001_"]` → `'['`, blok öğesi
      `- '#NSPC#SD001:…'` → `['']`. Düzeltme `_yorumu_ayikla`: `#` yalnız TIRNAK DIŞINDA yorum.
  (a) `check_object_in_correct_pkg.matches_package` yalnız "ad paket kısa adıyla başlar" kuralını
      biliyordu; namespace'li nesne (`#NSPC#CL_SD001_X` ∈ `#NSPC#SD001`) her zaman "sızıntı"ydı.
      Düzeltme: namespace'li pakette nesne AYNI namespace önekini taşıyor VE paketin `.rules.md`
      Naming regex'lerinden birine (`check_package_naming.parse_rules_md`) uyuyorsa kabul.
      Z paketleri bu dala hiç girmez.

VEKTÖRLER
  Y*  `_yaml_lite` doğrudan (süreç içi). Y1/Y2 Issue repro'su (satır içi + blok), Y3 tırnak sonrası
      satır sonu yorumu, Y8 tek tırnak `''` kaçışı, Y9 tırnaklı skaler, Y11 3. bağlam BOM+CRLF,
      Y13 iki tırnaklı öğe. KONTROL (eski kodda da yeşil, değişmemeli): Y4 tüketici biçimi
      `- "ZSD001_CLC:^ZCL_SD001_"   # açıklama` · Y5 tırnaksız `#` keser · Y6 kelime içi kesme
      işareti tırnak sayılmaz · Y7 kapanmamış tırnak → eski kesim · Y10 Z satır içi · Y12 tüm dosya.
  A*  KABLOLAMA (gerçek giriş noktası, alt süreç): `.rules.md`'siz namespace paketi, istisna
      `project.yaml`'dan — A1 satır içi, A2 blok. (b) olmadan istisna bozulur → ihlal.
  N*  (a) kabul: N1 `.rules.md`'li namespace paketi doğru ad · N2 3. bağlam (başka modül, küçük harfli
      abapGit dosya adı, `cds/` altında `.ddls.asddls`) · S1 KAPSAM satırı namespace yolunu anar.
  R*  (a) red (fail-closed): R1 yanlış namespace — `.rules.md` regex'i namespace'e GEVŞEK yazılmış
      olsa bile önek şartı reddeder · R2 tabloya uymayan ad · R3 `.rules.md` yok (mesaj bunu söyler)
      · R4 Z paketi istisnasız `ZCL_SD001_X` (`.rules.md` regex'i uysa bile — Z davranışı DEĞİŞMEDİ)
      · R5 derlenmeyen regex çökme üretmez, kabul üretmez. K1 Z kontrol grubu `ZSD001_X` kabul.

Koşum:     python tests/fixtures/issue391_ns_yaml_yorum/run.py
MUTASYON (önce aynı sarmalayıcı YAMASIZ koşulur — kum tabanı tam yeşil olmalı):
  --mutasyon-yorum-kesimi  `_yorumu_ayikla` → eski `split("#", 1)[0]`
                           İLAN: {Y1, Y2, Y3, Y8, Y9, Y11, Y13, A1, A2}
  --mutasyon-ns-kapali     `namespace_kurallari` → [] (namespace dalı kapalı)
                           İLAN: {N1, N2, S1}
  --mutasyon-ns-onek-yok   `matches_package` içindeki `and base.startswith(ns)` şartı silinir
                           İLAN: {R1}
  Çıkış: 0 taban yeşil · 1 taban kırmızı YA DA yalnız ilan edilen küme düştü · 2 SAPMA ya da
  geçersiz kip · 3 kurulamadı (yama noktası yok / kum tabanı kırmızı).
Kontrol grubu: `I391_SCRIPTS_KOK=<scripts dizini>` ile başka bir sürüm koşulabilir (düzeltme öncesi
  kod `f646f36`: Y1 Y2 Y3 Y8 Y9 Y11 Y13 A1 A2 N1 N2 S1 R3 FAIL — 11/24, 2026-11-07 ölçüldü;
  R3 eski kodda da rc 1 verir ama namespace mesajı yoktur).
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
SCRIPTS = Path(os.environ.get("I391_SCRIPTS_KOK") or (KOK / "scripts"))
GATE = SCRIPTS / "validators" / "check_object_in_correct_pkg.py"

GECERLI_KIP = {"--mutasyon-yorum-kesimi", "--mutasyon-ns-kapali", "--mutasyon-ns-onek-yok"}
KIP_KISA = {"--mutasyon-yorum-kesimi": "yorum", "--mutasyon-ns-kapali": "ns",
            "--mutasyon-ns-onek-yok": "onek"}
BEKLENEN_DUSEN = {
    "yorum": {"Y1", "Y2", "Y3", "Y8", "Y9", "Y11", "Y13", "A1", "A2"},
    "ns": {"N1", "N2", "S1"},
    "onek": {"R1"},
}

SARMALAYICI = r'''
import os, sys, types
scripts, kip = sys.argv[1], sys.argv[2]
sys.path.insert(0, scripts)
sys.path.insert(0, os.path.join(scripts, "validators"))
import utils.project_config as pc
if kip == "yorum":
    if not callable(getattr(pc, "_yorumu_ayikla", None)):
        print("[KURULAMADI] _yorumu_ayikla yok (yama noktasi yok)")
        sys.exit(3)
    pc._yorumu_ayikla = lambda s: s.split("#", 1)[0]
    pc._yaml_lite.cache_clear()
gate = os.path.join(scripts, "validators", "check_object_in_correct_pkg.py")
with open(gate, encoding="utf-8") as fh:
    kaynak = fh.read()
if kip == "onek":
    capa = " and base.startswith(ns):"
    if kaynak.count(capa) != 1:
        print("[KURULAMADI] onek capasi bulunamadi/tekil degil: %d" % kaynak.count(capa))
        sys.exit(3)
    kaynak = kaynak.replace(capa, ":")
mod = types.ModuleType("check_object_in_correct_pkg")
mod.__file__ = gate
exec(compile(kaynak, gate, "exec"), mod.__dict__)
if kip == "ns":
    if not callable(getattr(mod, "namespace_kurallari", None)):
        print("[KURULAMADI] namespace_kurallari yok (yama noktasi yok)")
        sys.exit(3)
    mod.namespace_kurallari = lambda p: []
sys.argv = [gate]
sys.exit(mod.main())
'''

RULES_NS = """# {pkg}

## Naming

| Obje Tipi | Prefix | Regex |
|---|---|---|
| Class | `{ns}CL_{kisa}_*` | `^{ns}CL_{kisa}_[A-Z0-9_]+$` |
| CDS Interface View | `{ns}I_{kisa}_*` | `^{ns}I_{kisa}_[A-Z0-9_]+$` |

## Bilinen İstisnalar

- yok
"""


# ── (b) yaml vektörleri ─────────────────────────────────────────────────────
NS_GIRDI = "#NSPC#SD001:^#NSPC#CL_SD001_"
YAML_VEKTOR = [
    # (id, kontrol_mu, içerik, anahtar, beklenen, açıklama)
    ("Y1", False, 'package_exceptions: ["#NSPC#SD001:^#NSPC#CL_SD001_"]\n',
     "package_exceptions", [NS_GIRDI], "Issue repro satır içi liste"),
    ("Y2", False, "package_exceptions:\n  - '#NSPC#SD001:^#NSPC#CL_SD001_'\n",
     "package_exceptions", [NS_GIRDI], "Issue repro blok liste (tek tırnak)"),
    ("Y3", False, 'package_exceptions:\n  - "#NSPC#SD001:^#NSPC#CL_SD001_"   # açıklama\n',
     "package_exceptions", [NS_GIRDI], "tırnaklı değer + satır sonu yorumu"),
    ("Y4", True, 'package_exceptions:\n  - "ZSD001_CLC:^ZCL_SD001_"   # açıklama\n',
     "package_exceptions", ["ZSD001_CLC:^ZCL_SD001_"], "KONTROL tüketici biçimi (yorum korunur)"),
    ("Y5", True, "aciklama: a#b\nurl: deger # yorum\n",
     "aciklama", "a", "KONTROL tırnaksız `#` bugünkü gibi keser"),
    ("Y6", True, "baslik: Paket'in adi # yorum\n",
     "baslik", "Paket'in adi", "KONTROL kelime içi kesme işareti tırnak DEĞİL"),
    ("Y7", True, 'x: "abc # yorum\n',
     "x", "abc", "KONTROL kapanmamış tırnak → eski kesim"),
    ("Y8", False, "t: 'a''#b'\n", "t", "a''#b", "tek tırnak `''` kaçışı içinde `#`"),
    ("Y9", False, 's: "C#"   # yorum\n', "s", "C#", "tırnaklı skaler içinde `#`"),
    ("Y10", True, 'package_exceptions: ["ZSD001:^ZCL_SD001_"]\n',
     "package_exceptions", ["ZSD001:^ZCL_SD001_"], "KONTROL Z satır içi"),
    ("Y13", False, "package_exceptions: [\"#AAA#X:^#AAA#CL_\", '#BBB#Y:^#BBB#CL_']  # iki\n",
     "package_exceptions", ["#AAA#X:^#AAA#CL_", "#BBB#Y:^#BBB#CL_"], "iki tırnaklı öğe"),
]

Y12_ICERIK = ("# baslik yorumu\n"
              "sap_profile: s4_private  # profil\n"
              "release: \"2025\"\n"
              "source_root: SRC\n"
              "\n"
              "include_naming_exempt:\n"
              "  - ZSD001_I_A_T01   # legacy\n")
Y12_BEKLENEN = {"sap_profile": "s4_private", "release": "2025", "source_root": "SRC",
                "include_naming_exempt": ["ZSD001_I_A_T01"]}


def _pc(kip: str | None):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from utils import project_config as pc  # type: ignore
    return pc


def yaml_tur(tmp: Path, kip: str | None) -> dict[str, tuple[bool, str, str]]:
    pc = _pc(kip)
    asil = getattr(pc, "_yorumu_ayikla", None)
    sonuc: dict[str, tuple[bool, str, str]] = {}
    try:
        if kip == "yorum":
            pc._yorumu_ayikla = lambda s: s.split("#", 1)[0]
        for vid, _k, icerik, anahtar, beklenen, aciklama in YAML_VEKTOR:
            p = tmp / f"{vid}.yaml"
            p.write_bytes(icerik.encode("utf-8"))
            pc._yaml_lite.cache_clear()
            al = pc._yaml_lite(str(p)).get(anahtar)
            sonuc[vid] = (al == beklenen, f"{vid} {aciklama}", f"alındı={al!r} beklenen={beklenen!r}")
        # Y11 — 3. bağlam: BOM + CRLF (PowerShell şekli); bayt olarak yazılır
        p = tmp / "Y11.yaml"
        p.write_bytes(b"\xef\xbb\xbf" + 'sap_profile: s4_private\r\npackage_exceptions:\r\n'
                      "  - '#NSPC#SD001:^#NSPC#CL_SD001_'\r\n".encode("utf-8"))
        pc._yaml_lite.cache_clear()
        d = pc._yaml_lite(str(p))
        ok = d.get("sap_profile") == "s4_private" and d.get("package_exceptions") == [NS_GIRDI]
        sonuc["Y11"] = (ok, "Y11 3.bağlam BOM+CRLF blok liste", f"alındı={d!r}")
        p = tmp / "Y12.yaml"
        p.write_bytes(Y12_ICERIK.encode("utf-8"))
        pc._yaml_lite.cache_clear()
        d = pc._yaml_lite(str(p))
        sonuc["Y12"] = (d == Y12_BEKLENEN, "Y12 KONTROL tüm dosya (yorum satırı + satır sonu yorumu)",
                        f"alındı={d!r}")
    finally:
        if asil is not None:
            pc._yorumu_ayikla = asil
        pc._yaml_lite.cache_clear()
    return sonuc


# ── (a) + kablolama: gerçek kapı alt süreçte ────────────────────────────────
def _proje(kok: Path, paketler: list[tuple[str, str, dict[str, str], str | None]],
           yaml_ek: str = "") -> Path:
    """paketler: (modül, paket, {göreli_yol: içerik}, rules_md|None)."""
    kok.mkdir(parents=True)
    (kok / "project.yaml").write_bytes(
        ("sap_profile: s4_private\nsource_root: SRC\n" + yaml_ek).encode("utf-8"))
    for modul, pkg, dosyalar, rules in paketler:
        pd = kok / "SRC" / modul / pkg
        pd.mkdir(parents=True)
        if rules is not None:
            (pd / ".rules.md").write_bytes(rules.encode("utf-8"))
        for rel, icerik in dosyalar.items():
            f = pd / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(icerik.encode("utf-8"))
    return kok


def _rules(pkg: str, ns: str, kisa: str) -> str:
    return RULES_NS.format(pkg=pkg, ns=ns, kisa=kisa)


def _kos(proje: Path, sarm: Path | None, kip: str) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("IX_")}
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    env["PYTHONIOENCODING"] = "utf-8"
    if sarm is None:
        argv = [sys.executable, str(GATE)]
    else:
        argv = [sys.executable, str(sarm), str(SCRIPTS), kip]
    r = subprocess.run(argv, cwd=str(proje), env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def kapi_tur(tmp: Path, sarm: Path | None, kip: str) -> dict[str, tuple[bool, str, str]]:
    sonuc: dict[str, tuple[bool, str, str]] = {}
    ns_sinif = {"classes/#NSPC#CL_SD001_X.clas.abap": "x\n"}
    ns_pkg = "#NSPC#SD001"
    rules_ns = _rules(ns_pkg, "#NSPC#", "SD001")

    vakalar = [
        # (id, açıklama, paketler, yaml_ek, beklenen_rc, zorunlu_metin)
        ("A1", "KABLOLAMA satır içi istisna (.rules.md yok) → kabul",
         [("SD", ns_pkg, ns_sinif, None)],
         'package_exceptions: ["#NSPC#SD001:^#NSPC#CL_SD001_"]\n', 0, None),
        ("A2", "KABLOLAMA blok istisna + satır sonu yorumu (.rules.md yok) → kabul",
         [("SD", ns_pkg, ns_sinif, None)],
         "package_exceptions:\n  - '#NSPC#SD001:^#NSPC#CL_SD001_'   # namespace sinifi\n", 0, None),
        ("N1", "namespace paketi + .rules.md, doğru ad → kabul",
         [("SD", ns_pkg, ns_sinif, rules_ns)], "", 0, None),
        ("N2", "3.bağlam başka modül + küçük harf abapGit adı + cds .ddls.asddls → kabul",
         [("MM", "#NSPC#MM001",
           {"classes/#nspc#cl_mm001_y.clas.abap": "x\n",
            "cds/#NSPC#I_MM001_Z.ddls.asddls": "x\n"},
           _rules("#NSPC#MM001", "#NSPC#", "MM001"))], "", 0, None),
        ("S1", "KAPSAM satırı namespace yolunu anar (kabul edilen dosya: 1)",
         [("SD", ns_pkg, ns_sinif, rules_ns)], "", 0,
         "namespace'li paket: 1 (`.rules.md` Naming regex'iyle kabul edilen dosya: 1"),
        ("R1", "yanlış namespace (#XYZ#) — gevşek regex'e rağmen önek şartı reddeder",
         [("SD", ns_pkg, {"classes/#XYZ#CL_SD001_A.clas.abap": "x\n"},
           rules_ns.replace("`^#NSPC#CL_SD001_[A-Z0-9_]+$`", "`^#[A-Z]+#CL_SD001_[A-Z0-9_]+$`"))],
         "", 1, "#XYZ#CL_SD001_A.clas.abap"),
        ("R2", "tabloya uymayan ad (#NSPC#CX_…) → red",
         [("SD", ns_pkg, {"classes/#NSPC#CX_SD001_E.clas.abap": "x\n"}, rules_ns)],
         "", 1, "#NSPC#CX_SD001_E.clas.abap"),
        ("R3", ".rules.md yok → red + mesaj bunu söyler",
         [("SD", ns_pkg, ns_sinif, None)], "", 1, "Naming regex'i YOK"),
        ("R4", "Z paketi istisnasız ZCL_SD001_X → red (.rules.md regex'i uysa bile)",
         [("SD", "ZSD001", {"classes/ZCL_SD001_X.clas.abap": "x\n"},
           _rules("ZSD001", "Z", "SD001"))], "", 1, "ZCL_SD001_X.clas.abap"),
        ("R5", "derlenmeyen regex → çökme yok, kabul yok",
         [("SD", ns_pkg, ns_sinif,
           rules_ns.replace("`^#NSPC#CL_SD001_[A-Z0-9_]+$`", "`^#NSPC#CL_(`"))], "", 1,
         "#NSPC#CL_SD001_X.clas.abap"),
        ("K1", "KONTROL Z paketi ZSD001_X → kabul",
         [("SD", "ZSD001", {"classes/ZSD001_X.clas.abap": "x\n"}, None)], "", 0, None),
    ]
    for vid, aciklama, paketler, yaml_ek, b_rc, metin in vakalar:
        proje = _proje(tmp / f"{kip}_{vid}", paketler, yaml_ek)
        rc, cikti = _kos(proje, sarm, kip)
        ok = rc == b_rc and "Traceback" not in cikti and (metin is None or metin in cikti)
        sonuc[vid] = (ok, f"{vid} {aciklama}", f"rc={rc} (beklenen {b_rc}) :: {cikti.strip()[:300]}")
    return sonuc


def tur_kos(tmp: Path, sarm: Path | None, kip: str) -> dict[str, tuple[bool, str, str]]:
    sonuc = yaml_tur(tmp, kip if sarm is not None else None)
    sonuc.update(kapi_tur(tmp, sarm, kip))
    return sonuc


def yazdir(baslik: str, sonuc: dict[str, tuple[bool, str, str]]) -> int:
    print(f"── {baslik}")
    gecen = 0
    for _vid, (ok, ad, detay) in sonuc.items():
        gecen += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f" — {detay}"))
    return gecen


def main(argv: list[str]) -> int:
    kip = argv[0] if argv else None
    if kip is not None and kip not in GECERLI_KIP:
        print(f"[KULLANIM] gecersiz kip: {kip} · gecerli: {sorted(GECERLI_KIP)}")
        return 2
    if not GATE.is_file():
        print(f"[KURULAMADI] kapi yok: {GATE}")
        return 3
    tmp = Path(tempfile.mkdtemp(prefix="i391_"))
    try:
        if kip is None:
            sonuc = tur_kos(tmp, None, "gercek")
            gecen = yazdir("taban (gercek giris noktasi)", sonuc)
            print(f"\nissue391_ns_yaml_yorum: {gecen}/{len(sonuc)}")
            return 0 if gecen == len(sonuc) else 1

        kisa = KIP_KISA[kip]
        sarm = tmp / "sarmalayici.py"
        sarm.write_text(SARMALAYICI, encoding="utf-8")
        kum = tur_kos(tmp, sarm, "yok")
        k_gecen = yazdir("kum tabani (sarmalayici, YAMASIZ)", kum)
        if k_gecen != len(kum):
            print(f"\n[KURULAMADI] kum tabani yesil degil ({k_gecen}/{len(kum)}) — "
                  "mutasyon olcumu gecersiz")
            return 3
        mut = tur_kos(tmp, sarm, kisa)
        m_gecen = yazdir(f"mutasyon {kip}", mut)
        dusen = {k for k, (ok, _, _) in mut.items() if not ok}
        beklenen = BEKLENEN_DUSEN[kisa]
        print(f"\nissue391_ns_yaml_yorum: {m_gecen}/{len(mut)}")
        print(f"ILAN EDILEN: {sorted(beklenen)}")
        print(f"DUSEN:       {sorted(dusen)}")
        if any("[KURULAMADI]" in d for _, _, d in mut.values()):
            print("[KURULAMADI] sarmalayici yama noktasini bulamadi")
            return 3
        if dusen == beklenen:
            print("DUSTU — yalniz ilan edilen vektorler dustu")
            return 1
        print(f"SAPMA — fazla={sorted(dusen - beklenen)} eksik={sorted(beklenen - dusen)}")
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
