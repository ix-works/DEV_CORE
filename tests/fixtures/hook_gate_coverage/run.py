#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HOOK KATMANI COVERAGE + `# ENFORCES:` SATIR-BASI CAPASI (2026-08-22).

NEDEN BU KORPUS VAR
-------------------
ADR 0019 uc-kademesi ("dosya var · WIRED · beyanli") bugune kadar YALNIZ
`scripts/validators/check_*.py` icin hesaplaniyordu. Hook'lar da gate'tir ve ayni
curumeye aciktir -- dahasi hook'ta "WIRED" DAHA sert bir kavramdir:

  Olculmus vaka (lessons-learned): `pre_tool_guard`a PowerShell destegi eklendi,
  29 senaryoluk test YESIL verdi, PR merge edildi -- ama `settings` matcher'i
  `Bash|mcp__sap-adt__.*` oldugu icin hook PowerShell'de HIC tetiklenmedi.
  Ders: guard'i DOGRUDAN cagiran her test sahte guvence uretir
  ("kod-seviyesi koruma" != "korunuyor"). ORPHAN sinifi tam bu dersin gate'idir.

IKINCI KUSUR (C2'nin ON KOSULU): `ENFORCES_RE` satir-basi CAPASIZ idi
(`r"#\\s*ENFORCES:"`). Kardesi `SEVERITY_RE` 2026-08-20'de tam bu yuzden
`^[ \\t]*#` ile capalanmisti; gerekce kayitli: **bir markoru TARIF eden metin, o
markoru BEYAN etmis sayilamaz**. Capasiz regex ile bir docstring icindeki
"`# ENFORCES:` satiri ekle" ANLATIMI gercek beyan yerine gecerdi ⇒ 17 hook'a beyan
eklenirken kabul olcutu ("17/17 beyan gorulur") ANLAMSIZ olurdu (sahte-yesil).

⛔ IZOLASYON: mutasyonlar GERCEK kaynaga YAZILMAZ. Her senaryo kendi gecici
agacinda kurulur (kopya validator + stub hook'lar + kendi settings.template.json).
Gercek kaynaga yazan mutasyon komsu testleri kirletir (olculmus sinif).

KOSUM:  python tests/fixtures/hook_gate_coverage/run.py
        ... --mutasyon-capa-yok        (ENFORCES_RE capasi sokulur -> duzyazi beyan sayilir)
        ... --mutasyon-hook-katmani-yok(hook bulgulari exit koduna KATILMAZ)
        ... --mutasyon-olcum-sessiz    ("OLCULEMEDI" hali sessizce temiz sayilir)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (mutasyon capasi tutmadi)

⚠ UC MUTASYON, HICBIRI DIGERINI KAPSAMAZ: biri capayi, biri bulgu->exit kablolamasini,
  biri "olculemedi != temiz" sozlesmesini civiller.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
VDIR = REPO / "scripts" / "validators"
GATE = VDIR / "check_rule_gate_coverage.py"
TPL_SYNC = VDIR / "check_settings_template_sync.py"
HOOKS_GERCEK = REPO / "scripts" / "hooks"

OLCULEMEDI = "[ÖLÇÜLEMEDİ]"

# --- mutasyon capalari (ICERIK capasi; taban SHA DEGIL) ----------------------
CAPA_RE = ('ENFORCES_RE = re.compile(r"^[ \\t]*#\\s*ENFORCES:\\s*(.+)", '
           're.IGNORECASE | re.MULTILINE)')
CAPA_TOTAL = ("    total = (len(missing) + len(orphan) + len(undeclared)\n"
              "             + len(h_missing) + len(h_orphan) + len(h_undeclared)\n"
              "             + (1 if h_olcum_hatasi else 0))")
CAPA_OLCUM = "+ (1 if h_olcum_hatasi else 0))"

MUTLAR = {
    # fix'in SOKUMU: capa kaldirilir -> duzyazidaki anis BEYAN sayilir (S6 duser)
    "--mutasyon-capa-yok": (
        CAPA_RE,
        'ENFORCES_RE = re.compile(r"#\\s*ENFORCES:\\s*(.+)", re.IGNORECASE)'),
    # KABLOLAMA sokumu: hook bulgulari hesaplanir ama exit koduna KATILMAZ.
    # ⚠ Bu, "gate kodu var ama bagli degil" sinifidir -- tam da ORPHAN'in olctugu sey.
    "--mutasyon-hook-katmani-yok": (
        CAPA_TOTAL,
        "    total = len(missing) + len(orphan) + len(undeclared)"),
    # "OLCULEMEDI != TEMIZ" sozlesmesinin sokumu (S7 duser).
    "--mutasyon-olcum-sessiz": (CAPA_OLCUM, "+ 0)"),
}

SABLON_BOZUK = "{ bu gecerli JSON DEGIL "


def _hook_govdesi(beyan: str) -> str:
    """Stub hook. `beyan` ham satir olarak gomulur (girinti/duzyazi varyantlari icin)."""
    return ("#!/usr/bin/env python3\n"
            f"{beyan}\n"
            '"""stub hook (fixture)."""\n'
            "raise SystemExit(0)\n")


HOOK_GOVDELERI = {
    # kanonik beyan (satir basi)
    "alfa": _hook_govdesi("# ENFORCES: X-01  (ADR 0019 coverage binding)"),
    # ⭐ GIRINTILI beyan MESRUDUR -- kardes SEVERITY_RE de `[ \t]*` toleransi tasir.
    # Capa eklenirken bu tolerans KAYBOLSAYDI gercek beyanlar dusherdi (pozitif kontrol).
    "beta": _hook_govdesi("    # ENFORCES: X-02  (girintili ama GERCEK beyan)"),
    # ⛔ DUZYAZI: markoru TARIF eder, BEYAN ETMEZ -> UNDECLARED sayilmali.
    "gama": ('#!/usr/bin/env python3\n'
             '"""Bu hook `# ENFORCES: X-03` markorunu TARIF eder; beyan DEGILDIR."""\n'
             "raise SystemExit(0)\n"),
    # beyani hic olmayan hook
    "delta": _hook_govdesi("# (beyan yok)"),
}


def kur(kok: Path, hooklar: list[str], *, kablosuz: tuple[str, ...] = (),
        checklist_satiri: str = "", sablon_bozuk: bool = False,
        gate_kaynak: str | None = None) -> Path:
    """Izole agac kurar: kopya validator + stub hook'lar + kendi settings.template.json.

    `REPO = Path(__file__).resolve().parents[2]` oldugu icin validator'i
    <kok>/scripts/validators/ altina koymak REPO'yu <kok> yapar (CORE-03: core
    varliklari icin `__file__` MESRUDUR, proje-kokune cevrilmez).
    """
    (kok / "scripts" / "validators").mkdir(parents=True, exist_ok=True)
    (kok / "scripts" / "hooks").mkdir(parents=True, exist_ok=True)
    (kok / "claude").mkdir(parents=True, exist_ok=True)
    (kok / "playbook" / "checklists").mkdir(parents=True, exist_ok=True)

    hedef = kok / "scripts" / "validators" / GATE.name
    hedef.write_text(gate_kaynak if gate_kaynak is not None
                     else GATE.read_text(encoding="utf-8"), encoding="utf-8")
    # ⛔ Tuketicinin IMPORT KOKU tasinmali: gate, kablolama okuyucusunu C-TPL-01'den
    # import eder (kopya DEGIL). Kardes dosya agacta yoksa olculen sey "fix" degil
    # "kurulum hatasi" olur (KURULAMADI != KACTI).
    shutil.copy2(TPL_SYNC, kok / "scripts" / "validators" / TPL_SYNC.name)

    for ad in hooklar:
        (kok / "scripts" / "hooks" / f"{ad}.py").write_text(
            HOOK_GOVDELERI[ad], encoding="utf-8")

    kablolu = [a for a in hooklar if a not in kablosuz]
    sablon = {"hooks": {"PreToolUse": [{"hooks": [
        {"type": "command", "command": "python",
         "args": ["scripts/hook_shim.py", ad]} for ad in kablolu]}]}}
    yol = kok / "claude" / "settings.template.json"
    if sablon_bozuk:
        yol.write_text(SABLON_BOZUK, encoding="utf-8")
    else:
        yol.write_text(json.dumps(sablon, indent=2), encoding="utf-8")

    if checklist_satiri:
        (kok / "playbook" / "checklists" / "x.md").write_text(
            "| ID | Kontrol | Gate | Severity |\n|---|---|---|---|\n"
            + checklist_satiri + "\n", encoding="utf-8")
    return hedef


def kos(gate_yolu: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(gate_yolu)], capture_output=True, timeout=180)
    return p.returncode, (p.stdout.decode("utf-8", "replace")
                          + p.stderr.decode("utf-8", "replace"))


def main() -> int:
    # BILINMEYEN KIP SESSIZCE YESIL GECMESIN: `--mutasyon-ZIRVA` gibi bir yazim hatasi
    # HIC mutasyon kurmadan TAM PUAN uretirdi (exit 0) -- "mutasyon yakalandi" sanilan
    # sonuc aslinda mutasyonsuz kosum olurdu.
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in MUTLAR:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + ", ".join(sorted(MUTLAR)))

    secili = [a for a in sys.argv[1:] if a in MUTLAR]
    gate_kaynak = None
    if secili:
        ham = GATE.read_text(encoding="utf-8")
        eski, yeni = MUTLAR[secili[0]]
        if eski not in ham:
            print(f"[DOGRULANAMADI] mutasyon capasi tabanda bulunamadi ({secili[0]}) -> "
                  "mutasyon uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
            return 2
        gate_kaynak = ham.replace(eski, yeni, 1)

    tmp = Path(tempfile.mkdtemp(prefix="hook_gate_cov_"))
    sonuc: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, aciklama=""):
        sonuc.append((ad, bool(kosul), aciklama))

    def senaryo(ad: str, **kw) -> tuple[int, str]:
        kok = tmp / ad
        kok.mkdir(parents=True, exist_ok=True)
        return kos(kur(kok, gate_kaynak=gate_kaynak, **kw))

    try:
        # === S1 TEMIZ TABAN — kusursuz agac SIFIR bulgu vermeli ===============
        # ⚠ Bu vektor "erisilebilir yesil" kanitidir: gate'in TEMIZLENEBILIR oldugunu
        # gostermeyen bir gate, gecilemez bir gate'tir.
        rc, out = senaryo("s1", hooklar=["alfa", "beta"])
        ekle("S1 temiz agac -> exit 0 + hook ozeti SIFIR bulgu",
             rc == 0 and "Özet (hook): OK=2 · MISSING=0 · ORPHAN=0 · UNDECLARED=0" in out,
             f"exit={rc}")

        # === S2 GIRINTI TOLERANSI (pozitif kontrol) ==========================
        # ⛔ SILINEMEZ: capa eklenirken girinti toleransi de kaybolsaydi gercek
        # beyanlar dusherdi. "Sikilastirma kapiyi korletmedi" kaniti YALNIZ burasi.
        rc, out = senaryo("s2", hooklar=["beta"])
        ekle("S2 GIRINTILI `    # ENFORCES:` GERCEK beyandir (kapsam kaybi yok)",
             rc == 0 and "UNDECLARED=0" in out, f"exit={rc}")

        # === S3 UNDECLARED — beyansiz hook ===================================
        rc, out = senaryo("s3", hooklar=["alfa", "delta"])
        ekle("S3 beyansiz hook -> exit 1 + HOOK UNDECLARED + adi listelenir",
             rc == 1 and "HOOK UNDECLARED" in out and "delta" in out, f"exit={rc}")

        # === S4 ORPHAN — kablolanmamis hook (ASIL DERS) ======================
        rc, out = senaryo("s4", hooklar=["alfa", "beta"], kablosuz=("beta",))
        ekle("S4 settings.template.json'a KABLOSUZ hook -> exit 1 + HOOK ORPHAN",
             rc == 1 and "HOOK ORPHAN" in out and "beta" in out, f"exit={rc}")

        # === S5 MISSING — checklist yol-iddiasi, dosya YOK ===================
        rc, out = senaryo("s5", hooklar=["alfa"],
                          checklist_satiri="| K-01 | ornek | `scripts/hooks/hayalet.py` | BLOCKER |")
        ekle("S5 checklist `hooks/<ad>.py` verir ama dosya YOK -> exit 1 + HOOK MISSING",
             rc == 1 and "HOOK MISSING" in out and "hayalet" in out, f"exit={rc}")

        # === S6 DUZYAZI BEYAN SAYILMAZ (capanin KENDISI) =====================
        rc, out = senaryo("s6", hooklar=["alfa", "gama"])
        ekle("S6 docstring'de ANILAN `# ENFORCES:` BEYAN DEGILDIR -> gama UNDECLARED",
             rc == 1 and "HOOK UNDECLARED" in out and "gama" in out, f"exit={rc}")

        # === S7 OLCULEMEDI != TEMIZ =========================================
        # ⚠ HOOK LISTESI BILEREK BOS: ilk yazimda `hooklar=["alfa"]` idi ve vektor
        # SAHTE-YESIL veriyordu -- bozuk sablon kablolu-kumeyi de bosaltinca alfa
        # ORPHAN olup exit 1'i ZATEN uretiyordu. Yani "olculemedi exit'e katiliyor"
        # iddiasi olculmemis, KABA filtre ince filtreyi MASKELEMISTI
        # (`--mutasyon-olcum-sessiz` bu yuzden KACIYORdu; olculdu 2026-08-22).
        # Hook yokken tek olasi bulgu kaynagi OLCUM HATASIDIR -> izolasyon tam.
        rc, out = senaryo("s7", hooklar=[], sablon_bozuk=True)
        ekle("S7 sablon okunamazsa SESSIZ GECMEZ -> exit 1 + [ÖLÇÜLEMEDİ] notu",
             rc == 1 and OLCULEMEDI in out, f"exit={rc}")

        # === S8 KABLOLAMA MANTIGI KOPYALANMADI ==============================
        # C-TPL-01 ile ORTAK okuyucu: ayni olgu iki yerde yasarsa biri bayatlar.
        kaynak = GATE.read_text(encoding="utf-8")
        ekle("S8 kablolama okuyucusu C-TPL-01'den IMPORT edilir (kopya DEGIL)",
             "from check_settings_template_sync import _kablolu_hooklar" in kaynak,
             "kopya mantik = ikinci gercek (olculmus curume sinifi)")

        # === S9 GERCEK REPO — mevcut davranis BOZULMADI (pozitif kontrol) ====
        # ⚠ Sandbox yesili CANLI yesil demek degildir: gercek korpusta da olc.
        rc, out = kos(GATE)
        gercek_hook = len([p for p in HOOKS_GERCEK.glob("*.py")
                           if not p.name.startswith("_")])
        ekle("S9 CANLI repo: validator katmani + hook katmani birlikte TEMIZ",
             rc == 0 and "Özet: OK=" in out
             and f"Özet (hook): OK={gercek_hook} ·" in out
             and "MISSING=0 · ORPHAN=0 · UNDECLARED=0" in out,
             f"exit={rc}; canli hook sayisi={gercek_hook}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"[kalinti-kontrolu] gecici agac duruyor mu: "
              f"{'EVET -- TEMIZLIK BASARISIZ' if tmp.exists() else 'hayir'}")

    gecen = sum(1 for _a, k, _c in sonuc if k)
    for ad, k, ac in sonuc:
        print(f"  [{'PASS' if k else 'FAIL'}] {ad}" + (f"  ({ac})" if not k else ""))
    print(f"\nhook_gate_coverage: {gecen}/{len(sonuc)}")
    if secili:
        print(f"  (MUTASYON {secili[0]} — dusmesi BEKLENEN vektorler var; "
              f"tam skor 'mutasyon KACTI' demektir)")
        return 0 if gecen < len(sonuc) else 1
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    raise SystemExit(main())
