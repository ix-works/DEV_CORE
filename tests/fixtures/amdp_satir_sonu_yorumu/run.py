# -*- coding: utf-8 -*-
"""amdp_satir_sonu_yorumu — `check_amdp_comment_apostrophe` SATIR-BAŞI ÇAPASI (B2-09, KRİTİK).

KÖK (2026-08-28 adversarial bug-avı): desen `^\\s*--.*'` idi — **satır-başı çapalı**.
Oysa HANA SQLScript parser'ını kıran şey yorumun KONUMU değil, yorumdaki APOSTROFtur:
`--` nerede başlarsa başlasın, apostrof literal-açıcı sayılır → literal sonraki apostrofa
kadar UZAR → aktivasyonda "Literals across more than one line are not allowed".

Liderin canlı ölçümü (fix öncesi): aynı içerik satır BAŞINDA `--` → `1 ERROR`;
satır SONUNDA `--` → *"temiz"*. Yani BE-28c reçetesi ("`--` yorumlarında apostrof")
ile kodun denetlediği şey (tek bir YAZIM BİÇİMİ) ayrışmıştı. Gate'in var oluş sebebi
olan hata (bug-gate PASS der, activate patlar) tam da bu yazımla kaçıyordu.

⚠ FIX ESKİ KURALI KALDIRMADI, ÜSTÜNE EKLEDİ (iki değişmez → iki mutasyon):
  (1) tam-satır `--` taraması dosyanın TAMAMINDA — K1/K2 bunu çiviler.
  (2) satır-sonu `--` taraması YALNIZ AMDP GÖVDESİNDE (`BY DATABASE PROCEDURE`..
      `ENDMETHOD`). Gövde sınırı olmadan her ABAP yorumu (`" Ali'nin notu`) yanlış-pozitif
      olurdu — N2/N3 bu sınırın çapasıdır. Düşerlerse gate her Türkçe ABAP yorumuna
      bağırır ve alarm-yorgunluğundan ölür.

⚠ N4 EN KRİTİK FP ÇAPASI: `'a--b'` — literal İÇİNDEKİ `--` yorum DEĞİLDİR. Ham
  "satırda `--` var mı" araması bu literali ihlal sayardı (ardındaki `b'` apostrofu
  yüzünden). Literal-duyarlılık düşerse N4 kırmızıya döner.

⚠ DURUM: LATENT (canlı korpus 81 .clas.abap → 0 bulgu, fix öncesi ve sonrası AYNI).

Koşum:     python tests/fixtures/amdp_satir_sonu_yorumu/run.py
MUTASYON:  B2_GATE_KOK=<taban b2ab7f1 validators dizini> → P1/E1 DÜŞER;
           K1/K2/N* ayakta kalır.
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
GATE = GATE_KOK / "check_amdp_comment_apostrophe.py"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


def amdp(govde: str, disari: str = "", amdp_var: bool = True) -> str:
    """AMDP class şablonu. `disari` = AMDP gövdesinin DIŞINDAKİ ABAP satırları."""
    imza = ("    METHOD get_data BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT\n"
            "                    OPTIONS READ-ONLY USING vbak.\n"
            if amdp_var else "    METHOD get_data.\n")
    return (
        "CLASS zcl_demo_amdp DEFINITION PUBLIC FINAL CREATE PUBLIC.\n"
        "  PUBLIC SECTION.\n"
        "    INTERFACES if_amdp_marker_hdb.\n"
        "ENDCLASS.\n\n"
        "CLASS zcl_demo_amdp IMPLEMENTATION.\n"
        f"{imza}"
        f"{govde}"
        "    ENDMETHOD.\n"
        f"{disari}"
        "ENDCLASS.\n"
    )


def proje_kur(kok: Path, kaynak: str, dosya: str = "zcl_demo_amdp.clas.abap") -> Path:
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


# ── POZİTİF (B2-09): satır SONUNDA `--` yorumu + apostrof ─────────────────────────
P1 = amdp("      lt = SELECT vbeln FROM vbak WHERE mandt = :clnt;  -- voyage'a gore filtre\n")
# ── 3. BAĞLAM: `.ccimp.abap` (behavior pool içindeki AMDP) ────────────────────────
E1 = amdp("      lt = SELECT vbeln FROM vbak;  -- SELECT'te mandt zorunlu\n")
# ── KONTROL GRUBU: eskiden de yakalanan varyantlar (kural KALDIRILMADI) ───────────
K1 = amdp("      -- voyage'a gore filtre\n      lt = SELECT vbeln FROM vbak;\n")
K2 = amdp("      lt = SELECT vbeln FROM vbak;\n",
          disari="--  ENDMETHOD sonrasi tam-satir yorumu: Ali'nin notu\n")
# ── FP ÇAPALARI ───────────────────────────────────────────────────────────────────
N1 = amdp("      lt = SELECT vbeln FROM vbak;  -- apostrofsuz aciklama\n")
N2 = amdp("      lt = SELECT vbeln FROM vbak;\n",
          disari="  METHOD baska.\n    lv_a = 1.  \" Ali'nin ABAP yorumu\n  ENDMETHOD.\n")
N3 = amdp("      lt = SELECT vbeln FROM vbak;\n",
          disari="  METHOD baska.\n*   Ali'nin tam-satir ABAP yorumu\n    lv_a = 1.\n  ENDMETHOD.\n")
N4 = amdp("      lt = SELECT vbeln FROM vbak WHERE kod = 'a--b';\n")
N5 = amdp("      lv_a = 1.  \" Ali'nin notu -- burada AMDP yok\n", amdp_var=False)
N6 = amdp("      lt = SELECT vbeln FROM vbak WHERE ad = 'O''Brien';  -- apostrofsuz not\n")

SENARYOLAR: list[tuple[str, str, bool, str, str]] = [
    ("P1", P1, True, "zcl_demo_amdp.clas.abap",
     "P1 satır-SONU `--` yorumunda apostrof → ERROR (B2-09)"),
    ("E1", E1, True, "zcl_demo_amdp.ccimp.abap",
     "E1 3.BAĞLAM `.ccimp.abap` + satır-sonu `--` apostrofu"),
    ("K1", K1, True, "zcl_demo_amdp.clas.abap",
     "K1 KONTROL satır-BAŞI `--` apostrofu → ERROR (eskiden de)"),
    ("K2", K2, True, "zcl_demo_amdp.clas.abap",
     "K2 KONTROL AMDP gövdesi DIŞINDA tam-satır `--` → ERROR (eski kural KALDIRILMADI)"),
    ("N1", N1, False, "zcl_demo_amdp.clas.abap",
     "N1 FP satır-sonu `--` ama apostrof YOK → temiz"),
    ("N2", N2, False, "zcl_demo_amdp.clas.abap",
     "N2 FP ABAP `\"` yorumunda apostrof (AMDP dışı) → temiz (gövde sınırı)"),
    ("N3", N3, False, "zcl_demo_amdp.clas.abap",
     "N3 FP ABAP `*` tam-satır yorumunda apostrof → temiz"),
    ("N4", N4, False, "zcl_demo_amdp.clas.abap",
     "N4 FP `'a--b'` literali içindeki `--` yorum DEĞİL → temiz (literal-duyarlılık)"),
    ("N5", N5, False, "zcl_demo_amdp.clas.abap",
     "N5 FP AMDP olmayan class (`_has_amdp` kapısı) → temiz"),
    ("N6", N6, False, "zcl_demo_amdp.clas.abap",
     "N6 FP `'O''Brien'` escape'li literal + apostrofsuz yorum → temiz"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="b2amdp_"))
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

        # ── Yapısal çapa: ESKİ desen yerinde mi (kaldırma değil EKLEME) ──
        sys.path.insert(0, str(GATE_KOK))
        try:
            import check_amdp_comment_apostrophe as A  # noqa: PLC0415
            kontrol(getattr(A, "_RX_COMMENT_APOS", None) is not None
                    and A._RX_COMMENT_APOS.pattern == r"^\s*--.*'",
                    "S1 eski tam-satır deseni DEĞİŞMEDİ (üstüne eklendi)",
                    getattr(getattr(A, "_RX_COMMENT_APOS", None), "pattern", "YOK"))
        except Exception as e:  # noqa: BLE001
            kontrol(False, "S1 eski desen çapası", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\namdp_satir_sonu_yorumu: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
