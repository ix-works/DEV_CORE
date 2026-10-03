#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ADT datapreview/freestyle: SATIR BASINA 255 KARAKTER sinirinda otomatik satir kirma.

KOK (olculdu 2026-10-03, DEV, yalniz T000 SELECT, kontrol gruplu): freestyle ucu sorgu
metnini satir satir okur ve 255 karakterden uzun satirin devamini KESER. 288 kr tek satir
(14 OR terimi) -> 400 `"O" is invalid here (due to grammar)` (255. karakter `OR`un `O`su);
ayni sorgu iki satira bolununce 200; 252 kr tek satir 13 OR terimiyle 200. Eski "5'ten
fazla OR / WHERE terim sayisi -> 400" teshisi bu sinirin yansimasiydi.

FIX: `sap_adt_lib.sql_satirlarini_kir` — uzun satiri literal (`'..'`, `` `..` ``) ve satir
sonu yorumu (`"`) DISINDAKI bosluktan kirar; tek atom >255 ise `SQLSatirKirilamadi`
(istek GITMEZ). Freestyle'a POST eden 4 cagri noktasi (run_query · E070 fallback ·
ghost-transport sondasi · sprint_gate_check._query_sap) bundan gecer. Ayrica run_query
400 govdesini KIRPMADAN tasir (563 baytlik govde [:500] ile XML'i bozuyor, sebep
gorunmuyordu).

  K1-K9   saf fonksiyon: kisa=DEGISMEZ (CRLF dahil) · uzun -> her satir <=255 + token
          esitligi · literal/backtick/'' kacisi/yorum BOLUNMEZ · >255 literal -> hata ·
          CRLF uzun girdi -> eklenen ayirici CRLF · girinti
  R1-R3   run_query entegrasyonu (sahte HTTP): gonderilen govde kirik · kirilamayan sorguda
          istek GITMEZ · 400 govdesi kirpilmadan tasinir -> SAP sebebi ayristirilir
  S1      SINIF: scripts/ altinda freestyle'a POST eden HER fonksiyon reflow'dan gecer (AST)
  T1      3. BAGLAM: sprint_gate_check._query_sap (ayri arac, ayri istemci yolu)

  K10     devam satiri sutun-1'de `*` ile BASLAMAZ (freestyle `*`'i tam-satir yorumu sayar;
          bug-gate 2026-10-03 canli: `COUNT(` + LF + `* )` -> 400, ` * )` -> 200). K3'un
          token esitligi bunu GOREMEZ (bosluk oneki token degistirmez).
  K11     >255 kr `*` tam-satir yorum satiri -> SQLSatirKirilamadi (bolunemez)
  K12     girintisi ATILAN ilk atom `*` ile basliyorsa o da onek alir (sutun-1 `*` yok)
  K13     TAM 255 kr `*` atomu (onekle 256) -> SQLSatirKirilamadi + mesaj onekli boyu soyler

Mutasyon kipleri (kaynak METNI degistirilip gercek __file__ ile exec edilir):
  --mutasyon-kimlik        reflow hic kirmaz
  --mutasyon-literal-kor   literal tanima kapali
  --mutasyon-govde-kirp    run_query govdeyi [:500] kirpar
  --mutasyon-kardes        ghost-transport sondasi reflow'suz
  --mutasyon-yildiz-onek   devam satirina `*` oneki konmaz
  --mutasyon-yorum-satiri  `*` tam-satir yorum korumasi kapali
  --mutasyon-onek-ilk-atom girintisi atilan ilk atoma onek konmaz
  --mutasyon-onek-uzunluk  uzunluk kontrolu onekli boyu degil ciplak atomu olcer
CORE-07: her kipin DUSMESI BEKLENEN vektor kumesi `_BEKLENEN_DUSEN`'de PINLIDIR ve
ESITLIKLE kiyaslanir. Cikis: 0 taban yesil · 1 mutasyon BEKLENEN kumeyle dustu ·
2 SAPMA (mutasyonda dusen kume beklenenden farkli — fazlasi da eksigi de) ·
3 DOGRULANAMADI (capa tam 1 kez eslesmedi YA DA mutant derlenmedi — "dustu" SAYILMAZ).

Kosum: python tests/fixtures/sql_satir_kirma/run.py [--mutasyon-...]   (exit 0 = PASS)
"""
from __future__ import annotations

import ast
import io
import os
import sys
import types
import contextlib
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "scripts" / "sap_adt_lib.py").is_file():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
for _p in (REPO / "scripts", REPO / "scripts" / "utils"):
    sys.path.insert(0, str(_p))
os.environ.setdefault("CLAUDE_PROJECT_DIR", str(REPO))

LIB = REPO / "scripts" / "sap_adt_lib.py"

_GECERLI_KIP = frozenset({"--mutasyon-kimlik", "--mutasyon-literal-kor",
                          "--mutasyon-govde-kirp", "--mutasyon-kardes",
                          "--mutasyon-yildiz-onek", "--mutasyon-yorum-satiri",
                          "--mutasyon-onek-ilk-atom", "--mutasyon-onek-uzunluk"})

# CORE-07: kip -> dusmesi BEKLENEN vektor kimlikleri (ESITLIK; alt-kume degil).
# `_sql_devam_satiri_basi` UC yerde cagrilir; her cagri noktasinin kendi kipi + vektoru var:
#   devam satiri -> K10 (yildiz-onek tumunu birden kirar) · girinti atilan ilk atom -> K12
#   (onek-ilk-atom) · uzunluk kontrolu -> K13 (onek-uzunluk).
_BEKLENEN_DUSEN = {
    "--mutasyon-kimlik": {"K3", "K4", "K5", "K6", "K7", "K9", "K10", "K11", "K12", "K13",
                          "R1", "R2", "T1", "T2"},
    "--mutasyon-literal-kor": {"K4", "K5", "K6", "R2", "T2"},
    "--mutasyon-govde-kirp": {"R3"},
    "--mutasyon-kardes": {"S1"},
    "--mutasyon-yildiz-onek": {"K10", "K12", "K13"},
    "--mutasyon-yorum-satiri": {"K11"},
    "--mutasyon-onek-ilk-atom": {"K12"},
    "--mutasyon-onek-uzunluk": {"K13"},
}

# (eski, yeni) — CORE-07: eski TAM 1 kez eslesmeli.
_MUT = {
    "--mutasyon-kimlik": (
        "    if all(len(s) <= sinir for s in satirlar[0::2]):\n        return sorgu\n",
        "    if True:\n        return sorgu\n"),
    "--mutasyon-literal-kor": (
        "            if c in (\"'\", '`'):\n",
        "            if False:\n"),
    "--mutasyon-govde-kirp": (
        "                f\"Failed to run query\",\n"
        "                status_code=response.status_code,\n"
        "                response_text=response.text\n",
        "                f\"Failed to run query\",\n"
        "                status_code=response.status_code,\n"
        "                response_text=response.text[:500]\n"),
    "--mutasyon-kardes": (
        "data=sql_satirlarini_kir(query).encode('utf-8'),",
        "data=query.encode('utf-8'),"),
    "--mutasyon-yildiz-onek": (
        "    return (' ' + atom) if atom.startswith('*') else atom\n",
        "    return atom\n"),
    "--mutasyon-yorum-satiri": (
        "        if satir.startswith('*'):\n",
        "        if False:\n"),
    "--mutasyon-onek-ilk-atom": (
        "                aday = _sql_devam_satiri_basi(atom)\n",
        "                aday = atom\n"),
    "--mutasyon-onek-uzunluk": (
        "            if len(_sql_devam_satiri_basi(atom)) > sinir:\n",
        "            if len(atom) > sinir:\n"),
}

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(ok), detay))


def lib_yukle(kaynak: str) -> types.ModuleType:
    """Kaynak METNINI gercek dosya yoluyla exec et (mutant ve taban ayni yoldan)."""
    mod = types.ModuleType("sap_adt_lib")
    mod.__file__ = str(LIB)
    sys.modules["sap_adt_lib"] = mod
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(kaynak, str(LIB), "exec"), mod.__dict__)
    return mod


def uzun_sorgu() -> str:
    terms = " OR ".join(f"mandt = '{i:03d}'" for i in range(13))
    return f"SELECT mandt, mtext FROM t000 WHERE {terms} OR mtext <> 'ZZZZZZZZZZZZZZZZZZZZ'"


# ── S1: sinif taramasi — freestyle'a POST eden fonksiyonlar ─────────────────────
def _freestyle_post_fonksiyonlari(kaynak: str):
    """(fonksiyon_adi, reflow_cagiriyor_mu) — yalniz POST eden + URL'i KOD olarak tasiyan."""
    agac = ast.parse(kaynak)
    sonuc = []
    for fn in ast.walk(agac):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doc = (fn.body[0].value if fn.body and isinstance(fn.body[0], ast.Expr)
               and isinstance(getattr(fn.body[0], "value", None), ast.Constant) else None)
        url_var = post_var = reflow = False
        for d in ast.walk(fn):
            if isinstance(d, ast.Constant) and isinstance(d.value, str) and d is not doc:
                if "/datapreview/freestyle" in d.value and "{" not in d.value.split("freestyle", 1)[1][:2]:
                    url_var = True
                if d.value == "post":
                    post_var = True
            if isinstance(d, ast.Call):
                ad = (d.func.attr if isinstance(d.func, ast.Attribute)
                      else d.func.id if isinstance(d.func, ast.Name) else "")
                if ad == "post":
                    post_var = True
                if ad == "sql_satirlarini_kir":
                    reflow = True
        if url_var and post_var:
            sonuc.append((fn.name, reflow))
    return sonuc


def main(kip: str | None) -> int:
    kaynak = LIB.read_text(encoding="utf-8")
    if kip:
        eski, yeni = _MUT[kip]
        n = kaynak.count(eski)
        if n != 1:
            sys.stderr.write("[DOGRULANAMADI] mutasyon capasi %d kez eslesti (beklenen 1): %s "
                             "-> hicbir sayi raporlanmadi.\n" % (n, kip))
            return 3
        kaynak = kaynak.replace(eski, yeni, 1)
        print("mutasyon:", kip)
        # KURULAMADI != DUSTU: derlenmeyen mutant hicbir vektoru olcmez.
        try:
            compile(kaynak, str(LIB), "exec")
        except SyntaxError as e:
            sys.stderr.write("[DOGRULANAMADI] mutant DERLENMEDI (%s): %s -> hicbir sayi "
                             "raporlanmadi.\n" % (kip, e))
            return 3
    L = lib_yukle(kaynak)
    kir = L.sql_satirlarini_kir
    SINIR = L.SQL_SATIR_SINIRI

    # ── K: saf fonksiyon ─────────────────────────────────────────────────────
    kisa = "SELECT mandt FROM t000 WHERE mandt = '000'"
    kontrol("K1 kisa sorgu AYNEN doner", kir(kisa) == kisa, repr(kir(kisa))[:60])
    kisa_crlf = "SELECT mandt\r\nFROM t000\r\nWHERE mandt = '000'"
    kontrol("K2 kisa CRLF sorgu AYNEN doner (satir sonu korunur)", kir(kisa_crlf) == kisa_crlf)

    q = uzun_sorgu()
    try:
        r = kir(q)
        satirlar = r.split("\n")
        kontrol("K3 uzun tek satir -> her satir <=255 + en az 2 satir + token esitligi",
                len(q) > SINIR and len(satirlar) >= 2 and all(len(s) <= SINIR for s in satirlar)
                and r.split() == q.split(),
                "girdi=%d satirlar=%s" % (len(q), [len(s) for s in satirlar]))
    except Exception as e:  # noqa: BLE001
        kontrol("K3 uzun tek satir -> kirilir", False, "istisna: %r" % e)

    # K4: kirma noktasinin dogal dusecegi yerde BOSLUKLU literal
    lit = "'" + " ".join(["kelime"] * 20) + "'"          # 140 kr, icinde bosluk
    q4 = "SELECT mandt FROM t000 WHERE " + "mandt <> '999' AND " * 6 + "mtext <> " + lit
    try:
        r4 = kir(q4)
        kontrol("K4 bosluklu literal BOLUNMEZ (bir satirda butun durur)",
                len(q4) > SINIR and any(lit in s for s in r4.splitlines())
                and all(len(s) <= SINIR for s in r4.splitlines()),
                "girdi=%d satirlar=%s" % (len(q4), [len(s) for s in r4.splitlines()]))
    except Exception as e:  # noqa: BLE001
        kontrol("K4 bosluklu literal BOLUNMEZ", False, "istisna: %r" % e)

    # K5: '' kacisli + backtick literal + yorum
    lit_k = "'it''s " + "a b " * 30 + "end'"
    bt = "`" + "x y " * 30 + "`"
    kom = "\"yorum metni bosluklu " + "z " * 10
    q5 = ("SELECT mandt FROM t000 WHERE " + "mandt <> '998' AND " * 5 + "mtext <> " + lit_k
          + " AND mtext <> " + bt + " " + kom)
    try:
        r5 = kir(q5).splitlines()
        kontrol("K5 '' kacisi + backtick + satir-sonu yorumu BOLUNMEZ",
                len(q5) > SINIR and any(lit_k in s for s in r5) and any(bt in s for s in r5)
                and any(kom in s for s in r5)
                and all(len(s) <= SINIR for s in r5),
                "satirlar=%s" % [len(s) for s in r5])
    except Exception as e:  # noqa: BLE001
        kontrol("K5 kacis/backtick/yorum BOLUNMEZ", False, "istisna: %r" % e)

    # K6: tek basina >255 literal -> SQLSatirKirilamadi (literal BOLUNMEZ)
    q6 = "SELECT mandt FROM t000 WHERE mtext <> '" + "a b " * 70 + "'"
    try:
        r6 = kir(q6)
        kontrol("K6 >255 literal -> SQLSatirKirilamadi", False,
                "hata yok; satirlar=%s" % [len(s) for s in r6.splitlines()])
    except L.SQLSatirKirilamadi as e:
        kontrol("K6 >255 literal -> SQLSatirKirilamadi (SAPADTError alt sinifi, 'literal' der)",
                isinstance(e, L.SAPADTError) and "literal" in str(e), str(e)[:70])

    # K7: CRLF uzun girdi -> eklenen ayirici CRLF, ciplak LF YOK
    q7 = "SELECT mandt, mtext\r\nFROM t000\r\nWHERE " + uzun_sorgu().split("WHERE ", 1)[1]
    try:
        r7 = kir(q7)
        ciplak_lf = r7.replace("\r\n", "").count("\n")
        kontrol("K7 CRLF uzun girdi -> eklenen ayirici CRLF (ciplak LF yok) + satirlar <=255",
                r7 != q7 and ciplak_lf == 0 and all(len(s) <= SINIR for s in r7.split("\r\n")),
                "ciplak_lf=%d satirlar=%s" % (ciplak_lf, [len(s) for s in r7.split("\r\n")]))
    except Exception as e:  # noqa: BLE001
        kontrol("K7 CRLF uzun girdi", False, "istisna: %r" % e)

    # K8: tam 255 = sinirda, dokunulmaz (sinir DAHIL)
    q8 = "SELECT mandt FROM t000 WHERE mtext <> '" + "x" * (SINIR - 40) + "'"
    q8 = q8 + " " * (SINIR - len(q8))
    kontrol("K8 tam 255 kr satir DOKUNULMAZ", len(q8) == SINIR and kir(q8) == q8, "len=%d" % len(q8))

    # K9: girintili uzun satir -> ilk parca girintisini korur
    q9 = "    " + uzun_sorgu()
    try:
        r9 = kir(q9).split("\n")
        kontrol("K9 girintili uzun satir: ilk parca girintili, hepsi <=255",
                r9[0].startswith("    SELECT") and len(r9) >= 2 and all(len(s) <= SINIR for s in r9),
                "satirlar=%s" % [len(s) for s in r9])
    except Exception as e:  # noqa: BLE001
        kontrol("K9 girintili uzun satir", False, "istisna: %r" % e)

    # K10: kirma tam `*`'dan once dusuyor (bug-gate'in canli vakasinin bicimi)
    on = "SELECT mandt,"
    on = on + " " * (SINIR - len(on) - len("COUNT(")) + "COUNT("
    q10 = on + " * ) AS cnt FROM t000 GROUP BY mandt"
    try:
        r10 = kir(q10).splitlines()
        kontrol("K10 devam satiri sutun-1'de `*` ile BASLAMAZ (tek bosluk oneki) + <=255 + token esit",
                len(on) == SINIR and len(r10) >= 2
                and not any(s.startswith("*") for s in r10)
                and any(s.startswith(" * )") for s in r10[1:])
                and all(len(s) <= SINIR for s in r10) and kir(q10).split() == q10.split(),
                "girdi=%d satir_baslari=%r" % (len(q10), [s[:4] for s in r10]))
    except Exception as e:  # noqa: BLE001
        kontrol("K10 devam satiri `*` ile baslamaz", False, "istisna: %r" % e)

    # K11: >255 kr `*` tam-satir yorumu -> bolunemez
    q11 = "SELECT mandt FROM t000\n* " + "yorum " * 50 + "\nWHERE mandt = '000'"
    try:
        r11 = kir(q11)
        kontrol("K11 >255 `*` tam-satir yorum -> SQLSatirKirilamadi", False,
                "hata yok; satirlar=%s" % [len(s) for s in r11.splitlines()])
    except L.SQLSatirKirilamadi as e:
        kontrol("K11 >255 `*` tam-satir yorum -> SQLSatirKirilamadi ('tam-satır yorumu' der)",
                "tam-satır yorumu" in str(e), str(e)[:70])
    except Exception as e:  # noqa: BLE001
        kontrol("K11 >255 `*` tam-satir yorum -> SQLSatirKirilamadi", False, "istisna: %r" % e)

    # K12: girintisi ATILAN ilk atom `*` ile basliyor -> o yol da onek almali
    #      (cagri noktasi: `if not cur and len(aday) > sinir: aday = _sql_devam_satiri_basi(atom)`)
    q12 = " " * 250 + "*abcdefgh FROM t000 WHERE mandt = '000' OR mandt = '001'"
    try:
        r12 = kir(q12).splitlines()
        kontrol("K12 girintisi atilan ilk atom `*`: sutun-1 `*` YOK + <=255",
                len(q12) > SINIR and not any(s.startswith("*") for s in r12)
                and r12[0].startswith(" *abcdefgh") and all(len(s) <= SINIR for s in r12),
                "girdi=%d satir_baslari=%r" % (len(q12), [s[:4] for s in r12]))
    except Exception as e:  # noqa: BLE001
        kontrol("K12 girintisi atilan ilk atom `*`", False, "istisna: %r" % e)

    # K13: TAM 255 kr `*` atomu -> onekle 256 kr olur -> bolunemez
    #      (cagri noktasi: `if len(_sql_devam_satiri_basi(atom)) > sinir:`)
    a13 = "*" + "x" * (SINIR - 1)
    q13 = "SELECT mandt FROM t000 WHERE mandt = " + a13
    try:
        r13 = kir(q13)
        kontrol("K13 tam 255 kr `*` atomu -> SQLSatirKirilamadi", False,
                "hata yok; satirlar=%s" % [len(s) for s in r13.splitlines()])
    except L.SQLSatirKirilamadi as e:
        kontrol("K13 tam 255 kr `*` atomu -> SQLSatirKirilamadi (mesaj onekli 256'yi soyler)",
                len(a13) == SINIR and "önekiyle 256" in str(e), str(e)[:110])
    except Exception as e:  # noqa: BLE001
        kontrol("K13 tam 255 kr `*` atomu -> SQLSatirKirilamadi", False, "istisna: %r" % e)

    # ── R: run_query entegrasyonu (sahte HTTP; SAP'ye HIC gidilmez) ──────────
    class _Yanit:
        def __init__(self, kod, govde):
            self.status_code, self.text = kod, govde

    def istemci(kod=200, govde="<ok/>"):
        c = object.__new__(L.SAPADTClient)
        c.url = "https://sahte.invalid"
        c._get_headers = lambda *a, **k: {}
        c.gonderilen = []

        def _istek(method, url, **kw):
            c.gonderilen.append(kw.get("data"))
            return _Yanit(kod, govde)
        c._request_with_csrf_retry = _istek
        return c

    c = istemci()
    try:
        c.run_query(uzun_sorgu(), row_number=5)
        govde = (c.gonderilen[0] or b"").decode("utf-8")
        kontrol("R1 run_query gonderilen govdede her satir <=255",
                len(c.gonderilen) == 1 and all(len(s) <= SINIR for s in govde.splitlines())
                and govde.split() == uzun_sorgu().split(),
                "satirlar=%s" % [len(s) for s in govde.splitlines()])
    except Exception as e:  # noqa: BLE001
        kontrol("R1 run_query reflow", False, "istisna: %r" % e)

    c = istemci()
    try:
        c.run_query(q6, row_number=5)
        kontrol("R2 kirilamayan sorgu -> istisna + istek GITMEZ", False, "istisna yok")
    except L.SQLSatirKirilamadi:
        kontrol("R2 kirilamayan sorgu -> SQLSatirKirilamadi + istek GITMEZ",
                c.gonderilen == [], "gonderilen=%d" % len(c.gonderilen))

    # R3: 255-vakasinin GERCEK govde bicimi (563 bayt) — [:500] XML'i bozar
    sebep = '"O" is invalid here (due to grammar).'
    govde400 = ('<?xml version="1.0" encoding="utf-8"?><exc:exception xmlns:exc="http://www.sap.com/'
                'abapxml/types/communicationframework"><namespace id="http://www.sap.com/adt/wda/'
                'dataPreview"/><type id="ExceptionDataPreviewSQLGeneration"/><message lang="EN">'
                + sebep + '</message><localizedMessage lang="EN">' + sebep + '</localizedMessage>'
                '<properties><entry key="T100KEY-ID">ADT_DATAPREVIEW_MSG</entry><entry key="T100KEY-NO">'
                '004</entry><entry key="T100KEY-V1">' + sebep + '</entry></properties></exc:exception>')
    from sap_client import sap_hata_govdesi  # noqa: E402 (tuketici — uretim yolu)
    c = istemci(400, govde400)
    try:
        c.run_query("SELECT mandt FROM t000", row_number=5)
        kontrol("R3 400 govdesi kirpilmadan -> SAP sebebi ayristirilir", False, "istisna yok")
    except L.SAPADTError as e:
        h = sap_hata_govdesi(e) or {}
        kontrol("R3 400 govdesi (%d bayt) kirpilmadan tasinir -> sap_hata_govdesi SEBEBI verir"
                % len(govde400),
                len(govde400) > 500 and h.get("message") == sebep,
                "message=%r" % (h.get("message") or "")[:70])

    # ── S1: SINIF — freestyle'a POST eden her fonksiyon reflow'dan gecer ──────
    bulunan = []
    for p in sorted((REPO / "scripts").rglob("*.py")):
        rel = p.relative_to(REPO).as_posix()
        metin = kaynak if p == LIB else p.read_text(encoding="utf-8", errors="replace")
        for ad, ok in _freestyle_post_fonksiyonlari(metin):
            bulunan.append((rel, ad, ok))
    eksik = [f"{r}::{a}" for r, a, ok in bulunan if not ok]
    kontrol("S1 SINIF: scripts/ altinda freestyle POST eden %d fonksiyonun HEPSI reflow'lu"
            % len(bulunan),
            len(bulunan) >= 4 and not eksik,
            "taranan=%s eksik=%s" % (sorted(f"{r}::{a}" for r, a, _ in bulunan), eksik))

    # ── T1: 3. BAGLAM — sprint_gate_check._query_sap ─────────────────────────
    # stdout YONLENDIRILMEZ: modul import aninda sys.stdout'u reconfigure eder (StringIO'da yok).
    import sprint_gate_check as SG  # noqa: E402
    SG.sql_satirlarini_kir = L.sql_satirlarini_kir     # ayni (olasi mutant) uygulama
    SG.SQLSatirKirilamadi = L.SQLSatirKirilamadi

    class _Oturum:
        def __init__(self):
            self.gonderilen = []

        def get(self, *a, **k):
            return types.SimpleNamespace(headers={"X-CSRF-Token": "t"})

        def post(self, url, **kw):
            self.gonderilen.append(kw.get("data"))
            return types.SimpleNamespace(
                status_code=200, text="<dataPreview:data>000</dataPreview:data>")

    sc = types.SimpleNamespace(url="https://sahte.invalid", session=_Oturum(),
                               _invalidate_csrf_cache=lambda: None)
    out = SG._query_sap(sc, uzun_sorgu())
    g = (sc.session.gonderilen[0] or b"").decode("utf-8") if sc.session.gonderilen else ""
    kontrol("T1 3.BAGLAM sprint_gate_check._query_sap: govde satirlari <=255 + sonuc okunur",
            out == ["000"] and g and all(len(s) <= SINIR for s in g.splitlines()),
            "satirlar=%s out=%r" % ([len(s) for s in g.splitlines()], out))
    sc2 = types.SimpleNamespace(url="https://sahte.invalid", session=_Oturum(),
                                _invalidate_csrf_cache=lambda: None)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        out2 = SG._query_sap(sc2, q6)
    kontrol("T2 3.BAGLAM kirilamayan: istek GITMEZ, [] (eski non-200 sonucu AYNI) + UYARI gorunur",
            out2 == [] and sc2.session.gonderilen == [] and "kırılamadı" in err.getvalue(),
            "gonderilen=%d uyari=%r" % (len(sc2.session.gonderilen), err.getvalue()[:50]))

    hata = 0
    for ad, ok, detay in SONUC:
        hata += 0 if ok else 1
        print("[%s] %-60s %s" % ("ok" if ok else "FAIL", ad, detay))
    print("%d/%d OK" % (len(SONUC) - hata, len(SONUC)))
    print("SONUC: %d/%d gecti" % (len(SONUC) - hata, len(SONUC)))
    if kip:
        dusen = {ad.split()[0] for ad, ok, _ in SONUC if not ok}
        beklenen = _BEKLENEN_DUSEN[kip]
        if dusen != beklenen:
            print("[SAPMA] %s: beklenen=%s dusen=%s fazla=%s eksik=%s -> exit 2"
                  % (kip, sorted(beklenen), sorted(dusen), sorted(dusen - beklenen),
                     sorted(beklenen - dusen)))
            return 2
        print("[BEKLENEN] %s: dusen kume = beklenen %s" % (kip, sorted(beklenen)))
        return 1
    return 1 if hata else 0


if __name__ == "__main__":
    kip = None
    for _a in sys.argv[1:]:
        if _a.startswith("--mutasyon"):
            if _a not in _GECERLI_KIP:
                print("[KULLANIM] bilinmeyen mutasyon kipi: %s · gecerli kipler: %s"
                      % (_a, ", ".join(sorted(_GECERLI_KIP))))
                sys.exit(3)
            kip = _a
    sys.exit(main(kip))
