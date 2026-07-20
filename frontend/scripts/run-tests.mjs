/*
 * Bundles every tests/*.test.mjs with esbuild (the source modules use
 * extensionless ESM imports that Node cannot resolve directly) and runs
 * the bundles through the built-in Node test runner.
 */

import { build } from "esbuild";
import { spawnSync } from "node:child_process";
import { mkdirSync, readdirSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = fileURLToPath(new URL("..", import.meta.url));
const testsDir = path.join(rootDir, "tests");
const outDir = path.join(rootDir, ".test-dist");

rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

const entryPoints = readdirSync(testsDir)
  .filter((name) => name.endsWith(".test.mjs"))
  .map((name) => path.join(testsDir, name));

if (entryPoints.length === 0) {
  console.error("No test files found in tests/");
  process.exit(1);
}

await build({
  entryPoints,
  outdir: outDir,
  bundle: true,
  platform: "node",
  format: "esm",
  outExtension: { ".js": ".mjs" },
  logLevel: "warning",
});

const bundledTests = readdirSync(outDir)
  .filter((name) => name.endsWith(".mjs"))
  .map((name) => path.join(outDir, name));

const result = spawnSync(process.execPath, ["--test", ...bundledTests], {
  stdio: "inherit",
});

process.exit(result.status ?? 1);
