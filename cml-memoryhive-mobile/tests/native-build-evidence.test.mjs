import { describe, expect, it } from "vitest";

import {
  androidBuildEvidenceReady,
  iosBuildEvidenceReady,
  recordedArtifactExists,
  repoRelativePath,
  testedDeviceCount,
} from "../scripts/native-build-evidence.mjs";

const repoRoot = "/repo/memoryhive";
const existingFiles = new Set([
  "cml-memoryhive-mobile/builds/memoryhive-ios-production.ipa",
  "cml-memoryhive-mobile/builds/memoryhive-android-production.aab",
]);
const fileHasContent = (relativePath) => existingFiles.has(relativePath);
const context = { repoRoot, fileHasContent };

describe("native build evidence", () => {
  it("normalizes relative and in-repo absolute artifact paths", () => {
    expect(repoRelativePath("./cml-memoryhive-mobile/builds/app.ipa", repoRoot)).toBe(
      "cml-memoryhive-mobile/builds/app.ipa",
    );
    expect(repoRelativePath("/repo/memoryhive/cml-memoryhive-mobile/builds/app.ipa", repoRoot)).toBe(
      "cml-memoryhive-mobile/builds/app.ipa",
    );
    expect(repoRelativePath("/tmp/app.ipa", repoRoot)).toBe("");
    expect(repoRelativePath("", repoRoot)).toBe("");
  });

  it("accepts only non-empty artifacts under cml-memoryhive-mobile/builds with platform extensions", () => {
    expect(
      recordedArtifactExists("cml-memoryhive-mobile/builds/memoryhive-ios-production.ipa", [".ipa"], context),
    ).toBe(true);
    expect(
      recordedArtifactExists("cml-memoryhive-mobile/memoryhive-ios-production.ipa", [".ipa"], context),
    ).toBe(false);
    expect(
      recordedArtifactExists("cml-memoryhive-mobile/builds/memoryhive-ios-production.zip", [".ipa"], context),
    ).toBe(false);
    expect(recordedArtifactExists("cml-memoryhive-mobile/builds/missing.ipa", [".ipa"], context)).toBe(
      false,
    );
  });

  it("counts distinct non-empty tested device records", () => {
    expect(testedDeviceCount(["iPhone 15 / iOS 18", " iPhone 15 / iOS 18 ", ""])).toBe(1);
    expect(testedDeviceCount(["Pixel 8 / Android 16", "Tablet / Android 16"])).toBe(2);
    expect(testedDeviceCount("Pixel 8")).toBe(0);
  });

  it("requires complete production iOS build evidence", () => {
    expect(
      iosBuildEvidenceReady(
        {
          profile: "production",
          eas_build_id: "ios-build-123",
          artifact_path: "cml-memoryhive-mobile/builds/memoryhive-ios-production.ipa",
          tested_devices: ["iPhone 15 / iOS 18", "iPad Air / iPadOS 18"],
        },
        context,
      ),
    ).toBe(true);
    expect(
      iosBuildEvidenceReady(
        {
          profile: "production",
          eas_build_id: "replace-with-eas-ios-build-id",
          artifact_path: "cml-memoryhive-mobile/builds/memoryhive-ios-production.ipa",
          tested_devices: ["iPhone 15 / iOS 18", "iPad Air / iPadOS 18"],
        },
        context,
      ),
    ).toBe(false);
    expect(
      iosBuildEvidenceReady(
        {
          profile: "preview",
          eas_build_id: "ios-build-123",
          artifact_path: "cml-memoryhive-mobile/builds/memoryhive-ios-production.ipa",
          tested_devices: ["iPhone 15 / iOS 18", "iPad Air / iPadOS 18"],
        },
        context,
      ),
    ).toBe(false);
  });

  it("requires complete production Android target and permission evidence", () => {
    expect(
      androidBuildEvidenceReady(
        {
          profile: "production",
          eas_build_id: "android-build-123",
          artifact_path: "cml-memoryhive-mobile/builds/memoryhive-android-production.aab",
          target_sdk_version: 36,
          record_audio_permission_present: false,
          tested_devices: ["Pixel 8 / Android 16", "Android tablet / Android 16"],
        },
        context,
      ),
    ).toBe(true);
    expect(
      androidBuildEvidenceReady(
        {
          profile: "production",
          eas_build_id: "android-build-123",
          artifact_path: "cml-memoryhive-mobile/builds/memoryhive-android-production.aab",
          target_sdk_version: 35,
          record_audio_permission_present: false,
          tested_devices: ["Pixel 8 / Android 16", "Android tablet / Android 16"],
        },
        context,
      ),
    ).toBe(false);
    expect(
      androidBuildEvidenceReady(
        {
          profile: "production",
          eas_build_id: "android-build-123",
          artifact_path: "cml-memoryhive-mobile/builds/memoryhive-android-production.aab",
          target_sdk_version: 36,
          record_audio_permission_present: true,
          tested_devices: ["Pixel 8 / Android 16", "Android tablet / Android 16"],
        },
        context,
      ),
    ).toBe(false);
  });
});
