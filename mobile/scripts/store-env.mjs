import fs from "node:fs";
import path from "node:path";

function normalizeEnvValue(rawValue) {
  const value = rawValue.trim();
  const quote = value[0];
  if ((quote === "\"" || quote === "'") && value.endsWith(quote)) {
    const unquoted = value.slice(1, -1);
    if (quote === "\"") {
      return unquoted
        .replaceAll("\\n", "\n")
        .replaceAll('\\"', "\"")
        .replaceAll("\\\\", "\\");
    }
    return unquoted;
  }
  return value.replace(/\s+#.*$/, "").trim();
}

export function parseEnvText(text, sourceLabel = "env file") {
  const values = {};
  for (const [index, line] of text.split(/\r?\n/).entries()) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const match = trimmed.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!match) {
      throw new Error(`Invalid ${sourceLabel} line ${index + 1}: expected KEY=value.`);
    }

    values[match[1]] = normalizeEnvValue(match[2]);
  }
  return values;
}

export function parseStoreScriptArgs(argv) {
  const remainingArgs = [];
  let envFilePath;

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--release-env-file") {
      const next = argv[index + 1];
      if (!next || next.startsWith("--")) {
        throw new Error("Missing value for --release-env-file.");
      }
      envFilePath = next;
      index += 1;
      continue;
    }
    if (arg === "--env-file" || arg.startsWith("--env-file=")) {
      throw new Error("Use --release-env-file for store scripts; --env-file is reserved by Node.");
    }
    if (arg.startsWith("--release-env-file=")) {
      envFilePath = arg.slice("--release-env-file=".length);
      if (!envFilePath) throw new Error("Missing value for --release-env-file.");
      continue;
    }
    remainingArgs.push(arg);
  }

  return { envFilePath, remainingArgs };
}

export function assertNoNativeEnvFileFlag(execArgv) {
  if (execArgv.some((arg) => arg === "--env-file" || arg.startsWith("--env-file="))) {
    throw new Error("Use --release-env-file for store scripts; --env-file is reserved by Node.");
  }
}

function resolveEnvFilePath(envFilePath, roots) {
  if (path.isAbsolute(envFilePath)) return envFilePath;

  const candidates = roots
    .filter(Boolean)
    .map((root) => path.resolve(root, envFilePath));
  return candidates.find((candidate) => fs.existsSync(candidate)) ?? candidates[0];
}

export function loadStoreEnvFile(envFilePath, { cwd = process.cwd(), repoRoot } = {}) {
  if (!envFilePath) return { path: undefined, values: {} };

  const resolvedPath = resolveEnvFilePath(envFilePath, [cwd, repoRoot]);
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`Env file not found: ${resolvedPath}`);
  }

  const stats = fs.statSync(resolvedPath);
  if (!stats.isFile()) {
    throw new Error(`Env file is not a file: ${resolvedPath}`);
  }

  return {
    path: resolvedPath,
    values: parseEnvText(fs.readFileSync(resolvedPath, "utf8"), resolvedPath),
  };
}

export function envFileValue(envFile, name) {
  const value = envFile.values[name];
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}
