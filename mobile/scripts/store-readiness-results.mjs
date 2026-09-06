export const blockerScope = Object.freeze({
  release: "release",
  repository: "repository",
});

export function summarizeReadinessResults(results) {
  return results.reduce(
    (counts, entry) => {
      if (entry.level === "OK") counts.ok += 1;
      if (entry.level === "WARN") counts.warnings += 1;
      if (entry.level === "BLOCKED") {
        counts.blockers += 1;
        if (entry.scope === blockerScope.release) counts.releaseBlockers += 1;
        else counts.repositoryBlockers += 1;
      }
      return counts;
    },
    {
      ok: 0,
      warnings: 0,
      blockers: 0,
      repositoryBlockers: 0,
      releaseBlockers: 0,
    },
  );
}

export function readinessShouldFail({ counts, ci = false, strict = false }) {
  if (strict) return counts.blockers > 0;
  if (ci) return counts.repositoryBlockers > 0;
  return false;
}
