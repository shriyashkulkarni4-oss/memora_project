import path from "node:path";

export const androidTargetSdkMinimum = 36;
export const nativeArtifactManifestPath = "cml-memoryhive-mobile/builds/native-artifacts.json";
export const iosArtifactExtensions = [".ipa"];
export const androidArtifactExtensions = [".aab", ".apk"];

export function repoRelativePath(candidate, repoRoot) {
  if (typeof candidate !== "string" || !candidate.trim()) return "";
  const cleaned = candidate.trim().replace(/^\.\//, "");
  if (!path.isAbsolute(cleaned)) return cleaned;
  const relative = path.relative(repoRoot, cleaned);
  if (relative.startsWith("..") || path.isAbsolute(relative)) return "";
  return relative;
}

export function recordedArtifactExists(candidate, extensions, { repoRoot, fileHasContent }) {
  const relativePath = repoRelativePath(candidate, repoRoot);
  return Boolean(
    relativePath &&
      relativePath.startsWith("cml-memoryhive-mobile/builds/") &&
      extensions.includes(path.extname(relativePath).toLowerCase()) &&
      fileHasContent(relativePath),
  );
}

export function hasRealBuildId(candidate) {
  if (typeof candidate !== "string") return false;
  const value = candidate.trim();
  return Boolean(value) && !value.startsWith("replace-with-");
}

export function testedDeviceCount(candidate) {
  if (!Array.isArray(candidate)) return 0;
  return new Set(
    candidate
      .filter((device) => typeof device === "string")
      .map((device) => device.trim())
      .filter(Boolean),
  ).size;
}

export function hasTestedDevices(candidate, minimum = 1) {
  return testedDeviceCount(candidate) >= minimum;
}

export function iosBuildEvidenceReady(evidence, { repoRoot, fileHasContent }) {
  return Boolean(
    evidence?.profile === "production" &&
      hasRealBuildId(evidence?.eas_build_id) &&
      recordedArtifactExists(evidence?.artifact_path, iosArtifactExtensions, {
        repoRoot,
        fileHasContent,
      }) &&
      hasTestedDevices(evidence?.tested_devices, 2),
  );
}

export function androidBuildEvidenceReady(evidence, { repoRoot, fileHasContent }) {
  return Boolean(
    evidence?.profile === "production" &&
      hasRealBuildId(evidence?.eas_build_id) &&
      recordedArtifactExists(evidence?.artifact_path, androidArtifactExtensions, {
        repoRoot,
        fileHasContent,
      }) &&
      Number(evidence?.target_sdk_version) >= androidTargetSdkMinimum &&
      evidence?.record_audio_permission_present === false &&
      hasTestedDevices(evidence?.tested_devices, 2),
  );
}
