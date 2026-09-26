#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pull_msag_textpool.py — mesaj sınıfı CSV'si / program textpool dosyasını CANLIDAN tazele
(SALT-OKUR SAP; Q352-C, ADR 0016 PULL-BEFORE-EDIT).

NEDEN: `populate_message_class.py` ve `push_textpool.py` TAM PUT yapar ⇒ başka makinede canlıda
değişmiş bir metin, eski yerel dosyayla yapılan yüklemede SESSİZCE ezilir. Kapı
(`hooks/pull_before_edit.py` + eklenti `hooks/_pbe_msag_textpool.py`) bu dosyaların
düzenlenmesini, bu seansta bu araçla çekilmiş olmalarına bağlar.

KULLANIM
    python core/scripts/pull_msag_textpool.py msag     --name ZSD001     --file <messages-*.csv>
    python core/scripts/pull_msag_textpool.py textpool --program ZSD001_P_X --file <…/textpool/*.txt>
      ortak: [--session <sid>] [--dry-run] [--force] [--offline]
    `--session`: kapının blok mesajındaki komut bunu HOOK'un session_id'siyle zaten taşır
    (kapı ekler) — komutu olduğu gibi kopyala. Elle koşarken verilmezse
    `.claude/.current_session` marker'ına düşülür; aynı projede iki oturum açıksa marker
    ÖTEKİ oturumu gösterebilir → damga yanlış seansa gider, kapı bloklamaya devam eder.
    Proje kökü TEK kaynaktan: `CLAUDE_PROJECT_DIR` → cwd (`.conn_adt`, `source_root` ve damga
    store'u AYNI kökten). `--cwd` seçeneği bilerek YOK (Q352 bug-gate L4): yalnız `.conn_adt`'yi
    taşıyordu, damga store'u ise başka köke düşüyordu (kapı bloklamaya devam ederdi);
    kardeş `sap_sync_pull` da `--cwd` taşımaz.

BİRLEŞTİRME KURALI (lider/kullanıcı kararı 2026-09-26 — iki tür için AYNI):
  · canlıda olup yerelde olmayan girdi → dosyanın SONUNA eklenir (başka makinede eklenen gelsin)
  · yerelde olup canlıda olmayan girdi → DOKUNULMAZ, raporlanır (yerel WIP olabilir; mesaj
    sınıfında "CSV'de yok" ≠ "canlıdan silinmeli" — tam PUT gövdeden çıkarılanı SİLMEZ)
  · ikisinde de olan girdi → metin/bayrak canlıdan güncellenir, satır YERİNDE kalır
  · girdi SIRASI, ayraç/tırnak biçimi, kodlama (BOM dahil), satır sonu KORUNUR
  · anlamca eşitse (güncellenen VE eklenen girdi yoksa) dosyaya HİÇ yazılmaz, yalnız damga
    atılır — bayt farkı (ör. karışık satır sonu) tek başına yazma sebebi DEĞİLDİR
  · textpool: canlıdaki `=?...` / `=?` yer tutucuları (metinsiz seçim) YOK sayılır, yazılmaz
  · msag: canlıda metni BOŞ mesaj CSV'ye EKLENMEZ (populate `MesajSatiriEksikError` ile tüm
    dosyayı reddederdi) → `[ATLANDI]` raporlanır, damga atılır: populate yalnız CSV'deki
    msgno'ları PUT eder, gövdede olmayan mesaj canlıda DOKUNULMADAN kalır (populate_message_class
    başlığı "CSV'DEN ÇIKARMAK MESAJI SİLMEZ", ölçüldü 2026-09-24) ⇒ ezme riski yok.
    Canlı teyit 2026-09-26 (salt-GET, T100'de metni boş Z mesajı): ADT `('', 'true', 'false')`
    döner → EŞİT + [ATLANDI], sonuç CSV populate okuyucusundan hatasız geçer.
    Aynı msgno yerelde METİNLİ ise → ÖLÇÜLEMEDİ (push canlıdaki boşu ezer; karar insanın).

DAMGA: yalnız karşılaştırma TAM yapıldıysa (`source_drift.tazelik_damgala`, anahtar = DOSYA
yolu). Okuma hatası · paket uyuşmazlığı · aktive edilmemiş canlı değişiklik · ayrıştırılamayan
dosya → ÖLÇÜLEMEDİ: dosyaya dokunulmaz, damga YOK. Tek istisna: açık `--offline` kaçışı
(`sap_sync_pull --offline` ile aynı semantik — SAP'ye gitmeden damgalar, uyarı basar).

NORMALİZASYON (karşılaştırma bu kurallarla yapılır — md5 DEĞİL; ADT gövdesi kapanış satır
sonunu taşımaz):
  msag     : anahtar = msgno.zfill(3) · metin = strip() (populate de strip eder) ·
             selfexplainatory = küçük harf, true/false dışı → false (populate ile aynı).
             `documented` CSV'de TEMSİL EDİLMEZ → KARŞILAŞTIRILMAZ (kapsam beyanında).
  textpool : CRLF/CR → LF · boş satırlar ayraçtır (anlam taşımaz) · `@…` satırları sonraki
             girdiye aittir · girdi anahtarı `=`'den önceki kısım (sağ boşluk kırpılır) ·
             değer `=`'den sonrası AYNEN · girdi sırası anlam taşımaz (ADT alfabetik döner).

ÇIKIŞ KODU: 0 = karşılaştırma TAM (eşit ya da birleştirildi) + damga · --dry-run (damga YOK) ·
            --offline damga · 1 = kullanım hatası · 2 = ÖLÇÜLEMEDİ/durduruldu (dosya DEĞİŞMEDİ,
            damga YOK) · 4 = dosya canlıyla güncel ama damga YAZILAMADI (kapı açılmaz).
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Test/fixture enjeksiyonu: (seans_kimligi, tazelik_damgala) ikilisi. None → source_drift.
DAMGA_ARACLARI = None

TP_ALTLAR = ("selections", "symbols", "headings")
_TP_ADLI_RE = re.compile(r"^(?P<prog>[^.]+)\.(?P<alt>selections|symbols|headings)\.txt$", re.I)
_TP_CIPLAK_RE = re.compile(r"^(?P<alt>selections|symbols|headings)\.txt$", re.I)
_TP_YER_TUTUCU = ("?", "?...")
_PROG_ACCEPT = ("application/vnd.sap.adt.programs.programs.v2+xml, "
                "application/vnd.sap.adt.programs.programs+xml")

KAPSAM_MSAG = (
    "Bakılan: ADT GET /sap/bc/adt/messageclass/<ad> (oturum dilinde; master dil == yanıt dili "
    "şartı) — msgno kümesi + msgtext + selfexplainatory · packageRef (dosyanın paket diziniyle)",
    "BAKILMAYAN: `documented` bayrağı (CSV'de sütunu yok; populate onu sabit 'false' yazar — "
    "ayrı kusur, Q323) · master dil DIŞI çeviriler · uzun metinler (DOKHL) · sınıf açıklaması",
)
KAPSAM_TP = (
    "Bakılan: ADT GET …/textelements/programs/<p>/source/<alt> — çalışma (varsayılan) VE "
    "?version=active sürümü (ikisi farklıysa ÖLÇÜLEMEDİ) · program packageRef · girdi "
    "anahtarı + değer + `@` öznitelik satırları",
    "DİL: okuma OTURUM (login) dilinde; master dil DENETLENMEZ — msag'daki 'yanıt dili == "
    "master' şartının textpool karşılığı yok (uç master dili bildirmez). push_textpool da "
    "oturum dilinde yazar ⇒ ezme karşılaştırması aynı dilde tutarlıdır",
    "BAKILMAYAN: dosyada olmayan diğer alt kaynaklar (her dosya kendi alt kaynağıdır) · "
    "program açıklaması (adtcore:description) · oturum dili DIŞI çeviriler",
    "KALAN RİSK: yanlış `--program` ile KISMİ ortak anahtar kimlik denetimini GEÇER (symbols "
    "anahtarları B01/M01 programlar arasında sık çakışır) → yabancı girdiler birleştirilip "
    "damgalanabilir; çıplak adlı dosyada programı doğrula",
)

# Olası mojibake (UYARI, engel değil): UTF-8 baytlarının latin-1/cp1252 okunması → ikili dizi
# (U+00C3 U+00BC, U+00C4 U+00B1, U+00C5 U+0178 …); cp1254 (Türkçe) baytlarının cp1252 okunması
# → U+00FD U+00FE U+00F0 U+00DD U+00DE U+00D0 (ı ş ğ İ Ş Ğ yerine). Çıplak U+00C2/U+00C3
# ARANMAZ (U+00C2 Türkçede meşru: hâlâ). Kaynakta YALNIZ kaçış biçimi: literal karakter kodlama
# değişiminde sessizce bozulur ve kendi mojibake taramalarımıza takılır.
_MOJIBAKE_RE = re.compile(
    "[\u00c3\u00c4\u00c5][\u0080-\u00bf\u0152\u0153\u0160\u0161\u0178\u017d\u017e"
    "\u2018-\u201e\u2020-\u2022\u2026\u2030\u2039\u203a\u20ac\u2122]"
    "|[\u00fd\u00fe\u00f0\u00dd\u00de\u00d0]")


def _mojibake_uyar(metinler: dict) -> None:
    """{anahtar: metin} → olası mojibake içerenleri UYARI olarak bas (canlıdaki bozukluk
    dosyaya AYNEN taşınır — birleştirme kuralı; kullanıcı görsün)."""
    supheli = sorted(k for k, v in metinler.items() if _MOJIBAKE_RE.search(v or ""))
    if supheli:
        print(f"  [UYARI] canlı metinde olası mojibake (kodlama bozukluğu SAP'de): {supheli} — "
              f"dosyaya AYNEN taşındı; düzeltme canlıda yapılmalı")


class Olculemedi(Exception):
    """Karşılaştırma TAM yapılamadı → dosyaya dokunulmaz, damga YOK (rc 2)."""


# ─────────────────────────────── ortak yardımcılar ───────────────────────────────

def _kapsam_bas(satirlar) -> None:
    for s in satirlar:
        print(f"[KAPSAM] {s}")


def _dosya_oku(dosya: Path) -> tuple[str, dict]:
    """Ham bayt → (LF-normalize metin, biçim). Biçim: bom · satır sonu · sonda satır sonu."""
    ham = dosya.read_bytes()
    bom = ham.startswith(b"\xef\xbb\xbf")
    try:
        metin = ham.decode("utf-8-sig" if bom else "utf-8")
    except UnicodeDecodeError as e:
        raise Olculemedi(f"dosya UTF-8 değil ({e}) — push araçları UTF-8 okur; bu dosya zaten "
                         f"yüklenemez. Kodlamayı düzelt.")
    crlf = metin.count("\r\n")
    lf_ciplak = metin.count("\n") - crlf
    cr_ciplak = metin.count("\r") - crlf
    if crlf and (lf_ciplak or cr_ciplak):
        ss = "\r\n" if crlf >= lf_ciplak else "\n"
        karisik = True
    else:
        ss = "\r\n" if crlf else ("\n" if lf_ciplak else ("\r\n" if not cr_ciplak else "\r"))
        karisik = False
    norm = metin.replace("\r\n", "\n").replace("\r", "\n")
    sonda = norm.endswith("\n")
    govde = norm[:-1] if sonda else norm
    satirlar = govde.split("\n") if govde else []
    return norm, {"bom": bom, "ss": ss, "sonda": sonda, "karisik": karisik,
                  "satirlar": satirlar, "ham": ham,
                  "yeni_satir_yok": not (crlf or lf_ciplak or cr_ciplak)}


def _dosya_bayt(satirlar: list, bicim: dict) -> bytes:
    metin = bicim["ss"].join(satirlar) + (bicim["ss"] if bicim["sonda"] else "")
    b = metin.encode("utf-8")
    return (b"\xef\xbb\xbf" + b) if bicim["bom"] else b


def _git_kirli(dosya: Path) -> bool:
    try:
        r = subprocess.run(["git", "-C", str(dosya.parent), "status", "--porcelain", "--",
                            dosya.name], capture_output=True, text=True, timeout=10)
        return r.returncode == 0 and bool(r.stdout.strip())
    except Exception:
        return False


def _kok_segmentleri() -> set:
    try:
        hooks = str(HERE / "hooks")
        if hooks not in sys.path:
            sys.path.append(hooks)
        from _pbe_msag_textpool import _kok_segmentleri as ks  # type: ignore
        return ks()
    except Exception:
        return {"source_codes", "erp"}


def paket_dizini(dosya: Path) -> Optional[str]:
    """`<source_root>/<MOD>/<PKG>/…` düzeninde PKG adı; düzen dışıysa None.

    SON eşleşen kök segmenti alınır (Q352 bug-gate L3): yolda üstte `ERP/` gibi aynı adlı
    bir dizin olabilir (`ERP/Proj/SOURCE_CODES/SD/<PKG>/…`); ilk eşleşme PKG yerine
    `SOURCE_CODES`'u verir ve araç kalıcı ÖLÇÜLEMEDİ'ye düşerdi."""
    parts = list(Path(dosya).resolve().parts)
    kok = _kok_segmentleri()
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].lower() in kok and len(parts) > i + 3:
            return parts[i + 2].upper()
    return None


def _paket_denetle(dosya: Path, canli_paket: str) -> None:
    beklenen = paket_dizini(dosya)
    if beklenen is None:
        print(f"[UYARI] paket denetimi YAPILAMADI: {dosya} `<source_root>/<MOD>/<PKG>/` düzeninde "
              f"değil — nesne adının doğruluğunu ölçen koruma bu koşumda YOK.")
        return
    if (canli_paket or "").upper() != beklenen:
        raise Olculemedi(f"canlı nesnenin paketi {canli_paket or '?'} ≠ dosyanın paket dizini "
                         f"{beklenen} — yanlış nesne adı olabilir; yazılmadı, damgalanmadı.")


def _kimlik_denetle(yerel: dict, canli: dict, birim: str) -> None:
    """Yerel dolu ama canlıyla ORTAK tek anahtar yoksa dosyanın bu nesneye ait olduğu
    KANITLANAMAZ (yanlış ad · canlıda henüz yok) → ÖLÇÜLEMEDİ. Aksi hâlde başka nesnenin
    dosyası "taze" damgalanır ve asıl nesnesi hiç karşılaştırılmadan düzenlemeye açılırdı
    (ölçüldü: iki programlı pakette çıplak `selections.txt` yanlış `--program` ile rc 0 +
    damga veriyordu). Yeni/boş nesnede bilinçli kaçış: --offline."""
    if yerel and not (set(yerel) & set(canli)):
        raise Olculemedi(
            f"yerel dosyadaki {len(yerel)} {birim} anahtarının HİÇBİRİ canlıda (metinli) "
            f"yok — dosyanın bu "
            f"nesneye ait olduğu kanıtlanamadı (yanlış ad? canlıda henüz yok?). Adı doğrula; "
            f"nesne gerçekten yeniyse bilerek: --offline.")


def _damga_araclari():
    if DAMGA_ARACLARI is not None:
        return DAMGA_ARACLARI
    from source_drift import seans_kimligi, tazelik_damgala  # type: ignore
    return seans_kimligi, tazelik_damgala


def _damgala(session: str, dosya: Path) -> int:
    try:
        seans_kimligi, tazelik_damgala = _damga_araclari()
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] damga yazılamadı: source_drift.tazelik_damgala yüklenemedi "
              f"({type(e).__name__}: {e}) — dosya canlıyla güncel ama kapı açılmaz.")
        return 4
    sid = seans_kimligi(session or "")
    anahtar = tazelik_damgala(sid, dosya)
    if not anahtar:
        print(f"[FAIL] damga yazılamadı ({dosya}) — kapı bu dosyayı 'taze değil' sayar.")
        return 4
    print(f"[DAMGA] seans {sid} · anahtar {anahtar}")
    return 0


def _sonuc_yaz(dosya: Path, eski: bytes, yeni: bytes, dry_run: bool,
               anlamca_degisti: bool = True) -> bool:
    """Değiştiyse yazar (dry-run hariç). Döner: değişti mi.

    `anlamca_degisti=False` (güncellenen VE eklenen girdi yok) → bayt farkı ne olursa olsun
    YAZILMAZ: birleştirme satırları aynen taşır, fark ancak yeniden birleştirmenin biçimidir
    (karışık satır sonu → baskın ayraç). Yazmak onaylı 'eşitse yazma' + 'satır sonu korunur'
    kurallarını çiğnerdi (Q352 bug-gate M1)."""
    if not anlamca_degisti or yeni == eski:
        ek = "" if yeni == eski else " (bayt farkı yalnız biçimde — dosya olduğu gibi korundu)"
        print(f"[SONUÇ] EŞİT — dosyaya YAZILMADI.{ek}")
        return False
    if dry_run:
        print("[SONUÇ] FARKLI — --dry-run: dosyaya YAZILMADI.")
        return True
    dosya.write_bytes(yeni)
    print(f"[SONUÇ] YAZILDI: {dosya}")
    return True


# ─────────────────────────────── mesaj sınıfı (CSV) ───────────────────────────────

def csv_satir_ayir(satir: str) -> list:
    """Tek fiziksel CSV satırı → [(değer, tırnaklı_mı), ...]. Kapanmayan tırnak → ValueError."""
    alanlar, i, n = [], 0, len(satir)
    while True:
        if i < n and satir[i] == '"':
            j, parca = i + 1, []
            while True:
                k = satir.find('"', j)
                if k < 0:
                    raise ValueError("kapanmayan tırnak (çok satırlı alan?)")
                parca.append(satir[j:k])
                if k + 1 < n and satir[k + 1] == '"':
                    parca.append('"')
                    j = k + 2
                    continue
                i = k + 1
                break
            alanlar.append(("".join(parca), True))
            if i < n and satir[i] != ",":
                raise ValueError("kapanış tırnağından sonra ayraç yok")
        else:
            k = satir.find(",", i)
            k = n if k < 0 else k
            alanlar.append((satir[i:k], False))
            i = k
        if i >= n:
            return alanlar
        i += 1                                     # virgülü geç
        if i == n:
            alanlar.append(("", False))
            return alanlar


def _alan_yaz(deger: str, tirnakli: bool) -> str:
    if tirnakli or any(c in deger for c in ',"\r\n'):
        return '"' + deger.replace('"', '""') + '"'
    return deger


def _selfexp(ham: str) -> str:
    s = (ham or "").strip().lower()
    return s if s in ("true", "false") else "false"


def csv_modeli(satirlar: list) -> dict:
    """CSV satırları → model. Ayrıştırılamayan/tekrarlı → Olculemedi."""
    if not satirlar:
        raise Olculemedi("CSV boş — başlık satırı yok")
    try:
        baslik = [d.strip() for d, _ in csv_satir_ayir(satirlar[0])]
    except ValueError as e:
        raise Olculemedi(f"başlık satırı ayrıştırılamadı: {e}")
    if "msgno" not in baslik or "msgtext" not in baslik:
        raise Olculemedi(f"başlıkta msgno/msgtext yok: {baslik}")
    ino, imt = baslik.index("msgno"), baslik.index("msgtext")
    ise = baslik.index("selfexplainatory") if "selfexplainatory" in baslik else None
    satir_bilgi, anahtarlar, yarim = [], {}, []
    for no, s in enumerate(satirlar[1:], start=2):
        if not s.strip():
            satir_bilgi.append(None)
            continue
        try:
            alanlar = csv_satir_ayir(s)
            if [d for d, _ in alanlar] != next(csv.reader([s])):
                raise ValueError("csv modülüyle uyuşmayan ayrıştırma")
        except (ValueError, StopIteration, csv.Error) as e:
            raise Olculemedi(f"satır {no} ayrıştırılamadı ({e}) — satır bazlı birleştirme "
                             f"güvenli değil")
        deg = [d for d, _ in alanlar] + [""] * (len(baslik) - len(alanlar))
        ham_no, metin = deg[ino].strip(), deg[imt].strip()
        if not ham_no:
            yarim.append(no)
            satir_bilgi.append(None)
            continue
        anahtar = ham_no.zfill(3)
        if anahtar in anahtarlar:
            raise Olculemedi(f"msgno {anahtar} iki kez var (satır {anahtarlar[anahtar][0]} ve "
                             f"{no}) — hangisinin yükleneceği belirsiz")
        se = _selfexp(deg[ise]) if ise is not None else "false"
        anahtarlar[anahtar] = (no, metin, se)
        satir_bilgi.append({"anahtar": anahtar, "alanlar": alanlar})
    tirnakli = [b["alanlar"][imt][1] for b in satir_bilgi if b and len(b["alanlar"]) > imt]
    return {"baslik": baslik, "ino": ino, "imt": imt, "ise": ise, "satirlar": satir_bilgi,
            "mesajlar": {k: (v[1], v[2]) for k, v in anahtarlar.items()},
            "sira": list(anahtarlar), "yarim": yarim,
            "tirnak_baskin": (sum(tirnakli) * 2 >= len(tirnakli)) if tirnakli else True}


def msag_birlestir(satirlar: list, canli: dict) -> tuple[list, dict]:
    """(yerel CSV satırları, canlı {no: (metin, selfexp, documented)}) → (yeni satırlar, rapor)."""
    m = csv_modeli(satirlar)
    if m["ise"] is None and any(v[1] == "true" for v in canli.values()):
        raise Olculemedi("CSV'de selfexplainatory sütunu yok ama canlıda selfexplainatory=true "
                         "mesaj var — dosya bu bayrağı TEMSİL EDEMEZ")
    c = {no: (v[0].strip(), _selfexp(v[1])) for no, v in canli.items()}
    bosluk = sorted(no for no, v in canli.items() if v[0] != v[0].strip())
    satir_sonlu = sorted(no for no, v in c.items() if "\r" in v[0] or "\n" in v[0])
    if satir_sonlu:
        raise Olculemedi(f"canlı metinde satır sonu var {satir_sonlu} — satır bazlı CSV bu "
                         f"metni tek satırda taşıyamaz")
    # Canlıda metni BOŞ mesaj (Q352 bug-gate M2; T100'de Z sınıflarında ölçüldü): CSV bunu
    # temsil edemez (`NNN,,flag` → populate MesajSatiriEksikError ile TÜM dosyayı reddeder).
    bos_metin = sorted(no for no, v in c.items() if not v[0])
    catisan = [k for k in bos_metin if k in m["mesajlar"] and m["mesajlar"][k][0]]
    if catisan:
        raise Olculemedi(f"canlıda metni BOŞ mesaj(lar) {catisan} yerel CSV'de METİNLİ — CSV "
                         f"boş metni taşıyamaz ve push yereldeki metinle canlıdaki boşu EZER; "
                         f"hangisinin doğru olduğuna karar ver (canlıyı düzelt ya da yereli "
                         f"bilerek koru: --offline)")
    atlanan = [k for k in bos_metin if k not in m["mesajlar"]]
    for k in atlanan:
        del c[k]
    yeni = [satirlar[0]]
    guncel, yerel_yalniz = [], []
    for ham, bilgi in zip(satirlar[1:], m["satirlar"]):
        if not bilgi:
            yeni.append(ham)
            continue
        k = bilgi["anahtar"]
        if k not in c:
            yerel_yalniz.append(k)
            yeni.append(ham)
            continue
        if m["mesajlar"][k] == c[k]:
            yeni.append(ham)
            continue
        alanlar = list(bilgi["alanlar"]) + [("", False)] * (len(m["baslik"]) - len(bilgi["alanlar"]))
        alanlar[m["imt"]] = (c[k][0], alanlar[m["imt"]][1])
        if m["ise"] is not None and m["mesajlar"][k][1] != c[k][1]:
            alanlar[m["ise"]] = (c[k][1], alanlar[m["ise"]][1])
        yeni.append(",".join(_alan_yaz(d, t) for d, t in alanlar))
        guncel.append(k)
    eklenen = sorted(set(c) - set(m["mesajlar"]))
    for k in eklenen:
        alanlar = [("", False)] * len(m["baslik"])
        alanlar[m["ino"]] = (k, False)
        alanlar[m["imt"]] = (c[k][0], m["tirnak_baskin"])
        if m["ise"] is not None:
            alanlar[m["ise"]] = (c[k][1], False)
        yeni.append(",".join(_alan_yaz(d, t) for d, t in alanlar))
    return yeni, {"guncel": guncel, "eklenen": eklenen, "yerel_yalniz": yerel_yalniz,
                  "yarim": m["yarim"], "bosluk": bosluk, "model": m, "canli_norm": c,
                  "atlanan": atlanan}


def msag_oz_denetim(yeni: list, rapor: dict) -> list:
    """Yazmadan ÖNCE: yeni CSV'yi geri ayrıştır, birleştirme değişmezlerini ölç (boş = tamam)."""
    hatalar = []
    try:
        y = csv_modeli(yeni)
    except Olculemedi as e:
        return [f"üretilen CSV ayrıştırılamadı: {e}"]
    eski, c = rapor["model"], rapor["canli_norm"]
    for k, v in c.items():
        if y["mesajlar"].get(k) != v:
            hatalar.append(f"{k}: yeni dosyada {y['mesajlar'].get(k)} ≠ canlı {v}")
    for k in rapor["yerel_yalniz"]:
        if y["mesajlar"].get(k) != eski["mesajlar"][k]:
            hatalar.append(f"{k}: yalnız-yerel satır DEĞİŞMİŞ")
    if y["sira"][: len(eski["sira"])] != eski["sira"]:
        hatalar.append("mevcut satırların SIRASI değişmiş")
    if set(y["mesajlar"]) != set(eski["mesajlar"]) | set(c):
        hatalar.append("anahtar kümesi yerel ∪ canlı değil")
    return hatalar


def msag_pull(client, name: str, dosya: Path, dry_run=False, force=False,
              session: str = "") -> int:
    name = name.upper()
    print(f"[PULL] MSAG {name} ↔ {dosya}")
    try:
        norm, bicim = _dosya_oku(dosya)
        if not dry_run and not force and _git_kirli(dosya):
            raise Olculemedi("dosyada commit'lenmemiş değişiklik var — pull onu EZEBİLİR. "
                             "Bilerek ezmek için --force (ya da önce --dry-run ile bak).")
        # populate import anında (win32) sys.stdout'u YENİ bir sarmalayıcıyla değiştirir →
        # eskisinin tamponundaki `[PULL]` başlığı pipe'ta kaybolur (Q352 bug-gate L1) ⇒ önce boşalt.
        sys.stdout.flush()
        import populate_message_class as pmc  # noqa: E402 — lazy: --offline SAP'siz koşar
        dil = getattr(client, "language", None) or ""
        try:
            durum, govde = pmc.sinif_oku(client, name, dil or None)
        except Exception as e:  # noqa: BLE001
            raise Olculemedi(f"canlı okuma istisnası ({type(e).__name__}: {e})")
        if durum != 200:
            raise Olculemedi(f"canlı mesaj sınıfı okunamadı (HTTP {durum})")
        try:
            canli = pmc.sinif_xml_ayristir(govde)
        except Exception as e:  # noqa: BLE001
            raise Olculemedi(f"canlı yanıt ayrıştırılamadı ({type(e).__name__}: {e})")
        if canli["name"].upper() != name:
            raise Olculemedi(f"yanıttaki sınıf adı {canli['name']!r} ≠ {name!r}")
        ml, yd = canli["masterLanguage"].upper(), canli["language"].upper()
        if not ml or ml != yd:
            raise Olculemedi(f"yanıt dili {yd or '?'} ≠ master dil {ml or '?'} — metinler "
                             f"master dilde değil; oturumu master dilde aç")
        _paket_denetle(dosya, canli["package"])
        yeni, rapor = msag_birlestir(bicim["satirlar"], canli["messages"])
        _kimlik_denetle(rapor["model"]["mesajlar"], rapor["canli_norm"], "msgno")
        hatalar = msag_oz_denetim(yeni, rapor)
        if hatalar:
            raise Olculemedi("birleştirme öz-denetimi TUTMADI:\n  - " + "\n  - ".join(hatalar))
    except Olculemedi as e:
        print(f"[ÖLÇÜLEMEDİ] {e}\n  → dosyaya DOKUNULMADI, damga YOK.")
        _kapsam_bas(KAPSAM_MSAG)
        return 2
    print(f"  canlı {len(canli['messages'])} mesaj · yerel {len(rapor['model']['mesajlar'])} "
          f"mesaj satırı")
    ortak = len(set(rapor["model"]["mesajlar"]) & set(rapor["canli_norm"]))
    print(f"  güncellenen: {len(rapor['guncel'])}/{ortak} ortak msgno "
          f"{rapor['guncel'] or '-'} (eşik YOK — oran yalnız bilgi)")
    print(f"  eklenen (canlıda var, yerelde yoktu → sona): {rapor['eklenen'] or '-'}")
    print(f"  yalnız-yerel (canlıda YOK → dosyada bırakıldı, yazılmadı): "
          f"{rapor['yerel_yalniz'] or '-'}")
    if rapor["yarim"]:
        print(f"  [UYARI] msgno'su boş satır(lar) {rapor['yarim']} dokunulmadan bırakıldı "
              f"(populate bunları zaten reddeder)")
    if rapor["bosluk"]:
        print(f"  [UYARI] canlı metinde baş/son boşluk: {rapor['bosluk']} — CSV yolu taşıyamaz "
              f"(populate strip eder); strip'li kıyaslandı")
    if rapor["atlanan"]:
        print(f"  [ATLANDI] canlıda metni BOŞ mesaj(lar) {rapor['atlanan']} CSV'ye EKLENMEDİ — "
              f"CSV boş metni taşıyamaz (populate tüm dosyayı reddederdi). Push onlara "
              f"dokunmaz (tam PUT gövdede olmayanı silmez) ⇒ damga engellenmez")
    if bicim["karisik"]:
        print("  [UYARI] dosyada karışık satır sonu — yazılırsa baskın biçim kullanılır")
    degisen = rapor["guncel"] + rapor["eklenen"]
    _mojibake_uyar({k: rapor["canli_norm"][k][0] for k in degisen})
    _kapsam_bas(KAPSAM_MSAG)
    _sonuc_yaz(dosya, bicim["ham"], _dosya_bayt(yeni, bicim), dry_run,
               anlamca_degisti=bool(degisen))
    if dry_run:
        print("[DRY-RUN] damga ATILMADI.")
        return 0
    return _damgala(session, dosya)


# ─────────────────────────────── program textpool ───────────────────────────────

def tp_ayristir(satirlar: list) -> list:
    """Textpool satırları → öğe listesi: ('bos', satır) | ('girdi', anahtar, [satırlar], değer, attr)."""
    ogeler, bekleyen, gorulen = [], [], set()
    for no, s in enumerate(satirlar, start=1):
        if not s.strip():
            if bekleyen:
                raise Olculemedi(f"satır {no}: `@` satırından sonra girdi gelmedi")
            ogeler.append(("bos", s))
            continue
        if s.startswith("@"):
            bekleyen.append(s)
            continue
        if "=" not in s:
            raise Olculemedi(f"satır {no} ayrıştırılamadı (`=` yok): {s[:60]!r}")
        anahtar, deger = s.split("=", 1)
        anahtar = anahtar.rstrip()
        if not anahtar:
            raise Olculemedi(f"satır {no}: anahtar boş")
        if anahtar in gorulen:
            raise Olculemedi(f"anahtar {anahtar!r} iki kez var")
        gorulen.add(anahtar)
        ogeler.append(("girdi", anahtar, bekleyen + [s], deger,
                       tuple(a.rstrip() for a in bekleyen)))
        bekleyen = []
    if bekleyen:
        raise Olculemedi("dosya sonunda sahipsiz `@` satırı")
    return ogeler


def _tp_sozluk(ogeler: list, yer_tutucusuz: bool = False) -> dict:
    d = {}
    for o in ogeler:
        if o[0] != "girdi":
            continue
        if yer_tutucusuz and o[3].strip() in _TP_YER_TUTUCU:
            continue
        d[o[1]] = (o[4], o[3])
    return d


def tp_birlestir(yerel_satirlar: list, canli_satirlar: list) -> tuple[list, dict]:
    yerel = tp_ayristir(yerel_satirlar)
    canli = tp_ayristir(canli_satirlar)
    c = _tp_sozluk(canli, yer_tutucusuz=True)
    c_ogeler = {o[1]: o for o in canli if o[0] == "girdi"}
    y = _tp_sozluk(yerel)
    # Girdi ayracı (boş satır mı?): yerelde en az İKİ girdi varsa yerelin kendi biçimi,
    # yoksa (tek/sıfır girdi — kanıt yok) canlının biçimi.
    ayrac_bos = any(o[0] == "bos" for o in yerel) \
        if sum(o[0] == "girdi" for o in yerel) >= 2 \
        else any(not s.strip() for s in canli_satirlar)
    yeni, guncel, yerel_yalniz = [], [], []
    for o in yerel:
        if o[0] == "bos":
            yeni.append(o[1])
            continue
        k = o[1]
        if k not in c:
            yerel_yalniz.append(k)
            yeni.extend(o[2])
        elif y[k] == c[k]:
            yeni.extend(o[2])
        else:
            yeni.extend(c_ogeler[k][2])
            guncel.append(k)
    eklenen = [o[1] for o in canli if o[0] == "girdi" and o[1] in c and o[1] not in y]
    for k in eklenen:
        if yeni and ayrac_bos and yeni[-1].strip():
            yeni.append("")
        yeni.extend(c_ogeler[k][2])
    yer_tutucu = sorted(o[1] for o in canli if o[0] == "girdi" and o[1] not in c)
    return yeni, {"guncel": guncel, "eklenen": eklenen, "yerel_yalniz": yerel_yalniz,
                  "yer_tutucu": yer_tutucu, "yerel": y, "canli": c,
                  "yerel_sira": [o[1] for o in yerel if o[0] == "girdi"]}


def tp_oz_denetim(yeni: list, rapor: dict) -> list:
    hatalar = []
    try:
        ogeler = tp_ayristir(yeni)
    except Olculemedi as e:
        return [f"üretilen dosya ayrıştırılamadı: {e}"]
    d = _tp_sozluk(ogeler)
    for k, v in rapor["canli"].items():
        if d.get(k) != v:
            hatalar.append(f"{k}: yeni dosyada {d.get(k)} ≠ canlı {v}")
    for k in rapor["yerel_yalniz"]:
        if d.get(k) != rapor["yerel"][k]:
            hatalar.append(f"{k}: yalnız-yerel girdi DEĞİŞMİŞ")
    sira = [o[1] for o in ogeler if o[0] == "girdi"]
    if sira[: len(rapor["yerel_sira"])] != rapor["yerel_sira"]:
        hatalar.append("mevcut girdilerin SIRASI değişmiş")
    if set(d) != set(rapor["yerel"]) | set(rapor["canli"]):
        hatalar.append("anahtar kümesi yerel ∪ canlı değil")
    return hatalar


def tp_alt_kaynak(dosya: Path) -> Optional[str]:
    m = _TP_ADLI_RE.match(dosya.name) or _TP_CIPLAK_RE.match(dosya.name)
    return m.group("alt").lower() if m else None


def _yanit_metni(r) -> str:
    icerik = getattr(r, "content", None)
    if isinstance(icerik, (bytes, bytearray)):
        return bytes(icerik).decode("utf-8")
    return r.text or ""


def _tp_oku(client, program: str, alt: str, aktif: bool) -> list:
    from push_textpool import SUB_CTYPE  # noqa: E402 — tek kaynak: yazma aracının tip tablosu
    url = (f"{client.url.rstrip('/')}/sap/bc/adt/textelements/programs/{program.lower()}"
           f"/source/{alt}" + ("?version=active" if aktif else ""))
    try:
        r = client._request_with_csrf_retry(
            "get", url, headers=client._get_headers(accept_type=SUB_CTYPE[alt]), timeout=30)
        metin = _yanit_metni(r)
    except Exception as e:  # noqa: BLE001
        raise Olculemedi(f"{alt} ({'active' if aktif else 'çalışma'}) okunamadı "
                         f"({type(e).__name__}: {e})")
    if r.status_code != 200:
        raise Olculemedi(f"{alt} ({'active' if aktif else 'çalışma'}) HTTP {r.status_code}")
    norm = metin.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    return norm.split("\n") if norm else []


def _program_paketi(client, program: str) -> str:
    url = f"{client.url.rstrip('/')}/sap/bc/adt/programs/programs/{program.lower()}"
    try:
        r = client._request_with_csrf_retry(
            "get", url, headers=client._get_headers(accept_type=_PROG_ACCEPT), timeout=30)
        metin = _yanit_metni(r)
    except Exception as e:  # noqa: BLE001
        raise Olculemedi(f"program meta verisi okunamadı ({type(e).__name__}: {e})")
    if r.status_code != 200:
        raise Olculemedi(f"program {program} canlıda okunamadı (HTTP {r.status_code})")
    m = re.search(r"<adtcore:packageRef\b[^>]*\badtcore:name=\"([^\"]+)\"", metin)
    if not m:
        raise Olculemedi("program yanıtında packageRef yok")
    return m.group(1)


def textpool_pull(client, program: str, dosya: Path, dry_run=False, force=False,
                  session: str = "") -> int:
    program = program.upper()
    alt = tp_alt_kaynak(dosya)
    print(f"[PULL] TEXTPOOL {program}/{alt or '?'} ↔ {dosya}")
    try:
        if not alt:
            raise Olculemedi("dosya adından alt kaynak (selections/symbols/headings) çıkmıyor")
        m = _TP_ADLI_RE.match(dosya.name)
        if m and m.group("prog").upper() != program:
            raise Olculemedi(f"dosya adı {m.group('prog').upper()} programına ait ≠ --program "
                             f"{program}")
        _norm, bicim = _dosya_oku(dosya)
        if not dry_run and not force and _git_kirli(dosya):
            raise Olculemedi("dosyada commit'lenmemiş değişiklik var — pull onu EZEBİLİR. "
                             "Bilerek ezmek için --force (ya da önce --dry-run ile bak).")
        _paket_denetle(dosya, _program_paketi(client, program))
        calisma = _tp_oku(client, program, alt, aktif=False)
        aktif = _tp_oku(client, program, alt, aktif=True)
        if _tp_sozluk(tp_ayristir(calisma), True) != _tp_sozluk(tp_ayristir(aktif), True):
            raise Olculemedi("canlıda AKTİVE EDİLMEMİŞ textpool değişikliği var (çalışma ≠ "
                             "active) — hangisinin korunacağı belirsiz; önce aktivasyonu çöz")
        yeni, rapor = tp_birlestir(bicim["satirlar"], calisma)
        _kimlik_denetle(rapor["yerel"], rapor["canli"], "girdi")
        hatalar = tp_oz_denetim(yeni, rapor)
        if hatalar:
            raise Olculemedi("birleştirme öz-denetimi TUTMADI:\n  - " + "\n  - ".join(hatalar))
    except Olculemedi as e:
        print(f"[ÖLÇÜLEMEDİ] {e}\n  → dosyaya DOKUNULMADI, damga YOK.")
        _kapsam_bas(KAPSAM_TP)
        return 2
    print(f"  canlı {len(rapor['canli'])} girdi (+{len(rapor['yer_tutucu'])} yer tutucu yok "
          f"sayıldı: {rapor['yer_tutucu'] or '-'}) · yerel {len(rapor['yerel'])} girdi")
    ortak = len(set(rapor["yerel"]) & set(rapor["canli"]))
    print(f"  güncellenen: {len(rapor['guncel'])}/{ortak} ortak girdi "
          f"{rapor['guncel'] or '-'} (eşik YOK — oran yalnız bilgi)")
    print(f"  eklenen (canlıda var, yerelde yoktu → sona): {rapor['eklenen'] or '-'}")
    print(f"  yalnız-yerel (canlıda YOK/yer tutucu → dosyada bırakıldı): "
          f"{rapor['yerel_yalniz'] or '-'}")
    if bicim["karisik"]:
        print("  [UYARI] dosyada karışık satır sonu — yazılırsa baskın biçim kullanılır")
    degisen = rapor["guncel"] + rapor["eklenen"]
    _mojibake_uyar({k: rapor["canli"][k][1] for k in degisen})
    _kapsam_bas(KAPSAM_TP)
    print(f"[KAPSAM] okunan dil (oturum): {getattr(client, 'language', None) or 'BELİRSİZ'}")
    if bicim["yeni_satir_yok"] and (rapor["eklenen"]):
        bicim = dict(bicim, ss="\r\n")               # tek satırlık dosya: ADT biçimi (CRLF)
    _sonuc_yaz(dosya, bicim["ham"], _dosya_bayt(yeni, bicim), dry_run,
               anlamca_degisti=bool(degisen))
    if dry_run:
        print("[DRY-RUN] damga ATILMADI.")
        return 0
    return _damgala(session, dosya)


# ─────────────────────────────── giriş noktası ───────────────────────────────

def _istemci():
    from sap_adt_lib import SAPADTClient  # noqa: E402 — kök: CLAUDE_PROJECT_DIR → cwd
    return SAPADTClient()


def main(argv=None, client=None) -> int:
    ap = argparse.ArgumentParser(description="Mesaj sınıfı CSV / textpool dosyasını canlıdan "
                                             "tazele (salt-okur SAP) + seans-taze damgala")
    alt = ap.add_subparsers(dest="tur", required=True)
    for ad, nesne in (("msag", "--name"), ("textpool", "--program")):
        p = alt.add_parser(ad)
        p.add_argument(nesne, dest="nesne", default="",
                       help="mesaj sınıfı adı" if ad == "msag" else "program adı")
        p.add_argument("--file", required=True, help="yerel dosya (kapının verdiği yol)")
        p.add_argument("--session", default="",
                       help="seans kimliği (kapının verdiği komut hook session_id'sini "
                            "taşır); boşsa .claude/.current_session marker'ı — iki oturum "
                            "açıksa yanlış seans olabilir")
        p.add_argument("--dry-run", action="store_true",
                       help="karşılaştır + raporla; YAZMA ve DAMGA yok")
        p.add_argument("--force", action="store_true",
                       help="commit'lenmemiş yerel değişikliği bilerek EZ")
        p.add_argument("--offline", action="store_true",
                       help="SAP'den ÇEKMEDEN taze damgala (escape; ezme riskini kabul)")
    a = ap.parse_args(argv)
    dosya = Path(a.file)
    if a.offline:
        if not dosya.is_file():
            print(f"[FAIL] --offline: damgalanacak dosya yok: {dosya}")
            return 1
        rc = _damgala(a.session, dosya.resolve())
        if rc == 0:
            print(f"[OFFLINE] {dosya} fetch YAPILMADI, seans-taze damgalandı. DİKKAT: canlıdaki "
                  f"belgelenmemiş değişikliği ezme riskini kabul ettin.")
        return rc
    if not a.nesne or a.nesne.startswith("<"):
        print(f"[FAIL] {'--name' if a.tur == 'msag' else '--program'} gerekli (yer tutucu "
              f"değil, gerçek ad) — hiçbir şey okunmadı/yazılmadı.")
        return 1
    if not a.nesne[:1].upper() in ("Z", "Y"):
        print(f"[FAIL] yalnız Z/Y nesne: {a.nesne}")
        return 1
    if not dosya.is_file():
        print(f"[FAIL] dosya yok: {dosya} (yeni dosyaysa çekecek bir şey yok — kapı da muaf tutar)")
        return 1
    dosya = dosya.resolve()
    if client is None:
        try:
            client = _istemci()
        except Exception as e:  # noqa: BLE001
            print(f"[ÖLÇÜLEMEDİ] SAP istemcisi kurulamadı ({type(e).__name__}: {e}) — dosyaya "
                  f"DOKUNULMADI, damga YOK. SAP erişilemiyorsa: aynı komuta --offline ekle.")
            return 2
    fn = msag_pull if a.tur == "msag" else textpool_pull
    return fn(client, a.nesne, dosya, dry_run=a.dry_run, force=a.force, session=a.session)


if __name__ == "__main__":
    raise SystemExit(main())
