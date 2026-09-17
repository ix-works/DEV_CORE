---
name: _indeks-ajan-takim
description: Alt-ajan ve takım yönetimi derslerinin tam indeksi
metadata: 
  node_type: memory
  type: reference
---

# Ajan · takım yönetimi — tohum indeksi

> Alt-ajan brifingi, kapsam, rapor ve paralel çalışma disiplini. Bu dosya `MEMORY.md`'den link'lenir; dersler burada yaşar.

**19 ders.**

- [Adt readback md5 disk md5 ile dogrudan kiyaslanamaz](feedback_adt-readback-md5-disk-md5-ile-dogrudan-kiyaslanamaz.md) — ADT readback md5'i disk md5'iyle DOĞRUDAN kıyaslanamaz — payload kapanış \n'ini taşımaz; ayrıca sap_sync_pull .ccimp'i hiç tazelemez
- ⭐ [Ajan bulgusu dogru mekanizmasi yanlis](feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis.md) — Ajanın POZİTİF bulgusunu kabul ederken GEREKÇESİNİ ayrı ölç — bulgu doğru, mekanizma yanlış olabilir; yanlış mekanizma kayda geçerse sonraki okuyucu yanlış yerde arar
- ⭐ [Ajan kurali brifingde degil taniminda yasar](feedback_ajan-kurali-brifingde-degil-taniminda-yasar.md) — Her yeni ajanın tekrarladığı bir hata varsa kural brifingde değil ajan TANIMINDA eksiktir — brifing uçucu, tanım kalıcıdır
- [Ajan model secimi olculdu ayri politika yazilmadi](feedback_ajan-model-secimi-olculdu-ayri-politika-yazilmadi.md) — Alt-ajanları iş-tipine göre ucuz modele indirme fikri 2026-08-29'da ÖLÇÜLDÜ ve BİLİNÇLİ olarak yapılmadı: kazanç tavanı %4-8, hata maliyeti asimetrik. Tekrar açmadan önce bu kaydı oku
- ⭐ [Brifinge koydugun yolu once kendin kos](feedback_brifinge-koydugun-yolu-once-kendin-kos.md) — Spawn brifingine yazdığın dosya yolu/komut bir İDDİADIR — göndermeden önce kendin koş; yanlış yol o ekseni SESSİZCE koşmamış bırakır
- ⭐ [Calisan ajanin dosyasi ucus halindedir iddia degil soru](feedback_calisan-ajanin-dosyasi-ucus-halindedir-iddia-degil-soru.md) — Çalışan bir ajanın dosyasında gördüğün eksik, İDDİA değil SORU olarak gönderilir — editör diagnostiği/grep anlık bir kesittir ve ajan gövdeyi yazıp import'u sonra ekler. Uçuş hâlindeki dosya durumu sonuç değildir.
- ⭐ [Dokuman turu donmus kod ister paralel kosturma](feedback_dokuman-turu-donmus-kod-ister-paralel-kosturma.md) — Doküman turu (FS/TS/KD + ekran görüntüsü) DONMUŞ koda bağlıdır. Kod düzeltme turuyla PARALEL koşturulursa aynı bedel üç kez ödenir: md5 çapası bayatlar, satır referansları kayar, ekran görüntüleri yeniden çekilir. Duvar saatinden kazanmaz, kaybettirir.
- [Infra expert spawn ad verme](feedback_infra-expert-spawn-ad-verme.md) — infra-expert'i spawn ederken ASLA custom `name` verme — guard kimliği `agent_type`'tan okur, `name` onu ezer ve muafiyet düşer; ajan hiçbir infra dosyasına yazamaz
- [Infra turunda yeni acilan maddeye baslama mevcutlari bitir](feedback_infra-turunda-yeni-acilan-maddeye-baslama-mevcutlari-bitir.md) — İnfra kuyruk turunda o tur içinde yeni açılan maddelere başlanmaz; önce mevcut (tur başında açık olan ve uçuştaki) maddeler bitirilir
- ⭐ [Kapi kosarken dosya donar md5 teyidi](feedback_kapi-kosarken-dosya-donar-md5-teyidi.md) — Bug-gate koşarken artefakt DONAR; dondurma liderin ölçümüyle değil ÜRETİCİNİN md5 teyidiyle başlar — yoksa kapı bayat sürüm ölçer
- ⭐ [Kardes taramasi spawn oncesi kapsama alinir kuyruga yazilmaz](feedback_kardes-taramasi-spawn-oncesi-kapsama-alinir-kuyruga-yazilmaz.md) — Kuyruk maddesi düzeltilmeden ÖNCE kardeş dosya taraması yapılır ve aynı sınıftaki vakalar KAPSAMA alınır; ajana \"kardeşleri raporla, düzeltme\" dersen kuyruk hiç yakınsamaz
- [Lider ajan paralel yazim cakismasi](feedback_lider-ajan-paralel-yazim-cakismasi.md) — Ajan çalışırken lider aynı dosyaya yazarsa sessiz çakışma olur — devralmadan ÖNCE ajanı durdur ve durduğunu doğrula
- [Paralel infra pr ortak dosya rebase sonrasi tam suit](feedback_paralel-infra-pr-ortak-dosya-rebase-sonrasi-tam-suit.md) — Paralel infra ajanları aynı core dosyalarına dokunuyorsa: kardeş PR merge olunca tam süit REBASE'Lİ HEAD'de koşar (KOD DONDU → HAZIR-REBASE → lider rebase → ajan süit); reçete/B-numarasını baştan ayır
- ⭐ [Performans onerisi de bir iddiadir maliyeti once olc](feedback_performans-onerisi-de-bir-iddiadir-maliyeti-once-olc.md) — Bir hızlandırma önerisi de ölçülmemiş bir iddiadır. Maliyetin NEREDE olduğunu ölçmeden kaldıraç önerme — 'rapor uzunluğu' gibi göze çarpan kalem çoğu zaman gürültüdür; ölçüm aracı zaten repoda olabilir.
- [Sendmessage gorevi sessizce islenmemis olabilir](feedback_sendmessage-gorevi-sessizce-islenmemis-olabilir.md) — Ajanın çıktısı henüz yokken 'görev işlenmedi' sonucuna atlama — çalışıyor olabilir; yeniden tetiklemeden önce ajandan ilerleme kanıtı iste
- [Spawn brifinde sablonun kanonik basliklarini kullan](feedback_spawn-brifinde-sablonun-kanonik-basliklarini-kullan.md) — Spawn brifi lint'i İÇERİĞİ değil BAŞLIK METNİNİ arar; şablonun kanonik başlıklarını birebir kullan
- ⭐ [Standing ajani bos bekletme tek tam brif](feedback_standing-ajani-bos-bekletme-tek-tam-brif.md) — Bir ajan koşusunun takvim süresinin %40-60'ı liderden mesaj BEKLEMEKTİR (ölçüldü 2026-08-29, 30 gün): gateway 36 dk, frontend 31, backend 21 dk/koşu. Ajan yavaş değil, lider parça parça besliyor. Kural: scoped spawn + kapat; standing zorunluysa (gateway) işi TEK TAM paketle ver
- ⭐ [Worktree kapatmadan once ajanin nihai raporunu al](feedback_worktree-kapatmadan-once-ajanin-nihai-raporunu-al.md) — Merge sonrası worktree'yi kapatmadan önce ajanın NİHAİ raporunu al — \"completed\" bildirimi, SendMessage ile yeniden uyanıp arka plan süiti koşan ajanı kapsamaz
- [Yeni mcp tool agent allowlist guncelle](feedback_yeni-mcp-tool-agent-allowlist-guncelle.md) — Yeni MCP tool eklenince agent allowlist'leri OTOMATİK güncellenmez; read-only'leri elle propagate et

<!-- makine-okunur erişilebilirlik çapası (C-MEM-01): indeks bütünlüğü kapısı
     cift-koseli-parantez linki arar, markdown link saymaz. Liste yukarıdakiyle AYNI olmalı. -->
[[feedback_adt-readback-md5-disk-md5-ile-dogrudan-kiyaslanamaz]] · [[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] · [[feedback_ajan-kurali-brifingde-degil-taniminda-yasar]] · [[feedback_ajan-model-secimi-olculdu-ayri-politika-yazilmadi]] · [[feedback_brifinge-koydugun-yolu-once-kendin-kos]] · [[feedback_calisan-ajanin-dosyasi-ucus-halindedir-iddia-degil-soru]] · [[feedback_dokuman-turu-donmus-kod-ister-paralel-kosturma]] · [[feedback_infra-expert-spawn-ad-verme]] · [[feedback_infra-turunda-yeni-acilan-maddeye-baslama-mevcutlari-bitir]] · [[feedback_kapi-kosarken-dosya-donar-md5-teyidi]] · [[feedback_kardes-taramasi-spawn-oncesi-kapsama-alinir-kuyruga-yazilmaz]] · [[feedback_lider-ajan-paralel-yazim-cakismasi]] · [[feedback_paralel-infra-pr-ortak-dosya-rebase-sonrasi-tam-suit]] · [[feedback_performans-onerisi-de-bir-iddiadir-maliyeti-once-olc]] · [[feedback_sendmessage-gorevi-sessizce-islenmemis-olabilir]] · [[feedback_spawn-brifinde-sablonun-kanonik-basliklarini-kullan]] · [[feedback_standing-ajani-bos-bekletme-tek-tam-brif]] · [[feedback_worktree-kapatmadan-once-ajanin-nihai-raporunu-al]] · [[feedback_yeni-mcp-tool-agent-allowlist-guncelle]]
