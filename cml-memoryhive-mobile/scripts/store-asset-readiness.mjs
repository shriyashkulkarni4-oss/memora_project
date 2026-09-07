export const expectedStoreScreenshots = [
  { name: "iphone-01-library.png", width: 1290, height: 2796 },
  { name: "android-phone-02-search.png", width: 1080, height: 1920 },
  { name: "ipad-03-library.png", width: 2048, height: 2732 },
  { name: "android-tablet-04-organize.png", width: 1600, height: 2560 },
];

const pngSignature = "89504e470d0a1a0a";

const requiredStoreAssetManifestEntries = [
  { name: "icon-1024.png", dimensions: "1024x1024" },
  { name: "feature-graphic.png", dimensions: "1024x500" },
];

function hasText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

export function pngMetadataFromBuffer(buffer) {
  if (!buffer || buffer.length < 26) return null;
  const bytes = Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
  if (bytes.subarray(0, 8).toString("hex") !== pngSignature) return null;
  return {
    width: bytes.readUInt32BE(16),
    height: bytes.readUInt32BE(20),
    bitDepth: bytes[24],
    colorType: bytes[25],
  };
}

export function isRgbPng(meta) {
  return Boolean(meta && meta.colorType === 2);
}

export function isStoreIconReady(meta) {
  return Boolean(meta && meta.width >= 1024 && meta.height >= 1024 && isRgbPng(meta));
}

export function isFeatureGraphicReady(meta) {
  return Boolean(meta && meta.width === 1024 && meta.height === 500 && isRgbPng(meta));
}

export function storeAssetManifestHasMetadata(assetManifest) {
  return requiredStoreAssetManifestEntries.every((expected) =>
    assetManifest?.assets?.some(
      (asset) =>
        asset.path?.endsWith(expected.name) &&
        asset.dimensions === expected.dimensions &&
        hasText(asset.purpose) &&
        hasText(asset.alt_text),
    ),
  );
}

export function missingExpectedScreenshots(
  fileNames,
  specs = expectedStoreScreenshots,
) {
  const screenshotSet = new Set(fileNames);
  return specs.filter((screenshot) => !screenshotSet.has(screenshot.name));
}

export function invalidExpectedScreenshots({
  fileNames,
  pngMetadataFor,
  specs = expectedStoreScreenshots,
}) {
  const screenshotSet = new Set(fileNames);
  return specs.filter((screenshot) => {
    if (!screenshotSet.has(screenshot.name)) return false;
    const meta = pngMetadataFor(screenshot.name);
    return (
      !meta ||
      meta.width !== screenshot.width ||
      meta.height !== screenshot.height ||
      !isRgbPng(meta)
    );
  });
}

export function screenshotsReady(
  fileNames,
  pngMetadataFor,
  specs = expectedStoreScreenshots,
) {
  return (
    missingExpectedScreenshots(fileNames, specs).length === 0 &&
    invalidExpectedScreenshots({ fileNames, pngMetadataFor, specs }).length === 0
  );
}

export function screenshotManifestHasMetadata(
  screenshotManifest,
  specs = expectedStoreScreenshots,
) {
  return specs.every((screenshot) =>
    screenshotManifest?.assets?.some(
      (asset) =>
        asset.name === screenshot.name &&
        asset.dimensions === `${screenshot.width}x${screenshot.height}` &&
        hasText(asset.platform) &&
        hasText(asset.form_factor) &&
        hasText(asset.screen) &&
        hasText(asset.alt_text),
    ),
  );
}
