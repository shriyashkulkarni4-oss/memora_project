import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import React, { useCallback } from "react";
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";

import { useAppState } from "@/src/app-state";
import { EmptyState, ItemRow, Page } from "@/src/components";
import { SyncIndicator } from "@/src/sync-indicator";
import { colors } from "@/src/theme";

export default function Home() {
  const { items, refresh, sync, syncState } = useAppState();
  const reload = useCallback(async () => { await refresh(); await sync(); }, [refresh, sync]);
  return (
    <Page>
      <View style={styles.toolbar}>
        <View>
          <Text style={styles.eyebrow}>YOUR KNOWLEDGE</Text>
          <Text style={styles.heading}>{items.length} saved {items.length === 1 ? "item" : "items"}</Text>
        </View>
        <SyncIndicator />
      </View>
      <FlatList
        contentContainerStyle={[styles.list, !items.length && styles.emptyList]}
        data={items}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <ItemRow item={item} />}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        ListEmptyComponent={<EmptyState body="Capture a link, screenshot, or note. It remains available even when you are offline." icon="bookmark-outline" title="Your library is empty" />}
        refreshControl={<RefreshControl onRefresh={() => void reload()} refreshing={syncState === "syncing"} tintColor={colors.primary} />}
      />
      <Pressable accessibilityLabel="Capture an item" onPress={() => router.push("/(app)/capture")} style={styles.fab}>
        <Ionicons color="#FFFFFF" name="add" size={28} />
      </Pressable>
    </Page>
  );
}

const styles = StyleSheet.create({
  toolbar: { alignItems: "center", borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingHorizontal: 18, paddingVertical: 14 },
  eyebrow: { color: colors.primary, fontSize: 11, fontWeight: "800" },
  heading: { color: colors.text, fontSize: 19, fontWeight: "700", marginTop: 3 },
  list: { padding: 16, paddingBottom: 100 },
  emptyList: { flexGrow: 1, justifyContent: "center" },
  separator: { height: 10 },
  fab: { alignItems: "center", backgroundColor: colors.primary, borderRadius: 28, bottom: 20, elevation: 5, height: 56, justifyContent: "center", position: "absolute", right: 20, shadowColor: colors.text, shadowOffset: { height: 3, width: 0 }, shadowOpacity: 0.2, shadowRadius: 5, width: 56 },
});
