#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pbe_kapsam — PULL-BEFORE-EDIT (ADR 0016) kapsam boşlukları (Q352, 2026-09-26).

SINIF: kapı (`hooks/pull_before_edit.py`) ile çekici (`sap_sync_pull.py`) bir dosyanın
"bu seansta canlıdan çekildi" bilgisini paylaşır. İki ayrı kusur aynı sonucu veriyordu —
canlıdaki değişiklik bayat yerel kopya üzerinden SESSİZCE ezilebiliyordu:

  A) DAMGA ADA yazılıyordu: ana sınıf çekilince hiç okunmamış `.ccimp/.ccau` da, DDLS
     çekilince aynı adlı BDEF de "taze" sayılıyordu. Ayrıca kapı sınıf alt-include'larını
     "ana sınıfla gelir" diye muaf tutuyordu (gelmiyordu).
  B) TİP ÇIKARIMI adan tahmin ediyordu: `.abap`→class, `.prog.abap`→program; include,
     yapı (`.ddls.asddls`), FM (`.func.abap`) yanlış uca yönleniyordu (404). Z tablo
     (`.tabl.ddl`/`.tabl`) kapsamda hiç yoktu.

DÜZELTME: damga = DOSYA (`source_drift.tazelik_anahtari`, yazan ve okuyan AYNI fonksiyon);
alt-include'lar kendi ucundan çekilir; tipi kesin olmayan dosyada `--type auto` (canlı ADT
araması, tam ad + dosya ailesi; 0/>1 aday → DUR).

KOŞUM ORTAMI: gerçek `scripts/` alt kümesi geçici bir KUMA kopyalanır (mutasyon kopyaya
uygulanır, canlı ağaç DOKUNULMAZ), sahte proje (git + project.yaml) kurulur. Kapı GERÇEK
giriş noktasından (stdin JSON, alt süreç) koşar; damgayı yazan GERÇEK `sap_sync_pull`dur
(`--offline` ya da sahte ADT istemcisiyle `main()`). SAP'ye bağlanılmaz; `.conn_adt` okunmaz.

  H*  kapı: alt-include · git-dirty · yeni dosya · parse-fail · muaf klasör · sınıflandırma yok
  T*  kapı: tip önerisi (auto) · aynı adlı DDLS/BDEF ayrımı · KONTROL (bugün çalışan tipler)
  P*  çekici: sınıf + alt-include'lar · auto çözümü (tek/çok/sıfır aday) · uçtan uca kapı
  X*  3. bağlam: farklı `source_root` adlı proje
  E*  EKLENTİ ARAYÜZÜ (Q352 dondurma): `_EK_DENETCILER` + `sinifla()` sözleşmesi (geçici
      `_pbe_ui` / `_pbe_msag_textpool` STUB'ı) + public `tazelik_damgala` / `seans_kimligi`

Kipler (her biri düzeltmenin bir ayağını geri alır → korpus KIRMIZI olmalı):
  --mutasyon-ad-anahtari   tazelik anahtarı eski hâline (obje ADI) döner
  --mutasyon-include-muaf  kapı alt-include'u yine muaf tutar
  --mutasyon-abap-class    `.abap` ailesi yine `--type class` önerir (auto yok)
  --mutasyon-tabl-yok      `.tabl.ddl/.tabl` kapsamdan düşer
  --mutasyon-eklenti-yok   kapı eklenti kaydına hiç sormaz (arayüz kablolanmamış)

Koşum: python tests/fixtures/pbe_kapsam/run.py [--mutasyon-…]   (exit 0 = PASS)
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
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SCRIPTS = CORE / "scripts"
SID = "fx-pbe-kapsam"

GECERLI_KIP = {"--mutasyon-ad-anahtari", "--mutasyon-include-muaf",
               "--mutasyon-abap-class", "--mutasyon-tabl-yok",
               "--mutasyon-eklenti-yok"}

# kip -> [(kopyadaki dosya, eski metin, yeni metin)]  — eski metin kopyada TAM 1 kez geçmeli
MUTASYONLAR = {
    "--mutasyon-ad-anahtari": [(
        "source_drift.py",
        "    return rel.as_posix().upper()\n",
        "    return Path(path).name.split('.', 1)[0].upper()\n")],
    "--mutasyon-include-muaf": [(
        "hooks/pull_before_edit.py",
        "    if not s:\n        return 0                       # SAP source değil → gate yok\n",
        "    if not s or s.get('tur') == 'sinif_include':\n        return 0\n")],
    # eski `_infer_type`: `.prog.abap`->program, diğer `.abap`->class (adan tahmin)
    "--mutasyon-abap-class": [(
        "source_drift.py",
        '    (".clas.abap", "class"),\n',
        '    (".clas.abap", "class"),\n    (".prog.abap", "program"),\n    (".abap", "class"),\n')],
    "--mutasyon-eklenti-yok": [(
        "hooks/pull_before_edit.py",
        "        s = _ek_sinifla(p)",
        "        s = None")],
    "--mutasyon-tabl-yok": [(
        "source_drift.py",
        '    (".tabl.ddl", "ddl"), (".tabl", "ddl"),\n',
        "")],
}

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


def _sil(d: Path) -> None:
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


def kopya_kur(kum: Path, kip: str | None) -> Path:
    """Gerçek `scripts/` alt kümesini kuma kopyalar (import kökü taşınır) + mutasyonu uygular."""
    hedef = kum / "core" / "scripts"
    (hedef / "hooks").mkdir(parents=True)
    for ad in ("source_drift.py", "object_types.py", "sap_sync_pull.py", "sap_adt_lib.py"):
        shutil.copy2(SCRIPTS / ad, hedef / ad)
    shutil.copy2(SCRIPTS / "hooks" / "pull_before_edit.py", hedef / "hooks" / "pull_before_edit.py")
    shutil.copytree(SCRIPTS / "utils", hedef / "utils",
                    ignore=shutil.ignore_patterns("__pycache__"))
    for rel, eski, yeni in MUTASYONLAR.get(kip or "", []):
        yol = hedef / rel
        metin = yol.read_text(encoding="utf-8")
        if metin.count(eski) != 1:
            print(f"[KURULAMADI] mutasyon yamasi kaynaga UYMADI ({kip}: {rel}, "
                  f"esleme={metin.count(eski)}) — sahte-yesil riski, SAYI RAPORLANMIYOR")
            raise SystemExit(3)
        yol.write_text(metin.replace(eski, yeni), encoding="utf-8", newline="\n")
    return hedef


DOSYALAR = {
    # sınıf + alt-include'lar (ADT ve abapGit adlandırması)
    "SD/ZSD001_CLC/classes/ZCL_SD001_X.clas.abap": "CLASS zcl_sd001_x DEFINITION.\n",
    "SD/ZSD001_CLC/classes/ZCL_SD001_X.ccimp.abap": "* yerel impl v1\n",
    "SD/ZSD001_CLC/classes/ZCL_SD001_X.ccau.abap": "* test v1\n",
    "SD/ZSD001_CLC/classes/ZCL_SD001_Y.clas.locals_imp.abap": "* abapgit impl\n",
    # program / include / FM (tip dosya adından kesin DEĞİL)
    "SD/ZSD001_CLC/programs/ZSD001_P_X.prog.abap": "REPORT zsd001_p_x.\n",
    "SD/ZSD001_CLC/programs/includes/ZSD001_I_X_TOP.prog.abap": "* top v1\n",
    "SD/ZSD001_CLC/programs/ZSD001_I_Y.abap": "* duz abap include\n",
    "SD/ZSD001_CLC/functions/ZSD001_FM_X.func.abap": "FUNCTION zsd001_fm_x.\n",
    # DDL ailesi: yapı + CDS (aynı adlı BDEF ile) + tablo
    "SD/ZSD001_CLC/structures/ZSD001_S_X.ddls.asddls": "define structure zsd001_s_x {\n",
    "SD/ZSD001_CLC/cds/ZSD001_I_X.cds": "define view entity ZSD001_I_X as select from x\n",
    "SD/ZSD001_CLC/cds/ZSD001_I_X.bdef": "managed implementation in class zbp;\n",
    "SD/ZSD001_CLC/tables/ZSD001_T_X.tabl.ddl": "define table zsd001_t_x {\n",
    "SD/ZSD001_CLC/tables/ZSD001_T_Y.tabl": "define table zsd001_t_y {\n",
    # muaf / kapsam dışı
    "SD/ZSD001_CLC/ref_docs/ZCL_SD001_X.ccimp.abap": "* referans\n",
    "SD/ZSD001_CLC/NOTLAR.md": "not\n",
    # eklenti arayüzü (E*): çekirdek sınıflandırmanın TANIMADIĞI dosyalar
    "SD/ZSD001_CLC/ui/webapp/Component.js": "sap.ui.define([], function () {});\n",
    "SD/ZSD001_CLC/ui/webapp/view/Main.view.xml": "<mvc:View/>\n",
}


def proje_kur(kok: Path, source_root: str = "SOURCE_CODES") -> Path:
    kok.mkdir(parents=True)
    (kok / "project.yaml").write_text(f"source_root: {source_root}\n", encoding="utf-8")
    (kok / ".claude").mkdir()
    for rel, govde in DOSYALAR.items():
        p = kok / source_root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(govde.encode("utf-8"))
    for c in (["init", "-q"], ["config", "user.email", "fx"],
              ["config", "user.name", "fx"], ["config", "core.autocrlf", "false"],
              ["add", "-A"], ["commit", "-q", "-m", "taban"]):
        subprocess.run(["git", "-C", str(kok), *c], check=True, capture_output=True)
    return kok


def _env(proje: Path) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("IX_") and k not in ("CLAUDE_CWD", "INIT_CWD", "COPILOT_CWD", "PWD")}
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def kapi(scripts: Path, proje: Path, dosya: Path | str, govde: bytes | None = None,
         sid: str = SID) -> tuple[int, str]:
    if govde is None:
        govde = json.dumps({"tool_name": "Edit", "session_id": sid,
                            "tool_input": {"file_path": str(dosya)}}).encode("utf-8")
    r = subprocess.run([sys.executable, str(scripts / "hooks" / "pull_before_edit.py")],
                       input=govde, capture_output=True, env=_env(proje), cwd=str(proje),
                       timeout=60)
    return r.returncode, r.stderr.decode("utf-8", errors="replace")


def cekici(scripts: Path, proje: Path, *arg: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(scripts / "sap_sync_pull.py"), *arg,
                        "--session", SID], capture_output=True, env=_env(proje),
                       cwd=str(proje), timeout=120)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", errors="replace")


# Sahte ADT istemcisiyle `sap_sync_pull.main()` (ağ YOK). Canlı uçlar URL -> gövde;
# listede olmayan uç 404 (SAPObjectNotFoundError) — gerçek istemcinin sözleşmesi.
_SAHTE = r'''
import json, sys, types
sys.path.insert(0, {scripts!r})
CANLI = json.loads({canli!r})
ARAMA = {arama!r}
class _ADT:
    def get_object_source(self, url, return_etag=False, version=None):
        from object_types import ensure_source_url
        u = ensure_source_url(url)
        if u in CANLI:
            return CANLI[u]
        import sap_adt_lib as L
        raise L.SAPObjectNotFoundError(message="Object not found", status_code=404, endpoint=u)
    def search_objects(self, query, max_results=50, obj_type=None):
        return ARAMA
class SAPClient:
    def __init__(self):
        self.adt_client = _ADT()
m = types.ModuleType("sap_client"); m.SAPClient = SAPClient; sys.modules["sap_client"] = m
import sap_sync_pull as S
sys.argv = ["sap_sync_pull.py"] + json.loads({argv!r})
rc = S.main()
print("RC=%s" % rc)
'''


def _arama_xml(*kayit: tuple[str, str, str]) -> str:
    ic = "".join(f'<adtcore:objectReference adtcore:uri="{u}" adtcore:type="{t}" '
                 f'adtcore:name="{n}"/>' for u, t, n in kayit)
    return ('<?xml version="1.0" encoding="utf-8"?><adtcore:objectReferences '
            'xmlns:adtcore="http://www.sap.com/adt/core">' + ic + '</adtcore:objectReferences>')


def cekici_sahte(scripts: Path, proje: Path, argv: list[str], canli: dict,
                 arama: str = "") -> tuple[int, str]:
    kod = _SAHTE.format(scripts=str(scripts), canli=json.dumps(canli), arama=arama,
                        argv=json.dumps(argv + ["--session", SID]))
    r = subprocess.run([sys.executable, "-c", kod], capture_output=True, env=_env(proje),
                       cwd=str(proje), timeout=180)
    cikti = (r.stdout + r.stderr).decode("utf-8", errors="replace")
    rc = None
    for satir in cikti.splitlines():
        if satir.startswith("RC="):
            rc = int(satir[3:]) if satir[3:].isdigit() else None
    return (rc if rc is not None else 99), cikti


def store(proje: Path) -> dict:
    try:
        return json.loads((proje / ".claude" / ".session_fresh.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _anahtar(scripts: Path, proje: Path, dosyalar: list[Path]) -> list[str]:
    """Anahtarı ÜRETİM fonksiyonundan al (fixture kendi kuralını yazmaz)."""
    kod = ("import sys,json; sys.path.insert(0, %r); from source_drift import tazelik_anahtari; "
           "print(json.dumps([tazelik_anahtari(p, %r) for p in json.loads(sys.argv[1])]))"
           % (str(scripts), str(proje)))
    r = subprocess.run([sys.executable, "-c", kod, json.dumps([str(d) for d in dosyalar])],
                       capture_output=True, env=_env(proje), cwd=str(proje), timeout=60)
    try:
        return json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
    except Exception:
        return ["<olculemedi>"] * len(dosyalar)


def senaryolar(scripts: Path, kum: Path) -> None:
    proje = proje_kur(kum / "proje")
    S = proje / "SOURCE_CODES" / "SD" / "ZSD001_CLC"
    main_ = S / "classes" / "ZCL_SD001_X.clas.abap"
    ccimp = S / "classes" / "ZCL_SD001_X.ccimp.abap"
    ccau = S / "classes" / "ZCL_SD001_X.ccau.abap"
    agit = S / "classes" / "ZCL_SD001_Y.clas.locals_imp.abap"
    incl = S / "programs" / "includes" / "ZSD001_I_X_TOP.prog.abap"
    duz = S / "programs" / "ZSD001_I_Y.abap"
    fm = S / "functions" / "ZSD001_FM_X.func.abap"
    yapi = S / "structures" / "ZSD001_S_X.ddls.asddls"
    cds = S / "cds" / "ZSD001_I_X.cds"
    bdef = S / "cds" / "ZSD001_I_X.bdef"
    tabl1 = S / "tables" / "ZSD001_T_X.tabl.ddl"
    tabl2 = S / "tables" / "ZSD001_T_Y.tabl"

    # ── H: alt-include kapsamı + muafiyetler ───────────────────────────────────
    rc, err = kapi(scripts, proje, ccimp)
    kontrol("H1 bayat .ccimp -> BLOK (exit 2) + kendi tipi + --file",
            rc == 2 and "--type implementations" in err and "--file" in err, f"rc={rc}")
    # KONTROL (E2'nin ikizi): çekirdek dal "çeker/yazar" metnini VE --offline kaçışını KORUR
    kontrol("H1b cekirdek dal blok metni: 'bu seansta SAP'den cekilMEDI' + 'dosyasina yazar' + --offline",
            "bu seansta SAP'den çekilMEDİ" in err and "dosyasına yazar" in err
            and "--offline" in err and "kapsam eklentisi" not in err, f"err={err[:160]!r}")
    rc, err = kapi(scripts, proje, agit)
    kontrol("H2 abapGit adli include (.clas.locals_imp) -> BLOK, ayni tur",
            rc == 2 and "--type implementations" in err, f"rc={rc}")
    rc_o, out = cekici(scripts, proje, "ZCL_SD001_X", "--type", "class", "--offline",
                       "--file", str(main_))
    rc1, _ = kapi(scripts, proje, main_)
    rc2, err2 = kapi(scripts, proje, ccimp)
    kontrol("H3 ANA sinif damgasi alt-include'u KAPSAMAZ (ana=0, .ccimp=2)",
            rc_o == 0 and rc1 == 0 and rc2 == 2, f"offline={rc_o} ana={rc1} ccimp={rc2}")
    cekici(scripts, proje, "ZCL_SD001_X", "--type", "ccimp", "--offline", "--file", str(ccimp))
    rc, err = kapi(scripts, proje, ccimp)
    kontrol("H4 .ccimp KENDI damgasiyla -> GECIS + SESSIZ", rc == 0 and err.strip() == "",
            f"rc={rc} err={err[:80]!r}")
    rc, err = kapi(scripts, proje, ccau)
    kontrol("H5 kardes .ccau hala BLOK (bir include digerini kapsamaz)", rc == 2,
            f"rc={rc}")
    ccau.write_text("* yerel WIP\n", encoding="utf-8")
    rc, err = kapi(scripts, proje, ccau)
    kontrol("H6 git-DIRTY .ccau -> GECIS (WIP muaf)", rc == 0 and err.strip() == "", f"rc={rc}")
    subprocess.run(["git", "-C", str(proje), "checkout", "--", str(ccau)], capture_output=True)
    rc, err = kapi(scripts, proje, S / "classes" / "ZCL_SD001_YENI.ccimp.abap")
    kontrol("H7 YENI include (dosya yok) -> GECIS", rc == 0 and err.strip() == "", f"rc={rc}")
    rc, err = kapi(scripts, proje, ccimp, govde=b'{"tool_name": "Edit", "tool_input": {')
    kontrol("H8 parse-fail -> exit 0 + GIRDI-PARSE-EDILEMEDI notu",
            rc == 0 and "GIRDI-PARSE-EDILEMEDI" in err, f"rc={rc}")
    rc, err = kapi(scripts, proje, S / "ref_docs" / "ZCL_SD001_X.ccimp.abap")
    kontrol("H9 ref_docs/ altindaki include -> MUAF (sessiz)", rc == 0 and err.strip() == "",
            f"rc={rc}")
    rc, err = kapi(scripts, proje, S / "NOTLAR.md")
    kontrol("H10 kaynak olmayan dosya -> gate yok (sessiz)", rc == 0 and err.strip() == "",
            f"rc={rc}")
    # tek kaynak yüklenemezse: görünür not + exit 0 (brick YOK)
    yalniz = kum / "yalniz" / "hooks"
    yalniz.mkdir(parents=True)
    shutil.copy2(scripts / "hooks" / "pull_before_edit.py", yalniz / "pull_before_edit.py")
    rc, err = kapi(yalniz.parent, proje, ccimp)
    kontrol("H11 siniflandirma modulu YOK -> exit 0 + SINIFLANDIRMA-YUKLENEMEDI notu",
            rc == 0 and "SINIFLANDIRMA-YUKLENEMEDI" in err, f"rc={rc} err={err[:90]!r}")

    # ── T: tip önerisi + aynı ad ayrımı + KONTROL grubu ────────────────────────
    for ad, dosya in (("T1 include .prog.abap", incl), ("T2 duz .abap", duz),
                      ("T3 FM .func.abap", fm), ("T4 yapi .ddls.asddls", yapi)):
        rc, err = kapi(scripts, proje, dosya)
        kontrol(f"{ad} -> BLOK + `--type auto` (adan tahmin YOK)",
                rc == 2 and "--type auto" in err
                and "--type class" not in err and "--type program" not in err
                and "--type ddls" not in err, f"rc={rc}")
    rc, err = kapi(scripts, proje, main_)
    kontrol("T5 KONTROL .clas.abap (damgali) -> GECIS", rc == 0, f"rc={rc}")
    rc, err = kapi(scripts, proje, bdef)
    kontrol("T6 KONTROL .bdef tipi kesin -> `--type bdef`", rc == 2 and "--type bdef" in err,
            f"rc={rc}")
    cekici(scripts, proje, "ZSD001_I_X", "--type", "auto", "--offline", "--file", str(cds))
    rc_c, _ = kapi(scripts, proje, cds)
    rc_b, _ = kapi(scripts, proje, bdef)
    kontrol("T7 ayni adli CDS damgasi BDEF'i KAPSAMAZ (cds=0, bdef=2)",
            rc_c == 0 and rc_b == 2, f"cds={rc_c} bdef={rc_b}")
    for ad, dosya in (("T8 tablo .tabl.ddl", tabl1), ("T9 tablo .tabl", tabl2)):
        rc, err = kapi(scripts, proje, dosya)
        kontrol(f"{ad} -> KAPSAMDA (BLOK + auto)", rc == 2 and "--type auto" in err, f"rc={rc}")

    # --offline çözülemeyen hedef: damga YOK, kapı kilitlenmez (komut --file verir)
    rc, out = cekici(scripts, proje, "ZSD001_HIC_YOK", "--type", "auto", "--offline")
    kontrol("T10 --offline hedef cozulemezse FAIL (sahte damga YOK)",
            rc == 1 and "--file" in out, f"rc={rc}")

    # ── P: çekici (sahte ADT, ağ YOK) ──────────────────────────────────────────
    (proje / ".claude" / ".session_fresh.json").write_text("{}", encoding="utf-8")
    canli = {
        "/sap/bc/adt/oo/classes/zcl_sd001_x/source/main": "CLASS zcl_sd001_x DEFINITION.\n* canli\n",
        "/sap/bc/adt/oo/classes/zcl_sd001_x/includes/implementations": "* yerel impl CANLI v2\n",
        # testclasses YOK -> 404
    }
    rc, out = cekici_sahte(scripts, proje, ["ZCL_SD001_X", "--type", "class",
                                            "--file", str(main_)], canli)
    st = (store(proje).get("objects") or {})
    k = _anahtar(scripts, proje, [main_, ccimp, ccau])
    kontrol("P1 --type class: ana + .ccimp KENDI uclarindan yazildi",
            main_.read_text(encoding="utf-8").endswith("* canli\n")
            and ccimp.read_text(encoding="utf-8") == "* yerel impl CANLI v2\n", out[-300:])
    kontrol("P2 cekilemeyen .ccau (404) DAMGALANMADI + 'CEKILMEDI' der + rc=1",
            k[2] not in st and k[0] in st and k[1] in st
            and "ÇEKİLMEDİ: ZCL_SD001_X.ccau.abap" in out and rc == 1,
            f"rc={rc} keys={sorted(st)}")
    rc_k1, _ = kapi(scripts, proje, main_)
    rc_k2, _ = kapi(scripts, proje, ccimp)
    rc_k3, _ = kapi(scripts, proje, ccau)
    kontrol("P3 UCTAN UCA: yazanin anahtari == okuyanin anahtari (ana=0 ccimp=0 ccau=2)",
            (rc_k1, rc_k2, rc_k3) == (0, 0, 2), f"{(rc_k1, rc_k2, rc_k3)}")

    ara = _arama_xml(("/sap/bc/adt/programs/includes/zsd001_i_x_top", "PROG/I", "ZSD001_I_X_TOP"),
                     ("/sap/bc/adt/programs/includes/zsd001_i_x_top_old", "PROG/I", "ZSD001_I_X_TOP_OLD"))
    rc, out = cekici_sahte(scripts, proje, ["ZSD001_I_X_TOP", "--type", "auto", "--file", str(incl)],
                           {"/sap/bc/adt/programs/includes/zsd001_i_x_top/source/main": "* top CANLI\n"},
                           ara)
    rc_k, _ = kapi(scripts, proje, incl)
    kontrol("P4 auto: tam-ad PROG/I -> include ucundan cekildi + kapi GECIYOR",
            rc == 0 and "PROG/I" in out and incl.read_text(encoding="utf-8") == "* top CANLI\n"
            and rc_k == 0, f"rc={rc} kapi={rc_k} {out[-200:]!r}")
    ara = _arama_xml(("/sap/bc/adt/functions/groups/zsd001_fg/fmodules/zsd001_fm_x", "FUGR/FF", "ZSD001_FM_X"))
    rc, out = cekici_sahte(scripts, proje, ["ZSD001_FM_X", "--type", "auto", "--file", str(fm)],
                           {"/sap/bc/adt/functions/groups/zsd001_fg/fmodules/zsd001_fm_x/source/main":
                            "FUNCTION zsd001_fm_x.\n* canli\n"}, ara)
    kontrol("P5 auto: FM grup ADRESI aramadan (adan turetilemez) -> cekildi",
            rc == 0 and "FUGR/FF" in out and fm.read_text(encoding="utf-8").endswith("* canli\n"),
            f"rc={rc} {out[-200:]!r}")
    ara = _arama_xml(("/sap/bc/adt/bo/behaviordefinitions/zsd001_i_x", "BDEF/BDO", "ZSD001_I_X"),
                     ("/sap/bc/adt/ddic/ddl/sources/zsd001_i_x", "DDLS/DF", "ZSD001_I_X"),
                     ("/sap/bc/adt/ddic/ddl/sources/zsd001_i_x/source/main#name=zsd001_i_x", "STOB/DO", "ZSD001_I_X"))
    rc, out = cekici_sahte(scripts, proje, ["ZSD001_I_X", "--type", "auto", "--file", str(cds)],
                           {"/sap/bc/adt/ddic/ddl/sources/zsd001_i_x/source/main":
                            "define view entity ZSD001_I_X as select from y\n"}, ara)
    kontrol("P6 auto: ayni adli DDLS+BDEF+STOB -> aile suzgeci DDLS'i secer",
            rc == 0 and "DDLS/DF" in out and "from y" in cds.read_text(encoding="utf-8"),
            f"rc={rc} {out[-200:]!r}")
    once = yapi.read_bytes()
    ara = _arama_xml(("/sap/bc/adt/ddic/structures/zsd001_s_x", "TABL/DS", "ZSD001_S_X"),
                     ("/sap/bc/adt/ddic/tables/zsd001_s_x", "TABL/DT", "ZSD001_S_X"))
    rc, out = cekici_sahte(scripts, proje, ["ZSD001_S_X", "--type", "auto", "--file", str(yapi)],
                           {}, ara)
    kontrol("P7 auto: aile icinde >1 aday -> DUR (tahmin YOK, yazma YOK, damga YOK)",
            rc == 1 and "tahmin YOK" in out and yapi.read_bytes() == once
            and _anahtar(scripts, proje, [yapi])[0] not in (store(proje).get("objects") or {}),
            f"rc={rc}")
    rc, out = cekici_sahte(scripts, proje, ["ZSD001_S_X", "--type", "auto", "--file", str(yapi)],
                           {}, _arama_xml(("/sap/bc/adt/ddic/ddl/sources/zsd001_s_x_v", "DDLS/DF",
                                           "ZSD001_S_X_V")))
    kontrol("P8 auto: tam-ad aday YOK (onek eslesmesi sayilmaz) -> DUR",
            rc == 1 and "YOK" in out and yapi.read_bytes() == once, f"rc={rc}")


# Eklenti STUB'ları — gerçek eklentiler başka PR'larda gelir; burada yalnız SÖZLEŞME ölçülür.
_STUB_UI = """from pathlib import Path


def sinifla(path, root):
    p = Path(path)
    if "webapp" not in [x.lower() for x in p.parts] or not p.name.endswith(".js"):
        return None
    return {"nesne": "ZSD001_UI", "tip": "ui5",
            "komut": "python core/scripts/fetch_ui_source.py ZSD001_UI --karsilastir"}
"""
_STUB_BOZUK = "def sinifla(path, root)\n    return None\n"          # SyntaxError
_STUB_PATLAYAN = "def sinifla(path, root):\n    raise RuntimeError('stub')\n"


def eklenti_arayuzu(scripts: Path, kum: Path) -> None:
    proje = proje_kur(kum / "proje3")
    ui = proje / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "ui" / "webapp"
    js, xml = ui / "Component.js", ui / "view" / "Main.view.xml"
    hooks = scripts / "hooks"

    # E1 — eklenti dosyası YOK: bugünkü davranış (kapsam yok, SESSİZ)
    rc, err = kapi(scripts, proje, js)
    kontrol("E1 eklenti YOK -> webapp dosyasi kapsam disi (exit 0, SESSIZ)",
            rc == 0 and err.strip() == "", f"rc={rc} err={err[:90]!r}")

    (hooks / "_pbe_ui.py").write_text(_STUB_UI, encoding="utf-8")
    rc, err = kapi(scripts, proje, js)
    kontrol("E2 eklenti dict -> BLOK + eklentinin KOMUTU + --offline sozu VERILMEZ",
            rc == 2 and "fetch_ui_source.py ZSD001_UI --karsilastir" in err
            and "kapsam eklentisi: _pbe_ui" in err and "--offline" not in err
            and "sap_sync_pull" not in err
            # eklenti komutu dosyaya YAZMAYABİLİR -> "çeker/yazar" iddiası verilmez
            and "dosyasına yazar" not in err and "SAP'den çekilMEDİ" not in err
            and "seans-taze damgalanır" in err, f"rc={rc} err={err[:160]!r}")
    rc, err = kapi(scripts, proje, xml)
    kontrol("E3 eklenti None -> o dosya kapsam disi (SESSIZ)", rc == 0 and err.strip() == "",
            f"rc={rc}")

    # E4 — public damga: başka bir çekici `source_drift.tazelik_damgala` ile yazar -> kapı geçer
    kod = ("import sys, json; sys.path.insert(0, %r); "
           "from source_drift import tazelik_damgala, seans_kimligi; "
           "print(json.dumps([tazelik_damgala(%r, %r), seans_kimligi('acik'), seans_kimligi()]))"
           % (str(scripts), SID, str(js)))
    r = subprocess.run([sys.executable, "-c", kod], capture_output=True, env=_env(proje),
                       cwd=str(proje), timeout=60)
    try:
        anahtar, acik, marker_yok = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
    except Exception:
        anahtar, acik, marker_yok = "", "", ""
    rc, err = kapi(scripts, proje, js)
    kontrol("E4 public tazelik_damgala -> anahtar doner + kapi GECER (yazan==okuyan)",
            bool(anahtar) and anahtar == _anahtar(scripts, proje, [js])[0] and rc == 0,
            f"anahtar={anahtar!r} rc={rc} stderr={r.stderr.decode('utf-8', 'replace')[-120:]!r}")
    kontrol("E5 seans_kimligi: acik kimlik aynen · marker yoksa 'default' (fail-safe)",
            acik == "acik" and marker_yok == "default", f"{acik!r} {marker_yok!r}")
    (proje / ".claude" / ".current_session").write_text(json.dumps({"session_id": "m-1"}),
                                                        encoding="utf-8")
    r = subprocess.run([sys.executable, "-c",
                        "import sys; sys.path.insert(0, %r); from source_drift import "
                        "seans_kimligi; print(seans_kimligi())" % str(scripts)],
                       capture_output=True, env=_env(proje), cwd=str(proje), timeout=60)
    kontrol("E6 seans_kimligi: marker varsa ondan okur",
            r.stdout.decode("utf-8").strip().endswith("m-1"), r.stdout.decode()[-40:])

    # E7 — eklentinin dosyası git-DIRTY -> muafiyet eklentiye de uygulanır
    subprocess.run(["git", "-C", str(proje), "checkout", "--", "."], capture_output=True)
    (proje / ".claude" / ".session_fresh.json").unlink(missing_ok=True)
    js.write_text("// yerel WIP\n", encoding="utf-8")
    rc, err = kapi(scripts, proje, js)
    kontrol("E7 eklenti dosyasi git-DIRTY -> GECIS (WIP muaf)", rc == 0 and err.strip() == "",
            f"rc={rc}")
    subprocess.run(["git", "-C", str(proje), "checkout", "--", str(js)], capture_output=True)

    # E8 — VAR ama yüklenemeyen eklenti -> GÖRÜNÜR not + exit 0; önceki eklenti çalışmaya devam
    (hooks / "_pbe_msag_textpool.py").write_text(_STUB_BOZUK, encoding="utf-8")
    rc, err = kapi(scripts, proje, xml)
    kontrol("E8 bozuk eklenti -> exit 0 + EKLENTI-YUKLENEMEDI notu (brick YOK)",
            rc == 0 and "EKLENTI-YUKLENEMEDI: _pbe_msag_textpool" in err, f"rc={rc} err={err[:120]!r}")
    rc, err = kapi(scripts, proje, js)
    kontrol("E9 bozuk KARDES eklenti, calisan eklentinin blokunu dusurmez", rc == 2
            and "fetch_ui_source.py" in err, f"rc={rc}")

    # E10 — sinifla() hata atar -> fail-open ama GÖRÜNÜR (lider kararı 2026-09-26): not + exit 0
    (hooks / "_pbe_msag_textpool.py").write_text(_STUB_PATLAYAN, encoding="utf-8")
    rc, err = kapi(scripts, proje, xml)
    kontrol("E10 sinifla() istisna -> exit 0 + EKLENTI-HATA notu (ad + istisna tipi; sessiz DEGIL)",
            rc == 0 and "EKLENTI-HATA: _pbe_msag_textpool: RuntimeError" in err,
            f"rc={rc} err={err[:120]!r}")
    rc, err = kapi(scripts, proje, js)
    kontrol("E11 patlayan KARDES eklenti, calisan eklentinin blokunu dusurmez", rc == 2
            and "fetch_ui_source.py" in err, f"rc={rc}")

    # E12 — ad konvansiyonu (C-TPL-01): `hooks/*.py` içinde `_` ile BAŞLAMAYAN dosya kablolanması
    # gereken HOOK sayılır (check_settings_template_sync). Eklenti hook DEĞİL, yardımcı modül ⇒
    # kayıttaki HER ad `_` önekli olmalı (ölçülmüş vaka 2026-09-26: `pbe_ui.py` CI'da düştü).
    import ast
    kayit = None
    for n in ast.walk(ast.parse((scripts / "hooks" / "pull_before_edit.py").read_text(encoding="utf-8"))):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_EK_DENETCILER" for t in n.targets):
            kayit = ast.literal_eval(n.value)
    kontrol("E12 eklenti adlari `_` onekli (C-TPL-01: hook sayilmaz)",
            bool(kayit) and all(a.startswith("_") for a in kayit), f"kayit={kayit}")

    # stub'ları kaldır (kum zaten silinir; sonraki senaryolar eklentisiz ortam varsayar)
    for ad in ("_pbe_ui.py", "_pbe_msag_textpool.py"):
        (hooks / ad).unlink(missing_ok=True)


def ucuncu_baglam(scripts: Path, kum: Path) -> None:
    """3. BAĞLAM: `source_root` farklı adlı proje — kök segmenti config'ten okunur."""
    proje = proje_kur(kum / "proje2", source_root="ABAP_SRC")
    ccimp = proje / "ABAP_SRC" / "SD" / "ZSD001_CLC" / "classes" / "ZCL_SD001_X.ccimp.abap"
    rc, err = kapi(scripts, proje, ccimp)
    kontrol("X1 source_root=ABAP_SRC projesinde .ccimp -> BLOK", rc == 2 and "--file" in err,
            f"rc={rc}")
    yabanci = proje / "BASKA" / "ZCL_SD001_X.ccimp.abap"
    yabanci.parent.mkdir(parents=True)
    yabanci.write_text("* x\n", encoding="utf-8")
    rc, err = kapi(scripts, proje, yabanci)
    kontrol("X2 kaynak-kok DISI ayni ad -> kapsam disi (sessiz)", rc == 0 and err.strip() == "",
            f"rc={rc}")


def main(argv: list[str]) -> int:
    kipler = [a for a in argv if a.startswith("--")]
    bilinmeyen = [k for k in kipler if k not in GECERLI_KIP]
    if bilinmeyen or len(kipler) > 1:
        print(f"[KULLANIM] gecerli kipler: {sorted(GECERLI_KIP)} (en fazla bir) — verilen: {kipler}")
        return 2
    kip = kipler[0] if kipler else None
    print("=" * 78)
    print(f"pbe_kapsam — PULL-BEFORE-EDIT kapsam (Q352){'  KIP=' + kip if kip else ''}")
    print("=" * 78)
    kum = Path(tempfile.mkdtemp(prefix="pbe_kapsam_"))
    try:
        scripts = kopya_kur(kum, kip)
        senaryolar(scripts, kum)
        ucuncu_baglam(scripts, kum)
        eklenti_arayuzu(scripts, kum)
    finally:
        _sil(kum)
    kirik = [a for a, ok, _ in SONUC if not ok]
    for ad, ok, detay in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
        if not ok:
            print(f"         gorulen: {detay}")
    print(f"\n{len(SONUC) - len(kirik)}/{len(SONUC)} PASS")
    return 1 if kirik else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
