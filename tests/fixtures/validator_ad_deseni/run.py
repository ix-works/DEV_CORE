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
  I4  reuse_gate: anahtar sözcük var + ad çözülemedi ⇒ ÖLÇÜLEMEDİ (measured=false)   R2
  I5  readonly : aynı K2                                                            C4
  I6  readonly Kural B `*.asbdef`'i de arar (sahte BLOCKER yok)                     C2
  I7  audit_fields repo taraması `*.asbdef`'i de görür                              A1
  I8  bdef_backtick repo yürüyüşü `*.asbdef`'i de toplar                            B1
  I9  bdef_backtick dosya süzgeci `*.asbdef`'i düşürmez (I8'den AYRI katman)         B1
  I10 package_naming `cds/` klasöründe `*.asbdef`'i de doğrular                      P1
  KONTROL GRUBU (taban ağaçta da YEŞİL olmalı — kilidin aşırı sıkı olmadığını kanıtlar):
    E1 Z managed bozuk → BLOCKER · E6 unmanaged → OK · E7 · C1 `.bdef` referanslı → temiz ·
    C3 BDEF'siz projeksiyon → BLOCKER · R1 Z duplicate → WARNING · R3 CDS olmayan → K2 susar ·
    B0/A0 düz `.bdef` hâlâ yakalanır.

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


def _yeni_kum(ad: str) -> Path:
    kum = Path(tempfile.mkdtemp(prefix=f"vad_{ad}_"))
    yaz(kum / "project.yaml", "source_root: SOURCE_CODES\n")
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
        ns = yaz(kum / "yeni" / "ns.ddls", DDLS_NS_BPNAME)
        rc, out, _ = kos(kum, "check_reuse_gate.py", str(ns))
        b = beyan(out)
        ekle("R2", rc == 0 and "ÖLÇÜLEMEDİ" in out and b is not None
             and b[0] == "check_reuse_gate" and b[1] == "SKIPPED" and b[2] == "false",
             f"rc={rc} beyan={b} out={out.strip()[:160]!r}")
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
             and b[0] == "check_rap_readonly_consumption" and b[1] == "SKIPPED" and b[2] == "false",
             f"rc={rc} beyan={b} out={out.strip()[:160]!r}")
        # C5 — TÜKETİCİ UCU: run_review'ın GERÇEK ayrıştırıcısı C4 çıktısını measured=false okur
        sys.path.insert(0, str(VAL))
        try:
            import importlib
            rr = importlib.import_module("run_review")
            d = rr.gate_durum_beyani(out, "check_rap_readonly_consumption.py")
            ekle("C5", bool(d) and d.get("measured") == "false", f"tuketici={d}")
        finally:
            sys.path.remove(str(VAL))
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


def main() -> int:
    for fn in (bolum_e, bolum_r, bolum_c, bolum_abp):
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
                            {"R2"}),
    "--mutasyon-readonly-k2": (_V + "check_rap_readonly_consumption.py",
                               "        if ENTITY_KW_RE.search(text):\n",
                               "        if False:\n",
                               {"C4", "C5"}),
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
KIPLER = ["--mutasyon-managed-ad", "--mutasyon-managed-ek1", "--mutasyon-managed-capa",
          "--mutasyon-reuse-k2", "--mutasyon-readonly-k2", "--mutasyon-readonly-asbdef",
          "--mutasyon-audit-asbdef", "--mutasyon-backtick-yuruyus", "--mutasyon-backtick-suzgec",
          "--mutasyon-naming-asbdef"]


def _mutasyon(kip) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kok = Path(tempfile.mkdtemp(prefix="vad_kum_"))
    try:
        shutil.copytree(REPO / "scripts", kok / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
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
