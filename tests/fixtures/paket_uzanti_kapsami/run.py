# -*- coding: utf-8 -*-
"""paket_uzanti_kapsami — naming + paket-sınırı gate'lerinin UZANTI KAPSAMI (KAYIT V2).

KÖK: iki gate de "hangi dosyalara bakacağını" bir allow-list'ten okur
(`check_package_naming.FOLDER_FILE_GLOBS`, `check_object_in_correct_pkg.OBJE_UZANTILARI`).
Listede olmayan uzantı HİÇ GÖRÜLMEZ; çıktı yine `[OK] ... doğru paket altında` /
`OK — N paket, naming ihlali yok` der. **"Bakmadım" ile "temiz" çıktıda ayırt edilemez** —
bu, run_all ailesinin tarihsel "dizin-yok → 0 dosya → GATE YEŞİL YANAR" sınıfının
(2026-07-09, d2d326d; `check_method_param_type_c` bilerek konan ihlale "[OK]" demişti)
uzantı-düzeyindeki ikizidir.

CANLI ÖLÇÜM (bir gerçek proje ağacı): paket-sınırı gate'i 340 dosya görüyordu, klasörlerdeki
gerçek obje sayısı 392'ydi → 52 dosya (26 `.bdef`, 15 `.srvd`, 7 `.tabl.ddl`, 3 `.dcl`,
1 `.tabl`) hiç kontrol edilmemişti. Yanlış-paket-prefiksli bir BDEF iki gate'ten de
sessizce geçiyordu.

İKİNCİ KÖK (ölçümle bulundu, brifingde yoktu): uzantıyı glob'a eklemek TEK BAŞINA yetmiyor.
Naming gate'i obje adını uzantıdan ayırırken BİLİNEN uzantı listesi kullanıyordu; bilinmeyen
uzantı kırpılmadan kalıyor, ad NOKTA taşıdığı için `^Z..._[A-Z0-9_]+$` regex'lerinin hiçbiri
eşleşemiyordu. Yalnız glob eklenince ölçüldü: 26 `.bdef`'in 26'sı da YANLIŞ-POZİTİF
(adları zaten kurala uygundu). Bu, 2026-07-28'deki `.ccau` vakasının aynısıydı (listeye
eklenmemiş uzantı → "hiçbir regex'le eşleşmiyor" sahte FAIL'i) — orada dosya listeye
eklenerek geçiştirilmişti, burada SINIF kapatıldı: SAP obje adı nokta içeremez → ad = ilk
noktaya kadar.

⚠ FP ÇAPALARI OMURGADIR (aşırı-sıkılaşma bekçisi):
  - N1/N2: doğru prefiksli + doğru adlandırılmış `.bdef`/`.tabl.ddl` → İKİ gate de PASS.
    Bu satırlar düşerse "ikinci kök" regresyona uğramıştır (uzantı kırpılmıyor demektir).
  - N3: `.srvd` naming gate'inde BİLİNÇLİ kapsam-dışıdır (Service Definition adı
    `Z<PKG>_UI_*`; kural paket `.rules.md`'sinde TABLO satırı değil DÜZ METİN → parse
    edilen regex kümesinde karşılığı yok; eklenirse 15 doğru dosya suçlanır). Bu satır
    kararın BEKÇİSİDİR: biri `*.srvd`'yi glob'a eklerse burada FAIL verir ve önce
    `.rules.md` şablonuna satır eklenmesi gerektiği hatırlatılır.
  - N4: `.srvd` paket-SINIRI gate'inde kapsam İÇİDİR (orada yalnız paket prefiksi
    ölçülür, tip-regex'i değil → FP riski yok). İki gate'in kapsamı BİLEREK farklıdır.

⚠ KONTROL GRUBU (K1/K2): yanlış-paket-prefiksli / kuralsız adlandırılmış `.cds` — eskiden
de yakalanan varyant. İki tarafta da FAIL vermeli; vermezse bulgu değil HARNESS bozuktur
(PATTERN#19).

Koşum:  python tests/fixtures/paket_uzanti_kapsami/run.py
MUTASYON: `git show <taban-sha>:scripts/validators/check_package_naming.py` (ve
          `check_object_in_correct_pkg.py`) ile eski sürümleri geri koy → P1..P4 düşer,
          K1/K2 ayakta kalır (harness ölçüyor kanıtı).
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
VALIDATORS = KOK / "scripts" / "validators"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


# Fixture paketi = ZSD001_CLC. "Yabancı" (yanlış paket) prefiksi = ZSD000_ — başka bir
# paketin namespace'i; aynı ağaçta durması cross-package sızıntısıdır.
RULES_MD = """# ZSD001_CLC paket kuralları (fixture)

## Naming (zorunlu prefix'ler)

| Obje Tipi | Prefix | Regex |
|---|---|---|
| CDS Interface View (RAP) | `ZSD001_I_*` | `^ZSD001_I_[A-Z0-9_]+$` |
| CDS Projection View (RAP) | `ZSD001_C_*` | `^ZSD001_C_[A-Z0-9_]+$` |
| Tablo | `ZSD001_T_*` | `^ZSD001_T_[A-Z0-9_]+$` |
| Class | `ZCL_SD001_*` | `^ZCL_SD001_[A-Z0-9_]+$` |

## Bilinen İstisnalar
- yok
"""


def proje_kur(kok: Path, dosyalar: dict[str, str]) -> Path:
    """<kok>/SOURCE_CODES/SD/ZSD001_CLC/... ağacını kurar; proje kökünü döner."""
    pkg = kok / "SOURCE_CODES" / "SD" / "ZSD001_CLC"
    (pkg / "cds").mkdir(parents=True, exist_ok=True)
    (pkg / "tables").mkdir(parents=True, exist_ok=True)
    (pkg / ".rules.md").write_text(RULES_MD, encoding="utf-8")
    for rel, icerik in dosyalar.items():
        p = pkg / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(icerik, encoding="utf-8")
    return kok


def kos(validator: str, proje: Path) -> tuple[int, str]:
    """Validator'ı fixture proje kökünde koştur (miras env SIZMAZ)."""
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    try:
        p = subprocess.run([sys.executable, str(VALIDATORS / f"{validator}.py")],
                           cwd=str(proje), env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
    except Exception as e:  # noqa: BLE001  (mutasyon-dostu: çökme ölçülen sonuca çevrilir)
        return (-1, f"KOŞULAMADI: {type(e).__name__}: {e}")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


BDEF = "managed implementation in class zbp_i_zsd001_order unique;\nstrict ( 2 );\n"
CDS = "define view entity ZSD001_I_X as select from t000 { key mandt as Mandt }\n"
TABL = ("@EndUserText.label : 'T'\ndefine table zsd001_t_x {\n"
        "  key mandt : mandt not null;\n}\n")
DCL = "@EndUserText.label: 'DCL'\ndefine role ZSD001_C_X {}\n"
SRVD = "@EndUserText.label: 'SRVD'\ndefine service ZSD001_UI_X {}\n"


SENARYOLAR: list[tuple[str, dict[str, str], str, bool, str]] = [
    # (kod, dosyalar, validator, FAIL_bekleniyor_mu, açıklama)

    # ── POZİTİF: kapsam boşluğunun ta kendisi ─────────────────────────────────
    ("P1", {"cds/ZSD000_I_YABANCI.bdef": BDEF}, "check_object_in_correct_pkg", True,
     "P1 yanlış-paket-prefiksli .bdef → paket-sınırı FAIL"),
    ("P2", {"cds/ZSD001_X_KURALSIZ.bdef": BDEF}, "check_package_naming", True,
     "P2 kurala uymayan .bdef adı → naming FAIL"),
    ("P3", {"tables/ZSD000_T_YABANCI.tabl.ddl": TABL}, "check_object_in_correct_pkg", True,
     "P3 yanlış-paket-prefiksli .tabl.ddl → paket-sınırı FAIL"),
    ("P4", {"cds/ZSD000_C_YABANCI.dcl": DCL}, "check_object_in_correct_pkg", True,
     "P4 yanlış-paket-prefiksli .dcl → paket-sınırı FAIL"),

    # ── KONTROL GRUBU: eskiden de yakalanan varyant (harness ölçüyor mu?) ─────
    ("K1", {"cds/ZSD000_I_YABANCI.cds": CDS}, "check_object_in_correct_pkg", True,
     "K1 KONTROL yanlış-paket-prefiksli .cds → paket-sınırı FAIL"),
    ("K2", {"cds/ZSD001_X_KURALSIZ.cds": CDS}, "check_package_naming", True,
     "K2 KONTROL kurala uymayan .cds adı → naming FAIL"),

    # ── FP ÇAPALARI ───────────────────────────────────────────────────────────
    ("N1", {"cds/ZSD001_I_ORDER.bdef": BDEF, "cds/ZSD001_C_ORDER.bdef": BDEF},
     "check_package_naming", False,
     "N1 FP doğru adlandırılmış .bdef → naming PASS (uzantı kırpılıyor mu?)"),
    ("N2", {"tables/ZSD001_T_ORDER.tabl.ddl": TABL}, "check_package_naming", False,
     "N2 FP doğru adlandırılmış .tabl.ddl → naming PASS (çift uzantı kırpılıyor mu?)"),
    ("N3", {"cds/ZSD001_UI_ORDER.srvd": SRVD}, "check_package_naming", False,
     "N3 FP .srvd naming gate'inde BİLİNÇLİ kapsam-dışı (karar bekçisi)"),
    ("N4", {"cds/ZSD001_UI_ORDER.srvd": SRVD}, "check_object_in_correct_pkg", False,
     "N4 FP doğru prefiksli .srvd → paket-sınırı PASS (kapsam İÇİ ama temiz)"),
    ("N5", {"cds/ZSD001_I_ORDER.bdef": BDEF}, "check_object_in_correct_pkg", False,
     "N5 FP doğru prefiksli .bdef → paket-sınırı PASS"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="paket_uzanti_"))
    try:
        for kod, dosyalar, validator, fail_bekleniyor, ad in SENARYOLAR:
            proje = proje_kur(tmp / kod, dosyalar)
            rc, cikti = kos(validator, proje)
            if rc < 0:
                kontrol(False, ad, cikti)
                continue
            oldu = rc != 0
            kontrol(oldu == fail_bekleniyor, ad,
                    f"exit={rc} (beklenen {'!=0' if fail_bekleniyor else '0'})"
                    + ("" if oldu == fail_bekleniyor else " :: " + cikti.strip()[:200]))

        # ── Yapısal çapa: allow-list'ler beyanı karşılıyor mu (sessiz daralma bekçisi) ──
        sys.path.insert(0, str(VALIDATORS))
        try:
            import check_object_in_correct_pkg as O  # noqa: PLC0415
            uz = getattr(O, "OBJE_UZANTILARI", None)
            eksik = [u for u in (".bdef", ".srvd", ".ddl", ".dcl", ".tabl")
                     if uz is None or u not in uz]
            kontrol(not eksik, "S1 paket-sınırı uzantı kümesi 5 SAP uzantısını kapsıyor",
                    f"eksik={eksik}")
        except Exception as e:  # noqa: BLE001
            kontrol(False, "S1 paket-sınırı uzantı kümesi", f"{type(e).__name__}: {e}")
        try:
            import check_package_naming as N  # noqa: PLC0415
            cds_glob = (getattr(N, "FOLDER_FILE_GLOBS", {}) or {}).get("cds", [])
            tbl_glob = (getattr(N, "FOLDER_FILE_GLOBS", {}) or {}).get("tables", [])
            kontrol("*.bdef" in cds_glob, "S2 naming glob'u `.bdef` içeriyor",
                    f"cds={cds_glob}")
            kontrol("*.srvd" not in cds_glob,
                    "S3 naming glob'u `.srvd` İÇERMİYOR (bilinçli; `.rules.md` satırı önkoşul)",
                    f"cds={cds_glob}")
            kontrol("*.tabl.ddl" in tbl_glob, "S4 naming glob'u `.tabl.ddl` içeriyor",
                    f"tables={tbl_glob}")
        except Exception as e:  # noqa: BLE001
            kontrol(False, "S2-S4 naming glob'ları", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\npaket_uzanti_kapsami: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
