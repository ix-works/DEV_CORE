#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIXTURE — `post_tool_failure` hook'unun **Bash yüzeyi** (2026-08-14).

NİÇİN VAR (ölçülmüş vaka): hook yalnız `mcp__sap-adt__.*` matcher'ına bağlıydı. Bir SAP-yazma
turunda **12 push denemesinin tamamı `Bash` üzerinden** (`python push_object.py …`) koştu ⇒ hook
HİÇ ateşlemedi. Oysa aradığı imzalar (`invalidlockhandle`, `is not locked`) listesinde ZATEN
vardı ve cevap `playbook/known-errors.md` §12.7c'de 3 gün önce yazılıydı. Ağ vardı; delik tam
düşülen yerdeydi. Bu korpus o deliğin **kapalı kaldığını** bekçilik eder.

İKİ DEĞİŞMEZ (ikisi de ayrı mutasyonla ölçülür):
  ① ATEŞLEME  — SAP-yazma komutu + tanınan hata imzası → hatırlatma ÜRETİLİR.
  ② SESSİZLİK — diğer HER durumda çıktı YOK. (Gürültü yapan hook ölü hook'tur: operatör
     filtrelemeyi öğrenir ve gerçek uyarıyı da görmez.)
İkinci değişmez birincisi kadar önemlidir; bu yüzden FP çapaları (N1-N4) mutasyonlarda AYAKTA.

Koşum:  python tests/fixtures/post_tool_failure_bash/run.py
Mutasyon (İKİSİ DE koşulur — biri diğerini KAPSAMAZ):
  --mutasyon-kapi1    Kapı-1'i (komut imzası) devre dışı bırakır → N2/N4 DÜŞMELİ
  --mutasyon-imza     Kapı-2'ye jenerik imza ('error') ekler    → N1/N3 DÜŞMELİ
Herhangi biri tam puan verirse korpus O DEĞİŞMEZ için BOŞTUR.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    for _akis in (sys.stdout, sys.stderr):
        try:
            _akis.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

KOK = Path(__file__).resolve().parents[3]
HOOK = KOK / "scripts" / "hooks" / "post_tool_failure.py"


def _kos(hook_yolu: Path, payload) -> tuple:
    """Hook'u GERÇEK giriş noktasından (stdin JSON) çağır."""
    ham = payload if isinstance(payload, str) else json.dumps(payload)
    p = subprocess.run([sys.executable, str(hook_yolu)], input=ham,
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def _bash(komut: str, cikti: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": komut},
            "tool_response": {"stdout": cikti, "stderr": ""}}


# (ad, payload, KONUŞMALI mı)
VEKTORLER = [
    # ── ① ATEŞLEME çapaları ────────────────────────────────────────────────
    ("P1 Bash + push_object + [ERROR] [423]",
     _bash("python core/scripts/push_object.py --name ZCL_X --type class",
           "[ERROR] [423] Failed to set source after 4 attempts."), True),
    ("P2 Bash + push_object + 400 Session Timed Out",
     _bash("python push_object.py --name ZCL_Y", "400 Session Timed Out"), True),
    ("P3 Bash + push_object + 'is not locked'",
     _bash("python push_object.py --name ZCL_Z",
           "Resource CLASS ZCL_Z is not locked (invalid lock handle: ABC)"), True),
    ("P4 imza STDERR'de (stdout temiz)",
     {"tool_name": "Bash", "tool_input": {"command": "python push_bo_atomic.py --kind class"},
      "tool_response": {"stdout": "", "stderr": "ExceptionResourceInvalidLockHandle"}}, True),

    # ── ② SESSİZLİK (FP) çapaları — mutasyonlarda AYAKTA kalmalı ───────────
    ("N1 SAP aracı ama BAŞARILI çıktı",
     _bash("python core/scripts/push_object.py --name ZCL_X",
           "[OK] Source uploaded\n[OK] Object activated"), False),
    ("N2 SAP-DIŞI komut, çıktıda hata metni olsa bile (kapı-1)",
     _bash("git status && npm test",
           "is not locked invalid lock handle session timed out"), False),
    ("N3 sıradan Bash çağrısı",
     _bash("ls -la", "total 42"), False),
    ("N4 SALT-OKUMA aracı (sap_sync_pull) — bilinçli kapsam dışı",
     _bash("python core/scripts/sap_sync_pull.py ZCL_X --type class",
           "[ERROR] [423] is not locked"), False),
    # ⚠ N5, kapı-1'in ARKASINDA kalan tek FP yüzeyini ölçer: SAP aracı BAŞARILI koştu ama
    #   çıktısında jenerik kelimeler ('error', 'warning') geçiyor. Kapı-2'ye jenerik imza
    #   eklenirse HER başarılı push'ta hatırlatma basılır = gürültü = hook'un ölümü.
    #   (Bu vektör olmadan `--mutasyon-imza` 12/12 veriyordu ⇒ korpus O DEĞİŞMEZ için BOŞTU.)
    ("N5 SAP aracı + BAŞARILI ama çıktıda jenerik 'error/warning' kelimeleri",
     _bash("python core/scripts/push_object.py --name ZCL_X --type class",
           "[OK] Source uploaded (0 errors, 2 warnings)\n[OK] Object activated — total 1 object"), False),

    # ── REGRESYON: MCP dalı bozulmadı ──────────────────────────────────────
    ("R1 MCP fail → hâlâ konuşur",
     {"tool_name": "mcp__sap-adt__adt_push_source", "tool_input": {"name": "ZCL_X"},
      "tool_response": {"ok": False, "error": "sap_error"}}, True),
    ("R2 MCP başarılı → sessiz",
     {"tool_name": "mcp__sap-adt__adt_get", "tool_input": {"name": "ZCL_X"},
      "tool_response": {"ok": True, "exists": True}}, False),
]


def _mutant(kip: str) -> Path:
    """Mutasyonu BUGÜNKÜ kaynaktan üret (git ref'inden DEĞİL: 'fix merge olunca taban kayar' yok).

    Mutant hook'un KENDİ dizinine yazılır — komşu modül importu kırılmasın (B0 dersi).
    """
    kaynak = HOOK.read_text(encoding="utf-8")
    if kip == "kapi1":
        yeni, n = re.subn(r"if not any\(s in komut for s in _BASH_SAP_KOMUT_IMZALARI\):\n\s*return 0.*",
                          "if False:\n        return 0", kaynak, count=1)
    elif kip == "imza":
        yeni, n = re.subn(r'(_BASH_FAIL_IMZALARI = \(\n)', r'\1    "error", "total",\n', kaynak, count=1)
    else:
        raise SystemExit(f"bilinmeyen mutasyon: {kip}")
    if n != 1:
        raise SystemExit(f"[KOSUCU DURDU] mutasyon capasi bulunamadi (kip={kip}) — "
                         "kaynak degismis olabilir; SAYI RAPORLAMIYORUM.")
    hedef = HOOK.parent / "_mutant_post_tool_failure.py"
    hedef.write_text(yeni, encoding="utf-8")
    return hedef


def main() -> int:
    kip = None
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon-"):
            kip = a.replace("--mutasyon-", "")

    hook_yolu = HOOK
    try:
        if kip:
            hook_yolu = _mutant(kip)
            print(f"  (MUTASYON: {kip} — ayirt edici vektorler DUSMELI)\n")

        sonuc = []
        for ad, payload, konusmali in VEKTORLER:
            rc, out, _ = _kos(hook_yolu, payload)
            ok = (rc == 0) and (bool(out) == konusmali)
            sonuc.append((ad, ok, f"exit={rc} cikti={'VAR' if out else 'YOK'} beklenen={'VAR' if konusmali else 'YOK'}"))

        # C1 — bozuk girdi sözleşmesi (exit 0 fail-safe + stderr NOTU); B0b sınıfı
        rc, out, err = _kos(hook_yolu, "{bozuk-json")
        sonuc.append(("C1 bozuk JSON -> exit 0 + stderr NOTU (fail-safe korundu)",
                      rc == 0 and "GIRDI-PARSE-EDILEMEDI" in err and not out,
                      f"exit={rc} not={'VAR' if 'GIRDI-PARSE-EDILEMEDI' in err else 'YOK'}"))

        # C2 — hatırlatma known-errors.md'ye YÖNLENDİRİYOR mu (dersin ta kendisi)
        rc, out, _ = _kos(hook_yolu, VEKTORLER[0][1])
        sonuc.append(("C2 hatirlatma known-errors.md'ye yonlendiriyor",
                      "known-errors.md" in out, f"cikti_uzunluk={len(out)}"))

        gecen = sum(1 for _, ok, _ in sonuc if ok)
        for ad, ok, detay in sonuc:
            print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
        print(f"\n{gecen}/{len(sonuc)} OK")
        return 0 if gecen == len(sonuc) else 1
    finally:
        if kip:
            try:
                (HOOK.parent / "_mutant_post_tool_failure.py").unlink()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
