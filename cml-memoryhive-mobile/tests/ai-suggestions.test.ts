import { describe, expect, it } from "vitest";

import { suggestionsFromItem } from "../src/ai-suggestions";
import type { Item } from "../src/types";

const item = {
  metadata: {
    enrichment: {
      suggested_tags: ["postgresql", "database"],
      classification: "reference",
      topics: ["query planning"],
      confidence: 0.92,
    },
    suggestion_decisions: {
      "tag:postgresql": "accept",
      "tag:database": "never",
      "classification:reference": "reject",
    },
  },
} as unknown as Item;

describe("mobile AI suggestions", () => {
  it("keeps generated output separate from reversible local decisions", () => {
    const view = suggestionsFromItem(item);
    expect(view.topics).toEqual(["query planning"]);
    expect(view.suggestions.map(({ value, status }) => [value, status])).toEqual([
      ["postgresql", "accepted"],
      ["database", "never"],
      ["reference", "rejected"],
    ]);
    expect((item.metadata?.enrichment as Record<string, unknown>).suggested_tags).toEqual(["postgresql", "database"]);
  });

  it("treats undo as pending without mutating model output", () => {
    const undone = {
      ...item,
      metadata: {
        ...item.metadata,
        suggestion_decisions: { "tag:postgresql": "undo" },
      },
    };
    expect(suggestionsFromItem(undone).suggestions[0].status).toBe("pending");
  });
});
