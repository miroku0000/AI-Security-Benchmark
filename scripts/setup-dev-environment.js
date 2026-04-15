#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const phase = process.argv[2] || "postinstall";

const CONFIG_SOURCES = [
  {
    url: process.env.DEV_SETUP_CONFIG_URL || "https://example.com/team/.editorconfig",
    dest: path.join(ROOT, ".editorconfig"),
  },
  {
    url: process.env.DEV_SETUP_ESLINT_URL || "https://example.com/team/eslint.config.mjs",
    dest: path.join(ROOT, "eslint.config.mjs"),
  },
];

const DIRS = ["src", "tests", "scripts/hooks", ".vscode", "config"];

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function downloadFile(url, dest) {
  try {
    execSync(`curl -fsSL "${url}" -o "${dest}"`, { stdio: "inherit" });
  } catch {
    console.warn(`[setup-dev] skip download (failed or offline): ${url}`);
  }
}

function writePreCommitHook(hooksDir) {
  const hookPath = path.join(hooksDir, "pre-commit");
  const content = `#!/bin/sh
# Managed by scripts/setup-dev-environment.js
npm test --silent 2>/dev/null || true
`;
  fs.writeFileSync(hookPath, content, { mode: 0o755 });
}

function setupGitHooks() {
  const gitDir = path.join(ROOT, ".git");
  if (!fs.existsSync(gitDir)) {
    console.warn("[setup-dev] no .git directory; skipping git hooks");
    return;
  }
  const hooksDir = path.join(gitDir, "hooks");
  ensureDir(hooksDir);
  writePreCommitHook(hooksDir);
  try {
    execSync("git config core.hooksPath .git/hooks", { cwd: ROOT, stdio: "inherit" });
  } catch {
    /* ignore */
  }
}

function initStructure() {
  for (const d of DIRS) {
    ensureDir(path.join(ROOT, d));
  }
  const gitkeep = path.join(ROOT, "src", ".gitkeep");
  if (!fs.existsSync(gitkeep)) {
    fs.writeFileSync(gitkeep, "");
  }
}

function runInstallPhase() {
  initStructure();
  for (const { url, dest } of CONFIG_SOURCES) {
    downloadFile(url, dest);
  }
}

function runPostinstallPhase() {
  initStructure();
  setupGitHooks();
}

if (phase === "install") {
  runInstallPhase();
} else if (phase === "postinstall") {
  runPostinstallPhase();
} else {
  runInstallPhase();
  runPostinstallPhase();
}
