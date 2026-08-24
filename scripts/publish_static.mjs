import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const source = resolve(root, "gh-pages-dist");
const routes = ["allocation", "regime", "correlation", "markets", "etf-flows", "ai-chain", "calendar", "research", "workspace", "report"];

await rm(resolve(root, "assets"), { recursive: true, force: true });
await cp(resolve(source, "assets"), resolve(root, "assets"), { recursive: true });
const html = await readFile(resolve(source, "index.html"), "utf8");
await writeFile(resolve(root, "index.html"), html, "utf8");
for (const route of routes) {
  const target = resolve(root, route);
  await mkdir(target, { recursive: true });
  await writeFile(resolve(target, "index.html"), html, "utf8");
}
await rm(source, { recursive: true, force: true });
console.log(`Published ${routes.length + 1} static pages.`);

