---
layer: L2
scope: project-wide
type: documentation-standard
applies-to: classic-gui-f1-help
version: 1.0
last-updated: 2026-06-25
status: active
source: ZSD001 Termin Raporu F1 dokümantasyonu (2026-06-25) — canlı doğrulanmış DOCU_UPDATE/adt_classrun yöntemi
---

# Klasik GUI Uygulama — In-System Kullanıcı Dokümanı (F1 / SE61) Standardı

> **Bu standart neyi kapsar:** Klasik ABAP GUI uygulamalarında (report / Dynpro / module pool / ALV)
> kullanıcının **F1 / Goto → Documentation** ile gördüğü **sistem-içi yardım dokümanını** nasıl
> üreteceğimizi tanımlar. Görsel olmasa da **mantık/içerik olarak RAP Fiori uygulamalarının KD'lerine
> paralel** bir kullanıcı kılavuzu hedefler.
>
> **İçerik kuralları** (ne yazılır, ton, FS/TS/KD ilişkisi) → `standards/04-documentation-fs-ts.md`.
> Bu dosya **TESLİM MEKANİZMASINI** (ITF format + SE61 RE/TX dokümanları + üretim aracı) tanımlar.

---

## 0. NE ZAMAN BU STANDART

| Uygulama tipi | Kullanıcı dokümanı teslim biçimi |
|---|---|
| **Klasik GUI** (report/Dynpro/ALV, ör. ZSD001) | **Bu standart** — in-system F1/SE61 (RE fihrist + TX detay) **+** repo'da markdown KD (`docs/KD-*.md`) |
| RAP + Fiori freestyle | Markdown KD (`docs/KD-*.md`) + (varsa) Fiori launchpad yardımı; bu standart UYGULANMAZ |

> Klasik GUI uygulamada **her ikisi de** olur: repo'daki markdown KD = yazım/otorite kaynağı;
> in-system F1 = ondan türeyen, kullanıcının programın içinden eriştiği yardım. İkisi **içerik olarak
> paralel** tutulur.

---

## 1. TESLİM MODELİ — Fihrist + Link'li Detay Sayfaları (tek-düz-sayfa YASAK)

SAP standart yardımı gibi **çok sayfalı, hyperlink'li** yapı:

```
RE-doc  (object = PROGRAM ADI, ör. ZSD001_P_TERMIN_RAPORU)   = FİHRİST (içindekiler)
  │  kısa giriş + İçindekiler listesi; her madde bir <DS:TX...> link'i
  ├─ TX-doc  ZSD<NNN>_KD_<KONU1>   = Detay sayfası 1
  ├─ TX-doc  ZSD<NNN>_KD_<KONU2>   = Detay sayfası 2
  └─ ...
```

- **Fihrist** = `RE` doc sınıfı, obje adı = **programın adı** (F1 bu dokümanı açar).
- **Her detay sayfası** = `TX` (genel-metin) doc sınıfı, ayrı obje.
- Fihristteki link'e tıklayınca ilgili TX sayfası açılır (**yeni-sayfa navigasyonu**).

---

## 2. YAPI / BÖLÜMLEME (KD-SD-004 paraleli — RAP KD mantığı)

Standart bölüm seti (uygulamaya göre uyarla; kanonik örnek ZSD001):

1. **Amaç ve Kapsam** — ne işe yarar, sunum biçimi (seviye/tablo sayısı), salt-okunur/risk güvencesi
2. **Ön Koşullar ve Yetki** — nereden açılır (atanmış **tcode** veya menü/rol), yetki notu, uyarlama bağımlılığı. ⛔ **SA38/SE38/SE80 ile program çalıştırma ASLA verilmez** (ne ana yol ne alternatif): son kullanıcı bu transaction'ları çalıştıramaz; tcode'a erişemiyorsa sebebi vardır (yetki kasıtlı) → workaround önerme, **sistem yöneticisine/yetkiliye yönlendir**. Tcode'u olmayan rapor → "kurumunuzca tanımlanan menü/rol üzerinden açılır." (Kural: `feedback_enduser-doc-no-sa38-se38-program-run`. İstisna: FS/TS gibi TEKNİK dokümanda geliştirici-SE38 — transport/aktivasyon kontrolü — meşru.)
3. **Seçim Ekranı ve Giriş Alanları** — her alan + **tip/değer tanımları** (ör. FI/SP/FD)
4. **Çıktı Tabloları** — her ALV listesi (üst/alt), içeriği, **sütunları**
5. **Hesaplanan Kolonlar ve Formüller** — türev alanların formülleri
6. **Özel Mantık** — uygulamaya özel kurallar (ör. teslimat planı termin timeline)
7. **İpuçları ve SSS** — sık sorulanlar, görünmeyen kayıt/boş alan açıklamaları

> Ton: sade, kullanıcı-dostu, teknik-jargonsuz. Tablo/sütun adlarını ve formülleri **açık** ver
> (kullanıcı raporu okurken karşılığını bilsin). RAP KD'lerindeki (ör. `KD-SD-015-ORDER`) derinlik/ton hedeftir.

---

## 3. ITF FORMAT KURALLARI (zorunlu)

Dokümanlar **ITF** formatındadır (markdown/HTML DEĞİL). Her satır bir `TDFORMAT` + `TDLINE`:

| Amaç | TDFORMAT | Not |
|---|---|---|
| **Başlık** (sayfa başı) | `U1` | **Her sayfanın İLK satırı U1 başlık OLMALI** (bkz. §6 title tuzağı) |
| Paragraf (yeni satır) | `/` | |
| Standart paragraf | `AS` | |
| **Bold / vurgu** (terim·ad·sütun) | inline `<ZH>metin</>` | Anlatılan terim/sütun adı **bold**, açıklaması normal |
| **Link** (detay sayfasına) | inline `<DS:TX.<DOCNAME>>görünen metin</>` | Kapanış `</>`; CANLI teyitli biçim |

**Inline tag kuralları:**
- `<DS:<SINIF>.<OBJE>>görünen metin</>` — SINIF=hedef doc sınıfı (detaylar `TX`), OBJE=doküman adı, kapanış `</>`. **Canlı std örnek:** `<DS:TX.PY_DE_SV_ZS_LAUFID>Laufidentifikation</>`, `<DS:TRAN.OOALEBSIZE>...</>`.
- **Bold tag = `<ZH>...</>`** (SAPscript "Hervorgehoben" karakter-stili). **CANLI TEYİTLİ** (RHALEINI std doc PROBE, 2026-06-25): SAP hem `<ZH>` hem `<zh>` kabul eder, kapanış `</>`. ⚠️ **TAHMİN YASAK kuralı:** yeni uygulamada tag biçimini varsayma — runner PROBE'u (std doküman DOCU_GET) çıktısından canlı doğrula.
- **Tag-içi-tag YASAK:** `<ZH>` içine `<DS:...>` veya literal `<...>` (ör. `FN<tarih>`) gömme → bozulur. Literal açılı-parantezi tag dışında tut ("FN + tarih" gibi yaz).
- **HTML entity / markdown YASAK.** Düz ITF.
- ⚠️ **İKİ AYRI LİMİT — KARIŞTIRMA:**
  - **DEPOLAMA:** `DOKTL-TDLINE` ≤ 132 karakter (bu aşılırsa veri DOKHL/DOKTL'ye yazılmaz).
  - **F1/SE61 GÖRÜNTÜLEME ≤ 72 ham karakter (tag'ler dahil) — GERÇEK SINIR.** SAPscript yardım penceresi klasik 72-char genişlikte; **bir satır 72 ham karakteri aşarsa F1/SE61'de KUYRUĞU KIRPILIR** (wrap değil, kayıp — örn `...kurumunuzca` → `...kurumunuz`). ≤132'ye güvenme; **her `iv_line` ≤ 72 (güvenli ≤ 70) tut**, uzun cümleyi kelime sınırında birden çok kısa `add()` satırına böl, `<ZH>...</>`/`<DS:...>` tag'ini İKİ satıra BÖLME. (CANLI-TEYİTLİ 2026-06-30, ZSD001 F1 testi: 72+ char satırlar kırpıldı; ≤132 check'i kaçırdı çünkü depolama limitiydi.) **Gate: DOCU runner `iv_line` >72 = FAIL.**
- **Gerçek Türkçe** (ş/ı/ç/ğ/ü/ö/İ), kaynak **UTF-8 (BOM yok)**, **TR login** ile yazılır (ADR 0005-D).

---

## 4. NAMING

| Obje | Ad |
|---|---|
| Fihrist (RE doc) | = **program adı** (`ZSD<NNN>_P_<...>`) |
| Detay sayfası (TX doc) | `ZSD<NNN>_KD_<KONU>` (ör. `ZSD001_KD_AMAC`, `ZSD001_KD_KOLON`) |
| Üretici runner (program-özel) | `ZSD<NNN>_CL_<...>_DOCU_RUN` (if_oo_adt_classrun) |
| Generic yazıcı (proje-ortak) | **`ZSD000_CL_DOCU`** (paket ZSD000_CLC) — tüm uygulamalar kullanır |

---

## 5. ÜRETİM MEKANİZMASI (yalnız bu yol çalışır)

> **Kanıtlı gerçek (araştırma 2026-06-25):** ADT/REST klasik RE/TX dokümantasyonunu **YAZAMAZ**
> (Eclipse ADT'de editörü bile yok). Tek yol **backend FM** (`DOCU_UPDATE` yaz / `DOCU_GET` oku),
> ITF/TLINE formatı, depo DOKHL/DOKTL/DOKIL. Proven-precedent = abapGit `zcl_abapgit_object_docv`.

**İki obje + gateway classrun:**
1. **`ZSD000_CL_DOCU`** (generic, ZSD000_CLC) — `write_object_doc( id, object, langu, title, it_itf )` → THEAD doldur (tdform=`S_DOCU_SHOW`, tdstyle=`S_DOCUS1`, state='A', typ='E') → `CALL FUNCTION 'DOCU_UPDATE'` → `COMMIT WORK` (`"#NO_RAP_COMMIT_CHECK` — util LUW, RAP değil). `read_object_doc(...)` → `DOCU_GET` (probe + geri-oku).
2. **`ZSD<NNN>_CL_<...>_DOCU_RUN`** (program-özel, `if_oo_adt_classrun~main`) — KD içerik (ITF satırları) burada gömülü. `main()` sırası: **PROBE → TX detay sayfaları → RE fihrist (link'li) → DOCU_GET readback**. Detaylar fihristten ÖNCE yazılır (link hedefleri var olsun).
3. **gateway** → `adt_classrun` (TR login) ile runner'ı çalıştırır. Güncelleme = içerik değiştir + re-classrun (kullanıcı GUI'de hiçbir şey yapmaz).

**PROBE (TAHMİN YASAK):** runner main()'i ÖNCE link/format içeren bir **standart** dokümanı (`DOCU_GET`) okuyup ham `<DS:...>` / `<ZH>...` satırlarını `out->write` ile basar → gerçek tag biçimi classrun çıktısında **canlı görünür**. Tag biçimini varsayma; probe doğrular.

**İçerik kaynağı (uydurma YASAK):** tip/değer tanımları (FI/SP/FD gibi) **domain fixed-value label'larından CANLI** (`adt_get`); kolon/formül **FS + class mantığından**; varsa repo markdown KD'sine paralel. Kaynak yetmezse DUR, kullanıcıya sor.

---

## 6. BİLİNEN TUZAKLAR (canlı yaşanmış — ZSD001)

| # | Tuzak | Çözüm |
|---|---|---|
| 1 | **Yeni DDLS/doc shell** `adt_push_source`/`post_shell` ile yaratılamaz | Generic class + `DOCU_UPDATE` zaten doc'u yaratır (shell gerekmez) |
| 2 | **Title (tdtitle) DSYST `DOKNAME C(20)` sınırı** — obje adı >20 char ise başlık hiçbir header'a yazılmaz, `DOCU_GET` title boş döner | **KOZMETİK** — SE61/F1 başlığı **gövdenin ilk `U1` satırından** alır → her sayfanın ilk satırı U1 başlık (zorunlu). Title param yine geçilir ama görsel etkisi U1'dedir |
| 3 | **MCP `adt_classrun` tool yanlış "does not implement main" hatası** döndürebilir (parse bug) | Gateway ham HTTP POST `/sap/bc/adt/oo/classrun/<class>` ile aşar; çıktı tamdır (LİDER-lane tooling fix adayı) |
| 4 | **DOCU_UPDATE transport** corr-insert ister; TX/RE doc'ları açık TR'ye gitmeli | Gateway tier-aware; mevcut TR (yeni TR yaratma — ADR 0005-C) |
| 5 | **DOCU_* released DEĞİL** → ATC cloud-readiness flag | Dev-time tooling + kendi Z objemizin doc'u → kabul; **Prio-1 değil** (Prio 2/3, açık onayla pass) |

---

## 7. DOĞRULAMA (DONE tanımı)

1. classrun readback: her doc `DOCU_GET exists=X`, DOKHL `DOKSTATE='A'`, TR.
2. **Bold/link tag biçimi** probe çıktısıyla canlı teyitli.
3. **Kullanıcı F1 testi:** tcode → F1 → fihrist açılır → link'e tıkla → detay sayfası açılır (navigasyon çalışır), TR karakterler düzgün.
4. ATC **Prio-1 = 0** (her iki class).

---

## 8. KANONİK ÖRNEK

- Generic: `ZSD000_CL_DOCU` (ZSD000_CLC)
- Uygulama: `ZSD001_CL_TERMIN_DOCU_RUN` (ZSD001_CLC) → `ZSD001_P_TERMIN_RAPORU` (tcode ZSD001) F1: fihrist + 7 TX detay (AMAC/ONKOSUL/SECIM/TABLO/KOLON/TESLPLAN/IPUCU).
- Repo markdown KD paraleli: `ERP/SD/ZSD001_CLC/docs/KD-SD-004_*.md` (yapı), `ZSD001 .../KD-SD-015-*.md` (ton/derinlik).

> **"Şu uygulamanın KD'sini yaz" denince:** bu standart + §5 mekanizma uygulanır — domain'den tip
> tanımlarını canlı çek, FS+class'tan kolon/formül, KD-004 bölümlemesi, ITF format (§3), ZSD000_CL_DOCU
> + program-özel runner, gateway classrun, F1 testi.
