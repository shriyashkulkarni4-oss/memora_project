import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { API_URL } from "@/src/api";
import { useAppState } from "@/src/app-state";
import { Brand, PrimaryButton } from "@/src/components";
import { SyncIndicator } from "@/src/sync-indicator";
import { colors } from "@/src/theme";

export default function Settings() {
  const { logout, sync, user } = useAppState();
  const [loading, setLoading] = useState(false);
  async function signOut() {
    setLoading(true);
    try { await logout(); } finally { setLoading(false); }
  }
  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Brand compact />
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        <View style={styles.row}>
          <View style={styles.avatar}><Text style={styles.avatarText}>{(user?.name || user?.email || "M")[0].toUpperCase()}</Text></View>
          <View style={styles.grow}><Text style={styles.name}>{user?.name || "Memoryhive user"}</Text><Text style={styles.secondary}>{user?.email}</Text></View>
        </View>
      </View>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Synchronization</Text>
        <Pressable onPress={() => void sync()} style={styles.actionRow}>
          <Ionicons color={colors.primary} name="sync-outline" size={21} />
          <View style={styles.grow}><Text style={styles.actionTitle}>Sync now</Text><SyncIndicator /></View>
          <Ionicons color={colors.textMuted} name="chevron-forward" size={19} />
        </Pressable>
        <View style={styles.actionRow}>
          <Ionicons color={colors.primary} name="server-outline" size={21} />
          <View style={styles.grow}><Text style={styles.actionTitle}>Server</Text><Text numberOfLines={1} style={styles.secondary}>{API_URL}</Text></View>
        </View>
      </View>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Local storage</Text>
        <View style={styles.info}><Ionicons color={colors.primary} name="phone-portrait-outline" size={20} /><Text style={styles.infoText}>Your library is cached on this device for offline access. Signing out clears this local copy.</Text></View>
      </View>
      <PrimaryButton danger icon="log-out-outline" label="Sign out" loading={loading} onPress={() => Alert.alert("Sign out?", "Pending local changes should be synced before signing out.", [{ text: "Cancel", style: "cancel" }, { text: "Sign out", style: "destructive", onPress: () => void signOut() }])} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { gap: 25, marginHorizontal: "auto", maxWidth: 680, padding: 20, paddingBottom: 80, width: "100%" },
  section: { borderBottomColor: colors.border, borderBottomWidth: 1, gap: 13, paddingBottom: 21 },
  sectionTitle: { color: colors.textMuted, fontSize: 12, fontWeight: "800", textTransform: "uppercase" },
  row: { alignItems: "center", flexDirection: "row", gap: 13 },
  avatar: { alignItems: "center", backgroundColor: colors.primary, borderRadius: 7, height: 46, justifyContent: "center", width: 46 },
  avatarText: { color: "#FFFFFF", fontSize: 19, fontWeight: "800" },
  grow: { flex: 1, gap: 3 },
  name: { color: colors.text, fontSize: 17, fontWeight: "700" },
  secondary: { color: colors.textMuted, fontSize: 13 },
  actionRow: { alignItems: "center", backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 7, borderWidth: 1, flexDirection: "row", gap: 12, minHeight: 65, padding: 13 },
  actionTitle: { color: colors.text, fontSize: 15, fontWeight: "700" },
  info: { alignItems: "flex-start", flexDirection: "row", gap: 10 },
  infoText: { color: colors.textMuted, flex: 1, fontSize: 14, lineHeight: 21 },
});
