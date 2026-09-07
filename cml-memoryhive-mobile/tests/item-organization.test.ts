import { describe, expect, it } from "vitest";

import {
  countItemsInCategory,
  summarizeManagedTags,
  summarizeOrganization,
} from "../src/item-organization";
import type { Item, ManagedTag } from "../src/types";

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

describe("mobile organization summary", () => {
  it("summarizes active status and item types", () => {
    const summary = summarizeOrganization([
      item({ id: "link", type: "link", is_favorite: true }),
      item({ id: "image", type: "screenshot", processing_status: "processing" }),
      item({ id: "archived", is_archived: true }),
    ]);

    expect(summary.active).toBe(2);
    expect(summary.archived).toBe(1);
    expect(summary.favorites).toBe(1);
    expect(summary.processing).toBe(1);
    expect(summary.byType).toEqual({ link: 1, screenshot: 1, text: 0 });
  });

  it("counts active tags and sorts by usage then name", () => {
    const summary = summarizeOrganization([
      item({ id: "a", tags: [{ id: "tag-1", name: "research", color: "#087F6D" }] }),
      item({ id: "b", tags: [{ id: "tag-2", name: "product", color: "#087F6D" }] }),
      item({ id: "c", tags: [{ id: "tag-1", name: "Research", color: "#087F6D" }] }),
      item({ id: "d", is_archived: true, tags: [{ id: "tag-3", name: "archive", color: "#087F6D" }] }),
    ]);

    expect(summary.tags).toEqual([
      { name: "research", count: 2 },
      { name: "product", count: 1 },
    ]);
  });

  it("counts category assignments from the local item cache", () => {
    expect(countItemsInCategory([
      item({ id: "a", category_id: "cat-1" }),
      item({ id: "b", category_id: "cat-1" }),
      item({ id: "c", category_id: "cat-2" }),
    ], "cat-1")).toBe(2);
  });

  it("merges managed tags with local-only tag summaries", () => {
    const managed: ManagedTag[] = [
      { id: "tag-1", name: "Research", color: "#2563EB", usage_count: 7 },
    ];

    const summary = summarizeManagedTags([
      item({ id: "a", tags: [{ id: "tag-1", name: "research", color: "#087F6D" }] }),
      item({ id: "b", tags: [{ id: "local:ideas", name: "ideas", color: "#087F6D" }] }),
    ], managed);

    expect(summary).toEqual([
      { id: "local:ideas", name: "ideas", color: "#087F6D", count: 1, managed: false },
      { id: "tag-1", name: "research", color: "#2563EB", count: 1, managed: true },
    ]);
  });
});
