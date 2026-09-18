---
name: feedback_deploy-ui-statik-varlik-korlugu
description: "deploy_ui.py yalnız Component-preload'ı kanıtlar; in-app yardım (webapp/help/**) kör noktadır → verify_ui_static_assets.py ayrıca koşulmalı. Ham byte kıyası BSP enjekte-metası yüzünden 12/12 yanlış-pozitif verir."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c9f6971e-7b33-4e0d-8953-9e226b56c2bf
---

**UI deploy'unun "doğrulandı"sı yalnız `Component-preload.js` içindir.** `webapp/help/**`
(in-app kullanıcı kılavuzu + ekran görüntüleri) preload paketine **girmez** ⇒ KD bayat kalsa
bile `deploy_ui.py` *"CANLI==kaynak ✓ (güncel)"* der.

**Why:** iki ayrı turda (2026-08-07, 2026-08-10) bu boşluk elle ölçülmek zorunda kaldı;
ikincisinde bulgu hatırlanmadığı için sıfırdan yeniden keşfedildi ve bir tur harcandı.

**How to apply:** yardım/statik içerik değiştiyse deploy'dan sonra **ayrıca** koş:
`python core/scripts/verify_ui_static_assets.py --all` (salt-okuma, negatif-testli).
⚠ **Kendi ham kıyasını yazma:** BSP runtime HTML `<head>`'ine 3 meta enjekte eder
(`sap-client` · `sap-ui-fesr` · `sap.whitelistService`, ~185 karakter, yalnız 1. satır) →
ham byte kıyası **12/12 app'i "STALE"** gösterir, hiçbiri bayat değilken. Teşhis ipucu:
**dokunulmamış bir app de kırmızıysa kusur ölçümdedir, deploy'da değil.**
⚠ `deploy_ui.py`'ye entegrasyon **yapılmadı** (ayrı karar) — unutulursa boşluk aynen duruyor.
Kayıt: `governance/infra-findings.md` 2026-08-07 satırı · standart `03-coding-ui-fiori.md` §2.4.2.

Son-doğrulama: 2026-08-10 (12 app / 124 dosya; negatif test rc=1/rc=0)
Applies-to: freestyle UI5 + BSP deploy (s4_private); in-app help/statik varlık taşıyan app'ler

İlgili: [[feedback_ui-deploy-noninteractive]] · [[feedback_exit0-degil-cikti-kaniti]] ·
[[feedback_dogrulama-sezgileri-dort-kural]] · [[project_zsd001-docs-yenileme]]

---

⚠ **`--verify-only` MASUM DEĞİLDİR (2026-09-08, ölçüldü):** `deploy_ui.py --verify-only`
karşılaştırmadan önce **`ui5 build --clean-dest --dest dist` KOŞAR** ⇒ `dist/` yeniden yazılır.
İki sonucu var: (a) eşzamanlı çalışan bir ajan bunu *"dışarıdan bir şey rebuild etti"* sanabilir
(bir turda tam bu oldu); (b) **çalışma ağacı kirliyken bayatlık ölçümü kirlenir** — "deploy'dan
beri `ui/` altında kaç satır değişti" tabanı alınamaz. Bayatlık ölçeceksen **önce commit et**,
sonra `--verify-only` koş.

**EK ÖLÇÜM (2026-09-09, <PAKET-B> shipment BSP).** Deploy sonrası 18 statik varlığı canlıdan
çekip md5 kıyasladım: **17/17 PNG birebir aynı**, ama `help/kullanici-kilavuzu.html`
**FARKLI** göründü (canlı 91.199 B ↔ disk 91.014 B, +185 B). **Bu bayatlık DEĞİL:** SAP,
HTML'i servis ederken `<head>`e kendi meta etiketlerini **enjekte ediyor**
(`sap-client`, `sap-ui-fesr`, `sap.whi…`). Ayırt edici test md5 değil **içerik sondası**
oldu: canlıda `20.000 KG` 1 kez, `80004501` 1 kez (ikisi de o gün eklenen içerik) ⇒ taze.
CRLF/LF sayıları ve satır sayısı (1487/1487) da eşitti; fark yalnız 1. satırdaydı.

⇒ **Kural:** statik varlık doğrulamasında **binary (PNG/JPG/PDF) için md5**, **HTML için
içerik sondası** kullan. HTML'de md5 eşitliği beklemek yanlış-alarm üretir; md5 farkını
gördüğünde önce "SAP enjeksiyonu mu?" diye ayrıştır — normalize edip `unified_diff`'in
**yalnız `<head>` ilk satırında** olduğunu göster.
