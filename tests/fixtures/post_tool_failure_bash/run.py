#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIXTURE — `post_tool_failure` hook'unun **Bash yüzeyi** (2026-08-14) + **PostToolUseFailure
olayı** (2026-11-19).

NİÇİN VAR (ölçülmüş vaka 1, 2026-08-14): hook yalnız `mcp__sap-adt__.*` matcher'ına bağlıydı. Bir
SAP-yazma turunda **12 push denemesinin tamamı `Bash` üzerinden** (`python push_object.py …`) koştu
⇒ hook HİÇ ateşlemedi. Oysa aradığı imzalar (`invalidlockhandle`, `is not locked`) listesinde ZATEN
vardı ve cevap `playbook/known-errors.md` §12.7c'de 3 gün önce yazılıydı.

NİÇİN VAR (ölçülmüş vaka 2, 2026-11-19): Bash dalı eklendi ama hook yalnız `PostToolUse` olayına
bağlıydı. Claude Code çıkış kodu ≠0 olan Bash/PowerShell çağrısını ve hata dönen MCP aracını
`PostToolUseFailure` olayına gönderir; o olayın payload'ında `tool_response` YOKTUR, hata metni
üst düzey `error` alanındadır ("Exit code N" + çıktı). `push_object.py` hata yolunda `return 1`
döner ⇒ vaka 1'in düzeltmesi tam o yolu kapsamıyordu. Kontrol gruplu ölçüm (lider): aynı çıktı
`exit 0` ile merdiveni bastı, `exit 1` ile sessiz kaldı. Resmî şema:
code.claude.com/docs/en/hooks §PostToolUseFailure.

DEĞİŞMEZLER (her biri ayrı mutasyonla ölçülür):
  ① ATEŞLEME  — SAP-yazma komutu + tanınan hata imzası → hatırlatma ÜRETİLİR (iki olayda da).
  ② SESSİZLİK — diğer HER durumda çıktı YOK (gürültü yapan hook ölü hook'tur).
  ③ OLAY ADI  — çıktının `hookEventName`'i koşan olayın adıdır.
  ④ KABLOLAMA — şablon hook'u `PostToolUseFailure` olayına Bash + PowerShell + sap-adt
     eşleyicisiyle bağlar (kod ≠ kablolama).

Koşum:  python tests/fixtures/post_tool_failure_bash/run.py
Mutasyon (HEPSİ koşulur — biri diğerini KAPSAMAZ; her kip DÜŞMESİ beklenen vektörleri İLAN eder):
  --mutasyon-kapi1      Kapı-1'i (komut imzası) devre dışı bırakır          → N2/N4 DÜŞMELİ
  --mutasyon-imza       Kapı-2'ye jenerik imza ('error') ekler              → N5/FN2 DÜŞMELİ
  --mutasyon-olaybash   kabuk dalı `error` alanını okumaz                   → F1/F2/F3/F5/C2 DÜŞMELİ
  --mutasyon-olaymcp    MCP dalı PostToolUseFailure'ı tanımaz               → FM1/FM2/C3 DÜŞMELİ
  --mutasyon-olayadi    hookEventName sabit "PostToolUse"                   → O1 DÜŞMELİ
  --mutasyon-kablo      şablon kopyasından PostToolUseFailure bloğu silinir → K1 DÜŞMELİ
Çıkış: 0 tam puan · 1 mutasyon İLAN edilen vektörleri düşürdü (ya da tabanda FAIL) ·
2 SAPMA (ilan edilen vektör düşmedi / beklenmeyen vektör düştü) · 3 mutasyon kurulamadı.
Testler ve mutantlar YALNIZ `tempfile.mkdtemp()` altına yazar.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

if sys.platform == "win32":
    for _akis in (sys.stdout, sys.stderr):
        try:
            _akis.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

KOK = Path(__file__).resolve().parents[3]
HOOK = KOK / "scripts" / "hooks" / "post_tool_failure.py"
SABLON = KOK / "claude" / "settings.template.json"

_GECERLI_KIP = ("--mutasyon-kapi1", "--mutasyon-imza", "--mutasyon-olaybash",
                "--mutasyon-olaymcp", "--mutasyon-olayadi", "--mutasyon-kablo")


def _kos(hook_yolu: Path, payload) -> tuple:
    """Hook'u GERÇEK giriş noktasından (stdin JSON) çağır."""
    ham = payload if isinstance(payload, str) else json.dumps(payload)
    p = subprocess.run([sys.executable, str(hook_yolu)], input=ham,
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def _bash(komut: str, cikti: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": komut},
            "tool_response": {"stdout": cikti, "stderr": ""}}


def _hata(arac: str, komut: str, hata: str, **ek) -> dict:
    """PostToolUseFailure — resmî örnek payload'ın TAM alan kümesi (tool_response YOK)."""
    d = {"session_id": "fixture", "transcript_path": "fixture.jsonl", "cwd": ".",
         "permission_mode": "default", "hook_event_name": "PostToolUseFailure",
         "tool_name": arac, "tool_input": {"command": komut, "description": "fixture"},
         "tool_use_id": "toolu_fixture", "error": hata, "is_interrupt": False,
         "duration_ms": 4187}
    d.update(ek)
    return d


def _mcp_hata(arac: str, girdi: dict, hata: str, **ek) -> dict:
    d = {"session_id": "fixture", "transcript_path": "fixture.jsonl", "cwd": ".",
         "permission_mode": "default", "hook_event_name": "PostToolUseFailure",
         "tool_name": arac, "tool_input": girdi, "tool_use_id": "toolu_fixture",
         "mcp_server": {"name": "sap-adt", "source": "project"},
         "error": hata, "is_interrupt": False, "duration_ms": 812}
    d.update(ek)
    return d


# (ad, payload, KONUŞMALI mı)
VEKTORLER = [
    # ── ① ATEŞLEME çapaları — PostToolUse (exit 0) ─────────────────────────
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

    # ── ① ATEŞLEME çapaları — PostToolUseFailure (exit ≠ 0; 2026-11-19) ───
    # F2 liderin kontrol gruplu ölçümündeki çıktının birebir biçimi.
    ("F1 FAILURE Bash + push_object exit 1 + [ERROR] [423]",
     _hata("Bash", "python core/scripts/push_object.py --name ZCL_X --type class",
           "Exit code 1\n[ERROR] [423] Failed to set source after 4 attempts."), True),
    ("F2 FAILURE Bash + push_object exit 1 + HTTP 423 InvalidLockHandle",
     _hata("Bash", "python push_object.py ZSD001",
           "Exit code 1\nHTTP 423 InvalidLockHandle - is not locked"), True),
    # ③ görev-DIŞI bağlam: başka kabuk (PowerShell) + başka SAP aracı + kesilmiş çıktı işareti
    ("F3 FAILURE PowerShell + deploy_ui exit 1 + kesilmiş çıktıda imza",
     _hata("PowerShell", "python C:/x/core/scripts/deploy_ui.py --app zsd001",
           "Exit code 1\n... [5120 characters truncated] ...\nActivation failed for ZSD001_UI"),
     True),
    ("F5 FAILURE Bash + populate_ exit 2 + Session Timed Out (stdout/stderr karışık)",
     _hata("Bash", "python core/scripts/populate_cds_views.py --package ZSD001",
           "Exit code 2\n[INFO] 3 view\n400 Session Timed Out\nCommand timed out after 2m 0s"),
     True),
    ("FM1 FAILURE MCP adt_push_source düz metin hata",
     _mcp_hata("mcp__sap-adt__adt_push_source", {"name": "ZCL_X", "object_type": "clas"},
               "Error executing tool adt_push_source: 423 Locked"), True),
    ("FM2 FAILURE MCP ddls + 'is not locked' (CDS reçetesi dalı)",
     _mcp_hata("mcp__sap-adt__adt_push_source", {"name": "ZSD001_I_X", "object_type": "ddls"},
               "Error executing tool adt_push_source: Resource is not locked"), True),

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
    #   çıktısında jenerik kelimeler ('error', 'warning') geçiyor.
    ("N5 SAP aracı + BAŞARILI ama çıktıda jenerik 'error/warning' kelimeleri",
     _bash("python core/scripts/push_object.py --name ZCL_X --type class",
           "[OK] Source uploaded (0 errors, 2 warnings)\n[OK] Object activated — total 1 object"), False),
    # FAILURE olayında SESSİZLİK: exit ≠ 0 tek başına konuşturmaz (iki kapı aynen geçerli).
    ("FN1 FAILURE sıradan komut exit 1 (npm test) — kapı-1",
     _hata("Bash", "npm test", "Exit code 1\nError: Cannot find module 'express'"), False),
    ("FN2 FAILURE SAP aracı exit 1 ama SAP imzası yok (ortam hatası) — kapı-2",
     _hata("Bash", "python core/scripts/push_object.py --name ZCL_X",
           "Exit code 1\nTraceback (most recent call last):\nModuleNotFoundError: No module named 'requests'"),
     False),
    # grep eşleşmesizlikte exit 1 döner ve komut metninde SAP aracı adı geçer → kapı-1 GEÇER;
    # sessizliği yalnız kapı-2 taşır (exit kodunu tek başına imza sayan tasarımın FP'si).
    ("FN3 FAILURE grep eşleşmesiz exit 1 (komutta push_object.py geçiyor)",
     _hata("Bash", "grep -rn push_object.py docs/", "Exit code 1"), False),
    ("FN4 FAILURE MCP kesintisi (is_interrupt=true) — araç hatası değil",
     _mcp_hata("mcp__sap-adt__adt_push_source", {"name": "ZCL_X"}, "Interrupted",
               is_interrupt=True), False),

    # ── REGRESYON: MCP PostToolUse dalı bozulmadı ──────────────────────────
    ("R1 MCP fail → hâlâ konuşur",
     {"tool_name": "mcp__sap-adt__adt_push_source", "tool_input": {"name": "ZCL_X"},
      "tool_response": {"ok": False, "error": "sap_error"}}, True),
    ("R2 MCP başarılı → sessiz",
     {"tool_name": "mcp__sap-adt__adt_get", "tool_input": {"name": "ZCL_X"},
      "tool_response": {"ok": True, "exists": True}}, False),
]

# Mutasyon kipi → DÜŞMESİ İLAN edilen vektörler (ad öneki). Fazlası da SAPMA sayılır.
ILAN = {
    "kapi1": {"N2", "N4"},
    "imza": {"N5", "FN2"},
    "olaybash": {"F1", "F2", "F3", "F5", "C2"},   # C2 F1'in metnini okur
    "olaymcp": {"FM1", "FM2", "C3"},   # C3 FM2'nin metnini okur
    "olayadi": {"O1"},
    "kablo": {"K1"},
}


def _mutant_hook(kip: str, dizin: Path) -> Path:
    """Mutasyonu BUGÜNKÜ kaynaktan üret (git ref'inden DEĞİL). Hook yalnız stdlib import eder ⇒
    mutant TEMP dizininde koşabilir (repo ağacına yazılmaz)."""
    kaynak = HOOK.read_text(encoding="utf-8")
    if kip == "kapi1":
        yeni, n = re.subn(r"if not any\(s in komut for s in _BASH_SAP_KOMUT_IMZALARI\):\n\s*return 0.*",
                          "if False:\n        return 0", kaynak, count=1)
    elif kip == "imza":
        yeni, n = re.subn(r'(_BASH_FAIL_IMZALARI = \(\n)', r'\1    "error", "total",\n', kaynak, count=1)
    elif kip == "olaybash":
        yeni, n = re.subn(r'\n\s*parcalar\.append\(str\(data\.get\("error"\) or ""\)\)', "", kaynak, count=1)
    elif kip == "olaymcp":
        yeni, n = re.subn(r'if olay == "PostToolUseFailure":  # MCP-HATA-DALI',
                          "if False:", kaynak, count=1)
    elif kip == "olayadi":
        yeni, n = re.subn(r'"hookEventName": olay,', '"hookEventName": "PostToolUse",', kaynak, count=1)
    else:
        raise ValueError(kip)
    if n != 1:
        print(f"[KURULAMADI] mutasyon capasi bulunamadi (kip={kip}) — kaynak degismis olabilir; "
              "SAYI RAPORLAMIYORUM.")
        sys.exit(3)
    hedef = dizin / "_mutant_post_tool_failure.py"
    hedef.write_text(yeni, encoding="utf-8")
    return hedef


def _mutant_sablon(dizin: Path) -> Path:
    veri = json.loads(SABLON.read_text(encoding="utf-8"))
    if "PostToolUseFailure" not in (veri.get("hooks") or {}):
        print("[KURULAMADI] sablonda PostToolUseFailure yok — kablo mutasyonu kurulamaz.")
        sys.exit(3)
    del veri["hooks"]["PostToolUseFailure"]
    hedef = dizin / "settings.template.json"
    hedef.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
    return hedef


def _kablo_kontrol(sablon_yolu: Path) -> tuple[bool, str]:
    """K1: şablonda PostToolUseFailure → post_tool_failure bağlantısı; eşleyici Claude Code gibi
    (çapasız regex `search`) Bash · PowerShell · sap-adt aracını TUTAR, Write/Read'i TUTMAZ."""
    veri = json.loads(sablon_yolu.read_text(encoding="utf-8"))
    eslikler = []
    for blok in (veri.get("hooks") or {}).get("PostToolUseFailure") or []:
        for k in blok.get("hooks") or []:
            if "post_tool_failure" in [str(a) for a in (k.get("args") or [])]:
                eslikler.append(str(blok.get("matcher") or ""))
    if not eslikler:
        return False, "PostToolUseFailure altinda post_tool_failure bagi YOK"
    e = eslikler[0]
    tutmali = ["Bash", "PowerShell", "mcp__sap-adt__adt_push_source"]
    tutmamali = ["Write", "Read", "mcp__other__x"]
    ok = all(re.search(e, a) for a in tutmali) and not any(re.search(e, a) for a in tutmamali)
    return ok, f"eslikler={eslikler}"


def _post_kontrol(sablon_yolu: Path) -> tuple[bool, str]:
    """K2 regresyon: PostToolUse bağlantısı yerinde."""
    veri = json.loads(sablon_yolu.read_text(encoding="utf-8"))
    for blok in (veri.get("hooks") or {}).get("PostToolUse") or []:
        for k in blok.get("hooks") or []:
            if "post_tool_failure" in [str(a) for a in (k.get("args") or [])]:
                return blok.get("matcher") == "mcp__sap-adt__.*|Bash", f"matcher={blok.get('matcher')}"
    return False, "PostToolUse bagi YOK"


def _v(onek: str) -> dict:
    """Vektörü AD ÖNEKİYLE bul (liste sırası değişince çapa kaymasın)."""
    return next(p for ad, p, _k in VEKTORLER if ad.split()[0] == onek)


def _context(out: str) -> tuple[str, str]:
    try:
        h = json.loads(out)["hookSpecificOutput"]
        return str(h.get("hookEventName", "")), str(h.get("additionalContext", ""))
    except Exception:
        return "", ""


def main() -> int:
    kip = None
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon"):
            if a not in _GECERLI_KIP:
                print(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} — gecerli: {', '.join(_GECERLI_KIP)}")
                return 3
            kip = a.replace("--mutasyon-", "")

    gecici = Path(tempfile.mkdtemp(prefix="ptf_fixture_"))
    hook_yolu, sablon_yolu = HOOK, SABLON
    if kip == "kablo":
        sablon_yolu = _mutant_sablon(gecici)
    elif kip:
        hook_yolu = _mutant_hook(kip, gecici)
    if kip:
        print(f"  (MUTASYON: {kip} — ilan edilen vektorler DUSMELI: {sorted(ILAN[kip])})\n")

    sonuc = []
    olay_ok = True
    olay_detay = []
    for ad, payload, konusmali in VEKTORLER:
        rc, out, _ = _kos(hook_yolu, payload)
        ok = (rc == 0) and (bool(out) == konusmali)
        sonuc.append((ad, ok, f"exit={rc} cikti={'VAR' if out else 'YOK'} beklenen={'VAR' if konusmali else 'YOK'}"))
        if konusmali and out:
            beklenen = payload.get("hook_event_name") or "PostToolUse"
            gelen, _ctx = _context(out)
            if gelen != beklenen:
                olay_ok = False
                olay_detay.append(f"{ad.split()[0]}:{gelen or '?'}≠{beklenen}")

    # O1 — çıktının olay adı koşan olayınki (Claude Code hookSpecificOutput'u olaya göre okur)
    sonuc.append(("O1 hookEventName = payload'daki olay (PostToolUse / PostToolUseFailure)",
                  olay_ok, "; ".join(olay_detay) or "hepsi esit"))

    # C1 — bozuk girdi sözleşmesi (exit 0 fail-safe + stderr NOTU); B0b sınıfı
    rc, out, err = _kos(hook_yolu, "{bozuk-json")
    sonuc.append(("C1 bozuk JSON -> exit 0 + stderr NOTU (fail-safe korundu)",
                  rc == 0 and "GIRDI-PARSE-EDILEMEDI" in err and not out,
                  f"exit={rc} not={'VAR' if 'GIRDI-PARSE-EDILEMEDI' in err else 'YOK'}"))

    # C2 — hatırlatma known-errors.md'ye YÖNLENDİRİYOR mu (iki olayda da)
    _, out1, _ = _kos(hook_yolu, _v("P1"))
    _, out2, _ = _kos(hook_yolu, _v("F1"))
    sonuc.append(("C2 hatirlatma known-errors.md'ye yonlendiriyor (PostToolUse + Failure)",
                  "known-errors.md" in _context(out1)[1] and "known-errors.md" in _context(out2)[1],
                  f"uzunluk={len(out1)}/{len(out2)}"))

    # C3 — FM2'de CDS reçetesi eklenir (MCP hata dalı _is_cds_create_fail'e düz metni veriyor)
    _, out3, _ = _kos(hook_yolu, _v("FM2"))
    sonuc.append(("C3 FM2 ddls hatasinda CDS-YARATMA recetesi eklenir",
                  "CDS-YARATMA" in _context(out3)[1], f"uzunluk={len(out3)}"))

    # K1/K2 — kablolama (kod ≠ kablolama)
    ok, detay = _kablo_kontrol(sablon_yolu)
    sonuc.append(("K1 sablon: PostToolUseFailure -> post_tool_failure (Bash|PowerShell|sap-adt)", ok, detay))
    ok, detay = _post_kontrol(sablon_yolu)
    sonuc.append(("K2 sablon: PostToolUse -> post_tool_failure eslikcisi degismedi", ok, detay))

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")

    if not kip:
        return 0 if gecen == len(sonuc) else 1
    dusen = {ad.split()[0] for ad, ok, _ in sonuc if not ok}
    ilan = ILAN[kip]
    if dusen == ilan:
        print(f"  [MUTASYON YAKALANDI] dusen={sorted(dusen)} = ilan")
        return 1
    print(f"  [SAPMA] dusen={sorted(dusen)} ilan={sorted(ilan)} — "
          f"eksik={sorted(ilan - dusen)} fazla={sorted(dusen - ilan)}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
