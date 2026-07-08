# -*- coding: utf-8 -*-
"""Genel doküman derleyici: markdown → şık tek-dosya HTML (mermaid render + figure-wrap + CSS).

Doğrudan `![](screenshots/..)` görselleri ve ```mermaid blokları olan herhangi bir doc (KD/FS/TS)
için. ZSD001'e özgü FIG/portal placeholder mantığı YOK (o build_kd_pdf.py'da). PDF ayrı adım:
  node scripts/html_to_pdf.js <html> <pdf>

Kullanım: python scripts/build_doc_pdf.py <girdi.md> <cikti.html> ["Doküman Başlığı"]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import markdown
from doc_tools import preprocess_mermaid_fences

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CSS = """
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
* { box-sizing: border-box; }
body { font-family: 'Segoe UI','Helvetica Neue',Arial,sans-serif; font-size: 10.5pt; color: #2b2b2b; line-height: 1.55; margin: 0; }
h1 { font-size: 23pt; color: #fff; background: linear-gradient(135deg,#0b4f8a,#1769b0); padding: 22px 24px; border-radius: 10px; margin: 0 0 18px 0; line-height:1.2; }
h2 { font-size: 15pt; color: #0b4f8a; border-bottom: 2px solid #0b4f8a; padding-bottom: 4px; margin: 26px 0 12px; page-break-after: avoid; }
h3 { font-size: 12.5pt; color: #1565a0; margin: 18px 0 8px; page-break-after: avoid; }
h4 { font-size: 11pt; color: #34556e; margin: 14px 0 6px; }
p, li { font-size: 10.5pt; }
a { color: #1769b0; text-decoration: none; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 9.6pt; page-break-inside: avoid; }
th { background: #0b4f8a; color: #fff; text-align: left; padding: 7px 9px; font-weight: 600; }
td { border: 1px solid #d0d7de; padding: 6px 9px; vertical-align: top; }
tr:nth-child(even) td { background: #f6f8fa; }
figure { margin: 16px 0; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; border: 1px solid #c3ccd6; border-radius: 6px; box-shadow: 0 2px 9px rgba(0,0,0,.13); }
figcaption { font-size: 9pt; color: #5a6b7b; font-style: italic; margin-top: 7px; padding: 0 8px; }
blockquote { border-left: 4px solid #4a90d9; background: #eef5fc; margin: 14px 0; padding: 10px 16px; border-radius: 0 6px 6px 0; }
blockquote h3 { margin-top: 0; color:#0b4f8a; }
code { background: #eef1f5; font-family: Consolas,monospace; font-size: 9.2pt; padding: 1px 5px; border-radius: 3px; }
pre { background: #f6f8fa; border: 1px solid #e1e6eb; border-radius: 6px; padding: 12px; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
hr { border: none; border-top: 1px solid #dfe5ec; margin: 22px 0; }
ul, ol { padding-left: 22px; }
strong { color: #1d3a52; }
"""


def build(md_path, html_path, title=None):
    md = open(md_path, encoding="utf-8").read()
    shot_dir = os.path.join(os.path.dirname(html_path), "screenshots")
    # ```mermaid → PNG
    md = preprocess_mermaid_fences(md, out_dir=shot_dir, rel_prefix="screenshots")
    body = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
    # <p><img></p> + <p><em>cap</em></p> → <figure><figcaption>
    body = re.sub(r'<p>(<img[^>]*?>)</p>\s*<p><em>(.*?)</em></p>',
                  r'<figure>\1<figcaption>\2</figcaption></figure>', body, flags=re.S)
    title = title or os.path.splitext(os.path.basename(html_path))[0]
    html = ('<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">'
            '<title>%s</title><style>%s</style></head><body>%s</body></html>' % (title, CSS, body))
    open(html_path, "w", encoding="utf-8").write(html)
    print("OK | <img>:", body.count("<img"), "| <figure>:", body.count("<figure>"))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("kullanım: python scripts/build_doc_pdf.py <girdi.md> <cikti.html> [başlık]")
        sys.exit(2)
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
