# -*- coding: utf-8 -*-
"""claude_paths.py — Claude Code'un KULLANICI-PROFİLİNDEKİ dosyalarının TEK adres kaynağı.

Auto-memory / transcript dosyaları repo DIŞINDA yaşar:
    ~/.claude/projects/<proje-slug>/            *.jsonl (transcript)
    ~/.claude/projects/<proje-slug>/memory/     *.md + MEMORY.md

`<proje-slug>` = proje kökünün MUTLAK yolundan türetilen ad. Bu türetme beş ayrı script'te
BAĞIMSIZ olarak yeniden yazılmıştı ve İKİ FARKLI sözleşme oluşmuştu; yanlış olan sessizce
BAŞKA (çoğu zaman var-olmayan) bir dizini gösteriyordu → "memory yok" / boş rapor.

──────────────────────────────────────────────────────────────────────────────────────
ÖLÇÜM (2026-08-01, KAYIT S4 — kontrol grubu; tahmin DEĞİL)
──────────────────────────────────────────────────────────────────────────────────────
Yer gerçeği: Claude Code'un KENDİ yazdığı transcript'ler. Her `*.jsonl` satırında `cwd`
alanı vardır → "dizin adı ↔ gerçek proje yolu" eşlemesi doğrudan okunur. Ölçüm makinesinde
transcript TAŞIYAN (yani CC'nin gerçekten yazdığı) 4 dizin, iki aday sözleşmeye karşı:

    A = re.sub(r"[^A-Za-z0-9]", "-", yol)
    B = yol.replace(":", "-").replace("\\", "-").replace("/", "-")

    yol şekli                          gözlenen dizin adı                  A    B
    C:\\<KOK_ALT_CIZGILI>\\<PROJE1>      C--<KOK-TIRELI>-<PROJE1>            OK   X
    C:\\<KOK_ALT_CIZGILI>\\<PROJE2>      C--<KOK-TIRELI>-<PROJE2>            OK   X
    C:\\<KOK>\\<PROJE3>                  C--<KOK>-<PROJE3>                   OK   OK
    C:\\<PROJE4>                        C--<PROJE4>                         OK   OK
                                                                     toplam 4/4  2/4

**A KAZANIR: Claude Code ALT ÇİZGİYİ de '-' yapar.** B yalnız yolunda alt çizgi/nokta
OLMAYAN projelerde A ile aynı sonucu verir; `C:\\IX\\DEV_CORE` ya da `<KOK>\\template_project`
gibi alt çizgili bir yolda B YANLIŞ dizini gösterir (sessizce boş sonuç).

⚠ KARŞI-KANIT SANILAN VAKA: `~/.claude/projects/` altında alt çizgi TAŞIYAN bir dizin
vardı ve "demek ki CC alt çizgiyi koruyor" diye okunmuştu. O dizinde HİÇ `*.jsonl` YOKTUR
— yani CC onu YAZMAMIŞTIR (içinde yalnız elle/script'le konmuş `memory/` var). Kanıt değeri
sıfırdır: konvansiyonu, konvansiyonu uygulayan aracın ÇIKTISI belirler; aynı klasörde
duran ama başka bir el tarafından yaratılmış dizin değil. Ölçümü yeniden üretmek için:
`tests/fixtures/proje_slug_tek_kaynak/run.py` (vektörler orada donduruldu).

⚠ SINIR: ölçüm bu makinedeki CC sürümüyle yapıldı. CC bir gün alt çizgiyi korumaya
başlarsa DEĞİŞMESİ GEREKEN TEK YER burasıdır (fixture vektörleri de güncellenir).
Sözleşme beş dosyaya dağılmışken bu imkânsızdı — tek-kaynağın asıl kazancı budur.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

__all__ = ["proje_slug", "claude_projects_dir", "transcript_dizini", "auto_memory_dizini"]

_SLUG_RE = re.compile(r"[^A-Za-z0-9]")


def proje_slug(proje_koku: str | os.PathLike) -> str:
    """Proje kökü (mutlak yol) → Claude Code proje-dizini adı.

    `C:\\IX\\DEV_CORE` -> `C--IX-DEV-CORE`   (alt çizgi de '-' olur; yukarıdaki ölçüm)
    """
    return _SLUG_RE.sub("-", str(proje_koku))


def claude_projects_dir() -> Path:
    """`~/.claude/projects` — testlerin yönlendirebilmesi için `CLAUDE_CONFIG_DIR` onurlanır."""
    ozel = os.environ.get("CLAUDE_CONFIG_DIR")
    kok = Path(os.path.expanduser(ozel)) if ozel else Path.home() / ".claude"
    return kok / "projects"


def transcript_dizini(proje_koku: str | os.PathLike) -> Path:
    """`~/.claude/projects/<slug>/` — oturum transcript'lerinin (*.jsonl) dizini."""
    return claude_projects_dir() / proje_slug(proje_koku)


def auto_memory_dizini(proje_koku: str | os.PathLike) -> Path:
    """`~/.claude/projects/<slug>/memory/` — auto-memory dosyalarının dizini."""
    return transcript_dizini(proje_koku) / "memory"
