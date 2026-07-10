#!/usr/bin/env python3
"""PreToolUse (SAP MCP tool'ları) — ITG DETERMİNİSTİK backstop.

NEDEN (2026-07-10 intake_triage redizaynı): ITG keşfi eskiden yalnız `intake_triage.py`
prompt-KEYWORD regex'iyle yapılıyordu → kırılgan: keyword-seti dışı ifade edilen gerçek
geliştirme talepleri ("bu ekrana kolon koyalım", "rapora müşteri adını getir") ITG'yi HİÇ
tetiklemiyordu (5/5 kaçış canlı ölçüldü). skill_injector'ın "CDS view yarat kaçtı" ikizi.

REDİZAYN — üç katman:
  (1) native `intake-triage` skill → SEMANTİK keşif (parafrazı da yakalar; model karar verir).
  (2) `intake_triage.py` (UserPromptSubmit regex) → ERKEN hatırlatma (kaçarsa tek-savunma DEĞİL).
  (3) BU HOOK → DETERMİNİSTİK net: SAP işi FİİLEN başladığında (ilk `mcp__sap-adt__*` tool'u —
      araştırma read'leri dahil, çünkü ITG'nin 3-eksen araştırması onları kullanır) session'da
      ITG-marker YOKSA protokolü enjekte eder. Prompt nasıl ifade edildi önemsizleşir.

Koordinasyon: hem (2) hem bu hook `.claude/.itg_shown.json` marker'ını okur/yazar → ITG session
başına BİR kez gösterilir. (2) prompt-anında set ederse bu hook sessiz; (2) kaçarsa bu hook
SAP-tool anında yakalar. Non-blocking (additionalContext); gerçek S2 gate `check_itg_signoff`.
"""
import json
import os
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


def _session_id(proj: Path) -> str:
    try:
        d = json.loads((proj / ".claude" / ".current_session").read_text(encoding="utf-8"))
        return str(d.get("session_id") or "")
    except Exception:
        return ""


def itg_shown_bir_kez(proj: Path, sid: str) -> bool:
    """ITG bu session'da GÖSTERİLDİ mi? Gösterilmediyse marker'ı yaz + False dön (=şimdi göster).
    intake_triage.py ile PAYLAŞILAN marker (.claude/.itg_shown.json)."""
    f = proj / ".claude" / ".itg_shown.json"
    try:
        st = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        st = {}
    if st.get("session") == sid:
        return True                                    # zaten gösterildi (regex hook ya da bu)
    try:
        f.write_text(json.dumps({"session": sid}), encoding="utf-8", newline="\n")
    except Exception:
        pass
    return False


_ITG_METIN = (
    "[INTAKE TRIAGE — SAP işi başladı, ITG henüz uygulanmadı (deterministik backstop)] "
    "Bu SAP çalışması bir geliştirme/revizyon talebiyse ITG protokolünü İZLE "
    "(OKU: core/playbook/intake-triage.md; atlanamaz): (1) KAPSAM sınıfla S0/S1/S2 + gerekçe. "
    "(2) Modül + iş-tipi; modül kural-paketi varsa OKU. (3) İsterlerden domain-konusu çıkar. "
    "(4) 3-EKSEN: domain + CANLI sistem/kod (adt_where_used/package_contents — reuse+blast-radius) "
    "+ prior-art (memory/playbook). Z-obje hatırlanıyorsa CANLI DOĞRULA. (5) KANITLI değerlendir "
    "(TAHMİN YASAK). (6) Kapsam-orantılı: S0 hafif · S1 hedefli soru · S2 artefakt+DoR+MUTABAKAT. "
    "Yalnız nokta-analiz/okuma ise hafif geç."
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name", "") or ""

    # SAP MCP tool'u mu (ping hariç — bağlantı testi iş değildir)?
    if not tool.startswith("mcp__sap-adt__") or tool == "mcp__sap-adt__ping":
        return 0

    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    sid = _session_id(proj)
    if itg_shown_bir_kez(proj, sid):
        return 0                                       # ITG bu session'da zaten gösterildi

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": _ITG_METIN,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
