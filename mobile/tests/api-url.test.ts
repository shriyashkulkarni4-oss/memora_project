import { describe, expect, it } from "vitest";

import { resolveApiUrl } from "../src/api-url";

describe("mobile API URL resolution", () => {
  it("uses an explicit production URL first", () => {
    expect(
      resolveApiUrl("https://memoryhive.example.com/api/v1/", {
        platform: "ios",
        expoHostUri: "192.168.1.10:8081",
      }),
    ).toBe("https://memoryhive.example.com/api/v1");
  });

  it("uses the current hostname for an Expo web preview", () => {
    expect(
      resolveApiUrl(undefined, {
        platform: "web",
        webHostname: "192.168.1.24",
      }),
    ).toBe("http://192.168.1.24:8000/api/v1");
  });

  it("uses the Expo development host for a physical device", () => {
    expect(
      resolveApiUrl(undefined, {
        platform: "ios",
        expoHostUri: "exp://192.168.1.24:8081",
      }),
    ).toBe("http://192.168.1.24:8000/api/v1");
  });

  it("falls back to the Android emulator host bridge", () => {
    expect(resolveApiUrl(undefined, { platform: "android" })).toBe(
      "http://10.0.2.2:8000/api/v1",
    );
  });
});
