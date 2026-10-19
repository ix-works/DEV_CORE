#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TENANT HOST + TRANSPORT NO uyari desenleri ve `core_precommit --ref/--msg` korpusu
(Q361 + Q365⑤, 2026-10-12).

NEDEN BU KORPUS VAR
-------------------
Public cekirdekte iki tur kimlik izi hicbir katmanca gorulmuyordu: bir bulut tenant
host'u (bir docstring ornegi) ve bir tuketici projenin transport numarasi (bir ajan
tanimi + 4 fixture). Ikisi de ISIM degil BICIM tasir; isim listesi proje basinadir ve
cekirdek onu bilmez => yapisal desen gerekir. Desenler WARN-FIRST'tur (ADR 0019):
bulgu basilir, cikis kodu DEGISMEZ, token BASILMAZ (CI gunlugu public).

Ayrica `core_precommit` iki yeni giris noktasi kazandi: `--ref <ref>` (bir ref'in agaci +
commit mesaji) ve `--msg <dosya|->` (commit mesaji). Her giris noktasi AYRI olculur —
bir yolun gordugu desen digerinin de gordugu anlamina gelmez.

BOLUMLER
  A  pozitif: bilinen sizinti bicimleri YAKALANIR (Q361'in gercek yazim bicimleri dahil)
  N  negatif: dokuman yer tutuculari, bolge alanlari, sahte SID'ler SESSIZ
  S  sozlesme: bloklayici yol (`sizintilari_bul`) yeni desenleri ICERMEZ (warn-first)
  W  kablolama: GERCEK staged `core_precommit` (ayri surec, ayri git deposu)
  R  `--ref` · M  `--msg` · U  kullanim: `--all`/`--ref`/`--msg` birbirini dislar
  C  sahte commit: GERCEK `git commit` + pre-commit shim (hooksPath) — uyari commit'i
     bloklamaz, bloklayici sinif hala bloklar

⚠ ORNEK DIZGELER LITERAL YAZILMAZ: bu dosya da tarayici tarafindan taranir; desene uyan
bir dizge burada duz yazilirsa her `--all` kosumunda kendi uyarimizi uretirdik.
Dizgeler `_h()` / `_tr()` ile parcadan kurulur.

KOSUM:  python tests/fixtures/genericize_tenant_transport/run.py [--mutasyon-<kip>]
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (capa tutmadi / mutant bozuk)
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import stat
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
REPO = HERE.parent.parent.parent
SCRIPTS = REPO / "scripts"


def _h(*parca: str) -> str:
    """Host'u PARCADAN kurar (yukaridaki ⚠ notu)."""
    return ".".join(parca)


def _tr(sid: str, no: str) -> str:
    """Transport numarasini PARCADAN kurar."""
    return sid + "K" + no


BULUT = _h("s4hana", "cloud", "sap")
BTP = _h("hana", "ondemand", "com")
IAS = _h("accounts", "ondemand", "com")

T_PUBLIC = _h("my" + "123456", BULUT)                 # public cloud tenant
T_API = _h("my" + "123456" + "-api", BULUT)            # ayni tenant'in API host'u
T_ABAP = _h("a1b2c3d4-e5f6", "abap", "eu10", BTP)     # BTP ABAP ortami
T_IAS = _h("acme01", IAS)                             # IAS tenant'i
TR_GERCEK = _tr("QA2", "912345")                      # gercek-gorunen SID
Z_SIZINTI = "Z" + "XY" + "022"                        # bloklayici sinif (allowlist disi)

# kip -> (hedef, eski, yeni) — YALNIZ sandbox kopyasina uygulanir
MUTLAR = {
    "--mutasyon-sid-allowlist-bos": (
        "gc", 'ORNEK_SID = frozenset({"SAH", "AB1"})', "ORNEK_SID = frozenset()"),
    "--mutasyon-bolge-muafiyeti-yok": (
        "gc", "and not (_BOLGE_ETIKETI.fullmatch(m.group(1)) and not m.group(2))", ""),
    # Issue #357 (2026-10-19): muafiyet ara etiketi YOK SAYARSA (eski kod) bolge bicimli ilk
    # etiketli tenant host sessizlesir (A12-A14 birim + M14 `--msg` ayri surec).
    # Mutant = 254134f'teki filtre.
    "--mutasyon-ara-etiket-kosulu-yok": (
        "gc", "and not (_BOLGE_ETIKETI.fullmatch(m.group(1)) and not m.group(2))",
        "and not _BOLGE_ETIKETI.fullmatch(m.group(1))"),
    "--mutasyon-host-bas-sinir": (
        "gc", 'r"(?<![A-Za-z0-9._-])"', 'r""'),
    # bug-gate 2026-10-12: `<` / `{` geri-bakis sinifina GERI eklenirse sarmal icindeki
    # somut host yine sessizlesir (A10/A11).
    "--mutasyon-host-bas-acili": (
        "gc", 'r"(?<![A-Za-z0-9._-])"', 'r"(?<![A-Za-z0-9._<{-])"'),
    "--mutasyon-uyari-kablosuz": (
        "pc", "uyarilar = uyari_sizintilari(satir)", "uyarilar = []"),
    "--mutasyon-bloklayici": (
        "pc", '        if not bulgular:\n            continue\n        ek = ""',
        '        bulgular = bulgular + uyarilar\n        if not bulgular:\n'
        '            continue\n        ek = ""'),
    "--mutasyon-token-basilir": (
        "pc", "return f\"'{tok}' \" if token_bas else \"\"", "return f\"'{tok}' \""),
    # bug-gate 2026-10-12: `#` muafiyeti GERI gelirse `--msg` (M2) ve `--ref` (R7) korlesir.
    # F3 (2026-10-14): atif dali artik satiri BOSALTMAZ (adresi maskeler) ⇒ `#` muafiyeti
    # o dala `or` ile eklenirse `#` satiri yine taranirdi (mutasyon sessizce KACTI, olculdu).
    # Muafiyet ayri bir bosaltma dali olarak geri konur.
    "--mutasyon-msg-yorum": (
        "pc", "if _ATIF_SATIRI.match(s):",
        'if s.lstrip().startswith("#"):\n            out.append("")\n            continue\n'
        "        if _ATIF_SATIRI.match(s):"),
    "--mutasyon-atif-muafiyeti-yok": (
        "pc", "if _ATIF_SATIRI.match(s):", "if False:"),
    # Desen 2026-10-12'den beri TEK KAYNAKTA (`genericize_common._ATIF_GOVDE`;
    # core_precommit `_ATIF_SATIRI = ATIF_SATIRI` alias'idir) ⇒ cekirdek mutasyonlari "gc"de.
    "--mutasyon-atif-genis": (
        "gc", r"<noreply@anthropic\.com>", r"<[^>]+>"),
    # bug-gate 2026-10-12: ad-adres arasi `@` kabul edilirse govdedeki e-posta muaf olurdu (M10).
    # ⚠ ANLAMI DEGISTI (bug-gate turu 3, 2026-10-14 — olculdu): F3'ten beri atif satiri
    # bosaltilmaz, yalniz uretici adresi maskelenir ⇒ bu kip artik GUVENLIK acisindan ESDEGER
    # mutanttir (`atif-son-capa-yok` gibi). Mutantta M10'un e-postasi YINE `kimlik izi` olarak
    # basilir (satir 3); dusen yalniz KAPSAM sayaci (`adresi maskelenen 1`, beklenen 0).
    # Guard tarafinda sayac yok ⇒ orada tam esdeger. Kip, sayacin dogrulugunu olcer.
    "--mutasyon-atif-orta-genis": (
        # (2026-10-14: adres `_ATIF_ADRES`'e ayrildi ⇒ capa `<` yerine kapanis tirnagina dayanir)
        "gc", r'Claude\b[^<@\n]*"', r'Claude\b[^<\n]*"'),
    # bug-gate F3 (2026-10-14): atif satiri yeniden tumden BOSALTILIRSA ad bolumundeki obje
    # adi taramadan gecer (M13).
    "--mutasyon-atif-bosalt": (
        "pc", 'out.append(ATIF_ADRES_PAT.sub("", s, count=1))', 'out.append("")'),
    # F1 kardesi: ATIF_SATIRI son capasi kalkar. Guvenlik ESDEGERI (satir yine taranir —
    # F3 maskelemesi); dusen yalniz KAPSAM sayaci (M12b: sonu kirli satir atif sayilir).
    "--mutasyon-atif-son-capa-yok": (
        "gc", 'ATIF_SATIRI = re.compile(r"^\\s*" + _ATIF_GOVDE + r"\\s*$", re.IGNORECASE)',
        'ATIF_SATIRI = re.compile(r"^\\s*" + _ATIF_GOVDE, re.IGNORECASE)'),
    "--mutasyon-bos-mesaj-temiz": (
        "pc", "    if not metin.strip():\n", "    if False:\n"),
    "--mutasyon-mod-dislama-yok": (
        "pc", "    if len(modlar) > 1:\n", "    if False:\n"),
}

# Ajan atif trailer'i — adres PARCADAN kurulur (bu dosya e-posta desenine taranir).
ATIF = "Co-Authored-By: Claude Opus 5.5 (1M context) <" + "noreply" + "@" + "anthropic.com>"
ATIF_BASKA = "Co-authored-by: Biri <" + "biri" + "@" + "ornek-firma.com.tr>"
# Ad ayni (Claude) ama adres BASKA — muafiyet adrese de bagli olmali.
ATIF_SAHTE = "Co-Authored-By: Claude Opus <" + "biri" + "@" + "ornek-firma.com.tr>"
# Ad + dogru adres AMA aralarinda ikinci bir e-posta (bug-gate 2026-10-12): muafiyet bu
# satiri yutarsa govdedeki adres hic taranmazdi.
ATIF_GOVDE_EPOSTA = ("Co-Authored-By: Claude " + "biri" + "@" + "ornek-firma.com.tr <"
                     + "noreply" + "@" + "anthropic.com>")
EPOSTA = "biri" + "@" + "ornek-firma.com.tr"

SONUC: list[tuple[str, bool, str]] = []


def ekle(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def _sil(d: Path) -> None:
    """Q319: Windows'ta salt-okur girdi `rmtree(ignore_errors=True)` ile SESSIZCE kalir."""
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


def _yukle(yol: Path):
    """Sandbox kopyasini AYRI modul adiyla yukle (gercek modul `sys.modules`'ta kalirsa
    mutant hic olculmezdi — sahte-YESIL sinifi)."""
    ad = "gc_tenant_transport_kopya"
    sys.modules.pop(ad, None)
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def main() -> int:
    gecerli = set(MUTLAR)
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in gecerli:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + " ".join(sorted(gecerli)))
    secili = next((a for a in sys.argv[1:] if a in gecerli), None)

    tmp = Path(tempfile.mkdtemp(prefix="tenant_tr_"))
    try:
        proje = tmp / "repo"
        (proje / "docs").mkdir(parents=True)
        (proje / "scripts" / "git-hooks").mkdir(parents=True)
        shutil.copy2(SCRIPTS / "genericize_common.py", proje / "scripts")
        for ad in ("core_precommit.py", "pre-commit"):
            shutil.copy2(SCRIPTS / "git-hooks" / ad, proje / "scripts" / "git-hooks")
        hedefler = {"gc": proje / "scripts" / "genericize_common.py",
                    "pc": proje / "scripts" / "git-hooks" / "core_precommit.py"}

        if secili:
            h, eski, yeni = MUTLAR[secili]
            hedef = hedefler[h]
            kaynak = hedef.read_bytes().decode("utf-8").replace("\r\n", "\n")
            if kaynak.count(eski) != 1:
                print(f"[DOGRULANAMADI] mutasyon capasi {kaynak.count(eski)} kez bulundu "
                      f"({secili}) -> mutasyon UYGULANMADI; 'gecti' sonucu ANLAMSIZ olurdu.")
                return 2
            hedef.write_bytes(kaynak.replace(eski, yeni, 1).encode("utf-8"))
            try:
                compile(hedef.read_text(encoding="utf-8"), str(hedef), "exec")
            except SyntaxError as e:
                print(f"[DOGRULANAMADI] mutant SOZDIZIMI BOZUK ({secili}): {e}")
                return 2

        G = _yukle(hedefler["gc"])
        U = G.uyari_sizintilari

        def turler(metin: str) -> list[str]:
            return [t for _, t in U(metin)]

        # ── A: POZITIF ─────────────────────────────────────────────────────────
        ekle("A1 public cloud tenant URL'si YAKALANIR",
             turler("https://" + T_PUBLIC + "/sap/bc/adt") == ["tenant host"],
             f"{turler('https://' + T_PUBLIC)}")
        ekle("A2 Q361 yazim bicimi (docstring `base_url='https://…'`) YAKALANIR",
             turler("            base_url='https://" + T_PUBLIC + "',") == ["tenant host"])
        ekle("A3 API host varyanti YAKALANIR", turler(T_API) == ["tenant host"])
        ekle("A4 BTP ABAP ortam host'u YAKALANIR", turler(T_ABAP) == ["tenant host"])
        ekle("A5 IAS tenant host'u YAKALANIR", turler("https://" + T_IAS + "/oauth2")
             == ["tenant host"])
        ekle("A6 gercek-gorunen SID'li transport YAKALANIR (tirnak icinde)",
             turler("transport='" + TR_GERCEK + "'") == ["transport no"])
        ekle("A7 kucuk harf transport YAKALANIR",
             turler("x " + TR_GERCEK.lower() + " y") == ["transport no"])
        ekle("A8 XML ozniteligindeki transport YAKALANIR (Q361 fixture bicimi)",
             turler('<tm:request tm:number="' + TR_GERCEK + '"/>') == ["transport no"])
        ekle("A9 ayni satirda ikisi birden — ikisi de raporlanir",
             sorted(turler(T_PUBLIC + " " + TR_GERCEK)) == ["tenant host", "transport no"])
        # bug-gate 2026-10-12: `<`/`{` sarmali icindeki SOMUT host (yer tutucu degil).
        ekle("A10 `<…>` sarmali icindeki somut host YAKALANIR",
             turler("baglanti <" + T_PUBLIC + ">") == ["tenant host"],
             f"{turler('<' + T_PUBLIC + '>')}")
        ekle("A11 `{…}` sarmali icindeki somut host YAKALANIR",
             turler('{"host": "x", "u": {' + T_IAS + '}}') == ["tenant host"],
             f"{turler('{' + T_IAS + '}')}")
        # Issue #357 (2026-10-19): ilk etiket BOLGE BICIMLI ama ara etiket VAR => tenant.
        # Eski kod (bolge muafiyeti ara etikete bakmiyordu) uc vektorde de sessizdi.
        for ad_, host_ in (("A12 bolge bicimli tenant + authentication ara etiketi",
                            _h("ab12", "authentication", "eu10", BTP)),
                           ("A13 bolge bicimli tenant + abap ara etiketi",
                            _h("de1", "abap", "eu10", BTP)),
                           ("A14 tireli bolge bicimli tenant + tek ara etiket",
                            _h("us10-001", "abap", BTP))):
            ekle(ad_ + " YAKALANIR", turler("https://" + host_ + "/x") == ["tenant host"],
                 f"{turler('https://' + host_)}")

        # ── N: NEGATIF (mesru metin) ──────────────────────────────────────────
        negatif = {
            "N1 `<tenant>` yer tutucusu": "https://<tenant>." + BULUT,
            "N2 olculen yer tutucu ilk etiket": "(e.g., " + _h("abc123", "eu10", BTP) + ")",
            "N3 yalin bolge alani": "return '" + _h("eu10", BTP) + "'",
            "N4 nokta onekli sonek listesi": "'." + _h("abap", "eu10", BTP) + "',",
            "N5 IAS yer tutucu URL": "https://<tenant>." + IAS + "/oauth2/token",
            "N6 kok IdP alani": "'" + _h("accounts", "cloud", "sap") + "',",
            "N7 sahte SID (SAH)": "transport='" + _tr("SAH", "900001") + "'",
            "N8 sahte SID (AB1)": 'TR_ISTEK = "' + _tr("AB1", "900029") + '"',
            "N9 yalniz-X SID": _tr("XXX", "900000"),
            "N10 `<SID>` yer tutucusu": "<SID>K900001",
            "N11 git SHA": "6b6c11d" + "0" * 33,
            "N12 7 haneli govde (transport degil)": _tr("QA2", "9123456"),
            "N13 tanimlayiciya bitisik": "foo" + TR_GERCEK,
            "N14 yalniz-x tenant": _h("xxxx", BULUT),
            "N15 Z-obje adi bu desenlere DUSMEZ": "ZSD001_CL_ORNEK",
            # Issue #357: ara etiketsiz bolge alani muaf KALIR (tireli bicim + baska sonek).
            "N16 tireli yalin bolge alani": "https://" + _h("us10-001", BTP) + "/",
            "N17 yalin bolge alani (public cloud soneki)": _h("eu10", BULUT),
        }
        for ad, metin in negatif.items():
            ekle(ad + " SESSIZ", U(metin) == [], f"bulunan={turler(metin)}")

        # ── K/S: ALLOWLIST OLCUTU + WARN-FIRST SOZLESMESI ─────────────────────
        ekle("K1 ORNEK_SID'deki her SID transport desenine UYAR (olu satir yok)",
             all(G.TRANSPORT_PAT.fullmatch(_tr(s, "900001")) for s in G.ORNEK_SID))
        ekle("K2 ORNEK_TENANT'taki her etiket bolge bicimli DEGIL (olu satir yok)",
             not any(G._BOLGE_ETIKETI.fullmatch(e) for e in G.ORNEK_TENANT))
        import re as _re
        hic = _re.compile(r"(?!x)x")
        ekle("S1 bloklayici yol (`sizintilari_bul`) tenant host'u ICERMEZ (warn-first)",
             G.sizintilari_bul("https://" + T_PUBLIC, hic) == [])
        ekle("S2 bloklayici yol transport no ICERMEZ (warn-first)",
             G.sizintilari_bul(TR_GERCEK, hic) == [])

        # ── W: KABLOLAMA — GERCEK staged `core_precommit` ─────────────────────
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        # Liste SABITLENIR: bos liste fail-closed dalini acardi (sentinel kimlik DEGILDIR).
        env["IX_GENERICIZE_BLOCKLIST"] = "SENTINEL" + "-ISIM"
        for k in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
            env.pop(k, None)

        def git(*a, girdi: str | None = None):
            return subprocess.run(["git", "-C", str(proje), *a], capture_output=True,
                                  text=True, encoding="utf-8", errors="replace",
                                  env=env, input=girdi)

        git("init", "-q")
        git("config", "user.email", "fixture@example.com")
        git("config", "user.name", "fixture")
        git("config", "commit.gpgsign", "false")
        git("add", "scripts")
        git("commit", "-q", "--no-verify", "-m", "taban")

        pc = proje / "scripts" / "git-hooks" / "core_precommit.py"

        def kos(*arg, girdi: str | None = None):
            r = subprocess.run([sys.executable, str(pc), *arg], cwd=str(proje), env=env,
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=180, input=girdi)
            return r.returncode, (r.stdout or "") + (r.stderr or "")

        def precommit(dosya_adi: str, icerik: str):
            p = proje / "docs" / dosya_adi
            p.write_text(icerik, encoding="utf-8")
            git("add", "docs/" + dosya_adi)
            rc, out = kos()
            git("rm", "-q", "--cached", "docs/" + dosya_adi)
            p.unlink(missing_ok=True)
            return rc, out

        rc0, out0 = precommit("temiz.md", "# not\n\nornek: https://<tenant>." + BULUT + "\n")
        ekle("W0 KONTROL GRUBU: temiz dosya rc 0 ve uyari sayisi 0 BASILIR (kapsam beyani)",
             rc0 == 0 and "[UYARI-DESENLERI]" in out0 and "): 0 (bulgu yok)" in out0,
             f"rc={rc0} cikti={out0[-400:]!r}")

        rc1, out1 = precommit("tenant.md", "# not\n\nbaglanti: https://" + T_PUBLIC + "\n")
        ekle("W1 tenant host staged: UYARI basilir ve COMMIT BLOKLANMAZ (rc 0, warn-first)",
             rc1 == 0 and "UYARI  docs/tenant.md:3  (tenant host)" in out1,
             f"rc={rc1} cikti={out1[-500:]!r}")
        ekle("W2 uyari ciktisinda TOKEN YOK (public gunluk)",
             T_PUBLIC not in out1 and "123456" not in out1, f"cikti={out1[-300:]!r}")

        rc3, out3 = precommit("tr.md", "x\ntransport " + TR_GERCEK + "\n")
        ekle("W3 transport staged: UYARI (transport no), rc 0",
             rc3 == 0 and "UYARI  docs/tr.md:2  (transport no)" in out3
             and TR_GERCEK not in out3, f"rc={rc3} cikti={out3[-400:]!r}")

        rc4, out4 = precommit("karisik.md", "a " + TR_GERCEK + "\nb " + Z_SIZINTI + "_CL_X\n")
        ekle("W4 KONTROL: ayni dosyada bloklayici sinif HALA bloklar (rc 1) + uyari da basilir",
             rc4 == 1 and "GENERICIZE-LEAK  docs/karisik.md:2" in out4
             and "UYARI  docs/karisik.md:1  (transport no)" in out4,
             f"rc={rc4} cikti={out4[-500:]!r}")

        rc5, out5 = precommit("muaf.md", "orn " + TR_GERCEK + "  <!-- genericize-allow"
                              ": sahte SID ile kurulmus ornek numara -->\n")
        ekle("W5 gerekceli muafiyet isaretcisi uyariyi da susturur ve MUAF sayilir",
             rc5 == 0 and "): 0 (bulgu yok)" in out5 and "muaf-satır 1" in out5,
             f"rc={rc5} cikti={out5[-500:]!r}")

        (proje / "docs" / "kalici.md").write_text("u: https://" + T_ABAP + "\n", encoding="utf-8")
        git("add", "docs/kalici.md")
        git("commit", "-q", "--no-verify", "-m", "kalici")
        rc6, out6 = kos("--all")
        ekle("W6 `--all` (CI modu) da uyariyi basar, rc 0",
             rc6 == 0 and "UYARI  docs/kalici.md:1  (tenant host)" in out6,
             f"rc={rc6} cikti={out6[-500:]!r}")

        # ── R: --ref ───────────────────────────────────────────────────────────
        (proje / "docs" / "ref.md").write_text("# r\n\n" + Z_SIZINTI + "_CL_Y\n",
                                               encoding="utf-8")
        git("add", "docs/ref.md")
        git("commit", "-q", "--no-verify", "-m",
            "ozet\n\nsiparis " + TR_GERCEK + " ile tasindi")
        rr, outr = kos("--ref", "HEAD")
        ekle("R1 --ref: agactaki uyari dosyasi raporlanir",
             "UYARI  docs/kalici.md:1  (tenant host)" in outr, f"cikti={outr[-600:]!r}")
        ekle("R2 --ref: commit MESAJI taranir (transport no, mesaj satiri 3)",
             "UYARI  <commit-mesajı>:3  (transport no)" in outr, f"cikti={outr[-600:]!r}")
        ekle("R3 --ref: bloklayici sinif da UYARI olarak gelir, rc 0 (warn-first)",
             rr == 0 and "UYARI  GENERICIZE-LEAK  docs/ref.md:3  (Z-obje adı)" in outr,
             f"rc={rr} cikti={outr[-600:]!r}")
        ekle("R4 --ref: ciktida TOKEN YOK",
             TR_GERCEK not in outr and Z_SIZINTI not in outr and "a1b2c3d4" not in outr,
             f"cikti={outr[-400:]!r}")
        rr2, outr2 = kos("--ref", "HEAD~2")
        ekle("R5 KONTROL: temiz ref'te bulgu 0 (yalniz taban dosyalari)",
             rr2 == 0 and "sızıntı-sınıfı bulgu 0" in outr2 and "): 0 (bulgu yok)" in outr2,
             f"rc={rr2} cikti={outr2[-500:]!r}")
        rr3, outr3 = kos("--ref", "yok-boyle-bir-ref")
        ekle("R6 cozulmeyen ref: rc 2 + OLCULEMEDI (sessiz 0 DEGIL)",
             rr3 == 2 and "ÖLÇÜLEMEDİ" in outr3, f"rc={rr3} cikti={outr3[-300:]!r}")
        # bug-gate 2026-10-12: kayitli commit mesajinda git yorumu YOKTUR (`-m` varsayilan
        # cleanup `#` satirini SILMEZ — olculdu) => `#` ile baslayan satir yayindaki metindir.
        git("commit", "-q", "--no-verify", "--allow-empty", "-m",
            "ozet\n\n# iletisim: " + EPOSTA + "\n")
        kayitli = git("log", "-1", "--format=%B").stdout
        rr4, outr4 = kos("--ref", "HEAD")
        ekle("R7 --ref: `#` satirindaki e-posta TARANIR (kayitli mesajda git yorumu yok)",
             "# iletisim" in kayitli and rr4 == 0
             and "UYARI  GENERICIZE-LEAK  <commit-mesajı>:3  (kimlik izi)" in outr4
             and EPOSTA not in outr4,
             f"kayitli#={'# iletisim' in kayitli} rc={rr4} cikti={outr4[-500:]!r}")

        # ── M: --msg ───────────────────────────────────────────────────────────
        mesaj = proje / "MSG.txt"
        mesaj.write_text("baslik\n\nhost " + T_IAS + "\n" + Z_SIZINTI + " duzeltildi\n"
                         "# yorum: " + _tr("QB3", "900111") + "\n", encoding="utf-8")
        rm, outm = kos("--msg", str(mesaj))
        ekle("M1 --msg: tenant host + bloklayici sinif raporlanir, rc 0",
             rm == 0 and "UYARI  <commit-mesajı>:3  (tenant host)" in outm
             and "<commit-mesajı>:4  (Z-obje adı)" in outm, f"rc={rm} cikti={outm[-600:]!r}")
        # bug-gate 2026-10-12: OLCULDU — `-m`/`-F` ile yazilan mesajda `#` satiri KAYITLI
        # mesajda kalir ve commit-msg hook'u da gorur => muafiyet kaldirildi, satir TARANIR.
        ekle("M2 --msg: `#` ile baslayan satir da TARANIR (transport no, satir 5)",
             "UYARI  <commit-mesajı>:5  (transport no)" in outm, f"cikti={outm[-600:]!r}")
        ekle("M3 --msg: ciktida TOKEN YOK",
             T_IAS not in outm and Z_SIZINTI not in outm, f"cikti={outm[-300:]!r}")
        rs, outs = kos("--msg", "-", girdi="baslik\n\n" + TR_GERCEK + "\n")
        ekle("M4 --msg - (stdin) okunur",
             rs == 0 and "UYARI  <commit-mesajı>:3  (transport no)" in outs,
             f"rc={rs} cikti={outs[-400:]!r}")
        rt, outt = kos("--msg", "-", girdi="temiz baslik\n\ngovde\n")
        ekle("M5 KONTROL: temiz mesaj 0 bulgu",
             rt == 0 and "sızıntı-sınıfı bulgu 0" in outt and "): 0 (bulgu yok)" in outt,
             f"rc={rt} cikti={outt[-400:]!r}")
        ry, outy = kos("--msg", str(proje / "yok.txt"))
        ekle("M6 okunamayan mesaj dosyasi: rc 2 + OLCULEMEDI",
             ry == 2 and "ÖLÇÜLEMEDİ" in outy, f"rc={ry} cikti={outy[-300:]!r}")
        # Olculen FP (2026-10-12, `--ref` tabanda): ajan atif trailer'i e-posta desenine
        # uyar ve HER ajan commit'inde vardir => muafiyetsiz her mesaj sahte bulgu verirdi.
        ra, outa = kos("--msg", "-", girdi="baslik\n\ngovde\n\n" + ATIF + "\n")
        # bug-gate F3 (2026-10-14): satir BOSALTILMAZ, yalniz uretici adresi maskelenir.
        ekle("M7 ajan atif trailer'i bulgu URETMEZ + maskelenen sayisi basilir",
             ra == 0 and "sızıntı-sınıfı bulgu 0" in outa and "adresi maskelenen 1" in outa,
             f"rc={ra} cikti={outa[-400:]!r}")
        rb, outb = kos("--msg", "-", girdi="baslik\n\n" + ATIF + "\n" + ATIF_BASKA + "\n"
                                           + ATIF_SAHTE + "\n")
        ekle("M8 KONTROL: baska adli trailer TARANIR (muafiyet yalniz atif bicimine)",
             rb == 0 and "UYARI  GENERICIZE-LEAK  <commit-mesajı>:4  (kimlik izi)" in outb
             and "<commit-mesajı>:3" not in outb, f"rc={rb} cikti={outb[-500:]!r}")
        ekle("M9 KONTROL: Claude adli ama BASKA adresli trailer TARANIR (adres bagli)",
             "UYARI  GENERICIZE-LEAK  <commit-mesajı>:5  (kimlik izi)" in outb,
             f"cikti={outb[-500:]!r}")
        rg, outg = kos("--msg", "-", girdi="baslik\n\n" + ATIF_GOVDE_EPOSTA + "\n")
        ekle("M10 Claude + dogru adres AMA aradaki govdede e-posta: satir TARANIR",
             rg == 0 and "UYARI  GENERICIZE-LEAK  <commit-mesajı>:3  (kimlik izi)" in outg
             and "adresi maskelenen 0" in outg and EPOSTA not in outg,
             f"rc={rg} cikti={outg[-500:]!r}")
        # bug-gate 2026-10-14 (F1 kardesi · F3): atif satiri + SONDA e-posta TARANIR;
        # atif satirinin AD bolumundeki obje adi TARANIR (satir bosaltilmaz, adres maskelenir).
        # M12 iki ayri olcu tasir: (a) satir TARANIR — guvenlik; (b) KAPSAM sayaci onu atif
        # satiri SAYMAZ. `--mutasyon-atif-son-capa-yok` YALNIZ (b)'yi dusurur: maskeleme
        # satirin geri kalanini zaten taradigi icin son capa artik guvenlik acisindan
        # ESDEGER mutanttir (olculdu 2026-10-14; guard tarafinda sayac yok ⇒ orada tam esdeger).
        rk, outk = kos("--msg", "-", girdi="baslik\n\n" + ATIF + " " + EPOSTA + "\n")
        ekle("M12 atif satiri + SONDA e-posta: satir TARANIR (kimlik izi, satir 3) + "
             "atif SAYILMAZ (maskelenen 0)",
             rk == 0 and "UYARI  GENERICIZE-LEAK  <commit-mesajı>:3  (kimlik izi)" in outk
             and "adresi maskelenen 0" in outk and EPOSTA not in outk,
             f"rc={rk} cikti={outk[-500:]!r}")
        rz, outz = kos("--msg", "-", girdi="baslik\n\nCo-Authored-By: Claude " + Z_SIZINTI
                                           + " <" + "noreply" + "@" + "anthropic.com>\n")
        ekle("M13 F3 atif satirinin AD bolumundeki obje adi TARANIR (Z-obje, satir 3)",
             rz == 0 and "<commit-mesajı>:3  (Z-obje adı)" in outz
             and "adresi maskelenen 1" in outz and "(kimlik izi)" not in outz
             and Z_SIZINTI not in outz, f"rc={rz} cikti={outz[-500:]!r}")
        # Issue #357 3. BAGLAM: birim cagrisi disinda AYRI surec + commit mesaji giris noktasi.
        # Bolge bicimli ilk etiketli tenant (ara etiketli) mesajda da uyari verir, token basilmaz.
        t_bolge = _h("ab12", "authentication", "eu10", BTP)
        rq, outq = kos("--msg", "-", girdi="baslik\n\nidp https://" + t_bolge + "/oauth\n")
        ekle("M14 --msg: bolge bicimli tenant (ara etiketli) UYARI verir, rc 0, token yok",
             rq == 0 and "UYARI  <commit-mesajı>:3  (tenant host)" in outq
             and t_bolge not in outq and "ab12" not in outq, f"rc={rq} cikti={outq[-400:]!r}")
        # Bos girdi "temiz" DEGILDIR (yanlis dosya / bos boru) — olculemedi ayri raporlanir.
        for ad_, girdi_ in (("M11a bos stdin", ""), ("M11b yalniz bosluk", "\n  \n\n")):
            re_, oute = kos("--msg", "-", girdi=girdi_)
            ekle(ad_ + ": rc 2 + 'bos mesaj — OLCULEMEDI' (sessiz 0 DEGIL)",
                 re_ == 2 and "boş mesaj — ÖLÇÜLEMEDİ" in oute
                 and "sızıntı-sınıfı bulgu" not in oute, f"rc={re_} cikti={oute[-300:]!r}")
        bos = proje / "BOS.txt"
        bos.write_text("", encoding="utf-8")
        rf, outf = kos("--msg", str(bos))
        ekle("M11c bos DOSYA: rc 2 + 'bos mesaj — OLCULEMEDI'",
             rf == 2 and "boş mesaj — ÖLÇÜLEMEDİ" in outf, f"rc={rf} cikti={outf[-300:]!r}")

        # ── U: KULLANIM — modlar birbirini DISLAR (bug-gate 2026-10-12) ──────────
        # Eskiden ilk denetlenen mod sessizce kazaniyor, digeri HIC kosmuyordu.
        for ad_, arg_ in (("U1 --ref + --all", ("--ref", "HEAD", "--all")),
                          ("U2 --msg + --all", ("--msg", str(mesaj), "--all")),
                          ("U3 --msg + --ref", ("--msg", str(mesaj), "--ref", "HEAD")),
                          ("U4 --ref= bicimi + --all", ("--ref=HEAD", "--all"))):
            ru, outu = kos(*arg_)
            ekle(ad_ + ": kullanim hatasi rc 2, tarama YAPILMAZ",
                 ru == 2 and "[KULLANIM]" in outu and "[KAPSAM]" not in outu,
                 f"rc={ru} cikti={outu[-300:]!r}")

        # ── C: SAHTE COMMIT — gercek `git commit` + pre-commit shim (hooksPath) ──
        # 3. BAGLAM: birim cagrisi ve dogrudan kosucu cagrisi disinda, git'in KENDISININ
        # hook'u cagirdigi yol (shim → python → core_precommit). Uyari bu yolda da
        # commit'i bloklamamali; bloklayici sinif hala bloklamali.
        git("config", "core.hooksPath", "scripts/git-hooks")
        (proje / "docs" / "c1.md").write_text("t " + TR_GERCEK + "\n", encoding="utf-8")
        git("add", "docs/c1.md")
        c1 = git("commit", "-m", "c1")
        cikti_c1 = (c1.stdout or "") + (c1.stderr or "")
        ekle("C1 gercek commit: transport iceren dosya commit'LENIR + uyari basilir",
             c1.returncode == 0 and "UYARI  docs/c1.md:1  (transport no)" in cikti_c1,
             f"rc={c1.returncode} cikti={cikti_c1[-500:]!r}")
        (proje / "docs" / "c2.md").write_text("z " + Z_SIZINTI + "_CL_Q\n", encoding="utf-8")
        git("add", "docs/c2.md")
        c2 = git("commit", "-m", "c2")
        ekle("C2 KONTROL: gercek commit bloklayici sinifta BLOKLANIR",
             c2.returncode != 0 and "GENERICIZE-LEAK" in (c2.stdout or "") + (c2.stderr or ""),
             f"rc={c2.returncode}")
    finally:
        _sil(tmp)

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    print(f"\n=== TENANT HOST + TRANSPORT NO (Q361/Q365) "
          f"{'[' + secili + ']' if secili else '[taban]'} ===")
    for ad, ok, detay in SONUC:
        print(f"  [{'OK ' if ok else 'FAIL'}] {ad}" + (f"   -> {detay}" if not ok else ""))
    print(f"\n{gecen}/{len(SONUC)} OK")
    if secili:
        print(f"  (MUTASYON {secili} — dusmesi BEKLENEN vektorler var; "
              "tam skor 'mutasyon KACTI' demektir)")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
