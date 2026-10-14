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


def test_KUMELENMIS_kisa_bayrak_YAKALANIR():
    """AV-16 (2026-08-01 adversarial bug-avi): `git commit -am` gate'i ATLIYORDU.

    Kok: mesaj cikarici lookbehind'i (`(?<![\\w-])-m`) KUMELENMIS kisa bayragin
    (`-am`, `-qam`) icindeki `m`'yi reddediyordu -> mesaj HIC cikarilmadi -> taranacak
    metin yok -> gate bos dondu. "Metin bulunamadi" ile "metin temiz" ayni sonuca
    (GEC) dusuyordu. Kontrol grubu: ayni icerikle `-m` exit 2 veriyordu.
    """
    _kur(True)
    try:
        for cmd in (f"cd /c/core && git commit -am 'fix {_SENTINEL}'",
                    f"cd /c/core && git commit -qam '{_SENTINEL}'",
                    f"cd /c/core && git commit -m'{_SENTINEL}'",
                    f"cd /c/core && git commit --message='{_SENTINEL}'",
                    f"git -C /c/core commit -am '{_SENTINEL}'"):
            assert G._git_commit_public_leak(cmd, cmd) != "", \
                f"kumelenmis/uzun bayrak bicimi YAKALANMADI: {cmd}"
    finally:
        _geri_al()


def test_UZUN_file_bayragi_YAKALANIR():
    """AV-17: `--file` git'in uzun bicimidir; cikarici yalniz `-F`yi taniyordu."""
    _kur(True)
    try:
        for cmd in ("cd /c/core && git commit --file=yok-boyle.txt",
                    "cd /c/core && git commit --file yok-boyle.txt"):
            sonuc = G._git_commit_public_leak(cmd, cmd)
            assert sonuc != "" and "FAIL-CLOSED" in sonuc, \
                f"--file okunamadigi halde gecti (fail-open!): {cmd} -> {sonuc!r}"
    finally:
        _geri_al()


def test_git_DISI_kumelenmis_am_BLOKLANMAZ():
    """FP ekseni: `-am` bir kara-liste dizgesi DEGILDIR — git DISI komutta gecerse
    dokunulmaz. Sikilastirmanin bedeli mesru komutlari bloklamak OLMAMALI."""
    _kur(True)
    try:
        for cmd in (f"grep -am 3 '{_SENTINEL}' dosya.txt",
                    f"tar -am -cf arsiv.tar {_SENTINEL}/",
                    f"echo 'git commit -am {_SENTINEL}'"):
            assert G._git_commit_public_leak(cmd, cmd) == "", \
                f"git DISI baglamda bloklandi (yanlis-pozitif): {cmd}"
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


# Ajan imza satirlari — adres PARCADAN kurulur (bu dosya e-posta desenine taranir).
_ATIF = "Co-Authored-By: Claude Opus 5.5 (1M context) <" + "noreply" + "@" + "anthropic.com>"
_OTURUM = "Claude-Session: https://claude.ai/code/session_01AbCdEf"
_URETICI = "\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)"


def test_GIT_IMZA_SATIRLARI_ayiklanir():
    """Ajanin UC imza satiri (atif · oturum · uretici) her ajan commit'inde ZORUNLU.

    Bu gate ilk yazildiginda tam da bunu bloklamisti (kendi commit'imi durdurdu):
    trailer'daki adres 'kimlik izi' kategorisine takiliyordu. Boyle bir gate TUM
    core commit'lerini bloklar -> kapatilir -> koruma sifirlanir.
    **Gurultu yapan gate, olmayan gate'ten kotudur.**

    bug-gate F3 (2026-10-14): atif satiri BOSALTILMAZ — yalniz uretici adresi silinir, ad
    bolumu TARANIR (ad bolumune yazilan obje/paket adi eskiden taramadan geciyordu).
    """
    metin = f"fix(tooling): readback esitligi\n\n{_ATIF}\n{_OTURUM}\n{_URETICI}\nson satir"
    sonuc = G._git_imza_satirlari_ayikla(metin)
    assert "noreply" not in sonuc, "ajan atif satirinin uretici adresi maskelenmedi"
    assert "Co-Authored-By: Claude Opus 5.5 (1M context)" in sonuc, \
        "atif satirinin AD bolumu de silindi — ad bolumu TARANMALI (F3)"
    assert "Claude-Session" not in sonuc, "ajan oturum satiri ayiklanmadi"
    assert "Generated with" not in sonuc, "ajan uretici satiri ayiklanmadi"
    assert "readback esitligi" in sonuc and "son satir" in sonuc, \
        "imza ayiklama mesajin GERCEK icerigini de sildi"
    assert sonuc.count("\n") == metin.count("\n"), "satir sayisi korunmadi"


def test_BASKA_trailer_AYIKLANMAZ():
    """2026-10-12 daraltmasi: ajan DISI trailer'lar (baska adres/ad) TARANIR.

    Eskiden `Co-Authored-By|Claude-Session|Signed-off-by|Reviewed-by|Cc` anahtarli her
    satir adresten bagimsiz dusuyordu => baska bir kisinin e-postasi sessizce geciyordu.
    """
    for satir in ("Signed-off-by: Biri <adres>", "Reviewed-by: Biri <adres>",
                  "Cc: Biri <adres>", "Co-authored-by: Biri <adres>",
                  "Co-Authored-By: Claude <adres>",                  # ad ayni, adres BASKA
                  "Claude-Session: https://claude.ai/code/x?u=adres",  # oturum disi govde
                  "\U0001F916 Generated with [Claude Code](adres)"):
        sonuc = G._git_imza_satirlari_ayikla(f"baslik\n\n{satir}")
        assert satir in sonuc, f"ajan DISI trailer ayiklandi (sizinti kor noktasi): {satir!r}"


def test_BASKA_trailer_SIZINTISI_BLOKLANIR_uctan_uca():
    """Pozitif vektor: trailer'daki bulgu (sentinel) public repoda BLOKLANIR."""
    _kur(True)
    try:
        cmd = "cd /c/core && git commit -q -F - <<'EOF'"
        for satir in (f"Signed-off-by: Biri <{_SENTINEL}>", f"Cc: {_SENTINEL}",
                      f"Co-authored-by: Biri <{_SENTINEL}>"):
            ham = cmd + f"\nfix(tooling): {_TEMIZ}\n\n{_ATIF}\n{satir}\nEOF"
            assert G._git_commit_public_leak(cmd, ham) != "", \
                f"trailer'daki bulgu YAKALANMADI: {satir!r}"
    finally:
        _geri_al()


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
        ham = (cmd + f"\nfix(tooling): {_TEMIZ}\n\n{_ATIF}\n{_OTURUM}\nEOF")
        assert G._git_commit_public_leak(cmd, ham) == "", \
            "imzali temiz commit bloklandi"
    finally:
        _geri_al()


def _cat(govde: str, ac: str = "<<'EOF'", kapa: str = "EOF") -> str:
    return '"$(cat ' + ac + "\n" + govde + "\n" + kapa + '\n)"'


def test_CAT_HEREDOC_m_YAKALANIR():
    """bug-gate P-1 (2026-10-14): Claude Code'un VARSAYILAN commit bicimi
    `-m "$(cat <<'EOF' … EOF)"` taranmiyordu — deger kirpilmis komuttan okunuyordu.
    Dispatcher gibi cagrilir: komut = `_komut_govdesi(ham)` (kirpilmis), ham = ham metin."""
    _kur(True)
    try:
        for ham in (f"cd /c/core && git commit -m {_cat('fix: x ' + _SENTINEL)}",
                    f"cd /c/core && git commit -m {_cat('fix: x ' + _SENTINEL, ac='<<EOF')}",
                    f"cd /c/core && git commit -m {_cat(_SENTINEL, ac=chr(60)*2 + chr(34) + 'M' + chr(34), kapa='M')}",
                    f"cd /c/core && git commit -m {_cat(_SENTINEL, ac='<<-EOF', kapa=chr(9) + 'EOF')}",
                    f"cd /c/core && git commit --message={_cat(_SENTINEL)}",
                    f"cd /c/core && git commit -m 'baslik' -m {_cat('govde ' + _SENTINEL)}",
                    f"cd /c/core && git commit -m $(cat <<'EOF'\n{_SENTINEL}\nEOF\n)"):
            assert G._git_commit_public_leak(G._komut_govdesi(ham), ham) != "", \
                f"$(cat) heredoc mesajindaki bulgu YAKALANMADI: {ham!r}"
    finally:
        _geri_al()


def test_CAT_HEREDOC_mesru_GECER():
    """Kontrol: bu repoda HER GUN kullanilan bicim (ajan atif + oturum) gecmeli."""
    _kur(True)
    try:
        ham = (f"cd /c/core && git commit -m "
               f"{_cat('fix(tooling): ' + _TEMIZ + chr(10) + chr(10) + _ATIF + chr(10) + _OTURUM)}")
        assert G._git_commit_public_leak(G._komut_govdesi(ham), ham) == "", \
            "mesru $(cat) commit'i bloklandi"
    finally:
        _geri_al()


def test_CAT_HEREDOC_cozulemez_FAIL_CLOSED():
    """Saf `cat` olmayan ikame (govde bilinemez) sessizce GECMEZ."""
    _kur(True)
    try:
        for ham in ("cd /c/core && git commit -m \"$(sed s/a/b/ <<'EOF'\ntemiz\nEOF\n)\"",
                    "cd /c/core && git commit -m \"$(cat <<'EOF' | tr a b\ntemiz\nEOF\n)\"",
                    "cd /c/core && git commit -m $(sed s/a/b/ <<'EOF'\ntemiz\nEOF\n)"):
            sonuc = G._git_commit_public_leak(G._komut_govdesi(ham), ham)
            assert "FAIL-CLOSED" in sonuc, f"cozulemeyen ikame gecti (fail-open!): {ham!r}"
    finally:
        _geri_al()


def test_PR_CAT_HEREDOC_govde_YAKALANIR():
    """P-1 kardesi: `gh pr create --body "$(cat <<'EOF' … EOF)"` PUBLIC-PR gate'inde de
    taranmiyordu. Ayni yayin yolundaki diger alt komutlar da (issue/release) kapsanir."""
    _kur(True)
    try:
        for on in ("gh pr create --repo org/CORE --title x --body",
                   "gh pr comment 1 --repo org/CORE -b",
                   "gh issue create --repo org/CORE -t x --body",
                   "gh release create v1 --repo org/CORE --notes",
                   "gh pr edit 1 --repo org/CORE --title"):
            ham = f"{on} {_cat('## Ozet' + chr(10) + _SENTINEL)}"
            assert G._gh_pr_public_leak(G._komut_govdesi(ham), ham) != "", \
                f"$(cat) yayin govdesindeki bulgu YAKALANMADI: {on}"
        ham = f"gh pr create --repo org/CORE --title x --body {_cat('## Ozet' + chr(10) + _TEMIZ)}"
        assert G._gh_pr_public_leak(G._komut_govdesi(ham), ham) == "", "temiz $(cat) PR bloklandi"
        ham = "gh pr create --repo org/CORE --title x --body \"$(sed s/a/b/ <<'EOF'\nx\nEOF\n)\""
        assert "FAIL-CLOSED" in G._gh_pr_public_leak(G._komut_govdesi(ham), ham), \
            "cozulemeyen PR govdesi ikamesi gecti (fail-open!)"
    finally:
        _geri_al()


def test_ATIF_AD_BOLUMU_TARANIR():
    """bug-gate F3 (2026-10-14): atif satirinin ad bolumune yazilan iz muafiyete saklanamaz."""
    _kur(True)
    try:
        cmd = "cd /c/core && git commit -q -F - <<'EOF'"
        atif = "Co-Authored-By: Claude " + _SENTINEL + " <" + "noreply" + "@" + "anthropic.com>"
        ham = cmd + f"\nfix(tooling): {_TEMIZ}\n\n{atif}\nEOF"
        assert G._git_commit_public_leak(cmd, ham) != "", "atif ad bolumundeki bulgu GECTI"
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
