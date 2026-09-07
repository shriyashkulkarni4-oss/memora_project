import type { ChangePage, Item, ItemCreate, ItemUpdate, PendingMutation } from "./types";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

export interface SyncApi {
  create(payload: ItemCreate): Promise<Item>;
  uploadScreenshot(payload: ItemCreate, localUri: string): Promise<Item>;
  update(id: string, payload: ItemUpdate): Promise<Item>;
  remove(id: string): Promise<void>;
  get(id: string): Promise<Item>;
  changes(since?: string, cursor?: string): Promise<ChangePage>;
}

export interface SyncRepository {
  pendingMutations(): Promise<PendingMutation[]>;
  removeMutation(sequence: number): Promise<void>;
  failMutation(sequence: number, message: string): Promise<void>;
  upsertRemote(item: Item): Promise<void>;
  hasPendingMutation(itemId: string): Promise<boolean>;
  getWatermark(): Promise<string | undefined>;
  setWatermark(value: string): Promise<void>;
}

export interface SyncResult {
  pushed: number;
  pulled: number;
  conflicts: number;
}

async function pushMutation(
  mutation: PendingMutation,
  api: SyncApi,
): Promise<{ item?: Item; conflict: boolean }> {
  try {
    if (mutation.operation === "create") {
      return { item: await api.create(mutation.payload as ItemCreate), conflict: false };
    }
    if (mutation.operation === "screenshot") {
      if (!mutation.localUri) throw new Error("Screenshot file is no longer available");
      return {
        item: await api.uploadScreenshot(mutation.payload as ItemCreate, mutation.localUri),
        conflict: false,
      };
    }
    if (mutation.operation === "update") {
      return {
        item: await api.update(mutation.itemId, mutation.payload as ItemUpdate),
        conflict: false,
      };
    }
    await api.remove(mutation.itemId);
    return { conflict: false };
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    if (mutation.operation === "delete" && error.status === 404) return { conflict: false };
    if (error.status !== 409) throw error;

    const remote = await api.get(mutation.itemId);
    if (mutation.operation === "create" || mutation.operation === "screenshot") {
      return { item: remote, conflict: true };
    }
    const payload = mutation.payload as ItemUpdate;
    const item = await api.update(mutation.itemId, {
      ...payload,
      expected_revision: remote.revision,
    });
    return { item, conflict: true };
  }
}

export async function synchronize(
  repository: SyncRepository,
  api: SyncApi,
): Promise<SyncResult> {
  const result: SyncResult = { pushed: 0, pulled: 0, conflicts: 0 };
  const mutations = await repository.pendingMutations();

  for (const mutation of mutations) {
    try {
      const pushed = await pushMutation(mutation, api);
      if (pushed.item) await repository.upsertRemote(pushed.item);
      await repository.removeMutation(mutation.sequence);
      result.pushed += 1;
      if (pushed.conflict) result.conflicts += 1;
    } catch (error) {
      await repository.failMutation(
        mutation.sequence,
        error instanceof Error ? error.message : "Sync failed",
      );
      throw error;
    }
  }

  const since = await repository.getWatermark();
  let cursor: string | undefined;
  let serverTime: string | undefined;
  do {
    const page = await api.changes(since, cursor);
    serverTime = page.server_time;
    for (const item of page.items) {
      if (!(await repository.hasPendingMutation(item.id))) {
        await repository.upsertRemote(item);
        result.pulled += 1;
      }
    }
    cursor = page.has_more ? page.next_cursor ?? undefined : undefined;
  } while (cursor);

  if (serverTime) await repository.setWatermark(serverTime);
  return result;
}
