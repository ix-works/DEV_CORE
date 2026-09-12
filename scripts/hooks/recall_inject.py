#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ENFORCES: C-RECALL-01  (ADR 0019 coverage binding)
"""recall_inject.py — U1 JIT-recall enjeksiyonu (radar 2026-08-01; ADOPT-1, kullanıcı onaylı).

OLAY: UserPromptSubmit. NE YAPAR: prompt'u .tmp/recall-index.json'a karşı skorlar;
eşik üstü top-K ders-İNDEKS-SATIRINI additionalContext olarak enjekte eder
("cevap yazılıydı, okunmadı" sınıfına karşı — denetim 2026-07-31'in en pahalı 3 tekrarı).

TASARIM (bilinçli sınırlar):
  · NUDGE-ONLY + FAIL-OPEN: indeks yoksa/bozuksa/zaman aşarsa SESSİZCE exit 0 —
    bir recall-yardımcısı, oturumu asla bozamaz.
  · İNDEKS-SATIRI enjekte edilir, tam metin DEĞİL (progressive disclosure): model
    gerekli görürse kaynağı okur. Enjeksiyon ≤ ~500 karakter hedefi.
  · Kısa/selamlaşma prompt'ları (<40 kar) ve düşük skor (<EŞİK) → sıfır çıktı
    (yanlış-pozitif gürültüsü, uyarıya bağışıklık yaratır — inspector D7 dersi).
  · LLM YOK; skorlama = ağırlıklı token-kesişimi (builder ile aynı katlama).
  · GENEL-TOKEN TAVANI (Q290): indeksin > max(%5·n, 4) kaydında geçen prompt token'ı skora
    katılmaz (`_genel_disi`). ESIK/TOP_K/MIN_PROMPT ve üretecin `anahtar` formülü DEĞİŞMEDİ.
    Ölçüm + reddedilen "en az 2 ayrık token" alternatifi: governance/infra-changelog.md Q290.

OTOMATİK TAZELEME (Q287, 2026-09-12):
  ⭐ NEDEN: indeksi tazeleyen HİÇBİR mekanizma yoktu (üretecin fixture dışı çağıranı 0,
  zamanlanmış görev 0) → bir projenin indeksi 3 hafta bayat kaldı, üç projede HİÇ yoktu;
  hook "indeks yok → exit 0" dalında sessizce kör çalışıyordu.
  · NE ZAMAN: yalnız MIN_PROMPT kapısını geçen prompt'ta (kısa prompt'ta maliyet SIFIR).
  · ÖLÇÜT: indeks YOK ya da mtime'ı `build_recall_index.kaynak_mtime()`'dan eski
    (kaynak listesinin TEK tanımı üreteçtedir; burada kopyası YOK). stat ~1,4 ms.
  · NASIL: AYNI SÜREÇTE senkron `uret()` (ölçüm: medyan 51 ms, max 87 ms / 300 dosya).
    Ayrık arka-plan süreci BİLİNÇLİ SEÇİLMEDİ: Windows konsol penceresi / yetim süreç /
    hook zaman aşımı riskini getirir ve bayat prompt eski indeksle hizmet alırdı.
  · EŞZAMANLILIK: `.tmp/recall-index.lock` (O_CREAT|O_EXCL). Kilit başkasındaysa tazeleme
    ATLANIR ve mevcut indeks (yoksa hiçbir şey) kullanılır. `_KILIT_BAYAT_SN`'den eski kilit
    ölü sayılıp kaldırılır. Kilit alındıktan sonra bayatlık YENİDEN ölçülür (çift kontrol).
    Üretecin yazımı atomiktir (geçici dosya + os.replace) → okuyucu yarım JSON görmez.
  · GÖRÜNÜRLÜK: her deneme `.tmp/recall-index.status`'a yazılır (zaman · tetik · sonuç ·
    sayılar · ms · hata). Hata ayrıca stderr'e (ASCII) düşer. additionalContext'e
    tazeleme hakkında HİÇBİR ŞEY yazılmaz — "ölçemedim" ile "temiz" status'ta ayrışır.

Test: tests/fixtures/recall_index_ozetsiz/run.py (T* vektörleri; gerçek hook CLI'si + hook_shim
  eşleniği runpy ortamı) · sentetik payload:
  echo '{"prompt":"..."}' | python scripts/hook_shim.py recall_inject
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

_TR = str.maketrans("İIıŞşĞğÜüÖöÇç", "iiissgguuoocc")
_STOP = {"ve", "ile", "icin", "bir", "bu", "da", "de", "the", "for", "and",
         "yok", "var", "olan", "her", "gate", "check", "yap", "olarak", "sonra"}
ESIK = 5          # min skor = `anahtar` LİSTESİNDE prompt'a düşen eleman sayısı (tekrarlar ayrı sayılır;
                  # ağırlık üreteçte: başlık ×3 · öz ×1, howto özü ×2 — build_recall_index.py)
TOP_K = 3
MIN_PROMPT = 40   # kısa prompt = selamlaşma/komut; recall gürültü olur
# Q290 — GENEL-TOKEN TAVANI: indeksin > max(GENEL_ORAN·n, GENEL_TABAN) kaydında geçen prompt token'ı
# skorlamaya KATILMAZ (liste elle tutulmaz, her prompt'ta indeksten türetilir). ORAN çünkü indeks boyu
# projeye göre onlarca↔yüzlerce kayıt; TABAN çünkü küçük indekste df=2 "genel" demek değildir.
GENEL_ORAN = 0.05
GENEL_TABAN = 4
_KILIT_BAYAT_SN = 30   # üretim ~50 ms; 30 sn'lik kilit ancak çökmüş bir üreticiden kalır


def _tokenle(s: str) -> set:
    s = s.translate(_TR).lower()
    return {t for t in re.findall(r"[a-z0-9_]{3,}", s) if t not in _STOP}


def _genel_disi(q: set, kayitlar: list) -> set:
    """Q290: indeksin çok kaydında geçen (GENEL) prompt token'larını skorlamadan çıkarır.

    ⭐ NEDEN (ölçüldü 2026-09-12, 80 gerçek prompt, kör etiket): gürültünün kökü "tek token"
    DEĞİL "genel token"dı — `once` (43/336 kayıt) · `degil` (49) · `ayni` (22) · `yeni` (24)
    başlıkta ×3 geçince skoru tek başına 5'e taşıyordu. "En az 2 AYRIK token" alternatifi ÇÜRÜDÜ:
    alakalı satırlı prompt 12→6 (düşürdüğü alakalı satırlar TEK güçlü içerik kelimesiyle geliyordu:
    `deploy`, `bos`, `infra`), tuttuğu gürültü ise genel kelime ÇİFTLERİYDİ (`once`+`yeni`).
    """
    n = len(kayitlar)
    if not n or not q:
        return q
    df = dict.fromkeys(q, 0)
    for k in kayitlar:
        for t in q.intersection(k.get("anahtar", [])):
            df[t] += 1
    tavan = max(GENEL_ORAN * n, GENEL_TABAN)
    return {t for t in q if df[t] <= tavan}


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Gerekce + sinif kaydi: scripts/hooks/README.md S4. ASCII-only + yazma hatasi
    fail-safe'i BOZMAMALI (except: pass).
    """
    try:
        sys.stderr.write(
            "[recall_inject] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> fail-safe "
            "SERBEST (exit 0); KARAR DEGILDIR (girdi hic okunamadi). "
            "Negatif-test: governance/infra-test-recipes.md B0b\n")
    except Exception:
        pass


def _uretec():
    """Üreteci AÇIK YOLLA yükler: hook_shim `runpy` ile çalıştırır → `sys.path[0]` proje
    kökü DEĞİLDİR, `import build_recall_index` bulunamaz. `__file__` ise runpy'de de doğrudur."""
    import importlib.util
    yol = Path(__file__).resolve().parent.parent / "build_recall_index.py"
    spec = importlib.util.spec_from_file_location("_ix_build_recall_index", str(yol))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _durum_yaz(tmp: Path, veri: dict) -> None:
    try:
        veri = {"zaman": time.strftime("%Y-%m-%dT%H:%M:%S"), **veri}
        (tmp / "recall-index.status").write_text(
            json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _kilit_al(kilit: Path):
    """O_EXCL kilit; alınamazsa None. ⚠ Windows'ta silinmekte olan dosyada O_EXCL
    `FileExistsError` DEĞİL `PermissionError` verir → ikisi de `OSError` olarak yakalanır."""
    for deneme in (0, 1):
        try:
            return os.open(str(kilit), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            if deneme:
                return None
            try:
                yas = time.time() - kilit.stat().st_mtime
            except OSError:
                continue            # kilit arada kalktı → bir kez daha dene
            if yas < _KILIT_BAYAT_SN:
                return None         # canlı üretim sürüyor → mevcut indeksle devam
            try:
                kilit.unlink()      # ölü kilit (çökmüş üretici)
            except OSError:
                return None
    return None


def _tazele(proj: Path, idx_p: Path) -> None:
    """Bayat/yok indeksi senkron tazeler. HİÇBİR koşulda istisna fırlatmaz (fail-open)."""
    tmp = idx_p.parent
    tetik = "?"
    try:
        B = _uretec()
        tetik = "YOK"
        if idx_p.is_file():
            if idx_p.stat().st_mtime >= B.kaynak_mtime(proj):
                return              # taze — sık yol, yalnız stat
            tetik = "BAYAT"
        tmp.mkdir(parents=True, exist_ok=True)
        fd = _kilit_al(tmp / "recall-index.lock")
        if fd is None:
            return
        try:
            if idx_p.is_file() and idx_p.stat().st_mtime >= B.kaynak_mtime(proj):
                return              # çift kontrol: kilidi beklerken başkası üretti
            t0 = time.perf_counter()
            bilgi = B.uret(proj)
            bilgi.pop("hedef", None)
            _durum_yaz(tmp, {"tetik": tetik, "sonuc": "OK",
                             "ms": round((time.perf_counter() - t0) * 1000, 1), **bilgi})
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                (tmp / "recall-index.lock").unlink()
            except OSError:
                pass
    except Exception as e:
        hata = f"{type(e).__name__}: {e}"[:300]
        _durum_yaz(tmp, {"tetik": tetik, "sonuc": "HATA", "hata": hata})
        try:
            sys.stderr.write(
                "[recall_inject] RECALL-INDEX-TAZELENEMEDI: " + hata.encode("ascii", "replace").decode()
                + " -> mevcut indeks (varsa) kullanildi; ayrinti .tmp/recall-index.status\n")
        except Exception:
            pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
        return 0
    prompt = str(data.get("prompt") or "")
    if len(prompt) < MIN_PROMPT:
        return 0

    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    idx_p = proj / ".tmp" / "recall-index.json"
    _tazele(proj, idx_p)
    if not idx_p.is_file():
        return 0
    try:
        kayitlar = json.loads(idx_p.read_text(encoding="utf-8")).get("kayit", [])
    except Exception:
        return 0

    q = _genel_disi(_tokenle(prompt), kayitlar)
    if not q:
        return 0
    skorlu = []
    for k in kayitlar:
        sk = sum(1 for a in k.get("anahtar", []) if a in q)
        if sk >= ESIK:
            skorlu.append((sk, k))
    if not skorlu:
        return 0
    skorlu.sort(key=lambda x: -x[0])
    satirlar = [f"· {k['baslik']} — {k['oz'][:90]}  [{k['kaynak']}]"
                for _s, k in skorlu[:TOP_K]]
    ctx = ("[JIT-RECALL] Göreve-ilişkin OLASI dersler (indeks; gerekirse kaynağı oku, "
           "alakasızsa yok say):\n" + "\n".join(satirlar))
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": ctx[:900]}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)  # fail-open: recall yardımcısı oturumu bozamaz
