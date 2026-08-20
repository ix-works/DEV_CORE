#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATOR — hook'ların ENJEKTE ettiği doküman yolları gerçekten açılabiliyor mu?

NEDEN (2026-07-09 denetimi): `skill_injector` ve `intake_triage`, ajana "OKU: <yol>" diye
ZORUNLU okuma talimatı enjekte ediyor. Metodoloji `core/` junction'ı altına taşınınca
enjekte edilen yollar öneksiz kaldı:

    Read("playbook/intake-triage.md")       -> "File does not exist"

Ölçüm: bir oturumda 32 `OKU:` talimatı enjekte edildi, 0 checklist okundu. Kırık yol,
"o dosya yok" gibi okunur — ajan protokolü atlar. Bu validator o sessiz kırılmayı yakalar.

ENFORCES: C-HOOK-01 (enjekte edilen her .md yolu proje kökünden çözülmeli)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Windows konsolu cp1252'dir: Türkçe karakterli çıktı UnicodeEncodeError ile ÇÖKER →
# validator her ortamda exit 1 verip SAHTE FAIL üretir (bu dosyanın ilk koşumunda oldu).
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

CORE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CORE / "scripts"))
from utils.project_config import project_root  # type: ignore  # noqa: E402

PROJ = project_root()

# Farklı iş-tiplerini tetikleyen örnek prompt'lar (her biri farklı checklist enjekte eder)
ORNEK_PROMPTLAR = [
    "RAP BDEF yarat, CDS view ekle, freestyle UI5 yap",
    "klasik ALV raporu yaz, DDIC struct ekle",
    "domain ve DTEL yarat, tablo ekle",
    "yeni bir rapor gelistir",          # intake_triage tetikleyicisi
]

HOOKLAR = ("skill_injector", "intake_triage")
YOL_DESENI = re.compile(r"[\w/\-.]+\.md")

# ── K8② (2026-08-20): STDERR nudge'ları da ENJEKSİYONDUR ─────────────────────
# Gate yalnız `additionalContext` üreten (UserPromptSubmit) hook'ları yokluyordu.
# Ama `post_validate` gibi PostToolUse hook'ları yolu **stderr**e yazar ve o metin
# de ajana geri beslenir (exit 2). Yani AYNI kırılma orada da olur — C-HOOK-01
# onu GÖRMÜYORDU. (Ölçüldü 2026-08-17: iki nudge'da çıplak `playbook/…` vardı.)
#
# ⚠ KAPSAM GENİŞLEMESİ (ADR 0019) — ÖLÇÜLDÜ, sertleştirme riski YOK:
#    bugünkü taban 4 yol / 0 kırık. Yani gate ne ÖLÜ (4 yol görüyor) ne de
#    GEÇİLEMEZ (0 ihlal). Taban 0 olduğu için mevcut HARD şiddeti korunur.
#
# ⚠ DETERMİNİZM: doc-fs nudge'ı bir "OKU-işaretçisi" (dedup marker) tutar; marker
#    varsa nudge SUSAR. Gerçek proje kökünde yoklarsak sonuç GÜNE göre değişir
#    (bugün 4 yol, yarın 0) ⇒ gate sessizce boşalır. Bu yüzden stderr sondası
#    HER KOŞUMDA TEMİZ bir sandbox kökü kullanır: marker asla önceden var olmaz.
STDERR_HOOKLAR = ("post_validate",)

# (etiket, göreli-yol) — nudge desenlerini tetikleyen temsili düzenlemeler.
STDERR_PAYLOADLARI = (
    ("KD dokümanı", "docs/KD-ORNEK.md"),
    ("FS dokümanı", "docs/ZORNEK-FS-v1.0.md"),
    ("infra validator", "core/scripts/validators/check_ornek.py"),
)


def _hook_ciktisi(hook: str, prompt: str) -> str:
    shim = PROJ / "scripts" / "hook_shim.py"
    argv = [sys.executable, str(shim), hook] if shim.exists() else \
           [sys.executable, str(CORE / "scripts" / "hooks" / f"{hook}.py")]
    r = subprocess.run(argv, input=json.dumps({"prompt": prompt}), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=60,
                       env=dict(os.environ, CLAUDE_PROJECT_DIR=str(PROJ)))
    if r.returncode != 0 or not r.stdout.strip():
        return ""
    try:
        return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    except Exception:
        return ""


def _stderr_ciktisi(hook: str, rel_yol: str) -> str:
    """PostToolUse hook'unu TEMIZ bir sandbox kokUyle kos, stderr'i dondur.

    Sandbox SART: nudge'larin dedup marker'i gercek proje kokUnde ZATEN VAR olabilir
    -> nudge susar -> gate "hic yol yok" deyip SESSIZCE bosalir (kendini kapatan gate).
    Temiz kok her kosumda ayni sonucu verir (idempotans).
    """
    import shutil
    import tempfile

    kum = Path(tempfile.mkdtemp(prefix="chip_"))
    try:
        (kum / "project.yaml").write_text(
            "sap_profile: s4_private\nsource_root: SOURCE_CODES\nmaster_language: TR\n",
            encoding="utf-8")
        hedef = kum / rel_yol
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text("# ornek\n", encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(CORE / "scripts" / "hooks" / f"{hook}.py")],
            input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(hedef)}}),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
            env=dict(os.environ, CLAUDE_PROJECT_DIR=str(kum), PYTHONIOENCODING="utf-8"))
        return r.stderr or ""
    except Exception:
        return ""
    finally:
        shutil.rmtree(kum, ignore_errors=True)


def main() -> int:
    kirik: list = []
    toplam = 0
    # HIZ (2026-08-13, süre-vergisi kuyruğu): iş `HOOKLAR × ORNEK_PROMPTLAR` = 8 AYRI
    # süreç başlatır ve her biri tam bir Python yorumlayıcısı + hook yüklemesidir.
    # ÖLÇÜLDÜ (cProfile): 8 `CreateProcess` + 2,8 sn thread-lock beklemesi ⇒ maliyetin
    # TAMAMI süreç bekleme; doküman/veri büyümesi DEĞİL (kod #4'ten beri değişmedi,
    # büyüyen şey kombinasyon sayısı ve hook başlangıç maliyetiydi).
    # Çağrılar BİRBİRİNDEN BAĞIMSIZ (her biri kendi payload'ıyla salt-okur bir hook
    # koşumu) → paralelleştirilir. `run_all_validators.py` aynı deseni kullanıyor.
    # ⚠ ÇIKTI SIRASI KORUNUR: sonuçlar KANONİK sırada (hook, prompt) toplanır —
    # yoksa bulgu listesi koşumdan koşuma değişir ve diff'lenemez hâle gelirdi.
    from concurrent.futures import ThreadPoolExecutor

    isler = [(hook, p) for hook in HOOKLAR for p in ORNEK_PROMPTLAR]
    with ThreadPoolExecutor(max_workers=min(8, len(isler))) as havuz:
        gelecekler = [havuz.submit(_hook_ciktisi, hook, p) for hook, p in isler]
        ciktilar = [(hook, p, f.result()) for (hook, p), f in zip(isler, gelecekler)]

    # K8②: stderr nudge'lari (PostToolUse) — ayni C-HOOK-01 degismezi orada da gecerli
    for _hook in STDERR_HOOKLAR:
        for _etiket, _rel in STDERR_PAYLOADLARI:
            ciktilar.append((f"{_hook}(stderr:{_etiket})", _rel,
                             _stderr_ciktisi(_hook, _rel)))

    for hook, p, metin in ciktilar:
        if not metin:
            continue
        for yol in sorted(set(YOL_DESENI.findall(metin))):
            toplam += 1
            if not (PROJ / yol).is_file():
                kirik.append(f"{hook}: '{yol}' çözülmüyor (prompt: {p[:30]}…)")

    if not toplam:
        print("  [WARN] hiçbir yol enjekte edilmedi — örnek prompt'lar tetiklemiyor olabilir")
        return 0
    if kirik:
        print(f"  [FAIL] enjekte edilen {len(kirik)}/{toplam} yol PROJE KÖKÜNDEN ÇÖZÜLMÜYOR:")
        for k in kirik:
            print(f"         - {k}")
        print("         Ajan bu yolu Read edemez → 'dosya yok' sanır → ZORUNLU protokolü atlar.")
        print("         Çözüm: core/scripts/utils/inject_paths.py::core_onekle() ile önekle.")
        return 1
    print(f"  [OK] enjekte edilen {toplam} doküman yolunun tamamı çözülüyor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
