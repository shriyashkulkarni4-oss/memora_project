import { describe, expect, it } from "vitest";

import {
  expectedStoreScreenshots,
  invalidExpectedScreenshots,
  isFeatureGraphicReady,
  isStoreIconReady,
  missingExpectedScreenshots,
  pngMetadataFromBuffer,
  screenshotManifestHasMetadata,
  screenshotsReady,
  storeAssetManifestHasMetadata,
} from "../scripts/store-asset-readiness.mjs";

function pngBuffer({ width, height, bitDepth = 8, colorType = 2 }) {
  const buffer = Buffer.alloc(33);
  Buffer.from("89504e470d0a1a0a", "hex").copy(buffer, 0);
  buffer.writeUInt32BE(width, 16);
  buffer.writeUInt32BE(height, 20);
  buffer[24] = bitDepth;
  buffer[25] = colorType;
  return buffer;
}

function pngMeta(width, height, colorType = 2) {
  return { width, height, bitDepth: 8, colorType };
}

describe("store asset readiness", () => {
  it("parses PNG metadata and rejects non-PNG buffers", () => {
    expect(
      pngMetadataFromBuffer(pngBuffer({ width: 1290, height: 2796 })),
    ).toEqual({
      width: 1290,
      height: 2796,
      bitDepth: 8,
      colorType: 2,
    });
    expect(pngMetadataFromBuffer(Buffer.from("not a png"))).toBeNull();
    expect(pngMetadataFromBuffer(Buffer.alloc(12))).toBeNull();
  });

  it("requires RGB store icon and feature graphic dimensions", () => {
    expect(isStoreIconReady(pngMeta(1024, 1024))).toBe(true);
    expect(isStoreIconReady(pngMeta(2048, 1024))).toBe(true);
    expect(isStoreIconReady(pngMeta(1024, 1024, 6))).toBe(false);
    expect(isStoreIconReady(pngMeta(1023, 1024))).toBe(false);

    expect(isFeatureGraphicReady(pngMeta(1024, 500))).toBe(true);
    expect(isFeatureGraphicReady(pngMeta(1024, 501))).toBe(false);
    expect(isFeatureGraphicReady(pngMeta(1024, 500, 6))).toBe(false);
  });

  it("requires generated asset manifest metadata", () => {
    const validManifest = {
      assets: [
        {
          path: "cml-memoryhive-mobile/store-assets/icon-1024.png",
          dimensions: "1024x1024",
          purpose: "Store icon source",
          alt_text: "Memoryhive app icon.",
        },
        {
          path: "cml-memoryhive-mobile/store-assets/feature-graphic.png",
          dimensions: "1024x500",
          purpose: "Google Play feature graphic",
          alt_text: "Memoryhive feature graphic.",
        },
      ],
    };

    expect(storeAssetManifestHasMetadata(validManifest)).toBe(true);
    expect(
      storeAssetManifestHasMetadata({
        assets: [
          validManifest.assets[0],
          { ...validManifest.assets[1], dimensions: "1200x630" },
        ],
      }),
    ).toBe(false);
    expect(
      storeAssetManifestHasMetadata({
        assets: [{ ...validManifest.assets[0], alt_text: "" }, validManifest.assets[1]],
      }),
    ).toBe(false);
  });

  it("detects missing, malformed, and non-RGB expected screenshots", () => {
    const allScreenshotNames = expectedStoreScreenshots.map((screenshot) => screenshot.name);
    const incompleteNames = allScreenshotNames.slice(0, 3);
    expect(missingExpectedScreenshots(incompleteNames).map((screenshot) => screenshot.name)).toEqual([
      "android-tablet-04-organize.png",
    ]);

    const invalidNames = allScreenshotNames.slice(0, 2);
    const invalidScreenshots = invalidExpectedScreenshots({
      fileNames: invalidNames,
      pngMetadataFor: (name) =>
        name === "iphone-01-library.png" ? pngMeta(1200, 2796) : pngMeta(1080, 1920, 6),
    });
    expect(invalidScreenshots.map((screenshot) => screenshot.name)).toEqual([
      "iphone-01-library.png",
      "android-phone-02-search.png",
    ]);
    expect(
      invalidExpectedScreenshots({
        fileNames: ["iphone-01-library.png"],
        pngMetadataFor: () => null,
      }).map((screenshot) => screenshot.name),
    ).toEqual(["iphone-01-library.png"]);
    expect(
      screenshotsReady(
        allScreenshotNames,
        (name) => {
          const spec = expectedStoreScreenshots.find((screenshot) => screenshot.name === name);
          return pngMeta(spec.width, spec.height);
        },
      ),
    ).toBe(true);
  });

  it("requires screenshot manifest dimensions and handoff metadata", () => {
    const validManifest = {
      assets: expectedStoreScreenshots.map((screenshot) => ({
        name: screenshot.name,
        dimensions: `${screenshot.width}x${screenshot.height}`,
        platform: "ios",
        form_factor: "phone",
        screen: "Library",
        alt_text: `${screenshot.name} store screenshot.`,
      })),
    };

    expect(screenshotManifestHasMetadata(validManifest)).toBe(true);
    expect(
      screenshotManifestHasMetadata({
        assets: validManifest.assets.map((asset, index) =>
          index === 0 ? { ...asset, dimensions: "1200x2600" } : asset,
        ),
      }),
    ).toBe(false);
    expect(
      screenshotManifestHasMetadata({
        assets: validManifest.assets.map((asset, index) =>
          index === 0 ? { ...asset, form_factor: "" } : asset,
        ),
      }),
    ).toBe(false);
  });
});
