# -*- coding: utf-8 -*-
"""hook_shim.py — PROJE-LOKAL hook yönlendiricisi (D15 tavuk-yumurta çözümü).

NEDEN VAR: settings.json hook'ları doğrudan core/'a işaret etseydi, junction koptuğunda
kullanıcı yalnız kriptik "hook command failed" görürdü — kontrolü yapacak kod da kopuk
junction'ın arkasında kalırdı. Bu shim PROJE reposunda commit'lidir; core'u bulamazsa
NET hata + onarım komutu basar, bulursa gerçek hook'u AYNI SÜREÇTE (runpy — Ö2: +0 ms;
subprocess +86 ms/çağrı ölçülmüştü) çalıştırır.

Bilinçli mini kopya-artefaktı: tek işi yönlendirme; drift'i session_start D7 denetler.
Kullanım (settings.json): python ${CLAUDE_PROJECT_DIR}/scripts/hook_shim.py <hook_adi>
"""
import os
import runpy
import sys

SHIM_SURUM = "1.0"  # D7 drift-karşılaştırması bu sürümü okur


def proje_koku() -> str:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return env
    # shim <proje>/scripts/hook_shim.py konumunda yaşar
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    if len(sys.argv) < 2:
        print("hook_shim: hook adı eksik (kullanım: hook_shim.py <hook_adi>)", file=sys.stderr)
        return 1
    hook = sys.argv[1]
    kok = proje_koku()
    core = os.path.join(kok, "core")
    hedef = os.path.join(core, "scripts", "hooks", hook + ".py")

    if not os.path.isdir(core) or not os.path.isfile(hedef):
        print(
            "=" * 62 + "\n"
            "⛔ CORE JUNCTION KOPUK/EKSİK — guardrail'ler ÇALIŞMIYOR!\n"
            f"   Aranan: {hedef}\n"
            "   ONARIM:\n"
            "     python core/scripts/team_setup.py --repair-junctions\n"
            "   core/ tamamen yoksa (DEV_CORE clone'u eksik):\n"
            "     git clone <CORE_REPO_URL> <CORE_CLONE_DIR>  &&  team_setup.py\n"
            "   Bu oturumda SAP-YAZMA YAPMA (pre_tool_guard devre dışı olabilir).\n"
            + "=" * 62,
            file=sys.stderr,
        )
        return 1

    # Gerçek hook'u aynı süreçte çalıştır (stdin/stdout/stderr doğal geçer)
    sys.argv = [hedef] + sys.argv[2:]
    try:
        runpy.run_path(hedef, run_name="__main__")
    except SystemExit as e:  # hook'un kendi exit-code'u aynen dışarı
        return int(e.code or 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
