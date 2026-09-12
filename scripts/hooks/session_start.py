#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ENFORCES: ADR-0020  (ADR 0019 coverage binding)
"""SessionStart hook — yasaklar + protokol enjeksiyonu + SAĞLIK KONTROLLERİ (B9b, ADR 0020).

Statik gövde İKİ dallıdır (girdideki `source` alanına göre; 2026-08-29):
  `STATIK`         — startup/resume/clear/fork VE tanınmayan/eksik `source` (fail-safe yön
                     = bugünkü davranış): ADR 0005 yasak özeti + Ekran-Teyidi zorunluluğu
                     + ADR 0018 çalışma modeli.
  `STATIK_COMPACT` — YALNIZ `source == "compact"`: Ekran-Teyidi satırı ÇIKARILIR (compact
                     yeni oturum değildir; harness'ın compact talimatıyla çelişiyordu),
                     yerine git'ten türetilmiş DURUM ÇAPASI eklenir (`_git_capa`).
Sağlık kontrolleri HER İKİ dalda da koşar (gerekçe `main()` içinde).

Dinamik (v3 mimarisi):
  D25 — 4 junction TEK TEK sağlam mı (kopuk agents/skills SESSİZ semptom verir)
  D7  — settings.json + hook_shim.py template-drift'i
  F2  — behavior-manifest diff (kayıtsız/değişmiş davranış dosyası → BÜYÜK uyarı)
  Ö3  — DEV_CORE origin-geride mi (THROTTLE: saatte 1 fetch, 2 sn timeout, cache .tmp/)
  D20b— detached@stable ise sakin bilgi (origin-geride yanlış-alarmı üretme)

Proje kökü: env CLAUDE_PROJECT_DIR → cwd (B9-fix: __file__ junction'la CORE'a çözülür).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

PROJ = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
CORE = PROJ / "core"


def _write_session_marker(data: dict) -> None:
    """Seans kimliği → .claude/.current_session (pull-before-edit, ADR 0016). Fail-safe."""
    try:
        sid = data.get("session_id")
        if not sid:
            return
        marker = PROJ / ".claude" / ".current_session"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"session_id": sid}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


STATIK = (
    "[session-loader hook]\n"
    "ZORUNLU: Yeni oturumun ILK yaniti CLAUDE.core.md §3 'Ekran Teyidi' formatiyla baslar.\n"
    # Q286 C3: 23 gun boyunca teyit "core yuklendi" dedi, core YUKLENMIYORDU. Beyan yerine olcum.
    "  Yukleme satirini ([YUKLEME — session_start]) AYNEN aktar; 'yuklendi' diye kendin beyan etme.\n"
    "ADR 0005 KESIN YASAKLAR aktif (A/B/C/D) — TAM metin kok CLAUDE.md fiziksel damgasinda "
    "(compact sonrasi CLAUDE.md ile geri gelir; damga=kanonik, check_kesin_yasaklar esligi zorlar).\n"
    "SAP yazma oncesi run_review.py (ADR 0006). Validator FAIL -> once duzelt (STOP).\n"
    "ARAMA (D29): metodoloji araması DAIMA path=core/ ile — kok-Grep core'u GORMEZ.\n"
    "\n"
    "CALISMA MODELI (ADR 0018 = LAZY/on-demand):\n"
    "  Oturum basinda roster SPAWN ETME. Ihtiyac aninda scoped spawn + bitince kapat.\n"
    "  Roller (.claude/agents/): adt-gateway (TEK SAP yazici; standing) ; frontend-expert ;\n"
    "     backend-expert ; bug-expert (adversarial, read-only, HER ZAMAN taze).\n"
    "  BUG GATE: expert substantive build bitince bug-expert'e -> PASS/WARNING/BLOCKER.\n"
    # ⚠ `core/` oneki ZORUNLU: bu metin PROJE kokunde okunur ve D29 geregi kok-Grep core'u
    # GORMEZ; `governance/...` proje kokunden cozulmez => isaretci KIRIK olur ve calisma
    # modeli fiilen okunamaz. Ayni sinif 2026-08-2x'de `run_review.py` icin 6 yuzeyde
    # kapatilmisti (#68); bu satir o kapanisin DISINDA kalmisti. Kardes yazim: :88 · :113 · :270.
    "  Kullanici 'solo' derse spawn etme. Detay: core/governance/agent-teams-operating-model.md"
)

# ── COMPACT SONRASI GOVDE (2026-08-29) ────────────────────────────────────────
# NEDEN AYRI: `STATIK`in ilk satiri *"Yeni oturumun ILK yaniti ... Ekran Teyidi"* der.
# Compact YENI OTURUM DEGILDIR ve harness'in compact-sonrasi talimati bunun TERSINI
# soyler (*"ozeti anma, kaldigin yerden devam et"*). Olculdu (tek oturum, 2026-08-29):
# 4 compact -> celiskili talimat 4 kez enjekte edildi. Lider harness'i tercih etti ama
# bu bir TERCIHTI, garanti degil. Kaynak alani `source` (startup|resume|clear|compact|
# fork) SessionStart girdisinde ZATEN var; bugune kadar okunmuyordu.
#
# ⛔ SATIR SECIMI KORLEMESINE DEGIL, TEK OLCUTLE YAPILDI:
#    "bu satir compact sonrasi kaybolursa lider YANLIS BIR ADIM atabilir mi?"
#    Ayrim ekseni: OTURUM-BASI semantigi olan satir DUSER, SONRAKI EYLEMI baglayan
#    yukumluluk KALIR. Kalan/dusen gerekceleri:
#  DUSTU · "Yeni oturumun ILK yaniti" (Ekran Teyidi): metnin KENDISI oturum-basi
#          semantigi tasiyor + harness talimatiyla dogrudan celisiyor. Celiskinin koku.
#  DUSTU · "Oturum basinda roster SPAWN ETME" ifadesi + 3 satirlik ROL SAYIMI: ilki gene
#          oturum-basi semantigi; rol listesi `.claude/agents/` altindan kesfedilebilir ve
#          proje compact-talimatinin 6. maddesi *"kosan alt ajan varsa hangisi"*yi ZATEN
#          korur. Lazy ilkesinin kendisi asagida tek satira indi + isaretci duruyor.
#  KALDI · ADR 0005 yasaklar: geri-alinamaz SAP hasarinin tek kapisi; en yuksek bedel,
#          en ucuz satir. (Tam metin kok CLAUDE.md damgasinda; bu yalnizca "AKTIF" der.)
#  KALDI · run_review.py: BIR SONRAKI SAP yazimini baglayan on-kapi; proje compact-
#          talimatinin koruma listesinde boyle bir "gelecekteki yukumluluk" maddesi YOK.
#  KALDI · adt-gateway + BUG GATE: ikisi de gelecekteki bir olayla tetiklenen yonlendirme
#          yukumlulugu (SAP yazimi / expert build bitisi) — run_review ile ayni sinif.
#  KALDI · D29: compact sonrasi her metodoloji Grep'ini yonetir; kaybolursa arama
#          "bulunamadi" doner ve bu "YOK" diye okunur (bilinen kusur sinifi).
#  EKLENDI (2026-09-12, Q286 M6) · cekirdek compact sonrasi GERI GELIR: kaybolursa lider
#          ya "cekirdek gitti" deyip elle yeniden okur (bosa tur) ya da tersine `paths:`li
#          bir kuralin da dondugunu sanip eslesen dosyayi okumadan o kurala guvenir. OLCUM
#          (claude -p + `/compact`, 2.1.269, N=1): IL `load_reason=compact` → 00-claude-core.md
#          + CLAUDE.md (pozitif kontrol); `paths:`li kural compact'ta YOK, eslesen dosya
#          okununca `path_glob_match`. Interaktif/otomatik compact OLCULMEDI (niteleyici metinde).
STATIK_COMPACT = (
    "[session-loader hook — COMPACT sonrasi]\n"
    "Bu YENI BIR OTURUM DEGIL: harness'in compact talimati gecerlidir "
    "(ozeti anma, kaldigin yerden devam et). Ekran Teyidi ISTENMIYOR.\n"
    "Cekirdek (.claude/rules/00-claude-core.md) compact sonrasi YENIDEN yuklenir (olculdu, print modu); "
    "paths:'li kurallar ancak eslesen dosya yeniden okununca doner.\n"
    "HALA YURURLUKTE — ADR 0005 KESIN YASAKLAR (A/B/C/D); tam metin kok CLAUDE.md "
    "fiziksel damgasinda.\n"
    "SAP yazma oncesi run_review.py (ADR 0006). Validator FAIL -> once duzelt (STOP).\n"
    "SAP yazimi TEK kanaldan: adt-gateway. Expert substantive build bitince "
    "BUG GATE -> bug-expert.\n"
    "ARAMA (D29): metodoloji araması DAIMA path=core/ ile — kok-Grep core'u GORMEZ.\n"
    "Calisma modeli LAZY (ADR 0018): ihtiyac aninda scoped spawn. "
    "Detay: core/governance/agent-teams-operating-model.md"
)


def _overlay_oto_tazele() -> list[str]:
    """Overlay'li tipleri açılışta KENDİLİĞİNDEN tazele (2026-08-13, kullanıcı onaylı).

    Neden BURADA: bayatlığı bugüne kadar RAPOR eden yer burasıydı ve kullanıcıdan tek
    istenen şey `team_setup.py`'yi koşmaktı — yani komut, bilgiyi zaten burada olan bir
    işin elle tekrarıydı. Junction'lı tipler (`skills`/`commands`/`rules`) tazeliği
    bedavaya alıyor; `agents` yalnız TEK bir proje-override yüzünden kopya olduğu için
    alamıyordu. Karar `claude_overlay.oto_tazele`'de (fark boşsa üret, doluysa dokunma).

    ⚠ SIRA ÖNEMLİ — bu, `_junction_kontrol`'den ÖNCE çağrılır: core'a yeni bir ajan
    dosyası eklendiğinde `durum()` "overlay'de EKSİK" der, o satır ⛔ dalına düşer ve
    ALTINDAKİ tüm kontrolleri bastırır ⇒ else-dalına konsaydı tam da düzeltmesi gereken
    vakada hiç koşmazdı (kod ≠ kablolama).
    """
    try:
        sys.path.insert(0, str(CORE / "scripts"))
        from utils import claude_overlay as ov  # type: ignore
        return ov.oto_tazele(PROJ, CORE)
    except Exception as e:  # noqa: BLE001
        return [f"overlay OTO-TAZELEME yuklenemedi: {type(e).__name__}: {e} "
                f"(oturum bozulmadi; elle: python core/scripts/team_setup.py --repair-junctions)"]


def _junction_kontrol() -> list[str]:
    """D25: junction'lar tek tek. OVERLAY'li tipler (claude-local/<tip>) gerçek dizindir.

    Q286 (2026-09-12): ZORUNLU tip (`rules`) claude-local OLMADAN da gerçek dizindir; o
    dizin varsa `durum()` ile tazeliği/eksiği denetlenir. Hâlâ junction ya da YOK ise bu
    listeye GİRMEZ — ⛔ dalı altındaki TÜM sağlık kontrollerini bastırırdı (canlı 4 projenin
    merge-sonrası ilk açılışları tam bu durumdadır); o hâli `_yukleme_satiri` raporlar.
    """
    sorun = []
    try:
        sys.path.insert(0, str(CORE / "scripts"))
        from utils import claude_overlay as ov  # type: ignore
        gerekli = getattr(ov, "overlay_gerekli", ov.overlay_var_mi)
        zorunlu = getattr(ov, "ZORUNLU_TIPLER", ())
        overlayli = set()
        for t in ov.TIPLER:
            if not gerekli(PROJ, t):
                continue
            h = PROJ / ".claude" / t
            if t in zorunlu and not ov.overlay_var_mi(PROJ, t) and \
                    (not h.is_dir() or ov._junction_mu(h, PROJ)):
                continue                  # junction/yok → YÜKLEME satırı raporlar (⛔'ye düşürülmez)
            overlayli.add(t)
        for t in overlayli:
            _, s = ov.durum(PROJ, CORE, t)
            sorun.extend(f"overlay {x}" for x in s if "GÜNCELLENDİ" not in x)
    except Exception:
        overlayli = set()

    plan = [("core", CORE)]
    plan += [(f".claude/{t}", PROJ / ".claude" / t)
             for t in ("agents", "skills", "commands") if t not in overlayli]
    for ad, p in plan:
        try:
            hedef = os.readlink(p)
        except (OSError, ValueError):
            hedef = None
        if not p.exists() or (hedef is None and not (p / ".").exists()):
            sorun.append(f"junction KOPUK/YOK: {ad} → onarim: python core/scripts/team_setup.py --repair-junctions")
        elif hedef is None:
            sorun.append(f"{ad} junction DEGIL gercek klasor — sizinti riski, elle incele")
    return sorun


# ── YÜKLEME SATIRI (2026-09-12, kayıt Q286 C2) ────────────────────────────────
# SORU: "bu oturumda CLAUDE.core.md + rules yüklendi mi?" 23 gün boyunca Ekran Teyidi
# "✓ Core loader yüklendi" dedi, oysa harness junction'daki dosyaları dış import sayıp
# YÜKLEMİYORDU (Q286). Serbest beyan yerine bu satır basılır ve Ekran Teyidi onu AYNEN aktarır.
# ⛔ ÖLÇÜLMÜŞ SIRA (2.1.269, 3/3): SessionStart hook'u InstructionsLoaded olaylarından ÖNCE
# koşar (IL +446..+593 ms, SS bitmeden) ⇒ BU oturumun yüklemesi burada ÖLÇÜLEMEZ. Bekleyerek
# ölçmek (polling) bilinçle REDDEDİLDİ: yarıştır ve her açılışa gecikme ekler.
# ⇒ İki parça: ① ÖN KOŞUL (deterministik, diskten) ② ÖNCEKİ OTURUMUN ÖLÇÜLMÜŞ değeri
#   (logger'ın `sid=` kolonundan; "bu oturum" İMA EDİLMEZ, sid8 + zaman yazılır).
# ⛔ "Ölçemedim" hiçbir dalda "YÜKLENDİ"ye de "YÜKLENMEDİ"ye de ÇÖKMEZ → `_OLCULEMEDI`.
# ⚠ BİLİNÇLİ İSTİSNA: "temizken sağlık kontrolleri SESSİZDİR" sözleşmesinin (main()) DIŞINDADIR —
#   bu satır HER açılışta (startup + compact) basılır, çünkü Ekran Teyidi onu alıntılar.
_OLCULEMEDI = "ÖLÇÜLEMEDİ"
_CORE_ADLARI = ("00-claude-core.md", "CLAUDE.core.md")


def _dis_importlar(claude_md: Path) -> list[str]:
    """CLAUDE.md'deki `@yol` importlarından PROJE DIŞINA çözülen ya da çözülmeyenler.

    Harness dış importu (junction ardı dahil) onaysız YÜKLEMEZ (Q286 t1/t2). Kod bloğu ve
    satır-içi kod içindekiler import sayılmaz (harness da saymaz).
    """
    import re as _re
    try:
        metin = claude_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    kok = os.path.realpath(PROJ)
    out, fence = [], False
    for satir in metin.splitlines():
        if satir.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        temiz = _re.sub(r"`[^`]*`", "", satir)
        for m in _re.finditer(r"(?<![\w@`])@([~\w.][^\s`)\]]*)", temiz):
            tok = m.group(1).rstrip(".,;:")
            if "/" not in tok and not tok.endswith(".md"):
                continue
            hedef = Path(os.path.expanduser(tok)) if tok.startswith("~") else PROJ / tok
            gercek = os.path.realpath(hedef)
            if not os.path.exists(gercek) or \
                    os.path.normcase(os.path.commonpath([kok, gercek])) != os.path.normcase(kok):
                out.append(tok)
    return out


def _on_kosul(ov, tazelenen: bool) -> str:
    """① ÖN KOŞUL — bu oturumun yüklenebilmesi için diskte olması gerekenler (yüklendi DEMEZ)."""
    rd = PROJ / ".claude" / "rules"
    adi = getattr(ov, "CORE_KOPYA_ADI", "00-claude-core.md") if ov else "00-claude-core.md"
    parca, eksik, onarim = [], False, False
    if not rd.exists():
        parca.append(".claude/rules YOK"); eksik = onarim = True
    # Q288: tek tanım `claude_overlay._junction_mu` (yazım-bağımsız + köke kadar ata korumalı).
    # Eski satır `realpath != abspath` idi: küçük harfli CLAUDE_PROJECT_DIR'de gerçek kopyayı
    # "JUNCTION" gösteriyordu. `ov` bu fonksiyona yalnız yüklenebildiyse gelir (_yukleme_satiri).
    elif ov._junction_mu(rd, PROJ):
        parca.append(".claude/rules JUNCTION (harness dış import sayar → YÜKLENMEZ)")
        eksik = onarim = True
    elif not (rd / adi).is_file():
        parca.append(f"{adi} YOK"); eksik = onarim = True
    else:
        parca.append(f"kopya VAR ({adi})")
        try:
            bayat = ov.tazeleme_gerekli(PROJ, CORE, "rules")
            if bayat:
                parca.append(f"BAYAT ({len(bayat)} dosya)"); eksik = True
            else:
                parca.append("taze")
        except Exception as e:  # noqa: BLE001
            parca.append(f"tazelik {_OLCULEMEDI} ({type(e).__name__})"); eksik = True
        if tazelenen:
            parca.append("bu açılışta tazelendi → kesin etkisi SONRAKİ oturum")
        try:
            red = ov.reddedilen_overridelar(PROJ, "rules")
            if red:
                parca.append(f"claude-local override YOK SAYILDI {red}")
        except Exception:
            pass
    dis = _dis_importlar(PROJ / "CLAUDE.md")
    if dis:
        parca.append(f"CLAUDE.md dış @import {len(dis)} ({dis[0]}) → onaysız yüklenmez")
        eksik = True
    else:
        parca.append("dış @import 0")
    satir = f"ÖN KOŞUL: {'EKSİK' if eksik else 'TAMAM'} — " + " · ".join(parca)
    if onarim:
        satir += " → onarım: python core/scripts/team_setup.py --repair-junctions"
    return satir


def _oturum_olcumu(bu_sid, compact: bool) -> str:
    """② Log'un `sid=` kolonundan ÖLÇÜLMÜŞ core yükleme değeri.

    startup/resume/clear/fork → `ÖNCEKİ OTURUM <sid8>`: bu sid DIŞINDAKİ en son sid (ekleme sırası).
    compact → `BU OTURUMUN AÇILIŞI <sid8>`: compact YENİ oturum değildir; aynı sid'in
      `session_start` satırları log'da ZATEN vardır. Bu sid'in açılış satırı yoksa ÖLÇÜLEMEDİ —
      önceki oturuma DÜŞÜLMEZ (başka oturumun değeri bu oturumunmuş gibi okunurdu).
    """
    etiket = "BU OTURUMUN AÇILIŞI" if compact else "ÖNCEKİ OTURUM"
    if compact and not bu_sid:
        return f"{etiket}: {_OLCULEMEDI} (girdide session_id yok)"
    log = PROJ / ".tmp" / "instructions-loaded.log"
    if not log.is_file():
        return f"{etiket}: {_OLCULEMEDI} (log yok)"
    try:
        satirlar = log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        return f"{etiket}: {_OLCULEMEDI} (log okunamadı: {type(e).__name__})"
    son, kayit = None, {}
    for ham in satirlar:
        p = ham.rstrip("\r").split("\t")
        if len(p) < 4:
            continue
        sid = next((x[4:] for x in p[4:] if x.startswith("sid=")), None)
        if not sid:
            continue
        if compact:
            if sid != bu_sid or p[1] != "session_start":
                continue
        elif sid == bu_sid:
            continue
        k = kayit.setdefault(sid, {"core": False})
        k["ts"] = p[0]
        if p[3].replace("\\", "/").rsplit("/", 1)[-1] in _CORE_ADLARI:
            k["core"] = True
        son = sid
    if son is None:
        neden = ("bu sid'in session_start satırı yok — logger sid kolonu öncesi açılmış olabilir"
                 if compact else
                 "bu oturum dışında sid'li log satırı yok — logger sid kolonu öncesi ya da ilk oturum")
        return f"{etiket}: {_OLCULEMEDI} ({neden})"
    k = kayit[son]
    zaman = "açılış satırı" if compact else "son satır"
    ek = "" if compact else "; bu oturum DEĞİL"
    return (f"{etiket} {son[:8]} ({zaman} {k['ts']}{ek}): "
            f"core={'YÜKLENDİ' if k['core'] else 'YÜKLENMEDİ'}")


def _yukleme_satiri(data: dict, tazelenen: bool, compact: bool = False) -> str:
    """Tek satır, iki parça: `ÖN KOŞUL: …  |  ÖNCEKİ OTURUM …` (compact'ta `BU OTURUMUN AÇILIŞI …`).
    Hiçbir koşulda bloklamaz."""
    try:
        try:
            sys.path.insert(0, str(CORE / "scripts"))
            from utils import claude_overlay as ov  # type: ignore
        except Exception:
            ov = None
        on = _on_kosul(ov, tazelenen) if ov is not None else \
            f"ÖN KOŞUL: {_OLCULEMEDI} (claude_overlay yüklenemedi — core junction kopuk?)"
        sid = data.get("session_id") if isinstance(data, dict) else None
        return on + "  |  " + _oturum_olcumu(sid, compact)
    except Exception as e:  # noqa: BLE001
        return f"YÜKLEME {_OLCULEMEDI}: {type(e).__name__}: {e}"


# ⭐ TEK KAYNAK (2026-09-09, kayıt Q212): D7'nin "sapma" TANIMI artık
# `scripts/utils/drift_imzasi.py`de yaşar — kardeş kapı `scripts/ix_doctor.py` 4a kolu AYNI
# tanımı oradan okur. Kopya bırakılsaydı ikisi ayrışırdı ve bu turun teşhisi tam olarak buydu:
# aynı dosya için burası "sapma YOK" (33522a6e2f10dcc5 == 33522a6e2f10dcc5), `ix_doctor` ham
# sha ile "SAPMIŞ" diyordu; fark yalnız `_comment*` anahtarlarıydı (davranış taşımaz).
# Import `__file__`ten türetilir → `hook_shim`in `runpy` çağrısında da çözülür (sys.path[0]
# boş olduğu için DÜZ kardeş-import ölürdü; `utils.inject_paths` aynı deseni üretimde koşar).
# ⛔ BAŞARISIZLIK SESSİZ DEĞİL: modül okunamazsa D7 "sapma yok" DEMEZ — `_drift_kontrol`
# ÖLÇÜLEMEDİ satırı basar. "Ölçemedim" ile "temiz" aynı değere çökerse kapı ölmüş olur.
_IMZA_KAYNAGI = "utils.drift_imzasi"
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # core/scripts
    from utils.drift_imzasi import (  # type: ignore  # noqa: E402
        anlamli_imza as _anlamli_imza, OKUNAMADI as _OKUNAMADI)
except Exception as _imza_hatasi:                                  # pragma: no cover
    _IMZA_KAYNAGI = f"YOK ({type(_imza_hatasi).__name__})"
    _anlamli_imza = None                                           # type: ignore
    _OKUNAMADI = "?"


def _drift_kontrol() -> list[str]:
    """D7: settings.json + hook_shim template'lerin gerisinde mi (davranışsal imza)."""
    sorun = []
    if _anlamli_imza is None:
        return [f"D7 OLCULEMEDI — imza modulu yuklenemedi ({_IMZA_KAYNAGI}): settings.json + "
                "hook_shim template-sapmasi BU OTURUMDA OLCULMEDI (TEMIZ demek DEGIL). "
                "Onarim: python core/scripts/team_setup.py --repair-junctions"]
    ciftler = [
        (PROJ / ".claude" / "settings.json", CORE / "claude" / "settings.template.json", "settings.json"),
        (PROJ / "scripts" / "hook_shim.py", CORE / "claude" / "hook_shim.template.py", "hook_shim.py"),
    ]
    for yerel, tpl, ad in ciftler:
        if not yerel.exists():
            sorun.append(f"{ad} YOK — team_setup ile uret")
            continue
        if not tpl.exists():
            continue
        y, t = _anlamli_imza(yerel), _anlamli_imza(tpl)
        if _OKUNAMADI in (y, t):
            sorun.append(f"{ad} OKUNAMADI/BOZUK — imza cikarilamadi (sessiz gecme)")
        elif y != t:
            sorun.append(f"{ad} template'ten SAPMIS (D7) — bilinçliyse manifest'e isle; degilse: "
                         f"template'ten yenile (fark: core/claude/{tpl.name} ile diff'le)")
    return sorun


def _yasaklar_kontrol() -> list[str]:
    """KESİN YASAKLAR fiziksel damgası kök CLAUDE.md'de var + kanonikle eş mi?
    (Damga junction'dan bağımsız güvence; bu kontrol junction sağlamken eşliği doğrular.)"""
    if not (PROJ / "project.yaml").exists() or not (PROJ / "CLAUDE.md").exists():
        return []
    try:
        sys.path.insert(0, str(PROJ / "core" / "scripts"))
        from utils import yasaklar_stamp  # type: ignore
        core = PROJ / "core"
        if not yasaklar_stamp.canonical_path(core).exists():
            return []
        ok, mesaj = yasaklar_stamp.check((PROJ / "CLAUDE.md").read_text(encoding="utf-8"), core)
        return [] if ok else [mesaj]
    except Exception as e:
        return [f"yasaklar-damga kontrolu calismadi: {e}"]


def _manifest_kontrol() -> list[str]:
    """F2: behavior-manifest diff (core'daki modülü yükle)."""
    try:
        sys.path.insert(0, str(CORE / "scripts"))
        import behavior_manifest  # type: ignore
        return behavior_manifest.verify_quiet(PROJ)
    except Exception as e:
        return [f"manifest kontrolu calismadi: {e}"]


def _origin_kontrol() -> list[str]:
    """Ö3+D20b: DEV_CORE origin-geride mi. THROTTLE: saatte 1 fetch (cache .tmp/),
    fetch timeout 2 sn; aradaki oturumlar cache'lenmiş sonucu gösterir."""
    out = []
    core_git = CORE / ".git"
    if not core_git.exists():
        return []
    # D20b: detached@stable sakin bilgi
    try:
        r = subprocess.run(["git", "-C", str(CORE), "symbolic-ref", "-q", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            out.append("core DETACHED HEAD'de (muhtemelen stable-rollback) — normal is icin: "
                       "git -C core switch main  (D20b; bu bir hata degil)")
            return out
    except Exception:
        pass
    cache = PROJ / ".tmp" / ".core_fetch_cache.json"
    simdi = time.time()
    durum = {}
    try:
        durum = json.loads(cache.read_text(encoding="utf-8"))
    except Exception:
        pass
    if simdi - float(durum.get("ts", 0)) > 3600:  # saatte 1
        try:
            subprocess.run(["git", "-C", str(CORE), "fetch", "--quiet", "origin", "main"],
                           capture_output=True, timeout=2)
        except Exception:
            pass  # ağ yok/yavaş → sessiz; cache'e yine de zaman yaz
        try:
            r = subprocess.run(["git", "-C", str(CORE), "rev-list", "--count", "HEAD..origin/main"],
                               capture_output=True, text=True, timeout=5)
            durum = {"ts": simdi, "behind": int((r.stdout or "0").strip() or 0)}
        except Exception:
            durum = {"ts": simdi, "behind": 0}
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(durum), encoding="utf-8")
        except Exception:
            pass
    behind = int(durum.get("behind", 0))
    if behind > 0:
        out.append(f"DEV_CORE origin'in {behind} commit GERISINDE — `git -C core pull` onerilir")
    return out


def _inspector() -> list[str]:
    """Inspector v1 (rapor-only): davranış katmanı GERÇEKTEN canlı mı?

    ⚠ Bu çağrı oturum açılışını ASLA bozamaz. Inspector çöker/yavaşlarsa sessizce atlanır —
    bir denetim aracı, denetlediği sistemi düşüremez. Geçerse tamamen SESSİZDİR
    (yanlış-pozitif üreten uyarı, uyarıya karşı bağışıklık yaratır — D7 dersi).
    """
    try:
        import importlib.util
        yol = CORE / "scripts" / "inspector.py"
        if not yol.is_file():
            return []
        spec = importlib.util.spec_from_file_location("_inspector", yol)
        if spec is None or spec.loader is None:
            return []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        bulgular, istat = mod.denetle(PROJ, CORE)
        if not bulgular:
            return []
        mod.rapor_yaz(PROJ, bulgular, istat)  # "detay şurada" dediğimiz dosya GERÇEKTEN yazılsın
        satirlar = [str(b).replace("\n", " ") for b in bulgular[:5]]
        if len(bulgular) > 5:
            satirlar.append(f"… +{len(bulgular) - 5} bulgu daha")
        satirlar.append(f"(negatif-testli gate: {istat['negatif_testli_gate']}/{istat['gate_toplam']})")
        satirlar.append("detay: .tmp/inspector-report.md · elle: python core/scripts/inspector.py")
        return satirlar
    except Exception:
        return []


def _git_capa() -> str:
    """Compact sonrasi DETERMINISTIK durum capasi — GIT'ten turetilir, STATE dosyasindan DEGIL.

    ⛔ NEDEN `active_package` DEGIL (olculdu 2026-08-29): bir musteri projesinde
    `.claude/active_package` BIR paketi gosterirken fiilen calisilan is BASKA bir
    paketteydi; `pre_compact` hatirlatmasi (`_active_pkg()`: once state dosyasi, sonra
    `project.yaml` fallback) bu yuzden YANLIS SESSION_NOTES'a yonlendirdi. Ayni sinif
    drift IKI kez tekrarladi. State dosyasina yaslanan bir capa o drift'i compact
    SONRASINA tasir — yani ozetin kaybettigi yerde YANLIS bilgiyle doldurur. Git durumu
    ozetleyiciden bagimsizdir, elle guncelleme istemez ve otoritedir.

    ⛔ FAIL-SAFE: git yok / repo degil / komut patladi -> BOS dize. Capa satiri SESSIZCE
    duser, hook exit 0 dondurmeye devam eder. Bu hook birden fazla projede kosuyor ve
    git'siz bir kokte cokecek bir capa, capanin kendisinden pahaliya mal olur.
    """
    def _git(*args: str) -> str | None:
        try:
            r = subprocess.run(["git", "-C", str(PROJ), *args], capture_output=True,
                               text=True, timeout=5, encoding="utf-8", errors="replace")
            return (r.stdout or "").strip() if r.returncode == 0 else None
        except Exception:
            return None

    dal = _git("rev-parse", "--abbrev-ref", "HEAD")
    son = _git("log", "-1", "--format=%h %s")
    durum = _git("status", "--short")
    if dal is None and son is None and durum is None:
        return ""                                  # git yok/repo degil -> capa YOK
    parcalar = []
    if dal:
        parcalar.append(f"dal: {dal}")
    if son:
        parcalar.append(f"son commit: {son[:72]}")
    if durum is not None:
        satirlar = [s for s in durum.splitlines() if s.strip()]
        if not satirlar:
            parcalar.append("calisma agaci TEMIZ")
        else:
            yeni = sum(1 for s in satirlar if s.startswith("??"))
            # Ilk 5 yol: "neyin ortasindayim" sorusunu ozetten BAGIMSIZ yanitlar.
            ilk = ", ".join(s[3:][:60] for s in satirlar[:5])
            parcalar.append(f"degisiklik: {len(satirlar) - yeni} degismis + {yeni} yeni"
                            f" (ilk {min(5, len(satirlar))}: {ilk}"
                            f"{' …' if len(satirlar) > 5 else ''})")
    return ("\n\n[DURUM CAPASI — git'ten turetildi, state dosyasindan DEGIL]\n"
            + "\n".join(parcalar))


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Bu hook bos sozlukle DEVAM eder ama seans MARKER'i session_id'siz yazilir —
    tazelik/seans zincirine (pull_before_edit, intake_triage) sessizce yansir.
    Gerekce + sinif kaydi: scripts/hooks/README.md S4. Not STDERR'e gider: bu hook'un
    STDOUT'u harness tarafindan JSON olarak PARSE edilir, kirletilemez.
    """
    try:
        sys.stderr.write(
            "[session_start] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> BOS girdiyle "
            "devam (degrade, exit 0); seans marker'i session_id'siz. "
            "Negatif-test: governance/infra-test-recipes.md B0b\n")
    except Exception:
        pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
        data = {}
    _write_session_marker(data if isinstance(data, dict) else {})

    # SessionStart girdisindeki `source`: startup | resume | clear | compact | fork.
    # ⛔ FAIL-SAFE YON = BUGUNKU DAVRANIS: alan yoksa, sozluk degilse ya da deger
    # taninmiyorsa `STATIK` (startup yolu) AYNEN kosar. Yeni dal YALNIZ `compact`ta acilir.
    # KAPSAM bilincli olarak DAR: `resume`/`clear`/`fork` de "yeni oturum" olmayabilir ama
    # olculmedi -> ayri karar (bu turda DEGISTIRILMEDI).
    kaynak = data.get("source") if isinstance(data, dict) else None
    compact = (kaynak == "compact")

    # Tazeleme ÖNCE koşar (docstring'deki sıra gerekçesi), sonucu HER dalda görünür:
    # ⛔ junction dalı bile bu satırları bastırmamalı — yapılan bir değişikliği gizlemek,
    # değişikliğin kendisinden daha pahalıdır.
    saglik: list[str] = ["✓ " + s for s in _overlay_oto_tazele()]
    junctions = _junction_kontrol()
    if junctions:
        saglik += ["⛔ " + s for s in junctions]
        saglik.append("⛔ JUNCTION SORUNU VARKEN SAP-YAZMA YAPMA (guardrail eksik olabilir).")
    else:
        for s in _yasaklar_kontrol():
            saglik.append("⛔ KESİN YASAKLAR DAMGASI: " + s)
        for s in _drift_kontrol():
            saglik.append("⚠ " + s)
        for s in _manifest_kontrol():
            saglik.append("⛔ DAVRANIS-YUZEYI (F2): " + s)
        for s in _origin_kontrol():
            saglik.append("⚠ " + s)
        for s in _inspector():
            saglik.append("⚠ INSPECTOR: " + s)
    # ⛔ SAGLIK KONTROLLERI COMPACT DALINDA DA KOSAR (karar, 2026-08-29). Gerekce:
    #   (1) Temizken bu kontroller ZATEN SESSIZDIR (`_inspector` docstring'i bunu sozlesme
    #       sayar) -> temiz oturumda token maliyeti SIFIRA yakin; "maliyet" argumani
    #       varsayilan halde ODENMIYOR.
    #   (2) Compact tipik olarak oturumun SAATLERCE icindedir — junction/damga/manifest
    #       sinyalleri tam da o aralikta degisir (ornegin oturum ortasinda CLAUDE.md ya da
    #       bir davranis dosyasi duzenlenir). Compact'ta susmak, oturum-ortasi bir infra
    #       degisikligini oturumun GERI KALANI boyunca gizlemek olurdu.
    #   (3) `main()`in ust yorumundaki ilke aynen gecerli: "yapilan bir degisikligi
    #       gizlemek, degisikligin kendisinden daha pahalidir". Bastirmak o ilkeyi
    #       delerdi ve bir GEVSETME olurdu; bu turda kaybedilen kapsam YOK.
    govde = (STATIK_COMPACT + _git_capa()) if compact else STATIK
    # Q286 C2 — BİLİNÇLİ İSTİSNA: "temizken sessiz" sözleşmesinin dışında, HER dalda basılır
    # (Ekran Teyidi bu satırı alıntılar; compact'ta etiket "BU OTURUMUN AÇILIŞI" olur).
    tazelenen = any("overlay tazelendi: rules" in s for s in saglik)
    govde += ("\n\n[YUKLEME — session_start]\n"
              + _yukleme_satiri(data if isinstance(data, dict) else {}, tazelenen, compact))
    if saglik:
        govde += "\n\n[SAGLIK KONTROLLERI — session_start]\n" + "\n".join(saglik)
        if any(x.startswith("⛔ DAVRANIS") for x in saglik):
            govde += ("\nKURAL: manifest-onaysiz davranis dosyasi varken bu oturumun "
                      "ciktisina GUVENME — lider'e bildir; gerekirse --safe-mode ile ac.")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": govde}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
