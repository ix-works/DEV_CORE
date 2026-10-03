#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K2 — `check_id_uniqueness` (CORE-08, HARD): core kimlik TANIMLARI tekil mi?

=== SINIF ===
Elle verilen kimlik aynı numarayla iki kez tanımlanınca atıf sessizce belirsizleşir:
BE-58 (core #49) · FE-36/FE-37/BE-63 (Q270) · `infra-test-recipes.md` B18d/B18e
(2026-09-26; c7d8b75'te ikisi de çift). Ders yazılıydı, yine çakıştı ⇒ HARD gate.

  P1 ⭐ GERÇEK ÇİFT   pinli c7d8b75 reçete dosyası → TAM {B18d, B18e} + dört satır no
  P2               B-no çifti (sentetik)
  P3 ⭐ AYIRT EDİCİ   checklist çifti İKİ AYRI dosyada (BE-58 vakasının biçimi)
  P4               checklist çifti aynı dosyada, biri `**FE-36**` biri düz `FE-36`
  P4b              checklist çifti aynı dosyada, biri backtick'li `` `FE-1` `` biri düz
  P5               `PATTERN #` çifti
  P5b              harf ekli `PATTERN #2a` çifti
  P6               ADR numara çifti (`0019-a.md` + `0019-b.md`)
  N1               temiz sentetik ağaç → rc 0 + KAPSAM BEYANI paydaları birebir
  N2 FP çapası     `### B0-SEÇİM` alt-etiketi `## B0`ın çifti DEĞİL
  N3 FP çapası     kod bloğu (``` ) içindeki `## B1` sayılmaz
  N3b FP çapası    kod bloğu (~~~) içindeki `## B1` sayılmaz
  N4 FP çapası     `B18` · `B18b` · `B18d` AYRI kimlikler
  N5 FP çapası     metin içi atıf + ikinci kolondaki kimlik TANIM değil
  S1               aile kaynağı YOK → rc 2 + ÖLÇÜLEMEDİ (sessiz körleşme yok)
  S2               kaynak var, 0 tanım (biçim değişti) → rc 2 + ÖLÇÜLEMEDİ
  S3               çift + ölçülemedi birlikte → rc 1, İKİ satır da basılır
  W1               kök önceliği: `--kok` > env `IX_CORE_ROOT` > `__file__`
  X1 ⭐ SINIR       argümansız alt-süreç GERÇEK core'u tarar: rc 0 + paydalar
                   (B-no ≥70 · checklist ≥300 · PATTERN ≥30 · ADR ≥20) — fix sonrası ağaç temiz

Mutasyon kipleri (validator kaynak METNİ değiştirilir, gerçek `__file__` ile exec edilir):
  --mutasyon-capraz-dosya   checklist tekilliği DOSYA BAŞINA (dosyalar arası çift kaçar)
  --mutasyon-alt-etiket     B başlığında tire ayrımı kalkar (`B0-SEÇİM` = B0)
  --mutasyon-harf-eki       harf eki atılır (`B18d` = B18)
  --mutasyon-fence          kod bloğu atlama kapalı
  --mutasyon-olculemedi-yok boş aile ÖLÇÜLEMEDİ üretmez (sessiz 0)
  --mutasyon-kalin          `**…**` kalın işareti soyulmaz (kalın kimlik görünmez)
  --mutasyon-tilde-fence    `_FENCE` yalnız ``` tanır (`~~~` bloğu taranır)
  --mutasyon-backtick       ilk hücrede backtick soyulmaz (`` `FE-1` `` görünmez)
  --mutasyon-pattern-harf   `PATTERN #<n>` harf ekini tanımaz (`#2a` görünmez)
  (son üçü düzeltme turu 2026-10-03: bug-gate Ö1 — üç mutant 16 vektörde hayatta kalmıştı)
CORE-07: her kipin DÜŞMESİ BEKLENEN vektör kümesi `_BEKLENEN_DUSEN`'de PİNLİDİR ve
EŞİTLİKLE kıyaslanır. Çıkış: 0 taban yeşil · 1 mutasyon BEKLENEN kümeyle düştü ·
2 SAPMA (düşen küme beklenenden farklı — fazlası da eksiği de) · 3 DOGRULANAMADI
(çapa tam 1 kez eşleşmedi YA DA mutant derlenmedi — "düştü" SAYILMAZ).

Koşum: python tests/fixtures/id_tekilligi/run.py [--mutasyon-...]   (exit 0 = PASS)
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
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

REPO = Path(__file__).resolve().parents[3]
GATE = REPO / "scripts" / "validators" / "check_id_uniqueness.py"
# ⛔ PİNLİ SHA (`HEAD:` DEĞİL — zamana bağlı taban merge'de yok olur): B18d/B18e çiftinin
# yaşadığı son main commit'i. CI `fetch-depth: 0` ile klonlar; erişilemezse vektör ATLA
# yazar (sessiz geçmez, özet satırında ayrı sayılır).
TABAN_SHA = "c7d8b75b8b0b970f05d74ca1971106fe4590035f"

_GECERLI_KIP = frozenset({"--mutasyon-capraz-dosya", "--mutasyon-alt-etiket",
                          "--mutasyon-harf-eki", "--mutasyon-fence",
                          "--mutasyon-olculemedi-yok", "--mutasyon-kalin",
                          "--mutasyon-tilde-fence", "--mutasyon-backtick",
                          "--mutasyon-pattern-harf"})

# Ölçülerek pinlendi (2026-10-03). Her küme NEDEN o vektörleri içerir:
#  capraz-dosya  : yalnız dosyalar arası çift (P3) — aynı dosyadaki çift (P4) hâlâ yakalanır
#  alt-etiket    : sentetik N2 + gerçek ağaçta B0/B4 alt-etiketleri çift olur (X1) + pinli
#                  tabanda da (P1: küme {B18d,B18e}'den büyür)
#  harf-eki      : N4 + gerçek ağaçta B18/B9… harfli aileler birleşir (X1, P1)
#  fence         : yalnız sentetik N3 + N3b (gerçek ağacın kod bloklarında başlık-biçimli kimlik
#                  yok). N3b düzeltme turunda eklendi: fence atlaması tümden kapanınca `~~~`
#                  bloğu da taranır ⇒ küme {N3}'ten {N3, N3b}'ye büyüdü (ölçüldü, beklenen).
#  olculemedi-yok: S1 · S2 · S3 (üçü de ÖLÇÜLEMEDİ satırını/rc 2'yi ister)
#  kalin         : P4 (kalın FE-36 görünmez) + N1 (kalın kimlik paydadan düşer) + X1
#                  (gerçek checklist'ler kalın kimlikli → payda <300). P4b kalın değil ⇒ düşmez.
#  tilde-fence   : yalnız N3b (gerçek ağaçta `~~~` bloğu 0 — grep, 2026-10-03)
#  backtick      : yalnız P4b (gerçek checklist'lerde backtick'li ilk-hücre kimliği 0 — grep)
#  pattern-harf  : yalnız P5b (gerçek lessons-learned'da harfli PATTERN 0 — grep). Eki tanımayan
#                  değil de eki atıp `#2`ye katan varyant da yalnız P5b'yi düşürür (ölçüldü, kip değil)
_BEKLENEN_DUSEN = {
    "--mutasyon-capraz-dosya": {"P3"},
    "--mutasyon-alt-etiket": {"P1", "N2", "X1"},
    "--mutasyon-harf-eki": {"P1", "N4", "X1"},
    "--mutasyon-fence": {"N3", "N3b"},
    "--mutasyon-olculemedi-yok": {"S1", "S2", "S3"},
    "--mutasyon-kalin": {"P4", "N1", "X1"},
    "--mutasyon-tilde-fence": {"N3b"},
    "--mutasyon-backtick": {"P4b"},
    "--mutasyon-pattern-harf": {"P5b"},
}

_MUT = {
    "--mutasyon-capraz-dosya": (
        '                out.append((ilk, f"{rel}:{i}"))',
        '                out.append((rel + "|" + ilk, f"{rel}:{i}"))'),
    "--mutasyon-alt-etiket": (
        r'(B\d+[a-z]?)(?![\w-])', r'(B\d+[a-z]?)(?![\w])'),
    "--mutasyon-harf-eki": (
        r'(B\d+[a-z]?)', r'(B\d+)[a-z]?'),
    "--mutasyon-fence": (
        "        if _FENCE.match(satir):", "        if False and _FENCE.match(satir):"),
    "--mutasyon-olculemedi-yok": (
        '            olculemedi.append(f"{ad}: {neden} — {dizin}/{glob}")',
        '            pass'),
    "--mutasyon-kalin": (
        '.strip().strip("*`").strip()', '.strip().strip("`").strip()'),
    "--mutasyon-tilde-fence": (
        '(```|~~~)")', '(```)")'),
    "--mutasyon-backtick": (
        '.strip().strip("*`").strip()', '.strip().strip("*").strip()'),
    "--mutasyon-pattern-harf": (
        r'PATTERN[ \t]*#(\d+[a-z]?)(?![\w-])', r'PATTERN[ \t]*#(\d+)(?![\w-])'),
}

SONUC: list[tuple[str, bool, str]] = []
ATLA: list[tuple[str, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


def gate_yukle(kaynak: str) -> types.ModuleType:
    """Kaynak METNİNİ gerçek `__file__` ile exec et (mutant kum dışına yazılmaz)."""
    m = types.ModuleType("_id_tekilligi_gate")
    m.__file__ = str(GATE)
    exec(compile(kaynak, str(GATE), "exec"), m.__dict__)
    return m


def kos(G: types.ModuleType, kok: Path | None, env_kok: str | None = None) -> tuple[int, str]:
    eski = os.environ.pop("IX_CORE_ROOT", None)
    if env_kok:
        os.environ["IX_CORE_ROOT"] = env_kok
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = G.main(["--kok", str(kok)] if kok else [])
    finally:
        os.environ.pop("IX_CORE_ROOT", None)
        if eski is not None:
            os.environ["IX_CORE_ROOT"] = eski
    return rc, buf.getvalue()


# ── Sentetik core ağacı ───────────────────────────────────────────────────────
TEMIZ = {
    "governance/infra-test-recipes.md":
        "# Reçeteler\n\n## B0 — taban\n\n## B1 — bir\n"
        "Bkz. B0 ve B1 (metin içi atıf).\n\n## B2 — iki\n",
    "playbook/checklists/a.md":
        "| ID | Kontrol |\n|---|---|\n| **BE-1** | bir |\n| BE-2 | iki |\n",
    "playbook/checklists/b.md":
        "| ID | Kontrol |\n|---|---|\n| FE-1 | bir · eşi BE-1 |\n",
    "playbook/lessons-learned.md":
        "# Dersler\n\n### PATTERN #1: bir\n\n### PATTERN #2: iki\n",
    "governance/decisions/0001-bir.md": "# ADR 0001\n",
    "governance/decisions/0002-iki.md": "# ADR 0002\n",
}


@contextlib.contextmanager
def agac(degisiklik: dict[str, str | None] | None = None):
    d = Path(tempfile.mkdtemp(prefix="idtek_"))
    try:
        dosyalar = dict(TEMIZ)
        for k, v in (degisiklik or {}).items():
            if v is None:
                dosyalar.pop(k, None)
            else:
                dosyalar[k] = v
        for rel, icerik in dosyalar.items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(icerik, encoding="utf-8", newline="\n")
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _payda(out: str, aile: str) -> int:
    for satir in out.splitlines():
        if satir.strip().startswith(f"[{aile}]") and "tanım" in satir:
            parca = satir.split("·")
            for p in parca:
                p = p.strip()
                if p.endswith(" tanım"):
                    try:
                        return int(p.split()[0])
                    except ValueError:
                        return -1
    return -1


def senaryolar(G: types.ModuleType) -> None:
    # P1 ⭐ GERÇEK ÇİFT — pinli taban
    try:
        taban = subprocess.run(["git", "-C", str(REPO), "show",
                                f"{TABAN_SHA}:governance/infra-test-recipes.md"],
                               capture_output=True, timeout=60)
        taban_metin = taban.stdout.decode("utf-8") if taban.returncode == 0 else None
        neden = taban.stderr.decode("utf-8", "replace").strip()[:120]
    except Exception as e:  # noqa: BLE001
        taban_metin, neden = None, f"{type(e).__name__}: {e}"
    if taban_metin is None:
        ATLA.append(("P1", f"pinli taban okunamadı ({neden}) — sığ klon?"))
    else:
        with agac({"governance/infra-test-recipes.md": taban_metin}) as d:
            rc, out = kos(G, d)
        satirlar = [s for s in out.splitlines() if s.strip().startswith("- [")]
        beklenen = {"  - [B-no] B18d: governance/infra-test-recipes.md:1001 · "
                    "governance/infra-test-recipes.md:1110",
                    "  - [B-no] B18e: governance/infra-test-recipes.md:1017 · "
                    "governance/infra-test-recipes.md:1090"}
        kontrol("P1 ⭐ pinli c7d8b75 reçetesi → TAM {B18d, B18e} + dört satır no",
                rc == 1 and set(satirlar) == beklenen, f"rc={rc} · {satirlar}")

    with agac({"governance/infra-test-recipes.md": TEMIZ["governance/infra-test-recipes.md"]
               + "\n## B1 — ikinci tanım\n"}) as d:
        rc, out = kos(G, d)
    kontrol("P2 B-no çifti → rc 1 + B1 listelenir",
            rc == 1 and "[B-no] B1:" in out, f"rc={rc}")

    with agac({"playbook/checklists/b.md": TEMIZ["playbook/checklists/b.md"] + "| BE-2 | çift |\n"}) as d:
        rc, out = kos(G, d)
    kontrol("P3 ⭐ checklist çifti İKİ dosyada → rc 1 + iki dosya da anılır",
            rc == 1 and "[checklist] BE-2:" in out and "a.md:" in out and "b.md:" in out,
            f"rc={rc} · {[s for s in out.splitlines() if 'BE-2' in s]}")

    with agac({"playbook/checklists/b.md": TEMIZ["playbook/checklists/b.md"] + "| **FE-1** | çift |\n"}) as d:
        rc, out = kos(G, d)
    # Satır biçiminden bağımsız (anahtar biçimi değişse de FE-1 satırı aranır).
    fe1 = [s for s in out.splitlines() if s.startswith("  - [checklist]") and "FE-1" in s]
    kontrol("P4 checklist çifti aynı dosyada, kalın + düz → rc 1 + FE-1 listelenir",
            rc == 1 and len(fe1) == 1, f"rc={rc} · {fe1}")

    # P4b: backtick'li kimlik (`` `FE-1` ``) düz `FE-1`in çiftidir — validator ilk hücrede
    # "*" ile birlikte "`"yi de soyar (docstring "`**X**` = X"). Kalın işareti YOK ⇒ `kalin`
    # mutantından bağımsız; yalnız backtick soymayı ölçer.
    with agac({"playbook/checklists/b.md": TEMIZ["playbook/checklists/b.md"] + "| `FE-1` | çift |\n"}) as d:
        rc, out = kos(G, d)
    fe1 = [s for s in out.splitlines() if s.startswith("  - [checklist]") and "FE-1" in s]
    kontrol("P4b checklist çifti aynı dosyada, backtick'li + düz → rc 1 + FE-1 listelenir",
            rc == 1 and len(fe1) == 1, f"rc={rc} · {fe1}")

    with agac({"playbook/lessons-learned.md": TEMIZ["playbook/lessons-learned.md"]
               + "\n### PATTERN #2: ikinci\n"}) as d:
        rc, out = kos(G, d)
    kontrol("P5 PATTERN çifti → rc 1", rc == 1 and "[PATTERN] PATTERN #2:" in out, f"rc={rc}")

    # P5b: harf ekli PATTERN çifti (`#2a` iki kez). Harf eki kimliğin parçasıdır: eki tanımayan
    # desen `#2a`yı hiç görmez (çift kaçar), eki atan desen `#2`ye katar (yanlış kimlik basılır)
    # — iki yönde de "PATTERN #2a:" satırı çıkmaz.
    with agac({"playbook/lessons-learned.md": TEMIZ["playbook/lessons-learned.md"]
               + "\n### PATTERN #2a: harfli\n\n### PATTERN #2a: harfli ikinci\n"}) as d:
        rc, out = kos(G, d)
    kontrol("P5b harfli PATTERN çifti (`#2a` ×2) → rc 1 + PATTERN #2a listelenir",
            rc == 1 and "[PATTERN] PATTERN #2a:" in out, f"rc={rc}")

    with agac({"governance/decisions/0002-baska.md": "# ADR 0002 (çift)\n"}) as d:
        rc, out = kos(G, d)
    kontrol("P6 ADR numara çifti → rc 1", rc == 1 and "[ADR] ADR 0002:" in out, f"rc={rc}")

    with agac() as d:
        rc, out = kos(G, d)
    paydalar = {a: _payda(out, a) for a in ("B-no", "checklist", "PATTERN", "ADR")}
    kontrol("N1 temiz ağaç → rc 0 + KAPSAM paydaları birebir (3/3/2/2) + BAKILMAYAN satırı",
            rc == 0 and paydalar == {"B-no": 3, "checklist": 3, "PATTERN": 2, "ADR": 2}
            and "BAKILMAYAN:" in out and "[OK]" in out, f"rc={rc} · {paydalar}")

    with agac({"governance/infra-test-recipes.md": TEMIZ["governance/infra-test-recipes.md"]
               + "\n### B0-SEÇİM — alt bölüm\n### B2-EK — alt bölüm\n"}) as d:
        rc, out = kos(G, d)
    kontrol("N2 FP: `B2-EK` / `B0-SEÇİM` alt-etiketi çift sayılmaz", rc == 0, f"rc={rc}")

    with agac({"governance/infra-test-recipes.md": TEMIZ["governance/infra-test-recipes.md"]
               + "\n```markdown\n## B1 — örnek başlık\n```\n"}) as d:
        rc, out = kos(G, d)
    kontrol("N3 FP: kod bloğu içindeki `## B1` sayılmaz", rc == 0, f"rc={rc}")

    # N3b: N3'ün `~~~` kardeşi (CommonMark tilde fence; validator `_FENCE` ikisini de tanır).
    with agac({"governance/infra-test-recipes.md": TEMIZ["governance/infra-test-recipes.md"]
               + "\n~~~markdown\n## B1 — örnek başlık\n~~~\n"}) as d:
        rc, out = kos(G, d)
    kontrol("N3b FP: `~~~` kod bloğu içindeki `## B1` sayılmaz", rc == 0, f"rc={rc}")

    with agac({"governance/infra-test-recipes.md": TEMIZ["governance/infra-test-recipes.md"]
               + "\n## B18 — a\n## B18b — b\n## B18d — d\n"}) as d:
        rc, out = kos(G, d)
    kontrol("N4 FP: B18 · B18b · B18d ayrı kimlikler", rc == 0 and _payda(out, "B-no") == 6,
            f"rc={rc} · payda={_payda(out, 'B-no')}")

    with agac({"playbook/checklists/b.md": TEMIZ["playbook/checklists/b.md"]
               + "| FE-2 | bkz. BE-2 ve FE-1 |\n\nMetinde BE-1 ve FE-1 geçer.\n",
               "playbook/lessons-learned.md": TEMIZ["playbook/lessons-learned.md"]
               + "\nPATTERN #1'e bak.\n"}) as d:
        rc, out = kos(G, d)
    kontrol("N5 FP: metin içi / ikinci kolon atıfı tanım değil", rc == 0, f"rc={rc}")

    with agac({"playbook/lessons-learned.md": None}) as d:
        rc, out = kos(G, d)
    kontrol("S1 aile kaynağı YOK → rc 2 + ÖLÇÜLEMEDİ", rc == 2 and "[ÖLÇÜLEMEDİ]" in out
            and "PATTERN: kaynak dosya YOK" in out, f"rc={rc}")

    with agac({"playbook/lessons-learned.md": "# Dersler\n\n## Pattern 1 — biçim değişti\n"}) as d:
        rc, out = kos(G, d)
    kontrol("S2 0 tanım → rc 2 + ÖLÇÜLEMEDİ", rc == 2 and "PATTERN: 0 tanım" in out, f"rc={rc}")

    with agac({"playbook/lessons-learned.md": None,
               "governance/decisions/0002-baska.md": "# çift\n"}) as d:
        rc, out = kos(G, d)
    kontrol("S3 çift + ölçülemedi → rc 1, iki satır da basılır",
            rc == 1 and "[FAIL]" in out and "[ÖLÇÜLEMEDİ]" in out, f"rc={rc}")

    with agac() as d_arg, agac({"governance/decisions/0002-baska.md": "# çift\n"}) as d_env:
        rc_a, _ = kos(G, d_arg, env_kok=str(d_env))
        rc_e, _ = kos(G, None, env_kok=str(d_env))
    kontrol("W1 kök önceliği: `--kok` env'i ezer; env `__file__`'ı ezer",
            rc_a == 0 and rc_e == 1, f"arg={rc_a} · env={rc_e}")


def x1_gercek(G: types.ModuleType) -> None:
    """X1: GERÇEK giriş noktası (alt-süreç, argümansız) — mutantta ise mutant kaynağıyla."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop("IX_CORE_ROOT", None)
    kaynak = G.__dict__.get("_KAYNAK_METNI")
    kod = ("import sys,types;src=sys.stdin.read();m=types.ModuleType('__main__');"
           f"m.__file__={str(GATE)!r};sys.argv=[{str(GATE)!r}];"
           f"exec(compile(src,{str(GATE)!r},'exec'),m.__dict__)")
    p = subprocess.run([sys.executable, "-c", kod], input=kaynak, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
    out = (p.stdout or "") + (p.stderr or "")
    paydalar = {a: _payda(out, a) for a in ("B-no", "checklist", "PATTERN", "ADR")}
    kontrol("X1 ⭐ argümansız alt-süreç GERÇEK core'u tarar: rc 0 + paydalar (≥70/≥300/≥30/≥20)",
            p.returncode == 0 and paydalar["B-no"] >= 70 and paydalar["checklist"] >= 300
            and paydalar["PATTERN"] >= 30 and paydalar["ADR"] >= 20,
            f"rc={p.returncode} · {paydalar} · {[s for s in out.splitlines() if s.startswith('  - [')][:3]}")


def main(kip: str | None) -> int:
    kaynak = GATE.read_text(encoding="utf-8")
    if kip:
        eski, yeni = _MUT[kip]
        n = kaynak.count(eski)
        if n != 1:
            sys.stderr.write("[DOGRULANAMADI] mutasyon capasi %d kez eslesti (beklenen 1): %s "
                             "-> hicbir sayi raporlanmadi.\n" % (n, kip))
            return 3
        kaynak = kaynak.replace(eski, yeni, 1)
        print("mutasyon:", kip)
        try:
            compile(kaynak, str(GATE), "exec")
        except SyntaxError as e:
            sys.stderr.write("[DOGRULANAMADI] mutant DERLENMEDI (%s): %s -> hicbir sayi "
                             "raporlanmadi.\n" % (kip, e))
            return 3
    G = gate_yukle(kaynak)
    G.__dict__["_KAYNAK_METNI"] = kaynak
    senaryolar(G)
    x1_gercek(G)

    hata = 0
    for ad, ok, detay in SONUC:
        hata += 0 if ok else 1
        print("[%s] %-72s %s" % ("ok" if ok else "FAIL", ad, "" if ok else detay))
    for ad, neden in ATLA:
        print("[ATLA] %s — %s" % (ad, neden))
    gecen = len(SONUC) - hata
    if ATLA:
        print("%d/%d OK · %d ATLA" % (gecen, len(SONUC), len(ATLA)))
    else:
        print("%d/%d OK" % (gecen, len(SONUC)))
    if kip:
        dusen = {ad.split()[0] for ad, ok, _ in SONUC if not ok}
        beklenen = _BEKLENEN_DUSEN[kip] - {a for a, _ in ATLA}
        if dusen != beklenen:
            print("[SAPMA] %s: beklenen=%s dusen=%s fazla=%s eksik=%s -> exit 2"
                  % (kip, sorted(beklenen), sorted(dusen), sorted(dusen - beklenen),
                     sorted(beklenen - dusen)))
            return 2
        print("[BEKLENEN] %s: dusen kume = beklenen %s" % (kip, sorted(beklenen)))
        return 1
    return 1 if hata else 0


if __name__ == "__main__":
    kip = None
    for _a in sys.argv[1:]:
        if _a.startswith("--mutasyon"):
            if _a not in _GECERLI_KIP:
                print("[KULLANIM] bilinmeyen mutasyon kipi: %s · gecerli kipler: %s"
                      % (_a, ", ".join(sorted(_GECERLI_KIP))))
                sys.exit(3)
            kip = _a
    sys.exit(main(kip))
