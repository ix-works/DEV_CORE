#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""q405_kapsam_bosluklari fixture — DEV_CORE #405: KAPSAM BOŞLUKLARI (2026-11-08, kullanıcı onaylı).

NEDEN VAR
  Aynı sınıfın beş yüzü: kontrol bir girdiyi HİÇ ölçmüyor ama sonuç "temiz" görünüyordu.
    ⑦  namespace'li dosya adı (`#xns#x` · `%23xns%23x` · `(xns)x`) SAP adına çözülmüyordu ⇒
        `sap_sync_pull` `/XNS/X` + `#xns#x.tabl.ddl`'yi "başka objenin dosyası" diye reddediyor,
        kapı `#XNS#X` diye (tırnaksız → kabukta YORUM) komut öneriyor, drift denetimi `%23xns%23x`
        URL'iyle canlıda bulamayıp SESSİZCE atlıyordu. ⚠ GEVŞETME (bilinçli): yalnız `#ns#`↔`/NS/`
        eşdeğerliği; farklı ad (bug gate M1, 2026-09-26) AYNEN red — negatif vektörler M*.
    ①  `check_package_naming` `cds/` altında `*.asddls`/`*.asdcls`'ı görmüyordu; KAPSAM satırı yoktu.
    ②  `check_rap_managed_etag` etag'i dosyanın TAMAMINDA arıyordu: kökten `etag master` silinip
        çocukta `etag dependent` kalınca rc=0. Artık blok düzeyi (lider kararı C).
    ③  docstring `\w` → `python -W error` altında SyntaxError.
    ④  `check_cds_currency_reference` takma adsız (`kbetr,` / `konp.kbetr,`) elemanı saymıyordu.
    ⑤  `run_review` DCL'yi hiç ölçmediğini söylemiyordu.

DEĞİŞMEZLER (vektör kimliği → bölüm)
  ⑦ A*/M*/K*: `_dosya_tutarsizligi` ad eşdeğerliği + M1 reddi korunur · S*: `pbe_siniflandir` adı ·
     D*: `check_source_drift` adı · F*: kaynak/aday/alt-include bulucular · H*: kapının ve
     `sap_sync_pull`'un önerdiği komut kabukta güvenli, Z adında BAYT-AYNI · T*: tekrar komutu ·
     ML*: `check_sap_master_language` pozisyonel ad
  ① N*: tarama kapsamı, ÖLÇÜLEMEDİ dalı, KAPSAM satırı · O*: `check_object_in_correct_pkg` uzantı kümesi
  ② E*: blok düzeyi etag · ③ W1 · ④ C* · ⑤ R*
  KONTROL GRUBU (taban ağaçta da YEŞİL olmalı — taban ölçümü aşağıda, B-reçetesinde).

KULLANIM
  python tests/fixtures/q405_kapsam_bosluklari/run.py                 # tüm vektörler
  python tests/fixtures/q405_kapsam_bosluklari/run.py --mutasyon-<ad> # tek mutasyon (KIPLER)
  Mutasyon çıkışı (run_battery karar tablosu): 1 = ilan edilen küme TAM düştü · 2 = SAPMA ·
  3 = kurulamadı (çapa sayısı ≠ 1 / derlenmedi / alt süreç sayı vermedi).

ORTAM: her vektör ALT SÜREÇTE, `cwd` + `CLAUDE_PROJECT_DIR` = geçici kum; `ADT_SAP_*` sahte adres.
SAP'ye bağlanan yol koşmaz: `_ic.py` `sap_client`/`sap_adt_lib`'i sahte modülle değiştirir.
Adlar yer tutucu (`/XNS/`, `ZSD001_…`, `ZBASKA_…`).
"""
from __future__ import annotations

import json
import os
import re
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

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]
SCR = REPO / "scripts"
VAL = SCR / "validators"
if not (VAL / "run_review.py").is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")

S: list[tuple[str, bool, str]] = []
KUMLAR: list[Path] = []


def ekle(ad: str, ok: bool, ayrinti: str = "") -> None:
    S.append((ad, ok, ayrinti))


def _env(kum: Path) -> dict:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(kum)
    env.pop("IX_CEVRIMDISI", None)
    env.update(ADT_SAP_URL="https://sahte.invalid", ADT_SAP_CLIENT="000", ADT_SAP_USER="x",
               ADT_SAP_PASSWORD="x", PYTHONIOENCODING="utf-8")
    return env


def kos(kum: Path, betik: Path, *argv: str, stdin: str | None = None) -> tuple[int, str, str]:
    r = subprocess.run([sys.executable, str(betik), *argv], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120, cwd=str(kum), env=_env(kum),
                       input=stdin)
    return r.returncode, r.stdout, r.stderr


def ic(kum: Path, *argv: str):
    """`_ic.py` sondası → JSON sonucu; sonda çökerse ('COKTU', son satır) döner (vektör FAIL)."""
    rc, out, err = kos(kum, BURASI / "_ic.py", *argv)
    for satir in reversed(out.splitlines()):
        if satir.startswith("@@"):
            return json.loads(satir[2:])
    son = [x for x in (out + err).splitlines() if x.strip()][-1:] or ["-"]
    return ["COKTU", f"rc={rc} {son[0][:200]}"]


def yaz(yol: Path, metin: str) -> Path:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(metin.encode("utf-8"))      # LF — satır sonu ekseni bu fixture'ın konusu değil
    return yol


def yeni_kum(ad: str) -> Path:
    kum = Path(tempfile.mkdtemp(prefix=f"q405_{ad}_"))
    KUMLAR.append(kum)
    yaz(kum / "project.yaml", "source_root: SOURCE_CODES\nsap_profile: s4_private\n")
    return kum


TABL = "define table /xns/x {\n  key mandt : mandt not null;\n  key a : abap.char(1) not null;\n}\n"
TABL_Z = TABL.replace("/xns/x", "zt_x")


# ── ⑦ namespace'li dosya adı ─────────────────────────────────────────────────────
def bolum_ns() -> None:
    kum = yeni_kum("ns")
    paket = kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC"
    ns = yaz(paket / "tables" / "#xns#x.tabl.ddl", TABL)
    z = yaz(paket / "tables" / "zt_x.tabl.ddl", TABL_Z)
    yaz(paket / "classes" / "#xns#cl_x.clas.abap", "CLASS /xns/cl_x DEFINITION.\nENDCLASS.\n")
    yaz(paket / "classes" / "#xns#cl_x.clas.locals_imp.abap", "* yerel\n")
    kum2 = yeni_kum("ns2")
    p2 = kum2 / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "tables"
    url = yaz(p2 / "%23xns%23x.tabl.ddl", TABL)
    aff = yaz(p2 / "(xns)x.tabl.ddl", TABL)
    erp = str(kum / "SOURCE_CODES")

    def kabul(vid, obj, dosya, k=kum):
        r = ic(k, "tutarsizlik", obj, "auto", str(dosya))
        ekle(vid, r == "", f"{obj} + {dosya.name} -> {r!r} (bos bekleniyordu)")

    def red(vid, obj, dosya):
        r = ic(kum, "tutarsizlik", obj, "auto", str(dosya))
        ekle(vid, isinstance(r, str) and "başka objenin dosyası" in r,
             f"{obj} + {dosya.name} -> {r!r} (M1 reddi bekleniyordu)")

    kabul("A1", "/XNS/X", ns)            # eski kod: "obje adı '#XNS#X' taşıyor" → RED
    kabul("A1b", "#XNS#X", ns)           # KONTROL: eski kod da kabul ediyordu
    kabul("A2", "/XNS/X", url, kum2)     # URL-kodlu abapGit adı
    kabul("A3", "/XNS/X", aff, kum2)     # AFF `(ns)x`
    kabul("A4", "/xns/x", ns)            # küçük harfli SAP adı
    kabul("A5", "#xns#x", ns)            # ham dosya-adı biçimi (kapının önerdiği) — KONTROL
    red("M1", "/XNS/Y", ns)              # farklı nesne adı
    red("M2", "/YNS/X", ns)              # farklı namespace
    red("M3", "ZCL_BASKA", ns)           # namespace'siz başka nesne (bug gate M1'in kendisi)
    red("M4", "#XNS#Y", ns)              # ham biçimde farklı ad
    kabul("K1", "ZT_X", z)               # KONTROL: Z adı
    red("K2", "ZT_Y", z)                 # KONTROL: Z adında M1

    r = ic(kum, "pbe", str(ns))
    ekle("S1", isinstance(r, dict) and r.get("ad") == "/XNS/X", f"pbe_siniflandir ad -> {r!r}")
    r = ic(kum, "pbe", str(z))
    ekle("S2", isinstance(r, dict) and r.get("ad") == "ZT_X", f"pbe_siniflandir Z ad -> {r!r}")
    r = ic(kum, "drift_ad", str(ns))
    ekle("D1", r == "/XNS/X", f"check_source_drift._object_name_from_file -> {r!r}")
    r = ic(kum, "drift_ad", str(z))
    ekle("D2", r == "ZT_X", f"Z -> {r!r}")
    r = ic(kum, "bul", "/XNS/X", erp)
    ekle("F1", r == "#xns#x.tabl.ddl", f"find_repo_source_file(/XNS/X) -> {r!r}")
    r = ic(kum, "bul", "#XNS#X", erp)
    ekle("F1b", r == "#xns#x.tabl.ddl", f"find_repo_source_file(#XNS#X) -> {r!r}")
    r = ic(kum, "bul", "ZT_X", erp)
    ekle("F1z", r == "zt_x.tabl.ddl", f"KONTROL Z -> {r!r}")
    r = ic(kum, "bul", "/XNS/Y", erp)
    ekle("Fneg", r is None, f"KONTROL farklı ad bulunmamalı -> {r!r}")
    r = ic(kum, "adaylar", "/XNS/X", erp)
    ekle("F2", r == ["#xns#x.tabl.ddl"], f"_pbe_adaylari(/XNS/X) -> {r!r}")
    r = ic(kum, "includes", "/XNS/CL_X", erp)
    ekle("F3", isinstance(r, list) and [x[1] for x in r] == ["#xns#cl_x.clas.locals_imp.abap"],
         f"find_repo_class_includes(/XNS/CL_X) -> {r!r}")

    # H — kapının önerdiği komut (PreToolUse yükü stdin'den; gerçek giriş noktası)
    def kapi(dosya):
        yuk = json.dumps({"tool_name": "Edit", "session_id": "SID",
                          "tool_input": {"file_path": str(dosya)}})
        return kos(kum, SCR / "hooks" / "pull_before_edit.py", stdin=yuk)

    rc, _o, err = kapi(ns)
    ekle("H1", rc == 2 and f'sap_sync_pull.py "#xns#x" --type auto --file "{ns}" --session SID' in err,
         f"rc={rc} komut satırı tırnaklı ham ad taşımıyor: {err[:300]!r}")
    ekle("H1n", "namespace'li nesne /XNS/X" in err, f"namespace notu yok: {err[:300]!r}")
    rc, _o, err = kapi(z)
    satirlar = err.splitlines()
    ekle("H2", rc == 2 and len(satirlar) > 1
         and satirlar[1] == f'   python core/scripts/sap_sync_pull.py ZT_X --type auto --file "{z}" --session SID'
         and "namespace'li" not in err,
         f"Z komutu bayt-aynı değil: {satirlar[1:2]!r}")

    # sap_sync_pull gerçek giriş noktası — --offline (SAP'siz)
    rc, out, _e = kos(kum, SCR / "sap_sync_pull.py", "/XNS/X", "--type", "auto", "--file", str(ns),
                      "--offline", "--session", "SID")
    ekle("H3", rc == 0 and "[OFFLINE]" in out, f"/XNS/X --offline rc={rc} {out[:200]!r}")
    rc, out, _e = kos(kum, SCR / "sap_sync_pull.py", "#xns#x", "--type", "auto", "--file", str(ns),
                      "--offline", "--session", "SID")
    ekle("H3b", rc == 0 and "[OFFLINE]" in out, f"KONTROL #xns#x --offline rc={rc} {out[:200]!r}")
    # canlı yol: ADT araması SAP adıyla yapılır (sahte istemci aranan adı kaydeder)
    r = ic(kum, "auto_stub", "#xns#x", str(ns))
    ekle("H4", isinstance(r, dict) and r.get("aranan") == ["/XNS/X"],
         f"#xns#x argümanıyla ADT araması -> {r!r}")

    r = ic(kum, "komut_adi", "#xns#x", "/XNS/X")
    ekle("T1", r == '"#xns#x"', f"_komut_adi(ham=#xns#x) -> {r!r}")
    r = ic(kum, "komut_adi", "/XNS/X", "/XNS/X")
    ekle("T2", r == '"%2Fxns%2Fx"', f"_komut_adi(ham=/XNS/X) -> {r!r}")
    r = ic(kum, "komut_adi", "ZT_X", "ZT_X")
    ekle("T3", r == "ZT_X", f"KONTROL Z -> {r!r}")
    r = ic(kum, "sonuc", "#xns#x", "/XNS/X")
    ekle("T4", isinstance(r, dict)
         and 'sap_sync_pull.py "#xns#x" --type auto --file "P" --force' in r.get("out", ""),
         f"_sonuc tekrar komutu -> {r!r}")
    r = ic(kum, "sonuc", "/XNS/X", "/XNS/X")
    ekle("T5", isinstance(r, dict)
         and 'sap_sync_pull.py "%2Fxns%2Fx" --type auto --file "P" --force' in r.get("out", ""),
         f"_sonuc tekrar komutu (url) -> {r!r}")
    r = ic(kum, "sonuc", "ZT_X", "ZT_X")
    ekle("T6", isinstance(r, dict)
         and "sap_sync_pull.py ZT_X --type auto --file \"P\" --force" in r.get("out", ""),
         f"KONTROL Z tekrar komutu -> {r!r}")

    ddl_ns = yaz(paket / "cds" / "#xns#i_x.ddls.asddls",
                 "define view entity /XNS/I_X as select from t000 { key mandt }\n")
    ddl_z = yaz(paket / "cds" / "zsd001_i_x.ddls.asddls",
                "define view entity ZSD001_I_X as select from t000 { key mandt }\n")
    r = ic(kum, "ml", str(ddl_ns))
    ekle("ML1", isinstance(r, dict) and r.get("aranan") == ["/XNS/I_X"], f"master_language ns -> {r!r}")
    r = ic(kum, "ml", str(ddl_z))
    ekle("ML2", isinstance(r, dict) and r.get("aranan") == ["zsd001_i_x"], f"KONTROL Z (aynen) -> {r!r}")


# ── ① check_package_naming + check_object_in_correct_pkg ────────────────────────
RULES_Z = ("# ZSD001_CLC\n\n## Naming\n\n| Obje tipi | Aciklama | Regex |\n|---|---|---|\n"
           "| CDS view | I/C | `^ZSD001_[IC]_[A-Z0-9_]+$` |\n\n## Diger\n")
RULES_NS = ("# #XNS#SD001\n\n## Naming\n\n| Obje tipi | Aciklama | Regex |\n|---|---|---|\n"
            "| CDS view abapgit | ham | `^#XNS#I_GOOD$` |\n"
            "| CDS view sap | cozulmus | `^/XNS/C_[A-Z0-9_]+$` |\n\n## Diger\n")
DDL = "define view entity X as select from t000 { key mandt }\n"


def _kapsam(metin: str) -> str:
    m = re.search(r"KAPSAM: taranan .*", metin)
    return m.group(0) if m else ""


def bolum_naming() -> None:
    nm = VAL / "check_package_naming.py"
    # A: Z paketi, abapGit DDLS/DCL + atlanan uzantı + küçük harfli Z
    kum = yeni_kum("nmA")
    cds = kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "cds"
    yaz(cds.parent / ".rules.md", RULES_Z)
    for ad in ("ZSD001_X_BAD.ddls.asddls", "ZSD001_X_BAD2.dcls.asdcls", "ZSD001_I_GOOD.ddls.asddls",
               "ZSD001_C_X.ddlx.asddlxs", "zsd001_i_lower.cds", "ZSD001_I_OK.cds"):
        yaz(cds / ad, DDL)
    rc, out, err = kos(kum, nm)
    ekle("N1", rc == 1 and "ZSD001_X_BAD.ddls.asddls: hiçbir regex" in err, f"rc={rc} {err[:300]!r}")
    ekle("N2", "ZSD001_X_BAD2.dcls.asdcls: hiçbir regex" in err, f"{err[:300]!r}")
    ekle("N3", "ZSD001_I_GOOD" not in err, f"iyi ad listelendi: {err[:300]!r}")
    k = _kapsam(err)
    ekle("N4", "atlanan 1 (.ddlx.asddlxs×1)" in k, f"KAPSAM: {k!r}")
    ekle("N10", k.startswith("KAPSAM: taranan 5 dosya"), f"KAPSAM: {k!r}")
    ekle("N9", "zsd001_i_lower.cds: hiçbir regex" in err, f"KONTROL G1 küçük harfli Z: {err[:300]!r}")

    # B: Z paketi + namespace'li dosya, tablo XNS'i anmıyor ⇒ ÖLÇÜLEMEDİ (FAIL değil)
    kum = yeni_kum("nmB")
    cds = kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "cds"
    yaz(cds.parent / ".rules.md", RULES_Z)
    yaz(cds / "ZSD001_I_OK.cds", DDL)
    yaz(cds / "#xns#i_y.ddls.asddls", DDL)
    rc, out, err = kos(kum, nm)
    ekle("N5", rc == 0 and "ÖLÇÜLEMEDİ — ZSD001_CLC/cds/#xns#i_y.ddls.asddls → /XNS/I_Y" in out,
         f"rc={rc} {out[:300]!r} {err[:200]!r}")
    ekle("N12", "ÖLÇÜLEMEDİ 1" in _kapsam(out), f"OK satırında KAPSAM yok: {out[:300]!r}")

    # D (bug-gate F2): Z paketinde biçimi BOZUK namespace (2 harf · boş) ⇒ FAIL kalır (taban
    # davranışı); ÖLÇÜLEMEDİ yalnız GEÇERLİ namespace + tablo onu anmıyor (N5) dalıdır.
    kum = yeni_kum("nmD")
    cds = kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "cds"
    yaz(cds.parent / ".rules.md", RULES_Z)
    yaz(cds / "ZSD001_I_OK.cds", DDL)
    yaz(cds / "#ab#i_x.cds", DDL)
    yaz(cds / "##zsd001_i_q.cds", DDL)
    rc, out, err = kos(kum, nm)
    ekle("N13", rc == 1 and "#ab#i_x.cds: hiçbir regex" in err, f"2 harfli ns rc={rc} {out[:200]!r} {err[:300]!r}")
    ekle("N14", rc == 1 and "##zsd001_i_q.cds: hiçbir regex" in err, f"boş ns rc={rc} {out[:200]!r} {err[:300]!r}")

    # C: namespace paketi, tablo XNS'i anıyor (ham + çözülmüş biçim)
    kum = yeni_kum("nmC")
    cds = kum / "SOURCE_CODES" / "SD" / "#XNS#SD001" / "cds"
    yaz(cds.parent / ".rules.md", RULES_NS)
    yaz(cds / "#xns#i_good.ddls.asddls", DDL)      # ham biçim satırına uyar
    yaz(cds / "#xns#c_res.ddls.asddls", DDL)       # YALNIZ çözülmüş ad (`/XNS/C_RES`) uyar
    yaz(cds / "#xns#x_bad.ddls.asddls", DDL)       # hiçbirine uymaz; tablo XNS'i anıyor ⇒ FAIL
    rc, out, err = kos(kum, nm)
    ekle("N6", rc == 1 and "#xns#x_bad.ddls.asddls: hiçbir regex" in err, f"rc={rc} {err[:300]!r}")
    ekle("N7", "#xns#i_good" not in err + out, f"ham-biçim iyi ad listelendi: {err[:300]!r}")
    ekle("N8", "#xns#c_res" not in err + out, f"çözülmüş-ad iyi ad listelendi/ölçülemedi: {err[:300]!r}")

    # O: check_object_in_correct_pkg — abapGit DCL/BDEF son uzantıları
    kum = yeni_kum("op")
    cds = kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "cds"
    yaz(cds / "ZBASKA_X.dcls.asdcls", DDL)
    yaz(cds / "ZBASKA_Y.bdef.asbdef", DDL)
    yaz(cds / "ZSD001_I_OK.dcls.asdcls", DDL)
    rc, out, err = kos(kum, VAL / "check_object_in_correct_pkg.py")
    ekle("O1", rc != 0 and "ZBASKA_X.dcls.asdcls" in out + err, f"rc={rc} {(out + err)[:300]!r}")
    ekle("O2", "ZBASKA_Y.bdef.asbdef" in out + err, f"{(out + err)[:300]!r}")
    ekle("O0", "ZSD001_I_OK" not in out + err, f"KONTROL doğru önek listelendi: {(out + err)[:300]!r}")


# ── ② + ③ check_rap_managed_etag ───────────────────────────────────────────────
KOK = ("define behavior for ZI_ROOT alias Root\npersistent table zroot\nlock master\n"
       "authorization master ( instance )\n{ETAG}{{\n  create; update; delete;\n"
       "  association _Child {{ create; }}\n}}\n")
COCUK = ("define behavior for ZI_CHILD alias Child\npersistent table zchild\n"
         "lock dependent by _Root\nauthorization dependent by _Root\n{ETAG}{{\n  update; delete;\n"
         "  association _Root;\n}}\n")
BAS = "managed implementation in class zbp_i_x unique;\nstrict ( 2 );\n"


def bdef(*bloklar: str) -> str:
    return BAS + "".join(bloklar)


def bolum_etag() -> None:
    kum = yeni_kum("et")
    et = VAL / "check_rap_managed_etag.py"

    def kos_b(ad, metin):
        f = yaz(kum / f"{ad}.bdef", metin)
        rc, out, err = kos(kum, et, str(f))
        return rc, out + err

    kok_tam = KOK.format(ETAG="etag master LastChangedAt\n")
    kok_yok = KOK.format(ETAG="")
    cocuk_dep = COCUK.format(ETAG="etag dependent by _Root\n")
    cocuk_yok = COCUK.format(ETAG="")
    rc, t = kos_b("e1", bdef(kok_yok, cocuk_dep))
    ekle("E1", rc == 1 and "blok #1 (satır 3, KÖK" in t, f"kökte etag yok + çocuk dependent rc={rc} {t[:300]!r}")
    rc, t = kos_b("e2", bdef(kok_tam, cocuk_yok))
    ekle("E2", rc == 0 and "ÖLÇÜLMEDİ: çocuk blok etag'i (etag'siz çocuk 1, denetlenmez)" in t,
         f"rc={rc} {t[:300]!r}")
    rc, t = kos_b("e3", bdef(KOK.format(ETAG="etag dependent by _Root\n"), cocuk_dep))
    ekle("E3", rc == 1 and "'etag dependent' kökte geçersiz" in t, f"rc={rc} {t[:300]!r}")
    kok2_yok = kok_yok.replace("ZI_ROOT alias Root", "ZI_ROOT2 alias Root2").replace("zroot", "zroot2")
    rc, t = kos_b("e4", bdef(kok_tam, cocuk_dep, kok2_yok))
    ekle("E4", rc == 1 and "blok #3" in t and "blok #1" not in t, f"çok-kök rc={rc} {t[:300]!r}")
    rc, t = kos_b("e5", bdef(kok_tam.replace("  association _Child { create; }\n", "")))
    ekle("E5", rc == 0 and "KAPSAM: 1 behavior bloğu · kök 1 · çocuk 0 · salt-okunur 0" in t,
         f"tek blok rc={rc} {t[:300]!r}")
    salt = "define behavior for ZI_RO alias Ro\nlock dependent by _Root\n{\n  association _Root;\n}\n"
    rc, t = kos_b("e6", bdef(kok_tam, cocuk_dep, salt))
    ekle("E6", rc == 0 and "kök 1 · çocuk 1 · salt-okunur 1" in t, f"salt-okunur blok rc={rc} {t[:300]!r}")
    rc, t = kos_b("e7", bdef(kok_yok, cocuk_yok))
    ekle("E7", rc == 1, f"KONTROL hiç etag yok rc={rc}")
    # bug-gate F1: CRUD'suz kök (yalnız action + association) + CRUD'lu çocuk + hiç etag yok.
    # Taban BLOCKER veriyordu; ilk #405 sürümü kökü "salt-okunur" sayıp rc 0 dönüyordu.
    kok_crudsuz = ("define behavior for ZI_ROOT alias Root\npersistent table zroot\nlock master\n"
                   "authorization master ( instance )\n{\n  action doIt;\n  association _Item;\n}\n")
    cocuk_crud = ("define behavior for ZI_ITEM alias Item\npersistent table zitem\n"
                  "lock dependent by _Root\nauthorization dependent by _Root\n{\n  update;\n  delete;\n"
                  "  field ( readonly ) RootId;\n  association _Root;\n}\n")
    rc, t = kos_b("e8", bdef(kok_crudsuz, cocuk_crud))
    ekle("E8", rc == 1 and "blok #1 (satır 3, KÖK" in t, f"CRUD'suz kök rc={rc} {t[:300]!r}")
    # ③ ham docstring: `-W error` altında derlenir
    r = subprocess.run([sys.executable, "-W", "error", "-c",
                        "import sys; compile(open(sys.argv[1], encoding='utf-8').read(), sys.argv[1], 'exec')",
                        str(et)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    ekle("W1", r.returncode == 0, f"-W error derleme rc={r.returncode} {r.stderr[-200:]!r}")


# ── ④ check_cds_currency_reference ─────────────────────────────────────────────
def _ddl(govde: str, kaynak: str = "konp", ad: str = "ZI_T") -> str:
    return f"define view entity {ad}\n  as select from {kaynak}\n{{\n{govde}}}\n"


def bolum_curr() -> None:
    kum = yeni_kum("cu")
    cu = VAL / "check_cds_currency_reference.py"

    def kos_c(ad, metin):
        f = yaz(kum / f"{ad}.ddls.asddls", metin)
        return kos(kum, cu, str(f), "--type", "cds")

    rc, out, err = kos_c("c1", _ddl("  key knumh,\n      kbetr,\n      konwa\n"))
    ekle("C1", rc == 0 and "'kbetr' elemanında @Semantics.amount.currencyCode annotation'ı YOK" in err,
         f"takma adsız kbetr, rc={rc} {out[:200]!r} {err[:200]!r}")
    rc, out, err = kos_c("c2", _ddl("  key knumh,\n      konp.kbetr,\n      konp.konwa\n"))
    ekle("C2", "'kbetr' elemanında" in err, f"konp.kbetr, {out[:200]!r} {err[:200]!r}")
    rc, out, err = kos_c("c3", _ddl("  key knumh,\n      @Semantics.amount.currencyCode: 'konwa'\n"
                                    "      konp.kbetr,\n      konp.konwa\n", kaynak="/xns/prc_t as konp",
                                    ad="/XNS/I_T"))
    ekle("C3", rc == 0 and "1 CURR/QUAN elemanı denetlendi" in out, f"ns kaynak {out[:250]!r} {err[:200]!r}")
    rc, out, err = kos_c("c4", _ddl("  key knumh,\n      konwa,\n      kbetr\n"))
    ekle("C4", "'kbetr' elemanında" in err, f"virgülsüz son eleman {out[:200]!r} {err[:200]!r}")
    rc, out, err = kos_c("c5", _ddl("  key knumh,\n      @Semantics.amount.currencyCode: 'konwa'\n"
                                    "      kbetr,\n      konwa\n"))
    ekle("C5", rc == 0 and "1 CURR/QUAN elemanı denetlendi" in out, f"annotasyonlu {out[:250]!r}")
    rc, out, err = kos_c("c10", _ddl("  key kbetr,\n      konwa\n"))
    ekle("C10", "'kbetr' elemanında" in err, f"`key` önekli takma adsız {out[:200]!r} {err[:200]!r}")
    rc, out, err = kos_c("c5a", _ddl("  key knumh as Knumh,\n      kbetr as Amount,\n      konwa as Konwa\n"))
    ekle("C5a", "'Amount' elemanında" in err, f"KONTROL takma adlı eksik annotation {err[:200]!r}")
    gb = ("define view entity ZI_GB\n  as select from konp\n{\n  key konp.knumh as Knumh,\n"
          "      konp.konwa as Konwa\n}\ngroup by\n  konp.knumh,\n  konp.kbetr,\n  konp.konwa\n")
    rc, out, err = kos_c("c6", gb)
    ekle("C6", rc == 0 and "kbetr" not in err, f"group by öğesi eleman sayıldı: {out[:200]!r} {err[:200]!r}")
    un = ("define view entity ZI_UN as select from konp {\n  key knumh,\n"
          "  @Semantics.amount.currencyCode: 'konwa'\n  kbetr,\n  konwa\n}\n"
          "union all select from konp {\n  key knumh,\n  kbetr,\n  konwa\n}\n")
    rc, out, err = kos_c("c7", un)
    ekle("C7", rc == 0 and "kbetr" not in err, f"union 2. dal sahte uyarı: {out[:200]!r} {err[:200]!r}")
    rc, out, err = kos_c("c8", _ddl("  key knumh,\n      @Semantics.amount.currencyCode: 'konwa'\n"
                                    "      kbetr,\n      konwa\n"))
    ekle("C8", "ÖLÇÜLMEDİ: projeksiyon (`as projection on`) annotation mirası MODELLENMEZ" in out,
         f"OK yolunda KAPSAM beyanı yok: {out[:300]!r}")
    rc, out, err = kos_c("c9", _ddl("  key knumh,\n      kbetr,\n      konwa\n"))
    ekle("C9", "annotation mirası MODELLENMEZ" in err, f"ihlal yolunda KAPSAM beyanı yok: {err[-300:]!r}")


# ── ⑤ run_review ────────────────────────────────────────────────────────────────
def bolum_review() -> None:
    kum = yeni_kum("rv")
    rr = VAL / "run_review.py"
    dcl = yaz(kum / "ZSD001_I_X.dcls.asdcls", "@EndUserText.label: 'x'\ndefine role ZSD001_I_X { }\n")
    cds = yaz(kum / "ZSD001_I_X.cds", DDL)
    rc, out, err = kos(kum, rr, "--task", "rap_service_binding", "--artifact", str(dcl))
    ekle("R1", "BAKILMAYAN — DCL: ÖLÇÜLMEDİ" in out and "İNCELENEN DOSYA BU TÜRDE" in out,
         f"rc={rc} {out[-400:]!r}")
    rc, out, err = kos(kum, rr, "--task", "rap_service_binding", "--artifact", str(cds))
    ekle("R2", "BAKILMAYAN — DCL: ÖLÇÜLMEDİ" in out and "İNCELENEN DOSYA" not in out,
         f"rc={rc} {out[-400:]!r}")
    rc, out, err = kos(kum, rr, "--task", "rap_service_binding", "--artifact", str(dcl), "--json")
    try:
        j = json.loads(out[out.index("{"):])
        b = j.get("bakilmayan")
    except Exception as exc:  # noqa: BLE001
        b = f"JSON okunamadı: {exc}"
    ekle("R3", isinstance(b, list) and len(b) == 1 and b[0].startswith("DCL: ÖLÇÜLMEDİ"),
         f"bakilmayan -> {b!r}")


def main() -> int:
    try:
        for fn in (bolum_ns, bolum_naming, bolum_etag, bolum_curr, bolum_review):
            try:
                fn()
            except Exception as exc:                   # noqa: BLE001 — bölüm çökmesi FAIL'dir
                ekle(f"{fn.__name__}_COKTU", False, f"{type(exc).__name__}: {exc}")
    finally:
        for k in KUMLAR:
            shutil.rmtree(k, ignore_errors=True)
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    return 0 if n == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYON — her kip TEK bir değişmezi geri alır; düşmesi İLAN EDİLEN küme TAM olmalıdır.
# ─────────────────────────────────────────────────────────────────────────────
_V = "scripts/validators/"
MUTASYONLAR = {
    # ⑦
    "--mutasyon-pull-ham-ad": ("scripts/sap_sync_pull.py",
                               "    govde = dosya_adindan_ad(repo_file.name.split(\".\", 1)[0])\n"
                               "    if govde != dosya_adindan_ad(obj):\n",
                               "    govde = repo_file.name.split(\".\", 1)[0].upper()\n"
                               "    if govde != obj.upper():\n",
                               # H3b/H4: `main` adı ÖNCE çözer (`#xns#x` → `/XNS/X`) ⇒ ham kıyas onları da reddeder
                               {"A1", "A2", "A3", "A4", "H3", "H3b", "H4"}),
    "--mutasyon-pull-farkli-kabul": ("scripts/sap_sync_pull.py",
                                     "    if govde != dosya_adindan_ad(obj):\n",
                                     "    if False:\n",
                                     {"M1", "M2", "M3", "M4", "K2"}),
    "--mutasyon-pull-obj-ham": ("scripts/sap_sync_pull.py",
                                "    obj = dosya_adindan_ad(args.name)\n",
                                "    obj = args.name.upper()\n",
                                {"H4"}),
    "--mutasyon-pbe-ad-ham": ("scripts/source_drift.py",
                              "    ad = dosya_adindan_ad(p.name.split(\".\", 1)[0])     # #405",
                              "    ad = p.name.split(\".\", 1)[0].upper()     # #405",
                              {"S1", "H1", "H1n"}),
    "--mutasyon-kaynak-dosya-ham": ("scripts/source_drift.py",
                                    "        if dosya_adindan_ad(base) != name_sap:\n",
                                    "        if base != object_name.lower():\n",
                                    {"F1"}),
    "--mutasyon-adaylar-ham": ("scripts/source_drift.py",
                               "dosya_adindan_ad(f.name.split(\".\", 1)[0]) != ad:   # #405",
                               "f.name.lower().split(\".\", 1)[0] != object_name.lower():   # #405",
                               {"F2", "F3"}),
    "--mutasyon-drift-ham": (_V + "check_source_drift.py",
                             "    return dosya_adindan_ad(f.name.split(\".\", 1)[0])\n",
                             "    return f.name.split(\".\", 1)[0].upper()\n",
                             {"D1"}),
    "--mutasyon-komut-ham": ("scripts/hooks/pull_before_edit.py",
                             "        ad = f'\"{ham}\"'\n",
                             "        pass\n",
                             {"H1"}),
    "--mutasyon-komut-not": ("scripts/hooks/pull_before_edit.py",
                             "f\"sonra edit'i TEKRAR dene.)\\n\") + cmd_notu",
                             "f\"sonra edit'i TEKRAR dene.)\\n\")",
                             {"H1n"}),
    "--mutasyon-komut-adi-ham": ("scripts/sap_sync_pull.py",
                                 "sap_sync_pull.py {_komut_adi(etiket)} --type",
                                 "sap_sync_pull.py {etiket} --type",
                                 {"T4", "T5"}),
    "--mutasyon-komut-adi-url": ("scripts/sap_sync_pull.py",
                                 "    return f'\"{url_segmenti(ad)}\"'\n",
                                 "    return f'\"{ad}\"'\n",
                                 {"T2", "T5"}),
    "--mutasyon-ml-ham": (_V + "check_sap_master_language.py",
                          "        if dosya_adindan_ad(name).startswith(\"/\"):\n",
                          "        if False:\n",
                          {"ML1"}),
    # ①
    "--mutasyon-naming-asddls": (_V + "check_package_naming.py",
                                 "\"cds\": [\"*.cds\", \"*.bdef\", \"*.asbdef\", \"*.dcl\", \"*.asddls\", \"*.asdcls\"],",
                                 "\"cds\": [\"*.cds\", \"*.bdef\", \"*.asbdef\", \"*.dcl\"],",
                                 {"N1", "N2", "N4", "N10", "N5", "N12", "N6"}),
    "--mutasyon-naming-cozulen-yok": (_V + "check_package_naming.py",
                                      "            adaylar = [name] + ([sap_ad, name.upper()] if sap_ad.startswith(\"/\") else [])\n",
                                      "            adaylar = [name] + ([name.upper()] if sap_ad.startswith(\"/\") else [])\n",
                                      {"N8"}),
    "--mutasyon-naming-ham-buyuk-yok": (_V + "check_package_naming.py",
                                        "            adaylar = [name] + ([sap_ad, name.upper()] if sap_ad.startswith(\"/\") else [])\n",
                                        "            adaylar = [name] + ([sap_ad] if sap_ad.startswith(\"/\") else [])\n",
                                        {"N7"}),
    "--mutasyon-naming-zy-buyuk": (_V + "check_package_naming.py",
                                   "            adaylar = [name] + ([sap_ad, name.upper()] if sap_ad.startswith(\"/\") else [])\n",
                                   "            adaylar = [name, sap_ad, name.upper()]\n",
                                   {"N9"}),
    "--mutasyon-naming-olculemedi-yok": (_V + "check_package_naming.py",
                                         "                if ns and not _tablo_ns_aniyor(applicable_regexes, ns):\n",
                                         "                if False:\n",
                                         {"N5", "N12"}),
    # bug-gate F2: biçimi bozuk namespace'i de ÖLÇÜLEMEDİ'ye sokan ilk #405 sürümü
    "--mutasyon-naming-bozuk-ns-olculemedi": (_V + "check_package_naming.py",
                                              "                if ns and not _tablo_ns_aniyor(applicable_regexes, ns):\n",
                                              "                if not ns or not _tablo_ns_aniyor(applicable_regexes, ns):\n",
                                              {"N13", "N14"}),
    "--mutasyon-naming-ns-anma-yok": (_V + "check_package_naming.py",
                                      "        if f\"/{ic}/\" in duz or f\"#{ic}#\" in duz:\n",
                                      "        if False:\n",
                                      {"N6"}),
    "--mutasyon-naming-kapsam-yok": (_V + "check_package_naming.py",
                                     "    print(f\"OK — {len(packages)} paket, naming ihlali yok. {kapsam_satiri}\")\n",
                                     "    print(f\"OK — {len(packages)} paket, naming ihlali yok.\")\n",
                                     {"N12"}),
    "--mutasyon-objpkg-asdcls": (_V + "check_object_in_correct_pkg.py",
                                 "\".tabl\", \".asdcls\", \".asbdef\"}",
                                 "\".tabl\"}",
                                 {"O1", "O2"}),
    # ② + ③
    "--mutasyon-etag-dosya": (_V + "check_rap_managed_etag.py",
                              "        if LOCK_MASTER_RE.search(blok) and bdef_yazmali:\n",
                              "        if False:\n",
                              # E7: hiçbir blok kök sayılmaz ⇒ etag'siz kök de geçer (dosya düzeyi kontrol yok)
                              {"E1", "E3", "E4", "E5", "E6", "E7", "E8"}),
    # bug-gate F1: kökün salt-okunurluğunu BLOK düzeyinde soran ilk #405 sürümü
    "--mutasyon-etag-kok-salt-okunur": (_V + "check_rap_managed_etag.py",
                                        "        if LOCK_MASTER_RE.search(blok) and bdef_yazmali:\n",
                                        "        if LOCK_MASTER_RE.search(blok) and WRITE_OP_RE.search(blok):\n",
                                        {"E8"}),
    "--mutasyon-etag-kok-dependent": (_V + "check_rap_managed_etag.py",
                                      "            if not etag or etag.group(1).lower() != 'master':\n",
                                      "            if not etag:\n",
                                      {"E3"}),
    "--mutasyon-etag-salt-okunur": (_V + "check_rap_managed_etag.py",
                                    "        if not WRITE_OP_RE.search(blok):\n",
                                    "        if False:\n",
                                    {"E6"}),
    "--mutasyon-etag-kapsam-yok": (_V + "check_rap_managed_etag.py",
                                   "        print(f'  {kapsam_satiri(say)}')\n        return 0\n",
                                   "        return 0\n",
                                   {"E2", "E5", "E6"}),
    "--mutasyon-etag-docstring": (_V + "check_rap_managed_etag.py",
                                  "r\"\"\"\ncheck_rap_managed_etag.py",
                                  "\"\"\"\ncheck_rap_managed_etag.py",
                                  {"W1"}),
    # ④
    "--mutasyon-curr-takmasiz-yok": (_V + "check_cds_currency_reference.py",
                                     "    m = _ELEMAN_TAKMASIZ.match(s) if liste_icinde else None\n",
                                     "    m = None\n",
                                     # C9: takma adsız eleman sayılmayınca ihlal yok ⇒ beyan stderr'e değil
                                     # stdout'a basılır; C8 (OK yolu) beyanı yine görür
                                     {"C1", "C2", "C3", "C4", "C5", "C9", "C10"}),
    "--mutasyon-curr-liste-yok": (_V + "check_cds_currency_reference.py",
                                  "    m = _ELEMAN_TAKMASIZ.match(s) if liste_icinde else None\n",
                                  "    m = _ELEMAN_TAKMASIZ.match(s)\n",
                                  {"C6"}),
    "--mutasyon-curr-key-onek": (_V + "check_cds_currency_reference.py",
                                 "    r\"^\\s*(?:key\\s+)?(?P<ifade>(?:\" + AD_DESENI",
                                 "    r\"^\\s*(?P<ifade>(?:\" + AD_DESENI",
                                 {"C10"}),
    "--mutasyon-curr-beyan-yok":(_V + "check_cds_currency_reference.py",
                                  "            print(f'  {CDS_KAPSAM_BEYANI}')\n",
                                  "",
                                  {"C8"}),
    # ⑤
    "--mutasyon-review-dcl-yok": (_V + "run_review.py",
                                  "    ((\".dcls.asdcls\", \".asdcls\", \".dcl\"), \"DCL (erişim kontrolü, `define role`)\"),\n",
                                  "",
                                  {"R1", "R2", "R3"}),
}
KIPLER = list(MUTASYONLAR)     # sözlük sırası = ilan sırası (elle ikinci liste tutulmaz)


def _mutasyon(kip) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kok = Path(tempfile.mkdtemp(prefix="q405_kum_"))
    try:
        shutil.copytree(REPO / "scripts", kok / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
        shutil.copytree(REPO / "playbook" / "checklists", kok / "playbook" / "checklists")
        hedef = kok / "tests" / "fixtures" / BURASI.name
        shutil.copytree(BURASI, hedef, ignore=shutil.ignore_patterns("__pycache__"))
        dosya = kok / yol
        asil = dosya.read_bytes().decode("utf-8")
        if asil.count(eski) != 1:
            print(f"[KURULAMADI] {kip} -> capa {asil.count(eski)} kez ({yol})")
            return 3
        mutant = asil.replace(eski, yeni, 1)
        try:
            compile(mutant, str(dosya), "exec")
        except SyntaxError as exc:
            print(f"[KURULAMADI] {kip} -> mutant derlenmedi: {exc}")
            return 3
        dosya.write_bytes(mutant.encode("utf-8"))
        r = subprocess.run([sys.executable, str(hedef / "run.py")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900, cwd=str(kok))
        m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
        if not m:
            son = [x for x in (r.stdout + r.stderr).splitlines() if x.strip()][-1:] or ["-"]
            print(f"[ALT-SUREC SAYI VERMEDI] {kip} rc={r.returncode} son={son[0][:160]}")
            return 3
        dusen = {x.split()[1] for x in r.stdout.splitlines() if x.strip().startswith("[FAIL]")}
        print(f"{kip}: {m.group(0)} · dusen={sorted(dusen)} · ilan={sorted(beklenen)}")
        if dusen == beklenen:
            print("MUTASYON DUSTU (ilan edilen kume TAM)")
            return 1
        print(f"[SAPMA] fazla={sorted(dusen - beklenen)} eksik={sorted(beklenen - dusen)}")
        return 2
    finally:
        shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    _kipler = [a for a in sys.argv[1:] if a.startswith("--")]
    if _kipler:
        if len(_kipler) != 1 or _kipler[0] not in MUTASYONLAR:
            print(f"[KULLANIM] gecerli kipler: {KIPLER}")
            sys.exit(2)
        sys.exit(_mutasyon(_kipler[0]))
    sys.exit(main())
