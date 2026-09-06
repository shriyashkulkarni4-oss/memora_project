import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import React, { useEffect, useMemo, useState } from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";

import { useAppState } from "@/src/app-state";
import { PrimaryButton } from "@/src/components";
import {
  countItemsInCategory,
  summarizeManagedTags,
  summarizeOrganization,
  type ManagedTagSummary,
} from "@/src/item-organization";
import { colors } from "@/src/theme";
import type { Category, ItemType } from "@/src/types";

const typeLabels: Record<ItemType, string> = {
  link: "Links",
  screenshot: "Screenshots",
  text: "Notes",
};

const categoryColors = ["#087F6D", "#2563EB", "#7C3AED", "#EA580C", "#CA8A04", "#BE123C"];

function StatTile({
  icon,
  label,
  value,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: number;
  onPress(): void;
}) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.statTile, pressed && styles.pressed]}>
      <Ionicons color={colors.primary} name={icon} size={20} />
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </Pressable>
  );
}

function CategoryRow({
  category,
  count,
  onDelete,
}: {
  category: Category;
  count: number;
  onDelete(): void;
}) {
  return (
    <View style={styles.managementRow}>
      <Pressable
        accessibilityRole="button"
        onPress={() => router.push({ pathname: "/(app)/home", params: { category: category.id } })}
        style={({ pressed }) => [styles.rowMain, pressed && styles.pressed]}
      >
        <View style={[styles.categorySwatch, { backgroundColor: category.color }]} />
        <View style={styles.grow}>
          <Text numberOfLines={1} style={styles.rowTitle}>{category.name}</Text>
          <Text numberOfLines={1} style={styles.secondary}>{category.description ?? "No description"}</Text>
        </View>
        <Text style={styles.rowCount}>{count}</Text>
      </Pressable>
      <Pressable accessibilityLabel={`Delete ${category.name}`} accessibilityRole="button" onPress={onDelete} style={styles.iconButton}>
        <Ionicons color={colors.danger} name="trash-outline" size={18} />
      </Pressable>
    </View>
  );
}

function TagRow({ tag, onDelete }: { tag: ManagedTagSummary; onDelete(): void }) {
  return (
    <View style={styles.managementRow}>
      <Pressable
        accessibilityRole="button"
        onPress={() => router.push({ pathname: "/(app)/home", params: { tag: tag.name } })}
        style={({ pressed }) => [styles.rowMain, pressed && styles.pressed]}
      >
        <View style={styles.tagIcon}><Ionicons color={tag.color} name="pricetag-outline" size={18} /></View>
        <View style={styles.grow}>
          <Text numberOfLines={1} style={styles.rowTitle}>#{tag.name}</Text>
          <Text style={styles.secondary}>{tag.count} {tag.count === 1 ? "item" : "items"}</Text>
        </View>
        <Ionicons color={colors.textMuted} name="chevron-forward" size={18} />
      </Pressable>
      {tag.managed ? (
        <Pressable accessibilityLabel={`Delete ${tag.name}`} accessibilityRole="button" onPress={onDelete} style={styles.iconButton}>
          <Ionicons color={colors.danger} name="trash-outline" size={18} />
        </Pressable>
      ) : null}
    </View>
  );
}

export default function Organize() {
  const {
    categories,
    createCategory,
    deleteCategory,
    deleteTag,
    items,
    refresh,
    refreshOrganization,
    tags,
  } = useAppState();
  const [categoryName, setCategoryName] = useState("");
  const [categoryColor, setCategoryColor] = useState(categoryColors[0]);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void refresh("", true);
    void refreshOrganization().catch((cause) => {
      setError(cause instanceof Error ? cause.message : "Unable to load organization data");
    });
  }, [refresh, refreshOrganization]);

  const summary = useMemo(() => summarizeOrganization(items), [items]);
  const tagRows = useMemo(() => summarizeManagedTags(items, tags), [items, tags]);
  const typeEntries = Object.entries(summary.byType) as [ItemType, number][];

  async function submitCategory() {
    const name = categoryName.trim();
    if (!name) {
      setError("Enter a category name.");
      return;
    }
    setCreating(true);
    setError("");
    try {
      await createCategory(name, categoryColor);
      setCategoryName("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to create category");
    } finally {
      setCreating(false);
    }
  }

  function confirmDeleteCategory(category: Category) {
    const count = Math.max(category.item_count, countItemsInCategory(items, category.id));
    Alert.alert(
      "Delete category?",
      `${category.name} will be removed from ${count} ${count === 1 ? "item" : "items"}. Items stay in your library.`,
      [
        { text: "Cancel", style: "cancel" },
        { text: "Delete", style: "destructive", onPress: () => void removeCategory(category.id) },
      ],
    );
  }

  async function removeCategory(categoryId: string) {
    setDeletingId(categoryId);
    setError("");
    try {
      await deleteCategory(categoryId);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to delete category");
    } finally {
      setDeletingId(null);
    }
  }

  function confirmDeleteTag(tag: ManagedTagSummary) {
    Alert.alert(
      "Delete tag?",
      `#${tag.name} will be removed from tagged items. Items stay in your library.`,
      [
        { text: "Cancel", style: "cancel" },
        { text: "Delete", style: "destructive", onPress: () => void removeTag(tag.id) },
      ],
    );
  }

  async function removeTag(tagId: string) {
    setDeletingId(tagId);
    setError("");
    try {
      await deleteTag(tagId);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to delete tag");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      <View style={styles.header}>
        <Text style={styles.eyebrow}>LIBRARY STRUCTURE</Text>
        <Text style={styles.heading}>Organize</Text>
        <Text style={styles.copy}>Browse and manage saved items by status, type, category, and tag.</Text>
      </View>

      <View style={styles.statsGrid}>
        <StatTile icon="bookmark-outline" label="Saved" value={summary.active} onPress={() => router.push({ pathname: "/(app)/home", params: { summary: "saved" } })} />
        <StatTile icon="star-outline" label="Favorites" value={summary.favorites} onPress={() => router.push({ pathname: "/(app)/home", params: { summary: "favorites" } })} />
        <StatTile icon="sparkles-outline" label="Processing" value={summary.processing} onPress={() => router.push({ pathname: "/(app)/home", params: { summary: "processing" } })} />
        <StatTile icon="archive-outline" label="Archived" value={summary.archived} onPress={() => router.push({ pathname: "/(app)/home", params: { summary: "archived" } })} />
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Ionicons color={colors.primary} name="albums-outline" size={19} />
          <Text style={styles.sectionTitle}>Types</Text>
        </View>
        <View style={styles.typeGrid}>
          {typeEntries.map(([type, count]) => (
            <Pressable
              accessibilityRole="button"
              key={type}
              onPress={() => router.push({ pathname: "/(app)/home", params: { type } })}
              style={({ pressed }) => [styles.typeRow, pressed && styles.pressed]}
            >
              <Text style={styles.typeName}>{typeLabels[type]}</Text>
              <Text style={styles.typeCount}>{count}</Text>
            </Pressable>
          ))}
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Ionicons color={colors.primary} name="folder-open-outline" size={19} />
          <Text style={styles.sectionTitle}>Categories</Text>
          <Text style={styles.sectionCount}>{categories.length}</Text>
        </View>
        <View style={styles.createPanel}>
          <TextInput
            accessibilityLabel="Category name"
            maxLength={100}
            onChangeText={setCategoryName}
            placeholder="New category"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
            value={categoryName}
          />
          <View style={styles.colorRail}>
            {categoryColors.map((option) => (
              <Pressable
                accessibilityLabel={`Use category color ${option}`}
                accessibilityRole="button"
                key={option}
                onPress={() => setCategoryColor(option)}
                style={[styles.colorChoice, categoryColor === option && styles.colorChoiceActive]}
              >
                <View style={[styles.colorDot, { backgroundColor: option }]} />
              </Pressable>
            ))}
          </View>
          <PrimaryButton
            disabled={!categoryName.trim()}
            icon="add-outline"
            label="Add category"
            loading={creating}
            onPress={() => void submitCategory()}
          />
        </View>
        {categories.length ? (
          <View style={styles.managementList}>
            {categories.map((category) => (
              <CategoryRow
                category={category}
                count={Math.max(category.item_count, countItemsInCategory(items, category.id))}
                key={category.id}
                onDelete={() => confirmDeleteCategory(category)}
              />
            ))}
          </View>
        ) : (
          <Text style={styles.emptyText}>Categories appear here after you create them.</Text>
        )}
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Ionicons color={colors.primary} name="pricetags-outline" size={19} />
          <Text style={styles.sectionTitle}>Tags</Text>
          <Text style={styles.sectionCount}>{tagRows.length}</Text>
        </View>
        {tagRows.length ? (
          <View style={styles.managementList}>
            {tagRows.map((tag) => (
              <TagRow key={tag.id} tag={tag} onDelete={() => confirmDeleteTag(tag)} />
            ))}
          </View>
        ) : (
          <Text style={styles.emptyText}>Tags appear here after you add them while capturing or editing items.</Text>
        )}
      </View>

      {deletingId ? <Text style={styles.status}>Updating organization...</Text> : null}
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { gap: 18, padding: 18, paddingBottom: 92 },
  header: { gap: 4 },
  eyebrow: { color: colors.primary, fontSize: 11, fontWeight: "800" },
  heading: { color: colors.text, fontSize: 24, fontWeight: "800" },
  copy: { color: colors.textMuted, fontSize: 14, lineHeight: 20 },
  statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 9 },
  statTile: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, flexBasis: "48%", flexGrow: 1, gap: 4, minHeight: 96, padding: 13 },
  statValue: { color: colors.text, fontSize: 22, fontWeight: "800" },
  statLabel: { color: colors.textMuted, fontSize: 11, fontWeight: "800", textTransform: "uppercase" },
  section: { gap: 10 },
  sectionHeader: { alignItems: "center", flexDirection: "row", gap: 8, marginTop: 5 },
  sectionTitle: { color: colors.text, fontSize: 16, fontWeight: "800" },
  sectionCount: { color: colors.textMuted, fontSize: 12, fontWeight: "700", marginLeft: "auto" },
  typeGrid: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, overflow: "hidden" },
  typeRow: { alignItems: "center", borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: "row", minHeight: 50, paddingHorizontal: 14 },
  typeName: { color: colors.text, flex: 1, fontSize: 14, fontWeight: "700" },
  typeCount: { color: colors.textMuted, fontSize: 14, fontWeight: "800" },
  createPanel: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, gap: 10, padding: 12 },
  input: { backgroundColor: colors.background, borderColor: colors.border, borderRadius: 7, borderWidth: 1, color: colors.text, fontSize: 16, minHeight: 46, paddingHorizontal: 12 },
  colorRail: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  colorChoice: { alignItems: "center", borderColor: colors.border, borderRadius: 7, borderWidth: 1, height: 34, justifyContent: "center", width: 34 },
  colorChoiceActive: { backgroundColor: "#EAF8F5", borderColor: "#A7D9D0" },
  colorDot: { borderRadius: 7, height: 16, width: 16 },
  managementList: { gap: 9 },
  managementRow: { alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, flexDirection: "row", gap: 8, minHeight: 62, paddingHorizontal: 8 },
  rowMain: { alignItems: "center", flex: 1, flexDirection: "row", gap: 12, minHeight: 60, paddingVertical: 9 },
  categorySwatch: { borderRadius: 6, height: 34, width: 34 },
  tagIcon: { alignItems: "center", backgroundColor: "#EAF8F5", borderRadius: 7, height: 38, justifyContent: "center", width: 38 },
  rowTitle: { color: colors.text, fontSize: 15, fontWeight: "800" },
  secondary: { color: colors.textMuted, fontSize: 12 },
  rowCount: { color: colors.textMuted, fontSize: 13, fontWeight: "800", minWidth: 24, textAlign: "right" },
  iconButton: { alignItems: "center", height: 44, justifyContent: "center", width: 42 },
  grow: { flex: 1, gap: 2 },
  emptyText: { color: colors.textMuted, fontSize: 13, lineHeight: 19 },
  status: { color: colors.textMuted, fontSize: 13, textAlign: "center" },
  error: { color: colors.danger, fontSize: 14 },
  pressed: { opacity: 0.72 },
});
