#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pre_tool_guard — hedef repo METİNDEN çözülmez (repo-maskeleme turu, 2026-10-14).

NEDEN BU KORPUS VAR
-------------------
İki sızıntı gate'i (PUBLIC-PR · COMMIT-MESAJI) yayın/commit hedefinin görünürlüğünü
komut METNİNDEKİ ilk `--repo` / ilk `cd` / ilk `git -C` eşleşmesinden çözüyordu. Tırnaklı
başlık/gövde/mesaj içine yazılmış bir private hedef gerçek PUBLIC hedefi maskeliyor, gövde
TARANMADAN geçiyordu (ağsız probe + gerçek CLI: rc 0). gh'nin kısa bayrağı `-R` hiç
tanınmıyordu: `gh pr create -R <public>` private proje kökünden cwd'ye düşüp geçiyordu.
Kardeş: GH-HEDEF kuralı "açık hedef" hükmünü de metinden veriyordu (`--title 'bkz --repo
x'` hedefsiz mutasyonu serbest bırakıyordu; IGNORECASE `-r <reviewer>`'ı `-R` sayıyordu).

DÜZELTME (ölçülen değişmezler)
  · Sızıntı gate'i: aday kümesi = ESKİ tek-aday (main'in birebir sorgusu) ∪ GERÇEK token
    adayları (`--repo`/`--repo=`/`-R`/`-RX`/`-dR`, `gh api` yolu, `git -C`/`--git-dir`/
    `--work-tree`/`GIT_DIR=`, son gerçek `cd`, yoksa proje kökü). Biri public ise public.
  · Eski aday TUTULUR ⇒ main'e göre gevşeme yapısal olarak 0; mevcut FP'ler (metinde public
    geçen private hedef) aynen kalır — K11/K13/K14 bunu çiviler (lider kararı).
  · Tekil aday > 5 ⇒ sorgusuz FAIL-CLOSED (T1).
  · GH-HEDEF: açık hedef yalnız pflag çözümlemesinin GERÇEK `--repo`/`-R` değerinden
    (değer alan bayrak bir sonraki token'ı tüketir — `-t "--repo"` başlıktır); küme yok,
    boşluklu değer hedef değil, `-r` reviewer; çözümleme kesin değilse (tabloda olmayan
    alt-komut / tanınmayan bayrak) blok; main'in metin deseni de tutmalı. ⚠GEVŞETME
    (kullanıcı onaylı 2026-10-14): `-Rorg/x` bitişik biçim açık hedeftir (H5).

DÜZELTME TURU (bug-gate 2026-10-14) — ek bölümler
  Q  kabuk lehçesi: Bash `'\''` · `$'…'` · PowerShell backtick/`''` kaçışından SONRAKİ
     içerik commit mesajında (kol a) ve PR/release metninde (kol b) TARANIR; metnin ilk
     eşleşmesi (`--title 'bkz --body x'`) gerçek değeri maskelemez.
  F  F1 bayrak DEĞERİ olan `"--repo"`/`"-Rorg/x"` açık hedef DEĞİL · F2 kaçışlı başlık
     FP üretmez (Windows yolu eskisi gibi) · F3 yol çözümleme istisnası çökme değil
     fail-closed.
  P  kesin gerçek hedef yoksa cwd aday kümesine girer (P1L: KATMAN vektörü — GH-HEDEF önce
     blokladığı için sızıntı gate'i doğrudan çağrılır; savunma derinliği katman başına).
  U  bayrak tablosu bayatlığı gevşetme üretmez (tabloda olmayan alt-komut / bayrak = blok).
  B5–B8 (tur-3) bitişik muafiyeti, muafiyeti DOĞURAN gerçek `-R<değer>` token'ına ve metinde
     birebir `-R<değer>` yazımına bağlıdır — başlıktaki `-Rx` metni başka biçimli gerçek
     hedefin (`"--repo" org/x` · PS ``--re`po`` · PS ``-R`org/x``) freni açmaz (main BLOK).
  Kablolama kipleri (`--mutasyon-commit-kablosuz` / `--mutasyon-pr-kablosuz`) main()
     üzerinden koşan vektörlerin dispatcher bağını ölçer (kaynak-regex testinin karşılığı).
  Y  (tur-4) kabuğun gh'ye argüman olarak GEÇİRMEDİĞİ metin (kelime başı `#` yorum, PS
     `<#…#>`, yönlendirme işleneni `<<<` `<` `>` `2>`, bash `\\<boşluk>` kaçışı) açık hedef ve
     sızıntı adayı üretmez; bitişik `-R<değer>` muafiyeti token'ın KENDİ ham yazımına bağlı.
     Y27–Y32 KATMAN vektörleri (sızıntı gate'i doğrudan; main() ucunda GH-HEDEF önce bloklar, Y33).
  YK (tur-4 kontrol) yaygın yönlendirme (`2>&1` `> out` `2>$null` `*>$null` heredoc), tırnak
     içi `#`/`>`, URL `#`, `a#b`, PS kelime ortası `>` ve onaylı bitişik biçim FP üretmez.
     Kabuk gerçekliği bash 5.3 + Windows PowerShell 5.1 argv dökümüyle ölçüldü (B82e tur-4).

BÖLÜMLER
  M  maskeleme/tanınmayan gerçek hedef: BLOKLANIR + gövde TARANDI (sentinel bulgusu)
  K  kontrol: gerçek hedef private ⇒ GEÇER · public ⇒ BLOK · mevcut FP'ler KALIR
  H  GH-HEDEF: metin hedef sayılmaz (BLOK) · gerçek token hedeftir (GEÇER)
  T  aday tavanı FAIL-CLOSED
  3. BAĞLAM: PowerShell yüzeyi (M1f, M3e, H13) + heredoc/`$(cat)` gövde (M1g, M1h, M2c)

Görünürlük: `gh repo view` alt süreci taklit edilir — repo ARGÜMANI "public" içeriyorsa
public; argüman yoksa cwd yolu "public" içeriyorsa public (ağ yok). Tarayıcı sentinel.
Guard + genericize_common GEÇİCİ kuma kopyalanır; mutasyon yalnız kopyaya uygulanır.
Tüm vektörler TEK alt süreçte koşar (`_PROJ_ROOT` vaka başına atanır).

KOŞUM:  python tests/fixtures/guard_hedef_maskeleme/run.py [--mutasyon-<kip>]
Çıkış:  0 hepsi beklendiği gibi · 1 sapma · 2 DOĞRULANAMADI (çapa tutmadı / mutant bozuk)
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
SCRIPTS = REPO / "scripts"

# kip -> (eski, yeni) — YALNIZ kumdaki guard kopyasına uygulanır. Yorum = düşmesi gereken.
MUTLAR = {
    # Karar yeniden YALNIZ eski (metin) adaydan => tüm M vektörleri KAÇAR (+ T1, P1L, M6;
    # tur-4: Y27–Y32 — eski aday metindeki private `--repo`).
    "--mutasyon-eski-tek-aday": (
        "    for h in [eski_hay] + list(adaylar):\n",
        "    for h in [eski_hay]:\n"),
    # Eski aday birleşimden düşer => mevcut FP'ler kalkar (main'e göre GEVŞEME) => K11/K13/K14.
    "--mutasyon-eski-aday-yok": (
        "    for h in [eski_hay] + list(adaylar):\n",
        "    for h in list(adaylar):\n"),
    # gh gerçek bayrak adayı yok (yalnız api yolu) => M1*, M2b, M4*.
    "--mutasyon-gh-bayrak-adayi-yok": (
        "    repolar = _gh_repo_degerleri(seg) + gercek + ([api_repo] if api_repo else [])\n",
        "    repolar = [api_repo] if api_repo else []\n"),
    # FAZLA (bağımsız) taramada `-R` tanınmaz => M6 (`-t -R <public>`: bayat tabloya karşı
    # sigorta — çözümleyici `-R`yi başlık değeri sayar, fazla tarama yine aday sayar).
    "--mutasyon-kisa-r-yok": (
        '_GH_KISA_REPO = re.compile(r"^-([A-Za-z]*)R(.*)$", re.DOTALL)',
        '_GH_KISA_REPO = re.compile(r"^-([A-Za-z]*)\\x00R(.*)$", re.DOTALL)'),
    # pflag çözümleyicisi `-R`yi tanımaz (bilinmeyen harf ⇒ kesin=False) => H5/H6/B8 BLOK olur;
    # `-R` hedefli M1e/M2b/M4*/K11 de imza değiştirir (GH-HEDEF önce bloklar). Tur-4: YK11–YK13,
    # YK20, YK25 (onaylı/kısa biçim + yönlendirme kontrolleri) BLOK olur.
    "--mutasyon-cozumleyici-r-yok": (
        '                if ch == "R" or ch in dk:\n',
        '                if ch in dk:\n'),
    # git üst seçenek/ortam adayı yok => M5, M5b, M5c, M5d, K7.
    "--mutasyon-git-hedef-yok": (
        "    baglam = _baglam_cwd_hay(segler, idx)\n    if not yollar:\n",
        "    baglam = _baglam_cwd_hay(segler, idx)\n    yollar = []\n    if not yollar:\n"),
    # Aday tavanı etkisiz => T1 (6 private aday) GEÇER.
    "--mutasyon-tavan-yok": ("_HEDEF_ADAY_TAVANI = 5", "_HEDEF_ADAY_TAVANI = 99"),
    # GH-HEDEF yeniden METİNDEN (eski `_GH_A_ACIK`) => H1, H2, H4, H7b, H9, H13, H16, H17, F1h,
    # P1, U1, U2 GEÇER; H5, B8, M4b BLOK. Tur-4: Y22/Y23/Y33 GEÇER (yorumdaki `--repo`/`-R` metni)
    # · YK11–YK13, YK25 BLOK.
    "--mutasyon-ghhedef-metin": (
        "    acik_bayrak = _gh_acik_bayrak(komut)\n",
        "    acik_bayrak = bool(_GH_A_ACIK.search(komut))\n"),
    # Küme biçimi açık hedef sayılır => H7b GEÇER (H7'yi metin-deseni freni de tutar —
    # iki katman, katman başına ayrı vektör: H7b'de metin deseni başlıktaki `-R y`'den tutar).
    "--mutasyon-ghhedef-kume": (
        'if b != "kume" and v and', 'if v and'),
    # Boşluklu değer hedef sayılır => H17 (konumsal `"-R org/x"`) GEÇER.
    "--mutasyon-ghhedef-bosluk": (
        " and not any(x.isspace() for x in v)]\n", "]\n"),
    # `-r` (reviewer) `-R` sayılır => H4 GEÇER.
    "--mutasyon-ghhedef-buyuk-kucuk": (
        '                if ch == "R" or ch in dk:\n',
        '                ch = "R" if ch == "r" else ch\n                if ch == "R" or ch in dk:\n'),
    # Konumsal hedef yeniden METİNDEN => H3 · B4 (`--description org/x` değerdir) · Y24/Y25
    # (yorum / `<<<` işleneni) GEÇER.
    "--mutasyon-ghhedef-konumsal-metin": (
        '    return bool(eski and c and c["kesin"]\n'
        '                and any(_GH_KONUMSAL.fullmatch(tok) for tok in c["konumsal"]))\n',
        "    return eski\n"),
    # F1: açık hedef yeniden BAĞIMSIZ token taramasından (değer tüketmez) => F1c · F1d · F1h · P1
    # GEÇER (biçim `bitisik` etiketlenir: bitişik freni tek başına F1c/F1d'yi tutamaz). Tur-4
    # ölçümü: bitişik freni artık çözümleyicide (ham yazım) olduğu için mutant onu da atlar ⇒
    # F1a–F1h, P1, B3, B5–B7, Y9, Y15–Y21 düşer.
    "--mutasyon-ghhedef-bagimsiz-tarama": (
        '    gercek = [(v, b) for v, b in c["repolar"]\n'
        '              if b != "kume" and v and not any(x.isspace() for x in v)]\n',
        '    gercek = [(v, "bitisik") for v in _gh_repo_degerleri(seg, kesin=True)]\n'),
    # main'in metin deseni freni yok => B3 (PowerShell ``--re`po``, metinde görünmeyen hedef) ·
    # B5 · B6 · B7 · Y15–Y21 GEÇER.
    "--mutasyon-ghhedef-eski-desen-yok": (
        '    return bool(c["kesin"] and gercek and (_GH_A_ACIK.search(seg) or bitisik))\n',
        '    return bool(c["kesin"] and gercek)\n'),
    # Tur-3: bitişik muafiyeti yeniden METİN deseninden (gerçek token'a bağlı değil) =>
    # B5 (`"--repo" org/x -t '-Rx'`) · B6 (PS ``--re`po`` + başlıkta `-Rfoo`) · B7 (PS ``-R`org/x``)
    # · Y15–Y21 (tur-4 tuzak + O3) GEÇER.
    "--mutasyon-bitisik-metin-freni": (
        '    return bool(c["kesin"] and gercek and (_GH_A_ACIK.search(seg) or bitisik))\n',
        '    return bool(c["kesin"] and gercek and (_GH_A_ACIK.search(seg) '
        'or _GH_BITISIK_R.search(seg)))\n'),
    # KABLOLAMA (tur-3): dispatcher sızıntı fonksiyonunu çağırmaz => tüm CM vektörleri (M2, M2c,
    # M3*, M5*, K3, K6, K8, K14, Q1, Q4, Q5, F3, F3c, YK23) KAÇAR. Kaynak-regex testinin davranışsal karşılığı.
    "--mutasyon-commit-kablosuz": (
        "        sorun = _iki_lehce(lehce, _git_commit_public_leak, komut, ham)\n",
        "        sorun = _iki_lehce(lehce, lambda *a: '', komut, ham)\n"),
    # KABLOLAMA (tur-3): PUBLIC-PR gate'i çağrılmaz => main() üzerinden koşan PR vektörleri
    # (M1*, Q2, Q3, Q6, Q7, Q10–Q14, M6, YK22 …) KAÇAR; P1L ve Y27–Y32 (gate doğrudan) DÜŞMEZ (beklenen).
    "--mutasyon-pr-kablosuz": (
        "        sorun = _iki_lehce(lehce, _gh_pr_public_leak, komut, ham)\n",
        "        sorun = _iki_lehce(lehce, lambda *a: '', komut, ham)\n"),
    # Tabloda olmayan alt-komut kesin sayılır (bayatlık gevşetir) => U1 GEÇER.
    "--mutasyon-tablo-disi-kesin": (
        "    kesin = giris is not None\n", "    kesin = True\n"),
    # Tanınmayan uzun bayrak kesin sayılır => U2 GEÇER.
    "--mutasyon-bilinmeyen-bayrak-kesin": (
        "                kesin = False                 # tanınmayan uzun bayrak\n",
        "                pass\n"),
    # P1: metinde `--repo` varsa cwd sorulmaz (eski kural) => P1L KAÇAR.
    "--mutasyon-p1-cwd-yok": (
        '    if not (api_repo or (c and c["kesin"] and gercek)):\n',
        "    if not repolar:\n"),
    # Kol b: yayın metni yalnız regex (ilk eşleşme, apostrofta kesilen) => Q2, Q3, Q6, Q10–Q13 KAÇAR.
    "--mutasyon-yayin-token-yok": (
        '    c = _gh_bayrak_cozumle(komut) if _LEHCE != "eski" else None\n',
        "    c = None\n"),
    # Lehçe kolu yok (yalnız eski model) => Q1, Q2, Q3, Q4, Q6, Q10–Q13, Y27–Y32 KAÇAR.
    "--mutasyon-iki-lehce-yok": (
        '    for l in dict.fromkeys(("eski", lehce)):\n',
        '    for l in ("eski",):\n'),
    # Bash tırnak dışı `\'` kaçışı yok (kelime bölücü) => Q1, Q2, Q3 KAÇAR; F2a/F2b/F2d FP döner;
    # tur-4: `\<boşluk>` da kaçış değil olur => Y3, Y5, Y29.
    "--mutasyon-bash-kacis-yok": (
        '        if lehce == "bash" and c == "\\\\" and i + 1 < n and s[i + 1] in _BASH_HARF_KACIS:\n'
        '            cur.append(',
        '        if False:\n            cur.append('),
    # ── tur-4 kipleri: kabuğun argüman saymadığı metin ──────────────────────────────────
    # Tırnaksız kelime başı `#` yorum sayılmaz => Y1 Y4 Y6 Y15 Y22–Y24 Y27 Y28 Y31–Y33 düşer.
    "--mutasyon-yorum-yok": (
        '            if c == "#":\n                break',
        '            if False:\n                break'),
    # PowerShell `<#…#>` blok yorumu yok => YK25 (blok yorumdan sonraki gerçek argüman kaybolur:
    # FP). Y10 DÜŞMEZ: `<` kelime başı işleç + `#` satır yorumu onu ikinci katmanda korur.
    "--mutasyon-ps-blok-yorum-yok": (
        '            if lehce == "ps" and s.startswith("<#", i):\n                j = s.find("#>", i + 2)\n'
        '                i = n if j < 0 else j + 2',
        '            if False:\n                j = s.find("#>", i + 2)\n'
        '                i = n if j < 0 else j + 2'),
    # Bash `\<boşluk>` kaçışı yok (kelimeyi böler) => Y3 Y5 Y29.
    "--mutasyon-kacisli-bosluk-yok": (
        "_BASH_HARF_KACIS = \"'\\\"\\\\ \\t#<>\"",
        "_BASH_HARF_KACIS = \"'\\\"\\\\#<>\""),
    # Bash yönlendirme işleneni argüman sayılır => Y2 Y7 Y8 Y9 Y17 Y25 Y30.
    "--mutasyon-bash-yonlendirme-yok": (
        '        if lehce == "bash" and c in "<>":\n',
        '        if False:\n'),
    # Bash fd öneki (`2>`) kelime sayılır => Y9 (`-t 2` değer alır, `-Rorg/x` hedef olur).
    "--mutasyon-fd-yok": (
        "            if cur and not tirnak_gordu and k.isdigit():\n",
        "            if False:\n"),
    # PowerShell kelime başı yönlendirme yok => Y11 Y12.
    "--mutasyon-ps-yonlendirme-yok": (
        '            m = _YONL_PS.match(s, i) if lehce == "ps" else None\n',
        "            m = None\n"),
    # Segmentleyici yorumu bilmez (yorumdaki apostrof tırnak açar) => Y26.
    "--mutasyon-segment-yorum-yok": (
        '        if yeni and not q and kb and c == "#":\n',
        '        if False:\n'),
    # Bitişik muafiyetinin metin şartı segmentin TAMAMINDA aranır (önceki tur) => Y15 Y16 Y17.
    "--mutasyon-bitisik-segment-metni": (
        '                                    ("-R" + v) in th[i][1] and _GH_BITISIK_DEGER.fullmatch(v)):\n',
        '                                    ("-R" + v) in seg and _GH_BITISIK_DEGER.fullmatch(v)):\n'),
    # Bitişik değerde karakter sınıfı yok => Y18 Y19.
    "--mutasyon-bitisik-deger-serbest": (
        '_GH_BITISIK_DEGER = re.compile(r"[\\w.:/-]+")',
        '_GH_BITISIK_DEGER = re.compile(r".+")'),
    # ANSI-C `$'…'` yok => Q4 KAÇAR; F2c FP döner.
    "--mutasyon-ansi-c-yok": (
        '        if lehce == "bash" and c == "$" and i + 1 < n and s[i + 1] == "\'":\n'
        '            i += 2\n',
        '        if False:\n            i += 2\n'),
    # PowerShell çift tırnak içi backtick kaçışı yok => Q6 KAÇAR; F2e FP döner.
    "--mutasyon-ps-tirnak-ici-backtick-yok": (
        '                    if q == \'"\' and ch == "`" and i + 1 < n:\n',
        '                    if False:\n'),
    # PowerShell tırnak dışı backtick kaçışı yok => Q13 KAÇAR. Tur-4: B7 artık DÜŞMEZ — token
    # ``-R`org/x`` kalır, değer sınıfı (`_GH_BITISIK_DEGER`) backtick'i reddeder (B7'yi
    # `--mutasyon-bitisik-metin-freni` ölçer).
    "--mutasyon-ps-tirnak-disi-backtick-yok": (
        '        if lehce == "ps" and c == "`" and i + 1 < n:\n            cur.append(',
        '        if False:\n            cur.append('),
    # F3: yol çözümleme istisnası yakalanmaz => F3, F3c ÇÖKER (fail-open).
    "--mutasyon-yol-istisnasi-yakalanmaz": (
        "    except (OSError, ValueError):\n        return \"cozulemedi\", cwd\n",
        "    except KeyError:\n        return \"cozulemedi\", cwd\n"),
}

S = "SIZINTI" + "-SENTINEL"
BS, BT = chr(92), chr(96)
KQ = "'" + BS + "''"          # Bash `'\''`
PR, CM, GH = "PUBLIC-PR SIZINTI GATE", "COMMIT-MESAJI SIZINTI GATE", "GH HEDEF BELİRSİZ"

# (ad, proje: "pub"|"priv", tool, komut, beklenen: imza | 0)
# Komutlarda <PUB>/<PRIV> = kumdaki gerçek dizinler (POSIX eğik çizgi), <ROOT> = üstleri.
VEKTORLER = [
    # ── M: maskeleme — gerçek PUBLIC hedef, metinde private hedef ─────────────
    ("M1 baslikta --repo private ONCE, gercek --repo public", "pub", "Bash",
     f"gh pr create --title 'bkz --repo org/private-proj' --repo org/public-core --body '{S}'", PR),
    ("M1b --repo= bicimi, cift tirnak", "pub", "Bash",
     f'gh pr create --title "bkz --repo=org/private-proj" --repo=org/public-core --body "{S}"', PR),
    ("M1c -b govdede once", "pub", "Bash",
     f"gh pr create -t t -b 'x --repo org/private-proj {S}' --repo org/public-core", PR),
    ("M1d issue comment", "pub", "Bash",
     f"gh issue comment 5 --body 'bkz --repo org/private-proj {S}' --repo org/public-core", PR),
    ("M1e -R gercek + metinde --repo private", "priv", "Bash",
     f"gh pr create -t 'bkz --repo org/private-proj' -R org/public-core -b '{S}'", PR),
    ("M1f 3.BAGLAM PowerShell", "pub", "PowerShell",
     f"gh pr create --title 'bkz --repo org/private-proj' --repo org/public-core --body '{S}'", PR),
    ("M1g 3.BAGLAM --body-file heredoc + baslikta --repo private", "priv", "Bash",
     f"gh pr create --title 'bkz --repo org/private-proj' --repo org/public-core "
     f"--body-file - <<'B'\n{S}\nB", PR),
    ("M1h 3.BAGLAM $(cat) govde + baslikta --repo private", "priv", "Bash",
     f"gh pr create --title 'bkz --repo org/private-proj' --repo org/public-core "
     f"--body \"$(cat <<'EOF'\n{S}\nEOF\n)\"", PR),
    ("M1i release --notes + metinde --repo private", "priv", "Bash",
     f"gh release create v1 --title 'bkz --repo org/private-proj' --notes '{S}' "
     f"--repo org/public-core", PR),
    ("M2 commit mesajinda cd <private>, cwd public", "pub", "Bash",
     f"git commit -m 'not: cd <PRIV> sonra {S}'", CM),
    ("M2b gh -R public + baslikta cd <private>", "priv", "Bash",
     f"gh pr create -R org/public-core -t 'cd <PRIV>' -b '{S}'", PR),
    ("M2c 3.BAGLAM $(cat) mesajda cd <private>, cwd public", "pub", "Bash",
     f"git commit -m \"$(cat <<'EOF'\nbaslik\n\ncd <PRIV>\n{S}\nEOF\n)\"", CM),
    ("M3 commit mesajinda --repo private, cwd public", "pub", "Bash",
     f"git commit -m 'bkz --repo org/private-proj {S}'", CM),
    ("M3b mesajda yeni satir + git -C <private>", "pub", "Bash",
     f"git commit -m 'baslik\ngit -C <PRIV> log {S}'", CM),
    ("M3c cd public && commit, mesajda --repo private", "priv", "Bash",
     f"cd <PUB> && git commit -m 'bkz --repo org/private-proj {S}'", CM),
    ("M3d -F heredoc + -m'de --repo private", "pub", "Bash",
     f"git commit -m 'bkz --repo=org/private-proj' -F - <<'M'\n{S}\nM", CM),
    ("M3e 3.BAGLAM PowerShell commit mesajinda --repo private", "pub", "PowerShell",
     f"git commit -m 'bkz --repo org/private-proj {S}'", CM),
    ("M4 -R public, proje koku private", "priv", "Bash",
     f"gh pr create -R org/public-core -t t -b '{S}'", PR),
    ("M4b -Rorg/public bitisik", "priv", "Bash",
     f"gh pr create -Rorg/public-core -t t -b '{S}'", PR),
    ("M4c -R=org/public", "priv", "Bash", f"gh pr create -R=org/public-core -t t -b '{S}'", PR),
    ("M4d issue comment -R public", "priv", "Bash",
     f"gh issue comment 5 -R org/public-core --body '{S}'", PR),
    ("M4e -dR kume + --repo private (iki deger: fail-closed)", "priv", "Bash",
     f"gh pr create -dR org/public-core -t t -b '{S}' --repo org/private-proj", PR),
    ("M4f iki --repo, ikincisi public", "priv", "Bash",
     f"gh pr create --repo org/private-proj --repo org/public-core -t t -b '{S}'", PR),
    ("M5 GIT_DIR public, cwd private", "priv", "Bash",
     f"GIT_DIR=<PUB>/.git git commit -m '{S}'", CM),
    ("M5b --git-dir= public, cwd private", "priv", "Bash",
     f"git --git-dir=<PUB>/.git commit -m '{S}'", CM),
    ("M5c --work-tree public, cwd private", "priv", "Bash",
     f"git --work-tree <PUB> commit -m '{S}'", CM),
    ("M5d git -C goreli (cd baglami + alt dizin public)", "priv", "Bash",
     f"cd <ROOT> && git -C public-core commit -m '{S}'", CM),
    # ── K: kontroller ────────────────────────────────────────────────────────
    ("K1 --repo public", "priv", "Bash", f"gh pr create --repo org/public-core -t t -b '{S}'", PR),
    ("K2 --repo private, cwd public", "pub", "Bash",
     f"gh pr create --repo org/private-proj -t t -b '{S}'", 0),
    ("K3 commit cwd public", "pub", "Bash", f"git commit -m '{S}'", CM),
    ("K4 commit cwd private", "priv", "Bash", f"git commit -m '{S}'", 0),
    ("K5 cd private && commit (cwd public)", "pub", "Bash", f"cd <PRIV> && git commit -m '{S}'", 0),
    ("K6 cd public && commit (cwd private)", "priv", "Bash", f"cd <PUB> && git commit -m '{S}'", CM),
    ("K7 git -C private commit (cwd public)", "pub", "Bash", f"git -C <PRIV> commit -m '{S}'", 0),
    ("K8 git -C public commit (cwd private)", "priv", "Bash", f"git -C <PUB> commit -m '{S}'", CM),
    ("K9 gh api repos/public", "priv", "Bash", f"gh api repos/org/public-core/issues -f body='{S}'", PR),
    ("K10 cd public && gh api repos/private (yol kazanir)", "priv", "Bash",
     f"cd <PUB> && gh api repos/org/private-proj/issues -f body='{S}'", 0),
    ("K11 -R private, cwd public — mevcut FP KALIR (eski aday)", "pub", "Bash",
     f"gh pr create -R org/private-proj -t t -b '{S}'", PR),
    ("K12 temiz govde --repo public", "priv", "Bash", "gh pr create --repo org/public-core -t t -b temiz", 0),
    ("K13 metinde --repo public ONCE, gercek private — mevcut FP KALIR", "priv", "Bash",
     f"gh pr create --title 'bkz --repo org/public-core' --repo org/private-proj --body '{S}'", PR),
    ("K14 mesajda cd <public>, cwd private — mevcut FP KALIR", "priv", "Bash",
     f"git commit -m 'not: cd <PUB> {S}'", CM),
    ("K15 metinde ve gercekte private, cwd public", "pub", "Bash",
     f"gh pr create --title 'bkz --repo org/private-proj' --repo org/private-proj --body '{S}'", 0),
    ("K16 private proje, mesajda --repo private", "priv", "Bash",
     f"git commit -m 'bkz --repo org/private-proj {S}'", 0),
    # ── T: aday tavani ────────────────────────────────────────────────────────
    ("T1 alti private --repo adayi -> FAIL-CLOSED", "priv", "Bash",
     "gh pr create " + " ".join(f"--repo org/private-{n}" for n in range(6)) + f" -t t -b '{S}'",
     "aday-tavani"),
    # ── H: GH-HEDEF ──────────────────────────────────────────────────────────
    ("H1 baslikta --repo, gercek hedef yok", "priv", "Bash", "gh pr create -t 'bkz --repo org/x' -b b", GH),
    ("H2 pr merge subject'te -R", "priv", "Bash", "gh pr merge 5 --squash --subject 'x -R org/x'", GH),
    ("H3 repo edit description'da org/x", "priv", "Bash", "gh repo edit --description 'bkz org/x'", GH),
    ("H4 -r reviewer (buyuk/kucuk harf)", "priv", "Bash", "gh pr create -r someone -t t -b b", GH),
    ("H5 -Rorg/x bitisik (GEVSETME: FP kalkar)", "priv", "Bash", "gh pr create -Rorg/x -t t -b b", 0),
    ("H6 -R=org/x", "priv", "Bash", "gh pr create -R=org/x -t t -b b", 0),
    ("H7 -dR kume (eskisi gibi BLOK)", "priv", "Bash", "gh pr create -dR org/x -t t -b b", GH),
    ("H7b -dR kume + baslikta '-R y' (metin freni tutar, kume filtresi bloklar)", "priv", "Bash",
     "gh pr create -dR org/x -t '-R y' -b b", GH),
    ("H8 -tRelease = baslik, hedef DEGIL", "priv", "Bash", "gh pr create -tRelease -b b", GH),
    ("H9 body'de tirnakli --repo", "priv", "Bash", 'gh pr comment 5 --body "--repo org/x"', GH),
    ("H10 commit mesajinda gh satiri + --repo (eskisi gibi GECER)", "priv", "Bash",
     'git commit -m "x\ngh pr create --repo org/x"', 0),
    ("H11 repo edit konumsal", "priv", "Bash", "gh repo edit org/x --description d", 0),
    ("H12 repo create URL (eskisi gibi BLOK)", "priv", "Bash", "gh repo create https://github.com/org/x", GH),
    ("H13 3.BAGLAM PowerShell baslikta --repo", "priv", "PowerShell",
     "gh issue create --title 'bkz --repo org/x' --body b", GH),
    ("H14 repo delete --yes konumsal", "priv", "Bash", "gh repo delete --yes org/x", 0),
    ("H15 --repo gercek + baslikta -R metni", "priv", "Bash", "gh pr create --repo org/x -t 'bkz -R org/y' -b b", 0),
    ("H16 subject tamamen '-R org/x' (bosluklu token)", "priv", "Bash",
     'gh pr merge 5 --squash --subject "-R org/x"', GH),
    ("H17 konumsal \"-R org/x\" (bosluklu deger, main GECIRIYORDU)", "priv", "Bash",
     'gh pr merge 5 --squash "-R org/x"', GH),
    # ── Q: kabuk lehçesi (bug-gate 2026-10-14, iki kol) ─────────────────────
    ("Q1 kol a: commit -m 'it'\\''s <iz>'", "pub", "Bash", f"git commit -m 'it{KQ}s {S}'", CM),
    ("Q2 kol b: -b 'it'\\''s <iz>'", "priv", "Bash",
     f"gh pr create --repo org/public-core -t t -b 'it{KQ}s {S}'", PR),
    ("Q3 kol b: --body 'main'\\''e <iz>'", "priv", "Bash",
     f"gh pr create --repo org/public-core --title t --body 'main{KQ}e {S}'", PR),
    ("Q4 ANSI-C -m $'it\\'s <iz>'", "pub", "Bash", f"git commit -m $'it{BS}'s {S}'", CM),
    ("Q5 3.BAGLAM PowerShell 'it''s' (kontrol: eskisi gibi)", "pub", "PowerShell",
     f"git commit -m 'it''s {S}'", CM),
    ("Q6 3.BAGLAM PowerShell cift tirnak icinde backtick", "priv", "PowerShell",
     f'gh pr create --repo org/public-core -t t -b "a {BT}" {S}"', PR),
    ("Q7 Bash cift tirnak \\\" (kontrol: eskisi gibi)", "priv", "Bash",
     f'gh pr create --repo org/public-core -t t -b "x {BS}" {S}"', PR),
    ("Q10 ilk eslesme: --title 'bkz --body x' --body <iz>", "priv", "Bash",
     f"gh pr create --repo org/public-core --title 'bkz --body x' --body '{S}'", PR),
    ("Q11 ilk eslesme: --title \"bkz -b x\" -b <iz>", "priv", "Bash",
     f'gh pr create --repo org/public-core --title "bkz -b x" -b "{S}"', PR),
    ("Q12 ilk eslesme: release --notes", "priv", "Bash",
     f"gh release create v1 --repo org/public-core --title 'bkz --notes x' --notes '{S}'", PR),
    ("Q13 3.BAGLAM PowerShell tirnak disi backtick-bosluk", "priv", "PowerShell",
     f"gh pr create --repo org/public-core -t t -b x{BT} {S}", PR),
    ("Q14 --body-file iki kez (ikisi de stdin)", "priv", "Bash",
     f"gh pr create --repo org/public-core -t t --body-file - --body-file - <<'B'\n{S}\nB", PR),
    # ── F1: bayrak DEĞERİ açık hedef değil ─────────────────────────────────
    ("F1a -t \"--repo\"", "priv", "Bash", 'gh pr create -t "--repo" -b b', GH),
    ("F1b -t '-R'", "priv", "Bash", "gh pr create -t '-R' -b b", GH),
    ("F1c comment --body \"-Rorg/x\"", "priv", "Bash", 'gh pr comment 5 --body "-Rorg/x"', GH),
    ("F1d merge --subject \"-Rorg/x\"", "priv", "Bash",
     'gh pr merge 5 --squash --subject "-Rorg/x"', GH),
    ("F1e close -c \"--repo\" --delete-branch", "priv", "Bash",
     'gh pr close 5 -c "--repo" --delete-branch', GH),
    ("F1f release -n \"-R\"", "priv", "Bash", 'gh release create v1 -n "-R" -t t', GH),
    ("F1g comment --body '--repo' --edit-last", "priv", "Bash",
     "gh pr comment 5 --body '--repo' --edit-last", GH),
    ("F1h -t --repo org/x (deger --repo'yu yutar; main GECIRIYORDU)", "priv", "Bash",
     "gh pr create -t --repo org/x -b b", GH),
    # ── F2: kaçışlı başlık FP üretmez ──────────────────────────────────────
    ("F2a --title 'PR'\\''i duzelt' --repo", "priv", "Bash",
     f"gh pr create --title 'PR{KQ}i duzelt' --repo org/x --body x", 0),
    ("F2b -t 'main'\\''e gore' --repo sonda", "priv", "Bash",
     f"gh pr create -t 'main{KQ}e gore' -b b --repo org/x", 0),
    ("F2c -t $'it\\'s' --repo", "priv", "Bash", f"gh pr create -t $'it{BS}'s' -b b --repo org/x", 0),
    ("F2d repo edit --description 'main'\\''e' org/x", "priv", "Bash",
     f"gh repo edit --description 'main{KQ}e' org/x", 0),
    ("F2e 3.BAGLAM PowerShell -t \"a `\" b\" --repo", "priv", "PowerShell",
     f'gh pr create -t "a {BT}" b" -b b --repo org/x', 0),
    ("F2f 3.BAGLAM PowerShell 'it''s' --repo", "priv", "PowerShell",
     "gh pr create -t 'it''s' -b b --repo org/x", 0),
    ("F2g Windows yolu --body-file C:\\IX\\… (eskisi gibi)", "priv", "Bash",
     f"gh pr create -t t --body-file C:{BS}IX{BS}yok.md --repo org/x", 0),
    # ── P1 · F3 · U · B ───────────────────────────────────────────────────
    ("P1 kok public, -t \"--repo=org/private\" (GH-HEDEF katmani)", "pub", "Bash",
     f"gh pr create -t \"--repo=org/private-proj\" -b '{S}'", GH),
    ("P1L KATMAN: sizinti gate'i dogrudan — kesin hedef yok => cwd aday", "pub", "Bash:pr-gate",
     f"gh pr create -t \"--repo=org/private-proj\" -b '{S}'", PR),
    ("F3 GIT_DIR=<KILITLI> (is_dir istisnasi) ; cd public && commit", "priv", "Bash",
     f"GIT_DIR=<KILITLI> git commit -m x ; cd <PUB> && git commit -m '{S}'", CM),
    ("F3c cd <KILITLI> && commit => hedef cozulemedi FAIL-CLOSED public", "priv", "Bash",
     f"cd <KILITLI> && git commit -m '{S}'", CM),
    ("U1 tabloda olmayan alt-komut (bayatlik gevsetmez)", "priv", "Bash",
     "gh ruleset delete 123 --repo org/x", GH),
    ("U2 tanınmayan bayrak (bayatlik gevsetmez)", "priv", "Bash",
     "gh pr create --yeni-bayrak v --repo org/x -t t -b b", GH),
    ("U3 bilinen bayraklar (kontrol)", "priv", "Bash", "gh pr create --repo org/x -t t -b b --draft", 0),
    ("B3 3.BAGLAM PowerShell --re`po (metinde gorunmeyen hedef: eskisi gibi BLOK)", "priv",
     "PowerShell", f"gh pr create --re{BT}po org/x -t t -b b", GH),
    ("B4 repo edit --description org/x (deger, hedef DEGIL)", "priv", "Bash",
     "gh repo edit --description org/x", GH),
    # ── tur-3: bitişik muafiyeti muafiyeti DOĞURAN token'a bağlı (main BLOK, metin freni geçirirdi)
    ("B5 \"--repo\" org/x + baslikta '-Rx' (main BLOK; onaysiz gevseme olmaz)", "priv", "Bash",
     "gh pr create \"--repo\" org/x -t '-Rx' -b b", GH),
    ("B6 3.BAGLAM PowerShell --re`po org/x + baslikta '-Rfoo' (main BLOK)", "priv", "PowerShell",
     f"gh pr create --re{BT}po org/x -t '-Rfoo' -b b", GH),
    ("B7 3.BAGLAM PowerShell -R`org/x (metinde -Rorg/x yok; main BLOK)", "priv", "PowerShell",
     f"gh pr create -R{BT}org/x -t t -b b", GH),
    ("B8 \"-Rorg/x\" tek token (onayli bitisik bicim, kontrol)", "priv", "Bash",
     "gh pr create -t t -b b \"-Rorg/x\"", 0),
    ("M6 -t -R <public> --repo <private> (fazla aday: bayat tabloya sigorta)", "priv", "Bash",
     f"gh pr create -t -R org/public-core -b '{S}' --repo org/private-proj", PR),
    # ── Y (tur-4): kabuğun gh'ye ARGÜMAN olarak geçirmediği metin hedef/aday üretmez ──────
    # (yorum · yönlendirme işleneni · `\<boşluk>`). Ölçülen main (f762cf6) / önceki tur (0324d2b):
    # Y1–Y19 main BLOK / önceki tur GEÇER (Bulgu-1 · tuzak) · Y20/Y21 (O3) ikisinde de BLOK ·
    # Y22–Y26 main GEÇER / önceki tur GEÇER (G10 · çok satır) · Y27–Y32 sızıntı gate'i ikisinde de
    # TARAMIYORDU (Bulgu-2) · Y33 ikisinde de rc 0. YK: YK11–YK13/YK25 main BLOK (onaylı bitişik
    # gevşeme), kalan YK üçünde de aynı sonuç.
    ("Y1 bash yorum # -Rorg/x (release delete)", "priv", "Bash",
     "gh release delete v1 --yes # -Rorg/x", GH),
    ("Y2 bash <<< -Rorg/x (here-string isleneni)", "priv", "Bash",
     "gh pr create -t x -b b <<< -Rorg/x", GH),
    ("Y3 bash -t \\<bosluk>-Rorg/x (kacisli bosluk degerin parcasi)", "priv", "Bash",
     f"gh pr create -t {BS} -Rorg/x -b b", GH),
    ("Y4 3.BAGLAM PowerShell yorum # -Rorg/x", "priv", "PowerShell",
     "gh pr create -t x -b b # -Rorg/x", GH),
    ("Y5 bash -H\\<bosluk>-Rorg/x (head degeri)", "priv", "Bash",
     f"gh pr create -H{BS} -Rorg/x -t x -b b", GH),
    ("Y6 bash issue close yorum", "priv", "Bash", "gh issue close 5 # -Rorg/x", GH),
    ("Y7 bash < -Rorg/x", "priv", "Bash", "gh pr create -t x -b b < -Rorg/x", GH),
    ("Y8 bash > -Rorg/x", "priv", "Bash", "gh pr create -t x -b b > -Rorg/x", GH),
    ("Y9 bash fd: -t 2>x -Rorg/x (-t degeri -Rorg/x olur)", "priv", "Bash",
     "gh pr create -t 2>x -Rorg/x -b b", GH),
    ("Y10 3.BAGLAM PowerShell blok yorum <# -Rorg/x #>", "priv", "PowerShell",
     "gh pr create -t x -b b <# -Rorg/x #>", GH),
    ("Y11 3.BAGLAM PowerShell > -Rorg/x", "priv", "PowerShell",
     "gh pr create -t x -b b > -Rorg/x", GH),
    ("Y12 3.BAGLAM PowerShell 2> -Rorg/x", "priv", "PowerShell",
     "gh pr create -t x -b b 2> -Rorg/x", GH),
    ("Y15 tuzak: -R''org/x + yorumda -Rorg/x", "priv", "Bash",
     "gh pr create -R''org/x -t x -b b # -Rorg/x", GH),
    ("Y16 tuzak: -R''org/x + baslikta ' -Rorg/x'", "priv", "Bash",
     "gh pr create -R''org/x -t ' -Rorg/x' -b b", GH),
    ("Y17 tuzak: -R\"org/x\" + <<< -Rorg/x", "priv", "Bash",
     "gh pr create -R\"org/x\" -t x -b b <<< -Rorg/x", GH),
    ("Y18 -R\\org/x (deger duz degil; main BLOK)", "priv", "Bash",
     f"gh pr create -R{BS}org/x -t x -b b", GH),
    ("Y19 -R$REPO (ikame; main BLOK)", "priv", "Bash", "gh pr create -R$REPO -t x -b b", GH),
    ("Y20 O3 bash -R''org/x (metin sarti, B7 esdegeri)", "priv", "Bash",
     "gh pr create -R''org/x -t t -b b", GH),
    ("Y21 O3 bash -R\"org/x\"", "priv", "Bash", "gh pr create -R\"org/x\" -t t -b b", GH),
    ("Y22 G10 yorumda --repo org/x (main GECIRIYORDU)", "priv", "Bash",
     "gh release delete v1 --yes # --repo org/x", GH),
    ("Y23 G10 pr create yorumda --repo", "priv", "Bash", "gh pr create -t x -b b # --repo org/x", GH),
    ("Y24 G10 repo delete yorumda konumsal org/x", "priv", "Bash", "gh repo delete --yes # org/x", GH),
    ("Y25 G10 repo edit <<< org/x (isleneni konumsal degil)", "priv", "Bash",
     "gh repo edit -d x <<< org/x", GH),
    ("Y26 cok satir: yorumdaki apostrof sonraki satirin gh'sini yutmaz", "priv", "Bash",
     "gh pr create --repo org/x -t x -b b # it's\ngh pr create -t y -b \"c'\"", GH),
    ("Y27 KATMAN Bulgu-2 yorumda -R<private>, kok public", "pub", "Bash:pr-gate",
     f"gh pr create -t x -b '{S} bkz --repo org/private-proj' # -Rorg/private-proj", PR),
    ("Y28 KATMAN Bulgu-2 yorumda --repo <private>", "pub", "Bash:pr-gate",
     f"gh pr create -t x -b '{S} bkz --repo org/private-proj' # --repo org/private-proj", PR),
    ("Y29 KATMAN Bulgu-2 \\<bosluk>-R<private>", "pub", "Bash:pr-gate",
     f"gh pr create -t {BS} -Rorg/private-proj -b '{S} bkz --repo org/private-proj'", PR),
    ("Y30 KATMAN Bulgu-2 <<< -R<private>", "pub", "Bash:pr-gate",
     f"gh pr create -t x -b '{S} bkz --repo org/private-proj' <<< -Rorg/private-proj", PR),
    ("Y31 KATMAN 3.BAGLAM PowerShell Bulgu-2 yorum", "pub", "PowerShell:pr-gate",
     f"gh pr create -t x -b '{S} bkz --repo org/private-proj' # -Rorg/private-proj", PR),
    ("Y32 KATMAN Bulgu-2 issue comment yorum", "pub", "Bash:pr-gate",
     f"gh issue comment 5 -b '{S} --repo org/private-proj' # -Rorg/private-proj", PR),
    ("Y33 Bulgu-2 main() ucu: GH-HEDEF bloklar", "pub", "Bash",
     f"gh pr create -t x -b '{S} bkz --repo org/private-proj' # -Rorg/private-proj", GH),
    # ── YK (tur-4 kontrol): yaygın yönlendirme / tırnak içi `#` / onaylı biçim — FP YOK ──
    ("YK1 --repo + 2>&1", "priv", "Bash", "gh pr create --repo org/x -t x -b b 2>&1", 0),
    ("YK2 --repo + > out.txt", "priv", "Bash", "gh pr create --repo org/x -t x -b b > out.txt", 0),
    ("YK3 --repo + 2>/dev/null | tee", "priv", "Bash",
     "gh pr create --repo org/x -t x -b b 2>/dev/null | tee log", 0),
    ("YK4 3.BAGLAM PowerShell --repo + 2>$null", "priv", "PowerShell",
     "gh pr create --repo org/x -t x -b b 2>$null", 0),
    ("YK5 3.BAGLAM PowerShell --repo + *>$null", "priv", "PowerShell",
     "gh pr create --repo org/x -t x -b b *>$null", 0),
    ("YK6 --body-file - + heredoc", "priv", "Bash",
     "gh pr create --repo org/x -t x --body-file - <<'B'\nhi\nB", 0),
    ("YK7 tirnak ici # (baslik/govde)", "priv", "Bash",
     "gh pr create --repo org/x -t 'Fix #12' -b \"issue #5\"", 0),
    ("YK8 3.BAGLAM PowerShell tirnak ici #", "priv", "PowerShell",
     "gh pr create --repo org/x -t 'Fix #12' -b \"issue #5\"", 0),
    ("YK9 URL ici #", "priv", "Bash",
     "gh pr create --repo org/x -t x -b https://github.com/org/x/pull/1#issuecomment-1", 0),
    ("YK10 tirnak ici > (--title \"a > b\")", "priv", "Bash",
     "gh pr create --repo org/x --title \"a > b\" -b b", 0),
    ("YK11 onayli bitisik + 2>&1", "priv", "Bash", "gh pr create -Rorg/x -t x -b b 2>&1", 0),
    ("YK12 onayli bitisik + > out + yorum", "priv", "Bash",
     "gh pr create -Rorg/x -t x -b b > out.txt # not", 0),
    ("YK13 3.BAGLAM PowerShell onayli bitisik + 2>$null + blok yorum", "priv", "PowerShell",
     "gh pr create -Rorg/x -t x -b b 2>$null <# not #>", 0),
    ("YK25 3.BAGLAM PowerShell blok yorumdan SONRAKI arguman gercektir", "priv", "PowerShell",
     "gh pr create -t x <# not #> -b b -Rorg/x", 0),
    ("YK14 repo delete konumsal + 2>&1", "priv", "Bash", "gh repo delete --yes org/x 2>&1", 0),
    ("YK15 repo edit konumsal + > /dev/null", "priv", "Bash",
     "gh repo edit org/x --description d > /dev/null", 0),
    ("YK16 tirnaksiz a#b (yorum degil)", "priv", "Bash", "gh pr create --repo org/x -t a#b -b b", 0),
    ("YK17 \\# kacisi (yorum degil)", "priv", "Bash", f"gh pr create --repo org/x -t x -b {BS}#5", 0),
    ("YK18 cok satir yorumdaki apostrof + okuma komutu", "priv", "Bash",
     "gh pr create --repo org/x -t x -b b # it's ok\ngh pr list", 0),
    ("YK19 3.BAGLAM PowerShell kelime ortasi > yonlendirme DEGIL", "priv", "PowerShell",
     "gh pr create --repo org/x -t a>b -b b", 0),
    ("YK20 -R org/x + 2>err (kisa bicim)", "priv", "Bash", "gh pr create -R org/x -t x -b b 2>err.txt", 0),
    ("YK21 notes tirnak ici '> #' + 1>/dev/null", "priv", "Bash",
     "gh release create v1 --repo org/x --notes 'a > b # c' 1>/dev/null", 0),
    ("YK22 sizinti: public hedef + 2>&1 => govde TARANIR", "pub", "Bash",
     f"gh pr create --repo org/public-core -t x -b '{S}' 2>&1", PR),
    ("YK23 sizinti: commit + > /dev/null 2>&1 => mesaj TARANIR", "pub", "Bash",
     f"git commit -m '{S}' > /dev/null 2>&1", CM),
    ("YK24 sizinti: commit mesajinda tirnak ici # (kok private)", "priv", "Bash",
     f"git commit -m 'Fix #12 {S}' 2>&1", 0),
]

_SURUCU = r'''
import importlib.util, io, json, sys, subprocess as sp, types
from pathlib import Path
guard, vek_yolu = sys.argv[1:3]
gercek = sp.run
CAGRI = []
def sahte(argv, *a, **k):
    if isinstance(argv, (list, tuple)) and list(argv[:3]) == ["gh", "repo", "view"]:
        hedef = str(argv[3]) if len(argv) > 3 and not str(argv[3]).startswith("-") else ""
        cwd = str(k.get("cwd") or "")
        pub = ("public" in hedef.lower()) if hedef else ("public" in Path(cwd).name.lower())
        CAGRI.append(hedef or "cwd")
        return types.SimpleNamespace(returncode=0, stderr="", stdout=json.dumps(
            {"isPrivate": not pub, "nameWithOwner": hedef or Path(cwd).name}))
    return gercek(argv, *a, **k)
sp.run = sahte
spec = importlib.util.spec_from_file_location("ptg_hedef_maske", guard)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
S = "SIZINTI" + "-SENTINEL"
m.sizintilari_bul = lambda metin, desen: [(S, "yapay-kategori")] if S in (metin or "") else []
out = []
for v in json.load(open(vek_yolu, encoding="utf-8")):
    m._PROJ_ROOT = Path(v["proje"])
    del CAGRI[:]
    e = io.StringIO(); ge, gi = sys.stderr, sys.stdin
    sys.stderr, sys.stdin = e, io.StringIO(json.dumps(
        {"tool_name": v["tool"], "tool_input": {"command": v["komut"]}}))
    try:
        if v["tool"].endswith(":pr-gate"):    # KATMAN vektoru: yalniz sizinti gate'i
            m._GORUNURLUK.clear()
            lehce = "ps" if v["tool"].startswith("PowerShell") else "bash"
            sorun = m._iki_lehce(lehce, m._gh_pr_public_leak, v["komut"], v["komut"])
            e.write(("PUBLIC-PR SIZINTI GATE: " + sorun) if sorun else "")
            rc = 2 if sorun else 0
        else:
            rc = m.main()
    except BaseException as x:
        rc = "COKTU:" + repr(x)[:80]
    finally:
        sys.stderr, sys.stdin = ge, gi
    out.append({"rc": rc, "err": e.getvalue(), "cagri": list(CAGRI)})
sys.stdout.write("<<SONUC>>" + json.dumps(out))
'''


def _sil(d: Path) -> None:
    """Q319: Windows'ta salt-okur girdi `rmtree(ignore_errors=True)` ile SESSIZCE kalir."""
    def _ac(func, path, _exc):                       # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)                       # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def main() -> int:
    gecerli = set(MUTLAR)
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in gecerli:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + " ".join(sorted(gecerli)))
    secili = next((a for a in sys.argv[1:] if a in gecerli), None)

    tmp = Path(tempfile.mkdtemp(prefix="hedef_maske_"))
    sonuc: list = []
    try:
        if ("public" in str(tmp).lower() or "private" in str(tmp).lower()
                or any(c.isspace() for c in str(tmp))):
            print(f"[DOGRULANAMADI] gecici yol gorunurluk taklidini bozar: {tmp}")
            return 2
        kum = tmp / "kum"
        (kum / "scripts" / "hooks").mkdir(parents=True)
        shutil.copy2(SCRIPTS / "genericize_common.py", kum / "scripts")
        ptg = kum / "scripts" / "hooks" / "pre_tool_guard.py"
        shutil.copy2(SCRIPTS / "hooks" / "pre_tool_guard.py", ptg)
        if secili:
            eski, yeni = MUTLAR[secili]
            kaynak = ptg.read_bytes().decode("utf-8").replace("\r\n", "\n")
            if kaynak.count(eski) != 1:
                print(f"[DOGRULANAMADI] mutasyon capasi {kaynak.count(eski)} kez bulundu "
                      f"({secili}) -> mutasyon UYGULANMADI; 'gecti' sonucu ANLAMSIZ olurdu.")
                return 2
            ptg.write_bytes(kaynak.replace(eski, yeni, 1).encode("utf-8"))
            try:
                compile(ptg.read_text(encoding="utf-8"), str(ptg), "exec")
            except SyntaxError as e:
                print(f"[DOGRULANAMADI] mutant SOZDIZIMI BOZUK ({secili}): {e}")
                return 2

        root = tmp / "ws"
        pub, priv = root / "public-core", root / "private-proj"
        for d in (pub, priv):
            d.mkdir(parents=True)
        # F3: `Path.is_dir()` yalnız "yok" hatalarını yutar. Windows: sistem kilitli dosya;
        # POSIX: erişimi kapalı dizinin altı (root değilken EACCES). Ön-sınama: istisna
        # GERÇEKTEN atılmıyorsa F3 vektörleri ölçmez ⇒ DOĞRULANAMADI (sessiz yeşil yok).
        if os.name == "nt":
            kilitli = "C:/Windows/System32/config/SAM"
        else:
            kd = tmp / "kilitli"
            (kd / "alt").mkdir(parents=True)
            os.chmod(kd, 0)
            kilitli = (kd / "alt").as_posix()
        try:
            Path(kilitli).is_dir()
            print(f"[DOGRULANAMADI] is_dir istisna atmadi ({kilitli}) -> F3 vektorleri olcmez")
            return 2
        except (OSError, ValueError):
            pass
        yer = {"<PUB>": pub.as_posix(), "<PRIV>": priv.as_posix(), "<ROOT>": root.as_posix(),
               "<KILITLI>": kilitli}

        def coz(s: str) -> str:
            for k, v in yer.items():
                s = s.replace(k, v)
            return s

        vek = [{"proje": str(pub if p == "pub" else priv), "tool": tool, "komut": coz(k)}
               for _, p, tool, k, _ in VEKTORLER]
        vy = tmp / "vek.json"
        vy.write_text(json.dumps(vek, ensure_ascii=False), encoding="utf-8")
        calisma = tmp / "calisma"
        calisma.mkdir()
        env = dict(os.environ)
        for k in ("CLAUDE_PROJECT_DIR", "IX_GENERICIZE_BLOCKLIST"):
            env.pop(k, None)
        r = subprocess.run([sys.executable, "-", str(ptg), str(vy)], input=_SURUCU,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=240, env=env, cwd=str(calisma))
        if "<<SONUC>>" not in (r.stdout or ""):
            print(f"[DOGRULANAMADI] surucu sonuc uretmedi: {(r.stderr or r.stdout)[-400:]}")
            return 2
        cikti = json.loads(r.stdout.split("<<SONUC>>", 1)[1])
        for (ad, _, _, _, bek), c in zip(VEKTORLER, cikti):
            rc, err = c["rc"], c["err"] or ""
            if bek == 0:
                ok = rc == 0
                beklenti = "GECER (exit 0)"
            elif bek in (PR, CM):
                # Blok SIZINTI TARAMASINDAN gelmeli (bulgu turu stderr'de) — gorunurluk
                # sorulamadi fail-closed'u ya da baska kural ayni rc'yi verir, olcmez.
                ok = (rc == 2 and bek in err and "yapay-kategori" in err
                      and "FAIL-CLOSED" not in err and "gorunurluk-sorulamadi" not in err)
                beklenti = "BLOKLANIR + govde TARANDI"
            elif bek == "aday-tavani":
                ok = rc == 2 and "hedef-aday-tavani-asildi" in err and not c["cagri"]
                beklenti = "FAIL-CLOSED (aday tavani, gh SORULMADI)"
            else:
                ok = rc == 2 and bek in err
                beklenti = "BLOKLANIR (GH-HEDEF)"
            sonuc.append((f"{ad} -> {beklenti}", ok,
                          f"rc={rc} cagri={c['cagri']} err={err[-160:]!r}"))
    finally:
        if (tmp / "kilitli").exists():
            os.chmod(tmp / "kilitli", stat.S_IRWXU)
        _sil(tmp)

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    print(f"\n=== GUARD HEDEF MASKELEME (pre_tool_guard sizinti gate'leri + GH-HEDEF) "
          f"{'[' + secili + ']' if secili else '[taban]'} ===")
    for ad, ok, detay in sonuc:
        print(f"  [{'OK ' if ok else 'FAIL'}] {ad}" + (f"   -> {detay}" if not ok else ""))
    print(f"\n{gecen}/{len(sonuc)} OK")
    if secili:
        print(f"  (MUTASYON {secili} — dusmesi BEKLENEN vektorler var; "
              "tam skor 'mutasyon KACTI' demektir)")
    print(f"[kum-temizligi] kalan={'evet' if tmp.exists() else 'hayir'}")
    return 0 if sonuc and gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
