import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

import type { Tokens } from "./types";

const ACCESS_KEY = "memoryhive.access-token";
const REFRESH_KEY = "memoryhive.refresh-token";
let accessToken: string | null = null;

function getValue(key: string) {
  if (Platform.OS === "web") return Promise.resolve(window.localStorage.getItem(key));
  return SecureStore.getItemAsync(key);
}

function setValue(key: string, value: string) {
  if (Platform.OS === "web") {
    window.localStorage.setItem(key, value);
    return Promise.resolve();
  }
  return SecureStore.setItemAsync(key, value);
}

function deleteValue(key: string) {
  if (Platform.OS === "web") {
    window.localStorage.removeItem(key);
    return Promise.resolve();
  }
  return SecureStore.deleteItemAsync(key);
}

export async function loadSession() {
  accessToken = await getValue(ACCESS_KEY);
  return Boolean(accessToken || (await getValue(REFRESH_KEY)));
}

export function currentAccessToken() {
  return accessToken;
}

export async function currentRefreshToken() {
  return getValue(REFRESH_KEY);
}

export async function saveSession(tokens: Tokens) {
  accessToken = tokens.access_token;
  await Promise.all([
    setValue(ACCESS_KEY, tokens.access_token),
    setValue(REFRESH_KEY, tokens.refresh_token),
  ]);
}

export async function clearSession() {
  accessToken = null;
  await Promise.all([
    deleteValue(ACCESS_KEY),
    deleteValue(REFRESH_KEY),
  ]);
}
