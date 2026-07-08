#!/usr/bin/env python3
"""PostToolUse (matcher: mcp__sap-adt__*) — başarısız SAP işleminde PATİNAJ KESİCİ.

Bir SAP ADT MCP tool'u hata/guardrail/aktivasyon-fail döndürünce, "kör deneme-yanılma"
döngüsünü (ADR 0006 / T10) sistemsel kesmek için Claude'a hatırlatma enjekte eder:
playbook'a bak, kök sebep bul, transport hata numarasını ASLA kullanma, körlemesine retry yok.

Hata yoksa sessiz (exit 0, sıfır gürültü). Kısa + hızlı.
"""
import json
import sys

# Yapısal hata sinyalleri (client_log PROSE'u taranmaz — "Unlocked" gibi kelimeler
# false-positive verir). Sadece response'un yapısal alanlarına bakılır.
_FAIL_ERROR_VALUES = ("guardrail_violation", "activation_failed", "locked",
                      "validation_error", "auth_failed", "sap_error",
                      "connection_failed", "not_found")

REMINDER = (
    "⛔ SAP işlemi BAŞARISIZ. PATİNAJ/ESKALASYON MERDİVENİ (ADR 0006/T10 + agent-teams-operating-model §5):\n"
    "  1. Kör tekrar YOK. Aynı objede EN ÇOK 3 deneme (yalnız geçici CSRF/lock için).\n"
    "  2. 3'te çözülmezse → ZORUNLU ARAŞTIR: ilgili playbook/adt-*.md + playbook/lessons-learned.md + playbook/checklists/ + hata pattern'i; kök sebebi bul, bulguyla devam.\n"
    "  3. TOPLAM 5 denemede hâlâ olmazsa → DUR + lider/kullanıcıya gel (ham hata + denenenler + araştırma bulgusu).\n"
    "  4. Transport: hata mesajındaki numarayı ASLA kullanma; lock conflict → SM12/SE10 sonrası dene.\n"
    "  5. Guardrail (ADR 0005/0010/0011) ihlali ise: kuralı değiştirme — yaklaşımı değiştir veya kullanıcıya sor.\n"
    "  6. Çözüm bulunca playbook güncelle (T1: çalışan + denenen-başarısız)."
)

# CDS-YARATMA patinaj imzaları → fail anında GENERIC değil SPESİFİK reçete (2026-06-13,
# 2 kez tekrarlanan tuzak: push_source-önce/post_shell-ddls/create_cds_view). Sinyaller
# error/message/client_log içinde aranır (yapısal fail zaten tespit edildikten SONRA).
_CDS_FAIL_SIGNS = (
    "ddls/df",                              # adt_post_shell ddls desteklemez
    "does not contain a valid definition",  # inline-POST boş source → activate fail
    "is not locked",                        # push_source shell yokken → 423
    "invalidlockhandle",
)

CDS_RECIPE = (
    "\n\n📌 CDS-YARATMA patinajı algılandı → playbook/adt-cds.md ⚡ 'TEK CDS YARATMA' reçetesi:\n"
    "  (1) raw-REST inline POST shell (create_ddls_ve.py deseni, taze CSRF) — 201 ama source BOŞ olabilir.\n"
    "  (2) adt_push_source (object_type=ddls, transport) — obje ARTIK VAR → source+activate (boş-source'u düzeltir).\n"
    "  (3) adt_get include_source=true → source DOLU + version=active doğrula.\n"
    "  ⛔ YAPMA: push_source-ÖNCE (423) · post_shell ddls (DDLS/DF) · create_cds_view.py (CSRF flaky)."
)


def _is_cds_create_fail(data: dict, resp: dict) -> bool:
    """ddls tool'u VEYA bilinen CDS-create hata imzası mı?"""
    ti = data.get("tool_input") or {}
    if isinstance(ti, dict) and str(ti.get("object_type", "")).lower() == "ddls":
        return True
    blob = " ".join(str(resp.get(k, "")) for k in ("error", "message", "client_log")).lower()
    inner = resp.get("result")
    if isinstance(inner, dict):
        blob += " " + str(inner.get("error", "")).lower()
    return any(s in blob for s in _CDS_FAIL_SIGNS)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    resp = data.get("tool_response", data.get("tool_result", {}))
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except Exception:
            return 0  # düz metin yanıt — yapısal hata sinyali yok
    if not isinstance(resp, dict):
        return 0

    # Yalnızca YAPISAL alanlar (client_log prose'u DEĞİL — "Unlocked" false-positive fix).
    failed = False
    if resp.get("ok") is False:
        failed = True
    err = str(resp.get("error", "")).lower()
    if err and err in _FAIL_ERROR_VALUES:
        failed = True
    inner = resp.get("result")
    if isinstance(inner, dict) and inner.get("success") is False:
        failed = True
    # Reviewer BLOCKER (push_source/composite reviewer alanı)
    rev = resp.get("reviewer") or {}
    if isinstance(rev, dict) and str(rev.get("verdict", "")).upper() == "BLOCKER":
        failed = True

    if not failed:
        return 0

    context = REMINDER
    if _is_cds_create_fail(data, resp):
        context += CDS_RECIPE

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
