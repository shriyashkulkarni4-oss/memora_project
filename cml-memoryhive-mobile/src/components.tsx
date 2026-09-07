import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import React from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  type TextInputProps,
  View,
  type ViewStyle,
} from "react-native";

import { colors, shadow } from "./theme";
import type { Category, Item } from "./types";
import { normalizeTag, uniqueTags } from "./item-filters";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <View style={styles.brand}>
      <View style={styles.brandMark}>
        <Ionicons name="bookmark" size={compact ? 17 : 22} color="#FFFFFF" />
      </View>
      <Text style={[styles.brandText, compact && styles.brandTextCompact]}>Memoryhive</Text>
    </View>
  );
}

export function Field({ label, ...props }: TextInputProps & { label: string }) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        placeholderTextColor={colors.textMuted}
        style={[styles.field, props.multiline && styles.fieldMultiline]}
        {...props}
      />
    </View>
  );
}

export function PrimaryButton({
  label,
  icon,
  loading,
  onPress,
  onPressIn,
  danger = false,
  disabled = false,
}: {
  label: string;
  icon?: keyof typeof Ionicons.glyphMap;
  loading?: boolean;
  onPress(): void;
  onPressIn?: () => void;
  danger?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled || loading}
      onPress={onPress}
      onPressIn={onPressIn}
      style={({ pressed }) => [
        styles.primaryButton,
        danger && styles.dangerButton,
        (disabled || loading) && styles.disabled,
        pressed && styles.pressed,
      ]}
    >
      {loading ? <ActivityIndicator color="#FFFFFF" /> : icon ? <Ionicons name={icon} size={19} color="#FFFFFF" /> : null}
      <Text style={styles.primaryLabel}>{label}</Text>
    </Pressable>
  );
}

export function EmptyState({ icon, title, body }: { icon: keyof typeof Ionicons.glyphMap; title: string; body: string }) {
  return (
    <View style={styles.empty}>
      <Ionicons name={icon} size={36} color={colors.primary} />
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyBody}>{body}</Text>
    </View>
  );
}

export function FilterPills({
  pills,
  onClear,
}: {
  pills: { id: string; label: string; onRemove(): void }[];
  onClear?: () => void;
}) {
  if (!pills.length) return null;
  return (
    <View style={styles.filterPills}>
      {pills.map((pill) => (
        <Pressable accessibilityRole="button" key={pill.id} onPress={pill.onRemove} style={styles.filterPill}>
          <Text style={styles.filterPillText}>{pill.label}</Text>
          <Ionicons color={colors.primaryDark} name="close" size={14} />
        </Pressable>
      ))}
      {onClear ? (
        <Pressable accessibilityRole="button" onPress={onClear} style={styles.clearPill}>
          <Text style={styles.clearPillText}>Clear all</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

export function TagPicker({
  selected,
  available,
  onChange,
  onInputChange,
  placeholder = "Search or add tag",
}: {
  selected: string[];
  available: string[];
  onChange(tags: string[]): void;
  onInputChange?: (value: string) => void;
  placeholder?: string;
}) {
  const [input, setInput] = React.useState("");
  const selectedSet = React.useMemo(() => new Set(selected.map(normalizeTag)), [selected]);
  const query = normalizeTag(input);
  const suggestions = React.useMemo(() => available
    .filter((tag) => !selectedSet.has(normalizeTag(tag)))
    .filter((tag) => !query || tag.includes(query))
    .slice(0, 8), [available, query, selectedSet]);
  const addTags = React.useCallback((raw: string) => {
    const next = uniqueTags([...selected, ...raw.split(",")]);
    onChange(next);
    setInput("");
    onInputChange?.("");
  }, [onChange, onInputChange, selected]);

  return (
    <View style={styles.tagPicker}>
      <Field
        autoCapitalize="none"
        label="Tags"
        onBlur={() => input.trim() && addTags(input)}
        onChangeText={(value) => {
          setInput(value);
          onInputChange?.(value);
        }}
        onSubmitEditing={() => input.trim() && addTags(input)}
        placeholder={placeholder}
        value={input}
      />
      <FilterPills
        pills={selected.map((tag) => ({
          id: tag,
          label: `#${tag}`,
          onRemove: () => onChange(selected.filter((name) => normalizeTag(name) !== normalizeTag(tag))),
        }))}
      />
      {suggestions.length ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View style={styles.tagSuggestions}>
            {suggestions.map((tag) => (
              <Pressable accessibilityRole="button" key={tag} onPress={() => addTags(tag)} style={styles.tagSuggestion}>
                <Text style={styles.tagSuggestionText}>#{tag}</Text>
              </Pressable>
            ))}
          </View>
        </ScrollView>
      ) : null}
    </View>
  );
}

export function CategoryPicker({
  categories,
  selectedId,
  onChange,
}: {
  categories: Category[];
  selectedId: string | null;
  onChange(categoryId: string | null): void;
}) {
  if (!categories.length) return null;
  return (
    <View style={styles.categoryPicker}>
      <Text style={styles.label}>Category</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View style={styles.categoryOptions}>
          <Pressable
            accessibilityRole="button"
            onPress={() => onChange(null)}
            style={[styles.categoryChoice, !selectedId && styles.categoryChoiceActive]}
          >
            <Text style={[styles.categoryChoiceText, !selectedId && styles.categoryChoiceTextActive]}>None</Text>
          </Pressable>
          {categories.map((category) => {
            const selected = selectedId === category.id;
            return (
              <Pressable
                accessibilityRole="button"
                key={category.id}
                onPress={() => onChange(category.id)}
                style={[styles.categoryChoice, selected && styles.categoryChoiceActive]}
              >
                <View style={[styles.categorySwatch, { backgroundColor: category.color }]} />
                <Text numberOfLines={1} style={[styles.categoryChoiceText, selected && styles.categoryChoiceTextActive]}>
                  {category.name}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </ScrollView>
    </View>
  );
}

export function ItemRow({ item }: { item: Item }) {
  const icon = item.type === "link" ? "link" : item.type === "screenshot" ? "image-outline" : "document-text-outline";
  const subtitle = item.url ?? item.raw_text ?? item.notes ?? "Saved item";
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push({ pathname: "/item/[id]", params: { id: item.id } })}
      style={({ pressed }) => [styles.item, pressed && styles.pressed]}
    >
      <View style={styles.itemIcon}><Ionicons name={icon} size={21} color={colors.primary} /></View>
      <View style={styles.itemCopy}>
        <Text numberOfLines={1} style={styles.itemTitle}>{item.title || (item.type === "text" ? "Note" : "Untitled")}</Text>
        <Text numberOfLines={2} style={styles.itemSubtitle}>{subtitle}</Text>
        <View style={styles.itemMeta}>
          <Text style={styles.metaText}>{item.type}</Text>
          {item.user_id === "local" ? <Text style={styles.localText}>Pending sync</Text> : null}
          {item.is_archived ? <Text style={styles.metaText}>Archived</Text> : null}
          {item.is_favorite ? <Ionicons name="star" size={13} color={colors.warning} /> : null}
        </View>
      </View>
      <Ionicons name="chevron-forward" size={19} color={colors.textMuted} />
    </Pressable>
  );
}

export function Page({ children, style }: React.PropsWithChildren<{ style?: ViewStyle }>) {
  return <View style={[styles.page, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.background },
  brand: { alignItems: "center", flexDirection: "row", gap: 10 },
  brandMark: { alignItems: "center", backgroundColor: colors.primary, borderRadius: 7, height: 36, justifyContent: "center", width: 36 },
  brandText: { color: colors.text, fontSize: 25, fontWeight: "700", letterSpacing: 0 },
  brandTextCompact: { fontSize: 20 },
  fieldWrap: { gap: 7 },
  label: { color: colors.text, fontSize: 14, fontWeight: "600" },
  field: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, color: colors.text, fontSize: 16, minHeight: 48, paddingHorizontal: 14, paddingVertical: 11 },
  fieldMultiline: { minHeight: 120, textAlignVertical: "top" },
  primaryButton: { alignItems: "center", backgroundColor: colors.primary, borderRadius: 7, flexDirection: "row", gap: 8, justifyContent: "center", minHeight: 48, paddingHorizontal: 18 },
  dangerButton: { backgroundColor: colors.danger },
  primaryLabel: { color: "#FFFFFF", fontSize: 16, fontWeight: "700" },
  disabled: { opacity: 0.5 },
  pressed: { opacity: 0.72 },
  empty: { alignItems: "center", gap: 9, justifyContent: "center", paddingHorizontal: 40, paddingVertical: 72 },
  emptyTitle: { color: colors.text, fontSize: 19, fontWeight: "700" },
  emptyBody: { color: colors.textMuted, fontSize: 15, lineHeight: 22, textAlign: "center" },
  filterPills: { flexDirection: "row", flexWrap: "wrap", gap: 7 },
  filterPill: { alignItems: "center", backgroundColor: "#EAF8F5", borderColor: "#A7D9D0", borderRadius: 6, borderWidth: 1, flexDirection: "row", gap: 5, minHeight: 29, paddingHorizontal: 9 },
  filterPillText: { color: colors.primaryDark, fontSize: 12, fontWeight: "700" },
  clearPill: { justifyContent: "center", minHeight: 29, paddingHorizontal: 5 },
  clearPillText: { color: colors.textMuted, fontSize: 12, fontWeight: "700" },
  tagPicker: { gap: 9 },
  tagSuggestions: { flexDirection: "row", gap: 7 },
  tagSuggestion: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 6, borderWidth: 1, minHeight: 30, justifyContent: "center", paddingHorizontal: 10 },
  tagSuggestionText: { color: colors.text, fontSize: 12, fontWeight: "700" },
  categoryPicker: { gap: 7 },
  categoryOptions: { flexDirection: "row", gap: 7 },
  categoryChoice: { alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 6, borderWidth: 1, flexDirection: "row", gap: 7, maxWidth: 190, minHeight: 34, paddingHorizontal: 10 },
  categoryChoiceActive: { backgroundColor: "#EAF8F5", borderColor: "#A7D9D0" },
  categorySwatch: { borderRadius: 5, height: 14, width: 14 },
  categoryChoiceText: { color: colors.textMuted, flexShrink: 1, fontSize: 12, fontWeight: "700" },
  categoryChoiceTextActive: { color: colors.primaryDark },
  item: { ...shadow, alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, flexDirection: "row", gap: 12, padding: 14 },
  itemIcon: { alignItems: "center", backgroundColor: "#E2F2EE", borderRadius: 7, height: 42, justifyContent: "center", width: 42 },
  itemCopy: { flex: 1, gap: 3 },
  itemTitle: { color: colors.text, fontSize: 16, fontWeight: "700" },
  itemSubtitle: { color: colors.textMuted, fontSize: 13, lineHeight: 18 },
  itemMeta: { alignItems: "center", flexDirection: "row", gap: 8, marginTop: 3 },
  metaText: { color: colors.textMuted, fontSize: 11, textTransform: "uppercase" },
  localText: { color: colors.warning, fontSize: 11, fontWeight: "600" },
});
