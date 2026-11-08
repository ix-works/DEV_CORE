# -*- coding: utf-8 -*-
"""cds_metin — CDS kaynak metni için yorum/string ayıklayıcının TEK KAYNAĞI (yalnız stdlib).

NEDEN AYRI MODÜL (DEV_CORE #410 / PR #412 düzeltme 4, 2026-11-08)
  `cds_kod_metni` önce `sap_adt_lib`'de yaşıyordu. `gen_field_table` (doküman üreticisi, yalnız
  stdlib) onu oradan import edince iki yan etki doğdu (bug-gate 4. tur, ölçüldü):
  ① `requests` / `urllib3` / `python-dotenv` olmadan araç AÇILMIYORDU · ② `sap_adt_lib`
  açılışta `.conn_adt`'yi bulup `ADT_SAP_*` kimlik bilgilerini süreç ortamına yüklüyordu (ağ ve
  yazma yok). Saf metin işlevi bağımlılıksız modülde durur; `sap_adt_lib` onu yeniden dışa
  açar (`sap_adt_lib.cds_kod_metni` çağrıları değişmez).
  ⛔ Bu modüle stdlib dışı import EKLEME — `cds_entity_baslik_kardesleri` G9/G10 bunu ölçer.
"""


def cds_kod_metni(metin, string_icerigini_koru=False):
    """CDS kaynağından yorumları atar: `//` ve `--` satır yorumları (satır sonu korunur) +
    `/* */` blok yorumu (tek boşluk olur). String ('..', `''` kaçışı) yorumdan ÖNCE tüketilir
    ⇒ string içindeki `//` / `--` / `/*` yorum SAYILMAZ.

    `string_icerigini_koru=False` (varsayılan): string yerine `''` bırakılır — anahtar sözcük /
    başlık araması YALNIZ kodda yapılsın diye. `True`: string olduğu gibi kalır (yalnız yorum
    atılır) — `@EndUserText.label: '…'` metnine ihtiyaç duyan tüketici için.
    Tüketiciler: `SAPADTClient._validate_cds_source` (Q277) · `populate_cds_views` RAP başlık
    tespiti (#410 K3, 2026-11-08: ham metinde arama yorumdaki `define view entity` /
    `define custom entity` ile klasik view'i RAP dalına düşürüyordu) · `gen_field_table`
    (`string_icerigini_koru=True`; #412 düzeltme 3). Kopyalama — buradan import et.
    """
    cikti = []
    i, n = 0, len(metin)
    while i < n:
        c = metin[i]
        if c == "'":
            j = i + 1
            while j < n:
                if metin[j] == "'":
                    if j + 1 < n and metin[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            cikti.append(metin[i:j + 1] if string_icerigini_koru else "''")
            i = j + 1
        elif metin.startswith('//', i) or metin.startswith('--', i):
            # `--` de CDS satır yorumudur (#412 düzeltme 2, bug-gate: canlı aktif bir CDS'te
            # `-- 601'in teslimat şartı …` satırı ölçüldü). Tanınmazsa yorumdaki `'` string
            # açar ve başlığı yutar. Kardeşlerle aynı normalizasyon:
            # `check_sap_active_version._yorumlari_siyir` ·
            # `check_cds_currency_reference.yorumu_kirp`/`blok_yorumu_maskele`. String
            # içindeki `--` yukarıdaki string dalında tüketilir, yorum SAYILMAZ.
            j = metin.find('\n', i)
            i = n if j < 0 else j
        elif metin.startswith('/*', i):
            j = metin.find('*/', i + 2)
            cikti.append(' ')
            i = n if j < 0 else j + 2
        else:
            cikti.append(c)
            i += 1
    return ''.join(cikti)
