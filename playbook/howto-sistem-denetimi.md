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

## 9. TUR-BAŞI İYİLEŞTİRME ÖNERİLERİ (runbook'un kendisi de evrilsin)
- **DELTA bölümü:** önceki denetim raporuyla kıyas — altın-listeye YENİ giriş var mı (kalıcılık
  §8.4-soru-3), hangi eski öneriler tuttu/tutmadı.
- Tur sonunda bu runbook'u GÜNCELLE (yeni öğrenilen adım/tuzak buraya işlenir — T1 trigger).
- Radar Bulgu-Log'ları + removed-controls sözlüğü tur-öncesi okunur (bağlam + sahte-koruma grep'i).
- Ölçüm scriptleri eskidiyse (agent_time_report, inspector) önce onların self-test'i.
