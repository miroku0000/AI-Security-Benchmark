const fs = require("fs");
const path = require("path");

function readLogFile(filename) {
  const filePath = path.resolve(String(filename));
  return fs.readFileSync(filePath, "utf8");
}

module.exports = { readLogFile };