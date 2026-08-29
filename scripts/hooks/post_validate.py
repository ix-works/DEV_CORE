#!/usr/bin/env python3
# ENFORCES: ADR-0006  (ADR 0019 coverage binding)
"""PostToolUse hook — governance/standards/validator/spec/.rules.md/populate_*.py
duzenlemesinden SONRA run_all_validators.py --quick'i otomatik kosturur.

Amac: ADR 0006 kod gate'lerini "agent elle hatirlasin" yerine "harness otomatik
zorlasin" haline getirmek. Advisory degil-blokaj: yalnizca validator FAIL olursa
stderr'e ozet yazip exit 2 ile sonucu Claude'a geri besler (CLAUDE.md §6 STOP
kurali: validator fail -> once duzelt). Validator OK ise sessizce cikar (exit 0).

Tetiklemeyen dosyalar (kaynak kod, UI, vb.) icin hicbir sey yapmaz -> sifir gurultu.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[2]

# Yalnizca asagidaki yollar validator'lari tetikler (regex, / normalize edilmis path uzerinde)
TRIGGER = re.compile(
    r"(\.rules\.md$"
    r"|/governance/"
    r"|/standards/"
    r"|/validators/"
    r"|populate_[^/]*\.py$"
    r"|sprint[^/]*\.(md|json)$"
    r"|SPRINT_PLAN"
    r"|td_spec)",
    re.IGNORECASE,
)

# P1 SEÇİCİLİK (T1.8, denetim 2026-07-31): edit-anında 24 validator'lık tam quick-tur
# (~13 sn) yerine dosya-SINIFINA göre bilinen-güvenli ALT-KÜME koşulur. İLKE: tabloda
# eşleşmeyen her TRIGGER dosyası TAM tura düşer (varsayılan DAİMA tam — fail-open yolu
# yok; ADR 0023). Tam tur pre-commit + CI'da zaten koşuyor → edit-anı erken-uyarı işlevi
# sınıfla İLGİLİ validator'larla korunur. Sıra önemli: ilk eşleşen sınıf kazanır.
HIZLI_KUME = [
    # (sınıf-adı, yol-regex'i, koşulacak validator script'leri)
    ("rules-md", re.compile(r"\.rules\.md$", re.IGNORECASE),
     ["check_rule_gate_coverage.py", "check_package_rules_present.py"]),
    ("validator-py", re.compile(r"/validators/[^/]+\.py$", re.IGNORECASE),
     ["check_console_utf8.py", "check_project_root_resolution.py",
      "check_rule_gate_coverage.py"]),
    ("populate-py", re.compile(r"populate_[^/]*\.py$", re.IGNORECASE),
     ["check_console_utf8.py", "check_project_root_resolution.py"]),
    ("standards-decisions", re.compile(r"/(standards|governance/decisions)/.+\.md$", re.IGNORECASE),
     ["check_core_index_fresh.py", "check_rule_gate_coverage.py"]),
    ("governance-md", re.compile(r"/governance/.+\.md$", re.IGNORECASE),
     ["check_core_index_fresh.py", "check_core_not_committed.py"]),
    # sprint*/SPRINT_PLAN/td_spec: BİLİNÇLİ tabloda YOK → tam tur (sprint kontrolleri
    # canlı-SAP'li populate-içi gate'lerdir; edit-anında hangi alt-kümenin yeteceği
    # kanıtlanmadı — kanıtsız daraltma yapılmaz).
]


def _hizli_kume_kos(sinif: str, scriptler: list) -> "tuple[bool, str]":
    """Alt-kümeyi koşar. (ok, fail_ozeti) döner; koşulamayan script = FAIL sayılır
    (fail-closed: 'koşamadım' sessiz PASS'e dönüşmez)."""
    hatalar = []
    for s in scriptler:
        yol = REPO / "scripts" / "validators" / s
        try:
            r = subprocess.run([sys.executable, str(yol)], cwd=str(REPO),
                               capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                hatalar.append(f"[{s}]\n" + (r.stdout or r.stderr or "")[-400:])
        except Exception as e:
            hatalar.append(f"[{s}] KOŞULAMADI: {e}")
    return (not hatalar, "\n".join(hatalar))


# Seçenek 2 (2026-06-24): DURUM/İZLEME dökümanları kural TAŞIMAZ → governance/ altında
# olsalar da heavy validator run'ı (run_all --quick) tetiklemezler. RESUME çapaları,
# SESSION_NOTES, auto-generated registry. Daraltma yönü under-exclude (şüpheli dosya yine
# tam doğrulanır); yalnız net-durum dosyaları. (ADR0019 onboarding nudge'ı zaten yalnız
# standards/playbook/governance-decisions için → bu dosyalar onu da tetiklemez.)
STATUS_DOC = re.compile(
    r"(RESUME[^/]*\.md$"
    r"|/SESSION_NOTES\.md$"
    r"|/package-registry\.md$)",
    re.IGNORECASE,
)


# ── PAYLAŞILAN İNFRA TESPİTİ (PATTERN #30: kuralı hatırlatan şey KONUMUDUR) ──
# `scripts/**/*.py` core deposunda (DEV_CORE + worktree'leri) VEYA junction üzerinden
# (`<proje>/core/scripts/...`) VEYA proje-lokal `scripts/validators-local/*.py`.
_INFRA_REL = re.compile(r"^scripts/.+\.py$", re.IGNORECASE)
_INFRA_HARIC = re.compile(r"/(tests|attic|TempScripts|__pycache__|\.tmp)/", re.IGNORECASE)


def _core_onekle(metin: str) -> str:
    """Enjekte edilen metodoloji yollarına `core/` öneki (C-HOOK-01).

    `playbook/x.md` ajanın Read()'inde ÇÖZÜLMEZ — metodoloji `core/` junction'ı altında.
    Tek kaynak `utils/inject_paths`; import `__file__`ten türetilir çünkü hook'lar
    `hook_shim` içinde `runpy` ile koşar ve `sys.path[0]` boş olur (kardeş-import ölür).
    Yardımcı bulunamazsa metin AYNEN döner — nudge asla hook'u düşürmez.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # core/scripts
        from utils.inject_paths import core_onekle  # type: ignore
        return core_onekle(metin)
    except Exception:
        return metin


def _paylasilan_infra(norm: str, ham: str):
    """→ sınıf etiketi ('hooks'/'validators'/'validators-local'/…) ya da None (deterministik)."""
    if _INFRA_HARIC.search(norm):
        return None                      # fixture/scratch/derleme artığı infra kararı DEĞİL
    if re.search(r"/scripts/validators-local/[^/]+\.py$", norm, re.IGNORECASE):
        return "proje-lokal validator"   # proje reposunda ama AYNI disiplin (overlay gate'i)
    rel = None
    m = re.search(r"/core/(scripts/.+\.py)$", norm, re.IGNORECASE)
    if m:                                # ① junction yazımı (<proje>/core/scripts/…)
        rel = m.group(1)
    else:
        try:
            p = Path(ham).resolve()
            if p.is_relative_to(REPO):   # ② bu hook'un KENDİ core'u — resolve + is_relative_to
                rel = p.relative_to(REPO).as_posix()  # (str-prefix DEĞİL: "…_wt_x" komşu FP'si)
            else:
                # ③ BAŞKA bir core checkout'u/worktree'si (ölçüldü 2026-08-17: lider canlı
                # oturumdan `…/DEV_CORE_wt_infra/scripts/...` düzenlediğinde ② tutmuyordu —
                # o yol bu hook'un core'una göre DIŞARIDA). Yapısal işaret: core kökünde
                # `CLAUDE.core.md` bulunur. Komşu-dizin FP'si üretmez: işaret dosyası yoksa None.
                for ana in p.parents:
                    if (ana / "CLAUDE.core.md").is_file():
                        rel = p.relative_to(ana).as_posix()
                        break
        except Exception:
            rel = None
    if not rel or not _INFRA_REL.match(rel):
        return None
    parca = rel.split("/")
    return "core scripts/" + (parca[1] if len(parca) > 2 else "")


def _isaret_koku(dosya_yolu: str) -> Path:
    """OKU-işaretçisi (dedup marker) dosyasının yazılacağı kök.

    Eskiden `CLAUDE_PROJECT_DIR` yoksa `os.getcwd()` kullanılıyordu; harness'in cwd'si
    proje olmak ZORUNDA değil → marker rastgele bir dizinde `.tmp/` açar, sonraki
    düzenlemede BULUNAMAZ ve nudge HER düzenlemede tekrar eder (gürültü = ölü hook).
    Sıra: env → düzenlenen dosyadan yukarı proje kökü (project.yaml/.git) → temp.
    """
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    try:
        for ana in Path(dosya_yolu).resolve().parents:
            if (ana / "project.yaml").exists() or (ana / ".git").exists():
                return ana
    except Exception:
        pass
    return Path(tempfile.gettempdir())


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Gerekce + sinif kaydi: scripts/hooks/README.md S4. ASCII-only + yazma hatasi
    fail-safe'i BOZMAMALI (except: pass).
    """
    try:
        sys.stderr.write(
            "[post_validate] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> fail-safe "
            "SERBEST (exit 0); KARAR DEGILDIR (girdi hic okunamadi). "
            "Negatif-test: governance/infra-test-recipes.md B0b\n")
    except Exception:
        pass


# ── K8① (2026-08-20): Bash ile yapılan DÜZENLEME de bir düzenlemedir ──────────
# Bu hook'un TÜM nudge'ları `tool_input.file_path`e bakıyordu. `sed -i`, heredoc,
# `> dosya` gibi Bash düzenlemelerinde o anahtar YOKTUR ⇒ nudge HİÇ ateşlemez
# (post_tool_failure 2026-08-14 sınıfının aynısı: araç değişti, tetik değişmedi).
#
# ⚠ SINIR-NOTU — bu kod TEK BAŞINA ÖLÜDÜR: hook `settings.template.json`'da
#    `matcher: "Edit|Write|MultiEdit"` ile kayıtlıdır; `Bash` eklenmedikçe hook
#    Bash çağrılarında ÇAĞRILMAZ. Matcher META-İNFRA'dır (bu turun kapsamı dışı)
#    ⇒ RAPORLANDI, kurulmadı. Aşağısı kablolama gelince ÇALIŞIR hâlde bekler ve
#    korpusla ölçülür (payload doğrudan hook'a verilerek).
#
# ⛔ TUTUCU OLMAK ZORUNDA: yanlış çıkarılan yol = her Bash komutunda gürültü =
#    ölü hook (alarm yorgunluğu). Bu yüzden YALNIZ yazma deyimleri taranır;
#    okuma (`cat`, `grep`, `head`) ASLA yol üretmez.
_BASH_YAZMA = (
    re.compile(r">>?\s*(?P<y>'[^']+'|\"[^\"]+\"|[^\s|;&<>]+)"),          # > dosya / >> dosya
    re.compile(r"\btee\s+(?:-a\s+)?(?P<y>'[^']+'|\"[^\"]+\"|[^\s|;&<>]+)"),
    re.compile(r"\bsed\s+(?:-[a-zA-Z]*i[a-zA-Z]*\S*\s+)(?:-e\s+\S+\s+|'[^']*'\s+|\"[^\"]*\"\s+)*"
               r"(?P<y>'[^']+'|\"[^\"]+\"|[^\s|;&<>]+)"),                 # sed -i ... dosya
    re.compile(r"\btouch\s+(?P<y>'[^']+'|\"[^\"]+\"|[^\s|;&<>]+)"),
)


def _bash_duzenlenen_yol(tool_input: dict) -> str:
    """Bash komutundan DÜZENLENEN dosya yolunu çıkar; emin değilse BOŞ döner.

    Boş dönmek güvenli taraftır: nudge ateşlemez (bugünkü davranış). Yanlış bir yol
    döndürmek ise her komutta yanlış hatırlatma üretir — o yüzden tahmin YOK.
    """
    komut = tool_input.get("command") or ""
    if not isinstance(komut, str) or not komut.strip():
        return ""
    for kalip in _BASH_YAZMA:
        m = kalip.search(komut)
        if not m:
            continue
        y = m.group("y").strip("'\"")
        # `/dev/null`, `&1` gibi hedefler dosya DEĞİLDİR; uzantısız hedefe de girmeyiz
        # (nudge'ların hepsi uzantıya bakar — uzantısızı taşımanın faydası yok).
        if y.startswith(("/dev/", "&")) or "." not in Path(y).name:
            continue
        return y
    return ""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
        return 0

    tool_input = data.get("tool_input", {}) or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path and (data.get("tool_name") or "") == "Bash":
        path = _bash_duzenlenen_yol(tool_input)
    if not path:
        return 0

    norm = path.replace("\\", "/")

    # #11 (2026-06-11): UI manifest.json düzenlendi → OData ref cross-check HATIRLAT.
    # Araç (check_ui_odata_refs.py) hazırdı, tetik eksikti → "remember to run" disiplini
    # kod-nudge'a çevrildi (ui-freestyle §H ZORUNLU). Servise/dataSource'a dokunulduysa
    # browser'da tıklayarak değil statik cross-check ile doğrula.
    if re.search(r"/ui/[^/]+/.*manifest\.json$", norm, re.IGNORECASE):
        app = re.sub(r"/webapp/.*$", "", norm)
        sys.stderr.write(
            "[hook:post_validate] UI manifest.json düzenlendi. dataSource/servis "
            "değiştiysen UI↔OData ref tutarlılığını DOĞRULA (ui-freestyle §H):\n"
            f"  python scripts/check_ui_odata_refs.py --app {app} --service <SRVB_adi>\n"
            "(entity/property/function ref'leri canlı metadata ile statik kıyas — tıklama testi DEĞİL).\n"
        )
        return 2  # reminder (Claude'a geri beslenir)

    # 2026-08-17: FS/TS/KD/EK dokümanı düzenlendi → İLKE-2b (3 katman) hatırlat + o dosyada
    # analiz-günlüğü sızıntısını say (check_fs_no_analysis_log --file --strict). Kullanıcı bulgusu:
    # 9 sürümlük FS gövdesi sürüm etiketi/gate-ID/"canlı ölçüldü" notuyla dolmuştu ve HİÇBİR hook
    # doküman düzenlemesinde ateşlemiyordu (TRIGGER'da docs/ yoktu; standart yalnız indeksten
    # erişilebilirdi) → kural vardı, okunma noktası yoktu. Bu blok: (a) oturumda ilk dokunuşta OKU
    # işaretçisi (dedup: .tmp marker), (b) her düzenlemede bulgu özeti. Warn-first: mesaj UYARI dilinde,
    # exit 2 yalnız geri-besleme (edit zaten oldu; ADR 0006 "önce düzelt" gate'i DEĞİL).
    m_doc = re.search(r"/docs/(FS|TS|KD|EK)-[^/]+\.md$", norm, re.IGNORECASE)
    if m_doc:
        kind = m_doc.group(1).upper()
        lines = []
        try:
            proj = _isaret_koku(path)
            # session_id yoksa sabit "nosession" marker'ı diske KALICI yazılır ve
            # nudge bir daha HİÇ ateşlemez (sessizce ölen hatırlatıcı). Gün damgası
            # en kötü durumda günde bir kez konuşmayı garanti eder.
            sid = str(data.get("session_id") or "").strip()[:12] or \
                ("gun-" + datetime.date.today().isoformat())
            marker = proj / ".tmp" / f".hook_docstd_{sid}_{kind}"
            if not marker.exists():
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text("1", encoding="utf-8")
                lines.append(_core_onekle(
                             f"[hook:post_validate] {kind} dokümanı düzenleniyor — ÖNCE OKU (oturumda bir kez): "
                             "standards/04-documentation-fs-ts.md §2.0 (İLKE-1/2/2b: kullanıcı isteği=kanon · öneri/soru "
                             "11-A/11-B · ÜÇ KATMAN: gövde=kapanmış hedef durum, karar günlüğü ayrı, analiz süreci FS'e girmez) "
                             "+ §2.3 · playbook/checklists/doc-checklist.md §B DOC-FS-01…07 (TS için §C). "
                             "Yeniden yazım/temizlikte veri kaybı=0: "
                             "core/scripts/doc_equivalence_check.py --old ESKİ --new YENİ --new EK "
                             "--kapanmis-karar <KAPANMIŞ_KARARIN_ESKİ_DEĞERİ>  "
                             "(#12③ — bayrak VERİLMEZSE ters yön HİÇ ölçülmez: 'elenmiştir' "
                             "cümlesi içinde geçen değer 'korunmuş' sayılır ve gate yeşil kalır. "
                             "Tekrarlanabilir; hangi değerin kapandığını SEN belirlersin — "
                             "'çözüm mü, reddedilen alternatif mi' sınıflandırması insana aittir)."))
        except Exception:
            pass
        if kind in ("FS", "EK"):
            try:
                res = subprocess.run(
                    [sys.executable, str(REPO / "scripts" / "validators" / "check_fs_no_analysis_log.py"),
                     "--file", path, "--bulguda-exit1", "--max-examples", "2"],
                    cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
                if res.returncode == 1 and (res.stdout or "").strip():
                    lines.append("[hook:post_validate] UYARI (warn-first, DOC-FS-05/06a — İLKE-2b): gövdede analiz-günlüğü izi var — "
                                 "sürüm etiketi/gate-ID/\"canlı ölçüldü\"/kullanıcı alıntısı → EK 'Karar ve Kanıt Günlüğü'ne taşı; "
                                 "§1.1 satırı 1-2 satır. Onaya çıkmadan temizle:\n" + (res.stdout or "")[-900:])
                elif res.returncode not in (0, 1):
                    # "ÖLÇEMEDİM" != "TEMİZ": gate okuyamadığı dosya için exit 2 döner.
                    lines.append(f"[hook:post_validate] NOT: analiz-günlüğü gate'i ÖLÇEMEDİ "
                                 f"(exit {res.returncode}) — bu 'temiz' ANLAMINA GELMEZ:\n"
                                 + ((res.stdout or res.stderr or "")[-300:]))
            except Exception:
                pass
        if lines:
            sys.stderr.write("\n".join(lines) + "\n")
            return 2  # geri besleme (edit oldu; bloklamaz)
        return 0

    # #7 (2026-06-11): list/report view.xml → grid (sap.ui.table) standardı kontrol (ADR 0008).
    # check_list_view_grid conservative; flag ederse nudge (bloklamaz).
    if re.search(r"/ui/.+\.view\.xml$", norm, re.IGNORECASE):
        try:
            res = subprocess.run(
                [sys.executable, str(REPO / "scripts" / "validators" / "check_list_view_grid.py"), path],
                cwd=str(REPO), capture_output=True, text=True, timeout=30)
            if res.returncode == 1 and (res.stdout or "").strip():
                sys.stderr.write(
                    "[hook:post_validate] Liste/rapor görünümü grid standardı (ADR 0008, feedback_grid-liste-standardi):\n"
                    + (res.stdout or "")[-500:] + "\n")
                return 2
        except Exception:
            pass

    # ADR 0019 §5 + §5A ONBOARDING (amendment 2026-06-18): kural-taşıyan dosyada YENİ/DEĞİŞEN
    # kural → 5-adım enforcement-onboarding + 8-ölçüt RUBRIC (metin-KALİTESİ) HATIRLAT.
    # KAPSAM genişletildi: checklists + standards + playbook + governance/decisions + AGENTS/CLAUDE
    # (eskiden YALNIZ checklists → ADR §5 "standards/playbook/checklists" sözünü eksik karşılıyordu).
    # Noise-azalt: edit güç-keyword içermeli (typo/format sessiz); checklist her zaman + coverage somut.
    nudged = False

    # 2026-08-17 — PATTERN #30 ("kural VARDI ama ateşlemedi; kuralı hatırlatan şey KONUMUDUR"):
    # paylaşılan infra'ya yazarken HİÇBİR hook "bu EXPRESS mi, kuyruk mu?" diye sormuyordu;
    # howto-infra-fix ADIM 2 yol-ayrımı yalnız playbook'ta duruyordu (okuyan hatırlıyordu).
    # Bloklamaz, oturumda BİR KEZ, erken-return YOK: TRIGGER/HIZLI_KUME yolu aynen sürer.
    _sinif = _paylasilan_infra(norm, path)
    if _sinif:
        try:
            _mk = _isaret_koku(path) / ".tmp" / (
                ".hook_infraexpress_" + (str(data.get("session_id") or "").strip()[:12]
                                         or ("gun-" + datetime.date.today().isoformat())))
            if not _mk.exists():
                _mk.parent.mkdir(parents=True, exist_ok=True)
                _mk.write_text("1", encoding="utf-8")
                sys.stderr.write(_core_onekle(
                    f"[hook:post_validate] PAYLAŞILAN İNFRA düzenleniyor ({_sinif}) — ÖNCE YOL AYRIMI "
                    "(playbook/howto-infra-fix-proseduru.md ADIM 2):\n"
                    "  ⚡ EXPRESS (lider, görev-içi) YALNIZ DÖRDÜ BİRDEN sağlanıyorsa: ① mekanik hata "
                    "(typo/kırık-yol/yanlış-değişken/eksik-import), davranış-kararı YOK · ② blast-radius "
                    "grep'le TEK-NOKTA kanıtlı · ③ mevcut fixture/negatif-test ≤1 dk'da YEŞİL · "
                    "④ hiçbir kuralı GEVŞETMİYOR → fix + test + AYRI commit.\n"
                    "  📥 DÖRDÜ BİRDEN DEĞİLSE → DUR, KUYRUK (varsayılan): governance/infra-findings.md'ye "
                    "tek satır (tarih | bileşen | semptom | kontrol-grubu | sınıf K1-K4 | görev-bağlamı | "
                    "önerilen-yön) → fix'i TAZE bir infra-expert AYRI seansta üretir (ADIM 3: F0 geçmiş-okuma · "
                    "F1 blast-radius · F2 sınıf-mı-vaka-mı · F3 ÜÇ-BAĞLAM + kalıcı fixture · F4 gevşetme-cetveli). "
                    "Görev DEVAM eder; workaround bypass DEĞİLDİR.\n"
                    "  (oturumda bir kez · bloklamaz · gate değil hatırlatıcı)\n"))
                nudged = True
        except Exception:
            pass

    if re.search(r"/(standards|playbook|governance/decisions)/.+\.md$|/(AGENTS|CLAUDE)\.md$", norm, re.IGNORECASE):
        new_txt = tool_input.get("new_string") or tool_input.get("content") or ""
        for _e in (tool_input.get("edits") or []):
            new_txt += "\n" + (_e.get("new_string") or "")
        is_checklist = "/checklists/" in norm
        guc = re.search(r"\b(MUST|MUST-NOT|SHOULD|SHOULD-NOT|MAY|ZORUNLU|YASAK|YASAKTIR|ÖNERİLİR|OPSİYONEL|BLOCKER|WARNING)\b",
                        new_txt, re.IGNORECASE)
        if is_checklist or guc:
            lines = ["[hook:post_validate] Kural-taşıyan dosya düzenlendi — YENİ/DEĞİŞEN KURAL ise (değilse yoksay):"]
            if is_checklist:
                try:
                    res = subprocess.run(
                        [sys.executable, str(REPO / "scripts" / "validators" / "check_rule_gate_coverage.py"), "--strict"],
                        cwd=str(REPO), capture_output=True, text=True, timeout=60)
                    if res.returncode != 0:
                        lines.append("• COVERAGE AÇIĞI (kural↔gate, ADR 0019):\n" + (res.stdout or "")[-450:])
                except Exception:
                    pass
            lines.append("• ÖNCE-ARA (KB-01, CLAUDE.core §4): ① ARA (repo+core path=core/+memory+SESSION_NOTES+register: "
                         "zaten yazılı mı · regresyon mu ilk temas mı · komşu obje-tipinde var mı) → ② ÖLÇ (kontrol grubu; "
                         "ölçümü GERÇEK giriş noktasından ve SON hâl üzerinde yap — elle script çağrısı kablolamayı kanıtlamaz) "
                         "→ ③ DARALT (kanıtın kapsamını yaz) → ④ YAZ. Kayda `prior-art: bulundu <ref>` VEYA `yok` koy.")
            lines.append("• ONBOARDING (ADR 0019 §5): (1)güç-etiketle MUST/MUST-NOT/SHOULD/MAY (2)enforcement-seç "
                         "(3)gate+fixture(oto) VEYA reviewer+checklist-üyeliği(yargı) (4)stabil-ID (5)coverage-check.")
            lines.append("• RUBRIC metin-KALİTESİ (ADR 0019 §5A, 8 ölçüt): atomik · güç-açık · denetlenebilir(pass/fail) · "
                         "kapsam-belli · tek-ev(canonical,tekrar değil) · bağımsız-anlaşılır(+gerekçe) · stabil-ID · güncel-çelişkisiz.")
            sys.stderr.write("\n".join(lines) + "\n")
            nudged = True

    # Seçenek 2: durum/izleme dökümanı → kural taşımaz, heavy run ATLA (governance/ match'lese bile)
    if not TRIGGER.search(norm) or STATUS_DOC.search(norm):
        return 2 if nudged else 0

    # P1: dosya-sınıfı eşleşirse ALT-KÜME koş; eşleşmezse aşağıdaki TAM tur (varsayılan).
    for sinif, desen, scriptler in HIZLI_KUME:
        if desen.search(norm):
            ok, ozet = _hizli_kume_kos(sinif, scriptler)
            if ok:
                return 2 if nudged else 0
            sys.stderr.write(
                f"[hook:post_validate] hızlı-küme FAIL (sınıf: {sinif}; "
                f"{Path(path).name} düzenlendi).\n"
                "ADR 0006 gate: forward progress YOK -> önce ihlali düzelt.\n"
                "(Tam tur pre-commit/CI'da ayrıca koşar.)\n--- özet ---\n" + ozet + "\n")
            return 2

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(REPO / "scripts" / "validators" / "run_all_validators.py"),
                "--quick",
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception:
        # Validator kosturulamazsa hook calismayi engellemesin
        return 0

    if result.returncode == 0:
        return 2 if nudged else 0  # run_all OK; nudge varsa yine de yüzeyle

    tail = (result.stdout or "")[-800:]
    sys.stderr.write(
        "[hook:post_validate] run_all_validators.py --quick FAIL "
        f"({Path(path).name} duzenlendi).\n"
        "ADR 0006 gate: forward progress YOK -> once ihlali duzelt.\n"
        "--- validator ozeti ---\n" + tail + "\n"
    )
    return 2  # PostToolUse: stderr Claude'a geri beslenir, blokaj degil


if __name__ == "__main__":
    sys.exit(main())
