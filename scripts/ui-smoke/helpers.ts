/**
 * helpers.ts — ui-smoke yardımcıları (radar 2026-08-01 ADOPT-4; Workflow-pilot BLOCKER
 * bulgularıyla düzeltilmiş sürüm — bkz. selftest.spec.ts P/N kanıtları).
 *
 * 1) discoverRoutes(page, startUrl, maxPages): aynı-origin <a href> BFS keşfi + sayfa
 *    başına console-error toplama + dead-link dayanıklılığı.
 *    ⚠ file:// ÖZEL DURUMU (pilot-denetçi bulgusu-A): file:// URL'lerinde `origin`
 *    daima "null" string'idir → origin-kıyası SESSİZ NO-OP olur. Bu yüzden file://'da
 *    "aynı-origin" = "başlangıç dosyasının DİZİNİ altinda" kuralı uygulanır.
 * 2) grayscaleDiff64(page, pngA, pngB): sıfır-bağımlılık 64×64 grinton ortalama-mutlak
 *    fark (canvas, sayfa-içi) — layout-çökmesi yakalar, piksel gürültüsünü yok sayar.
 */
import type { Page } from '@playwright/test';

export interface VisitedPage {
  url: string;
  consoleErrors: string[];
}
export interface DeadLink {
  url: string;
  error: string;
}
export interface DiscoverResult {
  visited: VisitedPage[];
  deadLinks: DeadLink[];
}

/** favicon + file-not-found gürültüsü; DİKKAT (pilot ÖNERİ-bulgusu): tüm net::ERR_*
 *  yutulmaz — ERR_CONNECTION_REFUSED gibi gerçek backend sinyalleri consoleErrors'ta kalır. */
function isNoiseConsoleError(text: string): boolean {
  return /favicon/i.test(text) || text.includes('net::ERR_FILE_NOT_FOUND');
}

function sameScope(startUrl: string, candidate: URL): boolean {
  const start = new URL(startUrl);
  if (start.protocol === 'file:') {
    // file:// → origin "null"; kapsam = başlangıç dizini önek-kıyası (küçük-harf, / normalize)
    const dirOf = (p: string) => p.replace(/\\/g, '/').replace(/\/[^/]*$/, '/').toLowerCase();
    return candidate.protocol === 'file:' &&
           dirOf(candidate.pathname).startsWith(dirOf(start.pathname));
  }
  return candidate.origin === start.origin;
}

export async function discoverRoutes(
  page: Page, startUrl: string, maxPages = 10,
): Promise<DiscoverResult> {
  const visited: VisitedPage[] = [];
  const deadLinks: DeadLink[] = [];
  const seen = new Set<string>([startUrl]);
  const queue: string[] = [startUrl];
  let attempts = 0;
  const maxAttempts = maxPages * 3; // dead-link'ler bütçeyi sınırsız tüketemesin (pilot ÖNERİ)

  const errors: string[] = [];
  const onConsole = (msg: { type(): string; text(): string }) => {
    if (msg.type() === 'error' && !isNoiseConsoleError(msg.text())) errors.push(msg.text());
  };
  page.on('console', onConsole); // goto'dan ÖNCE — erken error kaçmaz

  try {
    while (queue.length && visited.length < maxPages && attempts < maxAttempts) {
      const url = queue.shift() as string;
      attempts += 1;
      errors.length = 0;
      let resStatus: number | null = null;
      try {
        const res = await page.goto(url, { waitUntil: 'load', timeout: 10_000 });
        resStatus = res ? res.status() : null;
      } catch (e) {
        deadLinks.push({ url, error: String((e as Error).message).slice(0, 160) });
        continue;
      }
      // HTTP dead-link (pilot EKSİK-bulgusu): goto 404/500'de reject ETMEZ — status'a bak.
      if (resStatus !== null && resStatus >= 400) {
        deadLinks.push({ url, error: `HTTP ${resStatus}` });
        continue;
      }
      visited.push({ url, consoleErrors: [...errors] });

      const hrefs: string[] = await page.$$eval('a[href]',
        (as) => as.map((a) => (a as HTMLAnchorElement).getAttribute('href') || ''));
      for (const h of hrefs) {
        if (!h || h.startsWith('#') || h.startsWith('mailto:') || h.startsWith('javascript:')) continue;
        let abs: URL;
        try { abs = new URL(h, url); } catch { continue; }
        abs.hash = '';
        if (!sameScope(startUrl, abs)) continue;
        const key = abs.toString();
        if (!seen.has(key)) { seen.add(key); queue.push(key); }
      }
    }
  } finally {
    page.off('console', onConsole);
  }
  return { visited, deadLinks };
}

export interface GrayDiff {
  meanDiff: number; // 0..255
  pct: number;      // meanDiff/255
}

export async function grayscaleDiff64(
  page: Page, pngA: Buffer, pngB: Buffer,
): Promise<GrayDiff> {
  const a = 'data:image/png;base64,' + pngA.toString('base64');
  const b = 'data:image/png;base64,' + pngB.toString('base64');
  const meanDiff: number = await page.evaluate(async ([ua, ub]) => {
    const load = (src: string) => new Promise<HTMLImageElement>((ok, err) => {
      const im = new Image();
      im.onload = () => ok(im);
      im.onerror = () => err(new Error('img load fail'));
      im.src = src;
    });
    const [ia, ib] = await Promise.all([load(ua), load(ub)]);
    const gray = (im: HTMLImageElement) => {
      const c = document.createElement('canvas');
      c.width = 64; c.height = 64;
      const ctx = c.getContext('2d') as CanvasRenderingContext2D;
      ctx.drawImage(im, 0, 0, 64, 64);
      const d = ctx.getImageData(0, 0, 64, 64).data;
      const g = new Float64Array(64 * 64);
      for (let i = 0; i < 64 * 64; i++) {
        g[i] = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2];
      }
      return g;
    };
    const ga = gray(ia), gb = gray(ib);
    let s = 0;
    for (let i = 0; i < ga.length; i++) s += Math.abs(ga[i] - gb[i]);
    return s / ga.length;
  }, [a, b]);
  return { meanDiff, pct: meanDiff / 255 };
}
