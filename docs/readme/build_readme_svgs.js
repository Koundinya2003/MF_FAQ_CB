// Turns a one sheet HTML page into animated SVG panels for a GitHub README.
//
// GitHub strips CSS and scripts from READMEs, so every element in the page that
// carries data-panel="NN_name" is rendered with Playwright, frozen into XHTML
// (after the page's own script has run), given its fonts as subsetted data URIs,
// and wrapped in an SVG foreignObject. Motion must be CSS animations. Each panel
// is written twice: NN_name_light.svg and NN_name_dark.svg.
//
// Page conventions:
//   * One <style> block. Light tokens on `:root { ... }` (the first :root rule).
//   * Dark tokens in a `:root[data-theme="dark"] { ... }` block (a matching
//     @media (prefers-color-scheme: dark) block may sit just above it; it is dropped).
//   * A `body { ... }` rule (becomes the panel background and base font).
//   * Anything after the comment `/* ---------- responsive ---------- */` is dropped
//     (media queries do not behave inside an image), so put it last.
//   * Fonts from one Google Fonts <link rel="stylesheet" href="https://fonts.googleapis.com/css2?...">.
//   * Panels: top level blocks inside <main class="sheet"> with data-panel and data-alt.
//
// Usage: node build_readme_svgs.js <page.html> <outdir> [width=960]

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { chromium } = require("playwright");

const SRC = path.resolve(process.argv[2]);
const OUT = path.resolve(process.argv[3] || ".");
const WIDTH = +(process.argv[4] || 960);
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";

const BASE_CSS = `
.root { overflow: hidden; }
.sheet { padding-block: 12px; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; } }
`;

function blockAfter(css, start) {
  const i = css.indexOf(start);
  if (i < 0) return null;
  const open = css.indexOf("{", i);
  let depth = 0, j = open;
  for (; j < css.length; j++) {
    if (css[j] === "{") depth++;
    else if (css[j] === "}" && --depth === 0) break;
  }
  return { start: i, end: j + 1, inner: css.slice(open + 1, j) };
}

function panelCss(html, dark) {
  let css = html.match(/<style>([\s\S]*?)<\/style>/)[1];
  const media = blockAfter(css, "@media (prefers-color-scheme: dark)");
  if (media) css = css.slice(0, media.start) + css.slice(media.end);
  const darkBlock = blockAfter(css, ':root[data-theme="dark"]');
  let darkTokens = "";
  if (darkBlock) { darkTokens = darkBlock.inner; css = css.slice(0, darkBlock.start) + css.slice(darkBlock.end); }
  const cut = css.indexOf("/* ---------- responsive ---------- */");
  if (cut >= 0) css = css.slice(0, cut);
  css = css.replace(":root {", ".root {").replace(/(^|\n)\s*body\s*\{/, "$1.root {");
  if (dark) css += `\n.root { ${darkTokens} }\n`;
  return css + BASE_CSS;
}

function fontFaces(html, text) {
  const m = html.match(/href="(https:\/\/fonts\.googleapis\.com\/css2\?[^"]+)"/);
  if (!m) return "";
  const chars = Array.from(new Set(Array.from(text + "0123456789 .,:"))).join("");
  const url = m[1].replace(/&amp;/g, "&") + "&text=" + encodeURIComponent(chars);
  const css = execFileSync("curl", ["-sS", "-A", UA, url]).toString();
  // Google serves one variable file for several weights; embed each file once.
  const faces = new Map();
  for (const block of css.match(/@font-face \{[\s\S]*?\}/g) || []) {
    const fam = block.match(/font-family: '([^']+)'/)[1];
    const style = block.match(/font-style: (\w+)/)[1];
    const weight = +block.match(/font-weight: (\d+)/)[1];
    const u = block.match(/url\((https:[^)]+)\)/)[1];
    const key = fam + "|" + style + "|" + u;
    const f = faces.get(key) || { fam, style, u, lo: weight, hi: weight };
    f.lo = Math.min(f.lo, weight); f.hi = Math.max(f.hi, weight);
    faces.set(key, f);
  }
  let out = "";
  for (const f of faces.values()) {
    const buf = execFileSync("curl", ["-sS", "-A", UA, f.u]);
    out += `@font-face { font-family: '${f.fam}'; font-style: ${f.style}; font-weight: ${f.lo} ${f.hi}; src: url(data:font/woff2;base64,${buf.toString("base64")}) format('woff2'); }\n`;
  }
  return out;
}

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");

(async () => {
  const html = fs.readFileSync(SRC, "utf8");
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: WIDTH, height: 1200 } });
  await page.setContent("<!doctype html><html><head><meta charset=\"utf-8\"></head><body>" + html + "</body></html>", { waitUntil: "load" });
  await page.waitForTimeout(300);
  const panels = await page.evaluate(() => Array.from(document.querySelectorAll("[data-panel]")).map((el) => {
    const main = document.createElement("main");
    main.className = el.closest(".sheet") ? el.closest(".sheet").className : "sheet";
    const c = el.cloneNode(true);
    main.appendChild(c);
    main.querySelectorAll("[id]").forEach((e) => e.removeAttribute("id"));
    return { file: el.dataset.panel, alt: el.dataset.alt || el.dataset.panel, xml: new XMLSerializer().serializeToString(main), text: main.textContent };
  }));
  if (!panels.length) throw new Error("No [data-panel] elements found");

  const measure = await browser.newPage({ viewport: { width: WIDTH, height: 1200 } });
  const made = [];
  for (const p of panels) {
    const fonts = fontFaces(html, p.text);
    for (const dark of [false, true]) {
      const css = fonts + panelCss(html, dark);
      const wrap = `<div xmlns="http://www.w3.org/1999/xhtml" class="root" style="width:${WIDTH}px"><style>${esc(css)}</style>${p.xml}</div>`;
      await measure.setContent(`<!doctype html><html><body style="margin:0">${wrap}</body></html>`, { waitUntil: "load" });
      await measure.evaluate(() => document.fonts.ready);
      await measure.addStyleTag({ content: "*{animation:none!important}" });
      const h = Math.ceil(await measure.evaluate(() => document.querySelector(".root").getBoundingClientRect().height));
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${WIDTH}" height="${h}" viewBox="0 0 ${WIDTH} ${h}" role="img"><title>${esc(p.alt)}</title><foreignObject x="0" y="0" width="${WIDTH}" height="${h}">${wrap}</foreignObject></svg>\n`;
      const name = `${p.file}_${dark ? "dark" : "light"}.svg`;
      fs.writeFileSync(path.join(OUT, name), svg);
      made.push(name);
      console.log(name, h + "px", Math.round(svg.length / 1024) + " KB");
    }
  }
  await browser.close();
})();
