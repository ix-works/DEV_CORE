---
applies_to: [s4_private]
layer: L2
scope: project-wide
applies-to: ui
version: 1.0
last-updated: 2026-07-31
status: active
reference-app: ERP/SD/ZSD001_CLC/ui/order_app/
---

# SAP Fiori UI5 Geliştirme Kuralları
## <PROJECT_NAME> — Frontend Standartları

> Bu doküman, `order_app` uygulamasının SAP'ye başarıyla deploy edilmesinden çıkarılan dersleri
> ve bundan sonra yapılacak tüm Fiori geliştirmeleri için geçerli olan kuralları içermektedir.
> Temel referans: `order_app/` klasörü (çalışan, deploy edilebilen uygulama).
>
> **⚠️ Freestyle + OData V2 (RAP tüketen) uygulama yapıyorsan** (ORDER/ORDER
> tipi): koda başlamadan **önce** L3 operasyonel tecrübe + PRE-FLIGHT'ı oku:
> [`../playbook/ui-freestyle-odata-v2.md`](../playbook/ui-freestyle-odata-v2.md)
> §0 + [checklist](../playbook/checklists/ui-freestyle-creation.md). ORDER'de
> yaşanan UI patinajları orada; tekrarlama.
>
> **🛠️ Araç (`ui5` plugin):** UI5 yazarken `ui5-best-practices` skill'i + `ui5-mcp-server`
> kullan — control API'sini **tahmin etme**, `get_api_reference` ile doğrula; bitirmeden
> `run_ui5_linter` çalıştır. Tarayıcıda doğrulama için `playwright` (localhost dev server).
> Plugin'in **CAP** bölümleri bizde geçersiz (ABAP RAP backend). Bkz.
> [`../governance/tooling-plugins.md`](../governance/tooling-plugins.md).

---

## 1. PROJE YAPISI VE KİMLİK

### 1.1 Her Uygulama Bağımsız Klasörde Olmalı

```
<PROJECT_ROOT>\
└── <uygulama_adi>/           ← her uygulama kendi klasörü
    ├── package.json
    ├── package-lock.json
    ├── node_modules/
    ├── ui5.yaml
    ├── ui5-local.yaml
    ├── ui5-deploy.yaml
    ├── ui5-mock.yaml
    └── webapp/
        ├── manifest.json
        ├── Component.js
        ├── index.html
        ├── ...
```

**YASAK:** Birden fazla uygulama için paylaşımlı `node_modules` / `package.json` kullanmak.
Her uygulama `npm install` ile kendi bağımlılıklarını kurar.

### 1.2 Uygulama ID — Reverse Domain Formatı (ZORUNLU)

```
com.example.<alan>.<uygulama>
```

| Alan | Kısaltma |
|------|----------|
| SD — Satış ve Dağıtım | `sd` |
| FI — Finans | `fi` |
| MM — Malzeme Yönetimi | `mm` |
| PP — Üretim Planlama | `pp` |

**Örnekler:**
```
com.example.sd.orderapp   ✅
com.example.sd.salesreport     ✅
zsd001.somanagement                ❌  (SAP'ye deploy edilemez)
```

Bu ID şu yerlerde tutarlı olmalıdır:
- `manifest.json` → `sap.app.id`
- `Component.js` → `UIComponent.extend("com.example.sd.xxx.Component")`
- `index.html` → `data-sap-ui-resource-roots` + `data-name`
- `ui5.yaml` → `metadata.name`
- Tüm controller/view dosyalarındaki `controllerName` ve `extend` çağrıları
- `i18n` model `bundleName`

### 1.3 SAP BSP Uygulama Adı

SAP'deki BSP (ABAP repository) adı `Z` ile başlamalı, max 15 karakter:
```
ZSD_FIT_ORD      ✅
ZSD_SALES_RPT    ✅
```

---

## 2. TOOLING VE ALTYAPI

### 2.0 npm Workspace — paket `ui/` kökü (ZORUNLU, ilk app'ten itibaren)

**Her paketin `ui/` klasörü bir npm WORKSPACE köküdür — paket başlarken app sayısı belirsiz olsa da ÇOKLU varsay** (tek-app workspace'in dezavantajı yok; sonradan 2. app gelince retrofit gerekmez).

- `ERP/<MODULE>/<PKG>/ui/package.json` = workspace kökü: `{ "private": true, "workspaces": ["*"], "devDependencies": { <§2.1 ortak set> } }`.
- Yeni app → `ui/<app>/` altına; app'in package.json'u **minimal** (name + scripts; devDeps YOK → root'tan inherit).
- **`npm install`'ı `ui/` KÖKÜNDE çalıştır, app dizininde DEĞİL.** Tooling tek `ui/node_modules`'a hoist olur; yeni app **~anında** katılır (8dk install yok). `cd <app> && npm install` = gereksiz per-app node_modules → YAPMA. **GATE:** `scripts/hooks/pre_tool_guard.py` (PreToolUse Bash) app-içi `npm install/ci/add`'i bloklar. Lokal çalıştırmak için kurulum GEREKMEZ — app dizininden `npm run start-noflp`/`start-mock` (bin ata-dizin `ui/node_modules/.bin`'den çözülür).
- `node_modules` gitignore'da (commit'lenmez). **Yalnız root `ui/package-lock.json`** tracked; per-app `package-lock.json` OLMAZ (root lock yönetir).
- Gerekçe: app sayısı baştan kesin değil → çoklu-default; tek-app'te maliyet sıfır; gelecek app'ler otomatik dedupe + tutarlı yapı. Kanıt: ZSD001_CLC/ui (8 app, 7509 paket dedupe, 2026-06-24).

### 2.1 Zorunlu DevDependencies

```json
{
  "devDependencies": {
    "@ui5/cli": "^4.0.33",
    "@sap/ux-ui5-tooling": "1",
    "@sap-ux/eslint-plugin-fiori-tools": "^9.0.0",
    "eslint": "^9",
    "@sap-ux/ui5-middleware-fe-mockserver": "2",
    "rimraf": "^5.0.5"
  },
  "sapuxLayer": "CUSTOMER_BASE"
}
```

**YASAK:** `ui5-middleware-simpleproxy` kullanmak. Yerine `fiori-tools-proxy` kullanılır.

### 2.2 package.json Scripts (Standart Set)

```json
{
  "scripts": {
    "start":         "fiori run --open \"test/flp.html#app-preview\"",
    "start-local":   "fiori run --config ./ui5-local.yaml --open \"test/flp.html#app-preview\"",
    "start-noflp":   "fiori run --open \"/index.html?sap-ui-xx-viewCache=false\"",
    "start-mock":    "fiori run --config ./ui5-mock.yaml --open \"test/flp.html#app-preview\"",
    "build":         "ui5 build --config=ui5.yaml --clean-dest --dest dist",
    "lint":          "eslint ./",
    "deploy":        "npm run build && fiori deploy --config ui5-deploy.yaml",
    "deploy-config": "fiori add deploy-config",
    "undeploy":      "npm run build && fiori undeploy --config ui5-deploy.yaml",
    "deploy-test":   "npm run build && fiori deploy --config ui5-deploy.yaml --testMode true"
  }
}
```

### 2.3 ui5.yaml — Proxy Konfigürasyonu

```yaml
specVersion: "4.0"
metadata:
  name: com.example.<alan>.<uygulama>
type: application
server:
  customMiddleware:
    - name: fiori-tools-proxy
      afterMiddleware: compression
      configuration:
        ignoreCertErrors: true
        ui5:
          path:
            - /resources
            - /test-resources
          url: https://ui5.sap.com
        backend:
          - path: /sap
            url: https://<DEV_HOST>.example.com.tr:44300
            client: '100'
            authenticationType: basic
    - name: fiori-tools-appreload
      afterMiddleware: compression
      configuration:
        port: 35729
        path: webapp
        delay: 300
    - name: fiori-tools-preview
      afterMiddleware: fiori-tools-appreload
      configuration:
        flp:
          theme: sap_horizon
```

### 2.4 ui5-deploy.yaml — SAP Deploy Konfigürasyonu

```yaml
specVersion: "4.0"
metadata:
  name: com.example.<alan>.<uygulama>
type: application
builder:
  resources:
    excludes:
      - /test/**
      - /localService/**
  customTasks:
    - name: deploy-to-abap
      afterTask: generateCachebusterInfo
      configuration:
        ignoreCertErrors: true   # (çoğul; 'ignoreCertError' deprecated)
        target:
          url: https://<DEV_HOST>:<PORT>   # KANONİK host (.conn_adt ile aynı)
          client: '100'
        app:
          name: Z<BSP_ADI>
          description: <Açıklama>
          package: <SAP_PAKET>
          transport: <TRANSPORT_NO>
        exclude:
          - /test/
```

> ⚠️ **Deploy hedef URL'i `.conn_adt`'deki `ADT_SAP_URL` ile BİREBİR olmalı** (`<DEV_HOST>:<PORT>`). Bir alias (kısa/alternatif DNS) local serve'de çalışsa da deploy SAP repository+transport'a yazar → her zaman `.conn_adt`'deki kanonik host'u kullan. (Vaka: bir app'in yaml'ı alias host ile gelmişti → `.conn_adt` ile hizalanınca deploy düzeldi.)

### 2.4.1 Deploy — KANONİK YOL: `scripts/deploy_ui.py` (ZORUNLU)

> 🛑 **YALIN `fiori deploy` YASAK — PreToolUse guard BLOKLAR.** Doğrudan `fiori deploy --config ui5-deploy.yaml`
> **build YAPMAZ** → eski `dist/`'i archive edip **"Deployment Successful" DER ama canlıya BAYAT içerik gider**
> (abap-deploy-task "UI5 build result" = `dist/` klasörü; güncel değilse stale). **2026-07-06 dersi:** 3 tur FE
> deploy'u sessizce stale gitti, kullanıcı canlıda değişikliği görmeyince yakalandı ("Deployment Successful yalan söyledi").

**Kanonik deploy = tek güvenli yol** (build gömülü + deploy + CANLI içerik doğrulaması):
```bash
python scripts/deploy_ui.py --apps sip_se,dsk_se,fih_se     # veya --app dsk_se / --all-changed
python scripts/deploy_ui.py --app dsk_se --dry-run          # build+doğrula plan, deploy YOK
```
Script her app için sırayla: **(1) `ui5 build --clean-dest --dest dist` (BUILD ZORUNLU)** → (2) dist/Component-preload.js sha256 → (3) `npx fiori deploy … --yes` (env auth `.conn_adt`) → **(4) canlı `GET …/<bsp>/Component-preload.js?cb=<ts>` (no-cache) → yerel dist ile HASH karşılaştır** → eşleşmezse `[FAIL] STALE/CACHE`. "Successful" mesajına GÜVENMEZ, içeriği kanıtlar. Bkz. `scripts/deploy_ui.py` + `feedback_ui-deploy-noninteractive` (madde 8).

---

#### Altında yatan manuel yöntem (yalnız `deploy_ui.py` çalışmazsa acil geri-dönüş; guard'a takılır)

`fiori deploy` kimliği iki yolla alır; **doğru olan env değişkeni**:

| Yöntem | Sonuç |
|---|---|
| `--username X --password Y` (CLI arg) | ❌ **401** — `fiori` arg'ları `shell:true` ile escape ETMEDEN child process'e geçirir (DEP0190); özel karakterli parola (`.!.!.!` vb.) cmd.exe'de bozulur. Ayrıca parola log'a echo'lanır (sızıntı). |
| `FIORI_TOOLS_USER` / `FIORI_TOOLS_PASSWORD` (env) | ✅ Doğrudan `process.env`'den okunur — mangling yok, echo yok. |

**Çalışan komut deseni** (parolayı `.conn_adt`'den satır-içi oku, echo'lama; `--yes` onay prompt'unu atlar):
```bash
U=$(grep '^ADT_SAP_USER=' <PROJECT_ROOT>/.conn_adt | cut -d= -f2 | tr -d '\r')
P=$(grep '^ADT_SAP_PASSWORD=' <PROJECT_ROOT>/.conn_adt | cut -d= -f2- | tr -d '\r')
FIORI_TOOLS_USER="$U" FIORI_TOOLS_PASSWORD="$P" \
  npm --prefix <app_mutlak_yol> run deploy -- --yes
```
- `deploy-test` (testMode) ile önce dry-run → "Test run has indicated no problems".
- Validation'daki **"application name must be prefixed with [ZZ1_]"** = **soft uyarı**, Z-prefix deploy'u bloklamaz (kanıt: ZSD001_FIT_ORD + eski ZSD_FIT_ORD bu sistemde deploy oldu).

> ⚠️ **npm-workspace tuzağı (ZSD001 vaka, 2026-06-29):** App `ui/` npm-workspace kökü altındaysa (std §2.0),
> `npm run deploy` (script `npm run build && fiori deploy ...` zincirini cmd.exe wrapper'da koşar) Windows'ta
> **native crash** verir: `code 3221226505` (0xC0000409 STATUS_STACK_BUFFER_OVERRUN) — **build başarılı, deploy çöker.**
> **Çözüm:** build + deploy'u AYIR, `fiori deploy`'u doğrudan `npx` ile koş (npm-script wrapper'sız):
> ```bash
> cd <app_mutlak_yol>
> FIORI_TOOLS_USER="$U" FIORI_TOOLS_PASSWORD="$P" npm run build                 # ui5 build → dist/
> FIORI_TOOLS_USER="$U" FIORI_TOOLS_PASSWORD="$P" npx --no-install fiori deploy --config ui5-deploy.yaml --yes
> ```
> `keyring.getPassword is not a function` + `@zowe/secrets-for-zowe-sdk` uyarıları **non-fatal** — env kimliği kullanılır, deploy "Deployment Successful" döner.
- `tr -d '\r'` ŞART (.conn_adt CRLF → parolada trailing \r = auth bozar).
- cwd kaymasına karşı **mutlak yol** kullan (`--prefix`, `.conn_adt`).
- **STRAY DOSYA TUZAĞI (2026-06-11):** deploy `400 "Type of file X is unknown"` → build çıktısına (webapp→dist) UI5 repo'nun sınıflayamadığı stray dosya karışmış (ör. statusline cwd webapp'a kayınca yazdığı `webapp/.claude/.statusline_vpn_cache`). **Fix:** stray'i sil + `ui5-deploy.yaml`'de `builder.resources.excludes: /.claude/**` + deploy task `exclude: /.claude/`. Generic 400'ün altındaki gerçek hatayı verbose'la yakala (`-- --yes --verbose | grep -i unknown`).

---

## 2.5 index.html — UI5 Sürüm Sabitleme (ZORUNLU)

`index.html` bootstrap'ı **sabit UI5 sürümüyle** yüklenir; `manifest.json`
`minUI5Version` ile aynı olmalı. Sürümsüz CDN (latest) core ↔ locale-data skew
yaratır.

```html
<!-- DOĞRU -->
<script id="sap-ui-bootstrap"
  src="https://ui5.sap.com/1.120.23/resources/sap-ui-core.js"
  data-sap-ui-theme="sap_horizon"
  data-sap-ui-language="tr" ...></script>

<!-- YASAK: src=".../resources/sap-ui-core.js" (sürümsüz) -->
```

**Vaka (ZSD001 ORDER, 2026-05-15):** sürümsüz bootstrap + `tr` locale →
`TypeError: this.oLocaleData.getDatePlaceholder is not a function`
(`DateRangeSelection` çöktü, beyaz ekran). Sürüm 1.120.23'e sabitlenince çözüldü.
Ayrıca `Component.js`'te `sap/ui/model/json/JSONModel` **define bağımlılığı**
olmadan global `sap.ui.model.json.JSONModel` kullanımı = async/strict'te fırlatır
→ her zaman `sap.ui.define([...])` ile require et.

## 3. MANIFEST.JSON STANDARTLARI

### 3.1 Tam Şablon

```json
{
  "_version": "1.60.0",
  "sap.app": {
    "id": "com.example.<alan>.<uygulama>",
    "type": "application",
    "i18n": {
      "bundleUrl": "i18n/i18n.properties",
      "supportedLocales": ["", "tr"],
      "fallbackLocale": ""
    },
    "applicationVersion": { "version": "0.0.1" },
    "title": "{{appTitle}}",
    "description": "{{appDescription}}",
    "resources": "resources.json",
    "sourceTemplate": {
      "id": "@sap/generator-fiori:basic",
      "version": "1.23.0"
    },
    "dataSources": {
      "ZSD_ORDER_ANNO_MDL": {
        "uri": "/sap/opu/odata/IWFND/CATALOGSERVICE;v=2/Annotations(TechnicalName='<ANNO_MDL_ADI>',Version='0001')/$value/",
        "type": "ODataAnnotation",
        "settings": {
          "localUri": "localService/mainService/<ANNO_MDL_ADI>.xml"
        }
      },
      "mainService": {
        "uri": "/sap/opu/odata/SAP/<SERVIS_ADI>/",
        "type": "OData",
        "settings": {
          "annotations": ["<ANNO_MDL_ADI>"],
          "localUri": "localService/mainService/metadata.xml",
          "odataVersion": "2.0"
        }
      }
    }
  },
  "sap.ui": {
    "fullWidth": true,
    "technology": "UI5",
    "deviceTypes": { "desktop": true, "tablet": true, "phone": false }
  },
  "sap.ui5": {
    "flexEnabled": true,
    "dependencies": {
      "minUI5Version": "1.120.23",
      "libs": {
        "sap.m":          {},
        "sap.ui.core":    {},
        "sap.ui.comp":    {},
        "sap.ui.layout":  {},
        "sap.ui.unified": {}
      }
    },
    "contentDensities": { "compact": true, "cozy": false },
    "resources": {
      "css": [{ "uri": "css/style.css" }]
    },
    "models": {
      "i18n": {
        "type": "sap.ui.model.resource.ResourceModel",
        "settings": {
          "bundleName": "com.example.<alan>.<uygulama>.i18n.i18n"
        }
      },
      "": {
        "dataSource": "mainService",
        "preload": true,
        "settings": {
          "defaultBindingMode": "TwoWay",
          "defaultCountMode": "Inline",
          "useBatch": false
        }
      },
      "orderModel": {
        "type": "sap.ui.model.json.JSONModel",
        "settings": { "data": {} }
      }
    },
    "routing": {
      "config": {
        "routerClass": "sap.m.routing.Router",
        "type": "View",
        "viewType": "XML",
        "path": "com.example.<alan>.<uygulama>.view",
        "viewPath": "com.example.<alan>.<uygulama>.view",
        "controlId": "app",
        "controlAggregation": "pages",
        "transition": "show",
        "async": true
      },
      "routes": [
        { "name": "list",   "pattern": "", "target": "list" }
      ],
      "targets": {
        "list": { "id": "List", "name": "List", "viewLevel": 1 }
      }
    },
    "rootView": {
      "viewName": "com.example.<alan>.<uygulama>.view.App",
      "type": "XML",
      "id": "App",
      "async": true
    }
  }
}
```

### 3.2 Kritik Kurallar

| Kural | Açıklama |
|-------|----------|
| `_version: "1.60.0"` | **1.60 altı kullanma** (1.59 ve öncesi dahil) |
| `resources: "resources.json"` | SAP deploy için zorunlu |
| `flexEnabled: true` | UI adaptation için zorunlu |
| `minUI5Version: "1.120.23"` | Proje standart versiyonu |
| `fullWidth: true` | Fiori launchpad'de tam genişlik |
| `fallbackLocale: ""` | Boş string → default `.properties` dosyası (i18n.properties) |
| `supportedLocales: ["", "tr"]` | İngilizce default + Türkçe |
| `controlId: "app"` | App.view.xml'deki `<App id="app"/>` ile eşleşmeli |
| `useBatch: false` | OData V2 SEGW servisleri için |
| Annotation dataSource | Annotation model olmasa bile `localUri` ile tanımla |
| `type: "View"` | Routing config'e ekle |
| `path` + `viewPath` | İkisi de yazılmalı |
| Her target'a `"id"` | `"id": "List"` gibi ayrıca belirtilmeli |

---

## 4. COMPONENT.JS STANDARDI

```javascript
sap.ui.define([
    "sap/ui/core/UIComponent",
    "com/example/<alan>/<uygulama>/model/models"
], (UIComponent, models) => {
    "use strict";

    return UIComponent.extend("com.example.<alan>.<uygulama>.Component", {
        metadata: {
            manifest: "json",
            interfaces: [
                "sap.ui.core.IAsyncContentCreation"     // ZORUNLU
            ]
        },

        init() {
            UIComponent.prototype.init.apply(this, arguments);
            this.setModel(models.createDeviceModel(), "device");
            this.getRouter().initialize();
        },

        destroy: function () {
            UIComponent.prototype.destroy.apply(this, arguments);
        }
    });
});
```

**Kurallar:**
- Arrow function `(...) =>` kullanılabilir (ES6 modern stil)
- `sap.ui.core.IAsyncContentCreation` interface'i **zorunlu**
- ODataModel'i Component.js'te import etme — manifest yönetir
- `init()` kısa metot yazımı tercih edilir

---

## 5. INDEX.HTML STANDARDI

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{{Uygulama Adı}}</title>
    <style>
        html, body, body > div, #container, #container-uiarea {
            height: 100%;
        }
    </style>
    <script
        id="sap-ui-bootstrap"
        src="resources/sap-ui-core.js"
        data-sap-ui-theme="sap_horizon"
        data-sap-ui-resource-roots='{
            "com.example.<alan>.<uygulama>": "./"
        }'
        data-sap-ui-on-init="module:sap/ui/core/ComponentSupport"
        data-sap-ui-compat-version="edge"
        data-sap-ui-async="true"
        data-sap-ui-frame-options="trusted"
    ></script>
</head>
<body class="sapUiBody sapUiSizeCompact" id="content">
    <div
        data-sap-ui-component
        data-name="com.example.<alan>.<uygulama>"
        data-id="container"
        data-settings='{"id" : "com.example.<alan>.<uygulama>"}'
        data-handle-validation="true"
    ></div>
</body>
</html>
```

**Kurallar:**

| Kural | Açıklama |
|-------|----------|
| `data-sap-ui-libs` YASAK | Kütüphaneler manifest'te tanımlanır, index.html'de belirtme |
| `data-sap-ui-on-init` | camelCase — `data-sap-ui-oninit` değil |
| `sapUiSizeCompact` | Body class'a ekle — controller'da ayrıca set etme |
| `data-handle-validation="true"` | Validation framework desteği için ekle |
| `height: 100%` | CSS ile `html, body, body > div, #container, #container-uiarea` |

---

## 6. APP.VIEW.XML STANDARDI

```xml
<mvc:View
    xmlns:mvc="sap.ui.core.mvc"
    xmlns="sap.m"
    displayBlock="true"
    controllerName="com.example.<alan>.<uygulama>.controller.App">

    <App id="app"/>

</mvc:View>
```

**Kural:** `App` kontrolünün `id` değeri `"app"` olmalı. Manifest routing'deki `controlId: "app"` ile eşleşmeli.
`"appContainer"` gibi farklı bir id kullanma.

---

## 7. CONTROLLER YAZIM KURALLARI

### 7.1 Namespace ve Extend

```javascript
return Controller.extend("com.example.<alan>.<uygulama>.controller.List", {
```

### 7.2 Function Import Response Okuma (KRİTİK)

OData V2 Function Import dönüşleri bazen wrapper object içinde gelir. Her iki durumu da handle et:

```javascript
// DOĞRU — wrapper kontrolü ile
success: function (oData) {
    var oResult = oData.CreateSalesOrder || oData;   // wrapper varsa al, yoksa direk oData
    if (oResult.Success === true || oResult.Success === "true" || oResult.Success === "X") {
        // başarılı
    }
}

// YANLIŞ — sadece oData kullanan
success: function (oData) {
    if (oData.Success) { ... }   // wrapper gelince boş kalır
}
```

**Function Import → wrapper adı = Function Import adıdır:**
| Function Import | Wrapper key |
|----------------|-------------|
| `CreateSalesOrder` | `oData.CreateSalesOrder` |
| `RejectSalesItems` | `oData.RejectSalesItems` |
| `CreateDeliveryAddress` | `oData.CreateDeliveryAddress` |

### 7.3 Success Kontrolü

```javascript
// Her zaman 3 varyantı kontrol et:
if (oResult.Success === true || oResult.Success === "true" || oResult.Success === "X") {
```

### 7.4 onCustomerChange — Parametresiz Çağrı Tercihi

```javascript
// DOĞRU — değeri doğrudan modelden oku
onCustomerChange: function () {
    var sCustomer = this._getModel().getProperty("/header/soldToParty");
    ...
},

// XML'de change event'i:
// change=".onCustomerChange"   (parametreye ihtiyaç yok)
```

### 7.5 i18n Yapısı

- `i18n/i18n.properties` → **İngilizce** (default fallback)
- `i18n/i18n_tr.properties` → **Türkçe**
- manifest'te: `"supportedLocales": ["", "tr"]`, `"fallbackLocale": ""`
- ⚠️ **Etiket/metin değişiminde HER İKİ dosya güncellenir.** App `language=tr` çalışınca UI5 `i18n_tr.properties`'i yükler ve `i18n.properties`'i **override eder** → yalnız birini değiştirmek TR'de eski metni bırakır. (`grep <key> i18n*.properties` → bulunan tümünü güncelle; sonra **hard refresh / Ctrl+F5** — i18n bundle cache'lenir.) Memory: `feedback_i18n-tr-her-iki-dosya`.

### 7.6 Kaydetme / Aksiyon Geribildirimi (ZORUNLU)

- Her CRUD **save/create/action başarısında** kullanıcıya NET, garantili görünür geribildirim:
  **`MessageBox.success(<belge-no'lu metin>, { onClose: function(){ /* navTo(...) */ } })`** — modal,
  navigasyon ancak kullanıcı **OK**'leyince. Belge no varsa metne koy ("{0} numaralı … kaydedildi").
- ⛔ **`MessageToast.show()` + HEMEN `navTo` YAPMA** → toast sayfa geçişinde KAYBOLUR (kullanıcı "mesaj
  gelmedi" der). Toast yalnız **navigasyonsuz** anlık bilgi için (satır seçildi, kopyalandı vb.).
- Hata yolu: error callback `_parseError(oErr)` ile gerçek SAP `responseText`/`error.message.value`'yu
  bas (generic i18n yutma yok). **Kanonik desen: ZSD001 `CreateOrder.controller.js`.** Bug-checklist FE-21/FE-24.

---

## 8. LOCAL SERVICE DOSYALARI

Her uygulamada `localService/` klasörü zorunludur:

```
webapp/
└── localService/
    └── mainService/
        ├── metadata.xml          ← SAP'ten alınan gerçek metadata
        └── <ANNO_MDL_ADI>.xml    ← SAP'ten alınan annotation modeli
```

**metadata.xml nasıl alınır:**
```
GET /sap/opu/odata/SAP/<SERVIS_ADI>/$metadata
```
Tarayıcıdan veya Postman ile alınıp kaydedilir.

**Neden gerekli:**
- `fiori-tools-proxy` offline mod ve mock server için kullanır
- Annotation dataSource `localUri` ile referans verir
- SAP Fiori Tools'un bazı özellikleri (tooling, lint, preview) bu dosyaları gerektirir

---

## 9. CSS VE STIL KURALLARI

### 9.1 Standart CSS Sınıfları (Tüm Uygulamalarda Ortak)

```css
/* Input/alan altı kısa açıklama (tek satır, kırpılmış) */
.zsd001FieldDesc {
    font-size: 0.75rem;
    color: #6a6d70;
    max-width: 9em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    line-height: 1.2;
    margin-top: 0.125rem;
}

/* Uzun adres/metin açıklaması (çok satır) */
.zsd001FieldDescWrap {
    font-size: 0.75rem;
    color: #6a6d70;
    max-width: 18rem;
    white-space: normal;
    word-break: break-word;
    line-height: 1.4;
    margin-top: 0.125rem;
}
```

**NOT:** Yeni uygulamalarda CSS class ön eki uygulama koduna göre değişir (örn: `zfi001FieldDesc`).

### 9.2 Kural

- `sapUiSizeCompact` → `index.html` body class'ına ekle, controller'da `addStyleClass` yapma
- `sap.f` kütüphanesi ekleme — `DynamicSideContent` 404 verebilir
- `sap.ui.layout.Splitter` kullan (70%/30%) yerine

---

## 10. LAYOUT KURALLARI (View XML)

### 10.0 Liste / Rapor ekranı tablosu = GRID (`sap.ui.table.Table`) — STANDART (ADR 0008)

ALV-tarzı liste/rapor ekranları **`sap.ui.table.Table` (grid)** ile yapılır (masaüstü, çok-kolon,
native sort/filter, sanal scroll, kolon resize/sürükle/dondur). `sap.m.Table` yalnız
**mobil-öncelikli/hücre-zengin** ekranlar için istisna. Reusable util (`TablePersonalizer.js`
grid sürümü), kanonik şablon app, backend deseni (wrapper view entity + DCL + SRVD/SRVB) ve tam
kurulum reçetesi: **detay §16** (tekrarı önlemek için bu doküman içinde tek yerde tutulur).

### 10.0.1 Filtre / arama ekranı = SELECT-OPTIONS + harf-duyarsız "içeren" (STANDART, FE-32)

Rapor/liste **seçim (filtre) ekranı** ABAP SELECT-OPTIONS pariteli olmalı — **kullanıcı istemese de varsayılan** (gate: `check_filter_search_pattern.py`):

- **Çoklu-değer + aralık:** her filtre alanı `sap.m.MultiInput` + `sap.ui.comp.valuehelpdialog.ValueHelpDialog` (değer tablosu + "Koşul Tanımla"/ranges sekmesi). Tek-değer `<Input>` KULLANMA. Tarih = `DateRangeSelection`, durum/bayrak = `SegmentedButton` istisna.
- **Harf-duyarsız "içeren" varsayılan:** F4 değer-tablosu araması, grid sütun-başlığı filtresi ve düz-değer token'ları **harf-duyarsız `substringof` (Contains)** ile çalışır — kullanıcı küçük/BÜYÜK fark etmeksizin `gül`→`GÜLAK` bulur.
- **⛔ `caseSensitive:false` YASAK** (FE-32, gate'li): UI5 V2'de `$filter`'a `toupper()`/`tolower()` enjekte eder; SAP Gateway (/IWBEP) bunları DESTEKLEMEZ → **HTTP 400** "Function toupper/tolower is not supported" (SAP Note 1797736) → arama hiç sonuç döndürmez. `new Filter(path, FilterOperator.Contains, q)` — **caseSensitive parametresi VERME**; düz `substringof` zaten harf-duyarsız (DB collation, canlı kanıt 2026-06-24).
- **Wildcard (SAP alışkanlığı):** `*x*` / `x` → Contains · `x*` → StartsWith · `*x` → EndsWith (startswith/endswith /IWBEP'te DESTEKLENİR — toupper'ın aksine). Ortak `_parseSearchTerm` helper; literal asterisk aranmaz.
- **Kod / serbest-metin alanlarında** düz-token default `Contains` (kısmi-kod araması korunur; `defaultOp` config).
- **Kanonik referans (kopyala): `ERP/SD/ZSD001_CLC/ui/sales_order_report/`** — `Filter.view` (MultiInput+VHD), `Filter.controller` (`_openVH`/`_applyVHSearch`/`_syncTokens`/`_parseSearchTerm`), `TablePersonalizer` (`_onColumnFilter`). Teknik + tuzaklar: [`playbook/ui-freestyle-odata-v2.md` §C](../playbook/ui-freestyle-odata-v2.md).

### 10.1 `sap.ui.layout.Splitter` Namespace Kullanımı

```xml
<mvc:View
    xmlns:l="sap.ui.layout"
    xmlns:fl="sap.ui.layout.form"
    ...>

<l:Splitter orientation="Horizontal" height="100%">
    <l:contentAreas>
        <VBox>
            <layoutData>
                <l:SplitterLayoutData size="70%" resizable="true"/>
            </layoutData>
            ...
        </VBox>
    </l:contentAreas>
</l:Splitter>
```

**Kural:** `SplitterLayoutData` aggregation wrapper (`<layoutData>`) içinde yazılmalı — self-closing attribute olarak yazma.

### 10.2 Başlık Alanları — HBox/VBox Compact Layout

`SimpleForm/ResponsiveGridLayout` kullanma. Bunun yerine:

```xml
<HBox alignItems="Start" class="sapUiSmallMarginBegin sapUiSmallMarginEnd sapUiTinyMarginTop">

    <VBox class="sapUiSmallMarginEnd">
        <Label text="Alan Adı" required="true" design="Bold"/>
        <Input
            id="inpAlan"
            value="{orderModel>/header/alan}"
            width="9em"
            class="sapUiTinyMarginTop"/>
        <Text
            text="{orderModel>/header/alanAdi}"
            tooltip="{orderModel>/header/alanAdi}"
            class="zsd001FieldDesc"/>
    </VBox>

    <!-- Dikey ayraç -->
    <core:HTML content="&lt;div style='width:1px;height:4rem;background:#d9d9d9;margin:0 0.75rem;margin-top:1.5rem'/&gt;"/>

    <VBox class="sapUiSmallMarginEnd">
        ...
    </VBox>

</HBox>
```

### 10.3 Header Toolbar — Salt-Okunur Bilgiler

`ObjectStatus title+text` kullanma (yapışık görünür). Yerine:

```xml
<Toolbar>
    <Title text="Başlık" level="H4"/>
    <ToolbarSpacer/>
    <VBox class="sapUiSmallMarginEnd" alignItems="Center">
        <Label text="SatışOrg" design="Bold"/>
        <Text text="{orderModel>/header/salesOrganization}"/>
    </VBox>
    <VBox class="sapUiSmallMarginEnd" alignItems="Center">
        <Label text="DağKanal" design="Bold"/>
        <Text text="{orderModel>/header/distributionChannel}"/>
    </VBox>
</Toolbar>
```

---

## 11. MODEL YAPISI (models.js)

```javascript
sap.ui.define([
    "sap/ui/model/json/JSONModel",
    "sap/ui/Device"
], function (JSONModel, Device) {
    "use strict";

    return {
        createDeviceModel: function () {
            var oModel = new JSONModel(Device);
            oModel.setDefaultBindingMode("OneWay");
            return oModel;
        }
    };
});
```

---

## 12. ODATA ÇAĞRI KURALLARI

### 12.1 SimulatePricing — read() ile Çağır

```javascript
// DOĞRU
oODataModel.read("/SimulationItemResultSet", {
    urlParameters: {
        IvSalesOrderType: "...",
        IvItemsJson: sItemsJson
    },
    success: function (oData) {
        var aResults = oData.results || [];
    }
});

// YANLIŞ — 405 Method Not Allowed
// oODataModel.callFunction("/SimulatePricing", { method: "POST", ... })
```

### 12.2 Tüm Function Import'larda Wrapper Kontrolü

```javascript
var oResult = oData.<FunctionImportAdı> || oData;
```

### 12.3 JSON Parametreleri — Kısa Key Formatı

URL uzunluğunu kısa tutmak için:

| JSON Key | Anlamı |
|----------|--------|
| `I` | SalesOrderItem |
| `Q` | Quantity |
| `M` | Material |
| `U` | Unit |

```javascript
// ChangedItemsJson
[{ "I": "000010", "Q": 150 }]

// NewItemsJson
[{ "M": "000000000000054321", "Q": 100, "U": "ST" }]
```

### 12.4 Ölçü Birimi Dönüşümü

```javascript
var mUnitMap = { "ADT": "ST", "KAR": "ST" };
var sUnit = mUnitMap[oItem.unit] || oItem.unit || "ST";
```

---

## 13. KÜTÜPHANE KURALLARI

### 13.1 Kullanılacaklar

```json
"libs": {
    "sap.m":          {},
    "sap.ui.core":    {},
    "sap.ui.comp":    {},
    "sap.ui.layout":  {},
    "sap.ui.unified": {}
}
```

### 13.2 Kullanılmayacaklar

| Kütüphane | Neden |
|-----------|-------|
| `sap.f` | SAPUI5 1.120'de 404 verebiliyor — `DynamicSideContent` kullanılmıyor |
| `sap.ushell` | Launchpad bağımlılığı yaratır |

### 13.3 Annotation Datasource

```javascript
// YANLIŞ — SAP'de mevcut değilse 400 hatası verir
"mainAnnotation": {
    "uri": "/sap/opu/odata/SAP/ZSD_ORDER_SRV_VAN",
    ...
}

// DOĞRU — IWFND CATALOGSERVICE üzerinden
"ZSD_ORDER_ANNO_MDL": {
    "uri": "/sap/opu/odata/IWFND/CATALOGSERVICE;v=2/Annotations(TechnicalName='ZSD_ORDER_ANNO_MDL',Version='0001')/$value/",
    "type": "ODataAnnotation",
    "settings": { "localUri": "localService/mainService/ZSD_ORDER_ANNO_MDL.xml" }
}
```

---

## 14. YENİ UYGULAMA CHECKLIST

Yeni bir Fiori uygulaması oluşturulduğunda kontrol edilecekler:

- [ ] App ID → `com.example.<alan>.<uygulama>` formatında
- [ ] `package.json` → `sapuxLayer: "CUSTOMER_BASE"` ve standart scripts
- [ ] `devDependencies` → `@sap/ux-ui5-tooling` dahil
- [ ] `ui5.yaml` → `fiori-tools-proxy` middleware
- [ ] `ui5-deploy.yaml` → `deploy-to-abap` task + doğru BSP adı/paket/transport
- [ ] `manifest.json` → `_version: "1.60.0"`, `resources.json`, `flexEnabled: true`
- [ ] `manifest.json` → annotation dataSource + `localUri`
- [ ] `manifest.json` → `minUI5Version: "1.120.23"`
- [ ] `manifest.json` → routing `type: "View"` + her target'ta `id`
- [ ] `manifest.json` → `controlId: "app"` (appContainer değil)
- [ ] `Component.js` → `IAsyncContentCreation` interface
- [ ] `index.html` → `sapUiSizeCompact` body'de, `data-sap-ui-libs` YOK
- [ ] `index.html` → `data-handle-validation="true"`
- [ ] `App.view.xml` → `<App id="app"/>`
- [ ] `localService/mainService/metadata.xml` → SAP'ten alınmış
- [ ] `localService/mainService/<ANNO_MDL>.xml` → SAP'ten alınmış
- [ ] i18n iki-dosya kuralı uygulanmış mı? (bkz. §7.5 — İngilizce default + Türkçe override)
- [ ] Controller'larda `oData.<FunctionImportAdı> || oData` wrapper kontrolü
- [ ] `Success` kontrolünde 3 varyant: `true`, `"true"`, `"X"`
- [ ] **Her liste ekranı §16 ALV-paritesi standardını içeriyor** (zorunlu — ADR 0008)

---

## 15. REFERANS UYGULAMA

Tüm bu kuralların çalışan örneği:

```
<PROJECT_ROOT>\order_app\
```

Yeni bir uygulama yaratırken bu klasörü şablon olarak kullan:
1. `order_app/` klasörünü kopyala
2. Tüm dosyalarda `com.example.sd.orderapp` → yeni ID ile değiştir
3. `webapp/` içeriğini sıfırla, sadece altyapı dosyalarını (manifest, Component, index, model) tut
4. `ui5-deploy.yaml`'da BSP adı, paket ve transport'u güncelle
5. `localService/` için yeni servisin metadata'sını al

---

## 16. LİSTE EKRANI STANDARDI — ALV PARİTESİ (ZORUNLU, ADR 0008)

> **Bağlayıcı.** <PROJECT_NAME>'de **her liste ekranı** bu bileşeni içerir.
> AI, kullanıcı ayrıca istemese bile **otomatik** uygular. Gerekçe + tam
> karar: [`../governance/decisions/0008-liste-ekrani-alv-paritesi-standardi.md`](../governance/decisions/0008-liste-ekrani-alv-paritesi-standardi.md).
> Operasyonel pattern + gotcha: [`../playbook/ui-freestyle-odata-v2.md`](../playbook/ui-freestyle-odata-v2.md) §E.

> **⚠️ TABLO TEKNOLOJİSİ GÜNCEL (2026-06-08): GRID — bkz. §10.0.** Liste/rapor
> ekranları **`sap.ui.table.Table` (grid)** ile yapılır; sort/filtre grid'in
> **NATIVE** başlık menüsünden gelir → aşağıdaki madde 1-2 (`columnmenu.Menu` +
> `infoToolbar`) **GEREKMEZ**. m.Table yalnız mobil-öncelikli/hücre-zengin istisna.
> Bu bölümün **üst-ilkesi geçerli** (her liste ekranı ALV-paritesi: kolon
> göster/gizle + varyant + Excel — madde 3-5, grid'de de zorunlu); m.Table-spesifik
> mekanik (1-2) yalnız mobil-istisna içindir. Kanonik: §10.0 + playbook §E.

Her liste ekranı (grid; m.Table yalnız mobil-istisna) şunları **zorunlu** sağlar:

1. **(m.Table-legacy, grid'de NATIVE)** Kolon başlığı menüsü (`sap.m.table.columnmenu.Menu`): başlığa
   tıkla → hızlı **Sırala** (↑/↓) + alana **operatörlü Filtre**
   (tip-duyarlı: metin Contains/EQ/StartsWith/EndsWith/NE; sayı·tarih
   EQ/NE/GT/GE/LT/LE/BT; bool EQ). **`sap.m.P13nDialog`/P13nFilterPanel
   KULLANMA** (model-sync kırılgan — ADR 0008 reddi).
2. **Aktif filtre çubuğu** (tablo `infoToolbar`): `Alan op değer ✕`
   (✕=kaldır) + "Tümünü temizle"; filtreli kolon başlığı belirgin
   (`.zsd001FilterActive` benzeri stil).
3. **Kolon göster/gizle** popover ("Kolonlar" butonu).
4. **Excel export** (`sap.ui.export.Spreadsheet`): gerçek `.xlsx`,
   OData binding'den **filtreye uyan TÜM satırlar**; kapsam sorulur
   (Görünür / Tüm kolonlar). `manifest` libs → `sap.ui.export`.
5. State **localStorage** kalıcı; selection/scr1 filtreleriyle **AND**.

**Kanonik implementasyon (kopyala-uyarla) — GRID sürümü (§10.0):**
`ERP/SD/ZSD001_CLC/ui/delivery_report/webapp/util/TablePersonalizer.js` (grid
reusable util — `new TablePersonalizer({table, persoKey, columns:[{key,path,colId,
text,type}], bundle, baseFilters})`; DB-backed varyant `ZSD000_UI_VARIANT_O2`) +
`List.controller.js` `onColumns`/`onExportExcel` + i18n key seti (`op.*`, `flt.*`,
`exp.*`, `btn.cols`, `btn.excel`). (Voyage util = eski m.Table sürümü; yeni iş grid'i kopyalar.)

**Yeni uygulamada:** liste ekranı iskeleti kurulurken bu util kopyalanır,
kolon meta'sı (key/path/colId/text/type) uygulamaya göre doldurulur,
buton + i18n eklenir. Sıfırdan filtre/sort/export YAZILMAZ.

---

## 17. DÜZENLENEBİLİR SAYISAL INPUT — `type="Number"` YASAK (ZORUNLU)

Tablo/grid içindeki **düzenlenebilir sayısal Input** (miktar, sevk miktarı vb.) için
`sap.m.Input type="Number"` **KULLANILMAZ**:

- HTML `<input type="number">` yukarı/aşağı **ok tuşuyla değeri artırır/azaltır** →
  kullanıcı satır-gezmek için ok'a basınca **miktar sessizce değişir** (veri bozulması).
- Spinner okları yer kaplar; grid satırları arası ok-navigasyonunu bozar.
- Number'ın ok-artırmasını kapatan temiz UI5 property yok.

**Çözüm:** `type="Text"` + `liveChange` ile **canlı rakam filtresi** (`onNumericLiveChange`,
binding-path bağımsız). Harf engellenir, ok-tuşu değeri değiştirmez, ok'la satır-gezme çalışır.
`change`'de cap/validasyon yine parseFloat ile.

```xml
<Input value="{model>quantity}" type="Text" textAlign="End"
       change=".onItemQtyChange" liveChange=".onNumericLiveChange" .../>
```
```js
onNumericLiveChange: function (oEvent) {
    var oInput = oEvent.getSource(), sVal = oEvent.getParameter("value");
    if (sVal == null) { return; }
    var sClean = sVal.replace(/[^0-9.,]/g, "").replace(/,/g, ".");
    var p = sClean.split("."); if (p.length > 2) { sClean = p[0] + "." + p.slice(1).join(""); }
    if (sClean !== sVal) { oInput.setValue(sClean); var oB = oInput.getBinding("value"); if (oB) { oB.setValue(sClean); } }
}
```
Uygulama: ZSD001 (picker + SE kalem Create/Change), ZSD001 (sipariş kalem Create/Change).

---

## §18 GENEL UI TASARIM DESENLERİ (02'den taşındı, 2026-07-31)

> Bu bölüm eskiden `standards/02-coding-backend.md` içindeki "FRONTEND — FIORI / SAPUI5"
> bloğundaydı (dedup kararı D2, 2026-07-31). İçerik klasik SEGW/Fiori-Elements referansı +
> genel UX prensiplerini kapsar. **TD'nin (bu proje) sabit yaklaşımı freestyle + OData V2'dir**
> (§0-§17) — §18.1/§18.2 çoğunlukla dış-referans niteliğindedir, TD'de nadiren dokunulur.
> §18'in geri kalanı (genel UX ilkeleri, Object Page, status gösterimi, tema, erişilebilirlik,
> zorunlu UX kuralları) her uygulamada geçerlidir ve §1-§17'deki TD-spesifik kanonik desenlerle
> (grid=§10.0/§16, filtre=§10.0.1, i18n=§7.5, feedback=§7.6, sayısal input=§17) ÇAKIŞMAZ —
> çakışan orijinal içerik (SmartTable, SimpleForm, m.Table varsayılan, FilterBar ComboBox,
> `type="Number"`) bu taşımada zaten çıkarıldı; kalanlar aşağıda kendi başına anlaşılır haldedir.

### 18.1 UI Seçim Çerçevesi

Her UI implementasyonunun başında şunu belirt:
```
UI Approach: [Fiori Elements / Freestyle / Hybrid]
Reason: [One sentence why]
OData EntitySet used: [Name]
```
> **TD-sabit not (2026-07-31):** Bu projede yaklaşım **sabit**: Freestyle + OData V2 (RAP
> tüketen). Yukarıdaki çerçeve genel/diğer-proje senaryoları için referanstır — TD'de "Fiori
> Elements mi Freestyle mi" sorusu tekrar sorulmaz, doğrudan freestyle ile başlanır.

### 18.2 Fiori Elements — OData v2 Annotations (yalnız klasik dokunuş — kapsam-dışı istisna)

> **Kapsam notu:** Bu alt-bölüm yalnız **klasik Fiori Elements** (annotation-driven, freestyle
> DEĞİL) bir ekrana dokunulması gerektiğinde geçerlidir — TD'de nadir/istisnai. Çoğunluk iş
> §1-§17'deki freestyle desenini kullanır; bu annotation seti onu DEĞİŞTİRMEZ.

```xml
<!-- annotations.xml — for Fiori Elements OData v2 -->
<Annotations Target="Z_MYAPP_SRV.MyEntityType">

  <!-- List Report: filter fields -->
  <Annotation Term="UI.SelectionFields">
    <Collection>
      <PropertyPath>CompanyCode</PropertyPath>
      <PropertyPath>Status</PropertyPath>
      <PropertyPath>DocumentDate</PropertyPath>
    </Collection>
  </Annotation>

  <!-- List Report: table columns -->
  <Annotation Term="UI.LineItem">
    <Collection>
      <Record Type="UI.DataField">
        <PropertyValue Property="Value" Path="EntityId"/>
        <PropertyValue Property="Label" String="ID"/>
      </Record>
      <Record Type="UI.DataField">
        <PropertyValue Property="Value" Path="Description"/>
        <PropertyValue Property="Label" String="Description"/>
        <PropertyValue Property="Importance" EnumMember="UI.ImportanceType/High"/>
      </Record>
      <Record Type="UI.DataFieldForAnnotation">
        <PropertyValue Property="Target" AnnotationPath="@UI.DataPoint#StatusKPI"/>
        <PropertyValue Property="Label" String="Status"/>
      </Record>
    </Collection>
  </Annotation>

  <!-- Object Page: header -->
  <Annotation Term="UI.HeaderInfo">
    <Record>
      <PropertyValue Property="TypeName"       String="My Entity"/>
      <PropertyValue Property="TypeNamePlural" String="My Entities"/>
      <PropertyValue Property="Title">
        <Record Type="UI.DataField">
          <PropertyValue Property="Value" Path="Description"/>
        </Record>
      </PropertyValue>
      <PropertyValue Property="Description">
        <Record Type="UI.DataField">
          <PropertyValue Property="Value" Path="EntityId"/>
        </Record>
      </PropertyValue>
    </Record>
  </Annotation>

  <!-- Object Page: section facets -->
  <Annotation Term="UI.Facets">
    <Collection>
      <Record Type="UI.ReferenceFacet">
        <PropertyValue Property="ID"     String="GeneralInfo"/>
        <PropertyValue Property="Label"  String="General Information"/>
        <PropertyValue Property="Target" AnnotationPath="@UI.FieldGroup#General"/>
      </Record>
      <Record Type="UI.ReferenceFacet">
        <PropertyValue Property="ID"     String="Items"/>
        <PropertyValue Property="Label"  String="Items"/>
        <PropertyValue Property="Target" AnnotationPath="ToItems/@UI.LineItem"/>
      </Record>
    </Collection>
  </Annotation>

  <!-- Value Help annotation for Fiori Elements -->
  <Annotation Term="Common.ValueList" Qualifier="Status">
    <Record Type="Common.ValueListType">
      <PropertyValue Property="CollectionPath" String="ZVH_StatusSet"/>
      <PropertyValue Property="Parameters">
        <Collection>
          <Record Type="Common.ValueListParameterInOut">
            <PropertyValue Property="LocalDataProperty" PropertyPath="Status"/>
            <PropertyValue Property="ValueListProperty" String="StatusCode"/>
          </Record>
          <Record Type="Common.ValueListParameterDisplayOnly">
            <PropertyValue Property="ValueListProperty" String="StatusText"/>
          </Record>
        </Collection>
      </PropertyValue>
    </Record>
  </Annotation>

</Annotations>
```

### 18.3 DynamicPage İskeleti (Genel Şablon)

```xml
<!-- Always compact, always i18n, always proper error state -->
<mvc:View controllerName="com.mycompany.myapp.controller.List"
          xmlns:mvc="sap.ui.core.mvc"
          xmlns="sap.m"
          xmlns:f="sap.f"
          xmlns:l="sap.ui.layout"
          displayBlock="true">

  <f:DynamicPage id="dynamicPage" headerExpanded="true" toggleHeaderOnTitleClick="true">

    <f:title>
      <f:DynamicPageTitle>
        <f:heading>
          <Title text="{i18n>listTitle}" level="H2"/>
        </f:heading>
        <f:actions>
          <Button text="{i18n>create}" type="Emphasized" press=".onCreatePress"/>
          <Button icon="sap-icon://refresh" press=".onRefresh" tooltip="{i18n>refresh}"/>
        </f:actions>
        <f:snappedContent>
          <Label text="{= ${listModel>/totalCount} + ' ' + ${i18n>items} }"/>
        </f:snappedContent>
      </f:DynamicPageTitle>
    </f:title>

    <f:header>
      <f:DynamicPageHeader pinnable="true">
        <l:Grid defaultSpan="L4 M6 S12" hSpacing="1">
          <!-- Filter fields here -->
          <SearchField placeholder="{i18n>searchPlaceholder}" search=".onSearch"
                       width="100%"/>
        </l:Grid>
      </f:DynamicPageHeader>
    </f:header>

    <f:content>
      <!-- Empty state — always implement -->
      <IllustratedMessage id="emptyState" visible="false"
                          illustrationType="sapIllus-EmptyList"
                          title="{i18n>noDataTitle}"
                          description="{i18n>noDataDesc}"/>

      <!-- Tablo: liste/rapor ekranında sap.ui.table.Table (grid) kullan — bkz. §10.0/§16.
           sap.m.Table YALNIZ mobil-öncelikli/hücre-zengin istisna ekranlarda (§18.11/§18.16). -->

    </f:content>
  </f:DynamicPage>
</mvc:View>
```

### 18.4 Controller İskeleti (Genel Şablon)

```javascript
sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageToast",
  "sap/m/MessageBox"
], function(Controller, JSONModel, MessageToast, MessageBox) {
  "use strict";

  return Controller.extend("com.mycompany.myapp.controller.List", {

    onInit: function() {
      // Local UI state model — separate from OData model
      this.getView().setModel(new JSONModel({
        busy:           false,
        selectionCount: 0,
        totalCount:     0
      }), "listModel");

      // (§5/§9.2: density class BODY'ye index.html'de eklenir — controller'da
      //  addStyleClass KULLANILMAZ; eski 02 deseni bilinçli çıkarıldı, 2026-07-31 D2-review)
    },

    // OData read with error handling
    _loadData: function(oFilter) {
      var oModel = this.getView().getModel();
      var oTable = this.byId("mainTable");

      oTable.setBusy(true);
      oModel.read("/MyEntitySet", {
        filters:    oFilter ? [oFilter] : [],
        urlParameters: { "$inlinecount": "allpages" },
        success: function(oData) {
          this.getView().getModel("listModel").setProperty(
            "/totalCount", oData.__count || oData.results.length
          );
          oTable.setBusy(false);
        }.bind(this),
        error: function(oError) {
          oTable.setBusy(false);
          this._handleODataError(oError);
        }.bind(this)
      });
    },

    // Centralized OData error handler
    _handleODataError: function(oError) {
      var sMessage = this.getView().getModel("i18n")
                         .getResourceBundle().getText("errorGeneric");
      try {
        var oBody = JSON.parse(oError.responseText);
        sMessage = (oBody.error && oBody.error.message && oBody.error.message.value)
                   || sMessage;
      } catch(e) { /* use default message */ }

      MessageBox.error(sMessage);
    },

    // CSRF-safe write operation
    _callFunctionImport: function(sFuncName, oParams) {
      var oModel = this.getView().getModel();
      return new Promise(function(resolve, reject) {
        oModel.callFunction("/" + sFuncName, {
          method:     "POST",
          urlParameters: oParams,
          success:    resolve,
          error:      function(e) { reject(e); }
        });
      });
    }
  });
});
```

> **§7.6 ile birleştirme notu:** Yukarıdaki `_handleODataError` genel/didaktik isimdir; bu
> projenin (TD) kanonik hata-parse fonksiyonu **`_parseError`** adını taşır (§7.6, referans:
> ZSD001 `CreateOrder.controller.js`) ve gerçek SAP `responseText`/`error.message.value`'yu
> generic i18n mesajıyla YUTMADAN basar. Yeni kodda `_handleODataError` değil, §7.6'daki
> kanonik `_parseError` deseni kullanılır — ikisi aynı fikrin (merkezi hata ayrıştırma) farklı
> isimli iki tarifidir, TD'de tek isim (`_parseError`) geçerlidir.

### 18.5 $batch Request Handling

> **Kapsam notu:** Yalnız `useBatch:true` kullanan senaryolar için. TD'nin SEGW-V2 servisleri
> için varsayılanı **`useBatch:false`**'tur (§3.2) — bu bölüm `useBatch:true` tercih edilen
> istisnai/başka-proje senaryoları içindir.

```javascript
// === $batch — Deferred Group Pattern ===

// 1. Deferred group tanımla (otomatik gönderilmez, submitChanges bekler)
var oModel = this.getView().getModel();
oModel.setDeferredGroups(["batchCreate"]);

// 2. Birden fazla create'i aynı batch'e ekle
oModel.create("/MyEntitySet", oEntry1, { groupId: "batchCreate" });
oModel.create("/MyEntitySet", oEntry2, { groupId: "batchCreate" });
oModel.create("/MyEntitySet", oEntry3, { groupId: "batchCreate" });

// 3. Hepsini tek seferde gönder
oModel.submitChanges({
  groupId: "batchCreate",
  success: function(oData) {
    // oData.__batchResponses içinde her bir işlemin sonucu var
    var aResponses = oData.__batchResponses;
    var bHasError = aResponses.some(function(resp) {
      return resp.statusCode && parseInt(resp.statusCode, 10) >= 400;
    });
    if (bHasError) {
      MessageBox.error("Some operations failed");
    } else {
      MessageBox.success("All records created"); // §7.6: create/save başarısı = MessageBox
    }
  },
  error: function(oError) {
    this._handleODataError(oError);
  }.bind(this)
});

// 4. Batch iptal — gönderilmemiş değişiklikleri temizle
// oModel.resetChanges(undefined, undefined, "batchCreate");

// === submitChanges vs. tek işlem ===
// useBatch:true → model.create/update/remove otomatik batch'e eklenir
// submitChanges() ile gönderilir
// useBatch:false → her işlem anında gönderilir (SEGW-V2 servislerinde PRODÜKSİYON standardımız — §3.2)
```

### 18.6 OData v2 $filter — Frontend Filter Pattern

> ⛔ **`caseSensitive:false` YASAK** (§10.0.1/FE-32) — SAP Gateway `toupper()`/`tolower()`'ı
> desteklemez, HTTP 400 verir. Aşağıdaki `Filter`/`FilterOperator` API'si `caseSensitive`
> parametresi OLMADAN kullanılır; düz `substringof` zaten harf-duyarsızdır (DB collation).

```javascript
sap.ui.define([
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function(Filter, FilterOperator) {

  // === Single Filter ===
  var oFilter = new Filter("CompanyCode", FilterOperator.EQ, "1000");

  // === Multiple Filters — AND logic ===
  var oFilterAnd = new Filter({
    filters: [
      new Filter("CompanyCode", FilterOperator.EQ, "1000"),
      new Filter("Status", FilterOperator.NE, "X"),
      new Filter("DocumentDate", FilterOperator.BT, "2024-01-01", "2024-12-31")
    ],
    and: true   // true = AND, false = OR
  });

  // === Multi-value — OR logic (same field, multiple values) ===
  var oFilterOr = new Filter({
    filters: [
      new Filter("Status", FilterOperator.EQ, "A"),
      new Filter("Status", FilterOperator.EQ, "B"),
      new Filter("Status", FilterOperator.EQ, "C")
    ],
    and: false  // OR between same-field values
  });

  // === Combined: (CompanyCode = 1000) AND (Status = A OR Status = B) ===
  var oCombined = new Filter({
    filters: [ oFilterAnd, oFilterOr ],
    and: true
  });

  // === Apply to binding ===
  // this.byId("mainTable").getBinding("items").filter(oCombined);

  // === FilterOperator reference ===
  // EQ, NE, LT, LE, GT, GE — comparison
  // BT — between (requires two values)
  // Contains, StartsWith, EndsWith — string matching
  // Any, All — lambda operators (OData v4 only, NOT v2)
});
```

### 18.7 Value Help (F4) — Alan-Düzeyi Freestyle Pattern

```xml
<!-- View: Input with value help button -->
<Input id="inputStatus"
       value="{Status}"
       showValueHelp="true"
       valueHelpRequest=".onStatusValueHelp"
       placeholder="{i18n>selectStatus}"/>
```

```javascript
// Controller: Value Help Dialog
sap.ui.define([
  "sap/ui/comp/valuehelpdialog/ValueHelpDialog",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function(ValueHelpDialog, Filter, FilterOperator) {

  // In controller:
  onStatusValueHelp: function(oEvent) {
    var oInput = oEvent.getSource();
    var oModel = this.getView().getModel();

    // sap.ui.comp kullanılacaksa manifest.json dependencies'e ekle
    if (!this._oValueHelpDialog) {
      this._oValueHelpDialog = new ValueHelpDialog({
        title: this.getView().getModel("i18n").getResourceBundle().getText("selectStatus"),
        supportMultiselect: false,
        key: "StatusCode",
        descriptionKey: "StatusText",
        ok: function(oEvt) {
          var aTokens = oEvt.getParameter("tokens");
          if (aTokens.length > 0) {
            oInput.setValue(aTokens[0].getKey());
          }
          this._oValueHelpDialog.close();
        }.bind(this),
        cancel: function() {
          this._oValueHelpDialog.close();
        }.bind(this)
      });
    }

    // Load value help data from OData
    oModel.read("/ZVH_StatusSet", {
      success: function(oData) {
        this._oValueHelpDialog.setModel(
          new sap.ui.model.json.JSONModel({ items: oData.results }));
        this._oValueHelpDialog.getTable().bindRows("/items");
        this._oValueHelpDialog.open();
      }.bind(this),
      error: this._handleODataError.bind(this)
    });
  }
});
```

> **Alternatif (sap.ui.comp olmadan):** `sap.m.SelectDialog` veya `sap.m.TableSelectDialog`
> kullan — daha hafif, ek dependency gerektirmez. (Rapor/liste **filtre ekranı** için kanonik
> desen bu değil, §10.0.1/FE-32'deki `MultiInput` + `ValueHelpDialog`'dur — bu bölüm tekil
> alan-düzeyi F4 içindir.)

### 18.8 Message Handling — Message Popover Pattern

> **§7.6 çapraz-ref:** MessagePopover form-validasyonu/çoklu-hata gösterimi içindir (her
> detail/edit sayfasında). **Save/create/action BAŞARISI** için kanonik geribildirim yine
> §7.6'daki `MessageBox.success` (modal, OK'lenince navigasyon) — MessagePopover onun YERİNE
> geçmez, validasyon hatalarını tamamlar.

```xml
<!-- View: Message popover button in footer -->
<footer>
  <OverflowToolbar>
    <ToolbarSpacer/>
    <Button id="messagePopoverBtn"
            icon="sap-icon://message-popup"
            text="{= ${message>/}.length}"
            type="{= ${message>/}.length > 0 ? 'Negative' : 'Default'}"
            press=".onMessagePopoverPress"
            visible="{= ${message>/}.length > 0}"/>
    <Button text="{i18n>save}" type="Emphasized" press=".onSave"/>
  </OverflowToolbar>
</footer>
```

```javascript
sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/m/MessagePopover",
  "sap/m/MessagePopoverItem",
  "sap/ui/core/message/Message",
  "sap/ui/core/MessageType"
], function(Controller, MessagePopover, MessagePopoverItem, Message, MessageType) {

  return Controller.extend("com.mycompany.myapp.controller.Detail", {

    onInit: function() {
      // Register message manager
      this._oMessageManager = sap.ui.getCore().getMessageManager();
      this.getView().setModel(this._oMessageManager.getMessageModel(), "message");
      this._oMessageManager.registerObject(this.getView(), true);

      // Create message popover
      this._oMessagePopover = new MessagePopover({
        items: {
          path: "message>/",
          template: new MessagePopoverItem({
            type:        "{message>type}",
            title:       "{message>message}",
            description: "{message>description}",
            subtitle:    "{message>additionalText}"
          })
        }
      });
      this.byId("messagePopoverBtn").addDependent(this._oMessagePopover);
    },

    onMessagePopoverPress: function(oEvent) {
      this._oMessagePopover.toggle(oEvent.getSource());
    },

    // Client-side validation example
    _validateForm: function() {
      this._oMessageManager.removeAllMessages();
      var bValid = true;

      var sCompanyCode = this.byId("inputBukrs").getValue();
      if (!sCompanyCode) {
        this._oMessageManager.addMessages(new Message({
          message:    this._getText("validationCompanyRequired"),
          type:       MessageType.Error,
          target:     "/CompanyCode",
          processor:  this.getView().getModel()
        }));
        bValid = false;
      }

      return bValid;
    },

    onSave: function() {
      if (!this._validateForm()) {
        this.onMessagePopoverPress({ getSource: function() {
          return this.byId("messagePopoverBtn");
        }.bind(this) });
        return;
      }
      // ... proceed with save ...
    }
  });
});
```

### 18.9 UI Design Principles — 10 İlke

```
1. DENSITY:       Compact mode for desktop enterprise apps (cozy for mobile)
2. FEEDBACK:      Every user action must have immediate visual feedback (busy indicator, toast)
3. EMPTY STATE:   Always implement IllustratedMessage for empty tables/lists
4. ERROR STATE:   Always show meaningful error messages — never raw technical errors
5. NAVIGATION:    Breadcrumbs on Object Page, back button always functional
6. LOADING:       Table-level busy indicator, not page-level (avoid full-screen blocking)
7. TYPOGRAPHY:    Only SAP Fiori font scale — no custom font-size in CSS
8. COLORS:        Only SAP theming variables — never hardcoded hex in CSS
9. ICONS:         Only sap-icon:// font — no external icon libraries
10. RESPONSIVE:   Test L/M/S breakpoints — Grid with L4 M6 S12 default span
```

### 18.10 A. Visual Hierarchy — Görsel Hiyerarşi

> **Kural:** Kullanıcı ekrana baktığında 3 saniye içinde en önemli bilgiyi bulabilmeli.

```
PRENSIP 1 — Önem Sıralaması:
  ┌─────────────────────────────────────────────────────────┐
  │  H1: Sayfa Başlığı (tek, net, anlamlı)                 │
  │  H2: Section başlıkları                                 │
  │  H3: Sub-section / Tablo başlıkları                     │
  │  Body: Form alanları, tablo hücreleri                   │
  │  Caption: Yardımcı metin, footnote                      │
  └─────────────────────────────────────────────────────────┘

PRENSIP 2 — Renk ile Vurgulama:
  - Primary action: Emphasized (mavi) → Yalnızca 1 tane per sayfa
  - Secondary action: Default (beyaz/gri)
  - Destructive action: Reject (kırmızı) → Silme, iptal işlemleri
  - Success bildirim: Positive (yeşil) → Onay, tamamlama

PRENSIP 3 — Boşluk ve Gruplama (Gestalt):
  - İlişkili alanlar grupla → FieldGroup / HBox+VBox düzeni (§10.2 — SimpleForm YASAK)
  - Gruplar arası boşluk bırak → Section separator
  - Çok fazla bilgiyi tek seferde gösterme → Progressive disclosure
```

### 18.11 B. Tablo — Column Priority ile Responsive Gizleme

> **İstisna notu:** Bu alt-bölüm **yalnız m.Table-İSTİSNA ekranlarda** (mobil-öncelikli veya
> hücre-zengin/wrap gereken ekranlar) geçerlidir. Liste/rapor ekranı = **grid** (§10.0/§16);
> grid'de kolon gizleme farklı mekanizmayla (`TablePersonalizer` kolon göster/gizle) çözülür,
> aşağıdaki `importance`/`demandPopin` mekaniği GEREKMEZ.

```xml
<!-- Compact tablo: dar ekranlarda önemsiz sütunları otomatik gizle -->
<Table id="mainTable"
       items="{/MyEntitySet}"
       growing="true"
       growingThreshold="50"
       sticky="ColumnHeaders,HeaderToolbar"
       fixedLayout="Strict"
       popinLayout="GridSmall"
       alternateRowColors="true">

  <columns>
    <!-- HER ZAMAN görünsün -->
    <Column importance="High" width="8rem">
      <Text text="{i18n>colId}"/>
    </Column>
    <Column importance="High">
      <Text text="{i18n>colDescription}"/>
    </Column>

    <!-- Dar ekranda pop-in olarak göster -->
    <Column importance="Medium" minScreenWidth="Tablet"
            demandPopin="true" popinDisplay="Inline">
      <Text text="{i18n>colCompany}"/>
    </Column>

    <!-- Sadece geniş ekranda göster -->
    <Column importance="Low" minScreenWidth="Desktop"
            demandPopin="true" popinDisplay="Block">
      <Text text="{i18n>colCreatedBy}"/>
    </Column>

    <!-- Sayısal sütunlar sağa hizalı -->
    <Column importance="High" hAlign="End" width="10rem">
      <Text text="{i18n>colAmount}"/>
    </Column>

    <!-- Status sütunu -->
    <Column importance="High" hAlign="Center" width="8rem">
      <Text text="{i18n>colStatus}"/>
    </Column>
  </columns>

  <items>
    <ColumnListItem type="Navigation" press=".onItemPress"
                    highlight="{= ${Status} === 'E' ? 'Error' :
                                   ${Status} === 'B' ? 'Warning' :
                                   ${Status} === 'A' ? 'Success' : 'None'}">
      <cells>
        <ObjectIdentifier title="{EntityId}" text="{CompanyCode}"/>
        <Text text="{Description}" wrapping="false"/>
        <Text text="{CompanyCodeName}"/>
        <Text text="{CreatedBy}"/>
        <ObjectNumber number="{
            path: 'Amount',
            type: 'sap.ui.model.type.Currency',
            formatOptions: { showMeasure: false }
          }" unit="{CurrencyCode}"
          state="{= ${Amount} < 0 ? 'Error' : 'None'}"/>
        <ObjectStatus text="{StatusText}"
                      state="{= ${Status} === 'E' ? 'Error' :
                                 ${Status} === 'B' ? 'Warning' :
                                 ${Status} === 'A' ? 'Success' : 'None'}"
                      icon="{= ${Status} === 'E' ? 'sap-icon://error' :
                                ${Status} === 'B' ? 'sap-icon://alert' :
                                ${Status} === 'A' ? 'sap-icon://sys-enter-2' :
                                'sap-icon://question-mark'}"/>
      </cells>
    </ColumnListItem>
  </items>
</Table>
```

### 18.12 C. Object Page — Profesyonel Detay Sayfası

> **Kural:** Object Page = Fiori'nin en güçlü kontrolü. Doğru kullanıldığında 10x daha profesyonel görünür.

```xml
<!-- Object Page — KPI'lı Header + Organize Bölümler -->
<ObjectPageLayout id="objectPage"
                  showTitleInHeaderContent="false"
                  useIconTabBar="true"
                  upperCaseAnchorBar="false"
                  enableLazyLoading="true">

  <!-- === HEADER TITLE === -->
  <headerTitle>
    <ObjectPageDynamicHeaderTitle>
      <heading>
        <HBox alignItems="Center">
          <Avatar src="sap-icon://document" displaySize="S"
                  backgroundColor="Accent6" class="sapUiSmallMarginEnd"/>
          <Title text="{Description}" level="H2" wrapping="true"/>
        </HBox>
      </heading>
      <snappedHeading>
        <FlexBox alignItems="Center">
          <Avatar src="sap-icon://document" displaySize="XS"
                  backgroundColor="Accent6" class="sapUiSmallMarginEnd"/>
          <Title text="{Description}" level="H3"/>
        </FlexBox>
      </snappedHeading>
      <expandedContent>
        <Label text="{i18n>lblEntityId}: {EntityId}"/>
      </expandedContent>
      <snappedContent>
        <Label text="{EntityId}"/>
      </snappedContent>
      <breadcrumbs>
        <Breadcrumbs>
          <Link text="{i18n>listTitle}" press=".onNavBack"/>
        </Breadcrumbs>
      </breadcrumbs>
      <actions>
        <Button text="{i18n>btnEdit}" type="Emphasized" press=".onEdit"
                visible="{= !${detailModel>/editMode}}"/>
        <Button text="{i18n>btnSave}" type="Emphasized" press=".onSave"
                visible="{detailModel>/editMode}"/>
        <Button text="{i18n>btnCancel}" press=".onCancel"
                visible="{detailModel>/editMode}"/>
        <Button icon="sap-icon://action" type="Ghost" press=".onMoreActions"/>
      </actions>
    </ObjectPageDynamicHeaderTitle>
  </headerTitle>

  <!-- === HEADER CONTENT — KPI Kartları === -->
  <headerContent>
    <FlexBox wrap="Wrap" class="sapUiSmallMarginBeginEnd">
      <!-- KPI 1: Toplam Tutar -->
      <m:VBox class="sapUiSmallMarginEnd sapUiSmallMarginBottom" width="10rem">
        <ObjectAttribute title="{i18n>colAmount}"/>
        <ObjectNumber number="{
            path: 'Amount',
            type: 'sap.ui.model.type.Currency',
            formatOptions: { showMeasure: false }
          }" unit="{CurrencyCode}" emphasized="true"
          state="{= ${Amount} > 10000 ? 'Success' : 'None'}"/>
      </m:VBox>
      <!-- KPI 2: Durum -->
      <m:VBox class="sapUiSmallMarginEnd sapUiSmallMarginBottom" width="10rem">
        <ObjectAttribute title="{i18n>colStatus}"/>
        <ObjectStatus text="{StatusText}" state="{StatusState}"
                      icon="{StatusIcon}" inverted="true"/>
      </m:VBox>
      <!-- KPI 3: Oluşturma Tarihi -->
      <m:VBox class="sapUiSmallMarginEnd sapUiSmallMarginBottom" width="10rem">
        <ObjectAttribute title="{i18n>lblCreatedAt}"/>
        <Text text="{
            path: 'CreatedAt',
            type: 'sap.ui.model.type.Date',
            formatOptions: { style: 'medium' }
          }"/>
      </m:VBox>
      <!-- KPI 4: Progress Indicator (opsiyonel) -->
      <m:VBox class="sapUiSmallMarginEnd sapUiSmallMarginBottom" width="14rem">
        <ObjectAttribute title="{i18n>lblProgress}"/>
        <ProgressIndicator percentValue="{Progress}"
                           displayValue="{= ${Progress} + '%'}"
                           state="{= ${Progress} >= 80 ? 'Success' :
                                      ${Progress} >= 50 ? 'Warning' : 'Error'}"
                           showValue="true"/>
      </m:VBox>
    </FlexBox>
  </headerContent>

  <!-- === SECTIONS — IconTabBar ile gruplandırma === -->
  <sections>
    <!-- Section 1: Genel Bilgiler -->
    <ObjectPageSection id="sectionGeneral" title="{i18n>sectionGeneral}">
      <subSections>
        <ObjectPageSubSection title="{i18n>subSectionBasic}">
          <blocks>
            <!-- Form burada (§10.2 HBox/VBox deseni — SimpleForm/ResponsiveGridLayout DEĞİL) -->
          </blocks>
        </ObjectPageSubSection>
      </subSections>
    </ObjectPageSection>

    <!-- Section 2: Kalemler (Table) -->
    <ObjectPageSection id="sectionItems" title="{i18n>sectionItems}">
      <subSections>
        <ObjectPageSubSection>
          <blocks>
            <!-- Item tablosu burada -->
          </blocks>
        </ObjectPageSubSection>
      </subSections>
    </ObjectPageSection>

    <!-- Section 3: Notlar / Ekler -->
    <ObjectPageSection id="sectionNotes" title="{i18n>sectionNotes}">
      <subSections>
        <ObjectPageSubSection>
          <blocks>
            <FeedInput post=".onAddNote" placeholder="{i18n>addNote}" growing="true"/>
            <!-- Timeline veya Feed List burada -->
          </blocks>
        </ObjectPageSubSection>
      </subSections>
    </ObjectPageSection>
  </sections>
</ObjectPageLayout>
```

### 18.13 E. Status Gösterimi — Semantic Colors & Icons

> **Kural:** Status alanlarını asla düz text olarak gösterme. Renk + ikon + state kombinasyonu kullan.

```javascript
// Controller — Status'tan görsel state hesaplama
_formatStatusState: function(sStatus) {
  var mStates = {
    "01": "Success",    // Onaylı → Yeşil
    "02": "Warning",    // Beklemede → Turuncu
    "03": "Error",      // Reddedildi → Kırmızı
    "04": "Information", // Bilgi → Mavi
    "05": "None"        // Taslak → Gri
  };
  return mStates[sStatus] || "None";
},

_formatStatusIcon: function(sStatus) {
  var mIcons = {
    "01": "sap-icon://sys-enter-2",      // ✓ Yeşil check
    "02": "sap-icon://pending",           // ⏳ Bekleme
    "03": "sap-icon://decline",           // ✕ Red
    "04": "sap-icon://information",       // ℹ Bilgi
    "05": "sap-icon://document"           // 📄 Taslak
  };
  return mIcons[sStatus] || "sap-icon://question-mark";
}
```

```xml
<!-- View'da kullanım — 3 farklı status gösterim seviyesi -->

<!-- Seviye 1: Basit (sadece renk + text) -->
<ObjectStatus text="{StatusText}"
              state="{path: 'Status', formatter: '.formatter.formatStatusState'}"/>

<!-- Seviye 2: Orta (renk + text + ikon) -->
<ObjectStatus text="{StatusText}"
              state="{path: 'Status', formatter: '.formatter.formatStatusState'}"
              icon="{path: 'Status', formatter: '.formatter.formatStatusIcon'}"/>

<!-- Seviye 3: Vurgulu (inverted — dolu arka plan) — header KPI için -->
<ObjectStatus text="{StatusText}"
              state="{path: 'Status', formatter: '.formatter.formatStatusState'}"
              icon="{path: 'Status', formatter: '.formatter.formatStatusIcon'}"
              inverted="true"/>

<!-- Row Highlighting — tablo satırlarını status'a göre renklendir -->
<ColumnListItem highlight="{path: 'Status',
                            formatter: '.formatter.formatStatusState'}">
```

### 18.14 F. Micro-Interactions & Loading UX

> **Kural:** Kullanıcı herhangi bir aksiyon aldığında anında görsel geri bildirim olmalı. "Hiçbir şey olmuyor" hissi = kötü UX.

```javascript
// 1. Skeleton Loading — ilk yüklemede busy indicator yerine
onInit: function() {
  // Sayfayı açarken tablo shimmer/skeleton göstersin
  this.byId("mainTable").setBusyIndicatorDelay(0);  // Anında busy göster
  this.byId("mainTable").setBusy(true);
},

// 2. Inline Action Feedback — buton basıldığında (§7.6: aksiyon başarısı → MessageBox.success)
onApprove: function(oEvent) {
  var oButton = oEvent.getSource();
  oButton.setBusy(true);  // Butonu busy yap (tıklanamaz)

  this._callFunctionImport("Approve", { EntityId: sId })
    .then(function() {
      oButton.setBusy(false);
      MessageBox.success(this._getText("msg.approve.success"));   // §7.6 — MessageToast+nav YASAK
      this.getView().getModel().refresh();  // Tabloyu yenile
    }.bind(this))
    .catch(function(oError) {
      oButton.setBusy(false);
      this._handleODataError(oError);
    }.bind(this));
},

// 3. Optimistic UI — silme işleminde anında tablodan kaldır
onDeleteItem: function(oEvent) {
  var oItem = oEvent.getParameter("listItem");
  var sPath = oItem.getBindingContext().getPath();

  // Önce UI'dan kaldır (hızlı feedback)
  oItem.setVisible(false);

  // Sonra backend'e gönder
  this.getView().getModel().remove(sPath, {
    success: function() {
      MessageToast.show(this._getText("msg.delete.success"));   // navigasyonsuz anlık bilgi — Toast uygun
    }.bind(this),
    error: function(oError) {
      oItem.setVisible(true);  // Hata varsa geri göster
      this._handleODataError(oError);
    }.bind(this)
  });
},

// 4. Smooth Navigation — routing transition
// manifest.json → routing.config.transition: "slide"  (zaten var)

// 5. Success Animation — kaydettikten sonra kısa yeşil flash
onSaveSuccess: function() {
  // Header'a geçici success strip ekle
  var oStrip = new sap.m.MessageStrip({
    text: this._getText("msg.update.success"),
    type: "Success",
    showCloseButton: true,
    showIcon: true
  });
  this.byId("objectPage").getHeaderContent()[0].insertItem(oStrip, 0);

  // 3 saniye sonra otomatik kaldır
  setTimeout(function() {
    oStrip.destroy();
  }, 3000);
}
```

### 18.15 G. Theming & Visual Polish — SAP Horizon

> **Kural:** SAP Horizon (Morning/Evening) tema desteği = modern ve profesyonel görünüm. Asla hardcoded renk kullanma, her zaman CSS variable kullan.

```css
/* custom.css — SAP Theming Variables ile özelleştirme */
/* Bu değerler tema değiştiğinde otomatik uyum sağlar */

/* ✅ DOĞRU: Tema değişkenleri kullan */
.myApp .sapMListTblCell {
  border-bottom: 1px solid var(--sapList_BorderColor);
}

.myApp .highlightCard {
  background: var(--sapTile_Background);
  border: 1px solid var(--sapTile_BorderColor);
  border-radius: var(--sapElement_BorderCornerRadius);
  box-shadow: var(--sapContent_Shadow0);
  padding: 1rem;
}

.myApp .highlightCard:hover {
  box-shadow: var(--sapContent_Shadow1);
  transition: box-shadow 0.2s ease-in-out;
}

/* KPI Kartları — header'da kompakt görünüm */
.myApp .kpiCard {
  background: var(--sapTile_Background);
  border-radius: var(--sapElement_BorderCornerRadius);
  padding: 0.75rem 1rem;
  min-width: 8rem;
  border-left: 3px solid var(--sapBrandColor);
}

/* Status badge — inverted olmayan durumlarda custom */
.myApp .statusBadge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-size: var(--sapFontSmallSize);
}

/* ❌ YANLIŞ: Hardcoded renk kullanma */
/* .myBadge { background: #2196F3; color: white; }  → ASLA! */

/* Sık kullanılan SAP Theming variable'ları: */
/*
  --sapBrandColor              → Ana marka rengi (genelde mavi)
  --sapHighlightColor          → Vurgu rengi
  --sapPositiveColor           → Başarı (yeşil)
  --sapNegativeColor           → Hata (kırmızı)
  --sapCriticalColor           → Uyarı (turuncu)
  --sapInformativeColor        → Bilgi (mavi)
  --sapNeutralColor            → Nötr (gri)
  --sapBackgroundColor         → Sayfa arka planı
  --sapShellColor              → Shell arka planı
  --sapTile_Background         → Kart/tile arka planı
  --sapList_Background         → Liste arka planı
  --sapList_AlternatingBackground → Alternatif satır rengi
  --sapList_SelectionBackgroundColor → Seçili satır
  --sapContent_Shadow0..3      → Gölge seviyeleri
  --sapFontFamily              → Font family
  --sapFontSize                → Normal font boyutu
  --sapFontSmallSize           → Küçük font
  --sapFontLargeSize           → Büyük font
  --sapFontHeader1..6Size      → Başlık fontları
  --sapElement_BorderCornerRadius → Border radius
*/
```

**Horizon Tema Ayarı — Launchpad'de:**
```
FLP → Ayarlar → Görünüm:
  - "SAP Morning Horizon" → Açık tema (kurumsal, profesyonel)
  - "SAP Evening Horizon"  → Koyu tema (göz yorgunluğu azaltır)
  - "SAP Quartz Light/Dark" → Fiori 3.0 klasik

manifest.json'da tema bağımsız geliştirme yapıyorsan:
  → Asla hardcoded renk kullanma
  → var(--sapXxx) kullan
  → Tema değiştiğinde otomatik uyum sağlar
```

### 18.16 H. Tablo Tasarım Patternleri — İleri Seviye

> **İstisna notu:** Aşağıdaki `ColumnListItem`-tabanlı patternler **yalnız m.Table-istisna
> ekranlarda** geçerlidir (§18.11 istisnasıyla aynı kapsam). Liste/rapor ekranı = grid
> (§10.0/§16); `ColumnListItem` grid'de **YOKTUR** — grid eşdeğerleri farklı API kullanır.

```xml
<!-- Pattern 1: Grouped Header — Alt başlıklı tablo -->
<Table id="groupedTable" items="{
    path: '/MyEntitySet',
    sorter: { path: 'CompanyCode', group: true }
  }">
  <!-- GroupHeaderListItem otomatik render edilir -->
</Table>

<!-- Pattern 2: Inline Actions — Satır içi butonlar -->
<ColumnListItem>
  <cells>
    <!-- ... data cells ... -->
    <HBox justifyContent="End">
      <Button icon="sap-icon://edit" type="Ghost" press=".onEditRow"
              tooltip="{i18n>tooltipEdit}" class="sapUiTinyMarginEnd"/>
      <Button icon="sap-icon://copy" type="Ghost" press=".onCopyRow"
              tooltip="{i18n>tooltipCopy}"/>
    </HBox>
  </cells>
</ColumnListItem>

<!-- Pattern 3: Conditional Formatting — Koşullu biçimlendirme -->
<ObjectNumber number="{Amount}" unit="{CurrencyCode}"
              state="{= ${Amount} > 50000 ? 'Success' :
                         ${Amount} > 10000 ? 'Warning' : 'Error'}"
              emphasized="{= ${Amount} > 100000}"/>

<!-- Pattern 4: Multi-line Cell — Kompakt çok satırlı hücre -->
<VBox>
  <Text text="{Description}" wrapping="false" maxLines="1"/>
  <Label text="{= ${Category} + ' | ' + ${Subcategory}}"
         design="Light" wrapping="false"/>
</VBox>

<!-- Pattern 5: Selection + Bulk Actions -->
<Table mode="MultiSelect" selectionChange=".onSelectionChange">
  <headerToolbar>
    <OverflowToolbar>
      <Title text="{i18n>listTitle}" level="H3"/>
      <ToolbarSpacer/>
      <!-- Bulk action bar — seçim olduğunda görünür -->
      <Button text="{i18n>btnApproveSelected}" type="Accept"
              visible="{detailModel>/hasSelection}" press=".onBulkApprove"
              icon="sap-icon://accept"/>
      <Button text="{i18n>btnRejectSelected}" type="Reject"
              visible="{detailModel>/hasSelection}" press=".onBulkReject"
              icon="sap-icon://decline"/>
      <ToolbarSeparator visible="{detailModel>/hasSelection}"/>
      <Label text="{= ${detailModel>/selectionCount} + ' ' + ${i18n>selected}}"
             visible="{detailModel>/hasSelection}" design="Bold"/>
    </OverflowToolbar>
  </headerToolbar>
</Table>
```

```javascript
// Tablo seçim yönetimi
onSelectionChange: function(oEvent) {
  var oTable = oEvent.getSource();
  var iCount = oTable.getSelectedItems().length;
  var oModel = this.getView().getModel("detailModel");
  oModel.setProperty("/selectionCount", iCount);
  oModel.setProperty("/hasSelection", iCount > 0);
}
```

### 18.17 J. Accessibility & Keyboard Navigation

> **Kural:** Erişilebilirlik isteğe bağlı değil, zorunludur. Özellikle ARIA labeller ve keyboard shortcut'lar.

```xml
<!-- Her interaktif elemente anlamlı label/tooltip ekle -->
<Button icon="sap-icon://delete" press=".onDelete"
        ariaLabelledBy="deleteLabel"
        tooltip="{i18n>tooltipDelete}"/>
<InvisibleText id="deleteLabel" text="{i18n>ariaDeleteRecord}"/>

<!-- Form alanlarında label association -->
<Label text="{i18n>colCompany}" labelFor="inputCompany" required="true"/>
<Input id="inputCompany" value="{CompanyCode}"/>

<!-- Tablo boş durum — screen reader için -->
<IllustratedMessage illustrationType="sapIllus-EmptyList"
                    title="{i18n>noDataTitle}"
                    description="{i18n>noDataDesc}"
                    ariaLabelledBy="emptyTableLabel"/>
```

```javascript
// Keyboard navigation — Ctrl+S ile kaydet
onInit: function() {
  // Global keyboard shortcut
  $(document).on("keydown.myapp", function(e) {
    if (e.ctrlKey && e.key === "s") {
      e.preventDefault();
      this.onSave();
    }
    if (e.key === "Escape" && this._isEditMode()) {
      this.onCancel();
    }
  }.bind(this));
},

onExit: function() {
  // Cleanup
  $(document).off("keydown.myapp");
}
```

### 18.18 K. Tasarım Kalite Checklist — Her Geliştirmede Kontrol Et

```
╔══════════════════════════════════════════════════════════════════╗
║                    FIORI UI KALİTE CHECKLIST                   ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                 ║
║  LAYOUT & DENSITY                                               ║
║  □ Compact mode desktop'ta aktif mi?                            ║
║  □ §10.2: HBox/VBox kullanıyor mu? (SimpleForm/ResponsiveGridLayout YASAK) ║
║  □ Tablo sütunları sağ/sol hizalı (sayılar sağda) mı?          ║
║  □ Column importance ve demandPopin ayarlandı mı? (yalnız m.Table istisna) ║
║  □ Sticky column headers aktif mi?                              ║
║                                                                 ║
║  GÖRSEL KALİTE                                                  ║
║  □ Status alanları renk + ikon ile gösteriliyor mu?             ║
║  □ Row highlighting status'a göre aktif mi?                     ║
║  □ Object Page header'da KPI kartları var mı?                   ║
║  □ Breadcrumbs ve back navigation çalışıyor mu?                 ║
║  □ Avatar/ikon kullanımı başlıklarda var mı?                    ║
║  □ alternateRowColors tablo okunabilirliği artırıyor mu?        ║
║                                                                 ║
║  FEEDBACK & INTERACTION                                         ║
║  □ Her buton tıklamada busy feedback var mı?                    ║
║  □ §7.6: save/action sonrası MessageBox.success gösteriliyor mu? (MessageToast+navTo YASAK) ║
║  □ Boş tablo durumunda IllustratedMessage var mı?               ║
║  □ Validation hataları MessagePopover ile gösteriliyor mu?      ║
║  □ Unsaved changes uyarısı var mı? (navigation guard)           ║
║                                                                 ║
║  RESPONSIVE                                                     ║
║  □ L/M/S breakpoint'larda düzgün görünüyor mu?                  ║
║  □ Mobilde cozy, desktop'ta compact çalışıyor mu?               ║
║  □ Tablo sütunları dar ekranda pop-in oluyor mu? (yalnız m.Table istisna) ║
║                                                                 ║
║  THEMING                                                        ║
║  □ Hardcoded renk (hex/rgb) var mı? → OLMAMALI                 ║
║  □ var(--sapXxx) kullanılıyor mu? → OLMALI                     ║
║  □ Morning/Evening Horizon'da test edildi mi?                   ║
║                                                                 ║
║  ACCESSIBILITY                                                  ║
║  □ Tüm buton/ikon'larda tooltip var mı?                        ║
║  □ Form label-input association doğru mu?                       ║
║  □ InvisibleText ile ARIA label eklenmiş mi?                    ║
║  □ Keyboard navigation (Tab, Enter, Escape) çalışıyor mu?      ║
║                                                                 ║
║  DATA QUALITY                                                   ║
║  □ Tabloda max 6-8 görünür sütun var mı? (fazlası P13n'de)     ║
║  □ Teknik alanlar (GUID, internal code) gizlenmiş mi?           ║
║  □ Raw status kodları (A/B/X) yerine text gösteriliyor mu?      ║
║  □ Tüm label'lar i18n'den geliyor mu? (hardcoded yok)           ║
║                                                                 ║
║  CONSISTENCY                                                     ║
║  □ Aynı entity → her yerde aynı layout mu?                      ║
║  □ Aynı action → her yerde aynı pozisyonda mı?                  ║
║  □ Quick filter (segmented/tab) list sayfalarında var mı?       ║
║  □ Empty state'de CTA (Create) butonu var mı?                   ║
║                                                                 ║
╚══════════════════════════════════════════════════════════════════╝
```

### 18.19 L.1-L.7 — Mandatory UX Rules (Zorunlu UX Kuralları)

> **Kural:** Aşağıdaki kurallar her Fiori uygulamasında **istisnasız** uygulanmalıdır.

**L.1 Quick Filters — Liste Sayfalarında Hızlı Filtreleme:**
```xml
<!-- IconTabBar ile quick filter — status bazlı hızlı geçiş -->
<IconTabBar id="quickFilter" select=".onQuickFilterSelect"
            headerMode="Inline" stretchContentHeight="true"
            expandable="false">
  <items>
    <IconTabFilter text="{i18n>filterAll}" key="All"
                   count="{filterModel>/countAll}" showAll="true"/>
    <IconTabSeparator/>
    <IconTabFilter text="{i18n>filterActive}" key="A"
                   count="{filterModel>/countActive}"
                   iconColor="Positive" icon="sap-icon://sys-enter-2"/>
    <IconTabFilter text="{i18n>filterPending}" key="B"
                   count="{filterModel>/countPending}"
                   iconColor="Critical" icon="sap-icon://pending"/>
    <IconTabFilter text="{i18n>filterError}" key="E"
                   count="{filterModel>/countError}"
                   iconColor="Negative" icon="sap-icon://error"/>
  </items>
  <content>
    <!-- Tablo burada -->
  </content>
</IconTabBar>

<!-- Alternatif: SegmentedButton ile quick filter -->
<SegmentedButton id="segQuickFilter" select=".onQuickFilterSelect"
                 selectedKey="All">
  <items>
    <SegmentedButtonItem text="{i18n>filterAll}" key="All"/>
    <SegmentedButtonItem text="{i18n>filterActive}" key="A"/>
    <SegmentedButtonItem text="{i18n>filterPending}" key="B"/>
    <SegmentedButtonItem text="{i18n>filterError}" key="E"/>
  </items>
</SegmentedButton>
```

```javascript
// Quick filter controller logic
onQuickFilterSelect: function(oEvent) {
  var sKey = oEvent.getParameter("key") || oEvent.getParameter("item").getKey();
  var oTable = this.byId("mainTable");
  var oBinding = oTable.getBinding("rows") /* grid; m.Table-istisna ekranda "items" */;
  var aFilters = [];

  if (sKey !== "All") {
    aFilters.push(new Filter("Status", FilterOperator.EQ, sKey));
  }

  // Mevcut search filtrelerini koru
  var sSearchQuery = this.byId("filterSearch").getValue();
  if (sSearchQuery) {
    aFilters.push(new Filter("Description", FilterOperator.Contains, sSearchQuery));
  }

  oBinding.filter(aFilters.length > 0
    ? new Filter({ filters: aFilters, and: true })
    : []);
}
```

**L.2 Tablo Sütun Kuralı — Max 6-8 Görünür Sütun:**
```
┌──────────────────────────────────────────────────────────────┐
│ TABLO SÜTUN SIRASI KURALI                                    │
│                                                              │
│ 1. Identifier (ID / numara) → ilk sütun, HER ZAMAN görünür  │
│ 2. Primary info (açıklama, isim) → importance: High          │
│ 3. Status → importance: High, sağa veya ortaya hizalı       │
│ 4. Key metric (tutar, miktar) → importance: High, sağ hiza  │
│ 5. Secondary info (tarih, oluşturan) → importance: Medium    │
│ 6. Tertiary info (notlar, kategori) → importance: Low        │
│                                                              │
│ İLK AÇILIŞTA max 6-8 sütun göster.                           │
│ Kalan sütunlar P13n (Table Personalization) ile erişilebilir.│
│ Grid'de: TablePersonalizer kolon göster/gizle + varyant ile kontrol et (§16; SmartTable KULLANILMAZ — ADR 0008).           │
│ Manual Table: (m.Table-istisna ekranlarda) Column importance + minScreenWidth — grid'de karşılığı kolon göster/gizle (§16) kullan.     │
└──────────────────────────────────────────────────────────────┘
```

**L.3 Raw Kod Gösterme Yasağı — Her Zaman Okunabilir Metin:**
```javascript
// ❌ YANLIŞ: Raw kodu tabloda gösterme
// Status: "A"      → Kullanıcı A'nın ne olduğunu bilmez
// CompanyCode: "1000"  → Yanına text de göster

// ✅ DOĞRU: Formatter ile okunabilir metin
formatter: {
  formatStatusText: function(sStatus) {
    var oBundle = this.getView().getModel("i18n").getResourceBundle();
    var mTexts = {
      "A":  oBundle.getText("statusActive"),      // "Aktif"
      "B":  oBundle.getText("statusInProcess"),    // "İşlemde"
      "E":  oBundle.getText("statusError"),        // "Hatalı"
      "X":  oBundle.getText("statusDeleted")       // "Silinmiş"
    };
    return mTexts[sStatus] || sStatus;
  }
}
```

```xml
<!-- View'da: ObjectIdentifier ile hem kod hem text göster -->
<ObjectIdentifier title="{CompanyCode}" text="{CompanyCodeName}"/>

<!-- Veya sadece text, kodu tooltip'te göster -->
<Text text="{StatusText}" tooltip="{= 'Code: ' + ${Status}}"/>
```

**L.4 Empty State — CTA (Call-to-Action) ile Yönlendirici Boş Durum:**
```xml
<!-- ❌ YANLIŞ: Sadece "Veri yok" yazan boş tablo -->
<Table noDataText="No data"/>

<!-- ✅ DOĞRU: İllüstrasyon + açıklama + CTA butonu -->
<IllustratedMessage id="emptyState"
                    illustrationType="sapIllus-EmptyList"
                    title="{i18n>noDataTitle}"
                    description="{i18n>noDataDesc}"
                    visible="{= ${listModel>/totalCount} === 0}">
  <additionalContent>
    <Button text="{i18n>btnCreateFirst}" type="Emphasized"
            press=".onCreatePress" icon="sap-icon://add"/>
  </additionalContent>
</IllustratedMessage>

<!-- Filtered empty state — filtre sonucu boş -->
<IllustratedMessage id="emptyFilterState"
                    illustrationType="sapIllus-NoFilterResults"
                    title="{i18n>noFilterResultsTitle}"
                    description="{i18n>noFilterResultsDesc}"
                    visible="{= ${listModel>/isFiltered} && ${listModel>/totalCount} === 0}">
  <additionalContent>
    <Button text="{i18n>clearFilters}" press=".onClearFilters"
            icon="sap-icon://clear-filter"/>
  </additionalContent>
</IllustratedMessage>
```

**L.5 Inline Edit Pattern — Satır İçi Düzenleme:**

> [!WARNING]
> SAP backend **pessimistic locking (ENQUEUE_...)** kullandığı için, çoklu satırları `inline edit` moduna açmak, diğer kullanıcıların işlemlerini kilitleyebilir (lock error).
> **NE ZAMAN KULLANILMALI:** Sadece basit master-data tablolarında veya `BOPF Draft Framework` aktif ise. Diğer durumlarda klasik `Object Page -> Edit` navigasyonunu tercih et.

```xml
<!-- Tablo içinde editable/display mode toggle -->
<ColumnListItem>
  <cells>
    <ObjectIdentifier title="{EntityId}"/>
    <!-- Display mode: Text, Edit mode: Input -->
    <Input value="{Description}"
           editable="{detailModel>/editMode}"
           class="{= ${detailModel>/editMode} ? '' : 'sapUiSizeCompact'}"/>
    <!-- Display mode: ObjectStatus, Edit mode: Select -->
    <Select selectedKey="{Status}"
            enabled="{detailModel>/editMode}"
            forceSelection="false"
            visible="{detailModel>/editMode}">
      <items>
        <core:Item key="A" text="{i18n>statusActive}"/>
        <core:Item key="B" text="{i18n>statusInProcess}"/>
      </items>
    </Select>
    <ObjectStatus text="{StatusText}" state="{StatusState}"
                  visible="{= !${detailModel>/editMode}}"/>
    <!-- Editable amount field — düzenlenebilir sayısal input: type="Text"+onNumericLiveChange
         kullan, type="Number" YASAK (§17) -->
    <Input value="{Amount}" type="Text" textAlign="End"
           change=".onItemQtyChange" liveChange=".onNumericLiveChange"
           editable="{detailModel>/editMode}"/>
  </cells>
</ColumnListItem>
```

**L.6 Complex Forms — Wizard & Typeahead Kullanımı:**

> **Kural:** Uzun formlar kullanıcıyı bunaltır. Çok fazla alan varsa "Progressive Disclosure" (adım adım gösterme) için Wizard kullan. Eski F4 yardım menüleri yerine her zaman hızlı `Typeahead (Suggestion)` kullan.

```xml
<!-- ✅ DOĞRU: Karmaşık yaratma ekranları için Wizard -->
<Wizard id="createWizard" complete="wizardCompletedHandler">
  <WizardStep id="ProductInfoStep"
              title="{i18n>stepProductInfo}"
              validated="true">
    <MessageStrip text="{i18n>msgProductInfoDesc}" showIcon="true"/>
    <!-- Form alanları -->
  </WizardStep>

  <WizardStep id="PricingStep"
              title="{i18n>stepPricing}"
              validated="false">
    <!-- Adım 2 alanları -->
  </WizardStep>
</Wizard>

<!-- ✅ DOĞRU: Kullanıcı dostu Typeahead/Suggestion input -->
<Input id="inputCompany"
       placeholder="{i18n>placeholderCompany}"
       showSuggestion="true"
       suggestionItems="{/CompanyCodeSet}"
       suggestionItemSelected=".onCompanySelect">
  <suggestionItems>
    <core:ListItem key="{CompanyCode}"
                   text="{CompanyCode}"
                   additionalText="{CompanyCodeName}"/>
  </suggestionItems>
</Input>
```

**L.7 NEVER LIST — Anti-Pattern Kuralları:**
```
╔══════════════════════════════════════════════════════════════════╗
║                     ❌ ASLA YAPMA LİSTESİ                       ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                 ║
║  1. UI'ı bilgiyle BOĞMA                                         ║
║     → Max 6-8 sütun, geri kalanı P13n ile erişilebilir          ║
║     → Progressive disclosure: detay bilgiyi Object Page'e at    ║
║                                                                 ║
║  2. TEKNİK ALAN gösterme                                        ║
║     → GUID, MANDT, internal code, timestamp raw format          ║
║     → Kullanıcı görmemeli, sadece frontend model'de tutulmalı   ║
║                                                                 ║
║  3. i18n OLMADAN label kullanma                                  ║
║     → "Company Code" yerine {i18n>colCompany}                   ║
║     → Hardcoded text = çeviri yapılamaz, tutarsızlık oluşur     ║
║                                                                 ║
║  4. RAW STATUS KODU gösterme                                     ║
║     → "A" yerine "Aktif", "01" yerine "Onaylandı"              ║
║     → Formatter + i18n ile her zaman okunabilir metin           ║
║                                                                 ║
║  5. TÜM SAYFAYI busy yapma                                      ║
║     → Sadece etkilenen bileşeni busy yap (tablo, buton)         ║
║     → BusyDialog sadece kritik engelleme durumlarında           ║
║                                                                 ║
║  6. TUTARSIZ layout kullanma                                     ║
║     → Aynı entity = aynı sütun sırası, aynı renk kodlaması     ║
║     → Aynı aksiyon = aynı pozisyon (Create sağ üst, Delete sol)║
║     → Aynı status = aynı renk (yeşil=başarı her yerde)         ║
║                                                                 ║
║  7. CTA OLMADAN boş durum gösterme                               ║
║     → "Veri yok" tek başına yetmez                              ║
║     → "Oluştur" butonu veya filtre temizleme önerisi ekle       ║
║                                                                 ║
║  8. Filtre alanı OLMADAN liste sayfası yapma                     ║
║     → Quick filter (tab/segment) + arama her listede olmalı     ║
║     → Variant management power user'lar için aktif              ║
║                                                                 ║
║  9. DEFAULT browser/UI5 stillerini kullanma                      ║
║     → SAP Horizon temasını kullan                               ║
║     → Custom CSS → sadece var(--sapXxx) ile                     ║
║                                                                 ║
║ 10. Confirmation OLMADAN silme/iptal işlemi yapma                ║
║     → MessageBox.confirm ile onay al                            ║
║     → Geri alınamayacak işlemlerde: type="Warning"              ║
║                                                                 ║
╚══════════════════════════════════════════════════════════════════╝
```

---

*Son güncelleme: 2026-07-31 — §18 eklendi (02'den taşınan genel UI tasarım desenleri, D2 dedup) + §10.0/§14 iç-tekrar tekilleştirmesi*
