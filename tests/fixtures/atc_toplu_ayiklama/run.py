#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""atc_toplu_ayiklama — `scripts/atc_toplu_ayikla.py` korpusu (Q371①, 2026-10-12). SAP'siz.

KABUL ÖLÇÜTÜ (kaydın ⚠ RİSK bloğu): sınıflama checkId (GUID) + mesaj metniyle; parmak izinde
satır numarası YOK — aynı kod satır kaydırınca parmak izi DEĞİŞMEZ. Bulgu verisi SENTETİKTİR
(`ZSD001_*`, uydurma GUID'ler); canlı ATC kabul koşusu bu fixture'ın DIŞINDADIR.

SENARYOLAR
  K1  konum: sınıf ana kaynak `#start=` → tip/ad/satır · K2 include birimi korunur, obje = sınıf
  K3  ad alanlı (`%2f`) obje adı çözülür · K4 fragmansız konum → satır None (çökme yok)
  F1  SATIR KAYMASI: aynı bulgular +7 satır kaydı (mesajda satır no da var) → parmak izi AYNI,
      kıyas çözülen=0 yeni=0 kalan=N                                          [--mutasyon-satir]
  F2  Pretty Print birim başına İLK fark: aynı birimde satır 10 → 50 → KALAN (çözüldü+yeni DEĞİL)
  F3  gerçek çözülme + gerçek yeni bulgu ayrı sayılır
  F4  ÇOKLU-KÜME: aynı birim/check/mesaj iki kez → biri giderse çözülen=1 kalan=1 [--mutasyon-kume-seti]
  C1  küme anahtarı checkId GUID'i İÇERİR: aynı metin, farklı GUID → 2 küme   [--mutasyon-kume-metin]
  C2  aynı GUID, yalnız tırnaklı tanımlayıcı/sayı farklı → 1 küme (mesaj ŞEKLİ)
  C3  P1 kümesi P2'nin önünde (öncelik sırası)
  G1-G3 CANLI BİÇİM (2026-10-12 ölçümü, genericize): `;start=` konumu · mesaj içi satır no ·
      `SINIF=>METOT` maskesi tek küme / ayrı parmak izi                     [--mutasyon-uye-maske]
  U1  bug-gate 2026-10-12: aynı sınıfta METOT_A'da çözülen, METOT_C'de doğan bulgu (mesajda üye
      adı yok) → çözülen 1 · yeni 1 · uye_kaymasi 1 (konumdaki name= parmak izinde) [--mutasyon-uye]
  U1b aynı metotta satır kayması → kalan (kontrol grubu) · U2 konum_coz name= → uye
  U3  eski sürüm raporu (kayıtlı iz farklı) → izler konumdan YENİDEN hesaplanır [--mutasyon-kayitli-iz]
  W1  worklist ayrıştırılamadı + 0 bulgu → çıkış 4 (sahte-temiz 0 değil)     [--mutasyon-fallback-kod]
  W2  "sonra" raporu fallback'li → KIYAS EKSIK + çıkış 1                     [--mutasyon-fallback-kiyas]
  Q1  P paketi ↔ Q paketi → KIYAS EKSIK + çıkış 1 · Q2 variant/tavan farkı   [--mutasyon-kosul]
  Q3  aynı koşul, tam rapor → çıkış 0 (kontrol grubu) + KARSILASTIRMA SINIR satırı
  O1  obje = bulgunun KONUMU, hedef değil ("nested DB read" SELECT'li sınıfa yazılır) [--mutasyon-hedef-obje]
  T1  bulgu sayısı = tavan → kesilmis_olabilir + çıktı "KESILMIS OLABILIR" + çıkış 4 [--mutasyon-tavan]
  T2  tavanın altı → kesilmedi, çıkış 0 · T3 tavan koşucuya AÇIK geçirilir
  H1  hedef istisnası → hata raporda, diğer hedef yine ölçülür, çıkış 1, "[OLCULEMEDI]" basılır
  H2  bozuk sonuç biçimi (None) → hata (sessiz 0 bulgu YOK) · H3 zaman aşımı → ipucu metni
  Z1  NEGATİF: ortamdaki ADT_TIMEOUT_DEFAULT `--zaman-asimi` ile EZİLMEZ      [--mutasyon-zaman-ezer]
  Z2  ortamda yoksa varsayılan 900 · Z3 `--zaman-asimi 300` uygulanır
  V1  CSV: UTF-8 BOM · `;` ayraç · CRLF YOK · başlık sütunları
  R1  run_atc_check.atc_bulgulari max_verdicts'i lib'e AYNEN geçirir (yeniden kullanım kablosu)
  B1  3. BAĞLAM — gerçek CLI alt süreci: `kume` + `karsilastir` kaydedilmiş JSON üzerinde;
      bozuk girdi → çıkış 2; kesik rapor kıyasında "KIYAS EKSIK" + çıkış 1

Koşum:  python tests/fixtures/atc_toplu_ayiklama/run.py [--mutasyon-<kip>]
"""
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import types
from contextlib import redirect_stdout
from pathlib import Path

if sys.platform == "win32":
    for _a in (sys.stdout, sys.stderr):
        try:
            _a.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

KOK = Path(__file__).resolve().parents[3]
ARAC = KOK / "scripts" / "atc_toplu_ayikla.py"

MUTASYON = {
    # parmak izine satır numarasını sokar → F1/F2/G1 düşmeli
    # (mesaja eklemek NO-OP olurdu: parmak izi mesajdaki sayıları zaten maskeler — ölçüldü).
    # Çapa konum_coz'da: karsilastir izleri JSON'dan değil konumdan YENİDEN hesaplar ⇒
    # zenginlestir'e konan mutasyon kıyası ETKİLEMEZDİ (bug-gate turu 2026-10-12).
    "--mutasyon-satir": ('    uye = unquote(u.group(1)).upper() if u else ""\n',
                         '    uye = (unquote(u.group(1)).upper() if u else "") + "#" + str(satir)\n'),
    # parmak izinden üyeyi (name=) düşürür → U1 düşmeli
    "--mutasyon-uye": ('    parca = [birim or "", check_id or "", norm] + ([uye] if uye else [])\n',
                       '    parca = [birim or "", check_id or "", norm]\n'),
    # kayıtlı (eski sürüm) ize güvenir → U3 düşmeli
    "--mutasyon-kayitli-iz": ('    if "konum" not in b:', '    if True:'),
    # worklist fallback'i çıkış kodunda yok sayar → W1 düşmeli
    "--mutasyon-fallback-kod": (
        '    if any(h.get("kesilmis_olabilir") or h.get("worklist_parse_fallback") for h in rapor["hedefler"]):',
        '    if any(h.get("kesilmis_olabilir") for h in rapor["hedefler"]):'),
    # worklist fallback'i kıyasta yok sayar → W2 düşmeli
    "--mutasyon-fallback-kiyas": (
        '            if h.get("hata") or h.get("kesilmis_olabilir") or h.get("worklist_parse_fallback")]',
        '            if h.get("hata") or h.get("kesilmis_olabilir")]'),
    # kıyaslanabilirlik denetimini söker → Q1/Q2 düşmeli
    "--mutasyon-kosul": ('    return sorun\n', '    return []\n'),
    # çoklu-kümeyi kümeye indirger (sayım kaybolur) → F4 düşmeli
    "--mutasyon-kume-seti": ('a, b = Counter(p for p, _ in ia), Counter(p for p, _ in ib)',
                             'a, b = Counter(set(p for p, _ in ia)), Counter(set(p for p, _ in ib))'),
    # küme anahtarından GUID'i düşürür (yalnız metin) → C1 düşmeli
    "--mutasyon-kume-metin": ('    return (b["checkId"], b["mesaj_sekli"])\n',
                              '    return ("", b["mesaj_sekli"])\n'),
    # obje adını hedeften alır → O1 düşmeli
    "--mutasyon-hedef-obje": ('        **k,\n', '        **k, "obje_adi": hedef,\n'),
    # tavan eşitliğini kaçırır → T1 düşmeli
    "--mutasyon-tavan": ('h["kesilmis_olabilir"] = len(ham) >= tavan', 'h["kesilmis_olabilir"] = len(ham) > tavan'),
    # SINIF=>METOT maskesini söker → G2 düşmeli
    "--mutasyon-uye-maske": ('    m = _UYE_RE.sub("<>", m)\n', ''),
    # ortamdaki zaman aşımını ezer → Z1 düşmeli
    "--mutasyon-zaman-ezer": ('        if "ADT_TIMEOUT_DEFAULT" not in os.environ:\n', '        if True:\n'),
}
GECERLI_KIP = set(MUTASYON)
_kip = [a for a in sys.argv[1:] if a.startswith("--")]
for a in _kip:
    if a not in GECERLI_KIP:
        print(f"[DURDU] bilinmeyen kip: {a}")
        sys.exit(2)
KIP = _kip[0] if _kip else None


def yukle():
    """Aracın kaynak METNİNİ (mutasyon uygulanmış) gerçek __file__ ile modül olarak çalıştırır."""
    src = ARAC.read_text(encoding="utf-8")
    if KIP:
        eski, yeni = MUTASYON[KIP]
        if src.count(eski) != 1:
            print(f"[DURDU] mutasyon çapası bulunamadı/çoğul ({KIP}): {eski!r}")
            sys.exit(3)
        src = src.replace(eski, yeni)
    mod = types.ModuleType("atc_toplu_ayikla_fx")
    mod.__file__ = str(ARAC)
    sys.modules[mod.__name__] = mod
    exec(compile(src, str(ARAC), "exec"), mod.__dict__)
    return mod


A = yukle()
SONUC = []


def kontrol(ad, ok, detay=""):
    SONUC.append((ad, bool(ok), detay))


G1 = "3C9E0000-0000-4000-8000-00000000AAA1"   # uydurma GUID'ler
G2 = "3C9E0000-0000-4000-8000-00000000BBB2"
G_PP = "3C9E0000-0000-4000-8000-00000000CCC3"
SINIF = "/sap/bc/adt/oo/classes/zsd001_cl_a/source/main"
SINIF_B = "/sap/bc/adt/oo/classes/zsd001_cl_b/source/main"


def b(loc, cid, msg, prio="2"):
    return {"priority": prio, "location": loc, "checkId": cid, "message": msg}


def z(hamlar, hedef="ZSD001_P"):
    return [A.zenginlestir(h, hedef) for h in hamlar]


# ── K: konum ayrıştırma ──────────────────────────────────────────────────────
k = A.konum_coz(SINIF + "#start=27,4")
kontrol("K1 sınıf ana kaynak: tip/ad/satır", (k["obje_tipi"], k["obje_adi"], k["satir"], k["birim"])
        == ("classes", "ZSD001_CL_A", 27, SINIF), f"{k}")
k = A.konum_coz("/sap/bc/adt/oo/classes/zsd001_cl_a/includes/testclasses#start=5,0")
kontrol("K2 include birimi korunur, obje = sınıf",
        k["obje_adi"] == "ZSD001_CL_A" and k["birim"].endswith("/includes/testclasses"), f"{k}")
k = A.konum_coz("/sap/bc/adt/programs/programs/%2fns%2fzsd001_r/source/main#start=3,1")
kontrol("K3 ad alanlı obje adı çözülür", k["obje_adi"] == "/NS/ZSD001_R" and k["obje_tipi"] == "programs", f"{k}")
k = A.konum_coz("/sap/bc/adt/ddic/ddl/sources/zsd001_i_x")
kontrol("K4 fragmansız konum → satır None", k["satir"] is None and k["obje_adi"] == "ZSD001_I_X", f"{k}")

# ── F: parmak izi / kıyas ────────────────────────────────────────────────────
once = z([b(SINIF + "#start=12,0", G1, "SELECT in loop at line 12"),
          b(SINIF + "#start=40,2", G2, "Variable 'LV_X' not used"),
          b(SINIF_B + "#start=7,0", G1, "SELECT in loop at line 7")])
sonra = z([b(SINIF + "#start=19,0", G1, "SELECT in loop at line 19"),
           b(SINIF + "#start=47,2", G2, "Variable 'LV_X' not used"),
           b(SINIF_B + "#start=14,0", G1, "SELECT in loop at line 14")])
d = A.karsilastir(once, sonra)
kontrol("F1 satır kayması → parmak izi AYNI, çözülen=0 yeni=0 kalan=3",
        [x["parmak_izi"] for x in once] == [x["parmak_izi"] for x in sonra]
        and d["sayim"] == {"once": 3, "sonra": 3, "cozulen": 0, "yeni": 0, "kalan": 3, "uye_kaymasi": 0},
        f"{d['sayim']}")
pp_once = z([b(SINIF + "#start=10,0", G_PP, "Incorrect Pretty Print state", "3")])
pp_sonra = z([b(SINIF + "#start=50,0", G_PP, "Incorrect Pretty Print state", "3")])
d = A.karsilastir(pp_once, pp_sonra)
kontrol("F2 Pretty Print birimde kaydı → KALAN (çözüldü+yeni değil)",
        d["sayim"]["kalan"] == 1 and d["sayim"]["cozulen"] == 0 and d["sayim"]["yeni"] == 0, f"{d['sayim']}")
d = A.karsilastir(once, z([b(SINIF + "#start=12,0", G1, "SELECT in loop at line 12"),
                            b(SINIF_B + "#start=7,0", G2, "Variable 'LV_Y' not used")]))
kontrol("F3 gerçek çözülme ve gerçek yeni ayrı sayılır",
        d["sayim"]["cozulen"] == 2 and d["sayim"]["yeni"] == 1 and d["sayim"]["kalan"] == 1, f"{d['sayim']}")
iki = z([b(SINIF + "#start=12,0", G1, "SELECT in loop"), b(SINIF + "#start=30,0", G1, "SELECT in loop")])
d = A.karsilastir(iki, iki[:1])
kontrol("F4 çoklu-küme: ikiden biri giderse çözülen=1 kalan=1",
        d["sayim"]["cozulen"] == 1 and d["sayim"]["kalan"] == 1 and d["sayim"]["yeni"] == 0, f"{d['sayim']}")

# ── C: kümeleme ──────────────────────────────────────────────────────────────
km = A.kumele(z([b(SINIF + "#start=1,0", G1, "Same text"), b(SINIF + "#start=2,0", G2, "Same text")]))
kontrol("C1 aynı metin + farklı GUID → 2 küme", len(km) == 2, f"{[(g['checkId'], g['adet']) for g in km]}")
km = A.kumele(z([b(SINIF + "#start=1,0", G2, "Variable 'LV_A' not used in line 4"),
                 b(SINIF_B + "#start=2,0", G2, "Variable 'LV_B' not used in line 88")]))
kontrol("C2 aynı GUID, tanımlayıcı/sayı farkı → 1 küme, 2 obje",
        len(km) == 1 and km[0]["adet"] == 2 and km[0]["objeler"] == ["ZSD001_CL_A", "ZSD001_CL_B"], f"{km}")
km = A.kumele(z([b(SINIF + "#start=1,0", G2, "W", "2"), b(SINIF + "#start=2,0", G2, "W", "2"),
                 b(SINIF + "#start=3,0", G1, "E", "1")]))
kontrol("C3 P1 kümesi önde, numara 1", km[0]["oncelik"] == "1" and km[0]["kume_no"] == 1, f"{km}")

# ── G: CANLI BİÇİM (2026-10-12'de ölçülen yazım; adlar genericize) ─────────────
# location: `#type=CLAS%2FOM;name=<METOT>;start=<n>` (sütunsuz) · checkId: tiresiz 32 hex ·
# mesaj: "... at Method <SINIF>=><METOT> line <n>" (satır no MESAJIN İÇİNDE).
GC = "2529EE340000000000000000000000AA"
MSJ = "LOOP AT itab. EXIT/RETURN/LEAVE ... for result of statement at Method %s line %d"
CANLI = "/sap/bc/adt/oo/classes/zsd001_cl_a/source/main#type=CLAS%%2FOM;name=%s;start=%d"
g_once = z([b(CANLI % ("METOT_A", 140), GC, MSJ % ("ZSD001_CL_A=>METOT_A", 103), "3"),
            b(CANLI % ("METOT_B", 220), GC, MSJ % ("ZSD001_CL_A=>METOT_B", 183), "3")])
g_sonra = z([b(CANLI % ("METOT_A", 149), GC, MSJ % ("ZSD001_CL_A=>METOT_A", 112), "3"),
             b(CANLI % ("METOT_B", 229), GC, MSJ % ("ZSD001_CL_A=>METOT_B", 192), "3")])
d = A.karsilastir(g_once, g_sonra)
kontrol("G1 canlı biçim: `;start=` satırı okunur, satır kaymasında (konum+mesaj) parmak izi AYNI",
        g_once[0]["satir"] == 140 and g_once[0]["obje_adi"] == "ZSD001_CL_A"
        and d["sayim"] == {"once": 2, "sonra": 2, "cozulen": 0, "yeni": 0, "kalan": 2, "uye_kaymasi": 0},
        f"{d['sayim']}")
km = A.kumele(g_once)
kontrol("G2 canlı biçim: aynı kural iki metotta → TEK küme (SINIF=>METOT maskelenir)",
        len(km) == 1 and km[0]["adet"] == 2, f"{[(g['mesaj_sekli'], g['adet']) for g in km]}")
kontrol("G3 canlı biçim: iki metodun bulgusu AYRI parmak izi (birbirini yutmaz)",
        g_once[0]["parmak_izi"] != g_once[1]["parmak_izi"], "")

# ── U: üye (name=) parmak izinde — bug-gate 2026-10-12 ─────────────────────────
MSJ_U = "Statement result not used"   # mesajda üye adı YOK: ayrımı yalnız konumun name='i yapabilir
k = A.konum_coz(CANLI % ("METOT_A", 10))
k0 = A.konum_coz(SINIF + "#start=10,0")
kontrol("U2 konum_coz: name= → uye, name= yoksa boş", k.get("uye") == "METOT_A" and k0.get("uye") == "",
        f"{k} {k0}")
u_once = z([b(CANLI % ("METOT_A", 10), GC, MSJ_U, "3")])
u_sonra = z([b(CANLI % ("METOT_C", 90), GC, MSJ_U, "3")])
d = A.karsilastir(u_once, u_sonra)
kontrol("U1 METOT_A'da çözülen + METOT_C'de doğan → çözülen 1 · yeni 1 · kalan 0 · uye_kaymasi 1",
        d["sayim"] == {"once": 1, "sonra": 1, "cozulen": 1, "yeni": 1, "kalan": 0, "uye_kaymasi": 1},
        f"{d['sayim']}")
d = A.karsilastir(u_once, z([b(CANLI % ("METOT_A", 25), GC, MSJ_U, "3")]))
kontrol("U1b aynı metotta satır kayması → kalan 1, uye_kaymasi 0 (kontrol grubu)",
        d["sayim"]["kalan"] == 1 and d["sayim"]["cozulen"] == 0 and d["sayim"].get("uye_kaymasi") == 0,
        f"{d['sayim']}")
eski = [{**x, "parmak_izi": "eski-surum-izi"} for x in g_once]
d = A.karsilastir(eski, g_once)
kontrol("U3 eski sürüm raporu (kayıtlı iz farklı) → izler konumdan YENİDEN → kalan 2",
        d["sayim"]["kalan"] == 2 and d["sayim"]["cozulen"] == 0, f"{d['sayim']}")

# ── O: obje = bulgunun konumu ────────────────────────────────────────────────
o = z([b(SINIF_B + "#start=88,0", G1, "Nested DB read")], hedef="ZSD001_CL_A")[0]
kontrol("O1 obje bulgunun KONUMUNDAN (hedef ZSD001_CL_A, SELECT ZSD001_CL_B'de)",
        o["obje_adi"] == "ZSD001_CL_B" and o["hedef"] == "ZSD001_CL_A", f"{o['obje_adi']}")

# ── T/H: toplama sözleşmesi (sahte koşucu) ───────────────────────────────────
cagri = []


def kosucu_sabit(n):
    def f(ad, tip, varyant, tavan):
        cagri.append((ad, tip, varyant, tavan))
        return {"findings": [b(SINIF + "#start=%d,0" % i, G1, "M") for i in range(n)]}
    return f


r = A.topla([("package", "ZSD001_P")], "DEFAULT", 5, kosucu_sabit(5))
cikti = io.StringIO()
with redirect_stdout(cikti):
    A.kapsam_bas(r)
kontrol("T1 bulgu=tavan → kesilmis_olabilir + 'KESILMIS OLABILIR' + çıkış 4",
        r["hedefler"][0]["kesilmis_olabilir"] is True and "KESILMIS OLABILIR" in cikti.getvalue()
        and A.rapor_cikis_kodu(r) == 4, f"{r['hedefler']} {cikti.getvalue()!r}")
r = A.topla([("package", "ZSD001_P")], "V2", 5, kosucu_sabit(4))
kontrol("T2 tavanın altı → kesilmedi, çıkış 0",
        r["hedefler"][0]["kesilmis_olabilir"] is False and A.rapor_cikis_kodu(r) == 0, f"{r['hedefler']}")
kontrol("T3 tavan + varyant koşucuya AÇIK geçirildi", cagri[-1] == ("ZSD001_P", "package", "V2", 5), f"{cagri}")


def kosucu_karma(ad, tip, varyant, tavan):
    if ad == "ZSD001_BOZUK":
        raise RuntimeError("ADT 500")
    if ad == "ZSD001_NONE":
        return None
    if ad == "ZSD001_YAVAS":
        raise TimeoutError("Read timed out")
    return {"findings": [b(SINIF + "#start=1,0", G1, "M")]}


r = A.topla([("package", "ZSD001_BOZUK"), ("package", "ZSD001_IYI"), ("package", "ZSD001_NONE"),
             ("package", "ZSD001_YAVAS")], "DEFAULT", 100, kosucu_karma)
cikti = io.StringIO()
with redirect_stdout(cikti):
    A.kapsam_bas(r)
h = {x["hedef"]: x for x in r["hedefler"]}
kontrol("H1 hedef istisnası → hata raporda, diğeri ölçülür, çıkış 1, [OLCULEMEDI]",
        h["ZSD001_BOZUK"]["hata"] and h["ZSD001_IYI"]["bulgu_sayisi"] == 1 and len(r["bulgular"]) == 1
        and A.rapor_cikis_kodu(r) == 1 and "[OLCULEMEDI] package ZSD001_BOZUK" in cikti.getvalue(),
        f"{r['hedefler']}")
kontrol("H2 bozuk sonuç (None) → hata, bulgu_sayisi None (sessiz 0 yok)",
        h["ZSD001_NONE"]["hata"] and h["ZSD001_NONE"]["bulgu_sayisi"] is None, f"{h['ZSD001_NONE']}")
kontrol("H3 zaman aşımı → --zaman-asimi ipucu", "--zaman-asimi" in (h["ZSD001_YAVAS"]["hata"] or ""),
        f"{h['ZSD001_YAVAS']}")

# ── W/Q: worklist fallback + kıyaslanabilirlik (bug-gate 2026-10-12) ──────────
tmp_w = Path(tempfile.mkdtemp(prefix="atcfxw_"))


def rapor_r(ad, bulgular, fallback=False, hedef="ZSD001_P", variant="DEFAULT", tavan=5000):
    r = {"_surum": "x", "variant": variant, "tavan": tavan, "muaf_bulgular": "DAHIL DEGIL",
         "hedefler": [{"hedef": hedef, "tip": "package", "bulgu_sayisi": len(bulgular),
                       "kesilmis_olabilir": False, "worklist_parse_fallback": fallback, "hata": None}],
         "bulgular": bulgular}
    (tmp_w / ad).write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    return r, str(tmp_w / ad)


def kiyas_ic(a, b_):
    o = io.StringIO()
    with redirect_stdout(o):
        rc = A.main(["karsilastir", "--once", a, "--sonra", b_])
    return rc, o.getvalue()


r_fb, p_fb = rapor_r("fb.json", [], fallback=True)
_, p_o = rapor_r("o.json", once)
kontrol("W1 worklist fallback + 0 bulgu → çıkış 4 (sahte-temiz 0 DEĞİL)", A.rapor_cikis_kodu(r_fb) == 4,
        f"{A.rapor_cikis_kodu(r_fb)}")
rc, o = kiyas_ic(p_o, p_fb)
kontrol("W2 sonra raporu fallback'li → KIYAS EKSIK + çıkış 1 (3 bulgu 'çözülen' sayılmaz)",
        rc == 1 and "KIYAS EKSIK" in o and "worklist" in o, f"rc={rc} {o[-300:]!r}")
_, p_q = rapor_r("q.json", sonra, hedef="ZSD001_Q")
rc, o = kiyas_ic(p_o, p_q)
kontrol("Q1 P paketi ↔ Q paketi → KIYAS EKSIK (hedef kümesi) + çıkış 1",
        rc == 1 and "KIYAS EKSIK" in o and "hedef kumesi" in o, f"rc={rc} {o[-300:]!r}")
_, p_v = rapor_r("v.json", sonra, variant="V2", tavan=100)
rc, o = kiyas_ic(p_o, p_v)
kontrol("Q2 variant + tavan farkı → KIYAS EKSIK ×2 + çıkış 1",
        rc == 1 and "variant farkli" in o and "tavan farkli" in o, f"rc={rc} {o[-300:]!r}")
_, p_s = rapor_r("s.json", sonra)
rc, o = kiyas_ic(p_o, p_s)
kontrol("Q3 kontrol grubu: aynı koşul, tam rapor → çıkış 0, KIYAS EKSIK yok, KAPSAM sınırı basılır",
        rc == 0 and "KIYAS EKSIK" not in o and "SINIR:" in o and "uye_kaymasi=0" in o, f"rc={rc} {o[-300:]!r}")

# ── Z: zaman aşımı ortam değişkeni (topla CLI yolu, sahte koşucu) ─────────────
tmp = Path(tempfile.mkdtemp(prefix="atcfx_"))
import os  # noqa: E402
_gorulen = []
A._varsayilan_kosucu = lambda ad, tip, v, t: (_gorulen.append(os.environ.get("ADT_TIMEOUT_DEFAULT")),
                                               {"findings": []})[1]


def topla_cli(*ek, ortam=None):
    eski = os.environ.pop("ADT_TIMEOUT_DEFAULT", None)
    if ortam is not None:
        os.environ["ADT_TIMEOUT_DEFAULT"] = ortam
    try:
        with redirect_stdout(io.StringIO()):
            rc = A.main(["topla", "--paket", "ZSD001_P", "--json", str(tmp / "z.json"), *ek])
        return rc, _gorulen[-1] if _gorulen else None
    finally:
        os.environ.pop("ADT_TIMEOUT_DEFAULT", None)
        if eski is not None:
            os.environ["ADT_TIMEOUT_DEFAULT"] = eski


z1 = topla_cli(ortam="77")
z1b = topla_cli("--zaman-asimi", "300", ortam="77")
kontrol("Z1 NEGATİF: ortamdaki ADT_TIMEOUT_DEFAULT EZİLMEZ (bayraklı/bayraksız)",
        z1 == (0, "77") and z1b == (0, "77"), f"{z1} {z1b}")
kontrol("Z2 ortamda yoksa varsayılan 900 uygulanır", topla_cli() == (0, "900"), f"{_gorulen}")
kontrol("Z3 --zaman-asimi 300 (ortam boş) → 300", topla_cli("--zaman-asimi", "300") == (0, "300"),
        f"{_gorulen}")

# ── V: CSV ───────────────────────────────────────────────────────────────────
bl = z([b(SINIF + "#start=3,0", G1, 'Mesaj; noktalı virgül ve "tırnak"'), b(SINIF_B + "#start=4,0", G2, "İkinci Ş")])
A.kume_no_ata(bl, A.kumele(bl))
A.csv_yaz(bl, tmp / "x.csv")
ham = (tmp / "x.csv").read_bytes()
metin = ham.decode("utf-8-sig")
import csv as _csv  # noqa: E402
satirlar = list(_csv.reader(io.StringIO(metin), delimiter=";"))
kontrol("V1 CSV: BOM + ';' + CRLF yok + başlık + alan kaçışı",
        ham.startswith(b"\xef\xbb\xbf") and b"\r" not in ham and satirlar[0] == A.CSV_SUTUNLAR
        and len(satirlar) == 3 and satirlar[1][2] == 'Mesaj; noktalı virgül ve "tırnak"', f"{satirlar[:2]}")

# ── R: yeniden kullanım kablosu (run_atc_check) ──────────────────────────────
alt = subprocess.run([sys.executable, "-c", (
    "import sys; sys.path.insert(0, %r)\n"
    "import run_atc_check as r\n"
    "class L:\n"
    "    def run_atc_check(self, u, variant, max_verdicts): return {'u': u, 'v': variant, 'm': max_verdicts}\n"
    "class C: adt_client = L()\n"
    "print('R1=' + repr(r.atc_bulgulari('ZSD001_P', 'package', 'V9', max_verdicts=4321, client=C())))\n"
) % str(KOK / "scripts")], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
kontrol("R1 atc_bulgulari: paket URL + varyant + max_verdicts lib'e AYNEN",
        "R1={'u': '/sap/bc/adt/packages/zsd001_p', 'v': 'V9', 'm': 4321}" in alt.stdout,
        f"rc={alt.returncode} {alt.stdout[-200:]!r} {alt.stderr[-200:]!r}")

# ── B: gerçek CLI (3. bağlam) ────────────────────────────────────────────────
if KIP:
    print("  [ATLANDI] B1 — mutasyon kipinde (alt süreç gerçek aracı koşar, mutasyonu görmez)")
else:
    def rapor_yaz(ad, bulgular, kesik=False):
        r = {"_surum": "x", "variant": "DEFAULT", "tavan": 3, "muaf_bulgular": "DAHIL DEGIL",
             "hedefler": [{"hedef": "ZSD001_P", "tip": "package", "bulgu_sayisi": len(bulgular),
                           "kesilmis_olabilir": kesik, "worklist_parse_fallback": False, "hata": None}],
             "bulgular": bulgular}
        (tmp / ad).write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        return str(tmp / ad)

    def cli(*a):
        p = subprocess.run([sys.executable, str(ARAC), *a], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        return p.returncode, p.stdout + p.stderr

    ao, as_ = rapor_yaz("o.json", once), rapor_yaz("s.json", sonra)
    rc1, o1 = cli("kume", "--girdi", ao, "--csv", str(tmp / "k.csv"))
    rc2, o2 = cli("karsilastir", "--once", ao, "--sonra", as_, "--csv", str(tmp / "d.csv"))
    (tmp / "bozuk.json").write_text("{yok", encoding="utf-8")
    rc3, o3 = cli("kume", "--girdi", str(tmp / "bozuk.json"))
    ak = rapor_yaz("k.json", once, kesik=True)
    rc4, o4 = cli("karsilastir", "--once", ak, "--sonra", as_)
    kontrol("B1 CLI: kume rc0 + KAPSAM · karsilastir satır kaymasında 0/3/0 · bozuk girdi rc2 · "
            "kesik raporda KIYAS EKSIK rc1",
            rc1 == 0 and "KAPSAM:" in o1 and "SONUC: 3 bulgu · 2 kume" in o1
            and rc2 == 0 and "cozulen=0 · kalan=3 · yeni=0" in o2 and (tmp / "d.csv").exists()
            and rc3 == 2 and "[KULLANIM]" in o3 and rc4 == 1 and "KIYAS EKSIK" in o4,
            f"rc={rc1},{rc2},{rc3},{rc4} | {o1[-150:]!r} | {o2[-200:]!r} | {o4[-150:]!r}")

# ── rapor ────────────────────────────────────────────────────────────────────
print(f"atc_toplu_ayiklama{(' ' + KIP) if KIP else ''}")
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
gecen = sum(1 for _, ok, _ in SONUC if ok)
print(f"TOPLAM: {gecen}/{len(SONUC)} PASS")
sys.exit(0 if gecen == len(SONUC) else 1)
