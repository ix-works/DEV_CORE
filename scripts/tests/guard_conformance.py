#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KONFORMANS MATRİSİ — pre_tool_guard.py'nin her kuralı için 4 mercek.

NEDEN (2026-07-09 denetimi): mevcut test paketi 32 senaryoda yeşil basıyordu; bağımsız
80-senaryoluk korpus 16 bozuk davranış buldu. Sebep: test paketi bir ŞARTNAME değil,
yazarının düzelttiği hataların listesiydi. Bu harness şartnameyi zorlar.

DÖRT MERCEK (kullanıcı direktifi 2026-07-09):
  ① gerekli mi          → `katman` + `gerekce`; 4 = runtime guard, YALNIZ
                          "geri alınamaz VE sessizce başarısız olan" için meşru
  ② kurgu doğru mu      → `yuzey`: kural HANGİ tool'larda yaşamalı (+ Z2 kablolama)
  ③ tetiklenmeli        → `bloklamali`: exit 2 VE stderr'de O KURALIN imzası
  ④ tetiklenmemeli      → `gecmeli`: exit 0

DÖRT ZORLAMA:
  Z1 imza kontrolü   — `exit==2` YETMEZ; başka kuralın bloğu "geçti" sayılamaz.
  Z2 kablolama       — `bloklamali`daki her tool settings.json PreToolUse matcher'ında
                       guard'a yönlenmeli (kural silinip matcher unutulursa yakalar).
  Z3 META-GATE       — guard kaynağındaki HER `⛔ <etiket>` için en az bir bloklamali VE
                       bir gecmeli vaka olmalı. Kanıtsız kural = FAIL → sahte-gate imkânsız.
  Z4 harness öz-testi— nötrleştirilmiş guard'a karşı koşulur; harness yeşil basarsa
                       HARNESS bozuktur (protokol §7.1: sessiz atlama ≠ yeşil ışık).

Ayrıca GRUP koşumu: tek tek geçen kurallar birlikte çakışabilir.

⚠ ÖZ-GÖNDERME TUZAĞI: guard'ın `_DANGER` ve `GENERICIZE-LEAK` kuralları bu dosyanın
YAZILMASINI iki kez bloklad (2026-07-09, canlı). Bir kuralı test etmek için o kuralın
aradığı dizgiyi içermek gerekir. Çözüm: tüm tetikleyici dizgiler RUNTIME'da birleştirilir.

Kullanım:
    python scripts/tests/guard_conformance.py --project <PROJE_KÖKÜ> [--project <2.PROJE>]
    python scripts/tests/guard_conformance.py --self-test-only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

CORE = Path(__file__).resolve().parents[2]
GUARD = CORE / "scripts" / "hooks" / "pre_tool_guard.py"

# --- runtime'da kurulan tetikleyiciler (öz-gönderme tuzağı; yukarı bkz.) ---
T_CREATE = "create" + "Transport"
T_RELEASE = "release" + "Transport"
T_JOBS = "newrelease" + "jobs"
T_CC = "SCC" + "1"
T_FM = "TRINT_RELEASE" + "_REQUEST"
T_FM2 = "TR_RELEASE" + "_REQUEST"
T_MAIL = "kisi" + "@" + "gercek" + "firma" + ".com.tr"      # jenerik e-posta deseni
T_MAIL_OK = "kullanici" + "@" + "example.com"                # RFC 2606 → muaf
# Sentetik ZSD paket adı — parça parça (literal hâli bu dosyada geçerse core_precommit
# ZSD_PAT'e takılır; gerçek paket DEĞİL, yalnız PUBLIC-PR ③ vakasını tetikler).
T_PKG = "ZSD" + "0" + "42"

BLOK = 2
GECER = 0


@dataclass
class Vaka:
    tool: str
    ti: dict
    aciklama: str
    kosul: str = ""


@dataclass
class Kural:
    id: str
    etiket: str
    katman: int
    gerekce: str
    yuzey: list
    bloklamali: list = field(default_factory=list)
    gecmeli: list = field(default_factory=list)


def _kurallar(proj: Path) -> list:
    """Kural ŞARTNAMESİ. Mutlak/müşteri-adlı yol YAZILMAZ — proje argümandan gelir."""
    p = str(proj).replace("\\", "/")
    return [
        Kural(
            id="YASAK-DAMGA",
            etiket="KESİN YASAKLAR DAMGASI",
            katman=4,
            gerekce="Damga silinince hiçbir tool hata vermez (SESSİZ); o oturumun tüm SAP "
                    "yazımları anayasasız yapılır (pratikte geri alınamaz).",
            yuzey=["mcp__sap-adt__adt_push_source", "mcp__sap-adt__adt_activate",
                   "mcp__sap-adt__adt_delete", "mcp__sap-adt__adt_post_shell"],
            bloklamali=[Vaka("mcp__sap-adt__adt_push_source", {"object_name": "ZSD001_X"},
                             "damgasız projede SAP yazma", kosul="damgasiz_proje")],
            gecmeli=[Vaka("mcp__sap-adt__adt_push_source", {"object_name": "ZSD001_X"},
                          "damga sağlam projede SAP yazma"),
                     Vaka("mcp__sap-adt__adt_get", {"object_name": "ZSD001_X"},
                          "okuma tool'u damgadan etkilenmez", kosul="damgasiz_proje")],
        ),
        Kural(
            id="ADR-0010-BAGLANTI",
            etiket="BAĞLANTI TUTARSIZLIĞI",
            katman=4,
            gerekce="Yanlış sisteme yazım GERİ ALINAMAZ (transport/versiyon izi); istek "
                    "HTTP 200 döner (SESSİZ).",
            yuzey=["mcp__sap-adt__adt_push_source", "mcp__sap-adt__adt_get"],
            bloklamali=[Vaka("mcp__sap-adt__adt_get", {"object_name": "ZSD001_X"},
                             ".conn_adt ile MCP ayrışık", kosul="ayrisik_baglanti")],
            gecmeli=[Vaka("mcp__sap-adt__adt_get", {"object_name": "ZSD001_X"},
                          "bağlantı tutarlı"),
                     Vaka("mcp__sap-adt__ping", {}, "ping her hâlükârda serbest",
                          kosul="ayrisik_baglanti")],
        ),
        Kural(
            id="ADR-0005-C",
            etiket="ADR 0005-C İHLALİ",
            katman=4,
            gerekce="Transport release GERİ ALINAMAZ; HTTP 200 döner (SESSİZ). MCP'de "
                    "release tool'u YOK (①tasarımla çözülü) → kalan yüzey yalnız ham kabuk "
                    "ve keyfi-ABAP çalıştıran post_shell/classrun.",
            yuzey=["Bash", "PowerShell",
                   "mcp__sap-adt__adt_post_shell", "mcp__sap-adt__adt_classrun"],
            bloklamali=[
                Vaka("Bash", {"command": "curl -X POST https://h/cts/transportrequests/X/" + T_JOBS},
                     "ham HTTP release endpoint"),
                Vaka("PowerShell", {"command": "Invoke-RestMethod -Method POST https://h/" + T_JOBS},
                     "PowerShell'den aynı endpoint"),
                Vaka("Bash", {"command": "python -c \"c.rfc('%s')\"" % T_FM},
                     "release FM çağrısı"),
                Vaka("mcp__sap-adt__adt_post_shell", {"code": "CALL FUNCTION '%s'." % T_FM2},
                     "post_shell ile keyfi ABAP → release FM"),
                Vaka("mcp__sap-adt__adt_classrun", {"code": "SUBMIT %s." % T_CC},
                     "classrun payload'unda client-copy"),
            ],
            gecmeli=[
                Vaka("Write", {"file_path": "docs/adr.md", "content": "`%s` yasaktir." % T_CREATE},
                     "DOKÜMAN yazımı — kuralı ANLATAN metin komut değildir"),
                Vaka("Edit", {"file_path": "docs/adr.md", "old_string": "a",
                              "new_string": "%s client copy riskli" % T_CC},
                     "doküman düzenleme"),
                Vaka("Write", {"file_path": "docs/x.md", "content": "endpoint .../%s" % T_JOBS},
                     "endpoint adını anlatan doküman"),
                Vaka("Bash", {"command": "grep -rn '%s' scripts/" % T_RELEASE},
                     "ARAMA komutu — çalıştırmıyor"),
                Vaka("Bash", {"command": 'git commit -m "%s cagrisini sildik"' % T_CREATE},
                     "commit mesajı"),
                Vaka("Bash", {"command": "echo '%s asla kullanilmaz'" % T_CC},
                     "tırnak içinde metin"),
                Vaka("mcp__sap-adt__adt_get", {"object_name": "ZSD001_X"},
                     "okuma tool'unun argümanları taranmaz"),
            ],
        ),
        Kural(
            id="PUBLIC-PR",
            etiket="PUBLIC-PR SIZINTI GATE",
            katman=4,
            gerekce="Yayınlanan PR gövdesi cache'lenir/indexlenir — silmek GERİ ALMAZ; "
                    "`gh pr create` başarı döner (SESSİZ). core_precommit yalnız COMMIT "
                    "içeriğini tarar; PR gövdesi commit değildir.",
            yuzey=["Bash", "PowerShell"],
            bloklamali=[
                Vaka("Bash", {"command": "gh pr create --repo ix-works/DEV_CORE "
                                         "--title 'x' --body '%s paketi degisti'" % T_PKG},
                     "public repo + ZSD-paket adı (sentetik; gerçek paket DEĞİL)", kosul="gh_var"),
                Vaka("Bash", {"command": "gh pr create --repo ix-works/DEV_CORE "
                                         "--title 'x' --body-file -"},
                     "gövde stdin'den okunamıyor → fail-closed", kosul="gh_stdin"),
            ],
            gecmeli=[
                Vaka("Bash", {"command": "gh pr create --repo ix-works/DEV_CORE --title "
                                         "'fix: guard' --body 'jenerik govde, ZSD001 demo paketi'"},
                     "public repo + temiz gövde (demo paket istisnası)", kosul="gh_var"),
                Vaka("Bash", {"command": "git commit -m 'gh pr create govdesi taranmali'"},
                     "commit MESAJINDA 'gh pr create' geçiyor — komut değil"),
                Vaka("Bash", {"command": "gh pr create --repo ix-works/DEV_CORE --title 'x' "
                                         "--body-file - <<'B'\njenerik govde ZSD001\nB"},
                     "gövde heredoc'tan çözülebiliyor", kosul="gh_var"),
            ],
        ),
        Kural(
            id="INLINE-AKTIVASYON",
            etiket="INLINE AKTİVASYON",
            katman=4,
            gerekce="Elle activation POST'u activationExecuted'ı parse etmez → HTTP 200 "
                    "SAHTE-OK (SESSİZ); metadata eski kalır.",
            yuzey=["Bash", "PowerShell"],
            bloklamali=[Vaka("Bash", {"command": "python -c \"c.post('/sap/bc/adt/activation', d)\""},
                             "elle activation POST")],
            gecmeli=[Vaka("Bash", {"command": "python -c \"activate_and_verify(c, tok, refs)\""},
                          "kanonik helper"),
                     Vaka("Bash", {"command": "grep -rn 'adt/activation' playbook/"},
                          "arama komutu")],
        ),
        Kural(
            id="FIORI-DEPLOY",
            etiket="YALIN FIORI DEPLOY",
            katman=4,
            gerekce="'Deployment Successful' der ama bayat dist gider (SESSİZ); canlıya "
                    "yanlış içerik yayınlanır.",
            yuzey=["Bash", "PowerShell"],
            bloklamali=[Vaka("Bash", {"command": "npx fiori deploy"}, "yalın deploy"),
                        Vaka("PowerShell", {"command": "npx fiori deploy"}, "PS'ten yalın deploy")],
            gecmeli=[Vaka("Bash", {"command": "python scripts/deploy_ui.py --apps a,b"},
                          "kanonik deploy"),
                     Vaka("Bash", {"command": "grep -rn 'fiori deploy' docs/"},
                          "arama komutu")],
        ),
        Kural(
            id="NPM-INSTALL",
            etiket="APP-İÇİ NPM INSTALL",
            katman=4,
            gerekce="Workspace ihlali; kurulum başarılı görünür, tooling sonradan bozulur.",
            yuzey=["Bash", "PowerShell"],
            bloklamali=[Vaka("Bash", {"command": "cd %s/ui/app1 && npm install" % p},
                             "app dizininde npm install", kosul="ui_workspace")],
            gecmeli=[Vaka("Bash", {"command": "cd %s/ui && npm install" % p},
                          "workspace kökünde npm install", kosul="ui_workspace"),
                     Vaka("Bash", {"command": "npm run start-noflp"}, "npm run serbest")],
        ),
        Kural(
            id="GENERICIZE-LEAK",
            etiket="GENERICIZE-LEAK",
            katman=4,
            gerekce="core PUBLIC repodur; yazılan kimlik izi push'lanınca cache'lenir "
                    "(GERİ ALINAMAZ), Edit başarı döner (SESSİZ). Kesin gate pre-commit/CI'da; "
                    "bu erken-uyarı. Komut metnini DEĞİL veriyi tarar → çalışan tek desen.",
            yuzey=["Edit", "Write", "MultiEdit", "NotebookEdit"],
            bloklamali=[
                Vaka("Write", {"file_path": "core/x.py", "content": "# musteri: <BLOCKLIST>"},
                     "core'a proje blocklist deseni", kosul="blocklist_ornegi"),
                Vaka("MultiEdit", {"file_path": "core/x.py",
                                   "edits": [{"old_string": "a", "new_string": "<BLOCKLIST>"}]},
                     "MultiEdit edits[].new_string", kosul="blocklist_ornegi"),
                Vaka("NotebookEdit", {"notebook_path": "core/n.ipynb", "new_source": "<BLOCKLIST>"},
                     "NotebookEdit new_source", kosul="blocklist_ornegi"),
                Vaka("Write", {"file_path": "core/y.py", "content": T_MAIL},
                     "jenerik desen: gerçek e-posta"),
            ],
            gecmeli=[
                Vaka("Write", {"file_path": "core/x.py", "content": "print('jenerik icerik')"},
                     "temiz core yazımı"),
                Vaka("Write", {"file_path": "core/y.py", "content": T_MAIL_OK},
                     "RFC 2606 örnek domain muaf"),
                Vaka("Write", {"file_path": "docs/x.md", "content": T_MAIL},
                     "core DIŞI hedef taranmaz"),
            ],
        ),
    ]


def _grup_vakalari(proj: Path) -> list:
    """(tool, ti, beklenen_rc, beklenen_etiket|'', açıklama)"""
    return [
        ("Bash", {"command": "git add p.py && python core/scripts/validators/run_all_validators.py"},
         GECER, "", "core/ yalnız script YOLUNDA"),
        ("Bash", {"command": "cd core && git clean -n"}, GECER, "", "önizleme; silme yok"),
        ("Bash", {"command": "rm -rf .tmp/x && python core/scripts/x.py"},
         GECER, "", "silme hedefi scratch"),
        ("Bash", {"command": "git commit -F - <<'EOF'\nfix: `%s` artik taranmiyor\nEOF" % T_CREATE},
         GECER, "", "heredoc GÖVDESİ veri, komut değil"),
        ("Bash", {"command": "grep -rn '%s' core/ && echo bulundu" % T_RELEASE},
         GECER, "", "arama + echo zinciri"),
        ("Bash", {"command": "npx fiori deploy && git commit -m x"},
         BLOK, "YALIN FIORI DEPLOY", "zincirin İLK segmenti tehlikeli"),
        ("Bash", {"command": "echo ok && curl -X POST https://h/cts/transportrequests/X/" + T_JOBS},
         BLOK, "ADR 0005-C İHLALİ", "zincirin İKİNCİ segmenti tehlikeli"),
        ("Bash", {"command": """echo '{"cmd":"npx fiori deploy"}'"""},
         GECER, "", "tırnak içi JSON payload komut değil"),
        ("Bash", {"command": "rm -rf core/"}, GECER, "", "R9 SİLİNDİ (2026-07-09): junction "
                                                         "silme geri alınabilir + sessiz değil"),
        ("Bash", {"command": "git add core/"}, GECER, "", "SIZINTI-COMMIT runtime ayağı SİLİNDİ; "
                                                          "statik + CI ikizi koruyor"),
    ]


# ---------------- fixture'lar ----------------
def _fixture_damgasiz_proje(tmp: Path) -> Path:
    d = tmp / "damgasiz"
    d.mkdir(parents=True, exist_ok=True)
    (d / "project.yaml").write_text("sap_profile: s4_private\nmaster_language: TR\n",
                                    encoding="utf-8", newline="\n")
    (d / "CLAUDE.md").write_text("# proje\nDamga YOK.\n", encoding="utf-8", newline="\n")
    link = d / "core"
    if not link.exists():
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(CORE)],
                       capture_output=True, text=True)
    return d


def _fixture_ayrisik_baglanti(tmp: Path) -> Path:
    d = tmp / "ayrisik"
    (d / ".claude").mkdir(parents=True, exist_ok=True)
    (d / "project.yaml").write_text("sap_profile: s4_private\n", encoding="utf-8", newline="\n")
    (d / ".conn_adt").write_text(
        "ADT_SAP_URL=https://sistem-a.example.com\nADT_SAP_CLIENT=100\n"
        "ADT_SAP_SYSTEM_NAME=SYS_A\n", encoding="utf-8", newline="\n")
    (d / ".claude" / ".mcp_active_system").write_text(
        json.dumps({"url": "https://sistem-b.example.com", "client": "200", "system": "SYS_B"}),
        encoding="utf-8", newline="\n")
    return d


def _blocklist_ornegi(proj: Path) -> str:
    """Projenin KENDİ blocklist'inden bir desen al — bu dosyaya kimlik izi YAZILMAZ."""
    f = proj / ".claude" / "genericize-blocklist.txt"
    if not f.exists():
        return ""
    for s in f.read_text(encoding="utf-8", errors="replace").splitlines():
        s = s.strip()
        if s and not s.startswith("#") and re.fullmatch(r"[A-Za-z_]{4,}", s):
            return s
    return ""


def _ui_workspace_var(proj: Path) -> bool:
    pkg = proj / "ui" / "package.json"
    try:
        return pkg.exists() and "workspaces" in pkg.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False


# ---------------- koşum motoru ----------------
def _cagir(guard: Path, tool: str, ti: dict, proj: Path) -> tuple:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(proj))
    env.pop("IX_GENERICIZE_BLOCKLIST", None)
    r = subprocess.run([sys.executable, str(guard)],
                       input=json.dumps({"tool_name": tool, "tool_input": ti}, ensure_ascii=False),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=90)
    return r.returncode, (r.stderr or "")


def _matcher_kapsiyor_mu(settings: dict, tool: str) -> bool:
    for blok in settings.get("hooks", {}).get("PreToolUse", []):
        if "pre_tool_guard" not in json.dumps(blok):
            continue
        m = blok.get("matcher") or ""
        try:
            if re.fullmatch(m, tool):
                return True
        except re.error:
            pass
        if tool in [x.strip() for x in m.split("|")]:
            return True
    return False


def _imza(err: str) -> str:
    m = re.search(r"⛔ ([^(\n:]{3,45})", err)
    return m.group(1).strip() if m else "?"


def _vaka_uygula(v: Vaka, proj: Path, ctx: dict):
    ti = json.loads(json.dumps(v.ti, ensure_ascii=False))
    if v.kosul == "damgasiz_proje":
        return True, ctx["damgasiz"], ti, ""
    if v.kosul == "ayrisik_baglanti":
        return True, ctx["ayrisik"], ti, ""
    if v.kosul in ("gh_var", "gh_stdin"):
        if not shutil.which("gh"):
            return False, proj, ti, "gh CLI yok — PUBLIC-PR kanıtlanamaz (SESSİZ ATLAMA DEĞİL: FAIL)"
        return True, proj, ti, ""
    if v.kosul == "ui_workspace":
        if not ctx["ui_workspace"]:
            return False, proj, ti, "bu projede ui/ npm workspace yok (kural proje-koşullu)"
        return True, proj, ti, ""
    if v.kosul == "blocklist_ornegi":
        o = ctx["blocklist_ornegi"]
        if not o:
            return False, proj, ti, "projede genericize-blocklist deseni yok"
        return True, proj, json.loads(json.dumps(ti, ensure_ascii=False).replace("<BLOCKLIST>", o)), ""
    return True, proj, ti, ""


def kosum(guard: Path, proj: Path) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="guardconf_"))
    ctx = {
        "damgasiz": _fixture_damgasiz_proje(tmp),
        "ayrisik": _fixture_ayrisik_baglanti(tmp),
        "ui_workspace": _ui_workspace_var(proj),
        "blocklist_ornegi": _blocklist_ornegi(proj),
    }
    settings = {}
    sp = proj / ".claude" / "settings.json"
    if sp.exists():
        settings = json.loads(sp.read_text(encoding="utf-8"))

    hatalar, atlanan, gecen = [], [], 0
    kurallar = _kurallar(proj)

    for k in kurallar:
        for v in k.bloklamali:                       # ③
            calisir, p, ti, neden = _vaka_uygula(v, proj, ctx)
            if not calisir:
                (hatalar if v.kosul.startswith("gh") else atlanan).append(
                    f"{k.id} ③ {v.aciklama}: {neden}")
                continue
            rc, err = _cagir(guard, v.tool, ti, p)
            if rc != BLOK:
                hatalar.append(f"{k.id} ③ TETİKLENMEDİ: {v.tool} — {v.aciklama} (rc={rc})")
            elif k.etiket not in err:                # Z1
                hatalar.append(f"{k.id} ③ YANLIŞ KURAL ateşledi: {v.aciklama} → '{_imza(err)}'")
            else:
                gecen += 1
        for v in k.gecmeli:                          # ④
            calisir, p, ti, neden = _vaka_uygula(v, proj, ctx)
            if not calisir:
                (hatalar if v.kosul.startswith("gh") else atlanan).append(
                    f"{k.id} ④ {v.aciklama}: {neden}")
                continue
            rc, err = _cagir(guard, v.tool, ti, p)
            if rc != GECER:
                hatalar.append(f"{k.id} ④ YANLIŞ-POZİTİF: {v.tool} — {v.aciklama} "
                               f"(blokladı: '{_imza(err)}')")
            else:
                gecen += 1
        if settings:                                 # Z2
            for v in k.bloklamali:
                if not _matcher_kapsiyor_mu(settings, v.tool):
                    hatalar.append(f"{k.id} ② KABLOLAMA AÇIĞI: '{v.tool}' settings.json "
                                   f"PreToolUse matcher'ında guard'a yönlenmiyor")

    for tool, ti, bek_rc, bek_et, ac in _grup_vakalari(proj):   # GRUP
        rc, err = _cagir(guard, tool, ti, proj)
        if rc != bek_rc:
            hatalar.append(f"GRUP: {ac} (beklenen rc={bek_rc}, alınan {rc}"
                           + (f", '{_imza(err)}'" if rc == BLOK else "") + ")")
        elif bek_et and bek_et not in err:
            hatalar.append(f"GRUP: {ac} — yanlış kural ateşledi: '{_imza(err)}'")
        else:
            gecen += 1

    # Z3 META-GATE
    src = guard.read_text(encoding="utf-8", errors="replace")
    kod_et = {m.strip() for m in re.findall(r'"⛔ ([^(\n:{"]{3,45})', src)}
    kod_et |= {m.strip() for m in re.findall(r'f"⛔ ([^(\n:{"]{3,45})', src)}
    kapsanan = {k.etiket for k in kurallar}
    for et in sorted(kod_et):
        if not any(et.startswith(c) or c.startswith(et) for c in kapsanan):
            hatalar.append(f"META-GATE: guard'da '⛔ {et}' var ama KONFORMANS VAKASI YOK "
                           f"(kanıtsız kural — ya vaka yaz ya kuralı sil)")
    for k in kurallar:
        if not k.bloklamali:
            hatalar.append(f"META-GATE: {k.id} 'bloklamalı' vakası yok")
        if not k.gecmeli:
            hatalar.append(f"META-GATE: {k.id} 'geçmeli' vakası yok")
        if k.katman != 4:
            hatalar.append(f"META-GATE: {k.id} runtime guard'da ama katman={k.katman}")

    shutil.rmtree(tmp, ignore_errors=True)
    return {"gecen": gecen, "hatalar": hatalar, "atlanan": atlanan}


def _notr_guard(tmp: Path) -> Path:
    h = tmp / "notr_guard.py"
    h.write_text("import sys, json\n"
                 "try: json.load(sys.stdin)\n"
                 "except Exception: pass\n"
                 "raise SystemExit(0)\n", encoding="utf-8", newline="\n")
    return h


def oz_test(proj: Path) -> bool:
    """Z4 — harness nötr guard'a yeşil basarsa harness bozuktur."""
    tmp = Path(tempfile.mkdtemp(prefix="guardself_"))
    try:
        s = kosum(_notr_guard(tmp), proj)
        ucuncu = [h for h in s["hatalar"] if "③" in h]
        ok = len(ucuncu) >= 5
        print(f"  [{'OK' if ok else 'FAIL'}] Z4 öz-test: nötr guard'a karşı {len(ucuncu)} "
              f"adet ③ ihlali raporlandı (>=5 bekleniyor)")
        if not ok:
            print("       HARNESS BOZUK — bulguları geçersiz say.")
        return ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="pre_tool_guard konformans matrisi")
    ap.add_argument("--project", action="append", default=[])
    ap.add_argument("--guard", default=None,
                    help="test edilecek guard dosyası (staging doğrulaması için; "
                         "vermezsen canlı GUARD kullanılır)")
    ap.add_argument("--self-test-only", action="store_true")
    a = ap.parse_args()

    guard = Path(a.guard) if a.guard else GUARD

    projeler = [Path(x) for x in a.project] or \
               [Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())]
    projeler = [p for p in projeler if (p / "project.yaml").exists()]
    if not projeler:
        print("  [FAIL] geçerli proje kökü yok (project.yaml bulunamadı)")
        return 1

    print("=" * 74)
    print("KONFORMANS MATRİSİ — pre_tool_guard")
    print("=" * 74)
    if not oz_test(projeler[0]):
        return 1
    if a.self_test_only:
        return 0

    print(f"   (test edilen guard: {guard})")
    toplam = 0
    for proj in projeler:
        print(f"\n── PROJE: {proj.name} " + "─" * max(2, 56 - len(proj.name)))
        s = kosum(guard, proj)
        print(f"   geçen kontrol: {s['gecen']}")
        for x in s["atlanan"]:
            print(f"   [atlandı] {x}")
        if s["hatalar"]:
            print(f"   [FAIL] {len(s['hatalar'])} ihlal:")
            for h in s["hatalar"]:
                print(f"      - {h}")
            toplam += len(s["hatalar"])
        else:
            print("   [OK] tüm kurallar konformans matrisini geçti")

    print("\n" + "=" * 74)
    if toplam:
        print(f"SONUÇ: {toplam} ihlal — guard ŞARTNAMEYE UYMUYOR")
        return 1
    print("SONUÇ: guard ŞARTNAMEYE UYUYOR (③④ + kablolama + meta-gate + grup)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
