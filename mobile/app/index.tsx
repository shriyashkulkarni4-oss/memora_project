import { Redirect } from "expo-router";
import React from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { useAppState } from "@/src/app-state";
import { colors } from "@/src/theme";

export default function Index() {
  const { ready, user } = useAppState();
  if (!ready) {
    return <View style={styles.loading}><ActivityIndicator color={colors.primary} size="large" /></View>;
  }
  return <Redirect href={user ? "/(app)/home" : "/(auth)/login"} />;
}

const styles = StyleSheet.create({ loading: { alignItems: "center", backgroundColor: colors.background, flex: 1, justifyContent: "center" } });
