import type { MetadataRoute } from "next";

// PWA web manifest — Next.js serves this at /manifest.webmanifest and links it
// automatically. Icons live in /public (prefixed jv- to avoid clashing with
// the app/ icon-route conventions); maskable variants keep the mark inside
// Android's adaptive-icon safe zone.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "JKT48Verse — Fan-made Platform",
    short_name: "JKT48Verse",
    description:
      "Platform komunitas penggemar JKT48: live member, jadwal, news, birthday, games, chat, dan AI search. Proyek non-komersial.",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#e01b3c",
    lang: "id",
    categories: ["entertainment", "social"],
    icons: [
      { src: "/jv-favicon-16.png", sizes: "16x16", type: "image/png" },
      { src: "/jv-favicon-32.png", sizes: "32x32", type: "image/png" },
      { src: "/jv-apple-icon-180.png", sizes: "180x180", type: "image/png" },
      { src: "/jv-icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/jv-icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/jv-icon-maskable-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/jv-icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
