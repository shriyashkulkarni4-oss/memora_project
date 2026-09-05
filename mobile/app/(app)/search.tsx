import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useState } from "react";
import { FlatList, StyleSheet, TextInput, View } from "react-native";

import { useAppState } from "@/src/app-state";
import { EmptyState, ItemRow, Page } from "@/src/components";
import { colors } from "@/src/theme";

export default function Search() {
  const { items, refresh } = useAppState();
  const [query, setQuery] = useState("");
  useEffect(() => { void refresh(query); }, [query, refresh]);
  useEffect(() => () => { void refresh(); }, [refresh]);
  return (
    <Page>
      <View style={styles.search}>
        <Ionicons color={colors.textMuted} name="search" size={20} />
        <TextInput
          accessibilityLabel="Search saved items"
          autoCapitalize="none"
          autoFocus
          onChangeText={setQuery}
          placeholder="Search titles, text, URLs, and tags"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          value={query}
        />
        {query ? <Ionicons color={colors.textMuted} name="close-circle" onPress={() => setQuery("")} size={20} /> : null}
      </View>
      <FlatList
        contentContainerStyle={[styles.list, !items.length && styles.emptyList]}
        data={items}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <ItemRow item={item} />}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        keyboardShouldPersistTaps="handled"
        ListEmptyComponent={<EmptyState body={query ? "Try a broader title, URL, note, or tag." : "Search works against your on-device library without a connection."} icon="search-outline" title={query ? "No matches" : "Search offline"} />}
      />
    </Page>
  );
}

const styles = StyleSheet.create({
  search: { alignItems: "center", backgroundColor: colors.surface, borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: "row", gap: 9, paddingHorizontal: 17, paddingVertical: 10 },
  input: { color: colors.text, flex: 1, fontSize: 16, minHeight: 42 },
  list: { padding: 16, paddingBottom: 80 },
  emptyList: { flexGrow: 1, justifyContent: "center" },
  separator: { height: 10 },
});
