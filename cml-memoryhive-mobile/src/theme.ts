import { Platform } from "react-native";

export const colors = {
  // Light Mode — Warm Neumorphism
  background: "#F5EDDA",
  surface: "#F0E8D4",
  surfaceMuted: "#EAE0CA",
  text: "#013E37",
  textMuted: "#4A6B64",
  border: "#DDD4BE",
  primary: "#013E37",
  primaryDark: "#012E29",
  butter: "#FFEFB3",
  butterDeep: "#F0D878",
  danger: "#B42318",
  warning: "#A15C00",
};

export const darkColors = {
  background: "#1A2420",
  surface: "#16201C",
  surfaceMuted: "#121A16",
  text: "#FFEFB3",
  textMuted: "#C8D4C0",
  border: "#2A3A34",
  primary: "#FFEFB3",
  primaryDark: "#F0D878",
  butter: "#FFEFB3",
  butterDeep: "#F0D878",
  danger: "#FF6B5A",
  warning: "#F59E0B",
};

export const shadow = Platform.select({
  web: {
    boxShadow:
      "6px 6px 14px rgba(180,165,130,0.45), -6px -6px 14px #FFFDF5",
  },
  default: {
    shadowColor: "#B4A582",
    shadowOffset: { width: 6, height: 6 },
    shadowOpacity: 0.45,
    shadowRadius: 14,
    elevation: 4,
  },
});

export const floatingActionShadow = Platform.select({
  web: {
    boxShadow:
      "8px 8px 18px rgba(180,165,130,0.45), -8px -8px 18px #FFFDF5",
  },
  default: {
    elevation: 8,
    shadowColor: "#B4A582",
    shadowOffset: { height: 8, width: 0 },
    shadowOpacity: 0.45,
    shadowRadius: 18,
  },
});
