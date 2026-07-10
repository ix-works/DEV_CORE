"""Profil-bazlı tool yüzeyi (D34d / ADR 0007 §9.4d).

`CLAUDE.core.md §2` yıllardır şunu söylüyordu:

> "profil-dışı kural o projede UYGULANMAZ (validators/skill-injector/**MCP-guardrail**
>  profili okur; profil alanları BOŞSA varsayma — kullanıcıyı setup'a yönlendir,
>  **tool-yüzeyi kesilir**)"

…ama §7'de "profil-bazlı tool-blok HENÜZ KODDA DEĞİL — PLANLI" yazıyordu. Yazılı kural,
kodlanmamış kural. Bu modül o boşluğu kapatır.

## Tasarım (prior-art: arc-mcp/arc-1 `availableOn`)

Tool'lar `available_on` etiketi taşır. Profil uymuyorsa tool **hiç register edilmez** →
`tools/list`'te GÖRÜNMEZ. Model olmayan bir tool'u çağıramaz; bu, prompt-seviyesi
"kullanma" ricasından farklı olarak **tool-sınırında deterministik**tir.

## ⚠ Kanıt disiplini — neden gate listesi bu kadar kısa?

`profiles/*.yaml` kendi başında şunu yazar: *"MATRİS REHBERDİR, KANIT DEĞİLDİR: capability
iddiası CANLI TESTLE doğrulanır."* Bu yüzden tool'ları profil-dışı ilan etmek için
matriste **açık ve tartışmasız** bir hücre gerekir. Bugün (2026-07-10) tek böyle hücre var:

  * `btp_abap.transport: gcts` — gCTS'te klasik CTS yoktur; `adt_transport_list`
    `/sap/bc/adt/cts/...` uçlarına gider → o profilde anlamsızdır.
  * `s4_public.transport: cloud_ts` hücresi **açıkça "NÖTR (D27) — canlı doğrulanacak"**
    diyor → BLOKLAMIYORUZ. Kanıtsız daraltma yapılmaz.

Geri kalan 17 tool `("all",)`. Bu tembellik değil, **kanıt yokluğudur**: ilk s4_public /
btp_abap projesi açıldığında canlı test edilip buraya eklenecek. Mekanizma hazır, politika
kanıtla dolar.

## Fail-closed

`project.yaml`'da `sap_profile` yok/boş/bilinmeyense: **yalnız `ping` register edilir.**
Yanlış profil varsayıp yanlış sisteme yazmaktansa tool yüzeyi kesilir (ADR 0010 kültürü).
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# profiles/*.yaml dosya adları = geçerli profil enum'u
GECERLI_PROFILLER = ("ecc", "s4_private", "s4_public", "btp_abap")

HEPSI = ("all",)


def aktif_profil() -> str | None:
    """`project.yaml` → `sap_profile`. Geçersiz/eksikse None (fail-closed sinyali)."""
    try:
        from utils.project_config import sap_profile  # type: ignore
        p = sap_profile()
    except Exception:
        return None
    if not p or p not in GECERLI_PROFILLER:
        return None
    return p


def uygun_mu(available_on: tuple, profil: str | None) -> bool:
    """Profil bilinmiyor VEYA enum-dışıysa HİÇBİR tool uygun değildir (fail-closed).

    ⚠ İlk sürüm `"all" in available_on` kontrolünü profil doğrulamasından ÖNCE yapıyordu:
    `uygun_mu(("all",), "uydurma")` → True. `aktif_profil()` zaten None döndürdüğü için
    üretimde tetiklenmiyordu, ama fonksiyonun değişmezi tutmuyordu — çağıran biri profili
    başka yerden verirse sessizce açılırdı. (2026-07-10 negatif testiyle yakalandı.)
    """
    if profil is None or profil not in GECERLI_PROFILLER:
        return False
    return "all" in available_on or profil in available_on
