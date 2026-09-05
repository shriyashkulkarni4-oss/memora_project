import NetInfo from "@react-native-community/netinfo";
import { router } from "expo-router";
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { authApi, syncApi } from "./api";
import {
  captureLocal,
  clearLocalData,
  deleteLocal,
  getLocal,
  initializeDatabase,
  listLocal,
  prepareLocalDataForUser,
  sqliteSyncRepository,
  updateLocal,
} from "./database";
import { clearSession, loadSession } from "./session";
import { synchronize } from "./sync";
import type { Item, ItemCreate, ItemUpdate, User } from "./types";

type SyncState = "offline" | "idle" | "syncing" | "error";

interface AppContextValue {
  ready: boolean;
  user: User | null;
  items: Item[];
  syncState: SyncState;
  syncMessage: string;
  refresh(search?: string): Promise<void>;
  sync(): Promise<void>;
  login(email: string, password: string): Promise<void>;
  register(name: string, email: string, password: string): Promise<void>;
  logout(): Promise<void>;
  capture(payload: ItemCreate, localUri?: string): Promise<Item>;
  update(id: string, payload: ItemUpdate): Promise<Item>;
  remove(id: string): Promise<void>;
  get(id: string): Promise<Item | undefined>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppStateProvider({ children }: React.PropsWithChildren) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [syncState, setSyncState] = useState<SyncState>("idle");
  const [syncMessage, setSyncMessage] = useState("Up to date");

  const refresh = useCallback(async (search = "") => {
    setItems(await listLocal(search));
  }, []);

  const sync = useCallback(async () => {
    const network = await NetInfo.fetch();
    if (!network.isConnected) {
      setSyncState("offline");
      setSyncMessage("Saved offline");
      return;
    }
    setSyncState("syncing");
    setSyncMessage("Syncing");
    try {
      const result = await synchronize(sqliteSyncRepository, syncApi);
      await refresh();
      setSyncState("idle");
      setSyncMessage(
        result.pushed || result.pulled ? `${result.pushed + result.pulled} changes synced` : "Up to date",
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Sync failed";
      const networkFailure = /failed to fetch|network request failed/i.test(message);
      setSyncState(networkFailure ? "offline" : "error");
      setSyncMessage(networkFailure ? "Saved offline" : message);
    }
  }, [refresh]);

  useEffect(() => {
    void (async () => {
      await initializeDatabase();
      await refresh();
      if (await loadSession()) {
        try {
          const restoredUser = await authApi.me();
          await prepareLocalDataForUser(restoredUser.id);
          setUser(restoredUser);
          await sync();
        } catch {
          await clearSession();
        }
      }
      setReady(true);
    })();
  }, [refresh, sync]);

  useEffect(() => {
    return NetInfo.addEventListener((state) => {
      if (state.isConnected && user) void sync();
      if (!state.isConnected) {
        setSyncState("offline");
        setSyncMessage("Saved offline");
      }
    });
  }, [sync, user]);

  const value = useMemo<AppContextValue>(() => ({
    ready,
    user,
    items,
    syncState,
    syncMessage,
    refresh,
    sync,
    async login(email, password) {
      const authenticatedUser = await authApi.login({ email, password });
      await prepareLocalDataForUser(authenticatedUser.id);
      setUser(authenticatedUser);
      await sync();
    },
    async register(name, email, password) {
      await authApi.register({ name, email, password });
      const authenticatedUser = await authApi.login({ email, password });
      await prepareLocalDataForUser(authenticatedUser.id);
      setUser(authenticatedUser);
      await sync();
    },
    async logout() {
      await authApi.logout();
      await clearLocalData();
      setItems([]);
      setUser(null);
      router.replace("/(auth)/login");
    },
    async capture(payload, localUri) {
      const item = await captureLocal(payload, localUri);
      await refresh();
      void sync();
      return item;
    },
    async update(id, payload) {
      const item = await updateLocal(id, payload);
      await refresh();
      void sync();
      return item;
    },
    async remove(id) {
      await deleteLocal(id);
      await refresh();
      void sync();
    },
    get: getLocal,
  }), [items, ready, refresh, sync, syncMessage, syncState, user]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppState() {
  const value = useContext(AppContext);
  if (!value) throw new Error("useAppState must be used within AppStateProvider");
  return value;
}
