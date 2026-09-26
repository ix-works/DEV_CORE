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
  --- bug-gate düzeltme turu (PR #308, 2026-09-26) ---
  H10 adlı textpool Z/Y dışı ad → None · H11 muaf küme = source_drift (canlı + yedek eşit)
  M17 karışık satır sonu + anlamca eşit → YAZILMAZ (dry-run da "EŞİT") · T13 aynısı textpool
  M18 canlı boş metin (yerelde yok) → EKLENMEZ, [ATLANDI], damga; sonuç populate okuyucusundan
      geçer · M19 canlı boş / yerel metinli → ÖLÇÜLEMEDİ
  M20 selfexp sütunsuz CSV + canlı true → ÖLÇÜLEMEDİ (teşhis metniyle) · M21 canlı baş/son
      boşluk → strip'li eşit · M22 yanıt sınıf adı ≠ istenen → ÖLÇÜLEMEDİ · M23 csv_modeli satır
      içi CR (birim) · M24 canlı metinde satır sonu → ÖLÇÜLEMEDİ · M25 mojibake uyarısı + FP
  T14 yalnız `@` özniteliği farklı → güncellenir · T15 okunan oturum dili kapsamda basılır
  L1 `[PULL]` başlığı gerçek pipe'lı alt süreçte İLK satır · L3 paket_dizini SON kök eşleşmesi
  L4 `--cwd` kabul edilmez (tek kök kaynağı)
  --- 2. bug-gate turu (209bb95) ---
  H12 `..` (docs/.. muaf segmenti · textpool/x/.. ebeveyn) kararı kandırmaz; E1 aynısını gerçek
      kapıda ölçer (damgasız seans → exit 2; gerçek boş `docs`/`x` dizini — POSIX ENOENT notu)
  M12b commit'li TEMİZ dosya → --force'suz rc 0 + damga (stub'ın kör bıraktığı yön)
  T16 textpool git-kirli → --force · M26 mojibake deseni birim (Ö → U+2013) + yabancı FP yok
  M27 yerel boş + canlı boş → EŞİT + damga

Mutasyonlar (her biri korpusu KIRMIZI yapmalı; çapa TAM BİR KEZ eşleşmeli):
  MU1 paket koruması sökülür · MU2 ÖLÇÜLEMEDİ dalı damgalar (eşit-değilken damga) ·
  MU3 çalışma≠active denetimi sökülür · MU4 eklenen satır başa yazılır (sıra) ·
  MU5 tırnak stili yok sayılır (biçim) · MU6 satır sonu LF'ye sabitlenir ·
  MU7 yer tutucular gerçek sayılır · MU8 yalnız-yerel textpool girdisi düşer ·
  MU9 ref_docs muafiyeti sökülür · MU10 çıplak ad çok programda ilkini seçer ·
  MU11 msag öz-denetimi etkisiz + sıra bozuk (öz-denetimsiz de test yakalar) ·
  MU12 kimlik (ortak anahtar) denetimi sökülür · MU13-15 komut/not sözleşmesi ·
  MU16-33 bug-gate bulgularının her biri KENDİ vektörüyle (liste MUTASYONLAR'da, etiket
  `[M1]`/`[MX2]`/`[L3]`…). MU27 (L1) yalnız win32'de ölçülür — kusur yalnız orada var
  (populate stdout'u yalnız win32'de yeniden sarar); başka platformda görünür ATLA basılır.
  HEDEF: her mutasyonun düşürmesi ZORUNLU senaryolar; biri ayakta kalırsa HEDEF-KACTI = FAIL.
  MALİYET: PAHALI senaryolar (L1 alt süreç, M12 git) yalnız TABAN + onları hedefleyen kipte
  koşar; atlanan koşum `[ATLA-MALIYET]` satırıyla beyan edilir. `_git_kirli` M12 dışında
  sabit False (kum git deposu değil → gerçeği de False döner; ölçülen maliyet ~2,6 sn/geçiş).

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
    # Öznitelikteki satır sonu karakter referansıyla (XML öznitelik normalizasyonu çıplak
    # satır sonunu BOŞLUĞA çevirir — gerçek sunucu da referansla gönderir).
    a = lambda s: _esc(s, {'"': "&quot;", "\n": "&#10;", "\r": "&#13;"})  # noqa: E731
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
    mod.__kaynak__ = kaynak                      # L1 alt süreci AYNI (mutasyonlu) metni koşar
    sys.modules[ad] = mod
    exec(compile(kaynak, str(yol), "exec"), mod.__dict__)  # noqa: S102
    return mod


# ─────────────────────────────── senaryolar ───────────────────────────────

CANLI = {"001": ("Belge &1 bulunamadı", "false", "true"),
         "002": ("Miktar sıfır olamaz", "false", "false"),
         "003": ('Alan "&1" zorunlu', "true", "false")}
CSV_ESIT = ('msgno,msgtext,selfexplainatory\n001,"Belge &1 bulunamadı",false\n'
            '002,"Miktar sıfır olamaz",false\n003,"Alan ""&1"" zorunlu",true\n')


def _saf(r) -> bool:
    """Komut/not sözleşmesi (Q352): `komut` YALNIZ çalıştırılabilir komut — kapı sonuna
    `--session` ekler ⇒ eklenti `--session` basmaz, açıklama/kaçış komutun arkasına yazılmaz;
    kaçış (`--offline`/`--dry-run`) `not` alanında."""
    k, n = r.get("komut", ""), r.get("not", "")
    return ("--session" not in k and "\n" not in k and "--offline" not in k
            and "--dry-run" not in k and k.rstrip().endswith('"')
            and isinstance(n, str) and "--offline" in n and "--dry-run" in n)


PAHALI = ("L1", "M12")   # ≥0,4 sn/koşum: gerçek alt süreç (L1) · git init/commit (M12)
# Pahalı blok → içinde ölçülen senaryo kimlikleri (M12 bloğu tek git deposu kurar).
PAHALI_SENARYO = {"L1": ("L1",), "M12": ("M12", "M12b", "T16")}


def senaryolar(M, H, pahali=PAHALI):
    """`pahali`: bu koşumda koşulacak PAHALI senaryo kimlikleri (taban: hepsi; mutasyon: yalnız
    onu hedefleyenler — main() atlananı `[ATLA-MALIYET]` satırıyla beyan eder)."""
    s = {}
    # MALİYET (ölçüldü 2026-09-26: git çağrısı ~65 ms × ~40 pull/koşum = geçiş başına ~2,6 sn):
    # kum dizinleri git deposu DEĞİL → gerçek `_git_kirli` de `git status` rc≠0 ile False döner.
    # Bu yüzden M12 DIŞINDA sonuç-eşdeğer sabitle değiştirilir; gerçek fonksiyon yalnız M12'de
    # (gerçek git deposunda) ölçülür — git-kirli korumasının vektörü M12, mutasyonu MU33.
    _gercek_git_kirli = M._git_kirli
    M._git_kirli = lambda _dosya: False
    msag_yol = f"SOURCE_CODES/SD/{PAKET}/messages-zsd001.csv"
    tp_dizin = f"SOURCE_CODES/SD/{PAKET}/programs/textpool"

    # ---------------- H: sinifla ----------------
    k = kum("h")
    f = dosya(k, msag_yol, b"x")
    r = H.sinifla(f, k)
    s["H1 msag son-ek"] = bool(r and r["nesne"] == "ZSD001" and r["tip"] == "msag"
                                and "--name ZSD001" in r["komut"] and _saf(r)
                                and "<MSAG_ADI>" not in r["not"])
    r = H.sinifla(dosya(k, f"SOURCE_CODES/SD/{PAKET}/messages-all.csv", b"x"), k)
    s["H2 messages-all yer tutucu"] = bool(r and r["nesne"] == H.MSAG_YER_TUTUCU and _saf(r)
                                           and "<MSAG_ADI>" in r["not"])
    s["H3 ref_docs muaf"] = H.sinifla(
        dosya(k, f"SOURCE_CODES/SD/{PAKET}/ref_docs/messages.csv", b"x"), k) is None
    r = H.sinifla(dosya(k, f"{tp_dizin}/{PROG}.selections.txt", b"x"), k)
    s["H4 adlı textpool"] = bool(r and r["nesne"] == PROG and r["tip"] == "textpool"
                                 and f"--program {PROG}" in r["komut"] and _saf(r)
                                 and "<PROGRAM_ADI>" not in r["not"])
    dosya(k, f"SOURCE_CODES/SD/{PAKET}/programs/{PROG}.prog.abap", b"x")
    r = H.sinifla(dosya(k, f"{tp_dizin}/symbols.txt", b"x"), k)
    s["H5 çıplak ad + tek program"] = bool(r and r["nesne"] == PROG)
    dosya(k, f"SOURCE_CODES/SD/{BASKA_PAKET}/programs/ZSD000_P_A.prog.abap", b"x")
    dosya(k, f"SOURCE_CODES/SD/{BASKA_PAKET}/programs/ZSD000_P_B.prog.abap", b"x")
    r = H.sinifla(dosya(k, f"SOURCE_CODES/SD/{BASKA_PAKET}/programs/textpool/selections.txt",
                        b"x"), k)
    s["H6 çıplak ad + iki program → yer tutucu"] = bool(
        r and r["nesne"] == H.PROG_YER_TUTUCU and "--program <PROGRAM_ADI>" in r["komut"]
        and _saf(r) and "<PROGRAM_ADI> yerine" in r["not"])
    s["H7 kapsam dışı biçimler None"] = all(H.sinifla(dosya(k, g, b"x"), k) is None for g in (
        f"{tp_dizin}/{PROG}.textpool.txt", f"{tp_dizin}/{PROG}.README.md",
        f"SOURCE_CODES/SD/{PAKET}/programs/symbols.txt"))
    s["H8 kaynak kökü dışı None"] = H.sinifla(dosya(k, "notlar/messages-zsd001.csv", b"x"), k) is None
    r = H.sinifla(dosya(k, f"ERP/SD/{BASKA_PAKET}/messages-zsd000.csv", b"x"), k)
    s["H9 3.BAGLAM ERP kökü"] = bool(r and r["nesne"] == "ZSD000")
    # MX12: adlı textpool dosyasında program adı Z/Y değilse eklentinin işi değil.
    s["H10 adlı textpool Z/Y dışı ad → None"] = H.sinifla(
        dosya(k, f"{tp_dizin}/RSDEMO01.selections.txt", b"x"), k) is None
    # Öneri (c): muaf küme TEK kaynaktan; yedek de kaynakla EŞİT kalmalı (sessiz ayrışma yok).
    import source_drift as _sd  # noqa: E402
    s["H11 muaf küme = source_drift (canlı + yedek)"] = (
        H._MUAF_KLASORLER == set(_sd._EXCLUDED_DIR_SEGMENTS) == set(H._MUAF_YEDEK))
    # H12 (Q352 2. tur, kardeş sınıf): kapı HAM yol verir; `..` muaf segmenti/ebeveyn adı
    # kararı kandırmamalı (ölçüldü: üç biçim de gerçek kapıda exit 0 = SAHTE-MUAF idi).
    sep = os.sep
    dd = str(k / "SOURCE_CODES" / "docs") + sep + ".." + sep + "SD" + sep + PAKET + sep
    r1 = H.sinifla(dd + "messages-zsd001.csv", k)
    r2 = H.sinifla(dd + "programs" + sep + "textpool" + sep + f"{PROG}.selections.txt", k)
    r3 = H.sinifla(str(k / tp_dizin / "x") + sep + ".." + sep + f"{PROG}.symbols.txt", k)
    s["H12 `..` sahte-muaf/ebeveyn kandırmaz"] = bool(
        r1 and r1["nesne"] == "ZSD001" and r2 and r2["nesne"] == PROG
        and r3 and r3["nesne"] == PROG and ".." not in r1["komut"])

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

    if "M12" in pahali:
        M._git_kirli = _gercek_git_kirli
        kk = kum("m12")
        p = dosya(kk, msag_yol, CSV_ESIT.encode())
        tpf = dosya(kk, f"{tp_dizin}/{PROG}.selections.txt", b"P_DATE  =Tarih\n")
        g = ["git", "-C", str(kk), "-c", "user.name=fixture", "-c", "user.email=fixture",
             "-c", "core.autocrlf=false"]
        git_ok = all(subprocess.run(x, capture_output=True).returncode == 0 for x in (
            ["git", "init", "-q", str(kk)], g + ["add", "-A"], g + ["commit", "-q", "-m", "t"]))
        # M12b (2. tur MEDIUM): commit'li TEMİZ dosya → --force'suz rc 0 + damga. Stub
        # `_git_kirli`yi yalnız False yönünde sabitlediği için "daima True" kusuru buradan görünür.
        d0 = Damga()
        rc0, _o = kos(M, ["msag", "--name", SINIF, "--file", str(p)],
                      Sahte(msag=msag_xml(CANLI)), d0)
        s["M12b git-temiz commit'li dosya → --force'suz rc 0 + damga"] = (
            git_ok and rc0 == 0 and len(d0.cagri) == 1 and p.read_bytes() == CSV_ESIT.encode())
        p.write_bytes(CSV_ESIT.replace("sıfır", "SIFIR").encode())
        d1 = Damga()
        rc1, _o = kos(M, ["msag", "--name", SINIF, "--file", str(p)],
                      Sahte(msag=msag_xml(CANLI)), d1)
        b1 = p.read_bytes()
        d2 = Damga()
        rc2, _o = kos(M, ["msag", "--name", SINIF, "--file", str(p), "--force"],
                      Sahte(msag=msag_xml(CANLI)), d2)
        s["M12 git-kirli → --force"] = (git_ok and rc1 == 2 and "SIFIR".encode() in b1
                                       and not d1.cagri and rc2 == 0
                                       and p.read_bytes() == CSV_ESIT.encode())
        # T16 (2. tur öneri 4): textpool yolunun AYRI git-kirli koruması.
        tpf.write_bytes(b"P_DATE  =TARIH\n")
        d3 = Damga()
        rc3, _o = kos(M, ["textpool", "--program", PROG, "--file", str(tpf)],
                      Sahte(tp={"selections": "P_DATE  =Tarih"}), d3)
        b3 = tpf.read_bytes()
        d4 = Damga()
        rc4, _o = kos(M, ["textpool", "--program", PROG, "--file", str(tpf), "--force"],
                      Sahte(tp={"selections": "P_DATE  =Tarih"}), d4)
        s["T16 textpool git-kirli → --force"] = (
            git_ok and rc3 == 2 and b3 == b"P_DATE  =TARIH\n" and not d3.cagri and rc4 == 0
            and tpf.read_bytes() == b"P_DATE  =Tarih\n")
        M._git_kirli = lambda _dosya: False

    canli13 = {f"00{i}": (f"Mesaj {i}", "false", "true" if i % 2 else "false") for i in range(6)}
    yerel13 = 'msgno,msgtext,selfexplainatory\n005,"Mesaj 5",false\n'
    rc, out, b, d, c = msag("m13", yerel13.encode(), Sahte(msag=msag_xml(canli13)))
    s["M13 tek satırlı CSV + canlı 000-005"] = rc == 0 and b == (
        yerel13 + "".join(f'00{i},"Mesaj {i}",false\n' for i in range(5))).encode()

    # --- bug-gate düzeltme turu (Q352, 2026-09-26) ---
    # M17 (bug-gate M1): karışık satır sonu + anlamca EŞİT → dosya bayt-aynı, dry-run "EŞİT".
    karisik = ('msgno,msgtext,selfexplainatory\r\n001,"Belge &1 bulunamadı",false\n'
               '002,"Miktar sıfır olamaz",false\r\n003,"Alan ""&1"" zorunlu",true\n')
    rc, out, b, d, c = msag("m17", karisik.encode(), Sahte(msag=msag_xml(CANLI)))
    rc_d, out_d, b_d, d_d, _c = msag("m17d", karisik.encode(), Sahte(msag=msag_xml(CANLI)),
                                     "--dry-run")
    s["M17 karışık satır sonu + eşit → YAZILMAZ"] = (
        rc == 0 and b == karisik.encode() and len(d.cagri) == 1 and "EŞİT" in out
        and rc_d == 0 and b_d == karisik.encode() and "EŞİT" in out_d and "FARKLI" not in out_d)

    # M18 (bug-gate M2): canlıda metni BOŞ mesaj, yerelde yok → EKLENMEZ, [ATLANDI], damga;
    # sonuç dosyası GERÇEK populate okuyucusundan geçmeli (MesajSatiriEksikError YOK).
    import populate_message_class as _pmc  # noqa: E402
    canli18 = dict(CANLI)
    canli18["004"] = ("", "true", "false")          # ölçülen canlı biçim: ('', 'true', 'false')
    rc, out, b, d, c = msag("m18", CSV_ESIT.encode(), Sahte(msag=msag_xml(canli18)))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            yuklenen = _pmc.load_messages_from_csv(_KUM_KOK / "m18" / msag_yol)
        pop_ok = [m[0] for m in yuklenen] == ["001", "002", "003"]
    except Exception:  # noqa: BLE001
        pop_ok = False
    s["M18 canlı boş metin (yerelde yok) → ATLANDI, populate geçer"] = (
        rc == 0 and b == CSV_ESIT.encode() and len(d.cagri) == 1 and "[ATLANDI]" in out
        and "004" in out and pop_ok)
    # M19: canlıda boş, yerelde METİNLİ → push canlıdaki boşu ezer → ÖLÇÜLEMEDİ.
    canli19 = dict(CANLI)
    canli19["002"] = ("", "false", "false")
    rc, out, b, d, c = msag("m19", CSV_ESIT.encode(), Sahte(msag=msag_xml(canli19)))
    s["M19 canlı boş / yerel metinli → ÖLÇÜLEMEDİ"] = (rc == 2 and b == CSV_ESIT.encode()
                                                      and not d.cagri)
    # M20 (MX6): CSV'de selfexplainatory sütunu yok, canlıda true var → temsil edilemez.
    ikili = 'msgno,msgtext\n001,"Belge &1 bulunamadı"\n002,"Miktar sıfır olamaz"\n'
    rc, out, b, d, c = msag("m20", ikili.encode(), Sahte(msag=msag_xml(CANLI)))
    # Öz-denetim de aynı sonucu (rc 2) verir → mutasyonu ayırt eden TEŞHİS metnidir: kullanıcıya
    # "sütun yok" demek, "öz-denetim tutmadı" demekten farklı bir onarım söyler.
    s["M20 selfexp sütunu yok + canlı true → ÖLÇÜLEMEDİ"] = (
        rc == 2 and b == ikili.encode() and not d.cagri
        and "selfexplainatory sütunu yok" in out)
    # M21 (MX8): canlı metinde baş/son boşluk, yerel strip'li → anlamca EŞİT + uyarı.
    canli21 = dict(CANLI)
    canli21["002"] = ("  Miktar sıfır olamaz ", "false", "false")
    rc, out, b, d, c = msag("m21", CSV_ESIT.encode(), Sahte(msag=msag_xml(canli21)))
    s["M21 canlı baş/son boşluk → strip'li eşit + uyarı"] = (
        rc == 0 and b == CSV_ESIT.encode() and len(d.cagri) == 1 and "baş/son boşluk" in out)
    # M22 (MX9): yanıttaki sınıf adı istenen değil (paket aynı) → ÖLÇÜLEMEDİ.
    rc, out, b, d, c = msag("m22", CSV_ESIT.encode(), Sahte(msag=msag_xml(CANLI, ad="ZSD000")))
    s["M22 yanıt sınıf adı ≠ istenen → ÖLÇÜLEMEDİ"] = rc == 2 and not d.cagri
    # M23 (MX7): csv modülü çapraz denetimi — el ayrıştırıcısıyla csv modülünün AYRIŞTIĞI tek
    # ölçülen girdi sınıfı satır içi CR/LF'dir (fuzz: a , " boşluk NUL TAB → 0 ayrışma).
    # Dosya yolunda satırlar zaten bölünür ⇒ bu savunma derinliği; birimde ölçülür.
    try:
        M.csv_modeli(["msgno,msgtext,selfexplainatory", "001,a\rb,false"])
        s["M23 csv_modeli satır içi CR → ÖLÇÜLEMEDİ"] = False
    except M.Olculemedi:
        s["M23 csv_modeli satır içi CR → ÖLÇÜLEMEDİ"] = True
    # M24: canlı metinde satır sonu → tek satırlık CSV taşıyamaz → ÖLÇÜLEMEDİ.
    canli24 = dict(CANLI)
    canli24["005"] = ("İki\nsatır", "false", "false")
    rc, out, b, d, c = msag("m24", CSV_ESIT.encode(), Sahte(msag=msag_xml(canli24)))
    s["M24 canlı metinde satır sonu → ÖLÇÜLEMEDİ"] = (rc == 2 and b == CSV_ESIT.encode()
                                                     and not d.cagri)
    # M25 (öneri a): olası mojibake UYARISI (ikili dizi / cp1254 tekli) + FP: meşru Türkçe
    # (U+00C2, â, Ü, Ç, ı, İ, ş) uyarı ÜRETMEZ. Mojibake verisi YALNIZ kaçış biçiminde.
    canli25 = dict(CANLI)
    canli25["004"] = ("Kullanıcı tara\u00fdndan iptal", "false", "false")
    canli25["005"] = ("\u00c3\u00bcr\u00c3\u00bcn bulunamad\u00c4\u00b1", "false", "false")
    canli25["006"] = ("\u00c3\u2013zel alan", "false", "false")        # Ö → C3 96 → U+00C3 U+2013
    rc, out, b, d, c = msag("m25", CSV_ESIT.encode(), Sahte(msag=msag_xml(canli25)))
    canli25fp = dict(CANLI)
    canli25fp["004"] = ("\u00c2dem hâlâ Ümit'i Çığ İşi için bekliyor", "false", "false")
    rc2, out2, b2, d2, _c = msag("m25fp", CSV_ESIT.encode(), Sahte(msag=msag_xml(canli25fp)))
    # Liste UYARI SATIRINDAN okunur: aynı liste `eklenen:` satırında da basılır (ölçüldü 2. tur:
    # tüm-çıktı araması MU35'i sahte-geçirdi).
    moj = [ln for ln in out.splitlines() if "mojibake" in ln]
    s["M25 mojibake uyarısı + meşru Türkçe FP yok"] = (
        rc == 0 and len(moj) == 1 and "['004', '005', '006']" in moj[0]
        and rc2 == 0 and "mojibake" not in out2)
    # M26 (2. tur LOW): desen birim ölçümü — Türkçe harf bozulmaları (Ö → U+2013 dahil)
    # yakalanır; yabancı dillerin meşru harfleri (bug-gate FP sondaları) yakalanMAZ.
    poz = ["\u00c3\u2013zel", "\u00c3\u2014", "\u00c3\u0153", "\u00c5\u017e", "\u00c4\u0178",
           "\u00c3\u2021", "\u00c4\u00b0", "tara\u00fdndan"]
    neg = ["Gr\u00f6\u00dfe", "\u00dcbersicht", "h\u00e2l\u00e2 \u00c2dem", "\u00c4\u00d6\u00dc",
           "\u00c5land", "S\u00e3o Paulo", "Çığ İşi Ümit"]
    s["M26 mojibake deseni: Türkçe bozulmalar + yabancı FP yok"] = (
        all(M._MOJIBAKE_RE.search(x) for x in poz)
        and not any(M._MOJIBAKE_RE.search(x) for x in neg))
    # M27 (2. tur öneri 5): yerel BOŞ + canlı BOŞ aynı msgno → bugünkü davranış EŞİT + damga
    # (çatışma değil; atlanan da değil — satır yerelde zaten var).
    yerel27 = CSV_ESIT + "004,,false\n"
    canli27 = dict(CANLI)
    canli27["004"] = ("", "false", "false")
    rc, out, b, d, c = msag("m27", yerel27.encode(), Sahte(msag=msag_xml(canli27)))
    s["M27 yerel boş + canlı boş → EŞİT + damga"] = (
        rc == 0 and b == yerel27.encode() and len(d.cagri) == 1 and "EŞİT" in out
        and "[ATLANDI]" not in out)

    # L3: yolda üstte aynı adlı `ERP/` dizini → SON kök segmenti.
    s["L3 paket_dizini SON kök eşleşmesi"] = M.paket_dizini(
        _KUM_KOK / "ERP" / "Proj" / "SOURCE_CODES" / "SD" / PAKET / "messages-zsd001.csv") == PAKET
    # L4: `--cwd` yok (tek kök kaynağı) — verilirse kullanım hatası, hiçbir şey okunmaz/damgalanmaz.
    kk = kum("l4")
    p = dosya(kk, msag_yol, CSV_ESIT.encode())
    d = Damga()
    with contextlib.redirect_stderr(io.StringIO()):
        rc, _o = kos(M, ["msag", "--name", SINIF, "--file", str(p), "--cwd", str(kk)],
                     Sahte(msag=msag_xml(CANLI)), d)
    s["L4 --cwd kabul edilmez (kök ayrışması yok)"] = rc == 2 and not d.cagri
    # L1: populate import'u başlık satırını YUTMAZ (gerçek pipe'lı alt süreç, --dry-run).
    if "L1" in pahali:
        s["L1 [PULL] başlığı pipe'ta ilk satır"] = _l1_baslik(M, kum("l1"), msag_yol)

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
    # T13 (bug-gate M1, textpool yüzü): karışık satır sonu + anlamca EŞİT → bayt-aynı.
    tp_karisik = "S_KUNNR =Müşteri\r\n\r\nP_FILE  =Dosya\n\nP_DATE  =Tarih\r\n"
    rc, out, b, d, c = tp("t13", f"{PROG}.selections.txt", tp_karisik.encode(),
                          Sahte(tp={"selections": sel_canli}))
    s["T13 textpool karışık satır sonu + eşit → YAZILMAZ"] = (
        rc == 0 and b == tp_karisik.encode() and len(d.cagri) == 1 and "EŞİT" in out)
    # T14 (MX2): YALNIZ `@` özniteliği değişmiş (metin aynı) → güncellenir (sahte-taze değil).
    rc, out, b, d, c = tp("t14", f"{PROG}.symbols.txt", "@MaxLength:40\nB01=Abc\n".encode(),
                          Sahte(tp={"symbols": "@MaxLength:50\r\nB01=Abc"}))
    s["T14 yalnız @ özniteliği farklı → güncellenir"] = (
        rc == 0 and b == "@MaxLength:50\nB01=Abc\n".encode() and "['B01']" in out)
    # T15 (L5): okunan dil KAPSAM satırında koddan (istemcinin oturum dili) basılır.
    rc, out, b, d, c = tp("t15", f"{PROG}.headings.txt", hd.encode(),
                          Sahte(tp={"headings": hd}, dil="EN"))
    s["T15 kapsam: okunan oturum dili basılır"] = (
        rc == 0 and "okunan dil (oturum): EN" in out and "master dil DENETLENMEZ" in out)
    M._git_kirli = _gercek_git_kirli                 # E1 ve sonraki kullanıcılar gerçeğini görür
    return s


_L1_SURUCU = r'''
import sys, types
kaynak_yolu, gercek_yol, csv_yolu, xml = sys.argv[1:5]
mod = types.ModuleType("pull_msag_textpool")
mod.__file__ = gercek_yol
sys.modules["pull_msag_textpool"] = mod
exec(compile(open(kaynak_yolu, encoding="utf-8").read(), gercek_yol, "exec"), mod.__dict__)
class Y:
    status_code = 200
    def __init__(self, t):
        self.text, self.content = t, t.encode("utf-8")
class C:
    url, language, client = "https://sahte.invalid", "TR", "000"
    def __init__(self):
        self.session = types.SimpleNamespace(
            get=lambda url, headers=None, params=None, **k: Y(xml))
mod.DAMGA_ARACLARI = (lambda s: s or "X", lambda sid, p: "K")
sys.exit(mod.main(["msag", "--name", "ZSD001", "--file", csv_yolu, "--dry-run"], client=C()))
'''


def _l1_baslik(M, kk: Path, msag_yol: str) -> bool:
    """Bug-gate L1: `populate_message_class` import'u (win32) sys.stdout'u yeniden sarar; import
    ÖNCESİ basılan `[PULL]` başlığı eski sarmalayıcının tamponunda kalıp pipe'ta kayboluyordu.
    Ölçüm TAZE süreçte (populate henüz yüklenmemiş) + gerçek pipe'la yapılır; kaynak, harness'ın
    yüklediği (mutasyonlu olabilir) metindir."""
    p = dosya(kk, msag_yol, CSV_ESIT.encode())
    kaynak = dosya(kk, "pull_kaynak.py", M.__kaynak__.encode("utf-8"))
    r = subprocess.run([sys.executable, "-c", _L1_SURUCU, str(kaynak), str(PULL_PATH), str(p),
                        msag_xml(CANLI)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    return r.returncode == 0 and r.stdout.lstrip().startswith(f"[PULL] MSAG {SINIF}")


def _kapi_sozlesmesi(stderr: str, p) -> bool:
    """Blok mesajı: komut satırı `--file "<p>" --session SID-E2E` ile biter (tek `--session`,
    kopyalanabilir) + `not` kaçışı (`--offline`, `--dry-run`) mesajda."""
    return (f'--file "{p}" --session SID-E2E' in stderr and stderr.count("--session") == 1
            and "SAP erişilemiyorsa" in stderr and "--offline" in stderr
            and "--dry-run" in stderr)


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
    # Sözleşme (Q352): kapı eklentinin SAF komutunun sonuna HOOK'un session_id'sini ekler
    # (tek `--session`) ve `not` metnini (kaçış) blok mesajına basar.
    ok = r1.returncode == 2 and "pull_msag_textpool.py msag" in r1.stderr and rc == 0 \
        and r2.returncode == 0 and _kapi_sozlesmesi(r1.stderr, p)
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
    ok = t1.returncode == 2 and "<PROGRAM_ADI> yerine" in t1.stderr \
        and _kapi_sozlesmesi(t1.stderr, t) and rct == 0 and t2.returncode == 0
    if not ok:
        return (f"FAIL textpool (blok rc={t1.returncode} pull rc={rct} sonra rc={t2.returncode}: "
                f"{t1.stderr[-300:]!r})")
    # `..` ayağı (2. tur, kardeş sınıf): damgasız YENİ seansta `docs/..` ve `textpool/x/..`
    # yolları gerçek kapıda BLOKLANMALI (düzeltme öncesi ölçüm: ikisi de exit 0). POSIX `docs/..`
    # yolunu fiziksel çözer → `docs` ve `x` GERÇEK dizin olarak kurulur (yoksa ENOENT).
    (kk / "SOURCE_CODES" / "docs").mkdir(parents=True, exist_ok=True)
    xdir = kk / "SOURCE_CODES" / "SD" / BASKA_PAKET / "programs" / "textpool" / "x"
    xdir.mkdir(parents=True, exist_ok=True)
    sep = os.sep
    dd_yollar = (str(kk / "SOURCE_CODES" / "docs") + sep + ".." + sep + "SD" + sep + PAKET
                 + sep + "messages-zsd001.csv", str(xdir) + sep + ".." + sep + "selections.txt")
    dd_rc = []
    for yol in dd_yollar:
        yuk = json.dumps({"tool_name": "Edit", "session_id": "SID-E2E-DD",
                          "tool_input": {"file_path": yol}})
        dd_rc.append(kapi_kos().returncode)
    if dd_rc != [2, 2]:
        return f"FAIL `..` ayağı (beklenen [2, 2], alınan {dd_rc})"
    return "PASS (msag + textpool yer tutucu + `..` iki biçim)"


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
    ("MU13 kaçış metni komutun arkasına döner (msag)", HOOK_PATH,
     """                "komut": f'{_PULL} msag --name {nesne} --file "{p}"',""",
     """                "komut": f'{_PULL} msag --name {nesne} --file "{p}"' + _KACIS,"""),
    ("MU14 eklenti --session basar (textpool)", HOOK_PATH,
     """            "komut": f'{_PULL} textpool --program {prog} --file "{p}"',""",
     """            "komut": f'{_PULL} textpool --program {prog} --file "{p}" --session S',"""),
    ("MU15 yer tutucu nedeni nottan düşer (textpool)", HOOK_PATH,
     '"<PROGRAM_ADI> yerine programı yaz; pull o DOSYAYI damgalar. ")', '"")'),
    ("MU12 kimlik (ortak anahtar) denetimi sökülür", PULL_PATH,
     "    if yerel and not (set(yerel) & set(canli)):", "    if False:"),
    ("MU11 msag öz-denetimi etkisiz + sıra bozuk", PULL_PATH,
     "        hatalar = msag_oz_denetim(yeni, rapor)\n",
     "        hatalar = []\n        yeni = [yeni[0]] + yeni[1:][::-1]\n"),
    # --- bug-gate düzeltme turu (Q352, 2026-09-26): her bulgu kendi vektörüyle ---
    ("MU16 [M1] anlamca-eşit yazma koruması sökülür", PULL_PATH,
     "    if not anlamca_degisti or yeni == eski:", "    if yeni == eski:"),
    ("MU17 [M2] canlı boş metin atlanmaz (NNN,, eklenir)", PULL_PATH,
     "    for k in atlanan:\n        del c[k]", "    atlanan = []"),
    ("MU18 [M2] boş-canlı/metinli-yerel çatışma denetimi sökülür", PULL_PATH,
     "    if catisan:", "    if False:"),
    ("MU19 [MX2] textpool @ öznitelikleri kıyaslanmaz", PULL_PATH,
     "        d[o[1]] = (o[4], o[3])", "        d[o[1]] = ((), o[3])"),
    ("MU20 [MX6] selfexp-sütunsuz + canlı true koruması sökülür", PULL_PATH,
     'if m["ise"] is None and any(v[1] == "true" for v in canli.values()):', "if False:"),
    ("MU21 [MX7] csv modülü çapraz denetimi sökülür", PULL_PATH,
     "if [d for d, _ in alanlar] != next(csv.reader([s])):", "if False:"),
    ("MU22 [MX8] canlı metin strip edilmez", PULL_PATH,
     "c = {no: (v[0].strip(), _selfexp(v[1])) for no, v in canli.items()}",
     "c = {no: (v[0], _selfexp(v[1])) for no, v in canli.items()}"),
    ("MU23 [MX9] yanıttaki sınıf adı denetimi sökülür", PULL_PATH,
     'if canli["name"].upper() != name:', "if False:"),
    ("MU24 [MX12] adlı textpool Z/Y denetimi sökülür", HOOK_PATH,
     "        if not _SAP_AD_RE.match(prog):\n            return None", "        pass"),
    ("MU25 [L3] paket_dizini İLK kök eşleşmesini alır", PULL_PATH,
     "    for i in range(len(parts) - 1, -1, -1):", "    for i in range(len(parts)):"),
    ("MU26 [L4] --cwd seçeneği geri gelir", PULL_PATH,
     '        p.add_argument("--dry-run", action="store_true",',
     '        p.add_argument("--cwd", default="")\n'
     '        p.add_argument("--dry-run", action="store_true",'),
    ("MU27 [L1] import öncesi flush sökülür", PULL_PATH,
     "        sys.stdout.flush()\n        import populate_message_class as pmc",
     "        import populate_message_class as pmc", "win32"),
    ("MU28 [öneri a] mojibake uyarısı susturulur", PULL_PATH,
     'supheli = sorted(k for k, v in metinler.items() if _MOJIBAKE_RE.search(v or ""))',
     "supheli = []"),
    ("MU29 [öneri a] mojibake çıplak U+00C2/U+00E7 arar (FP)", PULL_PATH,
     r'"|[\u00fd', r'"|[\u00c2\u00e7\u00fd'),
    ("MU30 [öneri c] muaf yedek kümesi kayar", HOOK_PATH,
     '"_archive", "archive", "drafts"}\ntry:', '"_archive", "archive"}\ntry:'),
    ("MU31 canlı metinde satır sonu denetimi sökülür", PULL_PATH,
     "    if satir_sonlu:", "    if False:"),
    ("MU32 [L5] okunan dil kapsam satırı düşer", PULL_PATH,
     "    print(f\"[KAPSAM] okunan dil (oturum): ", "    (f\"[KAPSAM] okunan dil (oturum): "),
    ("MU34 [2.tur M] _git_kirli daima True", PULL_PATH,
     "        return r.returncode == 0 and bool(r.stdout.strip())", "        return True"),
    ("MU35 [2.tur L] mojibake deseni U+2013/U+2014 kaçırır (Ö)", PULL_PATH,
     r'\u2013\u2014\u2018', r'\u2018'),
    ("MU36 [2.tur öneri 4] textpool git-kirli koruması sökülür", PULL_PATH,
     "        _norm, bicim = _dosya_oku(dosya)\n        if not dry_run and not force and _git_kirli(dosya):",
     "        _norm, bicim = _dosya_oku(dosya)\n        if False:"),
    ("MU37 [2.tur öneri 5] yerel-boş + canlı-boş çatışma sayılır", PULL_PATH,
     '    catisan = [k for k in bos_metin if k in m["mesajlar"] and m["mesajlar"][k][0]]',
     '    catisan = [k for k in bos_metin if k in m["mesajlar"]]'),
    ("MU38 [2.tur kardeş] `..` normpath sökülür", HOOK_PATH,
     "    p = Path(os.path.normpath(str(path)))", "    p = Path(path)"),
    ("MU33 [MX3] git-kirli koruması sökülür (msag)", PULL_PATH,
     "        norm, bicim = _dosya_oku(dosya)\n        if not dry_run and not force and _git_kirli(dosya):",
     "        norm, bicim = _dosya_oku(dosya)\n        if False:"),
]

# Her mutasyonun DÜŞÜRMESİ ZORUNLU vektörleri (senaryo kimliği = adın ilk kelimesi). Mutasyon
# başka senaryoları da düşürebilir; ama bunlardan biri ayakta kalırsa "HEDEF-KACTI" = FAIL.
HEDEF = {
    "MU1": ("M4", "T5"), "MU2": ("M4", "M5", "M14"), "MU3": ("T4",), "MU4": ("M2",),
    "MU5": ("M2", "M13"), "MU6": ("M2",), "MU7": ("T1", "T11"), "MU8": ("T2",), "MU9": ("H3",),
    "MU10": ("H6",), "MU11": ("M2", "M3"), "MU12": ("M14", "T7", "T11"), "MU13": ("H1", "H2"),
    "MU14": ("H4", "H6"), "MU15": ("H6",), "MU16": ("M17", "T13"), "MU17": ("M18",),
    "MU18": ("M19",), "MU19": ("T14",), "MU20": ("M20",), "MU21": ("M23",), "MU22": ("M21",),
    "MU23": ("M22",), "MU24": ("H10",), "MU25": ("L3",), "MU26": ("L4",), "MU27": ("L1",),
    "MU28": ("M25",), "MU29": ("M25",), "MU30": ("H11",), "MU31": ("M24",), "MU32": ("T15",),
    "MU33": ("M12",), "MU34": ("M12b",), "MU35": ("M25", "M26"), "MU36": ("T16",),
    "MU37": ("M27",), "MU38": ("H12",),
}
# PAHALI senaryolar (bkz. PAHALI) yalnız TABANDA + onları HEDEFLEYEN mutasyonlarda koşulur.
PAHALI_KIP = {p: tuple(mu for mu, h in HEDEF.items() if set(h) & set(PAHALI_SENARYO[p]))
              for p in PAHALI}


def kos_hepsi(pull_degisim=None, hook_degisim=None, pahali=PAHALI):
    H = modul_yukle("_pbe_msag_textpool", HOOK_PATH, hook_degisim)
    M = modul_yukle("pull_msag_textpool", PULL_PATH, pull_degisim)
    return senaryolar(M, H, pahali), M


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
        print("\n--- MUTASYONLAR (her biri korpusu KIRMIZI yapmalı; HEDEF vektörleri ZORUNLU) ---")
        for p, kipler in PAHALI_KIP.items():
            tam_ad = " · ".join(a for a in taban if a.split()[0] in PAHALI_SENARYO[p]) or p
            print(f"  [ATLA-MALIYET] {tam_ad} — yalnız TABAN + {', '.join(kipler) or '-'} "
                  f"kiplerinde koşulur (diğer mutasyonlarda ölçülmez)")
        kacan = []
        for ad, yol, eski, yeni, *kosul in MUTASYONLAR:
            mu = ad.split()[0]
            if kosul and kosul[0] == "win32" and sys.platform != "win32":
                # Kusur yalnız win32'de VAR (populate yalnız orada stdout'u yeniden sarar) →
                # başka platformda mutasyon ÖLÇÜLEMEZ; kaçan sayılmaz ama görünür basılır.
                print(f"  ATLA   {ad}  ← yalnız win32'de ölçülür (platform {sys.platform})")
                continue
            pahali = tuple(p for p, kipler in PAHALI_KIP.items() if mu in kipler)
            if yol == HOOK_PATH:
                sonuc, _ = kos_hepsi(hook_degisim=(eski, yeni), pahali=pahali)
            else:
                sonuc, _ = kos_hepsi(pull_degisim=(eski, yeni), pahali=pahali)
            dusen = [a for a, ok in sonuc.items() if not ok and taban.get(a)]
            idler = {a.split()[0] for a in dusen}
            eksik = [h for h in HEDEF.get(mu, ()) if h not in idler]
            if mu not in HEDEF:
                eksik = ["<HEDEF tanımsız>"]
            durum = "DUSTU" if dusen and not eksik else ("HEDEF-KACTI" if dusen else "KACTI")
            print(f"  {durum}  {ad}  ← {sorted(idler)}" + (f"  eksik hedef {eksik}" if eksik else ""))
            if durum != "DUSTU":
                kacan.append(ad)
        kos_hepsi(pahali=())                         # temiz modülleri geri yükle
    finally:
        _sil(_KUM_KOK)
    if hata or kacan:
        print(f"\nFAIL — taban hataları {hata} · kaçan mutasyonlar {kacan}")
        return 1
    print(f"\nPASS — {len(taban)} senaryo + {len(MUTASYONLAR)} mutasyon · E1: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
