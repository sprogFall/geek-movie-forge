const fs = require("fs");
const path = require("path");

const appRoot = path.resolve(__dirname, "..");

for (const dirname of [".next", "out", "dist"]) {
  fs.rmSync(path.join(appRoot, dirname), { recursive: true, force: true });
}
