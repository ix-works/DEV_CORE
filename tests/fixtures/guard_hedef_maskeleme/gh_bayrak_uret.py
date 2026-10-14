#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pre_tool_guard `_GH_BAYRAK_TABLOSU` üreticisi — gh'nin KENDİ yardım çıktısından (ağsız).

NEDEN: GH-HEDEF ve sızıntı gate'leri pflag modeliyle hangi bayrağın DEĞER aldığını bilmek
zorunda (`-t "--repo"` başlıktır, hedef değil). Tablo elle yazılmaz; gh sürümü değişince
bu betikle yeniden üretilip `scripts/hooks/pre_tool_guard.py`'ye yapıştırılır (yorumdaki
sürüm satırı da güncellenir). Bayat tablo GEVŞETME üretmez — tanınmayan bayrak/alt-komut
guard'da `kesin=False` olur (fail-closed); yeniden üretmenin amacı FP'yi azaltmaktır.

Kaynak: `gh help <grup> <alt>` çıktısının FLAGS + INHERITED FLAGS bölümleri. Tip sütunu olan
satır (`--title string`) = değer alır. `--repo` ve `--help` tabloya yazılmaz (guard ayrı ele
alır). Alt-komut listesi guard'ın `_GH_A`/`_GH_B` desenleriyle AYNI kümedir.

KULLANIM:  python tests/fixtures/guard_hedef_maskeleme/gh_bayrak_uret.py > tablo.txt
Çıktı:     ilk satır `# gh version …`, sonra sözlük gövdesi satırları. stderr'deki
           "bayrak bulunamadi" uyarıları bayraksız alt-komutlar için normaldir
           (gh 2.96.0: workflow enable/disable, repo deploy-key delete).
Bu betik test DEĞİLDİR (run_fixture_tests koşmaz); reçete: infra-test-recipes B82e.
"""
import re
import subprocess
import sys
import textwrap

KOMUTLAR = {
    "pr": ["create", "edit", "comment", "merge", "close", "reopen", "ready", "review"],
    "issue": ["create", "edit", "comment", "close", "reopen", "delete"],
    "release": ["create", "edit", "delete", "upload"],
    "secret": ["set", "delete"],
    "variable": ["set", "delete"],
    "workflow": ["run", "enable", "disable"],
    "ruleset": ["list", "view", "check"],
    "label": ["create", "edit", "delete", "clone"],
    "repo": ["create", "edit", "rename", "delete", "archive"],
    "repo deploy-key": ["add", "delete"],
}
SATIR = re.compile(r"^\s+(?:-(\w), )?--([\w-]+)(?: (\S+))?(?:\s{2,}|$)")


def main() -> int:
    surum = subprocess.run(["gh", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    print("# " + surum)
    tablo = {}
    for grup, altlar in KOMUTLAR.items():
        for alt in altlar:
            argv = ["gh", "help"] + grup.split() + [alt]
            r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                               errors="replace")
            bolum, degerli, bool_ = None, [], []
            for s in r.stdout.splitlines():
                if s.strip() in ("FLAGS", "INHERITED FLAGS"):
                    bolum = s.strip()
                    continue
                if s and not s.startswith(" "):
                    bolum = None
                if not bolum:
                    continue
                m = SATIR.match(s)
                if not m:
                    continue
                k, u, tip = m.groups()
                if u in ("repo", "help"):
                    continue
                (degerli if tip else bool_).append((k + ":" + u) if k else u)
            if not (degerli or bool_):
                print(f"# UYARI: {' '.join(argv)} bayrak bulunamadi rc={r.returncode}",
                      file=sys.stderr)
            anahtar = ("repo", "deploy-key " + alt) if grup.startswith("repo ") else (grup, alt)
            tablo[anahtar] = tuple(" ".join(sorted(x, key=lambda a: a.split(":")[-1]))
                                   for x in (degerli, bool_))
    for (g, a), alanlar in tablo.items():
        print(f'    ("{g}", "{a}"): (')
        for al in alanlar:
            parcalar = textwrap.wrap(al, 80, break_on_hyphens=False) or [""]
            for j, pc in enumerate(parcalar):
                son = " " if j < len(parcalar) - 1 else ""
                print(f'        "{pc}{son}"' + ("," if j == len(parcalar) - 1 else ""))
        print("    ),")
    return 0


if __name__ == "__main__":
    sys.exit(main())
