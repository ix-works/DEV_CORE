#!/usr/bin/env python3
"""Genericize/sızıntı desenleri — `core_precommit` + `pre_tool_guard` TEK KAYNAK (D9).

Bu iki guard 2026-07-10'a kadar AYRI listelerden besleniyordu: `pre_tool_guard`
`<proje>/.claude/genericize-blocklist.txt`'ten, `core_precommit`
`<git-dir>/genericize-blocklist`'ten. Biri güncellenip diğeri unutulabiliyordu; üstelik
çözümleme cwd'ye bağlıydı. Artık ikisi de buradan okur ve HER İKİ konumu birleştirir.

⚠ İSİM LİSTESİ BU DOSYADA TUTULMAZ. DEV_CORE **public**tir; müşteri/sistem/kişi adını
buraya yazmak, engellemeye çalıştığımız sızıntının kendisidir.

Kaynak sırası (hepsi BİRLEŞİR, ilk-bulan-kazanır DEĞİL):
  1. env `IX_GENERICIZE_BLOCKLIST` (virgülle ayrılmış)   ← CI secret'i buraya
  2. `<git-dir>/genericize-blocklist`                     ← repo ağacı DIŞI, klonlanmaz
  3. `<proje-kökü>/.claude/genericize-blocklist.txt`      ← gitignore'lu
  4. yapısal (isimsiz) desenler — HER ZAMAN eklenir

Yapısal desenler isim içermediği için public'te güvenlidir ve taze klonda/CI'da da
çalışır. Ama isim-listesi YOKSA koruma yarımdır → `blocklist_var_mi()` ile fail-closed
davranmak arayanın sorumluluğudur (CI'da zorunlu).
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# ---------------------------------------------------------------- isim listesi

def _dosyadan(p: Path) -> list[str]:
    if not p.exists():
        return []
    try:
        satirlar = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [s.strip() for s in satirlar if s.strip() and not s.lstrip().startswith("#")]


def _git_dir(cwd: Path | None = None) -> Path | None:
    """Blocklist'in yaşadığı git dizini — **ORTAK** dizin (`--git-common-dir`).

    ⚠ 2026-08-01 (bug-avı kuyruğu, infra-expert saha-bulgusu): eskiden `--git-dir` idi.
    Bir git **worktree**'sinde `--git-dir` → `.git/worktrees/<ad>` döner, blocklist ise
    ANA deponun `.git/genericize-blocklist` dosyasıdır → dosya BULUNAMAZ → `core_precommit`
    fail-closed'a düşer ve **worktree'den hiçbir commit atılamaz**. Worktree, infra-fix
    prosedürünün ZORUNLU çalışma alanı olduğu için bu, akışın tamamını kilitliyordu.
    (Aynı sınıfın yazma-anı kardeşi AV-21'di: `pre_tool_guard` core'u yol-dizgesinden
    tanıdığı için worktree'de sızıntı guard'ı kapalıydı.)

    ⚠ Dönen değer **göreli** olabilir (`.git`) — platforma göre değişir: Windows'ta mutlak,
    Linux'ta göreli gelir. Göreli sonuç **sorgunun `cwd`'sine** göre çözülmelidir, sürecin
    kendi cwd'sine göre DEĞİL. `Path(".git").resolve()` yazmak tam da bu hatadır: süreç
    başka bir dizindeyse sessizce yanlış yere bakar. (2026-08-01 CI bunu yakaladı; yerelde
    Windows mutlak döndürdüğü için görünmüyordu — ve bu, AV-21c'nin aynısı: göreli yolu
    yanlış tabana göre çözmek.)
    """
    taban = Path(cwd) if cwd else Path.cwd()
    for bayrak in ("--git-common-dir", "--git-dir"):   # eski git'lerde ilki yoksa geri düş
        try:
            out = subprocess.run(["git", "rev-parse", bayrak], capture_output=True,
                                 text=True, check=True, cwd=str(cwd) if cwd else None)
            ham = out.stdout.strip()
            if not ham:
                continue
            p = Path(ham)
            return p if p.is_absolute() else (taban / p).resolve()
        except Exception:
            continue
    return None


def proje_desenleri(proje_koku: Path | None = None, cwd: Path | None = None) -> list[str]:
    """Kimlik izi isim listesi (BİRLEŞİM, sırasız). Boşsa koruma yarımdır."""
    bulunan: list[str] = []

    env = os.environ.get("IX_GENERICIZE_BLOCKLIST", "").strip()
    if env:
        bulunan += [p.strip() for p in env.split(",") if p.strip()]

    gd = _git_dir(cwd)
    if gd is not None:
        bulunan += _dosyadan(gd / "genericize-blocklist")

    if proje_koku is not None:
        bulunan += _dosyadan(Path(proje_koku) / ".claude" / "genericize-blocklist.txt")

    # tekilleştir, sırayı koru
    return list(dict.fromkeys(bulunan))


def blocklist_var_mi(proje_koku: Path | None = None, cwd: Path | None = None) -> bool:
    return bool(proje_desenleri(proje_koku, cwd))


# ------------------------------------------------------------ yapısal desenler
# İsim içermez → public'te güvenli, taze klonda da çalışır.
YAPISAL = [
    r"C:[/\\]+Users[/\\]+(?!<)[^/\\ ]+",                       # makine-lokal kullanıcı yolu
    r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|net)\b)(?!test\b)(?!localhost\b)"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}",                           # e-posta (örnek domainler hariç)
]


def id_pattern(proje_koku: Path | None = None, cwd: Path | None = None) -> re.Pattern:
    """İsim listesi + yapısal desenler. IGNORECASE (D2: 'trakya' de yakalanmalı)."""
    desenler = proje_desenleri(proje_koku, cwd) + YAPISAL
    return re.compile("(" + "|".join(desenler) + ")", re.IGNORECASE)


# --------------------------------------------------------------- Z-obje adları
# Core dokümanlarında GEÇMESİNE İZİN VERİLEN kanonik örnek adları. Bunlar hiçbir
# gerçek projenin objesi değildir; naming standardı / playbook örnekleridir.
# Buraya yeni ad eklemek = "core'da bu ad görünebilir" demektir → GEREKÇELİ PR.
ORNEK_Z = frozenset({
    "ZSD000", "ZSD001",           # kanonik SD demo çifti (ADR 0005 istisnası)
    "ZMM001", "ZMM002", "ZMM004",  # standards/01-naming.md ağaç örnekleri
    "ZPP001", "ZFI001",            # standards/01-naming.md tablo örnekleri
    "ZBC001", "ZQM001",            # playbook API-proxy örnekleri
})

# D3: eski desen `\bzsd0(?!00|01)\d{2}` idi. `_` ve `z` ikisi de word-char olduğu için
# `\b` alt-çizgiden SONRA eşleşmiyordu → `project_zsd015`, `zcl_zsd009_mizan` KAÇIYORDU.
# D4: kapsam yalnız ZSD idi → ZBC/ZMM/ZQM/ZFI/ZPP hiç görülmüyordu.
Z_OBJ_PAT = re.compile(r"(?<![A-Za-z0-9])(Z[A-Z]{2}\d{3})(?!\d)", re.IGNORECASE)

# D4: SAP kullanıcı adı (gerçek kişi).
# ⚠ Yalnız 'X' ya da yalnız 'N' harflerinden oluşan diziler dokümantasyon PLACEHOLDER'ıdır
# (gerçek kullanıcı değil) → muaf. 2026-07-10: kendi README şablonumuz bu yanlış-pozitife
# takıldı. Guard doğru çalışıyordu; desen fazla genişti. → BU MUAFİYET KORUNUR.
#
# D6 (2026-08-01 bug-avı AV-03) — desen İKİ yazım-varyantını kaçırıyordu:
#   küçük-harf yazım (`d_` + gövde) → KAÇIYORDU — ve bu, bir projenin kendi
#     `CLAUDE.md`'sinde bağlantı bilgisi yazılırken kullanılan olağan yazımdır
#   rakam sonekli ad (`D_` + gövde + rakam) → KAÇIYORDU (`(?![A-Za-z0-9])` rakamda kesiyordu)
# ⚠ Bu yorumda GERÇEK kullanıcı adı ÖRNEK OLARAK YAZILMAZ: bu dosya iki gate'te de
#   SCAN_EXEMPT'tir, yani buraya yazılan bir kimlik hiçbir kapı tarafından yakalanmaz
#   ve public çekirdeğe sızar. (İlk taslakta tam da bu oldu; lider FP-ölçümünde yakaladı.)
# İkisi birden gereken gerçek bir vaka ölçüldü: küçük-harf + rakam-sonekli bir servis
# kullanıcısı hiçbir katman tarafından görülmüyordu. Bu, PUBLIC çekirdeğe kimlik
# sızmasını önleyen SON kapıdır (2026-07-10 D1 vakası) → kaçırmak geri-alınamaz.
#
# ⚠ İLK TASLAK YANLIŞTI — DÜZELTME GEREKÇESİ (aynı gün, lider canlı kapıyla çürüttü):
# Deseni topyekûn IGNORECASE yapmıştım. Ölçümüm "çekirdekte FP=0" diyordu ama ÖLÇÜM
# YÖNTEMİ HATALIYDI: doğrulamayı `core_precommit --all` ile yapmıştım ve `--all`
# `git ls-files` kullanır = YALNIZ TAKİPLİ dosyalar. Yeni yazdığım fixture'lar
# takipsizdi → tarama onları YAPISAL OLARAK GÖREMEDİ. Gerçek `git commit`
# (staged yol) 4 ihlalle bloklandı; ikisi kendi test dosyalarımdı.
# Ders: "taradım" demeden ÖNCE tarayıcının KAPSAMINI doğrula (--all ≠ tüm dosyalar).
#
# Asıl mesele fixture değildi: `d_` + 4+ harf, IGNORECASE'te `d_data`/`d_rows`/`d_total`
# gibi SIRADAN değişken adlarına uyar → bundan sonra yazılacak olağan kodda da ateşler.
# FP burada ucuz DEĞİL: kapı commit'i bloklar ve geliştiriciyi bypass refleksine iter
# (PATTERN #14 / 08bb6e6 dersi).
#
# ── ÇÖZÜM: yazım-varyantına göre AYRI ŞİDDET, ölçümle seçildi ────────────────────
# A) BÜYÜK harf (`D_XXXXXX`, ops. rakam) → BAĞLAMSIZ yakalanır. SAP kullanıcı adının
#    kanonik yazımı budur; çekirdek ağacında ölçülen FP = 0.
# B) küçük/karışık harf → YALNIZ KİMLİK BAĞLAMINDA (aynı satırda user/kullanıcı/
#    login/hesap/owner gibi bir anahtar varsa). Serbest metindeki yalın `d_xxxx`
#    artık tetiklemez.
#
# ÖLÇÜM (2026-08-01; TARANAN KAPSAM AÇIKÇA: `C:\IX\_wt\girdi` çekirdek ağacının TÜM
# dosyaları — takipli + TAKİPSİZ, `tests/` dahil; hariç: .git, node_modules, attic,
# __pycache__ — ve ayrıca proje ağacı, core junction'ı hariç):
#   bağlamsız IGNORECASE (ilk taslak) : çekirdekte 4 FP · projede 3 FP
#   bağlam-duyarlı (B, seçilen)       : çekirdekte 0 FP · projede 1 FP
#   ve HER İKİ tasarım da iki gerçek kimliği (biri listede olmayan servis kullanıcısı)
#   kaçırmadan yakalıyor → FP 4→0 düşerken FN artmadı.
# Sözlük-freni (data/total/rows... muafiyeti) da ölçüldü; FP'si benzer ama `d_matnr`,
# `d_bookno` gibi SAP-vari adları kapsayamaz ve büyüyen liste bakım borcu doğurur
# ("kural kuralı doğurmasın") → REDDEDİLDİ.
#
# KABUL EDİLEN SINIR (FN, bilinçli): hiçbir kimlik anahtarı olmayan bir satırdaki YALIN
# küçük-harf ad kaçar. Telafi katmanları: (1) aynı adın BÜYÜK yazımı bağlamsız yakalanır,
# (2) isim-listesi katmanı (`id_pattern`, IGNORECASE/D2) bilinen adları her yazımda
# yakalar — ölçüldü. Yapısal desenin küçük-harf işi, LİSTEDE OLMAYAN adı taze-klon/CI'da
# yakalamaktır; onu da kimlik bağlamında yapar.
SAP_USER_PAT = re.compile(
    r"(?<![A-Za-z0-9_])D_"
    r"(?!X{2,}[0-9]*(?![A-Za-z0-9]))"   # placeholder: D_ + yalnız X'ler (+ops. rakam)
    r"(?!N{2,}[0-9]*(?![A-Za-z0-9]))"   # placeholder: D_ + yalnız N'ler (+ops. rakam)
    r"[A-Z]{4,}[0-9]*(?![A-Za-z0-9])")  # rakam soneki SINIRSIZ: {0,4} yazsaydık 5+ rakamlı
                                        # ad sessizce kaçardı (tasarım-anı ölçümü)

# (B) Yalnız KİMLİK BAĞLAMINDA aranan varyant — küçük/karışık harf de kapsanır.
SAP_USER_BAGLAMLI_PAT = re.compile(
    r"(?<![A-Za-z0-9_])D_"
    r"(?!X{2,}[0-9]*(?![A-Za-z0-9]))"
    r"(?!N{2,}[0-9]*(?![A-Za-z0-9]))"
    r"[A-Za-z]{4,}[0-9]*(?![A-Za-z0-9])",
    re.IGNORECASE)

# Kimlik taşıyan bağlam işaretleri (aynı SATIRDA aranır — açıklanabilir ve test edilebilir
# sınır; `ADT_SAP_USER=...`, "User: ...", "kullanıcı ..." hepsi bu kümeye düşer).
KIMLIK_BAGLAMI_PAT = re.compile(
    r"user|kullanic|kullanıc|login|logon|uname|hesap|account|owner|sap_user", re.IGNORECASE)


def z_obje_sizintilari(metin: str) -> list[str]:
    """Örnek-allowlist'te olmayan Z-obje adları."""
    return [m.group(1) for m in Z_OBJ_PAT.finditer(metin)
            if m.group(1).upper() not in ORNEK_Z]


def sap_user_sizintilari(metin: str) -> list[str]:
    """SAP kullanıcı adı izleri. SATIR SATIR bakar: BÜYÜK-harf yazım her yerde,
    küçük/karışık yazım YALNIZ kimlik bağlamı taşıyan satırda (yukarıdaki gerekçe).
    """
    bulunan: list[str] = []
    for satir in (metin.splitlines() or [metin]):
        satirda = [m.group(0) for m in SAP_USER_PAT.finditer(satir)]
        if KIMLIK_BAGLAMI_PAT.search(satir):
            satirda += [m.group(0) for m in SAP_USER_BAGLAMLI_PAT.finditer(satir)]
        # Aynı token iki desenden de gelebilir → satır içinde tekilleştir (sıra korunur).
        bulunan += list(dict.fromkeys(satirda))
    return bulunan


def sizintilari_bul(metin: str, idp: re.Pattern) -> list[tuple[str, str]]:
    """(token, tür) listesi. Çağıran `idp`'yi `id_pattern()` ile üretir."""
    bulgular: list[tuple[str, str]] = []
    m = idp.search(metin)
    if m:
        bulgular.append((m.group(0), "kimlik izi"))
    for t in z_obje_sizintilari(metin):
        bulgular.append((t, "Z-obje adı"))
    for t in sap_user_sizintilari(metin):
        bulgular.append((t, "SAP kullanıcı adı"))
    return bulgular
