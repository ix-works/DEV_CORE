# -*- coding: utf-8 -*-
"""imza_cok_satirli_type_c — `check_method_param_type_c` SATIR-KAPSAMI (B2-11).

KÖK (2026-08-28 adversarial bug-avı): `_TYPE_C_LEN` tek-satır regex'i satır BAŞINA
koşuyordu. Oysa ABAP imzası satıra değil NOKTAYA bağlıdır ve uzun imzalar rutin sarılır:

    METHODS get_text
      IMPORTING iv_key  TYPE c
                        LENGTH 100.

Bu, save-scan'i kıran TAM AYNI bildirimdir (`OO_SOURCE_BASED` / `ResourceScanDuringSave
Failure` — **satır numarası VERMEZ**, bu yüzden gate'in var oluş sebebi "körlemesine
bisect'ten kurtarmak"tır) ama gate onu GÖRMÜYORDU: yani gate'in kapatmak için yazıldığı
en pahalı senaryo (saatlerce patinaj) açık kalmıştı.

⚠ N1 EN KRİTİK FP ÇAPASI: `TYPE c.` (nokta = ifade sonu) + sonraki satırda `LENGTH`
  geçen BAŞKA bir ifade. Birleştirme noktayı aşarsa gate her `WORK`/`LENGTH` benzeri
  komşuluğa bağırır. Nokta `\\s+` ile eşleşmediği için sınır kendiliğinden korunur —
  N1 bunu ölçer, VARSAYMAZ.

⚠ N3 (yorum) bir DARALTMADIR ve bilinçlidir: tam-satır `*` yorumundaki örnek imza artık
  ihlal değildir. Karşılığında K1/K2/P1 pozitif kontrol olarak durur — gerçek bildirim
  hâlâ yakalanıyor.

⚠ DURUM: LATENT (canlı korpus 283 .clas/.intf.abap → fix öncesi/sonrası 0 bulgu, BAYT AYNI).

Koşum:     python tests/fixtures/imza_cok_satirli_type_c/run.py
MUTASYON:  B2_GATE_KOK=<taban b2ab7f1 validators dizini> → P1/P2/E1 DÜŞER;
           K1/K2/N1/N2 ayakta kalır (N3 eski sürümde de FAIL verir → çift yönlü kanıt).
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
GATE_KOK = Path(os.environ.get("B2_GATE_KOK") or (KOK / "scripts" / "validators"))
GATE = GATE_KOK / "check_method_param_type_c.py"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


def clas(bildirim: str, govde: str = "    lv_a = 1.\n") -> str:
    return (
        "CLASS zcl_demo_helper DEFINITION PUBLIC FINAL CREATE PUBLIC.\n"
        "  PUBLIC SECTION.\n"
        f"{bildirim}"
        "ENDCLASS.\n\n"
        "CLASS zcl_demo_helper IMPLEMENTATION.\n"
        "  METHOD get_text.\n"
        f"{govde}"
        "  ENDMETHOD.\n"
        "ENDCLASS.\n"
    )


def proje_kur(kok: Path, kaynak: str, dosya: str = "zcl_demo_helper.clas.abap") -> Path:
    d = kok / "SOURCE_CODES" / "SD" / "ZDEMO_PKG" / "src"
    d.mkdir(parents=True, exist_ok=True)
    (d / dosya).write_text(kaynak, encoding="utf-8")
    return kok


def kos(proje: Path) -> tuple[int, str]:
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    try:
        r = subprocess.run([sys.executable, str(GATE)], cwd=str(proje), env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except Exception as e:  # noqa: BLE001
        return (-1, f"KOŞULAMADI: {type(e).__name__}: {e}")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ── POZİTİF (B2-11): imza iki satıra sarılmış ────────────────────────────────────
P1 = clas("    METHODS get_text\n"
          "      IMPORTING iv_key TYPE c\n"
          "                       LENGTH 100.\n")
P2 = clas("    CLASS-METHODS build\n"
          "      RETURNING VALUE(rv_out) TYPE\n"
          "                c LENGTH 220.\n")
# ── 3. BAĞLAM: `.intf.abap` (interface bildirimi) ────────────────────────────────
E1 = ("INTERFACE zif_demo_helper PUBLIC.\n"
      "  METHODS get_text\n"
      "    IMPORTING iv_key TYPE c\n"
      "                     LENGTH 40.\n"
      "ENDINTERFACE.\n")
# ── KONTROL GRUBU ────────────────────────────────────────────────────────────────
K1 = clas("    METHODS get_text IMPORTING iv_key TYPE c LENGTH 100.\n")
K2 = clas("    METHODS get_text\n"
          "      IMPORTING iv_key TYPE c LENGTH 100.\n")
# ── FP ÇAPALARI ──────────────────────────────────────────────────────────────────
N1 = clas("    METHODS get_text IMPORTING iv_key TYPE c.\n"
          "    CONSTANTS gc_length TYPE i VALUE 100.\n")
N2 = clas("    METHODS get_text IMPORTING iv_key TYPE string.\n"
          "  PRIVATE SECTION.\n"
          "    TYPES ty_buf TYPE c LENGTH 220.\n")   # TYPES/struct MEŞRU (imza değil)
N3 = clas("    METHODS get_text\n"
          "*     ESKI: IMPORTING iv_key TYPE c LENGTH 100\n"
          "      IMPORTING iv_key TYPE string.\n")

SENARYOLAR: list[tuple[str, str, bool, str, str]] = [
    ("P1", P1, True, "zcl_demo_helper.clas.abap",
     "P1 `TYPE c` + sonraki satırda `LENGTH 100` → İHLAL (B2-11)"),
    ("P2", P2, True, "zcl_demo_helper.clas.abap",
     "P2 `TYPE` / `c LENGTH 220` başka noktadan bölünmüş → İHLAL"),
    ("E1", E1, True, "zif_demo_helper.intf.abap",
     "E1 3.BAĞLAM `.intf.abap` interface bildirimi + çok-satırlı imza"),
    ("K1", K1, True, "zcl_demo_helper.clas.abap",
     "K1 KONTROL tek satırlık imza → İHLAL (eskiden de)"),
    ("K2", K2, True, "zcl_demo_helper.clas.abap",
     "K2 KONTROL sarılı ama `TYPE c LENGTH` aynı satırda → İHLAL (eskiden de)"),
    ("N1", N1, False, "zcl_demo_helper.clas.abap",
     "N1 FP `TYPE c.` + AYRI ifadede `LENGTH` → temiz (birleştirmenin SINIRI)"),
    ("N2", N2, False, "zcl_demo_helper.clas.abap",
     "N2 FP `TYPES ... TYPE c LENGTH 220` (imza DEĞİL) → temiz"),
    ("N3", N3, False, "zcl_demo_helper.clas.abap",
     "N3 FP tam-satır `*` yorumundaki örnek imza → temiz (bilinçli daraltma)"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="b2sig_"))
    try:
        for kod, kaynak, fail_bekleniyor, dosya, ad in SENARYOLAR:
            proje = proje_kur(tmp / kod, kaynak, dosya)
            rc, cikti = kos(proje)
            if rc < 0:
                kontrol(False, ad, cikti)
                continue
            ok = (rc == 1 and "[İHLAL]" in cikti) if fail_bekleniyor \
                else (rc == 0 and "[İHLAL]" not in cikti)
            kontrol(ok, ad, f"exit={rc}" + ("" if ok else " :: " + cikti.strip()[:200]))

        # ── Yapısal çapa: desen DEĞİŞMEDİ (fix tarama katmanında, desende değil) ──
        sys.path.insert(0, str(GATE_KOK))
        try:
            import check_method_param_type_c as M  # noqa: PLC0415
            kontrol(M._TYPE_C_LEN.pattern == r"\bTYPE\s+c\s+LENGTH\s+\d+",
                    "S1 `_TYPE_C_LEN` deseni DEĞİŞMEDİ (fix tarama katmanında)",
                    M._TYPE_C_LEN.pattern)
        except Exception as e:  # noqa: BLE001
            kontrol(False, "S1 desen çapası", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\nimza_cok_satirli_type_c: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
