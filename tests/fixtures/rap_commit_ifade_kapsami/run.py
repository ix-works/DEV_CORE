# -*- coding: utf-8 -*-
"""rap_commit_ifade_kapsami — `check_no_rap_commit` SATIR-KAPSAMI + LİTERAL-DURUMU (B2-07/B2-08).

KÖK (2026-08-28 adversarial bug-avı, B2 ailesi):
  B2-07 (KRİTİK) — gate `splitlines()` + satır-başına regex ile tarıyordu. ABAP ifadesi
    satıra değil NOKTAYA bağlıdır: `COMMIT` \\n `WORK.` **tek ifadedir** ve TAM OLARAK
    gate'in var oluş sebebi olan runtime `BEHAVIOR_ILLEGAL_STATEMENT` dump'ını üretir —
    ama gate onu GÖRMÜYORDU. Bu bir BLOCKER'ın sessiz kaçışıydı.
  B2-08 (YÜKSEK) — `_strip_comment` yalnız `line.find('"')` yapıyordu; tek-tırnaklı
    literal tanınmıyordu. İKİ YÖNLÜ hasar:
      (a) YANLIŞ-POZİTİF: `lv_msg = 'COMMIT WORK yapılmadı'` → BLOCKER.
      (b) SESSİZ KAÇIŞ: `lv_x = 'say \"hi\"'. COMMIT WORK.` → literal içindeki `"`
          yorum-başlangıcı sanılıp satırın gerisi atılıyordu → ihlal görünmüyordu.

⚠ FIX'İN EN KRİTİK SINIRI — İKİ KÜME AYRI NORMALİZE EDİLİR:
  `COMMIT WORK`/`ROLLBACK WORK` bir İFADEDİR → literalleri boşaltılmış metinde aranır.
  `BAPI_TRANSACTION_COMMIT` bir FM ADIDIR ve ABAP'ta **her zaman literal içinde** yazılır
  (`CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'`) → literal boşaltılırsa GERÇEK POZİTİF
  KAYBOLUR. K2 tam olarak bunu çiviler: literal-temizliği tek kümeye uygulanırsa K2 düşer.
  (Bu, "FP düzeltirken gerçek pozitifi kaybetme" negatif kontrolüdür.)

⚠ FP ÇAPALARI OMURGADIR: N5 (`COMMIT.` \\n `WORK = 1.` = İKİ AYRI ifade) çok-satırlı
  taramanın sınırıdır. Aradaki nokta `\\s+` ile eşleşmez; düşerse birleştirme fazla
  agresiftir ve `WORK` adlı her değişken BLOCKER üretir.

⚠ DURUM: LATENT. Canlı korpusta (81 .clas.abap / 6 WARN) bu vektörlerin HİÇBİRİ yok;
  fix bugünkü bir ihlali düzeltmez, yarınki yazımı yakalar. Kanıt bu fixture'dır.
  Fix öncesi/sonrası canlı korpus çıktısı **BAYT AYNI** (ölçüldü 2026-08-28).

Koşum:      python tests/fixtures/rap_commit_ifade_kapsami/run.py
MUTASYON:   B2_GATE_KOK=<eski scripts/validators dizini> ile koş (taban b2ab7f1) →
            P1/P2/E1/E2 ve N1 DÜŞER; K1/K2/K3/W1/N2/N4/N5 ayakta kalır.
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
GATE = GATE_KOK / "check_no_rap_commit.py"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


def clas(govde: str) -> str:
    return (
        "CLASS zbp_i_zdemo_order DEFINITION PUBLIC FINAL CREATE PUBLIC "
        "FOR BEHAVIOR OF zdemo_i_order.\n"
        "  PUBLIC SECTION.\n"
        "    METHODS create_doc FOR MODIFY IMPORTING it_order FOR CREATE order.\n"
        "ENDCLASS.\n\n"
        "CLASS zbp_i_zdemo_order IMPLEMENTATION.\n"
        "  METHOD create_doc.\n"
        f"{govde}"
        "  ENDMETHOD.\n"
        "ENDCLASS.\n"
    )


def proje_kur(kok: Path, kaynak: str, dosya_adi: str = "zbp_i_zdemo_order.clas.abap") -> Path:
    d = kok / "SOURCE_CODES" / "SD" / "ZDEMO_PKG" / "src"
    d.mkdir(parents=True, exist_ok=True)
    (d / dosya_adi).write_text(kaynak, encoding="utf-8")
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
    except Exception as e:  # noqa: BLE001  (mutasyon-dostu: çökme değil ÖLÇÜM)
        return (-1, f"KOŞULAMADI: {type(e).__name__}: {e}")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ── POZİTİF (B2-07): ifade İKİ SATIRA bölünmüş ────────────────────────────────────
P1 = clas("    COMMIT\n      WORK.\n")
P2 = clas("    ROLLBACK\n      WORK.\n")
# ── POZİTİF (B2-08b): literal içindeki `\"` yorum sanılıp satırın gerisi atılıyordu ─
E1 = clas("    lv_x = 'say \"hi\"'. COMMIT WORK.\n")
# ── 3. BAĞLAM: farklı uzantı (.ccimp.abap = behavior pool) + çok-satırlı ifade ─────
E2 = clas("    COMMIT\n      WORK.\n")          # .ccimp.abap olarak yazılacak
# ── KONTROL GRUBU: fix'ten ÖNCE de yakalanan varyantlar ───────────────────────────
K1 = clas("    COMMIT WORK.\n")
K2 = clas("    CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'.\n")   # ⚠ literal İÇİNDE = GERÇEK pozitif
K3 = clas("    CALL FUNCTION 'SD_SCDS_CREATE' EXPORTING i_opt_commit = 'X'.\n")  # WARN
W1 = clas("    COMMIT ENTITIES BEGIN.\n")                                        # WARN
# ── FP ÇAPALARI ───────────────────────────────────────────────────────────────────
N1 = clas("    lv_msg = 'COMMIT WORK yapilmadi'.\n")            # B2-08a: literal → temiz
N2 = clas("*   COMMIT WORK burada yasak\n    lv_a = 1.\n")      # tam-satır yorumu
N4 = clas("    lv_a = 1.  \" COMMIT WORK burada yasak\n")       # satır-içi yorum
N5 = clas("    COMMIT.\n    work = 1.\n")                       # İKİ AYRI ifade (nokta ayırır)
N6 = clas("    lv_t = 'COMMIT ENTITIES'.\n")                    # WARN deseni de literalde temiz
N7 = clas("    COMMIT\n      WORK.  \"#NO_RAP_COMMIT_CHECK gercek non-RAP class\n")  # kaçış

# (kod, kaynak, beklenen_exit1, dosya_adi, beklenen_etiket, ad)
SENARYOLAR: list[tuple[str, str, bool, str, str, str]] = [
    ("P1", P1, True, "zbp_i_zdemo_order.clas.abap", "COMMIT WORK",
     "P1 çok-satırlı `COMMIT`/`WORK.` → ERROR (B2-07)"),
    ("P2", P2, True, "zbp_i_zdemo_order.clas.abap", "ROLLBACK WORK",
     "P2 çok-satırlı `ROLLBACK`/`WORK.` → ERROR (B2-07)"),
    ("E1", E1, True, "zbp_i_zdemo_order.clas.abap", "COMMIT WORK",
     "E1 literal içi `\"` yorum sanılıyordu → ifade artık görünüyor (B2-08b)"),
    ("E2", E2, True, "zbp_i_zdemo_order.ccimp.abap", "COMMIT WORK",
     "E2 3.BAĞLAM `.ccimp.abap` (behavior pool) + çok-satırlı ifade"),
    ("K1", K1, True, "zbp_i_zdemo_order.clas.abap", "COMMIT WORK",
     "K1 KONTROL tek-satır `COMMIT WORK.` → ERROR (eskiden de)"),
    ("K2", K2, True, "zbp_i_zdemo_order.clas.abap", "BAPI_TRANSACTION_COMMIT",
     "K2 NEGATİF KONTROL literal içi FM adı → ERROR KALMALI (literal temizliği bu kümeye UYGULANMAZ)"),
    ("K3", K3, False, "zbp_i_zdemo_order.clas.abap", "i_opt_commit",
     "K3 KONTROL `i_opt_commit='X'` → WARN (exit 0), literal gerekli"),
    ("W1", W1, False, "zbp_i_zdemo_order.clas.abap", "COMMIT ENTITIES",
     "W1 KONTROL `COMMIT ENTITIES` → WARN (exit 0)"),
    ("N1", N1, False, "zbp_i_zdemo_order.clas.abap", "",
     "N1 FP `'COMMIT WORK ...'` string literali → temiz (B2-08a)"),
    ("N2", N2, False, "zbp_i_zdemo_order.clas.abap", "",
     "N2 FP tam-satır `*` yorumu → temiz"),
    ("N4", N4, False, "zbp_i_zdemo_order.clas.abap", "",
     "N4 FP satır-içi `\"` yorumu → temiz"),
    ("N5", N5, False, "zbp_i_zdemo_order.clas.abap", "",
     "N5 FP `COMMIT.` + `work = 1.` İKİ AYRI ifade → temiz (birleştirmenin SINIRI)"),
    ("N6", N6, False, "zbp_i_zdemo_order.clas.abap", "",
     "N6 FP `'COMMIT ENTITIES'` literali → WARN bile yok"),
    ("N7", N7, False, "zbp_i_zdemo_order.clas.abap", "",
     "N7 FP çok-satırlı ifadede `#NO_RAP_COMMIT_CHECK` kaçışı KAPSANAN satırda → temiz"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="b2rap_"))
    try:
        for kod, kaynak, fail_bekleniyor, dosya, etiket, ad in SENARYOLAR:
            proje = proje_kur(tmp / kod, kaynak, dosya)
            rc, cikti = kos(proje)
            if rc < 0:
                kontrol(False, ad, cikti)
                continue
            if fail_bekleniyor:
                ok = rc == 1 and etiket in cikti
            elif etiket:                       # WARN beklenen: exit 0 AMA bulgu görünmeli
                ok = rc == 0 and etiket in cikti and "[UYARI]" in cikti
            else:                              # temiz beklenen: hiç bulgu olmamalı
                ok = rc == 0 and "[İHLAL]" not in cikti and "[UYARI]" not in cikti
            kontrol(ok, ad, f"exit={rc}" + ("" if ok else " :: " + cikti.strip()[:220]))

        # ── Yapısal çapa: iki kümenin AYRI kaldığı (K2'nin gerçek koruması) ──
        sys.path.insert(0, str(GATE_KOK))
        try:
            import check_no_rap_commit as R  # noqa: PLC0415
            kimlik = [lbl for _, lbl in getattr(R, "_ERROR_KIMLIK", [])]
            ifade = [lbl for _, lbl in getattr(R, "_ERROR_IFADE", [])]
            kontrol("BAPI_TRANSACTION_COMMIT" in kimlik,
                    "S1 FM-adı deseni KİMLİK kümesinde (literal korunur)", str(kimlik))
            kontrol("COMMIT WORK" in ifade,
                    "S2 `COMMIT WORK` İFADE kümesinde (literal boşaltılır)", str(ifade))
        except Exception as e:  # noqa: BLE001
            kontrol(False, "S1-S2 küme ayrımı çapası", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\nrap_commit_ifade_kapsami: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
