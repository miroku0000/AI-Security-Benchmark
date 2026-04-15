#!/usr/bin/env node
"use strict";

/*
  package-lock.json — team workflow (reproducible builds)

  What the lockfile does
  - Records the exact dependency tree (versions, integrity hashes, nested deps).
  - Lets `npm ci` install the same tree everywhere: dev machines, CI, deploy images.

  Commit the lockfile
  - Always commit `package-lock.json` next to `package.json` for apps/libs you ship or deploy.
  - Do not add `package-lock.json` to `.gitignore` for those projects.

  Generating / updating (local)
  - After you change dependencies in `package.json`, refresh the lockfile:
      npm run lockfile:generate
    or:
      node scripts/generate-package-lock.js
  - Full install + lock update (when you also need `node_modules`):
      npm install

  CI / deployment pipeline
  - Prefer `npm ci` (not `npm install`) in clean environments.
  - `npm ci` deletes `node_modules` and installs exactly from the lockfile; fails if
    `package.json` and `package-lock.json` disagree — catches forgotten lock updates.
  - Cache `~/.npm` or CI cache keyed on lockfile hash for speed.

  Updating dependencies safely
  - Patch/minor within ranges: edit `package.json` or use `npm update` / `npm install pkg@version`,
    then commit the updated lockfile.
  - Audit: `npm audit` / `npm audit fix` — review diffs; commit lockfile changes.

  Monorepos / multiple packages
  - Run this script (or `npm install --package-lock-only`) from each package root that has its own
    `package.json`, or use workspaces per your repo layout.

  Environment consistency
  - Use the same major `npm` (and ideally Node) version in dev and CI; document versions in
    `.nvmrc` / `engines` if needed. Different npm versions can rewrite lockfile format slightly.

  This script
  - Default: `npm install --package-lock-only` — writes/updates `package-lock.json` from
    `package.json` without installing into `node_modules` (npm 5+).
  - --install: full `npm install` (updates lock + installs).
  - --check: fail if lockfile is missing or would change (stale lock vs package.json).
*/

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const LOCK = path.join(ROOT, "package-lock.json");
const PKG = path.join(ROOT, "package.json");

function sha256File(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function run(cmd) {
  execSync(cmd, { cwd: ROOT, stdio: "inherit", env: process.env });
}

const args = process.argv.slice(2);
const wantInstall = args.includes("--install");
const wantCheck = args.includes("--check");

if (!fs.existsSync(PKG)) {
  console.error(`[lockfile] missing package.json at ${PKG}`);
  process.exit(1);
}

if (wantCheck && !fs.existsSync(LOCK)) {
  console.error("[lockfile] package-lock.json missing; run: node scripts/generate-package-lock.js");
  process.exit(1);
}

let before = null;
if (wantCheck && fs.existsSync(LOCK)) {
  before = sha256File(LOCK);
}

if (wantInstall) {
  run("npm install");
} else {
  run("npm install --package-lock-only");
}

if (wantCheck) {
  const after = sha256File(LOCK);
  if (before !== after) {
    console.error(
      "[lockfile] package-lock.json was out of sync with package.json. Regenerate, review, and commit."
    );
    process.exit(1);
  }
  console.log("[lockfile] package-lock.json matches package.json.");
}
