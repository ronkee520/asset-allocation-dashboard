import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const source = resolve(root, "gh-pages-dist");
const routes = ["allocation", "regime", "correlation", "markets", "etf-flows", "ai-chain", "calendar", "research"];
const allocationDetails = ["equity", "bonds", "commodities", "gold", "usd", "ai", "hk", "china-a"];
const retiredRoutes = ["workspace", "report"];

await rm(resolve(root, "assets"), { recursive: true, force: true });
await cp(resolve(source, "assets"), resolve(root, "assets"), { recursive: true });
const html = `${(await readFile(resolve(source, "index.html"), "utf8")).trimEnd()}\n`;
await writeFile(resolve(root, "index.html"), html, "utf8");
for (const route of routes) {
  const target = resolve(root, route);
  await mkdir(target, { recursive: true });
  await writeFile(resolve(target, "index.html"), html, "utf8");
}
for (const detail of allocationDetails) {
  const target = resolve(root, "allocation", detail);
  await mkdir(target, { recursive: true });
  await writeFile(resolve(target, "index.html"), html, "utf8");
}
for (const route of retiredRoutes) {
  await rm(resolve(root, route), { recursive: true, force: true });
}
await rm(source, { recursive: true, force: true });
console.log(`Published ${routes.length + allocationDetails.length + 1} static pages.`);

