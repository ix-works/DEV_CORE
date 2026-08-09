# -*- coding: utf-8 -*-
"""ui5_t1_tirnak_sinifi — UI5 T1 (V2-nav `_X`) deseninin TIRNAK SINIFI (KAYIT V6).

KÖK: `check_ui5_freestyle_traps` T1 desenlerinden ikisi tırnak sınıfı olarak `["\\']`
kullanıyordu → ES6 **template literal** (ters-tırnak) desenin DIŞINDA kalıyordu:
    createEntry(`_Container`, {...})        → YAKALANMIYORDU
    { $expand: `_Container` }               → YAKALANMIYORDU
Modern UI5 controller'ları template literal'i rutin kullanır; yani bu, tesadüfi değil
ZAMANLA BÜYÜYEN bir boşluktu (aynı sınıf: `check_bdef_backtick`, 2026-07-29 — ters-tırnak
repoda 2 iken canlıda 8'di).

NEDEN ÖNEMLİ: T1 bir **ERROR**'dur, build DURDURUR. Kaçan `_X` nav adı OData V2'de
SESSİZCE kırılır (RAP composition `_X` → V2'de `to_X`) — yani gate'in var oluş sebebi olan
tam hasar, gate açıkken gerçekleşebiliyordu.

⚠ BRİFİNGİN İDDİASI DOĞRULANDI, VARSAYILMADI: kuyruk-kaydı "2. desen (`/_[A-Z]` yol
segmenti) tırnaktan bağımsız ve ETKİLENMİYOR; kapsamı abartma" diyordu. Bu bir hipotezdi
ve E1/E2 vektörleriyle ÖLÇÜLDÜ — ters-tırnaklı yol ifadesi ESKİ kodda da yakalanıyor.
Bu yüzden fix YALNIZ `createEntry` ve `$expand` desenlerine dokundu; 2. desen elden
geçirilMEDİ (gereksiz genişletme = FP üretir).

⚠ DURUM: LATENT. Canlı proje UI kodunda `createEntry(` hiç ÖLÇÜLMEDİ (0 eşleşme) →
fix bugünkü bir ihlali düzeltmez, yarınki yazımı yakalar. Kanıt bu fixture'dır.

⚠ FP ÇAPALARI OMURGADIR: N2/N3 — ters-tırnak KULLANAN ama adı DOĞRU (`to_X`) kod sessiz
kalmalı. Düşerlerse gate her template literal'e bağırır ve alarm-yorgunluğundan ölür.
N4: `/to_Container` yol segmenti de sessiz kalmalı (2. desenin FP çapası).

⚠ KONTROL GRUBU (K1/K2): çift-tırnaklı `_X` — eskiden de yakalanan varyant. İki tarafta
da ERROR vermeli; vermezse bulgu değil HARNESS bozuktur (PATTERN#19). Aynı vaka ayrıca
`tests/fixtures/check_ui5_freestyle_traps/{bad,good}` çiftinde de yaşar (bilinçli örtüşme:
o çift bad/good koşucusunun, bu dosya vektör-ölçümünün kanıtıdır).

Koşum:  python tests/fixtures/ui5_t1_tirnak_sinifi/run.py
MUTASYON: `git show <taban-sha>:scripts/validators/check_ui5_freestyle_traps.py` →
          P1/P2 düşer; K1/K2/E1/E2 ve N* ayakta kalır.
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
GATE = KOK / "scripts" / "validators" / "check_ui5_freestyle_traps.py"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


def controller(govde: str) -> str:
    return (
        'sap.ui.define([\n'
        '    "sap/ui/core/mvc/Controller"\n'
        '], function (Controller) {\n'
        '    "use strict";\n\n'
        '    return Controller.extend("zsd001.controller.Booking", {\n'
        '        onGo: function () {\n'
        '            var oModel = this.getView().getModel();\n'
        f'{govde}'
        '        }\n'
        '    });\n'
        '});\n'
    )


def proje_kur(kok: Path, js: str) -> Path:
    d = kok / "SOURCE_CODES" / "ZSD001" / "ui" / "webapp" / "controller"
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
    except Exception as e:  # noqa: BLE001  (mutasyon-dostu)
        return (-1, f"KOŞULAMADI: {type(e).__name__}: {e}")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ── POZİTİF: template literal (ters-tırnak) kaçışı ────────────────────────────────
P1 = controller('            oModel.createEntry(`_Container`, { properties: {} });\n')
P2 = controller('            oModel.read("/Booking", { urlParameters: { $expand: `_Container` } });\n')

# ── KONTROL GRUBU: çift-tırnaklı aynı ihlal (eskiden de yakalanan) ────────────────
K1 = controller('            oModel.createEntry("_Container", { properties: {} });\n')
K2 = controller('            oModel.read("/Booking", { urlParameters: { "$expand": "_Container" } });\n')

# ── 3. BAĞLAM: 2. desen (`/_[A-Z]`) tırnaktan BAĞIMSIZ — brifing iddiasının ölçümü ─
E1 = controller('            oModel.read(`/Booking(\'1\')/_Container`, {});\n')
E2 = controller('            oModel.read("/Booking(\'1\')/_Container", {});\n')

# ── FP ÇAPALARI ───────────────────────────────────────────────────────────────────
N1 = controller('            oModel.createEntry("to_Container", { properties: {} });\n')
N2 = controller('            oModel.createEntry(`to_Container`, { properties: {} });\n')
N3 = controller('            oModel.read("/Booking", { urlParameters: { $expand: `to_Container` } });\n')
N4 = controller('            oModel.read(`/Booking(\'1\')/to_Container`, {});\n')
N5 = controller('            var sMsg = `Kayit ${this._id} guncellendi`;\n')

SENARYOLAR: list[tuple[str, str, bool, str]] = [
    ("P1", P1, True, "P1 `createEntry(`_Container`)` template literal → ERROR"),
    ("P2", P2, True, "P2 ``$expand: `_Container` `` template literal → ERROR"),
    ("K1", K1, True, "K1 KONTROL `createEntry(\"_Container\")` çift tırnak → ERROR"),
    ("K2", K2, True, "K2 KONTROL `\"$expand\": \"_Container\"` → ERROR"),
    ("E1", E1, True, "E1 3.BAĞLAM ters-tırnaklı `/_Container` yolu (2. desen, DEĞİŞMEDİ)"),
    ("E2", E2, True, "E2 3.BAĞLAM tırnaklı `/_Container` yolu (2. desen kontrol)"),
    ("N1", N1, False, "N1 FP `createEntry(\"to_Container\")` → temiz"),
    ("N2", N2, False, "N2 FP `createEntry(`to_Container`)` ters-tırnak + doğru ad → temiz"),
    ("N3", N3, False, "N3 FP ``$expand: `to_Container` `` → temiz"),
    ("N4", N4, False, "N4 FP `/to_Container` yol segmenti → temiz"),
    ("N5", N5, False, "N5 FP alakasız template literal (`${...}` interpolasyon) → temiz"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ui5_t1_"))
    try:
        for kod, js, fail_bekleniyor, ad in SENARYOLAR:
            proje = proje_kur(tmp / kod, js)
            rc, cikti = kos(proje)
            if rc < 0:
                kontrol(False, ad, cikti)
                continue
            oldu = rc != 0
            ok = oldu == fail_bekleniyor and (not fail_bekleniyor or "T1" in cikti)
            kontrol(ok, ad, f"exit={rc} (beklenen {'1' if fail_bekleniyor else '0'})"
                    + ("" if ok else " :: " + cikti.strip()[:200]))

        # ── Yapısal çapa: tırnak sınıfı + 2. desenin DOKUNULMADIĞI ──
        sys.path.insert(0, str(KOK / "scripts" / "validators"))
        try:
            import check_ui5_freestyle_traps as U  # noqa: PLC0415
            desenler = [p.pattern for p in getattr(U, "_T1_PATTERNS", [])]
            kontrol(any("createEntry" in d and "`" in d for d in desenler),
                    "S1 createEntry deseni ters-tırnağı kapsıyor", str(desenler[:1]))
            kontrol(any("expand" in d and "`" in d for d in desenler),
                    "S2 $expand deseni ters-tırnağı kapsıyor",
                    str([d for d in desenler if "expand" in d]))
            kontrol(any(d == r"/_[A-Z]" for d in desenler),
                    "S3 yol deseni `/_[A-Z]` DEĞİŞTİRİLMEDİ (bilinçli dar kapsam)",
                    str(desenler))
        except Exception as e:  # noqa: BLE001
            kontrol(False, "S1-S3 desen çapaları", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\nui5_t1_tirnak_sinifi: {gecen}/{len(SONUC)}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
