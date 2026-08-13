#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`.claude/{agents,skills,commands}` için PROJE-LOKAL overlay kanalı.

SORUN (2026-07-09 denetimi): bu üç dizin core'a junction'dır. Claude Code proje-seviyesi
agent/skill/command'ı YALNIZ bu dizinlerden okur → **proje-özel agent tanımlanamıyordu.**
Sonuç: core'daki jenerik tanımlar projeye dayatılıyor ve genericize sırasında proje
gerçekleri placeholder'a dönüyor (ör. `backend-expert.md`: gerçek bir örnek obje yerine
var olmayan bir ad). "Tahmin yasak" diyen sistem, ajanı tahmine itiyordu.

ÇÖZÜM — OPT-IN overlay:
    <proje>/claude-local/agents/*.md   (COMMIT'Lİ, proje reposunda)
Bu dizin varsa `team_setup` `.claude/agents`'ı **junction yerine gerçek dizin** olarak
üretir: core dosyaları + üzerine proje dosyaları (aynı ad = override).
Yoksa hiçbir şey değişmez — junction kalır (sıfır blast radius).

GÜVENLİK: `.claude/{agents,skills,commands}/` zaten `.gitignore`'da (R1 sızıntı kilidi,
`check_core_not_committed` zorlar) → üretilen core kopyası proje reposuna GİRMEZ.

DRIFT: overlay manifest'i, override edilen her dosyanın **core'daki hash'ini** saklar.
Core güncellenince `check_claude_overlay` uyarır: "core değişti, overlay'i gözden geçir".
Böylece overlay sessizce bayatlamaz.

EZME KAPISI (T2.5) ayrı bir sorudur ve ayrı bir tabanı vardır: manifest her dosyanın
**üretildiği andaki hash'ini** (`uretilen_hash`) de saklar. `fark_raporu` kopyanın
ŞİMDİKİ hâlini bununla kıyaslar → "core değişti" ile "kopya elle düzeltildi" ayrışır.
(2026-08-13 kök-fix'i; gerekçe `fark_raporu` docstring'inde.)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

# "rules" 2026-07-10'da eklendi (L1b glob-tetiklemeli davranış kuralları). Junction'lanmazsa
# yeni projede `.claude/rules` HİÇ kurulmaz → kural yazılır ama hiç yüklenmez (kod≠kablolama).
TIPLER = ("agents", "skills", "commands", "rules")
MANIFEST_ADI = ".overlay-manifest.json"
DAMGA = "<!-- CORE-URETILDI: elle duzenleme; kaynak core/claude/{tip}/{ad} -->\n"

# ⚠ Agent/skill/command dosyaları YAML frontmatter ile BAŞLAMAK ZORUNDADIR (`---`).
# İlk sürümde damga frontmatter'ın ÖNÜNE konmuştu → 6/6 agent yüklenemez oldu ve harness
# "agent types no longer available" dedi. Dosya SAYISI doğruydu, FORMAT bozuktu; içerik
# saymak yetmiyor. Damga artık frontmatter'dan SONRA girer, dosyalar LF yazılır.
_FRONTMATTER = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.S)


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _junction_mu(p: Path) -> bool:
    try:
        return p.is_dir() and os.path.realpath(p) != os.path.abspath(p)
    except OSError:
        return False


def _damgala(icerik: str, damga: str) -> str:
    """Damgayı frontmatter'dan SONRA yerleştir — dosya `---` ile başlamalı."""
    m = _FRONTMATTER.match(icerik)
    if m:
        return icerik[:m.end()] + damga + icerik[m.end():]
    return damga + icerik          # frontmatter yoksa (command dosyaları) başa


def frontmatter_ile_basliyor(p: Path) -> bool:
    """Agent/skill dosyası `---` ile mi başlıyor? (yüklenebilirlik ön koşulu)"""
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            return f.readline().strip() == "---"
    except OSError:
        return False


def overlay_kaynagi(proje: Path, tip: str) -> Path:
    return proje / "claude-local" / tip


def overlay_var_mi(proje: Path, tip: str) -> bool:
    k = overlay_kaynagi(proje, tip)
    return k.is_dir() and any(k.glob("*.md"))


def hedef(proje: Path, tip: str) -> Path:
    return proje / ".claude" / tip


def _beklenen(proje: Path, core_root: Path, tip: str) -> dict:
    """Üretilecek dosya kümesi: {ad: (kaynak_yolu, core_hash|None)}"""
    out: dict = {}
    core_dizin = core_root / "claude" / tip
    if core_dizin.is_dir():
        for f in sorted(core_dizin.glob("*.md")):
            out[f.name] = (f, _hash(f))
    for f in sorted(overlay_kaynagi(proje, tip).glob("*.md")):
        core_esi = core_dizin / f.name
        out[f.name] = (f, _hash(core_esi) if core_esi.is_file() else None)
    return out


def _norm(icerik: str) -> str:
    """Damga satırı + satır-sonu normalizasyonu (fark kıyası için)."""
    satirlar = [s for s in icerik.replace("\r\n", "\n").split("\n")
                if not s.startswith("<!-- CORE-URETILDI")]
    return "\n".join(satirlar).strip()


def _manifest_dosyalari(h: Path) -> dict:
    """`.overlay-manifest.json` → {ad: kayit}. Okunamazsa BOŞ (kanıt yok = muhafazakâr dal)."""
    try:
        return json.loads((h / MANIFEST_ADI).read_text(encoding="utf-8")).get("dosyalar", {})
    except Exception:
        return {}


def _uretildigi_gibi(mevcut: Path, kayit) -> bool:
    """Kopya, EN SON ÜRETİLDİĞİ hâlde mi (bayt-bayt)?

    Bu, fark kıyasının TABANIDIR. `uretilen_hash` yoksa (2026-08-13 öncesi manifest)
    kanıt da yoktur → False döner ve çağıran bugünkü muhafazakâr içerik-kıyasına düşer.
    Sessiz gevşeme olmaz: eski manifestli projeler birebir eski davranışı görür.
    """
    beklenen = (kayit or {}).get("uretilen_hash")
    if not beklenen:
        return False
    try:
        return _hash(mevcut) == beklenen
    except OSError:
        return False


def fark_raporu(proje: Path, core_root: Path, tip: str) -> list:
    """T2.5 (2026-07-31): senkron ÖNCESİ fark raporu — senkronun EZECEĞİ proje emeği
    var mı? Boş liste = güvenli; dolu liste = önce terfi/claude-local kararı ver.

    KIYAS TABANI = kopya-ŞİMDİ ↔ en son ÜRETİLEN (manifest `uretilen_hash`).
    ⚠ 2026-08-13 kök-fix'i: taban eskiden "bugün üretilecek içerik"ti. O taban, ELLE
    DÜZELTME ile CORE GÜNCELLEMESİNİ ayırt edemiyordu → core'da bir ajan dosyası
    değiştiği an, projede hiçbir elle düzeltme olmasa bile kapı kapanıyordu (kurt
    masalı). Bedeli iki katmanlıydı: (a) junction'lı tipler bedavaya tazelenirken
    overlay'li tip her core commit'inde tören istiyordu; (b) `--overlay-onayli` refleks
    hâline gelince gerçek bir elle düzeltmeyi SESSİZCE ezecekti — yani kapı kendi
    koruduğu şeyi aşındırıyordu. Doğru soru "içerik core'dan farklı mı" değil,
    **"kopyaya senkrondan sonra dokunuldu mu"**dur.
    """
    h = hedef(proje, tip)
    if not h.is_dir() or _junction_mu(h):
        return []
    beklenen = _beklenen(proje, core_root, tip)
    kayitlar = _manifest_dosyalari(h)
    farklar = []
    for ad, (kaynak, _ch) in beklenen.items():
        mevcut = h / ad
        if not mevcut.is_file():
            continue  # yeni dosya — ezme değil ekleme
        if _uretildigi_gibi(mevcut, kayitlar.get(ad)):
            continue  # el değmemiş üretim artığı: kaynak değişmiş olabilir, KAYIP yok
        if _norm(mevcut.read_text(encoding="utf-8", errors="replace")) != \
           _norm(kaynak.read_text(encoding="utf-8", errors="replace")):
            farklar.append(f"{tip}/{ad}: mevcut kopya, üretilecek içerikten FARKLI "
                           f"(elle düzeltme olabilir → önce core'a terfi ya da claude-local'e al)")
    for f in sorted(h.glob("*.md")):
        if f.name in beklenen:
            continue
        # Aynı sınıfın ikinci yüzü: core bir dosyayı SİLDİYSE, el değmemiş kopyanın
        # silinmesi zaten doğru sonuçtur (junction'da bedavaya olur). Yalnız manifest
        # onu core-üretimi diye tanıyor VE bayt-bayt el değmemişse sessizce geç.
        kayit = kayitlar.get(f.name) or {}
        if kayit.get("kaynak") == "core" and _uretildigi_gibi(f, kayit):
            continue
        farklar.append(f"{tip}/{f.name}: üretim kümesinde YOK — senkronda SİLİNİR")
    return farklar


def materyalize(proje: Path, core_root: Path, tip: str, onayli: bool = False) -> tuple:
    """`.claude/<tip>`'i gerçek dizin olarak üret (core + overlay). -> (ok, mesaj)
    onayli=False iken mevcut kopyalarda fark varsa ÜRETMEZ (fark-onay kapısı, T2.5)."""
    if not overlay_var_mi(proje, tip):
        return False, f"overlay yok: {overlay_kaynagi(proje, tip)}"

    if not onayli:
        farklar = fark_raporu(proje, core_root, tip)
        if farklar:
            return False, ("FARK VAR — onaysız ezme YOK (T2.5):\n    "
                           + "\n    ".join(farklar)
                           + "\n    Karar ver (terfi/claude-local) → sonra --overlay-onayli ile koş.")

    h = hedef(proje, tip)
    if _junction_mu(h):
        os.rmdir(h)                     # junction'ı kaldır (hedefe DOKUNMAZ)
    elif h.is_dir():
        shutil.rmtree(h)                # eski üretim
    h.mkdir(parents=True, exist_ok=True)

    beklenen = _beklenen(proje, core_root, tip)
    manifest = {"tip": tip, "dosyalar": {}}
    for ad, (kaynak, core_hash) in beklenen.items():
        icerik = kaynak.read_text(encoding="utf-8", errors="replace")
        proje_ustu = kaynak.parent == overlay_kaynagi(proje, tip)
        if not proje_ustu:
            icerik = _damgala(icerik, DAMGA.format(tip=tip, ad=ad))
        # newline="\n" ŞART: varsayılan (None) Windows'ta CRLF yazar → frontmatter satırları
        # `---\r\n` olur ve bazı parser'lar bozulur; ayrıca sahte diff üretir.
        (h / ad).write_text(icerik, encoding="utf-8", newline="\n")
        manifest["dosyalar"][ad] = {
            "kaynak": "proje" if proje_ustu else "core",
            "core_hash": core_hash,       # override edilen core dosyasının hash'i (drift için)
            # ÜRETİLEN hâlin hash'i = fark_raporu'nun KIYAS TABANI (2026-08-13).
            # Damga + LF normalizasyonu SONRASI, yani diskteki gerçek bayt: kıyas
            # "yeniden üretsem ne çıkardı" tahminine değil, ölçüme dayansın.
            "uretilen_hash": _hash(h / ad),
        }
    (h / MANIFEST_ADI).write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                                  encoding="utf-8")
    n_proje = sum(1 for v in manifest["dosyalar"].values() if v["kaynak"] == "proje")
    return True, f"{tip}: {len(beklenen)} dosya ({n_proje} proje-lokal override)"


def durum(proje: Path, core_root: Path, tip: str) -> tuple:
    """-> (mod, sorunlar)  mod ∈ {'junction','overlay','yok'}"""
    h = hedef(proje, tip)
    if not h.exists():
        return "yok", [f"{tip}: dizin yok"]
    if _junction_mu(h):
        if overlay_var_mi(proje, tip):
            return "junction", [f"{tip}: claude-local/{tip} VAR ama .claude/{tip} hâlâ junction "
                                f"→ proje agent'ları YÜKLENMİYOR. Onarım: team_setup.py --repair-junctions"]
        return "junction", []

    # gerçek dizin → overlay olmalı ve güncel olmalı
    if not overlay_var_mi(proje, tip):
        return "overlay", [f"{tip}: gerçek dizin ama claude-local/{tip} yok → sızıntı riski, elle incele"]

    mf = h / MANIFEST_ADI
    if not mf.is_file():
        return "overlay", [f"{tip}: overlay manifest yok → team_setup.py --repair-junctions"]
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
    except Exception:
        return "overlay", [f"{tip}: overlay manifest okunamadı"]

    sorunlar = []

    # FORMAT: agents/skills frontmatter ile BAŞLAMALI. İlk sürümde damga frontmatter'ın
    # önüne girdi → 6/6 agent yüklenemedi, ama dosya SAYISI doğru olduğu için "güncel"
    # raporlandı. Sayı ≠ yüklenebilirlik. (2026-07-09)
    if tip in ("agents", "skills"):
        bozuk = [f.name for f in sorted(h.glob("*.md")) if not frontmatter_ile_basliyor(f)]
        if bozuk:
            sorunlar.append(f"{tip}: FRONTMATTER BOZUK {bozuk} — dosya `---` ile başlamalı, "
                            f"yoksa Claude Code bu {tip[:-1]}'ları HİÇ yüklemez")
        crlf = [f.name for f in sorted(h.glob("*.md")) if b"\r\n" in f.read_bytes()]
        if crlf:
            sorunlar.append(f"{tip}: CRLF satır sonu {crlf} — LF yazılmalı")

    beklenen = _beklenen(proje, core_root, tip)
    eksik = set(beklenen) - set(m["dosyalar"])
    fazla = set(m["dosyalar"]) - set(beklenen)
    if eksik:
        sorunlar.append(f"{tip}: overlay'de EKSİK {sorted(eksik)} (core yeni dosya ekledi?)")
    if fazla:
        sorunlar.append(f"{tip}: overlay'de FAZLA {sorted(fazla)} (core sildi?)")

    for ad, kayit in m["dosyalar"].items():
        if kayit["kaynak"] != "proje" or ad not in beklenen:
            continue
        _, guncel_core_hash = beklenen[ad]
        if guncel_core_hash and kayit.get("core_hash") and guncel_core_hash != kayit["core_hash"]:
            sorunlar.append(f"{tip}/{ad}: CORE GÜNCELLENDİ ({kayit['core_hash']} → {guncel_core_hash}) "
                            f"— proje override'ı bayatlamış olabilir, gözden geçir")
    return "overlay", sorunlar
