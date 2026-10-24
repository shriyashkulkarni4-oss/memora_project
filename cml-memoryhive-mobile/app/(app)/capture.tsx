import { Ionicons } from "@expo/vector-icons";
import * as Crypto from "expo-crypto";
import * as ImagePicker from "expo-image-picker";
import { router } from "expo-router";
import { useShareIntentContext } from "expo-share-intent";
import React, { useEffect, useRef, useState } from "react";
import { Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { useAppState } from "@/src/app-state";
import { CategoryPicker, Field, PrimaryButton, TagPicker } from "@/src/components";
import { tagsFromItems, uniqueTags } from "@/src/item-filters";
import { colors } from "@/src/theme";
import type { ItemType } from "@/src/types";

const modes: { type: ItemType; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { type: "link", label: "Link", icon: "link" },
  { type: "text", label: "Note", icon: "document-text-outline" },
  { type: "screenshot", label: "Image", icon: "image-outline" },
];

export default function Capture() {
  const { capture, categories, items } = useAppState();
  const { hasShareIntent, resetShareIntent, shareIntent } = useShareIntentContext();
  const [type, setType] = useState<ItemType>("link");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [notes, setNotes] = useState("");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [pendingTagInput, setPendingTagInput] = useState("");
  const [imageUri, setImageUri] = useState<string>();
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const pressInSubmit = useRef(false);

  useEffect(() => {
    if (!hasShareIntent) return;
    const timer = setTimeout(() => {
      const file = shareIntent.files?.find((candidate) => candidate.mimeType?.startsWith("image/"));
      if (file) {
        setType("screenshot");
        setImageUri(file.path);
      } else if (shareIntent.webUrl) {
        setType("link");
        setContent(shareIntent.webUrl);
      } else if (shareIntent.text) {
        const value = shareIntent.text.trim();
        if (/^https?:\/\//i.test(value)) {
          setType("link");
        } else {
          setType("text");
        }
        setContent(value);
      }
    }, 0);
    return () => clearTimeout(timer);
  }, [hasShareIntent, shareIntent]);

  async function selectImage() {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.9 });
    if (!result.canceled) setImageUri(result.assets[0].uri);
  }

  async function takePhoto() {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (permission.status !== "granted") {
      setError("Camera permission is required to take photos.");
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ mediaTypes: ["images"], quality: 0.9 });
    if (!result.canceled) setImageUri(result.assets[0].uri);
  }

  async function submit() {
    setError("");
    if (type === "link") {
      try { new URL(content); } catch { setError("Enter a complete http or https URL."); return; }
    }
    if (type === "text" && !content.trim()) { setError("Enter some text to save."); return; }
    if (type === "screenshot" && !imageUri) { setError("Choose an image to save."); return; }
    setSaving(true);
    try {
      const now = new Date().toISOString();
      await capture({
        id: Crypto.randomUUID(),
        type,
        created_at: now,
        title: title.trim() || undefined,
        notes: notes.trim() || undefined,
        category_id: categoryId ?? undefined,
        tags: uniqueTags([...tags, ...pendingTagInput.split(",")]),
        ...(type === "link" ? { url: content.trim() } : {}),
        ...(type === "text" ? { raw_text: content.trim() } : {}),
        ...(type === "screenshot" ? { metadata: { local_uri: imageUri } } : {}),
      }, imageUri);
      if (hasShareIntent) resetShareIntent();
      router.replace("/(app)/home");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save item");
    } finally {
      setSaving(false);
    }
  }

  function submitFromPressIn() {
    pressInSubmit.current = true;
    void submit();
  }

  function submitFromPress() {
    if (pressInSubmit.current) {
      pressInSubmit.current = false;
      return;
    }
    void submit();
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.page}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View accessibilityRole="tablist" style={styles.segmented}>
          {modes.map((mode) => (
            <Pressable accessibilityRole="tab" accessibilityState={{ selected: type === mode.type }} key={mode.type} onPress={() => setType(mode.type)} style={[styles.segment, type === mode.type && styles.segmentActive]}>
              <Ionicons color={type === mode.type ? "#FFFFFF" : colors.textMuted} name={mode.icon} size={18} />
              <Text style={[styles.segmentText, type === mode.type && styles.segmentTextActive]}>{mode.label}</Text>
            </Pressable>
          ))}
        </View>
        <Text style={styles.lead}>{type === "link" ? "Save a page for later." : type === "text" ? "Capture a thought or useful passage." : "Save a screenshot from your library."}</Text>
        <Field label="Title (optional)" onChangeText={setTitle} placeholder="A useful name" value={title} />
        {type === "link" ? <Field autoCapitalize="none" keyboardType="url" label="URL" onChangeText={setContent} placeholder="https://example.com/article" value={content} /> : null}
        {type === "text" ? <Field label="Text" multiline onChangeText={setContent} placeholder="What do you want to remember?" value={content} /> : null}
        {type === "screenshot" ? (
          imageUri ? (
            <Pressable onPress={() => void selectImage()} style={styles.imagePicker}>
              <Image resizeMode="cover" source={{ uri: imageUri }} style={styles.preview} />
            </Pressable>
          ) : (
            <View style={styles.imageActions}>
              <Pressable onPress={() => void takePhoto()} style={styles.imagePickerHalf}>
                <Ionicons color={colors.primary} name="camera-outline" size={31} />
                <Text style={styles.imageTitle}>Take photo</Text>
              </Pressable>
              <Pressable onPress={() => void selectImage()} style={styles.imagePickerHalf}>
                <Ionicons color={colors.primary} name="image-outline" size={31} />
                <Text style={styles.imageTitle}>Choose image</Text>
              </Pressable>
            </View>
          )
        ) : null}
        <Field label="Notes (optional)" multiline onChangeText={setNotes} placeholder="Why is this worth keeping?" value={notes} />
        <CategoryPicker categories={categories} selectedId={categoryId} onChange={setCategoryId} />
        <TagPicker
          available={tagsFromItems(items)}
          placeholder="research, design, later"
          selected={tags}
          onChange={setTags}
          onInputChange={setPendingTagInput}
        />
        {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
        <PrimaryButton
          icon="bookmark-outline"
          label="Save to library"
          loading={saving}
          onPress={submitFromPress}
          onPressIn={Platform.OS === "web" ? submitFromPressIn : undefined}
        />
        <Text style={styles.offlineNote}>Saved on this device immediately. Sync runs when a connection is available.</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: { backgroundColor: colors.background, flex: 1 },
  content: { gap: 18, marginHorizontal: "auto", maxWidth: 680, padding: 18, paddingBottom: 70, width: "100%" },
  segmented: { backgroundColor: colors.surfaceMuted, borderRadius: 7, flexDirection: "row", padding: 4 },
  segment: { alignItems: "center", borderRadius: 5, flex: 1, flexDirection: "row", gap: 6, justifyContent: "center", minHeight: 42 },
  segmentActive: { backgroundColor: colors.primary },
  segmentText: { color: colors.textMuted, fontSize: 14, fontWeight: "700" },
  segmentTextActive: { color: "#FFFFFF" },
  lead: { color: colors.textMuted, fontSize: 15, lineHeight: 22 },
  imagePicker: { alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderStyle: "dashed", borderWidth: 1, gap: 6, justifyContent: "center", minHeight: 190, overflow: "hidden" },
  imageActions: { flexDirection: "row", gap: 12 },
  imagePickerHalf: { flex: 1, alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderStyle: "dashed", borderWidth: 1, gap: 6, justifyContent: "center", minHeight: 150 },
  preview: { height: 250, width: "100%" },
  imageTitle: { color: colors.text, fontSize: 16, fontWeight: "700" },
  imageBody: { color: colors.textMuted, fontSize: 13 },
  error: { color: colors.danger, fontSize: 14 },
  offlineNote: { color: colors.textMuted, fontSize: 12, lineHeight: 18, textAlign: "center" },
});
