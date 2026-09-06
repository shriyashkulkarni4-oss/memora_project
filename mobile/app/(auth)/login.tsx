import { Link, router, useLocalSearchParams } from "expo-router";
import React, { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";

import { useAppState } from "@/src/app-state";
import { Brand, Field, PrimaryButton } from "@/src/components";
import { colors } from "@/src/theme";

export default function Login() {
  const { login } = useAppState();
  const params = useLocalSearchParams<{ notice?: string }>();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit() {
    setLoading(true);
    setError("");
    try {
      await login(email.trim(), password);
      router.replace("/(app)/home");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to sign in");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.page}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Brand />
        <View style={styles.heading}>
          <Text style={styles.title}>Welcome back</Text>
          <Text style={styles.subtitle}>Sign in to access your saved knowledge.</Text>
        </View>
        <View style={styles.form}>
          {params.notice ? <Text style={styles.notice}>{params.notice}</Text> : null}
          <Field autoCapitalize="none" autoComplete="email" keyboardType="email-address" label="Email" onChangeText={setEmail} value={email} />
          <Field autoCapitalize="none" autoComplete="password" label="Password" onChangeText={setPassword} secureTextEntry value={password} />
          {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
          <PrimaryButton disabled={!email || !password} label="Sign in" loading={loading} onPress={() => void submit()} />
        </View>
        <Text style={styles.footer}>New to Memoryhive? <Link href="/(auth)/register" style={styles.link}>Create an account</Link></Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: { backgroundColor: colors.background, flex: 1 },
  content: { flexGrow: 1, justifyContent: "center", marginHorizontal: "auto", maxWidth: 480, padding: 28, width: "100%" },
  heading: { gap: 8, marginBottom: 26, marginTop: 42 },
  title: { color: colors.text, fontSize: 30, fontWeight: "700", letterSpacing: 0 },
  subtitle: { color: colors.textMuted, fontSize: 16, lineHeight: 23 },
  form: { gap: 17 },
  error: { color: colors.danger, fontSize: 14 },
  notice: { backgroundColor: "#EAF8F5", borderColor: "#A7D9D0", borderRadius: 7, borderWidth: 1, color: colors.primaryDark, fontSize: 14, lineHeight: 20, padding: 12 },
  footer: { color: colors.textMuted, fontSize: 14, marginTop: 24, textAlign: "center" },
  link: { color: colors.primary, fontWeight: "700" },
});
