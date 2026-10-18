---
applies_to: [all]
layer: L2
scope: project-wide
applies-to: both
version: 1.0
last-updated: 2026-10-18
status: active
---

# Kural Yazım Standardı — dört alan, kapsam koşulu, üç test

> **Ne:** Bu çekirdekte yazılan her **kural** (checklist maddesi, ajan tanımı satırı, `CLAUDE.core.md`
> değişmezi, `claude/rules/` maddesi, standart/playbook'taki MUST/YASAK cümlesi) bu sayfadaki dört
> alanı taşır, olumsuz iddiasını kapsam koşuluyla yazar ve birleşmeden önce üç testten geçer.
> **Neden:** Bir denetim turunda (2026-10-18) kural kaçaklarının büyük kısmının sebebi kuralın
> **yokluğu değil**, yazılış biçimiydi: kural uygulayacak ajanın o an okuduğu dosyada değildi
> (konum), hangi eylemde uygulanacağı yazmıyordu (ateşleme anı), ya da başka bir metinle
> çelişiyordu. Aşağıdaki §5 vakaları ölçülmüştür.
> **Ne zaman:** yeni kural yazarken **ve** mevcut bir kuralın metnine dokunurken. Dokunulmayan eski
> kurallar toplu yeniden yazılmaz (bürokrasi üretme); dokunulan kural bu standarda çekilir.
> **Kim uygular:** kuralı yazan (lider, infra-expert, kuralı öneren uzman) dört alanı yazar, ulaşım ve
> çelişki testini koşar, netlik testinin senaryolarını hazırlar; netlik testinin taze okurunu **lider** koşar (§4.1).

## 1. DÖRT ZORUNLU ALAN

| Alan | Soru | Yeterli | Yetersiz (örnek) |
|---|---|---|---|
| **NE** | Tam olarak ne yapılır / yapılmaz? | Tek anlamlı; terimler tanımlı; ölçülebilir eşik (*"her satır ≤ 72 ham karakter, etiketler dahil"*) | *"formatter **veya eşdeğeri**"* — eşdeğerin ölçütü yok |
| **NEDEN** | Hangi hatayı önler? Hangi vakada doğdu? | Mekanizma tek cümle + vaka (tarih, genericize) | *"önemli"*, *"best practice"* |
| **NE ZAMAN** | Hangi **eylemde**, hangi **dosya türünde** ateşler? | *"`.clas.abap` içinde yeni metot ya da bölüm başlığı yazarken"* | Yalnız semptom (*"push 400 verirse"*) — o an iş olmuştur |
| **NEREDE** | Kuralı uygulayacak rol onu **o an hangi dosyada** okuyor? | §3 tablosundaki kanal + o kanalda metin ya da ID | Yalnız memory · yalnız register · yalnız ilgisiz bir howto |

⛔ **NE ZAMAN ile NEREDE birbirinin yerine geçmez.** Ateşleme anı yazılı ama kural yazan ajanın okumadığı
dosyadaysa kural o anda **görünmez**. Doğru dosyadaysa ama ateşleme anı yazmıyorsa okunur, ama
uygulanacağı an tanınmaz.

**Checklist satırında alanların yeri** (sütun yapısı değişmez): *Kontrol* sütununun başındaki kalın
cümle = **NE**; ardından `NEDEN:` (mekanizma + vaka) ve `NE ZAMAN:` (eylem + dosya türü) etiketleri;
**NEREDE** = `playbook/checklists/checklist-map.yaml` satırının `yazan_kanali` alanı (+ *Ref* sütunu).
Ajan tanımına giden tek cümle de aynı dört alanı taşır, kısaltılmış hâliyle: *"<eylem> yaparken <kural>
— çünkü <mekanizma> (<ID>)"*.

## 2. OLUMSUZ İDDİA = KAPSAM KOŞULU

*"X çalışmaz / X ÇÜRÜDÜ / X YASAK / X yoktur / X yakalamaz"* tipi her cümle **koşuluyla** yazılır:
profil/sürüm · obje tipi · uç/araç · bağlam · ölçüm tarihi. Ölçülmeyen komşu bağlam açıkça
**"ÖLÇÜLMEDİ"** diye yazılır.

- ✅ *"Bitişikleme reçetesi source-based class'ın IMPLEMENTATION bölümünde çözmez (s4_private 2025,
  2026-07-31 ölçümü); DEFINITION bölümünde yorum push açısından serbesttir."*
- ⛔ *"Bitişikleme reçetesi ÇÜRÜDÜ."* — okuyucu bunu her bağlama genelleştirir.

Neden: koşulsuz çürütme notu, **hâlâ geçerli olduğu yerde de** uygulanmaz ve yanlış yöntem seçtirir
(prior-art: `playbook/lessons-learned.md` ders (g) "X ÇÜRÜDÜ bir cümle değil, bir KOŞULDUR").
Aynı ilke başlıklarda da geçerlidir: başlık gövdeden ayrı okunur ve ayrı genellenir.

## 3. NEREDE — kural türüne göre kanal

| Kuralı kim uygular | Kanal (o an okunan dosya) | Not |
|---|---|---|
| Kodu/objeyi **yazan** uzman ajan | `claude/agents/<rol>.md` (zorunlu ön-uçuş) **ve/veya** `playbook/checklists/<tip>-creation.md` | Ajan tanımı yalnız zorunlu ön-uçuşta saydığı dosyaları okur; kural orada değilse yazım anında görünmez |
| Diff'i **inceleyen** kapı (bug-expert) | `playbook/checklists/bug-checklist-backend.md` · `bug-checklist-frontend.md` · doküman için `doc-checklist.md` | İnceleme kanalı tek başına **önleme değildir** — bulgu bir tur sonra gelir |
| **İkisi birden** | Yazım kanalı + inceleme kanalı | **Varsayılan budur** eğer kusur statik kapılardan geçiyorsa (sözdizimi, aktivasyon, abaplint, ATC yakalamıyor) ya da sessizse |
| Her oturum, her rol (lider dahil) davranış değişmezi | `CLAUDE.core.md` §1.1 (kısa) | Değişmez başka yere taşınmaz (`playbook/howto-talimat-dosyasi-bakimi.md` S2) |
| Belirli dosya türü açıldığında herkes | `claude/rules/<konu>.md` (`paths:`) | `paths:`'li kural her oturum yüklenmez; her oturum gereken kural buraya konmaz (S3) |
| Lider → alt ajan süreç kuralı | `claude/templates/spawn-brief.md` | İki ajanda tekrar eden kural brifte değil **ajan tanımında** yaşar |
| Nasıl yapılır reçetesi | `playbook/<konu>.md` | Reçete tek başına NEREDE'yi karşılamaz; ateşleme kanalından reçeteye **atıf** verilir |
| Projeye özgü | proje `CLAUDE.md` / paket `.rules.md` | Çekirdeğe yazılmaz (public repo) |

⛔ **YETMEZ:** yalnız auto-memory (alt ajanlar memory görmez) · yalnız bir register/kuyruk kaydı
(iş listesidir, okuma yolu değildir) · yalnız bir konuya dar howto (kural başka konuda da geçerliyse,
o konuda çalışan ajan howto'yu açmaz).

**"İkisi birden" tek-ev ilkesini bozmaz** (ADR 0019 §5A ölçüt 5): kuralın **kanonik metni tek yerde**
yaşar (çoğunlukla checklist satırı). Öbür kanala, ateşleme anını ve ID'yi taşıyan **tek cümle** yazılır;
ayrıntı kopyalanmaz. Tek cümle bayatlarsa kanonik satır yine doğrudur.

## 4. ÜÇ TEST — kural birleşmeden önce (ulaşım + çelişki: yazan · netlik: yazan hazırlar, lider koşar)

### 4.1 Netlik testi — yazan hazırlar, lider koşar
Taze okuru her durumda lider koşar; kuralı yazan senaryoları ve beklenen cevabı testten ÖNCE hazırlar.
1. **Taze okuyucu:** kuralın yazarı olmayan, bağlam verilmemiş bir ajan (kuralı uygulayacak rolün türü).
   Lider koşar ve `NETLİK` satırını doldurur; yazan madde 2-3'ü PR gövdesine/changelog'a koyar.
2. **2-3 gerçekçi senaryo**, en az biri **istisna ya da sınır vakası** (kuralın uygulanmadığı yer).
   Senaryo kuralın metnini tekrarlamaz; durumu anlatır (*"şu metodu ekliyorsun, başına şu notu koymak istiyorsun"*).
3. Her senaryonun **beklenen** uygulaması testten **önce** yazılır.
4. Okuyucu yalnız kural metnini + senaryoyu alır; ne yapacağını yazar.
5. Alınan ≠ beklenen ⇒ kural **muğlaktır**: metni düzelt, aynı senaryolarla yeniden koş.

**Sonuç kaydı** (infra-changelog satırının ya da PR gövdesinin içine):
`NETLİK: <kural-ID> · S1 <beklenen> → <alınan> UYUŞTU|AYRIŞTI · S2 … · S3 (istisna) … · okuyucu=<ajan türü> · <tarih>`

### 4.2 Ulaşım testi
- Checklist maddesi: `python scripts/validators/checklist_check.py --repo <core-kökü> --reach` —
  `checklist-map.yaml`'da `yazan_kanali` dolu her maddenin o dosyada ID'si ya da metin çapasıyla
  gerçekten bulunduğunu doğrular.
- Map dışındaki kural (core loader, rules, şablon): **yükleme zincirini** yaz ve her halkayı `rg` çıktısıyla
  göster — *rol → ajan tanımının zorunlu okuma listesi → dosya → kural satırı*. Bir halka eksikse kural
  ulaşmıyordur.

### 4.3 Çelişki testi
- Kuralın anahtar terimlerini **ve eşanlamlılarını** tara:
  `rg -n -i "<terim>|<eşanlamlı>" standards playbook claude CLAUDE.core.md scripts`.
- Türkçe karakterli terimde **harf varyantlarını** ayrıca ara (`ı/i`, `ş/s`, `ğ/g`, `ü/u`, `ö/o`, `ç/c`, büyük
  `İ`) — desen ile metnin alfabesi uyuşmazsa **sahte sıfır** çıkar, iki yönde de (ASCII desen ↔ Türkçe metin ·
  Türkçe desen ↔ ASCII'leştirilmiş metin); aramayı `rg` ya da Python ile yap. Üretilen HTML'de entity
  kodlaması (`&#304;`) ayrı bir sınıftır: çözülmüş metinde ara.
- Aynı konuyu farklı söyleyen her metin: ya hizala ya da **gerekçeli istisna** olarak iki tarafa yaz.
  Sayısal sınırlar (uzunluk, eşik) en sık çelişen sınıftır — kod/validator'daki değeri de tara.

## 5. ÖLÇÜLMÜŞ VAKALAR (genericize; standardın gerekçesi)

| # | Düşen alan | Vaka (bir projede) | Sonuç |
|---|---|---|---|
| V1 | NEREDE | Source-based class'ta metotlar arasına yorum koymak push'ta satır nosuz 400 veriyor. Kural 2026-07-31'den beri yazılı, ama **yalnız inceleme checklist'inde**; kodu yazan ajanın zorunlu ön-uçuşunda yok | 4 olay (2026-09 – 2026-10); sonuncusunda iki inceleme kapısı da kaçırdı |
| V2 | NEREDE | NUMC satır tipine karakter literali ve `EMPTY KEY` tabloda ölçütsüz `SORT` kuralları **yalnız liderin auto-memory'sindeydi** | Alt ajanlar her birini 2'şer kez tekrarladı |
| V3 | NE ZAMAN | ATC Pretty Print düzeltme reçetesi vardı; **yazım anında** önleme talimatı yoktu, aracın kendi başlığı *"zorunlu adım değil"* diyordu | 8 olay, 7 paket |
| V4 | Çelişki | Doküman checklist'i satır sınırını depolama sınırından (132) yazmıştı, standart görüntüleme sınırını (72) | Brife yanlış sınır geçti, doküman kapısı 3 BLOCKER |
| V5 | NE (muğlak) | *"formatter veya eşdeğeri"* — eşdeğer diye seçilen tip Türkçe yerel ayarda `"14.000"` → 14000, `"0.000"` → boş | Düzeltmenin kendi kapısı BLOCKER |
| V6 | Kapsam koşulu | Kapsamsız bir *"X ÇÜRÜDÜ"* başlığı iki rol tarafından genellendi; aynı sayfada koşul yazılıydı | Yanlış kanal seçildi, bir tur kayboldu (2026-07-31) |
| V7 | Çelişki | Yeni paket şablonundaki obje öneki adlandırma standardıyla farklıydı | 3 kez elle düzeltildi |
| V8 | NE ZAMAN | Liderin ÖNCE-ARA tetik listesinde *"başarısız bir denemeden sonra aynı amaçla yeniden denerken"* yoktu | Bir araç sorunu ~2 saat / 12 denemeyle kovalandı; cevap yazılıydı |

Kural netliği örneklemi (aynı tur): incelenen kuralların çoğu **kısmen net** çıktı; en sık düşen iki
alan **NEREDE** ve **NE ZAMAN**.

## 6. ADR 0019 İLE İLİŞKİSİ (çakışma yok — tamamlayıcı)

ADR 0019 §5 kuralın **zorlama** biçimini (güç etiketi, gate mi yargı mı, stabil ID, kapsam denetimi),
§5A metin **kalitesini** (8 ölçüt) belirler. Bu standart onların yerine geçmez; ikisinin karşılamadığı
iki boşluğu doldurur:
- **NE ZAMAN**: §5A ölçüt 4 *"kapsam-belli"* rolü/koşulu sorar ama **eylemi** (hangi yazım anında) sormaz.
- **NEREDE**: §5A'da yok — kural iyi yazılmış ve doğru gate'lenmiş olup yine de uygulayacak rolün
  okuma yolunda olmayabilir (§5 V1).

Eşleşme: NE ↔ ölçüt 1 + 3 · NEDEN ↔ ölçüt 6 · olumsuz iddia kapsam koşulu (§2) ↔ ölçüt 4 ·
çelişki testi (§4.3) ↔ ölçüt 8 · tek cümlelik ikinci kanal ↔ ölçüt 5.

## 7. İLGİLİ

- `governance/decisions/0019-kural-enforcement-mimarisi-3-eksen-coverage-check.md` §5 / §5A
- `playbook/howto-talimat-dosyasi-bakimi.md` — talimat dosyalarına dokunma akışı (bu standart orada bir adımdır)
- `playbook/lessons-learned.md` ders (g) — çürütme notu koşuludur
- `CLAUDE.core.md` §4 ÖNCE-ARA — kural yazmadan önce "zaten yazılı mı"
- ADR 0019 — yeni gate açma moratoryumu (bu standart gate değildir; kural metni + yazan disiplini)
