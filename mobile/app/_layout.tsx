import { Stack } from "expo-router";
import { ShareIntentProvider } from "expo-share-intent";
import { StatusBar } from "expo-status-bar";
import React from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AppStateProvider } from "@/src/app-state";
import { colors } from "@/src/theme";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ShareIntentProvider>
        <AppStateProvider>
          <StatusBar style="dark" />
          <Stack screenOptions={{ contentStyle: { backgroundColor: colors.background }, headerShadowVisible: false }}>
            <Stack.Screen name="index" options={{ headerShown: false }} />
            <Stack.Screen name="(auth)" options={{ headerShown: false }} />
            <Stack.Screen name="(app)" options={{ headerShown: false }} />
            <Stack.Screen name="item/[id]" options={{ title: "Item", headerBackTitle: "Library" }} />
          </Stack>
        </AppStateProvider>
      </ShareIntentProvider>
    </SafeAreaProvider>
  );
}
