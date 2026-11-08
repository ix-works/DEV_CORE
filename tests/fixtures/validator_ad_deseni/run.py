#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validator_ad_deseni fixture — DEV_CORE #402: "ad deseni tutmadı ⇒ kapsam dışı / OK" SINIFI.

NEDEN VAR (2026-11-08, tüketici ölçümü + lider teyidi, origin/main b0bcfac)
  run_review zincirindeki validator'lar nesne adını `(\\w+)` / `Z…` desenleriyle yakalıyordu.
  `\\w` `/` eşlemediği için müşteri namespace'li (`/NSPC/…`) bir nesne "behavior definition
  değil" / "view entity değil" sayılıp rc=0 dönüyordu: kontrol HİÇ koşmadığı hâlde sonuç temiz
  görünüyordu. Aynı turda namespace'ten bağımsız iki kör nokta:
    EK-1  `managed with additional save` / `managed with unmanaged save` tanınmıyordu
          (Z adlı BDEF bile "managed implementation değil, kapsam dışı").
    EK-2  BDEF araması yalnız `*.bdef`'e bakıyordu; abapGit biçimi `X.bdef.asbdef` görünmüyordu
          (readonly Kural B → SAHTE BLOCKER; audit/backtick/naming → dosya hiç taranmıyordu).

DEĞİŞMEZLER (her biri bir vektörle çivili; mutasyon kipleri aşağıda)
  I1  managed_etag BDEF'i ANAHTAR SÖZCÜKLE tanır, ada bakmaz (NS BDEF ölçülür)       E2 E5 RR1
  I2  managed_etag uygulama türünü ilk deyimden okur: `managed with … save` dahil    E3 E4
  I3  managed tanıması satır-başı çapalıdır (alias `Managed` unmanaged'ı managed yapmaz) E7
  I4  reuse_gate: anahtar sözcük var + ad çözülemedi ⇒ ÖLÇÜLEMEDİ (measured=false)   R2b
  I4b reuse_gate: namespace'li ad gramerce AYRIŞTIRILIR, denetim KOŞAR (Faz B-2)      R2
  I5  readonly : aynı K2 (ad çözülemedi)                                            C4a
  I5b readonly : kayıtsız namespace ⇒ ÖLÇÜLEMEDİ `namespace-kayitsiz`                C4 C5
  I5c readonly : kayıtlı namespace ⇒ Kural B GERÇEKTEN koşar (BLOCKER)              C4b
  N*  Faz B-2 (TEK AD GRAMERİ, `ad_politikasi`): `/` ile başlayan ad ya katı gramerle
      ayrıştırılıp DENETLENİR ya da ÖLÇÜLEMEDİ (`ad-cozulemedi` / `namespace-kayitsiz`) —
      hiçbir validator onu sessizce "kapsam dışı / OK" saymaz. Bölüm N (validator başına).
  I6  readonly Kural B `*.asbdef`'i de arar (sahte BLOCKER yok)                     C2
  I7  audit_fields repo taraması `*.asbdef`'i de görür                              A1
  I8  bdef_backtick repo yürüyüşü `*.asbdef`'i de toplar                            B1
  I9  bdef_backtick dosya süzgeci `*.asbdef`'i düşürmez (I8'den AYRI katman)         B1
  I10 package_naming `cds/` klasöründe `*.asbdef`'i de doğrular                      P1
  KONTROL GRUBU (taban ağaçta da YEŞİL olmalı — kilidin aşırı sıkı olmadığını kanıtlar):
    E1 Z managed bozuk → BLOCKER · E6 unmanaged → OK · E7 · C1 `.bdef` referanslı → temiz ·
    C3 BDEF'siz projeksiyon → BLOCKER · R1 Z duplicate → WARNING · R3 CDS olmayan → K2 susar ·
    B0/A0 düz `.bdef` hâlâ yakalanır · N1 gramer dışı ad active_version'da zaten ÖLÇÜLEMEDİ ·
    N5b KAYITLI namespace tablosu müşteri sayılır (std_table_fields aşırı sıkı DEĞİL).
    TABAN ÖLÇÜMÜ (e52ad6f, 2026-11-08): 11/44 — yeşil kalanlar TAM bu kontrol grubu (11 vektör);
    düşen 33 vektörün her biri bu turun (Faz A + B-2) kapattığı bir boşluktur.

KULLANIM
  python tests/fixtures/validator_ad_deseni/run.py                       # tüm vektörler
  python tests/fixtures/validator_ad_deseni/run.py --mutasyon-<ad>       # tek mutasyon (KIPLER)
  Mutasyon çıkışı (run_battery karar tablosu): 1 = ilan edilen küme TAM düştü · 2 = SAPMA ·
  3 = kurulamadı (çapa sayısı ≠ 1 / derlenmedi / alt süreç sayı vermedi).

ORTAM: validator'lar ALT SÜREÇTE, `cwd` + `CLAUDE_PROJECT_DIR` = geçici kum (gerçek proje
ağacına dokunulmaz; hiçbir vektör SAP'ye bağlanan validator koşmaz — `.conn_adt` üretilmez).
"""
from __future__ import annotations

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
VAL = REPO / "scripts" / "validators"
if not (VAL / "run_review.py").is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")

S: list[tuple[str, bool, str]] = []


def ekle(ad: str, ok: bool, ayrinti: str = "") -> None:
    S.append((ad, ok, ayrinti))


def kos(kum: Path, betik: str, *argv: str) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(kum)
    env.pop("IX_CEVRIMDISI", None)
    # sap_adt_lib alt süreci ASLA gerçek sisteme düşmesin (kumdaki .conn_adt de sahte adres)
    env.update(ADT_SAP_URL="https://sahte.invalid", ADT_SAP_CLIENT="000", ADT_SAP_USER="x",
               ADT_SAP_PASSWORD="x")
    r = subprocess.run([sys.executable, str(VAL / betik), *argv], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120, cwd=str(kum), env=env)
    return r.returncode, r.stdout, r.stderr


_BEYAN = re.compile(r"^IX-GATE-STATUS:\s+gate=(\S+)\s+status=(\S+)\s+measured=(true|false)\s+"
                    r"reason=(\S+)\s*$", re.M)


def beyan(out: str):
    m = _BEYAN.findall(out)
    return m[-1] if m else None


def yaz(yol: Path, metin: str) -> Path:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(metin.encode("utf-8"))      # LF — CRLF ekseni bu fixture'ın konusu değil
    return yol


# ── Girdiler (jenerik adlar: ZSD001_… ve /NSPC/…) ─────────────────────────────
BDEF_Z_BOZUK = ("managed implementation in class zbp_sd001_i_x unique;\nstrict ( 2 );\n"
                "define behavior for ZSD001_I_X alias X\npersistent table zsd001_t01\n"
                "{\n  create; update; delete;\n}\n")
BDEF_NS_BOZUK = (BDEF_Z_BOZUK.replace("zbp_sd001_i_x", "/nspc/bp_sd001_i_x")
                 .replace("ZSD001_I_X", "/NSPC/SD001_I_X").replace("zsd001_t01", "/nspc/sd001_t01"))
BDEF_Z_EK_SAVE = BDEF_Z_BOZUK.replace(
    "managed implementation in class zbp_sd001_i_x unique;",
    "managed with additional save implementation in class zbp_sd001_i_x unique;")
BDEF_Z_UNM_SAVE = BDEF_Z_BOZUK.replace(
    "managed implementation in class zbp_sd001_i_x unique;",
    "managed with unmanaged save implementation in class zbp_sd001_i_x unique;")
BDEF_NS_TEMIZ = ("managed implementation in class /nspc/bp_sd001_i_x unique;\nstrict ( 2 );\n"
                 "define behavior for /NSPC/SD001_I_X alias X\npersistent table /nspc/sd001_t01\n"
                 "lock master\netag master LastChangedAt\n{\n  create; update; delete;\n}\n"
                 "// CDS root: @Semantics.systemDateTime.lastChangedAt: true\n")
BDEF_UNMANAGED = ("unmanaged implementation in class zbp_sd001_i_x unique;\nstrict ( 2 );\n"
                  "define behavior for ZSD001_I_X alias X\n{\n  create; update; delete;\n}\n")
# alias `Managed` satır başında DEĞİL ama sözcük olarak var: çapasız `\bmanaged\b` bunu managed sanar
BDEF_UNMANAGED_ALIAS = ("unmanaged implementation in class zbp_sd001_i_x unique;\nstrict ( 2 );\n"
                        "define behavior for ZSD001_I_X alias Managed\n{\n  create; update; delete;\n}\n")
DDLS_Z_C_PROJ = ("define root view entity ZSD001_C_X provider contract transactional_query\n"
                 "  as projection on ZSD001_I_X { key A }\n")
DDLS_NS_C_PROJ = DDLS_Z_C_PROJ.replace("ZSD001_C_X", "/NSPC/SD001_C_X").replace("ZSD001_I_X", "/NSPC/SD001_I_X")
BDEF_PROJ_REF = "projection;\nstrict ( 2 );\ndefine behavior for ZSD001_C_X alias X\n{\n  use create;\n}\n"
DDLS_Z_BPNAME = ("@AccessControl.authorizationCheck: #NOT_REQUIRED\n"
                 "define view entity ZSD001_I_BPNAME as select from but000 { key partner as Partner }\n")
DDLS_NS_BPNAME = DDLS_Z_BPNAME.replace("ZSD001_I_BPNAME", "/NSPC/SD001_I_BPNAME")
BDEF_AUDIT = ("managed implementation in class zbp_sd001_i_x unique;\nstrict ( 2 );\n"
              "define behavior for ZSD001_I_X alias X\npersistent table zsd001_t01\nlock master\n"
              "etag master LastChangedAt\n{\n  field ( readonly ) created_by, created_at;\n"
              "  create; update;\n}\n")
BDEF_BACKTICK = ("managed implementation in class zbp_sd001_i_x unique;\n"
                 "// alan `x` notu\ndefine behavior for ZSD001_I_X alias X\n{\n  create;\n}\n")
RULES_MD = ("# ZSD001_CLC kurallari\n\n## Naming\n\n| Obje tipi | Aciklama | Regex |\n|---|---|---|\n"
            "| CDS view | I/C katmani | `^ZSD001_[IC]_[A-Z0-9_]+$` |\n\n## Diger\n")


def _yeni_kum(ad: str, ns: bool = False) -> Path:
    """`ns=True`: `customer_namespaces: ["/NSPC/"]` + SAHTE `.conn_adt` (ad_politikasi izin listesini
    ÇÖZÜLEN bağlantı dosyasının dizininden okur; adres çözülmez — `sahte.invalid`)."""
    kum = Path(tempfile.mkdtemp(prefix=f"vad_{ad}_"))
    yaz(kum / "project.yaml", "source_root: SOURCE_CODES\nsap_profile: s4_private\n"
        + ('customer_namespaces: ["/NSPC/"]\n' if ns else ""))
    if ns:
        yaz(kum / ".conn_adt", "ADT_SAP_URL=https://sahte.invalid\nADT_SAP_CLIENT=000\n")
    return kum


# ── Bölüm E: check_rap_managed_etag ────────────────────────────────────────────
def bolum_e() -> None:
    kum = _yeni_kum("e")
    try:
        g = kum / "g"
        vakalar = [
            ("E1", BDEF_Z_BOZUK, 1, "lock master"),
            ("E2", BDEF_NS_BOZUK, 1, "lock master"),
            ("E3", BDEF_Z_EK_SAVE, 1, "lock master"),
            ("E4", BDEF_Z_UNM_SAVE, 1, "lock master"),
            ("E5", BDEF_NS_TEMIZ, 0, "etag/lock temiz"),
            ("E6", BDEF_UNMANAGED, 0, "unmanaged"),
            ("E7", BDEF_UNMANAGED_ALIAS, 0, "unmanaged"),
        ]
        for vid, metin, b_rc, b_metin in vakalar:
            f = yaz(g / f"{vid.lower()}.bdef", metin)
            rc, out, err = kos(kum, "check_rap_managed_etag.py", str(f))
            ok = rc == b_rc and b_metin in (out + err)
            ekle(vid, ok, f"rc={rc} (beklenen {b_rc}, '{b_metin}') out={out.strip()[:140]!r}")
        # RR1 — GERÇEK GİRİŞ NOKTASI: run_review rap_bdef_creation zinciri (SAP'siz üç gate)
        f = yaz(g / "rr1.bdef", BDEF_NS_BOZUK)
        rc, out, err = kos(kum, "run_review.py", "--task", "rap_bdef_creation", "--artifact", str(f))
        ok = "VERDICT: BLOCKER" in out and re.search(r"✗ \[BLOCKER\] check_rap_managed_etag", out) is not None
        verdict = re.findall(r"VERDICT: \S+", out)
        ekle("RR1", ok, f"rc={rc} verdict={verdict}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)


# ── Bölüm R: check_reuse_gate (WARNING-only, rc daima 0) ───────────────────────
def bolum_r() -> None:
    kum = _yeni_kum("r")
    try:
        yaz(kum / "CLAUDE.md", "# kum\n")
        src = kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "cds"
        yaz(src / "mevcut.ddls", DDLS_Z_BPNAME)
        yeni = yaz(kum / "yeni" / "z.ddls", DDLS_Z_BPNAME)
        rc, out, _ = kos(kum, "check_reuse_gate.py", str(yeni))
        ekle("R1", rc == 0 and "ZATEN tanımlı" in out and beyan(out) is None,
             f"rc={rc} out={out.strip()[:160]!r}")
        # R2 — namespace'li ad ayrıştırılır: aynı NS adı repoda varsa duplicate WARNING (denetim KOŞTU)
        yaz(src / "mevcut_ns.ddls", DDLS_NS_BPNAME)
        ns = yaz(kum / "yeni" / "ns.ddls", DDLS_NS_BPNAME)
        rc, out, _ = kos(kum, "check_reuse_gate.py", str(ns))
        ekle("R2", rc == 0 and "ZATEN tanımlı" in out and "/NSPC/SD001_I_BPNAME" in out
             and beyan(out) is None, f"rc={rc} out={out.strip()[:160]!r}")
        # R2b — gramer dışı ad (`/AB/` = 2 karakterli NS) ⇒ ÖLÇÜLEMEDİ, "temiz" DEĞİL
        ab = yaz(kum / "yeni" / "ab.ddls", DDLS_Z_BPNAME.replace("ZSD001_I_BPNAME", "/AB/SD001_I_BPNAME"))
        rc, out, _ = kos(kum, "check_reuse_gate.py", str(ab))
        b = beyan(out)
        ekle("R2b", rc == 0 and "ÖLÇÜLEMEDİ" in out and b is not None
             and b[0] == "check_reuse_gate" and b[1] == "SKIPPED" and b[2] == "false"
             and b[3] == "ad-cozulemedi", f"rc={rc} beyan={b} out={out.strip()[:160]!r}")
        duz = yaz(kum / "yeni" / "x.abap", "REPORT zsd001_x.\nWRITE 'define'.\n")
        rc, out, _ = kos(kum, "check_reuse_gate.py", str(duz))
        ekle("R3", rc == 0 and "kapsamı dışı" in out and beyan(out) is None,
             f"rc={rc} out={out.strip()[:160]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)


# ── Bölüm C: check_rap_readonly_consumption ────────────────────────────────────
def bolum_c() -> None:
    def paket(kum: Path, ad: str) -> Path:
        p = kum / "SOURCE_CODES" / "SD" / ad
        yaz(p / ".rules.md", "# kurallar\n")
        return p

    kum = _yeni_kum("c")
    try:
        p1 = paket(kum, "P1")
        yaz(p1 / "cds" / "zsd001_c_x.bdef", BDEF_PROJ_REF)
        rc, out, err = kos(kum, "check_rap_readonly_consumption.py",
                           str(yaz(p1 / "cds" / "zsd001_c_x.ddls", DDLS_Z_C_PROJ)))
        ekle("C1", rc == 0 and "temiz" in out, f"rc={rc} out={(out + err).strip()[:160]!r}")
        p2 = paket(kum, "P2")
        yaz(p2 / "src" / "zsd001_c_x.bdef.asbdef", BDEF_PROJ_REF)
        rc, out, err = kos(kum, "check_rap_readonly_consumption.py",
                           str(yaz(p2 / "src" / "zsd001_c_x.ddls.asddls", DDLS_Z_C_PROJ)))
        ekle("C2", rc == 0 and "temiz" in out, f"rc={rc} out={(out + err).strip()[:160]!r}")
        p3 = paket(kum, "P3")
        rc, out, err = kos(kum, "check_rap_readonly_consumption.py",
                           str(yaz(p3 / "cds" / "zsd001_c_x.ddls", DDLS_Z_C_PROJ)))
        ekle("C3", rc == 1 and "Rule B" in err, f"rc={rc} err={err.strip()[:160]!r}")
        p4 = paket(kum, "P4")
        rc, out, err = kos(kum, "check_rap_readonly_consumption.py",
                           str(yaz(p4 / "cds" / "ns.ddls", DDLS_NS_C_PROJ)))
        b = beyan(out)
        ekle("C4", rc == 0 and "ÖLÇÜLEMEDİ" in out and b is not None
             and b[0] == "check_rap_readonly_consumption" and b[1] == "SKIPPED" and b[2] == "false"
             and b[3] == "namespace-kayitsiz", f"rc={rc} beyan={b} out={out.strip()[:160]!r}")
        # C5 — TÜKETİCİ UCU: run_review'ın GERÇEK ayrıştırıcısı C4 çıktısını measured=false okur
        sys.path.insert(0, str(VAL))
        try:
            import importlib
            rr = importlib.import_module("run_review")
            d = rr.gate_durum_beyani(out, "check_rap_readonly_consumption.py")
            ekle("C5", bool(d) and d.get("measured") == "false", f"tuketici={d}")
        finally:
            sys.path.remove(str(VAL))
        # C4a — gramer dışı ad ⇒ K2 (`ad-cozulemedi`)
        p5 = paket(kum, "P5")
        rc, out, err = kos(kum, "check_rap_readonly_consumption.py",
                           str(yaz(p5 / "cds" / "ab.ddls", DDLS_Z_C_PROJ.replace("ZSD001_C_X", "/AB/SD001_C_X"))))
        b = beyan(out)
        ekle("C4a", rc == 0 and b is not None and b[1] == "SKIPPED" and b[2] == "false"
             and b[3] == "ad-cozulemedi", f"rc={rc} beyan={b} out={(out + err).strip()[:160]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)
    # C4b — KAYITLI namespace: BDEF'siz NS projeksiyon ⇒ Kural B GERÇEKTEN koşar (BLOCKER)
    kum = _yeni_kum("c4b", ns=True)
    try:
        p6 = paket(kum, "P6")
        rc, out, err = kos(kum, "check_rap_readonly_consumption.py",
                           str(yaz(p6 / "cds" / "ns.ddls", DDLS_NS_C_PROJ)))
        ekle("C4b", rc == 1 and "Rule B" in err and "/NSPC/SD001_C_X" in err,
             f"rc={rc} out={(out + err).strip()[:160]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)


# ── Bölüm A/B/P: `*.asbdef` repo taraması ──────────────────────────────────────
def bolum_abp() -> None:
    kum = _yeni_kum("abp")
    try:
        pk = kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC"
        # A0/B0 kontrol (düz .bdef) — ayrı kumda ki A1/B1 yalnız .asbdef'ten beslensin
        k0 = _yeni_kum("abp0")
        try:
            p0 = k0 / "SOURCE_CODES" / "SD" / "ZSD001_CLC"
            yaz(p0 / "cds" / "a.bdef", BDEF_AUDIT)
            yaz(p0 / "cds" / "b.bdef", BDEF_BACKTICK)
            rc, out, _ = kos(k0, "check_audit_fields_autofill.py")
            ekle("A0", rc == 1 and "a.bdef" in out, f"rc={rc} out={out.strip()[:160]!r}")
            rc, out, err = kos(k0, "check_bdef_backtick.py")
            ekle("B0", rc == 1 and "b.bdef" in (out + err), f"rc={rc} out={(out + err).strip()[:160]!r}")
        finally:
            shutil.rmtree(k0, ignore_errors=True)
        yaz(pk / "src" / "zsd001_i_a.bdef.asbdef", BDEF_AUDIT)
        yaz(pk / "src" / "zsd001_i_b.bdef.asbdef", BDEF_BACKTICK)
        rc, out, _ = kos(kum, "check_audit_fields_autofill.py")
        ekle("A1", rc == 1 and "zsd001_i_a.bdef.asbdef" in out, f"rc={rc} out={out.strip()[:200]!r}")
        rc, out, err = kos(kum, "check_bdef_backtick.py")
        ekle("B1", rc == 1 and "zsd001_i_b.bdef.asbdef" in (out + err),
             f"rc={rc} out={(out + err).strip()[:200]!r}")
        # P1 — package_naming: cds/ altında YANLIŞ adlı abapGit BDEF doğrulanmalı
        yaz(pk / ".rules.md", RULES_MD)
        yaz(pk / "cds" / "ZSD001_I_OK.cds", "define view entity ZSD001_I_OK as select from t000 { key mandt }\n")
        yaz(pk / "cds" / "ZSD001_X_BAD.bdef.asbdef", BDEF_PROJ_REF)
        rc, out, err = kos(kum, "check_package_naming.py", "--source-root", str(kum / "SOURCE_CODES"),
                           "--package", "ZSD001_CLC")
        ekle("P1", rc == 1 and "ZSD001_X_BAD.bdef.asbdef" in err and "ZSD001_I_OK" not in err,
             f"rc={rc} err={err.strip()[:200]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)


# ── Bölüm N: TEK AD GRAMERİ — validator başına namespace vektörleri (DEV_CORE #402 Faz B-2) ──
# Her validator için: gramer dışı `/AB/…` (2 karakterli NS) ⇒ `ad-cozulemedi` · bildirilmemiş
# `/NSPC/…` ⇒ `namespace-kayitsiz` (ya da validator'ın kendi fail-closed hükmü) · kayıtlı `/NSPC/`
# ⇒ denetim GERÇEKTEN koşar. SAP'ye giden yola hiçbir vektör ulaşmaz (karar bağlantıdan ÖNCE).
DDLS_AB_I = "define view entity /AB/SD001_I_X as select from t000 { key mandt }\n"
DDLS_NS_I = "define view entity /NSPC/SD001_I_X as select from t000 { key mandt }\n"
STR_AB_AD = "define structure /ab/sd001_s_x {\n  f1 : abap.char(1);\n}\n"
STR_AB_ALAN = "define structure zsd001_s_x {\n  /ab/f1 : abap.char(1);\n}\n"
STR_NS_DTEL = "define structure zsd001_s_x {\n  f1 : /nspc/sd001_e_x;\n}\n"
STR_AB_DTEL = "define structure zsd001_s_x {\n  f1 : /ab/sd001_e_x;\n}\n"
TAB_AB_AD = "define table /ab/sd001_t_x {\n  key mandt : mandt not null;\n}\n"
TAB_AB_ALAN = "define table zsd001_t_x {\n  key mandt : mandt not null;\n  /ab/f1 : abap.char(1);\n}\n"
CDS_NS_TAB = "define view entity ZSD001_I_X as select from /nspc/t01 { key /nspc/t01.f1 as F }\n"
CDS_AB_TAB = "define view entity ZSD001_I_X as select from /ab/t01 { key /ab/t01.f1 as F }\n"
TAB_AB_CURR = "define table zsd001_t_x {\n  key mandt : mandt not null;\n  /ab/amt : netwr;\n}\n"
# Marker ihtiyacı YALNIZ namespace'li CURR alanının başvurusundan doğar (yerleşik `abap.cuky` alanı
# sözlükte değil) ⇒ alan ayrıştırılmazsa (taban) bulgu da YOK — ayırt edici vektör.
TAB_NS_CURR = ("define table zsd001_t_x {\n  key mandt : mandt not null;\n"
               "  @Semantics.amount.currencyCode : 'zsd001_t_x.cur'\n  /nspc/amt : netwr;\n"
               "  cur : abap.cuky;\n}\n")
TAB_NS_CURR_ANOTSIZ = "define table zsd001_t_x {\n  key mandt : mandt not null;\n  /nspc/amt : netwr;\n}\n"


def _gs(out: str, gate: str, reason: str) -> tuple[bool, object]:
    b = beyan(out)
    return (b is not None and b[0] == gate and b[1] == "SKIPPED" and b[2] == "false"
            and b[3] == reason), b


def bolum_n() -> None:
    kum = _yeni_kum("n")
    try:
        g = kum / "g"
        for vid, betik, ad, metin, argv, reason in [
            ("N1", "check_sap_active_version.py", "a.ddls", DDLS_AB_I, [], "ad-cozulemedi"),
            ("N1b", "check_sap_active_version.py", "b.ddls", DDLS_NS_I, [], "namespace-kayitsiz"),
            ("N2", "check_sap_struct_consistency.py", "s1.ddl", STR_AB_AD, [], "ad-cozulemedi"),
            ("N2b", "check_sap_struct_consistency.py", "s2.ddl", STR_AB_ALAN, [], "ad-cozulemedi"),
            ("N3", "check_struct_field_dtel_active.py", "d1.ddl", STR_NS_DTEL, [], "namespace-kayitsiz"),
            ("N3b", "check_struct_field_dtel_active.py", "d2.ddl", STR_AB_DTEL, [], "ad-cozulemedi"),
            ("N4", "check_table_field_drop.py", "t1.ddl", TAB_AB_AD, [], "ad-cozulemedi"),
            ("N4b", "check_table_field_drop.py", "t2.ddl", TAB_AB_ALAN, [], "ad-cozulemedi"),
            ("N5", "check_standard_table_fields.py", "c1.cds", CDS_NS_TAB, ["--type", "cds"],
             "namespace-kayitsiz"),
            ("N5c", "check_standard_table_fields.py", "c2.cds", CDS_AB_TAB, ["--type", "cds"],
             "ad-cozulemedi"),
        ]:
            gate = betik[:-3]
            rc, out, err = kos(kum, betik, str(yaz(g / ad, metin)), *argv)
            ok, b = _gs(out, gate, reason)
            ekle(vid, rc == 0 and ok, f"rc={rc} beyan={b} (beklenen {reason}) "
                 f"out={(out + err).strip()[:160]!r}")
        # N6 — cds_currency (exit sözleşmesi: 2 = ÖLÇÜLEMEDİ)
        rc, _o, err = kos(kum, "check_cds_currency_reference.py", str(yaz(g / "k1.ddl", TAB_AB_CURR)),
                          "--type", "table")
        ekle("N6", rc == 2 and "ÖLÇÜLEMEDİ" in err and "/ab/amt" in err, f"rc={rc} err={err.strip()[:160]!r}")
        # N6b — namespace'li alan AYRIŞTIRILIR: başvurduğu CUKY alanının marker eksiği yakalanır
        rc, out, err = kos(kum, "check_cds_currency_reference.py", str(yaz(g / "k2.ddl", TAB_NS_CURR)),
                           "--type", "table")
        ekle("N6b", rc == 1 and "C-TBL-CUR-04" in (out + err) and "'cur'" in (out + err),
             f"rc={rc} out={(out + err).strip()[:160]!r}")
        # N6c — namespace'li CURR alanının KENDİ annotation eksiği (taban: alan görünmez ⇒ "temiz")
        rc, out, err = kos(kum, "check_cds_currency_reference.py",
                           str(yaz(g / "k3.ddl", TAB_NS_CURR_ANOTSIZ)), "--type", "table")
        ekle("N6c", rc == 1 and "C-TBL-CUR-03" in (out + err) and "/nspc/amt" in (out + err),
             f"rc={rc} out={(out + err).strip()[:160]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)
    # N5b — KAYITLI namespace tablosu müşteri sayılır (Z gibi atlanır) — KONTROL: aşırı sıkı değil
    kum = _yeni_kum("n5b", ns=True)
    try:
        rc, out, err = kos(kum, "check_standard_table_fields.py",
                           str(yaz(kum / "g" / "c1.cds", CDS_NS_TAB)), "--type", "cds")
        b = beyan(out)
        ekle("N5b", rc == 0 and b is not None and b[1] == "OK" and b[2] == "true",
             f"rc={rc} beyan={b} out={(out + err).strip()[:160]!r}")
    finally:
        shutil.rmtree(kum, ignore_errors=True)
    # N7 — checklist_check BE-01 (dosya adı `#ns#` okuma yönü + DB yazım hedefi)
    for ns in (False, True):
        kum = _yeni_kum("n7" + ("k" if ns else ""), ns=ns)
        try:
            yaz(kum / "src" / "#nspc#sd001_x.prog.abap", "REPORT /nspc/sd001_x.\n")
            yaz(kum / "src" / "#ab#sd001_x.prog.abap", "REPORT /ab/sd001_x.\n")
            yaz(kum / "src" / "zsd001_y.prog.abap", "REPORT zsd001_y.\nUPDATE /nspc/t01 SET f = 1 WHERE k = 2.\n")
            hucre = {}
            for f in ("#nspc#sd001_x.prog.abap", "#ab#sd001_x.prog.abap", "zsd001_y.prog.abap"):
                _rc, out, _e = kos(kum, "checklist_check.py", "--repo", str(kum), "--files", "src/" + f,
                                   "--kind", "backend", "--ids", "BE-01")
                s = [x for x in out.splitlines() if x.startswith("| BE-01 ")]
                hucre[f] = s[0].split("|")[3].strip() if s else "SATIR-YOK"
            if not ns:
                ekle("N7", hucre["#nspc#sd001_x.prog.abap"] == "FAIL", f"kayıtsız NS dosyası: {hucre}")
                ekle("N7b", hucre["#ab#sd001_x.prog.abap"] == "ÖLÇÜLEMEDİ", f"gramer dışı dosya: {hucre}")
                ekle("N7c", hucre["zsd001_y.prog.abap"] == "FAIL", f"kayıtsız NS tabloya yazım: {hucre}")
            else:
                ekle("N7e", hucre["#nspc#sd001_x.prog.abap"] == "PASS", f"kayıtlı NS dosyası: {hucre}")
                ekle("N7f", hucre["#ab#sd001_x.prog.abap"] == "ÖLÇÜLEMEDİ", f"gramer dışı dosya: {hucre}")
                ekle("N7d", hucre["zsd001_y.prog.abap"] == "PASS", f"kayıtlı NS tabloya yazım: {hucre}")
        finally:
            shutil.rmtree(kum, ignore_errors=True)


def main() -> int:
    for fn in (bolum_e, bolum_r, bolum_c, bolum_abp, bolum_n):
        try:
            fn()
        except Exception as exc:                       # noqa: BLE001 — bölüm çökmesi FAIL'dir
            ekle(f"{fn.__name__}_COKTU", False, f"{type(exc).__name__}: {exc}")
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
    "--mutasyon-managed-ad": (_V + "check_rap_managed_etag.py",
                              "DEFINE_BEHAVIOR_RE = re.compile(r'\\bdefine\\s+behavior\\s+for\\b', re.IGNORECASE)",
                              "DEFINE_BEHAVIOR_RE = re.compile(r'\\bdefine\\s+behavior\\s+for\\s+(\\w+)', re.IGNORECASE)",
                              {"E2", "E5", "RR1"}),
    "--mutasyon-managed-ek1": (_V + "check_rap_managed_etag.py",
                               "MANAGED_RE = re.compile(r'^\\s*managed\\b', re.IGNORECASE | re.MULTILINE)",
                               "MANAGED_RE = re.compile(r'\\bmanaged\\b\\s+implementation', re.IGNORECASE)",
                               {"E3", "E4"}),
    "--mutasyon-managed-capa": (_V + "check_rap_managed_etag.py",
                                "MANAGED_RE = re.compile(r'^\\s*managed\\b', re.IGNORECASE | re.MULTILINE)",
                                "MANAGED_RE = re.compile(r'\\bmanaged\\b', re.IGNORECASE | re.MULTILINE)",
                                {"E7"}),
    "--mutasyon-reuse-k2": (_V + "check_reuse_gate.py",
                            "        if ENTITY_KW_RE.search(text):\n",
                            "        if False:\n",
                            {"R2b"}),
    "--mutasyon-reuse-eski-desen": (_V + "check_reuse_gate.py",
                                    "r'\\bdefine\\s+(?:root\\s+)?view\\s+entity\\s+(' + AD_ADAYI + r')', re.IGNORECASE)",
                                    "r'\\bdefine\\s+(?:root\\s+)?view\\s+entity\\s+(\\w+)', re.IGNORECASE)",
                                    {"R2"}),
    "--mutasyon-readonly-k2": (_V + "check_rap_readonly_consumption.py",
                               "        if ENTITY_KW_RE.search(text):\n",
                               "        if False:\n",
                               {"C4a"}),
    # ── Bölüm N (Faz B-2): her kip bir validator'ın gramer bağını / ÖLÇÜLEMEDİ dalını geri alır
    "--mutasyon-struct-k2": (_V + "check_sap_struct_consistency.py",
                             "    if not struct_name and STRUCT_KW_PATTERN.search(local_text):\n",
                             "    if False:\n",
                             {"N2"}),
    "--mutasyon-dtel-ns": (_V + "check_struct_field_dtel_active.py",
                           "            olculemeyen.append((aday.upper(), karar))\n",
                           "            pass\n",
                           {"N3"}),
    "--mutasyon-drop-k2": (_V + "check_table_field_drop.py",
                           "    if not table and TABLE_KW_RE.search(new_text):\n",
                           "    if False:\n",
                           {"N4"}),
    "--mutasyon-drop-alan": (_V + "check_table_field_drop.py",
                             "    bozuk = cozulemeyen_alanlar(new_text)\n",
                             "    bozuk = []\n",
                             {"N4b"}),
    "--mutasyon-stdtab-ns": (_V + "check_standard_table_fields.py",
                             "                olculemeyen[f'{tbl}.{field}'] = 'namespace-kayitsiz'\n",
                             "                pass\n",
                             {"N5"}),
    "--mutasyon-curr-alan": (_V + "check_cds_currency_reference.py",
                             "        bozuk = cozulemeyen_alanlar(text)\n",
                             "        bozuk = []\n",
                             {"N6"}),
    "--mutasyon-be01-std": (_V + "checklist_check.py",
                            "        return not (musteri_adi_mi(tab) or ",
                            "        return not (t.startswith((\"z\", \"y\")) or ",
                            {"N7d"}),
    "--mutasyon-be01-dosya": (_V + "checklist_check.py",
                              "    nesne = dosya_adindan_ad(m.group(1)) if m else \"\"\n",
                              "    nesne = m.group(1) if m else \"\"\n",
                              {"N7", "N7e"}),
    "--mutasyon-readonly-asbdef": (_V + "check_rap_readonly_consumption.py",
                                   "for bdef in (*root.rglob('*.bdef'), *root.rglob('*.asbdef')):",
                                   "for bdef in root.rglob('*.bdef'):",
                                   {"C2"}),
    "--mutasyon-audit-asbdef": (_V + "check_audit_fields_autofill.py",
                                "                 *(root / SOURCE_ROOT_NAME).rglob(\"*.asbdef\")]",
                                "                 ]",
                                {"A1"}),
    "--mutasyon-backtick-yuruyus": (_V + "check_bdef_backtick.py",
                                    "if f.lower().endswith(_BDEF_UZANTILARI)]",
                                    "if f.lower().endswith(\".bdef\")]",
                                    {"B1"}),
    "--mutasyon-backtick-suzgec": (_V + "check_bdef_backtick.py",
                                   "        if not target and not f.name.lower().endswith(_BDEF_UZANTILARI):\n",
                                   "        if not target and f.suffix.lower() != \".bdef\":\n",
                                   {"B1"}),
    "--mutasyon-naming-asbdef": (_V + "check_package_naming.py",
                                 "\"cds\": [\"*.cds\", \"*.bdef\", \"*.asbdef\", \"*.dcl\"],",
                                 "\"cds\": [\"*.cds\", \"*.bdef\", \"*.dcl\"],",
                                 {"P1"}),
}
KIPLER = list(MUTASYONLAR)     # sözlük sırası = ilan sırası (elle ikinci liste tutulmaz)


def _mutasyon(kip) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kok = Path(tempfile.mkdtemp(prefix="vad_kum_"))
    try:
        shutil.copytree(REPO / "scripts", kok / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
        # checklist_check (N7) madde haritasını CORE/playbook/checklists'ten okur — yoksa BE-01 satırı
        # hiç basılmaz ve her kipte N7 ailesi FAZLA düşer (ölçüldü: 19 kipin 19'u SAPMA)
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
                           encoding="utf-8", errors="replace", timeout=600, cwd=str(kok))
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
