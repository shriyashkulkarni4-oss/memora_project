import { describe, expect, it } from "vitest";

import { localMemoryConnections } from "../src/memory-connections";
import type { Item } from "../src/types";

const base = {
  user_id: "user",
  type: "text",
  url: null,
  description: null,
  notes: null,
  source_domain: null,
  author: null,
  published_at: null,
  favicon_url: null,
  extracted_text: null,
  language: null,
  summary: null,
  metadata: null,
  processing_status: "ready",
  processing_error: null,
  analysis_status: "analyzed",
  analysis_error: null,
  analysis_version: 1,
  analysis_requested_at: null,
  analysis_started_at: null,
  analysis_completed_at: null,
  category_id: null,
  assets: [],
  is_favorite: false,
  is_archived: false,
  read_count: 0,
  last_visited_at: null,
  revision: 1,
  deleted_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
} as const;

function item(overrides: Partial<Item>): Item {
  return { ...base, id: "source", title: "Memory", raw_text: "durable content", source: "notes", tags: [], ...overrides } as Item;
}

describe("offline memory connections", () => {
  it("finds exact duplicates and related tags without a provider", () => {
    const source = item({ tags: [{ id: "t", name: "temporal", color: "#000" }] });
    const duplicate = item({ id: "duplicate", title: "Copy" });
    const related = item({ id: "related", title: "Workflow", raw_text: "different", tags: [{ id: "t2", name: "temporal", color: "#000" }] });
    const unrelated = item({ id: "other", raw_text: "bread", source: "kitchen" });

    const results = localMemoryConnections(source, [source, unrelated, related, duplicate]);

    expect(results.map((value) => value.item.id)).toEqual(["duplicate", "related"]);
    expect(results[0].duplicate).toBe(true);
    expect(results[1].reasons).toContain("shared tags: temporal");
  });
});
