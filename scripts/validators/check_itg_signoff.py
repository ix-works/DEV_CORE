#!/usr/bin/env python3
# ENFORCES: C-ITG-01, C-ITG-02, C-ITG-03, C-ITG-04  (ADR 0019 coverage binding)
"""check_itg_signoff.py — ITG S2 intake-artefaktı + mutabakat gate (ADR 0022, Faz-1).

S2 (kapsamlı) bir iş SAP-yazmasına geçmeden ÖNCE, intake-artefaktının üretildiğini VE
kullanıcı sign-off'unun alındığını deterministik doğrular. run_review task `itg_s2_signoff`
üzerinden çağrılır (artifact = intake-artefaktı .md yolu).

Kontroller (playbook/intake-triage.md S2 şeması):
  - MUTABAKAT satırında işaret [x]/[X] var mı (kullanıcı sign-off)?
  - Zorunlu alanlar dolu mu: KAPSAM, Etkilenen objeler, Prior-art, Kabul kriterleri.
  - Prior-art alanı boş bırakılamaz (bulundu:<ref> VEYA yok — aramayı mecbur kılar).

Bulgu varsa exit 1 (run_review BLOCKER → SAP-yazma YASAK). Temizse exit 0.
NOT (Faz-1): bu YARGI+deterministik-artefakt gate'idir; hangi işin S2 olduğunu ajan/lider
belirler (hook durum-tutmaz — ADR 0022). Faz-2 pre_tool_guard state-gate pilot-kanıtına bağlı.
"""
import argparse
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# Zorunlu alan başlıkları (intake-artefaktı şeması; büyük/küçük harf duyarsız, esnek eşleşme)
_ZORUNLU = [
    ("kapsam", re.compile(r"kapsam\s*:", re.I)),
    ("etkilenen objeler", re.compile(r"etkilenen\s+obje", re.I)),
    ("prior-art", re.compile(r"prior-?art\s*:", re.I)),
    ("kabul kriterleri", re.compile(r"kabul\s+kriter", re.I)),
]
_MUTABAKAT_ISARETLI = re.compile(r"mutabakat.*\[[xX]\]|\[[xX]\].*mutabakat|sign-?off.*\[[xX]\]", re.I)
_MUTABAKAT_SATIR = re.compile(r"mutabakat|sign-?off", re.I)
# Prior-art satırının DOLU olması: "bulundu" veya "yok" içermeli (boş bırakılamaz)
_PRIOR_ART_DOLU = re.compile(r"prior-?art\s*:.*\b(bulundu|yok|none|found)\b", re.I)


def main() -> int:
    ap = argparse.ArgumentParser(description="ITG S2 intake-artefaktı + mutabakat gate")
    ap.add_argument("artifact", help="intake-artefaktı .md yolu")
    args = ap.parse_args()

    p = Path(args.artifact)
    if not p.exists():
        sys.stderr.write(
            f"⛔ ITG-S2 SIGNOFF: intake-artefaktı bulunamadı: {args.artifact}\n"
            "S2 (kapsamlı) iş SAP-yazmasına geçmeden ÖNCE intake-artefaktı üretilmeli "
            "(playbook/intake-triage.md S2 şeması) + kullanıcı MUTABAKAT'ı alınmalı.\n")
        return 1

    text = p.read_text(encoding="utf-8", errors="replace")

    eksik = [ad for ad, rx in _ZORUNLU if not rx.search(text)]
    if eksik:
        sys.stderr.write(
            f"⛔ ITG-S2 SIGNOFF: intake-artefaktında zorunlu alan(lar) eksik: {', '.join(eksik)}.\n"
            "Şema: KAPSAM · Etkilenen objeler (canlı-doğrulanmış) · Prior-art · Kabul kriterleri (EARS). "
            "Bkz. playbook/intake-triage.md S2 intake-artefaktı.\n")
        return 1

    if not _PRIOR_ART_DOLU.search(text):
        sys.stderr.write(
            "⛔ ITG-S2 SIGNOFF: 'Prior-art' alanı boş/belirsiz — 'bulundu: <ref>' VEYA 'yok' "
            "yazılmalı (kurumsal-hafıza araması mecburi; ADR 0022 3-eksen). Referansı doğrula, "
            "yoksa 'yok' de.\n")
        return 1

    if not _MUTABAKAT_ISARETLI.search(text):
        durum = "MUTABAKAT satırı var ama işaretsiz" if _MUTABAKAT_SATIR.search(text) else "MUTABAKAT satırı yok"
        sys.stderr.write(
            f"⛔ ITG-S2 SIGNOFF: kullanıcı sign-off'u yok ({durum}). S2 işi build'e ancak "
            "'MUTABAKAT: [x]' (kullanıcı onayı) sonrası geçer (ADR 0022). Kullanıcıyla "
            "intake-artefaktını madde-madde mutabık kal, sonra işaretle.\n")
        return 1

    print(f"✓ ITG-S2 SIGNOFF: intake-artefaktı tam + MUTABAKAT işaretli ({p.name}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
