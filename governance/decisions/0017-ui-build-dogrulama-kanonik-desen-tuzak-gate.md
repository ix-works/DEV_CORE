# ADR 0017 — Freestyle UI Build Doğrulama: Kanonik Desen + Statik Tuzak Gate + Runtime Smoke + Lider Protokolü

**Durum:** Kabul edildi (2026-06-16)
**Bağlam tetikleyici:** Booking (ZSD001) UI post-mortem.

## Bağlam

Booking UI geliştirmesinde diğer ekranlara göre **çok daha fazla** amatör, basit, tekrar-eden hata çıktı (V2 nav `_Container`→`to_Container`, `core:Title` VBox-child runtime crash, `setProperty`+submitChanges save'in programatik değerleri kaydetmemesi, eş-zamanlı update BO-kilit çakışması, MERGE'de boş-tarih `""`, `setData` eksik şekli). Kanıtlı kök sebepler:

1. **Çalışan kardeş deseni kullanılmadı.** sip_se/ihr_se ChangeSe save'i temiz `oModel.update()` kullanırken (submitChanges=0), Booking `submitChanges`+`setProperty` (kırılgan change-detection) ile **sıfırdan yeniden yazdı**. Git: Booking UI "iskelet v0.1 + yama" olarak inşa edildi, çalışan template'ten kopya değil. ("Use ZSD001 template" denmişti ama kopya-temelli inşa edilmedi.)
2. **Runtime-doğrulama gate'i yoktu.** Hatalar yalnız kullanıcı test edince çıktı. Ajan "node --check OK / XML well-formed / done" dedi — bunlar runtime/fonksiyonel hatayı yakalamaz.
3. **Lider aşırı-güven.** "done/verified" raporları runtime-doğrulanmadan kabul edildi; recon "bitti" sayılıp implementasyon doğrulanmadı (gating boşluğu).

Kural dosyaları bu spesifik tuzakları **içermiyordu** → "okumak" yardım etmezdi; ve "çalışan deseni reuse et" prensibi vardı ama **dayatan gate yoktu** → okumak ≠ uygulamak.

## Karar

Drift-guard (ADR 0016) gibi **dayatılan** (advisory değil) 4 katman:

- **G2 — Kanonik PLUMBING deseni (app-kopyalama DEĞİL):** Freestyle UI5+V2'nin **mekanik** kısmı (save=sıralı `update`, nav=`to_X`, `setData` şekil, master-detail seçim-wiring, MERGE tarih-null) tek-doğru-yol, uygulamadan bağımsız → `playbook/ui-freestyle-odata-v2.md` §K'de kodlandı; **referans alınır, sıfırdan icat edilmez.** Uygulamaya özel içerik (entity/alan/layout/iş-kuralı/VH/label) **bespoke** yazılır — hiçbir ekran kopya değildir. **Sınır: framework-plumbing = reuse · iş-içeriği = bespoke.** Kardeş uygulama ŞART DEĞİL — kanonik §K yeterli.
- **G3 — Statik tuzak gate:** `scripts/validators/check_ui5_freestyle_traps.py`, `run_all_validators`'a wire'lı. **T1 (V2-nav `_X`) = HARD ERROR** (build durur); T2 (type=Number) / T3 (core:Title) = WARN (meşru istisnaları var: filtre-sayaç / Form).
- **G4 — Lider doğrulama protokolü:** AGENTS.md'ye eklendi — "done/verified" kanıtsız kabul edilmez (UI: G3 PASS + runtime smoke; SAP: active readback); recon ≠ implementasyon; kör-bug yasak (önce gerçek hata).
- **G1 — Runtime smoke-test gate (PLANLI, auth kurulumu ile):** UI "done" öncesi app çalıştırılıp console yakalanır (zero render error + ana akış). **Araç = SADECE playwright-cli** (scriptli, headless, tekrarlanabilir, commit'lenebilir). **MCP canlı-browser GATE'te KULLANILMAZ** — iki sebep: (1) her G1 run'ında canlı browser sürmek YAVAŞ; (2) taze-context = SAP oturumu yok → `$metadata` 401 → yalnız render görülür, veri/fonksiyonel akış görülmez. MCP-browser yalnız ajanın **ad-hoc debug'ı** içindir, gate değil. playwright-cli `httpCredentials` ile `.conn_adt` kimliğini fiori-proxy'ye geçirir → 401 yok → gerçek akış test edilir. **KURULDU ve KANITLANDI (2026-06-16):** `scripts/ui-smoke/` (playwright.config + generic `ui.smoke.spec.ts` + lockout-safe `run_ui_smoke.py`). fiori dev-proxy Basic-auth'u SAP'ye FORWARD ediyor (kanıt: `8099 + basic = 200`) → httpCredentials çalışıyor. **Booking 8099 smoke PASS** (`$metadata` 200, zero gerçek console-error). Runner auth'u tek-doğrular (401→DUR, hesap-kilidi önlemi), `retries:0`.

## Sonuçlar

- **Hız:** G2/G3/G4 net hızlandırıcı/maliyetsiz (kopya > sıfırdan; lint saniyeler; disiplin). G1 build-başına birkaç dk ama saatlerce kör-fix turunu önler (shift-left). Bizi yavaşlatan gate değil, BUG'lardı.
- **Kapsam:** T1 hard-block tek başına Booking save-bug zincirini (sessiz V2-nav) baştan keserdi.
- **G1 açık:** auth kurulumu yapılana kadar runtime gate yarı-manuel (elle console). Bkz. `governance/deferred-triggers.md`.

## İlgili
- Kanonik desen: `playbook/ui-freestyle-odata-v2.md` §K + §J tuzak tablosu
- Gate: `scripts/validators/check_ui5_freestyle_traps.py` (CLAUDE.md §7)
- Lider protokolü: `AGENTS.md` §2 "UI BUILD DONE-CRITERIA"
- Benzer enforced-gate felsefesi: ADR 0016 (drift-guard), ADR 0006 (reviewer)
