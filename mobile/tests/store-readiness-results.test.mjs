import { describe, expect, it } from "vitest";

import {
  blockerScope,
  readinessShouldFail,
  summarizeReadinessResults,
} from "../scripts/store-readiness-results.mjs";

const results = [
  { level: "OK", title: "config" },
  { level: "WARN", title: "notice" },
  { level: "BLOCKED", scope: blockerScope.repository, title: "asset" },
  { level: "BLOCKED", scope: blockerScope.release, title: "credentials" },
];

describe("store readiness result handling", () => {
  it("summarizes repository and release blockers separately", () => {
    expect(summarizeReadinessResults(results)).toEqual({
      ok: 1,
      warnings: 1,
      blockers: 2,
      repositoryBlockers: 1,
      releaseBlockers: 1,
    });
  });

  it("keeps the default report informational", () => {
    const counts = summarizeReadinessResults(results);

    expect(readinessShouldFail({ counts })).toBe(false);
  });

  it("fails CI only for repository blockers", () => {
    const releaseOnlyCounts = summarizeReadinessResults([
      { level: "BLOCKED", scope: blockerScope.release, title: "credentials" },
    ]);
    const mixedCounts = summarizeReadinessResults(results);

    expect(readinessShouldFail({ counts: releaseOnlyCounts, ci: true })).toBe(false);
    expect(readinessShouldFail({ counts: mixedCounts, ci: true })).toBe(true);
  });

  it("fails strict checks for any blocker", () => {
    const counts = summarizeReadinessResults([
      { level: "BLOCKED", scope: blockerScope.release, title: "credentials" },
    ]);

    expect(readinessShouldFail({ counts, strict: true })).toBe(true);
  });
});
