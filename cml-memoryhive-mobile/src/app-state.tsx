import NetInfo from "@react-native-community/netinfo";
import { router } from "expo-router";
import React, { createContext, use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { View } from "react-native";

import { accountApi, authApi, categoriesApi, syncApi, tagsApi } from "./api";
import {
  captureLocal,
  clearLocalCategory,
  clearLocalData,
  deleteLocal,
  getLocal,
  initializeDatabase,
  listLocal,
  prepareLocalDataForUser,
  removeLocalTag,
  sqliteSyncRepository,
  updateLocal,
} from "./database";
import { clearSession, loadSession } from "./session";
import { ApiError, synchronize } from "./sync";
import type { Category, Item, ItemCreate, ItemUpdate, ManagedTag, User } from "./types";

type SyncState = "offline" | "idle" | "syncing" | "error";

interface AppContextValue {
  ready: boolean;
  user: User | null;
  items: Item[];
  categories: Category[];
  tags: ManagedTag[];
  syncState: SyncState;
  syncMessage: string;
  refresh(search?: string, includeArchived?: boolean): Promise<void>;
  refreshOrganization(): Promise<void>;
  sync(): Promise<void>;
  login(email: string, password: string): Promise<void>;
  register(name: string, email: string, password: string): Promise<void>;
  logout(): Promise<void>;
  changePassword(currentPassword: string, newPassword: string): Promise<void>;
  exportAccount(): Promise<{ filename: string; uri?: string }>;
  deleteAccount(password: string): Promise<void>;
  capture(payload: ItemCreate, localUri?: string): Promise<Item>;
  update(id: string, payload: ItemUpdate): Promise<Item>;
  remove(id: string): Promise<void>;
  createCategory(name: string, color: string): Promise<Category>;
  deleteCategory(id: string): Promise<void>;
  deleteTag(id: string): Promise<void>;
  get(id: string): Promise<Item | undefined>;
}

const AppContext = createContext<AppContextValue | null>(null);
const IDLE_REFRESH_MS = 60_000;
const IDLE_LOGOUT_MS = 10 * 60_000;

export function AppStateProvider({ children }: React.PropsWithChildren) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<ManagedTag[]>([]);
  const [syncState, setSyncState] = useState<SyncState>("idle");
  const [syncMessage, setSyncMessage] = useState("Up to date");
  const lastActivity = useRef<number | null>(null);

  const markActive = useCallback(() => {
    lastActivity.current = Date.now();
  }, []);

  const refresh = useCallback(async (search = "", includeArchived = false) => {
    setItems(await listLocal(search, includeArchived));
  }, []);

  const refreshOrganization = useCallback(async () => {
    const [nextCategories, nextTags] = await Promise.all([
      categoriesApi.list(),
      tagsApi.list(),
    ]);
    setCategories(nextCategories);
    setTags(nextTags);
  }, []);

  const forceLogout = useCallback(async (message: string, revokeServerSession = false) => {
    if (revokeServerSession) await authApi.logout();
    else await clearSession();
    await clearLocalData();
    setItems([]);
    setCategories([]);
    setTags([]);
    setUser(null);
    setSyncState("idle");
    setSyncMessage(message);
    router.replace({ pathname: "/(auth)/login", params: { notice: message } });
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
      await refreshOrganization();
      setSyncState("idle");
      setSyncMessage(
        result.pushed || result.pulled ? `${result.pushed + result.pulled} changes synced` : "Up to date",
      );
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        await forceLogout("Your session expired. Sign in again.");
        return;
      }
      const message = error instanceof Error ? error.message : "Sync failed";
      const networkFailure = /failed to fetch|network request failed/i.test(message);
      setSyncState(networkFailure ? "offline" : "error");
      setSyncMessage(networkFailure ? "Saved offline" : message);
    }
  }, [forceLogout, refresh, refreshOrganization]);

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
          await forceLogout("Your session expired. Sign in again.");
        }
      }
      setReady(true);
    })();
  }, [forceLogout, refresh, sync]);

  useEffect(() => {
    return NetInfo.addEventListener((state) => {
      if (state.isConnected && user) void sync();
      if (!state.isConnected) {
        setSyncState("offline");
        setSyncMessage("Saved offline");
      }
    });
  }, [sync, user]);

  useEffect(() => {
    if (!user) return undefined;
    lastActivity.current = Date.now();
    const timer = setInterval(() => {
      if (lastActivity.current === null) return;
      const idleFor = Date.now() - lastActivity.current;
      if (idleFor >= IDLE_LOGOUT_MS) {
        void forceLogout("Signed out after 10 minutes of inactivity.");
        return;
      }
      if (idleFor >= IDLE_REFRESH_MS) void sync();
    }, IDLE_REFRESH_MS);
    return () => clearInterval(timer);
  }, [forceLogout, sync, user]);

  const value = useMemo<AppContextValue>(() => ({
    ready,
    user,
    items,
    categories,
    tags,
    syncState,
    syncMessage,
    refresh,
    refreshOrganization,
    sync,
    async login(email, password) {
      const authenticatedUser = await authApi.login({ email, password });
      markActive();
      await prepareLocalDataForUser(authenticatedUser.id);
      setUser(authenticatedUser);
      await sync();
    },
    async register(name, email, password) {
      await authApi.register({ name, email, password });
      const authenticatedUser = await authApi.login({ email, password });
      markActive();
      await prepareLocalDataForUser(authenticatedUser.id);
      setUser(authenticatedUser);
      await sync();
    },
    async logout() {
      await forceLogout("Signed out.", true);
    },
    async changePassword(currentPassword, newPassword) {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      await forceLogout("Password changed successfully. Sign in with your new password.");
    },
    async exportAccount() {
      markActive();
      await sync();
      return accountApi.exportData();
    },
    async deleteAccount(password) {
      markActive();
      await accountApi.remove(password);
      await forceLogout("Account deleted.");
    },
    async capture(payload, localUri) {
      markActive();
      const item = await captureLocal(payload, localUri);
      await refresh();
      void sync();
      return item;
    },
    async update(id, payload) {
      markActive();
      const item = await updateLocal(id, payload);
      await refresh();
      void sync();
      return item;
    },
    async remove(id) {
      markActive();
      await deleteLocal(id);
      await refresh();
      void sync();
    },
    async createCategory(name, color) {
      markActive();
      const category = await categoriesApi.create({ name: name.trim(), color, icon: "folder" });
      setCategories((current) => [...current, category].sort((left, right) => left.name.localeCompare(right.name)));
      return category;
    },
    async deleteCategory(id) {
      markActive();
      await categoriesApi.remove(id);
      await clearLocalCategory(id);
      setCategories((current) => current.filter((category) => category.id !== id));
      await refresh("", true);
    },
    async deleteTag(id) {
      markActive();
      const tag = tags.find((candidate) => candidate.id === id);
      await tagsApi.remove(id);
      await removeLocalTag(id, tag?.name);
      setTags((current) => current.filter((candidate) => candidate.id !== id));
      await refresh("", true);
    },
    get: getLocal,
  }), [
    categories,
    forceLogout,
    items,
    markActive,
    ready,
    refresh,
    refreshOrganization,
    sync,
    syncMessage,
    syncState,
    tags,
    user,
  ]);

  return (
    <AppContext value={value}>
      <View onTouchStart={markActive} style={{ flex: 1 }}>
        {children}
      </View>
    </AppContext>
  );
}

export function useAppState() {
  const value = use(AppContext);
  if (!value) throw new Error("useAppState must be used within AppStateProvider");
  return value;
}
