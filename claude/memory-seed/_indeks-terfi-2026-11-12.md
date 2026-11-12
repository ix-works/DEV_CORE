---
name: _indeks-terfi-2026-11-12
description: 2026-11-12 tohum terfisi (11 ders, kuyruk Q407 A+C) — konu başlıklarıyla gruplu tam indeks
metadata: 
  node_type: memory
  type: reference
---

# 2026-11-12 tohum terfisi — tohum indeksi

> Bu dersler mevcut konu hub'larına DEĞİL bu dosyaya yazıldı: kurulu bir makinede hub yerelde
> düzenlenmişse tohumlama onu EZMEZ ⇒ oraya eklenen satır o makineye ulaşmaz. Yeni bir hub dosyası
> ise her makineye kopyalanır ve `MEMORY.md`'deki tek satırını `seed_memory` indekse ekler
> (2026-10-18 terfisinin emsali). Vaka anlatımları genericize edildi; paket/obje adları temsilîdir.
> Üç ders (Türkçe iletişim · test için açık onay · exit include'unda az yorum) **kullanıcı kararıyla
> tüm core kullanıcılarına** uygulanır (2026-11-12).

**11 ders.** Karar 4 · Ajan 2 · Araç 2 · SAP 2 · UI 1

## Karar · iletişim

- ⭐ [Kullaniciya her mesaj turkce](feedback_kullaniciya-her-mesaj-turkce.md) — Kullanıcıya giden HER metin Türkçe — ara durum bildirimleri ve kısa notlar dahil (kullanıcı kararı: tüm core kullanıcıları)
- ⭐ [Test yazmadan once acik onay](feedback_test-yazmadan-once-acik-onay.md) — Yeni SAP uygulama testi (ABAP Unit/karakterizasyon) yazmadan ÖNCE kullanıcıdan AÇIK ONAY — varsayılan testsiz; mevcut testi koşmak serbest (kullanıcı kararı: tüm core kullanıcıları)
- [Is parametresini koda gomme onerme](feedback_is-parametresini-koda-gomme-onerme.md) — Kullanılan iş parametresini (eşik, yüzde, süre) koda sabit gömmeyi ÖNERME — kullanılıyorsa ayar tablosunda kalır, gereksizse alan+mantık kaldırılır
- [Isaret sozdizimi onermeden once prior art ara](feedback_isaret-sozdizimi-onermeden-once-prior-art-ara.md) — Kaynağa konacak işaret/sözdizimi (yorum işareti, pragma) ÖNERMEDEN önce o obje tipinin playbook'unda prior-art ara — yapı DDL'i `//` kabul etmez, SAP yorumu siler

## Ajan · takım

- [Infra brifinde kardes kipleri kod dondu oncesi](feedback_infra-brifinde-kardes-kipleri-kod-dondu-oncesi.md) — Paylaşılan modül/validator değiştiren infra brifinde KOD DONDU öncesi kardeş fixture'ların TÜM kiplerini (`run_battery --kardes-tam`) koşturmayı açıkça iste
- [Kapi raporu kaydi verify report tuzaklari](feedback_kapi-raporu-kaydi-verify-report-tuzaklari.md) — Bug-gate raporunu kaydedip `checklist_check --verify-report` koşarken: tam metin alt-ajan jsonl'ında · `--repo .` şart · gruplu hüküm satırı 'satır yok' · repo dışı `--files` glob'a girmez

## Araç tuzakları

- [Python ile dosya duzenlerken bayt kipi kullan eol korunur](feedback_python-ile-dosya-duzenlerken-bayt-kipi-kullan-eol-korunur.md) — Repo dosyasını Python'la yerinde düzenlerken metin kipi CRLF'yi LF'ye çevirir, tek CR'yi satıra böler ⇒ tüm dosya diff'i; bayt kipi + `bytes.replace`
- [Seed alanina satir ici yorum yazma](feedback_seed-alanina-satir-ici-yorum-yazma.md) — `metadata.seed:` değerinin yanına satır içi yorum yazma — `--terfi-adaylari` satırı okuyamaz, ders sessizce '<YOK>' kovasına düşer

## SAP · ABAP

- ⭐ [Exit include e az yorum](feedback_exit-include-e-az-yorum.md) — Exit include'una uzun yorum YAZMA — çağrı başına en çok tek kısa satır; gerekçe TS'te (kullanıcı kararı: tüm core kullanıcıları)
- [Fugr include push fugr i yolu tmg olay](feedback_fugr-include-push-fugr-i-yolu-tmg-olay.md) — Fonksiyon grubu include'u (SE54 TMG olay include'u) programs/includes yolundan yazılamaz (403 TK 103) — FUGR/I yolu + 4 ölçüm; TMG olay 01 iptal deseni S DISPLAY LIKE 'E' + vim_abort_saving

## UI

- [Deploy ui yarida kesilince bsp yine yaratilmis olabilir](feedback_deploy-ui-yarida-kesilince-bsp-yine-yaratilmis-olabilir.md) — deploy_ui yarıda kesilse de BSP/SICF yaratılmış ve göreve yazılmış olabilir — TADIR/E071 ile ölç, baştan deploy + `--verify-only`

<!-- makine-okunur erişilebilirlik çapası (C-MEM-01): indeks bütünlüğü kapısı
     cift-koseli-parantez linki arar, markdown link saymaz. Liste yukarıdakiyle AYNI olmalı. -->
[[feedback_kullaniciya-her-mesaj-turkce]] · [[feedback_test-yazmadan-once-acik-onay]] · [[feedback_is-parametresini-koda-gomme-onerme]] · [[feedback_isaret-sozdizimi-onermeden-once-prior-art-ara]] · [[feedback_infra-brifinde-kardes-kipleri-kod-dondu-oncesi]] · [[feedback_kapi-raporu-kaydi-verify-report-tuzaklari]] · [[feedback_python-ile-dosya-duzenlerken-bayt-kipi-kullan-eol-korunur]] · [[feedback_seed-alanina-satir-ici-yorum-yazma]] · [[feedback_exit-include-e-az-yorum]] · [[feedback_fugr-include-push-fugr-i-yolu-tmg-olay]] · [[feedback_deploy-ui-yarida-kesilince-bsp-yine-yaratilmis-olabilir]]
