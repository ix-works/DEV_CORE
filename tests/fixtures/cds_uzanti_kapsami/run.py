# -*- coding: utf-8 -*-
"""cds_uzanti_kapsami — `check_cds_srvd_comment_syntax` UZANTI KAPSAMI (B2-10).

KÖK (2026-08-28 adversarial bug-avı): gate `f.lower().endswith((".cds", ".srvd"))` ile
seçiyordu. Ama AYNI CDS/DDL kaynağı repoda ÜÇ uzantıyla yaşıyor — bu bizim kendi yazma
yolumuzun sözleşmesi (`source_drift._TYPE_TO_EXTENSIONS`: table/structure →
`.asddls/.ddls/.cds`). Sonuç: `.ddls.asddls` uzantılı DDL kaynakları **hiç taranmıyordu**.

Liderin canlı ölçümü (fix öncesi): AYNI içerik `.cds`'te `1 ihlal`, `.ddls.asddls`'te
*"temiz"*. Bu LATENT bir boşluk DEĞİLDİ: tüketici projede 28 `.asddls` + 1 `.ddls` +
12 `.ddl` = **41 dosya** denetim dışıydı.

NEDEN ÖNEMLİ (BE-61): bu hata sınıfı SESSİZDİR — CDS DDL'de `"` yorum değildir; SAP
kaynağı hiç almaz ama push `[OK] Source uploaded` + `[OK] Object activated` der ve canlı
kaynak DEĞİŞMEZ. Yakalayan tek şey readback eşitliğidir. Yani taranmayan 41 dosyada
sapma sessizce birikebilirdi (kural yokken 3 SRVD'nin aylarca sapık kalması gibi).

⚠ KAPSAM GENİŞLETMESİ = SIKILAŞTIRMA, ama yine de bir KARARDIR. Ölçüldü (2026-08-28,
  tüketici korpusu): 280 → 321 dosya, **0 yeni bulgu** (`tara_cds` her aday uzantıda
  0 döndü) ⇒ FP riski ölçülmüş, sıfır. `.dcl` (3) ve `.bdef` (32) de ölçüldü (0 bulgu)
  ama BİLİNÇLİ olarak kapsama ALINMADI — ayrı artefakt sınıflarıdır (BDEF'in kendi
  kapısı var: check_bdef_backtick). Emsal: 2026-08-01 `check_package_naming` turunda
  `.srvd` 15 FP nedeniyle EKLENMEMİŞTİ; genişletme kanıtla yapılır, refleksle değil.

⚠ FP ÇAPALARI: N1/N2 — doğru `//` yorumu ve annotation'daki tek-tırnaklı literal
  (`'Şoför Ana Verisi'`) her uzantıda sessiz kalmalı. Düşerlerse gate 41 dosyanın
  tamamına bağırır.

Koşum:     python tests/fixtures/cds_uzanti_kapsami/run.py
MUTASYON:  B2_GATE_KOK=<taban b2ab7f1 validators dizini> → P1/P2/P3 DÜŞER;
           K1/K2/N1/N2 ayakta kalır.
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
GATE = GATE_KOK / "check_cds_srvd_comment_syntax.py"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


# `"` = CDS DDL'de YORUM DEĞİL → SAP sessizce reddeder
BOZUK = ('@EndUserText.label : \'Demo Yapisi\'\n'
         '"Bu ABAP tarzi yorum CDS/DDL kaynaginda GECERSIZ\n'
         'define structure zdemo_s_basic {\n'
         '  full_name : abap.char(100);\n'
         '}\n')
TEMIZ = ('@EndUserText.label : \'Demo Yapisi\'\n'
         '// CDS DDL dogru yorum sozdizimi: // ve /* */\n'
         'define structure zdemo_s_basic {\n'
         '  full_name : abap.char(100);\n'
         '}\n')
# FP çapası: annotation literalinde apostrof + `//` yorumu birlikte
TEMIZ_LITERAL = ('@EndUserText.label : \'Sofor Ana Verisi\'\n'
                 '@AbapCatalog.tableCategory : #TRANSPARENT\n'
                 '// kaynak: TD-spec // ikinci egik cizgi de sorun degil\n'
                 'define table zdemo_t_driver {\n'
                 '  key mandt : mandt not null;\n'
                 '}\n')
SRVD_BOZUK = ('@EndUserText.label: \'Demo Servis\'\n'
              '// SRVD yorum DESTEKLEMEZ\n'
              'define service ZDEMO_SRV {\n'
              '  expose zdemo_i_order;\n'
              '}\n')


def proje_kur(kok: Path, dosya_adi: str, icerik: str) -> Path:
    d = kok / "SOURCE_CODES" / "SD" / "ZDEMO_PKG" / "structures"
    d.mkdir(parents=True, exist_ok=True)
    (d / dosya_adi).write_text(icerik, encoding="utf-8")
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


SENARYOLAR: list[tuple[str, str, str, bool, str]] = [
    ("P1", "ZDEMO_S_BASIC.ddls.asddls", BOZUK, True,
     "P1 `.ddls.asddls` içinde `\"` yorumu → İHLAL (B2-10; 28 canlı dosya)"),
    ("P2", "ZDEMO_S_BASIC.struct.ddls", BOZUK, True,
     "P2 `.ddls` içinde `\"` yorumu → İHLAL"),
    ("P3", "ZDEMO_T_DRIVER.tabl.ddl", BOZUK, True,
     "P3 `.ddl` (define table) içinde `\"` yorumu → İHLAL (12 canlı dosya)"),
    ("K1", "ZDEMO_I_ORDER.cds", BOZUK, True,
     "K1 KONTROL `.cds` → İHLAL (eskiden de)"),
    ("K2", "ZDEMO_SRV.srvd", SRVD_BOZUK, True,
     "K2 KONTROL `.srvd` yorum yasağı DEĞİŞMEDİ → İHLAL"),
    ("N1", "ZDEMO_S_BASIC.ddls.asddls", TEMIZ, False,
     "N1 FP doğru `//` yorumu `.asddls`'te → temiz"),
    ("N2", "ZDEMO_T_DRIVER.tabl.ddl", TEMIZ_LITERAL, False,
     "N2 FP annotation literali + `//` yorumu `.ddl`'de → temiz"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="b2cds_"))
    try:
        for kod, dosya, icerik, fail_bekleniyor, ad in SENARYOLAR:
            proje = proje_kur(tmp / kod, dosya, icerik)
            rc, cikti = kos(proje)
            if rc < 0:
                kontrol(False, ad, cikti)
                continue
            ok = (rc == 1 and "[İHLAL]" in cikti) if fail_bekleniyor \
                else (rc == 0 and "[İHLAL]" not in cikti)
            kontrol(ok, ad, f"exit={rc}" + ("" if ok else " :: " + cikti.strip()[:200]))

        # ── Yapısal çapa: uzantı ailesi + BİLİNÇLİ dışarıda bırakılanlar ──
        sys.path.insert(0, str(GATE_KOK))
        try:
            import check_cds_srvd_comment_syntax as C  # noqa: PLC0415
            uz = set(getattr(C, "_CDS_UZANTILARI", ()))
            kontrol({".cds", ".ddls", ".asddls", ".ddl"} <= uz,
                    "S1 CDS-DDL uzantı ailesi tam", str(sorted(uz)))
            kontrol(".dcl" not in uz and ".bdef" not in uz,
                    "S2 `.dcl`/`.bdef` BİLİNÇLİ olarak kapsam DIŞI (ayrı artefakt sınıfı)",
                    str(sorted(uz)))
        except Exception as e:  # noqa: BLE001
            kontrol(False, "S1-S2 uzantı çapası", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\ncds_uzanti_kapsami: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
