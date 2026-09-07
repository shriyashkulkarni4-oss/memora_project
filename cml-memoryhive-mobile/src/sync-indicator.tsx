import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";

import { useAppState } from "./app-state";
import { colors } from "./theme";

export function SyncIndicator() {
  const { sync, syncMessage, syncState } = useAppState();
  return (
    <Pressable accessibilityLabel="Sync now" onPress={() => void sync()} style={styles.wrap}>
      {syncState === "syncing" ? (
        <ActivityIndicator color={colors.primary} size="small" />
      ) : (
        <Ionicons
          color={syncState === "error" ? colors.danger : syncState === "offline" ? colors.warning : colors.primary}
          name={syncState === "offline" ? "cloud-offline-outline" : syncState === "error" ? "alert-circle-outline" : "cloud-done-outline"}
          size={17}
        />
      )}
      <Text numberOfLines={1} style={styles.text}>{syncMessage}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: "center", flexDirection: "row", gap: 6, maxWidth: 155 },
  text: { color: colors.textMuted, fontSize: 12, fontWeight: "600" },
});
