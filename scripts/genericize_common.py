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
    """İsim listesi + yapısal desenler. IGNORECASE (D2: kimlik listesindeki ad küçük harfle de yakalanmalı)."""
    desenler = proje_desenleri(proje_koku, cwd) + YAPISAL
    return re.compile("(" + "|".join(desenler) + ")", re.IGNORECASE)


class TembelDesen:
    """`id_pattern()` sonucunu İLK KULLANIMDA üretir — davranış AYNI, yalnız ZAMAN farklı.

    NEDEN VAR (2026-08-13, süre-vergisi kuyruğu): `pre_tool_guard` deseni MODÜL
    yüklenirken kuruyordu (`_CORE_LEAK = id_pattern(...)`). `id_pattern` →
    `proje_desenleri` → `_git_dir` → `subprocess.run(git rev-parse)` zinciri ölçüldü:
    **~100 ms** (cProfile: thread-lock 87 ms + CreateProcess 20 ms). Bu bedel HER araç
    çağrısında ödeniyordu — oysa desen yalnız ÜÇ dalda kullanılır (commit-mesajı taraması,
    `gh` yayın taraması, core'a yazma taraması). Araç çağrılarının çoğunluğu bu dalların
    hiçbirine girmez ⇒ vergi tümüyle boşa gidiyordu.

    ⚠ DAVRANIŞ DEĞİŞMEZİ: bu sınıf desenin İÇERİĞİNİ değil, KURULMA ANINI değiştirir.
    Kullanıldığı anda `id_pattern()` aynen çağrılır, aynı kaynaklardan (env + git-dir +
    proje `.claude/`) aynı birleşim kurulur. Bir dal deseni kullanıyorsa maliyeti orada
    ödenir; kullanmıyorsa hiç ödenmez.

    ⚠ MEMOIZE EDİLMEDİ (bilinçli, ölçümle): `_git_dir`'e süreç-içi önbellek eklemek
    cazipti ama `tests/fixtures/worktree_blocklist/run.py` **S6** çapasını SESSİZCE
    öldürürdü — S6 `subprocess.run`'ı sahteleştirip "git GÖRELİ döndü" (Linux şekli)
    vakasını sınar; aynı cwd için S1'den gelen önbellek dolu olsaydı sahte hiç
    çağrılmaz, S6 trivial-yeşil olurdu (bu tam olarak CI'da bir kez patlamış sınıftır).
    Üstelik tembelleştirmeden SONRA guard süreci deseni zaten en fazla 1 kez kurar ⇒
    önbelleğin kazancı 0, riski gerçek.

    Yalnız `re.Pattern` yüzeyini devreder (`sizintilari_bul` `.search` kullanır);
    kullanım yerindeki çağrı metni DEĞİŞMEZ, böylece `_CORE_LEAK` şartnamesini
    sabitleyen kaynak-metin testi (`test_commit_message_leak_gate`) aynen geçerli kalır.
    """
    __slots__ = ("_kw", "_derlenmis")

    def __init__(self, **kw) -> None:
        self._kw = kw
        self._derlenmis: re.Pattern | None = None

    def _desen(self) -> re.Pattern:
        if self._derlenmis is None:
            self._derlenmis = id_pattern(**self._kw)
        return self._derlenmis

    def __getattr__(self, ad: str):
        # __slots__ + __getattr__: yalnız NORMAL arama başarısız olunca çağrılır,
        # yani `_kw`/`_derlenmis` buraya hiç düşmez → özyineleme yok.
        return getattr(self._desen(), ad)


def tembel_id_pattern(proje_koku: Path | None = None, cwd: Path | None = None) -> TembelDesen:
    """`id_pattern()`in tembel sarmalayıcısı — modül yükleme yolunda git çağırmaz."""
    return TembelDesen(proje_koku=proje_koku, cwd=cwd)


# --------------------------------------------------------------- Z-obje adları
# Core dokümanlarında GEÇMESİNE İZİN VERİLEN kanonik örnek adları. Bunlar hiçbir
# gerçek projenin objesi değildir; naming standardı / playbook örnekleridir.
# Buraya yeni ad eklemek = "core'da bu ad görünebilir" demektir → GEREKÇELİ PR.
ORNEK_Z = frozenset({
    "ZSD000", "ZSD001",           # kanonik SD demo çifti (ADR 0005 istisnası)
    "ZMM001", "ZMM002", "ZMM004",  # standards/01-naming.md ağaç örnekleri
    "ZPP001", "ZFI001",            # standards/01-naming.md tablo örnekleri
    "ZBC001", "ZQM001",            # playbook API-proxy örnekleri
    # ── 3-4 harfli modül kodları: D7 genişletmesiyle GÖRÜNÜR olan jenerik adlar ──
    # ⛔ Q326'nın "jenerik" saydığı 4 harfli bir ad BİLEREK BURADA DEĞİL: ölçüm çürüttü —
    #    gerçek bir müşteri paketidir (tüketici proje reposunda canlı paket + sınıfı). Allowlist'e
    #    almak, D7'nin ilk gerçek bulgusunu meşrulaştırmak olurdu. Doğru çare adı allowlist'e
    #    almak değil, çekirdekteki geçtiği yeri genericize etmektir.
    "ZMOD001",                     # "<MODÜL>" yerine geçen kanonik paket adı: playbook/adt-cds,
                                   # cds-creation checklist, populate_cds_views + td_spec_check öneri metinleri
    "ZMOD002", "ZMOD003",          # cds_paket_kapsami korpusu: paket-adı çözümleme vektörleri
    "ZMOD005",                     # aynı korpus: modül-altı düz (paket dizini olmayan) yerleşim vektörü
    "ZMOD009",                     # aynı korpus: `<PKG>_CLC` sonekli paket vektörü
})

# D3: eski desen `\bzsd0(?!00|01)\d{2}` idi. `_` ve `z` ikisi de word-char olduğu için
# `\b` alt-çizgiden SONRA eşleşmiyordu → `project_zsd001`, `zcl_zsd001_mizan` biçimindeki adlar KAÇIYORDU.
# D4: kapsam yalnız ZSD idi → ZBC/ZMM/ZQM/ZFI/ZPP hiç görülmüyordu.
#
# D7 (2026-09-18, kayıt Q326) — desen ÜÇÜNCÜ kez genişliyor ve sınıf her seferinde AYNI:
# *desen, yazıldığı gün karşılaştığı kümeye göre daraltılıyor.* D3 alt-çizgi sınırıydı,
# D4 "yalnız ZSD" kapsamıydı, D7 ise "yalnız 2 harfli modül kodu" (`Z[A-Z]{2}\d{3}`).
# SAP modül/uygulama kısaltması 2 harfle sınırlı DEĞİLDİR (SD, MM ama EWM, MOD, CRM…)
# ⇒ 3-4 harfli her Z adı kapıdan görünmeden geçiyordu; kontrol grubuyla ölçüldü
# (2 harfli modül kodu yakalanırken 3-4 harflisi YAKALANMIYORDU — mekanizma sağlam, kapsam dardı).
# Bu desen bir SINIFI (SAP Z obje adı) tarif etmelidir, elimizdeki örnekleri değil.
#
# ⚠ Genişletmenin bedeli ORNEK_Z'dedir: desen genişleyince core'un KENDİ jenerik örnek
# adları da "sızıntı" sayılır ve her commit bloklanır. Allowlist'e alınacak kümenin
# KURALI şudur (sayı YAZILMAZ — bayatlar): *core ağacında geçen, hiçbir gerçek projenin
# objesi olmayan, doküman/fixture içinde yer-tutucu olarak kullanılan adlar.* Yeni bir
# ad çıkarsa allowlist'e almadan ÖNCE gerçek bir objeye ait olmadığı ÖLÇÜLÜR; ölçmeden
# eklemek kapıyı sessizce gevşetir (yayın cache'lenir, geri alınamaz).
Z_OBJ_PAT = re.compile(r"(?<![A-Za-z0-9])(Z[A-Z]{2,4}\d{3})(?!\d)", re.IGNORECASE)

# D4: SAP kullanıcı adı (gerçek kişi).
# ⚠ Yalnız 'X' ya da yalnız 'N' harflerinden oluşan diziler dokümantasyon PLACEHOLDER'ıdır
# (gerçek kullanıcı değil) → muaf. 2026-07-10: kendi README şablonumuz bu yanlış-pozitife
# takıldı. Guard doğru çalışıyordu; desen fazla genişti. → BU MUAFİYET KORUNUR.
#
# D6 (2026-08-01 bug-avı AV-03) — desen İKİ yazım-varyantını kaçırıyordu:
#   küçük-harf yazım (`d_` + gövde) → KAÇIYORDU — ve bu, bir projenin kendi
#     `CLAUDE.md`'sinde bağlantı bilgisi yazılırken kullanılan olağan yazımdır
#   rakam sonekli ad (`D_` + gövde + rakam) → KAÇIYORDU (`(?![A-Za-z0-9])` rakamda kesiyordu)
# ⚠ Bu yorumda GERÇEK kullanıcı adı ÖRNEK OLARAK YAZILMAZ. Gerekçe Q329'dan (2026-09-18)
#   sonra DARALDI ama kaybolmadı: `core_precommit` artık bu dosyayı SATIR SATIR tarar
#   (dosya-bazlı `SCAN_EXEMPT` kaldırıldı) ⇒ commit anında yakalanır; ama YAZIM anındaki
#   guard `pre_tool_guard` hâlâ dosya ADIYLA muaf tutar (`_DESEN_TANIMLAYAN`) ⇒ Edit/Write
#   sırasında uyarı GELMEZ. (İlk taslakta tam da bu oldu; lider FP-ölçümünde yakaladı.)
#   Desen literali gerçekten gerekiyorsa: o satıra `genericize-allow: <gerekçe>`.
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


# ------------------------------------------------ UYARI desenleri (warn-first)
# Q361 (2026-10-12): public çekirdekte iki kimlik izi türü HİÇBİR katmanca görülmüyordu —
# bir bulut tenant host'u (auth docstring'i) ve bir tüketici projenin transport numarası
# (ajan tanımı + 4 fixture). İkisi de İSİM değil BİÇİM taşır ⇒ isim listesi (proje başına,
# çekirdek onu bilmez) yakalayamaz; yapısal desen gerekir. Fikir bir dış çekirdekten alındı,
# kod KOPYALANMADI.
#
# ⚠ WARN-FIRST (ADR 0019 moratoryumu): bu desenler `sizintilari_bul`'a GİRMEZ — o fonksiyon
# commit'i BLOKLAYAN yoldur ve `pre_tool_guard` + `seed_memory` de onu çağırır. Yeni desen
# FP'si ölçülmeden bloklayıcı yapılmaz; terfi AYRI ve bilinçli karardır. Tek tüketici
# `core_precommit` (staged · `--all` · `--ref` · `--msg`): bulgu basılır, çıkış kodu değişmez.
#
# KORPUS ÖLÇÜMÜ (2026-10-12, çekirdek ağacının takipli dosyaları): transport biçimli 19
# farklı dizge — fixture/örneklerde SAHTE SID'ler (aşağıdaki ORNEK_SID) + gerçek görünen
# SID'ler (bulgu; ilgili dosyalarda ayrı işte genericize edilir). Host biçimli dizgeler:
# yer tutucu ilk etiket (`abc123`), yalın bölge alanı (`eu10.hana…`) ve `.` önekli sonek
# listeleri — hiçbiri tenant DEĞİL ⇒ aşağıdaki muafiyetler bu ölçülen kümeden türetildi.
# YENİDEN ÖLÇÜM (Issue #357, 2026-10-19, takipli 1011 dosya): bölge muafiyeti ara etikete
# bağlandıktan sonra eşleşen dizgeler (span) eskisiyle 1011/1011 dosyada AYNI, uyarı farkı 0
# (yeni 0 · kaybolan 0). ⚠ Korpusta ham host eşleşmesi yalnız 4 — FP tabanı İNCE; ara etiketli
# + bölge biçimli ilk etiketli SAP-genel bir uç (tenant olmayan) bilinmiyor ama ÖLÇÜLMEDİ.

# SAP transport numarası: <SID>K<6 rakam>; SID 3 karakter, ilki harf.
TRANSPORT_PAT = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{2})K(\d{6})(?![A-Za-z0-9])",
                           re.IGNORECASE)
# Fixture/doküman yer tutucusu olduğu ÖLÇÜLEN SID'ler. Buraya SID eklemek o SID için uyarıyı
# KALICI susturur ⇒ gerçek bir sisteme ait olmadığı ölçülmeden eklenmez (ORNEK_Z ile aynı ölçüt).
ORNEK_SID = frozenset({"SAH", "AB1"})
_YER_TUTUCU_SID = re.compile(r"X{3}", re.IGNORECASE)

# Bulut tenant host'u: <ilk-etiket>[.<ara etiketler>].<SAP bulut soneki>
TENANT_HOST_PAT = re.compile(
    r"(?<![A-Za-z0-9._-])"                   # host'un BAŞI (ad karakteri / nokta / tireden sonra değil)
    # `<` ve `{` BİLEREK sınıfta YOK (bug-gate 2026-10-12): `<host>` / `{host}` sarmalı içindeki
    # somut host da uyarı vermeli. `<tenant>.…` yer tutucusu yine sessizdir — onu `>` keser.
    r"([A-Za-z0-9][A-Za-z0-9-]*)"            # ilk etiket = tenant / alt hesap
    # Ara etiketler (bölge, abap, authentication …) YAKALANIR (Issue #357, 2026-10-19): bölge
    # muafiyeti yalnız ara etiket YOKKEN geçerlidir ve bunu filtre group(2)'den okur. Yalnız
    # yakalayıcı grup eklendi; tembel `*?` aynen ⇒ eşleşen dizgeler eskisiyle birebir aynıdır.
    r"((?:\.[A-Za-z0-9-]+)*?)"
    r"\.(?:s4hana\.cloud\.sap|s4hana\.ondemand\.com|hana\.ondemand\.com"
    r"|accounts\.ondemand\.com|accounts\.cloud\.sap)"
    r"(?![A-Za-z0-9-])",
    re.IGNORECASE)
# İlk etiket bir BÖLGE/landscape kodu VE ardından ara etiket YOKSA host tenant değil, yalın
# bölge alanıdır (eu10.<sonek>, us10.<sonek>…). Ara etiket varsa (`<x>.authentication.eu10.…`,
# `<x>.abap.eu10.…`) ilk etiket bölge BİÇİMLİ olsa da bir alt hesap / tenant adıdır ⇒ uyarı.
# Issue #357 (2026-10-19): muafiyet eskiden ara etikete bakmıyordu; `ab12`/`de1` gibi bölge
# biçimli tenant adları sessizce geçiyordu.
_BOLGE_ETIKETI = re.compile(r"[a-z]{2}\d{1,3}(?:-\d{1,3})?", re.IGNORECASE)
# Ölçülen yer tutucu ilk etiketler (+ yalnız-x). `<tenant>` biçimi desene zaten uymaz.
ORNEK_TENANT = frozenset({"abc123"})
_YER_TUTUCU_ETIKET = re.compile(r"x{3,}", re.IGNORECASE)


def transport_sizintilari(metin: str) -> list[str]:
    """Allowlist dışı SID taşıyan transport numaraları (warn-first)."""
    return [m.group(0) for m in TRANSPORT_PAT.finditer(metin)
            if m.group(1).upper() not in ORNEK_SID
            and not _YER_TUTUCU_SID.fullmatch(m.group(1))]


def tenant_host_sizintilari(metin: str) -> list[str]:
    """Somut (yer tutucu / bölge olmayan) ilk etiketli SAP bulut host'ları (warn-first)."""
    return [m.group(0) for m in TENANT_HOST_PAT.finditer(metin)
            if m.group(1).lower() not in ORNEK_TENANT
            and not (_BOLGE_ETIKETI.fullmatch(m.group(1)) and not m.group(2))
            and not _YER_TUTUCU_ETIKET.fullmatch(m.group(1))]


def uyari_sizintilari(metin: str) -> list[tuple[str, str]]:
    """WARN-FIRST bulgular — (token, tür). Çağıran TOKEN'I BASMAMALIDIR (CI günlüğü public;
    uyarı commit'i bloklamadığı için iz her koşumda yeniden yazılırdı)."""
    return ([(t, "tenant host") for t in tenant_host_sizintilari(metin)]
            + [(t, "transport no") for t in transport_sizintilari(metin)])


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


# ------------------------------------------------ commit mesajı: ajan atıf satırları
# TEK KAYNAK (D9 kardeşi, 2026-10-12): commit mesajı taramasında tarama DIŞI tutulan
# satırlar. İki tüketici: `core_precommit` (`--ref`/`--msg`, yalnız `ATIF_SATIRI`) ve
# `pre_tool_guard` (commit-mesajı gate'i, `AJAN_IMZA_SATIRI`). Eskiden guard kendi
# desenini taşıyordu ve `Co-Authored-By|Claude-Session|Signed-off-by|Reviewed-by|Cc`
# anahtarlı HER satırı adresten bağımsız düşürüyordu ⇒ başka bir kişinin e-postasını
# taşıyan trailer sızıntı taramasından SESSİZCE geçiyordu.
# Muafiyet YALNIZ ajanın kendi yazdığı üç biçime işler; ölçüldü (takipli tarihçe, 630
# Claude co-author satırı + 323 oturum satırı): dar biçime uymayan 0.
#  · atıf trailer'ı: ad Claude + üreticinin noreply adresi; ad–adres arası `@` taşıyamaz
#    (aradaki ikinci e-posta muafiyete saklanamaz — bug-gate 2026-10-12, M10).
#    Bu satır e-posta yapısal desenine UYAR ⇒ muafiyetsiz her ajan commit'i bloklanırdı.
#    Muafiyet YALNIZ ADRESTİR (aşağıdaki ⛔ notu): ad bölümü taranır.
#  · oturum satırı: yalnız alfasayısal oturum kimlikli claude.ai bağlantısı.
#  · üretici satırı: yalnız sabit Claude Code bağlantısı.
#    (son ikisi bugün tarayıcıya takılmıyor — ölçüldü; dar tutuldukları için iz saklayamazlar)
# Satır satır uygulanır (`re.match`, MULTILINE değil): `\s` satır sonunu yiyip komşu
# satırı birleştiremez.
# ⛔ ATIF SATIRI BOŞALTILMAZ, YALNIZ ADRESİ MASKELENİR (bug-gate F3, 2026-10-14): ad bölümü
# (`Claude\b[^<@\n]*`) `@` dışında her şeyi taşıyabilir ⇒ satırı tümden boşaltmak oraya
# yazılan bir Z-obje / paket adını taramadan geçiriyordu. İki tüketici de satırı
# `ATIF_SATIRI` ile TANIR, `ATIF_ADRES_PAT` ile yalnız üreticinin adresini siler; satırın
# geri kalanı TARANIR. ÖLÇÜLDÜ (takipli tarihçe, iki repo, 2110 atıf satırı, 7 farklı ad
# biçimi — model adı + bağlam): maskeli satırın tarayıcıya takıldığı 0.
_ATIF_ADRES = r"<noreply@anthropic\.com>"
_ATIF_GOVDE = r"Co-Authored-By:\s*Claude\b[^<@\n]*" + _ATIF_ADRES
ATIF_SATIRI = re.compile(r"^\s*" + _ATIF_GOVDE + r"\s*$", re.IGNORECASE)
ATIF_ADRES_PAT = re.compile(_ATIF_ADRES, re.IGNORECASE)
AJAN_IMZA_SATIRI = re.compile(
    r"^\s*(?:" + _ATIF_GOVDE
    + r"|Claude-Session:[ \t]*https://claude\.ai/code/session_[A-Za-z0-9]+"
    + r"|\U0001F916[ \t]*Generated with \[Claude Code\]"
      r"\(https://claude\.(?:com/claude-code|ai/code)\)"
    + r")\s*$",
    re.IGNORECASE)
