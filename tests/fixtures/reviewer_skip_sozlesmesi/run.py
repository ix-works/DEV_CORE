# -*- coding: utf-8 -*-
"""reviewer_skip_sozlesmesi — run_review.py SKIP yolunun sözleşmesi (KAYIT S1 + S2).

TEK KÖK, İKİ YÜZ:
  S1 — SKIP kaydı `stdout`/`stderr` anahtarlarını TAŞIMIYORDU → insan-okunur yazıcı
       `KeyError: 'stdout'` ile ÇÖKTÜ → **VERDICT satırı hiç basılmadı** (canlı repro).
  S2 — SKIP verdict'e SAYILMIYORDU → BLOCKER sınıfındaki bir gate'in dosyası yoksa
       VERDICT `PASS` + exit 0 ("✓ devam edebilirsin") → sahte-PASS. Gate'i SİLMEK,
       onu geçmenin en kolay yoluydu.

⚠ İZOLASYON: `run_review` PROJ_ROOT'u İMPORT ANINDA `CLAUDE_PROJECT_DIR`/cwd'den okur.
Bu yüzden env, import'tan ÖNCE sentetik bir proje köküne çevrilir; gerçek repo'nun
`validators-local/` dizini teste sızmaz (bu tuzak conn_cift_anahtar/sir_gate
fixture'larında bizzat yaşandı: "gerçek dosyayı okuyan fixture hiçbir şey ölçmez").

ÜÇÜNCÜ YÜZ (2026-08-29, KAYIT #5③ — IX-GATE-STATUS SÖZLEŞMESİNİN TÜKETİCİ UCU):
  S3 — `check_abaplint` gibi bir gate `exit 0` döndürdüğünde bunun ÜÇ anlamı vardı
       ("ölçtüm temiz" · "config yok" · "obje tipini koşturamıyorum" · "npx yok") ve
       `run_review` üçünü de `PASS` sayıyordu. Üretici uç 2026-08-29'da makinece okunur
       bir satır basmaya başladı (`IX-GATE-STATUS: gate=… measured=<true|false> …`) ama
       TÜKETİCİ uç bağlanmamıştı: sözleşmenin iki ucu birbirine DEĞMİYORDU.
       V10-V17 bu ucu çiviliyor. ⛔ ÇIKIŞ KODU DEĞİŞMEDİ (ne üretici ne tüketici) —
       `measured=false` bir SKIP'tir, WARNING sınıfında verdict WARNING + exit 0 kalır.

Koşum:  python tests/fixtures/reviewer_skip_sozlesmesi/run.py   → exit 0 / 1
MUTASYON — DÖRT AYRI DEĞİŞMEZ (hiçbiri diğerini KAPSAMAZ; dördü de koşulmalı):
ÖLÇÜLDÜ 2026-08-29 (taban 21/21; her kip TAM OLARAK hedeflediği vektörleri düşürür):
  --mutasyon-sozlesme       IX-GATE-STATUS dalı SÖKÜLÜR (`status = PASS if rc==0 else FAIL`)
                            → 17/21: V10, V10b, V13, V15 düşer.
  --mutasyon-kapsam         dal `rc == 0` niteleyicisini KAYBEDER (her rc'de beyan okunur)
                            → 20/21: V16 düşer (rc=1 + measured=false artık SKIP'e kayıyor).
  --mutasyon-gate-adi       beyan seçimi `gate=` eşleşmesini KAYBEDER (hep son satır)
                            → 20/21: V14 düşer (yabancı beyan kendi beyanını eziyor).
  --mutasyon-capa-satirbasi regex `^` satır-başı çapasını KAYBEDER
                            → 20/21: V12a düşer (girintili ÖRNEK satır beyan sanılıyor).
  --mutasyon-capa-token     `(true|false)` TAM eşleşmesi + `== 'false'` karşılaştırması
                            gevşer → 20/21: V12b düşer (`measured=<true|false>` şablonu
                            beyan sanılıyor).
  V1-V9 + V11 + V17 BEŞ kipte de AYAKTA (regresyon çapası: mutasyon yalnız hedefini vurur).
Mutant, kaynağın BUGÜNKÜ hâlinden üretilir (git ref'inden DEĞİL) ve temp'te yaşar:
`run_review.py` kardeş-import TAŞIMAZ (yalnız stdlib) — ölçüldü, o yüzden temp güvenli.
Desen bulunamazsa koşucu SAYI RAPORLAMADAN durur (sahte-yeşil yerine görünür duruş).
"""
from __future__ import annotations

import contextlib
import io
import json
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

KOK = Path(__file__).resolve().parents[3]          # repo kökü (DEV_CORE)
SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, ok: bool, detay: str = "") -> None:
    SONUC.append((ad, ok, detay))


# ── sentetik proje kökü: kendi validators-local'i ile ─────────────────────────────
PROJE = Path(tempfile.mkdtemp(prefix="rw_skip_"))
(PROJE / "scripts" / "validators-local").mkdir(parents=True)
ARTIFACT = PROJE / "sentetik.cds"
ARTIFACT.write_text("define view X as select from t {}\n", encoding="utf-8")

(PROJE / "scripts" / "validators-local" / "check_sentetik_gecer.py").write_text(
    "import sys\nprint('OK — sentetik gate temiz')\nsys.exit(0)\n", encoding="utf-8")
(PROJE / "scripts" / "validators-local" / "check_sentetik_duser.py").write_text(
    "import sys\nprint('IHLAL bulundu', file=sys.stderr)\nsys.exit(1)\n", encoding="utf-8")

os.environ["CLAUDE_PROJECT_DIR"] = str(PROJE)      # ⚠ import'tan ÖNCE

# ── MUTANT ÜRETİMİ (kaynağın BUGÜNKÜ hâlinden) ──────────────────────────────────
_GECERLI_KIP = {"--mutasyon-sozlesme", "--mutasyon-kapsam", "--mutasyon-gate-adi",
                "--mutasyon-capa-satirbasi", "--mutasyon-capa-token"}
for _a in sys.argv[1:]:
    # ⛔ BİLİNMEYEN KİP SESSİZCE YEŞİL GEÇMESİN: `--mutasyon-ZIRVA` eskiden hiç mutasyon
    #    kurmadan TAM PUAN üretirdi (kardeş ders: infra_write_guard / atc_p1_sonuc).
    if _a.startswith("--mutasyon") and _a not in _GECERLI_KIP:
        raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {_a} — geçerli: "
                         + ", ".join(sorted(_GECERLI_KIP)))
_KIP = next((a for a in sys.argv[1:] if a in _GECERLI_KIP), "")

_MUTASYONLAR: dict[str, list[tuple[str, str]]] = {
    # Her kip TEK bir değişmezi söker; değer = uygulanacak (eski, yeni) yamaların LİSTESİ.
    "--mutasyon-sozlesme": [(
        "        beyan = gate_durum_beyani(out, script_name) if rc == 0 else None\n"
        "        if beyan is not None and beyan['measured'] == 'false':",
        "        beyan = None\n"
        "        if False:")],
    "--mutasyon-kapsam": [(
        "        beyan = gate_durum_beyani(out, script_name) if rc == 0 else None\n",
        "        beyan = gate_durum_beyani(out, script_name)\n")],
    "--mutasyon-gate-adi": [(
        "    return (kendi or beyanlar)[-1]\n",
        "    return beyanlar[-1]\n")],
    # ÇAPA-1: satır-başı. Sökülünce, sözleşmeyi TARİF eden GİRİNTİLİ örnek satır
    # (docstring/yardım çıktısı) BEYAN sanılır.
    "--mutasyon-capa-satirbasi": [(
        "    r'^IX-GATE-STATUS:", "    r'IX-GATE-STATUS:")],
    # ÇAPA-2: `true|false` TAM eşleşmesi + `== 'false'` karşılaştırması. Sökülünce
    # şablon metni (`measured=<true|false>`) "ölçülmedi" sayılır.
    "--mutasyon-capa-token": [
        ("r'measured=(?P<measured>true|false)\\s+", "r'measured=(?P<measured>\\S+)\\s+"),
        ("beyan['measured'] == 'false'", "beyan['measured'] != 'true'"),
    ],
}

_KAYNAK_RR = KOK / "scripts" / "validators" / "run_review.py"
if _KIP:
    _metin = _KAYNAK_RR.read_text(encoding="utf-8")
    for _eski, _yeni in _MUTASYONLAR[_KIP]:
        if _metin.count(_eski) != 1:
            print(f"⛔ MUTASYON DESENİ BULUNAMADI/ÇOK EŞLEŞTİ ({_metin.count(_eski)}x) "
                  f"[{_KIP}] {_eski[:48]!r} — SAYI RAPORLANMIYOR "
                  f"(sahte-yeşil yerine görünür duruş).")
            shutil.rmtree(PROJE, ignore_errors=True)
            sys.exit(3)
        _metin = _metin.replace(_eski, _yeni)
    _MUT_DIZIN = Path(tempfile.mkdtemp(prefix="rw_mut_"))
    (_MUT_DIZIN / "run_review.py").write_text(_metin, encoding="utf-8")
    sys.path.insert(0, str(_MUT_DIZIN))
else:
    _MUT_DIZIN = None
    sys.path.insert(0, str(_KAYNAK_RR.parent))
import run_review as R  # noqa: E402


def kos(zincir, json_mod=True, strict=False):
    """TASK_VALIDATORS'ı geçici olarak `zincir` yapıp main()'i koş → (rc, metin/sözlük)."""
    eski = R.TASK_VALIDATORS.get("cds_creation")
    R.TASK_VALIDATORS["cds_creation"] = zincir
    argv = ["run_review.py", "--task", "cds_creation", "--artifact", str(ARTIFACT)]
    if json_mod:
        argv.append("--json")
    if strict:
        argv.append("--strict")
    eski_argv = sys.argv
    sys.argv = argv
    buf, hata = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(hata):
            rc = R.main()
    except Exception as exc:  # noqa: BLE001
        # MUTASYON/regresyon dostu: çökme testi durdurmaz, ÖLÇÜLEN bir sonuç olur
        # (fix-öncesi kod tam burada `KeyError: 'stdout'` ile ölüyor).
        return -1, ({"verdict": f"COKME:{type(exc).__name__}", "results": [],
                     "blocker_count": -1, "warning_count": -1} if json_mod
                    else f"COKME:{type(exc).__name__}: {exc}")
    finally:
        sys.argv = eski_argv
        R.TASK_VALIDATORS["cds_creation"] = eski
    ham = buf.getvalue()
    if not json_mod:
        return rc, ham + hata.getvalue()
    try:
        return rc, json.loads(ham)
    except json.JSONDecodeError:
        return rc, {"verdict": "JSON-BOZUK", "results": [],
                    "blocker_count": -1, "warning_count": -1}


EKSIK_B = ("check_HIC_YOK_BLOCKER.py", "BLOCKER", "sentetik: diskte olmayan BLOCKER gate")
EKSIK_W = ("check_HIC_YOK_WARNING.py", "WARNING", "sentetik: diskte olmayan WARNING gate")
GECER = ("check_sentetik_gecer.py", "BLOCKER", "sentetik: proje-lokal, geçer")
DUSER = ("check_sentetik_duser.py", "BLOCKER", "sentetik: proje-lokal, düşer")

# ── V1 (S1) — insan-okunur mod SKIP'te ÇÖKMEZ ve VERDICT'i BASAR ─────────────────
rc, metin = kos([EKSIK_B], json_mod=False)
kontrol("V1 (S1) SKIP'te KeyError YOK + 'VERDICT:' satırı BASILIYOR",
        "VERDICT:" in metin and "Traceback" not in metin,
        f"rc={rc} çıktı-kuyruğu={metin.strip()[-160:]!r}")
kontrol("V1b (S1) koşmayan gate GÖRÜNÜR ('PRE-FLIGHT KOŞMADI')",
        "PRE-FLIGHT KOŞMADI" in metin, f"çıktı={metin.strip()[:200]!r}")

# ── V2 (S2) — eksik BLOCKER gate → BLOCKER + exit 1 (eskiden PASS + exit 0) ──────
rc, d = kos([EKSIK_B])
kontrol("V2 (S2) eksik BLOCKER gate → verdict BLOCKER + exit 1",
        d["verdict"] == "BLOCKER" and rc == 1,
        f"verdict={d['verdict']} rc={rc} skipped_blocker={d.get('skipped_blocker_count')}")
kontrol("V2b sayaç ayrımı: koşan-FAIL 0, KOŞMAYAN 1",
        d.get("failed_blocker_count") == 0 and d.get("skipped_blocker_count") == 1,
        f"failed={d.get('failed_blocker_count')} skipped={d.get('skipped_blocker_count')}")

# ── V3 (S2) — eksik WARNING gate → WARNING ama exit 0 (bloklamaz) ────────────────
rc, d = kos([EKSIK_W])
kontrol("V3 (S2) eksik WARNING gate → verdict WARNING, exit 0 (bloklamaz)",
        d["verdict"] == "WARNING" and rc == 0,
        f"verdict={d['verdict']} rc={rc}")

# ── V4 — FP ÇAPASI: her şey yerinde ve temiz → PASS + exit 0 (davranış DEĞİŞMEZ) ──
rc, d = kos([GECER])
kontrol("V4 FP ÇAPASI: gate VAR ve geçiyor → PASS + exit 0 (aşırı-sıkılaşma yok)",
        d["verdict"] == "PASS" and rc == 0 and d["results"][0]["status"] == "PASS",
        f"verdict={d['verdict']} rc={rc} status={d['results'][0]['status']}")

# ── V5 — FP ÇAPASI: gerçek ihlal hâlâ BLOCKER (gate'in asıl işi bozulmadı) ───────
rc, d = kos([DUSER])
kontrol("V5 FP ÇAPASI: gate VAR ve düşüyor → BLOCKER + exit 1 (eskisi gibi)",
        d["verdict"] == "BLOCKER" and rc == 1 and d.get("failed_blocker_count") == 1,
        f"verdict={d['verdict']} rc={rc} failed={d.get('failed_blocker_count')}")

# ── V6 — FP ÇAPASI: BOŞ ZİNCİR bilinçli boşluktur, PASS kalmalı ─────────────────
#   (dtel_update / rap_service_binding: "zincir henüz yok" KAYITLI bir karardır;
#    kayıtsız eksiklik ile karıştırılırsa meşru push'lar bloklanır.)
rc, d = kos([])
kontrol("V6 FP ÇAPASI: BOŞ zincir (bilinçli boşluk) → PASS + exit 0",
        d["verdict"] == "PASS" and rc == 0, f"verdict={d['verdict']} rc={rc}")

# ── V7 — GEÇMİŞ-ETKİ ÇAPASI (2026-07-10 fix'i): proje-lokal validator BULUNUR ────
#   O fix, yalnız core'a bakıp proje-lokal validator'ı DAİMA SKIP'e düşürmeyi kapatmıştı.
#   Artık SKIP verdict'e sayıldığı için o regresyon geri gelirse gürültü değil BLOCKER
#   üretir → bu çapa onun hâlâ çalıştığını kanıtlar.
rc, d = kos([GECER])
kontrol("V7 GEÇMİŞ-ETKİ: proje-lokal validators-local/ keşfi HÂLÂ çalışıyor (SKIP değil)",
        d["results"][0]["status"] != "SKIP", f"status={d['results'][0]['status']}")

# ── V8 — MCP sözleşmesi: --json çıktısı ayrıştırılabilir + anahtarlar tam ────────
#   `mcp _reviewer.run_reviewer` json.loads eder ve verdict/blocker_count/results okur.
rc, d = kos([EKSIK_B, GECER])
gerekli = {"verdict", "blocker_count", "warning_count", "results",
           "skipped_blocker_count", "failed_blocker_count"}
kontrol("V8 MCP sözleşmesi: --json tam anahtar kümesi + SKIP kaydında stdout/stderr var",
        gerekli <= set(d) and all({"stdout", "stderr", "message"} <= set(r) for r in d["results"]),
        f"eksik_ust={gerekli - set(d)} kayit_anahtarlari={sorted(d['results'][0])}")

# ── V9 — 3. BAĞLAM (görev-dışı): --strict yolu SKIP'i de yükseltiyor mu ─────────
rc, d = kos([EKSIK_W], strict=True)
kontrol("V9 3.BAĞLAM: --strict + eksik WARNING → BLOCKER (strict sözleşmesi korunur)",
        d["verdict"] == "BLOCKER" and rc == 1, f"verdict={d['verdict']} rc={rc}")

# ═══════════════════════════════════════════════════════════════════════════════
# S3 — IX-GATE-STATUS SÖZLEŞMESİNİN TÜKETİCİ UCU (kayıt #5③, 2026-08-29)
# ═══════════════════════════════════════════════════════════════════════════════
# Stub'lar `validators-local/` altında yaşar → run_review'in GERÇEK keşif+koşum yolu
# kullanılır (monkeypatch YOK: "kod ≠ kablolama"). Her stub `exit 0` döner; ayrımı
# YALNIZ bastığı IX-GATE-STATUS satırı yapar — düzeltilen sınıf tam olarak budur.
_VL = PROJE / "scripts" / "validators-local"
_SATIR = "IX-GATE-STATUS: gate={g} status={s} measured={m} reason={r}"


def _stub(ad: str, govde: str, cikis: int = 0) -> None:
    """⛔ STUB GÖVDESİ ASCII-ONLY (C-ENC-01). Ölçüldü 2026-08-29: alt süreç stdout'u
    Windows'ta cp1252'dir; `ı/İ/ş/ğ` içeren bir `print` UnicodeEncodeError ile
    **exit 1** verir ve vektör "gate düştü" diye okunur — yani stub'ın DİLİ ölçümü
    sessizce tersine çevirir. (Bu tuzak bu korpusta bizzat yaşandı: 5 vektör
    yanlış sebeple kırmızıydı.) Türkçe metin YALNIZ vektör ADLARINDA kullanılır."""
    kod = "import sys\n" + govde + f"\nsys.exit({cikis})\n"
    kod.encode("ascii")                      # yapısal koruma: sapma GÜRÜLTÜLÜ çöker
    (_VL / f"{ad}.py").write_text(kod, encoding="utf-8")


_stub("check_gs_olculmedi",
      "print('SKIP - npx yok; lint OLCULMEDI')\n"
      f"print('{_SATIR.format(g='check_gs_olculmedi', s='SKIPPED', m='false', r='tool-unavailable')}')")
_stub("check_gs_olculdu",
      "print('OK - temiz (0 issue / 1 file(s) analyzed)')\n"
      f"print('{_SATIR.format(g='check_gs_olculdu', s='OK', m='true', r='clean')}')")
_stub("check_gs_yok", "print('OK - eski tarz gate, durum satiri BASMAZ')")
# ÇAPA-1: sözleşmeyi TARİF eden GİRİNTİLİ satır (docstring/yardım çıktısı) BEYAN DEĞİLDİR.
_stub("check_gs_tarif",
      "print('OK - temiz. Sozlesme soyledir:')\n"
      f"print('    {_SATIR.format(g='check_gs_tarif', s='SKIPPED', m='false', r='ornek')}')")
# ÇAPA-2: satır-başında ama ŞABLON değerlerle (`<true|false>`) → yine BEYAN DEĞİLDİR.
_stub("check_gs_sablon",
      "print('OK - temiz. Bicim:')\n"
      f"print('{_SATIR.format(g='check_gs_sablon', s='<OK|FINDING|SKIPPED|FAIL>', m='<true|false>', r='<slug>')}')")
# Kendi beyanı ÖNCE, YABANCI gate'in beyanı SONRA → kendi beyanı kazanmalı.
_stub("check_gs_yabanci",
      f"print('{_SATIR.format(g='check_gs_yabanci', s='OK', m='true', r='clean')}')\n"
      f"print('{_SATIR.format(g='check_baska_gate', s='SKIPPED', m='false', r='tool-unavailable')}')")
# YALNIZ yabancı beyan → yedek dal (son satır) devreye girmeli; dal ÖLÜ bırakılmaz.
_stub("check_gs_yalniz_yabanci",
      f"print('{_SATIR.format(g='check_baska_gate', s='SKIPPED', m='false', r='config-missing')}')")
# rc != 0 + measured=false → FAIL kalmalı (kapsam niteleyicisi: sessiz olan yol exit 0'dır).
_stub("check_gs_rc1",
      "print('FINDING - 2 bulgu')\n"
      f"print('{_SATIR.format(g='check_gs_rc1', s='FAIL', m='false', r='summary-missing')}')", cikis=1)


def _z(ad: str, sev: str = "WARNING"):
    return (f"{ad}.py", sev, f"sentetik: {ad}")


# V10 ⭐ ASIL FIX — exit 0 + measured=false → PASS DEĞİL, SKIP; WARNING sınıfı ⇒ exit 0
rc, d = kos([_z("check_gs_olculmedi")])
r0 = d["results"][0]
kontrol("V10 ⭐ exit 0 + measured=false → status SKIP (PASS DEĞİL) + verdict WARNING + exit 0",
        r0["status"] == "SKIP" and d["verdict"] == "WARNING" and rc == 0
        and d.get("skipped_warning_count") == 1,
        f"status={r0['status']} verdict={d['verdict']} rc={rc} "
        f"skipped_warning={d.get('skipped_warning_count')}")
kontrol("V10b SEBEP GÖRÜNÜR: message reason slug'ını taşıyor ('koşmadı' sessiz kalmaz)",
        "PRE-FLIGHT ÖLÇMEDİ" in r0["message"] and "tool-unavailable" in r0["message"],
        f"message={r0['message'][:120]!r}")

# V11 POZİTİF KONTROL — measured=true → PASS (gate'in asıl işi bozulmadı)
rc, d = kos([_z("check_gs_olculdu")])
kontrol("V11 POZİTİF KONTROL: measured=true → PASS + verdict PASS + exit 0",
        d["results"][0]["status"] == "PASS" and d["verdict"] == "PASS" and rc == 0,
        f"status={d['results'][0]['status']} verdict={d['verdict']} rc={rc}")

# V12a/V12b FP ÇAPALARI — markörü TARİF eden metin BEYAN sayılmaz (iki ayrı çapa)
rc, d = kos([_z("check_gs_tarif")])
kontrol("V12a FP ÇAPASI: GİRİNTİLİ örnek satır beyan DEĞİL → PASS (satır-başı çapası)",
        d["results"][0]["status"] == "PASS" and d["verdict"] == "PASS",
        f"status={d['results'][0]['status']} verdict={d['verdict']}")
rc, d = kos([_z("check_gs_sablon")])
kontrol("V12b FP ÇAPASI: ŞABLON değerli satır (`measured=<true|false>`) beyan DEĞİL → PASS",
        d["results"][0]["status"] == "PASS" and d["verdict"] == "PASS",
        f"status={d['results'][0]['status']} verdict={d['verdict']}")

# V13 ŞİDDET SÖZLEŞMESİ — aynı olay BLOCKER sınıfında verdict'i BLOCKER + exit 1 yapar
rc, d = kos([_z("check_gs_olculmedi", "BLOCKER")])
kontrol("V13 ŞİDDET: measured=false BLOCKER sınıfında → verdict BLOCKER + exit 1",
        d["verdict"] == "BLOCKER" and rc == 1 and d.get("skipped_blocker_count") == 1,
        f"verdict={d['verdict']} rc={rc} skipped_blocker={d.get('skipped_blocker_count')}")

# V14 gate= EŞLEŞMESİ — yabancı gate'in SON satırı kendi beyanını EZMEZ
rc, d = kos([_z("check_gs_yabanci")])
kontrol("V14 yabancı `gate=` beyanı kendi beyanını EZMEZ → PASS",
        d["results"][0]["status"] == "PASS" and d["verdict"] == "PASS",
        f"status={d['results'][0]['status']} verdict={d['verdict']}")

# V15 YEDEK DAL — kendi adıyla beyan YOKSA son beyan okunur (dal ölü bırakılmaz)
rc, d = kos([_z("check_gs_yalniz_yabanci")])
kontrol("V15 yedek dal: kendi adıyla beyan yoksa SON beyan okunur → SKIP",
        d["results"][0]["status"] == "SKIP",
        f"status={d['results'][0]['status']} verdict={d['verdict']}")

# V16 KAPSAM NİTELEYİCİSİ — rc != 0 davranışı BİT-BAZINDA korunur (FAIL, SKIP değil)
rc, d = kos([_z("check_gs_rc1")])
kontrol("V16 KAPSAM: rc=1 + measured=false → FAIL kalır (SKIP'e KAYMAZ)",
        d["results"][0]["status"] == "FAIL" and d.get("failed_warning_count") == 1
        and d.get("skipped_warning_count") == 0,
        f"status={d['results'][0]['status']} failed={d.get('failed_warning_count')} "
        f"skipped={d.get('skipped_warning_count')}")

# V17 GERİYE DÖNÜK UYUM — durum satırı BASMAYAN gate'lerin davranışı DEĞİŞMEZ
rc, d = kos([_z("check_gs_yok")])
kontrol("V17 GERİYE DÖNÜK UYUM: IX-GATE-STATUS satırı YOK → PASS (bugünkü davranış)",
        d["results"][0]["status"] == "PASS" and d["verdict"] == "PASS" and rc == 0,
        f"status={d['results'][0]['status']} verdict={d['verdict']} rc={rc}")

shutil.rmtree(PROJE, ignore_errors=True)
if _MUT_DIZIN is not None:
    shutil.rmtree(_MUT_DIZIN, ignore_errors=True)

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)
