---
layer: L2
scope: project-wide
applies-to: ui
version: 1.0
last-updated: 2026-05-14
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

ALV-tarzı liste/rapor ekranları **`sap.ui.table.Table` (grid)** ile yapılır (masaüstü, çok-kolon):
**yatay scroll** + **sanal scroll** (binlerce satır) + kolon **resize/sürükle-sırala/dondur** +
**native** kolon-başlığı sort/filter (`sortProperty`/`filterProperty`). `sap.m.Table` (responsive)
yalnızca **mobil-öncelikli** veya **hücre-zengin** (wrap/değişken yükseklik) ekranlar için istisna.

- **Reusable util:** `TablePersonalizer.js` (grid sürümü) — kolon göster/gizle (geniş Dialog) +
  **DB-backed varyant/default** (OData `ZSD000_UI_VARIANT_O2`, layout = visible+width+index) + Excel.
  Kanonik kopya: `ERP/SD/ZSD001_CLC/ui/delivery_report/webapp/util/TablePersonalizer.js`. **Kopyala, sıfırdan yazma.**
- **Kanonik şablon app:** `ERP/SD/ZSD001_CLC/ui/sales_order_report/` (veya `delivery_report`) — yeni rapor bunu kopyalar.
- **Backend (salt-okunur rapor RAP'i):** wrapper view entity (`select from <klasik DDL>`, key + `@AccessControl #CHECK`)
  + DCL (`V_VBAK_VKO`/VKORG/ACTVT='03') + SRVD (expose + ortak `ZSD000_I_*VH`) + SRVB (OData V2) publish.
  **Kur/EXCRT conversion-exit alanları → `cast(.. as abap.dec)`** (yoksa publish ERROR).
- Tam reçete + kurulum + tuzaklar: [`playbook/ui-freestyle-odata-v2.md` §E](../playbook/ui-freestyle-odata-v2.md) + [`playbook/ui-backend-rap.md`](../playbook/ui-backend-rap.md).

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
- [ ] `i18n/i18n.properties` → İngilizce default
- [ ] `i18n/i18n_tr.properties` → Türkçe
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

*Son güncelleme: 12.06.2026 — §17 düzenlenebilir sayısal input type=Number yasağı*
