const fs = require("fs");
const path = require("path");

const appRoot = path.resolve(__dirname, "..");
const exportRoot = path.join(appRoot, "out");
const distRoot = path.join(appRoot, "dist");

if (!fs.existsSync(exportRoot)) {
  throw new Error(`Missing static export output: ${exportRoot}`);
}

fs.rmSync(distRoot, { recursive: true, force: true });
fs.cpSync(exportRoot, distRoot, { recursive: true, force: true });
fs.rmSync(exportRoot, { recursive: true, force: true });
