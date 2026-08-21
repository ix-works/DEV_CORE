# ENFORCES: CORE-04  (ADR 0019 coverage binding — kendi kuralını da bağlar)
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
  - Şiddet: gate script'i `# GATE-SEVERITY: advisory` beyan ediyor mu (beyan YOKSA
    "bloklayıcı" varsayılır — sessiz advisory olmasın diye default sıkı taraftadır).

⚠ NİÇİN ŞİDDET AYRIMI (2026-08-20): "auto-gate iddiası" sayısı, arkasında **bloklayan** bir
script varmış gibi okunuyordu. Oysa bazı gate'ler bilinçle warn-first/advisory'dir (default
exit 0) — desen meşru kullanımı hatalıdan AYIRT EDEMEDİĞİ için (ör. `check_rap_byassoc_keys_only`:
canlı korpusta 2 bulgunun İKİSİ DE meşru). Bunları tek bir "N auto-gate" rakamına katmak
iddiayı gerçeğinden FAZLA gösterir. Özet artık `N iddia (B bloklayıcı · A advisory)` basar.
⛔ Bu AYRIM bir GEVŞETME DEĞİLDİR: MISSING/ORPHAN/UNDECLARED bulgu mantığı ve HARD exit 1
davranışı AYNEN korunur — advisory gate de dosya-var + WIRED + ENFORCES-beyanlı olmak
ZORUNDADIR. Değişen yalnız ÖZET SATIRININ dürüstlüğüdür.

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
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# ⚠ CORE-03: `REPO` core'un KENDİ varlıklarını (playbook/ · scripts/ · claude/) gösterir →
# `__file__` türevi BURADA MEŞRUDUR ve `project_config.project_root()`'a ÇEVRİLMEZ. Çevrilirse
# gate proje kökünde boş tarar, exit 0 verir ve hiçbir şeyi denetlemez (sessiz-yeşil sınıfı,
# core-script-development.md §Neden — üç ölçülmüş vaka). Hook dizini + settings.template.json
# da core varlığıdır, aynı kural geçerli.
REPO = Path(__file__).resolve().parents[2]
VALIDATORS_DIR = REPO / "scripts" / "validators"
CHECKLISTS_DIR = REPO / "playbook" / "checklists"
HOOKS_DIR = REPO / "scripts" / "hooks"
SETTINGS_SABLON = REPO / "claude" / "settings.template.json"

SCRIPT_RE = re.compile(r"\bcheck_[a-z0-9_]+\.py\b", re.IGNORECASE)
SCRIPT_BARE_RE = re.compile(r"\bcheck_[a-z0-9_]+(?:\.py)?\b", re.IGNORECASE)
# ⛔ SATIR-BAŞI ÇAPASI (2026-08-22) — kardeş `SEVERITY_RE` ile AYNI gerekçe, AYNI sınıf:
# "bir markörü TARİF eden metin, o markörü BEYAN etmiş sayılamaz". Çıplak `#\s*ENFORCES:`
# düz metin içindeki anışı da beyan sanıyordu — bu dosyanın KENDİ docstring'indeki
# "`# ENFORCES: <rule-id>` ile beyan eder mi" cümlesi hayalet bir `<rule-id>` üretiyordu.
# 17 hook'a beyan eklenirken (C2-b) bu boşluk SAHTE-YEŞİL demekti: bir docstring'de geçen
# "`# ENFORCES:` satırı ekle" anlatımı gerçek beyan yerine sayılırdı.
# ⛔ GEVŞETME DEĞİL SIKILAŞTIRMA. Girinti TOLERANSI bilerek korunur (`[ \t]*`) — kardeş
# SEVERITY_RE de izin veriyor; girintili `    # ENFORCES: X` MEŞRU beyandır (fixture S2).
ENFORCES_RE = re.compile(r"^[ \t]*#\s*ENFORCES:\s*(.+)", re.IGNORECASE | re.MULTILINE)
# `# GATE-SEVERITY: advisory` — beyan YOKSA "blocking" (default sıkı tarafta).
# ⛔ SATIR-BAŞI ÇAPASI ZORUNLU (`^\s*#`, MULTILINE): ilk sürüm çıplak `#\s*GATE-SEVERITY:`
# idi ve DÜZ METİN İÇİNDEKİ anışı da beyan sandı — bu dosyanın KENDİ docstring'i markörü
# tarif ettiği için `check_rule_gate_coverage` (HARD, exit 1) kendini "advisory" ilan etti
# (ölçüldü 2026-08-20: özet "2 advisory" derken biri bu sahte beyandı). Sınıf: bir markörü
# TARİF eden metin, o markörü BEYAN etmiş sayılamaz. Çapa fixture'da çivili (S3).
SEVERITY_RE = re.compile(r"^[ \t]*#\s*GATE-SEVERITY:\s*([A-Za-z]+)", re.MULTILINE)
ADVISORY_KELIMELER = {"advisory", "soft", "warn", "warn-first"}


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


# =============================== HOOK KATMANI (2026-08-22) ===========================
# NİÇİN: ADR 0019 üç-kademesi ("dosya var · WIRED · beyanlı") bugüne kadar YALNIZ
# `scripts/validators/check_*.py` için hesaplanıyordu. Oysa hook'lar da gate'tir ve
# aynı çürümeye açıktır — dahası hook'ta "WIRED" kavramı DAHA sert: matcher'ı yanlış
# bir hook hiç tetiklenmez ama kodu kusursuz görünür (ölçülmüş vaka: `pre_tool_guard`
# PowerShell desteği 29 senaryoyla yeşil geçip merge edildi, `settings` matcher'ı
# `Bash|mcp__sap-adt__.*` olduğu için PowerShell'de HİÇ ateşlenmedi — lessons-learned).
# ⇒ "kod-seviyesi koruma" ile "korunuyor" arasındaki farkı ölçen sınıf ORPHAN'dır.
#
# ⛔ ASİMETRİ BİLİNÇLİDİR (brifing kararı, ölçümle uyumlu):
#   · MISSING     = İDDİA-güdümlü (checklist bir hook adı verdi, dosya YOK)
#   · ORPHAN/UNDECLARED = ENVANTER-güdümlü (17 hook'un TAMAMI taranır)
# Sebep ölçüldü: checklist gate-kolonu HİÇBİR hook adı vermiyor; hook'lar düzyazıda
# anılıyor. İddia-güdümlü bir ORPHAN taraması bu yüzden 0 hook denetlerdi (ölü gate).

# İddia biçimi: YALNIZ `hooks/<ad>.py` / `scripts/hooks/<ad>.py` YOL yazımı.
# ⛔ ÇIPLAK AD TANIMA BİLEREK YAPILMADI — ölçüldü (2026-08-22): checklist düzyazısında
# `sap_sync_pull` · `pull_before_edit` yan yana anılıyor; `sap_sync_pull` bir hook DEĞİL
# (MCP tool) ⇒ çıplak snake_case tanıma onu "dosyası yok" diye YANLIŞ MISSING üretirdi.
# Yol yazımı belirsizlik taşımaz (FP=0). Bugünkü erişim: checklist'te 0 iddia — yani bu
# dal şu an ÖLÜ; canlı olan ORPHAN/UNDECLARED'dır. Sözleşme ileriye dönük tanımlıdır ve
# fixture'da mutasyonla canlılığı kanıtlanır (kod ölü değil, korpus henüz kullanmıyor).
HOOK_IDDIA_RE = re.compile(r"\b(?:scripts/)?hooks/([a-z0-9_]+)\.py", re.IGNORECASE)


def mevcut_hooklar() -> set[str]:
    """scripts/hooks/*.py adları (`_` önekliler yardımcı sayılır — C-TPL-01 ile AYNI kural)."""
    return {p.stem for p in HOOKS_DIR.glob("*.py") if not p.name.startswith("_")}


def kablolu_hooklar() -> tuple[set[str], str]:
    """settings.template.json'a kablolu hook adları + (varsa) ölçüm-hatası.

    ⛔ KOPYALAMA YOK: kablolama mantığının TEK KAYNAĞI C-TPL-01
    (`check_settings_template_sync._kablolu_hooklar`) — burada yeniden yazmak "ikinci
    gerçek" üretirdi (bu evde ölçülmüş çürüme sınıfı: aynı olgu iki yerde yaşarsa biri
    bayatlar). Kardeş-import doğrudan çağrıda çalışır ama `sys.path` garantisi ŞART
    (runner subprocess ile koşar; başka bir giriş noktası `sys.path[0]`'ı boş bırakabilir).

    ⛔ ÖLÇÜLEMEDİ ≠ TEMİZ: şablon okunamazsa boş küme dönmek TÜM hook'ları ORPHAN
    gösterirdi (sahte-kırmızı) ya da sessizce geçerdi (sahte-yeşil). Hata metni geri
    verilir, çağıran bunu AYRI bir çıktı satırı olarak bildirir.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from check_settings_template_sync import _kablolu_hooklar  # type: ignore
        d = json.loads(SETTINGS_SABLON.read_text(encoding="utf-8"))
        return _kablolu_hooklar(d, []), ""
    except Exception as e:  # noqa: BLE001 — teşhis metni raporlanacak
        return set(), f"{type(e).__name__}: {e}"


def hook_enforces() -> dict[str, set[str]]:
    """hook adı → `# ENFORCES:` ile beyan ettiği rule-id kümesi (validator'la AYNI okuyucu)."""
    out: dict[str, set[str]] = {}
    for p in sorted(HOOKS_DIR.glob("*.py")):
        if p.name.startswith("_"):
            continue
        ids: set[str] = set()
        for m in ENFORCES_RE.finditer(p.read_text(encoding="utf-8", errors="replace")):
            ids |= {t.strip() for t in re.split(r"[,\s]+", m.group(1)) if t.strip()}
        out[p.stem] = ids
    return out


def parse_hook_claims() -> list[tuple[str, str]]:
    """checklist tablo satırlarında `hooks/<ad>.py` yoluyla adı geçen hook'lar → (ad, dosya)."""
    claims: list[tuple[str, str]] = []
    for md in sorted(CHECKLISTS_DIR.glob("*.md")):
        for raw in md.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line.startswith("|"):
                continue
            for m in HOOK_IDDIA_RE.finditer(line):
                claims.append((m.group(1).lower(), md.name))
    return claims


def script_severity() -> dict[str, str]:
    """check_*.py → 'advisory' | 'blocking' (beyan yoksa 'blocking')."""
    out: dict[str, str] = {}
    for p in VALIDATORS_DIR.glob("check_*.py"):
        m = SEVERITY_RE.search(p.read_text(encoding="utf-8", errors="replace"))
        kelime = m.group(1).lower() if m else ""
        out[p.name.lower()] = "advisory" if kelime in ADVISORY_KELIMELER else "blocking"
    return out


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

    sev = script_severity()
    adv_iddia = sorted({(r, s) for r, s, _ in claims if sev.get(s) == "advisory"})
    n_adv = len(adv_iddia)
    n_blok = len(claims) - n_adv
    print(f"Coverage-check: {len(claims)} auto-gate iddiası "
          f"({n_blok} bloklayıcı · {n_adv} advisory) (checklist gate-kolonu check_*.py).")
    if adv_iddia:
        # Görünürlük: advisory bir gate BLOKLAMAZ — "korunuyor" sanısı üretmesin.
        print("  advisory (default exit 0 — bulguyu RAPORLAR, commit'i durdurmaz): "
              + " · ".join(f"{r}→{s}" for r, s in adv_iddia))
    dump("MISSING — checklist gate-script verir ama DOSYA YOK (sahte-WIRED)", missing)
    dump("ORPHAN — script VAR ama hiçbir runner'a WIRED DEĞİL", orphan)
    dump("UNDECLARED — WIRED ama gate `# ENFORCES:<id>` beyan etmiyor (binding eksik)", undeclared)
    print(f"\nÖzet: OK={ok} · MISSING={len(missing)} · ORPHAN={len(orphan)} · UNDECLARED={len(undeclared)}")

    # ---------------------- HOOK KATMANI (2026-08-22) ----------------------
    h_mevcut = mevcut_hooklar()
    h_kablolu, h_olcum_hatasi = kablolu_hooklar()
    h_enforces = hook_enforces()
    h_claims = parse_hook_claims()

    h_missing = [(ad, f"scripts/hooks/{ad}.py", md) for ad, md in h_claims
                 if ad not in h_mevcut]
    h_orphan: list[tuple[str, str, str]] = []
    h_undeclared: list[tuple[str, str, str]] = []
    h_ok = 0
    for ad in sorted(h_mevcut):
        if ad not in h_kablolu:
            h_orphan.append((ad, f"scripts/hooks/{ad}.py", "claude/settings.template.json"))
        elif not h_enforces.get(ad):
            # NOT: validator dalında test "bu rule_id beyan edildi mi"dir (iddia var).
            # Hook'ta iddia kaynağı yok → test "HERHANGİ bir beyan var mı" olur.
            h_undeclared.append((ad, f"scripts/hooks/{ad}.py", "beyan YOK"))
        else:
            h_ok += 1

    print(f"\nHook-coverage: {len(h_mevcut)} hook script · kablolama kaynağı "
          f"claude/settings.template.json (C-TPL-01 okuyucusu ORTAK, kopya değil) · "
          f"checklist yol-iddiası: {len(h_claims)}.")
    if h_olcum_hatasi:
        # ⛔ ÖLÇÜLEMEDİ ≠ TEMİZ (ve ≠ hepsi ORPHAN). Sessiz geçmek YASAK.
        print(f"  [ÖLÇÜLEMEDİ] settings.template.json okunamadı → ORPHAN hesaplanamadı: "
              f"{h_olcum_hatasi}", file=sys.stderr)
    dump("HOOK MISSING — checklist `hooks/<ad>.py` verir ama DOSYA YOK", h_missing)
    dump("HOOK ORPHAN — hook VAR ama settings.template.json'a KABLOLU DEĞİL", h_orphan)
    dump("HOOK UNDECLARED — kablolu ama `# ENFORCES:<id>` beyan etmiyor", h_undeclared)
    print(f"Özet (hook): OK={h_ok} · MISSING={len(h_missing)} · ORPHAN={len(h_orphan)}"
          f" · UNDECLARED={len(h_undeclared)}")

    total = (len(missing) + len(orphan) + len(undeclared)
             + len(h_missing) + len(h_orphan) + len(h_undeclared)
             + (1 if h_olcum_hatasi else 0))
    if total:
        # HARD (ADR 0019 Gatekeeper TERFİ 2026-06-18): warn-first shakeout temiz geçti
        # (OK=49/0/0/0) → exact-logic detektör (sezgisel FP yok) default-hard'a terfi etti.
        # Bulgu = kural↔gate kopukluğu → forward progress YOK, önce kapat. (--strict gereksiz, hep hard.)
        print(f"\n{total} coverage bulgusu — BLOCKER (kural↔gate kopuk). "
              f"MISSING=sahte-WIRED (script yok/ad yanlış) · ORPHAN=run_all/run_review'e wire · "
              f"UNDECLARED=gate'e `# ENFORCES:<id>` ekle. "
              f"HOOK ORPHAN=claude/settings.template.json'a kabla (kod ≠ kablolama).",
              file=sys.stderr)
        return 1
    print("\n[OK] tüm auto-gate iddiaları: dosya var + WIRED + ENFORCES-beyanlı.")
    print(f"[OK] {len(h_mevcut)} hook: kablolu + ENFORCES-beyanlı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
