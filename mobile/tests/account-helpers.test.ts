import { describe, expect, it } from "vitest";

import {
  filenameFromDisposition,
  resolvePrivacyPolicyUrl,
  resolveSupportUrl,
} from "../src/account-helpers";

describe("account helpers", () => {
  it("extracts export filenames from content disposition headers", () => {
    expect(filenameFromDisposition('attachment; filename="memoryhive-export-2026-09-06.zip"')).toBe(
      "memoryhive-export-2026-09-06.zip",
    );
    expect(filenameFromDisposition(null)).toBe("memoryhive-export.zip");
  });

  it("uses configured privacy URLs before deriving from the API origin", () => {
    expect(resolvePrivacyPolicyUrl(" https://memoryhive.example.com/privacy ", "http://localhost:8000/api/v1")).toBe(
      "https://memoryhive.example.com/privacy",
    );
    expect(resolvePrivacyPolicyUrl(undefined, "http://localhost:8000/api/v1")).toBe(
      "http://localhost:8000/privacy",
    );
  });

  it("uses configured support URLs before deriving from the API origin", () => {
    expect(resolveSupportUrl(" https://memoryhive.example.com/support ", "http://localhost:8000/api/v1")).toBe(
      "https://memoryhive.example.com/support",
    );
    expect(resolveSupportUrl(undefined, "http://localhost:8000/api/v1")).toBe(
      "http://localhost:8000/support",
    );
  });
});
