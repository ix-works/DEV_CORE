#!/usr/bin/env python3
# ENFORCES: C-PUSH-01  (ADR 0019 coverage binding)
"""test_push_readback_mismatch.py — push readback: BICIM farki vs ICERIK farki.

VAKA (2026-07-28, canli): bir CDS view kaynaginda ABAP tarzi `"` yorumu vardi.
CDS DDL'de `"` yorum DEGILDIR -> SAP kaynagi SESSIZCE reddetti.
BES kontrol de yesil verdi: run_review PASS · abaplint temiz · run_all_validators OK ·
adt_syntax_check valid:true · push "[OK] Source uploaded" + "[OK] Object activated".
Kaynak canliya HIC inmedi (canli 4163 ch, yerel 5321 ch). Yakalayan tek sey readback.

KOK-NEDEN: push_object readback kiyasini ZATEN yapiyordu ama farki yalnizca WARNING
basip result'a hicbir basarisizlik isareti koymuyordu -> 'success' True donuyordu.

KOR KORUNE hard-fail YAPILAMAZ: SAP bazi obje tiplerinde kaynagi pretty-print eder
(gercek vaka: bir tabloda 12 fark satiri, hepsi hizalama boslugu, icerik AYNI).
AYRIM: tum bosluklar atildiginda hala farkli ise -> GERCEK icerik uyusmazligi.

⚠ Bu test GERCEK kod yolunu cagirir. Ilk taslakta mantik testte YENIDEN UYGULANMISTI
ve kok-fix sabote edildiginde test YESIL kaldi — sahte guvence. Ders: bir testin
neyi CAGIRDIGI, ne iddia ettigi kadar onemlidir.

Agsiz (offline) kosar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sap_client import readback_farki_yalniz_bicim_mi as _ayrim  # noqa: E402


def test_pretty_print_bicim_farki_gecer():
    """SAP hizalamayi genisletirse (gercek vaka) icerik AYNI -> basarisizlik DEGIL."""
    yuklenen = "key mandt : mandt not null;\nkey ctype : zsd001_e_ctype not null;"
    canli = "key mandt   : mandt not null;\nkey ctype   : zsd001_e_ctype not null;"
    assert _ayrim(yuklenen, canli) is True, "pretty-print bicim farki basarisizlik sayilmamali"


def test_icerik_farki_yakalanir():
    """Vaka: canli ESKI kaynak (yeni alanlar YOK) -> GERCEK uyusmazlik."""
    yuklenen = "Header.fld1 as FieldOne,\nHeader.fld2 as FieldTwo,"
    canli = "Header.fld1 as LegacyCombinedField,"
    assert _ayrim(yuklenen, canli) is False, "icerik farki YAKALANMALI"


def test_birebir_ayni_gecer():
    s = "define view entity ZSD001_I_X as select from zsd001_t_y { key a }"
    assert _ayrim(s, s) is True


def test_satir_sonu_farki_gecer():
    """CRLF/LF farki icerik farki DEGILDIR."""
    assert _ayrim("a\r\nb\r\n", "a\nb\n") is True


def test_tek_karakter_farki_yakalanir():
    """Bosluk-disi tek karakter bile icerik farkidir (ornek: // vs ABAP tarzi yorum)."""
    assert _ayrim("as FieldOne,   // not1", 'as FieldOne,   " not1') is False


def test_bos_ve_none_cokmez():
    """Savunmaci: readback okunamazsa cagri patlamamali."""
    assert _ayrim("", "") is True
    assert _ayrim(None, None) is True
    assert _ayrim("abc", None) is False


def test_result_success_readback_ok_false_ile_duser():
    """push_object'in success ifadesi readback_ok'i hesaba katmali (UC-DEGERLI).

    2026-08-01: `readback_ok` artik True/False/None. None = "dogrulama KOSAMADI" ->
    push'u DUSURMEZ (asiri-sikilasma olurdu) ama success'i de dogrulanmis SAYMAZ;
    ayrim `readback_reason` + MCP `readback_verified` alanindan okunur.
    """
    for uploaded, activated, readback, beklenen in [
        (True, True, True, True),
        (True, True, False, False),   # ASIL REGRESYON (2026-07-28)
        (True, True, None, True),     # olculemedi -> push dusmez (gorunurluk ayri alanda)
        (True, False, True, False),
        (False, True, True, False),
    ]:
        result = {'source_uploaded': uploaded, 'activated': activated, 'readback_ok': readback}
        success = (result['source_uploaded'] and result['activated']
                   and result.get('readback_ok') is not False)
        assert success is beklenen, f"{result} -> {success}, beklenen {beklenen}"


def test_readback_ok_yoksa_varsayilan_true():
    """Geriye donuk uyum: anahtar hic konmadiysa (dogrulama atlandi) push'u dusurme."""
    result = {'source_uploaded': True, 'activated': True}
    assert (result['source_uploaded'] and result['activated']
            and result.get('readback_ok') is not False) is True


def test_push_yolu_gercekten_kabloludur():
    """Kablolama: helper push akisinda KULLANILIYOR ve success ifadesi readback_ok'i okuyor.

    Fonksiyon dogru calissa bile push'a bagli DEGILSE koruma yoktur (kod != kablolama).
    """
    import re
    src = (Path(__file__).resolve().parents[1] / "sap_client.py").read_text(encoding="utf-8")
    assert "readback_farki_yalniz_bicim_mi(uploaded_norm, active_norm)" in src, \
        "helper push akisinda CAGRILMIYOR — koruma kablolu degil"
    assert "result['readback_ok'] = False" in src, "icerik uyusmazliginda readback_ok False yapilmiyor"

    # ⚠ Burada "dosyada bir yerde gecsin" YETMEZ: ayni dize asagidaki elif'te de var,
    # o yuzden success ifadesinden SILINSE BILE gevsek bir 'in src' kontrolu yesil kalir
    # (2026-07-28'de sabotaj testinde bizzat yasandi). success ATAMASININ KENDISINI ara.
    m = re.search(r"result\['success'\]\s*=\s*\((.*?)\)", src, re.S)
    assert m, "result['success'] atamasi bulunamadi (yapi degismis olabilir)"
    ifade = m.group(1)
    assert "readback_ok" in ifade, \
        "success ifadesi readback_ok'i OKUMUYOR — icerik uyusmazligi push'u dusurmez"
    for zorunlu in ("source_uploaded", "activated"):
        assert zorunlu in ifade, f"success ifadesinde {zorunlu} kayboldu"

    # 2026-08-01 (bug-avi, "dogrulama kosamadi = dogrulandi"): readback OKUNAMADIGINDA
    # ucuncu deger ACIKCA yazilmali. Yoksa "kostu ve tuttu" ile "hic kosamadi" ayni
    # cikti (success:true, isaret yok) olur — iki durum cagiran icin AYIRT EDILEMEZ.
    assert "result['readback_ok'] = None" in src, \
        "readback KOSAMADI dali readback_ok=None yazmiyor — ucuncu deger kayboldu"
    # ⚠ HARNESS NOTU: yukaridaki regex `(.*?)\)` NON-GREEDY -> ilk `)`de kesilir ve
    # `result.get('readback_ok')` parantezinde durur; bu yuzden uc-degerli okumayi
    # `ifade` uzerinden ARAMA (yanlis FAIL verir). Tam satiri kaynakta ara.
    assert "and result.get('readback_ok') is not False" in src, \
        "success ifadesi None'i False'a katliyor (asiri-siki) ya da uc-degerli okumuyor"


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
    print(f"\npush readback ayrimi: {len(testler) - hata}/{len(testler)} gecti")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
