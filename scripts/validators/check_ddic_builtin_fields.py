#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ENFORCES: C-STR-FIELD-01, C-TBL-CRE-01  (ADR 0019 coverage binding)
# GATE-SEVERITY: advisory  (run_review zincirinde WARNING; rc 1 = bulgu sinyali, hiçbir zinciri bloklamaz)
"""check_ddic_builtin_fields.py — DDIC tablo/yapı kaynağında DTEL'siz (yerleşik `abap.*` tipli)
alanları LİSTELER.

NEDEN VAR (DEV_CORE Issue #406, kullanıcı onayı 2026-11-08 — ADR 0019 beş şartı)
  `run_review --task table_creation|struct_creation` yerleşik tipli alana bakan hiçbir denetim
  koşturmuyordu: `key id : abap.numc(3)` + `cnt : abap.int4` + `note : abap.char(100)` taşıyan
  bir tablo `VERDICT: PASS` alıyordu. `check_struct_field_dtel_active` ise Z DTEL bulamayınca
  `measured=true reason=kapsam-disi-z-dtel-yok` diyordu, yani DTEL'siz alan onun kapsamında
  değildi ama çıktısı "ölçtüm" diye okunuyordu. Kural (`claude/rules/sap-source-protokolu.md`
  "Yeni DDIC tablo" · checklist BE-13): tablo yaratılmadan önce her alanın DTEL'i kullanıcıya
  gösterilir ve onay alınır; mümkün olan her alanda mevcut DTEL kullanılır.

ŞİDDET — LİSTELER, ENGELLEMEZ
  Tüketici korpusunda (49 tablo/yapı DDL'i) 125 DTEL'siz alan var; çoğu BAPI tarzı `_X`
  değişiklik bayrağı yapısıdır ve meşrudur. Bu yüzden kapı yalnız YARATIM zincirlerinde koşar
  (`run_review` table_creation + struct_creation, şiddet WARNING) ve `run_all_validators`'a
  bağlanmaz. Bloklamak bu dosyanın işi değildir (BE-13 onay kaydı yargıdır, adt-gateway tanımı).

BİLİNÇLİ KARAR İŞARETİ
  Alan-adı satırında, alan deyiminin devam satırlarında ya da alan-adı satırının hemen
  üstündeki kesintisiz yorum/annotation satırlarında `// dtel-istisna: <gerekçe>` ⇒ alan
  "istisna (gerekçeli)" sayılır, uyarı vermez ama listelenir. Gerekçesiz işaret
  (`// dtel-istisna:` boş) uyarı olarak KALIR. Yalnız `//` satır yorumu tanınır.

ÇIKIŞ SÖZLEŞMESİ
  1 — istisnasız (ya da gerekçesiz işaretli) en az bir DTEL'siz alan var (run_review: WARNING)
  0 + `IX-GATE-STATUS measured=true`  — baktığı yüzeyde DTEL'siz alan yok ya da hepsi
      gerekçeli istisna
  0 + `IX-GATE-STATUS measured=false` — ölçülemeyen yüzey var (çözülemeyen deyim · klasik
      `.tabl.xml` · append `extend type` · tablo/yapı tanımı bulunamadı). Bu TEMİZ DEĞİLDİR:
      run_review bunu SKIP sayar ve kendi şiddetiyle (WARNING) verdict'e katar.
  2 — kullanım hatası / dosya yok

KULLANIM
  python scripts/validators/check_ddic_builtin_fields.py <dosya|dizin> [...]
"""
from __future__ import annotations

import argparse
import bisect
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _gate_status import gate_status  # noqa: E402
from utils.ad_politikasi import AD_ADAYI, ad_coz  # noqa: E402

_GATE = Path(__file__).stem

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Dizin verildiğinde taranan uzantılar (dosya verildiğinde uzantıya bakılmaz)
DDL_UZANTILARI = (".tabl.ddl", ".asddls", ".ddls", ".ddl")
XML_UZANTISI = ".tabl.xml"

_BASLIK_RE = re.compile(r"^[ \t]*define[ \t]+(table|structure)[ \t\r\n]+(?!function\b)(" + AD_ADAYI + r")",
                        re.IGNORECASE | re.MULTILINE)
_TABLO_FONK_RE = re.compile(r"^[ \t]*define[ \t]+table[ \t]+function\b", re.IGNORECASE | re.MULTILINE)
_APPEND_RE = re.compile(r"^[ \t]*extend[ \t]+type\b", re.IGNORECASE | re.MULTILINE)
# `\A` YOK: `.match(metin, konum)` konumda çapalar; `\A` ise yalnız dizenin gerçek başında tutar
# (ikinci annotation hiç soyulmaz, alan "ayrıştırılamayan annotation" olurdu).
_ANNOT_RE = re.compile(
    r"\s*@[A-Za-z0-9_.]+\s*:\s*(?:'[^']*'|#[A-Za-z0-9_]+|true\b|false\b|-?[0-9]+(?:\.[0-9]+)?"
    r"|\{[^{}]*\}|\[[^\[\]]*\])", re.IGNORECASE)
_DAHIL_RE = re.compile(r"\A\s*(?:(" + AD_ADAYI + r")\s*:\s*)?include\s+(" + AD_ADAYI + r")"
                       r"(?:\s+with\s+suffix\s+(" + AD_ADAYI + r"))?\s*\Z", re.IGNORECASE)
_ALAN_RE = re.compile(r"\A\s*(?:key\s+)?(" + AD_ADAYI + r")\s*:\s*(\S.*)\Z", re.IGNORECASE | re.DOTALL)
_YERLESIK_RE = re.compile(r"\A(?:reference\s+to\s+)?(abap\.[A-Za-z0-9_]+)(\s*\([^)]*\))?",
                          re.IGNORECASE)
_TIP_ADI_RE = re.compile(r"\A(?:reference\s+to\s+)?(" + AD_ADAYI + r")", re.IGNORECASE)
_ISARET_RE = re.compile(r"\A//\s*dtel-istisna\s*:(.*)\Z", re.IGNORECASE | re.DOTALL)


def maskele(metin: str) -> tuple[str, dict[int, list[str]]]:
    """Yorumları boşluğa, dize içeriğini boşluğa çevirir (tırnaklar kalır; konum + satır korunur).

    Dönüş: (maskeli metin, {satır_no(0-tabanlı): [o satırdaki `//` yorum metinleri]}).
    """
    out = []
    yorumlar: dict[int, list[str]] = {}
    i, n, satir = 0, len(metin), 0
    while i < n:
        c = metin[i]
        if c == "\n":
            out.append(c)
            satir += 1
            i += 1
        elif c == "'":
            out.append("'")
            i += 1
            while i < n:
                if metin[i] == "'" and i + 1 < n and metin[i + 1] == "'":
                    out.append("  ")
                    i += 2
                elif metin[i] == "'":
                    out.append("'")
                    i += 1
                    break
                elif metin[i] == "\n":       # kapanmamış dize satırı aşmaz
                    break
                else:
                    out.append(" ")
                    i += 1
        elif metin.startswith("//", i):
            j = metin.find("\n", i)
            j = n if j < 0 else j
            yorumlar.setdefault(satir, []).append(metin[i:j].rstrip("\r"))
            out.append(" " * (j - i))
            i = j
        elif metin.startswith("/*", i):
            j = metin.find("*/", i + 2)
            j = n if j < 0 else j + 2
            parca = metin[i:j]
            out.append("".join("\n" if ch == "\n" else " " for ch in parca))
            satir += parca.count("\n")
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out), yorumlar


def _isaret_bul(maskeli_satirlar: list[str], yorumlar: dict[int, list[str]],
                ad_satiri: int, son_satir: int) -> str | None:
    """Alanın istisna işareti: gerekçe metni ('' = gerekçesiz) ya da None (işaret yok)."""
    adaylar = list(range(ad_satiri, son_satir + 1))
    k = ad_satiri - 1
    while k >= 0:
        s = maskeli_satirlar[k].strip()
        if (not s and k in yorumlar) or s.startswith("@"):
            adaylar.append(k)
            k -= 1
            continue
        break
    bulunan = None
    for sat in adaylar:
        for y in yorumlar.get(sat, []):
            m = _ISARET_RE.match(y.strip())
            if m:
                gerekce = m.group(1).strip()
                if gerekce:
                    return gerekce
                bulunan = ""
    return bulunan


def _govde_deyimleri(maskeli: str, ac: int) -> tuple[list[tuple[int, int]], bool]:
    """`{` konumundan başlayıp gövdeyi `;` ile (derinlik 1'de) deyimlere böler.

    Dönüş: ([(başlangıç, bitiş)], kapandı_mı). Son `;`'den sonra `}`'e kadar kalan boş
    olmayan parça da deyim sayılır (noktalı virgülsüz son alan çözülemeyen deyim olur).
    """
    derinlik, bas, parcalar = 0, ac + 1, []
    for i in range(ac, len(maskeli)):
        c = maskeli[i]
        if c == "{":
            derinlik += 1
        elif c == "}":
            derinlik -= 1
            if derinlik == 0:
                parcalar.append((bas, i))
                return parcalar, True
        elif c == ";" and derinlik == 1:
            parcalar.append((bas, i))
            bas = i + 1
    return parcalar, False


def dosya_tara(yol: Path, sonuc: dict) -> None:
    """Tek dosyayı tara; bulguları `sonuc`'a ekle."""
    ad = str(yol)
    if ad.lower().endswith(XML_UZANTISI):
        sonuc["olculmedi"].append((ad, 0, "klasik-xml-olculmedi", "klasik *.tabl.xml (DD03P) yolu"))
        return
    try:
        metin = yol.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        sonuc["olculmedi"].append((ad, 0, "dosya-okunamadi", f"{type(exc).__name__}"))
        return
    maskeli, yorumlar = maskele(metin)
    satir_bas = [0] + [i + 1 for i, ch in enumerate(maskeli) if ch == "\n"]

    def satir_no(konum: int) -> int:          # 0-tabanlı
        return bisect.bisect_right(satir_bas, konum) - 1

    basliklar = list(_BASLIK_RE.finditer(maskeli))
    if not basliklar:
        if _APPEND_RE.search(maskeli):
            sonuc["olculmedi"].append((ad, 0, "append-olculmedi", "append yapısı (extend type)"))
        elif sonuc["dizin_kipi"]:
            sonuc["atlanan"] += 1           # dizin kipinde CDS view vb. tablo/yapı dışı dosya
        elif _TABLO_FONK_RE.search(maskeli):
            sonuc["olculmedi"].append((ad, 0, "tablo-yapi-tanimi-yok", "define table function — DDIC tablo değil"))
        else:
            sonuc["olculmedi"].append((ad, 0, "tablo-yapi-tanimi-yok",
                                       "`define table|structure <ad> {` bulunamadı"))
        return
    sonuc["dosya_ddl"] += 1
    maskeli_satirlar = maskeli.split("\n")
    for b in basliklar:
        obje_ham = b.group(2)
        obje = ad_coz(obje_ham)[0] or f"{obje_ham}(ad-cozulemedi)"
        ac = maskeli.find("{", b.end())
        if ac < 0 or maskeli[b.end():ac].strip():
            sonuc["olculmedi"].append((ad, satir_no(b.start()) + 1, "deyim-cozulemedi",
                                       f"{obje}: başlıktan sonra `{{` bulunamadı"))
            continue
        deyimler, kapandi = _govde_deyimleri(maskeli, ac)
        if not kapandi:
            sonuc["olculmedi"].append((ad, satir_no(ac) + 1, "deyim-cozulemedi",
                                       f"{obje}: gövde `}}` ile kapanmıyor"))
        for bas, bit in deyimler:
            govde = maskeli[bas:bit]
            if not govde.strip():
                continue
            # baştaki annotation'ları soy
            kesim = 0
            while True:
                m = _ANNOT_RE.match(govde, kesim)
                if not m:
                    break
                kesim = m.end()
            kalan = govde[kesim:]
            if not kalan.strip():
                sonuc["olculmedi"].append((ad, satir_no(bas + len(govde) - len(govde.lstrip())) + 1,
                                           "deyim-cozulemedi", "annotation'ı izleyen alan yok"))
                continue
            if kalan.lstrip().startswith("@"):
                sonuc["olculmedi"].append((ad, satir_no(bas + kesim + len(kalan) - len(kalan.lstrip())) + 1,
                                           "deyim-cozulemedi",
                                           "ayrıştırılamayan annotation: " + " ".join(kalan.split())[:60]))
                continue
            if _DAHIL_RE.match(kalan):
                sonuc["dahil"] += 1
                continue
            m = _ALAN_RE.match(kalan)
            if not m:
                sonuc["olculmedi"].append((ad, satir_no(bas + kesim + len(kalan) - len(kalan.lstrip())) + 1,
                                           "deyim-cozulemedi", " ".join(kalan.split())[:60]))
                continue
            alan = m.group(1)
            tip_ifade = " ".join(m.group(2).split())
            ad_konum = bas + kesim + m.start(1)
            ad_satiri = satir_no(ad_konum)
            sonuc["alan"] += 1
            y = _YERLESIK_RE.match(tip_ifade)
            if not y:
                if not _TIP_ADI_RE.match(tip_ifade):
                    sonuc["alan"] -= 1
                    sonuc["olculmedi"].append((ad, ad_satiri + 1, "deyim-cozulemedi",
                                               f"{alan}: tip çözülemedi: {tip_ifade[:40]}"))
                else:
                    sonuc["dtelli"] += 1
                continue
            tip = y.group(1).lower() + ("" if not y.group(2) else re.sub(r"\s+", "", y.group(2)))
            isaret = _isaret_bul(maskeli_satirlar, yorumlar, ad_satiri, satir_no(bit))
            kayit = (ad, ad_satiri + 1, alan, tip, obje)
            if isaret:
                sonuc["istisna"].append(kayit + (isaret,))
            elif isaret == "":
                sonuc["gerekcesiz"].append(kayit)
            else:
                sonuc["uyari"].append(kayit)


def girdileri_topla(yollar: list[str]) -> tuple[list[Path], bool, list[str]]:
    dosyalar, eksik, dizin = [], [], False
    for y in yollar:
        p = Path(y)
        if p.is_dir():
            dizin = True
            for q in sorted(p.rglob("*")):
                if not q.is_file() or "node_modules" in q.parts:
                    continue
                low = q.name.lower()
                if low.endswith(XML_UZANTISI) or low.endswith(DDL_UZANTILARI):
                    dosyalar.append(q)
        elif p.is_file():
            dosyalar.append(p)
        else:
            eksik.append(y)
    return dosyalar, dizin, eksik


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DDIC tablo/yapı: DTEL'siz (yerleşik abap.* tipli) alan listesi")
    ap.add_argument("yollar", nargs="+", help="tablo/yapı kaynak dosyası ya da dizin")
    ap.add_argument("--strict", action="store_true",
                    help="(uyumluluk; NO-OP — şiddeti DEĞİŞTİRMEZ)")
    args = ap.parse_args(argv)

    dosyalar, dizin_kipi, eksik = girdileri_topla(args.yollar)
    if eksik:
        print(f"HATA: bulunamadı: {', '.join(eksik)}", file=sys.stderr)
        return 2
    sonuc = {"dizin_kipi": dizin_kipi, "dosya_ddl": 0, "atlanan": 0, "alan": 0, "dtelli": 0,
             "dahil": 0, "uyari": [], "gerekcesiz": [], "istisna": [], "olculmedi": []}
    for d in dosyalar:
        dosya_tara(d, sonuc)

    uyari = sonuc["uyari"] + sonuc["gerekcesiz"]
    for ad, sat, alan, tip, obje in sonuc["uyari"]:
        print(f"[UYARI] DTEL'siz alan · {alan} · {tip} · {obje}  ({ad}:{sat})")
    for ad, sat, alan, tip, obje in sonuc["gerekcesiz"]:
        print(f"[UYARI] DTEL'siz alan · {alan} · {tip} · {obje}  ({ad}:{sat}) — "
              f"`// dtel-istisna:` işareti GEREKÇESİZ, uyarı kalır")
    for ad, sat, alan, tip, obje, gerekce in sonuc["istisna"]:
        print(f"[İSTİSNA] DTEL'siz alan · {alan} · {tip} · {obje}  ({ad}:{sat}) — gerekçe: {gerekce}")
    for ad, sat, neden, ayrinti in sonuc["olculmedi"]:
        yer = f"{ad}:{sat}" if sat else ad
        print(f"[ÖLÇÜLEMEDİ] {yer} · {neden} · {ayrinti}")

    n_dtelsiz = len(uyari) + len(sonuc["istisna"])
    xml = sum(1 for o in sonuc["olculmedi"] if o[2] == "klasik-xml-olculmedi")
    app = sum(1 for o in sonuc["olculmedi"] if o[2] == "append-olculmedi")
    deyim = sum(1 for o in sonuc["olculmedi"] if o[2] == "deyim-cozulemedi")
    print(f"KAPSAM: {len(dosyalar)} dosya (tablo/yapı DDL {sonuc['dosya_ddl']} · klasik .tabl.xml {xml} "
          f"ÖLÇÜLMEDİ · append {app} ÖLÇÜLMEDİ · tablo/yapı dışı atlanan {sonuc['atlanan']}) · "
          f"alan {sonuc['alan']} (DTEL'li {sonuc['dtelli']} · DTEL'siz {n_dtelsiz}: uyarı "
          f"{len(sonuc['uyari'])} · gerekçesiz işaret {len(sonuc['gerekcesiz'])} · istisna-gerekçeli "
          f"{len(sonuc['istisna'])}) · include {sonuc['dahil']} · çözülemeyen deyim {deyim} · "
          f"ölçülemeyen kalem {len(sonuc['olculmedi'])}")
    print("BAKILMAYAN: klasik *.tabl.xml (DD03P) ÖLÇÜLMEDİ · append yapıları (extend type) ÖLÇÜLMEDİ · "
          "canlı DD03L (SAP'deki tablo yerel kaynakla aynı mı) · include edilen yapının alanları "
          "(o yapı kendi review'unda) · DTEL'in varlığı/aktifliği (check_struct_field_dtel_active) · "
          "`/* */` blok yorumundaki işaret")
    print("HÜKÜM OKUMA: rc 1 = istisnasız DTEL'siz alan var (run_review WARNING) · rc 0 + "
          "measured=false = ölçülemeyen yüzey var, TEMİZ DEĞİL (run_review SKIP → WARNING) · rc 0 + "
          "measured=true = baktığı yüzeyde DTEL'siz alan yok ya da hepsi gerekçeli istisna")

    if uyari:
        gate_status(_GATE, "FINDING", True, f"{len(uyari)}-dtelsiz-alan")
        return 1
    if sonuc["olculmedi"]:
        gate_status(_GATE, "SKIPPED", False, sonuc["olculmedi"][0][2])
        return 0
    gate_status(_GATE, "OK", True, "hepsi-istisna-gerekceli" if sonuc["istisna"] else "temiz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
