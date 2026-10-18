# -*- coding: utf-8 -*-
"""rules_naming_standard — check_package_rules_naming_standard.py KALICI KORPUSU (19 vektör, 11 mutasyon).

Kapının iddiası İKİ YÖNLÜDÜR ve ikisi de kanıtlanır:
  (a) YAKALAMA : paket `.rules.md` naming tablosunda kanonik kümede olmayan DTEL/Domain öneki
      (asıl sınıf: eski şablonun `{PKG}_DE_*`/`{PKG}_DOM_*` satırını miras alan paket),
  (b) SESSİZLİK: şablonun alternatiflerinden birini seçen paket (ALT KÜME), `{PKG_NOZ}` yer
      tutuculu `Class` satırı, gerekçeli muafiyet, `_CLC` eki olmayan paket adı.
Ayrıca kapının KANONİK KAYNAĞI tektir (şablon): gömülü bir kopyaya dönülürse V10 düşer.

2026-10-18 bug-gate düzeltme turu (V12–V19):
  · V12/V13 obje tipi anahtarı harf/biçimden bağımsız (`| Data element |`, `| **Domain** |`,
    `` | `Domain` | `` + küçük harfli NAMING-ISTISNA) — eski kodda bu satırlar SESSİZCE atlanıyordu.
  · V14 KAPSAM BEYANI: ölçülen paket/satır sayısı + eksen satırı olmayan paket `ÖLÇÜLMEDİ`
    (tam + kısmi); satırın `run_all --ozet` süzgecinden geçtiği GERÇEK `_gorunur_zorunlu_mu`
    ile ölçülür.
  · V15 kaynak kökü YOK → ÖLÇÜLEMEDİ exit 2 (0 paket ile karışmaz; V8 o dalın kontrolü).
  · V16 paket keşfi iki seviye (`find_packages` ortak): iç içe `.rules.md` paket sayılmaz.
  · V17–V19 KARDEŞ `check_package_rules_present` aynı ayrımı yapar (kök yok 2 · 0 paket
    [SKIP] 0 · eksik `.rules.md` 1 = değişmeyen davranışın kontrol grubu).

Şablon çıktısı GERÇEK üreticiden alınır: V3/V4 `scripts/bootstrap_package.py`'yi alt süreçte
koşar (V4'te şablonun eski `_DE_`/`_DOM_` satırlı bir kopyasıyla) — elle yazılmış bir taklit
değil, üreticinin ürettiği `.rules.md` ölçülür.

Her vektör KENDİ sandbox'ını kurar: sahte proje kökü (`project.yaml` + kaynak kökü) + sahte
core kökü (`scripts/validators/<kapı>` kopyası + `templates/new-package/.rules.md.tmpl`
kopyası) — kapının `__file__`-türevli varsayılan şablon yolu da böylece ölçülür. Mutasyonlar
yalnız sandbox kopyasına yazılır (gerçek kaynağa dokunulmaz).

Kullanım:
    python tests/fixtures/rules_naming_standard/run.py
    python tests/fixtures/rules_naming_standard/run.py --mutasyon-altkume   (…-pkgnoz /
          -kapsamsifir / -sablonfailopen / -istisna / -gomulu / -tipnorm / -olculmedi /
          -kokyok / -rglob / -presentkokyok)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
GATE = CORE / "scripts" / "validators" / "check_package_rules_naming_standard.py"
# Paket keşfi kardeş kapıdan import edilir (tek kaynak) ⇒ sandbox'a o da kopyalanır.
PRESENT = CORE / "scripts" / "validators" / "check_package_rules_present.py"
RUN_ALL = CORE / "scripts" / "validators" / "run_all_validators.py"
SABLON = CORE / "templates" / "new-package" / ".rules.md.tmpl"
TPL_DIR = CORE / "templates" / "new-package"
BOOT = CORE / "scripts" / "bootstrap_package.py"

DE_DOGRU = "| Data Element | `{PKG}_E_*` | `^{PKG}_E_[A-Z0-9_]+$` |"
DOM_DOGRU = "| Domain | `{PKG}_D_*` | `^{PKG}_D_[A-Z0-9_]+$` |"
DE_ESKI = "| Data Element | `{PKG}_DE_*` veya `{PKG}_DTEL_*` | `^{PKG}_(DE|DTEL)_[A-Z0-9_]+$` |"
DOM_ESKI = "| Domain | `{PKG}_DOM_*` | `^{PKG}_DOM_[A-Z0-9_]+$` |"


def rules(pkg: str, de: str, dom: str, cls: str | None = None, ek: str = "") -> str:
    satirlar = ["# %s — Paket Kuralları" % pkg, "", "## Naming", "",
                "| Obje Tipi | Prefix | Regex |", "|---|---|---|",
                "| Data Element | `%s` | x |" % de, "| Domain | `%s` | x |" % dom]
    if cls:
        satirlar.append("| Class | %s | x |" % cls)
    return "\n".join(satirlar) + "\n" + ek


def eski_sablon() -> str:
    """Gerçek şablonun 2026-08-20 ÖNCESİ DTEL/Domain satırlarıyla kopyası."""
    metin = SABLON.read_text(encoding="utf-8")
    for dogru, eski in ((DE_DOGRU, DE_ESKI), (DOM_DOGRU, DOM_ESKI)):
        if metin.count(dogru) != 1:
            print(f"[DUR] şablon çapası {metin.count(dogru)} kez geçiyor (1 olmalı): {dogru!r}",
                  file=sys.stderr)
            sys.exit(3)
        metin = metin.replace(dogru, eski)
    return metin


def sandbox(tmp: Path, kaynaklar: tuple, source_root: str = "SOURCE_CODES") -> tuple:
    gate_kaynak, present_kaynak = kaynaklar
    proje, core = tmp / "proje", tmp / "core"
    (proje / source_root).mkdir(parents=True)
    (proje / "project.yaml").write_text(
        f"sap_profile: s4_private\nsource_root: {source_root}\n", encoding="utf-8")
    (core / "scripts" / "validators").mkdir(parents=True)
    (core / "scripts" / "validators" / GATE.name).write_text(gate_kaynak, encoding="utf-8")
    (core / "scripts" / "validators" / PRESENT.name).write_text(present_kaynak, encoding="utf-8")
    (core / "templates" / "new-package").mkdir(parents=True)
    shutil.copyfile(SABLON, core / "templates" / "new-package" / ".rules.md.tmpl")
    return proje, core


def env_for(proje: Path) -> dict:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(proje), PYTHONIOENCODING="utf-8")
    for k in ("IX_SOURCE_ROOT", "IX_SAP_PROFILE"):
        env.pop(k, None)              # çevre config'ini miras alma (yokluk vektörü dersi)
    yollar = [str(CORE / "scripts")]
    if os.environ.get("PYTHONPATH"):
        yollar.append(os.environ["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(yollar)
    return env


def yaz(proje: Path, rel: str, metin: str) -> None:
    p = proje / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(metin, encoding="utf-8")


def bootstrap(proje: Path, paket: str, templates_root: Path) -> None:
    r = subprocess.run([sys.executable, str(BOOT), paket, "--title", "Fixture", "--module", "SD",
                        "--templates-root", str(templates_root)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env_for(proje), cwd=str(proje))
    if r.returncode != 0:
        print(f"[DUR] bootstrap kurulamadı (rc={r.returncode}): {(r.stderr or r.stdout)[:300]}",
              file=sys.stderr)
        sys.exit(3)


# ── vektör kurucuları: (proje, core, tmp) -> ek-argümanlar ──────────────────
def k_eski_paket(proje, core, tmp):
    yaz(proje, "SOURCE_CODES/SD/ZSD001_CLC/.rules.md", rules("ZSD001", "ZSD001_DE_*", "ZSD001_D_*"))
    return []


def k_eski_paket_hard(proje, core, tmp):
    k_eski_paket(proje, core, tmp)
    return ["--bulguda-exit1"]


def k_bootstrap_temiz(proje, core, tmp):
    bootstrap(proje, "ZSD001_CLC", TPL_DIR)
    return []


def k_bootstrap_eski_sablon(proje, core, tmp):
    eski = tmp / "eski_tpl"
    shutil.copytree(TPL_DIR, eski)
    (eski / ".rules.md.tmpl").write_text(eski_sablon(), encoding="utf-8")
    bootstrap(proje, "ZSD000_CLC", eski)
    return []


def k_class_altkume(proje, core, tmp):
    yaz(proje, "SOURCE_CODES/SD/ZSD001_CLC/.rules.md",
        rules("ZSD001", "ZSD001_E_*", "ZSD001_D_*", cls="`ZCL_SD001_*`"))
    return []


def k_class_eski_bilgi(proje, core, tmp):
    yaz(proje, "SOURCE_CODES/SD/ZSD001_CLC/.rules.md",
        rules("ZSD001", "ZSD001_E_*", "ZSD001_D_*", cls="`ZCL_ZSD001_*`"))
    return []


def k_istisna(proje, core, tmp):
    yaz(proje, "SOURCE_CODES/SD/ZSD001_CLC/.rules.md",
        rules("ZSD001", "ZSD001_E_*", "ZSD001_DOM_*",
              ek="<!-- NAMING-ISTISNA: Domain — canlıda eski önekli obje var, rename yok -->\n"))
    return []


def k_kapsam_sifir(proje, core, tmp):
    (proje / "SOURCE_CODES" / ".gitkeep").write_text("", encoding="utf-8")
    return []


def k_sablon_yok(proje, core, tmp):
    k_eski_paket(proje, core, tmp)
    (core / "templates" / "new-package" / ".rules.md.tmpl").unlink()
    return []


def k_ucuncu_baglam(proje, core, tmp):
    # project.yaml source_root=ABAP_SRC (sandbox çağrısında) · MM modülü · `_CLC` eki YOK
    yaz(proje, "ABAP_SRC/MM/ZMM001/.rules.md",
        rules("ZMM001", "ZMM001_E_*", "ZMM001_D_*", cls="`ZCL_MM001_*` veya `ZMM001_CL_*`"))
    yaz(proje, "ABAP_SRC/MM/ZMM002/.rules.md", rules("ZMM002", "ZMM002_DE_*", "ZMM002_D_*"))
    return []


def k_tip_bicim(proje, core, tmp):
    # Tüketici pakette ölçülen biçim (`| Data element |`) + kalın tip: ikisi de ÖLÇÜLMELİ.
    yaz(proje, "SOURCE_CODES/SD/ZSD001_CLC/.rules.md",
        "# ZSD001\n\n| Obje Tipi | Prefix | Regex |\n|---|---|---|\n"
        "| Data element | `ZSD001_DE_*` | x |\n| **Domain** | `ZSD001_DOM_*` | x |\n")
    return []


def k_tip_backtick_istisna(proje, core, tmp):
    yaz(proje, "SOURCE_CODES/SD/ZSD001_CLC/.rules.md",
        "# ZSD001\n\n| Obje Tipi | Prefix | Regex |\n|---|---|---|\n"
        "|  **Data  ELEMENT**  | `ZSD001_E_*` | x |\n| `Domain` | `ZSD001_DOM_*` | x |\n"
        "<!-- NAMING-ISTISNA: domain — canlıda eski önekli obje var -->\n")
    return []


def k_kapsam_beyani(proje, core, tmp):
    yaz(proje, "SOURCE_CODES/SD/ZSD001_CLC/.rules.md", rules("ZSD001", "ZSD001_E_*", "ZSD001_D_*"))
    yaz(proje, "SOURCE_CODES/SD/ZSD000_CLC/.rules.md",
        "# ZSD000\n\n| Obje Tipi | Prefix | Regex |\n|---|---|---|\n"
        "| Class | `ZCL_SD000_*` | x |\n")
    yaz(proje, "SOURCE_CODES/MM/ZMM001/.rules.md",
        "# ZMM001\n\n| Obje Tipi | Prefix | Regex |\n|---|---|---|\n"
        "| Domain | `ZMM001_D_*` | x |\n")
    return []


def k_kok_yok(proje, core, tmp):
    (proje / "SOURCE_CODES").rmdir()
    return []


def k_ic_ice(proje, core, tmp):
    yaz(proje, "SOURCE_CODES/SD/ZSD001_CLC/.rules.md", rules("ZSD001", "ZSD001_E_*", "ZSD001_D_*"))
    yaz(proje, "SOURCE_CODES/SD/ZSD001_CLC/ui/app/node_modules/paket/.rules.md",
        rules("paket", "paket_DE_*", "paket_DOM_*"))
    return []


def k_present_paket_eksik(proje, core, tmp):
    yaz(proje, "SOURCE_CODES/SD/ZSD001_CLC/.rules.md", rules("ZSD001", "ZSD001_E_*", "ZSD001_D_*"))
    (proje / "SOURCE_CODES" / "MM" / "ZMM001").mkdir(parents=True)
    return []


def k_tek_kaynak(proje, core, tmp):
    # Kapı şablonu OKUYORSA şablon değişince hüküm de değişir: Domain `{PKG}_DOM_*` yapılmış
    # bir şablona karşı, bootstrap'in (gerçek şablonla) ürettiği `_D_` satırı SAPMA olur.
    bootstrap(proje, "ZSD001_CLC", TPL_DIR)
    t = core / "templates" / "new-package" / ".rules.md.tmpl"
    metin = t.read_text(encoding="utf-8")
    if metin.count(DOM_DOGRU) != 1:
        print("[DUR] V10 çapası şablonda yok", file=sys.stderr)
        sys.exit(3)
    t.write_text(metin.replace(DOM_DOGRU, DOM_ESKI), encoding="utf-8")
    return []


# (ad, kurucu, source_root, beklenen-exit, çıktıda-OLMALI, çıktıda-OLMAMALI)
VEKTORLER = [
    ("V1 KIRMIZI — eski `_DE_` satırlı paket → PREFIX-SAPMASI (warn-first exit 0)",
     k_eski_paket, "SOURCE_CODES", 0, ["PREFIX-SAPMASI", "ZSD001_DE_*", "[UYARI]"], ["[OK]"]),
    ("V2 KIRMIZI + --bulguda-exit1 → exit 1",
     k_eski_paket_hard, "SOURCE_CODES", 1, ["PREFIX-SAPMASI", "[BULGU]"], []),
    ("V3 YEŞİL — GERÇEK şablondan bootstrap edilmiş paket TAM uyumlu ([BİLGİ] bile yok)",
     k_bootstrap_temiz, "SOURCE_CODES", 0, ["[OK] 1 paket · 2 satır ölçüldü"],
     ["PREFIX-SAPMASI", "[BİLGİ]", "ÖLÇÜLMEDİ:"]),
    ("V4 ŞABLON ÇIKTISI — eski `_DE_/_DOM_` şablonundan bootstrap → İKİ eksen yakalanır",
     k_bootstrap_eski_sablon, "SOURCE_CODES", 0,
     ["PREFIX-SAPMASI", "ZSD000_DE_*", "ZSD000_DOM_*", "2 sapma"], ["[OK]"]),
    ("V5 FP ÇAPASI — `Class` = `ZCL_SD001_*` ({PKG_NOZ} çözülür, ALT KÜME) → bilgi YOK",
     k_class_altkume, "SOURCE_CODES", 0, ["[OK]"], ["[BİLGİ]", "PREFIX-SAPMASI"]),
    ("V6 `Class` = eski `ZCL_ZSD001_*` → [BİLGİ] (bulgu DEĞİL)",
     k_class_eski_bilgi, "SOURCE_CODES", 0, ["[BİLGİ]", "ZCL_ZSD001_*", "[OK]"], ["PREFIX-SAPMASI"]),
    ("V7 NAMING-ISTISNA — gerekçeli muafiyet bulgu üretmez, sayılır",
     k_istisna, "SOURCE_CODES", 0, ["muafiyet (NAMING-ISTISNA): 1", "[OK]"], ["PREFIX-SAPMASI"]),
    ("V8 KAPSAM SIFIR — `.rules.md` yok → görünür [SKIP], exit 0, '[OK]' YOK",
     k_kapsam_sifir, "SOURCE_CODES", 0, ["[SKIP] KAPSAM SIFIR", "ÖLÇÜLMEDİ"], ["[OK]"]),
    ("V9 ŞABLON YOK → ÖLÇÜLEMEDİ exit 2, 'temiz' DEĞİL",
     k_sablon_yok, "SOURCE_CODES", 2, ["ÖLÇÜLEMEDİ", "kanonik şablon YOK"], ["[OK]"]),
    ("V10 TEK KAYNAK — şablon değişince hüküm değişir (gömülü kopya YOK)",
     k_tek_kaynak, "SOURCE_CODES", 0, ["PREFIX-SAPMASI", "Domain", "ZSD001_DOM_*"], ["[OK]"]),
    ("V11 ÜÇÜNCÜ BAĞLAM — source_root=ABAP_SRC · MM · `_CLC`'siz ad: biri temiz, biri sapma",
     k_ucuncu_baglam, "ABAP_SRC", 0,
     ["2 paket", "ZMM002_DE_*", "1 sapma"], ["ZMM001_E_*", "[BİLGİ]"]),
    # ── 2026-10-18 bug-gate düzeltme turu ──
    ("V12 F1 TİP BİÇİMİ — `| Data element |` + `| **Domain** |` satırları ÖLÇÜLÜR → 2 sapma",
     k_tip_bicim, "SOURCE_CODES", 0,
     ["PREFIX-SAPMASI", "ZSD001_DE_*", "ZSD001_DOM_*", "2 sapma"], ["[OK]", "ÖLÇÜLMEDİ:"]),
    ("V13 F1 TİP BİÇİMİ — boşluklu/kalın/backtick tip + küçük harfli NAMING-ISTISNA eşleşir",
     k_tip_backtick_istisna, "SOURCE_CODES", 0,
     ["muafiyet (NAMING-ISTISNA): 1", "[OK] 1 paket · 1 satır ölçüldü"],
     ["PREFIX-SAPMASI", "ÖLÇÜLMEDİ:"]),
    ("V14 F2 KAPSAM BEYANI — ölçülen paket/satır + eksen satırsız paket ÖLÇÜLMEDİ (tam + kısmi)",
     k_kapsam_beyani, "SOURCE_CODES", 0,
     ["[OK] 2 paket · 3 satır ölçüldü", "3 paket `.rules.md` tarandı",
      "ÖLÇÜLMEDİ: 1 paket (DTEL/Domain satırı yok)", "SOURCE_CODES/SD/ZSD000_CLC/.rules.md",
      "ÖLÇÜLMEDİ (kısmi): 1 paket"],
     ["PREFIX-SAPMASI", "check_package_rules_present"],
     {"ozet": ["ÖLÇÜLMEDİ: 1 paket", "ÖLÇÜLMEDİ (kısmi): 1 paket"]}),
    ("V15 F7 KAYNAK KÖKÜ YOK → ÖLÇÜLEMEDİ exit 2 (0 paket [SKIP]'i ile karışmaz)",
     k_kok_yok, "SOURCE_CODES", 2, ["[ÖLÇÜLEMEDİ] kaynak kökü yok"], ["[SKIP]", "[OK]"]),
    ("V16 Ö1 PAKET KEŞFİ iki seviye — iç içe `.rules.md` (node_modules) paket SAYILMAZ",
     k_ic_ice, "SOURCE_CODES", 0, ["1 paket `.rules.md`", "[OK] 1 paket"],
     ["PREFIX-SAPMASI", "paket_DE_*"]),
    ("V17 KARDEŞ rules_present — kaynak kökü YOK → ÖLÇÜLEMEDİ exit 2",
     k_kok_yok, "SOURCE_CODES", 2, ["[ÖLÇÜLEMEDİ] kaynak kökü yok"], ["[SKIP]", "OK —"],
     {"hedef": "present"}),
    ("V18 KARDEŞ rules_present — kök var, 0 paket → görünür [SKIP] KAPSAM SIFIR exit 0",
     k_kapsam_sifir, "SOURCE_CODES", 0, ["[SKIP] KAPSAM SIFIR", "ÖLÇÜLMEDİ"],
     ["ÖLÇÜLEMEDİ", "OK —"], {"hedef": "present"}),
    ("V19 KARDEŞ rules_present KONTROL — `.rules.md`'siz paket → exit 1 (davranış DEĞİŞMEDİ)",
     k_present_paket_eksik, "SOURCE_CODES", 1, ["HATA", "ZMM001"], ["[SKIP]"],
     {"hedef": "present"}),
]

# çapa-metni → değişim (TAM eşleşme; bulunamazsa koşucu DURUR)
MUTASYONLAR = {
    "altkume": ("            yabanci = tablo[tip] - beklenen",
                "            yabanci = set()"),
    "pkgnoz": ('    return {"PKG": pkg, "PKG_NOZ": pkg_noz_turet(pkg), "PKG_FULL": pkg_full}',
               '    return {"PKG": pkg, "PKG_FULL": pkg_full}'),
    "kapsamsifir": ("    if not dosyalar:\n", "    if False:\n"),
    "sablonfailopen": ('        raise Olculemedi(f"kanonik şablon YOK: {sablon}")',
                       "        return {}"),
    "istisna": ("            if tip in muaf:", "            if False:"),
    "gomulu": ('    tablo = naming_satirlari(sablon.read_text(encoding="utf-8", errors="replace"), adlar)',
               '    tablo = {"data element": {"{PKG}_E_*"}, "domain": {"{PKG}_D_*"},\n'
               '             "class": {"ZCL_{PKG_NOZ}_*", "{PKG}_CL_*"}}'),
    # F1: tip anahtarı ham metne döner (eski harf/biçim duyarlılığı) → V12 V13
    "tipnorm": ('    return " ".join(ham.replace("*", " ").replace("`", " ").split()).casefold()',
                "    return ham.strip()"),
    # F2: eksen satırsız paket sayısı basılmaz → V14
    "olculmedi": ('    if eksensiz:\n', "    if False:\n"),
    # F7: kök yok dalı kalkar (0 paket [SKIP]'ine düşer) → V15
    "kokyok": ("    if not kok.is_dir():\n", "    if False:\n"),
    # Ö1: eski tüm-ağaç taraması → V16
    "rglob": ("    dosyalar = paket_rules_dosyalari(kok)",
              '    dosyalar = sorted(kok.rglob(".rules.md"))'),
    # F7 KARDEŞ: rules_present kök yok dalı kalkar → V17 (naming kapısının kendi dalı ayrı)
    "presentkokyok": ("    if not erp_root.is_dir():\n", "    if False:\n", "present"),
}

# Batarya keşfinin BEYAN katmanı bu literali okur; `_kip_capasi()` eşliği ölçer.
GECERLI_KIP = {"--mutasyon-altkume", "--mutasyon-pkgnoz", "--mutasyon-kapsamsifir",
               "--mutasyon-sablonfailopen", "--mutasyon-istisna", "--mutasyon-gomulu",
               "--mutasyon-tipnorm", "--mutasyon-olculmedi", "--mutasyon-kokyok",
               "--mutasyon-rglob", "--mutasyon-presentkokyok"}


def _kip_capasi() -> None:
    beklenen = {"--mutasyon-" + k for k in MUTASYONLAR}
    if beklenen != GECERLI_KIP:
        print(f"[DURDU] kip beyanı ile MUTASYONLAR ayrıştı: yalnız-beyanda="
              f"{sorted(GECERLI_KIP - beklenen)} yalnız-sözlükte={sorted(beklenen - GECERLI_KIP)}",
              file=sys.stderr)
        sys.exit(2)


def gate_kaynagi(ad: str | None) -> tuple:
    """(kapı kaynağı, kardeş rules_present kaynağı) — mutasyon yalnız hedef dosyaya."""
    kaynak = {"gate": GATE.read_text(encoding="utf-8"),
              "present": PRESENT.read_text(encoding="utf-8")}
    if ad:
        capa, yeni, *hedef = MUTASYONLAR[ad]
        h = hedef[0] if hedef else "gate"
        if kaynak[h].count(capa) != 1:
            print(f"[DUR] mutasyon '{ad}' çapası {h} kaynağında {kaynak[h].count(capa)} kez "
                  f"geçiyor (1 olmalı) — sessiz no-op mutasyon sahte YEŞİL üretirdi.",
                  file=sys.stderr)
            sys.exit(3)
        kaynak[h] = kaynak[h].replace(capa, yeni)
    return kaynak["gate"], kaynak["present"]


_GORUNUR = None


def ozet_gorunur_mu(satir: str) -> bool:
    """GERÇEK `run_all_validators._gorunur_zorunlu_mu` (kopya süzgeç değil)."""
    global _GORUNUR
    if _GORUNUR is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_run_all_ozet", RUN_ALL)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        _GORUNUR = mod._gorunur_zorunlu_mu
    return bool(_GORUNUR(satir))


def main() -> int:
    _kip_capasi()
    mut = None
    for a in sys.argv[1:]:
        if not a.startswith("--mutasyon"):
            continue
        if a not in GECERLI_KIP:
            print(f"[KULLANIM] gecersiz mutasyon kipi: {a} — gecerli: "
                  f"{', '.join(sorted(GECERLI_KIP))}", file=sys.stderr)
            return 1
        mut = a[len("--mutasyon-"):]
    for f in (GATE, PRESENT, RUN_ALL, SABLON, BOOT):
        if not f.is_file():
            print(f"[DUR] bulunamadı: {f}", file=sys.stderr)
            return 3
    kaynak = gate_kaynagi(mut)

    gecen, dusen = 0, []
    for ad, kurucu, sroot, beklenen, olmali, olmamali, *sec in VEKTORLER:
        o = sec[0] if sec else {}
        tmp = Path(tempfile.mkdtemp(prefix="rulesnaming_"))
        try:
            proje, core = sandbox(tmp, kaynak, sroot)
            ek = kurucu(proje, core, tmp)
            gate = core / "scripts" / "validators" / (
                PRESENT.name if o.get("hedef") == "present" else GATE.name)
            r = subprocess.run([sys.executable, str(gate), *ek], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=env_for(proje),
                               cwd=str(proje))
            rc, cikti = r.returncode, (r.stdout or "") + (r.stderr or "")
            sorun = []
            if rc != beklenen:
                sorun.append(f"exit {rc} ≠ {beklenen}")
            sorun += [f"çıktıda YOK: {t!r}" for t in olmali if t not in cikti]
            sorun += [f"çıktıda OLMAMALIYDI: {t!r}" for t in olmamali if t in cikti]
            for t in o.get("ozet", []):
                satirlar = [s for s in cikti.splitlines() if t in s]
                if not satirlar or not all(ozet_gorunur_mu(s) for s in satirlar):
                    sorun.append(f"`run_all --ozet` süzgecinde GÖRÜNMEZ: {t!r}")
            if sorun:
                dusen.append((ad, "; ".join(sorun), cikti.strip()[:400]))
            else:
                gecen += 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print(f"rules_naming_standard — {gecen}/{len(VEKTORLER)}" + (f" [mutasyon: {mut}]" if mut else ""))
    for ad, sorun, cikti in dusen:
        print(f"  DÜŞTÜ: {ad}\n         {sorun}\n         çıktı: {cikti}")
    if mut:
        if not dusen:
            print("  [KORPUS ZAYIF] mutasyona rağmen tam puan — bu değişmez sınanmıyor!",
                  file=sys.stderr)
            return 1
        return 0
    return 0 if not dusen else 1


if __name__ == "__main__":
    raise SystemExit(main())
