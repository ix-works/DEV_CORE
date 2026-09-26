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
  Bug gate #306 düzeltme turu (her bulgu geri sokulunca KIRMIZI):
  --mutasyon-file-dogrulama-yok  M1 `--file` obje adı/tipiyle doğrulanmaz
  --mutasyon-systemexit          M2 eklentide SystemExit `Exception` sanılır
  --mutasyon-eklenti-session     N1 kapı eklenti komutuna `--session` eklemez
  --mutasyon-dirty-kok           N2 dirty kontrolü dosyanın deposunda değil ROOT'ta
  --mutasyon-force-tipi          L1 auto dalında tekrar komutu çözülen tiple basılır
  --mutasyon-offline-rc          L2 `--offline` damgalayamasa da rc 0
  --mutasyon-drift-tablo         L3 check_source_drift tablo uzantısını tanımaz
  Takip turu (bug gate PASS sonrası, 2026-09-26):
  --mutasyon-kardes-kok    alt-include'lar `--file`'ın ağacında değil proje kökünde aranır
  --mutasyon-noktanokta    `..` içeren yol normalize edilmez (docs/.. sahte-muaf)
  --mutasyon-session-ez    eklenti komutundaki FARKLI --session kapıyla değiştirilmez
  --mutasyon-yer-tutucu    komutsuz eklentinin yer tutucusuna --session eklenir
  --mutasyon-not-kirp      eklenti `not`u iki uçtan kırpılmaz
  --mutasyon-esanlam       --file tip eşanlamlıları (behaviordefinition/bdo) reddedilir
  Son dar tur (bug gate WARNING, 2026-09-26):
  --mutasyon-kardes-kok-auto  `--type auto` SINIF dalı alt-include'ları proje kökünde arar
  --mutasyon-kanonik-tip      eşanlamlı tip çevrimiçi çekmeye kanonik ada çevrilmeden gider
  Kapanış turu (son kapı WARNING — test eksiği, 2026-09-26):
  --mutasyon-kanonik-koruma-yok  `_kanonik_tip` baştaki `normalize_object_type` korumasını
                                 kaybeder (çözülebilen `.abap` tipleri `class`a çevrilir)

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
               "--mutasyon-eklenti-yok", "--mutasyon-file-dogrulama-yok",
               "--mutasyon-systemexit", "--mutasyon-eklenti-session", "--mutasyon-dirty-kok",
               "--mutasyon-force-tipi", "--mutasyon-offline-rc", "--mutasyon-drift-tablo",
               "--mutasyon-kardes-kok", "--mutasyon-noktanokta", "--mutasyon-session-ez",
               "--mutasyon-yer-tutucu", "--mutasyon-not-kirp", "--mutasyon-esanlam",
               "--mutasyon-kardes-kok-auto", "--mutasyon-kanonik-tip",
               "--mutasyon-kanonik-koruma-yok"}

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
    "--mutasyon-file-dogrulama-yok": [(
        "sap_sync_pull.py",
        "        hata = _dosya_tutarsizligi(obj, t, repo_file)\n",
        "        hata = \"\"\n")],
    "--mutasyon-systemexit": [
        ("hooks/pull_before_edit.py",
         "        except BaseException as exc:  # noqa: BLE001 — kapı asla çökmemeli\n",
         "        except Exception as exc:  # noqa: BLE001\n"),
        ("hooks/pull_before_edit.py",
         "        except BaseException as exc:  # noqa: BLE001 — M2: SystemExit(0) sessiz açık bırakmasın\n",
         "        except Exception as exc:  # noqa: BLE001\n")],
    "--mutasyon-eklenti-session": [(
        "hooks/pull_before_edit.py",
        "            return f\"{komut} --session {session_id}\", \"\"\n",
        "            return komut, \"\"\n")],
    "--mutasyon-dirty-kok": [(
        "hooks/pull_before_edit.py",
        "            [\"git\", \"-C\", str(p.parent), \"status\", \"--porcelain\", \"--\", p.name],\n",
        "            [\"git\", \"-C\", str(ROOT), \"status\", \"--porcelain\", \"--\", str(p)],\n")],
    "--mutasyon-force-tipi": [(
        "sap_sync_pull.py",
        "        rc = _sonuc(obj, cozulen, res, session, dosya_eki, komut_tipi=\"auto\")\n",
        "        rc = _sonuc(obj, cozulen, res, session, dosya_eki)\n")],
    "--mutasyon-offline-rc": [(
        "sap_sync_pull.py",
        "                rc = 1\n        return rc\n",
        "                pass\n        return rc\n")],
    "--mutasyon-drift-tablo": [(
        "validators/check_source_drift.py",
        "    \".tabl.ddl\": [\"table\"],\n    \".tabl\": [\"table\"],\n",
        "")],
    "--mutasyon-kardes-kok": [(
        "sap_sync_pull.py",
        "        includes = find_repo_class_includes(obj, erp_root)\n",
        "        includes = find_repo_class_includes(obj)\n")],
    "--mutasyon-kardes-kok-auto": [(
        "sap_sync_pull.py",
        "            rc = max(rc, _sinif_includelari(obj, session, client.adt_client, args.force,\n"
        "                                            kardes_koku))\n",
        "            rc = max(rc, _sinif_includelari(obj, session, client.adt_client, args.force,\n"
        "                                            None))\n")],
    "--mutasyon-kanonik-tip": [(
        "sap_sync_pull.py",
        "    t = _kanonik_tip(t)                    # eşanlamlı → çekme yolunun tanıdığı ad (son dar tur 2)\n",
        "")],
    # `_kanonik_tip` başındaki koruma: çözülebilen ad (class/program/…) DOKUNULMAZ. Söküldüğünde
    # `.abap` paylaşan her tip `_PBE_ACIK_TIP`'in ilk satırıyla (`.clas.abap` -> class) eşleşir.
    "--mutasyon-kanonik-koruma-yok": [(
        "sap_sync_pull.py",
        "        from object_types import normalize_object_type\n"
        "        normalize_object_type(t)\n"
        "        return t\n",
        "        pass\n")],
    "--mutasyon-noktanokta": [(
        "source_drift.py",
        "    p = Path(normpath(str(path)))\n    n = p.name.lower()\n",
        "    p = Path(path)\n    n = p.name.lower()\n")],
    "--mutasyon-session-ez": [(
        "hooks/pull_before_edit.py",
        "        if all(v == session_id for v in eski):\n",
        "        if eski:\n")],
    "--mutasyon-yer-tutucu": [(
        "hooks/pull_before_edit.py",
        "            return komut, \"\"               # çalıştırılabilir komut YOK → yer tutucuya ekleme\n",
        "            pass\n")],
    "--mutasyon-not-kirp": [(
        "hooks/pull_before_edit.py",
        "                    \"not\": not_.strip() if isinstance(not_, str) else \"\"}",
        "                    \"not\": not_ if isinstance(not_, str) else \"\"}")],
    "--mutasyon-esanlam": [(
        "sap_sync_pull.py",
        "            return \"uzanti:\" + \",\".join(exts) if exts else ham\n",
        "            return ham\n")],
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
    (hedef / "validators").mkdir()
    shutil.copy2(SCRIPTS / "validators" / "check_source_drift.py",
                 hedef / "validators" / "check_source_drift.py")
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
    "SD/ZSD001_CLC/ui/webapp/Other.js": "sap.ui.define([], function () {});\n",
    "SD/ZSD001_CLC/ui/webapp/Ayni.js": "sap.ui.define([], function () {});\n",
    "SD/ZSD001_CLC/ui/webapp/Bos.js": "sap.ui.define([], function () {});\n",
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
    # CRLF -> LF: Windows metin kipi stderr satır sonunu CRLF yapar; satır-sınırlı iddialar
    # (komut satırının SONU, not satırı) platformdan bağımsız ölçülsün.
    return r.returncode, r.stderr.decode("utf-8", errors="replace").replace("\r\n", "\n")


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

    # P9/P10 — Z TABLO uçtan uca (DoD ①): auto -> TABL/DT -> `/ddic/tables/<t>/source/main`
    # (canlı ölçüm 200) -> `.tabl.ddl` / `.tabl` dosyasına yazılır -> kapı GEÇER.
    for ad_, dosya_, obj_ in (("P9 .tabl.ddl", tabl1, "ZSD001_T_X"), ("P10 .tabl", tabl2, "ZSD001_T_Y")):
        kucuk = obj_.lower()
        ara = _arama_xml((f"/sap/bc/adt/ddic/tables/{kucuk}", "TABL/DT", obj_))
        govde = f"define table {kucuk} {{\n  key mandt : mandt not null;\n}}\n"
        rc, out = cekici_sahte(scripts, proje, [obj_, "--type", "auto", "--file", str(dosya_)],
                               {f"/sap/bc/adt/ddic/tables/{kucuk}/source/main": govde}, ara)
        rc_k, _ = kapi(scripts, proje, dosya_)
        kontrol(f"{ad_} auto: TABL/DT tablo ucundan cekildi + dosyaya yazildi + kapi GECIYOR",
                rc == 0 and "TABL/DT" in out and "key mandt" in dosya_.read_text(encoding="utf-8")
                and rc_k == 0, f"rc={rc} kapi={rc_k} {out[-200:]!r}")


# Eklenti STUB'ları — gerçek eklentiler başka PR'larda gelir; burada yalnız SÖZLEŞME ölçülür.
_STUB_UI = """from pathlib import Path


def sinifla(path, root):
    p = Path(path)
    if "webapp" not in [x.lower() for x in p.parts] or not p.name.endswith(".js"):
        return None
    if p.name == "Other.js":        # not YOK + komutta FARKLI --session (sözleşme ihlali)
        return {"nesne": "ZSD001_UI", "tip": "ui5",
                "komut": "python core/scripts/fetch_ui_source.py ZSD001_UI --session=HAZIR"}
    if p.name == "Ayni.js":         # komutta kapının KENDİ kimliği zaten var → dokunulmaz
        return {"nesne": "ZSD001_UI", "tip": "ui5",
                "komut": "python core/scripts/fetch_ui_source.py ZSD001_UI --session __SID__"}
    if p.name == "Bos.js":          # komut YOK + boşluklu not
        return {"nesne": "ZSD001_UI", "tip": "ui5", "komut": "",
                "not": "   NOT-BOSLUK   \\n\\n"}
    return {"nesne": "ZSD001_UI", "tip": "ui5",
            "komut": "python core/scripts/fetch_ui_source.py ZSD001_UI --karsilastir",
            "not": "NOT-STUB: SAP erisilemiyorsa elle karsilastir."}
"""
_STUB_UI = _STUB_UI.replace("__SID__", SID)
_STUB_IMPORT_EXIT = "import sys\nsys.exit(2)\n"                          # M2 import dalı
_STUB_CAGRI_EXIT = "import sys\ndef sinifla(path, root):\n    sys.exit(0)\n"   # M2 çağrı dalı
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
    kontrol("E13 N1: kapi eklenti komutunun SONUNA hook'un seans kimligini ekler",
            f"--karsilastir --session {SID}" in err, f"err={err[:200]!r}")
    kontrol("E14 N1: eklentinin `not`u blok mesajinda basilir", "NOT-STUB:" in err,
            f"err={err[-160:]!r}")
    rc, err = kapi(scripts, proje, ui / "Other.js")
    kontrol("E15 takip-3: komutta FARKLI --session -> kapinin kimligiyle DEGISTIRILIR + gorunur not "
            "(`not` yokken NOT-STUB basilmaz, ekleme CIFTLENMEZ)",
            rc == 2 and "NOT-STUB" not in err and f"ZSD001_UI --session={SID}\n" in err
            and "--session=HAZIR" not in err and "seans kimliğiyle değiştirildi" in err
            and err.count(f"--session {SID}") == 0, f"rc={rc} err={err[:260]!r}")
    rc, err = kapi(scripts, proje, ui / "Ayni.js")
    kontrol("E18 takip-3 KONTROL: komutta kapinin KENDI kimligi -> dokunulmaz, not YOK",
            rc == 2 and f"ZSD001_UI --session {SID}\n" in err and err.count(f"--session {SID}") == 1
            and "değiştirildi" not in err, f"rc={rc} err={err[:200]!r}")
    rc, err = kapi(scripts, proje, ui / "Bos.js")
    kontrol("E19 takip-4: komutsuz eklenti -> yer tutucuya --session EKLENMEZ",
            rc == 2 and "<_pbe_ui: canlıdan-çekme komutu verilmedi>\n" in err,
            f"rc={rc} err={err[:200]!r}")
    kontrol("E20 takip-4: `not` iki uctan kirpilir (bosluk/bos satir basilmaz)",
            "\nNOT-BOSLUK\nAMAÇ" in err, f"err={err[-260:]!r}")
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

    # E16/E17 — M2: SystemExit `Exception` DEĞİLDİR. Import anında sys.exit(2) ilgisiz her
    # edit'i BLOKLUYORDU (brick); sinifla() içindeki SystemExit(0) sessiz açık bırakıyordu.
    (hooks / "_pbe_msag_textpool.py").write_text(_STUB_IMPORT_EXIT, encoding="utf-8")
    rc, err = kapi(scripts, proje, xml)
    kontrol("E16 M2: eklenti IMPORT aninda SystemExit -> exit 0 + EKLENTI-YUKLENEMEDI (brick YOK)",
            rc == 0 and "EKLENTI-YUKLENEMEDI: _pbe_msag_textpool" in err, f"rc={rc} err={err[:140]!r}")
    (hooks / "_pbe_msag_textpool.py").write_text(_STUB_CAGRI_EXIT, encoding="utf-8")
    rc, err = kapi(scripts, proje, xml)
    kontrol("E17 M2: sinifla() icinde SystemExit(0) -> EKLENTI-HATA notu (sessiz DEGIL)",
            rc == 0 and "EKLENTI-HATA: _pbe_msag_textpool: SystemExit" in err,
            f"rc={rc} err={err[:140]!r}")

    # stub'ları kaldır (kum zaten silinir; sonraki senaryolar eklentisiz ortam varsayar)
    for ad in ("_pbe_ui.py", "_pbe_msag_textpool.py"):
        (hooks / ad).unlink(missing_ok=True)


def duzeltme_turu(scripts: Path, kum: Path) -> None:
    """Bug gate #306 bulguları — her biri AYRI mutasyon kipiyle geri sokulur."""
    proje = proje_kur(kum / "proje4")
    S = proje / "SOURCE_CODES" / "SD" / "ZSD001_CLC"
    main_ = S / "classes" / "ZCL_SD001_X.clas.abap"
    ccimp = S / "classes" / "ZCL_SD001_X.ccimp.abap"
    ccau = S / "classes" / "ZCL_SD001_X.ccau.abap"
    incl = S / "programs" / "includes" / "ZSD001_I_X_TOP.prog.abap"
    prog = S / "programs" / "ZSD001_P_X.prog.abap"
    fm = S / "functions" / "ZSD001_FM_X.func.abap"

    def _st():
        return store(proje).get("objects") or {}

    # ── M1: --file obje adı + tip ile tutarlı olmalı ──────────────────────────
    once = main_.read_bytes()
    rc, out = cekici_sahte(scripts, proje, ["ZCL_SD001_BASKA", "--type", "class", "--file", str(main_)],
                           {"/sap/bc/adt/oo/classes/zcl_sd001_baska/source/main": "CLASS baska.\n"})
    kontrol("F1 M1: BASKA objenin adi + bu dosya -> [FAIL], yazma YOK, damga YOK",
            rc == 1 and "[FAIL]" in out and main_.read_bytes() == once and not _st(),
            f"rc={rc} damga={sorted(_st())} {out[-160:]!r}")
    rc, out = cekici_sahte(scripts, proje, ["ZCL_SD001_X", "--type", "class", "--file", str(ccimp)], {})
    kontrol("F2 M1: --type class + .ccimp dosyasi -> [FAIL] (tur tutarsiz)",
            rc == 1 and "[FAIL]" in out and not _st(), f"rc={rc} {out[-160:]!r}")
    rc, out = cekici(scripts, proje, "ZCL_SD001_BASKA", "--type", "class", "--offline", "--file", str(main_))
    kontrol("F3 M1: --offline da dogrular (baska ad) -> [FAIL], damga YOK",
            rc == 1 and "[FAIL]" in out and not _st(), f"rc={rc} {out[-160:]!r}")
    rc, out = cekici(scripts, proje, "ZCL_SD001_X", "--type", "implementations", "--offline",
                     "--file", str(ccau))
    kontrol("F4 M1: --type implementations + .ccau (kardes tur) -> [FAIL], damga YOK",
            rc == 1 and "[FAIL]" in out and not _st(), f"rc={rc} {out[-160:]!r}")
    rc, out = cekici(scripts, proje, "ZSD001_I_BASKA", "--type", "auto", "--offline", "--file", str(incl))
    kontrol("F5 M1: auto dali da dogrular (baska ad) -> [FAIL], damga YOK",
            rc == 1 and "[FAIL]" in out and not _st(), f"rc={rc} {out[-160:]!r}")
    rc, out = cekici(scripts, proje, "ZSD001_P_X", "--type", "program", "--offline", "--file", str(prog))
    kontrol("F6 KONTROL M1: dogru ad + uzantiyi kabul eden acik tip -> damgalanir (asiri-red YOK)",
            rc == 0 and _anahtar(scripts, proje, [prog])[0] in _st(), f"rc={rc} {out[-160:]!r}")

    # ── L1: auto dalında KORUMA tekrar komutu `--type auto` ile ───────────────
    fm.write_text("FUNCTION zsd001_fm_x.\n* yerel WIP\n", encoding="utf-8")
    ara = _arama_xml(("/sap/bc/adt/functions/groups/zsd001_fg/fmodules/zsd001_fm_x", "FUGR/FF", "ZSD001_FM_X"))
    rc, out = cekici_sahte(scripts, proje, ["ZSD001_FM_X", "--type", "auto", "--file", str(fm)],
                           {"/sap/bc/adt/functions/groups/zsd001_fg/fmodules/zsd001_fm_x/source/main":
                            "FUNCTION zsd001_fm_x.\n* canli\n"}, ara)
    satir = next((x for x in out.splitlines() if "sap_sync_pull.py" in x and "--force" in x), "")
    kontrol("L1 auto + KORUMA: tekrar komutu `--type auto` (cozulen `function` DEGIL)",
            rc == 1 and "[KORUMA]" in out and "--type auto" in satir and "--type function" not in satir,
            f"rc={rc} satir={satir!r}")
    subprocess.run(["git", "-C", str(proje), "checkout", "--", str(fm)], capture_output=True)

    # ── L2: --offline damga yazılamazsa rc 1 (başarı iddiası YOK) ─────────────
    kod = ("import sys; sys.path.insert(0, %r)\n"
           "import source_drift; source_drift.tazelik_damgala = lambda *a, **k: ''\n"
           "import sap_sync_pull as S\n"
           "sys.argv = ['sap_sync_pull.py', 'ZSD001_P_X', '--type', 'program', '--offline', "
           "'--file', %r, '--session', %r]\n"
           "print('RC=%%s' %% S.main())\n" % (str(scripts), str(prog), SID))
    r = subprocess.run([sys.executable, "-c", kod], capture_output=True, env=_env(proje),
                       cwd=str(proje), timeout=60)
    o = (r.stdout + r.stderr).decode("utf-8", "replace")
    kontrol("L2 --offline damga YAZILAMADI -> rc=1 + [FAIL] ([OFFLINE] basari satiri YOK)",
            "RC=1" in o and "[FAIL]" in o and "[OFFLINE]" not in o, o[-200:])

    # ── N2: kök DIŞI depodaki (kanonik .wt worktree) dosyada dirty muafiyeti ────
    wt = kum / "wt_repo"
    wtf = wt / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "classes" / "ZCL_SD001_W.ccimp.abap"
    wtf.parent.mkdir(parents=True)
    wtf.write_text("* impl\n", encoding="utf-8")
    for c in (["init", "-q"], ["config", "user.email", "fx"], ["config", "user.name", "fx"],
              ["add", "-A"], ["commit", "-q", "-m", "taban"]):
        subprocess.run(["git", "-C", str(wt), *c], check=True, capture_output=True)
    rc_temiz, _ = kapi(scripts, proje, wtf)
    wtf.write_text("* yerel WIP\n", encoding="utf-8")
    rc_kirli, err = kapi(scripts, proje, wtf)
    kontrol("N2 kok DISI depoda git-DIRTY -> GECIS (temizken BLOK = kontrol)",
            rc_temiz == 2 and rc_kirli == 0, f"temiz={rc_temiz} kirli={rc_kirli} {err[:100]!r}")

    # ── L3: check_source_drift tablo DDL'ini tanır (canlı uç ölçülmüş) ─────────
    kod = ("import sys, json; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
           "import check_source_drift as C\n"
           "from source_drift import SOURCE_EXTENSIONS\n"
           "istek = []\n"
           "class _R:\n    status_code = 200\n    text = 'define table zsd001_t_x {\\n}\\n'\n"
           "class _S:\n    def get(self, url, **k):\n        istek.append(url); return _R()\n"
           "class _C:\n    url = 'https://sap.invalid'\n    session = _S()\n"
           "src, tip = C._fetch_active_source(_C(), 'ZSD001_T_X', '.tabl.ddl')\n"
           "print(json.dumps({'eksik': [e for e in SOURCE_EXTENSIONS if e not in C._EXT_TO_TYPES],"
           " 'tip': tip, 'istek': istek}))\n" % (str(scripts), str(scripts / "validators")))
    r = subprocess.run([sys.executable, "-c", kod], capture_output=True, env=_env(proje),
                       cwd=str(proje), timeout=60)
    try:
        d = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
    except Exception:
        d = {"eksik": ["<olculemedi>"], "tip": None, "istek": [], "hata": r.stderr.decode()[-200:]}
    kontrol("L3a check_source_drift: SOURCE_EXTENSIONS'in HER uzantisinin canli tipi var (tamlik)",
            d.get("eksik") == [], f"eksik={d.get('eksik')} {d.get('hata', '')}")
    kontrol("L3b check_source_drift: .tabl.ddl -> table + `/ddic/tables/<t>/source/main` ucu",
            d.get("tip") == "table"
            and any(u.endswith("/sap/bc/adt/ddic/tables/zsd001_t_x/source/main") for u in d.get("istek", [])),
            f"{d}")


def takip_turu(scripts: Path, kum: Path) -> None:
    """Bug gate PASS sonrası takip turu: 1 (alt-include ağacı) · 2 (`..`/harf) · 5 (eşanlamlı)."""
    C = "SOURCE_CODES/SD/ZSD001_CLC/classes/"

    # ── 1: `--type class --file <.wt ağacı>` → alt-include'lar AYNI ağaçta ──────
    proje = proje_kur(kum / "proje5")
    wt = proje_kur(kum / "wt" / "proje5" / "dal")         # kanonik .wt: proje kökü DIŞINDA
    ana_ccimp = (proje / C / "ZCL_SD001_X.ccimp.abap").read_bytes()
    canli = {"/sap/bc/adt/oo/classes/zcl_sd001_x/source/main": "CLASS zcl_sd001_x DEFINITION.\n",
             "/sap/bc/adt/oo/classes/zcl_sd001_x/includes/implementations": "* CANLI impl\n",
             "/sap/bc/adt/oo/classes/zcl_sd001_x/includes/testclasses": "* CANLI test\n"}
    rc, out = cekici_sahte(scripts, proje, ["ZCL_SD001_X", "--type", "class", "--file",
                                            str(wt / C / "ZCL_SD001_X.clas.abap")], canli)
    st = store(proje).get("objects") or {}
    k_wt, k_ana = _anahtar(scripts, proje, [wt / C / "ZCL_SD001_X.ccimp.abap",
                                            proje / C / "ZCL_SD001_X.ccimp.abap"])
    kontrol("K1 takip-1: --file .wt ana kaynagi -> alt-include'lar AYNI agacta cekilip damgalanir",
            rc == 0 and (wt / C / "ZCL_SD001_X.ccimp.abap").read_text(encoding="utf-8") == "* CANLI impl\n"
            and k_wt in st, f"rc={rc} wt_damga={k_wt in st} {out[-200:]!r}")
    kontrol("K2 takip-1: ANA proje agacinin alt-include'una DOKUNULMAZ (yazma + damga YOK)",
            (proje / C / "ZCL_SD001_X.ccimp.abap").read_bytes() == ana_ccimp and k_ana not in st,
            f"ana_damga={k_ana in st}")

    # ── 1b (K3): AYNI sınıf, `--type auto` dalı (düz `.abap`; arama CLAS/OC döner) ───
    W_ = "SOURCE_CODES/SD/ZSD001_CLC/auto/"
    for kok, govde in ((proje, "* ANA impl\n"), (wt, "* wt impl\n")):
        d = kok / W_
        d.mkdir(parents=True, exist_ok=True)
        (d / "ZCL_SD001_W.abap").write_text("CLASS zcl_sd001_w DEFINITION.\n", encoding="utf-8")
        (d / "ZCL_SD001_W.ccimp.abap").write_text(govde, encoding="utf-8")
        for c in (["add", "-A"], ["commit", "-q", "-m", "auto sinif"]):
            subprocess.run(["git", "-C", str(kok), *c], check=True, capture_output=True)
    ana_w = (proje / W_ / "ZCL_SD001_W.ccimp.abap").read_bytes()
    canli_w = {"/sap/bc/adt/oo/classes/zcl_sd001_w/source/main": "CLASS zcl_sd001_w DEFINITION. \"c\n",
               "/sap/bc/adt/oo/classes/zcl_sd001_w/includes/implementations": "* CANLI W impl\n"}
    ara = _arama_xml(("/sap/bc/adt/oo/classes/zcl_sd001_w", "CLAS/OC", "ZCL_SD001_W"))
    rc, out = cekici_sahte(scripts, proje, ["ZCL_SD001_W", "--type", "auto", "--file",
                                            str(wt / W_ / "ZCL_SD001_W.abap")], canli_w, ara)
    st = store(proje).get("objects") or {}
    k_wt, k_ana = _anahtar(scripts, proje, [wt / W_ / "ZCL_SD001_W.ccimp.abap",
                                            proje / W_ / "ZCL_SD001_W.ccimp.abap"])
    kontrol("K3 son-tur-1: `--type auto` SINIF dali da alt-include'lari --file agacinda ceker "
            "(ANA agaca yazma/damga YOK)",
            rc == 0 and (wt / W_ / "ZCL_SD001_W.ccimp.abap").read_text(encoding="utf-8") == "* CANLI W impl\n"
            and k_wt in st and k_ana not in st
            and (proje / W_ / "ZCL_SD001_W.ccimp.abap").read_bytes() == ana_w,
            f"rc={rc} wt_damga={k_wt in st} ana_damga={k_ana in st} {out[-220:]!r}")

    # ── 2: `..` içeren yol + harf farkı (gerçek kapı alt süreci) ────────────────
    proje = proje_kur(kum / "proje6")
    dz = proje / "SOURCE_CODES" / "SD" / "ZSD001_CLC"
    duz = dz / "classes" / "ZCL_SD001_X.ccimp.abap"
    # `docs`/`DOCS` GERÇEK (boş) dizin: POSIX `a/docs/../b`yi fiziksel çözer (docs yoksa ENOENT),
    # Win32 sözdizimsel çözer — dizin varken ikisi AYNI dosyayı açar ⇒ vektör CI'da (ubuntu) da
    # koşar. Harf-duyarsız FS'te `DOCS` ile `docs` aynı dizindir (exist_ok).
    for d in ("docs", "DOCS"):
        (dz / d).mkdir(exist_ok=True)
    rc0, _ = kapi(scripts, proje, duz)
    rc1, _ = kapi(scripts, proje, str(dz) + "/docs/../classes/ZCL_SD001_X.ccimp.abap")
    rc2, _ = kapi(scripts, proje, str(dz) + "/DOCS/../classes/ZCL_SD001_X.ccimp.abap")
    kontrol("G1 takip-2: `docs/..` / `DOCS/..` yol -> BLOK (sahte-muaf YOK; kontrol `..`'suz = 2)",
            rc0 == 2 and rc1 == 2 and rc2 == 2, f"duz={rc0} docs/..={rc1} DOCS/..={rc2}")
    nn = str(dz) + "/docs/../classes/ZCL_SD001_X.ccimp.abap"
    rc, out = cekici(scripts, proje, "ZCL_SD001_X", "--type", "implementations", "--offline",
                     "--file", nn)
    st = store(proje).get("objects") or {}
    kontrol("G2 takip-2: sap_sync_pull `--file` `..`li yol -> kabul + damga KANONIK anahtarda",
            rc == 0 and _anahtar(scripts, proje, [duz])[0] in st, f"rc={rc} {out[-160:]!r}")
    # G3 — harf farkı YALNIZ harf-duyarsız FS'te anlamlıdır (harf-duyarlı FS'te harf-farklı yol
    # BAŞKA, var olmayan bir dosyadır → kapı "yeni dosya" der). FS YOKLANIR, görünür ATLANDI.
    proje_b = proje_kur(kum / "proje6b")
    duz_b = proje_b / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "classes" / "ZCL_SD001_X.ccimp.abap"
    harf = str(duz_b).replace("SOURCE_CODES", "source_codes").replace("classes", "CLASSES")
    if not Path(harf).exists():
        print("  [ATLANDI] G3 harf-farkli yol (harf duyarli FS — ayak harf-duyarsiz FS'e ozgu)")
    else:
        rc_hb, _ = kapi(scripts, proje_b, harf)
        rc_d, _ = cekici(scripts, proje_b, "ZCL_SD001_X", "--type", "implementations", "--offline",
                         "--file", str(duz_b))
        rc_h, _ = kapi(scripts, proje_b, harf)
        kontrol("G3 takip-2 (sozlesme capasi): harf-farkli yol -> damgasizken BLOK, kanonik damga okunur",
                rc_hb == 2 and rc_d == 0 and rc_h == 0, f"damgasiz={rc_hb} damga={rc_d} damgali={rc_h}")

    # ── 5: `--file` tip eşanlamlıları (`_TYPE_TO_EXTENSIONS`ten türetilir) ───────
    proje = proje_kur(kum / "proje7")
    bdef = proje / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "cds" / "ZSD001_I_X.bdef"
    sonuc = {}
    for tip in ("bdef", "behaviordefinition", "bdo", "srvd"):
        rc, out = cekici(scripts, proje, "ZSD001_I_X", "--type", tip, "--offline", "--file", str(bdef))
        sonuc[tip] = rc
    kontrol("F7 takip-5: --file .bdef + behaviordefinition/bdo (esanlamli) -> kabul",
            sonuc["bdef"] == 0 and sonuc["behaviordefinition"] == 0 and sonuc["bdo"] == 0, f"{sonuc}")
    kontrol("F8 takip-5 KONTROL: --file .bdef + srvd (farkli tip) -> hala [FAIL]",
            sonuc["srvd"] == 1, f"{sonuc}")
    # F9 — F7'nin ÇEVRİMİÇİ karşılığı: eşanlamlı ad çekme yoluna KANONİK adla gider (sahte ADT).
    canli_b = {"/sap/bc/adt/bo/behaviordefinitions/zsd001_i_x/source/main":
               "managed implementation in class zbp; // canli\n"}
    cevrim = {}
    for tip in ("behaviordefinition", "bdo"):
        subprocess.run(["git", "-C", str(proje), "checkout", "--", str(bdef)], capture_output=True)
        rc, out = cekici_sahte(scripts, proje, ["ZSD001_I_X", "--type", tip, "--file", str(bdef)],
                               canli_b)
        cevrim[tip] = (rc, "[OK]" in out and "yeni obje" not in out,
                       bdef.read_text(encoding="utf-8").endswith("// canli\n"), out[-160:])
    kontrol("F9 son-tur-2: cevrimici `--type behaviordefinition|bdo --file .bdef` -> bdef ucundan "
            "cekilir + yazilir ('yeni obje olabilir' YOK)",
            all(v[0] == 0 and v[1] and v[2] for v in cevrim.values()), f"{cevrim}")
    kanonik_tip_saf(scripts, proje)


# F10 — `_kanonik_tip` SAF fonksiyon vektörü (kapanış turu). Ad kümesi KODDAN türetilir (elle
# liste YOK): `_TYPE_TO_EXTENSIONS` anahtarları ∪ `OBJECT_TYPES` ∪ takma adlar (anahtar+hedef) ∪
# sınıf alt-include adları (tür+takma) ∪ `auto`. Dosya sistemine dokunmaz (yalnız import + çağrı).
_KANONIK_KOD = r'''
import json, sys
sys.path.insert(0, %r)
import sap_sync_pull as S
import object_types as O
import source_drift as D
kaynak = {
    "_TYPE_TO_EXTENSIONS": set(D._TYPE_TO_EXTENSIONS),
    "OBJECT_TYPES": set(O.OBJECT_TYPES),
    "OBJECT_TYPE_ALIASES": set(O.OBJECT_TYPE_ALIASES) | set(O.OBJECT_TYPE_ALIASES.values()),
    "CLASS_INCLUDE": set(O.CLASS_INCLUDE_TYPES) | set(O.CLASS_INCLUDE_ALIASES),
    "auto": {"auto"},
}
adlar = sorted(set().union(*kaynak.values()))
print(json.dumps({"say": {k: len(v) for k, v in kaynak.items()},
                  "sonuc": {n: S._kanonik_tip(n) for n in adlar}}))
'''
# Beklenen tek istisna: `normalize_object_type`ın ÇÖZEMEDİĞİ, uzantı kümesi açık bir tiple aynı adlar.
_KANONIK_ESANLAM = {"bdo": "bdef", "behaviordefinition": "bdef", "servicebinding": "srvb"}
_KANONIK_ALT_SINIR = 40      # 2026-09-26 ölçümü 57 ad; altına düşerse türetme kırılmıştır


def kanonik_tip_saf(scripts: Path, proje: Path) -> None:
    r = subprocess.run([sys.executable, "-c", _KANONIK_KOD % str(scripts)], capture_output=True,
                       env=_env(proje), cwd=str(proje), timeout=60)
    try:
        d = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
    except Exception:
        # yalnız SON stderr satırı: alıntılanan "Traceback" başlığı bataryada COKTU sanılmasın
        son = [x for x in r.stderr.decode("utf-8", "replace").splitlines() if x.strip()][-1:]
        d = {"say": {}, "sonuc": {}, "hata": "alt-surec: " + (son[0][-200:] if son else "<cikti yok>")}
    sonuc, say = d.get("sonuc") or {}, d.get("say") or {}
    beklenen = {n: _KANONIK_ESANLAM.get(n, n) for n in sonuc}
    sapma = {n: v for n, v in sonuc.items() if v != beklenen[n]}
    eksik_esanlam = sorted(set(_KANONIK_ESANLAM) - set(sonuc))
    bos_kaynak = sorted(k for k, v in say.items() if not v) or ([] if say else ["<olculemedi>"])
    print(f"  [KAPSAM] F10 _kanonik_tip: {len(sonuc)} ad denendi (kaynak basina: {say}; "
          f"esanlam {sum(1 for n in sonuc if n in _KANONIK_ESANLAM)}, "
          f"kimlik {sum(1 for n in sonuc if n not in _KANONIK_ESANLAM)}; "
          f"alt sinir {_KANONIK_ALT_SINIR})")
    kontrol("F10 kapanis: _kanonik_tip cozulebilen HER adi DOKUNMAZ + yalniz bdo/behaviordefinition"
            "->bdef, servicebinding->srvb (ad kumesi koddan; bos/kucuk kume FAIL)",
            len(sonuc) >= _KANONIK_ALT_SINIR and not bos_kaynak and not eksik_esanlam and not sapma,
            f"ad={len(sonuc)} bos_kaynak={bos_kaynak} eksik_esanlam={eksik_esanlam} "
            f"sapma={sapma} {d.get('hata', '')}")


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
        duzeltme_turu(scripts, kum)
        takip_turu(scripts, kum)
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
