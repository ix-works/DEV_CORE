# -*- coding: utf-8 -*-
"""overlay_kiyas_tabani — T2.5 ezme-kapısının KIYAS TABANI (kurt masalı sınıfı).

KÖK (2026-08-13 kuyruk kaydı): `claude_overlay.fark_raporu()` mevcut `.claude/<tip>/<ad>.md`
kopyasını **bugün üretilecek** içerikle (core + claude-local) kıyaslıyordu. O taban iki ayrı
olayı ayırt EDEMEZ: (a) core dosyası değişti, (b) kopya elle düzeltildi. Sonuç: core'da bir
ajan dosyası değiştiği an, projede hiçbir elle düzeltme olmasa bile kapı kapanıyor ve
`materyalize()` `--overlay-onayli` olmadan üretmiyordu.

Bedeli ÇİFT katmanlıydı:
  (a) junction'lı tipler (`skills`/`commands`/`rules`) core değişince bedavaya tazelenirken
      yalnız overlay'li tip her core commit'inde tören istiyordu — kusur "kopya olmak"tan
      değil TABAN SEÇİMİNDEN doğuyordu (kontrol grubu: V0);
  (b) kapı her core değişiminde bağırınca `--overlay-onayli` refleks olur; o gün gerçekten
      elle düzeltilmiş bir dosya varsa gate onu SESSİZCE ezer → koruma kendini aşındırır.

FIX: manifest dosya başına `uretilen_hash` (üretilen kopyanın diskteki gerçek hash'i) taşır;
kıyas **kopya-ŞİMDİ ↔ en son ÜRETİLEN** olur. Doğru soru "içerik core'dan farklı mı" değil,
**"kopyaya senkrondan sonra dokunuldu mu"**dur.

ÖLÇÜT (mutasyon etiketi):
  * P → fix'in GETİRDİĞİ ayrım. `--mutasyon` (taban SHA) koşumunda DÜŞMELİ.
  * N → FP çapası: gate'in KORUDUĞU davranış. Her iki mutasyonda da davranışı sabittir;
        `--mutasyon-gevsek` (fix'in sökümü) koşumunda DÜŞMELİ — düşmezlerse korpus
        gevşemeyi ölçmüyor demektir.
  * K → kontrol grubu / kablolama / regresyon çapası.

⚠ N ÇAPALARI OMURGADIR (V3/V4/V6/V7/V9/V10/V11). Bu gate'in var olma sebebi elle yapılmış
proje düzeltmesinin senkronda sessizce kaybolmasını önlemektir. Biri silinirse gevşeme
ölçüsüz kalır. V10/V11 ayrıca GERİYE-UYUM çapasıdır: `uretilen_hash` alanı OLMAYAN eski
manifestli bir proje birebir ESKİ (muhafazakâr) davranışı görmeli — sessiz gevşeme YOK.

⚠ FP ÇAPASI ile AYIRT EDİCİ AYNI VEKTÖRDE BİRLEŞTİRİLMEZ: V2 (core değişti → geç) ile V3
(elle düzeltme → dur) ayrı satırlardır. Birleştirilirse "doğru vaka bozulmadı" kanıtı
sessizce kaybolur.

Koşum:    python tests/fixtures/overlay_kiyas_tabani/run.py
MUTASYON: python tests/fixtures/overlay_kiyas_tabani/run.py --mutasyon [--ref <SHA>]
              → fix ÖNCESİ sürümle koş; P vektörleri DÜŞMELİ, N/K ayakta kalmalı.
          python tests/fixtures/overlay_kiyas_tabani/run.py --mutasyon-gevsek
              → fix'i AŞIRI-GEVŞET (`_uretildigi_gibi` daima True); N vektörleri DÜŞMELİ.
          ⛔ `--ref`e DAL ADI VERME: bu dal merge edilince `origin/main` "fix sonrası"na
          kayar ve korpus ayırt etmiyormuş gibi görünür. Taban SHA'ya pinlidir ve koşucu
          tabanın GERÇEKTEN kusurlu olduğunu ön-doğrular; doğrulayamazsa sayı BASMAZ (exit 2).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
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
if not (KOK / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {KOK}")

MODUL_REL = "scripts/utils/claude_overlay.py"
# Kusurun CANLI olduğu SHA (2026-08-13, `fix(hooks): parse-fail ...` — bu fix'in TABANI).
# Dal adı DEĞİL: merge sonrası hareket etmesin.
TABAN_SHA = "15e9a51"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


# ─────────────────────────────────────────────────────────────────────────────
# Sentetik core + proje kurulumu
# ⚠ Bütün yazımlar newline="\n": Windows'ta varsayılan CRLF yazar ve `durum()`'un
#   CRLF çapası ile karışır → ölçtüğünü sandığın şeyi ölçmezsin.
# ─────────────────────────────────────────────────────────────────────────────
def yaz(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", newline="\n")


def ajan(ad: str, govde: str) -> str:
    return f"---\nname: {ad}\ndescription: sentetik fixture ajani\n---\n\n{govde}\n"


def kur(tmp: Path, etiket: str, tam_core: bool = False) -> tuple[Path, Path]:
    """Sentetik (core, proje) çifti. agents: alpha=core-only, beta=proje-override.

    `tam_core=True` → core köküne `scripts/utils/claude_overlay.py` de kurulur. GEREKLİ:
    `inspector.b5_core_baglantisi` üçlü-kıyas dalında modülü **kendisine verilen core
    kökünden** import eder (`sys.path.insert(core/"scripts")`) ve import'u bare
    `except Exception: pass` ile yutar. Bu iskelet olmadan dal SESSİZCE hiç koşmaz ve
    K16b "bulgular=[]" ile sahte-KIRMIZI verir (ilk koşumda tam bu oldu).
    """
    core = tmp / etiket / "core"
    proj = tmp / etiket / "proje"
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi."))
    yaz(core / "claude" / "agents" / "beta.md", ajan("beta", "Core beta govdesi."))
    yaz(proj / "claude-local" / "agents" / "beta.md", ajan("beta", "PROJE beta govdesi."))
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    if tam_core:
        yaz(core / "scripts" / "utils" / "claude_overlay.py",
            (KOK / MODUL_REL).read_text(encoding="utf-8"))
    return core, proj


def manifest(proj: Path, tip: str = "agents") -> dict:
    return json.loads((proj / ".claude" / tip / ".overlay-manifest.json")
                      .read_text(encoding="utf-8"))


def manifest_yaz(proj: Path, veri: dict, tip: str = "agents") -> None:
    (proj / ".claude" / tip / ".overlay-manifest.json").write_text(
        json.dumps(veri, indent=1, ensure_ascii=False), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# SENARYOLAR
# ─────────────────────────────────────────────────────────────────────────────
def senaryolar(ov, tmp: Path) -> None:
    # ── V0 (K) KONTROL GRUBU: junction'lı tip HİÇ tören istemez ──────────────
    # Kusur "kopya olmak"tan değil taban seçiminden doğuyor. Junction'da fark_raporu
    # daima boştur; bu satır kırmızıya dönerse teşhisin kendisi yanlıştır.
    core, proj = kur(tmp, "v0")
    ov.materyalize(proj, core, "agents")
    # `skills` için claude-local YOK → gerçek kurulumda junction kalır, dizin hiç yoktur.
    kontrol(ov.fark_raporu(proj, core, "skills") == [],
            "V0 (K) kontrol grubu: overlay'siz tip (junction yolu) fark ÜRETMEZ")

    # ── V1 (N) taze üretim temiz ────────────────────────────────────────────
    core, proj = kur(tmp, "v1")
    ok, mesaj = ov.materyalize(proj, core, "agents")
    kontrol(ok and ov.fark_raporu(proj, core, "agents") == [],
            "V1 (N) taze üretim → fark YOK", f"materyalize={ok} {mesaj}")

    # ── V2 (P) ASIL KAYIT: core değişti, kopyaya HİÇ dokunulmadı ────────────
    core, proj = kur(tmp, "v2")
    ov.materyalize(proj, core, "agents")
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nYENI SINIR satiri."))
    farklar = ov.fark_raporu(proj, core, "agents")
    ok2, msg2 = ov.materyalize(proj, core, "agents")          # BAYRAKSIZ
    kontrol(farklar == [] and ok2,
            "V2 (P) core değişti + kopya el değmemiş → fark YOK, BAYRAKSIZ üretim GEÇER",
            f"farklar={farklar} materyalize={ok2} {msg2.splitlines()[0] if msg2 else ''}")
    # ve tazelendiğini ÖLÇ (exit/True değil ÇIKTI kanıtı): kopya artık yeni satırı taşımalı
    kopya = (proj / ".claude" / "agents" / "alpha.md").read_text(encoding="utf-8")
    kontrol("YENI SINIR satiri" in kopya,
            "V2b (P) tazeleme GERÇEKTEN oldu (kopyada yeni içerik var)",
            "'OK' dedi ≠ üretti")

    # ── V3 (N) FP ÇAPASI: kopya ELLE düzeltildi → kapı AYNEN durur ──────────
    core, proj = kur(tmp, "v3")
    ov.materyalize(proj, core, "agents")
    hedef = proj / ".claude" / "agents" / "alpha.md"
    yaz(hedef, hedef.read_text(encoding="utf-8") + "\nELLE eklenmis proje notu.\n")
    farklar = ov.fark_raporu(proj, core, "agents")
    ok3, msg3 = ov.materyalize(proj, core, "agents")          # BAYRAKSIZ → RED beklenir
    kontrol(len(farklar) == 1 and "alpha.md" in farklar[0] and not ok3,
            "V3 (N) kopya elle düzeltildi → fark VAR + bayraksız üretim RED",
            f"farklar={farklar} materyalize={ok3}")
    # ve elle düzeltme HAYATTA kalmalı (ezilmedi)
    kontrol("ELLE eklenmis proje notu." in hedef.read_text(encoding="utf-8"),
            "V3b (N) RED sonrası elle düzeltme diskte DURUYOR (ezilmedi)")
    # onaylı koşum hâlâ ezebiliyor (kapı tamamen kilitlenmedi)
    ok3b, _ = ov.materyalize(proj, core, "agents", onayli=True)
    kontrol(ok3b and "ELLE eklenmis proje notu." not in hedef.read_text(encoding="utf-8"),
            "V3c (K) --overlay-onayli yolu hâlâ ÇALIŞIYOR (bilinçli ezme mümkün)")

    # ── V4 (N) İKİSİ BİRDEN: core değişti VE kopya elle düzeltildi ──────────
    # En tehlikeli hâl: yeni taban core değişimini görmezden gelirken elle düzeltmeyi
    # MASKELEMEMELİ.
    core, proj = kur(tmp, "v4")
    ov.materyalize(proj, core, "agents")
    hedef = proj / ".claude" / "agents" / "alpha.md"
    yaz(hedef, hedef.read_text(encoding="utf-8") + "\nELLE not.\n")
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nCORE degisimi."))
    farklar = ov.fark_raporu(proj, core, "agents")
    kontrol(any("alpha.md" in f and "FARKLI" in f for f in farklar),
            "V4 (N) core değişimi elle düzeltmeyi MASKELEMİYOR", f"farklar={farklar}")

    # ── V5 (P) core'dan dosya SİLİNDİ, kopya el değmemiş ────────────────────
    # Aynı sınıfın ikinci yüzü: junction'da bu silme bedavaya olur.
    core, proj = kur(tmp, "v5")
    ov.materyalize(proj, core, "agents")
    (core / "claude" / "agents" / "alpha.md").unlink()
    farklar = ov.fark_raporu(proj, core, "agents")
    ok5, _ = ov.materyalize(proj, core, "agents")
    kontrol(farklar == [] and ok5 and not (proj / ".claude" / "agents" / "alpha.md").exists(),
            "V5 (P) core sildi + kopya el değmemiş → fark YOK, bayraksız senkron SİLER",
            f"farklar={farklar}")

    # ── V6 (N) core SİLDİ ama kopya elle düzeltilmiş → hâlâ DUR ─────────────
    core, proj = kur(tmp, "v6")
    ov.materyalize(proj, core, "agents")
    hedef = proj / ".claude" / "agents" / "alpha.md"
    yaz(hedef, hedef.read_text(encoding="utf-8") + "\nELLE not.\n")
    (core / "claude" / "agents" / "alpha.md").unlink()
    farklar = ov.fark_raporu(proj, core, "agents")
    kontrol(any("alpha.md" in f and "SİLİNİR" in f for f in farklar),
            "V6 (N) core sildi + kopya elle düzeltilmiş → 'senkronda SİLİNİR' uyarısı DURUYOR",
            f"farklar={farklar}")

    # ── V7 (N) manifestin HİÇ tanımadığı yabancı dosya ──────────────────────
    core, proj = kur(tmp, "v7")
    ov.materyalize(proj, core, "agents")
    yaz(proj / ".claude" / "agents" / "yabanci.md", ajan("yabanci", "Elle konmus dosya."))
    farklar = ov.fark_raporu(proj, core, "agents")
    kontrol(any("yabanci.md" in f and "SİLİNİR" in f for f in farklar),
            "V7 (N) manifeste kayıtsız yabancı dosya → 'senkronda SİLİNİR' uyarısı",
            f"farklar={farklar}")

    # ── V8 (P) PROJE-OVERRIDE dosyası: claude-local değişti, kopya el değmemiş ──
    # `kaynak: proje` dalı da aynı tabandan beslenir; unutulursa proje-override'lı her
    # düzenleme tören ister.
    core, proj = kur(tmp, "v8")
    ov.materyalize(proj, core, "agents")
    yaz(proj / "claude-local" / "agents" / "beta.md", ajan("beta", "PROJE beta govdesi.\nYeni proje satiri."))
    farklar = ov.fark_raporu(proj, core, "agents")
    ok8, _ = ov.materyalize(proj, core, "agents")
    kontrol(farklar == [] and ok8,
            "V8 (P) claude-local değişti + kopya el değmemiş → fark YOK, bayraksız GEÇER",
            f"farklar={farklar}")

    # ── V9 (N) PROJE-OVERRIDE kopyası ELLE düzeltildi → DUR ─────────────────
    core, proj = kur(tmp, "v9")
    ov.materyalize(proj, core, "agents")
    hedef = proj / ".claude" / "agents" / "beta.md"
    yaz(hedef, hedef.read_text(encoding="utf-8") + "\nELLE not.\n")
    farklar = ov.fark_raporu(proj, core, "agents")
    kontrol(any("beta.md" in f and "FARKLI" in f for f in farklar),
            "V9 (N) proje-override kopyası elle düzeltildi → fark VAR", f"farklar={farklar}")

    # ── V10 (N) GERİYE-UYUM: `uretilen_hash`SİZ eski manifest ───────────────
    # 2026-08-13 öncesi üretilmiş her proje bu hâldedir (canlı bir projede ÖLÇÜLDÜ:
    # manifest yalnız `kaynak` + `core_hash` taşıyordu). Kanıt yoksa gevşeme de YOK.
    core, proj = kur(tmp, "v10")
    ov.materyalize(proj, core, "agents")
    m = manifest(proj)
    for kayit in m["dosyalar"].values():
        kayit.pop("uretilen_hash", None)
    manifest_yaz(proj, m)
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nCORE degisimi."))
    farklar = ov.fark_raporu(proj, core, "agents")
    ok10, _ = ov.materyalize(proj, core, "agents")
    kontrol(any("alpha.md" in f and "FARKLI" in f for f in farklar) and not ok10,
            "V10 (N) eski manifest (uretilen_hash YOK) → birebir ESKİ muhafazakâr davranış",
            f"farklar={farklar} materyalize={ok10}")

    # ── V11 (N) manifest DOSYASI bozuk/okunamaz → muhafazakâr ───────────────
    core, proj = kur(tmp, "v11")
    ov.materyalize(proj, core, "agents")
    (proj / ".claude" / "agents" / ".overlay-manifest.json").write_text(
        "{ bozuk json", encoding="utf-8")
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nCORE degisimi."))
    farklar = ov.fark_raporu(proj, core, "agents")
    kontrol(any("alpha.md" in f and "FARKLI" in f for f in farklar),
            "V11 (N) bozuk manifest → kanıt yok → muhafazakâr dal (çökme değil)",
            f"farklar={farklar}")

    # ── V12 (K) core'a YENİ dosya eklendi: ezme DEĞİL ekleme ────────────────
    # fark_raporu susmalı (kaybolacak proje emeği yok) AMA `durum()` EKSİK demeli —
    # yani sinyal kaybolmuyor, doğru kapıya taşınıyor.
    core, proj = kur(tmp, "v12")
    ov.materyalize(proj, core, "agents")
    yaz(core / "claude" / "agents" / "gamma.md", ajan("gamma", "Yeni core ajani."))
    farklar = ov.fark_raporu(proj, core, "agents")
    _, sorunlar = ov.durum(proj, core, "agents")
    kontrol(farklar == [] and any("EKSİK" in s and "gamma.md" in s for s in sorunlar),
            "V12 (K) core'a yeni dosya → fark_raporu SUSAR, durum() EKSİK der",
            f"farklar={farklar} sorunlar={sorunlar}")

    # ── V13 (K) 3. BAĞLAM — görev-DIŞI tip: `commands` (frontmatter'sız dosya) ──
    # agents dışında bir tip + damganın BAŞA girdiği dal. Sınıf fix'i orada da geçerli mi?
    core, proj = kur(tmp, "v13")
    yaz(core / "claude" / "commands" / "derle.md", "# Derle komutu\n\nGovde.\n")
    yaz(proj / "claude-local" / "commands" / "yerel.md", "# Yerel komut\n\nGovde.\n")
    ok13, _ = ov.materyalize(proj, core, "commands")
    yaz(core / "claude" / "commands" / "derle.md", "# Derle komutu\n\nGovde.\nCORE degisimi.\n")
    farklar_c = ov.fark_raporu(proj, core, "commands")
    ok13b, _ = ov.materyalize(proj, core, "commands")
    # Etiket (K değil P): mutasyon-1'de DÜŞTÜ → görev-dışı tipte de ayırt edici.
    kontrol(ok13 and farklar_c == [] and ok13b,
            "V13 (P) 3.BAĞLAM `commands` tipi: aynı sınıf, aynı sonuç (fark YOK)",
            f"farklar={farklar_c}")
    # aynı tipte elle düzeltme HÂLÂ durdurmalı (3. bağlamda FP çapası)
    h13 = proj / ".claude" / "commands" / "derle.md"
    yaz(h13, h13.read_text(encoding="utf-8") + "\nELLE not.\n")
    kontrol(ov.fark_raporu(proj, core, "commands") != [],
            "V13b (N) 3.BAĞLAM `commands`: elle düzeltme hâlâ DURDURUR")

    # ── V14 (K) REGRESYON ÇAPASI 2026-07-09: SAYI ≠ YÜKLENEBİLİRLİK ─────────
    # İlk sürümde damga frontmatter'ın ÖNÜNE girmişti → 6/6 agent yüklenemedi ama dosya
    # SAYISI doğru olduğu için "güncel" raporlanmıştı. Bu fix o çapaları bozmamalı.
    core, proj = kur(tmp, "v14")
    ov.materyalize(proj, core, "agents")
    dosyalar = sorted((proj / ".claude" / "agents").glob("*.md"))
    ilk_satir_ok = all(f.read_text(encoding="utf-8").splitlines()[0].strip() == "---"
                       for f in dosyalar)
    crlf_yok = all(b"\r\n" not in f.read_bytes() for f in dosyalar)
    damga_sonra = "<!-- CORE-URETILDI" in (proj / ".claude" / "agents" / "alpha.md") \
        .read_text(encoding="utf-8")
    _, sorunlar = ov.durum(proj, core, "agents")
    kontrol(len(dosyalar) == 2 and ilk_satir_ok and crlf_yok and damga_sonra and sorunlar == [],
            "V14 (K) frontmatter-önce + LF + damga-SONRA çapaları AYAKTA (2026-07-09 regresyonu)",
            f"dosya={len(dosyalar)} ilk_satir={ilk_satir_ok} crlf_yok={crlf_yok} "
            f"damga={damga_sonra} durum={sorunlar}")

    # ── V15 (K) manifest şeması: taban TAHMİN değil ÖLÇÜM ───────────────────
    # `uretilen_hash`, diskteki gerçek baytın hash'i olmalı ("yeniden üretsem ne çıkardı"
    # tahmini değil) — yoksa damga/LF farkı sessizce sahte-fark üretir.
    core, proj = kur(tmp, "v15")
    ov.materyalize(proj, core, "agents")
    m = manifest(proj)["dosyalar"]
    import hashlib
    sapan = [ad for ad, k in m.items()
             if k.get("uretilen_hash") != hashlib.sha256(
                 (proj / ".claude" / "agents" / ad).read_bytes()).hexdigest()[:16]]
    kontrol(len(m) == 2 and not sapan,
            "V15 (P) manifest `uretilen_hash` = diskteki gerçek bayt (ölçüm)",
            f"sapan={sapan} alanlar={sorted(next(iter(m.values())))}")

    # ── V16 (N) Ş2: `kaynak: proje` dosyası silme dalında HER DURUMDA kapıda kalır ──
    # Gevşetme YALNIZ core-üretimi artıklara uzanır. Proje-only bir override'ın kaynağı
    # (claude-local) kaldırılırsa kopya el değmemiş OLSA BİLE sessizce silinmez: o dosya
    # proje emeğinin ta kendisidir (core#69'un var oluş sebebi).
    core, proj = kur(tmp, "v16")
    yaz(proj / "claude-local" / "agents" / "gamma.md", ajan("gamma", "YALNIZ projede olan ajan."))
    ov.materyalize(proj, core, "agents")
    kayit_g = manifest(proj)["dosyalar"]["gamma.md"]
    (proj / "claude-local" / "agents" / "gamma.md").unlink()      # kaynak kaldırıldı
    farklar = ov.fark_raporu(proj, core, "agents")                 # kopyaya DOKUNULMADI
    kontrol(kayit_g["kaynak"] == "proje"
            and any("gamma.md" in f and "SİLİNİR" in f for f in farklar),
            "V16 (N) Ş2: `kaynak: proje` + kaynak kaldırıldı + kopya el değmemiş → HÂLÂ DURDURUR",
            f"kaynak={kayit_g['kaynak']} farklar={farklar}")

    # ── V17 (K) 3. VAKA SINIFI: "üretilmiş + bilinçli ÖZELLEŞTİRİLMİŞ" ──────────
    # Emsal: `.github/CODEOWNERS` template'ten FARKLIDIR çünkü `<OWNER_TEAM>` yer tutucusu
    # projeye göre doldurulur — "kopya ≠ şablon" orada DOĞRU durumdur. Overlay'deki
    # karşılığı `kaynak: proje` dosyalarıdır. FARK: overlay'de özelleştirmenin AYRI bir
    # doğruluk-kaynağı var (`claude-local/`, proje reposunda commit'li) → beklenen içerik
    # ZATEN özelleştirilmiş içeriktir. Bu yüzden bilinçli özelleştirme drift sanılmaz;
    # CODEOWNERS sınıfının aksine burada normalizasyona İHTİYAÇ YOKTUR.
    core, proj = kur(tmp, "v17")
    ov.materyalize(proj, core, "agents")
    kopya_beta = (proj / ".claude" / "agents" / "beta.md").read_text(encoding="utf-8")
    core_beta = (core / "claude" / "agents" / "beta.md").read_text(encoding="utf-8")
    kontrol("PROJE beta" in kopya_beta and kopya_beta != core_beta
            and ov.fark_raporu(proj, core, "agents") == [],
            "V17 (K) bilinçli özelleştirme (kaynak=proje) core'dan FARKLI ama drift SAYILMAZ",
            "özelleştirmenin doğruluk-kaynağı claude-local/'dir")

    # ── V18/V19 (K) NORMALİZASYON SINIRI: CRLF bozulması ────────────────────────
    # Taban BAYT-BAYT'tır (normalize DEĞİL) — kasıtlı: o hash'in baytlarını BİZ yazdık,
    # sapma = dışarıdan dokunuş kanıtıdır. Normalize etmek "el değmemiş"i genişletirdi =
    # ölçülmemiş ek gevşetme. Bedeli iki katmanlı ele alınır: taban tutmayınca `_norm`'lu
    # içerik-kıyasına düşülür ve saf CRLF gürültüsü ORADA emilir (V18).
    core, proj = kur(tmp, "v18")
    ov.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents" / "alpha.md"
    h.write_bytes(h.read_bytes().replace(b"\n", b"\r\n"))          # editör/araç CRLF'ledi
    kontrol(ov.fark_raporu(proj, core, "agents") == [],
            "V18 (K) saf CRLF bozulması + kaynak değişmemiş → `_norm` dalı EMER (sahte fark yok)")
    # V19 — BİLİNEN SINIR (dürüstlük çapası): CRLF + kaynak DA değiştiyse muhafazakâr davranır.
    # Bu bir FP'dir ama yönü güvenli (bloklar, ezmez) ve `durum()` CRLF'i ayrıca raporlar.
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nCORE degisimi."))
    _, sorunlar = ov.durum(proj, core, "agents")
    kontrol(ov.fark_raporu(proj, core, "agents") != []
            and any("CRLF" in s for s in sorunlar),
            "V19 (K) BİLİNEN SINIR: CRLF + kaynak değişimi birlikte → muhafazakâr + CRLF raporlanır",
            f"durum={sorunlar}")


def _git_show(ref: str, rel: str) -> str | None:
    r = subprocess.run(["git", "-C", str(KOK), "show", f"{ref}:{rel}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else None


def _modul_yukle(kaynak: str | None, tmp: Path, etiket: str):
    """claude_overlay'i dosyadan yükle. kaynak=None → çalışma ağacındaki CANLI dosya."""
    if kaynak is None:
        yol = KOK / MODUL_REL
    else:
        yol = tmp / f"_modul_{etiket}" / "claude_overlay.py"
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(kaynak, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location(f"claude_overlay_{etiket}", yol)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# `_uretildigi_gibi`yi DAİMA True yapan cerrahi mutasyon = "fix'in sökümü" (aşırı gevşetme).
GEVSEK_CAPA = '    beklenen = (kayit or {}).get("uretilen_hash")'
GEVSEK_YENI = '    return True  # MUTASYON: fix soküldü (her kopya "el değmemiş" sayılır)\n' + GEVSEK_CAPA


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true",
                    help="fix ÖNCESİ sürümle koş (P vektörleri DÜŞMELİ)")
    ap.add_argument("--mutasyon-gevsek", action="store_true",
                    help="fix'i aşırı-gevşet: _uretildigi_gibi daima True (N vektörleri DÜŞMELİ)")
    ap.add_argument("--ref", default=TABAN_SHA, help="mutasyon taban SHA'sı (⛔ dal adı DEĞİL)")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="overlay_kiyas_"))
    try:
        kaynak = None
        etiket = "canli"

        if args.mutasyon and args.mutasyon_gevsek:
            print("[DOĞRULANAMADI] iki mutasyon aynı anda verilemez. Sayı basılmadı.")
            return 2

        if args.mutasyon:
            kaynak = _git_show(args.ref, MODUL_REL)
            if kaynak is None:
                print(f"[DOĞRULANAMADI] taban sürüm alınamadı: {args.ref}:{MODUL_REL}")
                return 2
            if "uretilen_hash" in kaynak:
                print(f"[DOĞRULANAMADI] taban {args.ref} ZATEN `uretilen_hash` taşıyor — "
                      f"bu ref fix ÖNCESİ sürüm DEĞİL. Hiçbir sayı raporlanmadı.")
                return 2
            etiket = "taban"

        if args.mutasyon_gevsek:
            ham = (KOK / MODUL_REL).read_text(encoding="utf-8")
            if ham.count(GEVSEK_CAPA) != 1:
                print(f"[DOĞRULANAMADI] gevşetme çapası {ham.count(GEVSEK_CAPA)} kez bulundu "
                      f"(1 bekleniyordu) — mutasyon UYGULANMADI. Sayı basılmadı.")
                return 2
            kaynak = ham.replace(GEVSEK_CAPA, GEVSEK_YENI, 1)
            etiket = "gevsek"

        ov = _modul_yukle(kaynak, tmp, etiket)
        if ov is None:
            print("[DOĞRULANAMADI] claude_overlay yüklenemedi.")
            return 2

        # ÖN-DOĞRULAMA: taban GERÇEKTEN kusurlu davranıyor mu? (hareketli/yanlış ref
        # verilirse korpus "ayırt etmiyor" gibi görünür — HATA VERMEDEN.)
        if args.mutasyon:
            c, p = kur(tmp, "_on")
            ov.materyalize(p, c, "agents")
            yaz(c / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nDEGISIM."))
            if ov.fark_raporu(p, c, "agents") == []:
                print(f"[DOĞRULANAMADI] taban {args.ref} core-değişiminde fark ÜRETMİYOR — "
                      f"kusur bu ref'te canlı değil. Hiçbir sayı raporlanmadı.")
                return 2
            print(f"[MUTASYON] taban {args.ref}: P vektörleri DÜŞMELİ, N/K ayakta kalmalı\n")

        if args.mutasyon_gevsek:
            c, p = kur(tmp, "_ong")
            ov.materyalize(p, c, "agents")
            h = p / ".claude" / "agents" / "alpha.md"
            yaz(h, h.read_text(encoding="utf-8") + "\nELLE not.\n")
            if ov.fark_raporu(p, c, "agents") != []:
                print("[DOĞRULANAMADI] gevşek mutasyon elle düzeltmeyi HÂLÂ yakalıyor — "
                      "mutasyon hedefi ıskaladı. Hiçbir sayı raporlanmadı.")
                return 2
            print("[MUTASYON-GEVSEK] fix söküldü: N vektörleri DÜŞMELİ\n")

        senaryolar(ov, tmp)

        # KABLOLAMA — canlı inspector B5, aynı bayatlığı KAÇ kez raporluyor?
        if not (args.mutasyon or args.mutasyon_gevsek):
            _kablolama_b5(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    # ⚠ Özet satırı `^\s*\d+/\d+ OK` ile BAŞLAMALI — `run_fixture_tests` sayıyı bu desenle okur.
    print(f"\n{gecen}/{len(SONUC)} OK — overlay_kiyas_tabani")
    if args.mutasyon or args.mutasyon_gevsek:
        return 0          # mutasyonda karar SATIRLARDA (hangi vektör düştü), exit'te değil
    return 0 if gecen == len(SONUC) else 1


def _kablolama_b5(tmp: Path) -> None:
    """K16 — inspector B5 kablolaması: core-bayatlığı TEK bulgu olarak düşmeli.

    Kusurun ikinci yüzü buydu: aynı bayatlık İKİ ayrı B5 satırı üretiyordu
    (`OVERLAY BAYAT` core_hash kıyasından + `OVERLAY SAPMA` fark_raporu'ndan).
    """
    spec = importlib.util.spec_from_file_location("_insp_fx", KOK / "scripts" / "inspector.py")
    if spec is None or spec.loader is None:
        kontrol(False, "K16 KABLOLAMA DOĞRULANAMADI: inspector spec kurulamadı")
        return
    insp = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(insp)
    except Exception as exc:  # noqa: BLE001
        kontrol(False, f"K16 KABLOLAMA DOĞRULANAMADI: inspector yüklenemedi — {exc}")
        return

    ov = _modul_yukle(None, tmp, "k16mod")
    core, proj = kur(tmp, "k16", tam_core=True)
    for t in ("skills", "commands", "rules"):
        yaz(core / "claude" / t / "ornek.md", "---\nname: ornek\n---\n\nGovde.\n")
        yaz(proj / "claude-local" / t / "yerel.md", "---\nname: yerel\n---\n\nGovde.\n")
    for t in ov.TIPLER:
        ov.materyalize(proj, core, t)

    # core'da bir ajan değişti; projede elle düzeltme YOK.
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nYENI SINIR satiri."))
    bulgular = [b.mesaj for b in insp.b5_core_baglantisi(proj, core) if "alpha.md" in b.mesaj]
    kontrol(len(bulgular) == 1 and "BAYAT" in bulgular[0],
            "K16 KABLOLAMA: inspector B5 core-bayatlığını TEK bulgu olarak raporlar",
            f"bulgular={bulgular}")

    # FP çapası (kablolama katmanında): elle düzeltme inspector'da HÂLÂ görünür.
    h = proj / ".claude" / "agents" / "beta.md"
    yaz(h, h.read_text(encoding="utf-8") + "\nELLE not.\n")
    sapma = [b.mesaj for b in insp.b5_core_baglantisi(proj, core) if "beta.md" in b.mesaj]
    kontrol(any("SAPMA" in m for m in sapma),
            "K16b KABLOLAMA (N): elle düzeltme inspector B5'te HÂLÂ görünür",
            f"bulgular={sapma}")

    # K16c — SESSİZ KAYIP çapası: üçlü-kıyas modülü import EDİLEMEZSE denetim koşmaz.
    # Bu dal 2026-08-13'e kadar `except Exception: pass` idi → rapor "sapma yok" gibi
    # okunuyordu. Bu fixture'ın ilk koşumunda sahte-KIRMIZI olarak bizi de yakaladı.
    # KOŞMADI ≠ TEMİZ: modül yokken GÖRÜNÜR bulgu düşmeli.
    (core / "scripts" / "utils" / "claude_overlay.py").unlink()
    # sys.modules ÖNBELLEĞİNİ boşalt: modül bir kez import edildikten sonra dosyayı silmek
    # import'u BOZMAZ (önbellekten gelir) → çapa hiçbir şey ölçmemiş olurdu.
    for _ad in ("utils.claude_overlay", "utils"):
        sys.modules.pop(_ad, None)
    kopuk = [b.mesaj for b in insp.b5_core_baglantisi(proj, core) if "KOŞAMADI" in b.mesaj]
    kontrol(bool(kopuk),
            "K16c KABLOLAMA (N): üçlü-kıyas modülü yoksa SESSİZ değil GÖRÜNÜR bulgu",
            f"bulgular={kopuk[:1]}")


if __name__ == "__main__":
    raise SystemExit(main())
