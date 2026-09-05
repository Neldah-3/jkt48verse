# public/ — static assets

Aset statis yang disajikan Next.js langsung dari root (`/nama-file`).

## Icon set (favicon + PWA)

Semua PNG di-render dari sumber vektor di `app/icon.svg` (regular) dan
`app/icon-maskable.svg` (maskable, konten di safe-zone 80%). Nama memakai
prefiks `jv-` agar tidak bentrok dengan konvensi icon-route di `app/`.

| File | Ukuran | Dipakai oleh |
| --- | --- | --- |
| `favicon.ico` | 16/32/48 | fallback browser legacy |
| `jv-favicon-16.png` | 16×16 | `layout.tsx` icons, `manifest.ts` |
| `jv-favicon-32.png` | 32×32 | `layout.tsx` icons, `manifest.ts` |
| `jv-apple-icon-180.png` | 180×180 | `layout.tsx` apple-touch-icon, `manifest.ts` |
| `jv-icon-192.png` | 192×192 | `layout.tsx` icons, PWA `purpose: any` |
| `jv-icon-512.png` | 512×512 | `layout.tsx` icons, PWA `purpose: any` |
| `jv-icon-maskable-192.png` | 192×192 | PWA `purpose: maskable` |
| `jv-icon-maskable-512.png` | 512×512 | PWA `purpose: maskable` |
| `jkt48verse-icon.svg` | vector | `layout.tsx` icons (SVG favicon) |

## Regenerasi

Kalau `app/icon.svg` / `app/icon-maskable.svg` diubah, re-render PNG:

```sh
npx sharp-cli resize 512 512 in.svg out.png # atau pakai script sharp
```

Icon UI dalam komponen (menu, tombol, dsb.) TIDAK ada di sini — itu inline
SVG via komponen `Icon` di `components/ui.tsx`, jadi tidak menambah request.
