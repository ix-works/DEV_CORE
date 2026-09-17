---
name: feedback_brifinge-koydugun-yolu-once-kendin-kos
description: Spawn brifingine yazdığın dosya yolu/komut bir İDDİADIR — göndermeden önce kendin koş; yanlış yol o ekseni SESSİZCE koşmamış bırakır
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 84facfd3-9151-4893-8380-15c2cfd0d393
---

Bir alt-ajana brifingde verdiğin **dosya yolu veya komut** ölçülmemiş bir iddiadır. Yanlışsa ajan
ya (a) kendi düzeltir — turunu senin hatanı ayıklamakla harcar, ya da (b) **sessizce atlar** ve o
denetim ekseni hiç koşmamış olur, ama rapor "yapıldı" gibi okunur.

**2026-09-08'de İKİ KEZ oldu** (aynı gün, farklı ajan ⇒ sınıf):
- FE bug gate brifinde `core/checklists/bug-checklist-FE.md` yazdım — **yok**; doğrusu
  `core/playbook/checklists/bug-checklist-frontend.md`. Ajan yakaladı ve kendi düzeltti.
- Gateway/gate brifinde `core/scripts/run_all_validators.py` yazdım — **yok** (`Errno 2`);
  doğrusu `core/scripts/validators/run_all_validators.py`. Gate ajanı `find -L core` ile buldu ve
  kendi raporunda *"brifingdeki komut olduğu gibi kullanılsaydı bu eksen SESSİZCE koşmamış olurdu"*
  diye niteleyici düşürdü.

**2026-09-08, 3. vaka — KAYNAK FARKLI, SINIF AYNI:** yolu bu kez *ben* uydurmadım; `PreToolUse`
hook'u *"run_all_validators.py → playbook/checklists/core-script-development.md"* atfını verdi ve ben
onu **doğrulamadan** brifinge kopyaladım. Gate ölçtü: o dosya 125 satır, core script **YAZMA**
checklist'i (CORE-01..05); `grep "quick|strict|warn-first|koşum|pre-commit"` → **0 eşleşme**. Gerçek
koşum sözleşmesi script'in **kendi docstring'inde** (`core/scripts/validators/run_all_validators.py:1-19`,
bayrak semantiği `:118-120`, `:154-155`, `:164-170`). Aynı turda ikinci bir çürütme: brifingde
*"`--quick` yok"* demiştim, **var** (`:120`; etkisi dar — yalnız dosya adında `freshness` geçen tek
kapıyı atlar).

**2026-09-08, 4. vaka — YOL DEĞİL **ALAN ADI**; aynı sınıf, daha sinsi biçim.**
Gateway brifine doğrulama sorgusunu yazdım: *"`SELECT Vbeln, Posnr, MengeTsl, MengeBky FROM
zsd001_i_so_item` → önce/sonra sıralı diff"*. Kolon adlarını **hiç doğrulamadan** yazdım;
view'ın gerçek alanları **`VBELNVA`/`POSNRVA`** (OData tarafında `VbelnVa`/`PosnrVa`). Ajan
`SELECT *` ile keşfedip düzeltti ve raporunda açıkça *"brifteki kolon adları YANLIŞTI"* yazdı.
⭐ Neden bu biçim daha tehlikeli: yanlış **yol** `Errno 2` verir — gürültülü düşer. Yanlış
**kolon adı** ise SQL'de `400`/`404` verir; "altyapı hatası, tekrar koş" diye sınıflandırılıp
**o doğrulama ekseni atlanabilir** — ve o eksen tam da *"tüketici deltası 0 mı?"* idi, yani
turun BLOCKER kapısı. Aynı brifte ikinci bir ölçülmemiş varsayım daha vardı: `adt_sql_query`'nin
3 AND-terimli `WHERE`'i **400** verdiğini bilmiyordum; ajan izole edip sınırı buldu ve ölçümü
üst-kümeye taşımak zorunda kaldı.
⇒ **Ek refleks:** brife bir SQL/OData sorgusu koyacaksan önce **`SELECT *` ile bir kez keşfet**
(ya da brife *"kolon adlarını DOĞRULAMADIM, `SELECT *` ile keşfet"* yaz). İlgili:
[[feedback_kopya-sayimi-tek-sozdizimi-desenine-dayanma]] · [[feedback_arac-basarisizligini-zararsiz-sayma]]

**How to apply (ek):** Hook / JIT-recall / memory'nin verdiği **atıf da bir iddiadır**. Enjekte edilen
bir yolu brifinge koymadan önce en az bir kez aç ve aradığın şeyin orada olduğunu gör — dosyanın VAR
olması, aradığın bölümün orada olduğu DEĞİLDİR. Doğru refleks: bir script'in koşum sözleşmesini önce
**script'in kendi docstring'inde** ara.

**Why:** Brifing, ajanın gerçeklik zeminidir. Oradaki yanlış bir yol, "TAHMİN YASAK" kuralını benim
tarafımdan ihlal etmemdir — ajandan kanıt isterken kendim kanıtsız yol veriyorum. Ve zararı
asimetrik: ajan düzeltirse **zaman**, düzeltmezse **sessiz kapsam deliği** kaybedersin
([[feedback_exit0-degil-cikti-kaniti]]).

**How to apply:** Spawn'dan **ÖNCE**, brifingde geçen her yolu/komutu bir kez koş ya da varlığını
doğrula (`ls`, tek `--help`, `path=core/` ile Grep — kök-Grep ve `find` junction'ı görmez,
[[feedback_bash-find-core-junctionu-gormez-yok-sanirsin]]). Doğrulayamadıysan brifingde **"yolu
DOĞRULAMADIM, önce teyit et"** diye yaz — ajan o zaman sessizce atlamaz. Yanlış verdiğini sonradan
fark edersen `SendMessage` ile **hemen** düzelt; ajan o eksene girmeden yetişirsin.
İlgili: [[feedback_spawn-brifinde-sablonun-kanonik-basliklarini-kullan]] ·
[[feedback_ajan-kurali-brifingde-degil-taniminda-yasar]] · [[feedback_kanit-yeniden-uretilebilir-bicimde-yazilir]]

---

## ⛔ 2026-09-10 — AYNI HATA ÜÇÜNCÜ KEZ, ve bu kez KAYIT VARDI ama İŞE YARAMADI

Bu turda `bug-expert` brifine yine **`core/playbook/checklists/bug-checklist-FE.md`** yazdım.
Bu dosya **YOK** — ve yukarıdaki *2026-09-08 vaka #1* zaten tam bunu belgeliyordu. Kapı yine
kendi buldu, raporunun başına *"bu oturumda üçüncü kez"* diye yazdı. Aynı oturumda bir de
`core/playbook/bug-checklist-BE.md` yazmıştım (doğrusu `checklists/bug-checklist-backend.md`).

⇒ **Ders güncellemesi: KURAL yetmiyor, AD lazım.** "Yolu önce koş" davranışsal bir hatırlatma;
brif yazarken akış içinde atlanıyor. Çare, doğru adları kaydın İÇİNDE tutmak ki kopyalanabilsin.

### 📌 `core/playbook/checklists/` — KANONİK DOSYA ADLARI (2026-09-10, `ls` ile ölçüldü, 16 dosya)
```
adobe-forms-creation.md      classic-dialog-creation.md   packing-consumption-creation.md
bug-checklist-backend.md     core-script-development.md   rap-creation.md
bug-checklist-frontend.md    doc-checklist.md             rap-troubleshoot.md
cds-creation.md              domain-dtel-creation.md      struct-creation.md
itg-s2-signoff.md            table-update.md              ui-backend-rap-creation.md
                                                          ui-freestyle-creation.md
```
⛔ **`bug-checklist-FE.md` ve `bug-checklist-BE.md` diye dosya YOKTUR.** Tam adlar
**`bug-checklist-frontend.md`** ve **`bug-checklist-backend.md`**'dir. Kısaltma refleksi
(FE/BE) bu iki adda TUTMUYOR — dizinin geri kalanı da uzun-ad kuralında (`domain-dtel-creation`,
`ui-backend-rap-creation`).

### ⛔ 2026-09-10, 5. vaka — OBJE ADI; ve bu kez ARAÇ da yanlışı ONAYLADI

Gateway brifine *"5 SRVB republish: `ZSD000_UI_SIPSE` · `_DSKSE` · `_FIHSE` · `_FITSE` · `_IHRSE`"*
yazdım. Adları **SRVD adlarından türettim** — ölçmedim. Gerçek SRVB adları sonuna **`_O2`** alıyor
(`ZSD000_UI_SIPSE_O2` …). 

⭐ **Bu vakayı diğer dördünden ayıran şey: yanlış ad GÜRÜLTÜLÜ DÜŞMEDİ.** `adt_publish_service`
var olmayan servise publish denemesine **HTTP 200 + `ok:true, published:true`** döndürdü; hata
yalnız yanıt gövdesindeki `SEVERITY=ERROR` + *"Service Binding does not exist"* alanındaydı.
Yani brifim uygulanıp `SEVERITY` okunmasaydı, tur *"5/5 republish OK"* diye **kapanacaktı** ve
bayat `$metadata` canlıda kalacaktı. Ajan alanı elle okudu, adları düzeltti, 5/5 `SEVERITY=OK` aldı.

⇒ **Ders güncellemesi:** yanlış yol `Errno 2` verir, yanlış kolon `400` verir — ama **yanlış obje adı,
aracın sahte-OK'i ile birleşince HİÇBİR sinyal vermez.** Bu, bu kaydın en tehlikeli biçimidir:
sessiz kapsam deliği + **yanlış başarı beyanı**.
**Refleks:** brife bir SAP obje adı koyacaksan (SRVB/SRVD/DDLS/sınıf) onu **canlıdan ölç**
(`adt_search_objects` / `adt_package_contents`) ya da brife *"bu adı DOĞRULAMADIM, önce ölç"* yaz.
Ad türetme kuralları (SRVD→SRVB) pakete göre değişir; emsalden çıkarım **ölçüm değildir**.
Kanonik ayrıntı: `governance/infra-findings.md` → **Q278**.

**How to apply (ek):** Bir kaydın VAR olması, o hatayı tekrarlamayacağın anlamına gelmez —
kayıt ancak **kopyalanabilir bir değer** taşıyorsa kapıyı kapatır. Aynı hatayı üçüncü kez
yaparsan kaydı "daha sert yaz" değil, **doğru değeri kaydın içine koy**.
İlgili: [[feedback_iddia-kac-yerde-yasiyorsa-o-kadar-yerde-kapatilir]] ·
[[feedback_capa-liste-degil-KURAL-olmali]] (bu vaka onun TERSİ: burada KURAL vardı, LİSTE lazımdı).
