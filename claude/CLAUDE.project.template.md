# CLAUDE.md — <PROJECT_NAME> (ince proje loader'ı)

<!-- KESİN YASAKLAR bloğu init_project tarafından buraya FİZİKSEL damgalanır (junction-
     bağımsız daima yüklü). Metodoloji çekirdeği bu dosyadan import EDİLMEZ — aşağıya bak. -->

> **Metodoloji çekirdeği (protokol, SORU 0, gate'ler) bu dosyadan `@import` ile YÜKLENMEZ**
> (Q286, 2026-09-12): `core/` junction'ının ardındaki dosya harness için DIŞ import'tur ve
> onaysız sessizce atlanır. Çekirdek, `team_setup.py`'nin ürettiği **fiziksel kopya**
> `.claude/rules/00-claude-core.md` olarak her oturum yüklenir (`paths:` yok). Bu dosyaya
> `@core/...` satırı EKLEME. Yükleme durumunu `session_start`'ın `[YUKLEME — session_start]`
> satırı söyler — "yüklendi" diye kendin beyan etme, o satırı aktar.
> **Yasaklar yukarıda fiziksel damgalıdır — import'a bağlı değil** (`check_kesin_yasaklar`
> guard'ı damganın kanonikle eşliğini zorlar).
> **Bu dosyada YALNIZ proje-özel bilgi durur.** Metodoloji buraya YAZILMAZ (SORU 0 → core).
> Not: Metodoloji dosyaları `core/` junction'ı altındadır; core dokümanlarındaki göreli
> yollar CORE köküne göredir. **Metodoloji araması DAİMA `path=core/` ile** (kök-Grep
> core'u görmez — D29).

## PROJE KİMLİĞİ

- **Profil:** `project.yaml` → `sap_profile: <ecc|s4_private|s4_public|btp_abap>` ·
  `release: "<REL>"` · `master_language: <ML>` · `source_root: <SOURCE_ROOT>`
- **SAP bağlantı:** `<PROJECT_ROOT>/.conn_adt` — Sistem: `<SYSTEM_ID>`, Client `<CLIENT>`,
  User: `<SAP_USER>`
- **Kaynak kod:** `<SOURCE_ROOT>/<MODULE>/<PKG>/` (L4 kuralları: her pakette `.rules.md`)

## PROJE-ÖZEL DOSYA İNDEKSİ

| Konu | Dosya |
|---|---|
| Paket listesi (auto-generated) | `governance/package-registry.md` |
| Proje ADR'leri (`<PROJE>-NNN` serisi) | `governance/decisions/` |
| Ertelenmiş iş tetikleri | `governance/deferred-triggers.md` |
| Proje-özel pattern/standart overlay | `playbook-local/` · `standards-local/` |
| Proje-özel validator'lar | `scripts/validators-local/` |

## PROJE-ÖZEL KURALLAR / AKTİF İŞ KÜLTÜRÜ

<!-- Proje-özel gate'ler, dondurulmuş-kök notları (DİSİPLİN kuralı — runtime guard YOK;
     `frozen_readonly_paths` ölü anahtardır, yazma), aktif sprint kültürü, müşteri-özel
     kısıtlar BURAYA. Örnek satırlar silinip doldurulur. -->

# Compact instructions

<!-- Harness bu başlığı compact özetinin talimatı olarak okur. Bölüm PROJE CLAUDE.md'sinde
     yaşar (core kopyasına taşınmaz). "Özete ALMA" listesi ÖLÇÜME bağlıdır — ölçülmemiş bir
     dosyayı "zaten geri geliyor" diye ekleme (Q286 M6, 2026-09-12). -->

Varsayılan özet bölümlerini KORU; aşağıdakileri onların içine ekle.

Öncelik sırasıyla KORU — kaybolursa geri getirilemez:
1. Yarım kalan SAP işlemi: hangi obje, push edildi mi, aktive edildi mi,
   transport / kilit / ATC durumu.
2. Bu oturumda ÖLÇÜLEN sonuçlar: sayı + birimi + kaynağı (`dosya:satır` ya da
   çalıştırılan komut). Niteleyiciyi DÜŞÜRME — "alt kırılımda boş" ≠ "hepsinde boş".
3. Alt ajanların döndürdüğü raporlar ve kullanıcının AskUserQuestion cevapları —
   özetleme, aynen taşı.
4. Değiştirilen dosyaların listesi + o değişikliği doğrulayan komut
   (validator / ATC / test) ve sonucu.
5. Verilen kararlar + GEREKÇESİ; açık kalan sorular; denenip çalışmayan yollar ve nedeni.
6. Aktif paket adı; koşan alt ajan varsa hangisi ve ne görev verildiği.

Emin olmadığın bir şeyi kesinmiş gibi yazma: "DOĞRULANMADI" diye etiketle.

Özete ALMA — compact sonrası zaten geri geliyor: CLAUDE.md kuralları ve yasaklar,
çekirdek kopyası `.claude/rules/00-claude-core.md` (ölçüldü: compact sonrası
`load_reason=compact` ile yeniden yüklenir — print modu, tek ölçüm), hook / system-reminder
çıktıları, skill ve araç listeleri.

⚠ `paths:`'li kurallar compact'ta yeniden yüklenMEZ; eşleşen bir dosya yeniden okununca
geri gelir. Yarım iş böyle bir kurala dayanıyorsa özete kuralın ADINI ve tetikleyen dosyayı al.
