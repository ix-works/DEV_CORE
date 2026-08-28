# -*- coding: utf-8 -*-
"""ui5_blok_yorumu — `check_ui5_freestyle_traps` T1 YORUM-DURUMU (B2-06, yanlış-pozitif).

KÖK (2026-08-28 adversarial bug-avı): `_scan()` JS'te yorumu şöyle eliyordu:
    if stripped.startswith("//") or stripped.startswith("*"): continue
Bu yalnızca JSDoc gibi **hizalı** blokları atlar. Yıldızsız çok-satırlı `/* ... */`
bloğunun içi KOD sayılır — ve T1 bir **ERROR**'dur, yani BUILD DURUR. Yorumdaki ölü
kod yüzünden duran build, gate'e güveni doğrudan aşındırır: bir sonraki geliştirici
gate'i atlamayı öğrenir ve T1'in gerçekten yakaladığı sessiz V2-nav kırılması
(RAP composition `_X` → V2'de `to_X`) ilk kullanıcı testine kadar görünmez kalır.
Yani yanlış-pozitif burada "gürültü" değil, gerçek kaçış RİSKİDİR.

Ek olarak `/*` bloğunun ilk satırı da (`/* ... */` tek satırlık dahil) hiçbir
`startswith` ölçütüne uymadığı için taranıyordu.

⚠ POZİTİF KONTROL OMURGADIR (FP düzeltirken gerçek pozitifi kaybetme): K1/K2 gerçek
  ihlaller, E1 ise blok KAPANDIKTAN sonraki ihlaldir. Blok durumu "açık kalırsa"
  dosyanın gerisi sessizce körelir — düzelttiğimizden DAHA KÖTÜ bir hâl. E1 tam olarak
  bunu ölçer.

⚠ E2 yan kazanç: `"http://..."` string'i içindeki `//` artık satır-yorumu sanılmıyor →
  aynı satırdaki gerçek T1 ihlali görünüyor (eskiden `//`den sonrası zaten taranıyordu
  çünkü kırpma YOKTU; burada kanıt, yeni kırpmanın string'i BOZMADIĞIDIR).

⚠ DESENLERE DOKUNULMADI: `_T1_PATTERNS` aynen duruyor (S1 çapası). 2026-08-01'de
  ters-tırnak eklenmişti; bu tur yalnız TARAMA KATMANINI değiştirir. Komşu fixture
  `ui5_t1_tirnak_sinifi` 14/14 ile regresyon kapısıdır.

⚠ DURUM: LATENT (canlı korpus 0 ERROR / 7 WARN; fix öncesi/sonrası BAYT AYNI).

Koşum:     python tests/fixtures/ui5_blok_yorumu/run.py
MUTASYON:  B2_GATE_KOK=<taban b2ab7f1 validators dizini> → N1/N2/N4 DÜŞER;
           K1/K2/E1/E2/N3 ayakta kalır.
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
GATE = GATE_KOK / "check_ui5_freestyle_traps.py"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


def controller(govde: str) -> str:
    return (
        'sap.ui.define([\n'
        '    "sap/ui/core/mvc/Controller"\n'
        '], function (Controller) {\n'
        '    "use strict";\n\n'
        '    return Controller.extend("zdemo.controller.Booking", {\n'
        '        onGo: function () {\n'
        '            var oModel = this.getView().getModel();\n'
        f'{govde}'
        '        }\n'
        '    });\n'
        '});\n'
    )


def proje_kur(kok: Path, js: str) -> Path:
    d = kok / "SOURCE_CODES" / "SD" / "ZDEMO_PKG" / "ui" / "app" / "webapp" / "controller"
    d.mkdir(parents=True, exist_ok=True)
    (d / "Booking.controller.js").write_text(js, encoding="utf-8")
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


# ── FP ÇAPALARI (B2-06): yorum içindeki ölü kod ERROR üretmemeli ─────────────────
N1 = controller('            /*\n'
                '               ESKI DENEME (silinmedi):\n'
                '               oModel.createEntry("_Container", {});\n'
                '            */\n'
                '            oModel.createEntry("to_Container", {});\n')
N2 = controller('            /* oModel.createEntry("_Container", {}); */\n'
                '            oModel.createEntry("to_Container", {});\n')
N3 = controller('            // oModel.createEntry("_Container", {});\n'
                '            oModel.createEntry("to_Container", {});\n')
N4 = controller('            /*\n'
                '               yol ornegi: "/Booking(\'1\')/_Container"\n'
                '            */\n'
                '            oModel.read("/Booking(\'1\')/to_Container", {});\n')
# ── POZİTİF KONTROL: gerçek ihlaller hâlâ yakalanıyor ────────────────────────────
K1 = controller('            oModel.createEntry("_Container", {});\n')
K2 = controller('            oModel.read("/Booking(\'1\')/_Destination", {});\n')
E1 = controller('            /*\n'
                '               eski not\n'
                '            */\n'
                '            oModel.createEntry("_Container", {});\n')
E2 = controller('            var u = "http://ornek.test/x"; '
                'oModel.createEntry("_Container", {});\n')

SENARYOLAR: list[tuple[str, str, bool, str]] = [
    ("N1", N1, False, "N1 FP yıldızsız çok-satırlı `/* */` içindeki `_Container` → temiz (B2-06)"),
    ("N2", N2, False, "N2 FP tek satırlık `/* ... */` yorumu → temiz (B2-06)"),
    ("N3", N3, False, "N3 FP `//` satır yorumu → temiz (eskiden de)"),
    ("N4", N4, False, "N4 FP yorum içindeki `/_Container` yol segmenti (2. desen) → temiz"),
    ("K1", K1, True, "K1 POZİTİF KONTROL gerçek `createEntry(\"_Container\")` → ERROR"),
    ("K2", K2, True, "K2 POZİTİF KONTROL gerçek `/_Destination` yol segmenti → ERROR"),
    ("E1", E1, True, "E1 blok yorumu KAPANDIKTAN sonraki gerçek ihlal → ERROR (körleşme yok)"),
    ("E2", E2, True, "E2 string içindeki `//` kırpmayı bozmuyor → ihlal görünüyor"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="b2ui5_"))
    try:
        for kod, js, fail_bekleniyor, ad in SENARYOLAR:
            proje = proje_kur(tmp / kod, js)
            rc, cikti = kos(proje)
            if rc < 0:
                kontrol(False, ad, cikti)
                continue
            # ⚠ Çapa `[İHLAL]`dir, "T1" DEĞİL: temiz çıktı da "T1/T2/T3 yok" der →
            #   dize araması sahte-KIRMIZI verirdi (ölçüldü, ilk yazımda düştü).
            ok = (rc == 1 and "[İHLAL]" in cikti and "T1 V2-nav" in cikti) if fail_bekleniyor \
                else (rc == 0 and "[İHLAL]" not in cikti)
            kontrol(ok, ad, f"exit={rc}" + ("" if ok else " :: " + cikti.strip()[:200]))

        # ── Yapısal çapa: desen kümesi DEĞİŞMEDİ (fix tarama katmanında) ──
        sys.path.insert(0, str(GATE_KOK))
        try:
            import check_ui5_freestyle_traps as U  # noqa: PLC0415
            desenler = [p.pattern for p in getattr(U, "_T1_PATTERNS", [])]
            kontrol(r"/_[A-Z]" in desenler and len(desenler) == 3,
                    "S1 `_T1_PATTERNS` DEĞİŞMEDİ (3 desen, yol deseni yerinde)",
                    str(desenler))
        except Exception as e:  # noqa: BLE001
            kontrol(False, "S1 desen çapası", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\nui5_blok_yorumu: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
