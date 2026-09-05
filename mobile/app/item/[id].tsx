import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import React, { useEffect, useState } from "react";
import { Alert, Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { useAppState } from "@/src/app-state";
import { EmptyState, PrimaryButton } from "@/src/components";
import { colors } from "@/src/theme";
import type { Item } from "@/src/types";

export default function ItemDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { get, remove, update } = useAppState();
  const [item, setItem] = useState<Item>();
  useEffect(() => { void get(id).then(setItem); }, [get, id]);
  if (!item) return <EmptyState body="It may have been removed on another device." icon="alert-circle-outline" title="Item unavailable" />;

  async function toggleFavorite() {
    setItem(await update(item!.id, { is_favorite: !item!.is_favorite }));
  }

  function confirmDelete() {
    Alert.alert("Delete this item?", "The deletion will sync to your other devices.", [
      { text: "Cancel", style: "cancel" },
      { text: "Delete", style: "destructive", onPress: async () => { await remove(item!.id); router.replace("/(app)/home"); } },
    ]);
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.header}>
        <View style={styles.typeIcon}><Ionicons color={colors.primary} name={item.type === "link" ? "link" : item.type === "screenshot" ? "image-outline" : "document-text-outline"} size={24} /></View>
        <View style={styles.grow}><Text style={styles.type}>{item.type}</Text><Text style={styles.title}>{item.title || (item.type === "text" ? "Note" : "Untitled item")}</Text></View>
        <Pressable accessibilityLabel={item.is_favorite ? "Remove favorite" : "Add favorite"} onPress={() => void toggleFavorite()} style={styles.iconButton}><Ionicons color={item.is_favorite ? colors.warning : colors.textMuted} name={item.is_favorite ? "star" : "star-outline"} size={23} /></Pressable>
      </View>
      {item.url ? <Pressable onPress={() => void Linking.openURL(item.url!)} style={styles.link}><Ionicons color={colors.primary} name="open-outline" size={18} /><Text numberOfLines={2} style={styles.linkText}>{item.url}</Text></Pressable> : null}
      {item.raw_text ? <View style={styles.block}><Text style={styles.blockLabel}>Saved text</Text><Text selectable style={styles.body}>{item.raw_text}</Text></View> : null}
      {item.notes ? <View style={styles.block}><Text style={styles.blockLabel}>Notes</Text><Text selectable style={styles.body}>{item.notes}</Text></View> : null}
      {item.summary ? <View style={styles.block}><Text style={styles.blockLabel}>Summary</Text><Text selectable style={styles.body}>{item.summary}</Text></View> : null}
      {item.tags.length ? <View style={styles.tags}>{item.tags.map((tag) => <Text key={tag.id} style={styles.tag}>#{tag.name}</Text>)}</View> : null}
      <View style={styles.meta}><Text style={styles.metaText}>Revision {item.revision}</Text><Text style={styles.metaText}>{item.user_id === "local" ? "Pending sync" : item.processing_status}</Text><Text style={styles.metaText}>{new Date(item.created_at).toLocaleDateString()}</Text></View>
      <PrimaryButton danger icon="trash-outline" label="Delete item" onPress={confirmDelete} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { gap: 22, marginHorizontal: "auto", maxWidth: 760, padding: 20, paddingBottom: 70, width: "100%" },
  header: { alignItems: "flex-start", flexDirection: "row", gap: 13 },
  typeIcon: { alignItems: "center", backgroundColor: "#E2F2EE", borderRadius: 7, height: 48, justifyContent: "center", width: 48 },
  grow: { flex: 1 },
  type: { color: colors.primary, fontSize: 12, fontWeight: "800", textTransform: "uppercase" },
  title: { color: colors.text, fontSize: 24, fontWeight: "700", letterSpacing: 0, lineHeight: 31, marginTop: 3 },
  iconButton: { alignItems: "center", height: 44, justifyContent: "center", width: 44 },
  link: { alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, flexDirection: "row", gap: 9, padding: 13 },
  linkText: { color: colors.primary, flex: 1, fontSize: 14, fontWeight: "600" },
  block: { gap: 8 },
  blockLabel: { color: colors.textMuted, fontSize: 12, fontWeight: "800", textTransform: "uppercase" },
  body: { color: colors.text, fontSize: 16, lineHeight: 25 },
  tags: { flexDirection: "row", flexWrap: "wrap", gap: 7 },
  tag: { backgroundColor: "#E2F2EE", borderRadius: 5, color: colors.primaryDark, fontSize: 13, fontWeight: "600", paddingHorizontal: 9, paddingVertical: 6 },
  meta: { borderBottomColor: colors.border, borderBottomWidth: 1, borderTopColor: colors.border, borderTopWidth: 1, flexDirection: "row", flexWrap: "wrap", gap: 15, paddingVertical: 13 },
  metaText: { color: colors.textMuted, fontSize: 12, textTransform: "capitalize" },
});
