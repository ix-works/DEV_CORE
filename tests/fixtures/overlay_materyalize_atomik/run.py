# -*- coding: utf-8 -*-
"""overlay_materyalize_atomik — Q30: YIKIM ile İNŞA arasında BOŞ PENCERE olmamalı.

KÖK (2026-08-27, ölçülmüş canlı vaka): `claude_overlay.materyalize()` hedef dizini
`shutil.rmtree` ile SİLİP yeniden kuruyordu. Windows'ta `rmtree` önce İÇERİDEKİ 7 ajan
tanımını sildi, sonra DİZİNİN KENDİSİNİ silerken `PermissionError [WinError 5]` aldı
(dışarıdan tutulan anlık handle; bu makinede repo kökü bir Drive senkron klasörü altındadır ve
`GoogleDriveFS`/Defender/indeksleyici canlıdır). İstisna `mkdir`+yazma satırlarına
gelinmesini engelledi ⇒ `.claude/agents` **BOŞ** kaldı.

Neden sessiz ve pahalı: `.claude/agents/` git'te izlenmiyor ⇒ `git status` hiçbir şey
göstermedi, `git checkout` geri getiremezdi. Kaybolanlar yaptırımlı rollerdi
(adt-gateway = tek SAP yazıcısı, bug-expert = BUG GATE). Ayrıca istisna `team_setup`
`main()`'ine kadar çıktı ⇒ kurulumun KALAN adımları (diğer 3 tip · dosya_tamamla ·
hookspath_* · _core_index_yenile) hiç koşmadı.

FIX iki değişmez taşır ve ikisi AYRI ölçülür:
  ① ATOMİKLİK  — dizin hiç silinmez: üzerine yaz → fazlalığı tek tek sil → manifest en son.
                 En kötü hâlde eski+yeni karışımı kalır; hiçbir noktada BOŞ kalmaz.
  ② DÜRÜSTLÜK  — üretim kendi çıktısını ölçmeden BAŞARILI demez (kanıt kapısı: core
                 okunamıyorsa DOKUNMA; son-durum öz-denetimi: eksik/frontmatter-bozuk
                 dosya varsa ok=False + hangi dizinin elden geçmesi gerektiği yazılır).
Tek mutasyon ikisini birden sınamaz; bu yüzden İKİ mutasyon modu vardır.

ÖLÇÜT (mutasyon etiketi):
  * P → fix'in GETİRDİĞİ ayrım. `--mutasyon` (TABAN_SHA) koşumunda DÜŞMELİ.
  * N → FP çapası: fix'in KORUMASI gereken eski doğru davranış. Her iki mutasyonda da
        ayakta kalmalı; kalmazsa fix bir şeyi sessizce bozmuş demektir.
  * D → DÜRÜSTLÜK değişmezi (②). `--mutasyon-gevsek` koşumunda DÜŞMELİ; `--mutasyon`da da
        düşer (taban sürümde hiç yok).
  * K → kontrol grubu / kablolama / komşu regresyon çapası.
  * G → ⚠GEVŞETME çapası: yeni kodun BİLEREK daha az sildiği yüzey (`.md` dışı dosya).
        Kaldırılırsa gevşemenin sınırı ölçüsüz kalır.

⚠ ÇAPALARI SİLME: N1-N7 fix'in "eski davranışı aynen üretiyor" kanıtıdır (son durum
bayt-bayt eski çıktıyla aynı olmalı). D1-D3 olmadan fix "hiç patlamayan ama yalan söyleyen"
bir üretime dönüşür — `exit 0 ≠ kanıt` sınıfı.

Koşum:    python tests/fixtures/overlay_materyalize_atomik/run.py
MUTASYON: python tests/fixtures/overlay_materyalize_atomik/run.py --mutasyon [--ref <SHA>]
              → kusurun CANLI olduğu sürümle koş; P ve D vektörleri DÜŞMELİ.
          python tests/fixtures/overlay_materyalize_atomik/run.py --mutasyon-gevsek
              → yalnız DÜRÜSTLÜK değişmezini sök (kanıt kapısı + öz-denetim); D DÜŞMELİ,
                P AYAKTA kalmalı ⇒ iki mutasyon birbirini KAPSAMAZ.
          ⛔ `--ref`e DAL ADI VERME (merge sonrası "fix sonrası"na kayar). Taban SHA'ya
          pinlidir ve koşucu tabanın GERÇEKTEN kusurlu olduğunu ön-doğrular; doğrulayamazsa
          hiçbir sayı BASMAZ (exit 2).

ÇIKIŞ KODU SÖZLEŞMESİ: normal modda 0=tümü geçti · 1=en az bir vektör düştü · 2=alet
geçersiz. Mutasyon modlarında 0 = ÖLÇÜM GEÇERLİ (düşen olması BEKLENEN sonuçtur) →
kararı `N/M OK` satırından oku, exit'ten DEĞİL.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
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
TEAM_REL = "scripts/team_setup.py"
# Kusurun CANLI olduğu SHA (Q30 vakasının koştuğu sürüm). Dal adı DEĞİL.
TABAN_SHA = "d51ba09"

SONUC: list[tuple[bool, str]] = []

# N8 dali icin kosum baglami (main() doldurur). Vektor fonksiyonu args almiyor.
# MUTASYON_KIPI YALNIZ taban-SHA kipinde True olur (--mutasyon); "gevsek" kip
# CANLI kaynagi kullanir, yani POSIX dali ONDA VARDIR -> orada istisna cikarsa
# bu GERCEK bir regresyondur ve FAIL olmalidir.
MUTASYON_KIPI = False
TAKLIT_POSIX = False


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((bool(ok), ad + (f" — {detay}" if detay else "")))


# ─────────────────────────────────────────────────────────────────────────────
# Sentetik core + proje
# ─────────────────────────────────────────────────────────────────────────────
def yaz(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", newline="\n")


def ajan(ad: str, govde: str) -> str:
    return f"---\nname: {ad}\ndescription: sentetik fixture ajani\n---\n\n{govde}\n"


def kur(tmp: Path, etiket: str, tipler=("agents",)) -> tuple[Path, Path]:
    """Sentetik (core, proje). Her tipte: alpha=core-only, beta=proje-override."""
    core = tmp / etiket / "core"
    proj = tmp / etiket / "proje"
    for t in tipler:
        govde = ajan if t in ("agents", "skills") else (lambda a, g: f"# {a}\n\n{g}\n")
        yaz(core / "claude" / t / "alpha.md", govde("alpha", "Alpha govdesi."))
        yaz(core / "claude" / t / "beta.md", govde("beta", "Core beta govdesi."))
        yaz(proj / "claude-local" / t / "beta.md", govde("beta", "PROJE beta govdesi."))
    (proj / ".claude").mkdir(parents=True, exist_ok=True)
    return core, proj


def imza(d: Path) -> dict:
    """Dizinin ölçülebilir hâli: {ad: bayt-uzunlugu}. Yoksa {}."""
    if not d.is_dir():
        return {}
    return {f.name: f.stat().st_size for f in sorted(d.iterdir()) if f.is_file()}


# ── Windows'un ölçülmüş davranışını taklit eden sahte shutil ────────────────
class _SahteShutil:
    """`rmtree`: önce İÇERİDEKİLERİ siler, sonra DİZİNİ silerken WinError 5 fırlatır.

    Bu, uydurulmuş bir senaryo değil; 2026-08-27'de canlı traceback'te ölçülen sıradır
    (`rmtree` içerik silmeyi tamamladı, `os.rmdir(h)` adımında PermissionError verdi).
    """

    def __init__(self) -> None:
        self.cagrildi = 0

    def rmtree(self, yol, *a, **k):
        self.cagrildi += 1
        yol = Path(yol)
        for f in list(yol.iterdir()):
            if f.is_file():
                f.unlink()
            else:
                shutil.rmtree(f, ignore_errors=True)
        raise PermissionError(13, "Access is denied", str(yol), 5)

    def __getattr__(self, ad):                      # geri kalan her şey gerçek shutil
        return getattr(shutil, ad)


@contextlib.contextmanager
def _shutil_enjekte(ov, sahte):
    """`shutil`i GERI ALINABILIR sekilde degistir.

    ⚠ Taban (kusurlu) surumde `shutil` GERCEK bir modul niteligidir; korumasizca
    `delattr` edilirse sonraki vektor `NameError` ile COKER ve kosucu "mutasyon
    kurulamadi"yi "mutasyon kacti" gibi gosterir (KURULAMADI != KACTI).
    """
    yok = object()
    eski = getattr(ov, "shutil", yok)
    ov.shutil = sahte
    try:
        yield sahte
    finally:
        if eski is yok:
            with contextlib.suppress(AttributeError):
                delattr(ov, "shutil")
        else:
            ov.shutil = eski


@contextlib.contextmanager
def _posix_symlink_taklidi(etkin: bool):
    """`os.rmdir`i POSIX symlink gibi davranmaya zorlar (ORTAMSIZ negatif kontrol).

    Neden gerekli: bu evde Linux ikizi kurulamiyor (WSL/docker yok). POSIX'te bir
    symlink DIZIN GIRDISI DEGILDIR -> `os.rmdir` NotADirectoryError verir; Windows'ta
    junction gercek bir dizin girdisi oldugu icin ayni cagri BASARILI olur. Yani
    platform farki bir ISTISNA TIPI farkidir ve tam olarak o taklit edilir.
    Kapsam DAR: yalniz N8'in `materyalize` cagrisini sarar, sonra geri alinir.
    """
    if not etkin:
        yield False
        return
    gercek = os.rmdir

    def sahte(yol, *a, **k):
        raise NotADirectoryError(20, "Not a directory", str(yol))

    os.rmdir = sahte
    try:
        yield True
    finally:
        os.rmdir = gercek


def _yaz_patlat(mod, patlayan: str):
    """`_yaz`i sar: adı `patlayan` olan dosyada OSError fırlat, diğerlerini gerçek yaz."""
    gercek = mod._yaz

    def sarmal(hedef_dosya, icerik):
        if Path(hedef_dosya).name == patlayan:
            raise PermissionError(13, "Access is denied", str(hedef_dosya), 5)
        return gercek(hedef_dosya, icerik)

    mod._yaz = sarmal
    return gercek


# ─────────────────────────────────────────────────────────────────────────────
# SENARYOLAR
# ─────────────────────────────────────────────────────────────────────────────
def senaryolar(ov, ts_kaynak: str, tmp: Path) -> None:
    # ═══ N — FIX ESKİ DOĞRU DAVRANIŞI AYNEN ÜRETİYOR MU (FP çapaları) ═══════
    core, proj = kur(tmp, "n1")
    ok, mesaj = ov.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents"
    icerik = {f.name for f in h.glob("*.md")}
    kontrol(ok and icerik == {"alpha.md", "beta.md"} and (h / ".overlay-manifest.json").is_file(),
            "N1 (N) taze uretim: beklenen kume + manifest", f"ok={ok} icerik={sorted(icerik)}")

    kontrol("CORE-URETILDI" in (h / "alpha.md").read_text(encoding="utf-8")
            and "CORE-URETILDI" not in (h / "beta.md").read_text(encoding="utf-8")
            and (h / "alpha.md").read_text(encoding="utf-8").startswith("---"),
            "N2 (N) damga: core dosyasi damgalanir, proje-override DAMGALANMAZ, "
            "damga frontmatter'dan SONRA")

    mf = json.loads((h / ".overlay-manifest.json").read_text(encoding="utf-8"))
    kontrol(mf["dosyalar"]["beta.md"]["kaynak"] == "proje"
            and mf["dosyalar"]["alpha.md"]["kaynak"] == "core"
            and all(k.get("uretilen_hash") for k in mf["dosyalar"].values()),
            "N3 (N) manifest semasi bozulmadi (kaynak + uretilen_hash)")

    once = imza(h)
    ok_b, _ = ov.materyalize(proj, core, "agents")
    kontrol(ok_b and imza(h) == once and ov.tazeleme_gerekli(proj, core, "agents") == [],
            "N4 (N) IDEMPOTANS: ikinci kosum bayt-bayt ayni sonuc, tazeleme_gerekli BOS")

    # T2.5 kapısı: elle düzeltme bayraksiz koşumda HÂLÂ durdurur
    yaz(h / "beta.md", (h / "beta.md").read_text(encoding="utf-8") + "\nELLE not.\n")
    ok_c, msg_c = ov.materyalize(proj, core, "agents")
    kontrol(not ok_c and "FARK VAR" in msg_c,
            "N5 (N) T2.5 kapisi bozulmadi: elle duzeltme -> bayraksiz uretim RED")
    ok_d, _ = ov.materyalize(proj, core, "agents", onayli=True)
    kontrol(ok_d and "ELLE not." not in (h / "beta.md").read_text(encoding="utf-8"),
            "N6 (N) --overlay-onayli hala EZEBILIYOR (onay kapisinin anlami korundu)")

    # fazlalık .md (core sildi) → onaylı koşumda SİLİNİR (eski davranış aynen)
    yaz(h / "gamma.md", ajan("gamma", "Fazlalik."))
    ok_e, _ = ov.materyalize(proj, core, "agents", onayli=True)
    kontrol(ok_e and not (h / "gamma.md").exists(),
            "N7 (N) fazlalik .md ONAYLI kosumda hala SILINIYOR (rmtree'siz de olsa)")

    # junction → gerçek dizine dönüşüm dalı (os.rmdir; hedefe DOKUNMAZ)
    core2, proj2 = kur(tmp, "n8")
    hj = proj2 / ".claude" / "agents"
    kaynak_dizin = core2 / "claude" / "agents"
    baglandi = _bagla(kaynak_dizin, hj)
    if baglandi:
        # ⛔ ISTISNA DISARI CIKARSA KOSUCU COKER ve 30+ vektorun HEPSI kaybolur
        # (olculdu 2026-08-29, CI run 33267199186: `COKTU(rc=2)` NotADirectoryError).
        # Taban surum (d51ba09:224) CIPLAK `os.rmdir(h)` cagirir -- 2026-08-27 fix'inin
        # getirdigi `except NotADirectoryError -> unlink` dali ONDA YOKTUR. POSIX'te
        # symlink dizin girdisi olmadigi icin bu, tabanin BILINEN eksigidir; Windows'ta
        # junction dizin oldugu icin dal hic tetiklenmez. Ayrim ETIKETLI sonuc olarak
        # raporlanir -- cokme DEGIL.
        try:
            with _posix_symlink_taklidi(TAKLIT_POSIX):
                ok_f, _ = ov.materyalize(proj2, core2, "agents")
        except NotADirectoryError as exc:
            if MUTASYON_KIPI:
                kontrol(True, "N8 (N) ATLANDI/BILINEN: taban surum POSIX symlink dalina "
                              "sahip degil (2026-08-27 fix'i) -- P-korlugu KORUNUR",
                        f"{type(exc).__name__}: {exc}")
            else:
                kontrol(False, "N8 (N) junction -> gercek dizin donusumu ISTISNA ATTI "
                               "(fix'li surumde bu dal CALISMALI)",
                        f"{type(exc).__name__}: {exc}")
        else:
            kontrol(ok_f and hj.is_dir() and not _junction_mu_yerel(hj)
                    and (kaynak_dizin / "alpha.md").is_file(),
                    "N8 (N) junction -> gercek dizin donusumu calisiyor, CORE hedefi dokunulmadan duruyor")
    else:
        kontrol(True, "N8 (N) ATLANDI: bu ortamda junction/symlink kurulamadi (not: gorunur)")

    # ═══ P — ATOMİKLİK (①) ══════════════════════════════════════════════════
    # P1 ⭐ AYIRT EDİCİ: dizin-silme basarisiz olsa bile dizin BOSALMAZ.
    core, proj = kur(tmp, "p1")
    ov.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents"
    onceki = imza(h)
    sahte = _SahteShutil()
    with _shutil_enjekte(ov, sahte):
        try:
            p1_ok, p1_msg = ov.materyalize(proj, core, "agents", onayli=True)
        except Exception as exc:                    # taban surum: istisna DISARI cikar
            p1_ok, p1_msg = None, f"{type(exc).__name__}: {exc}"
    kontrol(imza(h) == onceki and set(onceki) >= {"alpha.md", "beta.md"},
            "P1 (P) ⭐ dizin-silme COKSE BILE .claude/agents BOSALMAZ",
            f"sonra={sorted(imza(h))} rmtree_cagrildi={sahte.cagrildi} sonuc={p1_msg}")
    kontrol(sahte.cagrildi == 0,
            "P1b (P) uretim yolunda rmtree HIC cagrilmiyor (davranissal capa)",
            f"cagri={sahte.cagrildi}")

    # P2 — YAPISAL çapa: `materyalize` govdesinde rmtree/rmtree-benzeri yikim YOK (AST)
    kontrol(*_ast_yikim_yok(ov))

    # P3 — TEK DOSYA yazilamazsa: digerleri YERINDE kalir + ok=False
    core, proj = kur(tmp, "p3")
    ov.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents"
    eski_yaz = ov._yaz
    _yaz_patlat(ov, "beta.md")
    try:
        p3_ok, p3_msg = ov.materyalize(proj, core, "agents", onayli=True)
    except Exception as exc:
        p3_ok, p3_msg = None, f"{type(exc).__name__}: {exc}"
    finally:
        ov._yaz = eski_yaz
    kontrol((h / "alpha.md").is_file() and (h / "beta.md").is_file(),
            "P3 (P) tek dosya yazilamayinca DIGERLERI yerinde kalir (yikim yok)",
            f"icerik={sorted(imza(h))} sonuc={p3_msg}")
    kontrol(p3_ok is False and "URETIM EKSIK" in str(p3_msg),
            "P3b (D) ... ve sonuc BASARISIZ raporlanir (sessiz yarim uretim yok)",
            f"ok={p3_ok} msg={str(p3_msg)[:120]}")

    # P4 — 3. BAĞLAM (gorev-DISI tip): `commands` (frontmatter'siz, damga BASA girer)
    core, proj = kur(tmp, "p4", tipler=("commands",))
    ov.materyalize(proj, core, "commands")
    hc = proj / ".claude" / "commands"
    onceki_c = imza(hc)
    sahte_c = _SahteShutil()
    with _shutil_enjekte(ov, sahte_c):
        try:
            ov.materyalize(proj, core, "commands", onayli=True)
        except Exception:
            pass
    kontrol(imza(hc) == onceki_c and "derle" not in str(onceki_c),
            "P4 (P) 3.BAGLAM `commands` tipi: ayni sinif, ayni sonuc (dizin BOSALMAZ)",
            f"sonra={sorted(imza(hc))}")

    # ═══ D — DÜRÜSTLÜK (②) ══════════════════════════════════════════════════
    # D1 — KANIT KAPISI: core/claude/<tip> okunamiyorsa DOKUNMA (en pahali yanlis:
    # uretilecek kume core'suz hesaplanir -> core kopyalarinin HEPSI fazlalik sayilir)
    core, proj = kur(tmp, "d1")
    ov.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents"
    onceki = imza(h)
    shutil.rmtree(core / "claude" / "agents")
    d1_ok, d1_msg = None, ""
    try:
        d1_ok, d1_msg = ov.materyalize(proj, core, "agents", onayli=True)
    except Exception as exc:
        d1_msg = f"{type(exc).__name__}: {exc}"
    kontrol(imza(h) == onceki,
            "D1 (D) core/claude/agents okunamiyor -> kopyalara DOKUNULMADI",
            f"once={sorted(onceki)} sonra={sorted(imza(h))} msg={str(d1_msg)[:110]}")
    kontrol(d1_ok is False and "okunamadi" in str(d1_msg),
            "D1b (D) ... ve bu atlama GORUNUR (KOSMADI != TEMIZ)", f"msg={str(d1_msg)[:110]}")

    # D2 — SON-DURUM OZ-DENETIMI: uretilen dosya YUKLENEMEZ halde ise ok=False
    # ("SAYI != YUKLENEBILIRLIK" — 2026-07-09'da 6/6 ajan yuklenemedi ve sistem "guncel" dedi)
    core, proj = kur(tmp, "d2")
    yaz(core / "claude" / "agents" / "alpha.md", "Frontmatter YOK.\n")   # damga BASA girer
    d2_ok, d2_msg = ov.materyalize(proj, core, "agents", onayli=True)
    kontrol(d2_ok is False and "frontmatter-bozuk" in str(d2_msg)
            and "alpha.md" in str(d2_msg),
            "D2 (D) frontmatter'i bozuk uretim BASARILI sayilmaz (sayi != yuklenebilirlik)",
            f"ok={d2_ok} msg={str(d2_msg)[:150]}")
    kontrol(str(proj / ".claude" / "agents") in str(d2_msg),
            "D2b (D) hata mesaji ELDEN GECIRILECEK DIZINI adiyla soyler (eyleme donuk)",
            f"msg={str(d2_msg)[:150]}")

    # D3 — GERÇEK ŞEKİL (3. bağlam, canlı ölçümden): `core/claude/skills` DİZİN tabanlıdır
    # (`intake-triage/SKILL.md`), kökünde `*.md` YOKTUR. Overlay mekanizması bastan sona
    # `*.md` glob'una dayandigi icin bir proje `claude-local/skills/` acarsa "uretilecek
    # kume" core skill'lerini HIC icermez ⇒ eski kod `.claude/skills`i core'suz uretirdi
    # (tum core skill'lerine erisim kaybi, SESSIZ). Kanit kapisi bunu GORUNUR REDDE cevirir
    # ve otomatik yolun V7 capasiyla PARITE saglar.
    core, proj = kur(tmp, "d3")
    yaz(core / "claude" / "skills" / "ornek-skill" / "SKILL.md", ajan("ornek", "Dizin tabanli skill."))
    yaz(proj / "claude-local" / "skills" / "yerel.md", ajan("yerel", "Proje skill'i."))
    d3_ok, d3_msg = ov.materyalize(proj, core, "skills", onayli=True)
    hs = proj / ".claude" / "skills"
    kontrol(d3_ok is False and not any(hs.glob("*.md")) if hs.is_dir() else d3_ok is False,
            "D3 (D) 3.BAGLAM gercek sekil: dizin-tabanli `skills` -> uretim REDDEDILIR "
            "(sessiz kayip yerine gorunur ret)",
            f"ok={d3_ok} msg={str(d3_msg)[:110]}")

    # ═══ G — ⚠GEVŞETME çapası (yeni kod BİLEREK daha az siliyor) ════════════
    core, proj = kur(tmp, "g1")
    ov.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents"
    yaz(h / "notlar.txt", "elle birakilmis .md DISI dosya\n")
    g_ok, g_msg = ov.materyalize(proj, core, "agents", onayli=True)
    kontrol(g_ok and (h / "notlar.txt").is_file(),
            "G1 (G) ⚠GEVSETME: .md DISI dosya artik SILINMIYOR (eski rmtree siliyordu)",
            f"ok={g_ok}")
    kontrol("notlar.txt" in str(g_msg),
            "G1b (G) ... ama SESSIZ degil: mesajda adiyla listelenir", f"msg={g_msg}")

    # ═══ K — kablolama / komşu regresyon ════════════════════════════════════
    # K1 — ATOMIKLIK capasinin komsusu: `oto_tazele` zincirinde materyalize YOK
    kontrol(*_ast_oto_zinciri_temiz(ov))

    # K2 — komsu yol (`_yerinde_senkron`/oto_tazele) davranisi BOZULMADI
    core, proj = kur(tmp, "k2")
    ov.materyalize(proj, core, "agents")
    h = proj / ".claude" / "agents"
    yaz(core / "claude" / "agents" / "alpha.md", ajan("alpha", "Alpha govdesi. CORE DEGISTI."))
    satirlar = ov.oto_tazele(proj, core) if hasattr(ov, "oto_tazele") else []
    kontrol("CORE DEGISTI" in (h / "alpha.md").read_text(encoding="utf-8")
            and any("tazelendi" in s for s in satirlar),
            "K2 (K) komsu OTOMATIK yol bozulmadi (oto_tazele hala tazeliyor)",
            f"satirlar={satirlar}")

    # K3 — KABLOLAMA: team_setup.junctions TIP-BASINA YALITILMIS mi?
    kontrol(*_team_setup_yalitim(ts_kaynak, ov, tmp))


def _junction_mu_yerel(p: Path) -> bool:
    try:
        return p.is_dir() and os.path.realpath(p) != os.path.abspath(p)
    except OSError:
        return False


def _bagla(hedef: Path, link: Path) -> bool:
    """Windows: junction (mklink /J) · digerleri: symlink. Kurulamazsa False (GORUNUR)."""
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == "nt":
            r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(hedef)],
                               capture_output=True, text=True)
            return r.returncode == 0
        os.symlink(str(hedef), str(link), target_is_directory=True)
        return True
    except OSError:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# YAPISAL (AST) çapalar — kaynağı MODÜLLE AYNI YERDEN okur (mutasyonda git'ten)
# ─────────────────────────────────────────────────────────────────────────────
def _fonk_kaynagi(ov, ad: str):
    import ast
    metin = getattr(ov, "__fixture_kaynak__", None)
    if metin is None:
        metin = (KOK / MODUL_REL).read_text(encoding="utf-8")
    agac = ast.parse(metin)
    for d in ast.walk(agac):
        if isinstance(d, ast.FunctionDef) and d.name == ad:
            return d, agac
    return None, agac


def _cagrilar(d) -> set:
    import ast
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


def _ast_yikim_yok(ov):
    d, _ = _fonk_kaynagi(ov, "materyalize")
    if d is None:
        return False, "P2 (P) YAPISAL capa: materyalize bulunamadi (alet arizasi)"
    c = _cagrilar(d)
    kirli = sorted(x for x in c if "rmtree" in x)
    return (not kirli,
            "P2 (P) YAPISAL: materyalize govdesinde rmtree YOK (yorum/dizge degil AST)",
            f"bulunan={kirli}")


def _ast_oto_zinciri_temiz(ov):
    import ast
    metin = getattr(ov, "__fixture_kaynak__", None)
    if metin is None:
        metin = (KOK / MODUL_REL).read_text(encoding="utf-8")
    agac = ast.parse(metin)
    fonk = {d.name: d for d in ast.walk(agac) if isinstance(d, ast.FunctionDef)}
    if "oto_tazele" not in fonk:
        return True, "K1 (K) taban surumde oto_tazele yok — capa uygulanmaz (kontrol grubu)"
    goruldu, kuyruk, zincir = set(), ["oto_tazele"], set()
    while kuyruk:
        ad = kuyruk.pop()
        if ad in goruldu or ad not in fonk:
            continue
        goruldu.add(ad)
        for c in _cagrilar(fonk[ad]):
            zincir.add(c)
            if c in fonk:
                kuyruk.append(c)
    temiz = "materyalize" not in zincir and not any("rmtree" in x for x in zincir)
    return (temiz,
            "K1 (K) komsu capa AYAKTA: oto_tazele zincirinde materyalize/rmtree YOK",
            f"gezilen={sorted(goruldu)}")


# ─────────────────────────────────────────────────────────────────────────────
# KABLOLAMA — team_setup.junctions tip-başına yalıtım
# ─────────────────────────────────────────────────────────────────────────────
def _team_setup_yalitim(ts_kaynak: str, ov, tmp: Path):
    """`agents` tipinde istisna firlarsa DIGER tipler yine kurulur mu?

    Olculen zarar buydu: istisna `main()`e kadar cikti ve dongunun kalan tipleri +
    dosya_tamamla + hookspath_* + _core_index_yenile HIC kosmadi.
    """
    tipler = ("agents", "skills", "commands", "rules")
    core, proj = kur(tmp, "k3", tipler=tipler)

    # sandbox core'a modulun SINANAN surumunu koy + `agents`i zehirle
    modul_kaynak = getattr(ov, "__fixture_kaynak__", None)
    if modul_kaynak is None:
        modul_kaynak = (KOK / MODUL_REL).read_text(encoding="utf-8")
    zehir = (modul_kaynak + "\n\n_ORJ_MAT = materyalize\n"
             "def materyalize(proje, core_root, tip, onayli=False):\n"
             "    if tip == 'agents':\n"
             "        raise RuntimeError('Q30 sentetik: agents tipinde patla')\n"
             "    return _ORJ_MAT(proje, core_root, tip, onayli)\n")
    yaz(core / "scripts" / "utils" / "claude_overlay.py", zehir)

    ts_yol = tmp / "k3" / "_ts" / "team_setup.py"
    yaz(ts_yol, ts_kaynak)
    spec = importlib.util.spec_from_file_location("q30_team_setup", ts_yol)
    if spec is None or spec.loader is None:
        return False, "K3 (K) KABLOLAMA DOGRULANAMADI: team_setup yuklenemedi"
    ts = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(ts)
    except Exception as exc:                                   # noqa: BLE001
        return False, f"K3 (K) KABLOLAMA DOGRULANAMADI: team_setup import hatasi — {exc}"

    ts.CORE_ROOT = core
    ts.junction_kur = lambda link, hedef: True     # mklink platform-bagimliligini ele
    yol_eklendi = str(core / "scripts")
    for ad in [a for a in sys.modules if a == "utils" or a.startswith("utils.")]:
        sys.modules.pop(ad, None)
    try:
        with contextlib.redirect_stdout(io.StringIO()) as tut:
            try:
                ok = ts.junctions(proj, overlay_onayli=True)
            except Exception as exc:               # noqa: BLE001
                ok, tut = None, io.StringIO(f"ISTISNA DISARI CIKTI: {type(exc).__name__}")
    finally:
        for ad in [a for a in sys.modules if a == "utils" or a.startswith("utils.")]:
            sys.modules.pop(ad, None)
        while yol_eklendi in sys.path:
            sys.path.remove(yol_eklendi)

    kurulan = [t for t in ("skills", "commands", "rules")
               if (proj / ".claude" / t / "alpha.md").is_file()]
    return (sorted(kurulan) == ["commands", "rules", "skills"] and ok is False,
            "K3 (K) KABLOLAMA: `agents` patlasa da DIGER 3 tip kuruluyor ve kurulum "
            "yine de BASARISIZ sayiliyor",
            f"kurulan={kurulan} ok={ok} cikti={' '.join(tut.getvalue().split())[:170]}")


# ─────────────────────────────────────────────────────────────────────────────
# Mutasyon altyapısı
# ─────────────────────────────────────────────────────────────────────────────
def _git_show(ref: str, rel: str):
    r = subprocess.run(["git", "-C", str(KOK), "show", f"{ref}:{rel}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else None


def _modul_yukle(kaynak, tmp: Path, etiket: str):
    if kaynak is None:
        yol = KOK / MODUL_REL
        metin = yol.read_text(encoding="utf-8")
    else:
        yol = tmp / f"_modul_{etiket}" / "claude_overlay.py"
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(kaynak, encoding="utf-8", newline="\n")
        metin = kaynak
    spec = importlib.util.spec_from_file_location(f"q30_overlay_{etiket}", yol)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.__fixture_kaynak__ = metin        # AST çapaları MODÜLLE AYNI kaynağı okusun
    return mod


def _gevsek(kaynak: str):
    """DÜRÜSTLÜK değişmezini (②) sök; ATOMİKLİĞİ (①) bozma.

    İki nokta: (a) kanıt kapısı devre dışı, (b) eksik/bozuk üretim BAŞARILI raporlanır.
    Beklenen: D vektörleri düşer, P vektörleri AYAKTA kalır ⇒ iki mutasyon birbirini
    kapsamıyor.
    """
    a = 'if not core_dizin.is_dir() or not any(core_dizin.glob("*.md")):'
    b = 'if yazilamayan or eksik or bozuk:\n        return False, (mesaj'
    if a not in kaynak or b not in kaynak:
        return None
    kaynak = kaynak.replace(a, "if False:", 1)
    kaynak = kaynak.replace(b, 'if yazilamayan or eksik or bozuk:\n        return True, (mesaj', 1)
    return kaynak


def _taban_kusurlu_mu(kaynak: str) -> str:
    """ÖZ-DENETİM: taban sürüm GERÇEKTEN kusurlu mu? Değilse hiçbir sayı basma."""
    import ast
    agac = ast.parse(kaynak)
    for d in ast.walk(agac):
        if isinstance(d, ast.FunctionDef) and d.name == "materyalize":
            if any("rmtree" in c for c in _cagrilar(d)):
                return ""
            return "taban surumde materyalize icinde rmtree YOK — bu taban kusurlu degil"
    return "taban surumde materyalize fonksiyonu YOK"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true",
                    help="kusurun CANLI oldugu surumle kos (P + D dusmeli)")
    ap.add_argument("--mutasyon-gevsek", action="store_true",
                    help="yalniz DURUSTLUK degismezini sok (D dusmeli, P ayakta)")
    ap.add_argument("--ref", default=TABAN_SHA)
    # ORTAMSIZ NEGATIF KONTROL (kip DEGIL -- batarya kesfi `--mutasyon...` arar, bu ad
    # eslesmez; bilerek boyle adlandirildi ki yeni bir mutasyon kipi SAYILMASIN).
    ap.add_argument("--taklit-posix-symlink", action="store_true",
                    help="N8'de os.rmdir'i NotADirectoryError attirir (Linux ikizi yok)")
    a = ap.parse_args()

    global MUTASYON_KIPI, TAKLIT_POSIX
    MUTASYON_KIPI = bool(a.mutasyon)
    TAKLIT_POSIX = bool(a.taklit_posix_symlink)

    if a.mutasyon and a.mutasyon_gevsek:
        print("[DOGRULANAMADI] iki mutasyon modu ayni anda verilemez")
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="q30_atomik_"))
    try:
        ts_kaynak = (KOK / TEAM_REL).read_text(encoding="utf-8")
        if a.mutasyon:
            kaynak = _git_show(a.ref, MODUL_REL)
            ts_taban = _git_show(a.ref, TEAM_REL)
            if kaynak is None or ts_taban is None:
                print(f"[DOGRULANAMADI] taban alinamadi: {a.ref}")
                return 2
            hata = _taban_kusurlu_mu(kaynak)
            if hata:
                print(f"[DOGRULANAMADI] oz-denetim: {hata} (ref={a.ref})")
                return 2
            ts_kaynak = ts_taban
            mod = _modul_yukle(kaynak, tmp, "taban")
            etiket = f"MUTASYON (taban {a.ref})"
        elif a.mutasyon_gevsek:
            kaynak = _gevsek((KOK / MODUL_REL).read_text(encoding="utf-8"))
            if kaynak is None:
                print("[DOGRULANAMADI] gevsek mutasyon capalari tutmadi "
                      "(kod degisti mi? tarifi guncelle)")
                return 2
            mod = _modul_yukle(kaynak, tmp, "gevsek")
            etiket = "MUTASYON-GEVSEK (durustluk degismezi sokuldu)"
        else:
            mod = _modul_yukle(None, tmp, "canli")
            etiket = "NORMAL"
        if mod is None:
            print("[DOGRULANAMADI] modul yuklenemedi")
            return 2

        senaryolar(mod, ts_kaynak, tmp)
    except Exception as exc:                                   # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"[DOGRULANAMADI] kosucu coktu: {type(exc).__name__}: {exc}")
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    print(f"--- overlay_materyalize_atomik [{etiket}] ---")
    for ok, ad in SONUC:
        print(f"  {'OK  ' if ok else 'FAIL'}  {ad}")
    print(f"{gecen}/{len(SONUC)} OK")
    if a.mutasyon or a.mutasyon_gevsek:
        print("(mutasyon modu: exit 0 = OLCUM GECERLI; karar N/M satirindan okunur)")
        return 0
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
