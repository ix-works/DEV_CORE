#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ENFORCES: C-DTEL-CREATE-01  (ADR 0019 coverage binding)
"""check_dtel_creation_labels.py — DTEL YARATMA girdisi (CSV) ADR 0005-D'ye uygun mu?

NEDEN VAR (kayıt #30②, 2026-08-29 — ölçümle gerekçelendirildi):
`run_review.py`'de `dtel_update` görevi VARDI ama `dtel_creation` YOKTU. Ölçüldü:
  · `--task dtel_creation` → argparse exit 2 (gürültülü ret) ⇒ DTEL yaratımı hiç
    review edilemiyordu.
  · Boş bir zincir eklemek exit 2'yi `VERDICT: PASS` + exit 0'a çevirirdi = SIFIR
    kontrollü sahte-yeşil. O yüzden önce GERÇEK kontrol yazıldı, görev SONRA bağlandı.
  · `populate_dataelements.py` bu kontrolleri YAPMIYOR (ölçüldü): yalnız MAX uzunluğa
    bakıyor ve aşarsa `[WARN] ... (will trim)` deyip **sessizce kırpıyor**; label/
    description BOŞLUĞUNU hiç kontrol etmiyor (`r.get('short','')` → '' geçer gider).
  · `check_struct_field_dtel_active.py` DTEL'lerin KULLANIMINI denetler (struct/tabloda
    aktif mi), YARATILIŞINI değil — kapsam örtüşmesi yok.

⛔ AD ÖNERMEZ (ADR 0005-D): bu gate DTEL/domain **adı önermez, üretmez, düzeltmez** —
   ad kullanıcının kararıdır. Yalnızca **var/yok · biçim · doluluk · uzunluk** denetler.
   Bir alan boşsa "şunu yaz" demez; "boş, kullanıcıdan al" der.

DENETLENEN KURALLAR (her biri kaynağından okundu, özetten değil):
  R1 `name` dolu ve Z/Y ile başlıyor            → KESİN YASAKLAR madde A/D
  R2 4 label'ın (short/medium/long/heading) hiçbiri boş değil
                                                 → madde D: "Tüm 4 field label ... TAM yazılır"
  R3 `description` boş değil                     → madde D: "Title/description boş bırakılmaz"
  R4 label uzunlukları ≤ 10/20/40/55             → playbook/adt-domain-dtel.md (TR label max)
                                                   populate SESSİZCE kırpar ⇒ yazımdan ÖNCE dur
  R5 `type_kind=domain` ise `type_name` dolu      → playbook/adt-domain-dtel.md: eksikse
                                                   "domain bağı KAYBOLUR" (HTTP 201 ama bozuk)

Kullanım:
    python scripts/validators/check_dtel_creation_labels.py <dataelements.csv>
    python scripts/validators/check_dtel_creation_labels.py <dizin>   # *dataelement*.csv süpür
    python scripts/validators/check_dtel_creation_labels.py           # proje kökünü süpür

Exit: 0 = temiz/ilgisiz-artefakt · 1 = ihlal (BLOCKER) · 2 = ÖLÇÜLEMEDİ (sessiz yeşil YOK)
"""
import csv
import io
import sys
from pathlib import Path

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts/

# ADR 0020: junction'da __file__ DEV_CORE'a çözülür → kanonik project_root()/source_dir()
try:
    from utils.project_config import project_root, source_dir
except Exception:                                            # pragma: no cover
    project_root = source_dir = None                         # type: ignore[assignment]

# Kanonik prune kümesi — `check_no_rap_commit.py:58`den KOPYALANDI (yeniden icat YOK).
# `worktrees`: paralel infra worktree'leri aynı CSV'yi taşır → mükerrer bulgu + yabancı
# dalın hatasını bu dala yazma riski.
_SKIP_SEGMENTS = {"node_modules", "dist", "tmp", ".tmp", "fixtures", "attic", "worktrees"}

# DTEL CSV'sini TANIYAN sütunlar (populate_dataelements.py'nin okuduğu şema).
_ZORUNLU_SUTUNLAR = {"name", "short", "medium", "long", "heading", "description"}

# playbook/adt-domain-dtel.md — TR label max uzunlukları
_MAX = {"short": 10, "medium": 20, "long": 40, "heading": 55}


def _aday_dosyalar(hedef: Path):
    """DTEL CSV adaylarını topla.

    ⚠ PRUNE, TARAMA KÖKÜNÜN ALTINDA uygulanır — `check_no_rap_commit.py:92-93`ün
    `os.walk` + `dirnames[:]` kalıbı BİREBİR kopyalandı. Tam yolun parçalarına bakan
    bir prune (`any(p in _SKIP_SEGMENTS for p in yol.parts)`) YANLIŞTIR: gate'in KENDİ
    korpusu `tests/fixtures/...` altında yaşadığı için kök segmentine takılır ve gate
    kendi fixture'ını tarayamaz → sessiz [ATLANDI] + exit 0 (ölçüldü, kırmızı-first
    koşumda yakalandı: "bad" korpusu 0 bulgu vermişti).
    """
    import os
    if hedef.is_file():
        return [hedef]
    bulunan = []
    for dirpath, dirnames, filenames in os.walk(hedef):
        dirnames[:] = [d for d in dirnames if d.lower() not in _SKIP_SEGMENTS]
        for fn in filenames:
            if fn.lower().endswith(".csv") and "dataelement" in fn.lower():
                bulunan.append(Path(dirpath) / fn)
    return bulunan


def _satirlari_oku(yol: Path):
    """(basliklar, satirlar) döner. Ayrıştırılamazsa (None, sebep)."""
    try:
        with io.open(yol, encoding="utf-8-sig", newline="") as f:
            okuyucu = csv.DictReader(f)
            basliklar = set(okuyucu.fieldnames or [])
            return basliklar, list(okuyucu)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _dosyayi_denetle(yol: Path, bulgular: list) -> bool:
    """DTEL CSV'si ise denetler. DTEL CSV'si DEĞİLSE False döner (ilgisiz artefakt)."""
    basliklar, satirlar = _satirlari_oku(yol)
    if basliklar is None:
        bulgular.append((str(yol), "-", f"CSV ayrıştırılamadı ({satirlar})"))
        return True
    if not _ZORUNLU_SUTUNLAR.issubset(basliklar):
        return False                                  # DTEL CSV'si değil → ilgisiz

    for i, r in enumerate(satirlar, start=2):         # 1 = başlık satırı
        ad = (r.get("name") or "").strip()
        yer = f"satır {i}"
        if not ad:
            bulgular.append((str(yol), yer, "R1: `name` BOŞ"))
            continue
        yer = f"{ad} (satır {i})"
        if not ad.upper().startswith(("Z", "Y")):
            bulgular.append((str(yol), yer, f"R1: ad Z/Y ile başlamıyor ('{ad}')"))

        for alan in ("short", "medium", "long", "heading"):
            deger = (r.get(alan) or "").strip()
            if not deger:
                # ⛔ Metin ÖNERMİYORUZ — yalnız eksikliği bildiriyoruz (ADR 0005-D).
                bulgular.append((str(yol), yer,
                                 f"R2: '{alan}' label BOŞ — 4 label TAM olmalı "
                                 f"(metni KULLANICI belirler)"))
            elif len(deger) > _MAX[alan]:
                bulgular.append((str(yol), yer,
                                 f"R4: '{alan}' {len(deger)} karakter > {_MAX[alan]} "
                                 f"— populate SESSİZCE kırpar, yazımdan önce düzelt"))

        if not (r.get("description") or "").strip():
            bulgular.append((str(yol), yer, "R3: `description` BOŞ — boş bırakılamaz"))

        if (r.get("type_kind") or "").strip().lower() == "domain" \
                and not (r.get("type_name") or "").strip():
            bulgular.append((str(yol), yer,
                             "R5: type_kind=domain ama `type_name` BOŞ — domain bağı "
                             "KAYBOLUR (HTTP 201 döner ama DTEL bozuk yaratılır)"))
    return True


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg:
        hedef = Path(arg)
        if not hedef.exists():
            print(f"[OLCULEMEDI] Artefakt yok: {hedef}")
            return 2
    else:
        if project_root is None:
            print("[OLCULEMEDI] project_config yüklenemedi ve artefakt verilmedi.")
            return 2
        hedef = Path(source_dir() or project_root())

    adaylar = _aday_dosyalar(hedef)
    if not adaylar:
        print(f"[ATLANDI] DTEL CSV'si bulunamadı ({hedef}) — bu gate'in konusu değil.")
        return 0

    bulgular: list = []
    denetlenen = 0
    for y in adaylar:
        if _dosyayi_denetle(y, bulgular):
            denetlenen += 1

    if denetlenen == 0:
        print(f"[ATLANDI] {len(adaylar)} CSV bakıldı, hiçbiri DTEL şeması taşımıyor "
              f"(sütunlar: {sorted(_ZORUNLU_SUTUNLAR)}).")
        return 0

    if not bulgular:
        print(f"[OK] {denetlenen} DTEL CSV'si ADR 0005-D'ye uygun "
              f"(4 label dolu + açıklama dolu + uzunluklar sınırda + domain bağı tam).")
        return 0

    print(f"[BLOCKER] {len(bulgular)} ihlal / {denetlenen} DTEL CSV'si:")
    for yol, yer, mesaj in bulgular:
        print(f"  - {Path(yol).name} :: {yer} :: {mesaj}")
    print("\n⛔ ADR 0005-D: 4 label TAM ve master_language'de, description boş bırakılamaz.")
    print("   Bu gate METİN ÖNERMEZ — eksik metinleri KULLANICIDAN al, sonra tekrar koş.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
