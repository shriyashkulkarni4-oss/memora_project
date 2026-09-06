#!/usr/bin/env node
import fs from "node:fs";

import { easCiBuildPreflightErrors } from "./eas-release-readiness.mjs";

const appConfig = JSON.parse(fs.readFileSync(new URL("../app.json", import.meta.url), "utf8"));
const easConfig = JSON.parse(fs.readFileSync(new URL("../eas.json", import.meta.url), "utf8"));
const errors = easCiBuildPreflightErrors({
  appConfig: appConfig.expo,
  easConfig,
  expoToken: process.env.EXPO_TOKEN,
});

if (errors.length) {
  console.error("EAS build preflight failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exitCode = 1;
} else {
  console.log("EAS build preflight passed.");
}
