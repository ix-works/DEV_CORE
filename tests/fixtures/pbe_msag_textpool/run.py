#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PULL-BEFORE-EDIT eklentisi — mesaj sınıfı CSV + program textpool (Q352-C) korpusu (SAP'siz).

İki bileşeni GERÇEK giriş noktalarından ölçer:
  · `scripts/hooks/_pbe_msag_textpool.py::sinifla` — kapının eklenti sözleşmesi
  · `scripts/pull_msag_textpool.py::main` — sahte ADT istemcisine karşı (yalnız GET kabul eder;
    GET dışı her çağrı senaryoyu düşürür = salt-okur kanıtı)

Sahte yanıtlar CANLI ÖLÇÜMÜN BİÇİMİNİ taklit eder (2026-09-26, s4_private 2025, yalnız GET):
  textpool gövdesi CRLF, son satırdan sonra CRLF YOK, girdiler alfabetik, metinsiz seçim
  `NAME    =?...` olarak ve gerçek girdilerden SONRA gelir; boş alt kaynak 200 + 0 bayt;
  mesaj sınıfı `mc:messages` + packageRef; olmayan nesne 404. Kimlik/URL taşımaz.

Senaryolar (her biri rc + dosya BAYTLARI + damga sayısı + çağrı kaydıyla ölçülür):
  H1-H9  sinifla: msag adı son-ekten · `messages-all` yer tutucu · ref_docs muaf · adlı textpool
         · çıplak ad + tek program · çıplak ad + iki program → yer tutucu · `.textpool.txt` /
         README / textpool dışı `.txt` → None · kaynak kökü dışı → None · 3. BAĞLAM: `ERP/` kökü
  M1  msag EŞİT → rc 0, dosya BAYT-AYNI, 1 damga, yalnız GET
  M2  msag FARK (CRLF + BOM + tırnaklı): 002 metni + 003 bayrağı yerinde güncellenir, canlıda
      olup yerelde olmayan 000/004 SONA sıralı eklenir, yalnız-yerel 009 DOKUNULMAZ → beklenen
      baytlar birebir, 1 damga
  M3  msag biçim: tırnaksız stil + ham msgno `5` korunur; virgüllü yeni metin zorunlu tırnak alır;
      değişmeyen satırlar bayt-aynı
  M4  ⭐ paket uyuşmazlığı → rc 2, dosya aynı, 0 damga (yanlış ad koruması)
  M5  HTTP 500 → rc 2, 0 damga · M6 dil ≠ master → rc 2 · M7 mükerrer msgno → rc 2
  M8  kapanmayan tırnak → rc 2 · M9 --dry-run fark → rc 0, dosya aynı, 0 damga
  M10 damga yazılamaz ("") → rc 4 (dosya güncel, kapı açılmaz)
  M11 --offline → rc 0, 1 damga, SAP'ye SIFIR çağrı, [OFFLINE] uyarısı
  M12 git-kirli dosya → rc 2 (yazmaz); --force ile rc 0
  M13 yalnız 005'li CSV + canlı 000-005 (ölçülen canlı vakanın biçimi) → 000-004 sona eklenir
  T1  textpool anlamca EŞİT (sıra farkı + `=?...` yer tutucu) → rc 0, bayt-aynı, 1 damga
  T2  textpool FARK (LF dosya): metin güncellenir, canlı-yeni sona eklenir, yalnız-yerel kalır
  T3  symbols: @MaxLength + metin birlikte değişir → girdi iki satırıyla güncellenir
  T4  ⭐ çalışma ≠ active → rc 2, 0 damga · T5 paket uyuşmazlığı → rc 2 · T6 program 404 → rc 2
  T7  canlı alt kaynak BOŞ (0 bayt) + yerel dolu → rc 2 (kimlik kanıtsız), dosya AYNI, 0 damga
  T11 yanlış program: canlıda yalnız `=?...` → rc 2 (ölçülen iki-programlı paket vakası)
  T12 kısmi örtüşme (1 ortak girdi) yeter → rc 0, canlı-yeni sona
  M14 CSV'nin hiçbir msgno'su canlıda yok → rc 2 · M15 yalnız başlıklı CSV canlıdan doldurulur
  M16 ortak msgno var ama metinlerin HEPSİ farklı → hepsi güncellenir, oran basılır (eşik YOK)
  T8  adlı dosya başka programa ait (--program uyuşmaz) → rc 2
  T9  headings (boş değerli girdiler) EŞİT → rc 0
  T10 tek satırlık dosya + canlı-yeni girdi → CRLF ile eklenir
  E1  (A kolu birleşince) kapı uçtan uca: blok → pull damgası → serbest. Kapıda `_EK_DENETCILER`
      yoksa ATLA (sayılmaz, çıktıda görünür).

Mutasyonlar (her biri korpusu KIRMIZI yapmalı; çapa TAM BİR KEZ eşleşmeli):
  MU1 paket koruması sökülür · MU2 ÖLÇÜLEMEDİ dalı damgalar (eşit-değilken damga) ·
  MU3 çalışma≠active denetimi sökülür · MU4 eklenen satır başa yazılır (sıra) ·
  MU5 tırnak stili yok sayılır (biçim) · MU6 satır sonu LF'ye sabitlenir ·
  MU7 yer tutucular gerçek sayılır · MU8 yalnız-yerel textpool girdisi düşer ·
  MU9 ref_docs muafiyeti sökülür · MU10 çıplak ad çok programda ilkini seçer ·
  MU11 msag öz-denetimi etkisiz + sıra bozuk (öz-denetimsiz de test yakalar) ·
  MU12 kimlik (ortak anahtar) denetimi sökülür

Koşum: python tests/fixtures/pbe_msag_textpool/run.py   (exit 0 = PASS)
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from xml.sax.saxutils import escape as _esc

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[2]
SCRIPTS = CORE / "scripts"
PULL_PATH = SCRIPTS / "pull_msag_textpool.py"
HOOK_PATH = SCRIPTS / "hooks" / "_pbe_msag_textpool.py"
KAPI_PATH = SCRIPTS / "hooks" / "pull_before_edit.py"
for _p in (str(SCRIPTS), str(SCRIPTS / "hooks")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_KUM_KOK = Path(tempfile.mkdtemp(prefix="pbe_msag_tp_"))
os.environ["CLAUDE_PROJECT_DIR"] = str(_KUM_KOK)      # source_root çözümü kuma baksın

# populate_message_class import anında stdout'u yeniden sarar → GERÇEK stdout'la ÖNCE yükle,
# eski sarmalayıcıları tut (GC kapatmasın). push_textpool yalnız tip tablosu için.
_REFS = [sys.stdout, sys.stderr]
import populate_message_class  # noqa: E402,F401
import push_textpool  # noqa: E402,F401
_REFS += [sys.stdout, sys.stderr]

PAKET = "ZSD001_CLC"
BASKA_PAKET = "ZSD000_CLC"
SINIF = "ZSD001"
PROG = "ZSD001_P_RAPOR"
NS = 'xmlns:mc="http://www.sap.com/adt/MessageClass" xmlns:adtcore="http://www.sap.com/adt/core"'


def _sil(d: Path) -> None:
    def _ac(func, path, _exc):  # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)  # type: ignore[arg-type]
    except Exception:
        pass


# ─────────────────────────────── sahte ADT ───────────────────────────────

class _Yanit:
    def __init__(self, durum: int, govde: str = ""):
        self.status_code = durum
        self.content = govde.encode("utf-8")
        self.text = govde
        self.headers = {}


def msag_xml(mesajlar: dict, paket=PAKET, ad=SINIF, dil="TR", master="TR") -> str:
    a = lambda s: _esc(s, {'"': "&quot;"})  # noqa: E731
    satir = "".join(
        f'<mc:messages mc:msgno="{n}" mc:msgtext="{a(t)}" mc:selfexplainatory="{s}" '
        f'mc:documented="{d}"/>' for n, (t, s, d) in sorted(mesajlar.items()))
    return (f'<?xml version="1.0" encoding="utf-8"?><mc:messageClass {NS} adtcore:name="{ad}" '
            f'adtcore:masterLanguage="{master}" adtcore:language="{dil}" adtcore:description="d" '
            f'adtcore:responsible="U"><adtcore:packageRef adtcore:type="DEVC/K" '
            f'adtcore:name="{paket}"/>{satir}</mc:messageClass>')


class Sahte:
    """Yalnız GET kabul eder; her çağrıyı kaydeder."""

    def __init__(self, msag=None, msag_durum=200, tp=None, tp_aktif=None, prog_paket=PAKET,
                 prog_durum=200, dil="TR"):
        self.url = "https://sahte.invalid"
        self.language = dil
        self.client = "000"
        self.kayit = []
        self.msag, self.msag_durum = msag, msag_durum
        self.tp = tp or {}
        self.tp_aktif = tp_aktif
        self.prog_paket, self.prog_durum = prog_paket, prog_durum
        self.session = types.SimpleNamespace(get=self._oturum_get, put=self._yasak,
                                             post=self._yasak, delete=self._yasak)

    def _yasak(self, *a, **k):
        self.kayit.append(("YAZMA", a))
        raise AssertionError("GET dışı çağrı — salt-okur ihlali")

    def _oturum_get(self, url, headers=None, params=None, **k):
        self.kayit.append(("GET", url))
        if "/sap/bc/adt/messageclass/" in url:
            if self.msag_durum != 200:
                return _Yanit(self.msag_durum, "<exc/>")
            return _Yanit(200, self.msag)
        return _Yanit(404, "")

    def _get_headers(self, accept_type=None, content_type=None):
        return {"Accept": accept_type or ""}

    def _request_with_csrf_retry(self, method, url, headers=None, timeout=None, **k):
        if method.lower() != "get":
            return self._yasak(method, url)
        self.kayit.append(("GET", url))
        if "/programs/programs/" in url:
            if self.prog_durum != 200:
                return _Yanit(self.prog_durum, "<exc/>")
            return _Yanit(200, f'<program:abapProgram xmlns:adtcore="http://www.sap.com/adt/core">'
                               f'<adtcore:packageRef adtcore:name="{self.prog_paket}"/>'
                               f'</program:abapProgram>')
        if "/textelements/programs/" in url:
            alt = url.split("/source/")[1].split("?")[0]
            kaynak = self.tp_aktif if ("version=active" in url and self.tp_aktif) else self.tp
            return _Yanit(200, kaynak.get(alt, ""))
        return _Yanit(404, "")

    @property
    def yazma(self):
        return [k for k in self.kayit if k[0] != "GET"]


# ─────────────────────────────── yardımcılar ───────────────────────────────

def kum(ad: str) -> Path:
    d = _KUM_KOK / ad
    _sil(d)
    d.mkdir(parents=True)
    return d


def dosya(kok: Path, gorece: str, bayt: bytes) -> Path:
    p = kok / gorece
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(bayt)
    return p


class Damga:
    def __init__(self, sonuc=True):
        self.cagri, self.sonuc = [], sonuc

    def araclar(self):
        return (lambda s: s or "SID-MARKER",
                lambda sid, p: (self.cagri.append((sid, str(p))) or ("K:" + Path(p).name))
                if self.sonuc else "")


def kos(M, argv, client, damga: Damga):
    M.DAMGA_ARACLARI = damga.araclar()
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        try:
            rc = M.main(argv, client=client)
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 1
        except Exception as e:  # noqa: BLE001 — çökme = FAIL satırı, harness'ı düşürmez
            rc = f"COKTU {type(e).__name__}: {e}"
    return rc, tampon.getvalue()


def modul_yukle(ad: str, yol: Path, degisim=None):
    kaynak = yol.read_text(encoding="utf-8")
    if degisim:
        eski, yeni = degisim
        n = kaynak.count(eski)
        if n != 1:
            raise RuntimeError(f"mutasyon çapası {n} kez eşleşti (1 olmalı): {eski[:60]!r}")
        kaynak = kaynak.replace(eski, yeni)
    mod = types.ModuleType(ad)
    mod.__file__ = str(yol)
    sys.modules[ad] = mod
    exec(compile(kaynak, str(yol), "exec"), mod.__dict__)  # noqa: S102
    return mod


# ─────────────────────────────── senaryolar ───────────────────────────────

CANLI = {"001": ("Belge &1 bulunamadı", "false", "true"),
         "002": ("Miktar sıfır olamaz", "false", "false"),
         "003": ('Alan "&1" zorunlu', "true", "false")}
CSV_ESIT = ('msgno,msgtext,selfexplainatory\n001,"Belge &1 bulunamadı",false\n'
            '002,"Miktar sıfır olamaz",false\n003,"Alan ""&1"" zorunlu",true\n')


def senaryolar(M, H):
    s = {}
    msag_yol = f"SOURCE_CODES/SD/{PAKET}/messages-zsd001.csv"
    tp_dizin = f"SOURCE_CODES/SD/{PAKET}/programs/textpool"

    # ---------------- H: sinifla ----------------
    k = kum("h")
    f = dosya(k, msag_yol, b"x")
    r = H.sinifla(f, k)
    s["H1 msag son-ek"] = bool(r and r["nesne"] == "ZSD001" and r["tip"] == "msag"
                                and "--name ZSD001" in r["komut"])
    r = H.sinifla(dosya(k, f"SOURCE_CODES/SD/{PAKET}/messages-all.csv", b"x"), k)
    s["H2 messages-all yer tutucu"] = bool(r and r["nesne"] == H.MSAG_YER_TUTUCU)
    s["H3 ref_docs muaf"] = H.sinifla(
        dosya(k, f"SOURCE_CODES/SD/{PAKET}/ref_docs/messages.csv", b"x"), k) is None
    r = H.sinifla(dosya(k, f"{tp_dizin}/{PROG}.selections.txt", b"x"), k)
    s["H4 adlı textpool"] = bool(r and r["nesne"] == PROG and r["tip"] == "textpool"
                                 and f"--program {PROG}" in r["komut"])
    dosya(k, f"SOURCE_CODES/SD/{PAKET}/programs/{PROG}.prog.abap", b"x")
    r = H.sinifla(dosya(k, f"{tp_dizin}/symbols.txt", b"x"), k)
    s["H5 çıplak ad + tek program"] = bool(r and r["nesne"] == PROG)
    dosya(k, f"SOURCE_CODES/SD/{BASKA_PAKET}/programs/ZSD000_P_A.prog.abap", b"x")
    dosya(k, f"SOURCE_CODES/SD/{BASKA_PAKET}/programs/ZSD000_P_B.prog.abap", b"x")
    r = H.sinifla(dosya(k, f"SOURCE_CODES/SD/{BASKA_PAKET}/programs/textpool/selections.txt",
                        b"x"), k)
    s["H6 çıplak ad + iki program → yer tutucu"] = bool(
        r and r["nesne"] == H.PROG_YER_TUTUCU and "--program" in r["komut"])
    s["H7 kapsam dışı biçimler None"] = all(H.sinifla(dosya(k, g, b"x"), k) is None for g in (
        f"{tp_dizin}/{PROG}.textpool.txt", f"{tp_dizin}/{PROG}.README.md",
        f"SOURCE_CODES/SD/{PAKET}/programs/symbols.txt"))
    s["H8 kaynak kökü dışı None"] = H.sinifla(dosya(k, "notlar/messages-zsd001.csv", b"x"), k) is None
    r = H.sinifla(dosya(k, f"ERP/SD/{BASKA_PAKET}/messages-zsd000.csv", b"x"), k)
    s["H9 3.BAGLAM ERP kökü"] = bool(r and r["nesne"] == "ZSD000")

    # ---------------- M: mesaj sınıfı ----------------
    def msag(ad, bayt, client, *ek, damga=None):
        kk = kum(ad)
        p = dosya(kk, msag_yol, bayt)
        d = damga or Damga()
        rc, out = kos(M, ["msag", "--name", SINIF, "--file", str(p), *ek], client, d)
        return rc, out, p.read_bytes(), d, client

    rc, out, b, d, c = msag("m1", CSV_ESIT.encode(), Sahte(msag=msag_xml(CANLI)))
    s["M1 msag eşit"] = (rc == 0 and b == CSV_ESIT.encode() and len(d.cagri) == 1
                         and not c.yazma and "EŞİT" in out)

    canli2 = dict(CANLI)
    canli2["002"] = ("Miktar negatif olamaz", "false", "false")
    canli2["003"] = ('Alan "&1" zorunlu', "false", "false")
    canli2["000"] = ("&1 &2 &3 &4", "false", "false")
    canli2["004"] = ("Yeni, virgüllü mesaj", "true", "false")
    yerel2 = ('msgno,msgtext,selfexplainatory\r\n001,"Belge &1 bulunamadı",false\r\n'
              '009,"Yerel taslak",false\r\n002,"Miktar sıfır olamaz",false\r\n'
              '003,"Alan ""&1"" zorunlu",true\r\n')
    bek2 = ('msgno,msgtext,selfexplainatory\r\n001,"Belge &1 bulunamadı",false\r\n'
            '009,"Yerel taslak",false\r\n002,"Miktar negatif olamaz",false\r\n'
            '003,"Alan ""&1"" zorunlu",false\r\n000,"&1 &2 &3 &4",false\r\n'
            '004,"Yeni, virgüllü mesaj",true\r\n')
    rc, out, b, d, c = msag("m2", b"\xef\xbb\xbf" + yerel2.encode(), Sahte(msag=msag_xml(canli2)))
    s["M2 msag fark CRLF+BOM+sıra"] = (rc == 0 and b == b"\xef\xbb\xbf" + bek2.encode()
                                      and len(d.cagri) == 1 and "009" in out)

    yerel3 = "msgno,msgtext,selfexplainatory\n5,Eski metin,FALSE\n001,Aynı metin,false\n"
    canli3 = {"005": ("Yeni, metin", "false", "false"), "001": ("Aynı metin", "false", "false")}
    rc, out, b, d, c = msag("m3", yerel3.encode(), Sahte(msag=msag_xml(canli3)))
    s["M3 msag biçim (tırnaksız stil, ham msgno)"] = (
        rc == 0 and b == 'msgno,msgtext,selfexplainatory\n5,"Yeni, metin",FALSE\n'
                         '001,Aynı metin,false\n'.encode())

    yabanci = 'msgno,msgtext,selfexplainatory\n101,"Başka sınıfın mesajı",false\n'
    rc, out, b, d, c = msag("m14", yabanci.encode(), Sahte(msag=msag_xml(CANLI)))
    s["M14 ortak msgno yok → ÖLÇÜLEMEDİ"] = rc == 2 and b == yabanci.encode() and not d.cagri
    hepsi_farkli = {k: (v[0] + " (canlı)", v[1], v[2]) for k, v in CANLI.items()}
    rc, out, b, d, c = msag("m16", CSV_ESIT.encode(), Sahte(msag=msag_xml(hepsi_farkli)))
    s["M16 ortak var, metinlerin HEPSİ farklı → güncellenir + oran basılır (eşik yok)"] = (
        rc == 0 and "güncellenen: 3/3" in out and b.count(" (canlı)".encode()) == 3)
    rc, out, b, d, c = msag("m15",b"msgno,msgtext,selfexplainatory\n", Sahte(msag=msag_xml(CANLI)))
    s["M15 yalnız başlıklı CSV doldurulur"] = rc == 0 and b.count(b"\n") == 4 and len(d.cagri) == 1
    rc, out, b, d, c = msag("m4", CSV_ESIT.encode(), Sahte(msag=msag_xml(canli2, paket=BASKA_PAKET)))
    s["M4 paket uyuşmazlığı"] = rc == 2 and b == CSV_ESIT.encode() and not d.cagri
    rc, out, b, d, c = msag("m5", CSV_ESIT.encode(), Sahte(msag_durum=500))
    s["M5 HTTP 500"] = rc == 2 and b == CSV_ESIT.encode() and not d.cagri
    rc, out, b, d, c = msag("m6", CSV_ESIT.encode(), Sahte(msag=msag_xml(canli2, dil="EN")))
    s["M6 dil != master"] = rc == 2 and not d.cagri
    cift = CSV_ESIT + '1,"Tekrar",false\n'
    rc, out, b, d, c = msag("m7", cift.encode(), Sahte(msag=msag_xml(CANLI)))
    s["M7 mükerrer msgno"] = rc == 2 and b == cift.encode() and not d.cagri
    bozuk = CSV_ESIT + '004,"kapanmayan,false\n'
    rc, out, b, d, c = msag("m8", bozuk.encode(), Sahte(msag=msag_xml(CANLI)))
    s["M8 kapanmayan tırnak"] = rc == 2 and b == bozuk.encode() and not d.cagri
    rc, out, b, d, c = msag("m9", CSV_ESIT.encode(), Sahte(msag=msag_xml(canli2)), "--dry-run")
    s["M9 dry-run"] = rc == 0 and b == CSV_ESIT.encode() and not d.cagri and "FARKLI" in out
    rc, out, b, d, c = msag("m10", CSV_ESIT.encode(), Sahte(msag=msag_xml(canli2)),
                            damga=Damga(sonuc=False))
    s["M10 damga yazılamaz rc4"] = rc == 4 and b != CSV_ESIT.encode()

    class _Patlar:
        def __getattr__(self, a):
            raise AssertionError("offline'da SAP'ye dokunuldu")
    rc, out, b, d, c = msag("m11", CSV_ESIT.encode(), _Patlar(), "--offline")
    s["M11 offline"] = rc == 0 and len(d.cagri) == 1 and "[OFFLINE]" in out

    kk = kum("m12")
    p = dosya(kk, msag_yol, CSV_ESIT.encode())
    g = ["git", "-C", str(kk), "-c", "user.name=fixture", "-c", "user.email=fixture",
         "-c", "core.autocrlf=false"]
    git_ok = all(subprocess.run(x, capture_output=True).returncode == 0 for x in (
        ["git", "init", "-q", str(kk)], g + ["add", "-A"], g + ["commit", "-q", "-m", "t"]))
    p.write_bytes(CSV_ESIT.replace("sıfır", "SIFIR").encode())
    d1 = Damga()
    rc1, _o = kos(M, ["msag", "--name", SINIF, "--file", str(p)], Sahte(msag=msag_xml(CANLI)), d1)
    b1 = p.read_bytes()
    d2 = Damga()
    rc2, _o = kos(M, ["msag", "--name", SINIF, "--file", str(p), "--force"],
                  Sahte(msag=msag_xml(CANLI)), d2)
    s["M12 git-kirli → --force"] = (git_ok and rc1 == 2 and "SIFIR".encode() in b1
                                   and not d1.cagri and rc2 == 0
                                   and p.read_bytes() == CSV_ESIT.encode())

    canli13 = {f"00{i}": (f"Mesaj {i}", "false", "true" if i % 2 else "false") for i in range(6)}
    yerel13 = 'msgno,msgtext,selfexplainatory\n005,"Mesaj 5",false\n'
    rc, out, b, d, c = msag("m13", yerel13.encode(), Sahte(msag=msag_xml(canli13)))
    s["M13 tek satırlı CSV + canlı 000-005"] = rc == 0 and b == (
        yerel13 + "".join(f'00{i},"Mesaj {i}",false\n' for i in range(5))).encode()

    # ---------------- T: textpool ----------------
    def tp(ad, gorece, bayt, client, *ek, program=PROG):
        kk = kum(ad)
        p = dosya(kk, f"{tp_dizin}/{gorece}", bayt)
        d = Damga()
        rc, out = kos(M, ["textpool", "--program", program, "--file", str(p), *ek], client, d)
        return rc, out, p.read_bytes(), d, client

    sel_canli = ("P_DATE  =Tarih\r\n\r\nP_FILE  =Dosya\r\n\r\nS_KUNNR =Müşteri\r\n\r\n"
                 "P_MAX   =?...\r\n\r\nS_STAT  =?...")
    sel_yerel = "S_KUNNR =Müşteri\r\n\r\nP_FILE  =Dosya\r\n\r\nP_DATE  =Tarih\r\n"
    rc, out, b, d, c = tp("t1", f"{PROG}.selections.txt", sel_yerel.encode(),
                          Sahte(tp={"selections": sel_canli}))
    s["T1 textpool anlamca eşit"] = (rc == 0 and b == sel_yerel.encode() and len(d.cagri) == 1
                                     and not c.yazma and "EŞİT" in out)

    sel_canli2 = "P_DATE  =Tarih (yeni)\n\nP_NEW   =Yeni alan\n\nS_KUNNR =Müşteri\n\nP_MAX   =?..."
    sel_yerel2 = "S_KUNNR =Müşteri\n\nP_WIP   =Yerel\n\nP_DATE  =Tarih\n"
    bek = "S_KUNNR =Müşteri\n\nP_WIP   =Yerel\n\nP_DATE  =Tarih (yeni)\n\nP_NEW   =Yeni alan\n"
    rc, out, b, d, c = tp("t2", "selections.txt", sel_yerel2.encode(),
                          Sahte(tp={"selections": sel_canli2.replace("\n", "\r\n")}))
    s["T2 textpool fark LF + sıra + yalnız-yerel"] = (rc == 0 and b == bek.encode()
                                                      and len(d.cagri) == 1 and "P_WIP" in out)

    sym_yerel = "@MaxLength:5\nB01=Devam\n\n@MaxLength:6\nB02=Vazgeç\n"
    sym_canli = "@MaxLength:5\r\nB01=Devam\r\n\r\n@MaxLength:10\r\nB02=Vazgeç Hep"
    rc, out, b, d, c = tp("t3", f"{PROG}.symbols.txt", sym_yerel.encode(),
                          Sahte(tp={"symbols": sym_canli}))
    s["T3 symbols @MaxLength+metin"] = rc == 0 and b == (
        "@MaxLength:5\nB01=Devam\n\n@MaxLength:10\nB02=Vazgeç Hep\n").encode()

    rc, out, b, d, c = tp("t4", f"{PROG}.selections.txt", sel_yerel.encode(),
                          Sahte(tp={"selections": sel_canli},
                                tp_aktif={"selections": "P_DATE  =Eski"}))
    s["T4 çalışma != active"] = rc == 2 and b == sel_yerel.encode() and not d.cagri
    rc, out, b, d, c = tp("t5", f"{PROG}.selections.txt", sel_yerel.encode(),
                          Sahte(tp={"selections": sel_canli2}, prog_paket=BASKA_PAKET))
    s["T5 paket uyuşmazlığı"] = rc == 2 and b == sel_yerel.encode() and not d.cagri
    rc, out, b, d, c = tp("t6", f"{PROG}.selections.txt", sel_yerel.encode(),
                          Sahte(tp={"selections": sel_canli2}, prog_durum=404))
    s["T6 program 404"] = rc == 2 and not d.cagri
    sym_bos = "@MaxLength:30\nB01=Teslimat Planı Excel Dosyası\n"
    rc, out, b, d, c = tp("t7", "symbols.txt", sym_bos.encode(), Sahte(tp={"symbols": ""}))
    s["T7 canlı boş → kimlik kanıtsız, ÖLÇÜLEMEDİ"] = (rc == 2 and b == sym_bos.encode()
                                                     and not d.cagri)
    rc, out, b, d, c = tp("t11", "selections.txt", "P_FILE  =Excel Dosyası\n".encode(),
                          Sahte(tp={"selections": "P_FILE  =?...\r\n\r\nP_MAX   =?..."}))
    s["T11 yanlış program (yalnız yer tutucu) → ÖLÇÜLEMEDİ"] = rc == 2 and not d.cagri
    rc, out, b, d, c = tp("t12", f"{PROG}.selections.txt", "P_WIP   =Yerel\n".encode(),
                          Sahte(tp={"selections": "P_WIP   =Yerel\r\n\r\nP_YENI  =Yeni"}))
    s["T12 kısmi örtüşme yeterli"] = rc == 0 and b == "P_WIP   =Yerel\n\nP_YENI  =Yeni\n".encode()
    rc, out, b, d, c = tp("t8", "ZSD001_P_BASKA.selections.txt", sel_yerel.encode(),
                          Sahte(tp={"selections": sel_canli}))
    s["T8 dosya başka programa ait"] = rc == 2 and not d.cagri
    hd = "listHeader=\r\n\r\ncolumnHeader_1=\r\ncolumnHeader_2="
    rc, out, b, d, c = tp("t9", f"{PROG}.headings.txt", hd.encode(), Sahte(tp={"headings": hd}))
    s["T9 headings eşit"] = rc == 0 and b == hd.encode() and len(d.cagri) == 1
    rc, out, b, d, c = tp("t10", f"{PROG}.selections.txt", "P_REFDT =Referans".encode(),
                          Sahte(tp={"selections": "P_ESIK  =Eşik\r\n\r\nP_REFDT =Referans"}))
    s["T10 tek satır + eklenen CRLF"] = rc == 0 and b == \
        "P_REFDT =Referans\r\n\r\nP_ESIK  =Eşik".encode()
    return s


def e2e(M) -> str:
    """A kolunun kapısı ağaçtaysa uçtan uca: blok → pull damgası → serbest."""
    kapi = KAPI_PATH.read_text(encoding="utf-8") if KAPI_PATH.exists() else ""
    if "_EK_DENETCILER" not in kapi or '"_pbe_msag_textpool"' not in kapi:
        return "ATLA (kapıda eklenti kaydı yok — A kolu birleşince ölçülür)"
    try:
        import source_drift as sd  # noqa: E402
        seans_kimligi, tazelik_damgala = sd.seans_kimligi, sd.tazelik_damgala
    except Exception as e:  # noqa: BLE001
        return f"FAIL (source_drift arayüzü yok: {e})"
    kk = kum("e2e")
    p = dosya(kk, f"SOURCE_CODES/SD/{PAKET}/messages-zsd001.csv", CSV_ESIT.encode())
    sd.ROOT = kk
    sd.FRESH_STORE = kk / ".claude" / ".session_fresh.json"
    sd.FRESH_STORE.parent.mkdir(parents=True, exist_ok=True)
    yuk = json.dumps({"tool_name": "Edit", "session_id": "SID-E2E",
                      "tool_input": {"file_path": str(p)}})
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(kk))

    def kapi_kos():
        return subprocess.run([sys.executable, str(KAPI_PATH)], input=yuk, capture_output=True,
                              text=True, encoding="utf-8", env=env, timeout=60)
    r1 = kapi_kos()
    M.DAMGA_ARACLARI = (seans_kimligi, tazelik_damgala)
    with contextlib.redirect_stdout(io.StringIO()):
        rc = M.main(["msag", "--name", SINIF, "--file", str(p), "--session", "SID-E2E"],
                    client=Sahte(msag=msag_xml(CANLI)))
    r2 = kapi_kos()
    ok = r1.returncode == 2 and "pull_msag_textpool.py msag" in r1.stderr and rc == 0 \
        and r2.returncode == 0
    if not ok:
        return (f"FAIL msag (blok rc={r1.returncode} pull rc={rc} sonra rc={r2.returncode}: "
                f"{r1.stderr[-300:]!r})")
    # Textpool, çıplak ad + İKİ program: kapı yer tutucu komutla bloklar; `--program` ile
    # koşulan pull o DOSYAYI damgalar → kapı serbest (yer tutucu kalıcı kilit DEĞİL).
    dosya(kk, f"SOURCE_CODES/SD/{BASKA_PAKET}/programs/ZSD000_P_A.prog.abap", b"x")
    dosya(kk, f"SOURCE_CODES/SD/{BASKA_PAKET}/programs/ZSD000_P_B.prog.abap", b"x")
    t = dosya(kk, f"SOURCE_CODES/SD/{BASKA_PAKET}/programs/textpool/selections.txt",
              "P_FILE  =Dosya\n".encode())
    yuk = json.dumps({"tool_name": "Write", "session_id": "SID-E2E",
                      "tool_input": {"file_path": str(t)}})
    t1 = kapi_kos()
    with contextlib.redirect_stdout(io.StringIO()):
        rct = M.main(["textpool", "--program", "ZSD000_P_A", "--file", str(t),
                      "--session", "SID-E2E"],
                     client=Sahte(tp={"selections": "P_FILE  =Dosya"}, prog_paket=BASKA_PAKET))
    t2 = kapi_kos()
    ok = t1.returncode == 2 and "<PROGRAM_ADI>" in t1.stderr and "--offline" in t1.stderr \
        and rct == 0 and t2.returncode == 0
    return ("PASS (msag + textpool yer tutucu)" if ok else
            f"FAIL textpool (blok rc={t1.returncode} pull rc={rct} sonra rc={t2.returncode}: "
            f"{t1.stderr[-300:]!r})")


MUTASYONLAR = [
    ("MU1 paket koruması sökülür", PULL_PATH,
     'if (canli_paket or "").upper() != beklenen:', "if False:"),
    ("MU2 ÖLÇÜLEMEDİ dalı damgalar", PULL_PATH,
     "        _kapsam_bas(KAPSAM_MSAG)\n        return 2",
     "        _kapsam_bas(KAPSAM_MSAG)\n        return _damgala(session, dosya)"),
    ("MU3 çalışma≠active denetimi sökülür", PULL_PATH,
     "if _tp_sozluk(tp_ayristir(calisma), True) != _tp_sozluk(tp_ayristir(aktif), True):",
     "if False:"),
    ("MU4 eklenen satır başa yazılır (sıra)", PULL_PATH,
     '            alanlar[m["ise"]] = (c[k][1], False)\n        yeni.append(',
     '            alanlar[m["ise"]] = (c[k][1], False)\n        yeni.insert(1, '),
    ("MU5 tırnak stili yok sayılır (biçim)", PULL_PATH,
     "    if tirnakli or any(", "    if any("),
    ("MU6 satır sonu LF'ye sabitlenir", PULL_PATH,
     'metin = bicim["ss"].join(satirlar)', 'metin = "\\n".join(satirlar)'),
    ("MU7 yer tutucular gerçek sayılır", PULL_PATH,
     '_TP_YER_TUTUCU = ("?", "?...")', "_TP_YER_TUTUCU = ()"),
    ("MU8 yalnız-yerel textpool girdisi düşer", PULL_PATH,
     "            yerel_yalniz.append(k)\n            yeni.extend(o[2])",
     "            yerel_yalniz.append(k)"),
    ("MU9 ref_docs muafiyeti sökülür", HOOK_PATH,
     "    return not (_MUAF_KLASORLER & parts)", "    return True"),
    ("MU10 çıplak ad çok programda ilkini seçer", HOOK_PATH,
     "    if len(adaylar) != 1:", "    if not adaylar:"),
    ("MU12 kimlik (ortak anahtar) denetimi sökülür", PULL_PATH,
     "    if yerel and not (set(yerel) & set(canli)):", "    if False:"),
    ("MU11 msag öz-denetimi etkisiz + sıra bozuk", PULL_PATH,
     "        hatalar = msag_oz_denetim(yeni, rapor)\n",
     "        hatalar = []\n        yeni = [yeni[0]] + yeni[1:][::-1]\n"),
]


def kos_hepsi(pull_degisim=None, hook_degisim=None):
    H = modul_yukle("_pbe_msag_textpool", HOOK_PATH, hook_degisim)
    M = modul_yukle("pull_msag_textpool", PULL_PATH, pull_degisim)
    return senaryolar(M, H), M


def main() -> int:
    e = "?"
    try:
        taban, M = kos_hepsi()
        print("--- TABAN ---")
        for ad, ok in taban.items():
            print(f"  {'PASS' if ok else 'FAIL'}  {ad}")
        e = e2e(M)
        print(f"  E1 kapı uçtan uca: {e}")
        hata = [a for a, ok in taban.items() if not ok] + (["E1"] if e.startswith("FAIL") else [])
        print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmalı) ---")
        kacan = []
        for ad, yol, eski, yeni in MUTASYONLAR:
            if yol == HOOK_PATH:
                sonuc, _ = kos_hepsi(hook_degisim=(eski, yeni))
            else:
                sonuc, _ = kos_hepsi(pull_degisim=(eski, yeni))
            dusen = [a for a, ok in sonuc.items() if not ok and taban.get(a)]
            print(f"  {'DUSTU' if dusen else 'KACTI'}  {ad}  ← {dusen[:3]}")
            if not dusen:
                kacan.append(ad)
        kos_hepsi()                                  # temiz modülleri geri yükle
    finally:
        _sil(_KUM_KOK)
    if hata or kacan:
        print(f"\nFAIL — taban hataları {hata} · kaçan mutasyonlar {kacan}")
        return 1
    print(f"\nPASS — {len(taban)} senaryo + {len(MUTASYONLAR)} mutasyon · E1: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
