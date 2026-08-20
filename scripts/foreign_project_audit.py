#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yabancı-proje güvenlik ön-taraması (F1/F3 firewall — D30, iki modlu).

NEDEN: Claude Code bir klasörde açıldığında oradaki hook'lar/MCP server'lar/CLAUDE.md
ONAYSIZ etki eder (hook = keyfi komut çalıştırma). Tanımadığın bir projeyi Claude ile
açmadan ÖNCE davranış-yüzeyini görmek zorundasın.

MOD 0 (varsayılan — Claude'suz, düz python; ÖNCE BU):
    python foreign_project_audit.py C:\\yol\\yabanci-proje
  Dosya-VARLIK envanteri + risk sınıflaması. İçerik çalıştırmaz, import etmez.

MOD 1 (--deep — yine Claude'suz; komut/içerik özeti):
    python foreign_project_audit.py C:\\yol\\yabanci-proje --deep
  Hook komutlarını, MCP server komutlarını, CLAUDE.md import satırlarını LİSTELER
  (yalnız okur). Derin insan-incelemesi için ham madde. Temiz çıkarsa proje
  guest_mode.py ile misafir-modda açılabilir (bkz. scripts/guest_mode.py).

Çıkış kodu: 0 = yüzey boş/temiz · 1 = YÜKSEK-risk yüzey var (incele!) · 2 = kullanım hatası.
"""
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# (göreli-yol, risk, neden) — VARLIĞI bile rapor edilir
YUZEY = [
    (".claude/settings.json",       "YÜKSEK", "hook'lar ONAYSIZ çalışır (keyfi komut)"),
    (".claude/settings.local.json", "YÜKSEK", "lokal hook/permission override"),
    (".mcp.json",                   "YÜKSEK", "MCP server = oturumda çalışan süreç"),
    (".claude/hooks",               "YÜKSEK", "hook script klasörü"),
    ("CLAUDE.md",                   "ORTA",   "talimat enjeksiyonu (import zinciri dahil)"),
    ("CLAUDE.local.md",             "ORTA",   "lokal talimat dosyası"),
    (".claude/agents",              "ORTA",   "alt-ajan tanımları (araç yetkileri)"),
    (".claude/commands",            "ORTA",   "slash-komut tanımları"),
    (".claude/skills",              "ORTA",   "skill talimatları"),
    (".claude/plugins",             "ORTA",   "plugin konfigürasyonu"),
    (".claude/memory-seed",         "DÜŞÜK",  "memory tohumları (talimat etkisi dolaylı)"),
]

# ⛔ 2026-08-20 (K3): JSON'u REGEX ile okumak bu araçta bir GÜVENLİK körlüğüydü.
# `"command": "python -c \"import os; os.system(...)\""` gibi KAÇIŞLI bir değerde
# `[^"]+` ilk `\"`de durur → raporda komut **KESİK** görünür ve tam da tehlikeli
# kısmı gizlenir. Bu araç "bu klasörde Claude açayım mı" kararını besliyor;
# eksik gösterilen komut = yanlış onay. ⇒ Ayıklama artık gerçek JSON parse'ıyla.
#
# Regex'ler SİLİNMEDİ: JSON bozuksa (yorum satırlı/kırık dosya) sessizce
# "komut yok" demek fail-open olurdu → regex GERİ-DÖNÜŞÜ + GÖRÜNÜR uyarı.
_HOOK_CMD = re.compile(r'"command"\s*:\s*"([^"]+)"')
_MCP_CMD = re.compile(r'"(command|args|url)"\s*:\s*(\[[^\]]*\]|"[^"]*")')
_IMPORT = re.compile(r"^\s*@\S+", re.M)


def _gez(dugum, anahtarlar: tuple[str, ...]):
    """JSON ağacındaki `anahtarlar` değerlerini (anahtar, değer) olarak topla.

    Derinlik sınırı YOK: hook'lar `hooks.PreToolUse[i].hooks[j].command` gibi
    iç içe yaşar; sabit bir yol varsayımı yeni şemada sessizce 0 bulgu verir.
    """
    if isinstance(dugum, dict):
        for k, v in dugum.items():
            if k in anahtarlar:
                yield k, v
            yield from _gez(v, anahtarlar)
    elif isinstance(dugum, list):
        for x in dugum:
            yield from _gez(x, anahtarlar)


def _degeri_yaz(v) -> str:
    """Değeri TEK satırlık, kaçışları ÇÖZÜLMÜŞ hâlde göster (kesme YOK)."""
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def _satirlar(etiket: str, v):
    """(etiket, gosterilecek-metin) ciftleri — liste OGE OGE, kacislar COZULMUS.

    `args` gibi listeleri tek satira `json.dumps` ile gommek kacislari YENIDEN
    kacislar; rapor yine gercek komutu gostermez (kusurun kilik degistirmis hali).
    """
    if isinstance(v, list):
        for i, x in enumerate(v):
            yield f"{etiket}[{i}]", _degeri_yaz(x)
    else:
        yield etiket, _degeri_yaz(v)


def json_komutlari(icerik: str, anahtarlar: tuple[str, ...]):
    """(bulgular, uyari) — uyari None DEĞİLSE rapor EKSİK/KESİK olabilir.

    Sözleşme: çağıran uyarıyı BASMAK ZORUNDA. Sessizce yutmak, bu aracın
    tek işini (davranış-yüzeyini eksiksiz göstermek) sessizce iptal eder.
    """
    try:
        veri = json.loads(icerik)
    except ValueError as e:            # JSONDecodeError dahil
        ham = [("command", m.group(1)) for m in _HOOK_CMD.finditer(icerik)]
        return ham, (f"JSON parse EDİLEMEDİ ({type(e).__name__}: {e}) → regex geri-dönüşü. "
                     "KAÇIŞLI komutlar KESİK görünebilir; dosyayı ELLE aç.")
    return list(_gez(veri, anahtarlar)), None


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    deep = "--deep" in sys.argv
    if len(args) != 1:
        print(__doc__)
        return 2
    kok = Path(args[0])
    if not kok.is_dir():
        print(f"HATA: klasör yok: {kok}")
        return 2

    print(f"═══ YABANCI-PROJE ÖN-TARAMA (mod {'1/deep' if deep else '0'}): {kok} ═══")
    yuksek = 0
    bulgu = 0
    for rel, risk, neden in YUZEY:
        p = kok / rel
        if not p.exists():
            continue
        bulgu += 1
        if risk == "YÜKSEK":
            yuksek += 1
        n = sum(1 for _ in p.rglob("*") if _.is_file()) if p.is_dir() else 1
        print(f"  [{risk:6}] {rel}  ({n} dosya) — {neden}")
        if not deep:
            continue
        try:
            if p.is_file() and p.suffix == ".json" or p.name.endswith(".json"):
                icerik = p.read_text(encoding="utf-8", errors="replace")
                if p.name == ".mcp.json":
                    bulgular, uyari = json_komutlari(icerik, ("command", "args", "url"))
                    for k, v in bulgular:
                        for etiket, deger in _satirlar(k, v):
                            print(f"           mcp {etiket}: {deger}")
                else:
                    bulgular, uyari = json_komutlari(icerik, ("command",))
                    for _k, v in bulgular:
                        for etiket, deger in _satirlar("komut", v):
                            print(f"           {etiket}: {deger}")
                if uyari:
                    print(f"           ⚠ EKSİK-RAPOR RİSKİ: {uyari}")
            elif p.is_file() and p.suffix == ".md":
                for m in _IMPORT.finditer(p.read_text(encoding="utf-8", errors="replace")):
                    print(f"           import: {m.group(0).strip()}")
            elif p.is_dir():
                for f in sorted(p.rglob("*")):
                    if f.is_file():
                        print(f"           - {f.relative_to(kok)}")
        except Exception as e:
            print(f"           (okunamadı: {e})")

    if bulgu == 0:
        print("  Davranış-yüzeyi dosyası YOK — Claude etkileyecek bir şey bulunamadı.")
    print("═══ SONUÇ:", "⛔ YÜKSEK-risk yüzey VAR — içerikleri incele; onaylamadan bu "
          "klasörde Claude AÇMA (veya guest_mode + hooks'suz aç)" if yuksek
          else "✓ yüksek-risk yüzey yok (ORTA/DÜŞÜK varsa yine göz at)", "═══")
    return 1 if yuksek else 0


if __name__ == "__main__":
    raise SystemExit(main())
