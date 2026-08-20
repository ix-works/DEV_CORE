# -*- coding: utf-8 -*-
""".conn_adt YAZICI tarafı: kodlama VARSAYILANA bırakılmaz (KAYIT S6).

KÖK: `create_conn_template()` / `create_conn_file()` `write_text(metin)` diyordu — kodlama
İŞLETİM SİSTEMİ LOCALE'İNE kalıyordu (Windows-TR: **cp1252**). Şablon bir em-dash (U+2014)
içerir → cp1252'de tek bayt **0x97**. Dosyanın TÜKETİCİLERİ ise utf-8 / utf-8-sig okur
(sap_adt_lib'in kendi `load_dotenv`'i, MCP `_conn`, `pre_tool_guard`, `project_config`):

    UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in position 388

`load_dotenv(conn_path)` bu modülün İMPORT ANINDA koştuğu için sonuç, o dizinden yapılan
**her `import sap_adt_lib` çağrısının çökmesidir** → canlı-SAP kontrolü yapan validator'lar
"guard atlandı" yoluna düşer. Av sırasında kendiliğinden gerçekleşti (1085 baytlık bozuk dosya).

SINIF: "üretici taraf, tüketicinin sözleşmesine uymuyor" — okuyucular AV-02'de utf-8-sig'e
taşınmıştı, YAZAN taraf geride kalmıştı.

⚠ LOCALE-BAĞIMSIZLIK: bu testin CI'da (UTF-8 locale) da anlamlı olması gerekir. Bu yüzden
V1 nedenselliği cp1252'yi AÇIKÇA yazarak kanıtlar (makinenin locale'ine bağlı değildir) ve
V5 kaynak-metinde açık `encoding=` şartını AST ile arar (mutasyon her ortamda yakalanır).

Koşum:  python tests/fixtures/conn_yazici_encoding/run.py
MUTASYON: `_yaz_conn`'daki `encoding='utf-8'`i kaldır → V5 FAIL (ve cp1252 makinede V2/V3 de).
"""
from __future__ import annotations

import ast
import os
import shutil
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


# sap_adt_lib conn_path'i İMPORT ANINDA cwd/env'den çözer → önce sentetik dizine geç.
KUM = Path(tempfile.mkdtemp(prefix="s6_"))
eski_cwd = os.getcwd()
os.environ["CLAUDE_PROJECT_DIR"] = str(KUM)
os.chdir(KUM)

# ⛔ K4 (2026-08-20) — ÖLÇÜLMÜŞ VERİ KAYBI, "kalıntı" değil:
#   `CLAUDE_PROJECT_DIR` + `chdir` İZOLASYON SAĞLAMAZ. `find_conn_file()` adayları
#   *"dosyanın VAR OLDUĞU ilk yer"* diye seçer; env yalnızca orada dosya VARSA kazanır.
#   Git-bash `PWD`yi repo köküne kurar ⇒ repo kökünde bir `.conn_adt` VARSA (ki süitin
#   `populate_tables_unit_kind` korpusu import yan-etkisiyle bir şablon yazar) hedef
#   oraya kayar ve V4 **KULLANICININ GERÇEK `.conn_adt` DOSYASINI 522 B sentetik
#   TEST_USER verisiyle EZER**. Repro edildi (78 B gerçek → 522 B sentetik).
#   Süitin hijyeni bunu KURTARMAZ: "koşumdan önce vardı" gördüğü için dosyaya
#   dokunmaz — yani ezilmiş dosya olduğu gibi kalır (sessiz, gitignored).
#
# ⇒ İki katmanlı önlem: (1) kütüphanenin KENDİ izolasyon kancası, (2) yazmadan önce
#   hedefin kumda olduğunu KANITLA. (2) olmadan (1) bir gün sessizce bozulur.
for _kacak in ("PWD", "CLAUDE_CWD", "INIT_CWD", "COPILOT_CWD"):
    os.environ.pop(_kacak, None)
sys.path.insert(0, str(KOK / "scripts"))
import sap_adt_lib as L  # noqa: E402

L.set_explicit_working_dir(KUM)     # kütüphanenin belgelenmiş izolasyon kancası

HEDEF = Path(L.get_conn_path())
if not HEDEF.resolve().is_relative_to(KUM.resolve()):
    # SESSİZ GEÇME YOK: buradan sonraki her satır dosyaya KİMLİK YAZAR.
    os.chdir(eski_cwd)
    shutil.rmtree(KUM, ignore_errors=True)
    print(f"  [FAIL] KUM-DIŞI HEDEF: {HEDEF}\n"
          f"         Bu fixture .conn_adt YAZAR; hedef kum değilse gerçek bir kimlik "
          f"dosyası EZİLİR. Yazmadan durdu.")
    sys.exit(1)

# ── V1 — NEDENSELLİK / KONTROL GRUBU: cp1252 yazımı tüketicileri GERÇEKTEN kırar ─
#   (Bu vektör bug'ın var olduğunu kanıtlar; locale'den bağımsızdır.)
L.create_conn_template()
# ⚠ Şablonu DOSYADAN katı utf-8 ile okumak, fix-öncesi kodda testi burada ÇÖKERTİRDİ
# (mutasyon skoru ölçülemezdi). Kanarya/nedensellik için kaynak metni MODÜLDEN alırız;
# dosyanın kendisini okumak V2'nin işidir.
_ham = (KOK / "scripts" / "sap_adt_lib.py").read_text(encoding="utf-8")
_i = _ham.index('    template = """') + len('    template = """')
sablon = _ham[_i:_ham.index('"""', _i)]
bozuk = KUM / "bozuk.conn_adt"
bozuk.write_text(sablon, encoding="cp1252")     # cp1252 makinede write_text(encoding=None) BUDUR
kirildi = False
try:
    bozuk.read_text(encoding="utf-8-sig")
except UnicodeDecodeError:
    kirildi = True
kontrol("V1 NEDENSELLİK: cp1252 yazılan .conn_adt, utf-8-sig okuyucuda UnicodeDecodeError",
        kirildi, f"bayt={len(bozuk.read_bytes())} (kırılmadıysa şablon ASCII'ye inmiş olabilir)")

# ── V2 — create_conn_template() çıktısı utf-8 olarak OKUNABİLİR ────────────────
ok2 = True
try:
    HEDEF.read_text(encoding="utf-8-sig")
except UnicodeDecodeError as e:
    ok2 = False
kontrol("V2 create_conn_template() çıktısı utf-8-sig ile sorunsuz okunuyor", ok2,
        "" if ok2 else "yazıcı hâlâ locale'e bırakıyor")

# ── V3 — KABLOLAMA: ASIL tüketici (dotenv) o dosyayı okuyabiliyor ─────────────
#   sap_adt_lib import-anında load_dotenv çağırır; burada aynı çağrıyı birebir yaparız.
try:
    from dotenv import load_dotenv
    ok3 = bool(load_dotenv(dotenv_path=HEDEF, override=True))
    detay3 = f"load_dotenv={ok3} tier={os.getenv('ADT_SAP_TIER')!r}"
    ok3 = ok3 and os.getenv("ADT_SAP_TIER") == "DEV"
except Exception as exc:  # noqa: BLE001
    ok3, detay3 = False, f"{type(exc).__name__}: {exc}"
kontrol("V3 KABLOLAMA: load_dotenv (import-anı okuyucusu) dosyayı okuyor + tier çözülüyor",
        ok3, detay3)

# ── V4 — 3. BAĞLAM (görev-dışı): create_conn_file non-ASCII değerle round-trip ──
#   Gerçek parolalar/URL'ler non-ASCII taşıyabilir; aynı sınıf oradan da vurur.
try:
    # ⚠ fix-öncesi kod BURADA UnicodeEncodeError ile ÇÖKER (cp1252 bu karakterleri
    # kodlayamaz) — yani sınıfın ikinci yüzü: bozuk dosya değil, doğrudan çökme.
    L.create_conn_file("https://ornek.gecerli:44300", "TEST_USER", "pÄrola-üğş", "100",
                       sap_language="TR", sap_tier="DEV")
    icerik = HEDEF.read_text(encoding="utf-8-sig")
    ok4 = "pÄrola-üğş" in icerik and "ADT_SAP_TIER=DEV" in icerik
    detay4 = f"bayt={len(HEDEF.read_bytes())}"
except (UnicodeDecodeError, UnicodeEncodeError) as e:
    ok4, detay4 = False, f"{type(e).__name__}: {e}"
kontrol("V4 3.BAĞLAM: create_conn_file non-ASCII parolayla utf-8 round-trip", ok4, detay4)

# ── V5 — MUTASYON ÇAPASI (locale-bağımsız): .conn_adt yazan HER çağrı açık encoding'li ─
kaynak = (KOK / "scripts" / "sap_adt_lib.py").read_text(encoding="utf-8")
agac = ast.parse(kaynak)
kacak = []
for d in ast.walk(agac):
    if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
            and d.func.attr == "write_text"):
        if not any(k.arg == "encoding" for k in d.keywords):
            kacak.append(getattr(d, "lineno", "?"))
kontrol("V5 MUTASYON ÇAPASI: sap_adt_lib'de encoding'siz write_text KALMADI",
        not kacak, f"encoding'siz write_text satırları={kacak}")

# ── V6 — KANARYA: şablon hâlâ non-ASCII taşıyor (yoksa test SESSİZCE boşalır) ──
nonascii = sorted({hex(ord(c)) for c in sablon if ord(c) > 127})
kontrol("V6 KANARYA: şablon metni non-ASCII taşıyor (ASCII'ye inerse V1 anlamsızlaşır)",
        bool(nonascii), f"bulunan={nonascii}")

# ── V7 — FP ÇAPASI: dosyaya BOM yazılmıyor (utf-8, utf-8-sig DEĞİL) ───────────
#   BOM eklemek AV-02 sınıfının ta kendisidir; okuyucular utf-8-sig olduğu için ÇALIŞIR
#   ama başka okuyucuları kırar → yazıcı BOM basmamalı.
kontrol("V7 FP ÇAPASI: yazılan dosya BOM ile BAŞLAMIYOR",
        not HEDEF.read_bytes().startswith(b"\xef\xbb\xbf"),
        f"ilk baytlar={HEDEF.read_bytes()[:4]!r}")

# try/finally değil ama ETKİSİ aynı: yukarıdaki her erken çıkış yolunda da geri alınır
# (KUM-dışı hedef dalı kendi temizliğini yapar). Asıl koruma chdir'i geri almak DEĞİL,
# hedefin kumda olduğunu yazmadan ÖNCE kanıtlamaktır — chdir sızıntının sebebi değildi.
os.chdir(eski_cwd)
shutil.rmtree(KUM, ignore_errors=True)

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)
