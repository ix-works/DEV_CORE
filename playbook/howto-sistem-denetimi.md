---
applies_to: [all]
---

# HOWTO — Sistem Denetimi Runbook'u (envanter + hata-tekrarı + verimlilik + sadeleştirme)

> **Ne:** Core+proje katmanlarının TAM denetimi — envanter, hata-tekrarının kök sebebi,
> yavaşlamanın ölçülmüş sebebi, mükerrer/çelişik içerik, öneri kataloğu, uygulama ve kalıcılık.
> **İlk örnek:** 2026-07-31/08-01 turu (çıktıları proje reposunda:
> `governance/DENETIM-<tarih>-envanter-ve-verimlilik.md` + `...-UYGULAMA-PLANI.md`).
> **Bu dosya ≠ content-health-radar:** radar = aylık 1-2 saatlik süpürme; BU = dönemsel
> (6-12 ay / tetikleyici-durumda) 2-3 günlük derin tur.
>
> **KULLANIM (kullanıcı prompt'u):** `core/playbook/howto-sistem-denetimi.md dosyasını oku ve
> bu denetim turunu baştan sona uygula` — başka açıklama gerekmez; eksik kararlar AŞAĞIDAKİ
> onay-anlarında sorulur.

## 0. NE ZAMAN KOŞULUR (tetikleyiciler)
Kullanıcı istedi · ajanlar bilinen hataları YİNE tekrarlıyor hissi · iş süreleri bariz uzadı ·
radar trend tablosu 2+ turdur kötüleşiyor (§8 kalıcılık-raporundaki 4 soru cevapsız) ·
büyük mimari değişiklik/harness-sürüm sıçraması sonrası.

## 1. ÖN KOŞULLAR (başlamadan)
- **Yeni-taze oturum** başlat (ajan-tanımları oturum-başında yüklenir — bayat-tanım ölçümü kirletir).
- Kullanıcıdan: **tam yedek alındı mı** · VPN/SAP erişimi gerekiyorsa AÇIK mı · SAP-canlı test
  gerekirse hangi **paket + transport** (örn. Z<mod>000 sandbox + kullanıcının verdiği TR).
- **Paralel-oturum kontrolü:** core+proje `git status/branch` — başka oturumun merge-edilmemiş
  branch'i varsa ÖNCE kullanıcıyla sırala (ders: rapor dosyası paralel oturumun alakasız
  commit'ine süpürülmüştü; core branch'i 8 commit öndeydi → önce merge kararı alındı).
- Keşif fazı **plan-mode/salt-okunur** yürütülür; rapor+plan dışında dosya değişmez.

## 2. FAZ A — PARALEL KEŞİF (3-4 Explore/research ajanı, TEK mesajda)
Sabit 4 eksen (her brife: kanıt-kuralları bloğu + `path=core/` talimatı + "sayı ver, sıfat verme"):
1. **Enforcement yüzeyi:** hook/validator/gate/MCP-guardrail envanteri — tetik→script→blok
   tablosu + ölü/kablosuz olanlar + koşum-maliyet notları.
2. **Bilgi katmanı + mükerrerlik:** her-oturum yüklenenler (satır/KB) + on-demand kütle +
   çok-kopyalı kurallar (kopya SAYISI + yerleri) + aktif çelişkiler + süperseded-damgasızlar.
3. **Ajan maruziyeti:** rol×kanal matrisi (auto-memory/CLAUDE/rules/hooks/ITG alt-ajana
   ulaşıyor mu — KANITIYLA) + overlay↔kanonik drift (hash) + model beyanları.
4. **Vaka kronolojisi:** SESSION_NOTES + lessons-learned + ADR'lerden "yaşanmış hata → önlem →
   TEKRAR ETTİ Mİ" tam listesi; özellikle **"önlem alındı ama yine yaşandı"** altın listesi.

## 3. FAZ B — TAZE ÖLÇÜMLER (lider; #18: ESKİ RAPOR SAYISI KULLANILMAZ, hepsi yeniden ölçülür)
| Ölçüm | Nasıl |
|---|---|
| Hook birim-maliyeti | sentetik payload × 5 tekrar, medyan (`echo '<json>' \| python scripts/hook_shim.py <hook>`) |
| Validator zinciri | `time run_all --quick` + validator-başına ayrı-süreç dökümü + `run_review --task class_push` |
| Negatif-test örneklemi | ≥4 gate'e bozuk/temiz fixture (scratchpad'de; repo kirletme) — "koştu ≠ baktı" kontrolü |
| **Ajan duvar-saati** | `python core/scripts/agent_time_report.py` (+ gerekirse gün-filtreli) — süre-ayrışması/batch/tekrar-okuma/model-dağılımı |
| Yüklenme gerçeği | `.tmp/instructions-loaded.log` analizi + inspector koşumu + **deneme-spawn echo testi** (kural alt-ajanda VAR mı) |
| Guard FP'si | tur sırasında yaşanan her yanlış-blok KAYDEDİLİR (kendisi bulgudur) |

## 4. FAZ C — RAPOR (tek dosya: `governance/DENETIM-<tarih>-envanter-ve-verimlilik.md`)
Zorunlu iskelet (ilk örnekteki bölüm yapısı): **§0** yönetici özeti (3 soruya nicel cevap +
ilk-5 aksiyon) · **§1** envanter · **§2** vaka tarihçesi (önlem-türü×tekrar tablosu + altın
liste) · **§3/3B/3C** bulgular (tekrar-kökü zinciri / yavaşlama-ölçümlü / mükerrerlik-çelişki)
· **§4** her-oturum-yüklenen dosyaların içerik-sağlığı + sürekli-ölçüm yöntemi · **§5** öneri
kataloğu — HER maddede ZORUNLU şablon: *tespit → ne → nasıl → olumlu etki → YAN ETKİ/risk →
alternatif → öncelik/efor/KATMAN(CORE-PROJE+yayılım)* · **§5C** mekanizma-maddelerine çalışma-
tasarımı: *kurulum → çalışma-anı akışı → İLK doğrulama (kabul testi) → sürekli güvence →
dayanak (resmî doc/referans-repo)* · **§6** yapılmaması-gerekenler (moratoryum/FP-bütçesi/
fail-closed-takası-yasak) · **§7** fazlı yol haritası · **§8** kalıcılık (regresyon
mekanizmaları + başarı ölçütleri) · **Ek-A** ham ölçümler (tarih+komutla) · **Ek-B/C** tam
vaka kronolojisi + ADR-doğuran-vakalar (rapor KENDİNE-YETERLİ olsun; oturum-çıktısına atıf
bırakma) · **Ek-D** envanterin KALEM-KALEM aksiyon kararı (DOKUNMA/DÜZELT/KABLOLA/ATTIC/SİL/
İZLE — docstring-kanıtlı; DOKUNMA'lar da gerekçeli).
**+ İÇERİK-KONTROL TURU ZORUNLU:** rapor bitince baştan sona yeniden oku — ölü §-referansı,
bayat sayım, çapraz-tutarsızlık, kendine-yeterlilik (ilk örnekte bu tur 11 bulgu yakaladı).

## 5. FAZ D — UYGULAMA PLANI (ayrı dosya: `...-UYGULAMA-PLANI.md`)
- Görev-başına: ne/nasıl + **P/N/E testleri ÖNDEN yazılı** + boş alanlar (Yapılan/Test/Kapanış).
- Onay etiketi: `[S]` serbest · `[A]` ADT-infra/davranış-yüzeyi onaylı · `[K]` kullanıcı-kararı.
- **Kapsama-kontrol matrisi:** rapordaki HER öneri+Ek-D kalemi ↔ görev eşlemesi, İKİ TUR
  çapraz-doğrulama (ilk örnekte 2. tur 8 atlama yakaladı) + "bilinçli görevleştirilmeyenler".
- Çalışma ilkesi bloğu: doğruluk>hız · görev-başına tek odak · değişiklik SERİ (paralellik
  yalnız salt-okunur analizde) · test atlanmaz · şüphede dur-sor · küçük PR+yeşil-CI ·
  **atıl-bırakma yasağı** (görev+faz kapanışlarında yetim-artefakt süpürmesi).
- İşbölümü: değişiklik+test=LİDER (paylaşılan tooling) · token-ağır analiz=arka-plan ajanı ·
  içerik-ağır değişikliğe taze bug-expert · bazı kabul testleri doğası gereği deneme-spawn.

## 6. FAZ E — YÜRÜTME
- Onayları TOPLU al (AskUserQuestion, görev-ID'li; sonra otonom) — [K]'lar önden karara bağlanır.
- Faz sırası: temizlik → performans → recall-onarımı → konsolidasyon+güvence → kalıcılık.
- Her görev: uygula → P/N/E koş → plan dosyasına **tarih+komut+kanıt** işle (çıplak "OK"
  geçersiz) → durum etiketi. ⚠ İlk turun dersi: kapanışı başlığa yazıp ALTTAKİ BOŞ ŞABLON
  SATIRINI silmeyi unutma (19 artık kalmıştı).
- Çift-katman işlerde YAYILIM adımı görevin içindedir (core-fix + template/overlay/senkron).
- Beklenmedik durum → yamalamadan DUR: ya kullanıcıya (ekrandaysa) ya kanıtlı-devir kaydıyla
  yeni-oturum listesine (örn. ADT-400 bayat-oturum engeli kontrol-gruplu kanıtla devredildi).

## 7. FAZ F — KAPANIŞ (son check-up ZORUNLU)
1. Plan taraması: `grep "Yapılan/Nasıl: —\|Test sonucu: —\|BEKLİYOR"` → 0 olmalı; çelişen
   çift durum-etiketi kalmamalı.
2. **Disk-kanıt süpürmesi:** Ek-D kararlarının her biri diskte doğrulanır (attic'te mi,
   silinmiş mi, dosya var mı — ilk örnekte 8/8 listesi).
3. Rapor başına **SONUÇ damgası** (tarih + N/N + ölçülen kazanımlar + devirler; gövde
   tarihsel-kayıt olarak DEĞİŞTİRİLMEZ).
4. Memory: proje-kaydı güncelle (durum + varsa yeni-oturum listesi + RESUME çapası).
5. Radar beslemesi: trend tablosuna bu turun sayıları + bilinçli-devirler radar gündemine.
6. İki repo `git status` **0/0** + tüm PR'lar MERGED-doğrulanmış + main'ler senkron.

## 8. GARANTİ ASGARİLERİ (bunlar karşılanmadan tur "bitti" DENEMEZ)
☐ ≥3 paralel keşif ajanı (4 eksen kapsandı) ☐ tüm sayılar bu turda TAZE ölçüldü ☐ ≥4 gate
negatif-testlendi ☐ transcript/ajan-süre analizi yapıldı ☐ deneme-spawn ile en az 1
yüklenme-gerçeği ölçümü ☐ her öneri şablon-alanları eksiksiz + katman-atamalı ☐ mekanizma-
önerilerinde §5C garanti-tasarımı ☐ Ek-D tüm envanteri kapsadı ☐ rapor içerik-kontrol turu
☐ plan kapsama-matrisi 2-tur ☐ kapanışta disk-kanıt süpürmesi + SONUÇ damgası ☐ **karşı-kanıt
disiplini:** ajan bulgusu canlı ölçümle çelişirse ÇÜRÜTÜLDÜ diye yazılır, uygulanmaz
(ilk örnek: "paths→globs" önerisi böyle düşürüldü).

## 8B. ADVERSARIAL TUR — "doğru çalışıyor mu" DEĞİL, "hangi girdide YANLIŞ davranır"
*(2026-08-01'de ilk kez koşuldu; uyum-denetiminin ✅ verdiği bileşenlerde 20 doğrulanmış bulgu
çıkardı, 6'sı KRİTİK — yani **uyum turu bu turun yerini TUTMAZ**, ikisi ayrı işlerdir.)*

**Ayrım.** Uyum turu sorar: kural yazılı mı · kablolu mu · temiz girdi OK · bozuk girdi FAIL.
Adversarial tur sorar: **bu kodu hangi girdi/durum kandırır?** Senaryoyu denetleyen İCAT eder,
sentetik olarak KURAR, ÇALIŞTIRIR, çıktısıyla kanıtlar. Teorik bulgu YOK.

**Kapsam kuralı (ilk turun kendi hatası — tekrarlamayın):** hedef envanteri plandan değil
**taze sayımdan** çıkarılır (`ls`/`glob` ile dosya sayısı). İlk turda plan "45+ validator"
diyordu, gerçek sayı 49 validator + 93 kök script + 7 utils'ti → ilk dağıtım 22 validator'ı
ve ~78 script'i sessizce kapsam dışı bıraktı. Yani **avın kendisi desen-2'ye düştü.**

**15 SALDIRI DESENİ** (her bileşene en verimli 3-5'i seçilir):
1. **Fail-open sapması** — exception/timeout/eksik-dosya/boş-config'te exit 0 mu? *Bir guard'ın
   en tehlikeli arızası bloklamak değil, bloklaması gerekirken sessizce izin vermektir.*
   Buna **"varsayılan en izinli değer"** de dahildir (girdi okunamayınca en serbest moda düşmek).
2. **Sessiz-kapsam-kaybı** — 0 dosya tarayıp "OK" diyor mu? (dizin yok · yanlış kök · prune fazla
   geniş · uzantı eşleşmiyor). Sorulacak soru: **"kaç dosya taradığını söylüyor mu?"** Söylemiyorsa
   bu sınıfa açıktır.
3. **Yanlış-pozitif** — meşru girdiyi blokluyor mu? (yorum-içi token · string-literal · çok-satırlı
   komut · POSIX/UNC yol · boşluklu yol · yerel karakterler · CRLF). FP ucuz değildir: *atlatma
   refleksi* doğurur.
4. **Girdi uç-durumları** — boş dosya · yalnız-BOM · çok büyük dosya · binary · symlink/junction ·
   silinmiş dosya · eşzamanlı değişen dosya.
5. **Payload sözleşmesi** — eksik alan · null · yanlış tip · beklenmedik yeni alan · kesik payload ·
   non-UTF8 bayt.
6. **Eşzamanlılık/yarış** — iki hook aynı anda · paralel yazımlar · marker/log dosyasına eşzamanlı
   append (*"O_APPEND atomiktir" iddiası ölçülmeden kabul edilmez*).
7. **Sıra/idempotans** — iki kez koşunca fark? · yarıda kesilirse tutarsız state?
8. **Yol/platform** — junction arkası · göreli-vs-mutlak · başka cwd'den koşum · sürücü harfi.
9. **Regex kaçışı** — kuralın hedefini YAPAN ama yakalanmayan yazım: satıra bölünmüş ifade ·
   satır-sonu (trailing) yorum · alternatif tırnak (backtick/template literal) · kısa-vs-uzun
   bayrak biçimi (`-m` ↔ `-am`, `-F` ↔ `--file=`) · büyük/küçük harf · rakam soneki.
10. **Zaman** — bayatlık eşiğinin tam sınırı · gelecek tarih · aynı gün.
11. **Sayı/ölçüm** — off-by-one · sıfıra bölme · boş kümede yüzde/medyan.
12. **Bağımlılık kaybı** — ağ/SAP/git/node/env yok → nazikçe mi, çökerek mi, sessizce mi?
13. **Çıktı sözleşmesi** — exit kodu mesajla çelişiyor mu · stdout/stderr karışması · yönlendirilince
    sıra bozulması · non-ASCII konsolda çökme.
14. **Guard atlatma** — zincir (`&&`/`;`), env-öneki, alias, `sh -c`, çok-satır. *Zincirde bir
    segmentin sağladığı şart, sonraki segmenti serbest bırakıyor mu?* YALNIZ tespit amaçlı.
15. **Kendi-kendini doğrulama** — aletin canary'si gerçekten kırmızı yanabiliyor mu? Fixture'ın
    beklentisini TERSİNE ÇEVİR: test hâlâ PASS diyorsa test sahte-güvencedir.

**Yöntem.** Aile başına bir avcı (`bug-expert`, read-only), paralel fan-out; brif = spawn-brief
şablonu + bu katalog + şu şart: *repro komutu ve gerçek çıktı (exit kodu dahil) olmayan bulgu
rapora giremez.* Her avcı kendi bulgusunu önce çürütmeye çalışır.

**Lider doğrulaması ZORUNLU — ve kontrol grubuyla.** İlk turda liderin ilk üç repro denemesi
harness hatası yüzünden validator'ı hiç tetiklememişti; kontrol grubu olmasaydı üç sahte bulgu
yazılacaktı. **Kural: "kaçıyor" demeden önce, yakalandığı BİLİNEN varyantın aynı harness'ta
yakalandığını göster.** (PATTERN #19'un adversarial karşılığı.) Kapsamı daralan/genişleyen
bulgular "ELENDİ" değil "KAPSAM DÜZELTİLDİ" satırına yazılır — dürüstlük kaydı silinmez.

**Kapanış.** Doğrulanan her bug için kalıcı fixture (G1 korpusu) + changelog satırı +
test-reçetesi. Fixture'a dönüşmeyen bulgu, bir sonraki turda yeniden keşfedilir.

## 9. TUR-BAŞI İYİLEŞTİRME ÖNERİLERİ (runbook'un kendisi de evrilsin)
- **DELTA bölümü:** önceki denetim raporuyla kıyas — altın-listeye YENİ giriş var mı (kalıcılık
  §8.4-soru-3), hangi eski öneriler tuttu/tutmadı.
- Tur sonunda bu runbook'u GÜNCELLE (yeni öğrenilen adım/tuzak buraya işlenir — T1 trigger).
- Radar Bulgu-Log'ları + removed-controls sözlüğü tur-öncesi okunur (bağlam + sahte-koruma grep'i).
- Ölçüm scriptleri eskidiyse (agent_time_report, inspector) önce onların self-test'i.
