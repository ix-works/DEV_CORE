/** HTML → PDF (Edge, page.pdf). Kullanım: node scripts/html_to_pdf.js <input.html> <output.pdf>
 * KD/FS/TS markdown→HTML (build_kd_pdf.py) çıktısını şık A4 PDF'e çevirir. */
const path = require("path");
const PW = "C:/Users/<USER>/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core";
const { chromium } = require(PW);
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
