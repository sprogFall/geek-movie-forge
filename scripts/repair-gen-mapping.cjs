const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const ROOT_DIR = path.resolve(__dirname, "..");
const PACKAGE_NAME = "@jridgewell/gen-mapping";
const LOCKFILE_PATH = path.join(ROOT_DIR, "package-lock.json");
const PACKAGE_DIR = path.join(ROOT_DIR, "node_modules", "@jridgewell", "gen-mapping");
const PACKAGE_JSON_PATH = path.join(PACKAGE_DIR, "package.json");
const REQUIRED_FILE_PATH = path.join(PACKAGE_DIR, "dist", "gen-mapping.umd.js");

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function getInstalledVersion() {
  if (!fs.existsSync(PACKAGE_JSON_PATH)) {
    return null;
  }

  return readJson(PACKAGE_JSON_PATH).version ?? null;
}

function getLockedVersion() {
  if (!fs.existsSync(LOCKFILE_PATH)) {
    return null;
  }

  const lockfile = readJson(LOCKFILE_PATH);
  return (
    lockfile.packages?.["node_modules/@jridgewell/gen-mapping"]?.version ??
    lockfile.dependencies?.["@jridgewell/gen-mapping"]?.version ??
    null
  );
}

function run(command, args, cwd) {
  if (process.platform === "win32" && command === "npm") {
    const commandLine = ["npm.cmd", ...args]
      .map((part) => (/\s/.test(part) ? `"${part.replace(/"/g, '\\"')}"` : part))
      .join(" ");

    return execFileSync("cmd.exe", ["/d", "/s", "/c", commandLine], {
      cwd,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
  }

  const resolvedCommand = process.platform === "win32" && command === "tar" ? "tar.exe" : command;
  return execFileSync(resolvedCommand, args, {
    cwd,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function restorePackage(version) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "gen-mapping-repair-"));

  try {
    const packOutput = run("npm", ["pack", `${PACKAGE_NAME}@${version}`, "--json", "--silent"], tempDir);
    const [{ filename }] = JSON.parse(packOutput);
    const tarballPath = path.join(tempDir, filename);

    run("tar", ["-xf", tarballPath, "-C", tempDir], tempDir);

    const extractedPackageDir = path.join(tempDir, "package");
    if (!fs.existsSync(extractedPackageDir)) {
      throw new Error("Extracted package directory was not found.");
    }

    fs.mkdirSync(path.dirname(PACKAGE_DIR), { recursive: true });
    fs.cpSync(extractedPackageDir, PACKAGE_DIR, { recursive: true, force: true });
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

function main() {
  if (fs.existsSync(PACKAGE_JSON_PATH) && fs.existsSync(REQUIRED_FILE_PATH)) {
    return;
  }

  const version = getInstalledVersion() ?? getLockedVersion();
  if (!version) {
    console.error(`[repair-gen-mapping] Unable to resolve a version for ${PACKAGE_NAME}.`);
    process.exit(1);
  }

  try {
    restorePackage(version);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`[repair-gen-mapping] Failed to restore ${PACKAGE_NAME}@${version}: ${message}`);
    process.exit(1);
  }

  if (!fs.existsSync(PACKAGE_JSON_PATH) || !fs.existsSync(REQUIRED_FILE_PATH)) {
    console.error(`[repair-gen-mapping] Restored ${PACKAGE_NAME}@${version}, but required files are still missing.`);
    process.exit(1);
  }

  console.log(`[repair-gen-mapping] Restored ${PACKAGE_NAME}@${version} in node_modules.`);
}

main();
