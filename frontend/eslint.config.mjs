import { FlatCompat } from "@eslint/eslintrc";
import { fileURLToPath } from "node:url";
import path from "node:path";

const compat = new FlatCompat({ baseDirectory: path.dirname(fileURLToPath(import.meta.url)) });

const config = [
  { ignores: [".next/**", "out/**", "next-env.d.ts"] },
  ...compat.extends("next/core-web-vitals"),
  {
    rules: {
      // Live thumbnails originate from third-party CDNs; keep native <img>.
      "@next/next/no-img-element": "off",
    },
  },
];

export default config;
