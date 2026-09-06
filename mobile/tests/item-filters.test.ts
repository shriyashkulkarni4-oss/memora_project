import { describe, expect, it } from "vitest";

import { filterItems, uniqueTags, type ItemFilterState } from "../src/item-filters";
import type { Item } from "../src/types";

function item(overrides: Partial<Item> = {}): Item {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    user_id: "user-1",
    type: "text",
    url: null,
    raw_text: "Offline notes",
    title: "Notes",
    description: null,
    notes: null,
    source: "mobile",
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
    analysis_requested_at: "2026-09-05T09:00:00Z",
    analysis_started_at: "2026-09-05T09:00:00Z",
    analysis_completed_at: "2026-09-05T09:00:00Z",
    category_id: null,
    tags: [{ id: "tag-1", name: "research", color: "#087F6D" }],
    assets: [],
    is_favorite: false,
    is_archived: false,
    read_count: 0,
    last_visited_at: null,
    revision: 1,
    deleted_at: null,
    created_at: "2026-09-05T09:00:00Z",
    updated_at: "2026-09-05T09:00:00Z",
    ...overrides,
  };
}

const defaults: ItemFilterState = { summary: "saved", type: "all", categoryId: null, tags: [] };

describe("mobile item filters", () => {
  it("normalizes tag pills consistently", () => {
    expect(uniqueTags([" Research ", "research", "Deep Work"])).toEqual([
      "deep work",
      "research",
    ]);
  });

  it("filters by summary, type, and selected tags", () => {
    const records = [
      item({ id: "saved", category_id: "cat-1", tags: [{ id: "tag-1", name: "research", color: "#087F6D" }] }),
      item({ id: "favorite", is_favorite: true, type: "link", tags: [{ id: "tag-2", name: "product", color: "#087F6D" }] }),
      item({ id: "archived", is_archived: true }),
      item({ id: "processing", processing_status: "processing", tags: [{ id: "tag-3", name: "systems", color: "#087F6D" }] }),
    ];

    expect(filterItems(records, { ...defaults }).map((record) => record.id)).toEqual([
      "saved",
      "favorite",
      "processing",
    ]);
    expect(filterItems(records, { ...defaults, summary: "favorites" }).map((record) => record.id)).toEqual(["favorite"]);
    expect(filterItems(records, { ...defaults, summary: "archived" }).map((record) => record.id)).toEqual(["archived"]);
    expect(filterItems(records, { ...defaults, summary: "processing" }).map((record) => record.id)).toEqual(["processing"]);
    expect(filterItems(records, { ...defaults, type: "link" }).map((record) => record.id)).toEqual(["favorite"]);
    expect(filterItems(records, { ...defaults, categoryId: "cat-1" }).map((record) => record.id)).toEqual(["saved"]);
    expect(filterItems(records, { ...defaults, tags: ["research"] }).map((record) => record.id)).toEqual(["saved"]);
  });
});
