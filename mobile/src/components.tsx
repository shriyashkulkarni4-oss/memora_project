import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import React from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  type TextInputProps,
  View,
  type ViewStyle,
} from "react-native";

import { colors, shadow } from "./theme";
import type { Item } from "./types";

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
  danger = false,
  disabled = false,
}: {
  label: string;
  icon?: keyof typeof Ionicons.glyphMap;
  loading?: boolean;
  onPress(): void;
  danger?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled || loading}
      onPress={onPress}
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
  item: { ...shadow, alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, flexDirection: "row", gap: 12, padding: 14 },
  itemIcon: { alignItems: "center", backgroundColor: "#E2F2EE", borderRadius: 7, height: 42, justifyContent: "center", width: 42 },
  itemCopy: { flex: 1, gap: 3 },
  itemTitle: { color: colors.text, fontSize: 16, fontWeight: "700" },
  itemSubtitle: { color: colors.textMuted, fontSize: 13, lineHeight: 18 },
  itemMeta: { alignItems: "center", flexDirection: "row", gap: 8, marginTop: 3 },
  metaText: { color: colors.textMuted, fontSize: 11, textTransform: "uppercase" },
  localText: { color: colors.warning, fontSize: 11, fontWeight: "600" },
});
