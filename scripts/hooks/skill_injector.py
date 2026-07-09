#!/usr/bin/env python3
"""UserPromptSubmit — SAP işi tespit edilince sap-abap-dev skill + İŞ-TÜRÜNE ÖZEL
pre-flight checklist nudge'ı.

Skill zaten description ile auto-tetiklenir; bu hook ek deterministik güvence
(gap-analysis #9). GÜÇLÜ SAP sinyali varsa kısa bir nudge enjekte eder, ve tespit
edilen iş-türüne göre **okunması ZORUNLU checklist**i adıyla söyler (generic değil
hedefli — böylece o iş-türünün ~kuralları unutulmaz; bkz. lessons-learned PATTERN #8).
Sinyal yoksa sessiz (eşik yüksek, gürültü olmasın).
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

# Güçlü, az-yanlış-pozitif SAP geliştirme sinyalleri (hook'u tetikleyen genel eşik)
_STRONG = re.compile(
    r"\b(CDS\s+yarat|view\s+entity|RAP|BDEF|behavior\s+def|domain\s+ekle|DTEL|"
    r"struct(?:ure)?\s+yarat|tablo\s+yarat|SAP'?ye\s+push|aktive\s+et|"
    r"SRVB|service\s+binding|publish|where-used|ATC|ZSD\d{3}|\.conn_adt|"
    r"transport|lock\s+obje|message\s+class|Dynpro|ALV|Adobe\s+Form|"
    r"report\s+yaz|module\s+pool|fiori|UI5|freestyle)\b",
    re.IGNORECASE,
)

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

# İş-türü → okunması ZORUNLU pre-flight kaynağı (checklist varsa o, yoksa standart).
# Sıra önemli: ilk eşleşen(ler) raporlanır. (playbook/checklists/ altında.)
_WORKTYPES = [
    (re.compile(r"\b(CDS\s+yarat|value\s*help|arama\s+yardım|lookup\s+CDS|ddls|VH\s+yarat)\b", re.I),
     "CDS view-entity YARATMA", "playbook/adt-cds.md ⚡ 'TEK CDS YARATMA' reçetesi (shell→adt_push_source; post_shell-ddls/create_cds_view DEĞİL)"),
    (re.compile(r"\b(RAP|BDEF|behavior|view\s+entity|SRVB|service\s+binding|publish)\b", re.I),
     "RAP/CDS", "playbook/checklists/rap-creation.md (+ playbook/checklists/cds-creation.md) · standards/05"),
    (re.compile(r"\b(Dynpro|ALV|module\s+pool|report\s+yaz|klasik)\b", re.I),
     "Klasik dialog/ALV", "playbook/checklists/classic-dialog-creation.md · standards/06 (§1 include-böl ZORUNLU!)"),
    (re.compile(r"\b(freestyle|UI5|fiori)\b", re.I),
     "Freestyle UI5", "playbook/checklists/ui-freestyle-creation.md (+ playbook/checklists/ui-backend-rap-creation.md)"),
    (re.compile(r"\bstruct(?:ure)?\b", re.I),
     "DDIC struct", "playbook/checklists/struct-creation.md"),
    (re.compile(r"\b(tablo|table)\b", re.I),
     "DDIC tablo", "playbook/checklists/table-update.md"),
    (re.compile(r"\b(domain|DTEL)\b", re.I),
     "DDIC domain/DTEL", "playbook/checklists/domain-dtel-creation.md · standards/01 §5B (reuse-gate)"),
    (re.compile(r"\bAdobe\s+Form\b", re.I),
     "Adobe Forms", "playbook/checklists/adobe-forms-creation.md · standards/07"),
]


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

    sap_hit = bool(_STRONG.search(prompt))
    browser_hit = bool(_BROWSER.search(prompt))
    structural_hit = bool(_STRUCTURAL.search(prompt))
    if not sap_hit and not browser_hit and not structural_hit:
        return 0

    parts = []

    if sap_hit:
        hits = [(label, ref) for rx, label, ref in _WORKTYPES if rx.search(prompt)]
        if hits:
            lines = "; ".join(f"{label} → OKU: {ref}" for label, ref in hits)
            worktype_note = (
                f" İş-türü tespit edildi — ZORUNLU pre-flight checklist(ler): {lines}. "
                "SAP-yazma öncesi ilgili checklist'in HER maddesini geç (atlamak = patinaj)."
            )
        else:
            worktype_note = ""
        parts.append(
            "[SAP işi tespit edildi] sap-abap-dev skill rehberini izle: TIER 0 yasaklar "
            "(ADR 0005) → tetiklemeli yükleme tablosu (iş türü→okunacak dosya) → SAP yazma "
            "protokolü (run_review pre-flight, MCP tool/script kararı, .conn_adt'den oku). "
            "Bağlantı şüphesi: scripts/sap_doctor.py." + worktype_note
        )

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
