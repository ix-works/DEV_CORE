# -*- coding: utf-8 -*-
"""filtre_yorum_ve_tirnak — `check_filter_search_pattern` (B2-02 yanlış-pozitif + B2-03 kaçış).

İKİ KUSUR, TEK KÖK (2026-08-28 adversarial bug-avı): gate JS'i **ham satır** olarak
görüyordu; ne yorum DURUMU ne de anahtar YAZIMI normalize ediliyordu.

  B2-03 (KAÇIŞ) — `_CASE_SENS` deseni tırnaksız nesne anahtarı varsayıyordu.
    `caseSensitive: false`   → BLOCKER
    `"caseSensitive": false` → *"[OK] ihlal yok"*   ← canlı ölçüm, lider (fix öncesi)
    JS'te ikisi de AYNI anahtardır ve UI5'e aynı `toupper/tolower` $filter'ını üretir
    → aynı HTTP 400 (SAP Note 1797736). Yazım biçimi bu gate için meşru sınır DEĞİLDİR.

  B2-02 (YANLIŞ-POZİTİF) — `strip_line_comment()` satırlar-arası durum tutmuyordu:
    çok-satırlı `/* ... */` bloğunun İÇİ kod sayılıyor, ölü/örnek kod **BLOCKER**
    üretiyordu. Bir BLOCKER build'i DURDURUR; yorumdaki örnek yüzünden duran build,
    gate'e güveni doğrudan aşındırır (alarm-yorgunluğu → gate'i atlama refleksi).

⚠ POZİTİF KONTROL ZORUNLU (FP düzeltirken gerçek pozitifi kaybetme): K1/P1/P2 aynı
  korpusta duruyor. E1 blok yorumu KAPANDIKTAN sonra gelen gerçek ihlalin hâlâ
  yakalandığını çiviler — blok durumu "açık kalırsa" dosyanın gerisi sessizce körelir
  ve bu, düzelttiğimizden DAHA KÖTÜ bir sessiz kaçış olurdu.

⚠ E2 tarama katmanının ikinci kazancı: `"http://..."` string'i içindeki `//` artık
  satır-yorumu sanılmıyor → aynı satırdaki gerçek ihlal görünüyor (eskiden satırın
  gerisi atılıyordu = sessiz kaçış).

⚠ ÖLÇÜLDÜ AMA DOKUNULMADI (kapsam dışı, karar liderde): `notCaseSensitive: false`
  hem eski hem yeni desende eşleşir (alt-dizge FP'si). Bu FP sınıfı bu turda GELMEDİ,
  düzeltilmesi desen DARALTMASI = gevşetme-bayrağı gerektirir → ayrı kalem olarak
  raporlandı, burada TEST EDİLMİYOR (yanlış davranışı fixture'a çivilemeyelim).

⚠ DURUM: LATENT (canlı korpus 124 UI dosyası → fix öncesi/sonrası 0 bulgu, BAYT AYNI).

Koşum:     python tests/fixtures/filtre_yorum_ve_tirnak/run.py
MUTASYON:  B2_GATE_KOK=<taban b2ab7f1 validators dizini> → P1/P2/N1/N2/E2 DÜŞER;
           K1/E1/N3/N4/W1 ayakta kalır.
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
GATE = GATE_KOK / "check_filter_search_pattern.py"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


def controller(govde: str) -> str:
    return (
        'sap.ui.define([\n'
        '    "sap/ui/core/mvc/Controller",\n'
        '    "sap/ui/model/Filter"\n'
        '], function (Controller, Filter) {\n'
        '    "use strict";\n\n'
        '    return Controller.extend("zdemo.controller.Search", {\n'
        '        onSearch: function (sQuery) {\n'
        f'{govde}'
        '        }\n'
        '    });\n'
        '});\n'
    )


def proje_kur(kok: Path, js: str) -> Path:
    d = kok / "SOURCE_CODES" / "SD" / "ZDEMO_PKG" / "ui" / "rapor" / "webapp" / "controller"
    d.mkdir(parents=True, exist_ok=True)
    (d / "Search.controller.js").write_text(js, encoding="utf-8")
    return kok


def proje_kur_view(kok: Path, xml: str) -> Path:
    d = kok / "SOURCE_CODES" / "SD" / "ZDEMO_PKG" / "ui" / "rapor" / "webapp" / "view"
    d.mkdir(parents=True, exist_ok=True)
    (d / "Filter.view.xml").write_text(xml, encoding="utf-8")
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


# ── POZİTİF (B2-03): tırnaklı anahtar ─────────────────────────────────────────────
P1 = controller('            var f = new Filter({ path: "Id", "caseSensitive": false });\n')
P2 = controller("            var f = new Filter({ path: 'Id', 'caseSensitive': false });\n")
# ── KONTROL: tırnaksız (eskiden de yakalanan) ────────────────────────────────────
K1 = controller('            var f = new Filter({ path: "Id", caseSensitive: false });\n')
# ── POZİTİF KONTROL: blok yorumu KAPANDIKTAN sonra gerçek ihlal hâlâ görülüyor ───
E1 = controller('            /*\n'
                '               eski deneme: caseSensitive: false\n'
                '            */\n'
                '            var f = new Filter({ path: "Id", caseSensitive: false });\n')
# ── POZİTİF (yan kazanç): string içindeki `//` satırı yutuyordu ──────────────────
E2 = controller('            var u = "http://ornek.test/api"; '
                'var f = new Filter({ path: "Id", caseSensitive: false });\n')
# ── FP ÇAPALARI (B2-02) ──────────────────────────────────────────────────────────
N1 = controller('            /*\n'
                '               ESKI KOD (silinmedi, ornek):\n'
                '               var f = new Filter({ caseSensitive: false });\n'
                '            */\n'
                '            var f = new Filter({ path: "Id" });\n')
N2 = controller('            /**\n'
                '             * ARSIV: caseSensitive: false kullanmayin\n'
                '             */\n'
                '            var f = new Filter({ path: "Id" });\n')
N3 = controller('            // caseSensitive: false KULLANMA (FE-32)\n'
                '            var f = new Filter({ path: "Id" });\n')
N4 = controller('            var f = new Filter({ path: "Id" }); '
                '/* caseSensitive: false yasak */\n')

VIEW_W1 = ('<mvc:View xmlns:mvc="sap.ui.core.mvc" xmlns="sap.m">\n'
           '  <Input id="idKunnr" valueHelpRequest=".onF4"/>\n'
           '</mvc:View>\n')

SENARYOLAR: list[tuple[str, str, int, str, str]] = [
    ("P1", P1, 1, "[İHLAL]", "P1 `\"caseSensitive\": false` çift-tırnaklı anahtar → BLOCKER (B2-03)"),
    ("P2", P2, 1, "[İHLAL]", "P2 `'caseSensitive': false` tek-tırnaklı anahtar → BLOCKER (B2-03)"),
    ("K1", K1, 1, "[İHLAL]", "K1 KONTROL tırnaksız anahtar → BLOCKER (eskiden de)"),
    ("E1", E1, 1, "[İHLAL]", "E1 POZİTİF KONTROL blok yorumu KAPANDIKTAN sonraki ihlal → BLOCKER"),
    ("E2", E2, 1, "[İHLAL]", "E2 string içindeki `//` satırı yutmuyor → ihlal görünüyor"),
    ("N1", N1, 0, "", "N1 FP yıldızsız çok-satırlı `/* */` içindeki ölü kod → temiz (B2-02)"),
    ("N2", N2, 0, "", "N2 FP JSDoc `/** */` bloğu içindeki anım → temiz (B2-02)"),
    ("N3", N3, 0, "", "N3 FP `//` satır yorumu → temiz (eskiden de)"),
    ("N4", N4, 0, "", "N4 FP tek satırlık `/* */` yorumu → temiz (eskiden de)"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="b2filt_"))
    try:
        for kod, js, beklenen_rc, etiket, ad in SENARYOLAR:
            proje = proje_kur(tmp / kod, js)
            rc, cikti = kos(proje)
            if rc < 0:
                kontrol(False, ad, cikti)
                continue
            ok = rc == beklenen_rc and (etiket in cikti if etiket else "[İHLAL]" not in cikti)
            kontrol(ok, ad, f"exit={rc}" + ("" if ok else " :: " + cikti.strip()[:220]))

        # ── W1: WARNING dalı (IX sözleşmesi) bozulmadı ──
        proje = proje_kur_view(tmp / "W1", VIEW_W1)
        rc, cikti = kos(proje)
        kontrol(rc == 0 and "[UYARI]" in cikti,
                "W1 KONTROL Filter.view.xml valueHelpRequest+MultiInput yok → WARNING (exit 0)",
                f"exit={rc}")

        # ── Yapısal çapa ──
        sys.path.insert(0, str(GATE_KOK))
        try:
            import check_filter_search_pattern as F  # noqa: PLC0415
            kontrol(bool(F._CASE_SENS.search('"caseSensitive": false')),
                    "S1 desen tırnaklı anahtarı kapsıyor", F._CASE_SENS.pattern)
            kontrol(F.strip_line_comment('var a = 1; // x').strip() == "var a = 1;",
                    "S2 tek-satır kırpma API'si korundu (geriye dönük çapa)")
        except Exception as e:  # noqa: BLE001
            kontrol(False, "S1-S2 yapısal çapa", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\nfiltre_yorum_ve_tirnak: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
