---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: howto
applies-to: backend (classic dialog)
last-updated: 2026-08-18
status: active
purpose: Klasik Dynpro ekranı + GUI status'un ortak üreteç FM ile (SOAP-RFC, dialog context) üretilmesi — 16-parametrelik imza, donör seçimi, ekran alanı/buton üretimi, CUA merge, doğrulama protokolü
---

# HOW-TO — Klasik Dynpro Ekranı + GUI Status Üretimi (RFC, AI-otomatik)

> **Amaç:** Klasik bir ABAP programına (report/module pool) **Dynpro ekranı + GUI status + titlebar +
> (isteğe bağlı) app-toolbar butonları + ekran alanları** üretmek — operatöre SE51/SE41 GEREKMEDEN,
> tamamen AI/REST üzerinden. Bunu yapan üreteç: **`ZSD000_FM_SCREEN_GEN`** (RFC-enabled,
> FG `ZSD000_FG_SCREEN_GEN`), `/sap/bc/soap/rfc` (dialog) üzerinden çağrılır.
>
> **Bu dosya KOPYALANIP KOŞULABİLİR olacak şekilde yazılmıştır** (§1 tam zarf, §2.1 kanıtlı çağrı,
> §11 çalışan emsal program). Derin referans/iç mekanik: [`adt-fugr-functions.md`](adt-fugr-functions.md) §6.
> Üretimden önce: [`checklists/classic-dialog-creation.md`](checklists/classic-dialog-creation.md) §Faz 3 (CLC-SCR1..7).
> Alan/diyalog ekranına özel (DDIC bağlama, F4, çok-turlu CUA):
> [`howto-classic-dynpro-datafield-screens.md`](howto-classic-dynpro-datafield-screens.md).
>
> **Kanonik doğruluk kaynağı = FM'in KENDİ KAYNAĞI**
> (`<source_root>/SD/ZSD000_CLC/functions/ZSD000_FM_SCREEN_GEN.func.abap`, 1325 satır, canlıdan
> senkron). Bu dosyadaki `FM:<satır>` çapaları o sürüme aittir; satır numaraları kayabilir, yanına
> yazılan **grep çapası** kaymaz. §2'deki imza bloğu `check_fm_signature_doc_sync` gate'i ile
> kaynağa karşı OTOMATİK denetlenir (§13.2).

---

## 0. Ne zaman kullanılır

Klasik dialog programı (ALV liste, master-detail, header+liste, modal giriş formu) yazıyorsun ve
programın bir **ekrana (`CALL SCREEN`)** + **GUI status (PF-STATUS)** + **titlebar**'a ihtiyacı var.
RAP/Fiori değil, klasik SE80-tarzı program. ALV genelde bu ekrandaki bir container'a/docking'e bağlanır.

## 1. Neden SOAP-RFC, neden classrun DEĞİL (+ TAM ZARF)

`RPY_DYNPRO_INSERT` ve `RS_CUA_INTERNAL_WRITE` **dialog context** ister. `adt_classrun` ile çağırırsan
`400 "Session Timed Out"` alırsın. Çözüm: **RFC-enabled** FM'i **SOAP-RFC** kanalından çağır.

> ⚠️ `sap-language=TR` ile çağır (yoksa GUI metinleri Almanca/boş gelir — ADR 0005-D).

**Kopyalanabilir iskelet** (canlıda koşmuş bir script'ten alındı — `TABLES` satırlarının
`<item>` sarmalı ve alan sırası dahil):

```python
# python; kimlik/bağlantı core kütüphanesinden gelir (URL/kullanıcı GÖMÜLMEZ)
import sys; sys.path.insert(0, r"<CORE>\scripts")
import sap_adt_lib as L
c = L.SAPADTClient()

CALL = {                                  # skaler parametreler (istediğini ver, gerisi varsayılan)
    "IV_PROGRAM":     "Z____P_XXX",
    "IV_DYNPRO":      "0100",             # TAM 4 HANE (bkz. §2.4 rc=300)
    "IV_TITLE":       "<<KULLANICI>>",    # TR metin — AI UYDURMAZ (ADR 0005-D)
    "IV_SCREEN_TYPE": "DOCKING",          # DOCKING | CONTAINER
    "IV_MODE":        "WRITE",
    "IV_RECREATE":    " ",
    "IV_SRC_PROG":    "SAPLKKBL",         # ⭐ donör — §2.1'i OKUMADAN varsayılana bırakma
    "IV_SRC_STATUS":  "STANDARD",
    "IV_TRANSPORT":   "<AÇIK TR — kullanıcı/lider verir; YENİ TR AÇMA (ADR 0005-C)>",
}
FIELD_ORDER  = ["CONT_TYPE","CONT_NAME","NAME","TYPE","FORMAT","LENGTH","VISLENGTH",
                "LINE","COLUMN","TEXT","FROM_DICT","INPUT_FLD","OUTPUT_FLD",
                "REQU_ENTRY","POSS_ENTRY","MATCHCODE","CONV_EXIT","REF_FIELD","GROUP1"]
BUTTON_ORDER = ["FCODE","TEXT","ICON","QUICKINFO","FKEY"]
FIELDS, BUTTONS = [], []                  # §3 / §4

esc = lambda v: str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
inner   = "".join(f"<{k}>{esc(v)}</{k}>" for k, v in CALL.items())
fields  = "".join("<item>" + "".join(f"<{k}>{esc(f.get(k,''))}</{k}>" for k in FIELD_ORDER)  + "</item>" for f in FIELDS)
buttons = "".join("<item>" + "".join(f"<{k}>{esc(b.get(k,''))}</{k}>" for k in BUTTON_ORDER) + "</item>" for b in BUTTONS)
body = ('<?xml version="1.0" encoding="utf-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
        ' xmlns:urn="urn:sap-com:document:sap:rfc:functions"><soapenv:Body>'
        f'<urn:ZSD000_FM_SCREEN_GEN>{inner}'
        f'<IT_FIELDS>{fields}</IT_FIELDS><IT_BUTTONS>{buttons}</IT_BUTTONS>'
        '</urn:ZSD000_FM_SCREEN_GEN></soapenv:Body></soapenv:Envelope>')

# ⛔ YAZMADAN ÖNCE GUARD'LAR (payload yanlışsa CANLI ekran bozulur — hepsi ölçülmüş vakalardan):
assert "<IV_MODE>WRITE</IV_MODE>" in body
assert "<<" not in body, "placeholder KALDI — DUR"
r = c.session.post(f"{c.url}/sap/bc/soap/rfc?sap-client={c.client}&sap-language=TR",
                   data=body.encode("utf-8"),
                   headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
                   timeout=300)
print(r.status_code, r.text)              # <EV_RC> + <EV_MESSAGE> → §2.4 + §10
```

⚠️ **SOAP-RFC tuzağı — `TABLES` parametreleri istekte YER ALMAZSA DÖNMEZ.** Bir `TABLES`
parametresini okumak istiyorsan **boş etiketini bile göndermelisin** (`<STA></STA>…`). Aksi hâlde
cevap **HTTP 200 + boş tablo** gelir; *200 ≠ başarı* (ölçüldü 2026-08-18: eksik etiketlerle boş
cevap → etiketler eklenince 166 KB veri).

## 2. FM imzası (`ZSD000_FM_SCREEN_GEN`) — 16 parametre

> Aşağıdaki blok **makine-okunurdur**: `check_fm_signature_doc_sync` gate'i bu bloğu FM kaynağının
> imzasıyla karşılaştırır (§13.2). **Parametre eklerken/kaldırırken bu bloğu da güncelle** — yoksa
> gate `EKSİK`/`HAYALET` verir.

<!-- FM-IMZA: ZSD000_FM_SCREEN_GEN -->

| # | Parametre | Tip | Varsayılan | Anlam |
|---|---|---|---|---|
| 1 | `IV_PROGRAM` | `SCRHPROG` | — | Hedef program. **Z\*/Y\* ŞART** (§2.3, `EV_RC=301`) |
| 2 | `IV_DYNPRO` | `SCRFDYNNR` | `'0100'` | Ekran no — **tam 4 hane rakam** (§2.4 `rc=300`). Her şey buna göre dinamik |
| 3 | `IV_TRANSPORT` | `TRKORR` | opt | Transport (mevcut açık TR; **yeni TR açmak YASAK** — ADR 0005-C) |
| 4 | `IV_TITLE` | `RSMPE_TITT-TEXT` | `'Liste'` | Titlebar + dynpro açıklaması (TR) |
| 5 | `IV_SCREEN_TYPE` | `CHAR10` | `'DOCKING'` | `DOCKING` / `CONTAINER` (split = CONTAINER + kod). **`IT_FIELDS` ile DOCKING ŞART** (§4.4) |
| 6 | `IV_CC_NAME` | `SCRCNAME` | `'CC_ALV'` | Custom control adı (CONTAINER tipinde) |
| 7 | `IV_MODE` | `CHAR10` | `'WRITE'` | `WRITE`(üret) / `READ`(oku) / `DELETE`(`RS_SCRP_DELETE`) |
| 8 | `IV_RECREATE` | `CHAR1` | `' '` | `'X'` → mevcut ekranı sil+yeniden kur (alan/flow değişiminde ŞART) |
| 9 | **`IV_SRC_PROG`** | `SCRHPROG` | opt → **varsayılan donör** | **DONÖR program** (2026-08-14). Boş gelirse FM'in `c_def_src_prog` sabiti atanır (`FM:117`; minimal bir müşteri raporunun status'ü, `&F2..&F5`) — §2.1'i oku |
| 10 | **`IV_SRC_STATUS`** | `RSMPE_STA-CODE` | `'STATUS_0100'` | **DONÖR status kodu**. Donör+status ikilisi tutmazsa `EV_RC=120` |
| 11 | **`IV_CUA_MERGE`** | `CHAR1` | `'X'` | `'X'`=merge AÇIK (diğer status/titlebar KORUNUR) · `' '`/`'-'` = KAPALI (**SİLER**). Tanınmayan değer AÇIK bırakır + uyarır (§2.2) |
| 12 | **`IV_NAV_REMAP`** | `CHAR1` | `' '` | `' '`=OTOMATİK (yalnız legacy donörde) · `'X'`=ZORLA AÇ · `'-'`=ZORLA KAPA (§2.1/§2.2) |
| 13 | `EV_RC` | `I` | — | Sonuç kodu — **bantlar §2.4** |
| 14 | `EV_MESSAGE` | `STRING` | — | Tanı metni (donör · nav_remap · cua_merge · fields · DİKKAT satırları). **Kırpma!** (§2.2 sonu) |
| 15 | `IT_BUTTONS` | `ZSD000_TT_SCREEN_BUTTON` (TABLES) | opt | App-toolbar butonları — §3 |
| 16 | `IT_FIELDS` | `ZSD000_TT_SCREEN_FIELD` (TABLES) | opt | Ekran alanları — §4 |

<!-- /FM-IMZA -->

**Dinamik isimlendirme:** `IV_DYNPRO=<n>` → ekran `<n>`, flow modülleri `MODULE status_<n>` /
`user_command_<n>`, GUI status `STAT<n>`, titlebar `TIT<n>`, set kodları `PFK<n>`/`ACT<n>`/`B<n son 3>`.
**FM kodu ekran başına DEĞİŞMEZ** — sadece `IV_DYNPRO` değişir.

### 2.1 ⭐ TEMP-tarzı ekran üretme reçetesi (PAI'si `BACK`/`EXIT`/`CANCEL` bekleyen aile)

**Hangi aile:** `ZSD000_P_ALV_TEMP1/2/3/4` ve aynı ailedeki **beş** klasik rapor/diyalog programı —
hepsi `WHEN 'BACK' OR 'EXIT' OR 'CANCEL'` bekliyor (ölçüm 2026-08-17/18; tam liste FM
kaynağının imza notlarındadır). **Varsayılan donör programın** kendi PAI'si ise
`&F2`/`&F3`/`&F4`/`&F5` bekler — iki aile bir arada tek sabit kuralla yönetilemezdi,
bu yüzden anahtar çağırana bırakıldı.

✅ **KANITLI ÇAĞRI — donörü AÇIKÇA ver:**

```
IV_SRC_PROG = 'SAPLKKBL'      IV_SRC_STATUS = 'STANDARD'
IV_NAV_REMAP = ' '            (OTOMATİK: legacy donörde remap KENDİLİĞİNDEN açılır — FM:323
                               çapa `ELSE l_legacy_donor`; 'X' aynı sonucu verir, gerekmez)
IV_CUA_MERGE = (verme → 'X')  IV_MODE = 'WRITE'   IV_RECREATE = ' '
```

**Neden kanıtlı (canlı veri, çıkarım değil — ölçüm 2026-08-18 `RS_CUA_INTERNAL_FETCH`):**
- TEMP1/2/3'ün canlı status'ü `INT_NOTE='Standard for General List Output'` taşıyor — bu
  `SAPLKKBL/STANDARD`'ın **kendi iç notudur** ve FETCH/WRITE onu kopyalar ⇒ bu ekranlar legacy
  donörden üretilmiştir. (Varsayılan donörün notu farklıdır — kendi ekranının adını taşır.)
- Profil eşleşiyor: TEMP1/2/3 → `FUN 185/186/187` · `PFK 865/866/867` · `ACT 116/117`
  (legacy donörün "180+ bloat" imzası). Varsayılan (minimal) donörde `FUN 4` · `PFK 4` · **`ACT 0`**.
- Remap uygulanmış hâli canlıda görünüyor: üçünde de `pfno 03→BACK`, `12→CANCEL`, `15→EXIT`.

**🔎 DOĞRULAMA SİNYALİ (her koşumda BAK):** `EV_MESSAGE` içinde
**`nav_remap=ON(F3/Sh+F3/F12->BACK/EXIT/CANCEL)`** görünmeli (`FM:1264`).
**`nav_remap=OFF…` görünüyorsa ÇAĞRI YANLIŞTIR** — donör parametreleri gitmemiştir; **ekranı
kullanmadan önce çağrıyı düzelt** (o tur yanlış fcode üretmiştir).

⛔ **Varsayılanlarla üretme:** `IV_SRC_PROG` boş bırakılırsa **varsayılan (minimal) donör**
devreye girer (adı FM kaynağındaki `c_def_src_prog` sabitindedir — `FM:117`), fcode'ları
`&F2..&F5` gelir ve `WHEN 'BACK'` bekleyen PAI onları **yakalamaz** (buton görünür, tepkisiz).
⛔ **`IV_SRC_PROG=<hedefin kendisi>` seçenek DEĞİL:** üretilen status adı `STAT<dynnr>`,
`IV_SRC_STATUS` varsayılanı ise `STATUS_0100` — tutmaz → `EV_RC=120` ("donör status bulunamadı",
hiçbir şey yazılmaz). Kaynağın kendisi dururken kopyanın kopyası zaten gereksizdir.

⚠ **ALTERNATİF (varsayılan donör + `IV_NAV_REMAP='X'`) — HÂLÂ ÖLÇÜLMEDİ, kabul kriteri
değildir.** Ölçülen: varsayılan donörün `STATUS_0100`'ünde slotlar MEVCUT (`03→&F2 · 05→&F5 · 12→&F4 · 15→&F3`) ⇒ remap
4'ten 3'ünü yeniden yazardı. **Ama** o donörün `ACT` tablosu **BOŞ (0 satır)** iken `STA-ACTCODE`
dolu (`000001`); FM'in `l_setcode_miss` guard'ı `STA`'nın **ALANINA** bakar, **tabloya değil**
(`FM:809/818`) ⇒ bu yolda **uyarı vermez** ve status boş bir `act` havuzuyla kalabilir (00256
riski). **[ÖLÇÜLMEDİ]** runtime sonucu. *"Muhtemelen çalışır" yazma* — denenecekse ayrı bir test
programında denensin ve sonuç buraya işlensin.

### 2.2 Davranış anahtarları — FAIL-CLOSED polarite (İKİ AYRI DAVRANIŞ, karıştırma)

Değerler önce **BÜYÜK HARFE normalize** edilir (`FM:273`), sonra beyaz listeye bakılır:

| Gönderilen | `IV_CUA_MERGE` sonucu | `EV_MESSAGE` |
|---|---|---|
| `'X'` / `'x'` | merge **AÇIK** (tanınır) | uyarı **YOK** |
| `' '` (boş) veya `'-'` | merge **KAPALI** → diğer status/titlebar **SİLİNİR** | `cua_merge=KAPALI(...)` |
| `'J'` / `'1'` / başka | merge **AÇIK KALIR** (koruyucu) | `DIKKAT: IV_CUA_MERGE taninmayan deger … merge KAPATILMADI` |

`IV_NAV_REMAP` aynı normalizasyondan geçer: `'X'`=zorla aç · `'-'`=zorla kapa · `' '`=otomatik ·
**tanınmayan** (`'q'` gibi) → OTOMATİK'e düşer **+** `DIKKAT: IV_NAV_REMAP taninmayan deger` (`FM:283`).
⇒ *"Açmak için gönderdim ama kapandı"* sınıfı sessiz yıkım kapatılmıştır (2026-08-18 fix).

⚠ **`EV_MESSAGE`'ı KIRPMA.** Ölçülen uzunluklar: guard mesajı **266** · `'x'` **270** · `'J'` **435**
· `'q'` **394** · ikisi birden **559** karakter. `EV_MESSAGE[:400]` gibi bir kırpma (repo'da 5
script'te ölçüldü) **tanıyı düşürür** — `DIKKAT:` satırları mesajın SONUNDADIR.

### 2.3 Z/Y guard (`EV_RC=301`) — ADR 0005-A

`IV_PROGRAM` `Z*`/`Y*` ile başlamıyorsa FM **hiçbir şey yazmadan** `EV_RC=301` ile döner
(`FM:248-258`, çapa `IV_PROGRAM Z/Y KORUMASI`). Guard **`IV_MODE` dallarından ÖNCE**dir —
`READ` dahil her mod kapsanır (bilinçli karar: FM RFC ile dışarıdan çağrılabilir; sıkı guard
geri alınabilir, gevşek guard standart objeye yazma riskidir).
**Donör (`IV_SRC_PROG`) bu kurala TABİ DEĞİL** — yalnızca OKUNUR, bu yüzden `SAPLKKBL` meşrudur.
⚠ Namespace'li ad (`/ABC/ZFOO`) bugün guard'a **takılır** (`301`) — proje kuralı Z/Y olduğu için
risk yok; gerekirse guard o gün genişletilir.

⛔ **Guard'ı denerken VAR OLMAYAN bir ad kullan** (ör. `XX_GUARD_PROBE`). Gerçek bir standart
program adıyla test etmek, guard çalışmıyorsa **standart objeyi bozar**.

### 2.4 `EV_RC` bantları

| Bant | Anlam |
|---|---|
| `0-18` | Bileşik: `l_screen_rc`(0-10, `RPY_DYNPRO_INSERT` OTHERS=10) + status(0-3) + generate(0-5) |
| `5` | **`IT_FIELDS` ön-doğrulaması** — ekran YARATILMADI, kusurlu alan adları mesajda (§4.5) |
| `101-113` | Donör CUA fetch hatası (`100+subrc`, `FM:717`) + screen rc |
| `120-130` | Donör **status satırı** yok (`FM:754`) — CUA'ya HİÇBİR ŞEY yazılmadı, mevcut korundu |
| `202-213` | Merge fetch hatası (`200+rc`, `FM:1085`) |
| `300` | `IV_DYNPRO` geçersiz (4 hane rakam değil) — hiçbir adım koşmadı (`FM:342-349`) |
| `301` | **Z/Y guard** (§2.3) — hiçbir adım koşmadı |

> Bantlar **aralıktır** çünkü sonuç daima `l_screen_rc` ile TOPLANIR. Taban `110` bilerek
> SEÇİLMEMİŞTİR (110..120 donör-fetch bandına binerdi → yanlış teşhis).

## 3. `IT_BUTTONS` — app-toolbar üretimi

Satır alanları (bu sırayla gönderilir): `FCODE` · `TEXT` · `ICON` · `QUICKINFO` · `FKEY`.

- ⚠ **`FKEY`'i BOŞ bırak.** FM, donör status'ün `MAX(pfno)`+sıra mantığıyla **çakışmayan** bir slot
  seçer. Sabit tuş vermek donör `pfk` girdileriyle çakışabilir — **denenmedi**, riske girme.
- ⚠ **HER `WRITE` çağrısı hedef status'ün toolbar'ını (`but`) sıfırdan kurar** → o statüsün
  **TÜM** butonları her çağrıda verilmelidir; payload'da olmayan buton **düşer**
  (ayrıntı + ölçülmüş regresyon: datafield howto §3.2).
- Verilen her `FCODE` için programın PAI'sinde bir `CASE` dalı olmalı — yoksa toolbar'da
  **tepkisiz buton** kalır (canlı örnek: TEMP3'ün `&BTN_REFRESH`'i).
- **Ne zaman ALV-toolbar yerine app-toolbar:** butonun "etkin/pasif" koşulu varsa app-toolbar
  (`SET PF-STATUS … EXCLUDING` ile tek yerden yönetilir).

## 4. `IT_FIELDS` — ekran alanı üretimi (giriş/etiket/checkbox/radio)

Satır tipi `ZSD000_S_SCREEN_FIELD`; alan adları **`RPY_DYFATC` ile birebir aynıdır**
(FM `MOVE-CORRESPONDING` ile aktarır — dönüşüm/tahmin yok). Canlıda koşmuş çağrının alan sırası
§1'deki `FIELD_ORDER` listesidir.

**Geçerli `TYPE` değerleri:** `TEXT` `TEMPLATE` `RADIO` `CHECK` `FRAME` `FRAME_TMPL` `PUSH`
`PUSH_TMPL` `INFOBUTTON` `OKCODE` (kaynak: `LSIFPF11 i_check_field`). `TYPE` boş → **`TEMPLATE`**.

### 4.1 ⭐ ETİKET KURALI (2026-08-18 canlı sonda ile ölçüldü — geçici ekran, sonra silindi)

1. **Bir GİRİŞ alanı `FROM_DICT='X'` ile bile KENDİ ETİKETİNİ GETİRMEZ.**
   Ölçüm: `VBAK-ERDAT` + `FROM_DICT='X'`, `TEXT` elemanı yok → yalnız giriş alanı üretildi
   (`fDATS len010`), **etiket üretilmedi**.
2. **Her etiket AYRI bir `TYPE='TEXT'` satırıdır** — ama metni **elle yazmak gerekmez**:
   TEXT satırına `FROM_DICT='X'` ver, **`TEXT`'i BOŞ bırak** → metin DDIC'ten gelir
   (ölçüm: `VBAK-ERNAM` → `"Yaratan"`). ⇒ **ADR 0005-D dostu**: onlarca etiketi AI uydurmaz.
3. ⚠ **`TEXT` satırını unutmak SESSİZ kusurdur** — FM uyarı VERMEZ (etiketsiz giriş alanı meşru
   bir kullanımdır). Alan sayısını değil **etiket/alan çiftlerini** say.

### 4.2 DDIC'ten gerçekten ne gelir (`FROM_DICT='X'`)

| Gelen | Kanıt |
|---|---|
| Alan **uzunluğu** | payload'da kısa gönderilse bile canlı ekran DDIC `OUTPUTLEN`'e çıktı |
| `CONV_EXIT` (ör. `ALPHA`, `MATN1`) | canlı payload satırı |
| **F4 arama yardımı** | canlı doğrulandı: `VBAK-VBELN` → *"128 Girisler bulundu"* |
| Etiket metni | yalnız `TYPE='TEXT'` + `FROM_DICT='X'` + `TEXT` BOŞ iken (§4.1/2) |

Alan **adı** DDIC bağlaması için `<YAPI>-<ALAN>` biçiminde `NAME`'e yazılır
(ör. `NAME='ZSD001_S_DLG-MATNR'`, `TYPE='TEMPLATE'`, `FROM_DICT='X'`, `MATCHCODE` **BOŞ**).
Program tarafında work area adı yapı adıyla aynı olmalıdır (`DATA zsd001_s_dlg TYPE zsd001_s_dlg.`).

### 4.3 Giriş/çıkış varsayılanı — `io_default`

`TYPE='TEMPLATE'` + `INPUT_FLD`/`OUTPUT_FLD` **ikisi de boş** ise FM alanı **GİRİŞ+ÇIKIŞ**'a açar
(`FM:646-651`) ve kaç satıra uygulandığını `EV_MESSAGE`'a yazar: `fields=N io_default=M`.
Salt-okunur isteniyorsa `OUTPUT_FLD='X'` tek başına **ya da** `REQU_ENTRY='N'` ver.

### 4.4 Kısıtlar

- **`IV_SCREEN_TYPE='DOCKING'` ŞART.** `CONTAINER` modunda `CC_ALV` tüm ekranı kaplar
  (1..200 / 1..255) → koka konan her alan çakışır → `rc=6`. FM bu kombinasyonda `EV_MESSAGE`'a
  `DIKKAT: CONTAINER modu + IT_FIELDS` yazar (`FM:1321`).
- **`element_of` GÖNDERİLMEZ** (yapıda böyle bir alan yok; SAP INSERT sırasında kendisi atar —
  okumada `el=SCREEN` görünmesi bunun sonucudur, geri yazılırsa `rc=6`).
- Kök container (`SCREEN`/`SCREEN`) satırını **FM kendisi ekler** (`c_cont_root='SCREEN'`);
  eskiden "DOĞRULANMADI" şerhi vardı — **2026-08-18'de canlı üretimle ÖLÇÜLDÜ, kabul ediliyor**.
- `MATCHCODE` **BOŞ** (elle matchcode DDIC attachment'ının önüne geçer — datafield howto §2.2).
- **`SELECT-OPTIONS` kapsam dışıdır** (bilinçli): tek select-option ekranda 6 ayrı F2C satırı
  ister (`TEXT`/`OPTI_PUSH`/`LOW`/`TO_TEXT`/`HIGH`/`VALU_PUSH`); isteyen çağıran 6 satırı kendisi verir.
- **`PROCESS ON VALUE-REQUEST` (POV) üretilmez** — flow daima 2 modüldür. Veriye bağlı F4 için
  telafi: buton + `REUSE_ALV_POPUP_TO_SELECT` (datafield howto §2.4).

### 4.5 Negatif doğrulama ÇALIŞIYOR (`EV_RC=5`)

FM, alan verildiğinde **INSERT'ten önce** üç kusur sınıfını toplar ve **hiçbir şey yazmadan**
döner (`FM:549-601`) — yarım ekran yok:

| Kusur | Neden sert red |
|---|---|
| `LINE`/`COLUMN` boş (OKCODE hariç) | RPY gürültülü reddeder ama **hangi alan** olduğunu söylemez |
| `TEMPLATE`'te `LENGTH` **ve** `FROM_DICT` yok | RPY sessizce **0 genişlikli** kullanılamaz alan üretir |
| `CONT_NAME` dolu ama container yok (orphan) | RPY **tamamen sessiz** yutar, `rc=0` döner (sahte-OK) |

Mesajda **kusurlu alanların HEPSİ** listelenir (ilk hatada durmaz).

## 5. CUA merge (`IV_CUA_MERGE`)

CUA **program geneline** aittir: `RS_CUA_INTERNAL_WRITE` programın **TÜM** CUA'sını değiştirir
(delta DEĞİL). Bu yüzden FM, yazmadan önce mevcut CUA'yı okuyup yeni status'ün yanına **ekler** →
aynı programda `0100 + 0200 + 0300` birlikte yaşar. Her dynpro kendi set kodlarını alır
(`PFK<n>`/`ACT<n>`/`B<n>`).

**`EV_MESSAGE`'da dört durum AYRI raporlanır** (`FM:1271-1290`):

| Çıktı | Anlamı |
|---|---|
| `cua_merge=ok kept_status=N kept_title=M` | merge koştu, N status + M titlebar korundu |
| `cua_merge=none(programin onceden CUA'si yoktu -- ilk uretim, normal)` | ilk üretim |
| `cua_merge=KAPALI(IV_CUA_MERGE='…' verildi -> … SILINDI)` | çağıran kapattı — **yıkıcı** |
| `cua_merge=KOSMADI(donör CUA fetch basarisiz …)` | status adımına hiç girilmedi |

⛔ **`IV_CUA_MERGE=' '` GERÇEKTEN SİLER** — canlı kanıt (2026-08-18 kontrollü karşıt test):
`STAT`/`TIT` silindi, `FUN 186→185`, `BUT 1→0`; sonraki turda onarıldı.
ℹ Çok ekranlı programda merged sürüm ekrana **özel** `PFK<n>`/`ACT<n>` yazar (set-kodu çakışmasını
önler); eski sürüm donörün **tüm havuzunu** kopyalıyordu — **regresyon değil, bilinçli temizlenme**.

## 6. Layout tipleri

| Tip | Ne zaman | Nasıl |
|---|---|---|
| **DOCKING** (default) | Tam-ekran tek ALV liste · **alan ekranı (`IT_FIELDS`)** | `containers` boş; programda `cl_gui_docking_container` |
| **CONTAINER** | ALV'yi belirli yer/boyutta, header+liste, çoklu kontrol | 1 custom control (`CC_ALV`); programda `cl_gui_custom_container( container_name='CC_ALV' )` |
| **SPLIT** | Master-detail (üst/alt liste) | **AYRI tip DEĞİL** → `CONTAINER` üret + programda `cl_gui_splitter_container` |

### ⭐ CONTAINER üretiminde KANITLANMIŞ değerler (FM otomatik kullanır)

| Alan | Değer | Neden |
|---|---|---|
| Screen `lines`/`columns` | **200 / 255** | Küçük boyut → ALV kırpılır |
| CUST_CTRL `element_of` | **BOŞ** | Açık `'SCREEN'` → `illegal_field_value` (rc=6) |
| `line`/`column` · `height`/`length` | `1`/`1` · **200/255** | Tam ekran |
| `c_resize_v`/`c_resize_h` | **`'X'`/`'X'`** | ⚠️ ZORUNLU — yoksa control SABİT, ALV pencereyi doldurmaz |
| `c_line_min`/`c_coln_min` | `1`/`1` | Min satır/kolon |

```abap
" SPLIT — FM özel bir şey yapmaz, bölme PROGRAMDA:
go_split = NEW cl_gui_splitter_container( parent = go_cc rows = 2 columns = 1 ).
go_top   = go_split->get_container( row = 1 column = 1 ).
go_bot   = go_split->get_container( row = 2 column = 1 ).
```
Örnek: `ZSD000_P_ALV_TEMP3` (üst VBAK / çift-tık → alt VBAP). **Ekrana 2. container KOYMA.**

## 7. GUI status reçetesi — toolbar/menü temizliği (KRİTİK)

FM, donör status'ü alıp şöyle sadeleştirir:

- ✅ **`men`/`mtx` (menü) + `but` (app toolbar) REFRESH** → görünür menü+toolbar gider.
- ✅ **`act` (fonksiyon geçerlilik listesi) KORUNUR.**
- ⛔ **`act`/`actcode` TEMİZLENMEZ** → temizlersen BACK/EXIT/CANCEL **geçersiz** olur → runtime
  **`00256 "Geçerli bir işlev seçin"`** (buton tepkisiz). *(Bu hata 3-4 kez patinaja yol açtı.)*
- ✅ `tit` REFRESH → yalnız `TIT<n>` (title'lar status'tan bağımsız → güvenli prune).
- ✅ `pfk` re-map (**yalnız remap AÇIKSA** — §2.1): `03`→`BACK`, `15`→`EXIT`, `12`→`CANCEL` (`FM:856`).
- ✅ BACK/EXIT/CANCEL `fun-type` → **NORMAL'e zorla**; donör `EXIT type='E'` gelir, `AT EXIT-COMMAND`
  modülü yoksa komut işlenmez.
- ✅ **WRITE sonrası `RS_CUA_GENERATE` ŞART** — yoksa runtime **`00264 "GUI status not generated"`**.
- ⚠ Donör status'ünde `pfk`/`act` **set kodu** yoksa FM `DIKKAT: donör status'te set kodu YOK` yazar
  (`FM:1295`). ⚠ Bu guard `STA` **alanına** bakar, **tabloya değil** (§2.1 sonundaki varsayılan-donör notu).

## 8. ESC / çıkış

Nav fonksiyonları NORMAL type + `user_command_<n>` (`CASE sy-ucomm WHEN BACK/EXIT/CANCEL`).
**ESC = F12 = CANCEL** → `user_command` yakalar. *(type='E' + `AT EXIT-COMMAND` yolu DENENDİ ve
başarısız: üretilen ekranda OK command-field yok.)*
⛔ Programa `exit_command_<n>` modülü **KOYMA** — üretilen FLOW'da `AT EXIT-COMMAND` satırı yoktur,
o modül hiç çağrılmaz (TEMP1/2'de duran ölü koddur; TEMP4 taşımaz).

## 9. READ / RECREATE / DELETE modları

- **`IV_MODE='READ'`** → yazmadan dynpro header/container/`F2C` + CUA `TITLES`/`FUN`/`FUNDTL`/`FLOW`
  dökümü verir (denetim; §10'un asıl aracı).
- **`IV_RECREATE='X'`** → `RS_SCRP_DELETE` + INSERT. `RPY_DYNPRO_INSERT` overwrite ETMEZ
  (`already_exists` rc=2) ⇒ **alan/flow değişiminde ŞART**.
- **`IV_MODE='DELETE'`** → `RS_SCRP_DELETE` (`RPY_DYNPRO_DELETE` YOKTUR).
- ⚠️ DELETE sonrası INSERT patlarsa ekran kaybolur → INSERT değerlerini önce doğru bil.

## 10. Doğrulama protokolü (PATTERN #22)

⛔ **`TITLES=` / `FUN=` SAYAÇLARI KÖRDÜR.** Fonksiyon TANIMLARI silinmediği için etiket/quickinfo
kaybında bu sayaçlar **değişmez**. Sayaç "her şey yolunda" der.

✅ **Yapılacak:** `IV_MODE='READ'` çıktısındaki **`[FN:` dökümünü** tur-başı ↔ final **diff'le**
(kod + metin + ikon + quickinfo taşır). Ölçülmüş örnek: 0200'e yazımdan önce/sonra **185→185, kayıp 0**.

✅ **CUA içeriği RFC ile DOĞRUDAN OKUNABİLİR** (2026-08-18 ölçümü — eski *"EUDB ikili cluster,
okunamaz"* hükmü DÜŞTÜ): `RS_CUA_INTERNAL_FETCH` → `TFDIR-FMODE='R'`.

```python
TABS = ['STA','FUN','MEN','MTX','ACT','BUT','PFK','SET','DOC','TIT','BIV']   # 11 etiket ŞART
tabs = ''.join(f'<{t}></{t}>' for t in TABS)      # BOŞ etiket gönderilmezse TABLO DÖNMEZ
body = (f'<urn:RS_CUA_INTERNAL_FETCH><PROGRAM>{prog}</PROGRAM>'
        f'<LANGUAGE>T</LANGUAGE><STATE>A</STATE>{tabs}</urn:RS_CUA_INTERNAL_FETCH>')
```

⚠ **Yapısal güvence (aynı ölçüm):** 20 `RS_CUA_INTERNAL*` FM'i içinde `FMODE='R'` olan **yalnız
`_FETCH`**; `_WRITE`/`_GENERATE`/`_RESET`/`_PREPARE_TABLES`/`_TRANSFORMATION` → `null`
⇒ **RFC'den CUA OKUNUR, YAZILAMAZ.** (Pozitif kontrol: `RFC_READ_TABLE` → `R`.)

**Tur sonu kontrol listesi:** `EV_RC` bandı (§2.4) · `nav_remap=ON/OFF` (§2.1) ·
`cua_merge=…` (§5) · `fields=N io_default=M` (§4.3) · `[FN:` diff (kayıp 0) ·
`DIKKAT:` satırı var mı · ekranı **çalıştır** (00256/00264 yalnız runtime'da görünür).

## 11. Çalışan emsal: `ZSD000_P_ALV_TEMP4` (193 satır, üç yolu tek programda gösterir)

| Ekran | Çağrı | Gösterdiği |
|---|---|---|
| `0100` | `DOCKING` | TEMP1 profili (container=1, header 020/120, BUT=0) |
| `0200` | `CONTAINER` + `IV_CC_NAME='CC_ALV'` + `IT_BUTTONS` | TEMP2/3 profili + buton yolu |
| `0300` | `DOCKING` + `IT_FIELDS` | alan ekranı (ALV yok) |

⚠ **Klasik `FORM … USING` ALT-SINIF referansını KABUL ETMEZ** (ölçüldü 2026-08-18:
`cl_gui_docking_container` → `TYPE REF TO cl_gui_container` *"actual parameter incompatible"*).
**Upcast yalnız ATAMA ile olur** — ortak üst-sınıf referansı global değişkende taşınır:

```abap
DATA: go_docking TYPE REF TO cl_gui_docking_container,
      go_cc      TYPE REF TO cl_gui_custom_container,
      go_parent  TYPE REF TO cl_gui_container.        " ortak üst-sınıf
...
go_parent = go_docking.        " upcast (atama ile) → PERFORM show_alv. ortak yol
```

TEMP4'ün PAI'si nav-remap'in çalışıp çalışmadığını **görünür** kılar (donör fcode gelirse
`MESSAGE 'NAV REMAP YOK — donör fcode geldi'`) — yeni ekran üretirken bu deseni kopyalamak
teşhisi bir tura indirir.

## 12. Tuzaklar (hızlı referans)

| Belirti | Sebep / Çözüm |
|---|---|
| Butonlar/F3 tepkisiz, ekranda `&F2..&F5` fcode'ları | Varsayılan (minimal) donör gelmiş → `IV_SRC_PROG='SAPLKKBL'` + `IV_SRC_STATUS='STANDARD'` ver (§2.1) |
| `EV_MESSAGE`'da `nav_remap=OFF…` | Çağrı yanlış — ekranı kullanmadan düzelt (§2.1) |
| Diğer ekranların status/titlebar'ı gitti | `IV_CUA_MERGE` boş/`'-'` gönderilmiş (§5) |
| `EV_RC=301` | Hedef program Z/Y değil (§2.3) |
| `EV_RC=300` | `IV_DYNPRO` 4 hane rakam değil (`'300'` → butcode çakışması) |
| `EV_RC=120` | Donör program/status ikilisi tutmuyor (§2.1) |
| `EV_RC=5` | `IT_FIELDS` ön-doğrulaması — mesajdaki alan adlarını düzelt (§4.5) |
| Alan üretildi ama **etiketsiz** | `TYPE='TEXT'` satırı unutuldu — sessiz kusur (§4.1) |
| `rc=6` alan ekranında | `CONTAINER` + `IT_FIELDS` → `DOCKING` kullan (§4.4) |
| `400 Session Timed Out` (classrun) | Dialog context yok → SOAP-RFC kanalı |
| `00256 Geçerli bir işlev seçin` | `act` temizlenmiş / donör `ACT` havuzu boş (§7) |
| `00264 GUI status not generated` | `RS_CUA_GENERATE` çağrılmamış |
| `mandatory parameter BIV` (RABAX) | FETCH'ten gelen `biv`'i WRITE'a geçir |
| ALV pencereyi doldurmuyor | CUST_CTRL `c_resize_v/h='X'` yok |
| GUI metinleri Almanca | `sap-language=TR` ile çağır |
| SOAP cevabında tablo boş, HTTP 200 | `TABLES` etiketleri boş olarak gönderilmemiş (§1) |

## 13. Bilinen sınırlar + bu belgenin tazeliği

### 13.1 Sınırlar
- **Program açıklaması (`TRDIRT`) ADT'den değiştirilemiyor** — metadata `PUT`/lock rotası
  406/404/403 verir; aynı objeye **kaynak** push'u çalışır ⇒ açıklama için **SE38 gerekir**
  (kayıt: `governance/infra-findings.md`, 2026-08-18).
- **Runtime/GUI davranışı statik ölçümle kanıtlanamaz** (buton tepkisi, ESC, 00256/00264) —
  ekranı çalıştırmak ya da `sap-gui` yetkili bir ajan/kullanıcı gerekir.

### 13.2 Bu belge NASIL güncel tutuluyor (ikinci kez bayatladı, o yüzden gate var)
`ZSD000_FM_SCREEN_GEN` iki kez değişti ve iki kez kılavuza yansımadı (`IT_BUTTONS` 2026-07-31;
donör + davranış anahtarları 2026-08-14/18 — 4 gün). Bu yüzden §2'deki imza bloğu
**makine-okunurdur** ve `scripts/validators/check_fm_signature_doc_sync.py` gate'i
(run_all_validators → pre-commit + CI) onu FM kaynağıyla karşılaştırır:
`EKSİK` (imzada var, belgede yok) · `HAYALET` (belgede var, imzada yok) · `ÖLÇÜLEMEDİ`
(blok/dosya yok — "temiz" ile aynı çıkışa DÜŞMEZ). Gate bugün **warn-first**tir (bloklamaz).
⇒ **Parametre değiştiren kişi §2 bloğunu da günceller.** Davranış değişikliği (yalnız parametre
değil) ise §2.1/§2.2/§5'e de işlenir — gate metni değil, **parametre kümesini** korur.

---

## İlgili
- [`howto-classic-dynpro-datafield-screens.md`](howto-classic-dynpro-datafield-screens.md) — alan/diyalog ekranı (DDIC bağlama, F4, çok-turlu CUA)
- [`adt-fugr-functions.md`](adt-fugr-functions.md) §6 — derin iç mekanik / FUGR+FM yaratma
- [`checklists/classic-dialog-creation.md`](checklists/classic-dialog-creation.md) — üretim öncesi checklist (CLC-SCR1..7)
- [`../standards/06-coding-classic-dialog.md`](../standards/06-coding-classic-dialog.md) — klasik dialog kodlama standardı
- [`templates/classic-alv-list.prog.abap`](templates/classic-alv-list.prog.abap) · [`templates/classic-dynpro-dialog.prog.abap`](templates/classic-dynpro-dialog.prog.abap)
- Canlı örnekler: `<source_root>/SD/ZSD000_CLC/functions/ZSD000_FM_SCREEN_GEN.func.abap` ·
  `<source_root>/SD/ZSD000_CLC/programs/ZSD000_P_ALV_TEMP1/2/3/4.prog.abap`
