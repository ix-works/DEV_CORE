#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""checklist_check.py — ortak checklist kontrol programı (bug-checklist BE/FE + doc-checklist).

NEDEN VAR (2026-10-18): checklist maddelerinin çoğu bugün inceleme sırasında OKUNARAK
kontrol ediliyordu; bazı turlarda her incelemede yeniden yazılıp atılan geçici betikler
koşuyordu. Aynı kural (ör. BE-10b — metotlar arası yorum → push 400) dört kez kaçtı: kural
yalnız inceleyenin listesindeydi, kodu yazanın yolunda değildi. Bu program o işi TEK yerde
hazır tutar ve ÜÇ katman aynı programı koşar:
  ① kodu yazan ajan teslimden önce · ② bug-expert incelemede (çıktıyı raporuna koyar,
  kendi emeğini C-sınıfı yargıya verir) · ③ run_review (class_push → yalnız `--ids BE-10b`).

Madde → kontrol eşlemesi `playbook/checklists/checklist-map.yaml`'dadır (sınıf A/B/C,
uygulanma globları, kontrol fonksiyonu, seviye, yazan kanalı). Program checklist METNİNİ
okumaz; kimlik bütünlüğünü `--harita-denetim` denetler.

Sınıflar:
  A = kaynak metinden kesin tespit → gerçek kontrol (PASS/FAIL/WARN). Kontrolü YAZILMAMIŞ
      A maddesi ELLE'ye düşer ve KAPSAM BEYANI'nda "A ama kontrolsüz" diye listelenir.
  B = SAP/çalışma zamanı sorgusu gerekir → yalnız `--sap` ile; yoksa ÖLÇÜLEMEDİ.
  C = yalnız yargı → ELLE. `kontrol` doluysa bu bir İPUCU tarayıcısıdır: aday satırları
      kanıt sütununa yazar, HÜKÜM VERMEZ (sonuç yine ELLE).

Kullanım:
  python scripts/validators/checklist_check.py --repo <kök> --files <dosya...> [--kind backend|frontend|doc|auto]
  python scripts/validators/checklist_check.py --repo <kök> --diff <git aralığı> [--kind ...]
      [--ids BE-10b,BE-47] [--sap [--sap-kok <.conn_adt dizini>]] [--verify-report <rapor.md>]
  python scripts/validators/checklist_check.py --reach            # yazan_kanali ulaşım testi
  python scripts/validators/checklist_check.py --harita-denetim   # map ↔ checklist bütünlüğü (run_all)

Diff kipinde kontrol bulguları DEĞİŞEN satırlara göre ayrılır: değişmeyen satırdaki bulgu
FAIL değil WARN'dır ("önceden var"). İstisna: map'te `tum_dosya: true` olan maddeler
(BE-10b: SAP bütün kaynağı PUT eder → dosyanın neresinde olursa olsun 400).

Exit: 0 = engelleyici FAIL yok · 1 = `seviye: blok` maddede FAIL ya da `--verify-report` eksikliği
(satır yok / hükümsüz / kanıtsız / ELLE / ÇELİŞKİ — kategori adı stdout'ta) · 2 = kullanım hatası
ya da program KOŞMADI (`[PROGRAM KOŞMADI] <tip>: <mesaj>`: okunamayan map/rapor, beklenmeyen istisna).
Ayrı kipler kendi hükmünü aynı kodla verir: `--reach` ulaşmayan · `--harita-denetim` tutarsızlık → 1.
Hüküm sözlüğü tek yerde: `HUKUMLER` (aşağıda; `--help` ve tablo başlığı onu basar).
"""
# ENFORCES: BE-10b  (ADR 0019 coverage binding — run_review class_push zinciri)
from __future__ import annotations

import argparse
import difflib
import fnmatch
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# ⚠ CORE-03: `CORE` çekirdeğin KENDİ varlıklarını (map, checklist, validator'lar, ajan
# tanımları) gösterir → `__file__` türevi burada MEŞRUDUR. İncelenen kod `--repo`'dan gelir.
CORE = Path(__file__).resolve().parents[2]
VALIDATORS = CORE / "scripts" / "validators"
SCRIPTS = CORE / "scripts"
MAP_YOLU = CORE / "playbook" / "checklists" / "checklist-map.yaml"
CHECKLISTLER = {
    "BE": CORE / "playbook" / "checklists" / "bug-checklist-backend.md",
    "FE": CORE / "playbook" / "checklists" / "bug-checklist-frontend.md",
    "DOC": CORE / "playbook" / "checklists" / "doc-checklist.md",
}
sys.path.insert(0, str(SCRIPTS))
from utils.kaynak_tarama import js_kod  # noqa: E402

SONUCLAR = ("PASS", "FAIL", "WARN", "UYGULANMAZ", "ÖLÇÜLEMEDİ", "ELLE")
KIND_ONEK = {"backend": ("BE",), "frontend": ("FE",), "doc": ("DOC",),
             "auto": ("BE", "FE", "DOC")}


# ═══════════════════════════════════════════════════════════ harita (YAML alt kümesi) ══
def _skaler(v: str):
    v = v.strip()
    if v in ("null", "~", ""):
        return None
    if v in ("true", "false"):
        return v == "true"
    if len(v) >= 2 and v[0] == v[-1] == '"':
        return v[1:-1].replace('\\"', '"')
    return v


def _liste(v: str) -> list:
    v = v.strip()
    if not (v.startswith("[") and v.endswith("]")):
        raise ValueError(f"liste bekleniyordu: {v!r}")
    ic = v[1:-1].strip()
    if not ic:
        return []
    return [_skaler(p) for p in re.findall(r'"(?:[^"\\]|\\.)*"|[^,\s][^,]*', ic)]


def harita_oku(yol: Path = MAP_YOLU) -> list[dict]:
    """`maddeler:` altındaki blok-stil liste. PyYAML'a BAĞIMLI DEĞİL (CI kurmaz).

    Desteklenen alt küme: `- anahtar: değer` + girintili `anahtar: değer`; değer düz
    skaler, çift tırnaklı dize ya da `[a, "b"]` akış listesi. Fixture'da PyYAML varsa
    çıktı `yaml.safe_load` ile EŞİTLİKLE kıyaslanır (alt küme dışına çıkılırsa yakalanır).
    """
    maddeler: list[dict] = []
    cur: dict | None = None
    icinde = False
    for no, ham in enumerate(yol.read_text(encoding="utf-8").splitlines(), 1):
        s = ham.rstrip()
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        if not s.startswith(" ") and not s.startswith("-"):
            icinde = s.strip() == "maddeler:"
            cur = None
            continue
        if not icinde:
            continue
        m = re.match(r"^\s*(-\s+)?([a-z_]+):\s*(.*)$", s)
        if not m:
            raise ValueError(f"{yol.name}:{no}: ayrıştırılamadı: {s!r}")
        if m.group(1):
            cur = {}
            maddeler.append(cur)
        if cur is None:
            raise ValueError(f"{yol.name}:{no}: madde başı (`- id:`) yok")
        anahtar, deger = m.group(2), m.group(3)
        cur[anahtar] = _liste(deger) if deger.strip().startswith("[") else _skaler(deger)
    return maddeler


# ═══════════════════════════════════════════════════════════════════ glob eşleme ══
def _glob_rx(desen: str) -> re.Pattern:
    out, i = [], 0
    while i < len(desen):
        if desen.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif desen[i] == "*":
            out.append("[^/]*")
            i += 1
        elif desen[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(desen[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE)


_GLOB_ONBELLEK: dict[str, re.Pattern] = {}


def glob_eslesir(rel: str, desenler: list[str]) -> bool:
    ad = rel.rsplit("/", 1)[-1]
    for d in desenler or []:
        rx = _GLOB_ONBELLEK.get(d)
        if rx is None:
            rx = _GLOB_ONBELLEK[d] = _glob_rx(d)
        hedef = rel if "/" in d else ad
        if rx.match(hedef):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════ modeller ══
@dataclass
class Bulgu:
    durum: str
    satir: int | None
    mesaj: str


@dataclass
class Dosya:
    rel: str
    metin: str
    eski_kaynak: object = None       # diff kipinde aralığın sol tarafı: str | callable (tembel) | None
    degisen: set[int] | None = None  # None = tüm satırlar "değişmiş" sayılır (--files)
    yol: Path | None = None
    eslesme_adi: str | None = None   # glob eşlemesinde rel yerine kullanılacak ad (--ana-sinif)

    _satirlar: list[str] | None = None

    @property
    def eski(self) -> str | None:
        """Aralığın sol tarafındaki içerik — yalnız isteyen kontrol (DOC-FS-07) için TEMBEL okunur."""
        if callable(self.eski_kaynak):
            self.eski_kaynak = self.eski_kaynak()
        return self.eski_kaynak

    @property
    def satirlar(self) -> list[str]:
        if self._satirlar is None:
            self._satirlar = self.metin.splitlines()
        return self._satirlar


@dataclass
class Baglam:
    repo: Path
    dosyalar: list[Dosya]
    sap: bool = False
    sap_kok: Path | None = None
    _istemci: object = None
    _sap_hata: str | None = None
    notlar: list[str] = field(default_factory=list)
    onbellek: dict = field(default_factory=dict)

    def kardes(self, d: Dosya, desen: str) -> list[Dosya]:
        """Aynı paket kökündeki (ilk `classes|cds|programs|functions|ui` üstü) dosyalar.
        Önce girdi kümesinden, yoksa diskten okunur (çapraz-dosya kontrolleri için; önbellekli)."""
        kok = paket_koku(d.rel)
        anahtar = ("kardes", kok, desen)
        if anahtar in self.onbellek:
            return self.onbellek[anahtar]
        sonuc = [x for x in self.dosyalar if paket_koku(x.rel) == kok and glob_eslesir(x.rel, [desen])]
        gorulen = {x.rel for x in sonuc}
        disk = self.repo / kok if kok else None
        if disk and disk.is_dir():
            for p in _dosyalar_budayarak(disk):
                rel = p.relative_to(self.repo).as_posix()
                if rel in gorulen or not glob_eslesir(rel, [desen]):
                    continue
                try:
                    sonuc.append(Dosya(rel, p.read_text(encoding="utf-8", errors="replace"), yol=p))
                except OSError:
                    pass
        self.onbellek[anahtar] = sonuc
        return sonuc


_BUDA = {"node_modules", "dist", ".git", ".tmp", "tmp", "coverage"}


def _dosyalar_budayarak(kok: Path):
    """`rglob` budamaz: node_modules'a iner (ölçüldü: 128 dosyalık bir kontrol 43 sn). os.walk + budama."""
    for dp, dn, fn in os.walk(kok):
        dn[:] = [x for x in dn if x not in _BUDA]
        for f in fn:
            yield Path(dp) / f


def paket_koku(rel: str) -> str:
    parcalar = rel.split("/")
    for i, p in enumerate(parcalar):
        if p.lower() in ("classes", "cds", "programs", "functions", "ui", "tables",
                         "structures", "docs", "behaviors"):
            return "/".join(parcalar[:i])
    return "/".join(parcalar[:-1])


# ═════════════════════════════════════════════════════════ ABAP normalizasyonu ══
def abap_norm(ham: str) -> tuple[str, str, str]:
    """Tek ABAP satırı → (kod, kod_literalsiz, yorum). `kod` ve `kod_literalsiz` AYNI uzunluktadır.

    `utils.kaynak_tarama.abap_satir` yalnız `'…'` literalini tanır; string şablonu
    (`|…|`) ve ters-tırnak literalindeki `"` orada yorum sanılır. Burada üç literal türü
    tanınır: `'…'` (`''` kaçış), `` `…` `` (çift ` kaçış), `|…|` (`\\` kaçış). Şablonun
    `{ … }` gömülü İFADESİ koddur (içinde yeniden literal/şablon açılabilir — yığınla
    izlenir). Literalsiz çıktıda literal İÇİ boşluğa çevrilir; sınır karakterleri
    (`'` `` ` `` `|` `{` `}`) yerinde kalır. Durum satır sonunda sıfırlanır.
    """
    if ham.lstrip().startswith("*"):
        return "", "", ham.lstrip()[1:]
    kod: list[str] = []
    kodsuz: list[str] = []
    yigin = ["C"]          # C kod · S '…' · B `…` · T |…| metni · E şablon ifadesi
    i, n = 0, len(ham)
    while i < n:
        ch = ham[i]
        ust = yigin[-1]
        if ust in ("S", "B"):
            q = "'" if ust == "S" else "`"
            if ch == q:
                if i + 1 < n and ham[i + 1] == q:
                    kod.append(q + q)
                    kodsuz.append("  ")
                    i += 2
                    continue
                yigin.pop()
                kod.append(q)
                kodsuz.append(q)
            else:
                kod.append(ch)
                kodsuz.append(" ")
            i += 1
            continue
        if ust == "T":
            if ch == "\\" and i + 1 < n:
                kod.append(ham[i:i + 2])
                kodsuz.append("  ")
                i += 2
                continue
            if ch == "{":
                yigin.append("E")
                kod.append(ch)
                kodsuz.append(ch)
            elif ch == "|":
                yigin.pop()
                kod.append(ch)
                kodsuz.append(ch)
            else:
                kod.append(ch)
                kodsuz.append(" ")
            i += 1
            continue
        # C ya da E (kod)
        if ch == '"':
            return "".join(kod), "".join(kodsuz), ham[i + 1:]
        if ch == "'":
            yigin.append("S")
        elif ch == "`":
            yigin.append("B")
        elif ch == "|":
            yigin.append("T")
        elif ch == "}" and ust == "E":
            yigin.pop()
        elif ch == "{" and ust == "E":
            yigin.append("E")
        kod.append(ch)
        kodsuz.append(ch)
        i += 1
    return "".join(kod), "".join(kodsuz), ""


class Abap:
    """Dosya düzeyinde ABAP görünümü: satır kodu, ifadeler, bloklar (önbellekli)."""

    def __init__(self, metin: str):
        self.ham = metin.splitlines()
        self.norm = [abap_norm(s) for s in self.ham]
        self.kod = [k for k, _, _ in self.norm]          # literal içerikli kod
        self.kl = [kl for _, kl, _ in self.norm]          # literalsiz kod
        self._ifadeler = None

    def yorum_satiri(self, i: int) -> bool:
        """1-tabanlı: satır yalnız yorum mu (tam-satır `*` ya da satır başı `"`)."""
        s = self.ham[i - 1].strip()
        return bool(s) and (s.startswith("*") or s.startswith('"'))

    def ifadeler(self) -> list[tuple[int, int, str, str]]:
        """[(bas, son, metin_literalli, metin_literalsiz)] — `.` ile biten ABAP ifadeleri."""
        if self._ifadeler is not None:
            return self._ifadeler
        out = []
        bas = None
        par_l, par_kl = [], []
        for no, (k, kl, _) in enumerate(self.norm, 1):
            if not kl.strip():
                continue
            j = 0
            while j < len(kl):
                if bas is None and kl[j].strip():
                    bas = no
                c = kl[j]
                if bas is not None:
                    par_l.append(k[j] if j < len(k) else c)
                    par_kl.append(c)
                if c == "." and bas is not None:
                    # ondalık sayı / bileşen erişimi değil: ardından boşluk/satır sonu gelmeli
                    sonra = kl[j + 1] if j + 1 < len(kl) else " "
                    if sonra in " \t":
                        out.append((bas, no, "".join(par_l), "".join(par_kl)))
                        bas, par_l, par_kl = None, [], []
                j += 1
            if bas is not None:
                par_l.append("\n")
                par_kl.append("\n")
        if bas is not None:
            out.append((bas, len(self.ham), "".join(par_l), "".join(par_kl)))
        self._ifadeler = out
        return out

    def bloklar(self, ac: str, kapa: str) -> list[tuple[int, int, str]]:
        """[(bas, son, ad)] — `METHOD x.`…`ENDMETHOD.` gibi satır-başı anahtar blokları."""
        rx_ac = re.compile(r"^\s*" + ac + r"\s+([\w/~]+)", re.IGNORECASE)
        rx_ka = re.compile(r"^\s*" + kapa + r"\s*\.", re.IGNORECASE)
        out, acik = [], None
        for no, kl in enumerate(self.kl, 1):
            if acik is None:
                m = rx_ac.match(kl)
                if m:
                    acik = (no, m.group(1))
            elif rx_ka.match(kl):
                out.append((acik[0], no, acik[1]))
                acik = None
        return out


def abap(d: Dosya) -> Abap:
    """Önbellek NESNENİN ÜSTÜNDE: `id(d)` anahtarlı modül sözlüğü, çöp toplanan Dosya'nın adresi
    yeniden kullanılınca BAŞKA dosyanın görünümünü döndürür (aynı süreçte çok girdi — fixture)."""
    a = d.__dict__.get("_abap_gorunum")
    if a is None:
        a = d.__dict__["_abap_gorunum"] = Abap(d.metin)
    return a


def _ilk_satir(ifade_bas: int, metin: str, ofset: int) -> int:
    return ifade_bas + metin.count("\n", 0, ofset)


# ═════════════════════════════════════════════════════ mevcut validator'lar (reuse) ══
_MODUL_ONBELLEK: dict[str, object] = {}
_TUTULAN: list = []


def validator(ad: str):
    """`scripts/validators/<ad>.py`'yi modül olarak yükler (YENİDEN YAZMA YOK)."""
    if ad in _MODUL_ONBELLEK:
        return _MODUL_ONBELLEK[ad]
    yol = VALIDATORS / f"{ad}.py"
    spec = importlib.util.spec_from_file_location(f"_cc_{ad}", yol)
    mod = importlib.util.module_from_spec(spec)
    eski_out, eski_err = sys.stdout, sys.stderr
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        # Bazı validator'lar import anında `sys.stdout = TextIOWrapper(sys.stdout.buffer)` yapar.
        # Geri alırken yeni sarmalayıcı ÇÖP TOPLANIRSA ortak tamponu KAPATIR ("I/O operation on
        # closed file", ölçüldü) → sarmalayıcılar ömür boyu tutulur.
        _TUTULAN.extend([sys.stdout, sys.stderr])
        sys.stdout, sys.stderr = eski_out, eski_err
    _MODUL_ONBELLEK[ad] = mod
    return mod


KONTROLLER: dict = {}


def kontrol(ad: str):
    def sar(fn):
        KONTROLLER[ad] = fn
        return fn
    return sar


def U(mesaj: str) -> list[Bulgu]:
    return [Bulgu("UYGULANMAZ", None, mesaj)]


def F(satir, mesaj) -> Bulgu:
    return Bulgu("FAIL", satir, mesaj)


def W(satir, mesaj) -> Bulgu:
    return Bulgu("WARN", satir, mesaj)


def E(satir, mesaj) -> Bulgu:
    return Bulgu("ELLE", satir, mesaj)


# ─────────────────────────────────────────────────────────────────── BACKEND (A) ──
_NESNE_DOSYA = re.compile(r"^([A-Za-z0-9_/]+?)\.(clas|prog|func|intf|fugr|ccimp|ccau|ccdef|ccmac)\b", re.I)
_DB_YAZ_KESIN = [
    (re.compile(r"\bUPDATE\s+([\w/]+)\s+SET\b", re.I), "UPDATE … SET"),
    (re.compile(r"\bDELETE\s+FROM\s+([\w/]+)\b", re.I), "DELETE FROM"),
    (re.compile(r"\bINSERT\s+INTO\s+([\w/]+)\s+VALUES\b", re.I), "INSERT INTO … VALUES"),
]
_DB_YAZ_BELIRSIZ = [
    (re.compile(r"\bMODIFY\s+([\w/]+)\s+FROM\s+(TABLE\s+)?[@\w<]", re.I), "MODIFY … FROM"),
    (re.compile(r"\bINSERT\s+([\w/]+)\s+FROM\s+(TABLE\s+)?[@\w<]", re.I), "INSERT … FROM"),
    (re.compile(r"\bDELETE\s+([\w/]+)\s+FROM\s+(TABLE\s+)?[@\w<]", re.I), "DELETE … FROM"),
]
_YEREL_AD = re.compile(r"^(?:[lgmcirevp][a-z]?_|[a-z]{1,3}_)", re.I)


def _yerel_tanimli(a: Abap) -> set[str]:
    adlar = set()
    for _b, _s, _l, kl in a.ifadeler():
        for m in re.finditer(r"\b(?:DATA|CLASS-DATA|STATICS|FIELD-SYMBOLS|TABLES)\b\s*:?\s*([\w<>/-]+)", kl, re.I):
            adlar.add(m.group(1).lower())
        for m in re.finditer(r",\s*([\w<>]+)\s+(?:TYPE|LIKE)\b", kl, re.I):
            adlar.add(m.group(1).lower())
    return adlar


@kontrol("be01_std_obje_yazim")
def k_be01(d: Dosya, c: Baglam):
    out = []
    ad = d.rel.rsplit("/", 1)[-1]
    m = _NESNE_DOSYA.match(ad)
    if m and not re.match(r"^(?:[ZY/]|L[ZY]|SAPL[ZY]|SAPM[ZY])", m.group(1), re.I):
        out.append(F(1, f"dosya standart (Z/Y olmayan) bir nesneyi temsil ediyor: `{m.group(1)}` (ADR 0005-A)"))
    if not d.rel.lower().endswith(".abap"):
        return out
    a = abap(d)
    yerel = _yerel_tanimli(a)

    def _std(tab: str) -> bool:
        t = tab.lower()
        return not (t.startswith(("z", "y", "<", "@")) or _YEREL_AD.match(t) or t in yerel
                    or t in ("table", "lines", "adjacent", "from", "into", "value"))

    for bas, _son, _l, kl in a.ifadeler():
        if re.search(r"\bENTIT(?:Y|IES)\b", kl, re.I):
            continue                     # EML (`MODIFY ENTITIES … DELETE FROM VALUE #(…)`) DB SQL değil
        ic_tablo = bool(re.search(r"\b(INDEX|TRANSPORTING|ASSIGNING|REFERENCE\s+INTO)\b", kl, re.I))
        for rx, et in _DB_YAZ_KESIN:
            for mm in rx.finditer(kl):
                if _std(mm.group(1)):
                    out.append(F(_ilk_satir(bas, kl, mm.start()),
                                 f"standart tabloya doğrudan DB yazımı `{et}` → `{mm.group(1)}` (ADR 0005-B)"))
        for rx, et in _DB_YAZ_BELIRSIZ:
            if ic_tablo:
                continue                 # INDEX/TRANSPORTING yalnız iç tablo biçiminde geçer
            for mm in rx.finditer(kl):
                if _std(mm.group(1)):
                    out.append(W(_ilk_satir(bas, kl, mm.start()),
                                 f"`{et} {mm.group(1)}` — DB tablosu mu iç tablo mu metinden kesin değil; "
                                 "standart DB tablosuysa ADR 0005-B ihlali"))
    return out


@kontrol("be03_released")
def k_be03(d, c):
    mod = validator("check_released_objects")
    if "released_map" not in _MODUL_ONBELLEK:
        _MODUL_ONBELLEK["released_map"] = mod.load_map()
    harita = _MODUL_ONBELLEK["released_map"]
    if not harita:
        return [Bulgu("ÖLÇÜLEMEDİ", None, "released_successors.json okunamadı")]
    return [W(f["line"], f"`{f['table']}` → released halef: {', '.join(f['successors'])}")
            for f in mod.scan(d.metin, harita)]


@kontrol("be04_decimal_write")
def k_be04(d, c):
    mod = validator("check_decimal_write_to")
    if not mod.file_has_api_marker(d.metin):
        return U("dosyada API gövdesi işareti yok (check_decimal_write_to kapsamı)")
    return [F(no, f"API gövdesi sınıfında `WRITE … TO`: {s[:80]}") for no, s in mod.scan_text(d.metin)]


@kontrol("be05_ns_dtel_tirnak")
def k_be05(d, c):
    out = []
    rx = re.compile(r"\bas\s+'(/\w+/\w+)'", re.I)
    for no, s in enumerate(d.satirlar, 1):
        kod = s.split("//", 1)[0]
        for m in rx.finditer(kod):
            out.append(F(no, f"namespaced DTEL tek tırnakta: `'{m.group(1)}'` → tırnaksız küçük harf yaz"))
    return out


@kontrol("be10a_type_c")
def k_be10a(d, c):
    mod = validator("check_method_param_type_c")
    return [F(no, f"metot imzasında `TYPE c LENGTH n`: {s[:90]}") for no, s in mod.scan_text(d.metin)]


_IMPL_BAS = re.compile(r"^\s*CLASS\s+[\w/]+\s+IMPLEMENTATION\s*\.", re.I)
_DEF_BAS = re.compile(r"^\s*CLASS\s+[\w/]+\s+DEFINITION\b", re.I)
_DEF_DEFERRED = re.compile(r"^\s*CLASS\s+[\w/]+\s+DEFINITION\s+(?:LOAD|DEFERRED)\b", re.I)
_METHOD_BAS = re.compile(r"^\s*METHOD\s+[\w/~]+", re.I)
_ENDMETHOD = re.compile(r"^\s*ENDMETHOD\s*\.", re.I)
_ENDCLASS = re.compile(r"^\s*ENDCLASS\s*\.", re.I)

# Konum etiketleri: OLCULMUS = push 400 OO_SOURCE_BASED 012 canlı ölçüldü (adt-classes §24.10);
# OLCULMEMIS = kural "güvenli taraf: koyma" der, ön tarama SAYAR ama kesinlik aynı DEĞİLDİR.
OLCULMUS, OLCULMEMIS = "ölçülmüş", "ölçülmemiş"


def _yorum_satiri(ham: str) -> bool:
    """`"` satır başı boşluk atlandıktan sonra gelirse yorum; `*` YALNIZ 1. sütunda yorum."""
    return ham.startswith("*") or ham.lstrip().startswith('"')


def yorum_bantlari(metin: str) -> list[tuple[int, int, str, str]]:
    """BE-10b: source-based sınıfta metot gövdesi ve DEFINITION bölümü DIŞINDA kalan yorum
    satırları → [(ilk_satır, son_satır, konum, kesinlik)].

    Sayılan konumlar:
      ① `CLASS … IMPLEMENTATION.` ↔ ilk `METHOD`           (ölçülmüş)
      ② `ENDMETHOD.` ↔ sonraki `METHOD`                    (ölçülmüş)
      ③ son `ENDMETHOD.` ↔ IMPLEMENTATION'ın `ENDCLASS.`    (ölçülmemiş)
      ④ IMPLEMENTATION'ın `ENDCLASS.`'ından sonrası         (ölçülmemiş)
      ⑤ DEFINITION'ın `ENDCLASS.`'ı ↔ `CLASS … IMPLEMENTATION.` (ölçülmemiş)
    Serbest: DEFINITION bölümü · metot gövdesi · dosyanın ilk CLASS deyiminden önceki başlık.
    Boş satır ilgisizdir (bant sınırları yorum satırlarıyla verilir).
    """
    bantlar: list[tuple[int, int, str, str]] = []
    durum = "bas"     # bas · def · ara(⑤) · bekle(①②③) · govde · sonra(④)
    capa = ""
    yorumlar: list[int] = []

    def kapat(konum: str, kesinlik: str):
        if yorumlar:
            bantlar.append((yorumlar[0], yorumlar[-1], konum, kesinlik))
        yorumlar.clear()

    for no, ham in enumerate(metin.splitlines(), 1):
        kod = abap_norm(ham)[1]
        if durum == "govde":
            if _ENDMETHOD.match(kod):
                durum, capa = "bekle", "ENDMETHOD."
            continue
        if durum == "def":
            if _ENDCLASS.match(kod):
                durum = "ara"
            continue
        if not ham.strip():
            continue
        if _yorum_satiri(ham):
            if durum in ("ara", "bekle", "sonra"):
                yorumlar.append(no)
            continue
        # yorum olmayan, boş olmayan satır
        if durum == "bekle":
            if _METHOD_BAS.match(kod):
                kapat(f"`{capa}` ↔ `METHOD`", OLCULMUS)
                durum = "govde"
                continue
            if _ENDCLASS.match(kod):
                kapat("son `ENDMETHOD.` ↔ `ENDCLASS.`" if capa == "ENDMETHOD." else
                      "`CLASS … IMPLEMENTATION.` ↔ `ENDCLASS.`", OLCULMEMIS)
                durum = "sonra"
                continue
            yorumlar.clear()     # METHOD/ENDCLASS dışı deyim (ör. pragma) — bant kesilir
            continue
        if durum == "ara":
            if _IMPL_BAS.match(kod):
                kapat("DEFINITION `ENDCLASS.` ↔ `CLASS … IMPLEMENTATION.`", OLCULMEMIS)
                durum, capa = "bekle", "CLASS … IMPLEMENTATION."
                continue
        if durum == "sonra" and re.match(r"^\s*CLASS\b", kod, re.I):
            kapat("IMPLEMENTATION `ENDCLASS.` sonrası", OLCULMEMIS)
        # ortak: CLASS deyimleri
        if _IMPL_BAS.match(kod):
            yorumlar.clear()
            durum, capa = "bekle", "CLASS … IMPLEMENTATION."
        elif _DEF_BAS.match(kod) and not _DEF_DEFERRED.match(kod):
            yorumlar.clear()
            durum = "def"
        elif durum == "ara":
            yorumlar.clear()     # ara bölgede başka deyim (ör. LOCAL FRIENDS) — bant kesilir
    if durum == "sonra":
        kapat("IMPLEMENTATION `ENDCLASS.` sonrası", OLCULMEMIS)
    return bantlar


@kontrol("be10b_yorum_bandi")
def k_be10b(d, c):
    out = []
    for b, s, konum, kesinlik in yorum_bantlari(d.metin):
        if kesinlik == OLCULMUS:
            out.append(F(b, f"metotlar arası yorum bandı (satır {b}-{s}, {konum}) → push 400 OO_SOURCE_BASED 012 "
                            "[ölçülmüş konum]. FIX: yorumu sil ya da `METHOD x.` satırının ALTINA taşı"))
        else:
            out.append(F(b, f"yorum bandı (satır {b}-{s}, {konum}) [ölçülmemiş konum — 400 bu konumda ÖLÇÜLMEDİ; "
                            "kural güvenli tarafı seçer: koyma]. FIX: yorumu sil ya da metot gövdesine/DEFINITION'a taşı"))
    return out


@kontrol("be11_audit")
def k_be11(d, c):
    mod = validator("check_audit_fields_autofill")
    return [W(no, f"audit alanı `{fld}` var, admin/setAdmin determination yok") for no, fld in mod.scan_bdef(d.metin)]


_LOOP_AC = re.compile(r"^\s*LOOP\s+AT\b", re.I)
_LOOP_KAPA = re.compile(r"^\s*ENDLOOP\b", re.I)
_SELECT = re.compile(r"\bSELECT\b", re.I)


@kontrol("be12_loop_select")
def k_be12(d, c):
    a = abap(d)
    out, derinlik = [], 0
    amdp = _amdp_araliklari(d.metin)
    for bas, son, _l, kl in a.ifadeler():
        if any(b <= bas <= s for b, s in amdp):
            continue
        ilk = kl.lstrip()
        if _LOOP_AC.match(ilk):
            derinlik += 1
            continue
        if _LOOP_KAPA.match(ilk):
            derinlik = max(0, derinlik - 1)
            continue
        if derinlik and re.match(r"^\s*SELECT\b", ilk, re.I) and not re.search(r"\bFROM\s+@", ilk, re.I):
            if "#EC CI_SEL_NESTED" in " ".join(a.ham[bas - 1:son]).upper():
                continue
            out.append(F(bas, "LOOP AT … ENDLOOP içinde SELECT (ATC P1 Nested Reading) → döngü öncesi toplu oku"))
    return out or [E(None, "statik LOOP-içi-SELECT yok; öbür ATC P1 bulguları `adt_atc_check` ister")]


@kontrol("ip_be19_bp_ad")
def k_be19(d, c):
    rx = re.compile(r"\b(ZSD000_I_BPNAME|but000|bu_partner)\b", re.I)
    out = []
    for no, s in enumerate(d.satirlar, 1):
        kod = abap_norm(s)[1] if d.rel.lower().endswith(".abap") else s.split("//", 1)[0]
        m = rx.search(kod)
        if m:
            out.append(W(no, f"`{m.group(1)}` — partner adı için müşteri→I_Customer / satıcı→I_Supplier mi? (BU_PARTNER≠KUNNR)"))
    return out


@kontrol("ip_be20_byassoc")
def k_be20(d, c):
    mod = validator("check_rap_byassoc_keys_only")
    return [W(no, f"`{assoc}` … FROM — yalnız key alanları döner (non-key okunuyorsa ALL FIELDS WITH)")
            for no, assoc in mod.scan_text(d.metin)]


@kontrol("be26_rap_commit")
def k_be26(d, c):
    mod = validator("check_no_rap_commit")
    from utils.kaynak_tarama import abap_kod, MantiksalMetin
    satirlar = abap_kod(d.metin)
    kacan = {no for no, ham in enumerate(d.satirlar, 1) if mod._ESCAPE in ham}
    m_kod = MantiksalMetin([(no, k) for no, k, _ in satirlar])
    m_lit = MantiksalMetin([(no, kl) for no, _, kl in satirlar])
    out = []
    for sev, kume, mm in (("F", mod._ERROR_IFADE, m_lit), ("F", mod._ERROR_KIMLIK, m_kod),
                          ("W", mod._WARN_IFADE, m_lit), ("W", mod._WARN_KIMLIK, m_kod)):
        for rx, label in kume:
            for bas, son in mm.bul(rx):
                if any(n in kacan for n in range(bas, son + 1)):
                    continue
                out.append((F if sev == "F" else W)(bas, f"RAP bağlamında `{label}` (BEHAVIOR_ILLEGAL_STATEMENT)"))
    return out


def _amdp_araliklari(metin: str):
    from utils.kaynak_tarama import amdp_govde_araliklari
    return amdp_govde_araliklari(metin)


@kontrol("be28_amdp")
def k_be28(d, c):
    """BE-28 (b) ASCII-7 dışı karakter + (c) `--` yorumunda apostrof. (a)/(d) ELLE."""
    araliklar = _amdp_araliklari(d.metin)
    if not araliklar:
        return U("AMDP gövdesi yok")
    out = []
    for b, s in araliklar:
        for no in range(b, s + 1):
            satir = d.satirlar[no - 1] if no - 1 < len(d.satirlar) else ""
            yabanci = sorted({ch for ch in satir if ord(ch) > 127})
            if yabanci:
                out.append(F(no, f"(b) AMDP gövdesinde ASCII-7 dışı karakter {''.join(yabanci)!r} (yorumda bile yasak)"))
    mod = validator("check_amdp_comment_apostrophe")
    if d.yol is not None and d.yol.is_file():
        out += [F(no, f"(c) AMDP `--` yorumunda apostrof: {t[:70]}") for _f, no, t in mod._scan(str(d.yol))]
    else:
        out.append(Bulgu("ÖLÇÜLEMEDİ", None, "(c) dosya diskte değil (check_amdp_comment_apostrophe dosya yolu ister)"))
    return out + [E(None, "(a) client-handling seti ve (d) namespaced tablo erişimi aktivasyonla teyit (yargı)")]


_ALV_CHANGING = ("it_outtab", "it_fieldcatalog", "it_sort", "it_filter")


@kontrol("be30_alv_changing")
def k_be30(d, c):
    out = []
    for bas, _s, _l, kl in abap(d).ifadeler():
        if not re.search(r"set_table_for_first_display", kl, re.I):
            continue
        bolum = None
        for m in re.finditer(r"\b(EXPORTING|IMPORTING|CHANGING|RECEIVING|EXCEPTIONS)\b|\b(\w+)\s*=", kl, re.I):
            if m.group(1):
                bolum = m.group(1).upper()
            elif m.group(2) and m.group(2).lower() in _ALV_CHANGING and bolum not in (None, "CHANGING"):
                out.append(F(_ilk_satir(bas, kl, m.start()),
                             f"`{m.group(2)}` set_table_for_first_display'de CHANGING parametresidir, {bolum}'a konmuş"))
            elif m.group(2) and m.group(2).lower() in _ALV_CHANGING and bolum is None:
                # fonksiyonel çağrı kısa biçimi `( it_outtab = … )` → EXPORTING sayılır
                out.append(F(_ilk_satir(bas, kl, m.start()),
                             f"`{m.group(2)}` ekli bölüm olmadan verilmiş (EXPORTING sayılır) — CHANGING olmalı"))
    return out


@kontrol("be31_kna1_lfa1")
def k_be31(d, c):
    rx = re.compile(r"\b(?:FROM|JOIN)\s+(kna1|lfa1)\b", re.I)
    out = []
    for bas, _s, _l, kl in abap(d).ifadeler():
        for m in rx.finditer(kl):
            out.append(F(_ilk_satir(bas, kl, m.start()),
                         f"ham `{m.group(1).upper()}` SELECT → ATC P1; released halef (I_Customer / I_Supplier)"))
    return out


_UNIT_CUKY_AD = r"(?:vrkme|meins|waers|kmein|vrkme_int|gewei|voleh|\w*unit\w*|\w*currency\w*|\w*cuky\w*|\w*_uom\w*)"


def _ddl_kod(metin: str, literal_sil: bool = True) -> list[str]:
    """CDS: `//`, `--` ve `/* */` yorumları silinmiş satırlar (satır sayısı korunur).
    `literal_sil`: `'…'` içi boşluğa çevrilir (ör. `@EndUserText.label: '… Union'` yapı sanılmasın)."""
    temiz = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), metin, flags=re.S)
    out = []
    for s in temiz.splitlines():
        parca, i, lit = [], 0, False
        while i < len(s):
            ch = s[i]
            if lit:
                if ch == "'":
                    lit = False
                    parca.append(ch)
                else:
                    parca.append(" " if literal_sil else ch)
            elif ch == "'":
                lit = True
                parca.append(ch)
            elif s.startswith("//", i) or s.startswith("--", i):
                break
            else:
                parca.append(ch)
            i += 1
        out.append("".join(parca))
    return out


@kontrol("ip_be32_cds_agg_unit")
def k_be32(d, c):
    rx = re.compile(r"\b(max|min|sum|avg)\s*\(\s*(?:distinct\s+)?([\w.$]*?\b" + _UNIT_CUKY_AD + r")\s*\)", re.I)
    out = []
    for no, s in enumerate(_ddl_kod(d.metin), 1):
        for m in rx.finditer(s):
            out.append(W(no, f"`{m.group(1)}( {m.group(2)} )` — UNIT/CUKY tipli kolon aggregate edilemez → GROUP BY'a al "
                             "(alan tipi addan çıkarıldı; tipi doğrula)"))
    return out


@kontrol("be33_union_ignoreprop")
def k_be33(d, c):
    kod = "\n".join(_ddl_kod(d.metin))
    if not re.search(r"\bdefine\s+(?:root\s+)?view\s+entity\b", kod, re.I) or not re.search(r"\bunion\b", kod, re.I):
        return U("UNION'lı view entity değil")
    if re.search(r"@Metadata\.ignorePropagatedAnnotations\s*:\s*true", kod, re.I):
        return []
    no = next(i for i, s in enumerate(_ddl_kod(d.metin), 1) if re.search(r"\bunion\b", s, re.I))
    return [F(no, "UNION view entity'de `@Metadata.ignorePropagatedAnnotations: true` yok")]


@kontrol("be34_bape_vbak_zz1")
def k_be34(d, c):
    kod = abap(d).kod
    t = "\n".join(kod).lower()
    if not re.search(r"\bbape_vbak\b", t) or "zz1_" not in t:
        return U("BAPE_VBAK + ZZ1 kodda birlikte yok (yorumlar hariç)")
    no = next(i for i, s in enumerate(kod, 1) if re.search(r"\bbape_vbak\b", s, re.I))
    return [F(no, "ZZ1 alanları BAPE_VBAK ile taşınıyor — S/4'te BAPE_SDSALESDOC (BE-37: CL_CFD_BAPI_MAPPING)")]


@kontrol("be35_char_tip")
def k_be35(d, c):
    rx = re.compile(r"\bTYPE\s+(char(?:4[1-9]|[5-9]\d|\d{3,}))\b", re.I)
    out = []
    for no, (_k, kl, _y) in enumerate(abap(d).norm, 1):
        for m in rx.finditer(kl):
            out.append(W(no, f"`TYPE {m.group(1)}` — DDIC'te tanımlı olmayabilir (CHAR1..40 güvenli) → `c LENGTH n` / string / dtel"))
    return out


_SUBSTR = re.compile(r"(?<=[\w>\])])\+(\w+)\(\s*([^()]*?(?:\([^()]*\))?[^()]*?)\s*\)")


@kontrol("be36_substring_ifade")
def k_be36(d, c):
    out = []
    for no, (_k, kl, _y) in enumerate(abap(d).norm, 1):
        for m in _SUBSTR.finditer(kl):
            uz = m.group(2).strip()
            if re.fullmatch(r"\*|\d+|[\w-]+|<[\w-]+>(?:-[\w]+)*", uz):
                continue
            out.append(F(no, f"substring uzunluğu ifade: `+{m.group(1)}( {uz} )` → önce değişkene hesapla"))
    return out


@kontrol("be37_eew_klasik")
def k_be37(d, c):
    kod = abap(d).kod
    t = "\n".join(kod).lower()
    if "bape_sdsalesdoc" not in t:
        return U("BAPE_SDSALESDOC kodda yok (yorumlar hariç)")
    if "cl_cfd_bapi_mapping" in t:
        return []
    if "valuepart" in t:
        no = next(i for i, s in enumerate(kod, 1) if "valuepart" in s.lower())
        return [F(no, "BAPE_SDSALESDOC klasik valuepart imajıyla taşınıyor → CL_CFD_BAPI_MAPPING ile serileştir")]
    return [E(None, "BAPE_SDSALESDOC var, serileştirme yolu metinden belirlenemedi")]


@kontrol("be38_klasik_view")
def k_be38(d, c):
    kodl = _ddl_kod(d.metin)
    kod = "\n".join(kodl)
    if not re.search(r"@AbapCatalog\.sqlViewName", kod, re.I) or re.search(r"\bview\s+entity\b", kod, re.I):
        return U("klasik `define view` (sqlViewName) değil")
    out = []
    for no, s in enumerate(kodl, 1):
        if re.search(r"\b(?:not\s+)?in\s*\(", s, re.I) and not re.search(r"\bwith\s+parameters\b", s, re.I):
            out.append(F(no, "klasik define view'da `IN (liste)` reddedilir → `<>`/`=` zinciri"))
        if re.search(r"\b(max|min|sum|avg)\s*\(\s*cast\s*\(", s, re.I):
            out.append(F(no, "klasik define view'da aggregate içinde CAST reddedilir → CAST'i dışarı al"))
        if re.search(r"\$projection\b|\bcomposition\b", s, re.I):
            out.append(F(no, "klasik define view'da view-entity söz dizimi (`$projection`/`composition`)"))
    # UNION 2+. dalda `key`
    dal = 0
    for no, s in enumerate(kodl, 1):
        if re.search(r"\bunion\b", s, re.I):
            dal += 1
        elif dal and re.search(r"^\s*key\s+\w", s, re.I):
            out.append(F(no, "klasik UNION'da `key` yalnız 1. dalda olabilir"))
    return out


@kontrol("be40_tabfn_client")
def k_be40(d, c):
    rx = re.compile(r"\b(?:FROM|JOIN)\s+([\w/]+)\s*\(\s*p_client\s*=", re.I)
    out = []
    for bas, _s, _l, kl in abap(d).ifadeler():
        for m in rx.finditer(kl):
            out.append(F(_ilk_satir(bas, kl, m.start()),
                         f"`{m.group(1)}( p_client = … )` — #CLIENT parametresi derleyicice bağlanır, argümanı at"))
    return out


@kontrol("be41_perform_ifade")
def k_be41(d, c):
    out = []
    for bas, _s, lit, kl in abap(d).ifadeler():
        if not re.match(r"^\s*PERFORM\b", kl, re.I):
            continue
        m = re.search(r"\b(USING|CHANGING|TABLES)\b(.*)$", kl, re.I | re.S)
        if m and ("|" in m.group(2) or re.search(r"\w\s*\(\s", m.group(2))):
            out.append(F(bas, "PERFORM aktüel parametresi ifade/şablon (`|…|` ya da çağrı) → önce değişkene al"))
    return out


@kontrol("be47_template_pipe")
def k_be47(d, c):
    out = []
    for no, (_k, kl, _y) in enumerate(abap(d).norm, 1):
        if re.search(r"\}\|\{", kl):
            out.append(F(no, "string şablonunda kaçışsız `}|{` → şablon erken kapanır (OO_SOURCE_BASED 011); literal `|` için `\\|`"))
    return out


_PARAM_SIRA = ["IMPORTING", "EXPORTING", "CHANGING", "RETURNING", "RAISING", "EXCEPTIONS"]


@kontrol("be48_param_sirasi")
def k_be48(d, c):
    out = []
    rx_ek = re.compile(r"\b(IMPORTING|EXPORTING|CHANGING|RETURNING|RAISING|EXCEPTIONS)\b", re.I)
    for bas, _s, _l, kl in abap(d).ifadeler():
        m = re.match(r"^\s*(?:CLASS-)?METHODS\s*(:?)(.*)$", kl, re.I | re.S)
        if not m:
            continue
        # zincirli bildirimde (`METHODS: a …, b …`) virgül metotları ayırır; tekilde virgül yoktur
        parcalar = m.group(2).split(",") if m.group(1) else [m.group(2)]
        for parca in parcalar:
            onceki = -1
            for e in rx_ek.finditer(parca):
                idx = _PARAM_SIRA.index(e.group(1).upper())
                if idx < onceki:
                    out.append(F(_ilk_satir(bas, kl, kl.find(parca) + e.start()),
                                 f"METHODS parametre eki sırası bozuk: `{e.group(1).upper()}` "
                                 f"`{_PARAM_SIRA[onceki]}`'dan sonra (IMPORTING→EXPORTING→CHANGING→RETURNING→RAISING)"))
                    break
                onceki = idx
    return out


@kontrol("be49_include_ad")
def k_be49(d, c):
    mod = validator("check_package_naming")
    kok = paket_koku(d.rel)
    pkg = c.repo / kok if kok else None
    if not pkg or not (pkg / "programs").is_dir():
        return U("paket `programs/` dizini yok")
    ad = d.rel.rsplit("/", 1)[-1].split(".")[0].upper()
    return [F(None, v) for v in mod.validate_classic_include_naming(pkg) if ad in v.upper()]


@kontrol("be50_loop_data")
def k_be50(d, c):
    a = abap(d)
    out = []
    ifs = a.ifadeler()
    yigin: list[int] = []   # açık LOOP ifade indeksleri
    for idx, (bas, _s, _l, kl) in enumerate(ifs):
        ilk = kl.lstrip()
        if _LOOP_AC.match(ilk):
            yigin.append(idx)
            continue
        if _LOOP_KAPA.match(ilk):
            if yigin:
                yigin.pop()
            continue
        if not yigin:
            continue
        m = re.match(r"^\s*DATA\s*:?\s*(\w+)\b(.*)$", ilk, re.I | re.S)
        if not m:
            continue
        ad, kalan = m.group(1), m.group(2)
        if re.search(r"\bVALUE\b", kalan, re.I) and not re.search(r"\bVALUE\s*#", kalan, re.I):
            out.append(W(bas, f"LOOP içinde `DATA {ad} … VALUE` — VALUE yalnız bir kez atanır, her turda sıfırlanmaz → CLEAR"))
            continue
        if re.search(r"\bTABLE\b", kalan, re.I):
            # sonraki ifadelerde (aynı döngüde) APPEND … TO ad var, öncesinde CLEAR yok mu
            temiz = False
            for b2, _s2, _l2, kl2 in ifs[idx + 1:]:
                k2 = kl2.lstrip()
                if _LOOP_KAPA.match(k2):
                    break
                if re.search(rf"\b(CLEAR|FREE|REFRESH)\b[^.]*\b{ad}\b|\b{ad}\s*=\s*VALUE\b", k2, re.I):
                    temiz = True
                if re.search(rf"\bAPPEND\b.*\bTO\s+{ad}\b|\bINSERT\b.*\bINTO\s+TABLE\s+{ad}\b", k2, re.I | re.S) and not temiz:
                    out.append(W(bas, f"LOOP içinde `DATA {ad}` tablosu her turda temizlenmiyor (APPEND satır {b2}) → CLEAR"))
                    break
    return out


def _parantez_derinligi(s: str) -> int:
    return s.count("(") - s.count(")")


@kontrol("be51_once_kullanim")
def k_be51(d, c):
    """Metot/FORM içinde `DATA x` bildiriminden ÖNCE (metinsel sıra) `x` kullanımı.
    Kullanım SAYILMAZ: `AS x` (SELECT takma adı) · parantez içinde `x =` (adlı parametre /
    VALUE bileşeni) · `CALL … EXPORTING x =` · TYPES/DATA bildirimleri · `-x`/`~x`/`>x`.
    `DATA: BEGIN OF s, x TYPE …` bileşenleri değişken DEĞİLDİR (yalnız `s` alınır)."""
    a = abap(d)
    out = []
    ifs = a.ifadeler()
    for b, s, ad in a.bloklar("METHOD", "ENDMETHOD") + a.bloklar("FORM", "ENDFORM"):
        tanim: dict[str, int] = {}
        govde = [x for x in ifs if b < x[0] < s]
        for bas, _son, _l, kl in govde:
            if not re.match(r"^\s*DATA\b", kl, re.I):
                continue
            if re.search(r"\bBEGIN\s+OF\b", kl, re.I):
                adlar = [(mm.group(1), mm.start(1)) for mm in re.finditer(r"\bBEGIN\s+OF\s+(\w+)", kl, re.I)]
            else:
                adlar = [(mm.group(1), mm.start(1)) for mm in
                         re.finditer(r"(?:^\s*DATA\s*:?\s*|,\s*)(\w+)\s+(?:TYPE|LIKE)\b", kl, re.I)]
            for adx, ofs in adlar:
                tanim.setdefault(adx.lower(), _ilk_satir(bas, kl, ofs))
        for degisken, tsatir in tanim.items():
            rx = re.compile(rf"(?<![\w\-~>@]){re.escape(degisken)}\b", re.I)
            bulundu = None
            for bas, _son, _l, kl in govde:
                if bas >= tsatir or bulundu:
                    break
                if re.match(r"^\s*(DATA|TYPES|CLASS-DATA|STATICS|CONSTANTS)\b", kl, re.I):
                    continue
                cagri = bool(re.match(r"^\s*(CALL\s+(METHOD|FUNCTION)|RAISE|PERFORM)\b", kl, re.I))
                for mm in rx.finditer(kl):
                    onu, sonu = kl[:mm.start()], kl[mm.end():]
                    if re.search(r"\bAS\s+$", onu, re.I):
                        continue
                    adli = re.match(r"^\s*=(?!=)", sonu) is not None
                    if adli and (_parantez_derinligi(onu) > 0 or cagri):
                        continue
                    no = _ilk_satir(bas, kl, mm.start())
                    if no >= tsatir:
                        break
                    bulundu = no
                    break
            if bulundu:
                out.append(F(bulundu, f"`{degisken}` satır {tsatir}'deki `DATA` bildiriminden ÖNCE kullanılmış (metot `{ad}`)"))
    return out


@kontrol("be55_inline_tablo_param")
def k_be55(d, c):
    out = []
    for bas, _s, _l, kl in abap(d).ifadeler():
        if re.match(r"^\s*(CLASS-)?METHODS\b", kl, re.I):
            for m in re.finditer(r"\bTYPE\s+(?:STANDARD\s+|SORTED\s+|HASHED\s+|INDEX\s+|ANY\s+)?TABLE\s+OF\b", kl, re.I):
                out.append(F(_ilk_satir(bas, kl, m.start()),
                             "metot arayüzünde anonim `TYPE … TABLE OF` → isimli tablo tipi (TYPES tt_x …)"))
    return out


@kontrol("be57_returning_key")
def k_be57(d, c):
    a = abap(d)
    tipler: dict[str, bool] = {}
    for _b, _s, _l, kl in a.ifadeler():
        for m in re.finditer(r"(?:^\s*TYPES\s*:?\s*|,\s*)(\w+)\s+TYPE\s+(?:STANDARD\s+)?TABLE\s+OF\b([^,]*)", kl, re.I):
            tipler[m.group(1).lower()] = bool(re.search(r"\bKEY\b", m.group(2), re.I))
    out = []
    for bas, _s, _l, kl in a.ifadeler():
        for m in re.finditer(r"\bRETURNING\s+VALUE\s*\(\s*\w+\s*\)\s+TYPE\s+(\w+)", kl, re.I):
            t = m.group(1).lower()
            if tipler.get(t) is False:
                out.append(F(_ilk_satir(bas, kl, m.start()),
                             f"RETURNING tipi `{t}` key ifadesiz tanımlı → `WITH DEFAULT KEY` (fully typed)"))
    return out


@kontrol("be58_secim_ekrani_ad")
def k_be58(d, c):
    out = []
    for bas, _s, _l, kl in abap(d).ifadeler():
        m = re.match(r"^\s*(SELECT-OPTIONS|PARAMETERS)\s*:?\s*(.*)$", kl, re.I | re.S)
        if not m:
            continue
        for parca in re.split(r",", m.group(2)):
            ad = re.match(r"\s*([\w]+)", parca)
            if ad and len(ad.group(1)) > 8 and not re.match(r"\s*(FOR|TYPE|LIKE|DEFAULT)\b", parca, re.I):
                out.append(F(bas, f"seçim ekranı adı `{ad.group(1)}` {len(ad.group(1))} karakter (>8) → aktivasyon reddi"))
    return out


@kontrol("be59_concat_bosluk")
def k_be59(d, c):
    rx = re.compile(r"\bconcat\s*\(", re.I)
    out = []
    for no, s in enumerate(_ddl_kod(d.metin, literal_sil=False), 1):
        if not rx.search(s):
            continue
        for lit in re.findall(r"'((?:[^']|'')*)'", s):
            if lit != lit.strip() and lit.strip():
                out.append(F(no, f"`concat` argümanında boşluklu literal `'{lit}'` → concat sondaki boşluğu siler; concat_with_space"))
                break
    return out


def _bdef_silme_validasyonlari(bdefler: list) -> dict[str, set[str]]:
    """{validation_adı: {entity adı, alias}} — `on save { … delete … }` tetikli olanlar."""
    out: dict[str, set[str]] = {}
    for bd in bdefler:
        metin = re.sub(r"//[^\n]*|/\*.*?\*/", "", bd.metin, flags=re.S)
        parcalar = re.split(r"(?=\bdefine\s+behavior\s+for\b)", metin, flags=re.I)
        for p in parcalar:
            mh = re.match(r"\s*define\s+behavior\s+for\s+([\w/]+)(?:\s+alias\s+(\w+))?", p, re.I)
            if not mh:
                continue
            adlar = {x.lower() for x in mh.groups() if x}
            for mv in re.finditer(r"\bvalidation\s+(\w+)\s+on\s+save\s*\{([^}]*)\}", p, re.I):
                if re.search(r"\bdelete\b", mv.group(2), re.I):
                    out.setdefault(mv.group(1).lower(), set()).update(adlar)
    return out


@kontrol("be60_delete_val_read")
def k_be60(d, c):
    """Delete tetikli validation'ı uygulayan metotta, o validation'ın KENDİ entity'sini okuyan
    `READ ENTITIES … ENTITY <aynı>` → FAIL (silinmiş örnek tamponda yok, BOŞ döner). Başka
    entity'yi (ör. üst kayıt) okumak meşrudur. Metot ↔ validation eşlemesi sınıf tanımındaki
    `METHODS m FOR VALIDATE ON SAVE IMPORTING keys FOR <Entity>~<validation>`'dan okunur."""
    bdefler = c.kardes(d, "*.bdef") + c.kardes(d, "*.asbdef")
    silme = _bdef_silme_validasyonlari(bdefler)
    if not silme:
        return U(f"pakette delete tetikli validation yok (BDEF taranan: {len(bdefler)})")
    a = abap(d)
    yontem: dict[str, tuple[str, str]] = {}
    for _b, _s, _l, kl in a.ifadeler():
        for mm in re.finditer(r"\b(?:METHODS\s*:?\s*|,\s*)(\w+)\s+FOR\s+VALIDATE\s+ON\s+SAVE\b[^,.]*?\bFOR\s+(\w+)~(\w+)", kl, re.I):
            yontem[mm.group(1).lower()] = (mm.group(2).lower(), mm.group(3).lower())
    out = []
    for b, s, ad in a.bloklar("METHOD", "ENDMETHOD"):
        ent_val = yontem.get(ad.lower())
        if not ent_val or ent_val[1] not in silme:
            continue
        hedef = silme[ent_val[1]] | {ent_val[0]}
        for bas, _son, _l, kl in a.ifadeler():
            if not (b < bas < s) or not re.match(r"^\s*READ\s+ENTIT(?:Y|IES)\b", kl, re.I):
                continue
            okunan = {x.lower() for x in re.findall(r"\bENTITY\s+(\w+)", kl, re.I)}
            if not okunan:
                out.append(W(bas, f"delete tetikli validation `{ent_val[1]}` içinde READ — okunan entity belirlenemedi"))
            elif okunan & hedef:
                out.append(F(bas, f"delete tetikli validation `{ent_val[1]}` kendi entity'sini (`{', '.join(sorted(okunan & hedef))}`) "
                                  "READ ENTITIES ile okuyor → silinmiş örnek BOŞ döner, kural sessizce ölü; `keys` ile çalış"))
    return out


@kontrol("be61_cds_srvd_yorum")
def k_be61(d, c):
    mod = validator("check_cds_srvd_comment_syntax")
    if d.rel.lower().endswith((".srvd", ".srvdsrv")):
        hits = mod.tara_srvd(d.metin)
    else:
        hits = mod.tara_cds(d.metin)
    return [F(no, f"{msg[:90]}") for no, _s, msg in hits]


@kontrol("be62_bdef_backtick")
def k_be62(d, c):
    mod = validator("check_bdef_backtick")
    return [F(no, f"bdef'te {n} ters-tırnak (SAP çoğaltır)") for no, n, _s in mod.tara(d.metin)]


@kontrol("be63_alv_row_index")
def k_be63(d, c):
    rx = re.compile(r"\bINDEX\s+(e_row(?:_id)?-index)\b|\b(e_row_id-index)\b", re.I)
    out = []
    for no, (_k, kl, _y) in enumerate(abap(d).norm, 1):
        m = rx.search(kl)
        if m:
            out.append(F(no, f"ALV olayında `{m.group(1) or m.group(2)}` → `es_row_no-row_id`"))
    return out


@kontrol("be71_tables_importing")
def k_be71(d, c):
    a = abap(d)
    imp: dict[str, set[str]] = {}
    for _b, _s, _l, kl in a.ifadeler():
        m = re.match(r"^\s*(?:CLASS-)?METHODS\s+(\w+)(.*)$", kl, re.I | re.S)
        if not m:
            continue
        mm = re.search(r"\bIMPORTING\b(.*?)(?:\bEXPORTING\b|\bCHANGING\b|\bRETURNING\b|\bRAISING\b|\bEXCEPTIONS\b|$)", m.group(2), re.I | re.S)
        if mm:
            imp[m.group(1).lower()] = {x.lower() for x in re.findall(r"(?:VALUE\s*\(\s*)?\b(\w+)\s*\)?\s+TYPE\b", mm.group(1), re.I)}
    out = []
    for b, s, ad in a.bloklar("METHOD", "ENDMETHOD"):
        params = imp.get(ad.lower().split("~")[-1], set())
        if not params:
            continue
        for bas, _s, _l, kl in a.ifadeler():
            if not (b < bas < s) or not re.match(r"^\s*CALL\s+FUNCTION\b", kl, re.I):
                continue
            mt = re.search(r"\bTABLES\b(.*?)(?:\bEXCEPTIONS\b|\bEXPORTING\b|\bIMPORTING\b|\bCHANGING\b|$)", kl, re.I | re.S)
            if not mt:
                continue
            for p, akt in re.findall(r"(\w+)\s*=\s*([\w\[\]]+)", mt.group(1)):
                if akt.lower().rstrip("[]") in params:
                    out.append(F(bas, f"CALL FUNCTION TABLES `{p} = {akt}` — `{akt}` metodun IMPORTING parametresi (salt-okunur) → yerel kopyaya al"))
    return out


@kontrol("be76_wait_rap")
def k_be76(d, c):
    t = d.metin
    rap = bool(re.search(r"\bFOR\s+BEHAVIOR\s+OF\b|\bcl_abap_behavior_handler\b|\bcl_abap_behavior_saver\b", t, re.I))
    out = []
    for no, (_k, kl, _y) in enumerate(abap(d).norm, 1):
        if re.search(r"\bWAIT\s+(UP\s+TO|FOR)\b", kl, re.I):
            (out.append(F(no, "RAP davranış sınıfında `WAIT` → örtük COMMIT (LUW kayar)")) if rap else
             out.append(W(no, "`WAIT` örtük COMMIT tetikler — RAP/LUW bağlamında mı? (bağlam metinden belirlenemedi)")))
    return out


@kontrol("be81_pcre_bosluk")
def k_be81(d, c):
    out = []
    for bas, _s, lit, _kl in abap(d).ifadeler():
        for m in re.finditer(r"\bPCRE\s+(`(?:[^`]|``)*`|'(?:[^']|'')*')", lit, re.I):
            if " " in m.group(1)[1:-1]:
                out.append(F(_ilk_satir(bas, lit, m.start()), "PCRE deseninde çıplak boşluk → `\\s` kullan (0 eşleşme ölçüldü)"))
    return out


@kontrol("be85_empty_key_sort")
def k_be85(d, c):
    a = abap(d)
    bos_tip, bos_tab = set(), set()
    for _b, _s, _l, kl in a.ifadeler():
        for m in re.finditer(r"(?:^\s*(?:TYPES|DATA|CLASS-DATA)\s*:?\s*|,\s*)(\w+)\s+TYPE\s+(?:STANDARD\s+)?TABLE\s+OF\s+[^,]*?\bWITH\s+EMPTY\s+KEY\b", kl, re.I):
            (bos_tip if re.match(r"^\s*TYPES\b", kl, re.I) else bos_tab).add(m.group(1).lower())
    for _b, _s, _l, kl in a.ifadeler():
        for m in re.finditer(r"(?:^\s*(?:DATA|CLASS-DATA)\s*:?\s*|,\s*)(\w+)\s+TYPE\s+(\w+)\s*(?:[,.]|$)", kl, re.I):
            if m.group(2).lower() in bos_tip:
                bos_tab.add(m.group(1).lower())
        for m in re.finditer(r"\bDATA\s*\(\s*(\w+)\s*\)\s*=\s*VALUE\s+(\w+)\s*\(", kl, re.I):
            if m.group(2).lower() in bos_tip:
                bos_tab.add(m.group(1).lower())
    out = []
    for bas, _s, _l, kl in a.ifadeler():
        m = re.match(r"^\s*SORT\s+([\w\-]+)\s*(.*)$", kl, re.I | re.S)
        if m and m.group(1).lower().split("-")[-1] in bos_tab and not re.search(r"\bBY\b", m.group(2), re.I):
            out.append(F(bas, f"EMPTY KEY tablo `{m.group(1)}` BY'sız SORT → sessizce sıralanmaz"))
        m = re.match(r"^\s*DELETE\s+ADJACENT\s+DUPLICATES\s+FROM\s+([\w\-]+)\s*(.*)$", kl, re.I | re.S)
        if m and m.group(1).lower().split("-")[-1] in bos_tab and not re.search(r"\bCOMPARING\b", m.group(2), re.I):
            out.append(F(bas, f"EMPTY KEY tablo `{m.group(1)}` COMPARING'siz DELETE ADJACENT DUPLICATES → hiçbir şey silinmez"))
    return out


@kontrol("be86_alpha_out")
def k_be86(d, c):
    out = []
    for bas, _s, lit, kl in abap(d).ifadeler():
        if re.search(r"\bALPHA\s*=\s*OUT\b", kl, re.I) and not re.search(r"\bcondense\s*\(", kl, re.I):
            out.append(W(bas, "`ALPHA = OUT` şablonu sabit genişlikli CHAR alanda sonda boşluk bırakır → `condense( )`"))
    return out


_DOC_ZINCIR = re.compile(r"^\s*(TYPES|DATA|CLASS-DATA|CONSTANTS|METHODS|CLASS-METHODS|EVENTS|CLASS-EVENTS|INTERFACES)\s*:", re.I)


@kontrol("be87_abapdoc_konum")
def k_be87(d, c):
    """`"!` ABAP Doc bloğundan hemen sonra İKİ NOKTALI zincir bildirimi → ATC 'wrong position'.
    Kanıt: bir projede 2026-10-18 — `"!` bloğu `TYPES: BEGIN OF …` öncesindeydi, ATC P2+P3
    "ABAP Doc comment is in the wrong position", düzeltme `"!`→`"`. Yalnız bu ölçülmüş biçim
    FAIL'dir; `"!` sonrası bildirim OLMAYAN satır WARN (genelleme, ölçülmedi)."""
    out = []
    satirlar = d.satirlar
    i = 0
    while i < len(satirlar):
        if satirlar[i].lstrip().startswith('"!'):
            bas = i + 1
            while i < len(satirlar) and satirlar[i].lstrip().startswith('"!'):
                i += 1
            sonraki = satirlar[i] if i < len(satirlar) else ""
            if _DOC_ZINCIR.match(sonraki):
                out.append(F(bas, f"ABAP Doc (`\"!`) iki noktalı zincir bildiriminden (`{sonraki.strip()[:40]}`) önce → "
                                  "ATC 'wrong position'; `\"!`'i zincirde öğenin önüne taşı ya da düz `\"` yap"))
            elif not re.match(r"^\s*(TYPES|DATA|CLASS-DATA|CONSTANTS|METHODS|CLASS-METHODS|EVENTS|CLASS-EVENTS|"
                              r"INTERFACES|ALIASES|CLASS|INTERFACE|PARAMETERS|SELECT-OPTIONS|BEGIN\s+OF|END\s+OF|\w+\s+TYPE)\b",
                              sonraki, re.I):
                out.append(W(bas, f"ABAP Doc (`\"!`) ardından bildirim gelmiyor (`{sonraki.strip()[:40]}`) — konum hatası olabilir"))
            continue
        i += 1
    return out


# ─────────────────────────────────────────────────────────────── BACKEND (B, --sap) ──
def sap_istemci(c: Baglam):
    if c._istemci is not None or c._sap_hata:
        return c._istemci
    try:
        from sap_adt_lib import set_explicit_working_dir  # type: ignore
        from sap_client import SAPClient  # type: ignore
        kok = c.sap_kok or c.repo
        if not (Path(kok) / ".conn_adt").is_file():
            c._sap_hata = f"`.conn_adt` bulunamadı ({kok})"
            return None
        set_explicit_working_dir(str(kok))
        c._istemci = SAPClient()
    except Exception as e:      # kimlik bilgisi BASILMAZ: yalnız tür adı
        c._sap_hata = f"SAP istemcisi kurulamadı ({type(e).__name__})"
    return c._istemci


def birimler(a: Abap) -> list[tuple[int, int, str]]:
    """ATC CI_PRETTY_PRINT birimleri: metot / FORM / FUNCTION blokları (sınıf tanım bölümü dışlanır)."""
    return a.bloklar("METHOD", "ENDMETHOD") + a.bloklar("FORM", "ENDFORM") + a.bloklar("FUNCTION", "ENDFUNCTION")


@kontrol("be88_pretty_print")
def k_be88(d, c):
    ist = sap_istemci(c)
    if ist is None:
        return [Bulgu("ÖLÇÜLEMEDİ", None, f"SAP pretty printer'a ulaşılamadı: {c._sap_hata}")]
    try:
        adt = getattr(ist, "adt_client", ist)
        bicimli = adt.pretty_print(None, d.metin)
    except Exception as e:
        return [Bulgu("ÖLÇÜLEMEDİ", None, f"pretty_print çağrısı başarısız ({type(e).__name__})")]
    a = abap(d)
    bir = birimler(a)
    if not bir:
        bir = [(1, len(a.ham), "<dosya>")]
    orj = [s.rstrip() for s in a.ham]
    yeni = [s.rstrip() for s in bicimli.splitlines()]
    farkli: set[int] = set()
    for tag, i1, i2, _j1, _j2 in difflib.SequenceMatcher(a=orj, b=yeni, autojunk=False).get_opcodes():
        if tag != "equal":
            farkli.update(range(i1 + 1, max(i2, i1 + 1) + 1))
    # FUNCTION biriminde imza deyimi (`FUNCTION x IMPORTING … .`) yerel dosya biçimidir; SAP kaynağında
    # imza üretilmiş yorum bloğudur ve Pretty Printer onu biçimlemez → ölçüm imzadan SONRA başlar
    # (ölçüldü 2026-10-18: imzalı `.func.abap`'ta tek fark büyük/küçük harfli imzaydı → sahte bulgu).
    fonk_imza_sonu = {bas: son for bas, son, _l, kl in a.ifadeler() if re.match(r"^\s*FUNCTION\b", kl, re.I)}
    out = []
    for b, s, ad in bir:
        if b in fonk_imza_sonu:
            b = fonk_imza_sonu[b] + 1
        ilk = next((n for n in range(b, s + 1) if n in farkli), None)
        if ilk is None:
            continue
        out.append(F(ilk, f"birim `{ad}` SAP Pretty Printer çıktısından farklı (ilk fark satır {ilk}) — "
                          "birimi bütünüyle biçimle (adt-classes 'Incorrect Pretty Print state'); "
                          "not: uç kullanıcının ADT ayarını kullanır, ATC varyantı farklıysa sonuç farklı olabilir"))
    return out


@kontrol("be16_alan_drop")
def k_be16(d, c):
    if d.yol is None:
        return [Bulgu("ÖLÇÜLEMEDİ", None, "dosya diskte değil")]
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(c.sap_kok or c.repo))
    try:
        r = subprocess.run([sys.executable, str(VALIDATORS / "check_table_field_drop.py"), str(d.yol)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env=env)
    except Exception as e:
        return [Bulgu("ÖLÇÜLEMEDİ", None, f"check_table_field_drop koşturulamadı ({type(e).__name__})")]
    if "measured=false" in (r.stdout or ""):
        return [Bulgu("ÖLÇÜLEMEDİ", None, "check_table_field_drop: measured=false")]
    if r.returncode == 0:
        return []
    son = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["?"]
    return [F(None, f"check_table_field_drop rc={r.returncode}: {son[0][:120]}")]


# ───────────────────────────────────────────────────────────────── FRONTEND (A) ──
def _js_satirlari(d: Dosya) -> list[tuple[int, str]]:
    return js_kod(d.metin) if d.rel.lower().endswith(".js") else list(enumerate(d.satirlar, 1))


def _xml_kod(d: Dosya) -> str:
    return re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), d.metin, flags=re.S)


@kontrol("fe01_v2_nav")
def k_fe01(d, c):
    mod = validator("check_ui5_freestyle_traps")
    return [F(no, f"V2 nav `_X` (→ to_X): {k.strip()[:80]}") for no, k in js_kod(d.metin)
            if any(p.search(k) for p in mod._T1_PATTERNS)]


_FE06_EBEVEYN = {"VBox", "HBox", "FlexBox", "CSSGrid"}


@kontrol("fe06_core_title")
def k_fe06(d, c):
    """`core:Title` (sap.ui.core.Title) VBox/HBox/FlexBox/CSSGrid çocuğu → FAIL.
    Aggregation düğümü (`<items>`) atlanıp asıl kontrole bakılır. Form içindeki
    `core:Title` meşrudur (Form başlığı) → PASS."""
    import xml.etree.ElementTree as ET
    if "core:Title" not in d.metin and "}Title" not in d.metin:
        return U("core:Title yok")
    try:
        kok = ET.fromstring(d.metin.encode("utf-8"))
    except ET.ParseError as e:
        return [Bulgu("ÖLÇÜLEMEDİ", None, f"XML ayrıştırılamadı ({e})")]
    ebeveyn = {ch: p for p in kok.iter() for ch in p}

    def yerel(el):
        return el.tag.rsplit("}", 1)[-1]

    def ns(el):
        return el.tag[1:].split("}", 1)[0] if el.tag.startswith("{") else ""

    out = []
    satirlar = d.satirlar
    gorulen = 0
    for el in kok.iter():
        if yerel(el) != "Title" or ns(el) != "sap.ui.core":
            continue
        gorulen += 1
        p = ebeveyn.get(el)
        if p is not None and yerel(p)[:1].islower():      # aggregation düğümü
            p = ebeveyn.get(p)
        if p is not None and yerel(p) in _FE06_EBEVEYN:
            no = next((i for i, s in enumerate(satirlar, 1) if "core:Title" in s and gorulen ==
                       sum(1 for x in satirlar[:i] if "core:Title" in x)), None)
            out.append(F(no, f"`core:Title` `{yerel(p)}` çocuğu → render crash (not valid for aggregation); sap.m.Title kullan"))
    return out


@kontrol("ip_fe07_type_number")
def k_fe07(d, c):
    mod = validator("check_ui5_freestyle_traps")
    return [W(no, "`type=\"Number\"` — grid/miktar input'uysa type=Text+liveChange (sayaç filtresi istisna)")
            for no, s in enumerate(_xml_kod(d).splitlines(), 1) if mod._T2_PATTERN.search(s)]


@kontrol("fe33_form_container")
def k_fe33(d, c):
    mod = validator("check_ui5_freestyle_traps")
    metin = _xml_kod(d)
    out = []
    for m in mod._T4_FIELDS_RE.finditer(metin):
        cm = mod._T4_CONTAINER_RE.search(m.group(1))
        if cm:
            out.append(F(metin.count("\n", 0, m.start(1) + cm.start()) + 1,
                         f"`<f:fields>` içinde `<{cm.group(1)}>` → Form/ColumnLayout geçersiz içerik (diyalog açılmaz)"))
    return out


@kontrol("fe13_grid")
def k_fe13(d, c):
    mod = validator("check_list_view_grid")
    ad = d.rel.rsplit("/", 1)[-1]
    if not mod.is_list_view(ad, d.metin):
        return U("liste/rapor adlı view değil")
    return [F(1, f"liste view'ı sap.m.Table ({n} kolon) — sap.ui.table + TablePersonalizer (ADR 0008)")
            for _no, n in mod.scan_view(ad, d.metin)]


@kontrol("fe32_filter")
def k_fe32(d, c):
    mod = validator("check_filter_search_pattern")
    out = []
    if d.rel.lower().endswith(".js"):
        out += [F(no, "`caseSensitive:false` → /IWBEP toupper 400") for no, k in js_kod(d.metin) if mod._CASE_SENS.search(k)]
    elif re.search(r"filter", d.rel.rsplit("/", 1)[-1], re.I):
        if mod._VHREQ.search(d.metin) and not mod._MULTIINPUT.search(d.metin):
            out.append(W(None, "filtre view'ında F4 var, MultiInput yok (tek değer Input)"))
    return out + [E(None, "(c)-(e) joker/defaultOp/kolon filtresi yargı")]


def _app_koku(rel: str) -> str:
    i = rel.lower().find("/webapp/")
    return rel[: i + len("/webapp")] if i >= 0 else rel.rsplit("/", 1)[0]


def _app_dosyalari(d: Dosya, c: Baglam, desen: str) -> list[Dosya]:
    kok = _app_koku(d.rel)
    anahtar = ("app", kok, desen)
    if anahtar in c.onbellek:
        return c.onbellek[anahtar]
    sonuc = {x.rel: x for x in c.dosyalar if x.rel.startswith(kok + "/") and glob_eslesir(x.rel, [desen])}
    disk = c.repo / kok
    if disk.is_dir():
        for p in _dosyalar_budayarak(disk):
            rel = p.relative_to(c.repo).as_posix()
            if rel not in sonuc and glob_eslesir(rel, [desen]):
                try:
                    sonuc[rel] = Dosya(rel, p.read_text(encoding="utf-8", errors="replace"), yol=p)
                except OSError:
                    pass
    c.onbellek[anahtar] = list(sonuc.values())
    return c.onbellek[anahtar]


def _props_anahtarlar(metin: str) -> set[str]:
    out = set()
    for s in metin.splitlines():
        s = s.strip()
        if not s or s[0] in "#!":
            continue
        m = re.match(r"([^=:\s]+)\s*[=:]", s)
        if m:
            out.add(m.group(1))
    return out


@kontrol("fe11_i18n")
def k_fe11(d, c):
    i18n = [x for x in _app_dosyalari(d, c, "**/i18n/*.properties")]
    taban = next((x for x in i18n if x.rel.lower().endswith("/i18n.properties")), None)
    tr = next((x for x in i18n if x.rel.lower().endswith("/i18n_tr.properties")), None)
    if taban is None and tr is None:
        return U("uygulamada i18n dosyası yok")
    kumeler = {"i18n.properties": _props_anahtarlar(taban.metin) if taban else None,
               "i18n_tr.properties": _props_anahtarlar(tr.metin) if tr else None}
    out = []
    satirlar = _js_satirlari(d) if d.rel.lower().endswith(".js") else list(enumerate(_xml_kod(d).splitlines(), 1))
    rx_xml = re.compile(r"\{i18n>([\w.\-]+)\}")
    rx_js = re.compile(r"\b(?:getText|_txt|_t|_i18n)\(\s*[\"']([\w.\-]+)[\"']\s*[,)]")
    for no, s in satirlar:
        for m in list(rx_xml.finditer(s)) + list(rx_js.finditer(s)):
            k = m.group(1)
            eksik = [ad for ad, kume in kumeler.items() if kume is not None and k not in kume]
            eksik += [ad for ad, kume in kumeler.items() if kume is None]
            if eksik:
                out.append(F(no, f"i18n anahtarı `{k}` tanımsız: {', '.join(eksik)}"))
    return out


@kontrol("fe26_settings_data")
def k_fe26(d, c):
    try:
        man = json.loads(d.metin)
    except Exception:
        return [Bulgu("ÖLÇÜLEMEDİ", None, "manifest.json ayrıştırılamadı")]
    modeller = (man.get("sap.ui5") or {}).get("models") or {}
    js = _app_dosyalari(d, c, "**/*.js") + _app_dosyalari(d, c, "**/*.xml")
    out = []
    for ad, tanim in modeller.items():
        if not isinstance(tanim, dict) or "JSONModel" not in str(tanim.get("type", "")):
            continue
        ayar = tanim.get("settings")
        if isinstance(ayar, dict) and "data" in ayar:
            kullanim = any(re.search(rf"{re.escape(ad)}>/data/", x.metin) for x in js) if ad else False
            if not kullanim:
                no = next((i for i, s in enumerate(d.satirlar, 1) if '"data"' in s), None)
                out.append(F(no, f"JSONModel `{ad}` settings.data çift sarmalama — `{{{ad}>/...}}` kök binding'leri undefined"))
    return out


_FE35_AD = re.compile(r"(Qty|Quantity|Miktar|Bakiye|Remaining|Delivered)", re.I)
_FE35_DISLA = re.compile(r"(Unit|Uom|Text|Txt|Label|Desc)$", re.I)


@kontrol("fe35_qty_formatter")
def k_fe35(d, c):
    """`text` özniteliğinde formatter'sız VERİ binding'i: yol adı checklist'in miktar
    listesine uyar ve birim/metin alanı değildir. `{i18n>…}` etiketleri sayılmaz."""
    rx = re.compile(r"""\btext\s*=\s*"([^"]*)\"""")   # görüntü (Text/Label/ObjectStatus); Input `value` düzenlemedir
    out = []
    for no, s in enumerate(_xml_kod(d).splitlines(), 1):
        for m in rx.finditer(s):
            deger = m.group(1)
            if "{" not in deger or "formatter" in deger or re.search(r"\btype\s*:", deger):
                continue
            for model, yol in re.findall(r"\{\s*(\w+>)?([^{}\s,:]+)\s*\}", deger):
                if model == "i18n>":
                    continue
                son = yol.rsplit("/", 1)[-1]
                if _FE35_AD.search(son) and not _FE35_DISLA.search(son):
                    out.append(F(no, f"miktar alanı `{son}` formatter'sız binding (`{deger[:50]}`) → OData QUAN \"14.000\" basar"))
                    break
    return out


@kontrol("fe42_callfunction_yuk")
def k_fe42(d, c):
    out = []
    metin = "\n".join(k for _n, k in js_kod(d.metin))
    for m in re.finditer(r"\.callFunction\s*\(", metin):
        govde = metin[m.end(): m.end() + 1500]
        up = re.search(r"urlParameters\s*:\s*\{", govde)
        if not up:
            continue
        blok = _parantez_blogu(govde, up.end() - 1)
        if re.search(r"JSON\.stringify\s*\(|\bbtoa\s*\(|base64", blok, re.I):
            out.append(F(metin.count("\n", 0, m.start()) + 1,
                         "callFunction urlParameters'ta sınırsız yük (JSON.stringify/base64) → URL 414; useBatch:true ikinci model"))
    return out


def _parantez_blogu(metin: str, ac: int) -> str:
    acan = metin[ac]
    kapa = {"{": "}", "(": ")", "[": "]"}[acan]
    der = 0
    for i in range(ac, len(metin)):
        if metin[i] == acan:
            der += 1
        elif metin[i] == kapa:
            der -= 1
            if der == 0:
                return metin[ac + 1:i]
    return metin[ac + 1:]


@kontrol("fe43_metadataurlparams")
def k_fe43(d, c):
    metin = "\n".join(k for _n, k in js_kod(d.metin))
    out = []
    for m in re.finditer(r"\bnew\s+(?:\w+\.)*ODataModel\s*\(", metin):
        blok = _parantez_blogu(metin, m.end() - 1)
        if "metadataUrlParams" not in blok:
            out.append(F(metin.count("\n", 0, m.start()) + 1,
                         "`new ODataModel(` metadataUrlParams devralmıyor → metadata hatasında kalıcı busy (ana modelin mMetadataUrlParams'ı)"))
    return out


@kontrol("fe46_cdn_bootstrap")
def k_fe46(d, c):
    out = []
    for no, s in enumerate(d.satirlar, 1):
        if re.search(r"sap-ui-core\.js", s) and (re.search(r"ui5\.sap\.com/", s) or re.search(r"""src\s*=\s*["']resources/""", s)):
            out.append(F(no, "UI5 bootstrap CDN/göreli `resources/` → `/sap/public/bc/ui5_ui5/resources/sap-ui-core.js`"))
    return out


@kontrol("fe47_urlparam_null")
def k_fe47(d, c):
    metin = "\n".join(k for _n, k in js_kod(d.metin))
    out = []
    for m in re.finditer(r"urlParameters\s*:\s*\{", metin):
        blok = _parantez_blogu(metin, m.end() - 1)
        for mm in re.finditer(r"(\w+)\s*:\s*(null|undefined)\b", blok):
            out.append(F(metin.count("\n", 0, m.end() + mm.start()) + 1,
                         f"urlParameters `{mm.group(1)}: {mm.group(2)}` → URL'e `=null` yazılır (400); parametreyi koşullu ekle"))
    return out


@kontrol("fe49_sync_xhr")
def k_fe49(d, c):
    out = []
    kod = "\n".join(k for _n, k in js_kod(d.metin))
    unload = bool(re.search(r"""["'](?:beforeunload|pagehide|unload)["']|\bonbeforeunload\b|\bonunload\b""", kod))
    for no, k in js_kod(d.metin):
        if re.search(r"\.open\s*\([^)]*,\s*false\s*\)", k):
            if unload:
                out.append(F(no, "senkron XHR (`open(…, false)`) unload dinleyicili dosyada — Chromium göndermez → fetch keepalive + x-csrf-token"))
            else:
                out.append(W(no, "senkron XHR (`open(…, false)`) — unload dinleyicisinden çağrılıyorsa Chromium göndermez (çağıranı izle)"))
        if re.search(r"sendBeacon\s*\(", k):
            out.append(W(no, "`sendBeacon` CSRF başlığı taşıyamaz — kilit bırakma için fetch keepalive + x-csrf-token"))
    return out


@kontrol("fe50_multiinput_validator")
def k_fe50(d, c):
    if not re.search(r"<(?:\w+:)?MultiInput\b", _xml_kod(d)):
        return U("MultiInput yok")
    js = _app_dosyalari(d, c, "**/*.js")
    if any("addValidator" in "\n".join(k for _n, k in js_kod(x.metin)) for x in js):
        return [E(None, "(a) addValidator uygulamada var; (b)-(f) yargı + canlı kanıt (yaz+Enter → token, $filter)")]
    no = next(i for i, s in enumerate(d.satirlar, 1) if "MultiInput" in s)
    return [F(no, f"MultiInput var, uygulamanın {len(js)} JS dosyasında `addValidator` YOK → yazılı metin token olmaz, filtre sessizce düşer")]


@kontrol("fe51_selectall")
def k_fe51(d, c):
    no = next((i for i, s in enumerate(_xml_kod(d).splitlines(), 1) if re.search(r"""enableSelectAll\s*=\s*["']false["']""", s)), None)
    if no is None:
        return U("enableSelectAll=\"false\" yok")
    js = _app_dosyalari(d, c, "**/*.js")
    if any(re.search(r"""getParameter\(\s*["']selectAll["']\s*\)""", "\n".join(k for _n, k in js_kod(x.metin))) for x in js):
        return []
    return [F(no, "enableSelectAll=\"false\" Ctrl+A'yı ENGELLEMEZ; JS'te `getParameter(\"selectAll\")` ele alınmamış")]


# ───────────────────────────────────────────────────────────────────── C ipuçları ──
@kontrol("ip_fe24_toast_nav")
def k_ip_fe24(d, c):
    sat = js_kod(d.metin)
    out = []
    for i, (no, k) in enumerate(sat):
        if "MessageToast.show" in k and any(".navTo(" in k2 for _n2, k2 in sat[i:i + 4]):
            out.append(E(no, "MessageToast + hemen navTo — toast kaybolabilir (aday)"))
    return out


@kontrol("ip_fe38_promise_all")
def k_ip_fe38(d, c):
    metin = "\n".join(k for _n, k in js_kod(d.metin))
    if "Promise.all" in metin and re.search(r"\.(remove|update|create)\s*\(", metin):
        no = metin[: metin.find("Promise.all")].count("\n") + 1
        return [E(no, "Promise.all + OData değişiklik isteği aynı dosyada (aday: paralel kilit)")]
    return []


@kontrol("ip_fe48_client_param")
def k_ip_fe48(d, c):
    metin = "\n".join(k for _n, k in js_kod(d.metin))
    if re.search(r"new\s+XMLHttpRequest|\bfetch\s*\(|sServiceUrl\s*\+", metin) and not re.search(r"aUrlParams|sap-client|_secondModelUrl", metin):
        return [E(None, "elle kurulan istek var, ana modelin client parametresi izi yok (aday)")]
    return []


@kontrol("ip_fe30_client_prop")
def k_ip_fe30(d, c):
    sat = js_kod(d.metin)
    kod = "\n".join(k for _n, k in sat)
    if not re.search(r"\b(submitChanges|createEntry)\s*\(", kod):
        return []
    return [E(no, "OData context'e `_`-önekli setProperty + aynı dosyada submitChanges/createEntry (aday)")
            for no, k in sat if re.search(r"""setProperty\(\s*(?:["'][^"']*/)?["']?_\w+""", k)]


@kontrol("ip_fe44_file_size")
def k_ip_fe44(d, c):
    x = _xml_kod(d)
    if not re.search(r"<(?:\w+:)?FileUploader\b", x):
        return []
    if "maximumFileSize" not in x:
        no = next(i for i, s in enumerate(x.splitlines(), 1) if "FileUploader" in s)
        return [E(no, "FileUploader'da maximumFileSize yok (aday: boyut kapısı JS'te mi?)")]
    return [E(None, "maximumFileSize var — tek-sabit izi / falsy tuzağı / fileSizeExceed yargı")]


# ─────────────────────────────────────────────────────────────────────── DOC (A) ──
@kontrol("doc_kd15_mermaid")
def k_doc_kd15(d, c):
    mod = validator("check_kd_no_raw_mermaid")
    out = []
    md = d.rel.lower().endswith(".md")
    for no, s in enumerate(d.satirlar, 1):
        if (not md and mod._RAW_MERMAID_RE.search(s)) or (md and re.match(r"^\s*```\s*mermaid\b", s, re.I)):
            out.append(F(no, "ham mermaid kaynağı (render edilmemiş) — PNG'ye çevrilmeli" +
                         (" (md: build `preprocess_mermaid_fences`'e bağlı değilse)" if md else "")))
    if md and out:
        return [W(b.satir, b.mesaj) for b in out]   # md'de fence meşru olabilir (build PNG'ye çevirir)
    return out


def _slug_tr():
    if "slug" not in _MODUL_ONBELLEK:
        try:
            spec = importlib.util.spec_from_file_location("_cc_slug", SCRIPTS / "build_doc_pdf.py")
            src = (SCRIPTS / "build_doc_pdf.py").read_text(encoding="utf-8")
            # build_doc_pdf `markdown` paketini import eder; yalnız slug_tr + _TR_MAP alınır
            ns: dict = {"re": re, "unicodedata": __import__("unicodedata")}
            m1 = re.search(r"^_TR_MAP\s*=.*?$", src, re.M)
            m2 = re.search(r"^def slug_tr\(.*?(?=^def |\Z)", src, re.M | re.S)
            exec(m1.group(0) + "\n" + m2.group(0), ns)
            _MODUL_ONBELLEK["slug"] = ns["slug_tr"]
            del spec
        except Exception:
            _MODUL_ONBELLEK["slug"] = None
    return _MODUL_ONBELLEK["slug"]


def _slug_github(baslik: str) -> str:
    """GitHub/GitLab başlık çapası: küçük harf, harf/rakam/`-`/boşluk dışı silinir, Unicode KORUNUR.
    md bağlantısı build_doc_pdf.slug_tr'ye YA DA bu biçime uyarsa canlı sayılır (iki üretici yolu var);
    ürünün kendisi (html) ayrıca `id`/`name` kümesiyle ölçülür."""
    # U+0307: "İ".lower() = "i" + birleşik nokta; `\w` onu silerdi, GitHub korur
    return re.sub(r" ", "-", re.sub(r"[^\w\- ̇]", "", baslik.strip().lower()))


@kontrol("doc_kd16_capa")
def k_doc_kd16(d, c):
    out = []
    if d.rel.lower().endswith((".html", ".htm")):
        hedef = set(re.findall(r"""\bid\s*=\s*["']([^"']+)["']""", d.metin)) | \
            set(re.findall(r"""<a\b[^>]*\bname\s*=\s*["']([^"']+)["']""", d.metin, re.I))
        for no, s in enumerate(d.satirlar, 1):
            for h in re.findall(r"""href\s*=\s*["']#([^"']+)["']""", s):
                if h not in hedef:
                    out.append(F(no, f"ölü iç bağlantı `#{h}` (id/name hedefi yok)"))
        return out
    slug = _slug_tr()
    if slug is None:
        return [Bulgu("ÖLÇÜLEMEDİ", None, "build_doc_pdf.slug_tr yüklenemedi")]
    hedef, kodda = set(), False
    for s in d.satirlar:
        if s.strip().startswith("```"):
            kodda = not kodda
        if not kodda:
            m = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", s)
            if m:
                baslik = m.group(1)
                ma = re.search(r"\{[^}]*#([\w\-]+)[^}]*\}\s*$", baslik)
                if ma:                                  # `## Başlık {#ozel-id}` (attr_list)
                    hedef.add(ma.group(1))
                    baslik = baslik[:ma.start()].rstrip()
                hedef.add(slug(baslik))
                hedef.add(_slug_github(baslik))
            hedef |= set(re.findall(r"""<a\s+(?:name|id)\s*=\s*["']([^"']+)["']""", s))
    kodda = False
    for no, s in enumerate(d.satirlar, 1):
        if s.strip().startswith("```"):
            kodda = not kodda
            continue
        if kodda:
            continue
        for h in re.findall(r"\]\(#([^)\s]+)\)", s):
            if h not in hedef:
                out.append(F(no, f"ölü iç bağlantı `#{h}` (başlık slug'ı yok)"))
    return out


@kontrol("doc_kd11_gorsel")
def k_doc_kd11(d, c):
    if d.yol is None:
        return [Bulgu("ÖLÇÜLEMEDİ", None, "dosya diskte değil (göreli görsel yolu çözülemez)")]
    out = []
    for no, s in enumerate(d.satirlar, 1):
        for r in re.findall(r"!\[[^\]]*\]\(([^)\s]+)", s) + re.findall(r"""<img\b[^>]*\bsrc\s*=\s*["']([^"']+)["']""", s, re.I):
            if re.match(r"^(https?:|data:|//)", r):
                continue
            yol = (d.yol.parent / r.split("#")[0].split("?")[0])
            if not yol.exists():
                out.append(F(no, f"görsel bulunamadı: `{r}`"))
    return out + [E(None, "PDF üretimi + uygulama içi yardım görünürlüğü yargı/çalışma zamanı")] if not out else out


@kontrol("doc_kd13_itf")
def k_doc_kd13(d, c):
    mod = validator("check_docu_itf_line_width")
    if not mod._IS_DOCU_RUNNER.search(d.metin):
        return U("DOCU runner değil")
    out = []
    for h in mod.scan_text(d.metin):
        if h[0] == "WIDTH":
            out.append(F(h[1], f"ITF iv_line {h[2]} karakter (>72 görüntüleme)"))
        else:
            out.append(F(h[1], f"ITF tag satırda açılıp kapanmıyor (açılış {h[2]} / kapanış {h[3]})"))
    return out


def _fs_scan(d):
    return validator("check_fs_no_analysis_log").scan_text(d.metin)


@kontrol("doc_fs05_gunluk")
def k_doc_fs05(d, c):
    bulgular, _uzun, _govde = _fs_scan(d)
    out = [W(no, f"[{sinif}] {sn[:80]}") for sinif, liste in bulgular.items() for no, sn in liste]
    return out or [E(None, "kalıp sayımı 0; 'bugünkü hâl mi, nasıl bulundu mu' üslup yargısı reviewer'da")]


@kontrol("doc_fs06a_surum_satiri")
def k_doc_fs06a(d, c):
    mod = validator("check_fs_no_analysis_log")
    _b, uzun, _g = _fs_scan(d)
    return [W(no, f"versiyon/kimlik satırı {n} karakter (> {mod.VERSION_ROW_MAX})") for no, n in uzun]


_KIMLIK = re.compile(r"\b(?:FR|KR|AC|NFR|TC|ERR|EXC|SCR|ÖK|OK|K|T|G|R)-\d{1,4}[a-z]?\b")


@kontrol("doc_fs07_veri_kaybi")
def k_doc_fs07(d, c):
    if d.eski is None:
        return [Bulgu("ÖLÇÜLEMEDİ", None, "eski sürüm yok (yalnız --diff kipinde ölçülür)")]
    eski = set(_KIMLIK.findall(d.eski))
    yeni = set(_KIMLIK.findall(d.metin))
    ek_metin = "".join(x.metin for x in c.kardes(d, "**/EK-*.md"))
    kayip = sorted(k for k in eski - yeni if k not in ek_metin)
    out = [F(None, f"kimlik kayboldu (yeni belge ∪ EK'te yok): {', '.join(kayip[:15])}" + (" …" if len(kayip) > 15 else ""))] if kayip else []
    return out + [E(None, "cümle düzeyi denklik (bulanık eşleşme) yargı")]


@kontrol("doc_ts05_mesaj")
def k_doc_ts05(d, c):
    out = []
    baslik_mesaj = False
    sutun = None
    t100_satir = 0
    for no, s in enumerate(d.satirlar, 1):
        if s.startswith("#"):
            baslik_mesaj = bool(re.search(r"mesaj", s, re.I))
            sutun = None
            continue
        if not baslik_mesaj or not s.strip().startswith("|"):
            continue
        hucre = [h.strip() for h in s.strip().strip("|").split("|")]
        if sutun is None:
            sutun = next((i for i, h in enumerate(hucre) if re.search(r"metin|text", h, re.I)), -1)
            continue
        if sutun < 0 or set(s.replace("|", "").strip()) <= set("-: ") or sutun >= len(hucre):
            continue
        if not any(re.fullmatch(r"[*`\s]*\d{3}[*`\s]*(?:\(.*\))?", h) for h in hucre[:3]):
            continue                    # T100 satırı değil (ör. i18n anahtarı) → 73 / `&` kuralı uygulanmaz
        t100_satir += 1
        hc = hucre[sutun]
        mt = re.search(r"`([^`]+)`", hc)
        if not mt and "**" in hc:
            continue                    # vurgulu açıklama hücresi (ör. "Kullanılmıyor — …"), mesaj metni değil
        metin = mt.group(1) if mt else hc
        metin = metin.strip("*\"‹›«» _").strip()
        if not metin:
            continue
        if re.search(r"&(?!\d)", metin):
            out.append(F(no, f"mesaj metninde numarasız yer tutucu `&`: {metin[:60]}"))
        if len(metin) > 73:
            out.append(F(no, f"mesaj metni {len(metin)} karakter (> 73, T100 kırpar)"))
    if not t100_satir:
        return U("T100 mesaj envanteri satırı (3 haneli numara + metin sütunu, 'mesaj' başlığı altında) bulunamadı")
    return out + [E(None, "envanter tamlığı / üretim noktası / kullanıcı aksiyonu yargı")]


# ═════════════════════════════════════════════════════════════════════ girdi ══
def _git(repo: Path, *args, girdi: str | None = None) -> str:
    r = subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(repo), *args], capture_output=True,
                       input=girdi, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[:200]}")
    return r.stdout


def _aralik(repo: Path, aralik: str) -> tuple[str, str | None]:
    if "..." in aralik:
        sol, sag = aralik.split("...", 1)
        sag = sag or "HEAD"
        return _git(repo, "merge-base", sol or "HEAD", sag).strip(), sag
    if ".." in aralik:
        sol, sag = aralik.split("..", 1)
        return sol or "HEAD", sag or "HEAD"
    return aralik, None   # tek ref → çalışma ağacına karşı


def _cat_file(repo: Path, nesneler: list[str]) -> dict[str, str | None]:
    """`git cat-file --batch` — N dosyayı TEK süreçte okur (dosya başına `git show` yerine)."""
    if not nesneler:
        return {}
    r = subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(repo), "cat-file", "--batch"],
                       input=("\n".join(nesneler) + "\n").encode("utf-8"), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git cat-file: {r.stderr.decode('utf-8', 'replace')[:200]}")
    out, veri, i = {}, r.stdout, 0
    for ad in nesneler:
        j = veri.index(b"\n", i)
        baslik = veri[i:j].decode("utf-8", "replace")
        i = j + 1
        if baslik.endswith(" missing") or baslik.endswith(" ambiguous"):
            out[ad] = None
            continue
        boy = int(baslik.rsplit(" ", 1)[1])
        out[ad] = veri[i:i + boy].decode("utf-8", "replace")
        i += boy + 1
    return out


def girdileri_topla(repo: Path, dosyalar: list[str] | None, aralik: str | None) -> tuple[list[Dosya], list[str]]:
    hatalar = []
    out: list[Dosya] = []
    if dosyalar:
        for f in dosyalar:
            p = Path(f)
            p = p if p.is_absolute() else (repo / p)
            try:
                rel = p.resolve().relative_to(repo.resolve()).as_posix()
            except ValueError:
                rel = p.name
            if not p.is_file():
                hatalar.append(f"dosya yok: {f}")
                continue
            out.append(Dosya(rel, p.read_text(encoding="utf-8", errors="replace"), yol=p))
        return out, hatalar
    sol, sag = _aralik(repo, aralik)
    uclar = [sol, *([sag] if sag else [])]
    adlar = [a for a in _git(repo, "diff", "--no-renames", "--diff-filter=d", "--name-only", *uclar, "--").splitlines()
             if a.strip()]
    # değişen satırlar: TEK `-U0` diff'i, dosya başlıklarına göre bölünür
    degisen: dict[str, set[int]] = {}
    akim = None
    for satir in _git(repo, "diff", "--no-renames", "--diff-filter=d", "-U0", "--no-color", *uclar, "--").splitlines():
        if satir.startswith("+++ "):
            akim = satir[6:] if satir.startswith("+++ b/") else None
            if akim is not None:
                degisen.setdefault(akim, set())
            continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", satir)
        if m and akim is not None:
            bas, n = int(m.group(1)), int(m.group(2) or "1")
            degisen[akim].update(range(bas, bas + n))
    icerik = _cat_file(repo, [f"{sag}:{a}" for a in adlar]) if sag else {}
    for rel in adlar:
        if sag:
            metin = icerik.get(f"{sag}:{rel}")
            yol = None
        else:
            yol = repo / rel
            metin = yol.read_text(encoding="utf-8", errors="replace") if yol.is_file() else None
        if metin is None:
            hatalar.append(f"okunamadı: {rel}")
            continue
        out.append(Dosya(rel, metin, eski_kaynak=(lambda r=rel: _cat_file(repo, [f"{sol}:{r}"]).get(f"{sol}:{r}")),
                         degisen=degisen.get(rel, set()), yol=yol))
    return out, hatalar


# ═════════════════════════════════════════════════════════════════ değerlendirme ══
@dataclass
class Satir:
    madde: dict
    sonuc: str
    kanit: str
    blok_fail: bool = False


def _birlestir(durumlar: list[str]) -> str:
    for d in ("FAIL", "WARN", "ÖLÇÜLEMEDİ", "ELLE"):
        if d in durumlar:
            return d
    if durumlar and all(x == "UYGULANMAZ" for x in durumlar):
        return "UYGULANMAZ"
    return "PASS"


def degerlendir(madde: dict, dosyalar: list[Dosya], c: Baglam) -> Satir:
    sinif = madde.get("sinif")
    k = madde.get("kontrol")
    if sinif == "B" and not c.sap:
        return Satir(madde, "ÖLÇÜLEMEDİ" if k else "ELLE",
                     ("SAP sorgusu gerekir — `--sap` verilmedi" if k else "SAP/çalışma zamanı kanıtı gerekir (kontrol yok)")
                     + _not(madde))
    if not k:
        neden = "yargı" if sinif == "C" else ("A ama kontrol YAZILMADI" if sinif == "A" else "kontrol yok")
        return Satir(madde, "ELLE", neden + _not(madde))
    fn = KONTROLLER.get(k)
    if fn is None:
        return Satir(madde, "ELLE", f"kontrol `{k}` programda YOK (map ↔ kod tutarsız)")
    durumlar, kanitlar = [], []
    tum = bool(madde.get("tum_dosya"))
    for d in dosyalar:
        try:
            bulgular = fn(d, c)
        except Exception as e:
            durumlar.append("ÖLÇÜLEMEDİ")
            kanitlar.append(f"{d.rel}: kontrol çöktü ({type(e).__name__}: {str(e)[:60]})")
            continue
        if not bulgular:
            durumlar.append("PASS")
            continue
        for b in bulgular:
            dur = b.durum
            if dur == "FAIL" and not tum and d.degisen is not None and b.satir is not None and b.satir not in d.degisen:
                dur = "WARN"
                b.mesaj += " (değişmeyen satır — önceden var)"
            durumlar.append(dur)
            if dur != "PASS":
                yer = f"{d.rel}:{b.satir}" if b.satir else d.rel
                kanitlar.append(f"{yer} {b.mesaj}" if dur in ("FAIL", "WARN") else f"{yer} [{dur}] {b.mesaj}")
    sonuc = _birlestir(durumlar)
    if sinif == "C":
        sonuc = "ELLE"          # ipucu tarayıcısı hüküm vermez
    if sonuc == "PASS":
        kanit = f"`{k}`: {len(dosyalar)} dosya temiz ({', '.join(x.rel.rsplit('/', 1)[-1] for x in dosyalar[:3])}{' …' if len(dosyalar) > 3 else ''})"
    elif sonuc == "UYGULANMAZ":
        kanit = (f"`{k}`: " + "; ".join(sorted(set(kanitlar)))) if kanitlar else f"`{k}`: kapsam dışı ({len(dosyalar)} dosya)"
    else:
        kanit = " · ".join(kanitlar[:5]) + (f" · (+{len(kanitlar) - 5} bulgu)" if len(kanitlar) > 5 else "")
        if sinif == "C":
            kanit = ("ipucu (hüküm değil): " + kanit) if kanitlar else "yargı (ipucu taraması aday bulmadı)"
    blok = sonuc == "FAIL" and madde.get("seviye") == "blok"
    return Satir(madde, sonuc, kanit, blok)


def _not(madde: dict) -> str:
    return f" — {madde['not']}" if madde.get("not") else ""


def _md(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def calistir(args) -> int:
    t0 = time.perf_counter()
    repo = Path(args.repo).resolve()
    harita = harita_oku(Path(args.harita) if args.harita else MAP_YOLU)
    dosyalar, hatalar = girdileri_topla(repo, args.files, args.diff)
    for h in hatalar:
        print(f"UYARI: {h}", file=sys.stderr)
    ana_notlar: list[str] = []   # stdout'a (KAPSAM BEYANI) — stderr'e DEĞİL: run_review PASS+stderr'i "bulgu" sayar
    if args.ana_sinif:
        # Çağıran (run_review class_push) dosyanın sınıf ANA kaynağı olduğunu biliyor; yerel kopya
        # `.clas.abap` adını taşımayabilir (ör. `ZCL_X.abap`) → BE-10b sessizce UYGULANMAZ olurdu.
        # Include'lar (.ccimp/.ccau/.ccdef/.ccmac, locals_*, testclasses) bilerek HARİÇ.
        for d in dosyalar:
            ad = d.rel.rsplit("/", 1)[-1].lower()
            if not re.search(r"\.(ccimp|ccau|ccdef|ccmac)\.abap$|locals_(imp|def)|testclasses|macros", ad) \
                    and not ad.endswith(".clas.abap"):
                d.eslesme_adi = d.rel + ".clas.abap"
                ana_notlar.append(d.rel)
    onekler = KIND_ONEK[args.kind]
    ids = {x.strip() for x in args.ids.split(",")} if args.ids else None
    c = Baglam(repo, dosyalar, sap=args.sap, sap_kok=Path(args.sap_kok) if args.sap_kok else None)

    satirlar: list[Satir] = []
    uygulanmaz_madde = 0
    ayrildi = 0
    for m in harita:
        if not m["id"].startswith(onekler) or (ids and m["id"] not in ids):
            continue
        hedef = [d for d in dosyalar if glob_eslesir(d.eslesme_adi or d.rel, m.get("uygulanir") or [])]
        if not hedef:
            uygulanmaz_madde += 1
            continue
        if m.get("ayrildi"):
            ayrildi += 1
        satirlar.append(degerlendir(m, hedef, c))
    eslesmeyen = [d.rel for d in dosyalar
                  if not any(glob_eslesir(d.eslesme_adi or d.rel, m.get("uygulanir") or [])
                             for m in harita if m["id"].startswith(onekler))]

    print(f"## checklist_check — kapsama tablosu\n")
    print(f"Girdi: {'--diff ' + args.diff if args.diff else '--files'} · kind={args.kind} · "
          f"{len(dosyalar)} dosya · SAP={'AÇIK' if args.sap else 'kapalı'}\n")
    print(f"{HUKUM_SATIRI}\n")
    print("| ID | Sınıf | Sonuç | Kanıt |")
    print("|---|---|---|---|")
    for s in satirlar:
        son = s.sonuc + (" (BLOK)" if s.blok_fail else "")
        print(f"| {s.madde['id']} | {s.madde.get('sinif')} | {son} | {_md(s.kanit)} |")
    sayim = {r: sum(1 for s in satirlar if s.sonuc == r) for r in SONUCLAR}
    kontrolsuz_a = [s.madde["id"] for s in satirlar if s.madde.get("sinif") == "A" and not s.madde.get("kontrol")]
    blok = [s for s in satirlar if s.blok_fail]
    sure = time.perf_counter() - t0
    print("\n### KAPSAM BEYANI")
    print(f"- Uygulanan madde: {len(satirlar)} · " + " · ".join(f"{k} {v}" for k, v in sayim.items()))
    print(f"- Bu girdiye UYGULANMAYAN madde (glob eşleşmedi, tabloda yok): {uygulanmaz_madde}")
    print(f"- Hiçbir maddenin globuna girmeyen dosya ({len(eslesmeyen)}): "
          + (", ".join(eslesmeyen[:10]) + (" …" if len(eslesmeyen) > 10 else "") if eslesmeyen else "yok"))
    print(f"- ELLE = program hüküm VERMEDİ (C yargı / kontrolsüz madde) → inceleyen doldurur. "
          f"A sınıfı ama kontrolü yazılmamış: {', '.join(kontrolsuz_a) or 'yok'}")
    if not args.sap:
        print("- B sınıfı (SAP/çalışma zamanı) maddeler ÖLÇÜLMEDİ (`--sap` yok) — 'temiz' DEĞİL.")
    elif c._sap_hata:
        print(f"- `--sap` verildi ama SAP'ye ulaşılamadı: {c._sap_hata} → B maddeleri ÖLÇÜLEMEDİ.")
    if args.files:
        print("- `--files` kipinde önceden var olan ihlaller de FAIL sayılır (`--diff` kipinde değişmeyen "
              "satırdaki A-FAIL → WARN \"(önceden var)\"; `tum_dosya: true` maddeler hariç).")
    if ana_notlar:
        print(f"- `--ana-sinif`: {', '.join(ana_notlar)} sınıf ANA kaynağı sayıldı (ad `.clas.abap` değil)")
    if ayrildi:
        print(f"- {ayrildi} madde `ayrildi: true` (checklist metni henüz yazılmamış ayrılmış kimlik).")
    print("- Program checklist METNİNİ okumaz; kontrol desenleri map'teki fonksiyonlardır — "
          "desenin yakalamadığı yazım biçimi 'PASS'e dahil olabilir (PASS = desen bulmadı).")
    print(f"- Süre: {sure:.2f} sn")
    if blok:
        print(f"\n⛔ ENGELLEYİCİ: {', '.join(s.madde['id'] for s in blok)} FAIL (seviye: blok)")

    rc = 1 if blok else 0
    if args.verify_report:
        rc = max(rc, rapor_dogrula(Path(args.verify_report), satirlar))
    return rc


# ═══════════════════════════════════════════════════════════════ --verify-report ══
# ⭐ KANONİK HÜKÜM KÜMESİ — tek tanım (ajan tanımları ve rapor şablonu buna uyar; 2026-10-18 lider kararı).
# `FAIL→F<n>`: rapordaki bulgu numarasına bağlanan FAIL · `UYGULANMAZ+gerekçe`: gerekçe aynı satırda ŞART
# (kanıt sütunu boşsa `kanıtsız`) · `ÇÜRÜTÜLDÜ`: program A-FAIL dedi, inceleyen yanlış-pozitif olduğunu
# KANITLADI (kanıt şart; çelişki sayılmaz; korpus kalibrasyon adayı olarak ayrı listelenir).
# Eşanlamlı kabul edilen tek yazımlar: WARNING (=WARN) · OLCULEMEDI · CURUTULDU (ASCII). Başka kelime
# (BULGU, ilgisiz, BLOCKER, N/A …) hüküm DEĞİLDİR → satır `hükümsüz` sayılır.
HUKUMLER = ("PASS", "FAIL→F<n>", "WARN", "UYGULANMAZ+gerekçe", "ÖLÇÜLEMEDİ", "ELLE", "ÇÜRÜTÜLDÜ")
HUKUM_SATIRI = "Geçerli hükümler: " + " · ".join(HUKUMLER)
_HUKUM = re.compile(r"(?<![\w])(PASS|FAIL|WARN|WARNING|UYGULANMAZ|ÖLÇÜLEMED[İIi]|OLCULEMEDI|ELLE|ÇÜRÜTÜLDÜ|CURUTULDU)(?![\w])", re.I)
_HUKUM_NORM = {"WARNING": "WARN", "OLCULEMEDI": "ÖLÇÜLEMEDİ", "CURUTULDU": "ÇÜRÜTÜLDÜ"}


def _hukum_tokenlari(hucre: str) -> list[str]:
    out = []
    for m in _HUKUM.finditer(hucre):
        t = m.group(1).upper()
        if t.startswith(("ÖLÇÜLEMED", "OLCULEMED")):   # "ölçülemedi".upper() noktasız I verir
            t = "ÖLÇÜLEMEDİ"
        out.append(_HUKUM_NORM.get(t, t))
    return out


def _kanit_mi(hucre: str) -> bool:
    """Hüküm sözcükleri + `→F<n>` + süs çıkarıldıktan sonra anlamlı metin kalıyorsa kanıttır."""
    kalan = _HUKUM.sub(" ", hucre)
    kalan = re.sub(r"→\s*F\d+|\(BLOK\)|[*`_~|+—–\-:·.,()\[\]]", " ", kalan)
    kalan = kalan.strip()
    return len(re.findall(r"\w", kalan)) >= 2 and kalan not in ("A", "B", "C")


def rapor_dogrula(rapor: Path, satirlar: list[Satir]) -> int:
    try:
        metin = rapor.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        # okunamayan rapor bir EKSİKLİK değil, programın koşamamasıdır → exit 2
        raise ProgramKosmadi(f"--verify-report raporu okunamadı: {e}") from e
    hucreler: dict[str, list[list[str]]] = {}
    for s in metin.splitlines():
        if not s.strip().startswith("|"):
            continue
        h = [x.strip() for x in re.split(r"(?<!\\)\|", s.strip().strip("|"))]   # `\|` hücre içi kaçış
        m = re.fullmatch(r"\**`?((?:BE|FE|DOC)-[0-9A-Za-z-]+)`?\**", h[0]) if h else None
        if m:
            hucreler.setdefault(m.group(1), []).append(h[1:])
    eksik, hukumsuz, kanitsiz, elle, celiski, curutulen = [], [], [], [], [], []
    for s in satirlar:
        mid = s.madde["id"]
        rows = hucreler.get(mid)
        if not rows:
            eksik.append(mid)
            continue
        h = rows[-1]
        hk = [t for x in h for t in _hukum_tokenlari(x)]
        if not hk:
            hukumsuz.append(mid)
            continue
        if all(x == "ELLE" for x in hk):
            elle.append(mid)
            continue
        if not any(_kanit_mi(x) for x in h):
            kanitsiz.append(mid)
            continue
        if "ÇÜRÜTÜLDÜ" in hk:
            # yanlış-pozitif kanıtlandı → çelişki DEĞİL; kalibrasyon adayı
            curutulen.append(f"{mid} (program: {s.sonuc})")
            continue
        if s.sonuc == "FAIL" and s.madde.get("sinif") == "A" and "PASS" in hk and "FAIL" not in hk:
            celiski.append(mid)
    print("\n### --verify-report")
    print(f"- Rapor: {rapor.name} · beklenen madde {len(satirlar)} · {HUKUM_SATIRI}")
    for ad, liste in (("satır yok", eksik), ("hükümsüz", hukumsuz), ("kanıtsız", kanitsiz),
                      ("ELLE", elle), ("ÇELİŞKİ", celiski)):
        print(f"- {ad}: {len(liste)}" + (f" → {', '.join(liste)}" if liste else ""))
    print("  (ELLE = yargı doldurulmamış · ÇELİŞKİ = program A-FAIL, rapor PASS)")
    if curutulen:
        print(f"\n#### ÇÜRÜTÜLDÜ — korpus kalibrasyon adayı ({len(curutulen)}; eksiklik DEĞİL)")
        for x in curutulen:
            print(f"- {x}")
    eksiklik = [ad for ad, liste in (("satır yok", eksik), ("hükümsüz", hukumsuz), ("kanıtsız", kanitsiz),
                                     ("ELLE", elle), ("ÇELİŞKİ", celiski)) if liste]
    if eksiklik:
        print(f"\n⛔ RAPOR EKSİK: {' · '.join(eksiklik)}")
    return 1 if eksiklik else 0


# ═════════════════════════════════════════════════════════════════════ --reach ══
def reach(harita: list[dict]) -> int:
    print("## checklist_check --reach (yazan_kanali ulaşım testi)\n")
    print("| ID | yazan_kanali | Sonuç | Kanıt |")
    print("|---|---|---|---|")
    eksik = 0
    n = 0
    for m in harita:
        hedef = m.get("yazan_kanali")
        if not hedef:
            continue
        n += 1
        p = CORE / hedef
        if not p.is_file():
            print(f"| {m['id']} | {hedef} | FAIL | dosya yok |")
            eksik += 1
            continue
        metin = p.read_text(encoding="utf-8", errors="replace")
        capa = m.get("capa")
        rx = re.compile(rf"(?<![\w-]){re.escape(m['id'])}(?![\w])")
        bul = rx.search(metin) or (capa and capa in metin)
        if bul:
            no = metin[: bul.start()].count("\n") + 1 if hasattr(bul, "start") else "çapa"
            print(f"| {m['id']} | {hedef} | PASS | satır {no} |")
        else:
            print(f"| {m['id']} | {hedef} | FAIL | ne `{m['id']}` ne çapa ({capa!r}) geçiyor |")
            eksik += 1
    print(f"\n### KAPSAM BEYANI\n- yazan_kanali dolu madde: {n} · ulaşmayan: {eksik} · "
          f"yazan_kanali BOŞ madde: {sum(1 for m in harita if not m.get('yazan_kanali'))} (ölçülmedi)")
    return 1 if eksik else 0


# ════════════════════════════════════════════════════════════ --harita-denetim ══
def checklist_kimlikleri() -> dict[str, set[str]]:
    out = {}
    for onek, yol in CHECKLISTLER.items():
        ids = set()
        for s in yol.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\|\s*\**`?((?:BE|FE|DOC)-[0-9A-Za-z]+(?:-[0-9A-Za-z]+)?)`?\**\s*\|", s)
            if m:
                ids.add(m.group(1))
        out[onek] = ids
    return out


ALANLAR = {"id", "sinif", "uygulanir", "kontrol", "seviye", "yazan_kanali", "not", "ayrildi", "tum_dosya", "capa"}


def harita_denetim(yol: Path) -> int:
    hatalar, notlar = [], []
    try:
        harita = harita_oku(yol)
    except Exception as e:
        # okunamayan/ayrıştırılamayan map = program KOŞMADI (exit 2), içerik ihlali (exit 1) değil
        raise ProgramKosmadi(f"map okunamadı: {type(e).__name__}: {e}") from e
    ck = checklist_kimlikleri()
    tum_ck = set().union(*ck.values())
    gorulen = {}
    for m in harita:
        mid = m.get("id")
        if not mid:
            hatalar.append(f"id'siz madde: {m}")
            continue
        if mid in gorulen:
            hatalar.append(f"{mid}: map'te iki kez")
        gorulen[mid] = m
        fazla = set(m) - ALANLAR
        if fazla:
            hatalar.append(f"{mid}: bilinmeyen alan(lar) {sorted(fazla)}")
        if m.get("sinif") not in ("A", "B", "C"):
            hatalar.append(f"{mid}: sinif A/B/C değil ({m.get('sinif')!r})")
        if m.get("seviye") not in ("blok", "uyari", "bilgi"):
            hatalar.append(f"{mid}: seviye blok/uyari/bilgi değil ({m.get('seviye')!r})")
        if not m.get("uygulanir"):
            hatalar.append(f"{mid}: uygulanir boş")
        k = m.get("kontrol")
        if k and k not in KONTROLLER:
            hatalar.append(f"{mid}: kontrol `{k}` programda yok")
        if m.get("sinif") == "A" and not k and not m.get("not"):
            hatalar.append(f"{mid}: A sınıfı, kontrol yok ve gerekçe (`not`) yok")
        if m.get("sinif") == "C" and k and not k.startswith("ip_"):
            hatalar.append(f"{mid}: C sınıfında kontrol yalnız ipucu (`ip_` önekli) olabilir: {k}")
        if m.get("seviye") == "blok" and mid != "BE-10b":
            hatalar.append(f"{mid}: `seviye: blok` yalnız BE-10b'ye verilmiştir (ADR 0019 — kullanıcı onaylı tek kapı)")
        if mid not in tum_ck and not m.get("ayrildi"):
            hatalar.append(f"{mid}: checklist'te tanımlı değil (ve `ayrildi: true` değil)")
        if mid in tum_ck and m.get("ayrildi"):
            notlar.append(f"{mid}: checklist'te artık tanımlı — `ayrildi: true` kaldırılabilir")
    for onek, ids in ck.items():
        for i in sorted(ids - set(gorulen)):
            hatalar.append(f"{i}: {CHECKLISTLER[onek].name}'de var, map'te YOK")
    kullanilan = {m.get("kontrol") for m in harita}
    for k in sorted(set(KONTROLLER) - kullanilan):
        hatalar.append(f"kontrol `{k}` programda var ama hiçbir maddeye bağlı değil")
    print("checklist_check --harita-denetim")
    print(f"  KAPSAM: map {len(harita)} madde · checklist kimlik " +
          " · ".join(f"{k} {len(v)}" for k, v in ck.items()) + f" · programdaki kontrol {len(KONTROLLER)}")
    dag = {}
    for m in harita:
        dag.setdefault((m["id"].split("-")[0], m.get("sinif")), 0)
        dag[(m["id"].split("-")[0], m.get("sinif"))] += 1
    print("  Sınıf dağılımı: " + " · ".join(f"{o}/{s}={n}" for (o, s), n in sorted(dag.items())))
    for n in notlar:
        print(f"  NOT: {n}")
    for h in hatalar:
        print(f"  [FAIL] {h}")
    if not hatalar:
        print("  [OK] map ↔ checklist ↔ kontrol tutarlı")
    return 1 if hatalar else 0


class ProgramKosmadi(Exception):
    """Programın koşamadığı (girdi/ortam) durum → exit 2; eksiklik/FAIL ile karışmaz."""


def main(argv=None) -> int:
    try:
        return _main(argv)
    except ProgramKosmadi as e:
        print(f"[PROGRAM KOŞMADI] {e}")
        return 2
    except Exception as e:                       # beklenmeyen her istisna: exit 2, 1 DEĞİL
        print(f"[PROGRAM KOŞMADI] {type(e).__name__}: {e}")
        return 2


def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Ortak checklist kontrol programı (BE/FE/DOC)",
        epilog=HUKUM_SATIRI + ". Exit: 0 = engelleyici FAIL yok · 1 = blok FAIL ya da --verify-report "
               "eksikliği (satır yok/hükümsüz/kanıtsız/ELLE/ÇELİŞKİ) · 2 = kullanım hatası ya da program koşmadı.")
    ap.add_argument("--repo", help="incelenen reponun mutlak yolu (proje kökü)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--diff", help="git aralığı (ör. origin/main...HEAD, HEAD~1..HEAD, HEAD)")
    g.add_argument("--files", nargs="+", help="dosya listesi (mutlak ya da --repo'ya göreli)")
    ap.add_argument("--kind", default="auto", choices=list(KIND_ONEK))
    ap.add_argument("--ids", help="yalnız bu madde kimlikleri (virgüllü), ör. BE-10b")
    ap.add_argument("--verify-report", help="bug-expert raporunun kapsama tablosunu doğrula")
    ap.add_argument("--sap", action="store_true", help="B sınıfı (SAP sorgulu) kontrolleri aç")
    ap.add_argument("--ana-sinif", action="store_true",
                    help="girdi dosyaları sınıf ANA kaynağıdır (adı .clas.abap olmasa da; include'lar hariç) — run_review class_push")
    ap.add_argument("--sap-kok", help=".conn_adt'nin bulunduğu dizin (varsayılan --repo)")
    ap.add_argument("--reach", action="store_true", help="yazan_kanali ulaşım testi")
    ap.add_argument("--harita-denetim", action="store_true", help="map ↔ checklist ↔ kontrol bütünlüğü")
    ap.add_argument("--harita", help=argparse.SUPPRESS)          # test: alternatif map yolu
    ap.add_argument("--strict", action="store_true", help=argparse.SUPPRESS)  # run_all uyumu (no-op)
    ap.add_argument("--quick", action="store_true", help=argparse.SUPPRESS)   # run_all uyumu (no-op)
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    harita_yolu = Path(args.harita) if args.harita else MAP_YOLU
    if args.harita_denetim:
        return harita_denetim(harita_yolu)
    if args.reach:
        return reach(harita_oku(harita_yolu))
    if not args.repo or not (args.diff or args.files):
        print("KULLANIM HATASI: --repo + (--diff | --files) gerekli (ya da --reach / --harita-denetim)", file=sys.stderr)
        return 2
    if not Path(args.repo).is_dir():
        print(f"KULLANIM HATASI: --repo dizin değil: {args.repo}", file=sys.stderr)
        return 2
    try:
        return calistir(args)
    except RuntimeError as e:
        print(f"KULLANIM HATASI: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
