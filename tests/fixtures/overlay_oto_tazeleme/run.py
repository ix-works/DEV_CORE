# -*- coding: utf-8 -*-
"""overlay_oto_tazeleme — overlay bayatlığının KULLANICI KOMUTU OLMADAN kapanması.

KÖK (2026-08-13 ikinci yarı; kullanıcı onaylı): aynı günün kıyas-tabanı fix'i (core#128)
onay TÖRENİNİ kaldırdı ama KOMUTU kaldırmadı — core bir ajan dosyasını değiştirdiğinde
kullanıcı hâlâ açılışta "OVERLAY BAYAT" görüyor ve bir kez `team_setup.py` koşuyordu.
Junction'lı üç tip (`skills`/`commands`/`rules`) tazeliği bedavaya alıyor; `agents` yalnız
TEK bir proje-override yüzünden kopya olduğu için alamıyordu. Kullanıcının sorusu:
*"her defasında böyle mi olacak"*.

FIX: `claude_overlay.oto_tazele()` + `session_start` kablolaması. İki değişmez taşır:
  ① EYLEM   — fark_raporu boşsa (kaybolacak proje emeği YOK) kopya kendiliğinden üretilir
              ve bu **görünür bir satırla** duyurulur (sessiz tazeleme YASAK).
  ② İMTİNA  — fark_raporu doluysa HİÇBİR ŞEYE dokunulmaz; T2.5 kapısı aynen yürürlükte
              (`materyalize` bu yolda da `onayli=False` ile çağrılır).

⚠ ÖLÇÜLMÜŞ SINIR (kaydın İÇİNDE): ajan tanımları oturum BAŞINDA okunur ⇒ tazeleme bir
SONRAKİ oturumdan itibaren etkilidir. 2026-08-13'te canlı harness'ta 3 koşumla ölçüldü
(yeni ajan aynı oturumda listede YOK · sonraki oturumda VAR · mevcut ajanın içeriği
değiştirilince aynı oturumda spawn edilen alt-ajan ESKİ içerikle davrandı). Vaat
"artık komut koşmayacaksın"dır, "anında güncellenir" DEĞİL.

ÖLÇÜT (mutasyon etiketi):
  * P → fix'in GETİRDİĞİ eylem. `--mutasyon` (taban SHA, oto_tazele HİÇ YOK) koşumunda DÜŞMELİ.
  * N → FP çapası: korunan imtina davranışı. `--mutasyon-gevsek` (kapının sökümü) koşumunda
        DÜŞMELİ — düşmezlerse korpus gevşemeyi ölçmüyor demektir.
  * K → kontrol grubu / kablolama / geri-alma / regresyon çapası.

⚠ N ÇAPALARI OMURGADIR (V3/V3b/V4/V7/V10/V16). Otomatik bir yazma kanalı açıyoruz; bu
korpusun var olma sebebi o kanalın SESSİZ EZMEYE dönüşmediğini ölçmektir.

KOŞUM: python tests/fixtures/overlay_oto_tazeleme/run.py
MUTASYON:
  python tests/fixtures/overlay_oto_tazeleme/run.py --mutasyon [--ref <SHA>]
      → fix ÖNCESİ sürüm (taban 63e6faa; `oto_tazele` yok). P vektörleri DÜŞMELİ.
  python tests/fixtures/overlay_oto_tazeleme/run.py --mutasyon-gevsek
      → cerrahi: otomatik yolda fark-kapısı sökülür (`farklar = []`). N çapaları DÜŞMELİ.
  ⛔ `--ref`e DAL ADI VERME: dal merge edilince "fix sonrası"na kayar ve korpus ayırt
  etmiyormuş gibi görünür. Taban SHA'ya pinlidir; koşucu tabanın GERÇEKTEN fix'siz
  olduğunu ön-doğrular, doğrulayamazsa sayı BASMAZ (exit 2).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
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
HOOK_REL = "scripts/hooks/session_start.py"
# Fix'in TABANI: otomatik tazeleme bu SHA'da HENÜZ YOK (dal adı değil — merge sonrası kaymasın).
TABAN_SHA = "63e6faa"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


# ─────────────────────────────────────────────────────────────────────────────
# Sentetik core + proje kurulumu
# ⚠ Bütün yazımlar newline="\n" (Windows varsayılanı CRLF yazar → sahte fark).
# ─────────────────────────────────────────────────────────────────────────────
def yaz(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", newline="\n")


def ajan(ad: str, govde: str) -> str:
    return f"---\nname: {ad}\ndescription: sentetik fixture ajani\n---\n\n{govde}\n"


def kur(tmp: Path, etiket: str, modul_kaynak: str | None = None,
        tipler: tuple = ("agents",)) -> tuple[Path, Path]:
    """Sentetik (core, proje) çifti. Her tipte: alpha=core-only, beta=proje-override.

    `modul_kaynak` verilirse core köküne `scripts/utils/claude_overlay.py` de kurulur.
    GEREKLİ: `session_start` ve `inspector` modülü **kendilerine verilen core kökünden**
    import eder (`sys.path.insert(core/"scripts")`). İskelet olmadan o dallar hiç koşmaz
    ve fixture sahte-KIRMIZI/sahte-YEŞİL verir (tüketicinin import kökünü taşı).
    """
    core = tmp / etiket / "core"
    proj = tmp / etiket / "proje"
    for tip in tipler:
        yaz(core / "claude" / tip / "alpha.md", ajan("alpha", "Alpha govdesi."))
        yaz(core / "claude" / tip / "beta.md", ajan("beta", "Core beta govdesi."))
        yaz(proj / "claude-local" / tip / "beta.md", ajan("beta", "PROJE beta govdesi."))
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    if modul_kaynak is not None:
        yaz(core / "scripts" / "utils" / "claude_overlay.py", modul_kaynak)
    return core, proj


def oto(ov, proj: Path, core: Path) -> list:
    """`oto_tazele` yoksa (taban sürüm) sentinel döner — P vektörleri böyle DÜŞER."""
    fn = getattr(ov, "oto_tazele", None)
    if fn is None:
        return ["<oto_tazele YOK — taban surum>"]
    return fn(proj, core)


def dizin_imzasi(d: Path) -> dict:
    return {p.name: p.read_bytes() for p in sorted(d.glob("*.md"))}


def tazelendi_mi(satirlar: list) -> bool:
    return any(str(s).startswith("overlay tazelendi") for s in satirlar)


def atlandi_mi(satirlar: list) -> bool:
    return any("ATLANDI" in str(s) for s in satirlar)


# ─────────────────────────────────────────────────────────────────────────────
# SENARYOLAR
# ─────────────────────────────────────────────────────────────────────────────
def senaryolar(ov, tmp: Path) -> None:
    # ── V0 (K) KONTROL GRUBU: overlay'siz proje → hiç dokunma, hiç konuşma ──
    core, proj = kur(tmp, "v0")
    shutil.rmtree(proj / "claude-local")            # claude-local YOK = junction'lı proje
    kontrol(oto(ov, proj, core) == [] or not getattr(ov, "oto_tazele", None),
            "V0 (K) overlay'siz proje (junction yolu): NO-OP + sessiz")

    # ── V1 (N) taze proje: yapılacak iş yok → SESSİZ ────────────────────────
    core, proj = kur(tmp, "v1")
    ov.materyalize(proj, core, "agents")
    satirlar = oto(ov, proj, core)
    kontrol(satirlar == [] or not getattr(ov, "oto_tazele", None),
            "V1 (N) taze kopya → hiçbir satır basılmaz (gürültü yok)", f"satirlar={satirlar}")

    # ── V2 (P) ASIL KAYIT: core değişti, kopya el değmemiş → KENDİLİĞİNDEN ──
    core, proj = kur(tmp, "v2")
    ov.materyalize(proj, core, "agents")
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nYENI SINIR satiri."))
    satirlar = oto(ov, proj, core)
    kopya = (proj / ".claude" / "agents" / "alpha.md").read_text(encoding="utf-8")
    kontrol("YENI SINIR satiri" in kopya,
            "V2 (P) core değişti + el değmemiş → kopya KOMUTSUZ tazelendi (ÇIKTI kanıtı)",
            f"satirlar={satirlar}")
    kontrol(tazelendi_mi(satirlar) and "agents" in " ".join(map(str, satirlar)),
            "V2b (P) GÖRÜNÜRLÜK: tazeleme tek satırla duyuruldu (tip adı + dosya sayısı)",
            f"satirlar={satirlar}")
    kontrol(any("SONRAKI oturumdan" in str(s) for s in satirlar),
            "V2c (P) ölçülmüş sınır satırı basıldı (bu oturumda etkili DEĞİL)",
            f"satirlar={satirlar}")
    kontrol(oto(ov, proj, core) == [],
            "V2d (K) İDEMPOTANS: hemen ardından ikinci çağrı SESSİZ (sonsuz tazeleme yok)")

    # ── V3 (N) FP ÇAPASI: kopya ELLE düzeltilmiş → DOKUNMA ──────────────────
    core, proj = kur(tmp, "v3")
    ov.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents" / "alpha.md"
    yaz(h, h.read_text(encoding="utf-8") + "\nELLE eklenmis proje notu.\n")
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nCORE degisimi."))
    satirlar = oto(ov, proj, core)
    kontrol("ELLE eklenmis proje notu." in h.read_text(encoding="utf-8"),
            "V3 (N) elle düzeltme + core değişimi → otomatik EZMEDİ (proje emeği diskte)",
            f"satirlar={satirlar}")
    # ⚠ V3b (P) etiketi bilinçli: "ezmemek" (V3) fix'in KORUDUĞU davranıştır, "atladığını
    # SÖYLEMEK" fix'in GETİRDİĞİdir. İkisi tek vektörde birleştirilirse taban mutasyonunda
    # FP çapası da düşer ve "doğru vaka bozulmadı" kanıtı sessizce kaybolur.
    kontrol(atlandi_mi(satirlar) and not tazelendi_mi(satirlar),
            "V3b (P) atlama SESSİZ değil: görünür 'ATLANDI' satırı + karar/komut önerisi",
            f"satirlar={satirlar}")

    # ── V20 (N) İKİNCİ SAVUNMA KATMANI: kapı `materyalize` içinde de duruyor ──
    # Otomatik yoldaki ön-kontrol yanlışlıkla boş dönse bile ezme OLMAMALI. Ölçüldü:
    # tek noktalı bir gevşetme mutasyonu bu yüzden hedefi ıskalıyor (mutasyon İKİ
    # katmanı birden kesmek zorunda) — yani koruma gerçekten iki katmanlı.
    core, proj = kur(tmp, "v20")
    ov.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents" / "alpha.md"
    yaz(h, h.read_text(encoding="utf-8") + "\nIKINCI katman notu.\n")
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nD."))
    ok20, _ = ov.materyalize(proj, core, "agents", onayli=False)   # otomatik yolun ÇAĞRISI
    kontrol(not ok20 and "IKINCI katman notu." in h.read_text(encoding="utf-8"),
            "V20 (N) otomatik yolun kullandığı çağrı (onayli=False) kapıyı KENDİ içinde de tutuyor")

    # ── V4 (N) yalnız elle düzeltme (core hiç değişmedi) → yine dokunma ─────
    core, proj = kur(tmp, "v4")
    ov.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents" / "alpha.md"
    yaz(h, h.read_text(encoding="utf-8") + "\nYALNIZ elle not.\n")
    oto(ov, proj, core)
    kontrol("YALNIZ elle not." in h.read_text(encoding="utf-8"),
            "V4 (N) core değişmeden elle düzeltme → otomatik yol yine EZMEZ")

    # ── V5 (P) core YENİ dosya ekledi (bugün ⛔ 'overlay'de EKSİK' dalı) ────
    core, proj = kur(tmp, "v5")
    ov.materyalize(proj, core, "agents")
    yaz(core / "claude" / "agents" / "gamma.md", ajan("gamma", "Yeni core ajani."))
    satirlar = oto(ov, proj, core)
    kontrol((proj / ".claude" / "agents" / "gamma.md").is_file() and tazelendi_mi(satirlar),
            "V5 (P) core YENİ ajan ekledi → kopyada oluştu + duyuruldu", f"satirlar={satirlar}")

    # ── V6 (P) core dosya SİLDİ + kopya el değmemiş → silme yayılır ─────────
    core, proj = kur(tmp, "v6")
    ov.materyalize(proj, core, "agents")
    (core / "claude" / "agents" / "alpha.md").unlink()
    satirlar = oto(ov, proj, core)
    kontrol(not (proj / ".claude" / "agents" / "alpha.md").is_file() and tazelendi_mi(satirlar),
            "V6 (P) core SİLDİ + el değmemiş → kopya da silindi (junction paritesi)",
            f"satirlar={satirlar}")

    # ── V7 (N) CORE OKUNAMIYOR (junction kopuk) → SİLME YOK ────────────────
    # En pahalı yanlış: üretilecek küme core'suz hesaplanırsa otomatik yol tüm core
    # kopyalarını SİLER. Kanıt yokken silme yok.
    core, proj = kur(tmp, "v7")
    ov.materyalize(proj, core, "agents")
    onceki = dizin_imzasi(proj / ".claude" / "agents")
    shutil.rmtree(core / "claude" / "agents")
    satirlar = oto(ov, proj, core)
    kontrol(dizin_imzasi(proj / ".claude" / "agents") == onceki,
            "V7 (N) core/claude/agents okunamıyor → kopyalara DOKUNULMADI (silme yok)",
            f"satirlar={satirlar}")
    kontrol(atlandi_mi(satirlar) or not getattr(ov, "oto_tazele", None),
            "V7b (N) bu atlama da GÖRÜNÜR (KOŞMADI ≠ TEMİZ)", f"satirlar={satirlar}")

    # ── V8 (P) ESKİ manifest (uretilen_hash yok) → kayıt tazelenir ──────────
    # 2026-08-13 kıyas-tabanı fix'inin yayılım adımı: alan yalnız materyalize ile dolar.
    # İçerik zaten üretilecekle aynıysa bu, içerik değiştirmeyen bir KAYIT tazelemesidir.
    core, proj = kur(tmp, "v8")
    ov.materyalize(proj, core, "agents")
    mf = proj / ".claude" / "agents" / ".overlay-manifest.json"
    veri = json.loads(mf.read_text(encoding="utf-8"))
    for k in veri["dosyalar"].values():
        k.pop("uretilen_hash", None)
    mf.write_text(json.dumps(veri, indent=1, ensure_ascii=False), encoding="utf-8")
    onceki = dizin_imzasi(proj / ".claude" / "agents")
    satirlar = oto(ov, proj, core)
    yeni = json.loads(mf.read_text(encoding="utf-8"))
    kontrol(all(k.get("uretilen_hash") for k in yeni["dosyalar"].values())
            and dizin_imzasi(proj / ".claude" / "agents") == onceki,
            "V8 (P) eski manifest → kayıt tazelendi, İÇERİK bayt-bayt aynı kaldı",
            f"satirlar={satirlar}")
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nSONRAKI degisim."))
    oto(ov, proj, core)
    kontrol("SONRAKI degisim" in (proj / ".claude" / "agents" / "alpha.md").read_text(encoding="utf-8"),
            "V8b (P) yayılım kapandı: kayıt tazelendikten sonra core değişimi otomatik akıyor")

    # ── V9 (K) BOZUK manifest + içerik üretilecekle aynı → kendini onarır ───
    core, proj = kur(tmp, "v9")
    ov.materyalize(proj, core, "agents")
    onceki = dizin_imzasi(proj / ".claude" / "agents")
    (proj / ".claude" / "agents" / ".overlay-manifest.json").write_text("{bozuk", encoding="utf-8")
    oto(ov, proj, core)
    try:
        json.loads((proj / ".claude" / "agents" / ".overlay-manifest.json").read_text(encoding="utf-8"))
        gecerli = True
    except Exception:
        gecerli = False
    kontrol(gecerli and dizin_imzasi(proj / ".claude" / "agents") == onceki,
            "V9 (K) bozuk manifest + el değmemiş kopya → manifest onarıldı, içerik AYNI")

    # ── V10 (N) BOZUK manifest + elle düzeltme → kanıt yok, gevşeme de yok ──
    core, proj = kur(tmp, "v10")
    ov.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents" / "alpha.md"
    yaz(h, h.read_text(encoding="utf-8") + "\nELLE not (manifest bozuk).\n")
    (proj / ".claude" / "agents" / ".overlay-manifest.json").write_text("{bozuk", encoding="utf-8")
    satirlar = oto(ov, proj, core)
    kontrol("ELLE not (manifest bozuk)." in h.read_text(encoding="utf-8"),
            "V10 (N) manifest bozuk + elle düzeltme → EZME YOK (kanıtsız gevşeme yok)",
            f"satirlar={satirlar}")

    # ── V11 (K) GERİ ALMA: IX_OVERLAY_OTO=0 → tümüyle kapanır ──────────────
    core, proj = kur(tmp, "v11")
    ov.materyalize(proj, core, "agents")
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nKAPALIYKEN degisim."))
    os.environ["IX_OVERLAY_OTO"] = "0"
    try:
        satirlar = oto(ov, proj, core)
    finally:
        os.environ.pop("IX_OVERLAY_OTO", None)
    kopya = (proj / ".claude" / "agents" / "alpha.md").read_text(encoding="utf-8")
    kontrol("KAPALIYKEN degisim" not in kopya and (satirlar == [] or "<oto_tazele YOK" in str(satirlar[0])),
            "V11 (K) IX_OVERLAY_OTO=0 → otomatik yol KAPALI (eski davranış), satır basılmaz")
    kontrol(tazelendi_mi(oto(ov, proj, core)) or not getattr(ov, "oto_tazele", None),
            "V11b (K) bayrak kalkınca aynı vaka yeniden tazeleniyor (kapama kalıcı değil)")

    # ── V12 (K) SINIF mı VAKA mı: dört tipin hepsinde çalışır ──────────────
    core, proj = kur(tmp, "v12", tipler=("agents", "skills", "commands", "rules"))
    for t in ("agents", "skills", "commands", "rules"):
        ov.materyalize(proj, core, t)
        yaz(core / "claude" / t / "alpha.md", ajan("alpha", f"Alpha govdesi.\n{t} degisimi."))
    satirlar = oto(ov, proj, core)
    tazelenen = [t for t in ("agents", "skills", "commands", "rules")
                 if f"{t} degisimi" in (proj / ".claude" / t / "alpha.md").read_text(encoding="utf-8")]
    kontrol(len(tazelenen) == 4,
            "V12 (K) SINIF fix'i: dört overlay tipinde de çalışıyor (agents'a özel değil)",
            f"tazelenen={tazelenen} satirlar={len(satirlar)}")

    # ── V21 (K) SINIR: ilk materyalizasyon otomatiğin İŞİ DEĞİL ────────────
    # `claude-local` var ama `.claude/<tip>` henüz üretilmemiş (junction / hiç yok):
    # junction'ı gerçek dizine çevirmek KOPYA KANALINI AÇMAKTIR = kurulum kararı.
    # Otomatik yol bunu yapmaz; `durum()`'un mevcut "repair-junctions" uyarısı yürürlükte.
    core, proj = kur(tmp, "v21")                       # materyalize HİÇ çağrılmadı
    satirlar = oto(ov, proj, core)
    kontrol((satirlar == [] or not getattr(ov, "oto_tazele", None))
            and not (proj / ".claude" / "agents").exists(),
            "V21 (K) SINIR: ilk materyalizasyon (junction→dizin) otomatiğe DAHİL değil",
            f"satirlar={satirlar}")

    # ── V16 (N) PROJE-OVERRIDE kopyası elle düzeltilmiş → dokunma ──────────
    core, proj = kur(tmp, "v16")
    ov.materyalize(proj, core, "agents")
    hb = proj / ".claude" / "agents" / "beta.md"
    yaz(hb, hb.read_text(encoding="utf-8") + "\nOVERRIDE uzerinde elle not.\n")
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nCore degisti."))
    oto(ov, proj, core)
    kontrol("OVERRIDE uzerinde elle not." in hb.read_text(encoding="utf-8"),
            "V16 (N) proje-override kopyasındaki elle düzeltme de korunur")

    # ── V17 (P) claude-local'in KENDİSİ değişti → kopya tazelenir ──────────
    core, proj = kur(tmp, "v17")
    ov.materyalize(proj, core, "agents")
    yaz(proj / "claude-local" / "agents" / "beta.md", ajan("beta", "PROJE beta v2 govdesi."))
    oto(ov, proj, core)
    kontrol("PROJE beta v2" in (proj / ".claude" / "agents" / "beta.md").read_text(encoding="utf-8"),
            "V17 (P) claude-local güncellemesi de komutsuz akıyor")

    # ── V18 (K) HATA DALI: `except: pass` YOK — görünür + oturum bozulmaz ──
    core, proj = kur(tmp, "v18")
    ov.materyalize(proj, core, "agents")
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nDegisim."))
    if getattr(ov, "oto_tazele", None):
        gercek = ov._yerinde_senkron
        ov._yerinde_senkron = lambda *a, **k: (_ for _ in ()).throw(OSError("sentetik disk hatasi"))
        try:
            satirlar = ov.oto_tazele(proj, core)
        finally:
            ov._yerinde_senkron = gercek
        kontrol(any("KOSAMADI" in str(s) for s in satirlar),
                "V18 (K) tazeleme çökerse: görünür satır + istisna yutulmuyor (oturum ayakta)",
                f"satirlar={satirlar}")
    else:
        kontrol(True, "V18 (K) taban sürümde hata dalı yok — atlandı (kontrol grubu)")

    # ── V19 (K) SÖZLEŞME: disk değiştiyse MUTLAKA satır basılır ────────────
    # Sessiz davranış = denetlenemeyen davranış. Bu meta-vektör dört mutasyon
    # senaryosunu tek değişmezde toplar.
    ihlal = []
    for etiket, hazirla in (
        ("core-degisti", lambda c, p: yaz(c / "claude" / "agents" / "alpha.md",
                                          ajan("alpha", "Alpha govdesi.\nX."))),
        ("core-ekledi", lambda c, p: yaz(c / "claude" / "agents" / "delta.md",
                                         ajan("delta", "Yeni."))),
        ("core-sildi", lambda c, p: (c / "claude" / "agents" / "alpha.md").unlink()),
        ("local-degisti", lambda c, p: yaz(p / "claude-local" / "agents" / "beta.md",
                                           ajan("beta", "PROJE beta v3."))),
    ):
        core, proj = kur(tmp, f"v19_{etiket}")
        ov.materyalize(proj, core, "agents")
        onceki = dizin_imzasi(proj / ".claude" / "agents")
        hazirla(core, proj)
        satirlar = oto(ov, proj, core)
        if dizin_imzasi(proj / ".claude" / "agents") != onceki and not satirlar:
            ihlal.append(etiket)
    kontrol(not ihlal, "V19 (K) SESSİZ DEĞİŞİKLİK YOK: diski değiştiren her dal satır basar",
            f"ihlal={ihlal}")


# ─────────────────────────────────────────────────────────────────────────────
# KABLOLAMA — kod ≠ kablolama: hook'u GERÇEKTEN koştur
# ─────────────────────────────────────────────────────────────────────────────
def _kablolama(tmp: Path, modul_kaynak: str | None, hook_yolu: Path) -> None:
    """K20-K22: `session_start` hook'u alt-süreç olarak koşar (canlı giriş noktası).

    Elle `oto_tazele()` çağırmak KABLOLAMAYI kanıtlamaz. Burada gerçek hook, gerçek
    stdin JSON'u ve gerçek CLAUDE_PROJECT_DIR ile koşar; ölçüt hook'un STDOUT'undaki
    `additionalContext` (kullanıcının açılışta GÖRDÜĞÜ metin) ve diskteki sonuçtur.
    """
    # `session_start` modülü KENDİNE VERİLEN core kökünden import eder → iskelet ŞART.
    # (İlk koşumda burası None geçildi: import düştü, K20/K21 sahte-KIRMIZI verdi.)
    kaynak_metni = (modul_kaynak if modul_kaynak is not None
                    else (KOK / MODUL_REL).read_text(encoding="utf-8"))

    def kos(proj: Path) -> tuple[int, str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith("IX_")}
        env["CLAUDE_PROJECT_DIR"] = str(proj)
        r = subprocess.run([sys.executable, str(hook_yolu)], input='{"session_id":"fx-1"}',
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=120)
        try:
            govde = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
        except Exception:
            govde = ""
        return r.returncode, govde, (r.stderr or "")[-300:]

    # K20 — core değişti, el değmemiş: hook çıktısında duyuru VAR + disk tazelendi
    core, proj = kur(tmp, "k20", modul_kaynak=kaynak_metni)
    ov_yerel = _modul_yukle(modul_kaynak, tmp, "k20mod")
    ov_yerel.materyalize(proj, core, "agents")
    shutil.move(str(core), str(proj / "core"))          # session_start: CORE = PROJ/"core"
    core = proj / "core"
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nHOOK degisimi."))
    rc, govde, hata = kos(proj)
    kopya = (proj / ".claude" / "agents" / "alpha.md").read_text(encoding="utf-8")
    kontrol(rc == 0 and "HOOK degisimi" in kopya,
            "K20 (P) KABLOLAMA: gerçek session_start koşumu kopyayı tazeledi",
            f"exit={rc} stderr={hata[:120]}")
    kontrol("overlay tazelendi" in govde,
            "K21 (P) KABLOLAMA: duyuru kullanıcının GÖRDÜĞÜ açılış metnine düştü",
            f"govde={govde[-220:]!r}")
    # ⛔ junction dalı bu satırı BASTIRMAMALI: sentetik projede `core` gerçek klasördür,
    # yani hook zaten ⛔ 'junction DEGIL gercek klasor' dalındadır — satır yine görünmeli.
    kontrol("JUNCTION" in govde.upper() and "overlay tazelendi" in govde,
            "K22 (K) ⛔ junction uyarısı VARKEN bile tazeleme satırı bastırılmıyor")

    # K23 — fark DOLU: hook dokunmaz, bugünkü uyarı yolu (fark_raporu) ayakta kalır
    core, proj = kur(tmp, "k23", modul_kaynak=kaynak_metni)
    ov_yerel.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents" / "alpha.md"
    yaz(h, h.read_text(encoding="utf-8") + "\nELLE hook notu.\n")
    shutil.move(str(core), str(proj / "core"))
    core = proj / "core"
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nHOOK degisimi."))
    rc, govde, hata = kos(proj)
    kontrol(rc == 0 and "ELLE hook notu." in h.read_text(encoding="utf-8"),
            "K23 (N) KABLOLAMA: canlı hook elle düzeltmeyi EZMEDİ", f"exit={rc}")
    kontrol(ov_yerel.fark_raporu(proj, core, "agents") != [],
            "K24 (N) atlanan vakada bugünkü uyarı kaynağı (fark_raporu) HÂLÂ dolu")


def _kablolama_inspector(tmp: Path) -> None:
    """K25: tazeleme sonrası inspector B5 'OVERLAY BAYAT' bulgusu SUSAR (nag kapandı)."""
    spec = importlib.util.spec_from_file_location("_insp_fx", KOK / "scripts" / "inspector.py")
    if spec is None or spec.loader is None:
        kontrol(False, "K25 DOĞRULANAMADI: inspector spec kurulamadı")
        return
    insp = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(insp)
    except Exception as exc:  # noqa: BLE001
        kontrol(False, f"K25 DOĞRULANAMADI: inspector yüklenemedi — {exc}")
        return
    ov = _modul_yukle(None, tmp, "k25mod")
    core, proj = kur(tmp, "k25", modul_kaynak=(KOK / MODUL_REL).read_text(encoding="utf-8"))
    ov.materyalize(proj, core, "agents")
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nB5 degisimi."))
    once = [b.mesaj for b in insp.b5_core_baglantisi(proj, core) if "BAYAT" in b.mesaj]
    ov.oto_tazele(proj, core)
    sonra = [b.mesaj for b in insp.b5_core_baglantisi(proj, core) if "BAYAT" in b.mesaj]
    kontrol(len(once) == 1 and sonra == [],
            "K25 (P) nag KAPANDI: tazeleme öncesi 1 'OVERLAY BAYAT', sonrası 0",
            f"once={len(once)} sonra={len(sonra)}")


def _yapisal_rmtree_capasi(kaynak: str | None) -> None:
    """V22 (K) ATOMİKLİK ÇAPASI: `oto_tazele`'nin çağrı zincirinde `rmtree` YOK.

    `materyalize` dizini silip yeniden kurar (elle yolda kabul). Otomatik yol her oturum
    açılışında koşacağı için o pencere rutin olurdu — harness'ın ajan tanımlarını okuduğu
    dizinde. Bu çapa olmadan biri `oto_tazele`'yi tekrar `materyalize`'e bağlarsa SESSİZCE
    olur. Ölçüm AST'tir (yorum/dizge değil): modül-içi çağrı grafiği kapanışı gezilir.
    """
    import ast
    metin = kaynak if kaynak is not None else (KOK / MODUL_REL).read_text(encoding="utf-8")
    agac = ast.parse(metin)
    fonk = {d.name: d for d in ast.walk(agac) if isinstance(d, ast.FunctionDef)}
    if "oto_tazele" not in fonk:
        kontrol(True, "V22 (K) taban sürümde oto_tazele yok — çapa uygulanmaz (kontrol grubu)")
        return

    def cagrilar(d) -> set:
        out = set()
        for n in ast.walk(d):
            if isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Name):
                    out.add(f.id)
                elif isinstance(f, ast.Attribute):
                    kok = f.value.id if isinstance(f.value, ast.Name) else ""
                    out.add(f"{kok}.{f.attr}" if kok else f.attr)
        return out

    goruldu, kuyruk, zincir = set(), ["oto_tazele"], set()
    while kuyruk:
        ad = kuyruk.pop()
        if ad in goruldu or ad not in fonk:
            continue
        goruldu.add(ad)
        for c in cagrilar(fonk[ad]):
            zincir.add(c)
            if c in fonk:
                kuyruk.append(c)
    kontrol("shutil.rmtree" not in zincir and "rmtree" not in zincir
            and "materyalize" not in zincir,
            "V22 (K) ATOMİKLİK: oto_tazele çağrı zincirinde rmtree/materyalize YOK",
            f"gezilen={sorted(goruldu)}")


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
    spec = importlib.util.spec_from_file_location(f"claude_overlay_oto_{etiket}", yol)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Otomatik yoldaki fark-KAPISINI söken cerrahi mutasyon (aşırı gevşetme).
# ⚠ İKİ çapa ŞART — ölçüldü: tek başına ön-kontrolü boşaltmak YETMİYOR, çünkü aynı kapı
# `materyalize(onayli=False)` içinde bir kez daha uygulanıyor (V20). Tek-noktalı mutasyon
# hedefi ıskalıyordu ve koşucu haklı olarak "sayı basmadı" (exit 2) dedi.
GEVSEK_CAPALAR = [
    ("            farklar = fark_raporu(proje, core_root, tip)",
     "            farklar = []  # MUTASYON-1: oto_tazele on-kontrolu bosaltildi"),
    ("    farklar = fark_raporu(proje, core_root, tip)\n    if farklar:",
     "    farklar = []  # MUTASYON-2: _yerinde_senkron ic kapisi sokuldu\n    if farklar:"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true",
                    help="fix ÖNCESİ sürümle koş (oto_tazele YOK) — P vektörleri DÜŞMELİ")
    ap.add_argument("--mutasyon-gevsek", action="store_true",
                    help="otomatik yolda fark-kapısını sök — N çapaları DÜŞMELİ")
    ap.add_argument("--ref", default=TABAN_SHA, help="mutasyon taban SHA'sı (⛔ dal adı DEĞİL)")
    args = ap.parse_args()

    if args.mutasyon and args.mutasyon_gevsek:
        print("[DOĞRULANAMADI] iki mutasyon aynı anda verilemez. Sayı basılmadı.")
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="overlay_oto_"))
    try:
        kaynak, hook_yolu, etiket = None, KOK / HOOK_REL, "canli"

        if args.mutasyon:
            kaynak = _git_show(args.ref, MODUL_REL)
            taban_hook = _git_show(args.ref, HOOK_REL)
            if kaynak is None or taban_hook is None:
                print(f"[DOĞRULANAMADI] taban sürüm alınamadı: {args.ref}")
                return 2
            if "oto_tazele" in kaynak or "oto_tazele" in taban_hook:
                print(f"[DOĞRULANAMADI] taban {args.ref} ZATEN `oto_tazele` taşıyor — bu ref "
                      f"fix ÖNCESİ sürüm DEĞİL. Hiçbir sayı raporlanmadı.")
                return 2
            hook_yolu = tmp / "_taban_session_start.py"
            hook_yolu.write_text(taban_hook, encoding="utf-8", newline="\n")
            etiket = "taban"
            print(f"[MUTASYON] taban {args.ref} (oto_tazele YOK): P vektörleri DÜŞMELİ, "
                  f"N/K ayakta kalmalı\n")

        if args.mutasyon_gevsek:
            kaynak = (KOK / MODUL_REL).read_text(encoding="utf-8")
            for capa, yeni in GEVSEK_CAPALAR:
                if kaynak.count(capa) != 1:
                    print(f"[DOĞRULANAMADI] gevşetme çapası {kaynak.count(capa)} kez bulundu "
                          f"(1 bekleniyordu): {capa.strip()[:60]} — mutasyon UYGULANMADI. "
                          f"Sayı basılmadı.")
                    return 2
                kaynak = kaynak.replace(capa, yeni, 1)
            etiket = "gevsek"
            # ÖN-DOĞRULAMA: mutasyon GERÇEKTEN gevşetiyor mu (elle düzeltmeyi eziyor mu)?
            ov_on = _modul_yukle(kaynak, tmp, "_ong")
            c, p = kur(tmp, "_ong")
            ov_on.materyalize(p, c, "agents")
            hh = p / ".claude" / "agents" / "alpha.md"
            yaz(hh, hh.read_text(encoding="utf-8") + "\nELLE.\n")
            yaz(c / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi.\nD."))
            ov_on.oto_tazele(p, c)
            if "ELLE." in hh.read_text(encoding="utf-8"):
                print("[DOĞRULANAMADI] gevşek mutasyon elle düzeltmeyi HÂLÂ ezmiyor — "
                      "mutasyon hedefi ıskaladı. Hiçbir sayı raporlanmadı.")
                return 2
            print("[MUTASYON-GEVSEK] otomatik yolun kapısı söküldü: N çapaları DÜŞMELİ\n")

        ov = _modul_yukle(kaynak, tmp, etiket)
        if ov is None:
            print("[DOĞRULANAMADI] claude_overlay yüklenemedi.")
            return 2

        senaryolar(ov, tmp)
        _yapisal_rmtree_capasi(kaynak)
        _kablolama(tmp, kaynak, hook_yolu)
        if not (args.mutasyon or args.mutasyon_gevsek):
            _kablolama_inspector(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    # ⚠ Özet satırı `^\s*\d+/\d+ OK` ile BAŞLAMALI — `run_fixture_tests` sayıyı bu desenle okur.
    print(f"\n{gecen}/{len(SONUC)} OK — overlay_oto_tazeleme")
    if args.mutasyon or args.mutasyon_gevsek:
        return 0          # mutasyonda karar SATIRLARDA (hangi vektör düştü), exit'te değil
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
