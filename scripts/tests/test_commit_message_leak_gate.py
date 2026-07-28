#!/usr/bin/env python3
# ENFORCES: C-LEAK-02  (ADR 0019 coverage binding)
"""test_commit_message_leak_gate.py — commit MESAJI public-sizinti taramasi.

VAKA (2026-07-28, fiilen yasandi): PUBLIC core reposu icin hazirlanan bir PR'in
GOVDESINDE proje obje adi vardi -> `_gh_pr_public_leak` YAKALADI, islem reddedildi.
Ama AYNI ad **commit MESAJINDA** da vardi ve o commit ZATEN PUSH EDILMISTI.
Temizlik `--amend` + `--force-with-lease` gerektirdi.

BOSLUK: iki koruma vardi, ikisi de bu yolu gormuyordu —
  * `core_precommit`     -> commit'in ICERIGINI (dosyalari) tarar, MESAJINI TARAMAZ
  * `_gh_pr_public_leak` -> yalniz `gh` YAYIN komutlarina bakar, `git commit`e bakmaz
Commit mesaji push'la PUBLIC repoya gider ve orada KALICIDIR.

NEDEN COMMIT ANINDA (push'ta degil): mesaji o an degistirmek BEDAVA; push'tan
sonra gecmisi yeniden yazmak gerekir ve baskasi cektiyse artik gec kalinmistir.

--- TEST SINIRI (bilincli tasarim) ---------------------------------------
Bu testin isi: **mesaj metni cikariliyor mu, tarayiciya veriliyor mu, bulguda
bloklaniyor mu** (= bu gate'in sorumlulugu).
Bu testin isi DEGIL: "hangi dize sizintidir" (= `genericize_common` sorumlulugu,
kendi yerinde test edilir).
Bu yuzden tarayici MONKEYPATCH'lenir. Ilk taslakta gercek bir Z-obje adi
kullanmayi denedim: (1) `ZSD001*` cekirdegin KENDI demo adi ve beyaz-listede ->
sizinti sayilmadi, 4 test bosuna kirmizi dondu; (2) sentetik bir Z adi yazmayi
denedim -> **genericize guard'i dosyayi reddetti** (dogru davranis: core PUBLIC).
Ders: bir korumayi test ederken once korumanin NEYI sizinti saydigini olc; ve
her bileseni KENDI sinirinda test et.

⚠ Son test KABLOLAMAYI denetler: fonksiyon dogru calissa bile dispatcher'a bagli
degilse koruma YOKTUR. Bu fonksiyon ilk yazildiginda gercekten kablosuz kalmisti
(Pyright "not accessed" ile yakalandi) — kod != kablolama.

Agsiz (offline) kosar.
"""
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "hooks"))

import pre_tool_guard as G  # noqa: E402

_SENTINEL = "SIZINTI-SENTINEL"      # tarayicinin "bulgu" sayacagi yapay isaret
_TEMIZ = "readback esitligi eklendi"

_GERCEK_TARAYICI = G.sizintilari_bul
_GERCEK_PUBLIC = G._repo_public_mu


def _kur(public: bool):
    """Tarayiciyi ve gorunurluk sorgusunu sabitle — ag/gh cagrisi YAPILMASIN."""
    G._repo_public_mu = lambda hay: (public, "org/CORE" if public else "org/PRIVATE")
    G.sizintilari_bul = lambda metin, desen: (
        [(_SENTINEL, "yapay-kategori")] if _SENTINEL in (metin or "") else []
    )


def _geri_al():
    G.sizintilari_bul = _GERCEK_TARAYICI
    G._repo_public_mu = _GERCEK_PUBLIC


def test_public_repo_m_bayragi_YAKALANIR():
    """ASIL REGRESYON: public repoda -m mesajindaki bulgu bloklanmali."""
    _kur(True)
    try:
        cmd = f"cd /c/core && git commit -m 'fix: {_SENTINEL} icin readback'"
        assert G._git_commit_public_leak(cmd, cmd) != "", \
            "public repoda commit mesajindaki bulgu YAKALANMADI"
    finally:
        _geri_al()


def test_public_repo_heredoc_YAKALANIR():
    """`git commit -F -` + heredoc — YASANAN VAKANIN birebir sekli."""
    _kur(True)
    try:
        cmd = "cd /c/core && git commit -q -F - <<'EOF'"
        ham = cmd + f"\ndocs(playbook): tuzak notu\n\nKaynak: {_SENTINEL} kolonu.\nEOF"
        assert G._git_commit_public_leak(cmd, ham) != "", \
            "heredoc commit mesajindaki bulgu YAKALANMADI (yasanan vakanin sekli)"
    finally:
        _geri_al()


def test_coklu_m_bayragi_hepsi_taranir():
    """`-m ... -m ...` — IKINCI mesaj da taranmali (baslik temiz, govde sizdirir)."""
    _kur(True)
    try:
        cmd = f"cd /c/core && git commit -m 'temiz baslik' -m 'govde {_SENTINEL}'"
        assert G._git_commit_public_leak(cmd, cmd) != "", "ikinci -m govdesi taranmadi"
    finally:
        _geri_al()


def test_git_C_hedefi_de_gorulur():
    """`git -C <yol> commit` — hedef `cd` onekiyle degil `-C` ile verilir."""
    _kur(True)
    try:
        cmd = f"git -C /c/core commit -m 'fix {_SENTINEL}'"
        assert G._git_commit_public_leak(cmd, cmd) != "", \
            "`git -C` ile verilen hedef gorulmedi"
    finally:
        _geri_al()


def test_PRIVATE_repo_BLOKLANMAZ():
    """Yanlis-pozitif koruma: private proje reposunda obje adi MESRUDUR."""
    _kur(False)
    try:
        cmd = f"git commit -m 'feat: {_SENTINEL} alanlari'"
        assert G._git_commit_public_leak(cmd, cmd) == "", \
            "private repoda blokladi — yanlis-pozitif (proje commit'leri obje adi ICERIR)"
    finally:
        _geri_al()


def test_temiz_mesaj_BLOKLANMAZ():
    """Public repoda bile bulgu yoksa gecmeli — gate gurultu yapmamali."""
    _kur(True)
    try:
        cmd = f"cd /c/core && git commit -m '{_TEMIZ}'"
        assert G._git_commit_public_leak(cmd, cmd) == "", "temiz mesaj bloklandi"
    finally:
        _geri_al()


def test_commit_DISI_komut_dokunulmaz():
    """`git log`/`git push`/`git show` bu gate'e girmemeli."""
    _kur(True)
    try:
        for cmd in (f"git log --oneline | grep {_SENTINEL}",
                    "cd /c/core && git push origin main",
                    f"git show HEAD -- {_SENTINEL}.abap"):
            assert G._git_commit_public_leak(cmd, cmd) == "", f"commit olmayan komut bloklandi: {cmd}"
    finally:
        _geri_al()


def test_mesajsiz_commit_BLOKLANMAZ():
    """-m/-F yok (editor acilacak) -> taranacak metin yok, durdurma."""
    _kur(True)
    try:
        cmd = "cd /c/core && git commit --amend --no-edit"
        assert G._git_commit_public_leak(cmd, cmd) == "", \
            "mesajsiz commit bloklandi — taranacak metin yokken durdurmamali"
    finally:
        _geri_al()


def test_stdin_cozulemezse_FAIL_CLOSED():
    """`-F -` var ama heredoc yok -> sessizce GECME, hata dondur."""
    _kur(True)
    try:
        cmd = "cd /c/core && git commit -F -"
        sonuc = G._git_commit_public_leak(cmd, cmd)
        assert sonuc != "" and "FAIL-CLOSED" in sonuc, \
            f"stdin cozulemedigi halde gecti (fail-open!) -> {sonuc!r}"
    finally:
        _geri_al()


def test_GIT_IMZA_SATIRLARI_ayiklanir():
    """`Co-Authored-By:` / `Claude-Session:` her commit'te ZORUNLU boilerplate.

    Bu gate ilk yazildiginda tam da bunu bloklamisti (kendi commit'imi durdurdu):
    trailer'daki adres 'kimlik izi' kategorisine takiliyordu. Boyle bir gate TUM
    core commit'lerini bloklar -> kapatilir -> koruma sifirlanir.
    **Gurultu yapan gate, olmayan gate'ten kotudur.**
    (Trailer'lar SATIR olarak duser; icerigi onemli degil, o yuzden burada
    ornek adres YAZMAYA gerek yok — core'a kimlik izi yazilamaz zaten.)
    """
    metin = "fix(tooling): readback esitligi\n\nCo-Authored-By: Bot\nClaude-Session: <url>\nson satir"
    sonuc = G._git_imza_satirlari_ayikla(metin)
    assert "Co-Authored-By" not in sonuc, "Co-Authored-By imza satiri ayiklanmadi"
    assert "Claude-Session" not in sonuc, "Claude-Session imza satiri ayiklanmadi"
    assert "readback esitligi" in sonuc and "son satir" in sonuc, \
        "imza ayiklama mesajin GERCEK icerigini de sildi"


def test_git_imza_satirlari_ayiklama_DAR_tutulmus():
    """Fazla ayiklama olmamali: anahtar SATIR BASINDA degilse dokunulmaz."""
    metin = "fix: Co-Authored-By alani hakkinda not\nbu satir Claude-Session: icerir ama govdede"
    sonuc = G._git_imza_satirlari_ayikla(metin)
    assert "Co-Authored-By alani hakkinda not" in sonuc, \
        "satir-basi olmayan anahtar ayiklandi — govde metni kayboluyor"


def test_IMZALI_commit_BLOKLANMAZ_uctan_uca():
    """Trailer'li gercek bir commit mesaji, sizinti yoksa gecmeli (yanlis-pozitif yok)."""
    _kur(True)
    try:
        cmd = "cd /c/core && git commit -q -F - <<'EOF'"
        ham = (cmd + f"\nfix(tooling): {_TEMIZ}\n\nCo-Authored-By: Bot\n"
               "Claude-Session: <url>\nEOF")
        assert G._git_commit_public_leak(cmd, ham) == "", \
            "imzali temiz commit bloklandi"
    finally:
        _geri_al()


def test_GERCEK_desenle_taraniyor():
    """Tarayiciya `_CORE_LEAK` deseni VERILMELI.

    Monkeypatch'li testler "bir tarayici cagriliyor" der; bu test hangi DESENIN
    verildigini sabitler. Biri gevsek/bos bir desene gecerse gate sessizce korur
    gorunur ama hicbir sey yakalamaz.
    """
    src = (_SCRIPTS / "hooks" / "pre_tool_guard.py").read_text(encoding="utf-8")
    m = re.search(r"def _git_commit_public_leak\(.*?\n(?=\ndef |\nclass |\n_)", src, re.S)
    assert m, "_git_commit_public_leak govdesi bulunamadi"
    assert "sizintilari_bul(metin, _CORE_LEAK)" in m.group(0), \
        "commit mesaji `_CORE_LEAK` deseniyle taranmiyor"


def test_DISPATCHER_A_BAGLI():
    """KABLOLAMA: dispatcher'da CAGRILIYOR ve `return 2` ile BLOKLUYOR."""
    src = (_SCRIPTS / "hooks" / "pre_tool_guard.py").read_text(encoding="utf-8")
    m = re.search(r"sorun\s*=\s*_git_commit_public_leak\(komut,\s*ham\)\s*\n"
                  r"\s*if sorun:(.*?)return 2", src, re.S)
    assert m, "_git_commit_public_leak dispatcher'da cagrilmiyor ya da `return 2` ile bloklamiyor"
    assert "COMMIT-MESAJI SIZINTI GATE" in m.group(1), \
        "blok mesaji yok — kullanici neden durduruldugunu anlayamaz"


def main() -> int:
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    hata = 0
    for t in testler:
        try:
            t()
            print(f"  [OK]   {t.__name__}")
        except AssertionError as e:
            hata += 1
            print(f"  [FAIL] {t.__name__}: {e}")
    print(f"\ncommit-mesaji sizinti gate: {len(testler) - hata}/{len(testler)} gecti")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
