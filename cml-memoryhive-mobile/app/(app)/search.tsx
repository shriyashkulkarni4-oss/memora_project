import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import React, { useEffect, useMemo, useState } from "react";
import { FlatList, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { useAppState } from "@/src/app-state";
import { EmptyState, FilterPills, ItemRow, Page } from "@/src/components";
import { filterItems, tagsFromItems, uniqueTags, type SummaryFilter, type TypeFilter } from "@/src/item-filters";
import { colors } from "@/src/theme";
import type { ItemType } from "@/src/types";

const typeOptions: { value: TypeFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "link", label: "Links" },
  { value: "screenshot", label: "Images" },
  { value: "text", label: "Notes" },
];

const summaryLabels: Record<SummaryFilter, string> = {
  saved: "Saved",
  favorites: "Favorites",
  processing: "Processing",
  archived: "Archived",
};

export default function Search() {
  const { categories, items, refresh } = useAppState();
  const params = useLocalSearchParams<{ category?: string; tag?: string; summary?: SummaryFilter; type?: ItemType }>();
  const [query, setQuery] = useState("");
  const [summary, setSummary] = useState<SummaryFilter>("saved");
  const [type, setType] = useState<TypeFilter>("all");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  useEffect(() => { void refresh(query, true); }, [query, refresh]);
  useEffect(() => () => { void refresh(); }, [refresh]);
  useEffect(() => {
    const timer = setTimeout(() => {
      if (params.tag) setTags((current) => uniqueTags([...current, params.tag!]));
      if (params.category) setCategoryId(params.category);
      if (params.summary && params.summary in summaryLabels) setSummary(params.summary);
      if (params.type) setType(params.type);
    }, 0);
    return () => clearTimeout(timer);
  }, [params.category, params.summary, params.tag, params.type]);

  const visibleItems = useMemo(() => filterItems(items, { summary, type, categoryId, tags }), [categoryId, items, summary, tags, type]);
  const availableTags = useMemo(() => tagsFromItems(items), [items]);
  const selectedCategory = useMemo(
    () => categories.find((category) => category.id === categoryId),
    [categories, categoryId],
  );
  const pills = [
    ...(query.trim() ? [{ id: "query", label: `Search: ${query.trim()}`, onRemove: () => setQuery("") }] : []),
    ...(summary !== "saved" ? [{ id: "summary", label: summaryLabels[summary], onRemove: () => setSummary("saved") }] : []),
    ...(type !== "all" ? [{ id: "type", label: typeOptions.find((option) => option.value === type)?.label ?? type, onRemove: () => setType("all") }] : []),
    ...(categoryId ? [{ id: "category", label: selectedCategory?.name ?? "Category", onRemove: () => setCategoryId(null) }] : []),
    ...tags.map((tag) => ({ id: `tag:${tag}`, label: `#${tag}`, onRemove: () => setTags(tags.filter((value) => value !== tag)) })),
  ];
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
      <View style={styles.filters}>
        <View accessibilityRole="tablist" style={styles.segmented}>
          {(["saved", "favorites", "archived"] as SummaryFilter[]).map((value) => (
            <Pressable accessibilityRole="tab" accessibilityState={{ selected: summary === value }} key={value} onPress={() => setSummary(value)} style={[styles.segment, summary === value && styles.segmentActive]}>
              <Text style={[styles.segmentText, summary === value && styles.segmentTextActive]}>{summaryLabels[value]}</Text>
            </Pressable>
          ))}
        </View>
        <View accessibilityRole="tablist" style={styles.segmented}>
          {typeOptions.map((option) => (
            <Pressable accessibilityRole="tab" accessibilityState={{ selected: type === option.value }} key={option.value} onPress={() => setType(option.value)} style={[styles.segment, type === option.value && styles.segmentActive]}>
              <Text style={[styles.segmentText, type === option.value && styles.segmentTextActive]}>{option.label}</Text>
            </Pressable>
          ))}
        </View>
        <FilterPills pills={pills} onClear={pills.length ? () => { setQuery(""); setSummary("saved"); setType("all"); setCategoryId(null); setTags([]); } : undefined} />
        {categories.length ? (
          <View style={styles.categoryRail}>
            {categories.slice(0, 8).map((category) => (
              <Pressable accessibilityRole="button" key={category.id} onPress={() => setCategoryId(category.id)} style={styles.categoryButton}>
                <View style={[styles.categorySwatch, { backgroundColor: category.color }]} />
                <Text numberOfLines={1} style={styles.categoryButtonText}>{category.name}</Text>
              </Pressable>
            ))}
          </View>
        ) : null}
        {availableTags.length ? (
          <View style={styles.tagRail}>
            {availableTags.slice(0, 8).map((tag) => (
              <Pressable accessibilityRole="button" key={tag} onPress={() => setTags((current) => uniqueTags([...current, tag]))} style={styles.tagButton}>
                <Text style={styles.tagButtonText}>#{tag}</Text>
              </Pressable>
            ))}
          </View>
        ) : null}
      </View>
      <FlatList
        contentContainerStyle={[styles.list, !visibleItems.length && styles.emptyList]}
        data={visibleItems}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <ItemRow item={item} />}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        keyboardShouldPersistTaps="handled"
        ListEmptyComponent={<EmptyState body={query ? "Try a broader title, URL, note, or tag." : "Search works against your on-device library without a connection."} icon="search-outline" title={query || pills.length ? "No matches" : "Search offline"} />}
      />
    </Page>
  );
}

const styles = StyleSheet.create({
  search: { alignItems: "center", backgroundColor: colors.surface, borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: "row", gap: 9, paddingHorizontal: 17, paddingVertical: 10 },
  input: { color: colors.text, flex: 1, fontSize: 16, minHeight: 42 },
  filters: { borderBottomColor: colors.border, borderBottomWidth: 1, gap: 10, padding: 14 },
  segmented: { backgroundColor: colors.surfaceMuted, borderRadius: 7, flexDirection: "row", padding: 4 },
  segment: { alignItems: "center", borderRadius: 5, flex: 1, justifyContent: "center", minHeight: 34 },
  segmentActive: { backgroundColor: colors.surface },
  segmentText: { color: colors.textMuted, fontSize: 12, fontWeight: "700" },
  segmentTextActive: { color: colors.primary },
  tagRail: { flexDirection: "row", flexWrap: "wrap", gap: 7 },
  categoryRail: { flexDirection: "row", flexWrap: "wrap", gap: 7 },
  categoryButton: { alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 6, borderWidth: 1, flexDirection: "row", gap: 6, maxWidth: "48%", minHeight: 31, paddingHorizontal: 9 },
  categorySwatch: { borderRadius: 4, height: 12, width: 12 },
  categoryButtonText: { color: colors.textMuted, flexShrink: 1, fontSize: 12, fontWeight: "700" },
  tagButton: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 6, borderWidth: 1, minHeight: 29, justifyContent: "center", paddingHorizontal: 9 },
  tagButtonText: { color: colors.textMuted, fontSize: 12, fontWeight: "700" },
  list: { padding: 16, paddingBottom: 80 },
  emptyList: { flexGrow: 1, justifyContent: "center" },
  separator: { height: 10 },
});
