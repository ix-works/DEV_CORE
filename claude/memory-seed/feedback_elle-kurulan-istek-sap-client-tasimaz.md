---
name: feedback_elle-kurulan-istek-sap-client-tasimaz
description: Manifest dışı kurulan her UI5 isteği (new ODataModel, ham fetch/XHR, sServiceUrl + URL) sap-client'ı taşımaz — iki client aynı tarayıcıda açıkken HATASIZ çapraz-client okuma/yazma; ana modelin aUrlParams'ını devret
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

UI5'te `sap-client`'ı manifest modeline **Component** ekler. `new ODataModel(...)` ile kurulan ikinci/varyant/`$batch` modeli, ham `fetch`/`XMLHttpRequest` ve `oModel.sServiceUrl + "…"` ile kurulan URL bunu **almaz** — `sServiceUrl` sorgusuz saklanır, parametreler `aUrlParams`'tadır. `sap-client`'sız istek tarayıcının TEK `sap-usercontext` çerezine göre yönlenir; çerezi en son açılan client yazar.

**Why:** S/4 private projede (2026-09-25) aynı host'un iki client'ı (DEV/QA) aynı tarayıcıda açılınca QA sekmesindeki varyant listesi ve veri yazan yükleme modeli DEV'in verisini okudu — hata, dump, 4xx yok. Tek client ile yapılan her test yeşildi. 14 util kopyası + 2 veri yazan model + 5 kilit bırakma isteği etkilendi; kanonik şablon ve standart örnek de aynı kusuru öğretiyordu.

**How to apply:** manifest dışı her istekte ana modelin `aUrlParams`'ını (`sap-statistics` hariç) URL sorgusuna devret — literal client yazma; util'de ana modeli `Component.getOwnerComponentFor(ctrl).getModel()` ile al (onInit'te view modeli `undefined`). Reçete `core/standards/03-coding-ui-fiori.md` **§18.5b**, kontrol `bug-checklist-frontend.md` **FE-48**, genel ders **PATTERN #40**. Kanıt kaynak okuması değil: iki client'lı iki sekme + **ayırıcı veri** (iki client'ta sayısı farklı entity). Kardeş taraması: `new ODataModel(` / `XMLHttpRequest` / `fetch(` / `sServiceUrl +` tüm app'lerde. İlgili: [[feedback_paylasim-onbellek-sorusu-kaynak-okumasiyla-cevaplanmaz]] · [[feedback_sayfa-kapanirken-senkron-xhr-gitmez]]

Son-doğrulama: 2026-09-25 · Applies-to: freestyle UI5 + OData V2, çok client'lı host (S/4 private / ECC)
