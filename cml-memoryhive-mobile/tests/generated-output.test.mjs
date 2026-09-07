import { describe, expect, it } from "vitest";

import { generatedOutputMismatches } from "../scripts/generated-output.mjs";

const outputs = [
  { content: "current json\n", filePath: "/repo/packet.json", label: "packet.json" },
  { content: "current markdown\n", filePath: "/repo/packet.md", label: "packet.md" },
];

describe("generated output validation", () => {
  it("accepts generated files whose bytes match expected content", () => {
    const files = new Map(outputs.map(({ content, filePath }) => [filePath, content]));

    expect(generatedOutputMismatches(outputs, (filePath) => files.get(filePath))).toEqual([]);
  });

  it("reports stale and missing generated files", () => {
    const files = new Map([[outputs[0].filePath, "stale json\n"]]);

    expect(
      generatedOutputMismatches(outputs, (filePath) => files.get(filePath)).map(
        ({ label }) => label,
      ),
    ).toEqual(["packet.json", "packet.md"]);
  });
});
