import { Link, router } from "expo-router";
import React, { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";

import { useAppState } from "@/src/app-state";
import { Brand, Field, PrimaryButton } from "@/src/components";
import { colors } from "@/src/theme";

export default function Register() {
  const { register } = useAppState();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit() {
    setLoading(true);
    setError("");
    try {
      await register(name.trim(), email.trim(), password);
      router.replace("/(app)/home");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to create account");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.page}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Brand />
        <View style={styles.heading}>
          <Text style={styles.title}>Create your account</Text>
          <Text style={styles.subtitle}>Save links, screenshots, and notes from any device.</Text>
        </View>
        <View style={styles.form}>
          <Field autoComplete="name" label="Name" onChangeText={setName} value={name} />
          <Field autoCapitalize="none" autoComplete="email" keyboardType="email-address" label="Email" onChangeText={setEmail} value={email} />
          <Field autoCapitalize="none" autoComplete="new-password" label="Password" onChangeText={setPassword} secureTextEntry value={password} />
          <Text style={styles.hint}>Use at least 8 characters.</Text>
          {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
          <PrimaryButton disabled={!email || password.length < 8} label="Create account" loading={loading} onPress={() => void submit()} />
        </View>
        <Text style={styles.footer}>Already have an account? <Link href="/(auth)/login" style={styles.link}>Sign in</Link></Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: { backgroundColor: colors.background, flex: 1 },
  content: { flexGrow: 1, justifyContent: "center", marginHorizontal: "auto", maxWidth: 480, padding: 28, width: "100%" },
  heading: { gap: 8, marginBottom: 26, marginTop: 34 },
  title: { color: colors.text, fontSize: 29, fontWeight: "700", letterSpacing: 0 },
  subtitle: { color: colors.textMuted, fontSize: 16, lineHeight: 23 },
  form: { gap: 16 },
  hint: { color: colors.textMuted, fontSize: 12, marginTop: -9 },
  error: { color: colors.danger, fontSize: 14 },
  footer: { color: colors.textMuted, fontSize: 14, marginTop: 24, textAlign: "center" },
  link: { color: colors.primary, fontWeight: "700" },
});
