import { describe, expect, it } from "vitest";

import { matchesLocalSearch } from "../src/local-search";
import { ApiError, synchronize, type SyncApi, type SyncRepository } from "../src/sync";
import type { ChangePage, Item, ItemCreate, PendingMutation } from "../src/types";

function item(overrides: Partial<Item> = {}): Item {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    user_id: "user-1",
    type: "text",
    url: null,
    raw_text: "Offline-first architecture notes",
    title: "Architecture",
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
    processing_status: "skipped",
    processing_error: null,
    analysis_status: "analyzed",
    analysis_error: null,
    analysis_version: 1,
    analysis_requested_at: "2026-09-05T09:00:00Z",
    analysis_started_at: "2026-09-05T09:00:00Z",
    analysis_completed_at: "2026-09-05T09:00:00Z",
    category_id: null,
    tags: [{ id: "tag-1", name: "systems", color: "#087F6D" }],
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

class MemoryRepository implements SyncRepository {
  mutations: PendingMutation[] = [];
  records = new Map<string, Item>();
  watermark?: string;
  failures = 0;

  async pendingMutations() { return [...this.mutations]; }
  async removeMutation(sequence: number) { this.mutations = this.mutations.filter((entry) => entry.sequence !== sequence); }
  async failMutation() { this.failures += 1; }
  async upsertRemote(record: Item) { this.records.set(record.id, record); }
  async hasPendingMutation(itemId: string) { return this.mutations.some((entry) => entry.itemId === itemId); }
  async getWatermark() { return this.watermark; }
  async setWatermark(value: string) { this.watermark = value; }
}

function api(overrides: Partial<SyncApi> = {}): SyncApi {
  const empty: ChangePage = { items: [], next_cursor: null, has_more: false, server_time: "2026-09-05T10:00:00Z" };
  return {
    create: async (payload) => item({ id: payload.id }),
    uploadScreenshot: async (payload) => item({ id: payload.id, type: "screenshot" }),
    update: async (id, payload) => item({
      id,
      revision: (payload.expected_revision ?? 1) + 1,
      title: payload.title,
      url: payload.url,
      raw_text: payload.raw_text,
      notes: payload.notes,
      is_favorite: payload.is_favorite,
      is_archived: payload.is_archived,
    }),
    remove: async () => undefined,
    get: async (id) => item({ id }),
    changes: async () => empty,
    ...overrides,
  };
}

describe("offline sync", () => {
  it("searches locally captured content without a server", () => {
    const local = item({ user_id: "local" });
    expect(matchesLocalSearch(local, "architecture")).toBe(true);
    expect(matchesLocalSearch(local, "systems")).toBe(true);
    expect(matchesLocalSearch(local, "unrelated")).toBe(false);
  });

  it("pushes queued captures then pulls all change pages", async () => {
    const repository = new MemoryRepository();
    const payload: ItemCreate = {
      id: item().id,
      type: "text",
      raw_text: "Offline-first architecture notes",
      created_at: item().created_at,
    };
    repository.mutations.push({ sequence: 1, itemId: payload.id, operation: "create", payload, attempts: 0 });
    const remote = item({ id: "22222222-2222-4222-8222-222222222222" });
    let page = 0;
    const result = await synchronize(repository, api({
      changes: async () => page++ === 0
        ? { items: [remote], next_cursor: "next", has_more: true, server_time: "2026-09-05T10:00:00Z" }
        : { items: [], next_cursor: null, has_more: false, server_time: "2026-09-05T10:00:00Z" },
    }));

    expect(result).toEqual({ pushed: 1, pulled: 1, conflicts: 0 });
    expect(repository.mutations).toHaveLength(0);
    expect(repository.records.has(remote.id)).toBe(true);
    expect(repository.watermark).toBe("2026-09-05T10:00:00Z");
  });

  it("resolves an update conflict by replaying the pending local values", async () => {
    const repository = new MemoryRepository();
    repository.mutations.push({
      sequence: 1,
      itemId: item().id,
      operation: "update",
      payload: { title: "Local title", expected_revision: 1 },
      attempts: 0,
    });
    const revisions: number[] = [];
    const result = await synchronize(repository, api({
      update: async (id, payload) => {
        revisions.push(payload.expected_revision ?? 0);
        if (payload.expected_revision === 1) throw new ApiError("Item revision conflict", 409);
        return item({ id, title: payload.title ?? null, revision: 4 });
      },
      get: async () => item({ revision: 3, title: "Remote title" }),
    }));

    expect(revisions).toEqual([1, 3]);
    expect(repository.records.get(item().id)?.title).toBe("Local title");
    expect(result.conflicts).toBe(1);
  });

  it("applies remote tombstones", async () => {
    const repository = new MemoryRepository();
    const deleted = item({ deleted_at: "2026-09-05T10:00:00Z" });
    await synchronize(repository, api({
      changes: async () => ({ items: [deleted], next_cursor: null, has_more: false, server_time: "2026-09-05T11:00:00Z" }),
    }));

    expect(repository.records.get(deleted.id)?.deleted_at).not.toBeNull();
  });
});
