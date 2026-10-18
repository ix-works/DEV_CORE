#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""frontmatter_lint — tanım dosyası frontmatter kapısı (modül + core_precommit + ix_doctor 4g).

NEDEN VAR (ölçüldü 2026-10-18, çekirdek PR #347): dört ajan tanımının tırnaksız
`description:` değerinde `: ` vardı. Claude Code LF dosyada tolere etti, CRLF dosyada
(Windows checkout) ajanı UYARISIZ düşürdü (7 ajandan 3'ü listelendi). Linux CI'da dosyalar
LF olduğu için hiçbir katman görmedi. Kapı: `scripts/utils/frontmatter_lint.py` (tek kaynak)
+ `core_precommit` 6. kontrol (ENGEL → exit 1) + `ix_doctor` 4g (WARN, kaynak ayrımı).

BÖLÜMLER (her modül vektörü 4 kipte: {LF, CRLF} × {PyYAML açık, PyYAML engelli}):
  N1..N15  ENGEL beklenen (satır + seviye + anahtar sözcük birebir)
  U1..U4   UYARI sınıfı (`*`/`&` ile başlayan tırnaksız değer — lider kararı B) + nötrleme
  P1..P12  yanlış-pozitif sınaması: bulgu YOK
  PAR      düzey 1 ↔ PyYAML eşliği (her vektör için PyYAML'ın kabul/ret kararı beyan edilir)
  R1/R2    gerçek ağaç (16 tanım dosyası) + tarihî bozuk sürüm (a5e3c4a^ → bulgu, a5e3c4a → 0)
  C0..C7   core_precommit GERÇEK giriş noktası (geçici git reposu, `core.autocrlf=false`
           — CRLF blob gerçekten CRLF kalır); C0 = eski kapı (3d22d7b) vakayı GEÇİRİRDİ
  D1..D8   ix_doctor `_frontmatter_kontrol` + `katman4()` kablolaması (geçici proje kökü)

MUTASYON (çapa tam 1 kez bulunmazsa exit 2; düşen küme ILAN ile birebir değilse SAPMA → exit 2):
  --mutasyon-iki-nokta          `: ` tespiti kalkar        → N1 · N15 · U2 · R2 · C6
                                (yaml kipinde de düşerler: bulgu PyYAML'a kayar, sınıf adı değişir)
  --mutasyon-kirpma             ` #` tespiti kalkar        → N2
  --mutasyon-yildiz-engel       `*`/`&` UYARI → ENGEL       → U1..U4 · C4 · D5
  --mutasyon-notrleme-yok       UYARI satırı düzey 2'ye ham → U1[yaml] · U3[yaml] · C4 · D5 (PyYAML yoksa exit 2)
  --mutasyon-onek-yok           precommit `claude/` öneki   → C5 · C7 (modülsüz kumda normal.md)
  --mutasyon-cekirdek-ayrimi-yok ix_doctor kaynak ayrımı    → D2 · D3
⛔ Gerçek kaynağa YAZILMAZ: mutant modül bellekte derlenir; precommit geçici kum kopyasından koşar.
Çıkış: 0 beklendiği gibi · 1 sapma (kipte: ilan edilen küme düştü) · 2 KURULAMADI/SAPMA
"""
from __future__ import annotations

import re
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MODUL = REPO / "scripts" / "utils" / "frontmatter_lint.py"
PRECOMMIT = REPO / "scripts" / "git-hooks" / "core_precommit.py"
DOCTOR = REPO / "scripts" / "ix_doctor.py"
ESKI_KAPI_SHA = "3d22d7b"          # dal başlangıcı: 6. kontrol YOK (kontrol grubu C0)
VAKA_SHA = "a5e3c4a"               # PR #347: `a5e3c4a^` bozuk, `a5e3c4a` düzeltilmiş
VAKA_AJANLAR = {"backend-expert": 5, "frontend-expert": 5, "infra-expert": 6, "sap-feature": 5}
BLOKLISTE = "QQQ_HIC_ESLESMEZ_9"

GECERLI_KIP = ("--mutasyon-iki-nokta", "--mutasyon-kirpma", "--mutasyon-yildiz-engel",
               "--mutasyon-notrleme-yok", "--mutasyon-onek-yok", "--mutasyon-cekirdek-ayrimi-yok")
KIP: str | None = None
for _a in sys.argv[1:]:
    if _a in GECERLI_KIP and KIP is None:
        KIP = _a
    else:
        print(f"[DURDU] bilinmeyen/ikinci arguman: {_a!r} — gecerli: {list(GECERLI_KIP)}")
        sys.exit(2)

try:
    import yaml  # noqa: F401
    YAML_VAR = True
except Exception:  # noqa: BLE001
    YAML_VAR = False

ILAN: dict[str, list[str]] = {
    "--mutasyon-iki-nokta": ["N1 *", "N15 *", "U2 *", "R2 *", "C6 *"],
    "--mutasyon-kirpma": ["N2 *"],
    "--mutasyon-yildiz-engel": ["U1 *", "U2 *", "U3 *", "U4 *", "C4 *", "D5 *"],
    "--mutasyon-notrleme-yok": ["U1 * [yaml]", "U3 * [yaml]", "C4 *", "D5 *"],
    "--mutasyon-onek-yok": ["C5 *", "C7 *"],
    "--mutasyon-cekirdek-ayrimi-yok": ["D2 *", "D3 *"],
}

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if not kosul and detay else ""))


def _degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    n = metin.count(eski)
    if n != 1:
        print(f"[DURDU] KURULAMADI: {ad} capasi {n} kez bulundu (1 bekleniyordu): {eski[:70]!r}")
        sys.exit(2)
    return metin.replace(eski, yeni)


# ── kaynaklar (mutant ya da gerçek) ─────────────────────────────────────────────
def modul_kaynagi() -> str:
    m = MODUL.read_text(encoding="utf-8")
    if KIP == "--mutasyon-iki-nokta":
        m = _degistir(m, '    if ": " in deger or deger.endswith(":"):\n',
                      "    if False:\n", "iki-nokta")
    elif KIP == "--mutasyon-kirpma":
        m = _degistir(m, '    if " #" in deger or "\\t#" in deger:\n', "    if False:\n", "kirpma")
    elif KIP == "--mutasyon-yildiz-engel":
        m = _degistir(m, "out.append(Bulgu(no, UYARI, f\"'{anahtar}': \" + _UYARI_YILDIZ",
                      "out.append(Bulgu(no, ENGEL, f\"'{anahtar}': \" + _UYARI_YILDIZ", "yildiz")
    elif KIP == "--mutasyon-notrleme-yok":
        if not YAML_VAR:
            print("[DURDU] KURULAMADI: bu kip duzey 2'yi (PyYAML) olcer; PyYAML kurulu degil")
            sys.exit(2)
        m = _degistir(m, "            notrle[i] = _cift_tirnakla(anahtar, deger)\n",
                      "            pass\n", "notrleme")
    return m


def precommit_kaynagi() -> str:
    m = PRECOMMIT.read_text(encoding="utf-8")
    if KIP == "--mutasyon-onek-yok":
        m = _degistir(m, "    if not path.startswith(FM_ONEK):\n        return\n", "", "onek")
    return m


def doctor_kaynagi() -> str:
    m = DOCTOR.read_text(encoding="utf-8")
    if KIP == "--mutasyon-cekirdek-ayrimi-yok":
        bas = "def _frontmatter_kaynagi(f: Path, metin: str) -> tuple[bool, str]:\n"
        m = _degistir(m, bas, bas + '    return False, "PROJE dosyası"\n', "cekirdek-ayrimi")
    return m


_YOK = object()


def modul_yukle(kaynak: str, yaml_acik: bool, ad: str) -> types.ModuleType:
    eski = sys.modules.get("yaml", _YOK)
    if not yaml_acik:
        sys.modules["yaml"] = None  # type: ignore[assignment]  # import yaml → ImportError
    try:
        mod = types.ModuleType(ad)
        mod.__file__ = str(MODUL)
        sys.modules[ad] = mod                 # NamedTuple/annotations modül adını çözebilsin
        exec(compile(kaynak, str(MODUL), "exec"), mod.__dict__)
    finally:
        if eski is _YOK:
            sys.modules.pop("yaml", None)
        else:
            sys.modules["yaml"] = eski        # type: ignore[assignment]
    return mod


# ── kum yardımcıları ────────────────────────────────────────────────────────────
_KUMLAR: list[Path] = []
_BAGLAR: list[Path] = []


def _sil(d: Path) -> None:
    def _ac(func, path, _exc):                       # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)                       # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def _kum(on: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix=f"fmlint_{on}_"))
    _KUMLAR.append(d)
    return d


def _bag(hedef: Path, bag: Path) -> None:
    """Dizin bağı: Windows'ta junction, POSIX'te symlink (kurulum çekirdekle aynı şekil)."""
    bag.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        import _winapi  # type: ignore
        _winapi.CreateJunction(str(hedef), str(bag))
    else:
        os.symlink(str(hedef), str(bag), target_is_directory=True)
    _BAGLAR.append(bag)


def _yaz(p: Path, metin: str, crlf: bool = False) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    veri = metin.replace("\n", "\r\n") if crlf else metin
    p.write_bytes(veri.encode("utf-8"))              # bayt olarak: satır sonu ÇEVRİLMEZ


def FM(*satirlar: str) -> str:
    return "---\n" + "\n".join(satirlar) + "\n---\n\n# govde\n"


# ── A. MODÜL VEKTÖRLERİ ─────────────────────────────────────────────────────────
E, U = "ENGEL", "UYARI"
ESKI_SAP_FEATURE = FM(
    "name: sap-feature", "model: sonnet", "effort: high",
    "description: SAP özellik geliştirme ajanı (modül/uygulama sahibi). Tasarım yapar + YEREL "
    "kaynak hazırlar + read-only SAP analizi yapar. SAP'ye YAZAMAZ (push/activate/create/delete/"
    "post_shell araçları YOK) — tüm yazım adt_gateway'e devredilir. Single-writer enforcement: bu "
    "rol tool-düzeyinde yazma yetkisinden yoksundur.",
    "tools: Read, Edit, Write, Grep, Glob, Bash, Skill")

# (ad, metin, zorunlu, beklenen[yaml], beklenen[noyaml] | None=aynı, PyYAML ham FM'yi REDDEDER mi | None)
VEKTORLER: list[tuple] = [
    ("N1 vaka: tirnaksiz deger icinde ': '", FM("name: x", "description: NE ZAMAN — a: b"),
     True, [(3, E, "': '")], None, True),
    ("N2 ' #' sessiz kirpma", FM("name: x", "description: bkz issue #17204"),
     True, [(3, E, "' #'")], None, False),
    ("N3 '#' ile baslayan deger", FM("name: x", "description: #etiket"),
     True, [(3, E, "'#' ile")], None, False),
    ("N4 kapanmayan cift tirnak", FM("name: x", 'description: "acik kaldi'),
     True, [(3, E, "KAPANMIYOR")], None, True),
    ("N4b kapanmayan tek tirnak", FM("name: x", "description: 'acik"),
     True, [(3, E, "KAPANMIYOR")], None, True),
    ("N5 frontmatter yok (ajan)", "# baslik\n\nmetin\n", True, [(1, E, "frontmatter YOK")], None, None),
    ("N6 frontmatter kapanmiyor", "---\nname: x\ndescription: y\n\n# govde\n",
     True, [(1, E, "KAPANMIYOR")], None, None),
    ("N7 deger icinde '---'", FM("name: x", "description: a --- b"),
     True, [(3, E, "'---'")], None, False),
    ("N8 cift tirnakta gecersiz kacis", FM("name: x", 'description: "a\\qb"'),
     True, [(3, E, "kacis")], None, True),
    ("N9 kapanan tirnaktan sonra metin", FM("name: x", 'description: "a" b'),
     True, [(3, E, "SONRA")], None, True),
    ("N10 ayrilmis karakter '@'", FM("name: x", "description: @kullanici"),
     True, [(3, E, "ayrilmis")], None, True),
    ("N11 devam satirinda ': '", FM("name: x", "description: birinci", "  ikinci: ucuncu"),
     True, [(4, E, "devam")], None, True),
    ("N12 anahtarsiz duz satir", FM("name: x", "duz metin satiri"),
     True, [(3, E, "biciminde degil")], None, True),
    ("N13 liste ogesi '*' ile basliyor", FM("paths:", "  - **/*.abap"),
     False, [(3, E, "liste ogesi")], None, True),
    ("N14 kapanmayan akis listesi (yalniz duzey 2)", FM("name: x", "tools: [Read, Grep"),
     True, [(3, E, "PyYAML")], [], True),
    ("N15 tarihi vaka (sap-feature a5e3c4a^, gomulu)", ESKI_SAP_FEATURE,
     True, [(5, E, "': '")], None, True),
    ("U1 bugunku paths bicimi", FM("paths: **/*.abap, **/*.ddls"),
     False, [(2, U, "CRLF")], None, True),
    ("U2 UYARI + baska satirda ': '", FM("paths: **/*.abap", "description: a: b"),
     False, [(2, U, "CRLF"), (3, E, "': '")], None, True),
    ("U3 UYARI + yalniz duzey-2 hatasi (notrleme)", FM("paths: **/*.abap", "tools: [a, b"),
     False, [(2, U, "CRLF"), (3, E, "PyYAML")], [(2, U, "CRLF")], True),
    ("U4 '&' ile baslayan deger", FM("name: x", "description: &capa metin"),
     True, [(3, U, "'&'")], None, False),
    ("P1 cift tirnakli deger ': ' ve '#' tasir", FM("name: x", 'description: "NE ZAMAN: a # b"'),
     True, [], None, False),
    ("P1b tek tirnakli deger", FM("name: x", "description: 'a: b ''x'''"), True, [], None, False),
    ("P2 akis listesi", FM("name: x", "description: y", "tools: [Read, Grep, SendMessage]"),
     True, [], None, False),
    ("P3 paths blok listesi tirnakli", FM("paths:", '  - "**/*.abap"', '  - "src/**"'),
     False, [], None, False),
    ("P4 blok skaler |", FM("name: x", "description: |", "  satir: bir # degil", "  iki"),
     True, [], None, False),
    ("P4b blok skaler >-", FM("name: x", "description: >-", "  a: b", "  c"), True, [], None, False),
    ("P5 frontmatter'siz komut dosyasi", "# Komut\n\nAdimlar: bir\n", False, [], None, None),
    ("P6 guvenli duz degerler", FM("a: a#b", "b: http://x/y", "c: a, b", "d: -a", "e: =x",
                                   "f: x - y"), False, [], None, False),
    ("P7 kacisli tirnaklar", FM("name: x", 'description: "a \\"b\\" c\\\\d \\u00e7"'),
     True, [], None, False),
    ("P8 cok satirli cift tirnak", FM("name: x", 'description: "bir', '  iki: uc"'),
     True, [], None, False),
    ("P9 frontmatter icinde yorum satiri", FM("# yorum satiri", "name: x", "description: y"),
     True, [], None, False),
    ("P10 BOM + gecerli frontmatter", "﻿" + FM("name: x", "description: y"),
     True, [], None, None),
    ("P11 ic ice harita", FM("name: x", "metadata:", "  type: feedback", "  seed: evet"),
     True, [], None, False),
    ("P12 bos deger + skaler", FM("name: x", "model:", "effort: high"), True, [], None, False),
]


def _ozet(bl) -> list[tuple]:
    return [(b.satir, b.seviye) for b in bl]


def modul_bolumu() -> None:
    print("\n== A. MODUL VEKTORLERI ==")
    kaynak = modul_kaynagi()
    kipler = [("yaml", True), ("noyaml", False)] if YAML_VAR else [("noyaml", False)]
    if not YAML_VAR:
        print("  [ATLANDI] [yaml] kipleri — PyYAML kurulu degil (duzey 2 OLCULEMEDI)")
    for kip_ad, acik in kipler:
        L = modul_yukle(kaynak, acik, f"_fml_{kip_ad}")
        kontrol(f"A0 duzey-2 bayragi [{kip_ad}]", L.YAML_TAM == acik, f"YAML_TAM={L.YAML_TAM}")
        for ad, metin, zorunlu, bek, bek_noyaml, _py in VEKTORLER:
            beklenen = bek if (acik or bek_noyaml is None) else bek_noyaml
            for son in ("LF", "CRLF"):
                girdi = metin.replace("\n", "\r\n") if son == "CRLF" else metin
                bl = L.bulgular(girdi, zorunlu)
                ok = (len(bl) == len(beklenen) and all(
                    b.satir == s and b.seviye == sv and k in b.sorun
                    for b, (s, sv, k) in zip(bl, beklenen)))
                kontrol(f"{ad} [{son}] [{kip_ad}]", ok,
                        f"beklenen={beklenen} gelen={[(b.satir, b.seviye, b.sorun[:50]) for b in bl]}")

    # PAR — düzey 1'in ENGEL dediği ham frontmatter'ı PyYAML da reddediyor mu (ve tersi)?
    if YAML_VAR:
        import yaml as _y
        for ad, metin, _z, _b, _bn, py in VEKTORLER:
            if py is None:
                continue
            satir = metin.split("\n")
            kap = satir.index("---", 1)
            try:
                _y.safe_load("\n".join(satir[1:kap]))
                red = False
            except Exception:  # noqa: BLE001
                red = True
            kontrol(f"PAR {ad.split(' ')[0]} PyYAML reddi={py}", red == py, f"PyYAML red={red}")


# ── R. GERÇEK AĞAÇ + TARİHÎ VAKA ────────────────────────────────────────────────
def _git_show(ref: str, yol: str) -> str | None:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{yol}"], capture_output=True)
    return r.stdout.decode("utf-8", errors="replace") if r.returncode == 0 else None


def agac_bolumu() -> None:
    print("\n== R. GERCEK AGAC + TARIHI VAKA ==")
    kaynak = modul_kaynagi()
    kipler = [("yaml", True), ("noyaml", False)] if YAML_VAR else [("noyaml", False)]
    dosyalar = sorted([*REPO.glob("claude/agents/*.md"), *REPO.glob("claude/commands/*.md"),
                       *REPO.glob("claude/skills/*/SKILL.md"), *REPO.glob("claude/rules/*.md")])
    for kip_ad, acik in kipler:
        L = modul_yukle(kaynak, acik, f"_fmr_{kip_ad}")
        engel, uyari = [], []
        for f in dosyalar:
            with open(f, encoding="utf-8", newline="") as fh:
                bl = L.dosya_bulgulari(f.relative_to(REPO).as_posix(), fh.read())
            for b in bl or []:
                (engel if b.seviye == E else uyari).append(f"{f.relative_to(REPO).as_posix()}:{b.satir}")
        kontrol(f"R1 gercek agac {len(dosyalar)} tanim: ENGEL 0, UYARI 0 (rules tirnakli) [{kip_ad}]",
                len(dosyalar) >= 16 and not engel and not uyari,
                f"n={len(dosyalar)} engel={engel} uyari={uyari}")
        for ajan, satir_no in VAKA_AJANLAR.items():
            eski = _git_show(f"{VAKA_SHA}^", f"claude/agents/{ajan}.md")
            yeni = _git_show(VAKA_SHA, f"claude/agents/{ajan}.md")
            if eski is None or yeni is None:
                print(f"  [ATLANDI] R2 {ajan} [{kip_ad}] — tarihce yok (sig klon?)")
                continue
            be = L.bulgular(eski, True)
            by = L.bulgular(yeni, True)
            kontrol(f"R2 tarihi {VAKA_SHA}^ {ajan} bulgu, {VAKA_SHA} temiz [{kip_ad}]",
                    any(b.satir == satir_no and b.seviye == E and "': '" in b.sorun for b in be)
                    and by == [], f"eski={_ozet(be)} yeni={_ozet(by)}")


# ── C. core_precommit (gerçek giriş noktası) ────────────────────────────────────
BOZUK_AJAN = FM("name: kotu", "description: NE ZAMAN — a: b")
DUZ_AJAN = FM("name: kotu", "description: NE ZAMAN — a ve b")
KURAL_UYARI = FM("paths: **/*.abap") + "kural govdesi\n"


def _kum_scripts(precommit_src: str, modul_src: str) -> Path:
    k = _kum("pc")
    (k / "scripts" / "git-hooks").mkdir(parents=True)
    (k / "scripts" / "utils").mkdir(parents=True)
    (k / "scripts" / "git-hooks" / "core_precommit.py").write_text(precommit_src, encoding="utf-8")
    shutil.copyfile(REPO / "scripts" / "genericize_common.py", k / "scripts" / "genericize_common.py")
    shutil.copyfile(REPO / "scripts" / "utils" / "__init__.py", k / "scripts" / "utils" / "__init__.py")
    (k / "scripts" / "utils" / "frontmatter_lint.py").write_text(modul_src, encoding="utf-8")
    return k / "scripts" / "git-hooks" / "core_precommit.py"


def _repo() -> Path:
    d = _kum("repo")
    for args in (["init", "-q", "."], ["config", "user.email", "t@example.com"],
                 ["config", "user.name", "t"], ["config", "core.autocrlf", "false"]):
        subprocess.run(["git", *args], cwd=d, check=True, capture_output=True)
    (d / "normal.md").write_text("# normal\n", encoding="utf-8")
    return d


def _git(d: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=d, check=True, capture_output=True)


def _pc(gate: Path, d: Path, *args: str, yaml_engelli: bool = False,
        changelog_kacis: bool = False) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items()
           if k != "CLAUDE_PROJECT_DIR" and not k.startswith("IX_") and k != "PYTHONPATH"}
    env["IX_GENERICIZE_BLOCKLIST"] = BLOKLISTE
    if changelog_kacis:
        env["IX_NO_CHANGELOG"] = "1"
    if yaml_engelli:
        stub = _kum("stub")
        (stub / "yaml.py").write_text("raise ImportError('fixture: PyYAML engellendi')\n",
                                      encoding="utf-8")
        env["PYTHONPATH"] = str(stub)
    p = subprocess.run([sys.executable, str(gate), *args], cwd=d, env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def precommit_bolumu() -> None:
    print("\n== C. core_precommit ==")
    gate = _kum_scripts(precommit_kaynagi(), modul_kaynagi())
    satir = "FRONTMATTER-GECERSIZ  claude/agents/kotu.md:3"

    # C0 — kontrol grubu: eski kapı (6. kontrol öncesi) bozuk CRLF ajanı GEÇİRİRDİ.
    eski_src = _git_show(ESKI_KAPI_SHA, "scripts/git-hooks/core_precommit.py")
    if eski_src is None:
        print(f"  [ATLANDI] C0 eski kapi ({ESKI_KAPI_SHA}) — tarihce yok (sig klon?)")
    else:
        eski_gate = _kum_scripts(eski_src, modul_kaynagi())
        d = _repo()
        _yaz(d / "claude" / "agents" / "kotu.md", BOZUK_AJAN, crlf=True)
        _git(d, "add", "-A")
        rc, out = _pc(eski_gate, d)
        kontrol("C0 eski kapi bozuk CRLF ajani GECIRIRDI (vaka: hicbir katman gormedi)",
                rc == 0 and "frontmatter" not in out, f"rc={rc}")

    d = _repo()
    _yaz(d / "claude" / "agents" / "kotu.md", BOZUK_AJAN, crlf=True)
    _git(d, "add", "-A")
    rc, out = _pc(gate, d)
    kontrol("C1 staged bozuk CRLF ajan → exit 1 + ihlal satiri", rc == 1 and satir in out,
            f"rc={rc} cikti={out[-300:]!r}")
    _yaz(d / "claude" / "agents" / "kotu.md", DUZ_AJAN, crlf=True)
    _git(d, "add", "-A")
    rc2, out2 = _pc(gate, d)
    kontrol("C2 ayni ajan duzeltilince → exit 0", rc2 == 0 and "FRONTMATTER-GECERSIZ" not in out2,
            f"rc={rc2}")

    d = _repo()
    _yaz(d / "claude" / "agents" / "kotu.md", BOZUK_AJAN)
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "-m", "bozuk")
    rc, out = _pc(gate, d, "--all")
    _yaz(d / "claude" / "agents" / "kotu.md", DUZ_AJAN)
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "-m", "duz")
    rc2, out2 = _pc(gate, d, "--all")
    kontrol("C3 --all: takipli bozuk → exit 1, duzeltilince → exit 0",
            rc == 1 and satir in out and rc2 == 0, f"rc={rc} rc2={rc2}")

    d = _repo()
    _yaz(d / "claude" / "rules" / "r.md", KURAL_UYARI)
    _git(d, "add", "-A")
    rc, out = _pc(gate, d, changelog_kacis=True)
    kontrol("C4 yalniz UYARI sinifi (bugunku paths bicimi) → exit 0 + UYARI satiri",
            rc == 0 and "FRONTMATTER-UYARI  claude/rules/r.md:2" in out, f"rc={rc} {out[-300:]!r}")

    d = _repo()
    _yaz(d / "docs" / "agents" / "kotu.md", BOZUK_AJAN, crlf=True)
    _git(d, "add", "-A")
    rc, out = _pc(gate, d)
    kontrol("C5 `claude/` disindaki tanim-benzeri dosya kapsam disi + KAPSAM 0 satiri basilir",
            rc == 0 and "[KAPSAM] frontmatter: 0 tanım dosyası" in out, f"rc={rc} {out[-300:]!r}")

    d = _repo()
    _yaz(d / "claude" / "agents" / "kotu.md", BOZUK_AJAN, crlf=True)
    _git(d, "add", "-A")
    rc, out = _pc(gate, d, yaml_engelli=True)
    kontrol("C6 PyYAML engelli: duzey 1 tek basina yakalar + KAPSAM ÖLÇÜLEMEDİ der",
            rc == 1 and satir in out and "düzey 2: ÖLÇÜLEMEDİ" in out, f"rc={rc} {out[-300:]!r}")

    # C7 — modulsuz kum (komsu fixture'larin kopyaladigi sekil): kapi COKMEZ; tanim dosyasi
    # yoksa gecer, varsa FAIL-CLOSED (olculemeyen tanim temiz sayilmaz).
    gate_m = _kum_scripts(precommit_kaynagi(), modul_kaynagi())
    (gate_m.parents[1] / "utils" / "frontmatter_lint.py").unlink()
    d = _repo()
    _git(d, "add", "-A")
    rc, out = _pc(gate_m, d)
    _yaz(d / "claude" / "agents" / "iyi.md", DUZ_AJAN)
    _git(d, "add", "-A")
    rc2, out2 = _pc(gate_m, d)
    kontrol("C7 modul yoksa: tanimsiz commit exit 0 + KAPSAM ÖLÇÜLEMEDİ; tanimli commit exit 1",
            rc == 0 and "frontmatter: ÖLÇÜLEMEDİ" in out and "Traceback" not in out
            and rc2 == 1 and "FRONTMATTER-OLCULEMEDI  claude/agents/iyi.md" in out2,
            f"rc={rc} rc2={rc2} {out2[-300:]!r}")


# ── D. ix_doctor 4g ─────────────────────────────────────────────────────────────
def doctor_yukle(modul_src: str):
    os.environ["CLAUDE_PROJECT_DIR"] = str(_kum("ilk"))
    mod = types.ModuleType("_ixd_fml")
    mod.__file__ = str(DOCTOR)
    sys.modules["_ixd_fml"] = mod
    exec(compile(doctor_kaynagi(), str(DOCTOR), "exec"), mod.__dict__)
    import utils  # type: ignore  # ix_doctor CORE_ROOT/scripts'i sys.path'e koydu
    mutant = modul_yukle(modul_src, YAML_VAR, "utils.frontmatter_lint")
    sys.modules["utils.frontmatter_lint"] = mutant
    utils.frontmatter_lint = mutant          # type: ignore[attr-defined]
    return mod


def _calistir(mod, proje: Path) -> list[tuple[str, str]]:
    mod.PROJ = proje
    return mod._frontmatter_kontrol()


def doctor_bolumu() -> None:
    print("\n== D. ix_doctor 4g ==")
    mod = doctor_yukle(modul_kaynagi())

    p = _kum("d1")
    _yaz(p / "claude-local" / "agents" / "kotu.md", BOZUK_AJAN, crlf=True)
    r = _calistir(mod, p)
    w = [m for t, m in r if t == "WARN"]
    kontrol("D1 claude-local CRLF bozuk ajan → tek WARN: PROJE + oneri + CRLF notu + satir",
            len(w) == 2 and "claude-local/agents/kotu.md:3" in w[0] and "PROJE dosyası — öneri:" in w[0]
            and "CRLF" in w[0] and "[KAPSAM:" in w[1], f"{r}")

    p = _kum("d2")
    _yaz(p / "core" / "claude" / "agents" / "kotu.md", BOZUK_AJAN, crlf=True)
    _bag(p / "core" / "claude" / "agents", p / ".claude" / "agents")
    r = _calistir(mod, p)
    w = [m for t, m in r if t == "WARN" and m.startswith("frontmatter GEÇERSİZ")]
    kontrol("D2 junction ardindaki cekirdek dosyasi → ÇEKİRDEK + DOKUNMA, oneri YOK",
            len(w) == 1 and "ÇEKİRDEK dosyası (core/claude/agents/kotu.md)" in w[0]
            and "DOKUNMA" in w[0] and "öneri:" not in w[0], f"{r}")

    p = _kum("d3")
    damga = "<!-- CORE-URETILDI: elle duzenleme; kaynak core/claude/rules/kopya.md -->\n"
    metin = FM("paths: x", "description: a: b")
    _yaz(p / ".claude" / "rules" / "kopya.md", metin.replace("---\n\n", "---\n" + damga + "\n", 1))
    r = _calistir(mod, p)
    w = [m for t, m in r if t == "WARN" and m.startswith("frontmatter GEÇERSİZ")]
    kontrol("D3 damgali cekirdek KOPYASI (.claude/rules) → ÇEKİRDEK kopyası, oneri YOK",
            len(w) == 1 and "ÇEKİRDEK kopyası (team_setup üretti; kaynak core/claude/rules/kopya.md)" in w[0]
            and "öneri:" not in w[0], f"{r}")

    p = _kum("d4")
    _yaz(p / "claude-local" / "agents" / "p.md", BOZUK_AJAN)
    _yaz(p / ".claude" / "agents" / "p.md", BOZUK_AJAN)
    r = _calistir(mod, p)
    w = [m for t, m in r if t == "WARN" and m.startswith("frontmatter GEÇERSİZ")]
    kontrol("D4 overlay kopyasi claude-local ile ayni → bulgu BIR kez (kaynak yolunda)",
            len(w) == 1 and "claude-local/agents/p.md:3" in w[0], f"{r}")

    p = _kum("d5")
    _yaz(p / ".claude" / "agents" / "iyi.md", DUZ_AJAN)
    _yaz(p / ".claude" / "rules" / "r.md", KURAL_UYARI)
    r = _calistir(mod, p)
    kontrol("D5 gecerli ajan + UYARI sinifi kural → PASS, bilinen bicim 1 (WARN degil)",
            len(r) == 1 and r[0][0] == "PASS" and "bilinen biçim" in r[0][1]
            and ".claude/rules/r.md:2" in r[0][1] and "[KAPSAM:" in r[0][1], f"{r}")

    p = _kum("d6")
    r = _calistir(mod, p)
    kontrol("D6 tanim dosyasi yok → SKIP 'yuzey bos' (gecerli DENMEZ)",
            len(r) == 1 and r[0][0] == "SKIP" and "yüzey boş" in r[0][1], f"{r}")

    import utils  # type: ignore
    gercek = sys.modules.get("utils.frontmatter_lint")
    sys.modules["utils.frontmatter_lint"] = None  # type: ignore[assignment]
    attr = utils.__dict__.pop("frontmatter_lint", None)
    try:
        r = _calistir(mod, _kum("d7"))
    finally:
        sys.modules["utils.frontmatter_lint"] = gercek  # type: ignore[assignment]
        if attr is not None:
            utils.frontmatter_lint = attr      # type: ignore[attr-defined]
    kontrol("D7 modul yuklenemezse FAIL ÖLÇÜLEMEDİ (TEMIZ denmez)",
            len(r) == 1 and r[0][0] == "FAIL" and "ÖLÇÜLEMEDİ" in r[0][1], f"{r}")

    p = _kum("d8")
    _yaz(p / "claude-local" / "agents" / "kotu.md", BOZUK_AJAN)
    mod.PROJ = p
    mod._d7_drift = lambda: []
    mod._hook_kos = lambda *a, **k: (0, "hookSpecificOutput", 0.0)
    mod._kablolama_kontrol = lambda: []
    r = mod.katman4()
    kontrol("D8 kablolama: katman4() ciktisi 4g frontmatter satirlarini tasir",
            any(t == "WARN" and m.startswith("frontmatter GEÇERSİZ") for t, m in r)
            and any(m.startswith("frontmatter: ") for _, m in r), f"{[m[:60] for _, m in r]}")


def main() -> int:
    try:
        modul_bolumu()
        agac_bolumu()
        precommit_bolumu()
        doctor_bolumu()
    finally:
        for b in _BAGLAR:                     # ⛔ junction-ÖNCE: rmtree bağa girerse hedefi siler
            try:
                os.rmdir(b) if sys.platform == "win32" else os.unlink(b)
            except OSError:
                pass
        for d in _KUMLAR:
            _sil(d)

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    print(f"\n{gecen}/{len(SONUC)} OK")
    if KIP is None:
        return 0 if gecen == len(SONUC) else 1
    dusen = {ad for ad, ok, _ in SONUC if not ok}
    tum = [ad for ad, _, _ in SONUC]
    # Desende YALNIZ `*` jokerdir (fnmatch DEĞİL: `[yaml]` orada karakter sınıfı olurdu).
    desenler = [re.compile("^" + ".*".join(re.escape(x) for x in d.split("*")) + "$")
                for d in ILAN[KIP]]
    ilan = {ad for ad in tum if any(r.match(ad) for r in desenler)}
    if dusen == ilan and dusen:
        print(f"[KIP {KIP}] ilan edilen {len(ilan)} vektor DUSTU (beklenen)")
        return 1
    print(f"[SAPMA] {KIP}: ilan edilip dusmeyen={sorted(ilan - dusen)} · "
          f"ilan edilmeden dusen={sorted(dusen - ilan)}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
