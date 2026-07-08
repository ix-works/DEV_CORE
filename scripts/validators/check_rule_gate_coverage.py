"""
check_rule_gate_coverage.py — KEYSTONE coverage-check (ADR 0019).

Amaç: "kural bir gate'in koruduğunu İDDİA ediyor ama gate aslında yok/wire-değil"
durumunu OTOMATİK yakala — yani checklist'in "BLOCKER der ama arkasında çalışan
script yok" (table-update.md:46 tuzağı) çürümesini engelle. Elle-bakımlı eşleme
TUTULMAZ → hesaplattırılır.

Kaynak-of-truth (canlı, "(WIRED)" etiketine GÜVENMEZ — kendisi hesaplar):
  - İddia: playbook/checklists/*.md tablo satırları (gate kolonunda `check_*.py` adı).
  - Mevcut script'ler: scripts/validators/check_*.py (dosya VAR mı).
  - WIRED küme: run_all_validators.py::VALIDATORS + run_review.py::TASK_VALIDATORS
    içinde geçen `check_*.py` adları.
  - Binding: gate script'i `# ENFORCES: <rule-id>` ile hangi kuralı koruduğunu beyan eder mi.

3-kademe (ADR 0019): (a) dosya var · (b) bir runner'a WIRED · (c) kırmızı-fixture
(her gate kendi fixture-testini taşır; bu coverage-check a+b+binding'i denetler,
fixture-varlığı gate'in kendi sorumluluğu).

HARD (ADR 0019 Gatekeeper TERFİ 2026-06-18): bulgu varsa exit 1 (default). Warn-first
shakeout temiz geçti (OK=49/0/0/0); exact-logic detektör (sezgisel FP yok) → hard.
Bulgu sınıfları:
  - MISSING  : checklist gate-script adı veriyor ama dosya YOK (en ciddi — sahte-WIRED).
  - ORPHAN   : script VAR ama hiçbir runner'da DEĞİL (wire-edilmemiş).
  - UNDECLARED: script VAR + WIRED ama `# ENFORCES:<id>` beyanı yok (binding eksik).

Kullanım: python scripts/validators/check_rule_gate_coverage.py [--strict]
"""
import argparse
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

REPO = Path(__file__).resolve().parents[2]
VALIDATORS_DIR = REPO / "scripts" / "validators"
CHECKLISTS_DIR = REPO / "playbook" / "checklists"

SCRIPT_RE = re.compile(r"\bcheck_[a-z0-9_]+\.py\b", re.IGNORECASE)
SCRIPT_BARE_RE = re.compile(r"\bcheck_[a-z0-9_]+(?:\.py)?\b", re.IGNORECASE)
ENFORCES_RE = re.compile(r"#\s*ENFORCES:\s*(.+)", re.IGNORECASE)


def wired_scripts() -> set[str]:
    """run_all + run_review içinde geçen check_*.py adları (canlı hesap, etikete güvenme)."""
    wired: set[str] = set()
    for runner in ("run_all_validators.py", "run_review.py"):
        p = VALIDATORS_DIR / runner
        if not p.exists():
            continue
        for m in SCRIPT_RE.finditer(p.read_text(encoding="utf-8", errors="replace")):
            wired.add(m.group(0).lower())
    return wired


def existing_scripts() -> set[str]:
    return {p.name.lower() for p in VALIDATORS_DIR.glob("check_*.py")}


def script_enforces() -> dict[str, set[str]]:
    """check_*.py → beyan ettiği rule-id kümesi (# ENFORCES: A, B)."""
    out: dict[str, set[str]] = {}
    for p in VALIDATORS_DIR.glob("check_*.py"):
        ids: set[str] = set()
        for m in ENFORCES_RE.finditer(p.read_text(encoding="utf-8", errors="replace")):
            ids |= {t.strip() for t in re.split(r"[,\s]+", m.group(1)) if t.strip()}
        out[p.name.lower()] = ids
    return out


def parse_checklist_claims():
    """checklist tablo satırlarından (rule_id, claimed_script, dosya, severity) çıkar.

    Yalnız gate kolonunda check_*.py adı GEÇEN satırlar = "auto-gate iddia eden" kurallar.
    """
    claims = []
    for md in sorted(CHECKLISTS_DIR.glob("*.md")):
        for raw in md.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4:
                continue
            rule_id = cells[0].strip("*` ").strip()  # markdown bold/code işaretlerini at
            if not rule_id or rule_id.upper() == "ID" or set(rule_id) <= set("-: "):
                continue  # başlık / ayraç satırı
            # gate kolonu = check_* geçen ilk hücre (genelde 4. kolon "Automatable/Gate").
            # .py uzantısı opsiyonel (bazı hücreler `check_x` yazıyor) → normalize et.
            gate_cell = ""
            for c in cells[1:]:
                if SCRIPT_BARE_RE.search(c):
                    gate_cell = c
                    break
            if not gate_cell:
                continue  # bu satır auto-gate iddia etmiyor (semantik/manuel) → kapsam dışı
            for m in SCRIPT_BARE_RE.finditer(gate_cell):
                name = m.group(0).lower()
                if not name.endswith(".py"):
                    name += ".py"
                claims.append((rule_id, name, md.name))
    return claims


def main() -> int:
    ap = argparse.ArgumentParser(description="Kural↔gate coverage (ADR 0019 keystone)")
    ap.add_argument("--strict", action="store_true", help="bulgu varsa exit 1")
    args = ap.parse_args()

    exists = existing_scripts()
    wired = wired_scripts()
    enforces = script_enforces()
    claims = parse_checklist_claims()

    missing, orphan, undeclared = [], [], []
    ok = 0
    for rule_id, script, md in claims:
        if script not in exists:
            missing.append((rule_id, script, md))
        elif script not in wired:
            orphan.append((rule_id, script, md))
        elif rule_id not in enforces.get(script, set()):
            undeclared.append((rule_id, script, md))
        else:
            ok += 1

    def dump(title, rows):
        if not rows:
            return
        print(f"\n[{title}] ({len(rows)})")
        for rule_id, script, md in rows:
            print(f"  {md}: {rule_id} → {script}")

    print(f"Coverage-check: {len(claims)} auto-gate iddiası (checklist gate-kolonu check_*.py).")
    dump("MISSING — checklist gate-script verir ama DOSYA YOK (sahte-WIRED)", missing)
    dump("ORPHAN — script VAR ama hiçbir runner'a WIRED DEĞİL", orphan)
    dump("UNDECLARED — WIRED ama gate `# ENFORCES:<id>` beyan etmiyor (binding eksik)", undeclared)
    print(f"\nÖzet: OK={ok} · MISSING={len(missing)} · ORPHAN={len(orphan)} · UNDECLARED={len(undeclared)}")

    total = len(missing) + len(orphan) + len(undeclared)
    if total:
        # HARD (ADR 0019 Gatekeeper TERFİ 2026-06-18): warn-first shakeout temiz geçti
        # (OK=49/0/0/0) → exact-logic detektör (sezgisel FP yok) default-hard'a terfi etti.
        # Bulgu = kural↔gate kopukluğu → forward progress YOK, önce kapat. (--strict gereksiz, hep hard.)
        print(f"\n{total} coverage bulgusu — BLOCKER (kural↔gate kopuk). "
              f"MISSING=sahte-WIRED (script yok/ad yanlış) · ORPHAN=run_all/run_review'e wire · "
              f"UNDECLARED=gate'e `# ENFORCES:<id>` ekle.", file=sys.stderr)
        return 1
    print("\n[OK] tüm auto-gate iddiaları: dosya var + WIRED + ENFORCES-beyanlı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
