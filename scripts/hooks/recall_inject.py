#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

Test (P/N): tests/fixtures/recall_inject/ + run_fixture_tests koşucusuna uygun
  echo '{"prompt":"..."}' | python scripts/hook_shim.py recall_inject
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

_TR = str.maketrans("İIıŞşĞğÜüÖöÇç", "iiissgguuoocc")
_STOP = {"ve", "ile", "icin", "bir", "bu", "da", "de", "the", "for", "and",
         "yok", "var", "olan", "her", "gate", "check", "yap", "olarak", "sonra"}
ESIK = 5          # min skor (başlık-token'ı 3 puan → tek güçlü eşleşme yetmez, 2+ ister)
TOP_K = 3
MIN_PROMPT = 40   # kısa prompt = selamlaşma/komut; recall gürültü olur


def _tokenle(s: str) -> set:
    s = s.translate(_TR).lower()
    return {t for t in re.findall(r"[a-z0-9_]{3,}", s) if t not in _STOP}


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    prompt = str(data.get("prompt") or "")
    if len(prompt) < MIN_PROMPT:
        return 0

    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    idx_p = proj / ".tmp" / "recall-index.json"
    if not idx_p.is_file():
        return 0
    try:
        kayitlar = json.loads(idx_p.read_text(encoding="utf-8")).get("kayit", [])
    except Exception:
        return 0

    q = _tokenle(prompt)
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
