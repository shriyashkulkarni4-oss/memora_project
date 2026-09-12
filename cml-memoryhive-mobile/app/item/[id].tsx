import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import React, { useEffect, useRef, useState } from "react";
import { Alert, Linking, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { retryItemProcessing } from "@/src/api";
import { suggestionsFromItem } from "@/src/ai-suggestions";
import { useAppState } from "@/src/app-state";
import { CategoryPicker, EmptyState, Field, PrimaryButton, TagPicker } from "@/src/components";
import { tagsFromItems, uniqueTags } from "@/src/item-filters";
import { colors } from "@/src/theme";
import type { AISuggestionDecision, Item } from "@/src/types";

export default function ItemDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { categories, get, items, remove, reviewSuggestions, sync, update } = useAppState();
  const [item, setItem] = useState<Item>();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [pendingTagInput, setPendingTagInput] = useState("");
  const pressInSave = useRef(false);
  useEffect(() => { void get(id).then(setItem); }, [get, id]);
  const processingActive = Boolean(item && ["pending", "processing"].includes(item.processing_status));
  useEffect(() => {
    if (!processingActive) return;
    const timer = setInterval(() => {
      void sync().then(() => get(id)).then(setItem);
    }, 3000);
    return () => clearInterval(timer);
  }, [get, id, processingActive, sync]);
  if (!item) return <EmptyState body="It may have been removed on another device." icon="alert-circle-outline" title="Item unavailable" />;

  async function toggleFavorite() {
    if (!item) return;
    setItem(await update(item.id, { is_favorite: !item.is_favorite }));
  }

  async function toggleArchive() {
    if (!item) return;
    const next = await update(item.id, { is_archived: !item.is_archived });
    setItem(next);
  }

  async function saveChanges() {
    if (!item) return;
    setItem(await update(item.id, {
      title: title.trim() || null,
      notes: notes.trim() || null,
      category_id: categoryId,
      tags: uniqueTags([...tags, ...pendingTagInput.split(",")]),
    }));
    setEditing(false);
  }

  const category = categories.find((candidate) => candidate.id === item.category_id);
  const aiSuggestions = suggestionsFromItem(item);

  async function decideSuggestions(decisions: AISuggestionDecision[]) {
    if (!item) return;
    setItem(await reviewSuggestions(item.id, decisions));
  }

  function toggleEditing() {
    if (editing) {
      setEditing(false);
      return;
    }
    setTitle(item?.title ?? "");
    setNotes(item?.notes ?? "");
    setCategoryId(item?.category_id ?? null);
    setTags(item?.tags.map((tag) => tag.name) ?? []);
    setPendingTagInput("");
    setEditing(true);
  }

  function saveFromPressIn() {
    pressInSave.current = true;
    void saveChanges();
  }

  function saveFromPress() {
    if (pressInSave.current) {
      pressInSave.current = false;
      return;
    }
    void saveChanges();
  }

  function confirmFavorite() {
    if (!item) return;
    Alert.alert(
      item.is_favorite ? "Remove favorite?" : "Add favorite?",
      item.is_favorite ? "This item will leave Favorites." : "This item will appear in Favorites.",
      [
        { text: "Cancel", style: "cancel" },
        { text: item.is_favorite ? "Remove" : "Add", onPress: () => void toggleFavorite() },
      ],
    );
  }

  function confirmArchive() {
    if (!item) return;
    Alert.alert(
      item.is_archived ? "Restore item?" : "Archive item?",
      item.is_archived ? "This item will return to the active library." : "This item will move to Archive.",
      [
        { text: "Cancel", style: "cancel" },
        { text: item.is_archived ? "Restore" : "Archive", onPress: () => void toggleArchive() },
      ],
    );
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
        <Pressable accessibilityLabel={item.is_favorite ? "Remove favorite" : "Add favorite"} onPress={confirmFavorite} style={styles.iconButton}><Ionicons color={item.is_favorite ? colors.warning : colors.textMuted} name={item.is_favorite ? "star" : "star-outline"} size={23} /></Pressable>
      </View>
      <View style={styles.actions}>
        <PrimaryButton icon="create-outline" label={editing ? "Cancel edit" : "Edit item"} onPress={toggleEditing} />
        <PrimaryButton icon={item.is_archived ? "return-up-back-outline" : "archive-outline"} label={item.is_archived ? "Restore item" : "Archive item"} onPress={confirmArchive} />
      </View>
      {editing ? (
        <View style={styles.editPanel}>
          <Field label="Title" onChangeText={setTitle} placeholder="Item title" value={title} />
          <Field label="Notes" multiline onChangeText={setNotes} placeholder="Why is this worth keeping?" value={notes} />
          <CategoryPicker categories={categories} selectedId={categoryId} onChange={setCategoryId} />
          <TagPicker available={tagsFromItems(items)} selected={tags} onChange={setTags} onInputChange={setPendingTagInput} />
          <PrimaryButton
            icon="checkmark-outline"
            label="Save changes"
            onPress={saveFromPress}
            onPressIn={Platform.OS === "web" ? saveFromPressIn : undefined}
          />
        </View>
      ) : null}
      {item.url ? <Pressable onPress={() => void Linking.openURL(item.url!)} style={styles.link}><Ionicons color={colors.primary} name="open-outline" size={18} /><Text numberOfLines={2} style={styles.linkText}>{item.url}</Text></Pressable> : null}
      {item.raw_text ? <View style={styles.block}><Text style={styles.blockLabel}>Saved text</Text><Text selectable style={styles.body}>{item.raw_text}</Text></View> : null}
      {item.notes ? <View style={styles.block}><Text style={styles.blockLabel}>Notes</Text><Text selectable style={styles.body}>{item.notes}</Text></View> : null}
      {item.summary ? <View style={styles.block}><Text style={styles.blockLabel}>Summary</Text><Text selectable style={styles.body}>{item.summary}</Text></View> : null}
      {aiSuggestions.suggestions.length || aiSuggestions.topics.length ? (
        <View style={styles.suggestionPanel}>
          <View style={styles.suggestionHeader}>
            <Text style={styles.blockLabel}>AI suggestions</Text>
            {aiSuggestions.suggestions.filter((entry) => entry.status === "pending").length > 1 ? (
              <Pressable onPress={() => void decideSuggestions(aiSuggestions.suggestions.filter((entry) => entry.status === "pending").map(({ suggestion_type, value }) => ({ suggestion_type, value, action: "accept" })))} style={styles.suggestionButton}><Text>Accept all</Text></Pressable>
            ) : null}
          </View>
          {aiSuggestions.topics.length ? <Text style={styles.suggestionTopics}>Topics: {aiSuggestions.topics.join(" · ")}</Text> : null}
          {aiSuggestions.suggestions.map((suggestion) => (
            <View key={`${suggestion.suggestion_type}:${suggestion.value}`} style={styles.suggestionRow}>
              <Text style={styles.suggestionValue}>{suggestion.suggestion_type === "tag" ? "#" : ""}{suggestion.value}</Text>
              <Text style={styles.suggestionStatus}>{suggestion.status}</Text>
              {suggestion.status === "pending" ? <>
                <Pressable accessibilityLabel={`Accept ${suggestion.value}`} onPress={() => void decideSuggestions([{ suggestion_type: suggestion.suggestion_type, value: suggestion.value, action: "accept" }])} style={styles.suggestionButton}><Text>Accept</Text></Pressable>
                <Pressable accessibilityLabel={`Reject ${suggestion.value}`} onPress={() => void decideSuggestions([{ suggestion_type: suggestion.suggestion_type, value: suggestion.value, action: "reject" }])} style={styles.suggestionButton}><Text>Reject</Text></Pressable>
                {suggestion.suggestion_type === "tag" ? <Pressable onPress={() => void decideSuggestions([{ suggestion_type: "tag", value: suggestion.value, action: "never" }])} style={styles.suggestionButton}><Text>Never</Text></Pressable> : null}
              </> : suggestion.status === "accepted" ? <Pressable onPress={() => void decideSuggestions([{ suggestion_type: suggestion.suggestion_type, value: suggestion.value, action: "undo" }])} style={styles.suggestionButton}><Text>Undo</Text></Pressable> : null}
            </View>
          ))}
          <Text style={styles.suggestionHelp}>Suggestions never replace your tags or category without your action. Decisions sync when online.</Text>
        </View>
      ) : null}
      {category ? (
        <Pressable accessibilityRole="button" onPress={() => router.push({ pathname: "/(app)/home", params: { category: category.id } })} style={styles.categoryLink}>
          <View style={[styles.categorySwatch, { backgroundColor: category.color }]} />
          <Text numberOfLines={1} style={styles.categoryText}>{category.name}</Text>
        </Pressable>
      ) : null}
      {item.tags.length ? <View style={styles.tags}>{item.tags.map((tag) => (
        <Pressable accessibilityRole="button" key={tag.id} onPress={() => router.push({ pathname: "/(app)/home", params: { tag: tag.name } })} style={styles.tag}>
          <Text style={styles.tagText}>#{tag.name}</Text>
        </Pressable>
      ))}</View> : null}
      {item.processing_error ? <View style={styles.failure}><Ionicons color={colors.danger} name="alert-circle-outline" size={20} /><Text style={styles.failureText}>{item.processing_error}</Text></View> : null}
      {item.processing_status === "failed" ? <PrimaryButton icon="refresh-outline" label="Retry processing" onPress={() => void retryItemProcessing(item.id).then(async () => { setItem({ ...item, processing_status: "pending", processing_error: null }); await sync(); })} /> : null}
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
  actions: { flexDirection: "row", gap: 9 },
  editPanel: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, gap: 14, padding: 14 },
  link: { alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, flexDirection: "row", gap: 9, padding: 13 },
  linkText: { color: colors.primary, flex: 1, fontSize: 14, fontWeight: "600" },
  block: { gap: 8 },
  blockLabel: { color: colors.textMuted, fontSize: 12, fontWeight: "800", textTransform: "uppercase" },
  body: { color: colors.text, fontSize: 16, lineHeight: 25 },
  categoryLink: { alignItems: "center", alignSelf: "flex-start", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 6, borderWidth: 1, flexDirection: "row", gap: 7, maxWidth: "100%", minHeight: 34, paddingHorizontal: 10 },
  categorySwatch: { borderRadius: 4, height: 13, width: 13 },
  categoryText: { color: colors.primaryDark, flexShrink: 1, fontSize: 13, fontWeight: "700" },
  tags: { flexDirection: "row", flexWrap: "wrap", gap: 7 },
  tag: { backgroundColor: "#E2F2EE", borderRadius: 5, paddingHorizontal: 9, paddingVertical: 6 },
  tagText: { color: colors.primaryDark, fontSize: 13, fontWeight: "600" },
  meta: { borderBottomColor: colors.border, borderBottomWidth: 1, borderTopColor: colors.border, borderTopWidth: 1, flexDirection: "row", flexWrap: "wrap", gap: 15, paddingVertical: 13 },
  metaText: { color: colors.textMuted, fontSize: 12, textTransform: "capitalize" },
  failure: { alignItems: "flex-start", backgroundColor: "#FEF3F2", borderColor: "#FECDCA", borderRadius: 7, borderWidth: 1, flexDirection: "row", gap: 9, padding: 12 },
  failureText: { color: colors.danger, flex: 1, fontSize: 13, lineHeight: 19 },
  suggestionPanel: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, gap: 10, padding: 13 },
  suggestionHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  suggestionTopics: { color: colors.textMuted, fontSize: 13 },
  suggestionRow: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: 7 },
  suggestionValue: { color: colors.text, flex: 1, fontSize: 14, fontWeight: "700", minWidth: 100 },
  suggestionStatus: { color: colors.textMuted, fontSize: 11, textTransform: "uppercase" },
  suggestionButton: { backgroundColor: "#E2F2EE", borderRadius: 5, paddingHorizontal: 8, paddingVertical: 6 },
  suggestionHelp: { color: colors.textMuted, fontSize: 11, lineHeight: 16 },
});
