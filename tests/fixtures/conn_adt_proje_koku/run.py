# -*- coding: utf-8 -*-
"""conn_adt_proje_koku — `.conn_adt` PROJE kökündedir: hem ARAÇ hem GATE tarafı.

KÖK (tek sınıf, iki yüz):
  `.conn_adt` SAP kimlik dosyası PROJE kökünde yaşar (env `CLAUDE_PROJECT_DIR` → cwd).
  Core script'i proje içinden `core/` junction'ıyla koşar ⇒ `Path(__file__)` DAİMA
  DEV_CORE'a çözülür (ADR 0020). İki yüz aynı korpusta durur, çünkü biri diğerini
  yalanlarsa hangisinin bozulduğu ancak birlikte ölçülünce görülür:

  A) ARAÇ  — `scripts/ui-smoke/run_ui_smoke.py` kökü `__file__`'dan türetiyordu
     (`REPO = HERE.parent.parent`) ⇒ `<DEV_CORE>/.conn_adt` arıyordu, orada dosya YOK
     ⇒ G1 UI-smoke gate'i (ADR 0017 deploy done-criteria) HER çağrıda ilk satırda
     ".conn_adt yok" ile ölüyordu. Kod göçüşten (2026-07-08) önce DOĞRUYDU: script
     proje reposundaydı, aynı `parent.parent` proje kökünü veriyordu — taşınınca
     SESSİZCE yanlış oldu (satır değişmedi, anlamı değişti).
  B) GATE  — `check_project_root_resolution` (CORE-01) tam bu sınıfı yasaklamak için
     var ama ihlal listesinde `.conn_adt` YOKTU ⇒ aynı koşuda "N script temiz" diyerek
     SAHTE GÜVEN üretiyordu. (Aracı düzeltip gate'i bırakmak, sınıfın yarınki
     örneğini yine kaçırırdı — F2 kök-soru: fix SINIFI çözmeli.)

⚠ FP ÇAPALARI (fix'ten ÖNCE de DOĞRU olan iddialar — ayırt edici DEĞİL):
  - A-N1: core'un KENDİ ağacına `__file__` ile bakmak MEŞRUDUR. `run_ui_smoke` playwright
    config'ini `HERE`'dan çözer; "tüm `__file__`'ları at" biçimindeki aşırı-geniş bir fix
    bunu kırar ve araç kimlik bulduğu hâlde koşamaz.
  - A-N2: `.conn_adt` HİÇBİR yerde yoksa araç sıfır-olmayan kodla durur ve playwright'ı
    ÇALIŞTIRMAZ (kimliksiz koşum = 401 riski/hesap kilidi).
  - B-N1/N2: kanonik `project_root() / ".conn_adt"` ve core-içi `KÖK / "playbook"`
    dedektörde SESSİZ kalmalı; `.conn_adt` eklemesi bunlara sızarsa gate alarm-yorgunluğu
    üretir ve `run_all_validators` her commit'i bloklar.
  ÖLÇÜT: bu iddiaların hepsi fix'ten ÖNCE de doğruydu ⇒ mutasyonda AYAKTA kalmalılar.
  (Fix'le GELEN yeni alanlar — "denenen proje kökü" satırı, yeni gerekçe metni — ayrı
  P-vektörlerinde ölçülür; çapaya karıştırılırsa "bozulmadı" kanıtı sessizce yok olur.
  ⚠ Bu tuzağa bu korpusun İLK yazımında düşüldü: A-P4 "FP çapası" diye etiketlenmişti,
  mutasyon onu yalanladı — eski sürüm o dala hiç varamıyordu. Etiketi mutasyon belirler,
  niyet değil.)

⚠ KONTROL GRUBU (B-K1): eskiden de yakalanan `KÖK / "SOURCE_CODES"`. Mutasyonda da
  yakalanmalı; yakalanmıyorsa bulgu değil HARNESS bozuktur (PATTERN #19).

3. BAĞLAM (görev-dışı): araç YALNIZ "proje kökünden koşulan" şekilde değil, cwd core
  ağacının içindeyken (env'li) ve hiç ilgisiz bir cwd'de (env'siz) de ölçülür — ikinci
  şekilde SESSİZCE yanlış köke düşmemeli, hangi kökü denediğini YAZMALI.

Koşum   : python tests/fixtures/conn_adt_proje_koku/run.py
MUTASYON: python tests/fixtures/conn_adt_proje_koku/run.py --mutasyon --ref add889c
          (taban SHA'ya pinlenir, dal adına DEĞİL — D2/5) → A-P*/B-P* düşer,
          A-N*/B-N*/B-K1 ayakta kalır.
"""
from __future__ import annotations

import argparse
import importlib.util
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

KOK = Path(__file__).resolve().parents[3]          # core repo kökü (worktree'de gerçek dizin)
ARAC_REL = "scripts/ui-smoke/run_ui_smoke.py"
GATE_REL = "scripts/validators/check_project_root_resolution.py"

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((ok, ad + (f" — {detay}" if detay else "")))


def _git_show(ref: str, rel: str) -> str | None:
    """Eski sürümü git'ten al. Alınamazsa None (çökme değil: ölçülemedi)."""
    try:
        p = subprocess.run(["git", "-C", str(KOK), "show", f"{ref}:{rel}"],
                           capture_output=True, timeout=60)
        return p.stdout.decode("utf-8", "replace") if p.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


# ─────────────────────────────────────────────────────────────────────────────
# A) ARAÇ TARAFI — run_ui_smoke.py kök çözümlemesi (davranışsal, subprocess)
# ─────────────────────────────────────────────────────────────────────────────
def _sahte_core(kaynak: str, tmp: Path) -> Path:
    """`<tmp>/scripts/{utils,ui-smoke}/` — GERÇEK yerleşimi taklit eden sahte core ağacı.

    ZORUNLU: script'i düz bir tmp dizinine kopyalamak yerleşimi BOZAR (`parent.parent`
    başka yere düşer) ⇒ ölçüm anlamsızlaşırdı. `utils/` de kopyalanır, çünkü düzeltilmiş
    sürüm kanonik `project_config`i core ağacından import eder.
    """
    (tmp / "scripts" / "ui-smoke").mkdir(parents=True, exist_ok=True)
    shutil.copytree(KOK / "scripts" / "utils", tmp / "scripts" / "utils", dirs_exist_ok=True)
    hedef = tmp / "scripts" / "ui-smoke" / "run_ui_smoke.py"
    hedef.write_text(kaynak, encoding="utf-8")
    return hedef


def _proje_dizini(tmp: Path, ad: str, conn: str | None) -> Path:
    p = tmp / ad
    p.mkdir(parents=True, exist_ok=True)
    if conn is not None:
        (p / ".conn_adt").write_text(conn, encoding="utf-8")
    return p


# `verify_auth_once` kapalı bir porta çarpar → status None → "[DUR] ... ulaşılamadı".
# Yani KİMLİK OKUNDU ama app yok: kimlik-okuma başarısından ağa çıkmadan emin oluruz.
CONN_TAM = "ADT_SAP_URL=https://ornek.gecersiz:44300\nADT_SAP_USER=<KULLANICI>\nADT_SAP_PASSWORD=<PAROLA>\n"
CONN_EKSIK = "ADT_SAP_URL=https://ornek.gecersiz:44300\n"
KAPALI_PORT = "http://127.0.0.1:9"          # discard portu: bağlantı reddedilir


def _arac_kos(script: Path, cwd: Path, env_proje: Path | None) -> tuple[int, str]:
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    if env_proje is not None:
        env["CLAUDE_PROJECT_DIR"] = str(env_proje)
    # ⚠ `sys.exit(mesaj)` STDERR'e yazar ve script yalnız STDOUT'u reconfigure eder →
    # Windows kod sayfasında Türkçe harfler `ı` kaçışına dönüşür. Bu yüzden (a) burada
    # UTF-8 zorlanır, (b) aşağıdaki iddialar YİNE DE yalnız ASCII belirteçlere bakar:
    # kod-sayfası kaymasında "aranan metin yok" sessizce YEŞİL verirdi (sahte PASS).
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, str(script), "--base-url", KAPALI_PORT],
                       cwd=str(cwd), env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _kimlik_okundu(cikti: str) -> bool:
    """Kimlik okuma AŞAMASI geçildi mi? (ağ aşamasına varmış olmak = `.conn_adt` bulundu)

    Yalnız ASCII belirteç: `[DUR]` (ağ/401 dalı) veya `[ok] auth`. `.conn_adt yok` her iki
    sürümde de ASCII önekle başlar → mutasyonda da güvenilir ayırt eder.
    """
    return ".conn_adt yok" not in cikti and ("[DUR]" in cikti or "[ok] auth" in cikti)


def arac_testleri(kaynak: str, tmp: Path) -> None:
    script = _sahte_core(kaynak, tmp / "core")
    proje = _proje_dizini(tmp, "proje", CONN_TAM)
    proje_eksik = _proje_dizini(tmp, "proje_eksik_alan", CONN_EKSIK)
    bos = _proje_dizini(tmp, "bos_dizin", None)

    # A-P1 ①bilinen-bozuk vektörü: cwd = proje kökü, env yok → kimlik BULUNMALI.
    #      Eski sürümde `<sahte-core>/.conn_adt` aranırdı ve orada dosya YOK ⇒ FAIL.
    rc, out = _arac_kos(script, cwd=proje, env_proje=None)
    kontrol(_kimlik_okundu(out), "A-P1 cwd=proje kökü → `.conn_adt` bulunur (env yok)",
            f"rc={rc} :: {out.strip()[:150]}")

    # A-P2 ③3.BAĞLAM: cwd CORE ağacının İÇİNDE (junction'dan koşum şekli), env proje'yi
    #      gösteriyor → env kazanmalı. Eski sürüm env'i HİÇ okumuyordu.
    rc, out = _arac_kos(script, cwd=script.parent, env_proje=proje)
    kontrol(_kimlik_okundu(out), "A-P2 3.bağlam cwd=core/ + env CLAUDE_PROJECT_DIR → env kazanır",
            f"rc={rc} :: {out.strip()[:150]}")

    # A-P3 ③3.BAĞLAM: ilgisiz cwd, env yok → SESSİZ yanlış değil, GÜRÜLTÜLÜ hata:
    #      denenen kökü ve kaynağını (cwd/env) yazmalı.
    rc, out = _arac_kos(script, cwd=bos, env_proje=None)
    kontrol(rc != 0 and str(bos) in out and "denenen proje" in out,
            "A-P3 3.bağlam ilgisiz cwd → denenen kök + kaynağı mesajda",
            f"rc={rc} :: {out.strip()[:200]}")

    # A-N1 FP ÇAPASI: core'un KENDİ ağacına `__file__` ile bakmak MEŞRU — playwright
    #      config'i script'in yanından çözülür. (Fix'ten ÖNCE de doğruydu.)
    kontrol("playwright.config.ts" in kaynak and "HERE" in kaynak,
            "A-N1 FP çapası: playwright config core-içi `HERE`'dan çözülüyor")

    # A-N2 FP ÇAPASI: kimlik hiç yoksa sıfır-olmayan çıkış + playwright ÇALIŞMAZ.
    #      (Fix'ten ÖNCE de doğruydu — kilit-güvenliği sözleşmesi.)
    rc, out = _arac_kos(script, cwd=bos, env_proje=bos)
    kontrol(rc != 0 and "[ok] auth" not in out,
            "A-N2 FP çapası: `.conn_adt` yok → rc!=0 ve playwright KOŞTURULMAZ",
            f"rc={rc} :: {out.strip()[:150]}")

    # A-P4 POZİTİF (çapa DEĞİL — ilk yazımda "FP çapası" diye etiketlemiştim, MUTASYON
    #      yalanladı: eski sürüm `.conn_adt`'yi hiç bulamadığı için bu dala ASLA varmıyor,
    #      yani iddia fix'ten ÖNCE doğru DEĞİLDİ ⇒ ayırt edici). Ölçtüğü şey: kök artık
    #      doğru çözülünce alan-seviyesi hata dalı gerçekten çalışıyor (kök hatası ALAN
    #      hatasını maskelemiyor).
    rc, out = _arac_kos(script, cwd=proje_eksik, env_proje=None)
    kontrol(rc != 0 and "ADT_SAP_USER" in out,
            "A-P4 `.conn_adt` var/alan eksik → ALAN hatası (kök hatası maskelemiyor)",
            f"rc={rc} :: {out.strip()[:150]}")


# ─────────────────────────────────────────────────────────────────────────────
# B) GATE TARAFI — CORE-01 dedektörü `.conn_adt`'yi görüyor mu (AST, in-process)
# ─────────────────────────────────────────────────────────────────────────────
BAS = "from pathlib import Path\nimport os, sys\nKOK = Path(__file__).resolve().parents[2]\n"

B_P1 = BAS + 'conn = KOK / ".conn_adt"\n'                       # canlı kusurun birebir şekli
B_P2 = BAS + 'conn = KOK.joinpath(".conn_adt")\n'               # `/` metot ikizi
B_P3 = BAS + 'conn = f"{KOK}/.conn_adt"\n'                      # metin birleştirme
B_K1 = BAS + 'hedef = KOK / "SOURCE_CODES"\n'                   # KONTROL: eskiden de yakalanır
B_N1 = ('from pathlib import Path\nfrom utils.project_config import project_root\n'
        'KOK = Path(__file__).resolve().parents[2]\nconn = project_root() / ".conn_adt"\n')
B_N2 = BAS + 'hedef = KOK / "playbook" / "README.md"\n'
B_N3 = BAS + 'print(f"core kökü: {KOK}")\n'


def gate_testleri(modul, tmp: Path) -> None:
    fn = getattr(modul, "_ihlaller", None)

    def bulgular(kaynak: str, ad: str):
        if fn is None:
            return None
        p = tmp / f"gate_{ad}.py"
        p.write_text(kaynak, encoding="utf-8")
        try:
            return list(fn(p))
        except Exception as e:  # noqa: BLE001  — "çökme ≠ FAIL"
            return f"HATA {type(e).__name__}: {e}"

    for ad, kaynak, etiket in (
        ("BP1", B_P1, 'B-P1 `KÖK / ".conn_adt"` (canlı kusurun birebir şekli)'),
        ("BP2", B_P2, 'B-P2 `KÖK.joinpath(".conn_adt")`'),
        ("BP3", B_P3, 'B-P3 metin birleştirme `f"{KÖK}/.conn_adt"`'),
    ):
        b = bulgular(kaynak, ad)
        if not isinstance(b, list):
            kontrol(False, etiket, f"ölçülemedi: {b}")
            continue
        metin = " ".join(m for _s, m in b)
        kontrol(len(b) >= 1 and ".conn_adt" in metin, etiket,
                f"bulgu={len(b)} :: {metin[:140]}")

    b = bulgular(B_K1, "BK1")
    kontrol(isinstance(b, list) and len(b) >= 1,
            'B-K1 KONTROL GRUBU `KÖK / "SOURCE_CODES"` (eskiden de yakalanan)',
            f"bulgu={len(b) if isinstance(b, list) else b}")

    for ad, kaynak, etiket in (
        ("BN1", B_N1, 'B-N1 FP çapası: kanonik `project_root() / ".conn_adt"` SESSİZ'),
        ("BN2", B_N2, 'B-N2 FP çapası: core-içi `KÖK / "playbook"` SESSİZ'),
        ("BN3", B_N3, "B-N3 FP çapası: kökü YAZDIRAN f-string SESSİZ"),
    ):
        b = bulgular(kaynak, ad)
        kontrol(isinstance(b, list) and len(b) == 0, etiket,
                f"bulgu={b if not isinstance(b, list) else len(b)}"
                + ("" if isinstance(b, list) and not b else f" :: {str(b)[:160]}"))


def _gate_modulu(kaynak: str | None, tmp: Path):
    """Gate modülünü yükle. `kaynak` verilirse (mutasyon) o metin geçici dosyadan yüklenir."""
    yol = KOK / GATE_REL
    if kaynak is not None:
        yol = tmp / "gate_eski" / "check_project_root_resolution.py"
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(kaynak, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("chk_conn_adt", yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true",
                    help="fix'i geri al: her iki dosyanın TABAN sürümüyle koş")
    ap.add_argument("--ref", default="add889c", help="mutasyon taban SHA'sı (dal adı DEĞİL)")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="conn_adt_kok_"))
    try:
        if args.mutasyon:
            arac_kaynak = _git_show(args.ref, ARAC_REL)
            gate_kaynak = _git_show(args.ref, GATE_REL)
            if arac_kaynak is None or gate_kaynak is None:
                print(f"[DOĞRULANAMADI] taban sürüm alınamadı ({args.ref}) — "
                      f"arac={arac_kaynak is not None} gate={gate_kaynak is not None}")
                return 1
            print(f"[MUTASYON] taban {args.ref}: P vektörleri DÜŞMELİ, N/K ayakta KALMALI\n")
        else:
            arac_kaynak = (KOK / ARAC_REL).read_text(encoding="utf-8")
            gate_kaynak = None

        arac_testleri(arac_kaynak, tmp)
        gate_testleri(_gate_modulu(gate_kaynak, tmp), tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    for ok, ad in SONUC:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
    print(f"\nconn_adt_proje_koku: {gecen}/{len(SONUC)} OK")
    if args.mutasyon:
        return 0          # mutasyon modunda karar SATIRLARDA (P düştü mü?), exit'te değil
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
