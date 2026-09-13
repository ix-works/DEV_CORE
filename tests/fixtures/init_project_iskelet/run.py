# -*- coding: utf-8 -*-
"""init_project_iskelet — jeneratörden çıkan iskelet KAPIDAN geçiyor mu + sır kilidi TOPYEKÛN mü?

ÜÇ DEĞİŞMEZ, DÖRT MUTASYON (her değişmez kendi mutasyonuyla sınanır; tek mutasyon yarısını sınamaz):

  ① KUYRUK TOHUMU (Q213) — `hooks/post_validate.py` stderr nudge'ında
     `governance/infra-findings.md` yolunu ajana ENJEKTE eder; `check_hook_injected_paths`
     (C-HOOK-01) enjekte edilen her yolu PROJE KÖKÜNDEN `is_file()` ile arar. `init_project`
     `governance/`e yalnız `.gitkeep` koyuyordu ⇒ jeneratörden çıkan HER projenin ilk
     `git commit`i (pre-commit → `run_all_validators --quick`) C-HOOK-01 ile FAIL veriyordu.
     ÖLÇÜLDÜ (2026-09-02, core junction'lı prova iskeleti):
        fix ÖNCESİ  → `[FAIL] enjekte edilen 1/8 yol PROJE KÖKÜNDEN ÇÖZÜLMÜYOR`
        fix SONRASI → `[OK] enjekte edilen 8 doküman yolunun tamamı çözülüyor`
     ⚠ Yol `core/` öneki ALMAZ ve almamalı: kuyruk PROJENİN kendi dosyasıdır (core'da yok);
       `inject_paths.core_onekle` yalnız `playbook|standards|profiles|governance/decisions`
       yollarını önekler. "Nudge yolu koşullu bassın" alternatifi ELENDİ (yolu gizlemek
       protokolü gizler) — bu fixture o kararın çapasıdır.

  ② SIR KİLİDİ TOPYEKÛN (Q241) — şablon `conn/` altını TEK TEK sayıyordu (`conn/*.env` +
     `conn/.conn_adt.bak`). Sayılmayan her yeni sır dosyası SESSİZCE izlenir hâle geliyordu.
     ÖLÇÜLDÜ (aynı prova, `git check-ignore -q` ÇIKIŞ KODUYLA — `-v` çıktısı NEGASYON
     satırını da basar, "çıktı var ⇒ ignore'lu" çıkarımı YANLIŞTIR):
        fix ÖNCESİ  → `conn/.gmail_app_password` ve `conn/mail_list.txt` **izlenir**
        fix SONRASI → ikisi de IGNORED; `*.template` / `README.md` / `.gitkeep` izlenmeye devam
     Kilit `conn/*` + AÇIK negasyon; `!conn/.gitkeep` ŞARTTIR (yoksa `conn/` dizini repoda
     hiç doğmaz — kilidin yan etkisi).

  ③ [ATLA] TEK DOSYA İÇİN `--force` ÖNERMEZ (Q314, 2026-09-13) — `uret` mevcut dosyada
     `[ATLA] <yol> (mevcut; --force ile ez)` basıyordu, bir koşumda 9–12 kez. `--force`
     üretilen HER dosyayı ezer (kum: proje-özel satır 4/4 dosyada gitti). Şimdi satır başına
     öneri yok; [ATLA] varsa koşum başına BİR not: "dosyayı TAŞI + AYNI argümanlarla yeniden
     koş · --force KULLANMA". ÖLÇÜT ANLAMLIDIR, literal değil: not metni `--force`'u UYARI
     olarak taşır ⇒ öneri = `--force` geçen ve AYNI satırda `KULLANMA` taşımayan satır
     (`force_onerileri`). A5 notun söylediği yolun gerçekten işlediğini ölçer (Q303 Q4 deseni).

⚠ FP ÇAPALARI OMURGADIR (N1-N5): kilit GENİŞLEDİ, bu yüzden "ne kilitlenmemeli" tarafı da
  ölçülür. `docs/paket.zip` izlenir (kök-çapalı `/*.zip`), `scripts/hook_shim.py` izlenir
  (yalnız `.yedek-*` kilitli), core-sızıntı + SIR satır kilidi (`check_core_not_committed`)
  bozulmadı. Bunlar düşerse jeneratör meşru dosyaları sessizce commit'ten düşürür.
  A4 (ilk koşumda not YOK) ③'ün FP çapasıdır: notu her koşumda basan fix gürültü üretir.

⚠ TABAN NASIL TÜRETİLİR: `git show <sha>:` YOK (sığ klonda çözülmez, merge'de bayatlar) —
  taban BUGÜNKÜ kaynaktan fix SÖKÜLEREK türetilir ve her sökümün ÇAPASI vardır; çapa
  tutmazsa koşucu sayı BASMAZ (exit 2 = "YAMA TUTMADI"). Mutant GERÇEK ağaca YAZILMAZ:
  izole bir core iskeleti kurulur (`scripts/utils` + gerekli `claude/` şablonları), çünkü
  `init_project` `CORE_ROOT = __file__.parent.parent`ten şablon okur ve `utils.yasaklar_stamp`
  import eder.

⚠ TEMİZLİK `_sil` ile (Q314 turunda ölçüldü): `shutil.rmtree(ignore_errors=True)` Windows'ta
  her koşumda `%TEMP%\\initproj_*` bırakıyordu (143 → 144; kalan `izole_core/scripts/utils`
  + `__pycache__`, salt-okur). Desen `precommit_kopya_surum_esligi._sil`.

Koşum:    python tests/fixtures/init_project_iskelet/run.py
MUTASYON: --mutasyon                → ① sökülür (kuyruk tohumu üretilmez)
          --mutasyon-gevsek         → ② sökülür (conn kilidi tek-tek sayıma, arşiv/yedek + kaynak-kök
                                      desenleri yok, `.format` kablolaması geri alınır)
          --mutasyon-force-onerisi  → ③a eski `[ATLA] … (mevcut; --force ile ez)` satırı geri gelir
          --mutasyon-not-yok        → ③b koşum sonu [ATLA] notu basılmaz
ÇIKIŞ KODU SÖZLEŞMESİ (kardeş korpuslarla aynı): normal 0=hepsi geçti · 1=düşen var ·
  2=alet geçersiz (yama tutmadı / iki kip birden). Mutasyon kipinde 0 "düşen yok" DEMEK
  DEĞİLDİR — kararı `N/M OK` satırından oku.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import stat
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
GERCEK = KOK / "scripts" / "init_project.py"
CHIP = KOK / "scripts" / "validators" / "check_hook_injected_paths.py"
SIZINTI = KOK / "scripts" / "validators" / "check_core_not_committed.py"

MUT = "--mutasyon" in sys.argv
MUT_GEVSEK = "--mutasyon-gevsek" in sys.argv
MUT_FORCE = "--mutasyon-force-onerisi" in sys.argv
MUT_NOT = "--mutasyon-not-yok" in sys.argv
if sum((MUT, MUT_GEVSEK, MUT_FORCE, MUT_NOT)) > 1:
    print("HATA: iki mutasyon kipi birlikte verilemez"); raise SystemExit(2)
HERHANGI_MUT = MUT or MUT_GEVSEK or MUT_FORCE or MUT_NOT

SONUC: list[tuple[bool, str]] = []


def kontrol(ok: bool, ad: str, detay: str = "") -> None:
    SONUC.append((bool(ok), ad + (f" — {detay}" if detay else "")))


# ── TABAN TÜRETME (fix'i bugünkü kaynaktan SÖK) ───────────────────────────────
SEED_CAGRISI = '        uret(proje / "governance" / "infra-findings.md", INFRA_FINDINGS, a.force),\n'

CONN_YENI = """.conn_adt
conn/*
!conn/*.template
!conn/README.md
!conn/.gitkeep
"""
CONN_ESKI = """.conn_adt
conn/*.env
conn/.conn_adt.bak
"""
KAYNAK_KOK_BLOGU = """# UI build çıktısı + deploy paketi (kaynak-kök PARAMETREDİR — `--source-root`)
{source_root}/**/ui/*/dist/
{source_root}/**/ui/*/archive.zip
"""
ARSIV_BLOGU = """# ==== arşiv / yedek — KÖK seviyesi (alt dizinlerdeki meşru .zip'e dokunmaz) ====
/*.zip
/*.7z
/*.tar
/*.tar.gz
/*.tgz
/*.bak
scripts/hook_shim.py.yedek-*

"""
FORMAT_CAGRISI = "GITIGNORE.format(source_root=a.source_root)"
# ③ Q314 çapaları (ESKİ satır = 18bbe78'deki literal)
ATLA_SATIRI_YENI = 'f"{ATLA_ETIKETI} {hedef} (mevcut; dokunulmadı)"'
ATLA_SATIRI_ESKI = 'f"[ATLA] {hedef} (mevcut; --force ile ez)"'
NOT_BASKISI = ('    if any(s.startswith(ATLA_ETIKETI) for s in sonuc):\n'
               '        print("\\n" + ATLA_NOTU)\n')


def _sok(metin: str, capa: str, yeni: str, etiket: str) -> str:
    if capa not in metin:
        print(f"HATA: YAMA TUTMADI — '{etiket}' çapası scripts/init_project.py'de YOK. "
              "Fix elden geçirilmiş olabilir; çapayı güncelle. Hiçbir sayı basılmadı.")
        raise SystemExit(2)
    return metin.replace(capa, yeni, 1)


def kaynak_uret() -> str:
    metin = GERCEK.read_text(encoding="utf-8")
    if MUT:
        metin = _sok(metin, SEED_CAGRISI, "", "kuyruk tohumu üretimi")
    if MUT_GEVSEK:
        metin = _sok(metin, CONN_YENI, CONN_ESKI, "conn/* topyekûn kilidi")
        metin = _sok(metin, KAYNAK_KOK_BLOGU, "", "kaynak-kök UI desenleri")
        metin = _sok(metin, ARSIV_BLOGU, "", "arşiv/yedek bloğu")
        metin = _sok(metin, FORMAT_CAGRISI, "GITIGNORE", ".format kablolaması")
    if MUT_FORCE:
        metin = _sok(metin, ATLA_SATIRI_YENI, ATLA_SATIRI_ESKI, "[ATLA] satırı (Q314)")
    if MUT_NOT:
        metin = _sok(metin, NOT_BASKISI, "", "[ATLA] koşum sonu notu (Q314)")
    return metin


_CLAUDE_DOSYALARI = (
    "CLAUDE.project.template.md", "README.project.template.md", "settings.template.json",
    "hook_shim.template.py", "kesin-yasaklar.canonical.md", "CODEOWNERS.template",
    "git-hooks/pre-commit.template", "workflows/guard.template.yml",
)


def izole_core(kum: Path) -> Path:
    """Mutant GERÇEK ağaca yazılmaz: minimal ama ÇALIŞIR bir core iskeleti kur."""
    core = kum / "izole_core"
    (core / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copytree(KOK / "scripts" / "utils", core / "scripts" / "utils")
    for rel in _CLAUDE_DOSYALARI:
        hedef = core / "claude" / rel
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(KOK / "claude" / rel, hedef)
    (core / "scripts" / "init_project.py").write_text(kaynak_uret(), encoding="utf-8",
                                                      newline="\n")
    return core


def _sil(d: Path) -> None:
    """Windows'ta salt-okur dizin/dosya `ignore_errors` ile SESSİZCE kalır (Q314: koşum başına 1)."""
    def _ac(func, path, _exc):                       # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)                       # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def temiz_env() -> dict:
    env = os.environ.copy()
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def uret_proje(core: Path, hedef: Path, *ek: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(core / "scripts" / "init_project.py"),
                        str(hedef), "--name", "PROVA", *ek],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=temiz_env(), timeout=180)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def git_init(p: Path) -> None:
    subprocess.run(["git", "-C", str(p), "init", "-q"], capture_output=True, text=True)


def ignore_mu(p: Path, rel: str) -> bool:
    """`git check-ignore` ÇIKIŞ KODU (0=ignore'lu). `-v` çıktısı negasyonu da basar."""
    r = subprocess.run(["git", "-C", str(p), "check-ignore", "-q", rel],
                       capture_output=True, text=True)
    return r.returncode == 0


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


# ── ③ ÇIKTI ÖLÇÜTLERİ (anlam, literal değil) ─────────────────────────────────
def atla_satirlari(cikti: str) -> list[str]:
    return [s for s in cikti.splitlines() if s.startswith("[ATLA]")]


def force_onerileri(cikti: str) -> list[str]:
    """`--force` geçen ve AYNI satırda `KULLANMA` taşımayan satır = öneri."""
    return [s for s in cikti.splitlines() if "--force" in s and "KULLANMA" not in s]


def not_sayisi(cikti: str) -> int:
    return sum(1 for s in cikti.splitlines() if s.startswith("NOT: [ATLA]"))


def ok_dosyalari(cikti: str) -> list[str]:
    return [s for s in cikti.splitlines() if s.startswith("[ OK ]") and "(klasör)" not in s]


def main() -> int:
    kum = Path(tempfile.mkdtemp(prefix="initproj_"))
    try:
        core = izole_core(kum)

        # ── K1 KABLOLAMA: izole ağaçtaki üretici, mutasyon DIŞI kipte gerçek dosyanın
        #    BİREBİR kopyasıdır (aksi hâlde bu korpus başka bir şeyi ölçerdi).
        ayni = md5(core / "scripts" / "init_project.py") == md5(GERCEK)
        kontrol(ayni if not HERHANGI_MUT else not ayni,
                "K1 KABLOLAMA izole üretici ↔ gerçek dosya "
                + ("EŞİT (mutasyon yok)" if not HERHANGI_MUT else "FARKLI (mutasyon var)"))

        # ── TABAN PROJE (full) ────────────────────────────────────────────────
        proje = kum / "proje_full"
        rc, cikti = uret_proje(core, proje)
        kontrol(rc == 0, "K2 KURULUM üretici exit 0",
                f"rc={rc} " + " ".join(cikti.split())[-160:])
        kuyruk = proje / "governance" / "infra-findings.md"
        gi = proje / ".gitignore"
        metin = kuyruk.read_text(encoding="utf-8") if kuyruk.exists() else ""
        gi_metin = gi.read_text(encoding="utf-8") if gi.exists() else ""

        # ── ① KUYRUK TOHUMU ───────────────────────────────────────────────────
        kontrol(kuyruk.is_file() and len(metin) > 200,
                "P1 kuyruk dosyası ÜRETİLDİ (boş değil)",
                f"var={kuyruk.is_file()} bayt={len(metin)}")
        kontrol("İNFRA-BULGU KUYRUĞU" in metin and "howto-infra-fix-proseduru" in metin,
                "P1b başlık + prosedür çapası")
        kontrol("core/playbook/howto-infra-fix-proseduru.md" in metin,
                "P1c prosedür yolu `core/` ÖNEKLİ (projede playbook junction altındadır)")
        kontrol("prior-art" in metin and "kontrol-grubu" in metin,
                "P1d zorunlu alan + format satırı çapası")

        # P2 — GERÇEK KAPI: C-HOOK-01 üretilen projeye karşı koşar; kuyruk yolu
        # kırık-listesinde OLMAMALI. (Junction'sız provada `core/...` yolları ayrıca
        # düşer — bu vektör YALNIZ kuyruk yolunu sorar, junction'dan bağımsızdır.)
        env = temiz_env(); env["CLAUDE_PROJECT_DIR"] = str(proje)
        r = subprocess.run([sys.executable, str(CHIP)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=900)
        chip_cikti = (r.stdout or "") + (r.stderr or "")
        kontrol("'governance/infra-findings.md' çözülmüyor" not in chip_cikti,
                "P2 KAPI C-HOOK-01 kuyruk yolunu KIRIK saymıyor",
                chip_cikti.strip().splitlines()[0] if chip_cikti.strip() else "çıktı yok")

        # P3 — VERİ KORUMA: dolu bir kuyruğun üstüne ikinci koşum (--force'suz) YAZMAZ.
        kuyruk.write_text("# ELLE YAZILMIŞ KAYIT\n\n## [Q1] test\n", encoding="utf-8")
        rc2, cikti2 = uret_proje(core, proje)
        kontrol(rc2 == 0 and "ELLE YAZILMIŞ KAYIT" in kuyruk.read_text(encoding="utf-8"),
                "P3 ikinci koşum var olan kuyruğu EZMEZ ([ATLA])",
                f"rc={rc2}")

        # ── ③ [ATLA] ÇIKTISI (Q314) ──────────────────────────────────────────
        atla2 = atla_satirlari(cikti2)
        kontrol(len(atla2) >= 1, "A1 ÇAPA ikinci koşumda [ATLA] satırı VAR (A2/A3 boş kümede geçmesin)",
                f"[ATLA]={len(atla2)}")
        oneriler2 = force_onerileri(cikti2)
        kontrol(not oneriler2,
                "A2 KULLANMA bağlamı dışında `--force` önerisi 0 (ikinci koşum, full)",
                f"öneri={len(oneriler2)}" + (f" ilk: {oneriler2[0].strip()[-80:]}" if oneriler2 else ""))
        kontrol(not_sayisi(cikti2) == 1 and "TAŞI" in cikti2 and "--force KULLANMA" in cikti2,
                "A3 [ATLA] notu koşum başına TAM 1 kez (TAŞI + --force KULLANMA)",
                f"not={not_sayisi(cikti2)}")
        kontrol(not_sayisi(cikti) == 0,
                "A4 FP ilk koşumda [ATLA] yok → not da YOK", f"not={not_sayisi(cikti)}")

        # A5 — notun söylediği yol GERÇEKTEN işler: dosyayı taşı + AYNI argümanla yeniden koş.
        ozel = "PROJE-OZEL-SATIR-Q314"
        claude_md = proje / "CLAUDE.md"
        claude_md.write_text(claude_md.read_text(encoding="utf-8") + f"\n{ozel}\n",
                             encoding="utf-8", newline="\n")
        ayar = proje / ".claude" / "settings.json"
        ayar_md5 = md5(ayar)
        ayar.replace(kum / "tasinan_settings.json")
        rc4, cikti4 = uret_proje(core, proje)
        ok4 = ok_dosyalari(cikti4)
        kontrol(rc4 == 0 and len(ok4) == 1 and ok4[0].endswith("settings.json")
                and ayar.is_file() and md5(ayar) == ayar_md5
                and ozel in claude_md.read_text(encoding="utf-8")
                and "ELLE YAZILMIŞ KAYIT" in kuyruk.read_text(encoding="utf-8"),
                "A5 taşı + aynı argümanla yeniden koş → YALNIZ taşınan üretilir, proje-özel içerik korunur",
                f"rc={rc4} üretilen={[Path(s.split('] ', 1)[1]).name for s in ok4]}")

        # ── ② SIR KİLİDİ ──────────────────────────────────────────────────────
        git_init(proje)
        kilitli = {rel: ignore_mu(proje, rel) for rel in
                   ("conn/.gmail_app_password", "conn/mail_list.txt", "conn/DEV.env",
                    "conn/.conn_adt.bak", "conn/alt/dizin/gizli.txt")}
        kontrol(all(kilitli.values()), "P4 conn/ altı TOPYEKÛN kilitli",
                ", ".join(f"{k}={'IGN' if v else 'IZLENIR'}" for k, v in kilitli.items()))
        kontrol(ignore_mu(proje, "scripts/hook_shim.py.yedek-20260902"),
                "P5 shim yedeği kilitli")
        kontrol(ignore_mu(proje, "dump.zip"), "P6 kök arşivi kilitli (/*.zip)")
        kontrol(ignore_mu(proje, "SOURCE_CODES/SD/ZX/ui/app/dist/index.js"),
                "P7 UI build çıktısı kilitli (kaynak-kök varsayılanı)")

        # ── FP ÇAPALARI (kilit GENİŞLEDİ ⇒ ne kilitlenmemeli de ölçülür) ───────
        kontrol(not ignore_mu(proje, "conn/DEV.env.template"),
                "N1 FP `conn/*.template` İZLENİR (ADR 0010 slot şablonları)")
        kontrol(not ignore_mu(proje, "conn/README.md"), "N2 FP `conn/README.md` İZLENİR")
        kontrol(not ignore_mu(proje, "conn/.gitkeep"),
                "N3 FP `conn/.gitkeep` İZLENİR (yoksa conn/ dizini repoda hiç doğmaz)")
        kontrol(not ignore_mu(proje, "scripts/hook_shim.py"),
                "N4 FP shim'in KENDİSİ izlenir (yalnız .yedek-* kilitli)")
        kontrol(not ignore_mu(proje, "docs/paket.zip"),
                "N5 FP alt dizindeki .zip izlenir (kök-çapalı `/*.zip` semantiği)")

        # N6 — GEVŞETME ÇAPASI: sızıntı + SIR satır kilidi bozulmadı.
        env2 = temiz_env(); env2["CLAUDE_PROJECT_DIR"] = str(proje)
        r2 = subprocess.run([sys.executable, str(SIZINTI)], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", env=env2, timeout=300)
        kontrol(r2.returncode == 0, "N6 core-sızıntı + SIR satır kilidi hâlâ TEMİZ",
                f"rc={r2.returncode} {(r2.stdout or '').strip()[-160:]}")
        kontrol(all(s in gi_metin.splitlines() for s in
                    ("/core/", ".claude/agents/", ".conn_adt", ".csrf_token.json")),
                "N7 kanonik kilit satırları TAM SATIR olarak duruyor")

        # ── ÜÇÜNCÜ BAĞLAM: görev-dışı şekil (--repo-mode none + farklı kaynak-kök) ─
        proje3 = kum / "proje_lite"
        ek3 = ("--repo-mode", "none", "--source-root", "ABAP_SRC")
        rc3, cikti3 = uret_proje(core, proje3, *ek3)
        gi3 = (proje3 / ".gitignore").read_text(encoding="utf-8") if (proje3 / ".gitignore").exists() else ""
        kontrol(rc3 == 0 and (proje3 / "governance" / "infra-findings.md").is_file(),
                "U1 3.BAĞLAM (--repo-mode none) kuyruk tohumu YİNE üretiliyor", f"rc={rc3}")
        kontrol("ABAP_SRC/**/ui/*/dist/" in gi3,
                "U2 3.BAĞLAM kaynak-kök PARAMETREDEN geliyor (--source-root ABAP_SRC)")
        kontrol("SOURCE_CODES" not in gi3,
                "U3 3.BAĞLAM varsayılan kaynak-kök adı SIZMIYOR")
        kontrol("{source_root}" not in gi3 and "{source_root}" not in gi_metin,
                "U4 KABLOLAMA doldurulmamış placeholder KALMADI (.format çağrıldı)")

        # U5 — kaydın ölçüldüğü biçim: LITE proje + tek eksik dosya (pre-commit) → yeniden koşum.
        (proje3 / "scripts" / "git-hooks" / "pre-commit").unlink()
        rc5, cikti5 = uret_proje(core, proje3, *ek3)
        atla5, ok5 = atla_satirlari(cikti5), ok_dosyalari(cikti5)
        kontrol(rc5 == 0 and len(atla5) >= 1 and not force_onerileri(cikti5)
                and len(ok5) == 1 and ok5[0].endswith("pre-commit"),
                "U5a 3.BAĞLAM LITE + eksik pre-commit: yalnız o üretilir, `--force` önerisi 0",
                f"rc={rc5} [ATLA]={len(atla5)} öneri={len(force_onerileri(cikti5))} "
                f"üretilen={len(ok5)}")
        kontrol(not_sayisi(cikti5) == 1, "U5b 3.BAĞLAM [ATLA] notu TAM 1 kez",
                f"not={not_sayisi(cikti5)}")

        gecen = sum(1 for ok, _ in SONUC if ok)
        for ok, ad in SONUC:
            print(("  [OK]   " if ok else "  [FAIL] ") + ad)
        print(f"\n{gecen}/{len(SONUC)} OK"
              + ("  (MUTASYON KİPİ — düşmesi BEKLENEN vektörler var)" if HERHANGI_MUT else ""))
        return 0 if gecen == len(SONUC) else 1
    finally:
        _sil(kum)


if __name__ == "__main__":
    raise SystemExit(main())
