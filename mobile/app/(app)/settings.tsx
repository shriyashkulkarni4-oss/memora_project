import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { Alert, Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { API_URL, PRIVACY_POLICY_URL, SUPPORT_URL } from "@/src/api";
import { useAppState } from "@/src/app-state";
import { Brand, Field, PrimaryButton } from "@/src/components";
import { SyncIndicator } from "@/src/sync-indicator";
import { colors } from "@/src/theme";

export default function Settings() {
  const { changePassword, deleteAccount, exportAccount, logout, sync, user } = useAppState();
  const [loading, setLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [accountError, setAccountError] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);
  async function signOut() {
    setLoading(true);
    try { await logout(); } finally { setLoading(false); }
  }
  async function exportData() {
    setExportLoading(true);
    setAccountError("");
    try {
      const result = await exportAccount();
      Alert.alert(
        "Export ready",
        result.uri ? `Prepared ${result.filename}. Saved to ${result.uri}` : `Prepared ${result.filename}.`,
      );
    } catch (cause) {
      setAccountError(cause instanceof Error ? cause.message : "Unable to export account data");
    } finally {
      setExportLoading(false);
    }
  }
  async function updatePassword() {
    if (newPassword !== repeatPassword) {
      setPasswordError("New passwords do not match");
      return;
    }
    setPasswordLoading(true);
    setPasswordError("");
    try {
      await changePassword(currentPassword, newPassword);
    } catch (cause) {
      setPasswordError(cause instanceof Error ? cause.message : "Unable to change password");
      setPasswordLoading(false);
    }
  }
  function confirmPasswordChange() {
    setPasswordError("");
    Alert.alert(
      "Change password?",
      "All active sessions will be signed out.",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Change password", style: "destructive", onPress: () => void updatePassword() },
      ],
    );
  }
  async function removeAccount() {
    setDeleteLoading(true);
    setAccountError("");
    try {
      await deleteAccount(deletePassword);
    } catch (cause) {
      setAccountError(cause instanceof Error ? cause.message : "Unable to delete account");
      setDeleteLoading(false);
    }
  }
  function confirmAccountDeletion() {
    setAccountError("");
    Alert.alert(
      "Delete account?",
      "This permanently removes your account, uploads, and saved library data.",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Delete account", style: "destructive", onPress: () => void removeAccount() },
      ],
    );
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
        <Text style={styles.sectionTitle}>Security</Text>
        <Pressable onPress={() => setPasswordOpen((value) => !value)} style={styles.actionRow}>
          <Ionicons color={colors.primary} name="lock-closed-outline" size={21} />
          <View style={styles.grow}><Text style={styles.actionTitle}>Change password</Text><Text style={styles.secondary}>Signs out all active sessions</Text></View>
          <Ionicons color={colors.textMuted} name={passwordOpen ? "chevron-up" : "chevron-forward"} size={19} />
        </Pressable>
        {passwordOpen ? (
          <View style={styles.passwordForm}>
            <Field autoComplete="password" label="Current password" onChangeText={setCurrentPassword} secureTextEntry value={currentPassword} />
            <Field autoComplete="new-password" label="New password" onChangeText={setNewPassword} secureTextEntry value={newPassword} />
            <Field autoComplete="new-password" label="Confirm new password" onChangeText={setRepeatPassword} secureTextEntry value={repeatPassword} />
            {passwordError ? <Text accessibilityRole="alert" style={styles.error}>{passwordError}</Text> : null}
            <PrimaryButton
              disabled={!currentPassword || newPassword.length < 8 || !repeatPassword}
              icon="lock-closed-outline"
              label="Update password"
              loading={passwordLoading}
              onPress={confirmPasswordChange}
            />
          </View>
        ) : null}
      </View>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Local storage</Text>
        <View style={styles.info}><Ionicons color={colors.primary} name="phone-portrait-outline" size={20} /><Text style={styles.infoText}>Your library is cached on this device for offline access. Signing out clears this local copy.</Text></View>
      </View>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Data and privacy</Text>
        <PrimaryButton
          icon="download-outline"
          label={exportLoading ? "Preparing export" : "Export data"}
          loading={exportLoading}
          onPress={() => void exportData()}
        />
        <Pressable onPress={() => void Linking.openURL(PRIVACY_POLICY_URL)} style={styles.actionRow}>
          <Ionicons color={colors.primary} name="shield-checkmark-outline" size={21} />
          <View style={styles.grow}><Text style={styles.actionTitle}>Privacy policy</Text><Text numberOfLines={1} style={styles.secondary}>{PRIVACY_POLICY_URL}</Text></View>
          <Ionicons color={colors.textMuted} name="open-outline" size={19} />
        </Pressable>
        <Pressable onPress={() => void Linking.openURL(SUPPORT_URL)} style={styles.actionRow}>
          <Ionicons color={colors.primary} name="help-circle-outline" size={21} />
          <View style={styles.grow}><Text style={styles.actionTitle}>Support</Text><Text numberOfLines={1} style={styles.secondary}>{SUPPORT_URL}</Text></View>
          <Ionicons color={colors.textMuted} name="open-outline" size={19} />
        </Pressable>
        {accountError ? <Text accessibilityRole="alert" style={styles.error}>{accountError}</Text> : null}
      </View>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Delete account</Text>
        <Pressable onPress={() => setDeleteOpen((value) => !value)} style={styles.actionRow}>
          <Ionicons color={colors.danger} name="trash-outline" size={21} />
          <View style={styles.grow}><Text style={styles.actionTitle}>Delete account</Text><Text style={styles.secondary}>Permanently removes server data and local cache</Text></View>
          <Ionicons color={colors.textMuted} name={deleteOpen ? "chevron-up" : "chevron-forward"} size={19} />
        </Pressable>
        {deleteOpen ? (
          <View style={styles.passwordForm}>
            <Field autoComplete="password" label="Password" onChangeText={setDeletePassword} secureTextEntry value={deletePassword} />
            <Field autoCapitalize="characters" label="Type DELETE to confirm" onChangeText={setDeleteConfirmation} value={deleteConfirmation} />
            <PrimaryButton
              danger
              disabled={!deletePassword || deleteConfirmation !== "DELETE"}
              icon="trash-outline"
              label="Delete permanently"
              loading={deleteLoading}
              onPress={confirmAccountDeletion}
            />
          </View>
        ) : null}
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
  passwordForm: { gap: 13 },
  error: { color: colors.danger, fontSize: 13 },
  info: { alignItems: "flex-start", flexDirection: "row", gap: 10 },
  infoText: { color: colors.textMuted, flex: 1, fontSize: 14, lineHeight: 21 },
});
