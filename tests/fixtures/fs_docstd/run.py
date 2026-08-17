#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIXTURE — FS doküman-standardı üçlüsü (2026-08-17, infra-expert F1-F5 turu).

KAPSAM (üç artefakt, tek korpus — üçü aynı kuralı üç yüzeyde uygular):
  ① `scripts/validators/check_fs_no_analysis_log.py`  — DOC-FS-05/06 sayacı (warn-first)
  ② `scripts/hooks/post_validate.py` `doc-fs` dalı    — edit-anı OKU-işaretçisi + özet
  ③ `scripts/doc_equivalence_check.py`                — DOC-FS-07 veri-kaybı ölçümü

NİÇİN VAR (ölçülmüş): gate ilk hâlinde 21 FS/EK dokümanının 16'sını "kirli" gösteriyordu ve
işaretlerin 31'i **belgenin kendi kimlik bilgisiydi** — kapak satırı (`| Versiyon | v1.3 |`),
başlıksız §1.1 versiyon tablosu (21 dokümanın 8'inde tablo ayrı başlık OLMADAN duruyor;
tek başına 37 işaret), §1.3 ilgili-doküman satırı, altbilgi ve belgenin KENDİ tanımladığı
`H-1` gap ID'leri. Bunlar temizlenemez ⇒ yeşil ERİŞİLEMEZ ⇒ uyarı duvar kâğıdına döner
("gürültü yapan hook ölü hooktur"). Aynı turda üç sessiz kusur daha kapandı: okunamayan
dosya "temiz" sayılıyordu · komşu-dizin yolu `relative_to` ile ÇÖKÜYORDU · denklik aracı
yol hatasını "KAYIP VAR" ile AYNI exit'e (1) düşürüyordu.

İKİ YÖN AYNI KORPUSTA (biri diğerinin kontrol grubudur):
  • YAKALAMA  — gerçek analiz-günlüğü izi (sürüm anlatısı, doc-gate ID, süreç ifadesi,
                kullanıcı alıntısı, uzun §1.1 satırı) İŞARETLENİR.
  • SESSİZLİK — kimlik/metadata satırı, meşru hata kodu, ileriye dönük "TS'te ölçülür",
                katman-2 dosyası İŞARETLENMEZ. (FP çapaları mutasyonlarda AYAKTA kalır.)

Koşum:  python tests/fixtures/fs_docstd/run.py
Mutasyonlar (DÖRDÜ DE koşulur — hiçbiri diğerini kapsamaz):
  --mutasyon-desen        C-sınıfı deseni körelt        → P vektörleri DÜŞMELİ
  --mutasyon-katman0      kimlik-satırı muafiyetini sök → N-kimlik vektörleri DÜŞMELİ
  --mutasyon-failclosed   okunamayan dosya = sessiz atla→ A6 DÜŞMELİ
  --mutasyon-strict       --strict yine hard yapsın      → A10 DÜŞMELİ
  --mutasyon-esinifi      E sınıfı desenini körelt        → A1 DÜŞMELİ
  --mutasyon-baslik       başlık taramasını kapat         → A11 DÜŞMELİ
  --mutasyon-express      infra-EXPRESS nudge'ını sök     → X1/X3/X4 DÜŞMELİ, X5-X7 AYAKTA
  --mutasyon-onek         `core/` önekini sök             → Y1/Y2 DÜŞMELİ (yol çözülmez)
  --mutasyon-hook         doc-fs dalını sök             → B1-B5 DÜŞMELİ, R1-R3 AYAKTA
Herhangi biri tam puan verirse korpus O DEĞİŞMEZ için BOŞTUR.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

KOK = Path(__file__).resolve().parents[3]
VALIDATOR = KOK / "scripts" / "validators" / "check_fs_no_analysis_log.py"
HOOK = KOK / "scripts" / "hooks" / "post_validate.py"
DENKLIK = KOK / "scripts" / "doc_equivalence_check.py"
SHIM_SABLON = KOK / "claude" / "hook_shim.template.py"

# ── SANDBOX DOKÜMANLARI ───────────────────────────────────────────────────────
KIRLI_FS = """# FS-XX-999 — Örnek (Fonksiyonel Spesifikasyon)

## B1. Doküman Kontrolü
| Versiyon | Tarih | Yazar | Açıklama |
|---|---|---|---|
| v1.0 | 01.01.2026 | X | İlk sürüm |
| v1.2 | 02.01.2026 | X | %s |

## BÖLÜM 3: SÜREÇ (canlı-doğrulanmış — reuse/blast-radius)
Fatura tipi ZM12 seçilir (R-22 — DEV TVAK canlı ölçüldü; ilk turda alan adı yanlış yazılmıştı).
Kontrol Et butonu v1.5'te eklendi (doc-gate H-C netleşme).
Kullanıcı: "fiyat koşulumuz Z001 olmalı" — kullanıcı kararı 17.08.
Müşteri Malzeme No artık kalem satırında gösterilmez (R-6 revizyonu).
Şekil 1 — düz oklar koddan doğrulanmıştır; ön koşullar canlı S/4 DEV ölçümüyle doğrulanmış.
ÖK-05 bu revizyonla eklendi: kontrol edilmedi, build öncesi ayrıca doğrulanmalı.
""" % ("uzun anlatı " * 40)

TEMIZ_FS = """# FS-XX-998 v1.2 — Örnek (Fonksiyonel Spesifikasyon)

## B1. Doküman Kontrolü
| Versiyon | v1.2 |
| Durum | Onaylandı |

| Versiyon | Tarih | Yazar | Açıklama |
|---|---|---|---|
| v1.0 | 01.01.2026 | X | İlk sürüm |
| v1.2 | 02.01.2026 | X | Kolon eklendi |

### 1.3 İlgili Dokümanlar
| KD-XX-998 | Kullanıcı Kılavuzu | Yazıldı (v0.9) |
| RESEARCH-02 | S/4 DEV canlı teyit | ref_docs/RESEARCH-02.md |

## BÖLÜM 3: SÜREÇ
Fatura tipi ZM12'dir; teslimata bağlı fatura üretilir. Alan eşlemesi TS'te canlı ölçülür.
Miktar sıfırdan büyük olmalıdır; aksi halde L-01 hatası verilir ve kayıt M-02 ile kapatılır.
Bu kural standartta yazılmıştır ve değişmez.

<!-- E/C sınıfının FP KONTROL GRUBU — hepsi MEŞRU iş cümlesi, işaretlenmemeli -->
Bölünmeyen artık miktar hesaba katılır: artık = ana miktar − bölünme satırlarının toplamı.
Bakiye artık sayılmaz; kalan miktar HAZIR durumuna geçer.
Daha önce tahsis edilmiş bir lotun CEDNO'su sonradan değiştirilir; tahsis işaretlenir.
Sipariş ve mal çıkışı kontrolleri bu turda da ayrıca çalışır (ikinci güvenlik).
Alan eşlemesi build öncesi doğrulanmış olmalı.

*Doküman sonu — FS-XX-998 v1.2*
"""

# İÇ KONTROL GRUBU: aynı dosyada aynı sinyalin iki karşıt hâli.
IC_KONTROL_FS = """# FS-XX-997 — Örnek

## BÖLÜM 2: MEVCUT DURUM EKSİKLERİ
| **H-1** | Hareket sınıflandırması eksik. |
| **H-2** | Eşleşme üretilmiyor. |

## BÖLÜM 3: ÇÖZÜM
Sınıflandırma listesi eklenir (H-1 düzeltmesi) ve kolon ikiye ayrılır (H-2).
Buton matrisi netleştirildi (doc-gate M-6 netleşme).
"""

KATMAN2_EK = """# EK-B — Karar ve Kanıt Günlüğü

## R-22
(doc-gate v1.5 H-C) canlı ölçüldü, kullanıcı: "x" — ilk turda yanlış okunmuştu.
"""

# ⚠ Başlık YAZIM VARYANTI bilerek `| Ver. |` (canlı korpusta FS-EWM-000 böyle yazıyor;
# tek yazıma bağlanan atlama sınıfın yarısını ıskalar).
BASLIKSIZ_UZUN_FS = """# FS-XX-996 — Örnek

## B1. Doküman Kontrolü
| Ver. | Tarih | Yazar | Açıklama |
|---|---|---|---|
| v1.3 | 03.01.2026 | X | %s |

| v1.4 | 04.01.2026 | X | Kısa satır |

| Alan | Değer |
|---|---|
| Fatura tipi | v1.5'te ZM12 olarak değiştirildi (doc-gate H-1) |

## BÖLÜM 3: SÜREÇ
Sipariş kaydedilir ve teslimat oluşturulur.
""" % ("çok uzun sürüm anlatısı " * 30)

# Tek ihlali BAŞLIK satırında olan doküman: başlıklar eskiden hiç taranmıyordu.
BASLIK_FS = """# FS-XX-995 — Örnek

## 6. ETKİLENEN OBJELER (canlı-doğrulanmış — reuse/yeni/blast-radius)
Sipariş kaydedilir ve teslimat oluşturulur; kalemler tek tek işlenir.
"""

DQ_ESKI = """# FS-XX-001

| FR-001 | Kullanıcı malzeme kodunu ZSD001_T_HEAD tablosundan seçer ve miktarı girer. |
| FR-002 | Sistem 4500001234 numaralı referansı kontrol eder, uygun değilse P-01 verir. |

Kullanıcı teslimat tarihini 01.02.2026 girdiğinde sistem termin kontrolü yapar ve kaydeder.
"""
DQ_YENI_TAM = DQ_ESKI
DQ_YENI_KAYIPLI = """# FS-XX-001

| FR-001 | Kullanıcı malzeme kodunu ZSD001_T_HEAD tablosundan seçer ve miktarı girer. |
"""
DQ_ESKI_BUYUK = "Bu kural ZORUNLUDUR ve KESİNLİKLE uygulanır, aksi halde işlem REDDEDİLİR.\n"
DQ_YENI_KUCUK = "Bu kural zorunludur ve kesinlikle uygulanır, aksi halde işlem reddedilir.\n"


def _kur(sb: Path) -> None:
    (sb / "docs").mkdir(parents=True, exist_ok=True)
    (sb / "ref_docs").mkdir(parents=True, exist_ok=True)
    (sb / "scripts").mkdir(parents=True, exist_ok=True)
    (sb / "ui" / "app" / "webapp").mkdir(parents=True, exist_ok=True)
    (sb / "standards").mkdir(parents=True, exist_ok=True)
    (sb / "project.yaml").write_text("sap_profile: s4_private\nsource_root: SOURCE_CODES\n", encoding="utf-8")
    (sb / "docs" / "FS-XX-999_kirli.md").write_text(KIRLI_FS, encoding="utf-8")
    (sb / "docs" / "FS-XX-998_temiz.md").write_text(TEMIZ_FS, encoding="utf-8")
    (sb / "docs" / "FS-XX-997_ickontrol.md").write_text(IC_KONTROL_FS, encoding="utf-8")
    (sb / "docs" / "FS-XX-996_basliksiz.md").write_text(BASLIKSIZ_UZUN_FS, encoding="utf-8")
    (sb / "docs" / "FS-XX-995_baslik.md").write_text(BASLIK_FS, encoding="utf-8")
    (sb / "docs" / "EK-B-KARAR-GUNLUGU.md").write_text(KATMAN2_EK, encoding="utf-8")
    (sb / "governance").mkdir(parents=True, exist_ok=True)
    (sb / "governance" / "infra-findings.md").write_text("# kuyruk\n", encoding="utf-8")
    (sb / "scripts" / "validators-local").mkdir(parents=True, exist_ok=True)
    (sb / "scripts" / "validators-local" / "check_yerel.py").write_text("x = 1\n", encoding="utf-8")
    (sb / "docs" / "KD-XX-998_kilavuz.md").write_text(TEMIZ_FS, encoding="utf-8")
    (sb / "ref_docs" / "FS-benzeri-not.md").write_text(KIRLI_FS, encoding="utf-8")
    (sb / "ui" / "app" / "webapp" / "manifest.json").write_text("{}", encoding="utf-8")
    (sb / "scripts" / "sade.py").write_text("x = 1\n", encoding="utf-8")
    (sb / "standards" / "99-deneme.md").write_text("Bu kural ZORUNLU olarak uygulanır.\n", encoding="utf-8")
    if SHIM_SABLON.exists():
        shutil.copy2(SHIM_SABLON, sb / "scripts" / "hook_shim.py")


def _junction(sb: Path) -> bool:
    """<sandbox>/core → worktree. Junction (mklink /J) yönetici YETKİSİ İSTEMEZ."""
    hedef = sb / "core"
    if hedef.exists():
        return True
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(hedef), str(KOK)],
                       capture_output=True, text=True)
    return r.returncode == 0 and hedef.exists()


# ── KOŞUCULAR ─────────────────────────────────────────────────────────────────
def _val(validator: Path, *args, env=None) -> tuple:
    p = subprocess.run([sys.executable, str(validator), *args], cwd=str(KOK),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def _hook(sb: Path, hook_adi: str, payload, shim: bool, proje_env: bool = True) -> tuple:
    ham = payload if isinstance(payload, str) else json.dumps(payload)
    env = dict(os.environ)
    env.pop("CLAUDE_PROJECT_DIR", None)
    if proje_env:
        env["CLAUDE_PROJECT_DIR"] = str(sb)
    if shim:
        cmd = [sys.executable, str(sb / "scripts" / "hook_shim.py"), hook_adi]
    else:
        cmd = [sys.executable, str(KOK / "scripts" / "hooks" / (hook_adi + ".py"))]
    p = subprocess.run(cmd, input=ham, cwd=str(sb), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def _edit(yol: Path, sid: str) -> dict:
    return {"session_id": sid, "tool_name": "Edit",
            "tool_input": {"file_path": str(yol), "new_string": "x"}}


# ── MUTASYONLAR ───────────────────────────────────────────────────────────────
def _mutant(kip: str) -> tuple:
    """(validator_yolu, hook_adi) — mutant KOMŞULARININ yanına yazılır (import kırılmasın)."""
    v_yol, h_adi = VALIDATOR, "post_validate"
    if kip in ("hook", "express", "onek"):
        kaynak = HOOK.read_text(encoding="utf-8")
        if kip == "onek":
            yeni, n = re.subn(r"        return core_onekle\(metin\)",
                              "        return metin", kaynak, count=1)
            _capa(n, kip)
            hedef = HOOK.parent / "_mutant_post_validate.py"
            hedef.write_text(yeni, encoding="utf-8")
            return v_yol, "_mutant_post_validate"
        if kip == "express":
            yeni, n = re.subn(r"    _sinif = _paylasilan_infra\(norm, path\)",
                              "    _sinif = None", kaynak, count=1)
            _capa(n, kip)
            hedef = HOOK.parent / "_mutant_post_validate.py"
            hedef.write_text(yeni, encoding="utf-8")
            return v_yol, "_mutant_post_validate"
        yeni, n = re.subn(r'm_doc = re\.search\(r"/docs/\(FS\|TS\|KD\|EK\)-\[\^/\]\+\\\.md\$", norm, re\.IGNORECASE\)',
                          'm_doc = None', kaynak, count=1)
        _capa(n, kip)
        hedef = HOOK.parent / "_mutant_post_validate.py"
        hedef.write_text(yeni, encoding="utf-8")
        return v_yol, "_mutant_post_validate"

    kaynak = VALIDATOR.read_text(encoding="utf-8")
    if kip == "desen":
        yeni, n = re.subn(r'    "C süreç ifadesi": re\.compile\(', '    "C süreç ifadesi": re.compile(\n        r"ZZZ-ESLESMEYEN-DESEN") or re.compile(', kaynak, count=1)
    elif kip == "katman0":
        yeni, n = re.subn(r'def _metadata_satiri\(s: str\) -> bool:\n(    """[^"]*"""\n)',
                          r'def _metadata_satiri(s: str) -> bool:\n\1    return False\n', kaynak, count=1)
    elif kip == "esinifi":
        yeni, n = re.subn(r'    "E önceden→şimdi": re\.compile\(',
                          '    "E önceden→şimdi": re.compile(\n        r"ZZZ-ESLESMEYEN") or re.compile(',
                          kaynak, count=1)
    elif kip == "baslik":
        yeni, n = re.subn(r'            if not in_log and not in_version and not in_code and level > 1:',
                          '            if False:', kaynak, count=1)
    elif kip == "strict":
        yeni, n = re.subn(r'    bulguda_exit1 = "--bulguda-exit1" in argv',
                          '    bulguda_exit1 = "--bulguda-exit1" in argv or "--strict" in argv',
                          kaynak, count=1)
    elif kip == "failclosed":
        yeni, n = re.subn(r'            okunamadi \+= 1\n', '            okunamadi += 0\n', kaynak, count=1)
    else:
        raise SystemExit(f"bilinmeyen mutasyon: {kip}")
    _capa(n, kip)
    hedef = VALIDATOR.parent / "_mutant_check_fs.py"
    hedef.write_text(yeni, encoding="utf-8")
    return hedef, h_adi


def _capa(n: int, kip: str) -> None:
    if n != 1:
        raise SystemExit(f"[KOSUCU DURDU] mutasyon capasi bulunamadi (kip={kip}) — "
                         "kaynak degismis olabilir; SAYI RAPORLAMIYORUM.")


def main() -> int:
    kip = None
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon-"):
            kip = a.replace("--mutasyon-", "")

    validator, hook_adi = (VALIDATOR, "post_validate")
    sb = Path(tempfile.mkdtemp(prefix="fs_docstd_"))
    sonuc = []

    def ekle(ad, ok, detay):
        sonuc.append((ad, ok, detay))

    try:
        if kip:
            validator, hook_adi = _mutant(kip)
            print(f"  (MUTASYON: {kip} — ayirt edici vektorler DUSMELI)\n")
        _kur(sb)
        d = sb / "docs"
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(sb))

        # ── ① VALIDATOR ────────────────────────────────────────────────────
        rc, out, _ = _val(validator, "--file", str(d / "FS-XX-999_kirli.md"), "--bulguda-exit1", env=env)
        siniflar = sum(x in out for x in ("A sürüm-etiketi", "B gate-bulgu ID",
                                          "C süreç ifadesi", "D kullanıcı alıntı",
                                          "E önceden→şimdi"))
        ekle("A1 kirli FS → BEŞ sınıfın hepsi + exit 1", rc == 1 and siniflar == 5,
             f"exit={rc} sinif={siniflar}/5")
        ekle("A1b kirli FS'te uzun §1.1 satırı da raporlanıyor", "§1.1" in out,
             f"uzun_satir={'VAR' if '§1.1' in out else 'YOK'}")

        # FP ÇAPASI — kimlik/metadata/meşru kod: temiz FS gerçekten TEMİZ olabilmeli
        rc, out, _ = _val(validator, "--file", str(d / "FS-XX-998_temiz.md"), "--bulguda-exit1", env=env)
        ekle("A2 temiz FS (kapak+versiyon tablosu+ilgili dok.+altbilgi+L-01) → exit 0 temiz",
             rc == 0 and "temiz" in out, f"exit={rc} out={out.strip()[:70]}")

        rc, out, _ = _val(validator, "--file", str(d / "EK-B-KARAR-GUNLUGU.md"), "--bulguda-exit1", env=env)
        ekle("A3 katman-2 EK (Karar ve Kanıt Günlüğü) → taranmaz, exit 0",
             rc == 0 and "temiz" in out, f"exit={rc}")

        rc, out, _ = _val(validator, "--file", str(d / "FS-XX-996_basliksiz.md"), "--bulguda-exit1", env=env)
        # DURUM SIZMASI ÇAPASI: versiyon tablosundan SONRAKİ tablo yine GÖVDEDİR
        # (boş satır tabloyu kapatır) — aksi hâlde §1.1 muafiyeti belgeye yayılırdı.
        ekle("A4 BAŞLIKSIZ versiyon tablosu (`| Ver. |`): satırları gövde DEĞİL + uzunluk İŞLER, "
             "AMA sonraki tablo yine taranır",
             rc == 1 and "§1.1" in out and "A sürüm-etiketi" in out and "B gate-bulgu ID" in out,
             f"exit={rc} uzun={'VAR' if '§1.1' in out else 'YOK'} "
             f"sonraki_tablo={'TARANDI' if 'B gate-bulgu ID' in out else 'KAÇTI'}")

        rc, out, _ = _val(validator, "--file", str(d / "FS-XX-997_ickontrol.md"), "--bulguda-exit1", env=env)
        b_sayi = 0
        m = re.search(r"B gate-bulgu ID: (\d+)", out)
        if m:
            b_sayi = int(m.group(1))
        ekle("A5 İÇ KONTROL: belge-içi H-1/H-2 atfı sayılmaz, 'doc-gate M-6' SAYILIR",
             rc == 1 and b_sayi == 1 and "doc-gate" in out, f"exit={rc} B={b_sayi} (beklenen 1)")

        rc, out, err = _val(validator, "--file", str(d / "YOK-DOSYA-FS-1.md"), "--bulguda-exit1", env=env)
        # ⚠ ÇAPA "temiz" KELİMESİ DEĞİL, TEMİZ-VERDİCT cümlesidir: fail-closed mesajının
        # kendisi ("bu 'temiz' ANLAMINA GELMEZ") kelimeyi taşıyor — kelime çapası sahte FAIL verdi.
        temiz_verdict = "): temiz" in out
        ekle("A6 FAIL-CLOSED: okunamayan dosya TEMİZ VERDİCT'i vermez (exit 2)",
             rc == 2 and "ÖLÇÜLEMEDİ" in out and not temiz_verdict,
             f"exit={rc} olcemedi={'VAR' if 'ÖLÇÜLEMEDİ' in out else 'YOK'} temiz_verdict={'VAR' if temiz_verdict else 'YOK'}")

        # komşu-dizin tuzağı: str-prefix eşleşir ama relative_to ATAR → çökme
        komsu = Path(str(sb) + "2")
        (komsu / "docs").mkdir(parents=True, exist_ok=True)
        (komsu / "docs" / "FS-XX-995.md").write_text(KIRLI_FS, encoding="utf-8")
        rc, out, err = _val(validator, "--file", str(komsu / "docs" / "FS-XX-995.md"), "--bulguda-exit1", env=env)
        ekle("A7 KOMŞU dizin (…2) yolu → çökme YOK, bulgu raporlanır",
             rc == 1 and "Traceback" not in err, f"exit={rc} traceback={'VAR' if 'Traceback' in err else 'YOK'}")

        rc, out, err = _val(validator, "--file", env=env)
        ekle("A8 --file değersiz → net hata, çökme YOK", rc == 2 and "Traceback" not in err,
             f"exit={rc} traceback={'VAR' if 'Traceback' in err else 'YOK'}")

        # doc-gate v2.0: BAŞLIK satırındaki süreç izi de gövdedir
        rc, out, _ = _val(validator, "--file", str(d / "FS-XX-995_baslik.md"), "--bulguda-exit1", env=env)
        ekle("A11 tek ihlal BAŞLIK satırında → yakalanır (başlıklar eskiden hiç taranmıyordu)",
             rc == 1 and "C süreç ifadesi" in out, f"exit={rc}")

        # WARN-FIRST SÖZLEŞMESİ: run_all_validators --strict bu gate'i hard'a TERFİ ETTİRMEZ
        rc, out, _ = _val(validator, "--file", str(d / "FS-XX-999_kirli.md"), "--strict", env=env)
        ekle("A10 warn-first: --strict bulgu VARKEN bile exit 0 (kazara hard'a terfi YOK)",
             rc == 0 and "analiz-günlüğü işareti" in out, f"exit={rc} (beklenen 0)")

        rc, out, _ = _val(validator, "--selftest", env=env)
        ekle("A9 --selftest OK", rc == 0 and "OK" in out, f"exit={rc}")

        # ── ② HOOK (GERÇEK KABLOLAMA: hook_shim) ───────────────────────────
        shim_var = (sb / "scripts" / "hook_shim.py").exists() and _junction(sb)
        if not shim_var:
            print("  ⚠ NOT: hook_shim/junction kurulamadı → hook vektörleri DOĞRUDAN "
                  "çağrıyla koşuyor (kablolama KANITLANMADI, davranış kanıtlanıyor).\n")

        rc, _, err = _hook(sb, hook_adi, _edit(d / "FS-XX-999_kirli.md", "oturum-1"), shim_var)
        ekle("B1 kirli FS ilk dokunuş → exit 2 + ÖNCE OKU + UYARI",
             rc == 2 and "ÖNCE OKU" in err and "UYARI" in err,
             f"exit={rc} oku={'VAR' if 'ÖNCE OKU' in err else 'YOK'} uyari={'VAR' if 'UYARI' in err else 'YOK'}")

        rc, _, err = _hook(sb, hook_adi, _edit(d / "FS-XX-999_kirli.md", "oturum-1"), shim_var)
        ekle("B2 aynı oturum 2. dokunuş → OKU TEKRARLAMAZ, UYARI sürer",
             rc == 2 and "ÖNCE OKU" not in err and "UYARI" in err,
             f"exit={rc} oku={'VAR' if 'ÖNCE OKU' in err else 'YOK'}")

        rc, _, err = _hook(sb, hook_adi, _edit(d / "FS-XX-998_temiz.md", "oturum-2"), shim_var)
        ekle("B3 temiz FS yeni oturum → yalnız OKU (UYARI YOK)",
             rc == 2 and "ÖNCE OKU" in err and "UYARI" not in err,
             f"exit={rc} uyari={'VAR' if 'UYARI' in err else 'YOK'}")

        rc, _, err = _hook(sb, hook_adi, _edit(d / "FS-XX-998_temiz.md", "oturum-2"), shim_var)
        ekle("B4 temiz FS aynı oturum 2. dokunuş → exit 0 TAM SESSİZ",
             rc == 0 and not err.strip(), f"exit={rc} stderr={len(err.strip())}b")

        rc, _, err = _hook(sb, hook_adi, _edit(d / "KD-XX-998_kilavuz.md", "oturum-3"), shim_var)
        ekle("B5 KD dokümanı → OKU var, FS/EK gate'i KOŞMAZ (UYARI yok)",
             rc == 2 and "ÖNCE OKU" in err and "UYARI" not in err, f"exit={rc}")

        rc, _, err = _hook(sb, hook_adi, _edit(sb / "ref_docs" / "FS-benzeri-not.md", "oturum-4"), shim_var)
        ekle("B6 docs/ DIŞI md (ref_docs) → exit 0 sessiz", rc == 0 and not err.strip(),
             f"exit={rc} stderr={len(err.strip())}b")

        rc, _, err = _hook(sb, hook_adi, "{bozuk-json", shim_var)
        ekle("B7 bozuk JSON → exit 0 + GIRDI-PARSE-EDILEMEDI (fail-safe korundu)",
             rc == 0 and "GIRDI-PARSE-EDILEMEDI" in err, f"exit={rc}")

        # CLAUDE_PROJECT_DIR YOK: marker kökü dosyadan çözülmeli (yoksa dedup ölür)
        rc1, _, e1 = _hook(sb, hook_adi, _edit(d / "FS-XX-998_temiz.md", "oturum-5"), shim_var, proje_env=False)
        rc2, _, e2 = _hook(sb, hook_adi, _edit(d / "FS-XX-998_temiz.md", "oturum-5"), shim_var, proje_env=False)
        ekle("B8 CLAUDE_PROJECT_DIR YOK → marker proje kökünden bulunur (2. dokunuş sessiz)",
             "ÖNCE OKU" in e1 and "ÖNCE OKU" not in e2,
             f"1.={'OKU' if 'ÖNCE OKU' in e1 else '-'} 2.={'OKU' if 'ÖNCE OKU' in e2 else '-'}")

        # ── İNFRA-EXPRESS NUDGE (PATTERN #30): EXPRESS mi kuyruk mu? ───────
        def _ifade(err):
            return ("PAYLAŞILAN İNFRA" in err and "EXPRESS" in err
                    and "infra-findings.md" in err)

        rc, _, err = _hook(sb, hook_adi, _edit(KOK / "scripts" / "validators" / "check_x.py", "oturum-infra"), shim_var)
        ekle("X1 core validator .py ilk dokunuş → EXPRESS/kuyruk yol-ayrımı + 4 şart",
             rc == 2 and _ifade(err) and "④" in err, f"exit={rc} nudge={'VAR' if _ifade(err) else 'YOK'}")

        # X2 AYNI ZAMANDA "erken-return YOK" kanıtı: nudge susunca akış TRIGGER/HIZLI_KUME
        # yoluna devam edip validator alt-kümesini koşuyor ve temiz olduğu için exit 0 veriyor.
        rc, _, err = _hook(sb, hook_adi, _edit(KOK / "scripts" / "validators" / "check_y.py", "oturum-infra"), shim_var)
        ekle("X2 aynı oturum 2. validator .py → nudge TEKRARLAMAZ + HIZLI_KUME yolu KOŞUYOR (exit 0)",
             rc == 0 and not _ifade(err), f"exit={rc} nudge={'VAR' if _ifade(err) else 'YOK'}")

        rc, _, err = _hook(sb, hook_adi, _edit(sb / "core" / "scripts" / "hooks" / "yeni_hook.py", "oturum-inf2"), shim_var)
        ekle("X3 junction yazımı (<proje>/core/scripts/hooks/*.py) → nudge",
             _ifade(err), f"exit={rc} nudge={'VAR' if _ifade(err) else 'YOK'}")

        rc, _, err = _hook(sb, hook_adi, _edit(sb / "scripts" / "validators-local" / "check_yerel.py", "oturum-inf3"), shim_var)
        ekle("X4 proje-lokal validators-local/*.py → nudge (overlay gate'i de paylaşılan infra)",
             _ifade(err), f"exit={rc} nudge={'VAR' if _ifade(err) else 'YOK'}")

        rc, _, err = _hook(sb, hook_adi, _edit(sb / "scripts" / "sade.py", "oturum-inf4"), shim_var)
        ekle("X5 FP ÇAPASI: sıradan proje script'i → nudge YOK, exit 0 sessiz",
             rc == 0 and not err.strip(), f"exit={rc} stderr={len(err.strip())}b")

        rc, _, err = _hook(sb, hook_adi, _edit(KOK / "tests" / "fixtures" / "x" / "run.py", "oturum-inf5"), shim_var)
        ekle("X6 FP ÇAPASI: core tests/fixtures/*.py → nudge YOK (fixture infra KARARI değil)",
             not _ifade(err), f"exit={rc} nudge={'VAR' if _ifade(err) else 'YOK'}")

        # KOMŞU-DİZİN çapası: yol dizgesi str-prefix olarak core köküyle EŞLEŞİR ama
        # `is_relative_to` ile eşleşmez. Dizin YARATILMAZ (resolve() var olmayan yolu da çözer)
        # — worktree DIŞINA yazmadan komşu-FP'si ölçülür.
        rc, _, err = _hook(sb, hook_adi, _edit(Path(str(KOK) + "2") / "scripts" / "validators" / "x.py", "oturum-inf6"), shim_var)
        ekle("X7 FP ÇAPASI: KOMŞU dizin (…_wt_infra2) → nudge YOK (str-prefix tuzağı)",
             not _ifade(err), f"exit={rc} nudge={'VAR' if _ifade(err) else 'YOK'}")

        # X8: BAŞKA bir core checkout'u (kökünde CLAUDE.core.md) — canlı ölçümle bulundu:
        # lider ana oturumdan bir core WORKTREE'sini düzenlerse ② dalı tutmaz.
        sahte_core = sb / "baska_core"
        (sahte_core / "scripts" / "validators").mkdir(parents=True, exist_ok=True)
        (sahte_core / "CLAUDE.core.md").write_text("# core\n", encoding="utf-8")
        rc, _, err = _hook(sb, hook_adi, _edit(sahte_core / "scripts" / "validators" / "x.py", "oturum-inf7"), shim_var)
        ekle("X8 BAŞKA core checkout'u (CLAUDE.core.md işaretli) → nudge",
             _ifade(err), f"exit={rc} nudge={'VAR' if _ifade(err) else 'YOK'}")

        # X9 FP ÇAPASI: aynı şekle sahip ama core OLMAYAN ağaç (işaret dosyası YOK) → SESSİZ
        sahte_degil = sb / "core_degil"
        (sahte_degil / "scripts" / "validators").mkdir(parents=True, exist_ok=True)
        rc, _, err = _hook(sb, hook_adi, _edit(sahte_degil / "scripts" / "validators" / "x.py", "oturum-inf8"), shim_var)
        ekle("X9 FP ÇAPASI: scripts/validators şekli var ama CLAUDE.core.md YOK → nudge YOK",
             not _ifade(err), f"exit={rc} nudge={'VAR' if _ifade(err) else 'YOK'}")

        # ── ENJEKTE EDİLEN YOLLAR ÇÖZÜLÜYOR MU (C-HOOK-01 sınıfı) ──────────
        # "Ajan bu yolu Read edemez → 'dosya yok' sanır → ZORUNLU protokolü ATLAR."
        # Metin eşleşmesi YETMEZ: yolu sandbox proje kökünden GERÇEKTEN çözüyoruz.
        def _yollar_cozuluyor(err):
            yollar = sorted(set(re.findall(r"[\w/\-.]+\.md", err)))
            kirik = [y for y in yollar if not (sb / y).is_file()]
            return yollar, kirik

        rc, _, err = _hook(sb, hook_adi, _edit(KOK / "scripts" / "validators" / "check_z.py", "oturum-yol1"), shim_var)
        yollar, kirik = _yollar_cozuluyor(err)
        ekle("Y1 EXPRESS nudge'ındaki TÜM .md yolları proje kökünden çözülüyor",
             bool(yollar) and not kirik, f"yol={len(yollar)} kirik={kirik}")

        rc, _, err = _hook(sb, hook_adi, _edit(d / "FS-XX-998_temiz.md", "oturum-yol2"), shim_var)
        yollar, kirik = _yollar_cozuluyor(err)
        ekle("Y2 doc-fs OKU nudge'ındaki TÜM .md yolları proje kökünden çözülüyor",
             bool(yollar) and not kirik, f"yol={len(yollar)} kirik={kirik}")

        # ── KONTROL GRUBU: doc-fs dalı KOMŞU dalları bozmadı ───────────────
        rc, _, err = _hook(sb, hook_adi, _edit(sb / "ui" / "app" / "webapp" / "manifest.json", "oturum-6"), shim_var)
        ekle("R1 REGRESYON manifest.json → eski davranış (exit 2 + UI↔OData)",
             rc == 2 and "OData" in err, f"exit={rc}")

        rc, _, err = _hook(sb, hook_adi, _edit(sb / "scripts" / "sade.py", "oturum-6"), shim_var)
        ekle("R2 REGRESYON tetiksiz .py → exit 0 sessiz", rc == 0 and not err.strip(),
             f"exit={rc} stderr={len(err.strip())}b")

        rc, _, err = _hook(sb, hook_adi,
                           {"session_id": "oturum-6", "tool_name": "Edit",
                            "tool_input": {"file_path": str(sb / "standards" / "99-deneme.md"),
                                           "new_string": "Bu kural ZORUNLU olarak uygulanır."}}, shim_var)
        ekle("R3 REGRESYON standards/*.md + güç-keyword → ONBOARDING nudge sürüyor",
             rc == 2 and "ADR 0019" in err, f"exit={rc}")

        # ── ③ DENKLİK ARACI ────────────────────────────────────────────────
        dq = sb / "dq"
        dq.mkdir(exist_ok=True)
        (dq / "eski.md").write_text(DQ_ESKI, encoding="utf-8")
        (dq / "yeni_tam.md").write_text(DQ_YENI_TAM, encoding="utf-8")
        (dq / "yeni_kayipli.md").write_text(DQ_YENI_KAYIPLI, encoding="utf-8")
        (dq / "buyuk.md").write_text(DQ_ESKI_BUYUK, encoding="utf-8")
        (dq / "kucuk.md").write_text(DQ_YENI_KUCUK, encoding="utf-8")

        def _dq(*args):
            p = subprocess.run([sys.executable, str(DENKLIK), *args], cwd=str(dq),
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            return p.returncode, (p.stdout or "") + (p.stderr or "")

        rc, out = _dq("--old", "eski.md", "--new", "yeni_kayipli.md")
        ekle("C1 veri kaybı olan çift → exit 1 + KAYIP VAR", rc == 1 and "KAYIP VAR" in out, f"exit={rc}")
        rc, out = _dq("--old", "eski.md", "--new", "yeni_tam.md")
        ekle("C2 kayıpsız çift → exit 0 + DENK", rc == 0 and "DENK" in out, f"exit={rc}")
        rc, out = _dq("--old", "yok.md", "--new", "yeni_tam.md")
        ekle("C3 okunamayan girdi → exit 2 ('KAYIP VAR' ile karışmaz)",
             rc == 2 and "ÖLÇÜLEMEDİ" in out, f"exit={rc}")
        rc, out = _dq("--old", "buyuk.md", "--new", "kucuk.md")
        ekle("C4 FP ÇAPASI: yalnız büyük/küçük harf değişimi → DENK (T3 harf standardı)",
             rc == 0 and "DENK" in out, f"exit={rc}")

        gecen = sum(1 for _, ok, _ in sonuc if ok)
        for ad, ok, detay in sonuc:
            print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
        print(f"\n{gecen}/{len(sonuc)} OK")
        return 0 if gecen == len(sonuc) else 1
    finally:
        for artik in (VALIDATOR.parent / "_mutant_check_fs.py",
                      HOOK.parent / "_mutant_post_validate.py"):
            try:
                artik.unlink()
            except Exception:
                pass
        for yol in (sb, Path(str(sb) + "2")):
            try:
                if (yol / "core").exists():
                    subprocess.run(["cmd", "/c", "rmdir", str(yol / "core")], capture_output=True)
                shutil.rmtree(yol, ignore_errors=True)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
