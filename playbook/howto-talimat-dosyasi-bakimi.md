---
applies_to: [all]
---

# HOWTO — Talimat-Dosyası Bakımı (CLAUDE.md · rules · auto-memory)

> **Kim:** kuyruk-tipi bakım = infra-expert (lider-açtığı worktree'de) · teşhis/ölçüm + son söz +
> canlı memory'ye yazma = **lider**. EXPRESS (bloklayan) işler bu howto'nun dışıdır (lider, anında).
> **Neden var (2026-08-12):** her oturum yüklenen talimat yüzeyi ölçüldü — bir rules dosyasında
> %55 blok-tekrarı, indeks dosyasında %26 durum-sızması birikmişti; kimse tek tek dosyayı
> bütün olarak görmediği için 3 ayrı oturumun eklemeleri sessizce üst üste binmişti.

## SINIR — bu dosyalarda NE YAPILMAZ (önce oku)

| # | Yasak/Sınır | Neden |
|---|---|---|
| S1 | **Damgalı KESİN YASAKLAR bloğuna dokunma** (kök CLAUDE.md fiziksel damga + kanonik) | ADR 0021: duplikasyon TASARIM GEREĞİ; naif dedup onunla savaşır. Drift'i `check_kesin_yasaklar` + `sync_yasaklar.py` yönetir |
| S2 | **Davranış değişmezi skill'e/başka yere İNDİRİLMEZ** — CLAUDE.md/rules'ta kalır | Alt-ajanlar auto-memory'yi ve skill'leri görmez, CLAUDE.md kopyası alır → taşınan değişmez alt-ajanlarda SESSİZCE kaybolur |
| S3 | **Her-oturum-gerekli kural `paths:`li rules dosyasına taşınmaz** | `paths:` tembel yükleme bozukken (üst harness #17204) fark yok; DÜZELİRSE kural aniden koşullu olur ve eşleşmeyen oturumlarda yüklenmez |
| S4 | **Silme değil BİRLEŞTİRME** — tekrar bloklarında kopyalar diff'lenir, birleşim korunur | Ölçülmüş vaka: 3 kopyadan biri sapmıştı (fazladan satır); körlemesine silme kural kaybettirir |
| S5 | **MEMORY.md durum tutmaz** — proje durumu kanonik defterlere (governance) | Durum iki yerde yaşarsa biri bayatlıyor; indeks bütçesi (200 satır/25KB) durum taşımaya harcanmaz |

## AKIŞ (her bakım turu)

```
① ÖLÇ    → dokunmadan önce: satır/bayt + blok-tekrar (bölüm-hash) + hangi kopya kanonik.
           Rakamlar rapora yazılır — "büyüktü" değil, "407 satır / %55 tekrar".
② PLANLA → her tekrar kümesi için: kopyalar birebir mi (hash) / sapma var mı (diff)?
           Sapma varsa BİRLEŞİM metni çıkar. Hangi bölüm kanonik kalacak işaretle.
③ UYGULA → worktree'de (repo dosyaları) ya da memory-git BRANCH'inde (auto-memory).
           Canlı `~/.claude/...`'a doğrudan yazma — memory işi: branch → diff → LİDER merge.
④ KANITLA→ zorunlu dörtlü:
           (a) bayt/satır DELTA raporu (önce→sonra),
           (b) birleşim-hash kanıtı (birleşen bölümlerin içerik kaybı yok),
           (c) run_all_validators yeşil (özellikle C-MEM-01 · check_kesin_yasaklar),
           (d) ERTESİ OTURUM: InstructionsLoaded log'unda dosyanın yüklendiği satır
               (kayıpsız logger 2026-08-12'den beri güvenilir) — bu kanıt lider'de kalır.
⑤ KAYDET → infra-changelog satırı (B11 talimat-dosyalarını da kapsar, 2026-08-12'den beri).
```

## MEMORY-ÖZEL KURALLAR

- Auto-memory dizini **kendi private git'ine** sahiptir (kurulum 2026-08-12) → bakım DAİMA
  branch üzerinden; lider diff okuyup merge eder; her merge sonrası **remote'a push**.
- **Erişilebilirlik zinciri tam 2 seviyedir** (ölçüldü, `check_memory_index._butunluk`):
  `MEMORY.md →(md-link)→ dosya →([[wiki]])→ dosya`. Konu-dosyası indeksi kurarken yaprak
  linkler `[[wiki]]` formatında olmalı; 3. seviye zincir validator'ı FAIL'ler.
- Frontmatter + blok HTML yorumları yükleme bütçesine SAYILMAZ (üst harness ≥2.1.211) —
  bakım notları oraya bedava yazılır. ⚠ C-MEM-01'in ölçüm modeli de aynı semantiğe
  hizalanmış olmalı (K2 düzeltmesi); değilse validator sahte alarm verir.
- Hatıra SİLİNMEZ; bayatlayan kayıt ya kapanış şerhi alır ya komşusuyla birleştirilir.
  Silme yalnız kullanıcı kararıyla.

## ÖLÇÜM ARAÇLARI

- `check_instruction_budget.py` (C-BUD-01, warn-first) — satır/bayt + blok-tekrar.
- `check_memory_index.py` (C-MEM-01, HARD) — bütçe + ölü link + erişilebilirlik + frontmatter.
- Bölüm-hash kıyası: `## ` başlıklarına böl → gövde md5 → aynı başlığın kopyaları
  BİREBİR mi SAPMA mı (sapmada `difflib` ile birleşim çıkar).

> Gate durumu: HARD bütçe gate'i bilinçli AÇIK DEĞİL (moratoryum şart-4). Tarihli karar
> tetiği proje `deferred-triggers`'ında (≈2026-09-09 radar: taban temiz + nüks → terfi).
