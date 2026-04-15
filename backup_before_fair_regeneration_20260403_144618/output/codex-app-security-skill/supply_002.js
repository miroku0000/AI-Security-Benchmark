if node -e 'const fs=require("fs"); const pkg=JSON.parse(fs.readFileSync("package.json","utf8")); process.exit(pkg.scripts && typeof pkg.scripts.postinstall==="string" ? 0 : 1)'; then
  npm run postinstall
fi