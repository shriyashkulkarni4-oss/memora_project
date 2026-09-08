import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = "/Users/mahesh-kulkarni/projects/coding-monkey-labs-client-projects/cml-memoryhive/docs/Presentations";
const SKILL_DIR = "/Users/mahesh-kulkarni/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
// The presentation finalizer requires its plugin-owned interpreter and dependencies.
const RUNTIME_PYTHON = "/Users/mahesh-kulkarni/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python";
const TMP_DIR = path.join(ROOT, ".build");
const FINAL_DIR = path.join(ROOT, "final");
const ASSET_DIR = path.join(ROOT, "assets");
const W = 1280;
const H = 720;
const EMU_SIZE = "12192000,6858000";

const {
  resolvePresentationFont,
  makeNativeBulletParagraphs,
  finalizePresentation,
} = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);

const family = resolvePresentationFont();
const fontPolicy = { basis: "design", families: [family] };

const colors = {
  ink: "#101820",
  muted: "#5F6B7A",
  light: "#F6F8FB",
  line: "#D9E0EA",
  dark: "#05070C",
  blue: "#007AFF",
  blueDark: "#0B4E9C",
  green: "#34C759",
  amber: "#FFB000",
  red: "#FF3B30",
  slate: "#2B3440",
  white: "#FFFFFF",
};

const sources = [
  "Product source: MEMORA_README.md, cml-memoryhive-apps.",
  "Product source: MEMORYHIVE_REQUIREMENTS.md, cml-memoryhive/docs.",
  "Deck standardizes on the user-facing product name Memora. The PRD source uses Memoryhive.",
];

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(FINAL_DIR, { recursive: true });

const productHero = await fs.readFile(path.join(ASSET_DIR, "memora-product-hero.png"));
const engineeringHero = await fs.readFile(path.join(ASSET_DIR, "memora-engineering-hero.png"));

function addShape(slide, geometry, x, y, w, h, fill = "none", line = "none", radius = undefined) {
  return slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: line === "none" ? { style: "solid", fill: "none", width: 0 } : line,
    ...(radius ? { borderRadius: radius } : {}),
  });
}

function addText(slide, text, x, y, w, h, opts = {}) {
  const shape = addShape(slide, "textbox", x, y, w, h, opts.fill ?? "none", opts.line ?? "none", opts.radius);
  shape.text = text;
  shape.text.style = {
    typeface: family,
    fontSize: opts.size ?? 22,
    bold: opts.bold ?? false,
    italic: opts.italic ?? false,
    color: opts.color ?? colors.ink,
    alignment: opts.align ?? "left",
    autoFit: opts.autoFit ?? "none",
  };
  return shape;
}

function addTitle(slide, title, subtitle = undefined) {
  addText(slide, title, 64, 44, 870, subtitle ? 54 : 70, {
    size: 34,
    bold: true,
    color: colors.ink,
  });
  if (subtitle) {
    addText(slide, subtitle, 66, 98, 820, 46, {
      size: 18,
      color: colors.muted,
    });
  }
}

function addSectionLabel(slide, text, x = 64, y = 32, color = colors.blue) {
  addText(slide, text, x, y, 380, 26, {
    size: 13,
    bold: true,
    color,
  });
}

function addFooter(slide, page, theme = "light") {
  const color = theme === "dark" ? "#C9D1DA" : "#728092";
  addShape(slide, "line", 64, 682, 1030, 1, "none", { style: "solid", fill: theme === "dark" ? "#FFFFFF/18" : "#D9E0EA", width: 1 });
  addText(slide, "Memora", 64, 688, 160, 20, { size: 11, bold: true, color });
  addText(slide, String(page).padStart(2, "0"), 1158, 688, 58, 20, { size: 11, color, align: "right" });
}

function addBullets(slide, items, x, y, w, h, opts = {}) {
  const shape = addShape(slide, "textbox", x, y, w, h, "none", "none");
  shape.text = makeNativeBulletParagraphs(items, {
    marginLeftPoints: opts.marginLeftPoints ?? 17,
    hangingPoints: opts.hangingPoints ?? 8,
    spaceAfterPoints: opts.spaceAfterPoints ?? 8,
  });
  shape.text.style = {
    typeface: family,
    fontSize: opts.size ?? 20,
    color: opts.color ?? colors.ink,
    autoFit: "none",
  };
  return shape;
}

function addSmallCaption(slide, text, x, y, w, color = colors.muted) {
  addText(slide, text, x, y, w, 28, { size: 13, color });
}

function addPill(slide, text, x, y, w, fill, color = colors.ink) {
  const box = addShape(slide, "roundRect", x, y, w, 31, fill, { style: "solid", fill: fill, width: 0 }, "rounded-full");
  box.text = text;
  box.text.style = {
    typeface: family,
    fontSize: 12,
    bold: true,
    color,
    alignment: "center",
    autoFit: "none",
  };
  return box;
}

function addMetricBlock(slide, value, label, x, y, w, accent) {
  addShape(slide, "rect", x, y, w, 116, colors.white, { style: "solid", fill: colors.line, width: 1 }, 8);
  addShape(slide, "rect", x, y, 8, 116, accent, { style: "solid", fill: accent, width: 0 });
  addText(slide, value, x + 24, y + 20, w - 48, 34, { size: 30, bold: true, color: accent });
  addText(slide, label, x + 24, y + 62, w - 48, 36, { size: 16, color: colors.slate });
}

function addStep(slide, index, title, detail, x, y, w, h, accent) {
  const box = addShape(slide, "rect", x, y, w, h, colors.white, { style: "solid", fill: colors.line, width: 1 }, 8);
  addShape(slide, "ellipse", x + 22, y + 20, 34, 34, accent, { style: "solid", fill: accent, width: 0 });
  addText(slide, String(index), x + 22, y + 26, 34, 20, { size: 16, bold: true, color: colors.white, align: "center" });
  addText(slide, title, x + 72, y + 18, w - 92, 52, { size: 19, bold: true, color: colors.ink });
  addText(slide, detail, x + 72, y + 82, w - 92, h - 100, { size: 15, color: colors.muted });
  return box;
}

function addFlowNode(slide, label, detail, x, y, w, h, fill, color = colors.ink) {
  const node = addShape(slide, "roundRect", x, y, w, h, fill, { style: "solid", fill: "#FFFFFF/0", width: 0 }, 10);
  addText(slide, label, x + 20, y + 18, w - 40, 28, { size: 19, bold: true, color });
  addText(slide, detail, x + 20, y + 54, w - 40, h - 70, { size: 15, color: color === colors.white ? "#DDE6F3" : colors.muted });
  return node;
}

function connect(slide, from, to, fromSide = "right", toSide = "left") {
  return slide.shapes.connect(from, to, {
    kind: "elbow",
    fromSide,
    toSide,
    line: { style: "solid", fill: "#8391A3", width: 2 },
    tail: { type: "triangle", width: "sm", length: "sm" },
  });
}

function addRowCard(slide, title, detail, x, y, w, h, accent) {
  addShape(slide, "rect", x, y, w, h, colors.white, { style: "solid", fill: colors.line, width: 1 }, 8);
  addShape(slide, "rect", x, y, 7, h, accent, { style: "solid", fill: accent, width: 0 });
  addText(slide, title, x + 22, y + 16, 230, h - 22, { size: 18, bold: true, color: colors.ink });
  addText(slide, detail, x + 275, y + 16, w - 300, h - 22, { size: 15, color: colors.muted });
}

function addNotes(slide, extra = "") {
  slide.speakerNotes.textFrame.setText([...sources, extra].filter(Boolean).join("\n"));
  slide.speakerNotes.setVisible(true);
}

const investorColors = {
  bg: "#05070C",
  panel: "#0D1420",
  panelAlt: "#111A28",
  panelBlue: "#0B1B30",
  panelGreen: "#0B2118",
  panelAmber: "#2A2109",
  panelRed: "#2B1015",
  line: "#263449",
  title: "#F7FAFF",
  body: "#DDE6F3",
  muted: "#9AA8B8",
  blue: "#77B7FF",
  green: "#69D988",
  amber: "#FFD166",
  red: "#FF8A80",
};

function addInvestorTitle(slide, title, subtitle = undefined) {
  addText(slide, title, 64, 44, 900, subtitle ? 54 : 70, {
    size: 34,
    bold: true,
    color: investorColors.title,
  });
  if (subtitle) {
    addText(slide, subtitle, 66, 98, 850, 48, {
      size: 18,
      color: investorColors.muted,
    });
  }
}

function addInvestorBullets(slide, items, x, y, w, h, opts = {}) {
  return addBullets(slide, items, x, y, w, h, {
    ...opts,
    color: opts.color ?? investorColors.body,
  });
}

function addInvestorPanel(slide, x, y, w, h, fill = investorColors.panel) {
  return addShape(slide, "rect", x, y, w, h, fill, { style: "solid", fill: investorColors.line, width: 1 }, 8);
}

function addInvestorMetric(slide, value, label, x, y, w, accent) {
  addInvestorPanel(slide, x, y, w, 116);
  addShape(slide, "rect", x, y, 8, 116, accent, { style: "solid", fill: accent, width: 0 });
  addText(slide, value, x + 24, y + 20, w - 48, 34, { size: 30, bold: true, color: accent });
  addText(slide, label, x + 24, y + 62, w - 48, 36, { size: 16, color: investorColors.body });
}

function addInvestorFlowNode(slide, label, detail, x, y, w, h, fill, accent) {
  const node = addShape(slide, "roundRect", x, y, w, h, fill, { style: "solid", fill: investorColors.line, width: 1 }, 10);
  addText(slide, label, x + 20, y + 18, w - 40, 30, { size: 19, bold: true, color: accent });
  addText(slide, detail, x + 20, y + 56, w - 40, h - 72, { size: 15, color: investorColors.body });
  return node;
}

function addInvestorRow(slide, title, detail, emphasis, y, accent, fill = investorColors.panel) {
  addInvestorPanel(slide, 86, y, 1108, 74, fill);
  addText(slide, title, 112, y + 17, 220, 26, { size: 18, bold: true, color: accent });
  addText(slide, detail, 356, y + 16, 360, 34, { size: 15, color: investorColors.body });
  addText(slide, emphasis, 760, y + 16, 360, 34, { size: 15, bold: true, color: investorColors.title });
}

function coverSlide(presentation, { title, subtitle, label, image, dark = true }) {
  const slide = presentation.slides.add();
  slide.background.fill = dark ? colors.dark : colors.light;
  slide.images.add({
    blob: image,
    contentType: "image/png",
    alt: "Memora visual",
    fit: "cover",
    position: { left: 0, top: 0, width: W, height: H },
  });
  addShape(slide, "rect", 0, 0, W, H, dark ? "#05070C/72" : "#FFFFFF/68", { style: "solid", fill: "none", width: 0 });
  addText(slide, label, 72, 74, 520, 28, { size: 14, bold: true, color: dark ? "#77B7FF" : colors.blue });
  addText(slide, title, 72, 143, 650, 144, { size: 55, bold: true, color: dark ? colors.white : colors.ink });
  addText(slide, subtitle, 74, 315, 610, 86, { size: 23, color: dark ? "#DDE6F3" : colors.slate });
  addShape(slide, "line", 74, 430, 240, 1, "none", { style: "solid", fill: dark ? colors.green : colors.blue, width: 4 });
  addText(slide, "Prepared for Coding Monkey Labs", 74, 458, 360, 26, { size: 15, color: dark ? "#C9D1DA" : colors.muted });
  addText(slide, "September 2026", 74, 486, 220, 24, { size: 14, color: dark ? "#9AA8B8" : colors.muted });
  addNotes(slide, "Generated cover visual created for this pitch package. No external market claims used on this slide.");
  return slide;
}

async function finalizeDeck(presentation, filename, slideCount) {
  const staging = path.join(ROOT, ".codex-finalizer", `${filename.replace(/\.pptx$/, "")}-${Date.now()}`);
  await fs.mkdir(staging, { recursive: true });
  const candidatePath = path.join(staging, "candidate.pptx");
  await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
  const finalPath = path.join(FINAL_DIR, filename);
  await finalizePresentation({
    explicitTotalSlideCount: slideCount,
    requiredNativeTableOwnerSlides: [],
    requiredNativeChartOwnerSlides: [],
    workspaceDir: ROOT,
    candidatePath,
    finalPath,
    pythonExecutable: RUNTIME_PYTHON,
    integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
    layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
    layoutArgs: [
      "--expected-slide-size-emu", EMU_SIZE,
      "--validate-bullet-geometry",
      "--validate-heading-fit",
    ],
    fontPolicy,
    verifyArtifactToolImport: true,
    receiptPath: path.join(staging, `${filename}.validation.json`),
  });
  return finalPath;
}

function buildInternDeck() {
  const deck = Presentation.create({ slideSize: { width: W, height: H } });
  let page = 1;

  coverSlide(deck, {
    title: "Memora",
    subtitle: "Build the mobile memory layer for useful links, screenshots, and notes",
    label: "New Graduate Engineering Pitch",
    image: engineeringHero,
  });
  page += 1;

  {
    const slide = deck.slides.add();
    slide.background.fill = colors.light;
    addTitle(slide, "Why Memora Exists", "People save useful knowledge faster than they can organize it.");
    addMetricBlock(slide, "2 sec", "Target time to capture a useful item", 78, 185, 304, colors.blue);
    addMetricBlock(slide, "500 ms", "Target save action for instant local capture", 488, 185, 304, colors.green);
    addMetricBlock(slide, "Offline", "Core capture and search should work without network access", 898, 185, 304, colors.amber);
    addText(slide, "The user pain is simple: links, screenshots, and notes get saved across apps, then disappear when the user actually needs them.", 108, 365, 1040, 82, { size: 25, bold: true, color: colors.ink, align: "center" });
    addBullets(slide, [
      "Screenshots hold valuable text, but normal bookmark tools cannot search them.",
      "Bookmarks preserve the URL, but lose the reason the user saved it.",
      "Notes apps work only when users stop and organize manually."
    ], 190, 482, 900, 126, { size: 19 });
    addFooter(slide, page++);
    addNotes(slide, "Targets come from MEMORYHIVE_REQUIREMENTS.md success criteria and non-functional requirements.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = colors.white;
    addSectionLabel(slide, "PRODUCT DEFINITION");
    addTitle(slide, "Capture, Understanding, Recall", "The product rule: every feature must improve one of these three jobs.");
    const a = addFlowNode(slide, "Capture", "Screenshots, URLs, text, and photos saved from mobile flows", 88, 215, 304, 155, "#EAF3FF", colors.blueDark);
    const b = addFlowNode(slide, "Understand", "OCR, readable link extraction, summaries, and tags run in the background", 488, 215, 304, 155, "#EAFBF1", "#107C41");
    const c = addFlowNode(slide, "Recall", "Full-text search across items, source filters, time filters, and resurfaced context", 888, 215, 304, 155, "#FFF5D8", "#9A6500");
    connect(slide, a, b);
    connect(slide, b, c);
    addText(slide, "Core principles", 92, 452, 240, 32, { size: 20, bold: true });
    addPill(slide, "Mobile-first", 92, 500, 144, "#EAF3FF", colors.blueDark);
    addPill(slide, "Offline-first", 260, 500, 142, "#EAFBF1", "#107C41");
    addPill(slide, "Local ownership", 428, 500, 160, "#F0F3F7", colors.ink);
    addPill(slide, "Background AI", 612, 500, 150, "#FFF5D8", "#9A6500");
    addPill(slide, "Minimal effort", 786, 500, 142, "#FFEDEA", "#A51E18");
    addFooter(slide, page++);
    addNotes(slide, "Product framing from MEMORYHIVE_REQUIREMENTS.md sections 1, 6, and 15.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = colors.light;
    addTitle(slide, "MVP Experience", "The first release should make capture feel instant and recall feel obvious.");
    const steps = [
      ["Save from share menu", "A screenshot, link, or text snippet reaches Memora without extra metadata."],
      ["Store locally", "Raw content and the first search index land on the device first."],
      ["Process in background", "OCR, title extraction, summary, and tags run after the save action."],
      ["Search later", "Users find items by words inside screenshots, links, source, or time."]
    ];
    const xs = [72, 372, 672, 972];
    const accents = [colors.blue, colors.green, colors.amber, colors.red];
    const nodes = steps.map((s, i) => addStep(slide, i + 1, s[0], s[1], xs[i], 220, 236, 228, accents[i]));
    connect(slide, nodes[0], nodes[1]);
    connect(slide, nodes[1], nodes[2]);
    connect(slide, nodes[2], nodes[3]);
    addText(slide, "The MVP avoids folders, collaboration feeds, task management, and chat with notes. That restraint gives interns a clearer product surface and a better engineering target.", 135, 520, 1010, 78, { size: 23, color: colors.ink, align: "center" });
    addFooter(slide, page++);
    addNotes(slide, "MVP scope and explicit non-goals are from MEMORYHIVE_REQUIREMENTS.md sections 9 and 14.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = colors.white;
    addTitle(slide, "What New Grads Will Build", "A real product surface with meaningful ownership across mobile, backend, search, sync, and AI.");
    addRowCard(slide, "Mobile capture", "React Native and Expo flows for camera, image picker, share sheet, deep links, and offline-first UX.", 92, 160, 1096, 78, colors.blue);
    addRowCard(slide, "Local data layer", "MMKV storage, encrypted session state, search index persistence, and device-first performance tuning.", 92, 260, 1096, 78, colors.green);
    addRowCard(slide, "Backend services", "FastAPI APIs for auth, metadata, items, sync push/pull, stats, and cloud persistence.", 92, 360, 1096, 78, colors.amber);
    addRowCard(slide, "Search and AI", "OCR, readable link extraction, summary generation, auto tags, and background processing orchestration.", 92, 460, 1096, 78, colors.red);
    addFooter(slide, page++);
    addNotes(slide, "Workstreams map to MEMORA_README.md architecture and roadmap sections.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = colors.dark;
    addSectionLabel(slide, "REFERENCE ARCHITECTURE", 64, 32, "#77B7FF");
    addText(slide, "Mobile-First Technical System", 64, 64, 760, 48, { size: 34, bold: true, color: colors.white });
    addText(slide, "The architecture teaches practical product engineering: latency, offline behavior, sync, data ownership, and asynchronous processing.", 66, 116, 780, 44, { size: 18, color: "#C9D1DA" });
    const mobile = addFlowNode(slide, "Mobile app", "Expo Router, React Native, Zustand", 82, 230, 235, 132, "#132235", colors.white);
    const local = addFlowNode(slide, "Local store", "MMKV, SecureStore, local search index", 380, 230, 235, 132, "#102A20", colors.white);
    const api = addFlowNode(slide, "API layer", "Auth, items, search, sync, stats", 678, 230, 235, 132, "#33260A", colors.white);
    const data = addFlowNode(slide, "Data services", "Postgres or MongoDB, MinIO object storage", 976, 230, 235, 132, "#2E1820", colors.white);
    connect(slide, mobile, local);
    connect(slide, local, api);
    connect(slide, api, data);
    const ai = addFlowNode(slide, "Background processing", "OCR, summary, keywords, auto tags", 380, 470, 533, 94, "#0C2030", colors.white);
    connect(slide, api, ai, "bottom", "top");
    connect(slide, ai, local, "left", "bottom");
    addFooter(slide, page++, "dark");
    addNotes(slide, "Architecture combines MEMORA_README.md current stack with MEMORYHIVE_REQUIREMENTS.md target storage and AI pipeline options.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = colors.light;
    addTitle(slide, "Learning Outcomes", "The project is narrow enough for focus and deep enough for serious engineering growth.");
    const items = [
      ["Mobile UX", "Capture flows, navigation, permissions, and app store constraints"],
      ["Offline systems", "Local persistence, sync queues, retries, and conflict handling"],
      ["API design", "Auth, pagination, filters, CRUD, and observable service behavior"],
      ["Search quality", "Text extraction, indexing, ranking, and empty-state design"],
      ["AI product judgment", "When OCR and summaries help, and when they should stay optional"],
      ["Privacy engineering", "Data export, deletion, clear storage choices, and trust-building UX"]
    ];
    items.forEach((item, i) => {
      const x = i % 2 === 0 ? 88 : 676;
      const y = 158 + Math.floor(i / 2) * 130;
      addShape(slide, "rect", x, y, 516, 96, colors.white, { style: "solid", fill: colors.line, width: 1 }, 8);
      addText(slide, item[0], x + 24, y + 18, 330, 28, { size: 19, bold: true, color: i % 2 === 0 ? colors.blueDark : "#107C41" });
      addText(slide, item[1], x + 24, y + 52, 455, 30, { size: 15, color: colors.muted });
    });
    addFooter(slide, page++);
    addNotes(slide, "Learning outcomes are derived from the requested audience and source architecture.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = colors.white;
    addTitle(slide, "Intern Project Tracks", "Each track ends with a demoable product increment and a written engineering decision record.");
    const tracks = [
      ["Capture track", "Share sheet, camera/gallery intake, text note capture", "A capture flow that works in under two seconds"],
      ["Recall track", "OCR ingestion, local index, filters, result grouping", "Search that finds screenshot text and saved links"],
      ["Sync track", "Push/pull, retry queue, merge rules, network states", "Offline capture that syncs without user intervention"],
      ["AI track", "Readable link extraction, summaries, keywords, auto tags", "Background enrichment that never blocks saving"]
    ];
    tracks.forEach((track, i) => {
      const y = 160 + i * 106;
      addShape(slide, "rect", 78, y, 1124, 82, i % 2 === 0 ? "#F8FAFD" : "#FFFFFF", { style: "solid", fill: colors.line, width: 1 }, 6);
      addText(slide, track[0], 104, y + 18, 184, 30, { size: 18, bold: true, color: [colors.blueDark, "#107C41", "#9A6500", "#A51E18"][i] });
      addText(slide, track[1], 310, y + 17, 390, 32, { size: 15, color: colors.slate });
      addText(slide, track[2], 740, y + 17, 410, 32, { size: 15, bold: true, color: colors.ink });
    });
    addSmallCaption(slide, "Track scope can be assigned to individuals or two-person pods depending on intern count.", 92, 610, 760);
    addFooter(slide, page++);
    addNotes(slide, "Project tracks translate the PRD into intern-sized delivery units.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = colors.light;
    addTitle(slide, "Eight Week Build Plan", "The plan balances onboarding, implementation, validation, and a final product demo.");
    addShape(slide, "line", 130, 305, 1010, 1, "none", { style: "solid", fill: "#AAB6C5", width: 3 });
    const phases = [
      ["Week 1", "Product and stack onboarding"],
      ["Weeks 2-3", "Track implementation starts"],
      ["Weeks 4-5", "Search, sync, and quality pass"],
      ["Weeks 6-7", "Beta hardening and analytics"],
      ["Week 8", "Demo, handoff, next backlog"]
    ];
    phases.forEach((phase, i) => {
      const x = 88 + i * 238;
      addShape(slide, "ellipse", x + 74, 286, 38, 38, [colors.blue, colors.green, colors.amber, colors.red, colors.slate][i], { style: "solid", fill: colors.white, width: 4 });
      addText(slide, phase[0], x, 350, 190, 28, { size: 18, bold: true, color: colors.ink, align: "center" });
      addText(slide, phase[1], x - 5, 388, 200, 56, { size: 14, color: colors.muted, align: "center" });
    });
    addText(slide, "Expected cadence: weekly demos, short design reviews, small pull requests, and a product metric attached to every feature.", 170, 525, 940, 64, { size: 23, bold: true, color: colors.ink, align: "center" });
    addFooter(slide, page++);
    addNotes(slide, "Build plan is an operating proposal, not a source requirement.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = colors.white;
    addTitle(slide, "Engineering Operating Model", "New grads learn how product, design, and engineering decisions connect.");
    const product = addFlowNode(slide, "User problem", "Start with a real saved item and the recall moment the user wants", 126, 228, 230, 128, "#EAF3FF", colors.blueDark);
    const spec = addFlowNode(slide, "Thin spec", "Define the smallest behavior change worth building", 420, 228, 230, 128, "#EAFBF1", "#107C41");
    const code = addFlowNode(slide, "Build", "Ship a focused increment with tests and observability", 714, 228, 230, 128, "#FFF5D8", "#9A6500");
    const learn = addFlowNode(slide, "Learn", "Review usage, latency, bugs, and the next product question", 1008, 228, 230, 128, "#FFEDEA", "#A51E18");
    connect(slide, product, spec);
    connect(slide, spec, code);
    connect(slide, code, learn);
    addText(slide, "This model keeps the internship practical. Every project should improve capture speed, search success, or user trust.", 170, 470, 940, 64, { size: 25, bold: true, color: colors.ink, align: "center" });
    addFooter(slide, page++);
    addNotes(slide, "Operating model created for the recruiting pitch.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = colors.light;
    addTitle(slide, "Why This Internship Matters", "New grads can own visible product behavior instead of isolated tasks.");
    addText(slide, "The strongest learning happens when engineers see how a small decision affects a real user flow.", 92, 170, 1040, 52, { size: 28, bold: true, color: colors.ink });
    addBullets(slide, [
      "A capture bug directly affects whether users trust the app.",
      "A slow search result directly affects whether users come back.",
      "A poor privacy choice directly affects whether users store personal knowledge.",
      "A clear demo lets interns show product judgment, not only implementation effort."
    ], 118, 275, 850, 160, { size: 21, spaceAfterPoints: 10 });
    addShape(slide, "rect", 990, 235, 140, 250, "#101820", { style: "solid", fill: "#101820", width: 0 }, 22);
    addShape(slide, "rect", 1004, 258, 112, 190, "#1A2430", { style: "solid", fill: "#2E3A49", width: 1 }, 14);
    addShape(slide, "rect", 1020, 278, 80, 22, colors.blue, { style: "solid", fill: colors.blue, width: 0 }, 6);
    addShape(slide, "rect", 1020, 318, 80, 22, colors.green, { style: "solid", fill: colors.green, width: 0 }, 6);
    addShape(slide, "rect", 1020, 358, 80, 22, colors.amber, { style: "solid", fill: colors.amber, width: 0 }, 6);
    addShape(slide, "ellipse", 1045, 460, 28, 28, "#2E3A49", { style: "solid", fill: "#5A6778", width: 1 });
    addFooter(slide, page++);
    addNotes(slide, "Phone sketch is a native editable product concept diagram, not a screenshot.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = colors.dark;
    addText(slide, "The Opportunity", 72, 86, 650, 58, { size: 38, bold: true, color: colors.white });
    addText(slide, "Build the memory layer for mobile knowledge workers.", 72, 178, 760, 96, { size: 44, bold: true, color: colors.white });
    addText(slide, "Memora is narrow by design: capture useful information once, understand it in the background, and recall it when it matters.", 76, 318, 710, 74, { size: 22, color: "#DDE6F3" });
    addPill(slide, "Mobile engineering", 80, 460, 180, "#102A4A", "#CFE7FF");
    addPill(slide, "Backend systems", 285, 460, 170, "#123A28", "#D3F8DE");
    addPill(slide, "Search and AI", 480, 460, 152, "#4A3610", "#FFE6A4");
    addPill(slide, "Product craft", 656, 460, 145, "#411A21", "#FFD4D0");
    addFooter(slide, page++, "dark");
    addNotes(slide, "Closing slide for intern recruiting conversation.");
  }

  return { deck, count: page - 1 };
}

function buildInvestorDeck() {
  const deck = Presentation.create({ slideSize: { width: W, height: H } });
  let page = 1;

  coverSlide(deck, {
    title: "Memora",
    subtitle: "A mobile-first app for capturing and recalling the useful information people save across their day",
    label: "Investor Pitch",
    image: productHero,
  });
  page += 1;

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    addInvestorTitle(slide, "Digital Recall Problem", "The internet gives people more useful information than their current tools can recover later.");
    addInvestorPanel(slide, 82, 170, 520, 260, investorColors.panelBlue);
    addInvestorPanel(slide, 674, 170, 520, 260, investorColors.panel);
    addText(slide, "Users already save the signal.", 114, 200, 430, 58, { size: 28, bold: true, color: investorColors.title });
    addInvestorBullets(slide, [
      "Screenshots of posts, charts, receipts, ideas, and references",
      "Article links, social posts, videos, and research sources",
      "Short notes copied from conversations and browsing sessions"
    ], 124, 284, 420, 132, { size: 17, spaceAfterPoints: 4 });
    addText(slide, "The saved material does not become useful memory.", 706, 200, 430, 68, { size: 28, bold: true, color: investorColors.title });
    addInvestorBullets(slide, [
      "Screenshots remain invisible to normal search",
      "Bookmarks lack context and decay into long lists",
      "Notes require effort exactly when the user wants speed"
    ], 718, 292, 420, 132, { size: 17, spaceAfterPoints: 4 });
    addInvestorPanel(slide, 152, 484, 976, 76, "#071121");
    addText(slide, "Memora's wedge is the gap between capture and recall.", 180, 501, 920, 38, { size: 28, bold: true, color: investorColors.blue, align: "center" });
    addFooter(slide, page++, "dark");
    addNotes(slide, "Problem statement from MEMORYHIVE_REQUIREMENTS.md section 2.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    addInvestorTitle(slide, "Target Customer", "Start with heavy mobile savers who feel the pain weekly.");
    const users = [
      ["Knowledge workers", "Save screenshots and links during work, then need them in meetings or analysis."],
      ["Founders and builders", "Collect product references, competitor examples, and customer signals."],
      ["Researchers", "Capture articles, papers, charts, and sources across mobile workflows."],
      ["Curious professionals", "Build a personal library of ideas without wanting a complex note system."]
    ];
    users.forEach((user, i) => {
      const x = i % 2 === 0 ? 84 : 662;
      const y = 174 + Math.floor(i / 2) * 158;
      addInvestorPanel(slide, x, y, 534, 116, i % 2 === 0 ? investorColors.panelBlue : investorColors.panelGreen);
      addText(slide, user[0], x + 24, y + 20, 320, 30, { size: 21, bold: true, color: i % 2 === 0 ? investorColors.blue : investorColors.green });
      addText(slide, user[1], x + 24, y + 58, 470, 36, { size: 15, color: investorColors.body });
    });
    addText(slide, "Non-target users clarify focus: Memora should avoid project management, social collaboration, reminders, and folder-heavy workflows in v1.", 132, 542, 1016, 58, { size: 22, bold: true, color: investorColors.title, align: "center" });
    addFooter(slide, page++, "dark");
    addNotes(slide, "Target and non-target users from MEMORYHIVE_REQUIREMENTS.md section 4.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    addInvestorTitle(slide, "Product Wedge", "One-tap capture creates the habit. Searchable recall creates retention.");
    const capture = addInvestorFlowNode(slide, "Capture once", "Share sheet, camera, gallery, URL, and text intake", 108, 228, 280, 150, investorColors.panelBlue, investorColors.blue);
    const enrich = addInvestorFlowNode(slide, "Enrich later", "OCR, readable content, summary, tags, and source metadata", 500, 228, 280, 150, investorColors.panelGreen, investorColors.green);
    const recall = addInvestorFlowNode(slide, "Recall fast", "Search across text, screenshots, source, and time", 892, 228, 280, 150, investorColors.panelAmber, investorColors.amber);
    connect(slide, capture, enrich);
    connect(slide, enrich, recall);
    addText(slide, "Product promise", 126, 470, 220, 30, { size: 19, bold: true, color: investorColors.blue });
    addText(slide, "Save the useful thing now. Find it later without remembering where it came from.", 126, 508, 815, 54, { size: 29, bold: true, color: investorColors.title });
    addFooter(slide, page++, "dark");
    addNotes(slide, "Product concept from MEMORYHIVE_REQUIREMENTS.md product summary and core use cases.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    addInvestorTitle(slide, "MVP Scope", "A focused v1 improves credibility by keeping non-core features out.");
    addInvestorPanel(slide, 98, 166, 498, 270, investorColors.panelGreen);
    addInvestorPanel(slide, 682, 166, 498, 270, investorColors.panelRed);
    addText(slide, "Included in MVP", 126, 196, 360, 32, { size: 24, bold: true, color: investorColors.green });
    addInvestorBullets(slide, [
      "Capture screenshots, links, and text",
      "Local storage and local search",
      "OCR and text extraction",
      "Simple list and item detail view",
      "Delete and export paths for user trust"
    ], 138, 252, 410, 160, { size: 19 });
    addText(slide, "Excluded from MVP", 710, 196, 360, 32, { size: 24, bold: true, color: investorColors.red });
    addInvestorBullets(slide, [
      "Task management and reminder systems",
      "Public collections or social feeds",
      "Collaboration-heavy workflows",
      "Full markdown editor",
      "Chat with notes in v1"
    ], 722, 252, 410, 160, { size: 19 });
    addInvestorPanel(slide, 152, 500, 976, 58, investorColors.panel);
    addText(slide, "The guiding rule: if a feature does not improve capture, understanding, or recall, it waits.", 184, 514, 912, 28, { size: 21, bold: true, color: investorColors.title, align: "center" });
    addFooter(slide, page++, "dark");
    addNotes(slide, "MVP and non-goals from MEMORYHIVE_REQUIREMENTS.md sections 9 and 14.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    addInvestorTitle(slide, "Positioning", "Memora has a narrow position between bookmarks, notes, and read-later tools.");
    const rows = [
      ["Bookmarks", "Store URLs but lose intent, screenshot text, and later context.", "Memora stores the object, context, and searchable extracted text."],
      ["Notes apps", "Require manual writing, folders, and maintenance.", "Memora captures first and organizes in the background."],
      ["Read-later tools", "Work best for articles, not mixed mobile captures.", "Memora supports screenshots, links, text notes, and photos."],
      ["Cloud knowledge bases", "Assume team workflows and cloud-first storage.", "Memora starts as a private, local-first personal memory app."]
    ];
    addText(slide, "Category", 92, 154, 180, 24, { size: 15, bold: true, color: investorColors.muted });
    addText(slide, "Common limitation", 346, 154, 290, 24, { size: 15, bold: true, color: investorColors.muted });
    addText(slide, "Memora advantage", 752, 154, 290, 24, { size: 15, bold: true, color: investorColors.muted });
    rows.forEach((row, i) => {
      const y = 194 + i * 94;
      addInvestorPanel(slide, 82, y, 1116, 72, i % 2 === 0 ? investorColors.panel : investorColors.panelAlt);
      addText(slide, row[0], 106, y + 20, 170, 24, { size: 18, bold: true, color: investorColors.blue });
      addText(slide, row[1], 346, y + 17, 332, 34, { size: 15, color: investorColors.body });
      addText(slide, row[2], 752, y + 17, 364, 34, { size: 15, bold: true, color: investorColors.title });
    });
    addFooter(slide, page++, "dark");
    addNotes(slide, "Positioning is inferred from the PRD problem statement, principles, and non-goals. Competitive claims are category-level hypotheses to validate.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    addSectionLabel(slide, "TECHNICAL DEFENSIBILITY", 64, 32, investorColors.blue);
    addText(slide, "Architecture and Data Layer", 64, 64, 740, 50, { size: 34, bold: true, color: investorColors.title });
    addText(slide, "A useful personal memory product depends on fast capture, reliable offline behavior, and user trust.", 66, 118, 735, 42, { size: 18, color: investorColors.muted });
    const app = addInvestorFlowNode(slide, "Mobile clients", "iOS, Android, lightweight web viewer", 80, 230, 240, 116, investorColors.panelBlue, investorColors.blue);
    const local = addInvestorFlowNode(slide, "Local memory", "Raw content, encrypted tokens, search index", 382, 230, 240, 116, investorColors.panelGreen, investorColors.green);
    const sync = addInvestorFlowNode(slide, "Sync service", "Push, pull, merge rules, retry queue", 684, 230, 240, 116, investorColors.panelAmber, investorColors.amber);
    const cloud = addInvestorFlowNode(slide, "User-owned cloud", "Metadata DB and object storage", 986, 230, 240, 116, investorColors.panelRed, investorColors.red);
    connect(slide, app, local);
    connect(slide, local, sync);
    connect(slide, sync, cloud);
    const ai = addInvestorFlowNode(slide, "Processing layer", "OCR, readable link extraction, classification, summary, auto tags", 382, 462, 542, 96, "#071F31", investorColors.blue);
    connect(slide, cloud, ai, "bottom", "right");
    connect(slide, ai, local, "left", "bottom");
    addFooter(slide, page++, "dark");
    addNotes(slide, "Architecture from MEMORA_README.md and MEMORYHIVE_REQUIREMENTS.md sections 7, 10, and 11.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    addInvestorTitle(slide, "Roadmap", "The product can scale in layers while keeping v1 focused.");
    const phases = [
      ["Phase 1", "MVP base", "Auth, item capture, local storage, dashboard, search, settings"],
      ["Phase 2", "Sync and polish", "Background sync, pull-to-refresh, conflict UI, retry logic"],
      ["Phase 3", "AI integration", "OCR, summaries, keyword extraction, auto tags"],
      ["Phase 4", "Distribution features", "Share sheet, export, deep links, widget support"]
    ];
    phases.forEach((phase, i) => {
      const x = 88 + i * 292;
      const accent = [investorColors.blue, investorColors.green, investorColors.amber, investorColors.red][i];
      addInvestorPanel(slide, x, 185, 240, 264, investorColors.panel);
      addShape(slide, "rect", x, 185, 240, 8, accent, { style: "solid", fill: "none", width: 0 });
      addText(slide, phase[0], x + 22, 220, 160, 24, { size: 15, bold: true, color: investorColors.muted });
      addText(slide, phase[1], x + 22, 254, 192, 56, { size: 22, bold: true, color: accent });
      addText(slide, phase[2], x + 22, 326, 190, 88, { size: 15, color: investorColors.body });
    });
    addText(slide, "The README marks Phase 1 capabilities as built. Investor diligence should confirm product completeness, code quality, and user readiness.", 146, 525, 988, 52, { size: 21, bold: true, color: investorColors.title, align: "center" });
    addFooter(slide, page++, "dark");
    addNotes(slide, "Roadmap from MEMORA_README.md. Status should be validated against the current app before external fundraising use.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    addInvestorTitle(slide, "Business Model", "Monetization should follow trust: keep core capture useful, charge for higher value layers.");
    const free = addInvestorFlowNode(slide, "Free local tier", "Private capture, local search, basic item limits, export", 110, 220, 300, 170, investorColors.panelBlue, investorColors.blue);
    const paid = addInvestorFlowNode(slide, "Paid sync tier", "Cross-device sync, larger storage, backups, priority processing", 490, 220, 300, 170, investorColors.panelGreen, investorColors.green);
    const pro = addInvestorFlowNode(slide, "Advanced AI tier", "Stronger summaries, OCR for larger libraries, related-item discovery", 870, 220, 300, 170, investorColors.panelAmber, investorColors.amber);
    connect(slide, free, paid);
    connect(slide, paid, pro);
    addText(slide, "Pricing remains a validation item before packaging decisions.", 146, 488, 988, 40, { size: 27, bold: true, color: investorColors.title, align: "center" });
    addText(slide, "Early tests should measure willingness to pay for sync, recovery confidence, and search quality before optimizing packaging.", 194, 538, 892, 42, { size: 17, color: investorColors.muted, align: "center" });
    addFooter(slide, page++, "dark");
    addNotes(slide, "Monetization direction from MEMORYHIVE_REQUIREMENTS.md section 12. Specific prices were not provided.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    addInvestorTitle(slide, "Go-to-Market", "A credible launch starts with workflows where saved information already has obvious value.");
    const motions = [
      ["Founder workflow", "Competitor screenshots, customer quotes, product references", "Build examples from real saved libraries"],
      ["Research workflow", "Articles, papers, charts, reports, source links", "Show OCR and source recall in public demos"],
      ["Professional workflow", "Receipts, snippets, posts, useful links from mobile browsing", "Launch with a weekly search challenge"],
      ["Builder community", "Indie hackers, students, analysts, product managers", "Seed beta through build-in-public updates"]
    ];
    motions.forEach((motion, i) => {
      const y = 166 + i * 96;
      addInvestorRow(slide, motion[0], motion[1], motion[2], y, [investorColors.blue, investorColors.green, investorColors.amber, investorColors.red][i], i % 2 === 0 ? investorColors.panel : investorColors.panelAlt);
    });
    addFooter(slide, page++, "dark");
    addNotes(slide, "Go-to-market motions are recommendations derived from the target users in the PRD. No external traction data was provided.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    addInvestorTitle(slide, "Use of Funds", "Capital should convert the MVP into a measurable beta and app store launch.");
    const funds = [
      ["Product polish", "Capture reliability, onboarding, search UX, accessibility, and app store readiness"],
      ["Sync and security", "Cross-device sync, export/delete flows, auth hardening, storage controls"],
      ["AI processing", "OCR quality, summary pipeline, tag suggestions, link extraction, local model options"],
      ["Beta growth", "Founder and knowledge-worker beta cohorts, usage analytics, interview loop"]
    ];
    funds.forEach((fund, i) => {
      const x = i % 2 === 0 ? 96 : 674;
      const y = 178 + Math.floor(i / 2) * 152;
      const accent = [investorColors.blue, investorColors.green, investorColors.amber, investorColors.red][i];
      addInvestorPanel(slide, x, y, 510, 110, i % 2 === 0 ? investorColors.panel : investorColors.panelAlt);
      addText(slide, fund[0], x + 24, y + 20, 300, 26, { size: 20, bold: true, color: accent });
      addText(slide, fund[1], x + 24, y + 58, 440, 34, { size: 15, color: investorColors.body });
    });
    addText(slide, "Round amount, valuation, and runway assumptions should be inserted before investor circulation.", 144, 550, 992, 44, { size: 22, bold: true, color: investorColors.title, align: "center" });
    addFooter(slide, page++, "dark");
    addNotes(slide, "Funding allocation is a proposed use of funds. The source materials did not include round size or financial model.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    addInvestorTitle(slide, "Next Milestones", "The next phase should produce evidence investors can diligence.");
    const milestones = [
      ["90 days", "Private beta ready", "Reliable capture, local search, OCR path, and feedback loop with first users"],
      ["180 days", "Public app launch", "App store release, paid sync validation, support path, and retention baseline"],
      ["Fundable evidence", "Usage quality", "Activation, weekly repeat saves, search success, paid intent, and privacy trust signals"]
    ];
    milestones.forEach((m, i) => {
      const x = 88 + i * 386;
      const accent = [investorColors.blue, investorColors.green, investorColors.amber][i];
      addInvestorPanel(slide, x, 206, 314, 246, investorColors.panel);
      addText(slide, m[0], x + 24, 238, 220, 26, { size: 17, bold: true, color: investorColors.muted });
      addText(slide, m[1], x + 24, 278, 250, 62, { size: 24, bold: true, color: accent });
      addText(slide, m[2], x + 24, 354, 248, 64, { size: 15, color: investorColors.body });
    });
    addText(slide, "This pitch should be paired with a live product demo and a short metric sheet once beta usage begins.", 164, 528, 950, 48, { size: 23, bold: true, color: investorColors.title, align: "center" });
    addFooter(slide, page++, "dark");
    addNotes(slide, "Milestones are proposed planning targets for fundraising readiness.");
  }

  {
    const slide = deck.slides.add();
    slide.background.fill = investorColors.bg;
    slide.images.add({
      blob: productHero,
      contentType: "image/png",
      alt: "Memora product visual",
      fit: "cover",
      position: { left: 648, top: 0, width: 632, height: 720 },
      crop: { left: 0.28, top: 0, right: 0, bottom: 0 },
    });
    addShape(slide, "rect", 0, 0, W, H, "#05070C/66", { style: "solid", fill: "none", width: 0 });
    addText(slide, "Funding Ask", 72, 88, 560, 50, { size: 38, bold: true, color: investorColors.title });
    addText(slide, "Help move Memora from focused MVP to measurable beta.", 72, 178, 610, 110, { size: 43, bold: true, color: investorColors.title });
    addInvestorBullets(slide, [
      "Finish the app store-ready mobile experience.",
      "Validate sync and AI as paid value layers.",
      "Build evidence around activation, recall success, and retention.",
      "Insert round amount and terms before external circulation."
    ], 86, 344, 570, 152, { size: 20, color: investorColors.body, spaceAfterPoints: 9 });
    addFooter(slide, page++, "dark");
    addNotes(slide, "Ask slide contains a placeholder because round size and terms were not supplied.");
  }

  return { deck, count: page - 1 };
}

const target = process.argv.includes("--investor-only")
  ? "investor"
  : process.argv.includes("--intern-only")
    ? "intern"
    : "all";
const outputs = [];

if (target !== "investor") {
  const intern = buildInternDeck();
  outputs.push(await finalizeDeck(intern.deck, "Memora_Intern_Recruiting_Deck.pptx", intern.count));
}

if (target !== "intern") {
  const investor = buildInvestorDeck();
  const filename = process.argv.includes("--black-theme")
    ? "Memora_Investor_Pitch_Deck_Black_Theme.pptx"
    : "Memora_Investor_Pitch_Deck.pptx";
  outputs.push(await finalizeDeck(investor.deck, filename, investor.count));
}

console.log(JSON.stringify({
  font: family,
  outputs,
}, null, 2));
