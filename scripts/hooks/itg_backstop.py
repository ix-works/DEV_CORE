#!/usr/bin/env python3
# ENFORCES: C-ITG-01  (ADR 0019 coverage binding)
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
import datetime
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
    """Oturum kimliği; ⛔ ASLA BOŞ DÖNMEZ — çözülemezse GÜN DAMGASINA düşer (Q253).

    KUSUR (2026-09-04 kaydı): boş dize dönüyordu ve o boş dize `.itg_shown.json`e
    dedup ANAHTARI olarak yazılıyordu ⇒ sonraki her çözülemeyen oturumda
    `"" == ""` ⇒ "zaten gösterildi" ⇒ ITG kapısı SESSİZCE ve KALICI OLARAK ölüyordu.
    ADR 0022 ITG'yi "atlanamaz" ilan ederken kapı susuyordu.

    ⛔ NEDEN FAIL-CLOSED (rc≠0 / bloklama) DEĞİL — kaydın önerisi ÖLÇÜLDÜ ve ELENDİ:
    bu bir PreToolUse hook'udur; rc≠0 `mcp__sap-adt__*` çağrısını BLOKLAR. Kimliğin
    çözülemediği hâl istisna değil DEGRADE bir normaldir (`session_start`
    `_write_session_marker` `if not sid: return` ile marker'ı hiç yazmaz — parse-fail
    dalında bu HER oturumda olur; taze klonda ilk SessionStart'tan önce de dosya yoktur).
    Fail-closed, tam da degrade oturumda TÜM SAP işini brick'lerdi: hatırlatıcı bir
    kapının bedeli, hatırlattığı işten büyük olamaz.

    ⭐ EVİN KENDİ EMSALİ (iki bağımsız yer, ikisi de "boş DEĞİL, dejenere ANAHTAR"):
      · `post_validate.py:306-311` — aynı sınıf, aynı çözüm, gerekçesi kod içinde
        yazılı: "session_id yoksa sabit marker diske KALICI yazılır ve nudge bir daha
        HİÇ ateşlemez (sessizce ölen hatırlatıcı). Gün damgası en kötü durumda günde
        bir kez konuşmayı garanti eder."
      · `sap_sync_pull.py:43-50` — çözülemeyen kimlik `"default"`e düşer, boşa değil.
    SABİT bir anahtar (`"nosession"`) burada YETMEZ: dedup anahtarı sabitse susma yine
    KALICI olur. Gün damgası dejenerasyonu SINIRLAR: en kötü hâl "günde bir kez".
    """
    try:
        d = json.loads((proj / ".claude" / ".current_session").read_text(encoding="utf-8"))
        sid = str(d.get("session_id") or "")
    except Exception:
        sid = ""
    return sid or ("gun-" + datetime.date.today().isoformat())


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


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Gerekce + sinif kaydi: scripts/hooks/README.md S4. ASCII-only + yazma hatasi
    fail-safe'i BOZMAMALI (except: pass).
    """
    try:
        sys.stderr.write(
            "[itg_backstop] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> fail-safe "
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
