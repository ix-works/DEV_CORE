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
  · Otomatik olay (`<task-notification>` vb.) ve ajan/oturum mesajı (önekle BAŞLAYAN prompt)
    → sıfır çıktı; kardeş hook'larla aynı demetler (`_AUTO_EVENT_*`, K1-kardeş 2026-10-03).
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

OTURUM-İÇİ TEKRAR BASTIRMA (K1, 2026-10-03; kullanıcı onaylı):
  ⭐ NEDEN: oturum belleği yoktu → aynı ders aynı bağlam penceresinde her prompt'ta (ajan
  mesajları dahil) yeniden basılıyordu. Ölçüm (radar, 51 oturum, 2.883 enjeksiyon / 2,04 MB):
  compaction'da sıfırlanarak sayıldığında karakterlerin %41'i aynı pencerede tekrar; tek
  (oturum, ders) çifti 157 kez.
  · KAYIT: `.tmp/recall-shown/<session_id>.json` = {tp_ofs, gosterilen[id]} — anahtar
    PAYLOAD'daki `session_id` (paralel oturumlar `.tmp`'yi paylaşır; `.claude/.current_session`
    son açılan oturumu gösterir, bu yüzden KULLANILMAZ).
  · NE BASTIRILIR: TOP_K BUGÜNKÜ GİBİ seçilir, SONRA bu pencerede gösterilmiş `id`'ler düşer.
    Alt sıradaki ders öne ÇIKARILMAZ (yalnız bastırma; yeni içerik yok). Hepsi düşerse çıktı yok.
  · PENCERE SINIRI = transkriptteki `{"type":"system","subtype":"compact_boundary"}` satırı.
    Ölçüldü (claude -p 2.1.288, N=1): SessionStart(source=compact) ateşlendiği AN sınır satırı
    transkriptte HENÜZ YOK, sonraki UserPromptSubmit anında VAR ⇒ sinyal bu hook'un kendi
    girdisinden (`transcript_path`) okunur, başka hook'a bağımlılık YOK. Tarama yalnız kayıtlı
    ofsetten sonrasını okur. Tırnaksız `"subtype":"compact_boundary"` yalnız YAPISAL JSON'da
    geçer (string içinde tırnak kaçışlıdır); satır ayrıca parse edilip üst düzeyde doğrulanır.
  · FAIL-OPEN (bastırma ancak pencere KANITLANINCA): session_id yok · transkript yolu yok /
    okunamıyor · dosya küçülmüş (ofset > boyut) · taranacak bölge `_TARAMA_TAVANI`nı aşıyor ·
    kayıt bozuk/okunamıyor → BUGÜNKÜ GİBİ basılır ve kayıt yeniden başlatılır. Yazma hatası
    çıktıyı ETKİLEMEZ. GATE DEĞİL.
  · BAYAT KAYIT: yeni oturum dosyası doğarken `_KAYIT_OMRU_SN`'den eski kayıtlar silinir.

Test: tests/fixtures/recall_index_ozetsiz/run.py (T* vektörleri; gerçek hook CLI'si + hook_shim
  eşleniği runpy ortamı) · tests/fixtures/recall_tekrar_bastirma/run.py (K1) · sentetik payload:
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
# K1 — oturum-içi tekrar bastırma (docstring "OTURUM-İÇİ TEKRAR BASTIRMA").
_SINIR = b'"subtype":"compact_boundary"'
_TARAMA_TAVANI = 64 * 1024 * 1024   # iki enjeksiyon arası transkript büyümesi bunu aşarsa pencere
                                    # KANITLANAMAZ sayılır → bastırma yok (fail-open), kayıt yeniden
_KAYIT_OMRU_SN = 7 * 24 * 3600      # resume edilen eski oturum kaydı silinmişse ders BİR kez daha basılır
_SID_RE = re.compile(r"[^A-Za-z0-9_-]")

# K1-kardeş (2026-10-03): otomatik olay + ajan/oturum mesajı süzgeci — intake_triage.py ve
# skill_injector.py ile BİREBİR aynı iki demet (gerekçe + korpus ölçümü intake_triage.py
# `_AUTO_EVENT_ONEKLER` yorumunda). Bu hook'ta ölçülen (proje ana-oturum transkriptleri, 50
# dosya; [JIT-RECALL] eki parentUuid zinciriyle tetikleyen prompta bağlandı, 2.309 bağlanan /
# 613 bağlanamayan): 1.352 enjeksiyon (%59) bu öneklerden biriyle BAŞLAYAN promptlardan
# (1.287'si origin=peer), 359'u (%16) aşağıdaki işaretlerden birini taşıyan promptlardan (hepsi
# origin=task-notification); insan-origin 552 enjeksiyonun HİÇBİRİ bu iki süzgece takılmıyor.
_AUTO_EVENT_MARKERS = (
    "<task-notification>",
    "This is an automated background-task event",
    "[SYSTEM NOTIFICATION - NOT USER INPUT]",
)
_AUTO_EVENT_ONEKLER = (
    "Another Claude session sent a message",
    "<agent-message from=",
)


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


def _sinir_satiri_mi(satir: bytes) -> bool:
    """Aday satır GERÇEK pencere sınırı mı (üst düzey type=system + subtype=compact_boundary)?
    Parse edilemeyen aday (yarım yazılmış son satır) sınır SAYILIR: güvenli yön = yeniden bas."""
    try:
        d = json.loads(satir.decode("utf-8", "replace"))
    except Exception:
        return True
    return isinstance(d, dict) and d.get("type") == "system" and d.get("subtype") == "compact_boundary"


def _sinir_tara(tp: str, ofs: int):
    """(sınır_var, yeni_ofs). sınır_var None = pencere KANITLANAMADI (fail-open: bastırma yok)."""
    try:
        p = Path(tp)
        boy = p.stat().st_size
    except Exception:
        return None, 0
    if ofs > boy or boy - ofs > _TARAMA_TAVANI:
        return None, boy
    if boy == ofs:
        return False, boy
    try:
        with p.open("rb") as f:
            f.seek(ofs)
            blok = f.read(boy - ofs)
    except Exception:
        return None, boy
    i = blok.find(_SINIR)
    while i != -1:
        bas = blok.rfind(b"\n", 0, i) + 1
        son = blok.find(b"\n", i)
        son = len(blok) if son == -1 else son
        if _sinir_satiri_mi(blok[bas:son]):
            return True, boy
        i = blok.find(_SINIR, son)
    return False, boy


def _ders_kimligi(k: dict) -> str:
    return str(k.get("id") or (str(k.get("kaynak")) + "|" + str(k.get("baslik"))))


def _bayatlari_sil(dizin: Path) -> None:
    try:
        sinir = time.time() - _KAYIT_OMRU_SN
        for f in dizin.iterdir():
            try:
                if f.is_file() and f.stat().st_mtime < sinir:
                    f.unlink()
            except OSError:
                pass
    except OSError:
        pass


def _tekrar_bastir(proj: Path, data: dict, adaylar: list) -> list:
    """K1: bu bağlam penceresinde ZATEN basılmış dersleri `adaylar`dan (TOP_K) düşürür.
    Pencere kanıtlanamazsa `adaylar` AYNEN döner. HİÇBİR koşulda istisna fırlatmaz."""
    try:
        sid = _SID_RE.sub("", str(data.get("session_id") or ""))[:80]
        tp = data.get("transcript_path")
        if not sid or not isinstance(tp, str) or not tp:
            return adaylar                      # oturum/pencere kimliği yok → bugünkü davranış
        dizin = proj / ".tmp" / "recall-shown"
        yol = dizin / (sid + ".json")
        yeni_dosya = not yol.exists()
        gosterilen: set = set()
        try:
            kayit = json.loads(yol.read_text(encoding="utf-8"))
        except Exception:
            kayit = None
        if (isinstance(kayit, dict) and kayit.get("tp") == tp
                and isinstance(kayit.get("tp_ofs"), int) and isinstance(kayit.get("gosterilen"), list)):
            sinir, ofs = _sinir_tara(tp, kayit["tp_ofs"])
            if sinir is False:
                gosterilen = {str(x) for x in kayit["gosterilen"]}
        else:                                   # yeni pencere: yalnız ofset çapası (stat, okuma YOK)
            try:
                ofs = Path(tp).stat().st_size   # ilk prompt'ta transkript henüz YOK (ölçüldü) → 0
            except OSError:
                ofs = 0
        basilacak = [x for x in adaylar if _ders_kimligi(x[1]) not in gosterilen]
        try:
            dizin.mkdir(parents=True, exist_ok=True)
            if yeni_dosya:
                _bayatlari_sil(dizin)
            gecici = dizin / (sid + ".json.tmp")
            gecici.write_text(json.dumps({
                "tp": tp, "tp_ofs": ofs,
                "gosterilen": sorted(gosterilen | {_ders_kimligi(k) for _s, k in basilacak})},
                ensure_ascii=False), encoding="utf-8")
            os.replace(str(gecici), str(yol))
        except Exception:
            pass                                # yazılamadı → bu çıktı etkilenmez (sonraki prompt yine basar)
        return basilacak
    except Exception:
        return adaylar


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
        return 0
    prompt = str(data.get("prompt") or "")
    if len(prompt) < MIN_PROMPT:
        return 0
    # Otomatik olay / ajan mesajı = kullanıcı turu DEĞİL (kardeşler intake_triage + skill_injector
    # ile AYNI sözleşme; tuple'lar birlikte değişir — K0 vektörü AST ile eşitliği denetler).
    if any(mk in prompt for mk in _AUTO_EVENT_MARKERS):
        return 0
    if prompt.lstrip().startswith(_AUTO_EVENT_ONEKLER):   # ajan/oturum mesajı (Q-ITG-PEER)
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
    secilen = _tekrar_bastir(proj, data if isinstance(data, dict) else {}, skorlu[:TOP_K])
    if not secilen:
        return 0                                # hepsi bu pencerede zaten basıldı
    satirlar = [f"· {k['baslik']} — {k['oz'][:90]}  [{k['kaynak']}]"
                for _s, k in secilen]
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
