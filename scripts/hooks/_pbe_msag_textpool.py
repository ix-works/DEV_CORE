#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PULL-BEFORE-EDIT eklentisi (Q352-C, ADR 0016): mesaj sınıfı CSV'leri + program textpool'u.

Kapı (`hooks/pull_before_edit.py`) çekirdek sınıflandırmanın TANIMADIĞI bir dosyayı
`_EK_DENETCILER` sırasıyla eklentilere sorar. Bu modül tek fonksiyon sunar:

    sinifla(path: Path, root: Path) -> Optional[dict]
        None → bu dosya benim değil
        dict → {"nesne": <MSAG / PROGRAM adı>, "tip": "msag"|"textpool",
                "komut": <YALNIZ çalıştırılabilir pull komutu>, "not": <açıklama + kaçışlar>}

SÖZLEŞME (Q352, 2026-09-26): `komut` SAF komuttur — kapı onun SONUNA `--session <hook
session_id>` ekler (iki oturum aynı projede açıkken marker YANLIŞ seansı gösterir → damga
öteki seansa gider → kapı bloklamaya devam eder). Bu yüzden ① `komut` `--session` BASMAZ
(çift olmasın) ② açıklama / kaçış / yer tutucu nedeni `komut`un ARKASINA yazılmaz (kapının
eklediği `--session` metnin ortasına düşer, komut kopyalanamaz) → hepsi `not` alanında.

Tazelik kontrolünü KAPI yapar (damga anahtarı = dosya yolu, `source_drift.tazelik_anahtari`);
damgayı `scripts/pull_msag_textpool.py` yazar. Bu modül SAP'ye gitmez, yalnız yola bakar.

NEDEN: bu dosyalar SAP'ye TAM PUT ile yüklenir (`populate_message_class.py`,
`push_textpool.py`) ⇒ başka makinede canlıda değişmiş metin, eski yerel dosyayla yapılan
yüklemede SESSİZCE ezilir.

KAPSAM (yalnız `<source_root>/…` altında; muaf klasörler çekirdekle AYNI):
  · mesaj sınıfı : `messages.csv` · `messages-<ek>.csv`
      nesne = `<ek>` BÜYÜK harf (Z/Y ile başlıyorsa; örn `messages-zsd000.csv` → ZSD000).
      `messages-all.csv` / `messages.csv` → ad dosyadan ÇIKMAZ ⇒ yer tutucu `<MSAG_ADI>`
      (tahmin YOK; `.rules.md` adlandırma tablosu bir kuraldır, kanıt değildir).
  · textpool     : `…/textpool/<PROG>.{selections,symbols,headings}.txt` → nesne = PROG
                   `…/textpool/{selections,symbols,headings}.txt` (çıplak ad) → üst
                   `programs/` dizininde TEK `*.prog.abap` varsa o; yoksa/birden çoksa yer
                   tutucu `<PROGRAM_ADI>`. Yer tutucu düzenlemeyi kalıcı kilitlemez: pull
                   `--program <AD>` ile koşunca DOSYA damgalanır (anahtar yol, ad değil).
KAPSAM DIŞI (None döner): `*.textpool.txt` (tek dosyalı eski biçim — PUT gövdesi değil,
  yorum satırları taşır) · `*.README.md` · `ref_docs/` altındaki `messages.csv` (muaf klasör).

Kapı asla çökmemeli: bu modülde yalnız standart kütüphane; beklenmeyen hata kapıda
"tanınmadı" sayılır (çekirdek politikası).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

# Çekirdek sınıflandırmayla AYNI muaf klasör kümesi (source_drift._EXCLUDED_DIR_SEGMENTS).
_MUAF_KLASORLER = {"ref_docs", "docs", ".tmp", "legacy", "_archive", "archive", "drafts"}

_MSAG_RE = re.compile(r"^messages(?:-(?P<ek>[^.\\/]+))?\.csv$", re.IGNORECASE)
_TP_ALTLAR = ("selections", "symbols", "headings")
_TP_ADLI_RE = re.compile(r"^(?P<prog>[^.]+)\.(?P<alt>selections|symbols|headings)\.txt$",
                         re.IGNORECASE)
_TP_CIPLAK_RE = re.compile(r"^(?P<alt>selections|symbols|headings)\.txt$", re.IGNORECASE)
_SAP_AD_RE = re.compile(r"^[ZY][A-Z0-9_/]*$")

MSAG_YER_TUTUCU = "<MSAG_ADI>"
PROG_YER_TUTUCU = "<PROGRAM_ADI>"
_PULL = "python core/scripts/pull_msag_textpool.py"
# Kapının blok mesajı eklentide `--offline`ı SÖYLEMEZ → kaçış `not` alanında taşınır
# (komutun ARKASINDA değil: kapı komutun sonuna `--session` ekler).
_KACIS = ("SAP erişilemiyorsa: aynı komuta --offline ekle — ÇEKMEDEN damgalar, canlıdaki "
          "değişikliği ezme riskini bilerek kabul edersin. Önce bakmak için: --dry-run.")


def _kok_segmentleri() -> set:
    """`project.yaml:source_root` + geçiş-eski `erp` (çekirdek kapıyla aynı kural)."""
    seg = "source_codes"
    try:
        scripts = str(Path(__file__).resolve().parents[1])
        if scripts not in sys.path:
            sys.path.append(scripts)
        from utils.project_config import source_root_name  # type: ignore
        seg = (source_root_name() or "SOURCE_CODES").lower()
    except Exception:
        pass
    return {seg, "erp"}


def _kapsamda(p: Path) -> bool:
    parts = {s.lower() for s in p.parts}
    if not (_kok_segmentleri() & parts):
        return False
    return not (_MUAF_KLASORLER & parts)


def _tek_program(programs_dizini: Path) -> Optional[str]:
    """`programs/` altında TEK `*.prog.abap` varsa adı; yoksa/birden çoksa None."""
    try:
        adaylar = sorted(f.name for f in programs_dizini.iterdir()
                         if f.is_file() and f.name.lower().endswith(".prog.abap"))
    except Exception:
        return None
    if len(adaylar) != 1:
        return None
    ad = adaylar[0][: -len(".prog.abap")].upper()
    return ad if _SAP_AD_RE.match(ad) else None


def sinifla(path, root=None) -> Optional[dict]:
    p = Path(path)
    ad = p.name
    m = _MSAG_RE.match(ad)
    tp_adli = _TP_ADLI_RE.match(ad)
    tp_ciplak = _TP_CIPLAK_RE.match(ad)
    if not (m or tp_adli or tp_ciplak):
        return None
    if not _kapsamda(p):
        return None

    if m:
        ek = (m.group("ek") or "").upper()
        nesne = ek if (ek and ek != "ALL" and _SAP_AD_RE.match(ek)) else MSAG_YER_TUTUCU
        neden = "" if nesne != MSAG_YER_TUTUCU else (
            "Mesaj sınıfı adı dosya adından çıkmıyor — <MSAG_ADI> yerine sınıf adını yaz. ")
        return {"nesne": nesne, "tip": "msag",
                "komut": f'{_PULL} msag --name {nesne} --file "{p}"',
                "not": neden + _KACIS}

    if p.parent.name.lower() != "textpool":
        return None
    if tp_adli:
        prog = tp_adli.group("prog").upper()
        if not _SAP_AD_RE.match(prog):
            return None
    else:
        prog = _tek_program(p.parent.parent) or PROG_YER_TUTUCU
    neden = "" if prog != PROG_YER_TUTUCU else (
        "Program adı dosyadan çıkmıyor ve üst `programs/` dizininde tek program yok — "
        "<PROGRAM_ADI> yerine programı yaz; pull o DOSYAYI damgalar. ")
    return {"nesne": prog, "tip": "textpool",
            "komut": f'{_PULL} textpool --program {prog} --file "{p}"',
            "not": neden + _KACIS}
