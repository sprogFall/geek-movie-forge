const fs = require("fs");
const path = require("path");

const appRoot = path.resolve(__dirname, "..");
const nextDir = path.join(appRoot, ".next");
const standaloneRoot = path.join(nextDir, "standalone", "apps", "frontend");

function copyDirIfExists(source, target) {
  if (!fs.existsSync(source)) {
    return;
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.cpSync(source, target, { recursive: true, force: true });
}

copyDirIfExists(path.join(nextDir, "static"), path.join(standaloneRoot, ".next", "static"));
copyDirIfExists(path.join(appRoot, "public"), path.join(standaloneRoot, "public"));
