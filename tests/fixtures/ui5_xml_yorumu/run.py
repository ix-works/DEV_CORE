# -*- coding: utf-8 -*-
"""ui5_xml_yorumu — `check_ui5_freestyle_traps` XML dalı YORUM-DURUMU (Q386; T2/T3/T4).

KÖK (2026-11-02): XML dalı `<!-- … -->` yorumlarını ayıklamadan tarıyordu.
  · T4 (ERROR, build DURUR): `_T4_FIELDS_RE` ham içerikte koşuyordu. Yorumdaki
    `<f:fields>` metni bir sonraki GERÇEK `</f:fields>`'e kadar eşleşir ⇒ aradaki
    form-DIŞI `VBox`/`HBox`/`Panel` T4 sayılır (yanlış-pozitif ERROR). Şablon/örnek
    yorumu yazan geliştirici yorumu değiştirerek kapıyı atlatmaya itilir.
  · T2/T3 (WARN): ham SATIR bazlı; yorum içindeki `type="Number"` / `<core:Title`
    uyarı üretiyordu (2026-08-28 B2-06 turunda "bilinen sınır" olarak bırakılmıştı).
DÜZELTME: XML içeriği taramadan önce `_xml_yorum_maskele` ile maskelenir — yorumun
satır sonu DIŞINDAKİ her karakteri boşluk olur ⇒ satır sayısı ve ofsetler AYNI kalır,
basılan satır numarası ham dosyayla birebirdir. (Aynı maskeleme `checklist_check._xml_kod`
içinde FE-07/FE-33 için zaten vardı — üçüncü otorite.)

⚠ POZİTİF KONTROL OMURGADIR: K* gerçek ihlaller · E* yorumla AYNI satırdaki / yorum
  KAPANDIKTAN sonraki gerçek ihlal (maskeleme yorumun dışına taşmıyor, körleşme yok) ·
  K4b satır numarası çok-satırlı yorumdan sonra DOĞRU · U1 kapanmamış `<!--` bilinçli
  sınırdır (maskelenmez ⇒ uyarı KALIR; fail-closed yön).
⚠ ÜÇÜNCÜ BAĞLAM: N4c/K4c — fragment dosyası (`view/fragments/*.fragment.xml`), `form:`
  öneki, CRLF satır sonu (bayt olarak yazılır; `write_text` Windows'ta LF'yi CRLF'ye
  çevirip ekseni öldürürdü).

Koşum:     python tests/fixtures/ui5_xml_yorumu/run.py
MUTASYON:  python tests/fixtures/ui5_xml_yorumu/run.py --mutasyon-maske-yok
           Gerçek `main()` bir sarmalayıcıdan koşulur, `_xml_yorum_maskele` kimlik
           fonksiyonuyla değiştirilir (eski ham-içerik davranışı). ÖNCE aynı sarmalayıcı
           YAMASIZ koşulur (kum tabanı tam yeşil olmalı). İLAN EDİLEN düşüş kümesi:
           {N2a, N2b, N3, N4a, N4b, N4c} — K*/E*/U1/S1/N0 AYAKTA kalmalı.
           Çıkış: 1 = yalnız ilan edilen küme düştü · 2 = SAPMA · 3 = kurulamadı.
Kontrol grubu: `UI5_GATE_KOK=<validators dizini>` ile başka bir sürüm koşulabilir
           (düzeltme öncesi kod: N2a/N2b/N3/N4a/N4b/N4c FAIL — 2026-11-02 ölçüldü).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
GATE_KOK = Path(os.environ.get("UI5_GATE_KOK") or (KOK / "scripts" / "validators"))
GATE = GATE_KOK / "check_ui5_freestyle_traps.py"

GECERLI_KIP = {"--mutasyon-maske-yok"}
BEKLENEN_DUSEN = {"N2a", "N2b", "N3", "N4a", "N4b", "N4c"}

BULGU_RE = re.compile(r"^\[(İHLAL|UYARI)\] (.+?):(\d+)\s+(T\d)\b", re.M)

SARMALAYICI = r'''
import importlib.util, sys
gate, yamala = sys.argv[1], sys.argv[2] == "1"
spec = importlib.util.spec_from_file_location("check_ui5_freestyle_traps", gate)
U = importlib.util.module_from_spec(spec)
spec.loader.exec_module(U)
if not callable(getattr(U, "_xml_yorum_maskele", None)):
    print("[KURULAMADI] _xml_yorum_maskele bulunamadi (yama noktasi yok)")
    sys.exit(3)
if yamala:
    U._xml_yorum_maskele = lambda metin: metin
sys.argv = [gate]
sys.exit(U.main())
'''

# ── view/fragment iskeletleri ────────────────────────────────────────────────
VIEW_BAS = (
    '<mvc:View controllerName="zdemo.controller.Main"\n'
    '    xmlns:mvc="sap.ui.core.mvc" xmlns="sap.m"\n'
    '    xmlns:f="sap.ui.layout.form" xmlns:core="sap.ui.core">\n'
    '    <Page title="Demo">\n'
    '        <content>\n'
)
VIEW_SON = (
    '        </content>\n'
    '    </Page>\n'
    '</mvc:View>\n'
)
FORM_BAS = (
    '            <f:Form editable="true">\n'
    '                <f:layout><f:ColumnLayout/></f:layout>\n'
    '                <f:formContainers><f:FormContainer><f:formElements>\n'
)
FORM_SON = (
    '                </f:formElements></f:FormContainer></f:formContainers>\n'
    '            </f:Form>\n'
)
GECERLI_ELEMAN = (
    '                    <f:FormElement label="A">\n'
    '                        <f:fields><Input value="{A}"/></f:fields>\n'
    '                    </f:FormElement>\n'
)


def view(govde: str) -> str:
    return VIEW_BAS + govde + VIEW_SON


def form(elemanlar: str) -> str:
    return FORM_BAS + elemanlar + FORM_SON


# ── SENARYOLAR: (kod, dosya-türü, metin, satir-sonu, beklenen bulgular) ──────
# beklenen: [(tuzak, işaret-dizesi)] — satır no işaretin metindeki satırından hesaplanır.
SENARYOLAR: list[tuple[str, str, str, str, list[tuple[str, str]], str]] = []


def ekle(kod, tur, metin, beklenen, aciklama, eol="\n"):
    SENARYOLAR.append((kod, tur, metin, eol, beklenen, aciklama))


# N0 — FP çapası (yorumsuz): form DIŞI VBox + geçerli f:fields → temiz
ekle("N0", "view",
     view('            <VBox>\n' + form(GECERLI_ELEMAN) + '            </VBox>\n'),
     [], "N0 form-dışı VBox + geçerli <f:fields><Input/> → temiz (yorumsuz FP çapası)")

# N4a — Q386 KONTROL GRUBU girdisi: yorumda `<f:fields>`, ardından form-DIŞI VBox
ekle("N4a", "view",
     view('            <!-- not: <f:fields> icine yalniz kontrol koyun -->\n'
          '            <VBox>\n' + form(GECERLI_ELEMAN) + '            </VBox>\n'),
     [], "N4a yorumdaki `<f:fields>` + form-dışı VBox → temiz (Q386 FP, T4 ERROR)")

# N4b — yorum içinde TAM ölü örnek: <f:fields><HBox/></f:fields>
ekle("N4b", "view",
     view('            <!--\n'
          '                YANLIS ORNEK (render-crash):\n'
          '                <f:fields><HBox><Input/><Button/></HBox></f:fields>\n'
          '            -->\n' + form(GECERLI_ELEMAN)),
     [], "N4b çok-satırlı yorumdaki ölü `<f:fields><HBox>` örneği → temiz (T4 ERROR FP)")

# N2a/N2b — T2 yorum FP'si (WARN)
ekle("N2a", "view",
     view('            <!-- eski: <Input type="Number" value="{Q}"/> -->\n'
          '            <Input type="Text" value="{Q}"/>\n'),
     [], "N2a tek satır yorumdaki `type=\"Number\"` → uyarı YOK (T2 FP)")
ekle("N2b", "view",
     view('            <!--\n'
          '                <Input type="Number" value="{Q}"/>\n'
          '            -->\n'
          '            <Input type="Text" value="{Q}"/>\n'),
     [], "N2b çok-satırlı yorumun ORTA satırındaki `type=\"Number\"` → uyarı YOK (T2 FP)")

# N3 — T3 yorum FP'si (WARN)
ekle("N3", "view",
     view('            <!-- <core:Title text="Eski baslik"/> -->\n'
          '            <Title text="Baslik"/>\n'),
     [], "N3 yorumdaki `<core:Title` → uyarı YOK (T3 FP)")

# K* — POZİTİF KONTROL: gerçek ihlaller
ekle("K4", "view",
     view(form('                    <f:FormElement label="B">\n'
               '                        <f:fields><HBox id="K4"><Input/></HBox></f:fields>\n'
               '                    </f:FormElement>\n')),
     [("T4", '<HBox id="K4"')], "K4 POZİTİF KONTROL gerçek `<f:fields><HBox>` → ERROR")
ekle("K4b", "view",
     view('            <!--\n'
          '                satir 1\n'
          '                satir 2\n'
          '                satir 3\n'
          '            -->\n'
          + form('                    <f:FormElement label="B">\n'
                 '                        <f:fields>\n'
                 '                            <VBox id="K4b"><Input/></VBox>\n'
                 '                        </f:fields>\n'
                 '                    </f:FormElement>\n')),
     [("T4", '<VBox id="K4b"')], "K4b çok-satırlı yorumdan SONRA gerçek ihlal → ERROR, satır no DOĞRU")
ekle("K2", "view",
     view('            <Input type="Number" value="{Q}"/>\n'),
     [("T2", 'type="Number"')], "K2 POZİTİF KONTROL gerçek `type=\"Number\"` → WARN")
ekle("K3", "view",
     view('            <VBox><core:Title text="X"/></VBox>\n'),
     [("T3", '<core:Title')], "K3 POZİTİF KONTROL gerçek `<core:Title` → WARN")

# E* — maskeleme yorumun DIŞINA taşmıyor / körleşme yok
ekle("E1", "view",
     view('            <!-- not --> <Input type="Number" value="{Q}"/>\n'),
     [("T2", 'type="Number"')], "E1 yorumla AYNI satırda, yorum KAPANDIKTAN sonra gerçek T2 → WARN")
ekle("E3", "view",
     view('            <!-- <f:fields> -->\n'
          + form('                    <f:FormElement label="B">\n'
                 '                        <f:fields><Panel id="E3"/></f:fields>\n'
                 '                    </f:FormElement>\n')),
     [("T4", '<Panel id="E3"')], "E3 yorumda `<f:fields>` + ardından gerçek ihlal → TEK ERROR, doğru satır")

# U1 — bilinçli sınır: kapanmamış yorum maskelenmez (fail-closed yön)
ekle("U1", "view",
     view('            <!-- kapanmadi <Input type="Number"/>\n'),
     [("T2", 'type="Number"')], "U1 SINIR kapanmamış `<!--` maskelenmez → uyarı KALIR (fail-closed)")

# Üçüncü bağlam: fragment + `form:` öneki + CRLF
FRAG_BAS = ('<core:FragmentDefinition xmlns="sap.m" xmlns:core="sap.ui.core"\n'
            '    xmlns:form="sap.ui.layout.form">\n'
            '    <Dialog title="Demo">\n')
FRAG_SON = '    </Dialog>\n</core:FragmentDefinition>\n'
FRAG_FORM = ('        <form:SimpleForm editable="true">\n'
             '            <form:content><Input/></form:content>\n'
             '        </form:SimpleForm>\n'
             '        <form:Form><form:formContainers><form:FormContainer><form:formElements>\n'
             '            <form:FormElement label="C"><form:fields>{ICERIK}</form:fields></form:FormElement>\n'
             '        </form:formElements></form:FormContainer></form:formContainers></form:Form>\n')
ekle("N4c", "fragment",
     FRAG_BAS + '        <!-- ornek: <form:fields><FlexBox/></form:fields> -->\n'
     '        <FlexBox>\n' + FRAG_FORM.replace("{ICERIK}", "<Input/>") + '        </FlexBox>\n'
     + FRAG_SON,
     [], "N4c 3. BAĞLAM fragment + `form:` öneki + CRLF, yorumdaki örnek → temiz", eol="\r\n")
ekle("K4c", "fragment",
     FRAG_BAS + '        <!--\r\n uzun not\r\n -->\n'
     + FRAG_FORM.replace("{ICERIK}", '<FlexBox id="K4c"/>') + FRAG_SON,
     [("T4", '<FlexBox id="K4c"')], "K4c 3. BAĞLAM fragment + CRLF, yorumdan sonra gerçek ihlal → ERROR, satır no DOĞRU",
     eol="\r\n")


def beklenen_satir(metin: str, isaret: str) -> int:
    i = metin.index(isaret)
    return metin.count("\n", 0, i) + 1


def proje_kur(kok: Path, tur: str, metin: str, eol: str) -> Path:
    web = kok / "SOURCE_CODES" / "SD" / "ZDEMO_PKG" / "ui" / "app" / "webapp"
    if tur == "fragment":
        d, ad = web / "view" / "fragments", "Demo.fragment.xml"
    else:
        d, ad = web / "view", "Main.view.xml"
    d.mkdir(parents=True, exist_ok=True)
    govde = metin.replace("\r\n", "\n").replace("\n", eol) if eol != "\n" else metin
    (d / ad).write_bytes(govde.encode("utf-8"))      # bayt: satır sonu ekseni korunur
    return kok


def kos(proje: Path, mod: str, sarmalayici: Path | None) -> tuple[int, str]:
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    if mod == "gercek":
        argv = [sys.executable, str(GATE)]
    else:
        argv = [sys.executable, str(sarmalayici), str(GATE), "1" if mod == "yamali" else "0"]
    try:
        r = subprocess.run(argv, cwd=str(proje), env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
    except Exception as e:  # noqa: BLE001
        return (-1, f"KOSULAMADI: {type(e).__name__}: {e}")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def degerlendir(kod: str, metin: str, beklenen, rc: int, cikti: str) -> tuple[bool, str]:
    if rc < 0 or rc == 3:
        return False, f"kurulum: rc={rc} {cikti.strip()[-200:]}"
    if "Traceback (most recent call last)" in cikti:
        son = cikti.strip().splitlines()[-1] if cikti.strip() else ""
        return False, f"[ALT-SÜREÇ KAPI ÇÖKTÜ] {son[:160]}"
    alinan = sorted((m.group(4), int(m.group(3))) for m in BULGU_RE.finditer(cikti))
    bekle = sorted((t, beklenen_satir(metin, isaret)) for t, isaret in beklenen)
    hata_bekle = any(t in ("T1", "T4") for t, _ in beklenen)
    rc_ok = (rc == 1) if hata_bekle else (rc == 0)
    ok = rc_ok and alinan == bekle
    return ok, f"rc={rc} alinan={alinan} beklenen={bekle}"


def tur_kos(tmp: Path, mod: str, sarmalayici: Path | None) -> dict[str, tuple[bool, str, str]]:
    sonuc: dict[str, tuple[bool, str, str]] = {}
    for kod, tur, metin, eol, beklenen, ad in SENARYOLAR:
        proje = proje_kur(tmp / f"{mod}_{kod}", tur, metin, eol)
        rc, cikti = kos(proje, mod, sarmalayici)
        ok, detay = degerlendir(kod, metin, beklenen, rc, cikti)
        sonuc[kod] = (ok, ad, detay)
        if kod == "N0":
            # S1 — KAPSAM BEYANI: temiz çıktı T4'ü de anar (eskiden "T1/T2/T3 yok")
            s_ok = rc == 0 and "T1/T2/T3/T4 yok" in cikti
            sonuc["S1"] = (s_ok, "S1 temiz çıktı T4'ü de anar (`T1/T2/T3/T4 yok`)",
                           f"rc={rc} :: {cikti.strip()[:160]}")
    return sonuc


def yazdir(baslik: str, sonuc: dict[str, tuple[bool, str, str]]) -> int:
    print(f"── {baslik}")
    gecen = 0
    for kod, (ok, ad, detay) in sonuc.items():
        gecen += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f" — {detay}"))
    return gecen


def main(argv: list[str]) -> int:
    kip = argv[0] if argv else None
    if kip is not None and kip not in GECERLI_KIP:
        print(f"[KULLANIM] gecersiz kip: {kip} · gecerli: {sorted(GECERLI_KIP)}")
        return 2
    if not GATE.is_file():
        print(f"[KURULAMADI] kapi yok: {GATE}")
        return 3
    tmp = Path(tempfile.mkdtemp(prefix="ui5xml_"))
    try:
        if kip is None:
            sonuc = tur_kos(tmp, "gercek", None)
            gecen = yazdir("taban (gercek giris noktasi)", sonuc)
            print(f"\nui5_xml_yorumu: {gecen}/{len(sonuc)}")
            return 0 if gecen == len(sonuc) else 1

        sarm = tmp / "sarmalayici.py"
        sarm.write_text(SARMALAYICI, encoding="utf-8")
        kum = tur_kos(tmp, "yamasiz", sarm)
        k_gecen = yazdir("kum tabani (sarmalayici, YAMASIZ)", kum)
        if k_gecen != len(kum):
            print(f"\n[KURULAMADI] kum tabani yesil degil ({k_gecen}/{len(kum)}) — "
                  "mutasyon olcumu gecersiz")
            return 3
        mut = tur_kos(tmp, "yamali", sarm)
        m_gecen = yazdir("mutasyon --mutasyon-maske-yok (maskeleme kimlik)", mut)
        dusen = {k for k, (ok, _, _) in mut.items() if not ok}
        print(f"\nui5_xml_yorumu: {m_gecen}/{len(mut)}")
        print(f"ILAN EDILEN: {sorted(BEKLENEN_DUSEN)}")
        print(f"DUSEN:       {sorted(dusen)}")
        if dusen == BEKLENEN_DUSEN:
            print("DUSTU — yalniz ilan edilen vektorler dustu")
            return 1
        print(f"SAPMA — fazla={sorted(dusen - BEKLENEN_DUSEN)} "
              f"eksik={sorted(BEKLENEN_DUSEN - dusen)}")
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
