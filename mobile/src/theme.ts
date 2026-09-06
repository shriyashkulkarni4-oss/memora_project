import { Platform } from "react-native";

export const colors = {
  background: "#F7F8F6",
  surface: "#FFFFFF",
  surfaceMuted: "#EEF1EE",
  text: "#16201D",
  textMuted: "#66716D",
  border: "#D7DDDA",
  primary: "#087F6D",
  primaryDark: "#076354",
  danger: "#B42318",
  warning: "#A15C00",
};

export const shadow = Platform.select({
  web: { boxShadow: "0 1px 4px rgba(22, 32, 29, 0.08)" },
  default: {
    shadowColor: "#16201D",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
});

export const floatingActionShadow = Platform.select({
  web: { boxShadow: "0 3px 5px rgba(22, 32, 29, 0.2)" },
  default: {
    elevation: 5,
    shadowColor: colors.text,
    shadowOffset: { height: 3, width: 0 },
    shadowOpacity: 0.2,
    shadowRadius: 5,
  },
});
