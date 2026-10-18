---
name: feedback_alt-ajan-spawn-edince-bekci-baslat-onay-beklemesin
description: "Kullanıcı kuralı: alt-ajan kullanınca agent_stall_watch bekçisini (Monitor) BAŞLAT + ajanları takip et; kullanıcı ekrandan kalkacaksa ajan brifine 'onay bekleyip takılma — reddedilen çağrıyı tekrarlama, ÖLÇÜLEMEDİ yaz, devam et' maddesi koy."
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 10e41d9b-dbe7-47b8-b42e-99b8fddb9a68
  modified: 2026-10-02T21:08:07.642Z
---

Alt-ajan spawn edildiğinde **ilk spawn'dan ÖNCE** `python -u core/scripts/agent_stall_watch.py --seans <sid> --sure-dk 29` Monitor ile başlatılır (30 dk dolunca yeniden kur), ajanlar tamamlanana kadar takip edilir. Kullanıcı ekrandan kalkıp otonom devam istediğinde her brife **OTONOMİ** maddesi girer: izin isteyebilecek eylemden kaçın · reddedilen/bloklanan çağrıyı tekrarlama · alternatif yol ya da `ÖLÇÜLEMEDİ: <sebep>` · kullanıcıya soru yok · soru/onay gerekiyorsa **kullanıcı gitmeden ÖNCE** lider toplar.

**Why:** 2026-10-03 radar turu — kullanıcı ilk spawn'ı reddedip *"ajan bekçisini de başlat, alt ajan kullanırsan. ayrıca ajanlar bana bi onay isteyip takılmasınlar. takip et ajanları. ben kalkıyorum otonom devam et"* dedi. Bekçisiz arka plan ajanı asılırsa kimse görmez (bkz. [[feedback_agent-stall-watchdog-mekanizmasi]]); kullanıcı yokken izin bekleyen ajan saatlerce boşa durur.

**How to apply:** Spawn listesinden önce Monitor; brif şablonunun §2'sine OTONOMİ satırı; çok sayıda paralel spawn tek mesajda `Lock file is already being held` ile kısmen düşebilir (2026-10-03: 10'dan 4'ü) → düşenleri **tek tek** yeniden spawn et ve sayıyı doğrula.

Son-doğrulama: 2026-10-03 · Applies-to: tüm projeler, background alt-ajan kullanımı
