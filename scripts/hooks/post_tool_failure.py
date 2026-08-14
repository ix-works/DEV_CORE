#!/usr/bin/env python3
"""PostToolUse (matcher: mcp__sap-adt__* **+ Bash**) — başarısız SAP işleminde PATİNAJ KESİCİ.

⚠ 2026-08-14 — YÜZEY GENİŞLETİLDİ (ölçülmüş boşluk): hook yalnız `mcp__sap-adt__.*`
matcher'ına bağlıydı. Bir SAP-yazma turunda **12 push denemesinin tamamı `Bash` üzerinden**
(`python push_object.py …`) koştu ⇒ hook **hiç ateşlemedi**, tek hatırlatma üretmedi —
oysa aradığı imzalar (`invalidlockhandle`, `is not locked`) listesinde ZATEN vardı ve
cevap `playbook/known-errors.md` §12.7c'de yazılıydı. "Ağ vardı, delik tam düşülen yerdeydi."
⇒ Bash dalı eklendi. **İKİ KAPILI (AND)**: komut SAP-yazma aracına benzemeli VE çıktıda
SAP hata imzası olmalı. Sıradan Bash çağrısında **tam sessiz** (gürültü = hook'un ölümü).

Bir SAP ADT MCP tool'u hata/guardrail/aktivasyon-fail döndürünce, "kör deneme-yanılma"
döngüsünü (ADR 0006 / T10) sistemsel kesmek için Claude'a hatırlatma enjekte eder:
playbook'a bak, kök sebep bul, transport hata numarasını ASLA kullanma, körlemesine retry yok.

Hata yoksa sessiz (exit 0, sıfır gürültü). Kısa + hızlı.
"""
import json
import sys

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Yapısal hata sinyalleri (client_log PROSE'u taranmaz — "Unlocked" gibi kelimeler
# false-positive verir). Sadece response'un yapısal alanlarına bakılır.
_FAIL_ERROR_VALUES = ("guardrail_violation", "activation_failed", "locked",
                      "validation_error", "auth_failed", "sap_error",
                      "connection_failed", "not_found")

REMINDER = (
    "⛔ SAP işlemi BAŞARISIZ. PATİNAJ/ESKALASYON MERDİVENİ (ADR 0006/T10 + agent-teams-operating-model §5):\n"
    "  1. Kör tekrar YOK. Aynı objede EN ÇOK 3 deneme (yalnız geçici CSRF/lock için).\n"
    "  2. 3'te çözülmezse → ZORUNLU ARAŞTIR — **ÖNCE `playbook/known-errors.md`'de SEMPTOMU ARA**\n"
    "     (`Grep path=core/playbook pattern='<hata kodu veya mesaj parçası>'`; ör. 423 · 'is not locked' ·\n"
    "     'Session Timed Out'). O dosya hata-kodu bazlı düzenlidir ve ÇALIŞAN YÖNTEMİ de taşır.\n"
    "     Sonra: playbook/adt-*.md + playbook/lessons-learned.md + playbook/checklists/. Kök sebebi bul, bulguyla devam.\n"
    "     📌 Vaka 2026-08-14: cevap known-errors §12.7c'de 3 gün önce yazılıydı; aranmadığı için ~12 deneme + 2 saat kayboldu.\n"
    "  3. TOPLAM 5 denemede hâlâ olmazsa → DUR + lider/kullanıcıya gel (ham hata + denenenler + araştırma bulgusu).\n"
    "  4. Transport: hata mesajındaki numarayı ASLA kullanma; lock conflict → SM12/SE10 sonrası dene.\n"
    "  5. Guardrail (ADR 0005/0010/0011) ihlali ise: kuralı değiştirme — yaklaşımı değiştir veya kullanıcıya sor.\n"
    "  5b. Hata İNFRA'nın kendisinde mi (validator/hook/script bug'ı ya da yanlış-pozitif)? Görev-içi fix'e ATLAMA: DONDUR→SINIFLA→(EXPRESS|KUYRUK) — core/playbook/howto-infra-fix-proseduru.md\n"
    "  6. Çözüm bulunca playbook güncelle (T1: çalışan + denenen-başarısız).\n"
    "  7. AYNI çağrıyı AYNI girdiyle tekrarlamadan önce sor: ilk sonucu neden kullanamıyorum?"
    " Büyük çıktıyı scratch dosyasına yaz, oradan oku (P6 — ölçüm: çağrıların ~%24'ü birebir mükerrerdi)."
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


# ── Bash dalı (2026-08-14) — İKİ KAPI: komut SAP-yazma aracı MI + çıktı hata imzası taşıyor MU ──
# Kapı-1: komut imzası. Salt-okuma araçları (sap_sync_pull/adt_get) BİLEREK yok — onların
#   başarısızlığı patinaj üretmiyor; liste yalnız YAZMA/aktivasyon yollarını kapsar.
_BASH_SAP_KOMUT_IMZALARI = (
    "push_object.py", "push_bo_atomic.py", "sap_client.py", "sap_adt_lib.py",
    "activate_object.py", "create_access_control.py", "deploy_ui.py",
    "populate_", "create_rap_service.py", "tight_push",
)
# Kapı-2: çıktı imzası. HEPSİ SPESİFİK — çıplak "423"/"error" gibi jenerik token YOK
#   (jenerik imza = her Bash çağrısında gürültü = hook'un ölümü).
_BASH_FAIL_IMZALARI = (
    "invalid lock handle", "invalidlockhandle", "is not locked",
    "session timed out", "failed to set source", "exceptionresource",
    "[error] [4", "[error] [5", "activation failed", "aktivasyon basarisiz",
)

BASH_EKI = (
    "\n\n📌 Bu hata **Bash** üzerinden koşan bir SAP aracından geldi (MCP değil). Aynı komutu\n"
    "  AYNI parametrelerle tekrar koşmadan önce known-errors.md'de semptomu ARA — bu hook tam\n"
    "  bu tekrarı kesmek için var. Araç retry döngüsü asıl hatayı MASKELEYEBİLİR: ilk yanıtın\n"
    "  ham gövdesine bak (sonraki denemelerin kodu türev olabilir)."
)


def _bash_dali(data: dict) -> int:
    """Bash yüzeyi: iki kapı da geçilmezse TAM SESSİZ (exit 0, sıfır çıktı)."""
    ti = data.get("tool_input") or {}
    komut = str(ti.get("command", "")).lower() if isinstance(ti, dict) else ""
    if not any(s in komut for s in _BASH_SAP_KOMUT_IMZALARI):
        return 0  # SAP-yazma aracı değil → hiç bakma

    resp = data.get("tool_response", data.get("tool_result", ""))
    if isinstance(resp, dict):
        cikti = " ".join(str(resp.get(k, "")) for k in
                         ("stdout", "stderr", "output", "error", "content"))
    else:
        cikti = str(resp)
    if not any(s in cikti.lower() for s in _BASH_FAIL_IMZALARI):
        return 0  # başarılı ya da tanınmayan çıktı → SESSİZ (fail-safe: konuşmamak)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": REMINDER + BASH_EKI,
        }
    }))
    return 0


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


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Gerekce + sinif kaydi: scripts/hooks/README.md S4. ASCII-only + yazma hatasi
    fail-safe'i BOZMAMALI (except: pass).
    """
    try:
        sys.stderr.write(
            "[post_tool_failure] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> fail-safe "
            "SERBEST (exit 0); KARAR DEGILDIR (girdi hic okunamadi). "
            "Negatif-test: governance/infra-test-recipes.md B0b\n")
    except Exception:
        pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
        return 0

    # Bash yüzeyi ayrı dal: yanıt şekli MCP'den farklı (stdout/stderr, yapısal `ok` YOK)
    if str(data.get("tool_name", "")) == "Bash":
        return _bash_dali(data)

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
