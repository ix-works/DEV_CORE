---
name: feedback_atc-priority-1-zorunlu
description: ATC bulgularında yalnızca Priority 1 zorunlu düzeltilir; Priority 2/3 kullanıcı onayıyla pass
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 535400ae-b5a0-4696-a522-033556d99bcf
---

ATC (Code Inspector / ZZNDBS_ATC variant) çalıştırıldığında: bir bulgunun **Priority of
finding = 1** olanları **ZORUNLU düzeltilir**. **Priority 2 ve 3** bulguları **şimdilik
kullanıcının açık onayıyla pass geçilebilir** (zorunlu değil).

**Why:** Proje kalite politikası (kullanıcı kararı 2026-06-02). Prio-1 = gerçek/kritik;
Prio-2/3 = düşük öncelik, şu aşamada bloke etmesin.

**How to apply:**
- `adt_atc_check` (mcp_servers/sap_adt/tools/query.py) yanıtında `priority_1_count`,
  `other_priority_count`, `must_fix` (prio1>0), `policy` alanları var.
- `must_fix=True` (Priority 1 bulgu var) → **DUR, düzelt** (forward progress yok).
- Sadece Priority 2/3 varsa → kullanıcıya bulguları **göster + açık onay iste** ("pass geçeyim mi?");
  onay gelirse pass. Sessizce/otomatik pass GEÇME — onay şart (ADR 0011 onay-kelimesi mantığı gibi).
- ATC variant sisteme özgü ZZNDBS_ATC (`.conn_adt` ADT_ATC_VARIANT). Bkz. [[feedback_mcp-post-shell-en-master-lang]] kardeşi reviewer kültürü (ADR 0006).

### ⏱ NE ZAMAN — kural doğruydu, **uygulama ANI** eksikti (2026-08-21)

- **ATC canlı objede koşar** (`adt_atc_check` SAP'deki objeyi denetler; yerel `abaplint` bunun
  ikamesi **değildir** — çekirdeğin `abaplint.json`'unda `check_syntax` bilinçle kapalıdır).
  ⇒ **Bilinen bir P1 ailesi PUSH ÖNCESİ kapatılır.** Aksi hâlde bedeli ikinci bir
  **push + aktivasyon** turudur: obje canlıdır, her düzeltme yeniden yazım ister.
- **Kapı ETKİye göre derecelendirir, ev politikası ÖNCELİĞE göre.** Bir bug-gate ATC P1'i
  *"LOW"* diyebilir ve teknik olarak haksız da olmayabilir — ama politika `priority_1_count>0`
  için **DUR** der. ⇒ Kapı brifinde politika **açıkça yazılmazsa kapı onu bilemez**;
  kapının derecesi politikayı **ezmez**.

**Ölçülmüş vaka (bir projede):** bir kalem canlıya alındı → ATC **10 P1** verdi → düzeltme + **ikinci
push turu** gerekti. Bir önceki kapı turunda aynı aile *"LOW"* derecelendirilmiş ve ilerleme sürmüştü.
⇒ Bunu dayatan sonuç kapısı üretimde: `adt_atc_check` yanıtındaki `priority_1_count>0` yapısal alanı
`post_tool_failure` hook'unda hatırlatma doğurur. *(Brifing METNİNİ denetleyen alternatifler 605 gerçek
brif üzerinde ölçülüp elendi.)*

İlgili: [[feedback_yesil-sinyalin-kapsamini-sor]] · [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]] ·
[[feedback_duzeltme-turu-kendi-regresyonunu-uretir]]

### 🔎 ARAÇ KAPSAMI — `adt_atc_check` HER TİPİ ÖLÇEMEZ (ölçüldü 2026-08-24)

`adt_atc_check(name=..., object_type="bdef")` → `ok:false` · **`"Unsupported object type: bdef"`**.
Aracın kendi listelediği desteklenen tipler: `class, interface, program, include, functiongroup,
function, dataelement, domain, table, structure, tabletype, cds, metadataextension, accesscontrol,
**servicedefinition**, **package**`. ⇒ `bdef`, `srvb` ve `fugr` **tekil olarak ölçülemez**.
*(Liste ölçüm anınındır — araç genişlemiş olabilir; kullanmadan önce aracın kendi tip listesine bak.)*

**Sonuç (iki yönlü):**
- `bdef` bulguları **YALNIZ paket kapsamlı** koşuda görünür (`object_type="package"`). Tekil
  obje bazında *"bu bdef temiz mi"* diye **bakılamaz**.
- ⛔ **Ölçülemeyen tip "temiz" DEĞİLDİR.** Vaka: bir pakette paket kapsamı ilk kez koşulunca
  `5 → 11` P1 çıktı; artış **6 × BDEF `strict` (+BDL 339)** idi ve daha önce hiç ölçülmemişti.
  Sayı artmadı, **kapsam genişledi** — önceki ölçüm 10 SINIF taramıştı.

**Ayrıca — aynı kusur İKİ check'te, İKİ ayrı öncelikte olabilir:** `strict` eksikliği hem bir check'te
Priority **2** (sade metin) hem başka bir check'te Priority **1** (*"Syntax check warning."* sarmalayıcısı
+ `+BDL 339`) olarak rapor edilir. **P1'i doğuran, ABAP derleyicisinin kendi uyarısını aktaran check'tir**;
aynı check `transactional_query`'yi aynı objelerde **P3** verir ⇒ önceliği check değil **alttaki mesaj**
belirler. *"Priority 2'de gördüm, önemsiz"* diye geçme — aynı bulgunun P1 ikizi olabilir.

⚠ **Paket kapsamlı ATC PAHALIDIR:** büyük pakette istemci 60s read-timeout'a düşebilir ve
**sunucudaki koşu devam eder**. Art arda iki paket koşusu tetiklemek SAP'yi geçici olarak
erişilemez hâle getirdi (ölçüldü 2026-08-24: sonraki `adt_get` çağrıları da timeout; DNS/TCP sağlamdı
⇒ darboğaz uygulama tarafı). ⇒ Peş peşe paket ATC'si **koşturma**; timeout alırsan **hemen tekrarlama**.

### ⛔ SIRA — `adt_atc_check` AKTİF sürümü ölçer; doğru sıra **push → AKTİVE → ATC** (ölçüldü 2026-09-04)

Lider ajanlara *"ATC'yi yalnız PUSH'tan SONRA koş, yoksa eski sürümü ölçer"* talimatı verdi. **Bu
YANLIŞTI ve gateway ölçerek çürüttü.** Push yetmez: **aktivasyona kadar ATC hâlâ AKTİF (eski) sürümü ölçer.**

**Kanıt (bir sınıfta aynı bulgu, üç ölçüm):** push sonrası / aktivasyon öncesi bulgu `start=360` —
**eski dosyadaki** satır. Yeni dosyada aynı deyim `start=406`. Aktivasyondan sonra aynı ATC bulguyu
**`start=406`**'da gösterdi.
⇒ *"Aktive etmeden ATC ile yeni kodu gate'lemek"* **yapısal olarak mümkün değil.**
⇒ `adt_syntax_check`'i "aktivasyon öncesi ayrı adım" sanmak da aynı hatanın kardeşi: o araç
**temizse AKTİVE EDER** (core PATTERN #20), ayrı bir adım olarak var olamaz. Derlenirlik kanıtı
**aktivasyonun kendisidir**.

### ⭐ TEK ATIŞLIK ATC KAPI DEĞİLDİR — BASELINE ↔ SONRASI karşılaştır
Aktivasyondan sonraki tek bir ATC koşusu *"bu turun ürettiği"* ile *"zaten oradaki"* bulguyu
**ayıramaz**. Doğru kapı: **aktivasyon ÖNCESİ (eski aktif sürüm) P1 sayısı ↔ SONRASI P1 sayısı.**
Ancak o zaman *"bu tur SIFIR yeni Priority-1 üretti"* denebilir.

**Bunun doğurduğu işletilebilir ayrım — 22 objelik turda ölçüldü:**
- Bulgu **BİZİMSE** (metodu, diff'imizin dokunduğu bir metotsa) → **SERT DUR.**
- Bulgu **PRE-EXISTING ise** → aktive et, **topla**, sonunda tek karar al. Her biri için ayrı
  ayrı durmak 21 objede tek tek bloke olmak demekti.
- ⛔ *"Pre-existing"* bir **İDDİADIR** — her seferinde **canlı↔local diff**'iyle kanıtlanır
  (bulgunun metodu diff'te geçiyor mu: eşleşme 0 mı?). Kanıtlanamıyorsa durulur.

**Vaka:** bir rapor sınıfının aktivasyonu 2 P1 → 7 P1 yaptı; beş yenisinin hepsi başka bir
geliştiricinin korumasız `get_column( )` bloğuydu (`CX_SALV_NOT_FOUND` yakalanmıyor). Kullanıcı
kararı: pre-existing P1 kabul edilip aktive edildi — **istisna, kuralın iptali değil**; gerekçe,
aktive etmemenin durumu iyileştirmeyip kötüleştirmesiydi (düzeltme canlıya çıkmaz + sınıf inaktif
parçayla kalır). ⚠ *"Pre-existing" ZARARSIZ demek değildir* — aynı transport onları da PRD'ye taşır,
ayrıca gündeme alınır.

İlgili: [[feedback_kapi-zinciri-derlemeyi-gormez]] · [[feedback_capa-liste-degil-KURAL-olmali]]

Son-doğrulama: 2026-09-04 (SIRA ekseni + baseline↔sonrası kapısı); tohum geri akışı 2026-11-12 ·
Applies-to: ADT ile ABAP yazan tüm profiller (ATC erişimi olan)
