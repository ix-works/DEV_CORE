#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fixture — `session_start` COMPACT dalı (2026-08-29).

**Sınıf:** SessionStart hook'u girdideki `source` alanını (startup|resume|clear|compact|fork)
hiç okumuyordu ⇒ compact sonrasında da *"Yeni oturumun ILK yaniti ... Ekran Teyidi"* satırını
enjekte ediyordu. Aynı anda harness'ın compact-sonrası talimatı bunun TERSİNİ söyler
(*"özeti anma, kaldığın yerden devam et"*). Ölçüldü (tek oturum, 2026-08-29): **4 compact**
⇒ çelişkili talimat 4 kez enjekte edildi. Lider harness'ı tercih etti; bu bir TERCİHTİ.

**Fix:** `source == "compact"` dalı. Ekran-Teyidi satırı düşer; yerine GİT'ten türetilmiş
deterministik bir DURUM ÇAPASI gelir.

⛔ **Çapa neden git'ten (state dosyasından DEĞİL):** `.claude/active_package` sessizce
bayatlar — ölçülmüş vaka: state dosyası bir paketi, fiilen çalışılan iş başka bir paketi
gösteriyordu ve `pre_compact` bu yüzden yanlış SESSION_NOTES'a yönlendirdi. State'e yaslanan
çapa, özetin kaybettiği yeri YANLIŞ bilgiyle doldurur. **V7/V8 bu ayrımı çivilliyor.**

**Bu korpus neyi çivilliyor:**
  (a) compact dalında çelişkili satır YOK + çapa VAR                       → V1, V2
  (b) FP ÇAPASI: startup çıktısı fix'ten ÖNCEKİ ile BAYT-EŞ                → V3, V4
  (c) `source` YOK / tanınmıyor / girdi bozuk → fail-safe = BUGÜNKÜ yol    → V5, V6
  (d) çapa GİT'ten türetilir, `active_package`'tan DEĞİL                   → V7, V8
  (e) 3. BAĞLAM: git'siz kök + commit'siz repo → çapa DÜŞER, exit 0        → V9, V10
  (f) compact dalı SAĞLIK KONTROLLERİNİ bastırmaz (bilinçli karar)         → V11
  (g) stdout JSON sözleşmesi kirlenmez + kapsam DAR (resume değişmedi)     → V12, V13
  (h) düşürülmeyen YÜKÜMLÜLÜKLER compact gövdesinde duruyor                → V14

⚠ **Çapa metni ham stdout'ta DEĞİL, JSON'dan ÇÖZÜLEREK aranır.** Hook `json.dumps`
varsayılanıyla basar (`ensure_ascii=True`) ⇒ ham stdout'ta Türkçe karakter `\\uXXXX` olarak
durur; ham metinde arama sahte-KIRMIZI verir.

Koşum:  python tests/fixtures/session_start_compact_dali/run.py
MUTASYON — ÜÇ AYRI DEĞİŞMEZ (hiçbiri diğerini kapsamaz; fix üç bağımsız parça getirdi):
  --mutasyon-dalsiz    → `compact` ayrımı sökülür (govde daima `STATIK`)   [dal değişmezi]
  --mutasyon-capasiz   → `_git_capa()` daima "" döner                      [çapa değişmezi]
  --mutasyon-state     → çapa git yerine `.claude/active_package`'tan okur [KAYNAK değişmezi]
Mutasyon git ref'inden DEĞİL BUGÜNKÜ kaynaktan üretilir (taban kayması tuzağı yapısal olarak
yok). Desen bulunamazsa koşucu SAYI RAPORLAMADAN durur — sahte-yeşil yerine görünür duruş.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "scripts" / "hooks" / "session_start.py"

# ⛔ BİLİNMEYEN KİP SESSİZCE YEŞİL GEÇMESİN (negatif_test_harness'tan devralınan sözleşme).
GECERLI_KIP = {"--mutasyon-dalsiz", "--mutasyon-capasiz", "--mutasyon-state"}
for _a in sys.argv[1:]:
    if _a not in GECERLI_KIP:
        print(f"[DURDU] bilinmeyen kip: {_a!r} — gecerli: {sorted(GECERLI_KIP)}")
        sys.exit(2)
KIP = set(sys.argv[1:])

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))
    print(f"  {'[OK]' if kosul else '[FAIL]'} {ad}" + (f"  — {detay}" if not kosul and detay else ""))


# ══════════════════════════════════════════════════════════════════════════════
# MUTASYON — bugünkü kaynaktan üretilir; desen tutmazsa GÖRÜNÜR DURUŞ
# ══════════════════════════════════════════════════════════════════════════════
def _mutasyonlu_kaynak() -> str:
    src = HOOK.read_text(encoding="utf-8")
    if "--mutasyon-dalsiz" in KIP:
        hedef = "govde = (STATIK_COMPACT + _git_capa()) if compact else STATIK"
        if hedef not in src:
            print("[DURDU] --mutasyon-dalsiz deseni BULUNAMADI (fix yeniden mi yazildi?)")
            sys.exit(2)
        src = src.replace(hedef, "govde = STATIK")
    if "--mutasyon-capasiz" in KIP:
        hedef = "def _git_capa() -> str:"
        if hedef not in src:
            print("[DURDU] --mutasyon-capasiz deseni BULUNAMADI")
            sys.exit(2)
        src = src.replace(
            hedef, "def _git_capa() -> str:\n    return ''\n\n\ndef _git_capa_olu() -> str:", 1)
    if "--mutasyon-state" in KIP:
        # KAYNAK değişmezi: çapa git yerine state dosyasından beslenirse V7/V8 düşmeli.
        hedef = '    dal = _git("rev-parse", "--abbrev-ref", "HEAD")'
        if hedef not in src:
            print("[DURDU] --mutasyon-state deseni BULUNAMADI")
            sys.exit(2)
        src = src.replace(hedef, (
            '    try:\n'
            '        dal = (PROJ / ".claude" / "active_package").read_text('
            'encoding="utf-8").strip()\n'
            '    except Exception:\n'
            '        dal = None'), 1)
    return src


def _hook_yolu(tmp: Path) -> Path:
    """Mutasyonlu sürüm İZOLE bir dosyaya yazılır — gerçek kaynağa ASLA dokunulmaz
    (kalıntı birikir ve komşu korpusu kirletir)."""
    if not KIP:
        return HOOK
    p = tmp / "session_start_mutant.py"
    p.write_text(_mutasyonlu_kaynak(), encoding="utf-8", newline="\n")
    return p


def kos(hook: Path, payload, proj: Path) -> tuple[int, str, str]:
    """Hook'u alt-süreçte koşar. payload: dict → JSON; bytes → ham (bozuk girdi vektörü)."""
    govde = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    ortam = dict(os.environ, CLAUDE_PROJECT_DIR=str(proj))
    ortam.pop("IX_OVERLAY_OTO", None)
    r = subprocess.run([sys.executable, str(hook)], input=govde,
                       capture_output=True, cwd=str(proj), env=ortam, timeout=120)
    return (r.returncode,
            (r.stdout or b"").decode("utf-8", "replace"),
            (r.stderr or b"").decode("utf-8", "replace"))


def ctx(stdout: str) -> str:
    """⚠ additionalContext'i JSON'DAN ÇÖZ — ham stdout'ta arama sahte-KIRMIZI verir."""
    try:
        return json.loads(stdout)["hookSpecificOutput"]["additionalContext"]
    except Exception:
        return ""


# ⛔ ÇAPA = TALEBİN KENDİSİ, terim DEĞİL (ilk koşumda ÖLÇÜLDÜ, 2026-08-29).
# İlk yazımda çapa `"Ekran Teyidi"` idi ve V1/V9/V10 KIRMIZI döndü: compact gövdesi o terimi
# ZATEN içeriyor — ama olumsuzlayarak (*"Ekran Teyidi ISTENMIYOR"*). Yani çapa dizesi hem
# kusurlu hem düzeltilmiş sürümde bulunuyordu ⇒ assertion AYIRT EDİCİ DEĞİLDİ (mutasyonda da
# aynı sonucu verirdi). Kaldırılan şey terim değil, OTURUM-BAŞI TALEBİ: `STATIK`in
# *"ZORUNLU: Yeni oturumun ILK yaniti ..."* satırı. Çapa artık o talep.
TALEP = "Yeni oturumun ILK yaniti"
SERBEST_BIRAKMA = "ISTENMIYOR"
CAPA_BASLIK = "DURUM CAPASI"
BAYAT_STATE = "STATE-PAKETI-BAYAT"


def _git(proj: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(proj), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)


def _sahte_proje(kok: Path, git: bool = True, commit: bool = True) -> Path:
    """İzole sahte proje: git deposu + bilinen dal/commit/çalışma-ağacı."""
    kok.mkdir(parents=True, exist_ok=True)
    (kok / ".claude").mkdir(exist_ok=True)
    if not git:
        return kok
    _git(kok, "init", "-q", "-b", "sahte-dal")
    # ⚠ `user.email`e e-posta BİÇİMLİ değer yazma: core'un GENERICIZE-LEAK guard'ı o biçimi
    # kimlik izi sayar ve yazımı REDDEDER (ölçüldü — bu dosyanın ilk iki yazımı reddedildi).
    _git(kok, "config", "user.email", "fixture")
    _git(kok, "config", "user.name", "fixture")
    if commit:
        (kok / "okunur.txt").write_text("taban\n", encoding="utf-8")
        _git(kok, "add", "-A")
        _git(kok, "commit", "-q", "-m", "SAHTE-TABAN-COMMIT")
    return kok


# ══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ss_compact_") as td:
        tmp = Path(td)
        hook = _hook_yolu(tmp)

        # ── A) Ana bağlam: gerçek git deposu olan sahte proje ─────────────────
        proj = _sahte_proje(tmp / "proj")
        (proj / ".claude" / "active_package").write_text(BAYAT_STATE + "\n", encoding="utf-8")
        (proj / "yarim_is.txt").write_text("degisiklik\n", encoding="utf-8")  # untracked

        print("\n-- A) COMPACT DALI --")
        rc_c, so_c, _ = kos(hook, {"session_id": "s1", "source": "compact"}, proj)
        c_compact = ctx(so_c)
        kontrol("V1 compact -> oturum-basi TALEBI ('Yeni oturumun ILK yaniti') YOK",
                TALEP not in c_compact, f"ctx={c_compact[:200]!r}")
        kontrol("V1b compact -> talep ACIKCA serbest birakiliyor (sessiz dusurme degil)",
                SERBEST_BIRAKMA in c_compact, f"ctx={c_compact[:200]!r}")
        kontrol("V2 compact -> git capasi VAR (baslik + dal + commit ozeti)",
                CAPA_BASLIK in c_compact and "sahte-dal" in c_compact
                and "SAHTE-TABAN-COMMIT" in c_compact, f"ctx={c_compact[:400]!r}")

        print("\n-- B) FP CAPASI: bugunku davranis BOZULMADI --")
        rc_s, so_s, _ = kos(hook, {"session_id": "s1", "source": "startup"}, proj)
        c_startup = ctx(so_s)
        # Fix'ten ÖNCEKİ sürümün startup çıktısıyla BAYT-EŞ mi? Taban = HEAD'deki dosya.
        taban_src = subprocess.run(["git", "-C", str(REPO), "show",
                                    "HEAD:scripts/hooks/session_start.py"],
                                   capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", timeout=60)
        if taban_src.returncode == 0 and "STATIK_COMPACT" not in taban_src.stdout:
            taban = tmp / "session_start_taban.py"
            taban.write_text(taban_src.stdout, encoding="utf-8", newline="\n")
            _, so_t, _ = kos(taban, {"session_id": "s1", "source": "startup"}, proj)
            kontrol("V3 FP CAPASI: startup ciktisi fix-ONCESI surumle BAYT-ES",
                    so_s == so_t, f"yeni={len(so_s)}B taban={len(so_t)}B")
        else:
            # ⛔ Fix merge edilince taban kayar; o gün bu vektör OLCULEMEDI der (PASS demez).
            kontrol("V3 FP CAPASI: taban surum cozulemedi -> OLCULEMEDI (PASS DEGIL)",
                    False, "HEAD:scripts/hooks/session_start.py yok ya da fix HEAD'de "
                           "(taban artik SHA'ya pinlenmeli)")

        kontrol("V4 startup -> oturum-basi TALEBI HALA VAR (kapsam kaybi yok)",
                TALEP in c_startup, f"ctx={c_startup[:200]!r}")
        kontrol("V4b startup -> git capasi EKLENMEZ (dal yalniz compact'ta acilir)",
                CAPA_BASLIK not in c_startup)

        print("\n-- C) FAIL-SAFE YON = BUGUNKU DAVRANIS --")
        _, so_yok, _ = kos(hook, {"session_id": "s1"}, proj)          # `source` YOK
        kontrol("V5 `source` alani YOK -> startup ciktisiyla BAYT-ES",
                so_yok == so_s, f"len={len(so_yok)} vs {len(so_s)}")
        _, so_bil, _ = kos(hook, {"session_id": "s1", "source": "ZIRVA"}, proj)
        kontrol("V6 taninmayan `source` -> startup ciktisiyla BAYT-ES (fail-safe)",
                so_bil == so_s, f"len={len(so_bil)} vs {len(so_s)}")
        rc_boz, so_boz, se_boz = kos(hook, b'{"session_id": "s1", "sou', proj)
        kontrol("V6b bozuk girdi -> exit 0 + startup govdesi + parse-fail notu (B0b)",
                rc_boz == 0 and TALEP in ctx(so_boz)
                and "GIRDI-PARSE-EDILEMEDI" in se_boz,
                f"rc={rc_boz} stderr={se_boz[:160]!r}")

        print("\n-- D) CAPANIN KAYNAGI: git <-> state dosyasi --")
        kontrol("V7 capa STATE dosyasindaki (bayat) paket adini TASIMIYOR",
                BAYAT_STATE not in c_compact, f"ctx={c_compact[:400]!r}")
        # Ayırt edici: git durumunu DEĞİŞTİR, state dosyasına DOKUNMA → çapa değişmeli.
        _git(proj, "checkout", "-q", "-b", "ikinci-dal")
        _, so_c2, _ = kos(hook, {"session_id": "s1", "source": "compact"}, proj)
        c2 = ctx(so_c2)
        kontrol("V8 git durumu degisince capa DEGISIR (state dosyasi ayni kaldi)",
                "ikinci-dal" in c2 and "sahte-dal" not in c2, f"ctx={c2[:300]!r}")
        kontrol("V8b calisma agaci ozeti gercek `git status`u yansitir (untracked sayilir)",
                "yeni" in c2 and "yarim_is.txt" in c2, f"ctx={c2[:300]!r}")
        _git(proj, "checkout", "-q", "sahte-dal")

        print("\n-- E) 3. BAGLAM: git'siz / commit'siz kok (gorev-DISI eksen) --")
        gitsiz = _sahte_proje(tmp / "gitsiz", git=False)
        rc_g, so_g, _ = kos(hook, {"session_id": "s1", "source": "compact"}, gitsiz)
        c_g = ctx(so_g)
        kontrol("V9 git'siz kok -> exit 0 + capa SESSIZCE duser + govde saglam",
                rc_g == 0 and CAPA_BASLIK not in c_g and TALEP not in c_g
                and "ADR 0005" in c_g, f"rc={rc_g} ctx={c_g[:200]!r}")
        bos = _sahte_proje(tmp / "bosrepo", git=True, commit=False)   # commit'siz repo
        rc_b, so_b, _ = kos(hook, {"session_id": "s1", "source": "compact"}, bos)
        c_b = ctx(so_b)
        kontrol("V10 commit'siz repo (git log FAIL) -> exit 0, cokme YOK, govde saglam",
                rc_b == 0 and TALEP not in c_b and "ADR 0005" in c_b,
                f"rc={rc_b} ctx={c_b[:200]!r}")

        print("\n-- F) SOZLESMELER --")
        kontrol("V11 compact dali SAGLIK KONTROLLERINI bastirmaz (bilincli karar)",
                ("SAGLIK KONTROLLERI" in c_compact) == ("SAGLIK KONTROLLERI" in c_startup),
                f"compact={'SAGLIK KONTROLLERI' in c_compact} "
                f"startup={'SAGLIK KONTROLLERI' in c_startup}")
        try:
            j = json.loads(so_c)
            sozlesme = (j["hookSpecificOutput"]["hookEventName"] == "SessionStart"
                        and isinstance(j["hookSpecificOutput"]["additionalContext"], str))
        except Exception:
            sozlesme = False
        kontrol("V12 stdout JSON sozlesmesi compact dalinda da GECERLI", sozlesme,
                f"stdout={so_c[:160]!r}")
        _, so_r, _ = kos(hook, {"session_id": "s1", "source": "resume"}, proj)
        kontrol("V13 KAPSAM DAR: `resume` bu turda DEGISMEDI (startup ile bayt-es)",
                so_r == so_s, "resume dali bilincli olarak ACILMADI (ayri karar)")

        # Düşürülmeyen yükümlülükler: satır seçimi bilinçliydi, korpus onu çivilliyor.
        for anahtar, ad in (("ADR 0005", "yasaklar"), ("run_review", "SAP on-kapisi"),
                            ("adt-gateway", "tek SAP yazici"), ("BUG GATE", "bug gate"),
                            ("path=core/", "D29 arama")):
            kontrol(f"V14 compact govdesi '{ad}' yukumlulugunu TASIYOR",
                    anahtar in c_compact, f"ctx={c_compact[:400]!r}")

        # ── Token/bayt deltası (bilgi satırı; hükme esas DEĞİL) ───────────────
        print(f"\n  [bilgi] STATIK govde={len(c_startup)}B · COMPACT govde={len(c_compact)}B "
              f"(delta {len(c_compact) - len(c_startup):+d}B)")

    gecen = sum(1 for _, k, _ in SONUC if k)
    mod = f"  [KIP: {' '.join(sorted(KIP))}]" if KIP else ""
    print(f"\n{gecen}/{len(SONUC)} OK{mod}")
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
