#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""statusline_token_esikleri — `ctx <N>%` yaninda MUTLAK token sayisi + KENDI esikleri.

Kullanici karari (2026-08-29): <250k yesil · 250_000 <= t <= 300_000 sari (IKI SINIR DA
DAHIL) · >300_000 kirmizi. Yuzde esikleri (yesil<50 · sari 50-74 · kirmizi>=75) DEGISMEDI;
burada REGRESYON olarak olculur.

NIYE AYRI KOSUCU (bad/good proje dizini kalibiyla IFADE EDILEMEZ):
  * olculen sey bir validator ciktisi degil, bir KOD YOLUdur: stdin JSON'undan gelen
    `context_window` sozlugunun ayristirilmasi + esik/renk/bicim karari + segmentin
    build_line'a KABLOLANMASI. "bad/ dizini FAIL versin" seklinde yazilamaz.
  * degismezlerin bir kismi SINIR degeridir (249_999 / 250_000 / 300_000 / 300_001);
    bunlar ancak fonksiyon dogrudan cagrilarak olculur.

⚠ RENK KARSILASTIRMASI SABITLE YAPILIR (`m._C_RED` vb.), ham `\\033[31m` YAZILMAZ:
   renk sabiti degisirse fixture kirilmasin, DAVRANIS olculsun.

MUTASYON: `python run.py --mutasyon` — her degismez icin fix SOKULUR ve hangi vektorlerin
KIRMIZIYA dondugu ISIMLERIYLE basilir (ortusme gorunur olsun diye her mutasyon TUM vektor
kumesine kosulur). Mutasyon GERCEK KAYNAGA YAZILMAZ (kalinti komsu turlari kirletir):
kaynak metni okunur, bellekte degistirilir, izole modul olarak exec edilir.
Kurulum hatasi `KACTI` DEGILDIR -> ucuncu deger `KURULAMADI`.

UC BAGLAM (F3):
  (1) bilinen-BOZUK : fix sokulmus kod (mutasyon dali)
  (2) bilinen-TEMIZ : bugunku kod
  (3) gorev-DISI 3. baglam: ana repodan BAGIMSIZ, gecici dizinde kurulan SENTETIK bir
      proje kokunde (kendi `.conn_adt`'si, git YOK, SOURCE_CODES YOK, mcp_servers YOK)
      uctan-uca `build_line()` — yani segment gercekten satira giriyor mu.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
STATUSLINE = KOK / "scripts" / "statusline.py"

MUTASYON = "--mutasyon" in sys.argv
_kirmizi: list[str] = []
_yesil: list[str] = []


def sonuc(ad: str, tamam: bool, not_=None) -> None:
    (_yesil if tamam else _kirmizi).append(ad)
    if not MUTASYON:
        print(f"  [{'PASS' if tamam else 'FAIL'}] {ad}" + (f" -- {not_!r}" if not_ is not None else ""))


class Kurulamadi(RuntimeError):
    """Mutasyon ENJEKTE EDILEMEDI. `KACTI` ile ayni sey DEGILDIR."""


def modul(mutasyon=None, ad: str = "mut_statusline"):
    """statusline.py'yi BELLEKTE (gerekirse mutasyonlu) exec et. Gercek dosyaya YAZMAZ."""
    src = STATUSLINE.read_text(encoding="utf-8")
    if mutasyon is not None:
        eski, yeni = mutasyon
        if eski not in src:
            raise Kurulamadi(f"capa bulunamadi: {eski[:70]!r}")
        if src.count(eski) != 1:
            raise Kurulamadi(f"capa {src.count(eski)} kez geciyor (tekil degil): {eski[:50]!r}")
        src = src.replace(eski, yeni, 1)
    m = types.ModuleType(ad)
    m.__file__ = str(STATUSLINE)
    sys.modules.pop(ad, None)
    sys.modules[ad] = m
    exec(compile(src, str(STATUSLINE), "exec"), m.__dict__)  # noqa: S102
    return m


def yuk(**cw):
    """`context_window` sozlugu tasiyan sentetik statusline payload'i."""
    return {"context_window": dict(cw)}


# ---------------------------------------------------------------------------
# E — ESIK / RENK (kullanici karari: 250k ve 300k IKISI DE SARI)
# ---------------------------------------------------------------------------
def vek_esik(m) -> None:
    for ad, tok, beklenen in (
        ("E1 249_999 -> YESIL (sari bandinin 1 alti)", 249_999, m._C_GREEN),
        ("E2 250_000 -> SARI (alt sinir DAHIL)", 250_000, m._C_YELLOW),
        ("E3 300_000 -> SARI (ust sinir DAHIL)", 300_000, m._C_YELLOW),
        ("E4 300_001 -> KIRMIZI ('300K uzerine cikinca')", 300_001, m._C_RED),
        # FP capalari: bantlarin ORTASI da dogru olmali (esik kaymasi tek sinirda gizlenmesin)
        ("E5 0 -> YESIL (FP capasi: bos oturum)", 0, m._C_GREEN),
        ("E6 1_000_000 -> KIRMIZI (FP capasi: ust bant)", 1_000_000, m._C_RED),
        ("E7 275_000 -> SARI (FP capasi: bant ortasi)", 275_000, m._C_YELLOW),
    ):
        sonuc(ad, m._tok_renk(tok) == beklenen, m._tok_renk(tok))


# ---------------------------------------------------------------------------
# A — AYRISTIRMA (context_tokens): yokluk 0'a DUSMEZ, gecerli 0 KAYBOLMAZ
# ---------------------------------------------------------------------------
def vek_ayristirma(m) -> None:
    sonuc("A1 alan YOK -> None",
          m.context_tokens(yuk(used_percentage=42)) is None,
          m.context_tokens(yuk(used_percentage=42)))
    sonuc("A2 context_window sozluk DEGIL (str) -> None",
          m.context_tokens({"context_window": "412000"}) is None,
          m.context_tokens({"context_window": "412000"}))
    sonuc("A3 context_window anahtari YOK -> None",
          m.context_tokens({}) is None, m.context_tokens({}))
    sonuc("A4 context_window None -> None",
          m.context_tokens({"context_window": None}) is None,
          m.context_tokens({"context_window": None}))
    sonuc("A5 sayisal OLMAYAN deger -> None",
          m.context_tokens(yuk(total_input_tokens="abc")) is None,
          m.context_tokens(yuk(total_input_tokens="abc")))
    sonuc("A6 gecerli int -> aynen",
          m.context_tokens(yuk(total_input_tokens=412_345)) == 412_345,
          m.context_tokens(yuk(total_input_tokens=412_345)))
    sonuc("A7 sayisal STRING -> int",
          m.context_tokens(yuk(total_input_tokens="412000")) == 412_000,
          m.context_tokens(yuk(total_input_tokens="412000")))
    # ⚠ json.loads VARSAYILAN ayarda `Infinity` ayristirir; int(float('inf')) ValueError
    # DEGIL OverflowError atar. Yakalanmazsa satir tumden fallback'e duserdi.
    sonuc("A8 Infinity (json.loads ayristirir) -> None",
          m.context_tokens(json.loads('{"context_window": {"total_input_tokens": Infinity}}')) is None,
          m.context_tokens(json.loads('{"context_window": {"total_input_tokens": Infinity}}')))
    # FP CAPASI: GERCEK 0 yokluk DEGILDIR -> 0 olarak korunmali ('if not val' yazilirsa duser)
    sonuc("A9 gercek 0 -> 0 (yoklukla ayni sey DEGIL)",
          m.context_tokens(yuk(total_input_tokens=0)) == 0,
          m.context_tokens(yuk(total_input_tokens=0)))


# ---------------------------------------------------------------------------
# B — KISA BICIM: floor (ASLA yukari); gosterilen sayi <= gercek deger
# ---------------------------------------------------------------------------
def vek_bicim(m) -> None:
    for ad, tok, beklenen in (
        ("B1 0 -> '0'", 0, "0"),
        ("B2 999 -> '999'", 999, "999"),
        ("B3 1_000 -> '1k'", 1_000, "1k"),
        ("B4 249_999 -> '249k' (FLOOR; round olsa '250k' = sari-bandi sayisi yesil renkte)",
         249_999, "249k"),
        ("B5 412_345 -> '412k'", 412_345, "412k"),
        ("B6 1_048_576 -> '1.04M' (floor, dar terminal)", 1_048_576, "1.04M"),
    ):
        sonuc(ad, m._tok_bicim(tok) == beklenen, m._tok_bicim(tok))


# ---------------------------------------------------------------------------
# S — SEGMENT: iki AYRI ANSI blogu + imza geriye uyumlu
# ---------------------------------------------------------------------------
def vek_segment(m) -> None:
    seg = m._ctx_segment(42, 250_000)
    sonuc("S1a yuzde blogu KENDI rengiyle basta",
          seg.startswith(f"{m._C_GREEN}ctx 42%{m._C_RESET}"), seg)
    sonuc("S1b token blogu KENDI rengiyle sonda (yuzdenin YANINDA)",
          seg.endswith(f" {m._C_YELLOW}250k{m._C_RESET}"), seg)
    # REGRESYON + GERIYE UYUM: tok yokken bugunku cikti AYNEN korunur
    sonuc("S2 tok=None -> bugunku cikti AYNEN (regresyon)",
          m._ctx_segment(42, None) == f"{m._C_GREEN}ctx 42%{m._C_RESET}",
          m._ctx_segment(42, None))
    sonuc("S3 tek-argumanli eski cagri imzayi KIRMIYOR",
          m._ctx_segment(42) == f"{m._C_GREEN}ctx 42%{m._C_RESET}", m._ctx_segment(42))
    # AYRIT EDICI: iki renk BAGIMSIZ — dusuk yuzde + yuksek token AYNI segmentte
    seg2 = m._ctx_segment(10, 400_000)
    sonuc("S4 yuzde YESIL iken token KIRMIZI olabiliyor (renkler bagimsiz)",
          seg2.startswith(f"{m._C_GREEN}ctx 10%{m._C_RESET}")
          and seg2.endswith(f" {m._C_RED}400k{m._C_RESET}"), seg2)


# ---------------------------------------------------------------------------
# R — REGRESYON: yuzde davranisi DEGISMEDI
# ---------------------------------------------------------------------------
def vek_regresyon(m) -> None:
    sonuc("R1 context_pct degismedi (used_percentage okunuyor)",
          m.context_pct(yuk(used_percentage=42, total_input_tokens=412_345)) == 42,
          m.context_pct(yuk(used_percentage=42, total_input_tokens=412_345)))
    for ad, pct, renk in (
        ("R2a pct 49 -> YESIL", 49, m._C_GREEN),
        ("R2b pct 50 -> SARI", 50, m._C_YELLOW),
        ("R2c pct 74 -> SARI", 74, m._C_YELLOW),
        ("R2d pct 75 -> KIRMIZI", 75, m._C_RED),
    ):
        sonuc(ad, m._ctx_segment(pct).startswith(renk), m._ctx_segment(pct)[:8])


# ---------------------------------------------------------------------------
# U — UCTAN UCA (3. BAGLAM): sentetik proje kokunde build_line
# ---------------------------------------------------------------------------
def sentetik_proje(kok: Path) -> Path:
    """Ana repodan BAGIMSIZ proje sekli: git YOK, kaynak klasoru YOK, mcp_servers YOK."""
    proje = kok / "SENTETIK"
    (proje / ".claude").mkdir(parents=True)
    (proje / ".conn_adt").write_text(
        "ADT_SAP_SYSTEM_NAME=SYNTH\nADT_SAP_TIER=DEV\n"
        "ADT_SAP_URL=https://synth.example.invalid:44300\n", encoding="utf-8")
    # VPN sondasi AGA CIKMASIN: taze cache birak (deterministik + hizli)
    (proje / ".claude" / ".statusline_vpn_cache").write_text(
        json.dumps({"ok": True, "ts": time.time()}), encoding="utf-8")
    return proje


def vek_uctan_uca(m, proje: Path) -> None:
    satir = m.build_line(proje, yuk(used_percentage=42, total_input_tokens=412_345))
    sonuc("U1a satirda yuzde segmenti var", f"{m._C_GREEN}ctx 42%{m._C_RESET}" in satir, satir)
    sonuc("U1b token KABLOLANDI: satirda kirmizi '412k' yuzdenin YANINDA",
          f"{m._C_GREEN}ctx 42%{m._C_RESET} {m._C_RED}412k{m._C_RESET}" in satir, satir)
    # tok alani YOKKEN bugunku satir aynen (pct VAR / tok YOK dali)
    satir2 = m.build_line(proje, yuk(used_percentage=42))
    sonuc("U2 tok alani yok -> satirda YALNIZ yuzde (bugunku davranis)",
          f"{m._C_GREEN}ctx 42%{m._C_RESET}" in satir2 and "412k" not in satir2, satir2)
    # pct YOK / tok VAR -> hicbir ctx segmenti cizilmez (bilincli karar; ikili erken oturumda
    # used_percentage=null iken total_input_tokens'i 0 basiyor -> anlamsiz `0` gorunmesin)
    satir3 = m.build_line(proje, yuk(total_input_tokens=412_345))
    sonuc("U3 pct YOK / tok VAR -> ctx segmenti hic cizilmez",
          "ctx " not in satir3 and "412k" not in satir3, satir3)


def tur(mutasyon=None) -> None:
    m = modul(mutasyon)
    vek_esik(m)
    vek_ayristirma(m)
    vek_bicim(m)
    vek_segment(m)
    vek_regresyon(m)
    with tempfile.TemporaryDirectory() as t:
        vek_uctan_uca(m, sentetik_proje(Path(t)))


# ---------------------------------------------------------------------------
# MUTASYONLAR — her esik ve her None yolu AYRI AYRI oldurulur.
# Her mutasyon TUM vektor kumesine kosulur; dusen vektorler ISIMLERIYLE basilir ki
# ORTUSME gorunur olsun (ortusme varsa capa gevsektir).
# ---------------------------------------------------------------------------
MUTASYONLAR = [
    ("M1 sari esigi 250_000 -> 250_001 (alt sinir DISLANIR)",
     ("_TOK_SARI_ALT = 250_000", "_TOK_SARI_ALT = 250_001")),
    ("M2 kirmizi esigi 300_001 -> 300_000 (ust sinir DISLANIR)",
     ("_TOK_KIRMIZI_ALT = 300_001", "_TOK_KIRMIZI_ALT = 300_000")),
    ("M3 alan YOKLUGU 0'a dusurulur (None yolu-1)",
     ('    val = cw.get("total_input_tokens")\n    if val is None:\n        return None',
      '    val = cw.get("total_input_tokens")\n    if val is None:\n        return 0')),
    ("M4 context_window sozluk-DEGIL yolu 0'a dusurulur (None yolu-2)",
     ('    cw = payload.get("context_window")\n    if not isinstance(cw, dict):\n'
      '        return None\n    val = cw.get("total_input_tokens")',
      '    cw = payload.get("context_window")\n    if not isinstance(cw, dict):\n'
      '        return 0\n    val = cw.get("total_input_tokens")')),
    ("M5 sayiya-cevrilemez yolu 0'a dusurulur (None yolu-3)",
     ("    except (TypeError, ValueError, OverflowError):\n        return None",
      "    except (TypeError, ValueError, OverflowError):\n        return 0")),
    ("M6 kisa bicim FLOOR yerine ROUND (yukari yuvarlar)",
     ('        return f"{tok // 1_000}k"', '        return f"{round(tok / 1_000)}k"')),
    ("M7 token blogu segmente EKLENMEZ (kablolama-1: segment)",
     ('        seg += f" {_tok_renk(tok)}{_tok_bicim(tok)}{_C_RESET}"', '        seg += ""')),
    ("M8 build_line tokeni segmente GECIRMEZ (kablolama-2: satir)",
     ("        parts.append(_ctx_segment(pct, tok))", "        parts.append(_ctx_segment(pct))")),
    ("M9 REGRESYON capasi: yuzde kirmizi esigi 75 -> 70",
     ("    color = _C_RED if pct >= 75 else", "    color = _C_RED if pct >= 70 else")),
]


def main() -> int:
    if not MUTASYON:
        print("== statusline_token_esikleri -- BUGUNKU KOD (bilinen-TEMIZ) ==")
        tur()
        toplam = len(_yesil) + len(_kirmizi)
        print(f"\n{len(_yesil)}/{toplam} OK  ({len(_kirmizi)} FAIL)")
        return 0 if not _kirmizi else 1

    print("== MUTASYON TURU: her fix SOKULUR, dusen vektorler ISIMLE basilir ==")
    kacan = 0
    for ad, mut in MUTASYONLAR:
        _yesil.clear()
        _kirmizi.clear()
        try:
            tur(mut)
        except Kurulamadi as exc:
            print(f"  [KURULAMADI] {ad} -- {exc}   (KACTI DEGILDIR)")
            kacan += 1
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"  [YAKALANDI] {ad} -- mutasyon COKME uretti: {type(exc).__name__}: {exc}")
            continue
        if not _kirmizi:
            print(f"  [KACTI] {ad} -- korpus GORMEDI ({len(_yesil)} vektor hala yesil)")
            kacan += 1
        else:
            oldurulen = ", ".join(v.split(" ")[0] for v in _kirmizi)
            print(f"  [YAKALANDI] {ad}\n              oldurdugu vektorler ({len(_kirmizi)}): {oldurulen}")
    print(f"\nMUTASYON SONUCU: {len(MUTASYONLAR) - kacan}/{len(MUTASYONLAR)} yakalandi")
    return 0 if kacan == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
