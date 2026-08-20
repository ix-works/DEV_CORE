#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K6 — `_ACTIVATION_URI_SEG` + profil fail-closed'in SAP'siz BIRIM TESTI.

=== KOK (kayit satir 16) ===
Bu iki mekanizmanin tek kaniti CANLI kosumdu. Yani:
  - CI'da (SAP yok) HIC olculmuyorlardi,
  - bir regresyon ancak birisi gercek bir SAP'ye push denedigi an ortaya cikardi,
  - ve `profil_tool` fail-closed'i yanlislikla ACILSA bunu kimse fark etmezdi
    (fail-open sessizdir: tool'lar gorunur, kimse "neden gorunuyor" diye sormaz).

Ikisi de SAF MANTIK: `_activation_uri` bir sozluk aramasi + URL kacisi;
`uygun_mu`/`aktif_profil` bir enum dogrulamasi. Aglari YOK ⇒ offline olculebilirler.
Bu korpus o olcumu kalicilastirir.

⚠ NE OLCULMEZ (durustluk notu): gercek `/activation` POST'unun SAP tarafinda kabul
   edilmesi bu korpusun KAPSAMI DISINDADIR — burada URI'nin SOZLESMESI olculur,
   sunucunun yaniti degil. Canli kanit `B11` recetesindeki kosumdur.

  A1..A5   `_activation_uri`: bilinen tip · namespace kacisi · BILINMEYEN tip -> None
  A6 ⭐    KAPSAM: sozlukteki HER tip iyi-bicimli URI uretir ve HICBIRI `/source/main`
           tasimaz (bu ucun degismezi: aktivasyon kaynak ucuna GITMEZ)
  B1..B5   `uygun_mu` fail-closed cebiri (None · enum-disi · eslesme · eslesmeme)
  B6..B8   `aktif_profil`: project.yaml yok / uydurma / gecerli
  B9 ⭐    KABLOLAMA: profil cozulemiyorken `profil_tool` tool'u REGISTER ETMEZ
           (kod dogru olsa da kablolama kopuk olabilir — ayri olculur)
  M1..M4   fix'i sok -> korpus KIRMIZI olmali (IZOLE agac kopyasinda)
  F1 ⭐    IZOLASYON: korpus GERCEK atom.py/_profile.py dosyalarini DEGISTIRMEZ

Kosum: python tests/fixtures/mcp_profil_aktivasyon_offline/run.py     (exit 0 = PASS)
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
ATOM = KOK / "mcp_servers" / "sap_adt" / "tools" / "atom.py"
PROFIL = KOK / "mcp_servers" / "sap_adt" / "_profile.py"

PROJE_YAML = ("sap_profile: {p}\nrelease: '2025'\nmaster_language: TR\n"
              "source_root: SOURCE_CODES\n")


def _kum(profil: str | None) -> Path:
    d = Path(tempfile.mkdtemp(prefix="k6_"))
    if profil is not None:
        (d / "project.yaml").write_text(PROJE_YAML.format(p=profil), encoding="utf-8")
    return d


def _alt_surecte(kod: str, kum: Path, agac_kok: Path = KOK) -> tuple[int, str]:
    """Kodu TAZE bir yorumlayicida kos — modul-seviyesi profil cozumu import ANINDA olur,
    yani ayni surecte ikinci bir profille olcum YAPILAMAZ (bayat modul tuzagi)."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["CLAUDE_PROJECT_DIR"] = str(kum)
    env["PYTHONPATH"] = str(agac_kok)
    p = subprocess.run([sys.executable, "-c", kod], cwd=str(kum), env=env,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# Olcum kodu alt-surecte kosar; sonuclari `SONUC:` satirlariyla geri tasir.
OLCUM = r'''
import sys
sys.path.insert(0, r"{kok}")
import mcp_servers.sap_adt.tools.atom as A
from mcp_servers.sap_adt._profile import aktif_profil, uygun_mu

def s(ad, deger):
    print("SONUC:%s=%r" % (ad, deger))

s("A1", A._activation_uri("ZCL_X", "class"))
s("A2", A._activation_uri("/DMO/ZTEST", "ddls"))
s("A3", A._activation_uri("ZCL_X", "uydurma_tip"))
s("A4", A._activation_uri("ZCL_X", "  CLASS  "))
s("A5", A._activation_uri("ZCL_X", ""))
kotu = []
for tip in A._ACTIVATION_URI_SEG:
    u = A._activation_uri("ZTEST", tip)
    if not u or not u.startswith("/sap/bc/adt/") or "/source/main" in u or "//" in u[12:]:
        kotu.append((tip, u))
s("A6", kotu)
s("B1", uygun_mu(("all",), None))
s("B2", uygun_mu(("all",), "uydurma"))
s("B3", uygun_mu(("all",), "s4_private"))
s("B4", uygun_mu(("ecc",), "s4_private"))
s("B5", uygun_mu(("s4_private", "ecc"), "ecc"))
s("PROFIL", aktif_profil())
'''

# B9: fail-closed KABLOLAMASI — `profil_tool` gercekten register etmiyor mu?
KABLOLAMA = r'''
import sys
sys.path.insert(0, r"{kok}")
import mcp_servers.sap_adt.tools.atom as A       # import log satirlarini uretir
from mcp_servers.sap_adt._app import mcp
import asyncio
try:
    araclar = asyncio.run(mcp.list_tools())
    adlar = sorted(getattr(t, "name", str(t)) for t in araclar)
except Exception as e:
    adlar = ["<LISTELENEMEDI:%s>" % type(e).__name__]
print("SONUC:ARACLAR=%r" % (adlar,))
'''


def _oku(cikti: str) -> dict:
    out = {}
    for satir in cikti.splitlines():
        if satir.startswith("SONUC:") and "=" in satir:
            ad, ham = satir[len("SONUC:"):].split("=", 1)
            try:
                out[ad] = eval(ham, {"__builtins__": {}}, {})  # noqa: S307 (sabit repr)
            except Exception:
                out[ad] = ham
    return out


def _izole_agac() -> Path:
    """Mutasyon icin AGAC KOPYASI: `mcp_servers` + `scripts` (import zinciri icin).

    `_profile.py` komsu `scripts/utils`'i `__file__.parents[2]/scripts`ten cozer;
    yalniz `mcp_servers` kopyalanirsa `aktif_profil()` HER ZAMAN None doner ve
    her mutasyon "yakalandi" gorunur (SAHTE-KIRMIZI). Iki agac birlikte kopyalanir.
    """
    kok = Path(tempfile.mkdtemp(prefix="k6izo_"))
    for alt in ("mcp_servers", "scripts"):
        shutil.copytree(KOK / alt, kok / alt,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
    return kok


def senaryolar(agac_kok: Path = KOK) -> list[tuple[str, bool, str]]:
    r: list[tuple[str, bool, str]] = []

    def ekle(ad: str, ok: bool, detay: str = "") -> None:
        r.append((ad, ok, detay))

    kum = _kum("s4_private")
    try:
        rc, out = _alt_surecte(OLCUM.format(kok=str(agac_kok)), kum, agac_kok)
        d = _oku(out)
        if rc != 0 or "A1" not in d:
            ekle("A/B OLCUM KOSTU MU (cokme != FAIL)", False, f"rc={rc} · {out[-400:]!r}")
            return r
        ekle("A1 bilinen tip -> dogru URI (ad kucuk harfe iner)",
             d["A1"] == "/sap/bc/adt/oo/classes/zcl_x", repr(d["A1"]))
        # ⚠ Toplam `/` SAYMA: segment'in kendisi cok parcali olabilir
        # ("ddic/ddl/sources") -> sayi tipe gore degisir ve capa yaniltir.
        # Dogru olcut: AD kismi ham `/` TASIMAZ, `%2F` olarak kacislanmistir.
        ekle("A2 namespace'li ad KACISLANIR (`/` -> %2F; safe='' sozlesmesi)",
             isinstance(d["A2"], str)
             and d["A2"] == "/sap/bc/adt/ddic/ddl/sources/%2Fdmo%2Fztest",
             repr(d["A2"]))
        ekle("A3 ⭐ FP capasi: BILINMEYEN tip -> None (uydurma URI URETMEZ)",
             d["A3"] is None, repr(d["A3"]))
        ekle("A4 tip buyuk/kucuk + bosluk toleransi",
             d["A4"] == "/sap/bc/adt/oo/classes/zcl_x", repr(d["A4"]))
        ekle("A5 bos tip -> None", d["A5"] is None, repr(d["A5"]))
        ekle("A6 ⭐ KAPSAM: sozlukteki HER tip iyi-bicimli URI uretir; hicbiri "
             "`/source/main` tasimaz (aktivasyon kaynak ucuna GITMEZ)",
             d["A6"] == [], f"bozuk={d['A6']}")
        ekle("B1 ⭐ fail-closed: profil None -> hicbir tool uygun DEGIL",
             d["B1"] is False, repr(d["B1"]))
        ekle("B2 ⭐ SINIR: enum-DISI profil + available_on=('all',) -> yine False "
             "(2026-07-10'da yakalanan sinif)",
             d["B2"] is False, repr(d["B2"]))
        ekle("B3 FP capasi: gecerli profil + 'all' -> True (kapi kapali kalmiyor)",
             d["B3"] is True, repr(d["B3"]))
        ekle("B4 eslesmeyen profil -> False", d["B4"] is False, repr(d["B4"]))
        ekle("B5 listede olan profil -> True", d["B5"] is True, repr(d["B5"]))
        ekle("B8 FP capasi: gecerli project.yaml -> aktif_profil()='s4_private'",
             d["PROFIL"] == "s4_private", repr(d["PROFIL"]))
    finally:
        shutil.rmtree(kum, ignore_errors=True)

    # B6/B7: project.yaml YOK / UYDURMA
    for etiket, profil, beklenen in (("B6 project.yaml YOK", None, None),
                                     ("B7 uydurma profil", "uydurma_profil", None)):
        kum = _kum(profil)
        try:
            rc, out = _alt_surecte(OLCUM.format(kok=str(agac_kok)), kum, agac_kok)
            d = _oku(out)
            ekle(f"{etiket} -> aktif_profil()=None (fail-closed sinyali)",
                 rc == 0 and d.get("PROFIL", "?") == beklenen,
                 f"rc={rc} · profil={d.get('PROFIL', '<OKUNAMADI>')!r}")
        finally:
            shutil.rmtree(kum, ignore_errors=True)

    # B9: KABLOLAMA — kod dogru olsa da register yolu kopuk olabilir
    kum_yok = _kum(None)
    kum_var = _kum("s4_private")
    try:
        rc1, out1 = _alt_surecte(KABLOLAMA.format(kok=str(agac_kok)), kum_yok, agac_kok)
        rc2, out2 = _alt_surecte(KABLOLAMA.format(kok=str(agac_kok)), kum_var, agac_kok)
        d1, d2 = _oku(out1), _oku(out2)
        a1 = d1.get("ARACLAR", ["<YOK>"])
        a2 = d2.get("ARACLAR", ["<YOK>"])
        gizli1 = "adt_activate" not in a1
        acik2 = "adt_activate" in a2
        ekle("B9 ⭐ KABLOLAMA: profil cozulemiyorken `adt_activate` REGISTER EDILMEZ; "
             "gecerli profilde EDILIR (fail-closed hem kapali hem ACILABILIR)",
             gizli1 and acik2,
             f"profilsiz={len(a1)} arac (gizli={gizli1}) · profilli={len(a2)} arac (acik={acik2})")
    finally:
        shutil.rmtree(kum_yok, ignore_errors=True)
        shutil.rmtree(kum_var, ignore_errors=True)
    return r


MUTASYONLAR = [
    ("M1 ⭐ `uygun_mu`: 'all' kontrolunu profil dogrulamasindan ONCE yap "
     "(2026-07-10 bug'inin birebir hali)", "profil",
     lambda s: s.replace(
         '    if profil is None or profil not in GECERLI_PROFILLER:\n'
         '        return False\n    return "all" in available_on or profil in available_on\n',
         '    if "all" in available_on:\n        return True\n'
         '    if profil is None or profil not in GECERLI_PROFILLER:\n'
         '        return False\n    return profil in available_on\n')),
    ("M2 `aktif_profil`: enum dogrulamasini sok (her deger gecerli sayilir)", "profil",
     lambda s: s.replace(
         "    if not p or p not in GECERLI_PROFILLER:\n        return None\n",
         "    if not p:\n        return None\n")),
    ("M3 `_activation_uri`: bilinmeyen tipe URI UYDUR (None yerine tahmin)", "atom",
     lambda s: s.replace(
         "    seg = _ACTIVATION_URI_SEG.get((object_type or \"\").lower().strip())\n"
         "    if not seg:\n        return None\n",
         "    seg = _ACTIVATION_URI_SEG.get((object_type or \"\").lower().strip())\n"
         "    if not seg:\n        seg = (object_type or \"x\").lower().strip()\n")),
    ("M4 `_activation_uri`: `safe='/'` (namespace kacisi kaybolur)", "atom",
     lambda s: s.replace("quote(name.lower(), safe='')", "quote(name.lower(), safe='/')")),
]


def main() -> int:
    print("=" * 78)
    print("mcp_profil_aktivasyon_offline — K6: SAP'siz birim testi")
    print("=" * 78)
    for eksik in (ATOM, PROFIL):
        if not eksik.is_file():
            print(f"FAIL — dosya yok: {eksik}")
            return 1

    ham = {"atom": ATOM.read_text(encoding="utf-8"),
           "profil": PROFIL.read_text(encoding="utf-8")}
    # ⛔ 2026-08-20 DERSI: mutasyon GERCEK kaynaga YAZILMAZ. Ilk surum atom.py ve
    #    _profile.py'yi yerinde ezip finally'de geri yaziyordu; art arda kosumlarda
    #    kalinti birikti ve _profile.py bir ara **fail-closed enum dogrulamasi
    #    SOKULMUS** halde diskte kaldi (komsu korpus fs_docstd de kirlendi).
    #    Kalici cozum: mutasyon IZOLE bir AGAC KOPYASINDA yasar; gercek agac
    #    korpus boyunca SALT-OKUNURDUR. (Kanit: F1 vektoru.)
    yol = {"atom": ATOM, "profil": PROFIL}

    sonuc = senaryolar()
    kirik = [(a, d) for a, ok, d in sonuc if not ok]
    for ad, ok, detay in sonuc:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
        if not ok:
            print("         gorulen: %s" % detay)
    print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

    print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
    mut_kirik, yama_kirik = [], []
    for ad, hedef, mut in MUTASYONLAR:
        bozuk = mut(ham[hedef])
        if bozuk == ham[hedef]:
            print("  [YAMA TUTMADI] %s" % ad)
            yama_kirik.append(ad)
            continue
        izole = None
        try:
            izole = _izole_agac()
            (izole / yol[hedef].relative_to(KOK)).write_text(bozuk, encoding="utf-8")
            m_res = senaryolar(izole)
            yakalandi = any(not ok for _, ok, _ in m_res)
            kacan = [a for a, ok, _ in m_res if not ok]
        except BaseException as e:  # noqa: BLE001
            yakalandi, kacan = False, []
            print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
        finally:
            if izole is not None:
                shutil.rmtree(izole, ignore_errors=True)
        print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
        if yakalandi:
            print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
        else:
            mut_kirik.append(ad)

    # F1 ⭐ SALT-OKUNURLUK KANITI: korpus GERCEK agaci degistirmemis olmali.
    # (Bu satir bir "temizlik kontrolu" degil, bir DEGISMEZDIR: mutasyon izole
    #  agacta yasar, dolayisiyla burada fark CIKMAMALIDIR.)
    for k, p in yol.items():
        if p.read_text(encoding="utf-8") != ham[k]:
            print(f"FAIL — F1: {p} korpus tarafindan DEGISTIRILDI (izolasyon kirik)")
            return 1
    print("  [PASS] F1 ⭐ izolasyon: gercek atom.py/_profile.py korpus boyunca DEGISMEDI")

    print("\n" + "=" * 78)
    if kirik or mut_kirik or yama_kirik:
        if kirik:
            print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
        if mut_kirik:
            print("FAIL — mutasyon KACTI: %s" % ", ".join(mut_kirik))
        if yama_kirik:
            print("FAIL — mutasyon yamasi kaynaga UYMADI: %s" % ", ".join(yama_kirik))
        return 1
    print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(MUTASYONLAR)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
