// Generator icon JKT48Verse — sumber tunggal untuk favicon, apple-touch-icon, dan icon PWA.
//
// Pakai:  npx -y -p sharp@0.33 node scripts/gen-icons.mjs      (dari folder frontend/)
// Butuh:  ImageMagick `convert` di PATH untuk favicon.ico multi-size (opsional; dilewati jika tidak ada).
//
// Output:
//   app/icon.svg                      favicon modern (SVG, scalable)
//   app/favicon.ico                   16/32/48 px untuk browser lama
//   app/apple-icon.png                180x180 full-bleed (iOS memotong sudutnya sendiri)
//   public/icons/icon-{192,512}.png   PWA manifest (purpose: any)
//   public/icons/icon-maskable-*.png  PWA manifest (purpose: maskable, safe zone 80%)
//
// Komponen <Logo /> di components/ui.tsx memakai path & gradient yang sama — jaga agar tetap sinkron.

import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const sharp = require("sharp");

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const APP = path.join(ROOT, "app");
const PUB = path.join(ROOT, "public", "icons");
fs.mkdirSync(PUB, { recursive: true });

// Monogram "JV" (JKT48Verse) di kanvas 512x512, stroke 60 dengan ujung bulat, terpusat optis.
const LETTERS = "M190 151v168a42 42 0 0 1-84 0M273 151l66 210 66-210";
const RED_LIGHT = "#ff4d6d"; // sama dengan --primary-2 (dark) & gradient .brand
const RED_DARK = "#b60f2c";  // sama dengan --primary-2 (light)

function tile({ rx = 118, letterScale = 1, border = true } = {}) {
  const s = letterScale;
  const t = 256 - 256 * s; // skala huruf di sekitar titik tengah
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="${RED_LIGHT}"/>
      <stop offset="1" stop-color="${RED_DARK}"/>
    </linearGradient>
    <radialGradient id="hl" cx="0.2" cy="0.08" r="0.95">
      <stop offset="0" stop-color="#fff" stop-opacity="0.18"/>
      <stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="512" height="512" rx="${rx}" fill="url(#bg)"/>
  <rect width="512" height="512" rx="${rx}" fill="url(#hl)"/>${border ? `
  <rect x="1.5" y="1.5" width="509" height="509" rx="${Math.max(rx - 1.5, 0)}" fill="none" stroke="#fff" stroke-opacity="0.12" stroke-width="3"/>` : ""}
  <path d="${LETTERS}" fill="none" stroke="#fff" stroke-width="60" stroke-linecap="round" stroke-linejoin="round"${s !== 1 ? ` transform="translate(${t} ${t}) scale(${s})"` : ""}/>
</svg>
`;
}

const rounded = tile();                                             // favicon & manifest "any"
const square = tile({ rx: 0, border: false });                      // apple-touch-icon
const maskable = tile({ rx: 0, border: false, letterScale: 0.8 });  // Android adaptive icon

const png = (svg, size) => sharp(Buffer.from(svg)).resize(size, size).png({ compressionLevel: 9 }).toBuffer();
const write = (p, data) => { fs.writeFileSync(p, data); console.log(path.relative(ROOT, p).padEnd(36), String(fs.statSync(p).size).padStart(6), "bytes"); };

write(path.join(APP, "icon.svg"), rounded);
write(path.join(APP, "apple-icon.png"), await png(square, 180));
write(path.join(PUB, "icon-192.png"), await png(rounded, 192));
write(path.join(PUB, "icon-512.png"), await png(rounded, 512));
write(path.join(PUB, "icon-maskable-192.png"), await png(maskable, 192));
write(path.join(PUB, "icon-maskable-512.png"), await png(maskable, 512));

try {
  const tmp = fs.mkdtempSync(path.join(process.env.TMPDIR || "/tmp", "jv-ico-"));
  const parts = [];
  for (const s of [16, 32, 48]) { const p = path.join(tmp, `${s}.png`); fs.writeFileSync(p, await png(rounded, s)); parts.push(p); }
  execFileSync("convert", [...parts, path.join(APP, "favicon.ico")], { stdio: "ignore" });
  console.log("app/favicon.ico".padEnd(36), String(fs.statSync(path.join(APP, "favicon.ico")).size).padStart(6), "bytes");
  fs.rmSync(tmp, { recursive: true, force: true });
} catch {
  console.warn("! ImageMagick `convert` tidak ditemukan — app/favicon.ico dilewati (icon.svg tetap dipakai browser modern).");
}
