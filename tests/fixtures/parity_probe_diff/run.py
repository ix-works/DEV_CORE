#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parity_probe_diff — `parity_probe.py --diff ONCE SONRA` korpusu (Q371⑤, 2026-10-12).

NEDEN: araç iki makinede / önce-sonra koşulup JSON üretiyordu ama kıyas ELLE yapılıyordu
(playbook "ONCE ↔ SONRA karşılaştır"). Diff modu ÖNCE yoktu (ölçüldü: v1.2 argparse'ında yalnız
--no-doctor/--anon/--proje/--out). Rapor verisi SENTETİKTİR.

SENARYOLAR
  D1  yalnız `_zaman` farklı → çıkış 0, "0 farkli"                          [--mutasyon-zaman]
  D2  skaler fark → [FARK] + ONE CIKAN satırı FARK + çıkış 1
  D3  skaler liste → KÜME farkı (+eklenen −çıkan), sıra farkı FARK DEĞİL
  D4  sözlük listesi (ix_doctor katmanları) indeksle açılır, değişen alt alan adıyla görünür
  D5  "OLCULEMEDI" değer FARK sayılmaz, TEMİZ de sayılmaz → [OLCULEMEDI] + çıkış 3
                                                                            [--mutasyon-olculemedi]
  D6  yalnız bir tarafta olan alan → [YALNIZ-SONRA] + çıkış 1
  D7  parity raporu olmayan JSON / okunamayan dosya → çıkış 2 [KULLANIM]
  D8  sürüm farkı uyarısı basılır
  D9  bug-gate 2026-10-12: ilk ~110 karakteri aynı, sonu farklı liste elemanı → FARK (kıyas TAM
      değerle; `_kisa` yalnız ekranda)                                          [--mutasyon-kisa]
  D10 kısaltılmış hâlleri eşit görünen +/- elemanlar ekrana TAM basılır (fark gizlenmez)
  D11 çoklu-küme farkı sayılı: ['ab','ab','c']↔['ab','c','c'] → `+1 ["c"]  -1 ["ab"]`
                                                                            [--mutasyon-coklu]
  B1  3. BAĞLAM — gerçek giriş noktası: aynı sahte proje için `--no-doctor` iki koşum, sonra
      `--diff` alt süreçte → [FARK] yok, çıkış 0 ya da 3 (ortamda ölçülemeyen alan olabilir)

Koşum:  python tests/fixtures/parity_probe_diff/run.py [--mutasyon-<kip>]
"""
import copy
import io
import json
import subprocess
import sys
import tempfile
import types
from contextlib import redirect_stdout
from pathlib import Path

if sys.platform == "win32":
    for _a in (sys.stdout, sys.stderr):
        try:
            _a.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

KOK = Path(__file__).resolve().parents[3]
ARAC = KOK / "scripts" / "parity_probe.py"

MUTASYON = {
    "--mutasyon-zaman": ('DIFF_YOK_SAY = {"_zaman"}', 'DIFF_YOK_SAY = set()'),
    "--mutasyon-olculemedi": ('        return v.upper().startswith("OLCULEMEDI")\n', '        return False\n'),
    # kıyası eski KISALTILMIŞ değerle yapar → D9 düşmeli
    "--mutasyon-kisa": ('            if not eklenen and not cikan:\n',
                        '            if sorted(map(_kisa, x)) == sorted(map(_kisa, y)):\n'),
    # çoklu-kümeyi kümeye indirger → D11 düşmeli
    "--mutasyon-coklu": ('    cx, cy = Counter(map(_kanonik, x)), Counter(map(_kanonik, y))\n',
                         '    cx, cy = Counter(set(map(_kanonik, x))), Counter(set(map(_kanonik, y)))\n'),
}
GECERLI_KIP = set(MUTASYON)
_kip = [a for a in sys.argv[1:] if a.startswith("--")]
for a in _kip:
    if a not in GECERLI_KIP:
        print(f"[DURDU] bilinmeyen kip: {a}")
        sys.exit(2)
KIP = _kip[0] if _kip else None

src = ARAC.read_text(encoding="utf-8")
if KIP:
    eski, yeni = MUTASYON[KIP]
    if src.count(eski) != 1:
        print(f"[DURDU] mutasyon çapası bulunamadı/çoğul ({KIP}): {eski!r}")
        sys.exit(3)
    src = src.replace(eski, yeni)
P = types.ModuleType("parity_probe_fx")
P.__file__ = str(ARAC)
exec(compile(src, str(ARAC), "exec"), P.__dict__)

SONUC = []
TMP = Path(tempfile.mkdtemp(prefix="paritydiff_"))


def kontrol(ad, ok, detay=""):
    SONUC.append((ad, bool(ok), detay))


TABAN = {
    "_surum": "parity_probe/1.3", "_zaman": "2026-10-12T10:00:00",
    "harness": {"claude_version": "2.1.0 (Claude Code)", "model": "<yok>"},
    "claude_katmani": {"rules_dosyalari": ["00-claude-core.md", "10-a.md", "20-b.md"],
                       "kanca_template_farki": []},
    "core": {"head": "abc1234 x", "origin_main_gerisinde": "0"},
    "memory": {"ders_dosyasi_sayisi": 92},
    "mcp_ve_profil": {"aktif_paket_drift": False},
    "kosumlar": {"ix_doctor": {"rc": 0, "ozet": {"fail": 0, "warn": 1, "katmanlar": [
        {"no": 1, "ad": "K1", "durum": "PASS"}, {"no": 2, "ad": "K2", "durum": "PASS"}]}}},
}


def yaz(ad, veri):
    p = TMP / ad
    p.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")
    return str(p)


def diff(a, b):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = P.fark_modu(a, b)
    return rc, out.getvalue()


ta = yaz("a.json", TABAN)
v = copy.deepcopy(TABAN)
v["_zaman"] = "2026-10-12T11:11:11"
rc, o = diff(ta, yaz("d1.json", v))
kontrol("D1 yalnız _zaman farklı → çıkış 0, 0 farkli", rc == 0 and " 0 farkli" in o, f"rc={rc} {o[-200:]!r}")

v = copy.deepcopy(TABAN)
v["memory"]["ders_dosyasi_sayisi"] = 318
rc, o = diff(ta, yaz("d2.json", v))
kontrol("D2 skaler fark → [FARK] + ONE CIKAN FARK + çıkış 1",
        rc == 1 and "[FARK] memory.ders_dosyasi_sayisi: 92 -> 318" in o
        and "FARK memory.ders_dosyasi_sayisi" in o, f"rc={rc} {o!r}")

v = copy.deepcopy(TABAN)
v["claude_katmani"]["rules_dosyalari"] = ["20-b.md", "00-claude-core.md", "30-c.md"]
rc, o = diff(ta, yaz("d3.json", v))
v2 = copy.deepcopy(TABAN)
v2["claude_katmani"]["rules_dosyalari"] = list(reversed(TABAN["claude_katmani"]["rules_dosyalari"]))
rc_sira, o_sira = diff(ta, yaz("d3b.json", v2))
kontrol("D3 skaler liste KÜME farkı (+30-c −10-a)",
        rc == 1 and '[FARK] claude_katmani.rules_dosyalari  +1 ["30-c.md"]  -1 ["10-a.md"]' in o, f"{o!r}")
kontrol("D3b yalnız sıra farkı FARK DEĞİL", rc_sira == 0, f"rc={rc_sira} {o_sira[-200:]!r}")

v = copy.deepcopy(TABAN)
v["kosumlar"]["ix_doctor"]["ozet"]["katmanlar"][1]["durum"] = "FAIL"
rc, o = diff(ta, yaz("d4.json", v))
kontrol("D4 sözlük listesi indeksle açılır, değişen alt alan görünür",
        rc == 1 and '[FARK] kosumlar.ix_doctor.ozet.katmanlar[1].durum: "PASS" -> "FAIL"' in o, f"{o!r}")

v = copy.deepcopy(TABAN)
v["harness"]["claude_version"] = "OLCULEMEDI (KOMUT YOK)"
v["claude_katmani"]["kanca_template_farki"] = ["OLCULEMEDI: settings.json yok"]
rc, o = diff(ta, yaz("d5.json", v))
kontrol("D5 OLCULEMEDI → fark da temiz de değil: [OLCULEMEDI] ×2, [FARK] yok, çıkış 3",
        rc == 3 and o.count("[OLCULEMEDI]") == 2 and "[FARK]" not in o and "2 OLCULEMEDI" in o,
        f"rc={rc} {o[-300:]!r}")

v = copy.deepcopy(TABAN)
v["memory"]["yeni_alan"] = 5
rc, o = diff(ta, yaz("d6.json", v))
kontrol("D6 yalnız bir tarafta alan → [YALNIZ-SONRA] + çıkış 1",
        rc == 1 and "[YALNIZ-SONRA] memory.yeni_alan = 5" in o, f"{o!r}")

rc1, o1 = diff(ta, yaz("d7.json", {"bulgular": []}))
(TMP / "bozuk.json").write_text("{yok", encoding="utf-8")
rc2, o2 = diff(str(TMP / "bozuk.json"), ta)
kontrol("D7 parity raporu değil / okunamaz → çıkış 2 [KULLANIM]",
        rc1 == 2 and rc2 == 2 and "[KULLANIM]" in o1 and "[KULLANIM]" in o2, f"{rc1},{rc2}")

v = copy.deepcopy(TABAN)
v["_surum"] = "parity_probe/1.2"
rc, o = diff(ta, yaz("d8.json", v))
kontrol("D8 sürüm farkı uyarısı", "SURUM FARKLI" in o, f"{o[:300]!r}")

# D9-D11 — bug-gate 2026-10-12: kıyas TAM değerle (kısaltma yalnız ekranda) + çoklu-küme sayımı
UZUN = "[OK] " + "x" * 110
va, vb = copy.deepcopy(TABAN), copy.deepcopy(TABAN)
va["claude_katmani"]["kanca_template_farki"] = [UZUN + " FAIL=0", "kisa"]
vb["claude_katmani"]["kanca_template_farki"] = ["kisa", UZUN + " FAIL=3"]
rc, o = diff(yaz("d9a.json", va), yaz("d9b.json", vb))
kontrol("D9 ilk ~110 karakteri aynı, sonu farklı eleman → FARK + çıkış 1 (sıra farkı da var)",
        rc == 1 and "[FARK] claude_katmani.kanca_template_farki  +1 " in o, f"rc={rc} {o[-300:]!r}")
kontrol("D10 uzun elemanda ekran farkı GİZLEMEZ (kısaltılmış hâller eşitse tam basılır)",
        "FAIL=3" in o and "FAIL=0" in o, f"{o[-300:]!r}")
va, vb = copy.deepcopy(TABAN), copy.deepcopy(TABAN)
va["claude_katmani"]["rules_dosyalari"] = ["ab", "ab", "c"]
vb["claude_katmani"]["rules_dosyalari"] = ["ab", "c", "c"]
rc, o = diff(yaz("d11a.json", va), yaz("d11b.json", vb))
kontrol("D11 çoklu-küme farkı sayılı: +1 [\"c\"] -1 [\"ab\"] (boş +[] -[] DEĞİL)",
        rc == 1 and '[FARK] claude_katmani.rules_dosyalari  +1 ["c"]  -1 ["ab"]' in o, f"rc={rc} {o!r}")

if KIP:
    print("  [ATLANDI] B1 — mutasyon kipinde (alt süreç gerçek aracı koşar)")
else:
    proje = TMP / "proje"
    proje.mkdir()
    (proje / "CLAUDE.md").write_text("# <PROJECT_NAME>\n", encoding="utf-8")
    (proje / "project.yaml").write_text("sap_profile: s4_private\n", encoding="utf-8")
    outs = []
    for ad in ("r1.json", "r2.json"):
        r = subprocess.run([sys.executable, str(ARAC), "--no-doctor", "--anon", "--proje", str(proje),
                            "--out", str(TMP / ad)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=180)
        outs.append(r.returncode)
    r = subprocess.run([sys.executable, str(ARAC), "--diff", str(TMP / "r1.json"), str(TMP / "r2.json")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    o = r.stdout + r.stderr
    kontrol("B1 gerçek iki koşum + --diff alt süreç: [FARK] yok, çıkış 0/3",
            outs == [0, 0] and r.returncode in (0, 3) and "[FARK]" not in o and "KAPSAM:" in o,
            f"olcum={outs} diff rc={r.returncode} {o[-300:]!r}")

print(f"parity_probe_diff{(' ' + KIP) if KIP else ''}")
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
gecen = sum(1 for _, ok, _ in SONUC if ok)
print(f"TOPLAM: {gecen}/{len(SONUC)} PASS")
sys.exit(0 if gecen == len(SONUC) else 1)
