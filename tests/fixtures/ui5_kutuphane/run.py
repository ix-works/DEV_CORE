#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ui5_kutuphane fixture — UI5 reuse library kaynağını tanıyan TEK tanım + onu kullanan iki validator.

Ne ölçülür (2026-11-28):
  U  `aday_kokler`: yalnız bir `src` segmentindeki ya da altındaki ata dizinler, en yakından uzağa;
     `src`'nin üstü ve `src`'siz yol aday DEĞİL.
  D  `DiskKutuphanesi` (sabit dizin ağacı): `src/<ns>/.library` kökü bulunur (D1) · ad TAM eşleşir,
     `.Library` kök DEĞİL (D2) · `src/` dışındaki `.library` kök DEĞİL (D3) · iç içe kökte EN YAKIN (D4).
  T  `check_ui5_freestyle_traps` gerçek alt süreç (CLAUDE_PROJECT_DIR = geçici proje): kütüphane
     fragment'ındaki T4 ihlali ERROR + kapsam satırı "1 dosya" (T1) · `.library`'siz `src/` ağacı
     taranmaz (T2 NEGATİF) · E0: önyükleyici ↔ doğrudan `python <validator>` aynı çıktı.
  F  `check_filter_search_pattern`: `ui/` DIŞINDAKİ kütüphane JS'indeki `caseSensitive:false` BLOCKER
     (F1) · `.library`'siz, `ui/`'siz JS taranmaz (F2 NEGATİF).
D2'nin mutasyon kipi BİLEREK yok: `os.listdir` ↔ `Path.exists` farkı yalnız harf duyarsız dosya
sisteminde (Windows/macOS) gözlenir; Linux CI'da mutant tabanla aynı davranır (KACTI sayılırdı). D2
vektörü Windows'ta koruma, Linux'ta eşdeğerlik kontrolüdür.
Kütüphane kararı fixture'da test edilen fonksiyonla ÜRETİLMEZ — ağaç elle kurulur.

Mutasyon kipleri (kaynak METNİ değiştirilir; alt süreçte önyükleyici mutant modülü gerçek `__file__`
ile çalıştırır — mutant hiçbir zaman diske, repo içine yazılmaz):
  --mutasyon-src            `src` segmenti şartı kalkar (her ata aday)
  --mutasyon-traps          check_ui5_freestyle_traps kütüphane dalını yok sayar (yalnız `webapp`)
  --mutasyon-filter         check_filter_search_pattern kütüphane dalını yok sayar (yalnız `ui/`)
Çıkış: 0 taban yeşil · 1 mutasyon BEKLENEN kümeyle düştü · 2 SAPMA · 3 DOGRULANAMADI.
Koşum: python tests/fixtures/ui5_kutuphane/run.py [--mutasyon-...]
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "scripts"
YARDIMCI = SCRIPTS / "utils" / "ui5_kutuphane.py"
TRAPS = SCRIPTS / "validators" / "check_ui5_freestyle_traps.py"
FILTRE = SCRIPTS / "validators" / "check_filter_search_pattern.py"

_MUT = {
    "--mutasyon-src": (YARDIMCI, "if KUTUPHANE_KAYNAK in p[:i]]", "if True]"),
    "--mutasyon-traps": (TRAPS, '        if "webapp" not in parts and not lib:', '        if "webapp" not in parts:'),
    "--mutasyon-filter": (FILTRE, '            if "ui" not in Path(dirpath).parts and not lib:',
                          '            if "ui" not in Path(dirpath).parts:'),
}

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


def yaz(kok: Path, dosyalar: dict[str, str]) -> None:
    for rel, icerik in dosyalar.items():
        p = kok / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(icerik.encode("utf-8"))


# Önyükleyici: (isteğe bağlı) mutant yardımcıyı `utils.ui5_kutuphane` olarak yerleştirir, sonra validatör
# kaynağını gerçek `__file__` ile `__main__` olarak çalıştırır. Kaynaklar JSON ile verilir (diske mutant yok).
ONYUKLEYICI = r'''
import json, sys, types
v = json.loads(sys.stdin.read())
sys.path.insert(0, v["scripts"])
sys.argv = [v["dosya"]]
if v.get("yardimci"):
    import utils
    m = types.ModuleType("utils.ui5_kutuphane"); m.__file__ = v["yardimci_dosya"]
    sys.modules["utils.ui5_kutuphane"] = m; utils.ui5_kutuphane = m
    exec(compile(v["yardimci"], v["yardimci_dosya"], "exec"), m.__dict__)
g = {"__name__": "__main__", "__file__": v["dosya"]}
exec(compile(v["kaynak"], v["dosya"], "exec"), g)
'''


def kos(proje: Path, hedef: Path, kaynaklar: dict[Path, str], dogrudan: bool = False) -> tuple[int, str]:
    env = {k: x for k, x in os.environ.items() if k != "CLAUDE_PROJECT_DIR" and not k.startswith("IX_")}
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    env["PYTHONIOENCODING"] = "utf-8"
    if dogrudan:
        r = subprocess.run([sys.executable, str(hedef)], cwd=str(proje), env=env, capture_output=True)
    else:
        girdi = {"scripts": str(SCRIPTS), "dosya": str(hedef), "kaynak": kaynaklar[hedef],
                 "yardimci": kaynaklar.get(YARDIMCI) if kaynaklar.get("_yardimci_mutant") else None,
                 "yardimci_dosya": str(YARDIMCI)}
        r = subprocess.run([sys.executable, "-c", ONYUKLEYICI], cwd=str(proje), env=env, capture_output=True,
                           input=json.dumps(girdi).encode("utf-8"))
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")


def yardimci_modulu(kaynak: str) -> types.ModuleType:
    m = types.ModuleType("_ui5_kutuphane_fx")
    m.__file__ = str(YARDIMCI)
    exec(compile(kaynak, str(YARDIMCI), "exec"), m.__dict__)
    return m


LIB_TANIM = '<?xml version="1.0" encoding="UTF-8" ?>\n<library xmlns="http://www.sap.com/sap.ui.library.xsd">\n  <name>com.acme.ortak</name>\n</library>\n'
T4_KIRLI = ('<core:FragmentDefinition xmlns="sap.m" xmlns:core="sap.ui.core" xmlns:f="sap.ui.layout.form">\n'
            '  <f:Form><f:formContainers><f:FormContainer><f:formElements><f:FormElement>\n'
            '    <f:fields>\n      <HBox><Input/></HBox>\n    </f:fields>\n'
            '  </f:FormElement></f:formElements></f:FormContainer></f:formContainers></f:Form>\n'
            '</core:FragmentDefinition>\n')
CS_KIRLI = 'sap.ui.define([], function () {\n  return new Filter({ path: "A", caseSensitive: false });\n});\n'


def u_vektorleri(Y) -> None:
    kontrol("U1 `a/src/com/x/util/X.js` adayları en yakından uzağa `a/src`'ye kadar, `a` hariç",
            Y.aday_kokler("a/src/com/x/util/X.js") == ["a/src/com/x/util", "a/src/com/x", "a/src/com", "a/src"],
            repr(Y.aday_kokler("a/src/com/x/util/X.js")))
    kontrol("U2 `a/src/X.js` (doğrudan src altı) tek aday `a/src` (deploy_ui kahini)", Y.aday_kokler("a/src/X.js") == ["a/src"],
            repr(Y.aday_kokler("a/src/X.js")))
    kontrol("U3 `src`'siz yol aday YOK", Y.aday_kokler("a/com/x/util/X.js") == [],
            repr(Y.aday_kokler("a/com/x/util/X.js")))


def d_vektorleri(Y, tmp: Path) -> None:
    kok = tmp / "disk"
    yaz(kok, {"p/src/com/acme/ortak/.library": LIB_TANIM, "p/src/com/acme/ortak/util/X.js": "x\n",
              "q/src/com/acme/b/.Library": LIB_TANIM, "q/src/com/acme/b/util/X.js": "x\n",
              "r/com/acme/c/.library": LIB_TANIM, "r/com/acme/c/util/X.js": "x\n",
              "s/src/com/acme/.library": LIB_TANIM, "s/src/com/acme/ic/.library": LIB_TANIM,
              "s/src/com/acme/ic/util/X.js": "x\n"})
    lib = Y.DiskKutuphanesi(kok)
    k = lib.kok(kok / "p/src/com/acme/ortak/util/X.js")
    kontrol("D1 `src/<ns>/.library` kökü bulunur", k == "p/src/com/acme/ortak", repr(k))
    k = lib.kok(kok / "q/src/com/acme/b/util/X.js")
    kontrol("D2 NEGATİF: `.Library` (büyük harf) kök DEĞİL — ad tam eşleşir", k is None, repr(k))
    k = lib.kok(kok / "r/com/acme/c/util/X.js")
    kontrol("D3 NEGATİF: `src/` dışındaki `.library` kök DEĞİL", k is None, repr(k))
    k = lib.kok(kok / "s/src/com/acme/ic/util/X.js")
    kontrol("D4 iç içe `.library`: EN YAKIN kök", k == "s/src/com/acme/ic", repr(k))


def t_f_vektorleri(kaynaklar: dict, tmp: Path) -> None:
    kutup = "SOURCE_CODES/PKG/lib/src/com/acme/ortak"
    p1 = tmp / "t1"
    yaz(p1, {f"{kutup}/.library": LIB_TANIM, f"{kutup}/fragment/F.fragment.xml": T4_KIRLI})
    rc, out = kos(p1, TRAPS, kaynaklar)
    kontrol("T1 traps: kütüphane fragment'ındaki T4 → ERROR rc 1 + kapsam 'kütüphane … 1 dosya'",
            rc == 1 and "T4 <f:fields>" in out and "kökü): 1 dosya" in out, f"rc={rc} {out[-200:]!r}")
    rc2, out2 = kos(p1, TRAPS, kaynaklar, dogrudan=True)
    kontrol("E0 önyükleyici ↔ doğrudan `python <validator>` aynı rc ve çıktı (mutasyonsuz kipte)",
            bool(kaynaklar.get("_mutasyonsuz")) is False or (rc2 == rc and out2 == out),
            f"rc {rc}/{rc2}")
    p2 = tmp / "t2"
    yaz(p2, {"SOURCE_CODES/PKG/tool/src/com/acme/fragment/F.fragment.xml": T4_KIRLI})
    rc, out = kos(p2, TRAPS, kaynaklar)
    kontrol("T2 NEGATİF traps: `.library`'siz `src/` ağacı taranmaz (rc 0, kütüphane 0 dosya)",
            rc == 0 and "[İHLAL]" not in out and "kökü): 0 dosya" in out, f"rc={rc} {out[-200:]!r}")
    p3 = tmp / "f1"
    yaz(p3, {f"{kutup}/.library": LIB_TANIM, f"{kutup}/util/A.js": CS_KIRLI})
    rc, out = kos(p3, FILTRE, kaynaklar)
    kontrol("F1 filter: `ui/` DIŞINDAKİ kütüphane JS'inde caseSensitive:false → BLOCKER rc 1 + 1 JS",
            rc == 1 and "caseSensitive:false" in out and "kökü): 1 JS" in out, f"rc={rc} {out[-200:]!r}")
    p4 = tmp / "f2"
    yaz(p4, {"SOURCE_CODES/PKG/tool/src/com/acme/util/A.js": CS_KIRLI})
    rc, out = kos(p4, FILTRE, kaynaklar)
    kontrol("F2 NEGATİF filter: `.library`'siz, `ui/`'siz JS taranmaz (rc 0, 0 JS)",
            rc == 0 and "[İHLAL]" not in out and "kökü): 0 JS" in out, f"rc={rc} {out[-200:]!r}")


def harf_duyarsiz_fs(tmp: Path) -> bool:
    (tmp / "_sonda").write_bytes(b"")
    return (tmp / "_SONDA").exists()


def main(kip: str | None) -> int:
    kaynaklar: dict = {p: p.read_bytes().decode("utf-8") for p in (YARDIMCI, TRAPS, FILTRE)}
    kaynaklar["_mutasyonsuz"] = kip is None
    if kip:
        hedef, eski, yeni = _MUT[kip]
        n = kaynaklar[hedef].count(eski)
        if n != 1:
            sys.stderr.write(f"[DOGRULANAMADI] mutasyon capasi {n} kez eslesti (beklenen 1): {kip}\n")
            return 3
        kaynaklar[hedef] = kaynaklar[hedef].replace(eski, yeni, 1)
        try:
            compile(kaynaklar[hedef], str(hedef), "exec")
        except SyntaxError as e:
            sys.stderr.write(f"[DOGRULANAMADI] mutant DERLENMEDI ({kip}): {e}\n")
            return 3
        kaynaklar["_yardimci_mutant"] = hedef == YARDIMCI
        print("mutasyon:", kip)
    tmp = Path(tempfile.mkdtemp(prefix="ui5kut_fx_"))
    try:
        duyarsiz = harf_duyarsiz_fs(tmp)
        Y = yardimci_modulu(kaynaklar[YARDIMCI])
        u_vektorleri(Y)
        d_vektorleri(Y, tmp)
        t_f_vektorleri(kaynaklar, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    beklenen_tum = {
        "--mutasyon-src": {"U1", "U2", "U3", "D3"},
        "--mutasyon-traps": {"T1"},
        "--mutasyon-filter": {"F1"},
    }
    hata = 0
    for ad, ok, detay in SONUC:
        hata += 0 if ok else 1
        print("[%s] %-90s %s" % ("ok" if ok else "FAIL", ad, "" if ok else detay))
    print("%d/%d OK · dosya sistemi harf %s" % (len(SONUC) - hata, len(SONUC), "DUYARSIZ" if duyarsiz else "duyarlı"))
    if kip:
        dusen = {ad.split()[0] for ad, ok, _ in SONUC if not ok}
        beklenen = beklenen_tum[kip]
        if dusen != beklenen:
            print("[SAPMA] %s: beklenen=%s dusen=%s -> exit 2" % (kip, sorted(beklenen), sorted(dusen)))
            return 2
        print("[BEKLENEN] %s: dusen kume = beklenen %s" % (kip, sorted(beklenen)))
        return 1
    return 1 if hata else 0


if __name__ == "__main__":
    kip = None
    for _a in sys.argv[1:]:
        if _a.startswith("--mutasyon"):
            if _a not in _MUT:
                print("[KULLANIM] bilinmeyen mutasyon kipi: %s · gecerli: %s" % (_a, ", ".join(sorted(_MUT))))
                sys.exit(3)
            kip = _a
    sys.exit(main(kip))
