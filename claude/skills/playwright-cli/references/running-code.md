# Running Custom Playwright Code

Use `run-code` to execute arbitrary Playwright code for advanced scenarios not covered by CLI commands.

## Syntax

```bash
playwright-cli run-code "async page => {
  // Your Playwright code here
  // Access page.context() for browser context operations
}"
```

You can also load the function from a file:

```bash
playwright-cli run-code --filename=./my-script.js
```


The code must be a single function expression, it is wrapped in `(...)` and evaluated.
import/export/require syntax is not supported.

## Geolocation

```bash
# Grant geolocation permission and set location
playwright-cli run-code "async page => {
  await page.context().grantPermissions(['geolocation']);
  await page.context().setGeolocation({ latitude: 37.7749, longitude: -122.4194 });
}"

# Set location to London
playwright-cli run-code "async page => {
  await page.context().grantPermissions(['geolocation']);
  await page.context().setGeolocation({ latitude: 51.5074, longitude: -0.1278 });
}"

# Clear geolocation override
playwright-cli run-code "async page => {
  await page.context().clearPermissions();
}"
```

## Permissions

```bash
# Grant multiple permissions
playwright-cli run-code "async page => {
  await page.context().grantPermissions([
    'geolocation',
    'notifications',
    'camera',
    'microphone'
  ]);
}"

# Grant permissions for specific origin
playwright-cli run-code "async page => {
  await page.context().grantPermissions(['clipboard-read'], {
    origin: 'https://example.com'
  });
}"
```

## Media Emulation

```bash
# Emulate dark color scheme
playwright-cli run-code "async page => {
  await page.emulateMedia({ colorScheme: 'dark' });
}"

# Emulate light color scheme
playwright-cli run-code "async page => {
  await page.emulateMedia({ colorScheme: 'light' });
}"

# Emulate reduced motion
playwright-cli run-code "async page => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
}"

# Emulate print media
playwright-cli run-code "async page => {
  await page.emulateMedia({ media: 'print' });
}"
```

## Wait Strategies

```bash
# Wait for network idle
playwright-cli run-code "async page => {
  await page.waitForLoadState('networkidle');
}"

# Wait for specific element
playwright-cli run-code "async page => {
  await page.locator('.loading').waitFor({ state: 'hidden' });
}"

# Wait for function to return true
playwright-cli run-code "async page => {
  await page.waitForFunction(() => window.appReady === true);
}"

# Wait with timeout
playwright-cli run-code "async page => {
  await page.locator('.result').waitFor({ timeout: 10000 });
}"
```

## Frames and Iframes

```bash
# Work with iframe
playwright-cli run-code "async page => {
  const frame = page.locator('iframe#my-iframe').contentFrame();
  await frame.locator('button').click();
}"

# Get all frames
playwright-cli run-code "async page => {
  const frames = page.frames();
  return frames.map(f => f.url());
}"
```

## File Downloads

```bash
# Handle file download
playwright-cli run-code "async page => {
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download' }).click();
  const download = await downloadPromise;
  await download.saveAs('./downloaded-file.pdf');
  return download.suggestedFilename();
}"
```

## Clipboard

```bash
# Read clipboard (requires permission)
playwright-cli run-code "async page => {
  await page.context().grantPermissions(['clipboard-read']);
  return await page.evaluate(() => navigator.clipboard.readText());
}"

# Write to clipboard
playwright-cli run-code "async page => {
  await page.evaluate(text => navigator.clipboard.writeText(text), 'Hello clipboard!');
}"
```

## Page Information

```bash
# Get page title
playwright-cli run-code "async page => {
  return await page.title();
}"

# Get current URL
playwright-cli run-code "async page => {
  return page.url();
}"

# Get page content
playwright-cli run-code "async page => {
  return await page.content();
}"

# Get viewport size
playwright-cli run-code "async page => {
  return page.viewportSize();
}"
```

## JavaScript Execution

```bash
# Execute JavaScript and return result
playwright-cli run-code "async page => {
  return await page.evaluate(() => {
    return {
      userAgent: navigator.userAgent,
      language: navigator.language,
      cookiesEnabled: navigator.cookieEnabled
    };
  });
}"

# Pass arguments to evaluate
playwright-cli run-code "async page => {
  const multiplier = 5;
  return await page.evaluate(m => document.querySelectorAll('li').length * m, multiplier);
}"
```

## Error Handling

```bash
# Try-catch in run-code
playwright-cli run-code "async page => {
  try {
    await page.getByRole('button', { name: 'Submit' }).click({ timeout: 1000 });
    return 'clicked';
  } catch (e) {
    return 'element not found';
  }
}"
```

## Complex Workflows

```bash
# Login and save state
# ⛔ 'secret' here is a placeholder — a real password written like this is echoed into the
#    transcript. Use the "Sırlar" section below instead.
playwright-cli run-code "async page => {
  await page.goto('https://example.com/login');
  await page.getByRole('textbox', { name: 'Email' }).fill('user@example.com');
  await page.getByRole('textbox', { name: 'Password' }).fill('secret');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('**/dashboard');
  await page.context().storageState({ path: 'auth.json' });
  return 'Login successful';
}"

# Scrape data from multiple pages
playwright-cli run-code "async page => {
  const results = [];
  for (let i = 1; i <= 3; i++) {
    await page.goto(\`https://example.com/page/\${i}\`);
    const items = await page.locator('.item').allTextContents();
    results.push(...items);
  }
  return results;
}"
```

## Sırlar (auth header / parola / token) — IX eki

> `install --skills` bu bölümü ezer; skill güncellenince yeniden ekle.

**Ölçüldü (playwright-cli 0.1.17, 2026-10-03, yalnız sahte değerlerle):**

| Durum | Sonuç |
|---|---|
| `run-code "<kod>"` | Kod `### Ran Playwright code` bloğunda **aynen** basılır — literal sır transkripte düşer |
| `run-code --filename=<dosya>` | Dosyanın içeriği de **aynen** basılır (2026-08-06 vakası: Basic-auth başlığı böyle sızdı) |
| `run-code` içinde `process.env` | **Yok** — `typeof process` = `undefined` (Node tarafında da, sayfada da) |
| `--raw run-code` | Kod basılmaz (başarı ve hata dalı) — ama sır yine komut metninde/dosyada durur, **çözüm değil** |
| `PLAYWRIGHT_MCP_SECRETS_FILE` ile açılmış oturum | Çıktıdaki sır değerleri `<secret>AD</secret>` olarak maskelenir; `fill <ref> AD` değeri yerine koyar |

**Kural:** sır DEĞERİ hiçbir komut metnine, `run-code` koduna ya da `--filename` dosyasına
yazılmaz. Sır ortam değişkeninden gelir ve oturuma `open` anında verilir:

```bash
# 1) Sır env'de (ör. PW_AUTH_USER / PW_AUTH_PASS) — komut metnine DEĞER yazılmaz.
#    Yardımcı config + secrets dosyasını REPO DIŞINDA yazar ve değeri BASMAZ.
D="$(mktemp -d)"
python - "$D" <<'EOF'
import base64, json, os, sys
d = sys.argv[1]
u, p = os.environ["PW_AUTH_USER"], os.environ["PW_AUTH_PASS"]
json.dump({"browser": {"contextOptions": {"httpCredentials": {"username": u, "password": p}}}},
          open(os.path.join(d, "cli.config.json"), "w", encoding="utf-8"))
b64 = base64.b64encode(f"{u}:{p}".encode()).decode()
open(os.path.join(d, "secrets.env"), "w", encoding="utf-8").write(
    f"PW_AUTH_PASS={p}\nPW_AUTH_B64={b64}\n")
EOF
# 2) Oturumu bu config + secrets ile aç (ikisi de `open` anında okunur; sonradan verilen env etkisizdir)
PLAYWRIGHT_MCP_SECRETS_FILE="$D/secrets.env" playwright-cli -s=auth open --config="$D/cli.config.json" https://app.example.com/
# 3) Form alanına sırrın ADINI ver — CLI değeri koyar; çıktıda `fill(process.env['PW_AUTH_PASS'])` görünür
playwright-cli -s=auth fill e5 PW_AUTH_PASS
# 4) Bitince kapat + dosyaları sil
playwright-cli -s=auth close
rm -rf "$D"
```

Bu blok sahte bir Basic-auth sunucusuna karşı yazıldığı gibi koşuldu: config'siz oturum
`ERR_INVALID_AUTH_CREDENTIALS`, bu oturum 200 (sayfa başlığı beklenen) · alan uzunluğu sahte
parolanınkine eşit · çıktıda sır değeri **0** kez.
Basic-auth için `httpCredentials` yeterli çıktı (tarayıcı 401 sorgusuna cevap verir).
`contextOptions.extraHTTPHeaders` ile elle başlık kurma yolu **ölçülmedi** — gerekirse değer yine
aynı yardımcıdan config'e yazılır, `run-code`'a değil; önce sahte değerle ölç. Sızma şüphesinde: çıktıyı redakte et, geçici
dosyaları sil, kimlik bilgisini değiştirmeyi kullanıcıya öner.
