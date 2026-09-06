import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import React from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { useAppState } from "@/src/app-state";
import { colors } from "@/src/theme";

export default function AppLayout() {
  const { ready, user } = useAppState();
  if (!ready) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }
  if (ready && !user) return <Redirect href="/(auth)/login" />;
  return (
    <Tabs
      screenOptions={{
        headerShadowVisible: false,
        headerStyle: { backgroundColor: colors.background },
        headerTitleStyle: { color: colors.text, fontWeight: "700" },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border, height: 62, paddingBottom: 7, paddingTop: 5 },
      }}
    >
      <Tabs.Screen name="home" options={{ title: "Library", tabBarIcon: ({ color, size }) => <Ionicons color={color} name="library-outline" size={size} /> }} />
      <Tabs.Screen name="search" options={{ title: "Search", tabBarIcon: ({ color, size }) => <Ionicons color={color} name="search-outline" size={size} /> }} />
      <Tabs.Screen name="organize" options={{ title: "Organize", tabBarIcon: ({ color, size }) => <Ionicons color={color} name="pricetags-outline" size={size} /> }} />
      <Tabs.Screen name="capture" options={{ title: "Capture", tabBarIcon: ({ color, size }) => <Ionicons color={color} name="add-circle-outline" size={size} /> }} />
      <Tabs.Screen name="settings" options={{ title: "Settings", tabBarIcon: ({ color, size }) => <Ionicons color={color} name="settings-outline" size={size} /> }} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  loading: {
    alignItems: "center",
    backgroundColor: colors.background,
    flex: 1,
    justifyContent: "center",
  },
});
