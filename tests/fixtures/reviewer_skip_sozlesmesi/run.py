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

Koşum:  python tests/fixtures/reviewer_skip_sozlesmesi/run.py   → exit 0 / 1
MUTASYON: run_review'de skipped_* toplamlarını verdict'ten çıkar → V2/V3/V4 FAIL vermeli.
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
sys.path.insert(0, str(KOK / "scripts" / "validators"))
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

shutil.rmtree(PROJE, ignore_errors=True)

gecen = sum(1 for _, ok, _ in SONUC if ok)
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    if not ok:
        print(f"         -> {detay}")
print(f"\n{gecen}/{len(SONUC)} OK")
sys.exit(0 if gecen == len(SONUC) else 1)
