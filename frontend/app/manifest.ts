import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "JKT48Verse — Fan-made Platform",
    short_name: "JKT48Verse",
    description: "Platform komunitas penggemar JKT48: live member, jadwal, news, birthday, games, chat, dan AI search.",
    lang: "id",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#e01b3c",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-maskable-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
    ],
  };
}
