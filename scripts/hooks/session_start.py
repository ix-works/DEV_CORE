#!/usr/bin/env python3
"""SessionStart hook — ADR 0005 yasaklarini + 4-adim session protokolunu her
oturum/resume/compact basinda context'e enjekte eder.

Amac: CLAUDE.md zaten yuklenir; ancak context compaction sonrasi yasak ozeti
silinebilir. Bu hook startup + resume + compact'ta tekrar enjekte ederek
"Ekran Teyidi" protokolunun ve ADR 0005'in oturum boyunca diri kalmasini garanti eder.
Kisa tutulur (token tasarrufu); detay CLAUDE.md'de.
"""
import json
import sys
from pathlib import Path


def _write_session_marker(data: dict) -> None:
    """Geçerli seans kimliğini .claude/.current_session'a yaz (pull-before-edit, ADR 0016
    revize). sap_sync_pull.py bunu --session default'u olarak okur → proaktif pull doğru
    seansa damgalanır, PreToolUse hook'unun gördüğü session_id ile eşleşir. Fail-safe."""
    try:
        sid = data.get("session_id")
        if not sid:
            return
        root = Path(__file__).resolve().parents[2]
        marker = root / ".claude" / ".current_session"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"session_id": sid}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass  # marker yazımı asla session-start'ı bozmaz

CONTEXT = (
    "[session-loader hook — <PROJECT_NAME>]\n"
    "ZORUNLU: Yeni oturumun ILK yaniti CLAUDE.md §2 'Ekran Teyidi' formatiyla baslar.\n"
    "ADR 0005 KESIN YASAKLAR (bypass YOK):\n"
    "  A) Z/Y ile baslamayan standart SAP objesine dokunma (yarat/degistir/sil) yasak.\n"
    "  B) Standart tablo verisine direkt INSERT/UPDATE/DELETE/MODIFY yasak "
    "(BAPI->RFC->BDC->manuel sirasi).\n"
    "  C) Transport/package yaratma ve TR release etme yasak.\n"
    "  D) Z obje = TR (sap-language=TR) login + 4 alan label TAM TR.\n"
    "SAP yazma oncesi run_review.py (ADR 0006). Validator FAIL -> once duzelt (§6 STOP).\n"
    "\n"
    "CALISMA MODELI (ADR 0018 = LAZY/on-demand; eski model-B STANDING roster IPTAL):\n"
    "  Oturum basinda roster SPAWN ETME. Ihtiyac aninda, ise-birimine scoped spawn et + bitince kapat.\n"
    "  Roller (.claude/agents/): adt-gateway (TEK SAP yazici; standing/ilk-yazimda) ; frontend-expert (tum FE) ;\n"
    "     backend-expert (tum ABAP/RAP) ; bug-expert (adversarial kod-inceleme, read-only).\n"
    "  - LIFECYCLE (ADR0018 amendment 2026-06-18, 'dissallastirilamaz-state testi'): bug-expert HER ZAMAN LAZY+taze\n"
    "     (onceki-bug'a benzetme YASAK). gateway STANDING (serilestirme + ucus-halindeki-islem; baglanti/lock MCP-server'da,\n"
    "     ajanda DEGIL). backend/frontend = LAZY varsayilan; SADECE yuksek-coupling feature/app-build'de bounded-standing\n"
    "     (feature bitince ZORUNLU yik). GUARDRAIL: ayni anda max 1 feature-expert standing + gateway; echo-reset tetigi\n"
    "     (ajan bayat-baglam gosterirse kill+taze re-spawn); supheli ise LAZY. (bounded-standing != model-B roster.)\n"
    "  - BUG GATE (ADR 0018): Expert substantive build bitince lider'e DONMEDEN once bug-expert'e gonderir\n"
    "     (diff+niyet+blast-radius) -> verdict PASS/WARNING/BLOCKER (ADR0006). Checklist-ihlali (HATA/EKSIK) = ZORUNLU FIX.\n"
    "     Bulgu tipleri: HATA(bug)/EKSIK(must-do karsilanmamis)/ONERI(baglayici degil). Sonuc lider'e tek-satir yansir.\n"
    "  - AUDIT: alt-ajan logu SABIT adres -> 'python scripts/agent_log.py --agent <isim>' (arama YOK).\n"
    "  - Kullanici 'solo' derse spawn etme (lider dogrudan calisir; gateway hala tek SAP-yazici).\n"
    "  Detay: ADR 0018 + governance/agent-teams-operating-model.md"
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    _write_session_marker(data if isinstance(data, dict) else {})
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": CONTEXT,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
