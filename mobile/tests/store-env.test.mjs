import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import {
  assertNoNativeEnvFileFlag,
  envFileValue,
  loadStoreEnvFile,
  parseEnvText,
  parseStoreScriptArgs,
} from "../scripts/store-env.mjs";

const tempFiles = [];

afterEach(() => {
  while (tempFiles.length > 0) {
    const filePath = tempFiles.pop();
    if (filePath && fs.existsSync(filePath)) fs.rmSync(filePath);
  }
});

function writeTempEnvFile(contents) {
  const filePath = path.join(
    os.tmpdir(),
    `memoryhive-store-env-${process.pid}-${tempFiles.length}.env`,
  );
  fs.writeFileSync(filePath, contents);
  tempFiles.push(filePath);
  return filePath;
}

describe("store env parser", () => {
  it("parses comments, export prefixes, quoted values, and inline comments", () => {
    expect(
      parseEnvText(
        [
          "# release config",
          "export EXPO_PUBLIC_API_URL=https://app.memoryhive.com/api/v1",
          "VITE_SUPPORT_EMAIL='support@memoryhive.com'",
          'STORE_REVIEW_ACCOUNT_EMAIL="reviewer@memoryhive.com"',
          "EXPO_PUBLIC_SUPPORT_URL=https://app.memoryhive.com/support # public route",
        ].join("\n"),
      ),
    ).toEqual({
      EXPO_PUBLIC_API_URL: "https://app.memoryhive.com/api/v1",
      VITE_SUPPORT_EMAIL: "support@memoryhive.com",
      STORE_REVIEW_ACCOUNT_EMAIL: "reviewer@memoryhive.com",
      EXPO_PUBLIC_SUPPORT_URL: "https://app.memoryhive.com/support",
    });
  });

  it("reports invalid lines with the source label and line number", () => {
    expect(() => parseEnvText("OK=value\nnot valid", "release.env")).toThrow(
      "Invalid release.env line 2: expected KEY=value.",
    );
  });

  it("parses only the collision-free release env-file flag", () => {
    expect(parseStoreScriptArgs(["--release-env-file", "../.env.production", "--strict"])).toEqual({
      envFilePath: "../.env.production",
      remainingArgs: ["--strict"],
    });
    expect(parseStoreScriptArgs(["--release-env-file=../.env.production"])).toEqual({
      envFilePath: "../.env.production",
      remainingArgs: [],
    });
    expect(() => parseStoreScriptArgs(["--env-file", "../.env.production"])).toThrow(
      "Use --release-env-file for store scripts; --env-file is reserved by Node.",
    );
    expect(() => parseStoreScriptArgs(["--env-file=../.env.production"])).toThrow(
      "Use --release-env-file for store scripts; --env-file is reserved by Node.",
    );
  });

  it("requires a release env-file path when the flag is present", () => {
    expect(() => parseStoreScriptArgs(["--release-env-file"])).toThrow(
      "Missing value for --release-env-file.",
    );
    expect(() => parseStoreScriptArgs(["--release-env-file="])).toThrow(
      "Missing value for --release-env-file.",
    );
  });

  it("rejects native Node env-file flags before release config is read", () => {
    expect(() => assertNoNativeEnvFileFlag(["--env-file", "release.env"])).toThrow(
      "Use --release-env-file for store scripts; --env-file is reserved by Node.",
    );
    expect(() => assertNoNativeEnvFileFlag(["--env-file=release.env"])).toThrow(
      "Use --release-env-file for store scripts; --env-file is reserved by Node.",
    );
    expect(() => assertNoNativeEnvFileFlag(["--trace-warnings"])).not.toThrow();
  });

  it("loads env files and ignores blank values at lookup time", () => {
    const filePath = writeTempEnvFile(
      [
        "EXPO_PUBLIC_API_URL=https://app.memoryhive.com/api/v1",
        "EMPTY_VALUE=",
      ].join("\n"),
    );

    const envFile = loadStoreEnvFile(filePath);
    expect(envFile.path).toBe(filePath);
    expect(envFileValue(envFile, "EXPO_PUBLIC_API_URL")).toBe(
      "https://app.memoryhive.com/api/v1",
    );
    expect(envFileValue(envFile, "EMPTY_VALUE")).toBeUndefined();
  });
});
