import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";

import { useAppState } from "@/src/app-state";
import { EmptyState, FilterPills, ItemRow, Page } from "@/src/components";
import { filterItems, tagsFromItems, uniqueTags, type SummaryFilter, type TypeFilter } from "@/src/item-filters";
import { SyncIndicator } from "@/src/sync-indicator";
import { colors, floatingActionShadow } from "@/src/theme";
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

export default function Home() {
  const { categories, items, refresh, sync, syncState } = useAppState();
  const params = useLocalSearchParams<{ category?: string; tag?: string; summary?: SummaryFilter; type?: ItemType }>();
  const [summary, setSummary] = useState<SummaryFilter>("saved");
  const [type, setType] = useState<TypeFilter>("all");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const reload = useCallback(async () => { await sync(); await refresh("", true); }, [refresh, sync]);

  useEffect(() => { void refresh("", true); }, [refresh]);
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
  const active = items.filter((item) => !item.is_archived);
  const counts = {
    saved: active.length,
    favorites: active.filter((item) => item.is_favorite).length,
    processing: active.filter((item) => ["pending", "processing"].includes(item.processing_status)).length,
    archived: items.filter((item) => item.is_archived).length,
  };
  const pills = [
    ...(summary !== "saved" ? [{ id: "summary", label: summaryLabels[summary], onRemove: () => setSummary("saved") }] : []),
    ...(type !== "all" ? [{ id: "type", label: typeOptions.find((option) => option.value === type)?.label ?? type, onRemove: () => setType("all") }] : []),
    ...(categoryId ? [{ id: "category", label: selectedCategory?.name ?? "Category", onRemove: () => setCategoryId(null) }] : []),
    ...tags.map((tag) => ({ id: `tag:${tag}`, label: `#${tag}`, onRemove: () => setTags(tags.filter((value) => value !== tag)) })),
  ];
  return (
    <Page>
      <View style={styles.toolbar}>
        <View>
          <Text style={styles.eyebrow}>YOUR KNOWLEDGE</Text>
          <Text style={styles.heading}>
            {visibleItems.length} {summary === "saved" ? "saved " : ""}{visibleItems.length === 1 ? "item" : "items"}
          </Text>
        </View>
        <SyncIndicator />
      </View>
      <View style={styles.filters}>
        <View style={styles.summaryGrid}>
          {([
            ["saved", "bookmark-outline"],
            ["favorites", "star-outline"],
            ["processing", "sparkles-outline"],
            ["archived", "archive-outline"],
          ] as [SummaryFilter, keyof typeof Ionicons.glyphMap][]).map(([value, icon]) => (
            <Pressable accessibilityRole="button" key={value} onPress={() => setSummary(value)} style={[styles.summaryButton, summary === value && styles.summaryButtonActive]}>
              <Ionicons color={summary === value ? colors.primary : colors.textMuted} name={icon} size={16} />
              <Text style={styles.summaryCount}>{counts[value]}</Text>
              <Text style={[styles.summaryLabel, summary === value && styles.summaryLabelActive]}>{summaryLabels[value]}</Text>
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
        <FilterPills pills={pills} onClear={pills.length ? () => { setSummary("saved"); setType("all"); setCategoryId(null); setTags([]); } : undefined} />
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
        ListEmptyComponent={<EmptyState body="Adjust the active filters or capture a new item." icon="bookmark-outline" title="No matching items" />}
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
  filters: { backgroundColor: colors.background, borderBottomColor: colors.border, borderBottomWidth: 1, gap: 12, padding: 14 },
  summaryGrid: { flexDirection: "row", gap: 8 },
  summaryButton: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, flex: 1, gap: 3, minHeight: 72, padding: 9 },
  summaryButtonActive: { backgroundColor: "#EAF8F5", borderColor: "#A7D9D0" },
  summaryCount: { color: colors.text, fontSize: 17, fontWeight: "800" },
  summaryLabel: { color: colors.textMuted, fontSize: 10, fontWeight: "800", textTransform: "uppercase" },
  summaryLabelActive: { color: colors.primary },
  segmented: { backgroundColor: colors.surfaceMuted, borderRadius: 7, flexDirection: "row", padding: 4 },
  segment: { alignItems: "center", borderRadius: 5, flex: 1, justifyContent: "center", minHeight: 36 },
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
  list: { padding: 16, paddingBottom: 100 },
  emptyList: { flexGrow: 1, justifyContent: "center" },
  separator: { height: 10 },
  fab: { ...floatingActionShadow, alignItems: "center", backgroundColor: colors.primary, borderRadius: 28, bottom: 20, height: 56, justifyContent: "center", position: "absolute", right: 20, width: 56 },
});
