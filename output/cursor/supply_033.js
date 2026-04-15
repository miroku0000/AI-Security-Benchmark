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