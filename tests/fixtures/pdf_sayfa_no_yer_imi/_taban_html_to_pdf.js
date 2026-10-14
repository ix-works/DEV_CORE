/** HTML → PDF (Edge, page.pdf). Kullanım: node scripts/html_to_pdf.js <input.html> <output.pdf>
 * KD/FS/TS markdown→HTML (build_kd_pdf.py) çıktısını şık A4 PDF'e çevirir. */
const path = require("path");
const fs = require("fs");
const os = require("os");
// playwright-core yolunu DİNAMİK çöz (hardcode/username-placeholder YOK).
// Global npm kurulumundaki @playwright/cli altındaki playwright-core'u ara; bulunamazsa
// normal modül çözümüne düş (yerel node_modules / NODE_PATH).
function resolvePlaywrightCore() {
  const suffix = "npm/node_modules/@playwright/cli/node_modules/playwright-core";
  const cands = [
    process.env.APPDATA && path.join(process.env.APPDATA, suffix),           // Windows: C:\Users\<user>\AppData\Roaming
    path.join(os.homedir(), "AppData/Roaming", suffix),                       // Windows fallback
    process.env.npm_config_prefix && path.join(process.env.npm_config_prefix, "node_modules/@playwright/cli/node_modules/playwright-core"),
  ].filter(Boolean);
  for (const c of cands) { if (fs.existsSync(c)) return c; }
  return "playwright-core";                                                   // son çare: normal require çözümü
}
const { chromium } = require(resolvePlaywrightCore());
const IN = path.resolve(process.argv[2]);
const OUT = path.resolve(process.argv[3]);
(async () => {
  const fileUrl = "file:///" + IN.split(path.sep).join("/");
  const b = await chromium.launch({ channel: "msedge", headless: true, args: ["--no-sandbox"] });
  const p = await (await b.newContext()).newPage();
  await p.goto(fileUrl, { waitUntil: "networkidle", timeout: 60000 });
  await p.emulateMedia({ media: "screen" });
  await p.pdf({ path: OUT, format: "A4", printBackground: true, margin: { top: "14mm", bottom: "16mm", left: "12mm", right: "12mm" } });
  await b.close();
  console.log("PDF OK:", OUT);
})().catch(e => { console.error("ERR", e); process.exit(1); });
