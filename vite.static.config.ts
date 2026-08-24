import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  root: "static-src",
  base: "/asset-allocation-dashboard/",
  plugins: [react()],
  resolve: { alias: { "next/link": resolve(__dirname, "static-src/StaticLink.tsx") } },
  build: { outDir: "../gh-pages-dist", emptyOutDir: true },
});

