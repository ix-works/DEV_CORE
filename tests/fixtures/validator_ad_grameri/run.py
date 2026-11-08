#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validator_ad_grameri fixture — DEV_CORE #402: TEK AD GRAMERİ geri dönüş koruması.

NEDEN VAR (2026-11-08)
  Validator'lar SAP nesne adını kaynak metinden KENDİ desenleriyle yakalıyordu (`(\\w+)`,
  `([a-z][a-z0-9_]*)`, `(Z[A-Z]{2,4}\\d{3}_C_\\w+)` …). `\\w` `/` eşlemediği için namespace'li ad
  (`/NSPC/…`) hiç yakalanmıyor, kontrol KOŞMADAN "kapsam dışı / OK" dönüyordu (#402). Düzeltme:
  ad sözdizimi + yakalama YALNIZ `scripts/utils/ad_politikasi.py`'de yaşar (`AD_ADAYI` gevşek
  yakalama · `AD_DESENI` katı geçerlilik · `NS_GOVDE`). Bu fixture yeni bir validator'ın (ya da
  eski bir satırın) kendi ad desenine GERİ DÖNMESİNİ yakalar. Gate DEĞİLDİR — testtir.

NE ÖLÇER (statik, AST)
  `scripts/validators/*.py` içindeki her `re.<fonk>(<desen>, …)` çağrısının desen argümanı
  (sabit parçalar + adla gömülen değişkenler) birleştirilir. Desen "NESNE ADI BAĞLAMINDA kendi
  ad sınıfını yakalıyor" sayılır ⇔ bir nesne anahtar sözcüğünden (define/table/structure/view/
  entity/class/report/from/join/behavior for/include/update/into/modify/delete/insert/type/
  function) sonra 0-40 karakter içinde YAKALAYAN grup açılır ve grubun içeriği bir ad sınıfıdır
  (`\\w+`, `[A-Za-z0-9_/…]+`, `Z…`, `[ZY]…`). `ad_politikasi`'ndan gelen parça (`AD_ADAYI`,
  `AD_DESENI`, `NS_GOVDE`) içeren desen gramere BAĞLIDIR.

İZİN LİSTESİ — KODDAN TÜRETİLİR (elle tutulan liste YOK; #397 U8 dersi)
  Bilinçli istisna, desenin bulunduğu satırda ya da hemen üstündeki 3 satırda
  `# ad-grameri: <gerekçe>` işaretiyle BEYAN edilir. Gerekçesiz işaret (boş) kabul EDİLMEZ.
  Fixture işaretleri sayar ve listeler (KAPSAM BEYANI) — istisna görünür kalır.

VEKTÖRLER
  G1  yeni ağaç: gramere bağlı olmayan, işaretsiz nesne-adı deseni SAYISI = 0
  G2  her işaret gerekçe taşır (boş `# ad-grameri:` yok)
  G3  dedektör KONTROLÜ — bilinen kötü desen örnekleri YAKALANIR (`define table (\\w+)` ·
      `from\\s+([a-z][a-z0-9_]*)` · `(Z[A-Z]{2,4}\\d{3}_C_\\w+)` · `behavior for ([\\w/]+)`)
  G4  dedektör KONTROLÜ — gramere bağlı / bağlam dışı örnekler YAKALANMAZ (`(' + AD_ADAYI + ')`
      · `alias\\s+(\\w+)` · `adtcore:version="(\\w+)"` · `METHODS\\s+(\\w+)`)
  G5  envanter boş DEĞİL: taranan validator ≥ 40, toplanan desen ≥ 200 (dedektör kör değil)
  G6  bağlı (gramerden gelen) desen sayısı ≥ 15 (bağlama gerçekten yapıldı)

KULLANIM
  python tests/fixtures/validator_ad_grameri/run.py                 # vektörler
  python tests/fixtures/validator_ad_grameri/run.py --listele       # bulunan/işaretli tüm desenler
  python tests/fixtures/validator_ad_grameri/run.py --kok <repo>    # başka ağaç (taban ölçümü)
  python tests/fixtures/validator_ad_grameri/run.py --mutasyon-<ad> # tek mutasyon (KIPLER)
  Mutasyon çıkışı: 1 = ilan edilen küme TAM düştü · 2 = SAPMA · 3 = kurulamadı.
"""
from __future__ import annotations

import ast
import re
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

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]

RE_FONK = {"compile", "search", "match", "fullmatch", "findall", "finditer", "sub", "subn", "split"}
GRAMER_ADLARI = ("AD_ADAYI", "AD_DESENI", "NS_GOVDE")
ISARET = re.compile(r"#\s*ad-grameri:\s*(.*)$")

# Nesne anahtar sözcüğü (regex KAYNAĞINDA, `\b` / `\s+` kaçışlarıyla birlikte yazılı hâliyle)
# Sözcük sınırı KAYNAK METNİNDE: önünde harf yok (ya da `\b` kaçışı), arkasında harf/`-` yok ⇒
# `CLASS-METHODS` / `TYPES` / `DATA` anahtar sözcük SAYILMAZ (yerel tanımlayıcı bağlamı).
_KW = (r"(?:(?<=\\b)|(?<![A-Za-z]))"
       r"(?i:define|table|structure|entity|view|class|report|program|from|join|behavior\\s\+for|"
       r"include|update|into|modify|delete|insert|type|function)(?![A-Za-z\-])")
# Ad sınıfı (grubun TÜM içeriği): \w+ · [..]+ / [..]* / [..]{n,} (harf/rakam/_/ / sınıfı) ·
# Z/Y önekli kalıplar
_SINIF = (r"(?:/\?)?(?:\[[A-Za-z]-[A-Za-z](?:[^\]]*)\]|\[ZY\]|Z|\\w)?"
          r"(?:\\w[+*]|\\w\{[^}]*\}|\[(?:\\w|[A-Za-z0-9_\-/\\.])+\](?:[+*]|\{[^}]*\}))"
          r"(?:[^()]*)")
DEDEKTOR = re.compile(_KW + r".{0,40}?\((?!\?)" + _SINIF + r"\)")


def desenler(kaynak: str):
    """(satır_no, birleşik_desen) — `re.<fonk>(…)` çağrılarının desen argümanı."""
    agac = ast.parse(kaynak)
    for d in ast.walk(agac):
        if not isinstance(d, ast.Call) or not d.args:
            continue
        f = d.func
        if not (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                and f.value.id == "re" and f.attr in RE_FONK):
            continue
        parcalar = []
        for alt in ast.walk(d.args[0]):
            if isinstance(alt, ast.Constant) and isinstance(alt.value, str):
                parcalar.append(alt.value)
            elif isinstance(alt, ast.Name):
                parcalar.append("{" + alt.id + "}")
            elif isinstance(alt, ast.Attribute):
                parcalar.append("{" + alt.attr + "}")
        yield d.lineno, "".join(parcalar)


def sinifla(desen: str) -> str:
    """'bagli' (gramerden) · 'ihlal' (kendi ad deseni, nesne bağlamı) · 'notr'."""
    if any("{" + g + "}" in desen for g in GRAMER_ADLARI):
        return "bagli"
    return "ihlal" if DEDEKTOR.search(desen) else "notr"


def isaret(satirlar: list[str], no: int) -> str | None:
    """Desen satırında ya da üstündeki 3 satırda `# ad-grameri: …` ⇒ gerekçe (boş olabilir)."""
    for i in range(no - 1, max(no - 5, -1), -1):
        if 0 <= i < len(satirlar):
            m = ISARET.search(satirlar[i])
            if m:
                return m.group(1).strip()
    return None


def tara(kok: Path):
    val = kok / "scripts" / "validators"
    dosyalar = sorted(val.glob("*.py"))
    kayit = []          # (dosya, satır, sınıf, işaret, desen)
    for p in dosyalar:
        metin = p.read_text(encoding="utf-8")
        satirlar = metin.splitlines()
        for no, d in desenler(metin):
            s = sinifla(d)
            kayit.append((p.name, no, s, isaret(satirlar, no) if s == "ihlal" else None, d))
    return dosyalar, kayit


S: list[tuple[str, bool, str]] = []


def ekle(ad: str, ok: bool, ayrinti: str = "") -> None:
    S.append((ad, ok, ayrinti))


def main(kok: Path, listele: bool) -> int:
    dosyalar, kayit = tara(kok)
    ihlal = [k for k in kayit if k[2] == "ihlal" and k[3] is None]
    isaretli = [k for k in kayit if k[2] == "ihlal" and k[3] is not None]
    bagli = [k for k in kayit if k[2] == "bagli"]
    ekle("G1", not ihlal, "işaretsiz kendi-ad-deseni: "
         + "; ".join(f"{f}:{n} {d[:90]!r}" for f, n, _, _, d in ihlal[:12]))
    bos = [k for k in isaretli if not k[3]]
    ekle("G2", not bos, "; ".join(f"{f}:{n}" for f, n, *_ in bos))
    kotu = [r"define\s+table\s+(\w+)", r"\b(?:from|join)\s+([a-z][a-z0-9_]*)",
            r"\b(?:join|from)\s+(Z[A-Z]{2,4}\d{3}_C_\w+)", r"define\s+behavior\s+for\s+([\w/]+)",
            r"^\s*define\s+(table|structure|type)\s+([A-Za-z_/][A-Za-z0-9_/]*)",
            r"\bclass\s+(\w+)\s+definition"]
    kacan = [k for k in kotu if sinifla(k) != "ihlal"]
    ekle("G3", not kacan, f"dedektörün KAÇIRDIĞI kötü örnekler: {kacan}")
    iyi = [r"define\s+table\s+({AD_ADAYI})", r"\s+alias\s+(\w+)", r'adtcore:version="(\w+)"',
           r"^\s*(?:CLASS-)?METHODS\s+(\w+)(.*)$", r"masterLanguage=\"(\w+)\""]
    yanlis = [k for k in iyi if sinifla(k) == "ihlal"]
    ekle("G4", not yanlis, f"dedektörün YANLIŞ yakaladığı örnekler: {yanlis}")
    ekle("G5", len(dosyalar) >= 40 and len(kayit) >= 200,
         f"taranan dosya={len(dosyalar)} desen={len(kayit)}")
    ekle("G6", len(bagli) >= 15, f"gramere bağlı desen={len(bagli)}")
    # KAPSAM BEYANI — koddan türetilir, her koşumda basılır
    print(f"KAPSAM: {len(dosyalar)} validator · {len(kayit)} re-çağrısı deseni · "
          f"gramere bağlı {len(bagli)} · işaretli istisna {len(isaretli)} · işaretsiz ihlal {len(ihlal)}")
    print("BAKILMAYAN: re.* dışındaki eşleme (str.startswith/split/fnmatch), desenin çalışma "
          "zamanı birleştirilen parçaları (yalnız sabit + ad), scripts/validators dışı dosyalar.")
    if listele:
        for f, n, s, i, d in kayit:
            if s != "notr":
                print(f"  {s:6} {f}:{n}" + (f"  [işaret: {i}]" if i is not None else "") + f"  {d[:110]!r}")
        for f, n, s, i, d in isaretli:
            pass
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    return 0 if n == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYON — kontrol grubu: bir validator'a ESKİ deseni geri koymak G1'i düşürmeli;
# dedektörün kendisini köreltmek G3'ü düşürmeli.
# ─────────────────────────────────────────────────────────────────────────────
_V = "scripts/validators/"
MUTASYONLAR = {
    "--mutasyon-reuse-eski-desen": (
        _V + "check_reuse_gate.py",
        "r'\\bdefine\\s+(?:root\\s+)?view\\s+entity\\s+(' + AD_ADAYI + r')', re.IGNORECASE)",
        "r'\\bdefine\\s+(?:root\\s+)?view\\s+entity\\s+(\\w+)', re.IGNORECASE)",
        {"G1"}),
    "--mutasyon-tablo-eski-desen": (
        _V + "check_table_field_drop.py",
        "TABLE_NAME_RE = re.compile(r'define\\s+table\\s+(?!function\\b)(' + AD_ADAYI + r')', re.IGNORECASE)",
        "TABLE_NAME_RE = re.compile(r'define\\s+table\\s+([a-z][a-z0-9_]*)', re.IGNORECASE)",
        {"G1"}),
    "--mutasyon-dedektor-kor": (
        "tests/fixtures/validator_ad_grameri/run.py",
        'DEDEKTOR = re.compile(_KW + r".{0,40}?\\((?!\\?)" + _SINIF + r"\\)")',
        'DEDEKTOR = re.compile(r"(?!x)x")',
        {"G3"}),
}
KIPLER = sorted(MUTASYONLAR)


def _mutasyon(kip: str) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kum = Path(tempfile.mkdtemp(prefix="vag_kum_"))
    try:
        shutil.copytree(REPO / "scripts" / "validators", kum / "scripts" / "validators",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hedef = kum / "tests" / "fixtures" / BURASI.name
        shutil.copytree(BURASI, hedef, ignore=shutil.ignore_patterns("__pycache__"))
        dosya = kum / yol
        asil = dosya.read_bytes().decode("utf-8")
        if asil.count(eski) != 1:
            print(f"[KURULAMADI] {kip} -> capa {asil.count(eski)} kez ({yol})")
            return 3
        mutant = asil.replace(eski, yeni, 1)
        try:
            compile(mutant, str(dosya), "exec")
        except SyntaxError as exc:
            print(f"[KURULAMADI] {kip} -> mutant derlenmedi: {exc}")
            return 3
        dosya.write_bytes(mutant.encode("utf-8"))
        r = subprocess.run([sys.executable, str(hedef / "run.py"), "--kok", str(kum)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=300, cwd=str(kum))
        m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
        if not m:
            son = [x for x in (r.stdout + r.stderr).splitlines() if x.strip()][-1:] or ["-"]
            print(f"[ALT-SUREC SAYI VERMEDI] {kip} rc={r.returncode} son={son[0][:160]}")
            return 3
        dusen = {x.split()[1] for x in r.stdout.splitlines() if x.strip().startswith("[FAIL]")}
        print(f"{kip}: {m.group(0)} · dusen={sorted(dusen)} · ilan={sorted(beklenen)}")
        if dusen == beklenen:
            print("MUTASYON DUSTU (ilan edilen kume TAM)")
            return 1
        print(f"[SAPMA] fazla={sorted(dusen - beklenen)} eksik={sorted(beklenen - dusen)}")
        return 2
    finally:
        shutil.rmtree(kum, ignore_errors=True)


if __name__ == "__main__":
    _kipler = [a for a in sys.argv[1:] if a.startswith("--mutasyon")]
    if _kipler:
        if len(_kipler) != 1 or _kipler[0] not in MUTASYONLAR:
            print(f"[KULLANIM] gecerli kipler: {KIPLER}")
            sys.exit(2)
        sys.exit(_mutasyon(_kipler[0]))
    _kok = REPO
    if "--kok" in sys.argv:
        _kok = Path(sys.argv[sys.argv.index("--kok") + 1]).resolve()
    sys.exit(main(_kok, "--listele" in sys.argv))
