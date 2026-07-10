#!/usr/bin/env python3
"""UserPromptSubmit — tarayıcı/UI-doğrulama + yapısal-kod-arama akış nudge'ları.

⚠ 2026-07-10 SKILL-INJECTION REDİZAYNI: SAP-işi tespiti (`_STRONG`/`_TRANSPORT`) ve
worktype→checklist (`_WORKTYPES`) BU HOOK'TAN KALDIRILDI. Neden: prompt-KEYWORD regex'i
kırılgandı ("CDS view yarat" kaçtı, İngilizce "public transport" yanlış-tetikledi) ve
işlev ZATEN redundant'tı:
  (A) KEŞİF ("bu SAP işi mi + hangi skill") → native `sap-abap-dev` skill `description`'ı
      (943 char, "Use it whenever the work touches SAP/ABAP/CDS/RAP..."). Ekosistemin tamamı
      keşfi description-semantik ile yapıyor; keyword-hook en kırılgan azınlık desendi.
  (B) worktype→checklist → hem skill içeriğinde (SKILL.md "TETİKLEMELİ YÜKLEME" tablosu)
      hem de artık `sap_worktype_hint.py` (PreToolUse) GERÇEK obje-tipinden deterministik.
Bu hook YALNIZ SAP'den bağımsız akış-nudge'larını taşır (tarayıcı-token-verimli, ast-grep).
Sinyal yoksa sessiz.
"""
import json
import re
import sys

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Türkçe diyakritik-katlama (2026-07-10 health-check): ASCII yazımı da yakala.
_TR_FOLD = str.maketrans("şŞğĞıİöÖüÜçÇ", "sSgGiIoOuUcC")


def _fold(s: str) -> str:
    return s.translate(_TR_FOLD)


# (SAP-tespiti _STRONG/_TRANSPORT KALDIRILDI — redizayn; docstring'e bkz. Keşif native
#  skill description'ında, worktype-checklist sap_worktype_hint.py PreToolUse'da.)

# Tarayıcı/UI-doğrulama sinyali — SAP'den BAĞIMSIZ tetik. Amaç: token-verimli akışı
# (ui5-linter-önce, playwright-cli, bounding-box-assert, element-JPEG) DOĞRU ANDA dayatmak
# (T11: playbook notu yetmez). Vision-screenshot döngüsü patinajını keser.
_BROWSER = re.compile(
    r"(playwright|ekran\s*görüntü|screenshot|tarayıcı|\bbrowser\b|\be2e\b|"
    r"UI['’]?\s*[ıiy]?\s*(doğrula|test|kontrol|bak|gör)|görsel\s*(doğrula|test|kontrol)|"
    r"lokalde\s*(aç|bak|test|çalıştır|gör))",
    re.IGNORECASE,
)

# Yapısal kod arama/refactor sinyali — SAP'den BAĞIMSIZ. ast-grep'i (AST tabanlı) DOĞRU ANDA
# hatırlat; yoksa ripgrep/Grep'in LEXICAL körlüğüne düşülür (imza/yapı sorgusu). Kur-bırak DEĞİL,
# recall. 2026-06-13 tooling-radar ADOPT.
_STRUCTURAL = re.compile(
    r"(ast-?grep|\bAST\b|"
    r"yapısal\s*(ara|arama|sorgu|refactor|kod|eşleş|dönüş)|"
    r"toplu\s*(rename|refactor|yeniden\s*adlandır|imza)|"
    r"(imza|signature|method|fonksiyon|class|sınıf)\s*(deseni|bazlı|imzasıyla)\s*(ara|bul|değiş|tara))",
    re.IGNORECASE,
)

# (_WORKTYPES KALDIRILDI — redizayn: worktype→checklist artık sap_worktype_hint.py'de,
#  GERÇEK obje-tipinden, prompt-keyword tahmininden değil.)


# B5 fix (2026-07-09): otomatik-event işaretleri (task-notification/sistem-bildirimi =
# kullanıcı-turn'ü DEĞİL). Kullanıcı yazmaz → filtre yanlış-negatif üretmez. system-reminder HARİÇ.
_AUTO_EVENT_MARKERS = (
    "<task-notification>",
    "This is an automated background-task event",
    "[SYSTEM NOTIFICATION - NOT USER INPUT]",
)


def main() -> int:
    try:
        # UTF-8 stdin (Windows cp1252 TR-char bozulmasına karşı — intake_triage ile tutarlı, HC1 notu)
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except Exception:
        return 0
    prompt = data.get("prompt", "") or ""

    # B5: otomatik-event → enjeksiyon yok (task-notification'da "SAP işi" yanlış-pozitifi)
    if any(mk in prompt for mk in _AUTO_EVENT_MARKERS):
        return 0

    _folded = _fold(prompt)                       # diyakritik-bağımsız eşleşme
    # SAP-işi tespiti KALDIRILDI (redizayn): keşif native skill description'ında.
    browser_hit = bool(_BROWSER.search(prompt) or _BROWSER.search(_folded))
    structural_hit = bool(_STRUCTURAL.search(prompt) or _STRUCTURAL.search(_folded))
    if not browser_hit and not structural_hit:
        return 0

    parts = []

    if browser_hit:
        parts.append(
            "[Tarayıcı/UI doğrulama tespit edildi] Token-verimli akış (governance/tooling-plugins.md §playwright): "
            "(1) ÖNCE tarayıcısız doğrula — ui5-mcp run_ui5_linter / run_manifest_validation / get_api_reference "
            "(UI hatası + control-API; çoğu kontrol tarayıcı gerektirmez). "
            "(2) Tarayıcı gerekiyorsa `playwright-cli` skill'ini tercih et (Playwright MCP'den ~4x az token; snapshot→diske YAML). "
            "(3) Layout'u GÖZLE değil SAYIYLA doğrula: snapshot --json / `eval` getBoundingClientRect ile "
            "çakışma/hiza'yı KODLA kontrol et, vision'a gitme. "
            "(4) Görsel ŞARTSA yalnız elementi çek + JPEG (tam-sayfa PNG değil) → **`.tmp/`'ye yaz, ana klasöre DEĞİL** "
            "(gitignore'da; kullanıcı kuralı); state'i `eval` ile sür; snapshot'a hep target ver."
        )

    if structural_hit:
        parts.append(
            "[Yapısal kod arama/refactor] ripgrep/Grep LEXICAL — imza/AST desenine kör. Yapısal "
            "sorgu/dönüşüm için `ast-grep` CLI kullan (Bash): `ast-grep -p '<pattern>' -l <py|js|ts> "
            "<path>`; toplu rewrite `--rewrite '<yeni>'`. Düz metin eşleşmesi yetiyorsa Grep kalsın; "
            "imza/yapı/AST gerekiyorsa ast-grep (governance/tooling-plugins.md §ast-grep)."
        )

    # Enjekte edilen metodoloji yolları `core/` junction'ı altındadır; öneksiz yol
    # Read()'te çözülmez (2026-07-09 denetimi). Tek kaynak: utils/inject_paths.py
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # core/scripts
    from utils.inject_paths import core_onekle  # type: ignore

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": core_onekle("\n".join(parts)),
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
