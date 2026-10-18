# -*- coding: utf-8 -*-
"""rules_naming_standard — check_package_rules_naming_standard.py KALICI KORPUSU (11 vektör, 6 mutasyon).

Kapının iddiası İKİ YÖNLÜDÜR ve ikisi de kanıtlanır:
  (a) YAKALAMA : paket `.rules.md` naming tablosunda kanonik kümede olmayan DTEL/Domain öneki
      (asıl sınıf: eski şablonun `{PKG}_DE_*`/`{PKG}_DOM_*` satırını miras alan paket),
  (b) SESSİZLİK: şablonun alternatiflerinden birini seçen paket (ALT KÜME), `{PKG_NOZ}` yer
      tutuculu `Class` satırı, gerekçeli muafiyet, `_CLC` eki olmayan paket adı.
Ayrıca kapının KANONİK KAYNAĞI tektir (şablon): gömülü bir kopyaya dönülürse V10 düşer.

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
          -kapsamsifir / -sablonfailopen / -istisna / -gomulu)
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


def sandbox(tmp: Path, gate_kaynak: str, source_root: str = "SOURCE_CODES") -> tuple:
    proje, core = tmp / "proje", tmp / "core"
    (proje / source_root).mkdir(parents=True)
    (proje / "project.yaml").write_text(
        f"sap_profile: s4_private\nsource_root: {source_root}\n", encoding="utf-8")
    (core / "scripts" / "validators").mkdir(parents=True)
    (core / "scripts" / "validators" / GATE.name).write_text(gate_kaynak, encoding="utf-8")
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
     k_bootstrap_temiz, "SOURCE_CODES", 0, ["[OK] 1 paketin"], ["PREFIX-SAPMASI", "[BİLGİ]"]),
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
    "gomulu": ('    tablo = naming_satirlari(sablon.read_text(encoding="utf-8", errors="replace"))',
               '    tablo = {"Data Element": {"{PKG}_E_*"}, "Domain": {"{PKG}_D_*"},\n'
               '             "Class": {"ZCL_{PKG_NOZ}_*", "{PKG}_CL_*"}}'),
}

# Batarya keşfinin BEYAN katmanı bu literali okur; `_kip_capasi()` eşliği ölçer.
GECERLI_KIP = {"--mutasyon-altkume", "--mutasyon-pkgnoz", "--mutasyon-kapsamsifir",
               "--mutasyon-sablonfailopen", "--mutasyon-istisna", "--mutasyon-gomulu"}


def _kip_capasi() -> None:
    beklenen = {"--mutasyon-" + k for k in MUTASYONLAR}
    if beklenen != GECERLI_KIP:
        print(f"[DURDU] kip beyanı ile MUTASYONLAR ayrıştı: yalnız-beyanda="
              f"{sorted(GECERLI_KIP - beklenen)} yalnız-sözlükte={sorted(beklenen - GECERLI_KIP)}",
              file=sys.stderr)
        sys.exit(2)


def gate_kaynagi(ad: str | None) -> str:
    kaynak = GATE.read_text(encoding="utf-8")
    if not ad:
        return kaynak
    capa, yeni = MUTASYONLAR[ad]
    if kaynak.count(capa) != 1:
        print(f"[DUR] mutasyon '{ad}' çapası kaynakta {kaynak.count(capa)} kez geçiyor "
              f"(1 olmalı) — sessiz no-op mutasyon sahte YEŞİL üretirdi.", file=sys.stderr)
        sys.exit(3)
    return kaynak.replace(capa, yeni)


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
    for f in (GATE, SABLON, BOOT):
        if not f.is_file():
            print(f"[DUR] bulunamadı: {f}", file=sys.stderr)
            return 3
    kaynak = gate_kaynagi(mut)

    gecen, dusen = 0, []
    for ad, kurucu, sroot, beklenen, olmali, olmamali in VEKTORLER:
        tmp = Path(tempfile.mkdtemp(prefix="rulesnaming_"))
        try:
            proje, core = sandbox(tmp, kaynak, sroot)
            ek = kurucu(proje, core, tmp)
            gate = core / "scripts" / "validators" / GATE.name
            r = subprocess.run([sys.executable, str(gate), *ek], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=env_for(proje),
                               cwd=str(proje))
            rc, cikti = r.returncode, (r.stdout or "") + (r.stderr or "")
            sorun = []
            if rc != beklenen:
                sorun.append(f"exit {rc} ≠ {beklenen}")
            sorun += [f"çıktıda YOK: {t!r}" for t in olmali if t not in cikti]
            sorun += [f"çıktıda OLMAMALIYDI: {t!r}" for t in olmamali if t in cikti]
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
