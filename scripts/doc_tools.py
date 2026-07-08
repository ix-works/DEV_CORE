# -*- coding: utf-8 -*-
"""Dokümantasyon araç katmanı — Mermaid (diyagram) + Marp (eğitim slaytı) ortak helper.

Tek yerde topladığımız "kanıtlı" çağrı bilgisi (2026-06-14 adoption, gerçek render ile doğrulandı):
  - mmdc (Mermaid CLI) puppeteer postinstall'ı bizde çalışmıyor → kendi Chromium'unu indirmez;
    bir sistem tarayıcısına yönlendirilir (puppeteer config executablePath).
  - marp --pdf/--pptx Chrome ile TAKILIR (kullanıcının açık Chrome profiliyle çakışma) →
    **Edge ile çalışır** (`--browser edge`). Bu yüzden varsayılan tarayıcı = Edge.
  - mmdc puppeteer config'te Windows yolu **forward-slash** ile yazılır (ters-eğik JSON escape kırar).

Kullanım (kütüphane):
    from doc_tools import preprocess_mermaid_fences, marp_build
    md = preprocess_mermaid_fences(md, out_dir=SHOT, rel_prefix='screenshots')  # ```mermaid → ![](png)
    marp_build('deck.md', 'pdf', 'deck.pdf')

Kullanım (CLI):
    python doc_tools.py mermaid girdi.mmd cikti.png
    python doc_tools.py marp deck.md pdf            # → deck.pdf (yanına)
    python doc_tools.py check                       # araç + tarayıcı durumu
"""
import os
import re
import sys
import json
import shutil
import subprocess
import tempfile

# Windows konsol: utf-8 (Türkçe print güvenli; std kural — bkz. feedback_powershell-utf8-bom-trap)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Global npm bin (mmdc/marp .cmd buradadır; PATH'te olmayabilir)
_NPM_BIN = os.path.join(os.environ.get("APPDATA", ""), "npm")

# Tarayıcı adayları — Edge ÖNCE (marp Chrome'da takılıyor, Edge temiz)
_BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser():
    """Kurulu bir Chromium-tabanlı tarayıcı yolu döndürür (Edge tercih). Yoksa None."""
    env = os.environ.get("DOC_TOOLS_BROWSER")
    if env and os.path.exists(env):
        return env
    for p in _BROWSER_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def _resolve_cli(name):
    """mmdc / marp gibi global npm CLI'sini bulur (.cmd dahil). PATH + APPDATA\\npm."""
    hit = shutil.which(name)
    if hit:
        return hit
    for ext in (".cmd", ".exe", ""):
        cand = os.path.join(_NPM_BIN, name + ext)
        if os.path.exists(cand):
            return cand
    return None


def _browser_for_marp():
    """marp --browser argümanı: edge / chrome (Edge tercih)."""
    b = find_browser() or ""
    return "edge" if "Edge" in b or "msedge" in b.lower() else "chrome"


# --------------------------------------------------------------------------- Mermaid

def render_mermaid(mmd_path, out_path, scale=2, background="white", theme="default"):
    """Tek bir .mmd dosyasını SVG/PNG'ye render eder. Çıktı yolu uzantısı formatı belirler.

    Döner: out_path (başarılı) — hata olursa RuntimeError.
    """
    mmdc = _resolve_cli("mmdc")
    if not mmdc:
        raise RuntimeError("mmdc bulunamadı. Kurulum: npm i -g @mermaid-js/mermaid-cli")
    browser = find_browser()
    cfg_path = None
    cmd = [mmdc, "-i", mmd_path, "-o", out_path, "-t", theme, "-b", background, "-s", str(scale)]
    if browser:
        # forward-slash ŞART (ters-eğik JSON escape'i kırar)
        cfg = {"executablePath": browser.replace("\\", "/"), "args": ["--no-sandbox"]}
        fd, cfg_path = tempfile.mkstemp(suffix=".json", prefix="mmdc-")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        cmd += ["-p", cfg_path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                           stdin=subprocess.DEVNULL)
    finally:
        if cfg_path and os.path.exists(cfg_path):
            os.remove(cfg_path)
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError("mermaid render başarısız:\n" + (r.stderr or r.stdout)[-600:])
    return out_path


def preprocess_mermaid_fences(md, out_dir, rel_prefix="screenshots", scale=2, prefix="diagram"):
    """Markdown içindeki ```mermaid ... ``` bloklarını render edip ![](png) ile değiştirir.

    Fence'in hemen ÜSTÜNDEki blockquote/italik satır figcaption olarak korunur (varsa caption
    olarak `*...*` eklenir). build_kd_pdf.py'ın <figure> sarma regex'iyle uyumludur.

    out_dir   : png'lerin yazılacağı klasör (ör. docs/screenshots)
    rel_prefix: markdown'da img src göreli ön-eki (ör. 'screenshots')
    Döner: değiştirilmiş md. Render edilemeyen blok DOKUNULMADAN bırakılır (uyarı stderr'e).
    """
    os.makedirs(out_dir, exist_ok=True)
    pat = re.compile(r"```mermaid[^\n]*\n(.*?)\n```[^\n]*\n?", re.S)
    counter = {"n": 0}

    def _sub(m):
        counter["n"] += 1
        idx = counter["n"]
        src = m.group(1)
        name = "%s-%02d.png" % (prefix, idx)
        out_png = os.path.join(out_dir, name)
        fd, mmd = tempfile.mkstemp(suffix=".mmd", prefix="mmd-")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(src)
        try:
            render_mermaid(mmd, out_png, scale=scale)
        except Exception as exc:  # render edilemeyen blok metin kalsın
            sys.stderr.write("[doc_tools] mermaid blok #%d render edilemedi: %s\n" % (idx, exc))
            return m.group(0)
        finally:
            if os.path.exists(mmd):
                os.remove(mmd)
        cap = "Şekil — Diyagram %d" % idx
        return "\n\n![%s](%s/%s)\n\n*%s*\n" % (cap, rel_prefix, name, cap)

    return pat.sub(_sub, md)


# --------------------------------------------------------------------------- Marp

def marp_build(md_path, fmt, out_path=None, theme=None, allow_local_files=True):
    """Marp markdown'ını PDF/PPTX/HTML'e çevirir. fmt: 'pdf' | 'pptx' | 'html'.

    PDF/PPTX için Edge kullanılır (Chrome takılma sorunu). Döner: out_path.
    """
    marp = _resolve_cli("marp")
    if not marp:
        raise RuntimeError("marp bulunamadı. Kurulum: npm i -g @marp-team/marp-cli")
    fmt = fmt.lower()
    if out_path is None:
        out_path = os.path.splitext(md_path)[0] + "." + fmt
    cmd = [marp, md_path, "--" + fmt, "-o", out_path]
    if fmt in ("pdf", "pptx"):
        cmd += ["--browser", _browser_for_marp()]
        if allow_local_files:
            cmd += ["--allow-local-files"]
    if theme:
        cmd += ["--theme", theme]
    env = dict(os.environ)
    browser = find_browser()
    if browser:
        env["CHROME_PATH"] = browser
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180,
                       stdin=subprocess.DEVNULL, env=env)
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError("marp build başarısız:\n" + (r.stderr or r.stdout)[-600:])
    return out_path


# --------------------------------------------------------------------------- CLI

def _check():
    print("== doc_tools durum ==")
    for cli in ("mmdc", "marp"):
        p = _resolve_cli(cli)
        print("  %-6s : %s" % (cli, p or "KURULU DEĞİL (npm i -g ...)"))
    b = find_browser()
    print("  tarayıcı: %s" % (b or "BULUNAMADI"))
    print("  marp --browser → %s" % _browser_for_marp())


def main(argv):
    if not argv or argv[0] == "check":
        _check()
        return 0
    cmd = argv[0]
    if cmd == "mermaid":
        if len(argv) < 3:
            print("kullanım: doc_tools.py mermaid girdi.mmd cikti.(svg|png)")
            return 2
        out = render_mermaid(argv[1], argv[2])
        print("OK:", out)
        return 0
    if cmd == "marp":
        if len(argv) < 3:
            print("kullanım: doc_tools.py marp deck.md (pdf|pptx|html) [cikti]")
            return 2
        out = marp_build(argv[1], argv[2], argv[3] if len(argv) > 3 else None)
        print("OK:", out)
        return 0
    print("bilinmeyen komut:", cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
