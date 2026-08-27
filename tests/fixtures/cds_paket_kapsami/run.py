#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CDS kapilari TEK PAKETE kilitliydi (2026-08-27 kuyruk kaydi, K3).

KOK-1 populate_cds_views.validate_sql_view_names: sqlView/view-adi prefix'i
project.yaml'daki TEK duz string'ten (`sql_view_prefix`/`cds_view_name_prefix`)
geliyordu. Bir depoda birden cok paket yasadigi icin gate, HANGI paketin CDS'ini
dogruladigina bakmadan HERKESE ayni prefix'i dayatiyordu -> o paket disindaki her
paketin TUM canli .cds dosyalari yapisal olarak FAIL veriyordu (olculdu: 11 paket
/ ~121 dosya). FIX: prefix `--package` argumanindan DETERMINISTIK turetilir
(ZMOD001_CLC -> ZMOD001_V_ / zmod001_ddl_); config yalnizca kaliba uymayan
paketler icin FALLBACK olarak kalir; ikisi de yoksa FAIL-SAFE net hata.

KOK-2 td_spec_check._module_roots / find_td_spec: docstring "paket kokleri" derken
kod `source_dir().iterdir()` ile TEK seviye iniyordu -> eline MODUL klasoru (SD/MM)
geciyordu, PAKET klasoru (<MODUL>/<PAKET>) degil; ayrica aday yol yalniz
`<kok>/<folder>/<ad>.md` idi, `ref_docs/<folder>/` segmenti hic denenmiyordu ->
dogru yerde duran spec dosyalari BULUNAMIYORDU. FIX: kokler iki seviye + ref_docs
adayi EKLENDI (hicbir eski aday kaldirilmadan; yon daima genisletme).

Korpus S(enaryo) + M(utasyon) tasir:
  P1-P9  populate: paket-basina prefix, capraz-paket REDDI, config fallback (FP
         capasi), fail-safe, RAP dali regresyonu, 14-char siniri
  T1-T6  td_spec: iki-seviye, ref_docs, duz yapi (FP capasi), modul seviyesi
         (FP capasi), active_package onceligi, hata mesajinin DURUSTLUGU
  M1-M6  fix'i sok -> korpus KIRMIZI olmali (yesil kalirsa korpus o degismezi
         olcmuyor). Iki dosya x uc bagimsiz degismez = alti ayri mutasyon.

Kosum: python tests/fixtures/cds_paket_kapsami/run.py     (exit 0 = PASS)
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SCRIPTS = CORE / "scripts"
PCV_PATH = SCRIPTS / "populate_cds_views.py"
TSC_PATH = SCRIPTS / "td_spec_check.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_gc_koruma: list = []   # modullerin kurdugu stdout wrapper'lari canli tut


# ---------------------------------------------------------------------------
# Yukleyiciler — mutasyon icin KAYNAK METNI yamalanabilir surumu yukler.
# ---------------------------------------------------------------------------
def _exec_modul(yol: Path, ad: str, mut=None, env: dict | None = None):
    """Kaynagi (istege bagli mutasyonla) TAZE namespace'te calistirir.

    ⚠ Env, exec'ten ONCE kurulur: her iki modul de IMPORT ANINDA config okuyor
    (populate_cds_views._SQLP/_VNP). Sonradan monkeypatch GEC kalir.
    ⚠ stdout: modul win32 dalinda stdout'u reconfigure/gasp ediyor. Gercek
    stdout'a dokundurmamak icin atilabilir bir TextIOWrapper(BytesIO) baglanir
    (StringIO OLMAZ: `.buffer` yok -> modulun else dali AttributeError verir).
    """
    src = yol.read_text(encoding="utf-8")
    if mut:
        src = mut(src)
    eski_env = {}
    for k, v in (env or {}).items():
        eski_env[k] = os.environ.get(k)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    saved_out, saved_err = sys.stdout, sys.stderr
    cop_out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    cop_err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    sys.stdout, sys.stderr = cop_out, cop_err
    try:
        mod = types.ModuleType(ad)
        mod.__file__ = str(yol)
        exec(compile(src, str(yol), "exec"), mod.__dict__)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
        _gc_koruma.append((cop_out, cop_err))
        for k, v in eski_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return mod


# Config fallback'i DETERMINISTIK yap: gercek project.yaml'a bagimli olma.
# ⚠ CLAUDE_PROJECT_DIR de BOS bir koke bakmali. Yoksa `cfg()` env'de bulamayinca
# CWD'deki gercek project.yaml'a duser; "config YOK" vektoru cevredeki projenin
# prefix'ini gorur ve korpus KOSULDUGU DIZINE gore sonuc degistirir (2026-08-27'de
# olculdu: ayni dosya DEV_CORE kokunden PASS, proje kokunden FAIL).
_BOS_KOK: list = []


def _bos_kok() -> str:
    if not _BOS_KOK:
        _BOS_KOK.append(tempfile.mkdtemp(prefix="cds_paket_kapsami_bos_"))
    return _BOS_KOK[0]


def cfg_env() -> dict:
    return {"CLAUDE_PROJECT_DIR": _bos_kok(),
            "IX_SQL_VIEW_PREFIX": "ZMOD001_V_",
            "IX_CDS_VIEW_NAME_PREFIX": "zmod001_ddl_"}


def cfg_yok_env() -> dict:
    return {"CLAUDE_PROJECT_DIR": _bos_kok(),
            "IX_SQL_VIEW_PREFIX": None,
            "IX_CDS_VIEW_NAME_PREFIX": None}


def yukle_pcv(mut=None, env=None):
    return _exec_modul(PCV_PATH, "populate_cds_views", mut, env or cfg_env())


def yukle_tsc(mut=None):
    return _exec_modul(TSC_PATH, "td_spec_check", mut, {})


# ---------------------------------------------------------------------------
# Sekiller
# ---------------------------------------------------------------------------
def yaz_cds(dizin: Path, ad: str, sqlview: str, viewadi: str) -> Path:
    dizin.mkdir(parents=True, exist_ok=True)
    p = dizin / f"{ad}.cds"
    p.write_text(
        f"@AbapCatalog.sqlViewName: '{sqlview}'\n"
        f"@EndUserText.label: 'Test view'\n"
        f"define view {viewadi} as select from t000 {{\n"
        f"  key t000.mandt as Client\n"
        f"}}\n",
        encoding="utf-8")
    return p


def yaz_rap(dizin: Path, ad: str, entity: str) -> Path:
    dizin.mkdir(parents=True, exist_ok=True)
    p = dizin / f"{ad}.cds"
    p.write_text(
        f"@EndUserText.label: 'Test entity'\n"
        f"define root view entity {entity} as select from t000 {{\n"
        f"  key t000.mandt as Client\n"
        f"}}\n",
        encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# SENARYOLAR — populate_cds_views
# ---------------------------------------------------------------------------
def senaryolar_pcv(pcv, kum: Path, mut=None) -> list[tuple[str, bool, str]]:
    """`mut` ZORUNLU olarak iletilir: P6 kendi (config'siz) modul kopyasini yukler.
    Mutasyon o kopyaya TASINMAZSA fail-safe vektoru mutasyonu HIC gormez ve
    'M3 KACTI' der -- korpusun degil KOSUCUNUN kusuru olur (2026-08-27'de bir kez
    tam olarak bu yasandi; once boyle yazildi, mutasyon kacti, sonra duzeltildi)."""
    r = []
    d = kum / "cds_src"

    # Iki AYRI paketin kendi kurallarina uygun dosyalari
    f1 = yaz_cds(d, "ZMOD001_DDL_ORDER", "ZMOD001_V_ORD", "zmod001_ddl_order")
    f2 = yaz_cds(d, "ZMOD002_DDL_ITEM", "ZMOD002_V_ITM", "zmod002_ddl_item")

    def dogrula(dosyalar, paket):
        try:
            return pcv.validate_sql_view_names(dosyalar, package=paket)
        except BaseException as e:            # mutasyon cokertirse: FAIL sayilir
            return ["EXC:%s: %s" % (type(e).__name__, e)]

    # P1 — CONTEXT (i): config'in ZATEN tanidigi paket. Sonuc AYNI kalmali.
    e = dogrula([f1], "ZMOD001_CLC")
    r.append(("P1 tanidik paket (config ile ayni) -> hata YOK", e == [], str(e)))

    # P2 — capraz paket REDDI: ZMOD001 dosyasi ZMOD002 paketinde YASAK olmali.
    # (Ayirt edici capa: prefix GERCEKTEN pakete gore turetiliyor mu?)
    e = dogrula([f1], "ZMOD002_CLC")
    r.append(("P2 capraz paket (ZMOD001 dosyasi / ZMOD002 paketi) -> RED",
              len(e) == 2
              and any("sqlViewName='ZMOD001_V_ORD'" in x and "YASAK" in x for x in e)
              and any("define view='zmod001_ddl_order'" in x and "YASAK" in x for x in e),
              str(e)))

    # P3 — CONTEXT (ii): config'te HIC gecmeyen paket. KUSURUN TA KENDISI:
    # eski kod bunu FAIL ederdi (config ZMOD001'e ayarli).
    e = dogrula([f2], "ZMOD002_CLC")
    r.append(("P3 config-disi paket kendi kuralina uyuyor -> hata YOK (kusur)",
              e == [], str(e)))

    # P4 — FP CAPASI / geriye-uyum: package=None -> ESKI davranis (config prefix'i).
    e_ok = dogrula([f1], None)
    e_red = dogrula([f2], None)
    r.append(("P4 package=None -> config fallback (ZMOD001 gecer, ZMOD002 gecmez)",
              e_ok == [] and len(e_red) == 2, "None/f1=%s None/f2=%s" % (e_ok, e_red)))

    # P5 — CONTEXT (iii): kalip DISI paket adi + config VAR -> fallback'e duser.
    e = dogrula([f1], "LEGACY_STUFF")
    r.append(("P5 kalip disi paket + config VAR -> config fallback calisir",
              e == [], str(e)))

    # P6 — kalip DISI paket + config YOK -> FAIL-SAFE net hata (sessiz gecis YOK).
    pcv_cfgsiz = yukle_pcv(mut=mut, env=cfg_yok_env())
    try:
        e = pcv_cfgsiz.validate_sql_view_names([f1], package="LEGACY_STUFF")
    except BaseException as ex:
        e = ["EXC:%s: %s" % (type(ex).__name__, ex)]
    r.append(("P6 kalip disi paket + config YOK -> tek fail-safe hata (NAMESPACE-GATE)",
              len(e) == 1 and "NAMESPACE-GATE" in e[0] and "LEGACY_STUFF" in e[0],
              str(e)))

    # P6b — ayni cfgsiz modul, DOGRU paket adiyla: config olmasa da CALISIR
    # (turetme config'e bagimli degil; fail-safe her seyi kilitlemiyor).
    try:
        e = pcv_cfgsiz.validate_sql_view_names([f2], package="ZMOD002_CLC")
    except BaseException as ex:
        e = ["EXC:%s: %s" % (type(ex).__name__, ex)]
    r.append(("P6b config YOK ama paket adi kalipta -> hata YOK", e == [], str(e)))

    # P7 — sonek'siz duz paket adi (ZMOD003) da cozulur.
    f3 = yaz_cds(d, "ZMOD003_DDL_X", "ZMOD003_V_X", "zmod003_ddl_x")
    e = dogrula([f3], "ZMOD003")
    r.append(("P7 sonek'siz paket adi (ZMOD003) -> turetme calisir", e == [], str(e)))

    # P8 — FP CAPASI: RAP view-entity dali prefix'ten BAGIMSIZ (regresyon).
    fr_ok = yaz_rap(d, "ZMOD002_I_TEST", "ZMOD002_I_TEST")
    fr_kotu = yaz_rap(d, "ZMOD002_BAD", "ZMOD002_X_TEST")
    e_ok = dogrula([fr_ok], "ZMOD002_CLC")
    e_kotu = dogrula([fr_kotu], "ZMOD002_CLC")
    r.append(("P8 RAP view entity: dogru ad gecer, bozuk ad (X_) hala RED",
              e_ok == [] and len(e_kotu) == 1 and "RAP view entity" in e_kotu[0],
              "ok=%s kotu=%s" % (e_ok, e_kotu)))

    # P9 — 14 karakter siniri turetilmis prefix'te de yasiyor.
    f4 = yaz_cds(d, "ZMOD001_DDL_LONG", "ZMOD001_V_ABCDE", "zmod001_ddl_long")
    e = dogrula([f4], "ZMOD001_CLC")
    r.append(("P9 15 karakterlik sqlView -> uzunluk hatasi (sinir korunuyor)",
              len(e) == 1 and "uzunluk=15" in e[0], str(e)))

    return r


# ---------------------------------------------------------------------------
# SENARYOLAR — td_spec_check
# ---------------------------------------------------------------------------
def _spec_agaci(kok: Path) -> None:
    """Gercek yerlesimlerin hepsini tasiyan sahte kaynak agaci."""
    src = kok / "SOURCE_CODES"
    # iki seviye + ref_docs (bugunku paket agaci)
    (src / "SD" / "ZMOD001_CLC" / "ref_docs" / "cds").mkdir(parents=True, exist_ok=True)
    (src / "SD" / "ZMOD001_CLC" / "ref_docs" / "cds" / "ZMOD001_DDL_REFDOC.md").write_text(
        "# spec\n", encoding="utf-8")
    # iki seviye + duz folder
    (src / "SD" / "ZMOD001_CLC" / "cds").mkdir(parents=True, exist_ok=True)
    (src / "SD" / "ZMOD001_CLC" / "cds" / "ZMOD001_DDL_DUZ.md").write_text(
        "# spec\n", encoding="utf-8")
    # tek seviye duz paket (eski yerlesim — geriye uyum capasi)
    (src / "ZMOD009_CLC" / "cds").mkdir(parents=True, exist_ok=True)
    (src / "ZMOD009_CLC" / "cds" / "ZMOD009_DDL_FLAT.md").write_text(
        "# spec\n", encoding="utf-8")
    # modul seviyesinde spec (eski TEK-seviye davranisi — geriye uyum capasi)
    (src / "MM" / "cds").mkdir(parents=True, exist_ok=True)
    (src / "MM" / "cds" / "ZMOD005_DDL_MODUL.md").write_text("# spec\n", encoding="utf-8")
    # active_package onceligi: AYNI ad iki pakette
    for pkg in ("ZMOD001_CLC", "ZMOD002_CLC"):
        h = src / "SD" / pkg / "ref_docs" / "cds"
        h.mkdir(parents=True, exist_ok=True)
        (h / "ZMOD_DDL_CAKISMA.md").write_text("paket=%s\n" % pkg, encoding="utf-8")


def senaryolar_tsc(tsc, kok: Path, aktif: str = "ZMOD002_CLC") -> list[tuple[str, bool, str]]:
    eski = {}
    for k, v in (("CLAUDE_PROJECT_DIR", str(kok)),
                 ("IX_SOURCE_ROOT", "SOURCE_CODES"),
                 ("IX_ACTIVE_PACKAGE", aktif)):
        eski[k] = os.environ.get(k)
        os.environ[k] = v
    try:
        r = []

        def bul(ad):
            try:
                p = tsc.find_td_spec(ad, "cds")
                return str(p) if p else None
            except BaseException as e:
                return "EXC:%s" % type(e).__name__

        # T1 — KUSURUN TA KENDISI: iki seviye + ref_docs
        p = bul("ZMOD001_DDL_REFDOC")
        r.append(("T1 <modul>/<paket>/ref_docs/cds/X.md bulunuyor (kusur)",
                  bool(p) and p.replace("\\", "/").endswith(
                      "SD/ZMOD001_CLC/ref_docs/cds/ZMOD001_DDL_REFDOC.md"), str(p)))

        # T2 — FP CAPASI: tek seviye duz paket (eski yerlesim) HALA bulunuyor
        p = bul("ZMOD009_DDL_FLAT")
        r.append(("T2 <paket>/cds/X.md (duz yapi) hala bulunuyor (geriye uyum)",
                  bool(p) and p.replace("\\", "/").endswith(
                      "SOURCE_CODES/ZMOD009_CLC/cds/ZMOD009_DDL_FLAT.md"), str(p)))

        # T3 — iki seviye, ref_docs'suz
        p = bul("ZMOD001_DDL_DUZ")
        r.append(("T3 <modul>/<paket>/cds/X.md bulunuyor",
                  bool(p) and p.replace("\\", "/").endswith(
                      "SD/ZMOD001_CLC/cds/ZMOD001_DDL_DUZ.md"), str(p)))

        # T4 — FP CAPASI: modul seviyesindeki spec (ESKI tek-seviye davranisi)
        p = bul("ZMOD005_DDL_MODUL")
        r.append(("T4 <modul>/cds/X.md hala bulunuyor (eski davranis korunuyor)",
                  bool(p) and p.replace("\\", "/").endswith(
                      "SOURCE_CODES/MM/cds/ZMOD005_DDL_MODUL.md"), str(p)))

        # T5 — active_package onceligi: cakisan adda AKTIF paket kazanir
        p = bul("ZMOD_DDL_CAKISMA")
        r.append(("T5 cakisan ad -> active_package (%s) kazanir" % aktif,
                  bool(p) and ("/%s/" % aktif) in str(p).replace("\\", "/"), str(p)))

        # T6 — bulunamayan spec: SystemExit + mesaj ref_docs adayini DA listeler
        try:
            tsc.require_td_spec("ZMOD001_DDL_YOK", "cds")
            msj, tip = "(exit YOK)", "yok"
        except SystemExit as se:
            msj, tip = str(se), "SystemExit"
        except BaseException as e:
            msj, tip = str(e), type(e).__name__
        r.append(("T6 spec yok -> SystemExit + 'aranan yollar' ref_docs adayini gosterir",
                  tip == "SystemExit"
                  and "ref_docs/cds/ZMOD001_DDL_YOK.md" in msj.replace("\\", "/")
                  and "ZMOD001_CLC" in msj,
                  msj[-260:]))
        return r
    finally:
        for k, v in eski.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ---------------------------------------------------------------------------
# MUTASYONLAR — her biri BAGIMSIZ bir degismezi soker
# ---------------------------------------------------------------------------
PCV_MUT = [
    ("M1 prefix turetmesini sok (her sey yine config'ten gelsin)",
     lambda s: s.replace(
         "    if package:\n"
         "        m = _PKG_PREFIX_RE.match(str(package).strip().upper())\n"
         "        if m:\n"
         "            kok = m.group(1)\n"
         "            return f\"{kok}_V_\", f\"{kok.lower()}_ddl_\"\n"
         "    return _SQLP, _VNP",
         "    return _SQLP, _VNP")),
    ("M2 package parametresini yok say (kablolama kopsun)",
     lambda s: s.replace("    _sqlp, _vnp = _derive_prefixes(package)",
                         "    _sqlp, _vnp = _derive_prefixes(None)")),
    ("M3 fail-safe'i sok (cozulemeyen prefix sessizce gecsin)",
     lambda s: s.replace("    if not _sqlp or not _vnp:\n"
                         "        return [f\"NAMESPACE-GATE",
                         "    if False:\n"
                         "        return [f\"NAMESPACE-GATE")),
]

TSC_MUT = [
    ("M4 iki-seviye kok kesfini sok (yalniz modul klasoru kalsin)",
     lambda s: s.replace("    for d in birinci_seviye:\n"
                         "        for alt in _alt_dizinler(d):\n"
                         "            _ekle(alt)\n", "")),
    ("M5 ref_docs adayini sok (yalniz duz yapi denensin)",
     lambda s: s.replace("_SPEC_ALT_YOLLAR: tuple = ((), ('ref_docs',))",
                         "_SPEC_ALT_YOLLAR: tuple = ((),)")),
    ("M6 active_package onceligini sok (sirali ilk paket kazansin)",
     lambda s: s.replace("    if aktif:\n"
                         "        _ekle(src / aktif)\n"
                         "        for d in birinci_seviye:\n"
                         "            _ekle(d / aktif)\n",
                         "    if False:\n"
                         "        pass\n")),
]


def _kum_kur():
    kok = Path(tempfile.mkdtemp(prefix="cds_paket_kapsami_"))
    _spec_agaci(kok)
    return kok


def main() -> int:
    print("=" * 78)
    print("cds_paket_kapsami — CDS kapilarinin TEK-PAKET kilidi (2026-08-27)")
    print("=" * 78)

    kum = _kum_kur()
    try:
        sonuc = []
        sonuc += senaryolar_pcv(yukle_pcv(), kum)
        sonuc += senaryolar_tsc(yukle_tsc(), kum)
        kirik = [(a, d) for a, ok, d in sonuc if not ok]
        for ad, ok, detay in sonuc:
            print("  [%s] %s" % ("PASS" if ok else "FAIL", ad))
            if not ok:
                print("         gorulen: %s" % detay)
        print("  -> %d/%d senaryo PASS" % (len(sonuc) - len(kirik), len(sonuc)))

        print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmali) ---")
        mut_kirik = []
        for ad, mut in PCV_MUT + TSC_MUT:
            pcv_mi = (ad, mut) in PCV_MUT
            try:
                if pcv_mi:
                    m_res = senaryolar_pcv(yukle_pcv(mut=mut), kum, mut=mut)
                else:
                    m_res = senaryolar_tsc(yukle_tsc(mut=mut), kum)
                yakalandi = any(not ok for _, ok, _ in m_res)
                kacan = [a for a, ok, _ in m_res if not ok]
            except BaseException as e:
                # KURULAMADI != KACTI: yuklenemeyen mutasyon OLCUM DEGILDIR.
                print("  [KURULAMADI] %s -> %s: %s" % (ad, type(e).__name__, e))
                mut_kirik.append(ad + " (KURULAMADI)")
                continue
            print("  [%s] %s" % ("YAKALANDI" if yakalandi else "KACTI", ad))
            if yakalandi:
                print("         kiran senaryo(lar): %s" % ", ".join(kacan[:3]))
            else:
                mut_kirik.append(ad)

        # Mutasyonun GERCEKTEN uygulandigi kaniti (yama tutmazsa sahte-YESIL)
        print("\n--- yama-tuttu kaniti ---")
        ham_pcv = PCV_PATH.read_text(encoding="utf-8")
        ham_tsc = TSC_PATH.read_text(encoding="utf-8")
        yama_kirik = []
        for ad, mut in PCV_MUT + TSC_MUT:
            ham = ham_pcv if (ad, mut) in PCV_MUT else ham_tsc
            degisti = mut(ham) != ham
            print("  [%s] %s" % ("degisti" if degisti else "YAMA TUTMADI", ad))
            if not degisti:
                yama_kirik.append(ad)

        print("\n" + "=" * 78)
        if kirik or mut_kirik or yama_kirik:
            if kirik:
                print("FAIL — senaryo: %s" % ", ".join(a for a, _ in kirik))
            if mut_kirik:
                print("FAIL — mutasyon KACTI/KURULAMADI: %s" % ", ".join(mut_kirik))
            if yama_kirik:
                print("FAIL — mutasyon yamasi kaynaga UYMADI (sahte-yesil riski): %s"
                      % ", ".join(yama_kirik))
            return 1
        print("PASS — %d senaryo + %d mutasyon" % (len(sonuc), len(PCV_MUT) + len(TSC_MUT)))
        return 0
    finally:
        shutil.rmtree(kum, ignore_errors=True)
        for _b in _BOS_KOK:
            shutil.rmtree(_b, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
