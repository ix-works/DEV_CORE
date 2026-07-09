#!/usr/bin/env python3
"""check_docu_itf_line_width.py — DOCU/F1 runner class'larında ITF `iv_line`
satırlarının F1/SE61 görüntüleme genişliğini (72 ham karakter) aşmasını yakalar.

NEDEN (CANLI-TEYİTLİ 2026-06-30, ZSD001 F1 pilotu): SAPscript/SE61 yardım penceresi
klasik 72-char genişlikte. Bir ITF `iv_line` 72 ham karakteri (tag `<ZH>`/`<DS:>`
DAHİL) aşarsa F1'de **kuyruğu KIRPILIR** (wrap değil, kayıp): örn
  'tanımlanmamış olabilir; lütfen <ZH>... yetkilinize başvurun.</>'  (81 char)
F1'de '... yetkilinize baş' olarak görünür → 'vurun.</>' KAYBOLUR.
DOKTL-TDLINE depolama limiti (132) bunu YAKALAMAZ — depolama ≤132, görüntüleme ≤72.
Bu yüzden 'TDLINE ≤132 OK' diyen check'ler kaçırdı (max 85'ti). std/08 §3.

KURAL: DOCU runner (zsd000_cl_docu / write_object_doc kullanan classrun) içindeki
her `iv_line = '...'` literal'i, apostrof-doubling normalize edildikten sonra
(tag karakterleri dahil) ≤ 72 olmalı. Aşan = kırpılır.

Kullanım:
    python check_docu_itf_line_width.py [path] [--strict]
    (path verilmezse <source_root>/ altındaki tüm DOCU runner *.clas.abap taranır)
Çıkış: 0 temiz, 1 ihlal.
"""
# ENFORCES: DOC-F1-01  (ADR 0019 coverage binding)
import argparse
import io
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import SOURCE_ROOT_NAME, project_root  # K12: kaynak-klasor adi config'ten

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MAX_LEN = 72  # F1/SE61 görüntüleme genişliği (std/08 §3; güvenli hedef ≤70)

# DOCU runner imzası: generic yazıcı veya yazma metodu referansı
_IS_DOCU_RUNNER = re.compile(r"zsd000_cl_docu|write_object_doc", re.IGNORECASE)
# iv_line = '....'  (ABAP string literal; içerde '' = kaçışlı tek tırnak)
_IV_LINE = re.compile(r"iv_line\s*=\s*'((?:[^']|'')*)'", re.IGNORECASE)


_TAG_OPEN = re.compile(r"<ZH>|<DS:", re.IGNORECASE)
_TAG_CLOSE = re.compile(r"</>")


def scan_text(text):
    """İki tür ihlal döner:
    - ('WIDTH', line_no, length, rendered): iv_line >72 ham char
    - ('SPAN', line_no, opens, closes, rendered): `<ZH>`/`<DS:>` tag tek satırda
      açılıp kapanmıyor (per-satır open≠close) → std/08 §6 'tag'i 2 satıra BÖLME'.
      F1/SE61 char-format `/` satır sınırında resetlenebilir → bold/link render
      bozulur (CANLI 2026-06-30 ZSD001/009 gate)."""
    hits = []
    for i, raw in enumerate(text.splitlines(), 1):
        m = _IV_LINE.search(raw)
        if not m:
            continue
        rendered = m.group(1).replace("''", "'")  # F1'de görünen ham değer (tag dahil)
        if len(rendered) > MAX_LEN:
            hits.append(('WIDTH', i, len(rendered), rendered))
        o = len(_TAG_OPEN.findall(rendered))
        c = len(_TAG_CLOSE.findall(rendered))
        if o != c:
            hits.append(('SPAN', i, o, c, rendered))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="taranacak dosya (run_review pozisyonel artifact)")
    ap.add_argument("--file")
    ap.add_argument("--strict", action="store_true")
    args, _unknown = ap.parse_known_args()  # run_review ek flag geçebilir → yut

    # ADR 0020: junction'da __file__ DEV_CORE'a çözülür → kanonik project_root()
    root = project_root()
    target = args.file or args.path
    if target:
        files = [Path(target)]
    else:
        files = list((root / SOURCE_ROOT_NAME).rglob("*.clas.abap"))

    total = 0
    scanned = 0
    for f in files:
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if not _IS_DOCU_RUNNER.search(txt):
            continue  # DOCU runner değil → bu check'in konusu değil
        scanned += 1
        for hit in scan_text(txt):
            total += 1
            rel = f.relative_to(root) if str(f).startswith(str(root)) else f
            if hit[0] == 'WIDTH':
                _, ln, length, content = hit
                print(f"[İHLAL-WIDTH] {rel}:{ln}  iv_line {length}>72 ham char → F1'de kuyruk "
                      f"KIRPILIR; kelime sınırında ≤70 böl (std/08 §3): {content}")
            else:  # SPAN
                _, ln, o, c, content = hit
                print(f"[İHLAL-SPAN] {rel}:{ln}  tag açılış={o}≠kapanış={c} → `<ZH>`/`<DS:>` "
                      f"2 satıra bölünmüş; bold/link tek satırda aç-kapa (std/08 §6): {content}")

    if total:
        print(f"\n{total} ihlal — DOCU runner ITF: iv_line >72 (F1 kuyruk kırpar, std/08 §3) "
              f"VEYA tag-span (`<ZH>`/`<DS:>` 2 satıra bölünmüş, F1 char-format resetlenir, "
              f"std/08 §6). Düzelt: satır ≤70 + tag tek satırda kapansın.")
        return 1
    if scanned:
        print(f"[OK] DOCU runner ITF satır genişliği ≤72 ({scanned} runner tarandı).")
    else:
        print("[OK] DOCU runner yok (bu artifact ITF/F1 konusu değil).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
