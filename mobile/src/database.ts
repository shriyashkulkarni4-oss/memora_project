import * as SQLite from "expo-sqlite";

import { matchesLocalSearch } from "./local-search";
import type { Item, ItemCreate, ItemUpdate, PendingMutation } from "./types";
import type { SyncRepository } from "./sync";

let databasePromise: Promise<SQLite.SQLiteDatabase> | undefined;

function database() {
  databasePromise ??= SQLite.openDatabaseAsync("memoryhive.db");
  return databasePromise;
}

export async function initializeDatabase() {
  const db = await database();
  await db.execAsync(`
    PRAGMA journal_mode = WAL;
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS items (
      id TEXT PRIMARY KEY NOT NULL,
      payload TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      deleted_at TEXT,
      dirty INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS mutations (
      sequence INTEGER PRIMARY KEY AUTOINCREMENT,
      item_id TEXT NOT NULL,
      operation TEXT NOT NULL,
      payload TEXT NOT NULL,
      local_uri TEXT,
      attempts INTEGER NOT NULL DEFAULT 0,
      last_error TEXT,
      created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS ix_mutations_item_id ON mutations(item_id);
    CREATE INDEX IF NOT EXISTS ix_items_updated_at ON items(updated_at DESC);
    CREATE TABLE IF NOT EXISTS metadata (
      key TEXT PRIMARY KEY NOT NULL,
      value TEXT NOT NULL
    );
  `);
}

function draftItem(payload: ItemCreate): Item {
  const now = payload.created_at;
  return {
    id: payload.id,
    user_id: "local",
    type: payload.type,
    url: payload.url ?? null,
    raw_text: payload.raw_text ?? null,
    title: payload.title ?? null,
    description: null,
    notes: payload.notes ?? null,
    source: "mobile",
    source_domain: payload.url ? new URL(payload.url).hostname : null,
    author: null,
    published_at: null,
    favicon_url: null,
    extracted_text: null,
    language: null,
    summary: null,
    metadata: payload.metadata ?? null,
    processing_status: payload.type === "text" ? "skipped" : "pending",
    processing_error: null,
    category_id: null,
    tags: (payload.tags ?? []).map((name) => ({ id: `local:${name}`, name, color: "#087F6D" })),
    assets: [],
    is_favorite: false,
    is_archived: false,
    read_count: 0,
    last_visited_at: null,
    revision: 1,
    deleted_at: null,
    created_at: now,
    updated_at: now,
  };
}

export async function captureLocal(payload: ItemCreate, localUri?: string) {
  const db = await database();
  const item = draftItem(payload);
  const operation = payload.type === "screenshot" ? "screenshot" : "create";
  await db.withTransactionAsync(async () => {
    await db.runAsync(
      "INSERT INTO items (id, payload, updated_at, dirty) VALUES (?, ?, ?, 1)",
      item.id,
      JSON.stringify(item),
      item.updated_at,
    );
    await db.runAsync(
      "INSERT INTO mutations (item_id, operation, payload, local_uri, created_at) VALUES (?, ?, ?, ?, ?)",
      item.id,
      operation,
      JSON.stringify(payload),
      localUri ?? null,
      item.created_at,
    );
  });
  return item;
}

export async function updateLocal(id: string, update: ItemUpdate) {
  const db = await database();
  const row = await db.getFirstAsync<{ payload: string }>("SELECT payload FROM items WHERE id = ?", id);
  if (!row) throw new Error("Item not found");
  const current = JSON.parse(row.payload) as Item;
  const tags = update.tags?.map((name) => ({ id: `local:${name}`, name, color: "#087F6D" }));
  const item: Item = {
    ...current,
    ...update,
    tags: tags ?? current.tags,
    updated_at: new Date().toISOString(),
  };
  await db.withTransactionAsync(async () => {
    await db.runAsync(
      "UPDATE items SET payload = ?, updated_at = ?, dirty = 1 WHERE id = ?",
      JSON.stringify(item),
      item.updated_at,
      id,
    );
    await db.runAsync(
      "INSERT INTO mutations (item_id, operation, payload, created_at) VALUES (?, 'update', ?, ?)",
      id,
      JSON.stringify({ ...update, expected_revision: current.revision }),
      item.updated_at,
    );
  });
  return item;
}

export async function deleteLocal(id: string) {
  const db = await database();
  const now = new Date().toISOString();
  const row = await db.getFirstAsync<{ payload: string }>("SELECT payload FROM items WHERE id = ?", id);
  if (!row) return;
  const item = { ...(JSON.parse(row.payload) as Item), deleted_at: now, updated_at: now };
  await db.withTransactionAsync(async () => {
    await db.runAsync(
      "UPDATE items SET payload = ?, updated_at = ?, deleted_at = ?, dirty = 1 WHERE id = ?",
      JSON.stringify(item),
      now,
      now,
      id,
    );
    await db.runAsync(
      "INSERT INTO mutations (item_id, operation, payload, created_at) VALUES (?, 'delete', '{}', ?)",
      id,
      now,
    );
  });
}

export async function listLocal(search = "", includeArchived = false): Promise<Item[]> {
  const db = await database();
  const rows = await db.getAllAsync<{ payload: string }>(
    "SELECT payload FROM items WHERE deleted_at IS NULL ORDER BY updated_at DESC",
  );
  return rows
    .map(({ payload }) => JSON.parse(payload) as Item)
    .filter((item) => includeArchived || !item.is_archived)
    .filter((item) => matchesLocalSearch(item, search));
}

export async function getLocal(id: string): Promise<Item | undefined> {
  const db = await database();
  const row = await db.getFirstAsync<{ payload: string }>("SELECT payload FROM items WHERE id = ?", id);
  return row ? (JSON.parse(row.payload) as Item) : undefined;
}

export async function clearLocalData() {
  const db = await database();
  await db.execAsync("DELETE FROM mutations; DELETE FROM items; DELETE FROM metadata;");
}

export async function prepareLocalDataForUser(userId: string) {
  const db = await database();
  const row = await db.getFirstAsync<{ value: string }>(
    "SELECT value FROM metadata WHERE key = 'local_user_id'",
  );
  if (row && row.value !== userId) await clearLocalData();
  await db.runAsync(
    "INSERT INTO metadata (key, value) VALUES ('local_user_id', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
    userId,
  );
}

export const sqliteSyncRepository: SyncRepository = {
  async pendingMutations() {
    const db = await database();
    const rows = await db.getAllAsync<{
      sequence: number;
      item_id: string;
      operation: PendingMutation["operation"];
      payload: string;
      local_uri: string | null;
      attempts: number;
    }>("SELECT sequence, item_id, operation, payload, local_uri, attempts FROM mutations ORDER BY sequence");
    return rows.map((row) => ({
      sequence: row.sequence,
      itemId: row.item_id,
      operation: row.operation,
      payload: JSON.parse(row.payload),
      localUri: row.local_uri ?? undefined,
      attempts: row.attempts,
    }));
  },
  async removeMutation(sequence) {
    const db = await database();
    await db.runAsync("DELETE FROM mutations WHERE sequence = ?", sequence);
  },
  async failMutation(sequence, message) {
    const db = await database();
    await db.runAsync(
      "UPDATE mutations SET attempts = attempts + 1, last_error = ? WHERE sequence = ?",
      message,
      sequence,
    );
  },
  async upsertRemote(item) {
    const db = await database();
    await db.runAsync(
      `INSERT INTO items (id, payload, updated_at, deleted_at, dirty)
       VALUES (?, ?, ?, ?, 0)
       ON CONFLICT(id) DO UPDATE SET payload = excluded.payload,
         updated_at = excluded.updated_at, deleted_at = excluded.deleted_at, dirty = 0`,
      item.id,
      JSON.stringify(item),
      item.updated_at,
      item.deleted_at,
    );
  },
  async hasPendingMutation(itemId) {
    const db = await database();
    return Boolean(await db.getFirstAsync("SELECT 1 FROM mutations WHERE item_id = ? LIMIT 1", itemId));
  },
  async getWatermark() {
    const db = await database();
    const row = await db.getFirstAsync<{ value: string }>("SELECT value FROM metadata WHERE key = 'sync_watermark'");
    return row?.value;
  },
  async setWatermark(value) {
    const db = await database();
    await db.runAsync(
      "INSERT INTO metadata (key, value) VALUES ('sync_watermark', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
      value,
    );
  },
};
