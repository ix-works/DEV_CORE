# -*- coding: utf-8 -*-
"""Eski duzen KD markdown -> sik tek-dosya HTML (gomulu ekran goruntuleri + CSS).

Yalniz FIG/portal yer tutuculu ESKI KD duzeni icindir. Genel KD/FS/TS yolu:
  python scripts/build_doc_pdf.py <girdi.md> <cikti.html> ["Baslik"] --pdf

KULLANIM
  python scripts/build_kd_pdf.py <girdi.md> <cikti.html> [--baslik "Dokuman Basligi"]
         [--md-yerinde-yaz] [--kirp-kaynak <dizin>] [--yardim-dizini <dizin>]

  <girdi.md>        placeholder'li KD markdown'i (okunur; varsayilan olarak YAZILMAZ)
  <cikti.html>      uretilecek HTML. Gorseller <cikti.html dizini>/screenshots altinda
                    aranir; ```mermaid bloklarinin PNG'leri de oraya yazilir.
  --baslik          HTML <title>. Verilmezse cikti dosya adinin govdesi (build_doc_pdf ile ayni).
  --md-yerinde-yaz  temizlenmis markdown'i <girdi.md> uzerine GERI YAZ (eski varsayilan).
  --kirp-kaynak     ham kd-*.png'lerin durdugu dizin; varsa beyaz kenari kirpilip
                    screenshots/ altina yazilir (eskiden proje kokunden SESSIZCE okunurdu).
  --yardim-dizini   uygulama-ici yardim kopyasi (webapp/help): kullanici-kilavuzu.html +
                    screenshots/ oraya senkronlanir; ardindan UI RE-DEPLOY gerekir
                    (eskiden project.yaml kd_help_dir dizini varsa SESSIZCE yazilirdi).

CIKIS KODLARI
  0  HTML uretildi  ·  --help/-h: yalniz kullanim basilir, HICBIR dosyaya dokunulmaz
  2  kullanim hatasi (eksik/bilinmeyen arguman, olmayan girdi, olmayan cikti/kirp/yardim
     dizini, girdi == cikti) -- yazmadan ONCE denetlenir, hicbir dosyaya dokunulmaz

Yazma hedefleri YALNIZ argumanlardan gelir; sessiz varsayilan hedef YOKTUR. (Vaka: arguman
okumayan eski surumde "yardim bakayim" diye kosulan `--help`, bir tuketici projenin kapali
paketindeki gorselleri yeniden yazdi -- iki kez. Agir import'lar arguman ayristirmasindan
SONRA yapilir: modulu import etmek ve `--help` hicbir sey yazmaz, PIL/markdown gerektirmez.)

KANITLI YONTEM (arastirma): markdown -> HTML -> PDF (Chromium/Playwright page.pdf).
Kritik: markdown KAYNAGI temiz olmali. Orijinal placeholder'lar ``` kod-blogu
ICINDEYDI (markdown ![](..) orada parse etmez) -> fence BLOGUNUN TAMAMINI resimle
degistiririz (icine degil). Dairesel callout numaralari (Secenek B) sadelestirilir.
PDF ayri adim: node scripts/html_to_pdf.js <cikti.html> <cikti.pdf>
"""
import os
import re
import sys


def _konsol_utf8():
    # Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
    # (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
    # Arguman ayristirmasindan ONCE: --help metni de non-ASCII tasir.
    for _akis in (sys.stdout, sys.stderr):
        try:
            _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def _arg_ayristir(argv):
    import argparse
    p = argparse.ArgumentParser(
        prog="build_kd_pdf.py",
        description="Eski düzen KD markdown -> HTML (FIG/portal yer tutucuları). "
                    "Yazma hedefleri yalnız argümanlardan gelir.",
        epilog="Çıkış: 0 HTML üretildi · 2 kullanım hatası (hiçbir dosyaya dokunulmaz). "
               "Genel KD/FS/TS yolu: scripts/build_doc_pdf.py.",
        allow_abbrev=False)
    p.add_argument("girdi_md", help="placeholder'lı KD markdown'ı (varsayılan: YAZILMAZ)")
    p.add_argument("cikti_html", help="üretilecek HTML; görseller <dizini>/screenshots altında")
    p.add_argument("--baslik", default=None,
                   help="HTML <title>; verilmezse çıktı dosya adının gövdesi")
    p.add_argument("--md-yerinde-yaz", action="store_true",
                   help="temizlenmiş markdown'ı girdi dosyasının üzerine geri yaz")
    p.add_argument("--kirp-kaynak", default=None, metavar="DIZIN",
                   help="ham kd-*.png dizini; kırpılıp screenshots/ altına yazılır")
    p.add_argument("--yardim-dizini", default=None, metavar="DIZIN",
                   help="uygulama-içi yardım dizini (webapp/help); HTML + screenshots senkronlanır")
    return p, p.parse_args(argv)


def _on_kontrol(p, a):
    """Yazmadan ONCE: her sorun kullanim hatasidir (exit 2), hicbir dosyaya dokunulmaz."""
    if not os.path.isfile(a.girdi_md):
        p.error("girdi md bulunamadı: %s" % a.girdi_md)
    cikti_dizin = os.path.dirname(os.path.abspath(a.cikti_html))
    if not os.path.isdir(cikti_dizin):
        p.error("çıktı dizini yok: %s" % cikti_dizin)
    if os.path.normcase(os.path.realpath(a.girdi_md)) == os.path.normcase(os.path.realpath(a.cikti_html)):
        p.error("girdi ve çıktı aynı dosya: %s" % a.girdi_md)
    if a.kirp_kaynak is not None and not os.path.isdir(a.kirp_kaynak):
        p.error("--kirp-kaynak dizini yok: %s" % a.kirp_kaynak)
    if a.yardim_dizini is not None and not os.path.isdir(a.yardim_dizini):
        p.error("--yardim-dizini yok: %s" % a.yardim_dizini)


def main(argv=None):
    _konsol_utf8()
    p, a = _arg_ayristir(sys.argv[1:] if argv is None else argv)
    _on_kontrol(p, a)

    # Agir import'lar burada: --help / kullanim hatasi PIL/markdown gerektirmez.
    import html as _html
    import shutil
    from PIL import Image, ImageOps
    import markdown
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from doc_tools import preprocess_mermaid_fences  # ```mermaid → render PNG → ![](..)
    # ⛔ `toc` eklentisi ZORUNLU — yoksa hicbir basliga id verilmez ve dokumandaki TUM
    #    "Icindekiler" baglantilari OLU olur (sessiz kusur: sayfa acilir, tiklama etkisiz;
    #    ne build ne tarayici uyarir). slug_tr = TR-farkindali id ureticisi: varsayilan slug
    #    Turkce harfi cevirmez SILER ("Kilavuz"->"klavuz") -> elle yazilan #kilavuz hedefsiz kalir.
    from build_doc_pdf import slug_tr  # tek kaynak (kopyalanmaz)

    MD = os.path.abspath(a.girdi_md)
    HTML = os.path.abspath(a.cikti_html)
    SHOT = os.path.join(os.path.dirname(HTML), 'screenshots')
    os.makedirs(SHOT, exist_ok=True)

    # --- gorselleri kirp (yalniz --kirp-kaynak verildiyse; dosya varsa) ---
    def trim(src, name):
        im = Image.open(src).convert('RGB')
        g = im.convert('L').point(lambda p: 0 if p < 242 else 255)
        bbox = ImageOps.invert(g).getbbox()
        if bbox:
            l, t, r, b = bbox
            im = im.crop((max(0, l-14), max(0, t-14), min(im.width, r+14), min(im.height, b+14)))
        im.save(os.path.join(SHOT, name), 'PNG')

    if a.kirp_kaynak is not None:
        for f in ['kd-01-liste', 'kd-02-liste-filtre-acik', 'kd-02b-liste-kalem-acik', 'kd-03-yarat',
                  'kd-04-yarat-notlar', 'kd-05-degistir', 'kd-06-toplu-ekle', 'kd-07-portal', 'kd-08-yarat-dolu']:
            src = os.path.join(a.kirp_kaynak, f + '.png')
            if os.path.exists(src):
                trim(src, f + '.png')

    md = open(MD, encoding='utf-8').read()

    def img(name, cap):
        return '\n\n![%s](screenshots/%s)\n\n*%s*\n' % (cap, name, cap)

    # 1) Ekran goruntuleri notu
    md = re.sub(
        r'> ### 📷 Ekran Görüntüleri Hakkında Önemli Not.*?sonradan gerçek uygulama resmi konulacaktır\.',
        '> ### 📷 Ekran Görüntüleri Hakkında\n>\n'
        '> Bu kılavuzdaki ekran görüntüleri uygulamanın **demo ortamından**, anlamlı örnek '
        'verilerle (ör. "ÖRNEK MÜŞTERİ A.Ş.", "FT-DIRSEK-90") alınmıştır. Canlı kullanımda '
        'ekranlar **birebir aynıdır**; yalnızca veriler sizin gerçek müşteri ve malzemelerinizdir.',
        md, flags=re.S)

    # 2) Fence BLOGU (```...[EKRAN GÖRÜNTÜSÜ: KEY ...]...```) -> resim(ler)  [fence DISINA]
    FIG = {
     'Liste ekranı':
        img('kd-01-liste.png', 'Şekil 1 — Liste ekranı. Üstte arama/Filtreler çubuğu, ortada sipariş listesi, sağ üstte Yeni Sipariş / Sipariş Değiştir / Sipariş Sil düğmeleri.'),
     'Liste — filtre dolu + Ara':
        img('kd-02-liste-filtre-acik.png', 'Şekil 2 — “Filtreler” başlığına tıklayınca arama alanları açılır (Satış Org., Kanal, Bölüm, Müşteri, Malzeme, Sipariş Durumu, Sipariş Sayısı). Doldurup “Ara” deyin.')
        + img('kd-02b-liste-kalem-acik.png', 'Şekil 3 — Bir siparişin solundaki oka tıklayınca o siparişin kalemleri açılır: Teslimat Adresi + malzeme tablosu. Aynı okla tekrar kapatabilirsiniz.'),
     'Sipariş Yarat ekranı':
        img('kd-03-yarat.png', 'Şekil 4 — Sipariş Yarat ekranı. Solda Başlık Bilgileri ve kalem tablosu, sağda Sipariş Özeti ile Bakiye / Fiyat Kodu. Başlıktaki zorunlu alanlar dolmadan kalem düğmeleri pasiftir.')
        + img('kd-04-yarat-notlar.png', 'Şekil 5 — “Notlar” başlığına tıklayınca üç not alanı açılır: Sipariş Notu 1, Sipariş Notu 2 ve İrsaliye Notu (her biri en çok 100 karakter).')
        + img('kd-05-degistir.png', 'Şekil 6 — Sipariş Değiştir ekranı. Düzen Yarat ile aynıdır; en üstte salt-okunur uyarı çubuğu vardır (siparişi başkası açmışsa uyarır).'),
     'Sipariş Yarat — kalem girilmiş + Fiyat Hesapla':
        img('kd-08-yarat-dolu.png', 'Şekil 7 — Kalemler girildikten sonra (örnekte Portal Devral ile gelen 3 kalem). “Fiyat Hesapla” çalıştırıldığında Malzeme Adı, Tutar, KDV ve Sipariş Özeti dolar.'),
     'Toplu Kalem Ekle penceresi':
        img('kd-06-toplu-ekle.png', 'Şekil 8 — Toplu Kalem Ekle penceresi. Excel’den 3 kolonu (Malzeme No, Müşteri Malzeme No, Miktar — TAB ayraçlı) yapıştırın. Her satırda Malzeme No VEYA Müşteri Malzeme No dolu olması yeterlidir.'),
    }
    miss = []
    for key, val in FIG.items():
        pat = re.compile(r'```[a-zA-Z0-9]*\n[^\n]*' + re.escape(key) + r'[^\n]*\n(?:[^\n]*\n)*?```[^\n]*\n?')
        md, n = pat.subn(lambda m: val, md)
        if n == 0:
            miss.append(key)

    # 3) Portal -> §5.6 basligindan sonra (IDEMPOTENT: resim zaten md'de ise tekrar EKLEME)
    anchor = '### 5.6 Portal siparişini devralmak için'
    if 'kd-07-portal.png' in md:
        pass  # zaten inline; tekrar enjekte etme (aksi halde her build'de birikir)
    elif anchor in md:
        md = md.replace(anchor, anchor + img('kd-07-portal.png',
            'Şekil 9 — Portal Siparişleri penceresi (“Portal Devral” ile açılır). Üstte portaldan gelen açık siparişler; bir siparişe tıklayınca altta o siparişin kalemleri görünür. “Devral” siparişi Yarat ekranına aktarır.'))
    else:
        miss.append('portal-anchor')

    # 4) Kalan dairesel numaralari madde etiketlerinden siyir (Secenek B)
    md = re.sub('[①②③④⑤⑥⑦⑧⑨⑩]\\s?', '', md)

    # 5) temiz markdown'i geri yaz (yalniz --md-yerinde-yaz; HTML bellekteki md'den uretilir)
    if a.md_yerinde_yaz:
        open(MD, 'w', encoding='utf-8').write(md)

    # 5b) ```mermaid bloklarini PNG'ye render et (varsa) -> ![](screenshots/diagram-NN.png)
    md = preprocess_mermaid_fences(md, out_dir=SHOT, rel_prefix='screenshots')

    # 6) md -> html
    body = markdown.markdown(md, extensions=['tables', 'fenced_code', 'sane_lists', 'toc'],
                             extension_configs={'toc': {'slugify': slug_tr}})

    # 7) <p><img></p> + <p><em>cap</em></p> -> <figure><figcaption>
    body = re.sub(r'<p>(<img[^>]*?>)</p>\s*<p><em>(.*?)</em></p>',
                  r'<figure>\1<figcaption>\2</figcaption></figure>', body, flags=re.S)

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
    title = a.baslik if a.baslik is not None else os.path.splitext(os.path.basename(HTML))[0]
    html = ('<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">'
            '<title>%s</title>'
            '<style>%s</style></head><body>%s</body></html>' % (_html.escape(title, quote=False), CSS, body))
    open(HTML, 'w', encoding='utf-8').write(html)

    # 8) Uygulama-ici yardim kopyasi (yalniz --yardim-dizini): header'daki "Kullanici Kilavuzu"
    #    dugmesi webapp/help/kullanici-kilavuzu.html acar (onOpenHelp); senkronlanmazsa uygulamadaki
    #    kopya bayatlar. NOT: senkron sonrasi UI BSP RE-DEPLOY gerekir (canlida gorunmesi icin).
    if a.yardim_dizini is not None:
        HELP = a.yardim_dizini
        open(os.path.join(HELP, 'kullanici-kilavuzu.html'), 'w', encoding='utf-8').write(html)
        hshot = os.path.join(HELP, 'screenshots')
        os.makedirs(hshot, exist_ok=True)
        for f in os.listdir(SHOT):
            if f.lower().endswith('.png'):
                shutil.copy2(os.path.join(SHOT, f), os.path.join(hshot, f))
        print('  -> yardim dizini senkronlandi: %s (UI RE-DEPLOY gerekir)' % HELP)

    print('OK | <img>:', body.count('<img'), '| <figure>:', body.count('<figure>'), '| eksik:', miss if miss else 'YOK')
    return 0


if __name__ == "__main__":
    sys.exit(main())
