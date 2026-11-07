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
      Y13 iki tırnaklı öğe, Y14 çift tırnakta kaçışlı tırnak (`"x\\" # y"`). KONTROL (eski kodda da yeşil, değişmemeli): Y4 tüketici biçimi
      `- "ZSD001_CLC:^ZCL_SD001_"   # açıklama` · Y5 tırnaksız `#` keser · Y6 kelime içi kesme
      işareti tırnak sayılmaz · Y7 kapanmamış tırnak → eski kesim · Y10 Z satır içi · Y12 tüm dosya
      · Y15 iki kelime içi kesme işareti arasında `#` (`Paket'in # Ali'nin`) · Y16 değer ortasında
      `-'` (`a-'b#c'`) · Y17 akış listesi DIŞINDA `,'` (`a,'b # c'`) — üçü de eski kesimle AYNI sonuç.
  A*  KABLOLAMA (gerçek giriş noktası, alt süreç): `.rules.md`'siz namespace paketi, istisna
      `project.yaml`'dan — A1 satır içi, A2 blok. (b) olmadan istisna bozulur → ihlal.
  N*  (a) kabul: N1 `.rules.md`'li namespace paketi doğru ad · N2 3. bağlam (başka modül, küçük harfli
      abapGit dosya adı, `cds/` altında `.ddls.asddls`) · N3 küçük harfli PAKET KLASÖRÜ `#nspc#sd001`
      · S1 KAPSAM satırı namespace yolunu anar. ⚠ N2 yalnız BU kapı için geçerlidir: bu kapı adı
      `.upper()` ile regex'e uygular, `check_package_naming` olduğu gibi — küçük harfli abapGit adı +
      büyük harfli regex'te naming kapısı reddeder (bu fixture onu ölçmez).
  R*  (a) red (fail-closed): R1 yanlış namespace — `.rules.md` regex'i namespace'e GEVŞEK yazılmış
      olsa bile önek şartı reddeder · R2 tabloya uymayan ad · R3 `.rules.md` yok (mesaj bunu söyler)
      · R4 Z paketi istisnasız `ZCL_SD001_X` (`.rules.md` regex'i uysa bile — Z davranışı DEĞİŞMEDİ)
      · R5 derlenmeyen regex çökme üretmez, kabul üretmez. K1 Z kontrol grubu `ZSD001_X` kabul.

Koşum:     python tests/fixtures/issue391_ns_yaml_yorum/run.py
MUTASYON (önce aynı sarmalayıcı YAMASIZ koşulur — kum tabanı tam yeşil olmalı). Her kip kaynak
  METNİNE tekil bir ikame uygular (çapa tam 1 kez bulunmazsa exit 3); süreç içi Y* vektörleri ve
  alt süreç kapısı AYNI ikameli kaynağı yükler.
  --mutasyon-yorum-kesimi      `_yorumu_ayikla(ham)` → eski `ham.split("#", 1)[0]`
                               İLAN: {Y1, Y2, Y3, Y8, Y9, Y11, Y13, Y14, A1, A2}
  --mutasyon-tirnak-kapisi-yok her `'`/`"` tırnak açar (değer başı şartı yok)
                               İLAN: {Y15, Y16, Y17}
  --mutasyon-kacis-yok         çift tırnakta `\\` kaçış dalı kapalı          İLAN: {Y14}
  --mutasyon-virgul-akis-disi  `,` akış listesi DIŞINDA da değer başı sayılır   İLAN: {Y17}
  --mutasyon-tire-her-yerde    `-` satır başı dışında da blok öğesi sayılır    İLAN: {Y16}
  --mutasyon-ns-kapali         `ns_kur = namespace_kurallari(pkg)` → `[]`       İLAN: {N1, N2, N3, S1}
  --mutasyon-ns-onek-yok       `matches_package` içindeki `and base.startswith(ns)` silinir
                               İLAN: {R1}
  --mutasyon-ns-buyuk-harf-yok `paket_namespace` içinde `.upper()` kaldırılır   İLAN: {N3}
  Çıkış: 0 taban yeşil · 1 taban kırmızı YA DA yalnız ilan edilen küme düştü · 2 SAPMA ya da
  geçersiz kip · 3 kurulamadı (yama noktası yok / kum tabanı kırmızı).
Kontrol grubu: `I391_SCRIPTS_KOK=<scripts dizini>` ile başka bir sürüm koşulabilir (düzeltme öncesi
  kod `f646f36`: Y1 Y2 Y3 Y8 Y9 Y11 Y13 Y14 A1 A2 N1 N2 N3 S1 R3 FAIL — 14/29; R3 eski kodda da
  rc 1 verir ama namespace mesajı yoktur. İlk düzeltme `4029212` (tırnak "önceki boşluk dışı karakter
  `:` `-` `[` `,`" kuralıyla açılıyordu): Y16 Y17 FAIL — 27/29. İkisi 2026-11-07 ölçüldü). Kontrol grubu kurulurken `utils/` ve `validators/` aynı
  sürümden kopyalanır.
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

PC_REL = "utils/project_config.py"
GATE_REL = "validators/check_object_in_correct_pkg.py"

# kip → (ilan edilen düşen küme, [(göreli dosya, eski metin, yeni metin), ...])
MUTASYONLAR: dict[str, tuple[set[str], list[tuple[str, str, str]]]] = {
    "--mutasyon-yorum-kesimi": (
        {"Y1", "Y2", "Y3", "Y8", "Y9", "Y11", "Y13", "Y14", "A1", "A2"},
        [(PC_REL, "s = _yorumu_ayikla(ham).rstrip()", 's = ham.split("#", 1)[0].rstrip()')]),
    "--mutasyon-tirnak-kapisi-yok": (
        {"Y15", "Y16", "Y17"},
        [(PC_REL, "if bekle and c in (\"'\", '\"'):", "if c in (\"'\", '\"'):")]),
    "--mutasyon-kacis-yok": (
        {"Y14"},
        [(PC_REL, 'if c == "' + chr(92) * 2 + '":', "if False:")]),
    "--mutasyon-virgul-akis-disi": (
        {"Y17"},
        [(PC_REL, 'elif c == "," and derinlik > 0:', 'elif c == ",":')]),
    "--mutasyon-tire-her-yerde": (
        {"Y16"},
        [(PC_REL, 'elif c == "-" and satir_basi and (sonraki == "" or sonraki.isspace()):',
          'elif c == "-":')]),
    "--mutasyon-ns-kapali": (
        {"N1", "N2", "N3", "S1"},
        [(GATE_REL, "ns_kur = namespace_kurallari(pkg)", "ns_kur = []")]),
    "--mutasyon-ns-onek-yok": (
        {"R1"},
        [(GATE_REL, " and base.startswith(ns):", ":")]),
    "--mutasyon-ns-buyuk-harf-yok": (
        {"N3"},
        [(GATE_REL, "_NS_RE.match(pkg_name.upper())", "_NS_RE.match(pkg_name)")]),
}
GECERLI_KIP = set(MUTASYONLAR)


class Kurulamadi(Exception):
    pass


def ikameli_kaynak(rel: str, ikameler: list[tuple[str, str, str]]) -> str:
    """`SCRIPTS/rel` kaynağı + bu dosyaya düşen ikameler (her çapa TAM 1 kez)."""
    metin = (SCRIPTS / rel).read_text(encoding="utf-8")
    for dosya, eski, yeni in ikameler:
        if dosya != rel:
            continue
        n = metin.count(eski)
        if n != 1:
            raise Kurulamadi(f"çapa {rel} içinde {n} kez (1 olmalı): {eski!r}")
        metin = metin.replace(eski, yeni)
    return metin


SARMALAYICI = r'''
import json, os, sys, types
scripts, ikame_yolu = sys.argv[1], sys.argv[2]
with open(ikame_yolu, encoding="utf-8") as fh:
    kaynaklar = json.load(fh)          # {göreli dosya: ikameli kaynak}
sys.path.insert(0, scripts)
sys.path.insert(0, os.path.join(scripts, "validators"))
import utils                            # gerçek paket; alt modül ikameli kaynaktan kurulur
pc_yol = os.path.join(scripts, "utils", "project_config.py")
pc = types.ModuleType("utils.project_config")
pc.__file__ = pc_yol
sys.modules["utils.project_config"] = pc
utils.project_config = pc
exec(compile(kaynaklar["utils/project_config.py"], pc_yol, "exec"), pc.__dict__)
gate = os.path.join(scripts, "validators", "check_object_in_correct_pkg.py")
mod = types.ModuleType("check_object_in_correct_pkg")
mod.__file__ = gate
exec(compile(kaynaklar["validators/check_object_in_correct_pkg.py"], gate, "exec"), mod.__dict__)
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
    ("Y14", False, 'a: "x\\" # y" # z\n', "a", 'x\\" # y', "çift tırnakta kaçışlı tırnak + `#`"),
    ("Y15", True, "baslik: Paket'in # Ali'nin\n", "baslik", "Paket'in",
     "KONTROL iki kelime içi kesme işareti arasında `#` yorumdur"),
    ("Y16", True, "t: a-'b#c'\n", "t", "a-'b", "KONTROL değer ortasında `-'` tırnak açmaz"),
    ("Y17", True, "t: a,'b # c'\n", "t", "a,'b", "KONTROL akış listesi dışında `,'` tırnak açmaz"),
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


def _pc(ikameler: list[tuple[str, str, str]] | None):
    """None → gerçek import (taban). Liste → ikameli kaynaktan taze modül (kum/mutasyon)."""
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    if ikameler is None:
        from utils import project_config as pc  # type: ignore
        return pc
    import types
    pc = types.ModuleType("i391_pc")
    pc.__file__ = str(SCRIPTS / PC_REL)
    exec(compile(ikameli_kaynak(PC_REL, ikameler), pc.__file__, "exec"), pc.__dict__)
    return pc


def yaml_tur(tmp: Path, ikameler: list[tuple[str, str, str]] | None) -> dict[str, tuple[bool, str, str]]:
    pc = _pc(ikameler)
    sonuc: dict[str, tuple[bool, str, str]] = {}
    try:
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


def _kos(proje: Path, sarm: Path | None, ikame_yolu: Path | None) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("IX_")}
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    env["PYTHONIOENCODING"] = "utf-8"
    if sarm is None:
        argv = [sys.executable, str(GATE)]
    else:
        argv = [sys.executable, str(sarm), str(SCRIPTS), str(ikame_yolu)]
    r = subprocess.run(argv, cwd=str(proje), env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def kapi_tur(tmp: Path, sarm: Path | None, kip: str,
             ikame_yolu: Path | None) -> dict[str, tuple[bool, str, str]]:
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
        ("N3", "küçük harfli PAKET KLASÖRÜ #nspc#sd001 + büyük harfli regex → kabul",
         [("SD", "#nspc#sd001", ns_sinif, rules_ns)], "", 0, None),
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
        rc, cikti = _kos(proje, sarm, ikame_yolu)
        ok = rc == b_rc and "Traceback" not in cikti and (metin is None or metin in cikti)
        sonuc[vid] = (ok, f"{vid} {aciklama}", f"rc={rc} (beklenen {b_rc}) :: {cikti.strip()[:300]}")
    return sonuc


def tur_kos(tmp: Path, sarm: Path | None, etiket: str,
            ikameler: list[tuple[str, str, str]] | None) -> dict[str, tuple[bool, str, str]]:
    ikame_yolu = None
    if sarm is not None:
        import json
        ikame_yolu = tmp / f"ikame_{etiket}.json"
        ikame_yolu.write_text(json.dumps({r: ikameli_kaynak(r, ikameler or [])
                                          for r in (PC_REL, GATE_REL)}), encoding="utf-8")
    sonuc = yaml_tur(tmp, ikameler if sarm is not None else None)
    sonuc.update(kapi_tur(tmp, sarm, etiket, ikame_yolu))
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
            sonuc = tur_kos(tmp, None, "gercek", None)
            gecen = yazdir("taban (gercek giris noktasi)", sonuc)
            print(f"\nissue391_ns_yaml_yorum: {gecen}/{len(sonuc)}")
            return 0 if gecen == len(sonuc) else 1

        beklenen, ikameler = MUTASYONLAR[kip]
        sarm = tmp / "sarmalayici.py"
        sarm.write_text(SARMALAYICI, encoding="utf-8")
        try:
            kum = tur_kos(tmp, sarm, "kum", [])
        except Kurulamadi as e:
            print(f"[KURULAMADI] {e}")
            return 3
        k_gecen = yazdir("kum tabani (sarmalayici, YAMASIZ)", kum)
        if k_gecen != len(kum):
            print(f"\n[KURULAMADI] kum tabani yesil degil ({k_gecen}/{len(kum)}) — "
                  "mutasyon olcumu gecersiz")
            return 3
        try:
            mut = tur_kos(tmp, sarm, "mut", ikameler)
        except Kurulamadi as e:
            print(f"[KURULAMADI] {e}")
            return 3
        m_gecen = yazdir(f"mutasyon {kip}", mut)
        dusen = {k for k, (ok, _, _) in mut.items() if not ok}
        print(f"\nissue391_ns_yaml_yorum: {m_gecen}/{len(mut)}")
        print(f"ILAN EDILEN: {sorted(beklenen)}")
        print(f"DUSEN:       {sorted(dusen)}")
        if dusen == beklenen:
            print("DUSTU — yalniz ilan edilen vektorler dustu")
            return 1
        print(f"SAPMA — fazla={sorted(dusen - beklenen)} eksik={sorted(beklenen - dusen)}")
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
